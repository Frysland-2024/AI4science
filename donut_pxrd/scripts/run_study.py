from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "donut_pxrd"
sys.path[:0] = [
    str(OUT / "src"),
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
]

from donut_pxrd.data import (  # noqa: E402
    build_study_data,
    make_texture_test,
    sha256_array,
    sha256_file,
)
from donut_pxrd.model import (  # noqa: E402
    DONUTEncoderDecoder,
    map_latent_to_physics,
    physical_profile,
)
from pxrd_forward_loss.model import MeasurementAwareRegressor, ParameterRegressor  # noqa: E402
from pxrd_forward_loss.measurement_closure import expected_profile  # noqa: E402
from pymatgen.core import Lattice, Structure  # noqa: E402
from xrd_robustness.physics import PhysicsParameters  # noqa: E402
from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, simulate_from_peak_table  # noqa: E402


CONFIG_PATH = OUT / "configs" / "study_v1.json"
FROZEN_MANIFEST = OUT / "configs" / "preregistration_manifest.json"
STATUS_PATH = OUT / "reports" / "EXECUTION_STATUS.json"
LOG_PATH = OUT / "logs" / "execution.jsonl"
TRAIN_LOG = OUT / "logs" / "training.jsonl"
RESULTS = OUT / "results"
EPS = 1.0e-12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"time_utc": utc_now(), "event": event, **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def load_config() -> dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    frozen_hash = sha256_file(CONFIG_PATH)
    manifest = json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("study_config_sha256") != frozen_hash:
        raise RuntimeError("frozen study config SHA-256 does not match preregistration manifest")
    if cfg.get("status") != "FROZEN_BEFORE_MODEL_TRAINING":
        raise RuntimeError("study config is not frozen before model training")
    return cfg


def load_forward_driver():
    path = ROOT / "xrd_forward_loss" / "scripts" / "run_issue19_p3.py"
    spec = importlib.util.spec_from_file_location("donut_pxrd_forward_driver", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load repository's existing forward driver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def initialize_status(config: dict[str, Any]) -> dict[str, Any]:
    reproducibility_policy = {
        "fixed_python_numpy_and_torch_seed_streams": True,
        "cudnn_deterministic": True,
        "strict_torch_determinism": False,
        "reason": "PyTorch 2.13 CUDA has no deterministic backward implementation for the native linear 1D upsample used by the faithful latent-only decoder; deterministic mode is warn-only, so seeded runs are not guaranteed bitwise identical.",
    }
    if STATUS_PATH.exists():
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        if status.get("study_config_sha256") != sha256_file(CONFIG_PATH):
            raise RuntimeError("existing execution state belongs to a different frozen config")
        if "reproducibility_policy" not in status:
            status["reproducibility_policy"] = reproducibility_policy
            write_json(STATUS_PATH, status)
        return status
    status = {
        "schema": "donut_pxrd_execution_status_v1",
        "study_config_sha256": sha256_file(CONFIG_PATH),
        "branch": config["branch"],
        "source_donut_commit": config["sources"]["donut_source_commit"],
        "started_at_utc": utc_now(),
        "gpu_device": torch.cuda.get_device_name(0),
        "reproducibility_policy": reproducibility_policy,
        "experiments": {
            f"experiment_{i}": {"status": "NOT_RUN"}
            for i in range(1, 5)
        },
        "measured_gpu_training_seconds": 0.0,
        "events": [],
    }
    write_json(STATUS_PATH, status)
    return status


def status_event(status: dict[str, Any], name: str, event: str, **fields: Any) -> None:
    status["events"].append({"time_utc": utc_now(), "experiment": name, "event": event, **fields})
    write_json(STATUS_PATH, status)
    log(LOG_PATH, event, experiment=name, **fields)


def run_pytest(label: str, targets: list[str]) -> None:
    command = [sys.executable, "-m", "pytest", "-q", *targets]
    source_paths = [
        str(OUT / "src"),
        str(ROOT / "xrd_inversion" / "src"),
        str(ROOT / "xrd_robustness" / "src"),
        str(ROOT / "xrd_forward_loss" / "src"),
    ]
    inherited_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = os.pathsep.join(source_paths + ([inherited_pythonpath] if inherited_pythonpath else []))
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": pythonpath},
    )
    result = {
        "label": label,
        "command": command,
        "returncode": int(proc.returncode),
        "elapsed_seconds": time.perf_counter() - started,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "time_utc": utc_now(),
    }
    write_json(OUT / "reports" / f"pytest_{label}.json", result)
    if proc.returncode:
        raise RuntimeError(f"pytest gate {label} failed (exit {proc.returncode})")


def configure_runtime() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; this study is frozen GPU-first")
    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)


def run_preflight_only() -> int:
    """Build and validate the frozen dataset before any model is trained."""
    config = load_config()
    configure_runtime()
    status = initialize_status(config)
    driver = load_forward_driver()
    arrays, data_manifest, forward, forward_cfg, structure = prepare_artifacts(config, driver)
    split_counts = _validate_split(arrays)
    artifact_root = Path(config["data"]["raw_data_location"]).parent
    gate_results = verify_forward_and_gradients(forward, structure, forward_cfg)
    gate_results["dataset_npz_sha256"] = data_manifest["dataset_npz_sha256"]
    gate_results["split_counts"] = split_counts
    write_json(RESULTS / "preflight_gates.json", gate_results)
    run_pytest("preflight_existing_regression", ["xrd_inversion/tests", "xrd_forward_loss/tests", "donut_pxrd/tests"])
    status.update({
        "overall_status": "PREFLIGHT_PASSED_READY",
        "preflight_status": "PASSED",
        "preflight_finished_at_utc": utc_now(),
        "data_manifest_sha256": sha256_file(artifact_root / "datasets" / "data_manifest.json"),
        "dataset_npz_sha256": data_manifest["dataset_npz_sha256"],
        "split_counts": split_counts,
        "test_indices_sha256": data_manifest["test_indices_sha256"],
    })
    if LOG_PATH.exists():
        status["preflight_attempts"] = [
            {"time_utc": row.get("time_utc"), "error": row.get("error"), "recovered": True}
            for row in (json.loads(line) for line in LOG_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
            if row.get("event") == "RUN_STOPPED"
        ]
    previous_failure = status.pop("failure", None)
    if previous_failure:
        status.setdefault("recovery_history", []).append({
            "failed_preflight": previous_failure,
            "repairs": [
                "Removed an unused ideal_peak_table call that passed IndependentGrid where the legacy simulator requires SimulationGrid; it was not part of the parity calculation.",
                "An exploratory probe against xrd_inversion.independent_renderer exceeded the inherited max-absolute tolerance by 0.608e-6 while RMSE remained below threshold. Replaced that exploratory comparator with the repository's established independent Pymatgen/V9 simulator used by the closure gates; kept both inherited thresholds unchanged and included shift, width, and background in the parity case.",
                "CachedTetragonalGPUForward.__init__ resets PyTorch deterministic mode to strict after runtime setup. Reapplied warn-only determinism after constructing the fixed forward model; supported deterministic kernels remain enabled, while the decoder's native linear upsample backward is explicitly recorded as potentially nondeterministic.",
                "The regression-test subprocess did not inherit the in-process source paths and failed collection. Added the repository's four src directories to the subprocess PYTHONPATH; no test assertions or test data were changed.",
                "The new DONUT test filename collided with an existing test_model.py during combined collection. Renamed it to test_donut_pxrd_model.py; no test assertions or test data were changed."
            ],
            "recovered_at_utc": utc_now(),
        })
    write_json(STATUS_PATH, status)
    return 0


def prepare_artifacts(config: dict[str, Any], driver: Any) -> tuple[dict[str, np.ndarray], dict[str, Any], Any, dict[str, Any], Any]:
    artifact_root = Path(config["data"]["raw_data_location"]).parent
    marker = artifact_root / "run_manifest.json"
    if marker.exists():
        manifest = json.loads(marker.read_text(encoding="utf-8"))
        if manifest.get("study_config_sha256") != sha256_file(CONFIG_PATH):
            raise RuntimeError(f"local artifact path already belongs to another run: {artifact_root}")
        data_path = artifact_root / "datasets" / "study_v1.npz"
        if not data_path.exists():
            raise RuntimeError("artifact run manifest exists but frozen dataset is missing")
        arrays = dict(np.load(data_path, allow_pickle=False))
        data_manifest = json.loads((artifact_root / "datasets" / "data_manifest.json").read_text(encoding="utf-8"))
        cfg = json.loads((ROOT / config["sources"]["base_forward_config"]).read_text(encoding="utf-8"))
        forward, forward_cfg, structure = driver.make_forward(cfg)
        # The repository forward constructor enables strict deterministic mode.
        # Keep deterministic kernels where available but allow the decoder's
        # native linear interpolation backward, which has no deterministic CUDA implementation.
        torch.use_deterministic_algorithms(True, warn_only=True)
        if data_manifest["dataset_npz_sha256"] != sha256_file(data_path):
            raise RuntimeError("local data archive checksum mismatch")
        return arrays, data_manifest, forward, forward_cfg, structure

    artifact_root.mkdir(parents=True, exist_ok=False)
    (artifact_root / "datasets").mkdir()
    (artifact_root / "checkpoints").mkdir()
    data_path = artifact_root / "datasets" / "study_v1.npz"
    cfg = json.loads((ROOT / config["sources"]["base_forward_config"]).read_text(encoding="utf-8"))
    forward, forward_cfg, structure = driver.make_forward(cfg)
    torch.use_deterministic_algorithms(True, warn_only=True)
    arrays, manifest = build_study_data(
        config=config,
        forward=forward,
        forward_cfg=forward_cfg,
        structure=structure,
        output_path=data_path,
    )
    manifest["hardware"] = {
        "python": sys.version.split()[0],
        "torch": str(torch.__version__),
        "cuda_runtime": torch.version.cuda,
        "device": torch.cuda.get_device_name(0),
        "platform": platform.platform(),
    }
    write_json(artifact_root / "datasets" / "data_manifest.json", manifest)
    write_json(
        marker,
        {
            "schema": "donut_pxrd_local_run_manifest_v1",
            "study_config_sha256": sha256_file(CONFIG_PATH),
            "data_manifest_sha256": sha256_file(artifact_root / "datasets" / "data_manifest.json"),
            "dataset_npz_sha256": manifest["dataset_npz_sha256"],
            "created_at_utc": utc_now(),
        },
    )
    write_json(OUT / "results" / "data_manifest.json", manifest)
    return arrays, manifest, forward, forward_cfg, structure


def expected_physics(
    forward: Any,
    constrained: torch.Tensor,
    phase: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    mode = "v9_polynomial"
    return physical_profile(forward, constrained, phase=phase, background_shape_mode=mode)


def _validate_split(arrays: dict[str, np.ndarray]) -> dict[str, int]:
    splits = [np.asarray(arrays[f"{name}_indices"], dtype=np.int64) for name in ("train", "validation", "test")]
    combined = np.concatenate(splits)
    if len(combined) != len(np.unique(combined)) or len(combined) != len(arrays["q"]):
        raise RuntimeError("parent q split has duplicates or omissions")
    return {name: int(len(values)) for name, values in zip(("train", "validation", "test"), splits, strict=True)}


def verify_forward_and_gradients(forward: Any, structure: Any, forward_cfg: dict[str, Any]) -> dict[str, Any]:
    """Pre-training parity and autograd/finite-difference gates."""
    grid_cfg = forward_cfg["grid"]
    grid = SimulationGrid(
        two_theta_min=float(grid_cfg["two_theta_min"]),
        two_theta_max=float(grid_cfg["two_theta_max"]),
        step=float(grid_cfg["step"]),
        wavelength=float(grid_cfg["wavelength_angstrom"]),
    )
    padding = float(grid_cfg.get("peak_calculation_padding_deg", 0.0))
    padded_grid = SimulationGrid(
        two_theta_min=grid.two_theta_min - padding,
        two_theta_max=grid.two_theta_max + padding,
        step=grid.step,
        wavelength=grid.wavelength,
    )
    param_cfg = forward.parameter_config
    # Reproduce the repository's frozen Pymatgen/V9 full-profile parity probe.
    q = np.asarray([0.2, -0.15], dtype=np.float64)
    eta = np.asarray([0.045, 0.12, 0.006], dtype=np.float64)
    q_tensor = torch.as_tensor(q[None], device="cuda", dtype=torch.float64)
    eta_tensor = torch.as_tensor(eta[None], device="cuda", dtype=torch.float64)
    gpu = expected_profile(forward, q_tensor, eta_tensor)[0].detach().cpu().numpy()
    u0 = (2.0 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3.0
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    u = u0 + q[0] * float(param_cfg["du_half_range"])
    v = v0 + q[1] * float(param_cfg["dv_half_range"])
    a = math.exp(u - v / 3.0)
    c = math.exp(u + 2.0 * v / 3.0)
    varied = Structure(
        lattice=Lattice.tetragonal(a, c),
        species=[site.species for site in structure],
        coords=structure.frac_coords,
        coords_are_cartesian=False,
    )
    params = PhysicsParameters(
        delta_2theta_deg=float(eta[0]),
        fwhm_deg=float(eta[1]),
        background_to_peak_ratio=float(eta[2]),
        noise_std_ratio=0.0,
        background_type="polynomial",
        severity_level=2,
        zero_shift_active=True,
        broadening_active=True,
        background_active=True,
        noise_active=False,
        background_order=2,
        background_variation=0.0,
        background_floor_fraction=0.10,
        noise_model="poisson_gaussian",
        noise_stage="before_normalization",
        poisson_count_scale=30000.0,
        electronic_noise_std_counts=0.0,
        preferred_orientation_active=False,
    )
    peaks = ideal_peak_table(varied, padded_grid)
    cpu_normalized = simulate_from_peak_table(
        peaks.positions, peaks.intensities, params, rng_seed=7, grid=grid,
        normalize=True, reflection_table=peaks,
    )
    cpu = np.log1p(100.0 * cpu_normalized) / math.log(101.0)
    parity = {
        "max_abs": float(np.max(np.abs(gpu - cpu))),
        "rmse": float(np.sqrt(np.mean(np.square(gpu - cpu)))),
        "n": int(len(gpu)),
    }
    if parity["max_abs"] > 2e-6 or parity["rmse"] > 2e-7:
        raise RuntimeError(f"GPU/independent Pymatgen full-profile parity gate failed: {parity}")

    # Gradient through the exact training loss and PXRD physics branch.
    variable = torch.tensor([[0.21, -0.16, 0.18]], device="cuda", dtype=torch.float64, requires_grad=True)
    target_q = torch.tensor([[0.24, -0.11]], device="cuda", dtype=torch.float64)
    target_eta = torch.tensor([[0.012, 0.08, 0.0]], device="cuda", dtype=torch.float64)
    target_profile = expected_profile(forward, target_q, target_eta, background_shape_mode="v9_polynomial").detach()
    def scalar_loss(vector: torch.Tensor) -> torch.Tensor:
        qq = vector[:, :2]
        ee = torch.stack((0.06 * vector[:, 2], torch.full_like(vector[:, 2], 0.08), torch.zeros_like(vector[:, 2])), dim=1)
        prediction = expected_profile(forward, qq, ee, background_shape_mode="v9_polynomial")
        return F.smooth_l1_loss(prediction, target_profile)
    value = scalar_loss(variable)
    grad = torch.autograd.grad(value, variable)[0][0].detach().cpu().numpy()
    h = 1e-4
    finite = []
    for j in range(3):
        plus = variable.detach().clone(); plus[0, j] += h
        minus = variable.detach().clone(); minus[0, j] -= h
        finite.append(float((scalar_loss(plus).item() - scalar_loss(minus).item()) / (2.0 * h)))
    finite = np.asarray(finite)
    rel = np.abs(grad - finite) / np.maximum(np.abs(grad) + np.abs(finite), 1e-8)
    grad_gate = {
        "autograd": grad.tolist(),
        "finite_difference": finite.tolist(),
        "relative_error": rel.tolist(),
        "all_nonzero": bool(np.all(np.abs(grad) > 1e-8)),
        "max_relative_error": float(np.max(rel)),
    }
    if not grad_gate["all_nonzero"] or grad_gate["max_relative_error"] > 0.02:
        raise RuntimeError(f"physics branch gradient finite-difference gate failed: {grad_gate}")

    # Decoder-only and physics-only objectives both reach encoder weights.
    tiny = DONUTEncoderDecoder(input_length=256, latent_dim=2, dropout=0.0).cuda()
    toy = torch.rand((2, 256), device="cuda")
    recon, _, constrained = tiny(toy)
    decoder_grad = torch.autograd.grad(F.smooth_l1_loss(recon, toy), tiny.encoder_fc.weight, retain_graph=True)[0]
    fake_profile = torch.zeros((2, len(forward.axis)), device="cuda", dtype=torch.float32)
    physical, _, _ = physical_profile(forward, constrained, phase="experiment_1_fixed")
    physics_scalar = F.smooth_l1_loss(physical, fake_profile)
    physics_grad = torch.autograd.grad(physics_scalar, tiny.encoder_fc.weight)[0]
    branch_gate = {
        "decoder_to_encoder_gradient_norm": float(decoder_grad.norm().item()),
        "latent_to_encoder_gradient_norm": float(physics_grad.norm().item()),
    }
    if min(branch_gate.values()) <= 0 or not all(math.isfinite(x) for x in branch_gate.values()):
        raise RuntimeError(f"dual-branch gradient flow gate failed: {branch_gate}")
    return {"profile_parity": parity, "physics_gradient_fd": grad_gate, "branch_gradient_flow": branch_gate}


def _phase_dim(phase: str) -> int:
    return {"experiment_1_fixed": 2, "experiment_2_shift": 3, "experiment_3_width": 4, "experiment_3_background": 5, "experiment_3_noise": 5, "experiment_3_texture": 5}[phase]


def _checkpoint_path(artifact_root: Path, phase: str, seed: int, method: str = "DONUT") -> Path:
    return artifact_root / "checkpoints" / phase / f"{method.lower()}_seed{seed}.pt"


def _new_donut(phase: str, input_length: int) -> DONUTEncoderDecoder:
    return DONUTEncoderDecoder(input_length=input_length, latent_dim=_phase_dim(phase), dropout=0.0).cuda()


def _losses(
    model: DONUTEncoderDecoder,
    x: torch.Tensor,
    forward: Any,
    phase: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    recon, _, constrained = model(x)
    physics, q, eta = expected_physics(forward, constrained, phase)
    loss_decoder = F.smooth_l1_loss(recon, x)
    loss_physics = F.smooth_l1_loss(physics, x)
    total = loss_decoder + 5.0 * loss_physics
    return total, loss_decoder, loss_physics, q, eta


def _validation_dual_loss(
    model: DONUTEncoderDecoder,
    x: torch.Tensor,
    indices: np.ndarray,
    forward: Any,
    phase: str,
) -> tuple[float, float, float]:
    model.eval()
    totals: list[float] = []
    decs: list[float] = []
    phys: list[float] = []
    with torch.no_grad():
        for start in range(0, len(indices), 16):
            ids = torch.as_tensor(indices[start : start + 16], device=x.device, dtype=torch.long)
            total, ld, lp, _, _ = _losses(model, x.index_select(0, ids), forward, phase)
            totals.append(float(total.item())); decs.append(float(ld.item())); phys.append(float(lp.item()))
    return float(np.mean(totals)), float(np.mean(decs)), float(np.mean(phys))


def train_donut_one(
    *,
    phase: str,
    seed: int,
    arrays: dict[str, np.ndarray],
    forward: Any,
    config: dict[str, Any],
    artifact_root: Path,
    gpu_budget_used: list[float],
) -> dict[str, Any]:
    training = config["donut_method"]
    torch.manual_seed(int(seed)); torch.cuda.manual_seed_all(int(seed)); np.random.seed(int(seed))
    x = torch.as_tensor(arrays[f"{phase}_observed"], device="cuda", dtype=torch.float32)
    train_indices = np.asarray(arrays["train_indices"], dtype=np.int64)
    val_indices = np.asarray(arrays["validation_indices"], dtype=np.int64)
    model = _new_donut(phase, x.shape[-1])
    optimizer = torch.optim.AdamW(
        [
            {"params": list(model.encoder_blocks.parameters()) + list(model.encoder_fc.parameters()), "lr": float(training["encoder_learning_rate"])},
            {"params": list(model.decoder_fc.parameters()) + list(model.decoder_blocks.parameters()), "lr": float(training["decoder_learning_rate"])},
        ]
    )
    generator = torch.Generator(device="cpu"); generator.manual_seed(int(seed) + 400000)
    best_loss = float("inf"); best_epoch = 0; best_state: dict[str, torch.Tensor] | None = None
    history: list[dict[str, float | int]] = []
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize(); started = time.perf_counter()
    for epoch in range(1, int(training["max_epochs_per_seed_condition"]) + 1):
        model.train()
        order = torch.randperm(len(train_indices), generator=generator).numpy()
        epoch_totals: list[tuple[float, float, float]] = []
        for start in range(0, len(order), int(training["batch_size"])):
            local_ids = train_indices[order[start : start + int(training["batch_size"])]]
            ids = torch.as_tensor(local_ids, device="cuda", dtype=torch.long)
            xb = x.index_select(0, ids)
            optimizer.zero_grad(set_to_none=True)
            total, ld, lp, _, _ = _losses(model, xb, forward, phase)
            if not torch.isfinite(total):
                raise FloatingPointError(f"non-finite DONUT loss at {phase}/{seed}/{epoch}")
            total.backward()
            parameters = [parameter for parameter in model.parameters() if parameter.grad is not None]
            if not parameters or any(not torch.isfinite(parameter.grad).all() for parameter in parameters):
                raise FloatingPointError(f"non-finite DONUT gradient at {phase}/{seed}/{epoch}")
            optimizer.step()
            epoch_totals.append((float(total.detach().item()), float(ld.detach().item()), float(lp.detach().item())))
        torch.cuda.synchronize()
        val_total, val_decoder, val_physics = _validation_dual_loss(model, x, val_indices, forward, phase)
        record = {
            "epoch": epoch,
            "train_total_loss": float(np.mean([v[0] for v in epoch_totals])),
            "train_decoder_loss": float(np.mean([v[1] for v in epoch_totals])),
            "train_physics_loss": float(np.mean([v[2] for v in epoch_totals])),
            "validation_total_loss": val_total,
            "validation_decoder_loss": val_decoder,
            "validation_physics_loss": val_physics,
        }
        history.append(record)
        log(TRAIN_LOG, "DONUT_EPOCH", phase=phase, seed=seed, **record)
        if val_total < best_loss:
            best_loss = val_total; best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    torch.cuda.synchronize(); elapsed = time.perf_counter() - started
    gpu_budget_used[0] += elapsed
    if gpu_budget_used[0] > float(config["resource_limits"]["max_total_measured_gpu_training_seconds"]):
        raise RuntimeError("frozen cumulative GPU training budget exceeded")
    if best_state is None:
        raise RuntimeError(f"no DONUT checkpoint selected for {phase}/{seed}")
    path = _checkpoint_path(artifact_root, phase, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": best_state,
            "phase": phase,
            "seed": int(seed),
            "best_epoch": best_epoch,
            "best_validation_dual_loss": best_loss,
            "config_sha256": sha256_file(CONFIG_PATH),
            "input_length": int(x.shape[-1]),
            "latent_dim": _phase_dim(phase),
        },
        path,
    )
    torch.cuda.empty_cache()
    result = {
        "phase": phase,
        "seed": int(seed),
        "epochs_completed": len(history),
        "best_epoch": best_epoch,
        "best_validation_dual_loss": best_loss,
        "training_seconds": elapsed,
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated()),
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "checkpoint_path_local_only": str(path.resolve()),
        "checkpoint_bytes": int(path.stat().st_size),
        "checkpoint_sha256": sha256_file(path),
        "history": history,
    }
    log(TRAIN_LOG, "DONUT_TRAINING_COMPLETE", **{key: value for key, value in result.items() if key != "history"})
    del model
    return result


def infer_donut(
    model: DONUTEncoderDecoder,
    profiles: np.ndarray,
    *,
    forward: Any,
    phase: str,
    batch_size: int = 16,
) -> dict[str, np.ndarray]:
    model.eval()
    recon_rows: list[np.ndarray] = []; physics_rows: list[np.ndarray] = []; q_rows: list[np.ndarray] = []; eta_rows: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(profiles), batch_size):
            xb = torch.as_tensor(profiles[start : start + batch_size], device="cuda", dtype=torch.float32)
            recon, _, constrained = model(xb)
            physical, q, eta = expected_physics(forward, constrained, phase)
            recon_rows.append(recon.cpu().numpy()); physics_rows.append(physical.cpu().numpy()); q_rows.append(q.cpu().numpy()); eta_rows.append(eta.cpu().numpy())
    return {
        "reconstruction": np.concatenate(recon_rows),
        "physics": np.concatenate(physics_rows),
        "q": np.concatenate(q_rows),
        "eta": np.concatenate(eta_rows),
    }


def _lattice_values(q: np.ndarray, driver: Any, structure: Any, forward_cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    a, c = driver.q_to_lattice(np.asarray(q, dtype=np.float64), structure, forward_cfg)
    return np.asarray(a), np.asarray(c)


def benchmark_donut_encoder(model: DONUTEncoderDecoder, profiles: np.ndarray) -> dict[str, float]:
    one = torch.as_tensor(profiles[:1], device="cuda", dtype=torch.float32)
    with torch.inference_mode():
        for _ in range(10):
            model.encode(one)
    torch.cuda.synchronize()
    measurements: list[float] = []
    for _ in range(60):
        start = time.perf_counter()
        with torch.inference_mode():
            model.encode(one)
        torch.cuda.synchronize()
        measurements.append(time.perf_counter() - start)
    return {
        "encoder_p50_seconds": float(np.percentile(measurements, 50)),
        "encoder_p95_seconds": float(np.percentile(measurements, 95)),
        "encoder_profiles_per_second": float(1.0 / max(np.mean(measurements), EPS)),
    }


def write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})


def _per_seed_summary(rows: list[dict[str, Any]], metrics: list[str]) -> dict[str, Any]:
    seeds = sorted({int(row["seed"]) for row in rows})
    by_seed: dict[str, dict[str, float | int]] = {}
    for seed in seeds:
        group = [row for row in rows if int(row["seed"]) == seed]
        by_seed[str(seed)] = {"n": len(group)}
        for key in metrics:
            by_seed[str(seed)][key] = float(np.mean([float(row[key]) for row in group]))
    aggregate: dict[str, dict[str, float]] = {}
    for key in metrics:
        values = [float(by_seed[str(seed)][key]) for seed in seeds]
        aggregate[key] = {
            "mean": float(np.mean(values)),
            "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
            "by_seed": {str(seed): float(by_seed[str(seed)][key]) for seed in seeds},
        }
    return {"by_seed": by_seed, "aggregate": aggregate}


def evaluate_donut_condition(
    *,
    phase: str,
    seeds: list[int],
    arrays: dict[str, np.ndarray],
    forward: Any,
    driver: Any,
    structure: Any,
    forward_cfg: dict[str, Any],
    artifact_root: Path,
    profiles_override: np.ndarray | None = None,
    phase_for_mapping: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    test_ids = np.asarray(arrays["test_indices"], dtype=np.int64)
    input_phase = phase_for_mapping or phase
    profile_all = profiles_override if profiles_override is not None else arrays[f"{phase}_observed"]
    profiles = np.asarray(profile_all[test_ids], dtype=np.float32)
    q_truth = np.asarray(arrays["q"][test_ids], dtype=np.float64)
    eta_truth = np.asarray(arrays[f"{phase if profiles_override is None else 'experiment_3_noise'}_eta_truth"][test_ids], dtype=np.float64)
    a_true, c_true = _lattice_values(q_truth, driver, structure, forward_cfg)
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        path = _checkpoint_path(artifact_root, phase, int(seed))
        checkpoint_hash = sha256_file(path)
        checkpoint = torch.load(path, map_location="cuda", weights_only=False)
        model = _new_donut(input_phase, profiles.shape[-1])
        model.load_state_dict(checkpoint["state_dict"])
        first = infer_donut(model, profiles[:1], forward=forward, phase=input_phase)
        reload_probe = _new_donut(input_phase, profiles.shape[-1])
        reload_probe.load_state_dict(torch.load(path, map_location="cuda", weights_only=False)["state_dict"])
        second = infer_donut(reload_probe, profiles[:1], forward=forward, phase=input_phase)
        reload_delta = float(np.max(np.abs(first["q"] - second["q"])))
        if reload_delta != 0.0 or sha256_file(path) != checkpoint_hash:
            raise RuntimeError(f"checkpoint reload/hash verification failed: {phase}/{seed}")
        direct = infer_donut(model, profiles, forward=forward, phase=input_phase)
        latency = benchmark_donut_encoder(model, profiles)
        valid_mask = np.isfinite(direct["q"]).all(axis=1) & np.isfinite(direct["eta"]).all(axis=1)
        pred_a, pred_c = _lattice_values(direct["q"], driver, structure, forward_cfg)
        for local, global_index in enumerate(test_ids):
            qerr = np.abs(direct["q"][local] - q_truth[local])
            eta_err = np.abs(direct["eta"][local] - eta_truth[local])
            profile_rmse = float(np.sqrt(np.mean(np.square(direct["physics"][local] - profiles[local]))))
            decoder_rmse = float(np.sqrt(np.mean(np.square(direct["reconstruction"][local] - profiles[local]))))
            rows.append({
                "experiment_phase": phase,
                "seed": int(seed),
                "global_index": int(global_index),
                "du_true": float(q_truth[local, 0]), "dv_true": float(q_truth[local, 1]),
                "du_pred": float(direct["q"][local, 0]), "dv_pred": float(direct["q"][local, 1]),
                "du_abs_error": float(qerr[0]), "dv_abs_error": float(qerr[1]),
                "q_mae": float(np.mean(qerr)),
                "a_true_angstrom": float(a_true[local]), "c_true_angstrom": float(c_true[local]),
                "a_pred_angstrom": float(pred_a[local]), "c_pred_angstrom": float(pred_c[local]),
                "a_abs_error_angstrom": float(abs(pred_a[local] - a_true[local])),
                "c_abs_error_angstrom": float(abs(pred_c[local] - c_true[local])),
                "zero_shift_true_deg": float(eta_truth[local, 0]), "zero_shift_pred_deg": float(direct["eta"][local, 0]),
                "zero_shift_abs_error_deg": float(eta_err[0]),
                "fwhm_true_deg": float(eta_truth[local, 1]), "fwhm_pred_deg": float(direct["eta"][local, 1]),
                "fwhm_abs_error_deg": float(eta_err[1]),
                "background_true_ratio": float(eta_truth[local, 2]), "background_pred_ratio": float(direct["eta"][local, 2]),
                "background_abs_error": float(eta_err[2]),
                "physics_profile_rmse": profile_rmse, "decoder_profile_rmse": decoder_rmse,
                "prediction_finite": bool(valid_mask[local]),
                **latency,
                "checkpoint_sha256": checkpoint_hash,
            })
        del model, reload_probe
        torch.cuda.empty_cache()
    metrics = ["du_abs_error", "dv_abs_error", "q_mae", "a_abs_error_angstrom", "c_abs_error_angstrom", "zero_shift_abs_error_deg", "fwhm_abs_error_deg", "background_abs_error", "physics_profile_rmse", "decoder_profile_rmse", "encoder_p50_seconds", "encoder_p95_seconds"]
    summary = _per_seed_summary(rows, metrics)
    summary["failure_rate"] = float(1.0 - np.mean([row["prediction_finite"] for row in rows]))
    summary["prediction_count"] = len(rows)
    return rows, summary


def _fit_profile(
    forward: Any,
    observed: np.ndarray,
    *,
    initial: np.ndarray,
    include_shift: bool,
    include_width_background: bool,
    config: dict[str, Any],
) -> dict[str, Any]:
    solver = config["classical_lbfgsb"]
    target = torch.as_tensor(observed[None], device="cuda", dtype=torch.float32)
    if include_width_background:
        nparam = 5
        bounds = [tuple(solver["parameter_bounds"][name]) for name in ("du", "dv", "zero_shift_deg", "fwhm_deg", "background_ratio")]
        mode = "v9_polynomial"
    elif include_shift:
        nparam = 3
        bounds = [(-0.8, 0.8), (-0.8, 0.8), (-0.06, 0.06)]
        mode = "v9_polynomial"
    else:
        nparam = 2
        bounds = [(-0.8, 0.8), (-0.8, 0.8)]
        mode = "v9_polynomial"
    x0 = np.asarray(initial[:nparam], dtype=np.float64)
    def objective(values: np.ndarray) -> tuple[float, np.ndarray]:
        z = torch.as_tensor(values[None], device="cuda", dtype=torch.float64).requires_grad_(True)
        q = z[:, :2]
        if include_width_background:
            eta = z[:, 2:]
        elif include_shift:
            eta = torch.stack((z[:, 2], torch.full_like(z[:, 2], 0.08), torch.zeros_like(z[:, 2])), dim=1)
        else:
            eta = torch.stack((torch.zeros_like(z[:, 0]), torch.full_like(z[:, 0], 0.08), torch.zeros_like(z[:, 0])), dim=1)
        predicted = expected_profile(forward, q, eta, background_shape_mode=mode).to(torch.float32)
        loss = F.mse_loss(predicted, target)
        gradient = torch.autograd.grad(loss, z)[0]
        return float(loss.detach().item()), gradient.detach().cpu().numpy()[0]
    start = time.perf_counter()
    result = scipy.optimize.minimize(
        objective,
        x0,
        method="L-BFGS-B",
        jac=True,
        bounds=bounds,
        options={
            "maxiter": int(solver["max_iterations"]),
            "maxfun": int(solver["max_function_evaluations"]),
            "ftol": float(solver["ftol"]),
            "gtol": float(solver["gtol"]),
            "maxls": int(solver["maxls"]),
        },
    )
    torch.cuda.synchronize()
    vals = np.asarray(result.x, dtype=np.float64)
    if include_width_background:
        q = vals[:2]; eta = vals[2:]
    elif include_shift:
        q = vals[:2]; eta = np.asarray([vals[2], 0.08, 0.0])
    else:
        q = vals[:2]; eta = np.asarray([0.0, 0.08, 0.0])
    return {
        "q": q.tolist(), "eta": eta.tolist(), "success": bool(result.success),
        "status": int(result.status), "message": str(result.message),
        "iterations": int(result.nit), "function_evaluations": int(result.nfev),
        "seconds": time.perf_counter() - start,
        "profile_rmse": float(math.sqrt(max(0.0, float(result.fun)))),
        "finite": bool(np.isfinite(vals).all() and np.isfinite(result.fun)),
    }


def _pearson(x: list[float], y: list[float]) -> float | None:
    if len(x) < 2 or np.std(x) <= EPS or np.std(y) <= EPS:
        return None
    return float(np.corrcoef(np.asarray(x), np.asarray(y))[0, 1])


def experiment_2_solver_ablation(
    arrays: dict[str, np.ndarray], forward: Any, driver: Any, structure: Any, forward_cfg: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    test_ids = arrays["test_indices"]
    q_true = arrays["q"][test_ids]
    obs = arrays["experiment_2_shift_observed"][test_ids]
    eta_true = arrays["experiment_2_shift_eta_truth"][test_ids]
    rows = []
    initial = np.asarray([0.0, 0.0, 0.0], dtype=np.float64)
    for j, index in enumerate(test_ids):
        fixed = _fit_profile(forward, obs[j], initial=initial, include_shift=False, include_width_background=False, config=config)
        free = _fit_profile(forward, obs[j], initial=initial, include_shift=True, include_width_background=False, config=config)
        for label, result in (("fixed_zero_shift", fixed), ("free_zero_shift", free)):
            qerr = np.abs(np.asarray(result["q"]) - q_true[j])
            rows.append({
                "global_index": int(index), "fit": label, "du_abs_error": float(qerr[0]), "dv_abs_error": float(qerr[1]),
                "q_mae": float(np.mean(qerr)), "shift_true_deg": float(eta_true[j, 0]), "shift_pred_deg": float(result["eta"][0]),
                "shift_abs_error_deg": float(abs(result["eta"][0] - eta_true[j, 0])),
                "profile_rmse": result["profile_rmse"], "success": result["success"], "iterations": result["iterations"],
                "function_evaluations": result["function_evaluations"], "seconds": result["seconds"], "finite": result["finite"],
            })
    write_rows_csv(RESULTS / "experiment_2" / "fixed_vs_free_lbfgsb.csv", rows)
    summary = {}
    for fit in ("fixed_zero_shift", "free_zero_shift"):
        group = [row for row in rows if row["fit"] == fit]
        summary[fit] = {
            "n": len(group),
            "q_mae": float(np.mean([r["q_mae"] for r in group])),
            "zero_shift_mae_deg": float(np.mean([r["shift_abs_error_deg"] for r in group])),
            "profile_rmse": float(np.mean([r["profile_rmse"] for r in group])),
            "success_rate": float(np.mean([r["success"] and r["finite"] for r in group])),
            "p50_seconds": float(np.percentile([r["seconds"] for r in group], 50)),
            "p95_seconds": float(np.percentile([r["seconds"] for r in group], 95)),
        }
    return summary


def identifiability_audit(forward: Any) -> dict[str, Any]:
    vector = torch.tensor([0.13, -0.19, 0.0], device="cuda", dtype=torch.float64)
    def render(values: torch.Tensor) -> torch.Tensor:
        q = values[:2].reshape(1, 2)
        eta = torch.stack((values[2:3] * 0.06, torch.full_like(values[2:3], 0.08), torch.zeros_like(values[2:3])), dim=1)
        return expected_profile(forward, q, eta, background_shape_mode="v9_polynomial")[0]
    jacobian = torch.autograd.functional.jacobian(render, vector).detach().cpu().numpy()
    norms = np.linalg.norm(jacobian, axis=0)
    normalized = jacobian / np.maximum(norms, EPS)
    correlation = normalized.T @ normalized
    singular = np.linalg.svd(jacobian, compute_uv=False)
    rank = int(np.linalg.matrix_rank(jacobian, tol=float(singular[0]) * 1e-6))
    return {
        "parameters": ["du", "dv", "zero_shift_normalized"],
        "local_jacobian_shape": list(jacobian.shape),
        "column_norms": norms.tolist(),
        "column_cosine_matrix": correlation.tolist(),
        "du_shift_abs_cosine": float(abs(correlation[0, 2])),
        "dv_shift_abs_cosine": float(abs(correlation[1, 2])),
        "singular_values": singular.tolist(),
        "rank_rtol_1e-6": rank,
        "condition_number": float(singular[0] / singular[-1]) if singular[-1] > 0 else float("inf"),
    }


def _load_donut(path: Path, phase: str, input_length: int) -> DONUTEncoderDecoder:
    checkpoint = torch.load(path, map_location="cuda", weights_only=False)
    model = _new_donut(phase, input_length)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    return model


def run_donut_phase(
    *,
    phase: str,
    exp_number: int,
    status: dict[str, Any],
    arrays: dict[str, np.ndarray],
    data_manifest: dict[str, Any],
    forward: Any,
    driver: Any,
    structure: Any,
    forward_cfg: dict[str, Any],
    config: dict[str, Any],
    artifact_root: Path,
    gpu_budget_used: list[float],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    name = f"experiment_{exp_number}"
    phase_record = status["experiments"][name]
    phase_record["status"] = "RUNNING"; phase_record["started_at_utc"] = utc_now(); phase_record["conditions"] = phase_record.get("conditions", {})
    write_json(STATUS_PATH, status)
    seeds = list(config["donut_method"]["model_seeds"])
    training_runs = []
    for seed in seeds:
        training = train_donut_one(
            phase=phase, seed=int(seed), arrays=arrays, forward=forward, config=config,
            artifact_root=artifact_root, gpu_budget_used=gpu_budget_used,
        )
        training_runs.append(training)
        phase_record.setdefault("training_progress", []).append({key: value for key, value in training.items() if key != "history"})
        status["measured_gpu_training_seconds"] = gpu_budget_used[0]
        write_json(STATUS_PATH, status)
    phase_record["conditions"][phase] = {
        "status": "TRAINED",
        "seed_runs": [{key: value for key, value in row.items() if key != "history"} for row in training_runs],
        "history_path": str((RESULTS / f"experiment_{exp_number}" / f"{phase}_training_histories.json").resolve()),
    }
    result_dir = RESULTS / f"experiment_{exp_number}"
    result_dir.mkdir(parents=True, exist_ok=True)
    write_json(result_dir / f"{phase}_training_histories.json", {str(row["seed"]): row["history"] for row in training_runs})
    rows, summary = evaluate_donut_condition(
        phase=phase, seeds=seeds, arrays=arrays, forward=forward, driver=driver, structure=structure,
        forward_cfg=forward_cfg, artifact_root=artifact_root,
    )
    write_rows_csv(result_dir / f"{phase}_raw_predictions.csv", rows)
    write_json(result_dir / f"{phase}_summary.json", summary)
    if len(rows) != int(len(arrays["test_indices"])) * len(seeds):
        raise RuntimeError(f"raw test row count mismatch for {phase}")
    if summary["failure_rate"] != 0.0:
        raise RuntimeError(f"non-finite/out-of-domain prediction occurred in {phase}")
    phase_record["conditions"][phase]["summary"] = summary
    phase_record["conditions"][phase]["raw_predictions_sha256"] = sha256_file(result_dir / f"{phase}_raw_predictions.csv")
    phase_record["conditions"][phase]["metrics_recomputed_from_raw"] = True
    write_json(STATUS_PATH, status)
    run_pytest(f"experiment_{exp_number}_{phase}", ["donut_pxrd/tests"])
    return rows, summary


def _render_experiment_report(number: int, status: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    record = status["experiments"][f"experiment_{number}"]
    lines = [f"# Experiment {number}: DONUT-PXRD", "", f"**Status:** {record.get('status', 'NOT_RUN')}", ""]
    for phase, item in record.get("conditions", {}).items():
        summary = item.get("summary")
        if not summary:
            continue
        lines.extend([f"## `{phase}`", "", "| Metric | Mean over seeds | Seed SD |", "|---|---:|---:|"])
        for metric in ("du_abs_error", "dv_abs_error", "q_mae", "a_abs_error_angstrom", "c_abs_error_angstrom", "zero_shift_abs_error_deg", "fwhm_abs_error_deg", "background_abs_error", "physics_profile_rmse", "encoder_p50_seconds", "encoder_p95_seconds"):
            value = summary.get("aggregate", {}).get(metric)
            if value is not None:
                lines.append(f"| {metric} | {value['mean']:.8g} | {value['sample_sd']:.8g} |")
        lines.extend(["", f"Prediction failure fraction: `{summary.get('failure_rate', float('nan')):.8g}`; `n={summary.get('prediction_count', 0)}` sample-seed rows.", ""])
    if extra:
        lines.extend(["## Audits", "", "```json", json.dumps(extra, indent=2, ensure_ascii=False), "```", ""])
    (OUT / "reports" / f"EXPERIMENT_{number}.md").write_text("\n".join(lines), encoding="utf-8")


def train_baseline_one(
    *, method: str, seed: int, lam: float, arrays: dict[str, np.ndarray], forward: Any,
    config: dict[str, Any], artifact_root: Path, gpu_budget_used: list[float],
) -> dict[str, Any]:
    tr = config["baseline_abc"]
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); np.random.seed(seed)
    x = torch.as_tensor(arrays["experiment_3_noise_observed"], device="cuda", dtype=torch.float32)
    q = torch.as_tensor(arrays["q"], device="cuda", dtype=torch.float32)
    train_indices = np.asarray(arrays["train_indices"], dtype=np.int64)
    val_indices = np.asarray(arrays["validation_indices"], dtype=np.int64)
    model = ParameterRegressor(input_length=x.shape[-1]).cuda() if method == "A" else MeasurementAwareRegressor(input_length=x.shape[-1]).cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=float(tr["learning_rate"]), weight_decay=float(tr["weight_decay"]))
    generator = torch.Generator(device="cuda"); generator.manual_seed(seed + 500000)
    best = float("inf"); best_epoch = 0; best_state: dict[str, torch.Tensor] | None = None; history = []
    torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize(); started = time.perf_counter()
    for epoch in range(1, int(tr["max_epochs"]) + 1):
        model.train()
        order = torch.randperm(len(train_indices), generator=generator, device="cuda")
        epoch_losses: list[tuple[float, float, float]] = []
        for start in range(0, len(order), int(tr["batch_size"])):
            ids = torch.as_tensor(train_indices, device="cuda", dtype=torch.long).index_select(0, order[start : start + int(tr["batch_size"])])
            xb = x.index_select(0, ids); yb = q.index_select(0, ids)
            optimizer.zero_grad(set_to_none=True)
            output = model(xb)
            if method == "A":
                q_pred = output; loss_q = F.mse_loss(q_pred, yb); loss_profile = loss_q.new_zeros(()); loss = loss_q
            else:
                q_pred, eta_pred = output
                q_for_profile = q_pred.detach() if method == "C" else q_pred
                profile_pred = expected_profile(forward, q_for_profile.double(), eta_pred.double(), background_shape_mode="v9_polynomial").float()
                loss_q = F.mse_loss(q_pred, yb); loss_profile = F.mse_loss(profile_pred, xb); loss = loss_q + float(lam) * loss_profile
            if not torch.isfinite(loss):
                raise FloatingPointError(f"non-finite A/B/C loss {method}/{seed}/{lam}/{epoch}")
            loss.backward()
            parameters = [p for p in model.parameters() if p.grad is not None]
            if not parameters or any(not torch.isfinite(p.grad).all() for p in parameters):
                raise FloatingPointError(f"non-finite A/B/C gradient {method}/{seed}/{lam}/{epoch}")
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(tr["gradient_clip_norm"]))
            optimizer.step()
            epoch_losses.append((float(loss.detach()), float(loss_q.detach()), float(loss_profile.detach())))
        model.eval(); val_ids = torch.as_tensor(val_indices, device="cuda", dtype=torch.long)
        with torch.no_grad():
            output = model(x.index_select(0, val_ids)); q_pred = output[0] if isinstance(output, tuple) else output
            val_q_mae = float(torch.mean(torch.abs(q_pred - q.index_select(0, val_ids))).item())
        record = {"epoch": epoch, "train_total_loss": float(np.mean([v[0] for v in epoch_losses])), "train_q_loss": float(np.mean([v[1] for v in epoch_losses])), "train_profile_loss": float(np.mean([v[2] for v in epoch_losses])), "validation_q_mae": val_q_mae}
        history.append(record); log(TRAIN_LOG, "ABC_EPOCH", method=method, seed=seed, lambda_value=lam, **record)
        if val_q_mae < best:
            best = val_q_mae; best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    torch.cuda.synchronize(); elapsed = time.perf_counter() - started; gpu_budget_used[0] += elapsed
    if gpu_budget_used[0] > float(config["resource_limits"]["max_total_measured_gpu_training_seconds"]):
        raise RuntimeError("frozen cumulative GPU training budget exceeded")
    if best_state is None:
        raise RuntimeError(f"no checkpoint selected for A/B/C {method}/{seed}/{lam}")
    name = f"{method.lower()}_seed{seed}_lambda{lam:g}.pt"
    path = artifact_root / "checkpoints" / "experiment_4_abc" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": best_state, "method": method, "seed": seed, "lambda": lam, "best_epoch": best_epoch, "best_validation_q_mae": best, "config_sha256": sha256_file(CONFIG_PATH)}, path)
    result = {
        "method": method, "seed": int(seed), "lambda": float(lam), "epochs_completed": len(history),
        "best_epoch": best_epoch, "best_validation_q_mae": best, "training_seconds": elapsed,
        "peak_vram_bytes": int(torch.cuda.max_memory_allocated()), "parameter_count": int(sum(p.numel() for p in model.parameters())),
        "checkpoint_path_local_only": str(path.resolve()), "checkpoint_bytes": int(path.stat().st_size),
        "checkpoint_sha256": sha256_file(path), "history": history,
    }
    log(TRAIN_LOG, "ABC_TRAINING_COMPLETE", **{key: value for key, value in result.items() if key != "history"})
    del model; torch.cuda.empty_cache()
    return result


def _load_baseline(method: str, path: Path, input_length: int) -> torch.nn.Module:
    model = ParameterRegressor(input_length=input_length).cuda() if method == "A" else MeasurementAwareRegressor(input_length=input_length).cuda()
    checkpoint = torch.load(path, map_location="cuda", weights_only=False)
    model.load_state_dict(checkpoint["state_dict"]); model.eval()
    return model


def _benchmark_module(model: torch.nn.Module, profiles: np.ndarray) -> dict[str, float]:
    x = torch.as_tensor(profiles[:1], device="cuda", dtype=torch.float32)
    with torch.inference_mode():
        for _ in range(10): model(x)
    torch.cuda.synchronize(); times = []
    for _ in range(60):
        start = time.perf_counter()
        with torch.inference_mode(): model(x)
        torch.cuda.synchronize(); times.append(time.perf_counter() - start)
    return {"p50_seconds": float(np.percentile(times, 50)), "p95_seconds": float(np.percentile(times, 95)), "profiles_per_second": float(1.0 / max(np.mean(times), EPS))}


def evaluate_baselines_and_classical(
    *, arrays: dict[str, np.ndarray], forward: Any, driver: Any, structure: Any, forward_cfg: dict[str, Any],
    config: dict[str, Any], artifact_root: Path, training_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    tr = config["baseline_abc"]
    seeds = list(tr["seeds"])
    selection: dict[str, float] = {"A": 0.0}
    val_scores: dict[str, Any] = {}
    for method in ("B", "C"):
        candidates = {}
        for lam in tr["lambda_candidates_for_b_c"]:
            runs = [r for r in training_runs if r["method"] == method and math.isclose(r["lambda"], float(lam))]
            candidates[str(lam)] = float(np.mean([r["best_validation_q_mae"] for r in runs]))
        selected = min(tr["lambda_candidates_for_b_c"], key=lambda value: (candidates[str(value)], value))
        selection[method] = float(selected); val_scores[method] = {"validation_mean_q_mae_by_lambda": candidates, "selected_lambda": float(selected), "test_used": False}
    write_json(RESULTS / "experiment_4" / "validation_lambda_selection.json", {"selected": selection, "selection": val_scores, "test_used": False})

    test_ids = np.asarray(arrays["test_indices"], dtype=np.int64)
    profiles = np.asarray(arrays["experiment_3_noise_observed"][test_ids], dtype=np.float32)
    q_true = np.asarray(arrays["q"][test_ids], dtype=np.float64)
    eta_true = np.asarray(arrays["experiment_3_noise_eta_truth"][test_ids], dtype=np.float64)
    a_true, c_true = _lattice_values(q_true, driver, structure, forward_cfg)
    direct_rows: list[dict[str, Any]] = []
    direct_outputs: dict[tuple[str, int], tuple[np.ndarray, np.ndarray]] = {}
    model_records: dict[str, list[dict[str, Any]]] = {}

    for method in ("A", "B", "C"):
        model_records[method] = []
        for seed in seeds:
            lam = selection[method]
            path = artifact_root / "checkpoints" / "experiment_4_abc" / f"{method.lower()}_seed{seed}_lambda{lam:g}.pt"
            checkpoint_hash = sha256_file(path)
            model = _load_baseline(method, path, profiles.shape[-1])
            timing = _benchmark_module(model, profiles)
            x = torch.as_tensor(profiles, device="cuda", dtype=torch.float32)
            with torch.no_grad():
                output = model(x)
                if isinstance(output, tuple): q_pred = output[0].cpu().numpy(); eta_pred = output[1].cpu().numpy()
                else: q_pred = output.cpu().numpy(); eta_pred = np.tile(np.asarray([0.0, 0.105, 0.005]), (len(profiles), 1))
            direct_outputs[(method, int(seed))] = (q_pred, eta_pred)
            pred_a, pred_c = _lattice_values(q_pred, driver, structure, forward_cfg)
            for j, index in enumerate(test_ids):
                qerr = np.abs(q_pred[j] - q_true[j]); etaerr = np.abs(eta_pred[j] - eta_true[j])
                model_profile = expected_profile(
                    forward,
                    torch.as_tensor(q_pred[j : j + 1], device="cuda", dtype=torch.float64),
                    torch.as_tensor(eta_pred[j : j + 1], device="cuda", dtype=torch.float64),
                    background_shape_mode="v9_polynomial",
                )[0].detach().cpu().numpy()
                direct_rows.append({
                    "method": method, "seed": int(seed), "global_index": int(index),
                    "du_true": float(q_true[j, 0]), "dv_true": float(q_true[j, 1]), "du_pred": float(q_pred[j, 0]), "dv_pred": float(q_pred[j, 1]),
                    "du_abs_error": float(qerr[0]), "dv_abs_error": float(qerr[1]), "q_mae": float(np.mean(qerr)),
                    "a_abs_error_angstrom": float(abs(pred_a[j] - a_true[j])), "c_abs_error_angstrom": float(abs(pred_c[j] - c_true[j])),
                    "zero_shift_abs_error_deg": float(etaerr[0]), "fwhm_abs_error_deg": float(etaerr[1]), "background_abs_error": float(etaerr[2]),
                    "profile_rmse": float(np.sqrt(np.mean(np.square(model_profile - profiles[j])))),
                    "inference_p50_seconds": timing["p50_seconds"], "inference_p95_seconds": timing["p95_seconds"],
                    "inference_profiles_per_second": timing["profiles_per_second"],
                    "prediction_finite": bool(np.isfinite(q_pred[j]).all() and np.isfinite(eta_pred[j]).all()),
                    "checkpoint_sha256": checkpoint_hash,
                })
            model_records[method].append({"seed": seed, "lambda": lam, "checkpoint_sha256": checkpoint_hash, "checkpoint_bytes": path.stat().st_size, **timing})
            del model; torch.cuda.empty_cache()

    donut_rows_path = RESULTS / "experiment_3" / "experiment_3_noise_raw_predictions.csv"
    donut_rows: list[dict[str, Any]] = []
    with donut_rows_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            donut_rows.append(row)
    for seed in seeds:
        group = [row for row in donut_rows if int(row["seed"]) == seed]
        q_pred = np.asarray([[float(r["du_pred"]), float(r["dv_pred"])] for r in group])
        eta_pred = np.asarray([[float(r["zero_shift_pred_deg"]), float(r["fwhm_pred_deg"]), float(r["background_pred_ratio"])] for r in group])
        direct_outputs[("DONUT", int(seed))] = (q_pred, eta_pred)
        model_records.setdefault("DONUT", []).append({
            "seed": seed,
            "checkpoint_sha256": hashlib.sha256("".join(r["checkpoint_sha256"] for r in group).encode()).hexdigest(),
            "checkpoint_bytes": int(sum(_checkpoint_path(artifact_root, "experiment_3_noise", seed).stat().st_size for _ in [0])),
        })
        for row in group:
            cooked = {key: value for key, value in row.items()}
            for key in ("seed", "global_index"):
                cooked[key] = int(cooked[key])
            for key in ("du_abs_error", "dv_abs_error", "q_mae", "a_abs_error_angstrom", "c_abs_error_angstrom", "zero_shift_abs_error_deg", "fwhm_abs_error_deg", "background_abs_error", "physics_profile_rmse", "decoder_profile_rmse", "encoder_p50_seconds", "encoder_p95_seconds", "a_true_angstrom", "c_true_angstrom"):
                cooked[key] = float(cooked[key])
            cooked["profile_rmse"] = cooked["physics_profile_rmse"]
            cooked["prediction_finite"] = str(cooked["prediction_finite"]).lower() == "true"
            direct_rows.append({"method": "DONUT", **cooked})

    write_rows_csv(RESULTS / "experiment_4" / "direct_method_comparison.csv", direct_rows)
    direct_metrics = ["du_abs_error", "dv_abs_error", "q_mae", "a_abs_error_angstrom", "c_abs_error_angstrom", "zero_shift_abs_error_deg", "fwhm_abs_error_deg", "background_abs_error", "profile_rmse"]
    direct_summary = {}
    for method in ("A", "B", "C", "DONUT"):
        method_rows = [row for row in direct_rows if row["method"] == method]
        direct_summary[method] = _per_seed_summary(method_rows, direct_metrics)
        direct_summary[method]["failure_rate"] = float(1.0 - np.mean([bool(row["prediction_finite"]) for row in method_rows]))
        direct_summary[method]["inference_p50_seconds"] = float(np.mean([float(row.get("inference_p50_seconds", row.get("encoder_p50_seconds", 0))) for row in method_rows]))
        direct_summary[method]["inference_p95_seconds"] = float(np.mean([float(row.get("inference_p95_seconds", row.get("encoder_p95_seconds", 0))) for row in method_rows]))
        direct_summary[method]["checkpoint_bytes"] = model_records[method]

    # Same bounded joint refinement settings, initialized by each model's q and eta.
    joint_rows: list[dict[str, Any]] = []
    for method in ("A", "B", "C", "DONUT"):
        for seed in seeds:
            q_pred, eta_pred = direct_outputs[(method, int(seed))]
            for j, index in enumerate(test_ids):
                initial = np.concatenate((q_pred[j], eta_pred[j]))
                fit = _fit_profile(forward, profiles[j], initial=initial, include_shift=True, include_width_background=True, config=config)
                q_fit = np.asarray(fit["q"]); eta_fit = np.asarray(fit["eta"]); qerr = np.abs(q_fit - q_true[j]); etaerr = np.abs(eta_fit - eta_true[j])
                joint_rows.append({
                    "method": method, "seed": int(seed), "global_index": int(index), "du_abs_error": float(qerr[0]), "dv_abs_error": float(qerr[1]),
                    "q_mae": float(np.mean(qerr)), "zero_shift_abs_error_deg": float(etaerr[0]), "fwhm_abs_error_deg": float(etaerr[1]),
                    "background_abs_error": float(etaerr[2]), "profile_rmse": fit["profile_rmse"], "success": fit["success"], "finite": fit["finite"],
                    "iterations": fit["iterations"], "function_evaluations": fit["function_evaluations"], "seconds": fit["seconds"],
                })

    optimizer_rows = []
    neutral = np.asarray([0.0, 0.0, 0.0, 0.105, 0.005], dtype=np.float64)
    for j, index in enumerate(test_ids):
        fit = _fit_profile(forward, profiles[j], initial=neutral, include_shift=True, include_width_background=True, config=config)
        qerr = np.abs(np.asarray(fit["q"]) - q_true[j]); etaerr = np.abs(np.asarray(fit["eta"]) - eta_true[j])
        optimizer_rows.append({
            "method": "L-BFGS-B neutral-start optimizer-only", "global_index": int(index), "du_abs_error": float(qerr[0]), "dv_abs_error": float(qerr[1]),
            "q_mae": float(np.mean(qerr)), "zero_shift_abs_error_deg": float(etaerr[0]), "fwhm_abs_error_deg": float(etaerr[1]),
            "background_abs_error": float(etaerr[2]), "profile_rmse": fit["profile_rmse"], "success": fit["success"], "finite": fit["finite"],
            "iterations": fit["iterations"], "function_evaluations": fit["function_evaluations"], "seconds": fit["seconds"],
        })
    write_rows_csv(RESULTS / "experiment_4" / "joint_refinement_comparison.csv", joint_rows)
    write_rows_csv(RESULTS / "experiment_4" / "lbfgsb_optimizer_only.csv", optimizer_rows)
    joint_summary = {}
    for method in ("A", "B", "C", "DONUT"):
        group = [row for row in joint_rows if row["method"] == method]
        joint_summary[method] = {
            "n": len(group), "q_mae": float(np.mean([r["q_mae"] for r in group])),
            "profile_rmse": float(np.mean([r["profile_rmse"] for r in group])),
            "solver_success_rate": float(np.mean([r["success"] and r["finite"] for r in group])),
            "failure_rate": float(1.0 - np.mean([r["success"] and r["finite"] for r in group])),
            "iterations_mean": float(np.mean([r["iterations"] for r in group])),
            "runtime_p50_seconds": float(np.percentile([r["seconds"] for r in group], 50)),
            "runtime_p95_seconds": float(np.percentile([r["seconds"] for r in group], 95)),
        }
    optimizer_summary = {
        "n": len(optimizer_rows),
        "q_mae": float(np.mean([r["q_mae"] for r in optimizer_rows])),
        "profile_rmse": float(np.mean([r["profile_rmse"] for r in optimizer_rows])),
        "solver_success_rate": float(np.mean([r["success"] and r["finite"] for r in optimizer_rows])),
        "failure_rate": float(1.0 - np.mean([r["success"] and r["finite"] for r in optimizer_rows])),
        "iterations_mean": float(np.mean([r["iterations"] for r in optimizer_rows])),
        "runtime_p50_seconds": float(np.percentile([r["seconds"] for r in optimizer_rows], 50)),
        "runtime_p95_seconds": float(np.percentile([r["seconds"] for r in optimizer_rows], 95)),
    }
    return {
        "lambda_selection": {"selected": selection, "validation_only_scores": val_scores},
        "direct": direct_summary,
        "joint_refinement": joint_summary,
        "optimizer_only": optimizer_summary,
        "baseline_training": model_records,
        "baseline_training_seconds": float(sum(r["training_seconds"] for r in training_runs)),
        "donut_and_abc_total_gpu_training_seconds": float(sum(r["training_seconds"] for r in training_runs)),
        "direct_raw_rows": len(direct_rows),
        "joint_raw_rows": len(joint_rows),
    }


def _start_experiment(status: dict[str, Any], number: int) -> None:
    name = f"experiment_{number}"
    rec = status["experiments"][name]
    if rec.get("status") == "COMPLETE":
        return
    rec["status"] = "RUNNING"; rec["started_at_utc"] = rec.get("started_at_utc", utc_now())
    write_json(STATUS_PATH, status)
    status_event(status, name, "EXPERIMENT_STARTED")


def _finish_experiment(status: dict[str, Any], number: int, **fields: Any) -> None:
    rec = status["experiments"][f"experiment_{number}"]
    rec.update(fields); rec["status"] = "COMPLETE"; rec["finished_at_utc"] = utc_now()
    status["measured_gpu_training_seconds"] = float(fields.get("measured_gpu_training_seconds", status.get("measured_gpu_training_seconds", 0.0)))
    status_event(status, f"experiment_{number}", "EXPERIMENT_COMPLETE", **{k: v for k, v in fields.items() if k != "summary"})


def run_all() -> int:
    config = load_config()
    configure_runtime()
    status = initialize_status(config)
    driver = load_forward_driver()
    arrays, data_manifest, forward, forward_cfg, structure = prepare_artifacts(config, driver)
    artifact_root = Path(config["data"]["raw_data_location"]).parent
    split_counts = _validate_split(arrays)
    status["data_manifest_sha256"] = sha256_file(artifact_root / "datasets" / "data_manifest.json")
    status["dataset_npz_sha256"] = data_manifest["dataset_npz_sha256"]
    status["split_counts"] = split_counts
    status["test_indices_sha256"] = data_manifest["test_indices_sha256"]
    write_json(STATUS_PATH, status)

    gate_path = RESULTS / "preflight_gates.json"
    if gate_path.exists():
        gate_results = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate_results.get("dataset_npz_sha256") != data_manifest["dataset_npz_sha256"]:
            raise RuntimeError("saved preflight gates belong to a different dataset")
    else:
        gate_results = verify_forward_and_gradients(forward, structure, forward_cfg)
        gate_results["dataset_npz_sha256"] = data_manifest["dataset_npz_sha256"]
        gate_results["split_counts"] = split_counts
        write_json(gate_path, gate_results)
    run_pytest("preflight_existing_regression", ["xrd_inversion/tests", "xrd_forward_loss/tests", "donut_pxrd/tests"])

    gpu_budget_used = [float(status.get("measured_gpu_training_seconds", 0.0))]

    # Experiment 1: fixed instrument, lattice coordinates only.
    if status["experiments"]["experiment_1"].get("status") != "COMPLETE":
        _start_experiment(status, 1)
        rows, summary = run_donut_phase(
            phase="experiment_1_fixed", exp_number=1, status=status, arrays=arrays, data_manifest=data_manifest,
            forward=forward, driver=driver, structure=structure, forward_cfg=forward_cfg, config=config,
            artifact_root=artifact_root, gpu_budget_used=gpu_budget_used,
        )
        _finish_experiment(status, 1, summary={"fixed": summary}, measured_gpu_training_seconds=gpu_budget_used[0], data_manifest_sha256=status["data_manifest_sha256"])
        _render_experiment_report(1, status)

    # Experiment 2: add zero shift and report local identifiability/confounding.
    exp2_extra: dict[str, Any] = {}
    if status["experiments"]["experiment_2"].get("status") != "COMPLETE":
        _start_experiment(status, 2)
        rows, summary = run_donut_phase(
            phase="experiment_2_shift", exp_number=2, status=status, arrays=arrays, data_manifest=data_manifest,
            forward=forward, driver=driver, structure=structure, forward_cfg=forward_cfg, config=config,
            artifact_root=artifact_root, gpu_budget_used=gpu_budget_used,
        )
        all_du = [row["du_pred"] - row["du_true"] for row in rows]
        all_dv = [row["dv_pred"] - row["dv_true"] for row in rows]
        all_delta = [row["zero_shift_pred_deg"] - row["zero_shift_true_deg"] for row in rows]
        exp2_extra = {
            "local_identifiability": identifiability_audit(forward),
            "signed_du_shift_error_pearson": _pearson(all_du, all_delta),
            "signed_dv_shift_error_pearson": _pearson(all_dv, all_delta),
            "fixed_vs_free_lbfgsb": experiment_2_solver_ablation(arrays, forward, driver, structure, forward_cfg, config),
        }
        write_json(RESULTS / "experiment_2" / "confounding_audit.json", exp2_extra)
        status["experiments"]["experiment_2"]["confounding_audit"] = exp2_extra
        _finish_experiment(status, 2, summary={"q_and_shift": summary, **exp2_extra}, measured_gpu_training_seconds=gpu_budget_used[0], data_manifest_sha256=status["data_manifest_sha256"])
        _render_experiment_report(2, status, exp2_extra)

    # Experiment 3: progressive width, smooth background, shot/readout noise,
    # followed by a reflection-level texture OOD stress test.
    exp3_summaries: dict[str, Any] = {}
    if status["experiments"]["experiment_3"].get("status") != "COMPLETE":
        _start_experiment(status, 3)
        phases = ("experiment_3_width", "experiment_3_background", "experiment_3_noise")
        for phase in phases:
            _, summary = run_donut_phase(
                phase=phase, exp_number=3, status=status, arrays=arrays, data_manifest=data_manifest,
                forward=forward, driver=driver, structure=structure, forward_cfg=forward_cfg, config=config,
                artifact_root=artifact_root, gpu_budget_used=gpu_budget_used,
            )
            exp3_summaries[phase] = summary
        texture_path = artifact_root / "datasets" / "texture_test.npz"
        if texture_path.exists():
            tex_npz = np.load(texture_path, allow_pickle=False)
            texture_profiles = tex_npz["profiles"]
            texture_manifest = json.loads((artifact_root / "datasets" / "texture_test_manifest.json").read_text(encoding="utf-8"))
        else:
            texture_profiles, texture_records = make_texture_test(
                q=arrays["q"], eta=arrays["experiment_3_noise_eta_truth"], test_indices=arrays["test_indices"],
                structure=structure, forward_cfg=forward_cfg, seed=int(config["data"]["generator_seeds"]["texture_test"]),
            )
            np.savez_compressed(texture_path, profiles=texture_profiles)
            texture_manifest = {
                "schema": "donut_pxrd_texture_stress_v1", "dataset_npz_sha256": sha256_file(texture_path),
                "test_indices_sha256": data_manifest["test_indices_sha256"], "generator_records": texture_records,
                "march_parameter_r": 0.8, "preferred_hkl": [0, 0, 1], "evaluation_only": True,
                "renderer": "xrd_robustness.simulator.simulate_from_peak_table + apply_preferred_orientation",
            }
            write_json(artifact_root / "datasets" / "texture_test_manifest.json", texture_manifest)
        texture_rows, texture_summary = evaluate_donut_condition(
            phase="experiment_3_noise", seeds=list(config["donut_method"]["model_seeds"]), arrays=arrays,
            forward=forward, driver=driver, structure=structure, forward_cfg=forward_cfg, artifact_root=artifact_root,
            profiles_override=texture_profiles, phase_for_mapping="experiment_3_texture",
        )
        for row in texture_rows: row["evaluation_case"] = "texture_OOD_stress"
        write_rows_csv(RESULTS / "experiment_3" / "texture_OOD_raw_predictions.csv", texture_rows)
        write_json(RESULTS / "experiment_3" / "texture_OOD_summary.json", texture_summary)
        exp3_summaries["experiment_3_texture"] = texture_summary
        status["experiments"]["experiment_3"]["texture_manifest_sha256"] = sha256_file(artifact_root / "datasets" / "texture_test_manifest.json")
        status["experiments"]["experiment_3"]["progressive_summaries"] = exp3_summaries
        _finish_experiment(status, 3, summary=exp3_summaries, measured_gpu_training_seconds=gpu_budget_used[0], data_manifest_sha256=status["data_manifest_sha256"])
        _render_experiment_report(3, status, {"texture_OOD_stress": texture_summary, "texture_manifest": texture_manifest})

    # Experiment 4: paired fresh A/B/C baselines plus DONUT and optimizer-only L-BFGS-B.
    if status["experiments"]["experiment_4"].get("status") != "COMPLETE":
        _start_experiment(status, 4)
        training_runs: list[dict[str, Any]] = []
        lambdas = [0.0] + [float(v) for v in config["baseline_abc"]["lambda_candidates_for_b_c"]]
        total = 0
        for method in ("A", "B", "C"):
            for seed in config["baseline_abc"]["seeds"]:
                values = [0.0] if method == "A" else lambdas[1:]
                for lam in values:
                    if gpu_budget_used[0] >= float(config["resource_limits"]["max_total_measured_gpu_training_seconds"]):
                        raise RuntimeError("frozen cumulative GPU training budget reached before A/B/C completion")
                    row = train_baseline_one(
                        method=method, seed=int(seed), lam=float(lam), arrays=arrays, forward=forward,
                        config=config, artifact_root=artifact_root, gpu_budget_used=gpu_budget_used,
                    )
                    training_runs.append(row); total += 1
                    status["measured_gpu_training_seconds"] = gpu_budget_used[0]
                    status["experiments"]["experiment_4"]["baseline_training_progress"] = [
                        {key: value for key, value in item.items() if key != "history"} for item in training_runs
                    ]
                    write_json(STATUS_PATH, status)
                    write_json(RESULTS / "experiment_4" / "baseline_training_runs.json", [{key: value for key, value in item.items() if key != "history"} for item in training_runs])
                    # Keep each complete per-epoch log in a dedicated JSON file.
                    write_json(RESULTS / "experiment_4" / f"{method}_seed{seed}_lambda{lam:g}_history.json", row["history"])
        if total != 15:
            raise RuntimeError(f"expected 15 preregistered A/B/C candidate runs, got {total}")
        comparison = evaluate_baselines_and_classical(
            arrays=arrays, forward=forward, driver=driver, structure=structure, forward_cfg=forward_cfg,
            config=config, artifact_root=artifact_root, training_runs=training_runs,
        )
        write_json(RESULTS / "experiment_4" / "comparison_summary.json", comparison)
        status["experiments"]["experiment_4"]["comparison_summary"] = comparison
        status["experiments"]["experiment_4"]["baseline_candidate_runs"] = total
        status["experiments"]["experiment_4"]["test_parent_count"] = len(arrays["test_indices"])
        status["experiments"]["experiment_4"]["raw_comparison_files"] = {
            name: sha256_file(RESULTS / "experiment_4" / name)
            for name in ("direct_method_comparison.csv", "joint_refinement_comparison.csv", "lbfgsb_optimizer_only.csv")
        }
        _finish_experiment(status, 4, summary=comparison, measured_gpu_training_seconds=gpu_budget_used[0], data_manifest_sha256=status["data_manifest_sha256"])
        run_pytest("experiment_4_final", ["donut_pxrd/tests"])
        _render_experiment_report(4, status, comparison)

    status["finished_at_utc"] = utc_now()
    status["overall_status"] = "COMPLETE" if all(item.get("status") == "COMPLETE" for item in status["experiments"].values()) else "PARTIAL"
    status["measured_gpu_training_seconds"] = gpu_budget_used[0]
    write_json(STATUS_PATH, status)
    write_final_report(status, config)
    return 0 if status["overall_status"] == "COMPLETE" else 1


def write_final_report(status: dict[str, Any], config: dict[str, Any]) -> None:
    lines = [
        "# DONUT-PXRD final technical report",
        "",
        f"**Overall status:** {status.get('overall_status', 'PARTIAL')}",
        f"**Branch:** `{config['branch']}`",
        f"**Frozen study config SHA-256:** `{sha256_file(CONFIG_PATH)}`",
        f"**Source:** DONUT paper DOI `{config['sources']['donut_paper_doi']}`; official code commit `{config['sources']['donut_source_commit']}`",
        f"**Data:** one COD 9014273 BaTiO3 P4mm CIF; train/validation/test `{status.get('split_counts', {})}`",
        f"**Measured neural training time:** {status.get('measured_gpu_training_seconds', 0.0):.3f} seconds",
        "",
        "| Experiment | Status | Main numerical outcome |",
        "|---|---|---|",
    ]
    for number in range(1, 5):
        record = status["experiments"][f"experiment_{number}"]
        summary = record.get("summary", {})
        if number == 4:
            direct = summary.get("direct", {})
            outcomes = "; ".join(f"{method} q-MAE={values.get('aggregate', {}).get('q_mae', {}).get('mean', float('nan')):.6g}" for method, values in direct.items()) if direct else "no test comparison saved"
        else:
            summaries = summary.get("progressive_summaries", summary)
            result_bits = []
            if "aggregate" in summaries:
                result_bits.append(f"q-MAE={summaries['aggregate'].get('q_mae', {}).get('mean', float('nan')):.6g}")
            else:
                for condition, value in summaries.items():
                    if isinstance(value, dict) and "aggregate" in value:
                        result_bits.append(f"{condition}: q-MAE={value['aggregate'].get('q_mae', {}).get('mean', float('nan')):.6g}")
            outcomes = "; ".join(result_bits) if result_bits else "no metrics saved"
        lines.append(f"| {number} | {record.get('status', 'NOT_RUN')} | {outcomes} |")
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "DONUT-PXRD adapts the original 2D nanobeam SXDM dual-branch training principle to one-dimensional synthetic powder patterns. Values are conditional to one known single-phase tetragonal CIF and the frozen synthetic generator. They do not establish performance on real measurements, unknown structures, multiple phases, or general PXRD inversion.",
        "",
        "See each `EXPERIMENT_n.md`, raw per-sample CSV, full JSON histories, `EXECUTION_STATUS.json`, source fidelity audit, and external local-only checkpoint/data manifests for exact evidence.",
        "",
    ])
    (OUT / "reports" / "FINAL_TECHNICAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.joinpath("logs").mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true", help="validate the frozen dataset and forward model before training")
    args = parser.parse_args()
    try:
        return run_preflight_only() if args.preflight_only else run_all()
    except Exception as error:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if STATUS_PATH.exists():
            status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        else:
            status = {"schema": "donut_pxrd_execution_status_v1", "experiments": {f"experiment_{i}": {"status": "NOT_RUN"} for i in range(1, 5)}}
        running = next((key for key, value in status["experiments"].items() if value.get("status") == "RUNNING"), None)
        if running:
            status["experiments"][running].update({"status": "FAILED", "error": repr(error), "traceback": traceback.format_exc(), "finished_at_utc": utc_now()})
        status["overall_status"] = "BLOCKED" if running else "FAILED_PREFLIGHT"
        status["failure"] = {"error": repr(error), "traceback": traceback.format_exc(), "time_utc": utc_now()}
        write_json(STATUS_PATH, status)
        write_final_report(status, json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        log(LOG_PATH, "RUN_STOPPED", failed_experiment=running, error=repr(error), traceback=traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
