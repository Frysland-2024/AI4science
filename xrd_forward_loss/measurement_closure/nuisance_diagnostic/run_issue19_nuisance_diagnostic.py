"""Equal-compute post-hoc nuisance diagnostic for the frozen Issue #19 P3 pilot.

This script only reads the original P3 data and inference-only checkpoints. It
does not train, tune, modify model weights, or use nuisance/parameter truth in
prediction or profile fitting. The test set was already evaluated in P3, so all
new scores are explicitly exploratory post-hoc diagnostics.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import scipy.optimize
import torch
import torch.nn.functional as F
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
    str(ROOT / "xrd_forward_loss" / "scripts"),
]

from pxrd_forward_loss.measurement_closure import expected_profile  # noqa: E402
from pxrd_forward_loss.model import MeasurementAwareRegressor, ParameterRegressor  # noqa: E402
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward  # noqa: E402
import run_issue19_p3 as p3  # noqa: E402


CONFIG_PATH = ROOT / "xrd_forward_loss/measurement_closure/configs/issue19_batio3_v2.json"
FORMAL_DIR = ROOT / "xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/formal"
CHECKPOINT_MANIFEST_PATH = (
    ROOT / "xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/checkpoint_space_optimization.json"
)
CHECKPOINT_ROOT = Path(
    r"C:\Users\Lenovo\.codex\worktrees\issue19-forward-measurement\AI4science"
    r"\xrd_forward_loss\measurement_closure\results\p3_issue19_20261018"
)
RESULT_DIR = ROOT / "xrd_forward_loss/measurement_closure/nuisance_diagnostic/results/20261018"
SEEDS = (20261045, 20261046, 20261047)
CONDITIONS = ("simple", "v9")
METHODS = ("A", "B")
BACKGROUND_MODES = {"simple": "simple_linear_counts", "v9": "v9_polynomial"}
ETA_PARAMETER_NAMES = ("delta_2theta_deg", "fwhm_deg", "background_peak_ratio")
ETA_PARAMETER_UNITS = ("degree_2theta", "degree_fwhm", "relative_to_reference_clean_peak_height")
ETA_HALF_RANGES = np.asarray([0.06, 0.025, 0.005], dtype=np.float64)
SOLVER_KNOBS = {
    "method": "L-BFGS-B",
    "n_starts_per_profile": 1,
    "start_scaled_z": [0.0, 0.0, 0.0],
    "scaled_bounds_per_coordinate": [-0.999, 0.999],
    "options": {"maxiter": 80, "ftol": 1e-10, "gtol": 1e-7, "maxls": 25},
    "fixed_q": True,
    "initialization_source": "same canonical zero scaled nuisance coordinate for A and B; never model eta or eta_true",
    "objective": (
        "mean squared error between expected_profile and supplied observed_profile, "
        "both max-normalized log1p_100"
    ),
}
HISTORIC_ANCHORS = {
    "status": "frozen P3 reference values; verification anchors, not targets",
    "q_mae_normalized": {
        "simple": {"A": 0.013533, "B": 0.013676},
        "v9": {"A": 0.032235, "B": 0.030554},
    },
    "noncomparable_observed_profile_rmse": {"v9": {"A_profile_fit": 0.016034, "B_native_eta": 0.027332}},
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def sha256_array(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(json.dumps(list(contiguous.shape)).encode("ascii"))
    digest.update(contiguous.tobytes())
    return digest.hexdigest()


def checkpoint_path(row: dict[str, Any], checkpoint_root: Path = CHECKPOINT_ROOT) -> Path:
    return checkpoint_root / row["path"]


def verify_checkpoint_hashes(
    manifest_path: Path = CHECKPOINT_MANIFEST_PATH,
    checkpoint_root: Path = CHECKPOINT_ROOT,
) -> list[dict[str, Any]]:
    """Verify all 12 read-only inference assets before loading any model."""
    manifest = read_json(manifest_path)
    rows = manifest.get("retained_checkpoints", [])
    if len(rows) != 12:
        raise RuntimeError(f"expected 12 retained inference checkpoints, found {len(rows)}")
    checked: list[dict[str, Any]] = []
    identities: set[tuple[str, str, int]] = set()
    for row in rows:
        identity = (row["condition"], row["method"], int(row["seed"]))
        if identity in identities:
            raise RuntimeError(f"duplicate checkpoint identity: {identity}")
        identities.add(identity)
        path = checkpoint_path(row, checkpoint_root)
        if not path.is_file():
            raise FileNotFoundError(f"required inference-only checkpoint is missing: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != row["sha256"]:
            raise RuntimeError(f"checkpoint SHA-256 mismatch for {path.name}")
        if path.stat().st_size != int(row["bytes"]):
            raise RuntimeError(f"checkpoint byte-size mismatch for {path.name}")
        checked.append(
            {
                "path": row["path"],
                "condition": row["condition"],
                "method": row["method"],
                "seed": int(row["seed"]),
                "sha256": actual_hash,
                "bytes": path.stat().st_size,
                "inference_only": row.get("format") == "issue19_inference_only_best_state_v1",
            }
        )
    expected = {(condition, method, seed) for condition in CONDITIONS for method in METHODS for seed in SEEDS}
    if identities != expected:
        raise RuntimeError(f"checkpoint identity set differs from frozen A/B design: {identities}")
    if not all(row["inference_only"] for row in checked):
        raise RuntimeError("a retained checkpoint is not identified as inference-only")
    return checked


def load_and_freeze_model(
    row: dict[str, Any], input_length: int, device: torch.device
) -> torch.nn.Module:
    """Load the selected state without optimizer/RNG state and freeze all weights."""
    path = checkpoint_path(row)
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    expected_identity = (row["condition"], row["method"], int(row["seed"]))
    actual_identity = (checkpoint.get("condition"), checkpoint.get("method"), int(checkpoint.get("seed", -1)))
    if actual_identity != expected_identity:
        raise RuntimeError(f"checkpoint metadata identity mismatch: {actual_identity} != {expected_identity}")
    if "best_model_state" not in checkpoint or "optimizer_state" in checkpoint:
        raise RuntimeError(f"checkpoint is not a retained inference-only best state: {path.name}")
    model: torch.nn.Module = (
        ParameterRegressor(input_length=input_length)
        if row["method"] == "A"
        else MeasurementAwareRegressor(input_length=input_length)
    ).to(device)
    model.load_state_dict(checkpoint["best_model_state"], strict=True)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    if model.training or any(parameter.requires_grad for parameter in model.parameters()):
        raise RuntimeError("model is not frozen for inference")
    del checkpoint
    return model


def predict_profiles(
    model: torch.nn.Module, profiles: np.ndarray, device: torch.device, batch_size: int = 16
) -> tuple[np.ndarray, np.ndarray | None, dict[str, float]]:
    """Predict q (and optional native eta) from observed inputs only."""
    q_rows: list[np.ndarray] = []
    eta_rows: list[np.ndarray] = []
    started = time.perf_counter()
    gpu_started = torch.cuda.Event(enable_timing=True)
    gpu_finished = torch.cuda.Event(enable_timing=True)
    gpu_started.record()
    with torch.no_grad():
        for start in range(0, len(profiles), batch_size):
            x = torch.as_tensor(profiles[start : start + batch_size], device=device, dtype=torch.float32)
            output = model(x)
            if isinstance(output, tuple):
                q, eta = output
                eta_rows.append(eta.detach().cpu().numpy().astype(np.float64))
            else:
                q = output
            q_rows.append(q.detach().cpu().numpy().astype(np.float64))
    gpu_finished.record()
    torch.cuda.synchronize(device)
    wallclock = time.perf_counter() - started
    gpu_seconds = float(gpu_started.elapsed_time(gpu_finished) / 1000.0)
    return (
        np.concatenate(q_rows),
        np.concatenate(eta_rows) if eta_rows else None,
        {"cpu_wallclock_seconds": float(wallclock), "gpu_cuda_event_seconds": gpu_seconds},
    )


def eta_from_scaled(z: np.ndarray) -> np.ndarray:
    """Map the canonical scaled optimizer coordinates into physical nuisance units."""
    values = np.asarray(z, dtype=np.float64)
    return np.stack(
        (
            0.06 * values[..., 0],
            0.08 + 0.05 * (values[..., 1] + 1.0) / 2.0,
            0.01 * (values[..., 2] + 1.0) / 2.0,
        ),
        axis=-1,
    )


def profile_fit_eta_shared(
    forward: Any,
    q_value: np.ndarray,
    observed_profile: np.ndarray,
    *,
    background_mode: str,
    device: torch.device,
) -> dict[str, Any]:
    """The one shared, fixed-q, non-oracle profile solver used for A and B.

    Truth labels, model identity, native eta, and fitted q are deliberately not
    accepted by this function. The algorithm and knobs mirror the P3 A solver.
    """
    q_tensor = torch.as_tensor(np.asarray(q_value)[None, :], device=device, dtype=torch.float64)
    target = torch.as_tensor(np.asarray(observed_profile)[None, :], device=device, dtype=torch.float32)
    if not torch.isfinite(q_tensor).all() or not torch.isfinite(target).all():
        raise ValueError("profile solver inputs must be finite")

    def objective(z: np.ndarray) -> tuple[float, np.ndarray]:
        eta = torch.as_tensor(eta_from_scaled(z)[None, :], device=device, dtype=torch.float64)
        eta.requires_grad_(True)
        expected = expected_profile(forward, q_tensor, eta, background_shape_mode=background_mode)
        loss = F.mse_loss(expected.to(dtype=torch.float32), target)
        gradient = torch.autograd.grad(loss, eta)[0][0]
        scaled_gradient = np.asarray(
            [float(gradient[0].cpu()) * 0.06, float(gradient[1].cpu()) * 0.025, float(gradient[2].cpu()) * 0.005],
            dtype=np.float64,
        )
        return float(loss.detach().cpu()), scaled_gradient

    gpu_started = torch.cuda.Event(enable_timing=True)
    gpu_finished = torch.cuda.Event(enable_timing=True)
    gpu_started.record()
    started = time.perf_counter()
    result = scipy.optimize.minimize(
        objective,
        np.asarray(SOLVER_KNOBS["start_scaled_z"], dtype=np.float64),
        method=SOLVER_KNOBS["method"],
        jac=True,
        bounds=[tuple(SOLVER_KNOBS["scaled_bounds_per_coordinate"])] * 3,
        options=dict(SOLVER_KNOBS["options"]),
    )
    gpu_finished.record()
    torch.cuda.synchronize(device)
    wallclock = time.perf_counter() - started
    gpu_seconds = float(gpu_started.elapsed_time(gpu_finished) / 1000.0)
    scaled_z = np.asarray(result.x, dtype=np.float64)
    eta = eta_from_scaled(scaled_z)
    coordinate_hits = np.isclose(np.abs(scaled_z), 0.999, atol=1e-5)
    return {
        "eta_physical": eta.tolist(),
        "scaled_z": scaled_z.tolist(),
        "profile_mse": float(result.fun),
        "profile_rmse": float(math.sqrt(max(0.0, float(result.fun)))),
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "nfev": int(result.nfev),
        "nit": int(result.nit),
        "boundary_hit_by_coordinate": coordinate_hits.tolist(),
        "boundary_hit": bool(np.any(coordinate_hits)),
        "cpu_wallclock_seconds": float(wallclock),
        "gpu_cuda_event_seconds": gpu_seconds,
        "initial_scaled_z": list(SOLVER_KNOBS["start_scaled_z"]),
    }


def render_profiles(
    forward: Any,
    q_values: np.ndarray,
    eta_values: np.ndarray,
    *,
    background_mode: str,
    device: torch.device,
    batch_size: int = 16,
) -> np.ndarray:
    rows: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(q_values), batch_size):
            q = torch.as_tensor(q_values[start : start + batch_size], device=device, dtype=torch.float64)
            eta = torch.as_tensor(eta_values[start : start + batch_size], device=device, dtype=torch.float64)
            profiles = expected_profile(forward, q, eta, background_shape_mode=background_mode)
            rows.append(profiles.detach().cpu().numpy().astype(np.float64))
    return np.concatenate(rows)


def safe_pearson(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 2 or float(np.std(x)) == 0.0 or float(np.std(y)) == 0.0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def mean_and_sample_sd(values: list[float] | np.ndarray) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(np.mean(array)),
        "sd_sample": float(np.std(array, ddof=1)) if len(array) > 1 else 0.0,
        "per_seed_values": [float(item) for item in array],
    }


def validate_frozen_inputs(
    config: dict[str, Any], arrays: dict[str, np.ndarray], split_file: dict[str, Any],
    validation_selection: dict[str, Any], old_results: dict[str, Any]
) -> np.ndarray:
    if tuple(config["training"]["seeds"]) != SEEDS:
        raise RuntimeError("P3 seed roster differs from the frozen diagnostic roster")
    if config["forward"]["q_bounds"] != [-0.8, 0.8]:
        raise RuntimeError("frozen q bounds changed")
    if config["training"]["max_epochs"] != 24:
        raise RuntimeError("frozen selected epoch protocol changed")
    if validation_selection.get("simple", {}).get("selected_lambda") != 0.1:
        raise RuntimeError("frozen simple lambda selection changed")
    if validation_selection.get("v9", {}).get("selected_lambda") != 1.0:
        raise RuntimeError("frozen V9 lambda selection changed")
    if old_results.get("test_used_for_selection") is not False:
        raise RuntimeError("historic P3 result does not record test-free selection")
    for split in ("train", "validation", "test"):
        from_file = np.asarray(split_file[split], dtype=np.int64)
        from_npz = arrays[f"{split}_indices"].astype(np.int64, copy=False)
        if not np.array_equal(from_file, from_npz):
            raise RuntimeError(f"frozen {split} split differs between the two source records")
    test_indices = np.asarray(split_file["test"], dtype=np.int64)
    if len(test_indices) != 77 or len(np.unique(test_indices)) != 77:
        raise RuntimeError("expected exactly 77 unique frozen test q indices")
    return test_indices


def verify_prediction_against_p3(
    condition: str, method: str, seed: int, q_pred: np.ndarray, eta_pred: np.ndarray | None,
    old_results: dict[str, Any], subset_count: int
) -> None:
    old = old_results["per_seed"][condition][method][str(seed)]
    old_q = np.asarray(old["prediction_q"], dtype=np.float64)[:subset_count]
    if not np.allclose(q_pred, old_q, rtol=0.0, atol=2e-6):
        raise RuntimeError(f"frozen q predictions do not reproduce for {condition}/{method}/{seed}")
    if method == "B":
        if eta_pred is None:
            raise RuntimeError("B checkpoint did not return its nuisance head")
        old_eta = np.asarray(old["prediction_eta_used_for_observed_reconstruction"], dtype=np.float64)[:subset_count]
        if not np.allclose(eta_pred, old_eta, rtol=0.0, atol=2e-6):
            raise RuntimeError(f"frozen B eta predictions do not reproduce for {condition}/{seed}")


def evaluate_frozen_model(
    *, condition: str, method: str, seed: int, model: torch.nn.Module, arrays: dict[str, np.ndarray],
    test_indices: np.ndarray, forward: Any, structure: Structure, forward_cfg: dict[str, Any],
    device: torch.device, checkpoint_sha256: str, old_results: dict[str, Any], sample_count: int | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed_all = arrays[f"{condition}_observed"]
    selected_indices = test_indices if sample_count is None else test_indices[:sample_count]
    observed = observed_all[selected_indices]
    q_pred, eta_native, inference_cost = predict_profiles(model, observed, device)
    verify_prediction_against_p3(condition, method, seed, q_pred, eta_native, old_results, len(selected_indices))

    # Truth is first accessed below prediction. It is used only to score outputs.
    q_true = arrays["q"][selected_indices].astype(np.float64)
    eta_true = arrays[f"{condition}_eta_true"][selected_indices].astype(np.float64)
    q_abs_error = np.abs(q_pred - q_true)
    q_mae = {
        "du": float(q_abs_error[:, 0].mean()),
        "dv": float(q_abs_error[:, 1].mean()),
        "mean_two_coordinate": float(q_abs_error.mean()),
    }
    a_true, c_true = p3.q_to_lattice(q_true, structure, forward_cfg)
    a_pred, c_pred = p3.q_to_lattice(q_pred, structure, forward_cfg)
    lattice_mae = {
        "a_angstrom": float(np.mean(np.abs(a_pred - a_true))),
        "c_angstrom": float(np.mean(np.abs(c_pred - c_true))),
    }

    fit_rows: list[dict[str, Any]] = []
    for q_value, profile in zip(q_pred, observed, strict=True):
        fit_rows.append(
            profile_fit_eta_shared(
                forward,
                q_value,
                profile,
                background_mode=BACKGROUND_MODES[condition],
                device=device,
            )
        )
    eta_fit = np.asarray([row["eta_physical"] for row in fit_rows], dtype=np.float64)
    eta_fit_z = np.asarray([row["scaled_z"] for row in fit_rows], dtype=np.float64)
    shared_rmse = float(np.sqrt(np.mean([row["profile_mse"] for row in fit_rows])))
    eta_fit_scaled_error = (eta_fit - eta_true) / ETA_HALF_RANGES
    eta_fit_physical_error = eta_fit - eta_true
    eta_fit_mismatch = np.mean(np.abs(eta_fit_scaled_error), axis=1)
    q_error_scalar = np.mean(q_abs_error, axis=1)

    metrics: dict[str, Any] = {
        "condition": condition,
        "method": method,
        "seed": int(seed),
        "checkpoint_sha256": checkpoint_sha256,
        "sample_count": len(selected_indices),
        "q_prediction_sha256": sha256_array(q_pred),
        "native_eta_prediction_sha256": sha256_array(eta_native) if eta_native is not None else None,
        "q_mae_normalized": q_mae,
        "lattice_mae_angstrom": lattice_mae,
        "shared_fit_profile_rmse_transformed": shared_rmse,
        "shared_fit": {
            "solver_knobs_sha256": json_sha256(SOLVER_KNOBS),
            "n_profiles": len(fit_rows),
            "start_scaled_z": list(SOLVER_KNOBS["start_scaled_z"]),
            "nfev_total": int(sum(row["nfev"] for row in fit_rows)),
            "nfev_mean": float(np.mean([row["nfev"] for row in fit_rows])),
            "nit_total": int(sum(row["nit"] for row in fit_rows)),
            "nit_mean": float(np.mean([row["nit"] for row in fit_rows])),
            "failure_count": int(sum(not row["success"] for row in fit_rows)),
            "failure_rate": float(np.mean([not row["success"] for row in fit_rows])),
            "boundary_hit_count": int(sum(row["boundary_hit"] for row in fit_rows)),
            "boundary_hit_rate": float(np.mean([row["boundary_hit"] for row in fit_rows])),
            "boundary_hit_count_by_coordinate": np.sum(
                np.asarray([row["boundary_hit_by_coordinate"] for row in fit_rows], dtype=np.int64), axis=0
            ).tolist(),
            "eta_mean_physical_by_coordinate": np.mean(eta_fit, axis=0).tolist(),
            "eta_sd_across_examples_by_coordinate": np.std(eta_fit, axis=0, ddof=1).tolist()
            if len(eta_fit) > 1 else [0.0, 0.0, 0.0],
            "eta_mean_scaled_z_by_coordinate": np.mean(eta_fit_z, axis=0).tolist(),
            "eta_truth_mismatch_after_prediction_only": {
                "mae_physical_by_coordinate": np.mean(np.abs(eta_fit_physical_error), axis=0).tolist(),
                "rmse_physical_by_coordinate": np.sqrt(np.mean(eta_fit_physical_error**2, axis=0)).tolist(),
                "mean_scaled_absolute_error_by_coordinate": np.mean(np.abs(eta_fit_scaled_error), axis=0).tolist(),
            },
            "q_error_vs_eta_mismatch_pearson_r_descriptive_only": safe_pearson(q_error_scalar, eta_fit_mismatch),
            "cpu_wallclock_seconds_total": float(sum(row["cpu_wallclock_seconds"] for row in fit_rows)),
            "cpu_wallclock_seconds_mean_per_fit": float(np.mean([row["cpu_wallclock_seconds"] for row in fit_rows])),
            "gpu_cuda_event_seconds_total": float(sum(row["gpu_cuda_event_seconds"] for row in fit_rows)),
            "gpu_cuda_event_seconds_mean_per_fit": float(np.mean([row["gpu_cuda_event_seconds"] for row in fit_rows])),
        },
        "inference_cost": inference_cost,
    }

    native_profile_rmse: float | None = None
    eta_native_bias: np.ndarray | None = None
    eta_native_rmse: np.ndarray | None = None
    eta_native_scaled_abs_error: np.ndarray | None = None
    native_q_corr: float | None = None
    if method == "B":
        if eta_native is None:
            raise RuntimeError("B native-head diagnostic requires the model's eta prediction")
        native_expected = render_profiles(
            forward, q_pred, eta_native, background_mode=BACKGROUND_MODES[condition], device=device
        )
        native_profile_rmse = float(np.sqrt(np.mean((native_expected - observed.astype(np.float64)) ** 2)))
        eta_native_error = eta_native - eta_true
        eta_native_bias = np.mean(eta_native_error, axis=0)
        eta_native_rmse = np.sqrt(np.mean(eta_native_error**2, axis=0))
        eta_native_scaled = eta_native_error / ETA_HALF_RANGES
        eta_native_scaled_abs_error = np.mean(np.abs(eta_native_scaled), axis=0)
        native_q_corr = safe_pearson(q_error_scalar, np.mean(np.abs(eta_native_scaled), axis=1))
        metrics["native_head"] = {
            "profile_rmse_transformed_at_fixed_q": native_profile_rmse,
            "profile_rmse_reduction_after_shared_eta_fit_same_q": native_profile_rmse - shared_rmse,
            "eta_bias_physical_by_coordinate_after_prediction_only": eta_native_bias.tolist(),
            "eta_rmse_physical_by_coordinate_after_prediction_only": eta_native_rmse.tolist(),
            "eta_mean_physical_by_coordinate": np.mean(eta_native, axis=0).tolist(),
            "eta_mae_scaled_coordinate_after_prediction_only": eta_native_scaled_abs_error.tolist(),
            "zero_shift_bias_degree": float(eta_native_bias[0]),
            "zero_shift_rmse_degree": float(eta_native_rmse[0]),
            "q_error_vs_eta_mismatch_pearson_r_descriptive_only": native_q_corr,
        }

    per_example: list[dict[str, Any]] = []
    for local_i, global_index in enumerate(selected_indices.tolist()):
        row: dict[str, Any] = {
            "global_test_index": int(global_index),
            "condition": condition,
            "method": method,
            "seed": int(seed),
            "q_pred": q_pred[local_i].tolist(),
            "q_true_scoring_only": q_true[local_i].tolist(),
            "q_abs_error_scoring_only": q_abs_error[local_i].tolist(),
            "eta_shared_fit_physical": eta_fit[local_i].tolist(),
            "eta_shared_fit_scaled_z": eta_fit_z[local_i].tolist(),
            "shared_fit_profile_rmse_transformed": float(math.sqrt(max(0.0, fit_rows[local_i]["profile_mse"]))),
            "shared_fit_result": fit_rows[local_i],
            "eta_true_scoring_only": eta_true[local_i].tolist(),
        }
        if method == "B" and eta_native is not None and eta_native_bias is not None and eta_native_rmse is not None:
            expected_native_i = native_expected[local_i]
            row.update(
                {
                    "eta_native_head_physical": eta_native[local_i].tolist(),
                    "native_profile_rmse_transformed_at_fixed_q": float(
                        np.sqrt(np.mean((expected_native_i - observed[local_i]) ** 2))
                    ),
                    "eta_native_error_physical_scoring_only": (eta_native[local_i] - eta_true[local_i]).tolist(),
                }
            )
        per_example.append(row)
    return metrics, per_example


def summarize_runs(rows: list[dict[str, Any]], condition: str, method: str) -> dict[str, Any]:
    selected = [row for row in rows if row["condition"] == condition and row["method"] == method]
    if len(selected) != 3:
        raise RuntimeError(f"expected three frozen seed runs for {condition}/{method}, got {len(selected)}")
    scalar_paths: dict[str, Any] = {
        "q_mae_du": lambda row: row["q_mae_normalized"]["du"],
        "q_mae_dv": lambda row: row["q_mae_normalized"]["dv"],
        "q_mae_mean_two_coordinate": lambda row: row["q_mae_normalized"]["mean_two_coordinate"],
        "a_mae_angstrom": lambda row: row["lattice_mae_angstrom"]["a_angstrom"],
        "c_mae_angstrom": lambda row: row["lattice_mae_angstrom"]["c_angstrom"],
        "shared_fit_profile_rmse_transformed": lambda row: row["shared_fit_profile_rmse_transformed"],
        "shared_fit_nfev_mean": lambda row: row["shared_fit"]["nfev_mean"],
        "shared_fit_nit_mean": lambda row: row["shared_fit"]["nit_mean"],
        "shared_fit_failure_rate": lambda row: row["shared_fit"]["failure_rate"],
        "shared_fit_boundary_hit_rate": lambda row: row["shared_fit"]["boundary_hit_rate"],
        "shared_fit_cpu_wallclock_seconds_total": lambda row: row["shared_fit"]["cpu_wallclock_seconds_total"],
        "shared_fit_gpu_cuda_event_seconds_total": lambda row: row["shared_fit"]["gpu_cuda_event_seconds_total"],
        "inference_cpu_wallclock_seconds": lambda row: row["inference_cost"]["cpu_wallclock_seconds"],
        "inference_gpu_cuda_event_seconds": lambda row: row["inference_cost"]["gpu_cuda_event_seconds"],
        "shared_fit_eta_delta_mean_degree": lambda row: row["shared_fit"]["eta_mean_physical_by_coordinate"][0],
        "shared_fit_eta_fwhm_mean_degree": lambda row: row["shared_fit"]["eta_mean_physical_by_coordinate"][1],
        "shared_fit_eta_background_mean_ratio": lambda row: row["shared_fit"]["eta_mean_physical_by_coordinate"][2],
        "shared_fit_eta_delta_scaled_z_mean": lambda row: row["shared_fit"]["eta_mean_scaled_z_by_coordinate"][0],
        "shared_fit_eta_fwhm_scaled_z_mean": lambda row: row["shared_fit"]["eta_mean_scaled_z_by_coordinate"][1],
        "shared_fit_eta_background_scaled_z_mean": lambda row: row["shared_fit"]["eta_mean_scaled_z_by_coordinate"][2],
        "shared_fit_q_error_eta_mismatch_pearson_r_descriptive_only": lambda row: row[
            "shared_fit"
        ]["q_error_vs_eta_mismatch_pearson_r_descriptive_only"],
    }
    result: dict[str, Any] = {
        "seed_count": len(selected),
        "sample_count_per_seed": sorted({row["sample_count"] for row in selected}),
        "metrics_mean_sd_across_three_seed_level_estimates": {},
        "per_seed": selected,
    }
    for name, getter in scalar_paths.items():
        values = [getter(row) for row in selected]
        if all(value is not None for value in values):
            result["metrics_mean_sd_across_three_seed_level_estimates"][name] = mean_and_sample_sd(values)
    if method == "B":
        for key, getter in {
            "native_profile_rmse_transformed": lambda row: row["native_head"]["profile_rmse_transformed_at_fixed_q"],
            "native_to_profiled_rmse_reduction_same_fixed_q": lambda row: row["native_head"][
                "profile_rmse_reduction_after_shared_eta_fit_same_q"
            ],
            "native_eta_zero_shift_bias_degree": lambda row: row["native_head"]["zero_shift_bias_degree"],
            "native_eta_zero_shift_rmse_degree": lambda row: row["native_head"]["zero_shift_rmse_degree"],
            "native_eta_delta_scaled_mae": lambda row: row["native_head"][
                "eta_mae_scaled_coordinate_after_prediction_only"
            ][0],
            "native_eta_fwhm_scaled_mae": lambda row: row["native_head"][
                "eta_mae_scaled_coordinate_after_prediction_only"
            ][1],
            "native_eta_background_scaled_mae": lambda row: row["native_head"][
                "eta_mae_scaled_coordinate_after_prediction_only"
            ][2],
            "native_q_error_eta_mismatch_pearson_r_descriptive_only": lambda row: row[
                "native_head"
            ]["q_error_vs_eta_mismatch_pearson_r_descriptive_only"],
        }.items():
            values = [getter(row) for row in selected]
            if all(value is not None for value in values):
                result["metrics_mean_sd_across_three_seed_level_estimates"][key] = mean_and_sample_sd(values)
        for coordinate_index, coordinate_name in enumerate(ETA_PARAMETER_NAMES):
            for error_key in (
                "eta_bias_physical_by_coordinate_after_prediction_only",
                "eta_rmse_physical_by_coordinate_after_prediction_only",
            ):
                values = [row["native_head"][error_key][coordinate_index] for row in selected]
                key = f"native_{error_key.removesuffix('_by_coordinate_after_prediction_only')}_{coordinate_name}"
                result["metrics_mean_sd_across_three_seed_level_estimates"][key] = mean_and_sample_sd(values)
    return result


def input_asset_hashes() -> dict[str, str]:
    paths = {
        "p3_config": CONFIG_PATH,
        "formal_data_npz": FORMAL_DIR / "formal_data.npz",
        "split_indices_json": FORMAL_DIR / "split_indices.json",
        "validation_lambda_selection_json": FORMAL_DIR / "validation_lambda_selection.json",
        "prior_ab_results_json": FORMAL_DIR / "ab_results.json",
        "checkpoint_space_optimization_json": CHECKPOINT_MANIFEST_PATH,
        "forward_config": ROOT / "xrd_inversion/configs/week1_formal_gate.json",
        "cif": ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif",
        "p3_source_script": ROOT / "xrd_forward_loss/scripts/run_issue19_p3.py",
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def load_sources() -> tuple[dict[str, Any], dict[str, np.ndarray], dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = read_json(CONFIG_PATH)
    split_file = read_json(FORMAL_DIR / "split_indices.json")
    validation_selection = read_json(FORMAL_DIR / "validation_lambda_selection.json")
    old_results = read_json(FORMAL_DIR / "ab_results.json")
    with np.load(FORMAL_DIR / "formal_data.npz", allow_pickle=False) as source:
        arrays = {key: source[key].copy() for key in source.files}
    return config, arrays, split_file, validation_selection, old_results


def build_forward(config: dict[str, Any], device: torch.device) -> tuple[Any, dict[str, Any], Structure]:
    forward_cfg = read_json(ROOT / config["forward"]["config"])
    structure = Structure.from_file(ROOT / config["source"]["cif"])
    forward = CachedTetragonalGPUForward(
        structure,
        grid_config=forward_cfg["grid"],
        parameter_config=forward_cfg["parameterization"],
        device=str(device),
        dtype=torch.float64,
    )
    return forward, forward_cfg, structure


def run_diagnostic(*, mode: str, sample_count: int, output_dir: Path, command: list[str]) -> dict[str, Any]:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "BLOCKED: frozen P3 renderer requires CUDA; CPU backend is not implemented "
            "by its authoritative renderer"
        )
    device = torch.device("cuda")
    config, arrays, split_file, validation_selection, old_results = load_sources()
    test_indices = validate_frozen_inputs(config, arrays, split_file, validation_selection, old_results)
    checked_checkpoints = verify_checkpoint_hashes()

    if mode == "full":
        marker = output_dir / ".full_run_started.json"
        if (output_dir / "metrics.json").exists() or (output_dir / "run_manifest.json").exists() or marker.exists():
            raise RuntimeError("a full diagnostic run has already started or completed; refusing to rerun")
        output_dir.mkdir(parents=True, exist_ok=True)
        marker_data = {
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "command": command,
        }
        marker.write_text(
            json.dumps(marker_data, indent=2) + "\n", encoding="utf-8"
        )
    forward, forward_cfg, structure = build_forward(config, device)
    loaded: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    per_example: list[dict[str, Any]] = []
    smoke_repeatability: list[dict[str, Any]] = []

    if mode == "smoke":
        requested_seeds = (SEEDS[0],)
        requested_conditions = CONDITIONS
        requested_methods = METHODS
        requested_count = max(1, min(3, int(sample_count)))
    else:
        requested_seeds = SEEDS
        requested_conditions = CONDITIONS
        requested_methods = METHODS
        requested_count = None

    for row in checked_checkpoints:
        model = load_and_freeze_model(row, int(arrays[f"{row['condition']}_observed"].shape[1]), device)
        loaded.append({"condition": row["condition"], "method": row["method"], "seed": row["seed"], "loaded": True})
        del model
        torch.cuda.empty_cache()

    run_started = time.perf_counter()
    for condition in requested_conditions:
        for seed in requested_seeds:
            for method in requested_methods:
                checkpoint_row = next(
                    item for item in checked_checkpoints
                    if item["condition"] == condition and item["method"] == method and item["seed"] == seed
                )
                model = load_and_freeze_model(checkpoint_row, int(arrays[f"{condition}_observed"].shape[1]), device)
                metrics, examples = evaluate_frozen_model(
                    condition=condition,
                    method=method,
                    seed=seed,
                    model=model,
                    arrays=arrays,
                    test_indices=test_indices,
                    forward=forward,
                    structure=structure,
                    forward_cfg=forward_cfg,
                    device=device,
                    checkpoint_sha256=checkpoint_row["sha256"],
                    old_results=old_results,
                    sample_count=requested_count,
                )
                rows.append(metrics)
                per_example.extend(examples)

                # Deterministic repeat on the same small set verifies solver repeatability.
                if mode == "smoke":
                    observed = arrays[f"{condition}_observed"][test_indices[:requested_count]]
                    q_repeat, eta_repeat, _ = predict_profiles(model, observed, device)
                    if sha256_array(q_repeat) != metrics["q_prediction_sha256"]:
                        raise RuntimeError(f"deterministic q prediction repeat failed for {condition}/{method}")
                    if eta_repeat is not None and sha256_array(eta_repeat) != metrics["native_eta_prediction_sha256"]:
                        raise RuntimeError(f"deterministic eta prediction repeat failed for {condition}/{method}")
                    first_repeat = profile_fit_eta_shared(
                        forward, q_repeat[0], observed[0], background_mode=BACKGROUND_MODES[condition], device=device
                    )
                    first_initial = examples[0]["shared_fit_result"]
                    same_eta = np.allclose(
                        first_repeat["eta_physical"],
                        first_initial["eta_physical"],
                        rtol=0.0,
                        atol=1e-11,
                    )
                    same_loss = math.isclose(
                        first_repeat["profile_mse"],
                        first_initial["profile_mse"],
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    )
                    smoke_repeatability.append(
                        {
                            "condition": condition,
                            "method": method,
                            "seed": seed,
                            "same_eta": bool(same_eta),
                            "same_loss": bool(same_loss),
                        }
                    )
                    if not same_eta or not same_loss:
                        raise RuntimeError(f"deterministic repeatability failed for {condition}/{method}")
                    if method == "B" and eta_repeat is None:
                        raise RuntimeError("B smoke repeat did not return its native eta head")
                del model
                torch.cuda.empty_cache()
    runtime = time.perf_counter() - run_started

    # On smoke, every shared fit must match the historic A fit where applicable,
    # and all inferred q/native eta values were verified against stored P3 output.
    if mode == "smoke":
        for metric in rows:
            old = old_results["per_seed"][metric["condition"]][metric["method"]][str(metric["seed"])]
            if metric["method"] == "A":
                old_fit_eta = np.asarray(old["prediction_eta_used_for_observed_reconstruction"][:requested_count])
                current_fit_eta = np.asarray(
                    [
                        row["eta_shared_fit_physical"]
                        for row in per_example
                        if row["condition"] == metric["condition"]
                        and row["method"] == "A"
                    ]
                )
                if not np.allclose(old_fit_eta, current_fit_eta, rtol=0.0, atol=2e-6):
                    raise RuntimeError(
                        "new shared A solver does not reproduce historic P3 profile fit "
                        f"for {metric['condition']}"
                    )
        return {
            "status": "PASS",
            "mode": "read_only_smoke",
            "samples_per_condition_method": requested_count,
            "conditions": list(requested_conditions),
            "methods": list(requested_methods),
            "seed": SEEDS[0],
            "checkpoint_hashes_verified": len(checked_checkpoints),
            "all_checkpoint_states_loaded": len(loaded),
            "q_and_native_eta_match_frozen_p3": True,
            "shared_fit_reproduces_historic_a_fit_on_smoke_subset": True,
            "deterministic_repeats": smoke_repeatability,
            "all_models_frozen": True,
            "eta_true_and_q_true_used_after_prediction_only": True,
            "fit_count": sum(row["shared_fit"]["n_profiles"] for row in rows),
            "wallclock_seconds": runtime,
            "gpu": torch.cuda.get_device_name(0),
        }

    aggregate = {
        condition: {method: summarize_runs(rows, condition, method) for method in METHODS}
        for condition in CONDITIONS
    }
    for condition in CONDITIONS:
        for seed in SEEDS:
            row_a = next(
                row
                for row in rows
                if row["condition"] == condition
                and row["seed"] == seed
                and row["method"] == "A"
            )
            row_b = next(
                row
                for row in rows
                if row["condition"] == condition
                and row["seed"] == seed
                and row["method"] == "B"
            )
            q_a = row_a["q_mae_normalized"]["mean_two_coordinate"]
            q_b = row_b["q_mae_normalized"]["mean_two_coordinate"]
            shared_a = row_a["shared_fit_profile_rmse_transformed"]
            shared_b = row_b["shared_fit_profile_rmse_transformed"]
            aggregate[condition].setdefault("paired_seed_differences_B_minus_A", {})
            aggregate[condition]["paired_seed_differences_B_minus_A"][str(seed)] = {
                "q_mae_normalized_mean_two_coordinate": q_b - q_a,
                "shared_fit_profile_rmse_transformed": shared_b - shared_a,
            }
        for metric_name in ("q_mae_normalized_mean_two_coordinate", "shared_fit_profile_rmse_transformed"):
            values = [
                aggregate[condition]["paired_seed_differences_B_minus_A"][str(seed)][metric_name]
                for seed in SEEDS
            ]
            aggregate[condition].setdefault(
                "paired_difference_mean_sd_across_seeds", {}
            )[metric_name] = mean_and_sample_sd(values)

    metrics_doc = {
        "schema": "issue19_nuisance_diagnostic_metrics_v1",
        "status": "COMPLETED_EXPLORATORY_POST_HOC_DIAGNOSTIC",
        "scope": (
            "single BaTiO3 P4mm CIF; frozen 77 test q indices; two conditions; "
            "three paired seeds; fixed q predictions"
        ),
        "interpretation_limit": (
            "No causal effect on frozen q weights; no blind confirmatory test; "
            "no real-domain or unseen-structure claim."
        ),
        "shared_fit_is": "post-hoc test-time bounded eta solver with fixed q; it is not a learned B nuisance head",
        "fit_cost_implication": (
            "profile optimization cost is reported separately from direct B-head "
            "inference and changes deployment significance"
        ),
        "conditions": list(CONDITIONS),
        "methods": list(METHODS),
        "seeds": list(SEEDS),
        "test_count_per_seed_condition": 77,
        "q_predictions_verified_against_frozen_p3": True,
        "eta_true_policy": (
            "used only after prediction for descriptive error/correlation metrics; "
            "never passed to model, solver, fit initialization, or setting selection"
        ),
        "q_true_policy": (
            "used only after prediction for q/lattice scores and descriptive "
            "correlation; never passed to model, solver, or fit setting selection"
        ),
        "prior_frozen_anchors": HISTORIC_ANCHORS,
        "fit_loss_preprocessing": (
            "expected_profile and observed inputs in max-normalized log1p_100 "
            "domain; identical renderer/loss for both methods"
        ),
        "nuisance_coordinates": [
            {"name": name, "unit": unit} for name, unit in zip(ETA_PARAMETER_NAMES, ETA_PARAMETER_UNITS, strict=True)
        ],
        "shared_solver": SOLVER_KNOBS,
        "shared_solver_sha256": json_sha256(SOLVER_KNOBS),
        "per_seed": rows,
        "aggregate": aggregate,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"
    if metrics_path.exists():
        raise RuntimeError("metrics.json already exists; refusing to overwrite or repeat the full diagnostic")
    metrics_path.write_text(
        json.dumps(metrics_doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    local_path = output_dir / "per_example_local.json.gz"
    with gzip.open(local_path, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(per_example, handle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
    try:
        source_commit = __import__("subprocess").check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8"
        ).strip()
    except Exception:
        source_commit = "unavailable"
    manifest_doc = {
        "schema": "issue19_nuisance_diagnostic_run_manifest_v1",
        "status": "COMPLETED",
        "classification": "exploratory post-hoc; test had prior P3 history",
        "source_commit_before_diagnostic_changes": source_commit,
        "branch": "codex/issue19-nuisance-diagnostic-20261018",
        "full_diagnostic_runs": 1,
        "command": command,
        "return_code": 0,
        "started_and_completed_runtime_seconds": runtime,
        "input_asset_sha256": input_asset_hashes(),
        "checkpoint_source_root": str(CHECKPOINT_ROOT),
        "checkpoints_sha256_and_identity": checked_checkpoints,
        "checkpoint_load_validation": {"count": len(loaded), "all_inference_state_loads_passed": len(loaded) == 12},
        "model_sha256_per_run": [
            {
                "condition": row["condition"],
                "method": row["method"],
                "seed": row["seed"],
                "checkpoint_sha256": row["checkpoint_sha256"],
            }
            for row in rows
        ],
        "frozen_design": {
            "test_q_indices_sha256": sha256_array(test_indices),
            "test_count_per_condition_seed": 77,
            "seeds": list(SEEDS),
            "selected_lambda": {key: validation_selection[key]["selected_lambda"] for key in CONDITIONS},
            "no_retraining_or_model_selection": True,
        },
        "solver": SOLVER_KNOBS,
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu": torch.cuda.get_device_name(0),
            "gpu_free_total_memory_bytes_before_output": list(torch.cuda.mem_get_info(0)),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "pymatgen": importlib.metadata.version("pymatgen"),
            "device": str(device),
        },
        "artifacts": {
            "metrics_json": {
                "path": "metrics.json",
                "sha256": sha256_file(metrics_path),
                "bytes": metrics_path.stat().st_size,
            },
            "per_example_local_json_gz": {
                "path": "per_example_local.json.gz",
                "sha256": sha256_file(local_path),
                "bytes": local_path.stat().st_size,
                "commit": False,
            },
        },
    }
    manifest_path = output_dir / "run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest_doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    marker = output_dir / ".full_run_started.json"
    if marker.exists():
        marker.unlink()
    return {"status": "COMPLETED", "metrics": metrics_doc, "run_manifest": manifest_doc}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full"), required=True)
    parser.add_argument(
        "--sample-count",
        type=int,
        default=2,
        help="Smoke only; capped at three per condition/method.",
    )
    parser.add_argument("--output-dir", type=Path, default=RESULT_DIR)
    args = parser.parse_args()
    result = run_diagnostic(
        mode=args.mode,
        sample_count=args.sample_count,
        output_dir=args.output_dir,
        command=[sys.executable, *sys.argv],
    )
    if args.mode == "smoke":
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    else:
        print(json.dumps({"status": result["status"], "output_dir": str(args.output_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
