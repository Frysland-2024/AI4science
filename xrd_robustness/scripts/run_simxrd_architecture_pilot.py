#!/usr/bin/env python
"""Run the frozen, three-configuration SimXRD/CNN11 PXRD pilot."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.experiment import file_hash, save_checkpoint  # noqa: E402
from xrd_robustness.models import (  # noqa: E402
    ML4PXRDResNet1DConfig,
    SimXRDCNN11Config,
)
from xrd_robustness.online_views import OnlineViewFactory, TrainingMode  # noqa: E402
from xrd_robustness.parent_budget_efficiency import (  # noqa: E402
    CyclicParentSampler,
    load_split_rows,
    validate_parent_split,
)
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.simulator import SimulationGrid  # noqa: E402
from xrd_robustness.simulator_v10 import (  # noqa: E402
    DEFAULT_LINE_PROFILE,
    render_pseudo_voigt_caglioti_peaks,
    simulate_from_peak_table_v10,
)
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.objectives import (  # noqa: E402
    TrainingStepConfig,
    run_training_step,
)
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher  # noqa: E402
from xrd_robustness.training.runner import PeakRecord  # noqa: E402
from xrd_robustness.view_manifest import build_offline_view_manifest, build_parameter_batch  # noqa: E402


PROTOCOL_PATH = PROJECT_ROOT / "configs" / "simxrd_cnn11_pilot.20261103.json"
V9_SIM_PATH = PROJECT_ROOT / "configs" / "simulation.method_transfer.frozen.json"
V10_SIM_PATH = PROJECT_ROOT / "configs" / "simulation.simxrd_v10_pilot.20261103.json"
REPORT_ROOT = PROJECT_ROOT / "reports" / "simxrd_architecture_pilot_20261103"
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data" / "formal_14060"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "simxrd_architecture_pilot_20261103"
TRAIN_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)
VALIDATION_PROFILES = TRAIN_PROFILES + ("in_range",)
EVAL_SEEDS = (20260721, 20260722, 20260723)
TRAINING_SEEDS = (20260711, 20260712, 20260713)
SIMULATOR_VERSIONS = {
    "v9": "v9_gaussian",
    "v10": "v10_pseudo_voigt_caglioti",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    return file_hash(path).upper()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    partial.replace(path)


def _log(handle: Any, event: str, **payload: Any) -> None:
    row = {"event": event, **payload}
    encoded = json.dumps(row, sort_keys=True, ensure_ascii=False)
    handle.write(encoded + "\n")
    handle.flush()
    print(encoded, flush=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_config() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = _read_json(PROTOCOL_PATH)
    sim_v9 = _read_json(V9_SIM_PATH)
    sim_v10 = _read_json(V10_SIM_PATH)
    return protocol, sim_v9, sim_v10


def _verify_data_bindings(data_root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    data = protocol["data"]
    split_path = data_root / "manifests" / "split_manifest.json"
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    cache_manifest_path = data_root / "manifests" / "peak_cache_manifest.v7.reflection.csv"
    checks = {
        "split_manifest_sha256": (split_path, data["split_hash"]),
        "source_records_sha256": (records_path, data["source_records_hash"]),
        "peak_cache_manifest_sha256": (cache_manifest_path, data["peak_cache_manifest_hash"]),
    }
    actual: dict[str, str] = {}
    for name, (path, expected) in checks.items():
        actual[name] = _sha256(path)
        if actual[name] != str(expected).upper():
            raise ValueError(f"{name} mismatch for {path}: {actual[name]} != {expected}")
    return actual


def _records(rows: Sequence[Mapping[str, Any]], split: str, data_root: Path) -> list[PeakRecord]:
    return [
        PeakRecord(
            material_id=str(row["material_id"]),
            label=CRYSTAL_SYSTEMS.index(str(row["crystal_system"])),
            split=split,
            peak_table_path=(
                data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{row['material_id']}.npz"
            ),
        )
        for row in sorted(rows, key=lambda item: str(item["material_id"]))
        if str(row["split"]) == split
    ]


def _labels(rows: Sequence[Mapping[str, Any]], split: str) -> tuple[list[str], np.ndarray]:
    chosen = sorted((row for row in rows if str(row["split"]) == split), key=lambda row: str(row["material_id"]))
    material_ids = [str(row["material_id"]) for row in chosen]
    values = np.asarray([CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in chosen], dtype=np.int64)
    return material_ids, values


def _make_peak_table_simulator(version: str, line_profile: Mapping[str, Any]):
    if version == "v9_gaussian":
        return None
    if version == "v10_pseudo_voigt_caglioti":
        from functools import partial

        return partial(simulate_from_peak_table_v10, line_profile=dict(line_profile))
    raise ValueError(f"unknown simulator version {version!r}")


def _make_model(model_id: str) -> tuple[torch.nn.Module, Any]:
    if model_id == "resnet18gn":
        config = ML4PXRDResNet1DConfig(model_id="18")
        from xrd_robustness.models import ML4PXRDResNet1D

        return ML4PXRDResNet1D(config), config
    if model_id == "cnn11":
        config = SimXRDCNN11Config()
        from xrd_robustness.models import SimXRDCNN11

        return SimXRDCNN11(config), config
    raise ValueError(f"unknown model_id {model_id!r}")


def _configure_runtime(device: torch.device, *, worker_threads: int = 2) -> dict[str, Any]:
    for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        os.environ[name] = str(worker_threads)
    torch.set_num_threads(worker_threads)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    bf16 = bool(device.type == "cuda" and torch.cuda.is_bf16_supported())
    if device.type == "cuda":
        torch.set_float32_matmul_precision("high")
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = True
    return {
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "gpu_total_memory_bytes": int(torch.cuda.get_device_properties(device).total_memory)
        if device.type == "cuda"
        else None,
        "amp_dtype": "bfloat16" if bf16 else "float32",
        "fused_adamw": bool(device.type == "cuda"),
        "torch_threads": worker_threads,
        "tf32_matmul": device.type == "cuda",
        "cudnn_benchmark": device.type == "cuda",
        "cudnn_deterministic": device.type == "cuda",
    }


def _autocast(device: torch.device, runtime: Mapping[str, Any]):
    if device.type == "cuda" and runtime["amp_dtype"] == "bfloat16":
        return torch.autocast(device_type="cuda", dtype=torch.bfloat16)
    from contextlib import nullcontext

    return nullcontext()


def _panel_cache_path(output_root: Path, split: str, version: str, seed: int) -> Path:
    return output_root / "evaluation_cache" / f"{split}_{version}_seed_{seed}"


def _build_panels(
    *,
    data_root: Path,
    output_root: Path,
    split_rows: Sequence[Mapping[str, Any]],
    split: str,
    simulator_version: str,
    sim_config: Mapping[str, Any],
    sim_config_path: Path,
    line_profile: Mapping[str, Any],
    seed: int,
    profiles: Sequence[str],
) -> tuple[dict[str, np.ndarray], np.ndarray, list[str], dict[str, Any]]:
    material_ids, labels = _labels(split_rows, split)
    cache_dir = _panel_cache_path(output_root, split, simulator_version, seed)
    index_path = cache_dir / "panel_index.json"
    config_hash = _sha256(sim_config_path)
    binding = {
        "schema_version": "simxrd-pilot-panels-v1",
        "split": split,
        "simulator_version": simulator_version,
        "simulation_config_sha256": config_hash,
        "split_manifest_sha256": _sha256(data_root / "manifests" / "split_manifest.json"),
        "ordered_material_ids_sha256": hashlib.sha256(_canonical(material_ids).encode("utf-8")).hexdigest().upper(),
        "seed": int(seed),
        "profiles": list(profiles),
        "shape": [len(material_ids), 3501],
        "dtype": "float32",
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    if index_path.is_file():
        index = _read_json(index_path)
        if index.get("bindings") != binding:
            raise ValueError(f"evaluation cache binding mismatch: {index_path}")
    else:
        index = {"bindings": binding, "entries": {}}

    sampler = PhysicsParameterSampler.from_mapping({**sim_config, "run_seed": int(seed)})
    factory = OnlineViewFactory(
        sampler,
        grid=SimulationGrid(),
        **(
            {}
            if _make_peak_table_simulator(simulator_version, line_profile) is None
            else {"peak_table_simulator": _make_peak_table_simulator(simulator_version, line_profile)}
        ),
    )
    rows_by_id = {str(row["material_id"]): row for row in split_rows if str(row["split"]) == split}
    peaks_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    panel_arrays: dict[str, np.ndarray] = {}
    for profile in profiles:
        panel_path = cache_dir / f"{profile}.npy"
        entry = index["entries"].get(profile)
        if entry:
            if not panel_path.is_file() or _sha256(panel_path) != entry["sha256"]:
                raise ValueError(f"evaluation panel integrity mismatch: {panel_path}")
            panel_arrays[profile] = np.load(panel_path, mmap_mode="r", allow_pickle=False)
            continue

        view_rows = build_offline_view_manifest(
            material_ids,
            sampler,
            profile=profile,
            views_per_material=1,
            split=split,
        )
        view_by_id = {row.material_id: row for row in view_rows}
        temporary = panel_path.with_suffix(".partial.npy")
        matrix = np.lib.format.open_memmap(
            temporary, mode="w+", dtype=np.float32, shape=(len(material_ids), 3501)
        )
        for position, material_id in enumerate(material_ids):
            peak_table = load_peak_table(peaks_root / f"{material_id}.npz")
            matrix[position] = factory.make_view_from_manifest(
                peak_table, view_by_id[material_id]
            ).xrd
        matrix.flush()
        del matrix
        temporary.replace(panel_path)
        entry = {
            "path": panel_path.name,
            "sha256": _sha256(panel_path),
            "shape": [len(material_ids), 3501],
            "dtype": "float32",
        }
        index["entries"][profile] = entry
        _write_json(index_path, index)
        panel_arrays[profile] = np.load(panel_path, mmap_mode="r", allow_pickle=False)
    return panel_arrays, labels, material_ids, index


def _evaluate_one_panel(
    model: torch.nn.Module,
    spectra: np.ndarray,
    labels: np.ndarray,
    *,
    device: torch.device,
    batch_size: int = 256,
) -> dict[str, Any]:
    model.eval()
    probabilities = np.empty((len(labels), len(CRYSTAL_SYSTEMS)), dtype=np.float32)
    for start in range(0, len(labels), batch_size):
        stop = min(start + batch_size, len(labels))
        batch = torch.from_numpy(np.array(spectra[start:stop], copy=True))
        if device.type == "cuda":
            batch = batch.pin_memory()
        with torch.inference_mode():
            logits = model(batch.to(device, non_blocking=device.type == "cuda"))["logits"]
            probabilities[start:stop] = torch.softmax(logits.float(), dim=-1).cpu().numpy()
    predictions = probabilities.argmax(axis=1)
    metrics = classification_metrics(labels, predictions, probabilities=probabilities, num_classes=7)
    metrics["per_class_f1_by_name"] = {
        name: float(score) for name, score in zip(CRYSTAL_SYSTEMS, metrics["per_class_f1"], strict=True)
    }
    return metrics


def _select_score(metrics: Mapping[str, Any], seed: int) -> tuple[float, float]:
    by_profile = metrics[str(seed)]
    return (
        float(np.mean([by_profile[name]["macro_f1"] for name in TRAIN_PROFILES])),
        float(by_profile["in_range"]["macro_f1"]),
    )


def _seed_all(seed: int) -> None:
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))


def _measure_fwhm(axis: np.ndarray, values: np.ndarray) -> float:
    profile = np.asarray(values, dtype=np.float64)
    peak = int(np.argmax(profile))
    half = float(profile[peak]) / 2.0
    left_candidates = np.flatnonzero(profile[:peak] <= half)
    right_candidates = np.flatnonzero(profile[peak + 1 :] <= half)
    if left_candidates.size == 0 or right_candidates.size == 0:
        raise ValueError("could not find both half-height crossings")
    left = int(left_candidates[-1])
    right = int(peak + 1 + right_candidates[0])
    left_x = np.interp(half, [profile[left], profile[left + 1]], [axis[left], axis[left + 1]])
    right_x = np.interp(half, [profile[right], profile[right - 1]], [axis[right], axis[right - 1]])
    return float(right_x - left_x)


def _smoke_training_path(
    *,
    config_id: str,
    model_id: str,
    simulator_version: str,
    sim_config: Mapping[str, Any],
    sim_config_path: Path,
    line_profile: Mapping[str, Any],
    train_rows: Sequence[Mapping[str, Any]],
    data_root: Path,
    device: torch.device,
    runtime: Mapping[str, Any],
    log_handle: Any,
) -> dict[str, Any]:
    seed = 20261103
    _seed_all(seed)
    model, model_config = _make_model(model_id)
    model.to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=1e-4, weight_decay=1e-4,
        fused=bool(runtime["fused_adamw"]),
    )
    sampler = PhysicsParameterSampler.from_mapping({**sim_config, "run_seed": seed})
    parent_sampler = CyclicParentSampler(train_rows, seed=seed)
    prefetcher = DynamicBatchPrefetcher(
        worker_count=2,
        worker_native_threads=1,
        prefetch_batches=2,
        start_method="spawn",
        data_root=data_root,
        peak_cache_name="peak_tables_v7_reflection",
        sampler_config={**sim_config, "run_seed": seed},
        quality_gate=False,
        quality_gate_config=sim_config.get("quality_gates", {}),
        simulation_config_hash=_sha256(sim_config_path),
        simulator_version=simulator_version,
        line_profile_config=line_profile,
        profile="train",
    )
    pending: dict[int, list[Mapping[str, Any]]] = {}
    steps = 10
    window = 2
    losses: list[dict[str, float]] = []
    prefetch_wait = 0.0
    start = time.monotonic()
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    try:
        def submit(step: int) -> None:
            batch = parent_sampler.next_batch(16)
            pending[step] = batch
            ids = [str(row["material_id"]) for row in batch]
            parameter_rows = build_parameter_batch(
                ids, sampler, profile="train", epoch=0, global_step=step,
                split="train",
            )
            prefetcher.submit(step, ids, parameter_rows)

        for step in range(min(window, steps)):
            submit(step)
        for step in range(steps):
            wait_started = time.monotonic()
            rendered = prefetcher.get(step)
            prefetch_wait += time.monotonic() - wait_started
            rows = pending.pop(step)
            if rendered.material_ids != tuple(str(row["material_id"]) for row in rows):
                raise RuntimeError("smoke prefetch changed material order")
            next_step = step + window
            if next_step < steps:
                submit(next_step)
            x1 = torch.from_numpy(np.asarray(rendered.first, dtype=np.float32))
            x2 = torch.from_numpy(np.asarray(rendered.second, dtype=np.float32))
            target = torch.tensor(
                [CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in rows],
                dtype=torch.long,
            )
            if device.type == "cuda":
                x1 = x1.pin_memory().to(device, non_blocking=True)
                x2 = x2.pin_memory().to(device, non_blocking=True)
                target = target.to(device, non_blocking=True)
            else:
                x1, x2, target = x1.to(device), x2.to(device), target.to(device)
            optimizer.zero_grad(set_to_none=True)
            with _autocast(device, runtime):
                result = run_training_step(
                    TrainingStepConfig(TrainingMode.DYNAMIC_JS, lambda_js=60.0),
                    model,
                    x1=x1,
                    x2=x2,
                    target=target,
                )
            result["total"].backward()
            grad_norm = 0.0
            finite_gradients = True
            for parameter in model.parameters():
                if parameter.grad is None:
                    continue
                finite_gradients &= bool(torch.isfinite(parameter.grad).all())
                grad_norm += float(parameter.grad.detach().float().norm().item())
            if not finite_gradients or not math.isfinite(grad_norm) or grad_norm <= 0:
                raise RuntimeError(f"invalid gradient in smoke run {config_id}")
            optimizer.step()
            losses.append(
                {
                    "classification": float(result["classification"].detach().float().cpu()),
                    "consistency": float(result["consistency"].detach().float().cpu()),
                    "total": float(result["total"].detach().float().cpu()),
                    "gradient_l1_norm_sum": grad_norm,
                }
            )
    finally:
        prefetcher.close()
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        peak_memory = int(torch.cuda.max_memory_allocated(device))
    else:
        peak_memory = None
    elapsed = time.monotonic() - start
    result = {
        "configuration": config_id,
        "model_class": model.__class__.__name__,
        "model_config": asdict(model_config),
        "parameter_count": int(model.parameter_count),
        "simulator_version": simulator_version,
        "optimizer": "AdamW",
        "objective": "CE + lambda_js * JS, lambda_js=60",
        "steps": steps,
        "batch_size_parents": 16,
        "parent_occurrences": steps * 16,
        "rendered_views": steps * 16 * 2,
        "elapsed_seconds_including_worker_startup": elapsed,
        "steady_steps_per_second_excluding_first_two_steps": 8.0 / max(
            elapsed - (elapsed / steps * 2.0), 1e-9
        ),
        "all_steps_per_second": steps / max(elapsed, 1e-9),
        "prefetch_wait_seconds": prefetch_wait,
        "peak_cuda_allocated_bytes": peak_memory,
        "final_step_losses_and_gradient_norm": losses[-1],
        "all_losses_finite": all(
            all(math.isfinite(value) for value in loss.values()) for loss in losses
        ),
    }
    _log(log_handle, "training_smoke_complete", **result)
    del model, optimizer
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return result


def run_smoke(data_root: Path, output_root: Path, device: torch.device) -> dict[str, Any]:
    protocol, sim_v9, sim_v10 = _load_config()
    data_bindings = _verify_data_bindings(data_root, protocol)
    all_rows = load_split_rows(data_root)
    split_index = validate_parent_split(all_rows)
    train_rows = split_index["train"]
    class_counts = {name: sum(row["crystal_system"] == name for row in train_rows) for name in CRYSTAL_SYSTEMS}
    selected_per_class: dict[str, Mapping[str, Any]] = {}
    for name in CRYSTAL_SYSTEMS:
        candidates = sorted(
            (row for row in train_rows if row["crystal_system"] == name),
            key=lambda row: str(row["material_id"]),
        )
        if not candidates:
            raise ValueError(f"missing training parent for crystal system {name}")
        selected_per_class[name] = candidates[0]

    smoke_log_path = REPORT_ROOT / "smoke.log.jsonl"
    smoke_log_path.parent.mkdir(parents=True, exist_ok=True)
    physical: dict[str, Any] = {}
    line_config = sim_v10["line_profile"]
    fine_axis = np.linspace(10.0, 90.0, 80001, dtype=np.float64)
    center = 30.0
    areas: dict[str, float] = {}
    profiles: dict[str, np.ndarray] = {}
    for label, width in (("narrow", 0.08), ("broad", 0.20)):
        profile = render_pseudo_voigt_caglioti_peaks(
            [center], [1.0], fine_axis, width, line_profile=line_config, normalize=False
        ).astype(np.float64)
        profiles[label] = profile
        areas[label] = float(np.trapezoid(profile, fine_axis))
    width_low = _measure_fwhm(
        fine_axis,
        render_pseudo_voigt_caglioti_peaks(
            [20.0], [1.0], fine_axis, 0.08, line_profile=line_config, normalize=False
        ),
    )
    width_high = _measure_fwhm(
        fine_axis,
        render_pseudo_voigt_caglioti_peaks(
            [80.0], [1.0], fine_axis, 0.08, line_profile=line_config, normalize=False
        ),
    )
    peak_center_observed = float(fine_axis[int(np.argmax(profiles["narrow"]))])
    area_relative_error = abs(areas["narrow"] - areas["broad"]) / max(areas["narrow"], 1e-12)
    physical = {
        "integrated_area_narrow": areas["narrow"],
        "integrated_area_broad": areas["broad"],
        "area_relative_difference": area_relative_error,
        "area_conservation_passed": area_relative_error < 0.02,
        "unshifted_peak_center_deg": peak_center_observed,
        "peak_center_preservation_passed": abs(peak_center_observed - center) <= 0.001,
        "measured_fwhm_at_2theta_20_deg": width_low,
        "measured_fwhm_at_2theta_80_deg": width_high,
        "instrument_angle_width_increase_passed": width_high > width_low,
        "profile_nonnegative_finite": all(
            np.isfinite(values).all() and bool(np.all(values >= 0)) for values in profiles.values()
        ),
        "line_profile_config": dict(line_config),
    }
    if not all(
        physical[key]
        for key in (
            "area_conservation_passed",
            "peak_center_preservation_passed",
            "instrument_angle_width_increase_passed",
            "profile_nonnegative_finite",
        )
    ):
        raise RuntimeError(f"V10 physical profile smoke failed: {physical}")

    runtime = _configure_runtime(device)
    simulation_results: dict[str, Any] = {}
    with smoke_log_path.open("w", encoding="utf-8") as log_handle:
        _log(
            log_handle,
            "smoke_started",
            date="2026-11-03",
            data_bindings=data_bindings,
            split_counts={name: len(rows) for name, rows in split_index.items()},
            train_class_counts=class_counts,
            gpu=runtime,
            physical_profile_checks=physical,
        )
        for name, row in selected_per_class.items():
            material_id = str(row["material_id"])
            peak_table = load_peak_table(
                data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{material_id}.npz"
            )
            before_positions = peak_table.positions.copy()
            before_intensities = peak_table.intensities.copy()
            params_sampler = PhysicsParameterSampler.from_mapping({**sim_v10, "run_seed": 20261103})
            sampler_factory = OnlineViewFactory(
                params_sampler,
                peak_table_simulator=_make_peak_table_simulator(
                    SIMULATOR_VERSIONS["v10"], line_config
                ),
            )
            first_pair = sampler_factory.make_pair_from_peaks(
                peak_table,
                material_id=material_id,
                split="train",
                epoch=0,
                global_step=1,
                profile="train",
            )
            replay_pair = sampler_factory.make_pair_from_peaks(
                peak_table,
                material_id=material_id,
                split="train",
                epoch=0,
                global_step=1,
                profile="train",
            )
            if not np.array_equal(first_pair.first.xrd, replay_pair.first.xrd) or not np.array_equal(
                first_pair.second.xrd, replay_pair.second.xrd
            ):
                raise RuntimeError(f"same-parent deterministic replay failed for {material_id}")
            if first_pair.first.rng_seed == first_pair.second.rng_seed:
                raise RuntimeError(f"same-parent views have colliding seeds for {material_id}")
            if np.array_equal(first_pair.first.xrd, first_pair.second.xrd):
                raise RuntimeError(f"paired views unexpectedly identical for {material_id}")
            for view in (first_pair.first, first_pair.second):
                if (
                    view.xrd.shape != (3501,)
                    or not np.isfinite(view.xrd).all()
                    or np.any(view.xrd < 0)
                    or not np.isclose(float(view.xrd.max()), 1.0, atol=1e-6)
                ):
                    raise RuntimeError(f"invalid simulated profile for {material_id}/{name}")
            if not np.array_equal(peak_table.positions, before_positions) or not np.array_equal(
                peak_table.intensities, before_intensities
            ):
                raise RuntimeError(f"simulator mutated the cached ideal peaks for {material_id}")
            simulation_results[name] = {
                "material_id_sha256_prefix": hashlib.sha256(material_id.encode()).hexdigest()[:12],
                "label_index": CRYSTAL_SYSTEMS.index(name),
                "view_seeds_distinct": True,
                "same_parent_pair_replay_exact": True,
                "views_are_distinct": True,
                "valid_normalized_spectra": True,
                "cached_peak_table_immutable": True,
            }
        _log(log_handle, "seven_system_pairing_smoke_passed", classes=simulation_results)

        configs = (
            ("legacy_resnet18gn_v9", "resnet18gn", SIMULATOR_VERSIONS["v9"], sim_v9, V9_SIM_PATH, {}),
            ("resnet18gn_v10", "resnet18gn", SIMULATOR_VERSIONS["v10"], sim_v10, V10_SIM_PATH, line_config),
            ("cnn11_v10", "cnn11", SIMULATOR_VERSIONS["v10"], sim_v10, V10_SIM_PATH, line_config),
        )
        with smoke_log_path.open("a", encoding="utf-8") as log_handle:
            training_smoke = [
                _smoke_training_path(
                    config_id=config_id,
                    model_id=model_id,
                    simulator_version=version,
                    sim_config=sim_config,
                    sim_config_path=sim_path,
                    line_profile=config_line,
                    train_rows=train_rows,
                    data_root=data_root,
                    device=device,
                    runtime=runtime,
                    log_handle=log_handle,
                )
                for config_id, model_id, version, sim_config, sim_path, config_line in configs
            ]
            output = {
                "schema_version": "simxrd-cnn11-pilot-smoke-v1",
                "status": "passed",
                "date": "2026-11-03",
                "data_bindings": data_bindings,
                "data_counts": {name: len(rows) for name, rows in split_index.items()},
                "training_rows_per_crystal_system": class_counts,
                "physical_profile_checks": physical,
                "same_parent_pair_checks": simulation_results,
                "training_path_smoke": training_smoke,
                "runtime": runtime,
                "raw_log": smoke_log_path.name,
                "conclusion": "All requested physical profile, label-preservation, deterministic same-parent pairing, finite-loss/gradient, GPU memory, and throughput smoke checks passed. Full training may proceed under the preregistered fixed budget.",
            }
            _write_json(REPORT_ROOT / "smoke.json", output)
            _log(log_handle, "smoke_passed", output_path="smoke.json")
    return output


def _save_checkpoint_atomic(path: Path, **kwargs: Any) -> None:
    temporary = path.with_name(path.stem + ".partial" + path.suffix)
    save_checkpoint(temporary, **kwargs)
    temporary.replace(path)


def train_model(
    *,
    model_id: str,
    config_id: str,
    simulator_version: str,
    sim_config: Mapping[str, Any],
    sim_config_path: Path,
    line_profile: Mapping[str, Any],
    data_root: Path,
    output_root: Path,
    device: torch.device,
) -> dict[str, Any]:
    protocol, _, _ = _load_config()
    _verify_data_bindings(data_root, protocol)
    split_rows = load_split_rows(data_root)
    split_index = validate_parent_split(split_rows)
    train_rows = split_index["train"]
    validation_rows = split_index["validation"]
    expected = protocol["training"]
    validation_seed = int(expected["validation_evaluation_seed"])
    panels, val_labels, val_ids, panel_index = _build_panels(
        data_root=data_root,
        output_root=output_root,
        split_rows=split_rows,
        split="validation",
        simulator_version=simulator_version,
        sim_config=sim_config,
        sim_config_path=sim_config_path,
        line_profile=line_profile,
        seed=validation_seed,
        profiles=VALIDATION_PROFILES,
    )
    steps = int(expected["optimizer_steps_per_new_model"])
    batch_size = int(expected["batch_size_parents"])
    validation_interval = steps // 8
    output_dir = output_root / config_id
    output_dir.mkdir(parents=True, exist_ok=True)
    all_results = []
    for seed in expected["seeds"]:
        seed = int(seed)
        run_dir = output_dir / f"seed_{seed}"
        if run_dir.exists() and any(run_dir.iterdir()):
            raise FileExistsError(f"run output already exists; refusing implicit rerun: {run_dir}")
        run_dir.mkdir(parents=True, exist_ok=True)
        log_path = REPORT_ROOT / "logs" / config_id / f"seed_{seed}.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log_handle:
            runtime = _configure_runtime(device)
            _seed_all(seed)
            model, model_config = _make_model(model_id)
            model.to(device)
            optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=float(expected["learning_rate"]),
                weight_decay=float(expected["weight_decay"]),
                fused=bool(runtime["fused_adamw"]),
            )
            sampler = PhysicsParameterSampler.from_mapping({**sim_config, "run_seed": seed})
            parent_sampler = CyclicParentSampler(train_rows, seed=seed)
            run_config = {
                "schema_version": "simxrd-cnn11-pilot-run-v1",
                "configuration_id": config_id,
                "model_id": model_id,
                "simulator_version": simulator_version,
                "simulator_config_sha256": _sha256(sim_config_path),
                "protocol_config_sha256": _sha256(PROTOCOL_PATH),
                "official_split_manifest_sha256": _sha256(data_root / "manifests" / "split_manifest.json"),
                "source_records_sha256": _sha256(data_root / "mp_processed" / "structure_records.jsonl"),
                "peak_cache_manifest_sha256": _sha256(data_root / "manifests" / "peak_cache_manifest.v7.reflection.csv"),
                "train_parent_ids_sha256": hashlib.sha256(
                    _canonical(sorted(str(row["parent_structure_id"]) for row in train_rows)).encode("utf-8")
                ).hexdigest().upper(),
                "validation_material_ids_sha256": hashlib.sha256(_canonical(val_ids).encode("utf-8")).hexdigest().upper(),
                "evaluation_panel_index_sha256": _sha256(output_root / "evaluation_cache" / f"validation_{simulator_version}_seed_{validation_seed}" / "panel_index.json"),
                "training_seed": seed,
                "train_parent_count": len(train_rows),
                "optimizer": "AdamW",
                "learning_rate": float(expected["learning_rate"]),
                "weight_decay": float(expected["weight_decay"]),
                "scheduler": "none",
                "objective": "Dynamic JS Consistency: mean CE over two same-parent views + lambda_js * JS divergence",
                "lambda_js": float(expected["lambda_js"]),
                "optimizer_steps": steps,
                "batch_size_parents": batch_size,
                "expected_parent_occurrences": steps * batch_size,
                "expected_views": steps * batch_size * 2,
                "validation_profiles": list(VALIDATION_PROFILES),
                "validation_seed": validation_seed,
                "validation_selection": expected["checkpoint_selection"],
                "runtime": runtime,
                "model_config": asdict(model_config),
                "parameter_count": int(model.parameter_count),
                "started_unix_time": time.time(),
            }
            _write_json(run_dir / "resolved_config.json", run_config)
            _log(log_handle, "training_started", **run_config)
            prefetcher = DynamicBatchPrefetcher(
                worker_count=8,
                worker_native_threads=1,
                prefetch_batches=8,
                start_method="spawn",
                data_root=data_root,
                peak_cache_name="peak_tables_v7_reflection",
                sampler_config={**sim_config, "run_seed": seed},
                quality_gate=False,
                quality_gate_config=sim_config.get("quality_gates", {}),
                simulation_config_hash=_sha256(sim_config_path),
                simulator_version=simulator_version,
                line_profile_config=line_profile,
                profile="train",
            )
            pending: dict[int, list[Mapping[str, Any]]] = {}
            best_score = (float("-inf"), float("-inf"), 0)
            validation_history: list[dict[str, Any]] = []
            parent_occurrences = 0
            rendered_views = 0
            prefetch_wait = 0.0
            start = time.monotonic()
            if device.type == "cuda":
                torch.cuda.reset_peak_memory_stats(device)
            try:
                def submit(step: int) -> None:
                    batch = parent_sampler.next_batch(batch_size)
                    pending[step] = batch
                    ids = [str(row["material_id"]) for row in batch]
                    parameter_rows = build_parameter_batch(
                        ids,
                        sampler,
                        profile="train",
                        epoch=0,
                        global_step=step,
                        split="train",
                    )
                    prefetcher.submit(step, ids, parameter_rows)

                for step in range(min(prefetcher.prefetch_batches, steps)):
                    submit(step)
                for step in range(steps):
                    wait_started = time.monotonic()
                    rendered = prefetcher.get(step)
                    prefetch_wait += time.monotonic() - wait_started
                    batch = pending.pop(step)
                    expected_ids = tuple(str(row["material_id"]) for row in batch)
                    if rendered.material_ids != expected_ids:
                        raise RuntimeError("prefetch result changed the frozen parent order")
                    next_step = step + prefetcher.prefetch_batches
                    if next_step < steps:
                        submit(next_step)
                    x1 = torch.from_numpy(np.asarray(rendered.first, dtype=np.float32))
                    x2 = torch.from_numpy(np.asarray(rendered.second, dtype=np.float32))
                    target = torch.tensor(
                        [CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in batch],
                        dtype=torch.long,
                    )
                    if device.type == "cuda":
                        x1 = x1.pin_memory().to(device, non_blocking=True)
                        x2 = x2.pin_memory().to(device, non_blocking=True)
                        target = target.to(device, non_blocking=True)
                    else:
                        x1, x2, target = x1.to(device), x2.to(device), target.to(device)
                    optimizer.zero_grad(set_to_none=True)
                    with _autocast(device, runtime):
                        result = run_training_step(
                            TrainingStepConfig(
                                TrainingMode.DYNAMIC_JS,
                                lambda_js=float(expected["lambda_js"]),
                            ),
                            model,
                            x1=x1,
                            x2=x2,
                            target=target,
                        )
                    result["total"].backward()
                    optimizer.step()
                    parent_occurrences += batch_size
                    rendered_views += batch_size * 2
                    global_step = step + 1
                    if global_step % 1000 == 0 or global_step == 1:
                        elapsed = time.monotonic() - start
                        _log(
                            log_handle,
                            "training_progress",
                            seed=seed,
                            step=global_step,
                            total_steps=steps,
                            ce=float(result["classification"].detach().float().cpu()),
                            js=float(result["consistency"].detach().float().cpu()),
                            total_loss=float(result["total"].detach().float().cpu()),
                            elapsed_seconds=elapsed,
                            steps_per_second=global_step / max(elapsed, 1e-9),
                            prefetch_wait_seconds=prefetch_wait,
                        )
                    if global_step % validation_interval == 0 or global_step == steps:
                        metrics: dict[str, Any] = {str(validation_seed): {}}
                        for profile in VALIDATION_PROFILES:
                            metrics[str(validation_seed)][profile] = _evaluate_one_panel(
                                model,
                                panels[profile],
                                val_labels,
                                device=device,
                                batch_size=256,
                            )
                        ood_score, inrange_score = _select_score(metrics, validation_seed)
                        selection_tuple = (ood_score, inrange_score, -global_step)
                        improved = selection_tuple > (best_score[0], best_score[1], -best_score[2])
                        if improved:
                            best_score = (ood_score, inrange_score, global_step)
                            _save_checkpoint_atomic(
                                run_dir / "best.ckpt",
                                model=model,
                                optimizers=[optimizer],
                                epoch=0,
                                global_step=global_step,
                                config=model_config,
                                data_manifest_hash=run_config["train_parent_ids_sha256"],
                                view_manifest_hash=run_config["simulator_config_sha256"],
                                seed=seed,
                                provenance={
                                    "configuration_id": config_id,
                                    "simulator_version": simulator_version,
                                    "protocol_config_sha256": run_config["protocol_config_sha256"],
                                    "official_split_manifest_sha256": run_config["official_split_manifest_sha256"],
                                    "source_records_sha256": run_config["source_records_sha256"],
                                },
                                extra_state={
                                    "training_mode": "dynamic_js",
                                    "lambda_js": float(expected["lambda_js"]),
                                    "best_validation_single_factor_ood_macro_f1": ood_score,
                                    "validation_in_range_macro_f1": inrange_score,
                                },
                            )
                        row = {
                            "step": global_step,
                            "ood_macro_f1": ood_score,
                            "in_range_macro_f1": inrange_score,
                            "best_updated": improved,
                            "metrics": metrics[str(validation_seed)],
                            "checkpoint_selection_score": [ood_score, inrange_score, -global_step],
                        }
                        validation_history.append(row)
                        _write_json(run_dir / "validation_history.json", validation_history)
                        _log(
                            log_handle,
                            "validation",
                            seed=seed,
                            step=global_step,
                            ood_macro_f1=ood_score,
                            in_range_macro_f1=inrange_score,
                            best_updated=improved,
                            elapsed_seconds=time.monotonic() - start,
                        )
            finally:
                prefetcher.close()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
                peak_memory = int(torch.cuda.max_memory_allocated(device))
            else:
                peak_memory = None
            elapsed = time.monotonic() - start
            checkpoint_path = run_dir / "best.ckpt"
            checkpoint_payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            result_payload = {
                **run_config,
                "status": "completed",
                "completed_unix_time": time.time(),
                "elapsed_seconds": elapsed,
                "optimizer_steps_per_second": steps / max(elapsed, 1e-9),
                "prefetch_wait_seconds": prefetch_wait,
                "peak_cuda_allocated_bytes": peak_memory,
                "parent_occurrences": parent_occurrences,
                "rendered_views": rendered_views,
                "selected_step": int(checkpoint_payload["global_step"]),
                "selected_validation_ood_macro_f1": best_score[0],
                "selected_validation_in_range_macro_f1": best_score[1],
                "checkpoint_sha256": _sha256(checkpoint_path),
                "validation_history_path": "validation_history.json",
                "raw_log_path": str(log_path.relative_to(REPORT_ROOT)).replace("\\", "/"),
            }
            _write_json(run_dir / "result.json", result_payload)
            _log(log_handle, "training_complete", **result_payload)
            all_results.append(result_payload)
            del model, optimizer
            if device.type == "cuda":
                torch.cuda.empty_cache()
    return {"configuration_id": config_id, "runs": all_results}


def freeze_model_selection(
    *,
    data_root: Path,
    output_root: Path,
    rruff_root: Path,
) -> dict[str, Any]:
    protocol, _, _ = _load_config()
    if not rruff_root.is_dir():
        raise FileNotFoundError(f"RRUFF frozen panel not found: {rruff_root}")
    rruff_manifest = rruff_root / "manifests" / "real_test_manifest.csv"
    rruff_preprocessing = rruff_root / "contracts" / "preprocessing_contract.json"
    rruff_lock = _read_json(rruff_root / "contracts" / "execution_lock.json")
    if not rruff_lock.get("selection_use_forbidden", False):
        raise ValueError("RRUFF-70 lock does not prohibit selection use")
    if rruff_lock.get("real_test_execution_authorization", False):
        raise ValueError("RRUFF-70 historical lock was unexpectedly changed")
    config_freeze = {
        "schema_version": "simxrd-pilot-model-selection-freeze-v1",
        "status": "models_selected_by_validation_and_frozen_before_test_access",
        "frozen_at_unix_time": time.time(),
        "protocol_config_sha256": _sha256(PROTOCOL_PATH),
        "v9_simulation_config_sha256": _sha256(V9_SIM_PATH),
        "v10_simulation_config_sha256": _sha256(V10_SIM_PATH),
        "data_bindings": _verify_data_bindings(data_root, protocol),
        "rruff_manifest_sha256": _sha256(rruff_manifest),
        "rruff_preprocessing_contract_sha256": _sha256(rruff_preprocessing),
        "rruff_test_selection_use_forbidden": True,
        "rruff_execution_authorization": "explicit_user_request_2026-11-03_to_report_accuracy_and_macro_f1_under_existing_protocol_after_checkpoint_freeze",
        "checkpoint_sets": {},
        "historical_frozen_test_role": "already-used-test-parent-split; supplementary post-main evaluation only",
    }
    model_entries = (
        ("legacy_resnet18gn_v9", "resnet18gn", "historical"),
        ("resnet18gn_v10", "resnet18gn", "new"),
        ("cnn11_v10", "cnn11", "new"),
    )
    for config_id, model_id, origin in model_entries:
        entries: dict[str, Any] = {}
        if origin == "historical":
            available_seeds = TRAINING_SEEDS
        else:
            config_dir = output_root / config_id
            available_seeds = tuple(
                sorted(
                    int(path.name.removeprefix("seed_"))
                    for path in config_dir.glob("seed_*")
                    if path.is_dir() and (path / "best.ckpt").is_file()
                )
            )
            if not available_seeds:
                raise FileNotFoundError(f"no selected checkpoints found for {config_id}: {config_dir}")
        config_statuses: set[str] = set()
        for seed in available_seeds:
            seed_dir = (
                PROJECT_ROOT
                / "outputs"
                / "simulated_test_checkpoints"
                / "checkpoints"
                / f"seed_{seed}_js_lambda_60"
                if origin == "historical"
                else output_root / config_id / f"seed_{seed}"
            )
            checkpoint_path = seed_dir / ("best.ckpt" if origin == "historical" else "best.ckpt")
            if not checkpoint_path.is_file():
                raise FileNotFoundError(f"required selected checkpoint is missing: {checkpoint_path}")
            payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            if int(payload.get("seed", -1)) != int(seed):
                raise ValueError(f"checkpoint seed does not match expected seed: {checkpoint_path}")
            model_state = payload.get("model")
            if not isinstance(model_state, Mapping) or any(
                torch.is_tensor(value) and not torch.isfinite(value).all()
                for value in model_state.values()
            ):
                raise ValueError(f"selected checkpoint contains non-finite model state: {checkpoint_path}")
            entry = {
                "checkpoint_sha256": _sha256(checkpoint_path),
                "selected_step": int(payload.get("global_step", -1)),
                "model_config": payload.get("config"),
                "model_id": model_id,
                "origin": origin,
                "checkpoint_model_state_finite": True,
            }
            if origin == "new":
                run_result_path = seed_dir / "result.json"
                run_result = _read_json(run_result_path)
                if run_result.get("status") not in {"completed", "failed_nonfinite"}:
                    raise ValueError(f"new training status is not evaluable for {config_id}/{seed}")
                if run_result.get("checkpoint_sha256") != entry["checkpoint_sha256"]:
                    raise ValueError(f"checkpoint hash in result record differs for {config_id}/{seed}")
                config_statuses.add(str(run_result["status"]))
                entry["training_status"] = str(run_result["status"])
                entry["validation_ood_macro_f1"] = float(run_result["selected_validation_ood_macro_f1"])
                entry["validation_in_range_macro_f1"] = float(run_result["selected_validation_in_range_macro_f1"])
                entry["full_training_elapsed_seconds"] = float(run_result["elapsed_seconds"])
                entry["peak_cuda_allocated_bytes"] = run_result.get("peak_cuda_allocated_bytes")
                entry["optimizer_steps_per_second"] = run_result.get("optimizer_steps_per_second")
            entries[str(seed)] = entry
        config_freeze["checkpoint_sets"][config_id] = entries
        config_freeze.setdefault("training_status_by_configuration", {})[config_id] = {
            "expected_training_seeds": list(TRAINING_SEEDS),
            "observed_checkpoint_seeds": [int(seed) for seed in available_seeds],
            "run_statuses": sorted(config_statuses) if origin == "new" else ["historical_frozen"],
        }

    freeze_path = REPORT_ROOT / "model_selection_freeze.json"
    if freeze_path.exists():
        raise FileExistsError(f"model-selection freeze already exists: {freeze_path}")
    _write_json(freeze_path, config_freeze)
    return config_freeze


def _load_frozen_model(
    *,
    config_id: str,
    model_id: str,
    seed: int,
    freeze: Mapping[str, Any],
    output_root: Path,
) -> tuple[torch.nn.Module, dict[str, Any]]:
    entry = freeze["checkpoint_sets"][config_id][str(seed)]
    checkpoint_path = (
        PROJECT_ROOT
        / "outputs"
        / "simulated_test_checkpoints"
        / "checkpoints"
        / f"seed_{seed}_js_lambda_60"
        / "best.ckpt"
        if entry["origin"] == "historical"
        else output_root / config_id / f"seed_{seed}" / "best.ckpt"
    )
    if _sha256(checkpoint_path) != entry["checkpoint_sha256"]:
        raise ValueError(f"frozen checkpoint hash changed: {checkpoint_path}")
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model, _ = _make_model(model_id)
    model.load_state_dict(payload["model"], strict=True)
    return model, payload


def _mean_sd(values: Sequence[float]) -> dict[str, float | None]:
    array = np.asarray(list(values), dtype=np.float64)
    if not array.size:
        raise ValueError("cannot aggregate an empty metric list")
    return {
        "mean": float(array.mean()),
        "sample_sd": float(array.std(ddof=1)) if array.size > 1 else None,
        "n": int(array.size),
    }


def _load_rruff_panel(rruff_root: Path, expected_manifest_sha256: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    manifest_path = rruff_root / "manifests" / "real_test_manifest.csv"
    preprocessing_path = rruff_root / "contracts" / "preprocessing_contract.json"
    if _sha256(manifest_path) != str(expected_manifest_sha256).upper():
        raise ValueError("RRUFF-70 manifest hash differs from the pre-evaluation freeze")
    preprocessing = _read_json(preprocessing_path)
    expected_contract_hash = _sha256(preprocessing_path)
    axis = np.linspace(
        float(preprocessing["two_theta_min"]),
        float(preprocessing["two_theta_max"]),
        int(preprocessing["input_length"]),
        dtype=np.float64,
    )
    if not np.isclose(axis[1] - axis[0], float(preprocessing["step"]), atol=1e-10):
        raise ValueError("RRUFF preprocessing axis does not match its frozen step")
    spectra_root = rruff_root
    processed: list[np.ndarray] = []
    labels: list[int] = []
    spectrum_hashes: list[str] = []
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 70:
        raise ValueError(f"RRUFF-70 manifest has {len(rows)} rows, expected 70")
    for row in rows:
        spectrum_path = spectra_root / row["spectrum_path"]
        spectrum_hash = _sha256(spectrum_path)
        if spectrum_hash != str(row["spectrum_sha256"]).upper():
            raise ValueError(f"RRUFF spectrum hash mismatch: {spectrum_path}")
        theta: list[float] = []
        intensity: list[float] = []
        with spectrum_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for point in csv.DictReader(handle):
                theta.append(float(point["two_theta"]))
                intensity.append(float(point["intensity"]))
        x = np.asarray(theta, dtype=np.float64)
        y = np.asarray(intensity, dtype=np.float64)
        if x.ndim != 1 or y.shape != x.shape or x.size < 2 or not np.all(np.diff(x) > 0):
            raise ValueError(f"invalid RRUFF spectrum axis: {spectrum_path}")
        view = np.interp(axis, x, y, left=float(preprocessing["out_of_range_fill"]), right=float(preprocessing["out_of_range_fill"]))
        maximum = float(view.max())
        if not math.isfinite(maximum) or maximum <= 0:
            raise ValueError(f"RRUFF spectrum has no positive maximum: {spectrum_path}")
        view = view / maximum
        if not np.isfinite(view).all() or np.any(view < 0):
            raise ValueError(f"RRUFF preprocessing produced invalid values: {spectrum_path}")
        processed.append(view.astype(np.float32))
        labels.append(CRYSTAL_SYSTEMS.index(str(row["crystal_system"])))
        spectrum_hashes.append(spectrum_hash)
    label_array = np.asarray(labels, dtype=np.int64)
    counts = {name: int(np.sum(label_array == index)) for index, name in enumerate(CRYSTAL_SYSTEMS)}
    if counts != {name: 10 for name in CRYSTAL_SYSTEMS}:
        raise ValueError(f"RRUFF-70 class counts differ from the frozen balanced contract: {counts}")
    return np.stack(processed), label_array, {
        "manifest_sha256": _sha256(manifest_path),
        "preprocessing_contract_sha256": expected_contract_hash,
        "sample_count": len(rows),
        "class_counts": counts,
        "spectrum_sha256_list_hash": hashlib.sha256(_canonical(spectrum_hashes).encode("utf-8")).hexdigest().upper(),
        "preprocessing": preprocessing,
    }


def evaluate_all(
    *,
    data_root: Path,
    output_root: Path,
    rruff_root: Path,
    device: torch.device,
) -> dict[str, Any]:
    protocol, sim_v9, sim_v10 = _load_config()
    freeze_path = REPORT_ROOT / "model_selection_freeze.json"
    if not freeze_path.is_file():
        raise FileNotFoundError("model-selection freeze must be created before test evaluation")
    freeze = _read_json(freeze_path)
    freeze_hash = _sha256(freeze_path)
    if freeze.get("status") != "models_selected_by_validation_and_frozen_before_test_access":
        raise ValueError("invalid model-selection freeze status")
    if freeze.get("protocol_config_sha256") != _sha256(PROTOCOL_PATH):
        raise ValueError("pilot protocol changed after model selection was frozen")
    _verify_data_bindings(data_root, protocol)

    # Build all common simulated panels only after every selected checkpoint is frozen.
    test_rows = load_split_rows(data_root)
    split_index = validate_parent_split(test_rows)
    panel_cache: dict[tuple[str, int], dict[str, np.ndarray]] = {}
    panel_labels: np.ndarray | None = None
    panel_ids: list[str] | None = None
    panel_bindings: dict[str, Any] = {}
    for key, sim_version, sim_config, sim_path, line_profile in (
        ("v9", SIMULATOR_VERSIONS["v9"], sim_v9, V9_SIM_PATH, {}),
        ("v10", SIMULATOR_VERSIONS["v10"], sim_v10, V10_SIM_PATH, sim_v10["line_profile"]),
    ):
        for eval_seed in EVAL_SEEDS:
            arrays, labels, ids, index = _build_panels(
                data_root=data_root,
                output_root=output_root,
                split_rows=test_rows,
                split="test",
                simulator_version=sim_version,
                sim_config=sim_config,
                sim_config_path=sim_path,
                line_profile=line_profile,
                seed=eval_seed,
                profiles=TRAIN_PROFILES,
            )
            panel_cache[(key, eval_seed)] = arrays
            if panel_labels is None:
                panel_labels = labels
                panel_ids = ids
            elif not np.array_equal(panel_labels, labels) or panel_ids != ids:
                raise ValueError("common test panels disagree on split labels or order")
            panel_bindings[f"{key}:{eval_seed}"] = {
                "panel_index_sha256": _sha256(
                    _panel_cache_path(output_root, "test", sim_version, eval_seed) / "panel_index.json"
                ),
                "profiles": list(TRAIN_PROFILES),
            }
    if panel_labels is None:
        raise RuntimeError("test panels were not built")

    model_definitions = (
        ("legacy_resnet18gn_v9", "resnet18gn"),
        ("resnet18gn_v10", "resnet18gn"),
        ("cnn11_v10", "cnn11"),
    )
    results: dict[str, Any] = {
        "schema_version": "simxrd-cnn11-pilot-results-v1",
        "status": "completed",
        "date": "2026-11-03",
        "post_main_supplement": True,
        "model_selection_freeze_sha256": freeze_hash,
        "protocol_config_sha256": _sha256(PROTOCOL_PATH),
        "data_bindings": _verify_data_bindings(data_root, protocol),
        "simulated_test": {
            "role": "supplementary post-main evaluation on the existing parent-disjoint Test parents; no checkpoint selection",
            "panel_bindings": panel_bindings,
            "evaluation_seeds": list(EVAL_SEEDS),
            "profiles": list(TRAIN_PROFILES),
            "configurations": {},
        },
        "rruff_real_pxrd_70": {
            "role": "frozen external measurement-domain test; evaluated after model-selection freeze; no selection or tuning use",
            "configurations": {},
        },
        "historical_frozen_context": {},
    }
    for config_id, model_id in model_definitions:
        config_seeds = tuple(
            int(seed) for seed in freeze["checkpoint_sets"][config_id].keys()
        )
        per_training_seed: dict[str, Any] = {}
        for seed in config_seeds:
            model, payload = _load_frozen_model(
                config_id=config_id,
                model_id=model_id,
                seed=seed,
                freeze=freeze,
                output_root=output_root,
            )
            model.to(device)
            model.eval()
            by_eval: dict[str, Any] = {}
            per_seed_profile_metrics: dict[str, list[dict[str, Any]]] = {
                f"{version}:{profile}": []
                for version in ("v9", "v10")
                for profile in TRAIN_PROFILES
            }
            for version in ("v9", "v10"):
                by_eval[version] = {}
                for eval_seed in EVAL_SEEDS:
                    by_eval[version][str(eval_seed)] = {}
                    for profile in TRAIN_PROFILES:
                        metrics = _evaluate_one_panel(
                            model,
                            panel_cache[(version, eval_seed)][profile],
                            panel_labels,
                            device=device,
                            batch_size=256,
                        )
                        by_eval[version][str(eval_seed)][profile] = metrics
                        per_seed_profile_metrics[f"{version}:{profile}"].append(metrics)
            summary: dict[str, Any] = {}
            for version in ("v9", "v10"):
                all_metrics = [
                    by_eval[version][str(eval_seed)][profile]
                    for eval_seed in EVAL_SEEDS
                    for profile in TRAIN_PROFILES
                ]
                summary[version] = {
                    "mean_single_factor_ood_macro_f1": float(np.mean([m["macro_f1"] for m in all_metrics])),
                    "mean_single_factor_ood_accuracy": float(np.mean([m["accuracy"] for m in all_metrics])),
                    "by_profile_mean_across_evaluation_seeds": {
                        profile: {
                            "accuracy": float(np.mean([by_eval[version][str(seed)][profile]["accuracy"] for seed in EVAL_SEEDS])),
                            "macro_f1": float(np.mean([by_eval[version][str(seed)][profile]["macro_f1"] for seed in EVAL_SEEDS])),
                        }
                        for profile in TRAIN_PROFILES
                    },
                }
            per_training_seed[str(seed)] = {
                "checkpoint_sha256": freeze["checkpoint_sets"][config_id][str(seed)]["checkpoint_sha256"],
                "selected_step": int(payload["global_step"]),
                "validation_ood_macro_f1": freeze["checkpoint_sets"][config_id][str(seed)].get("validation_ood_macro_f1"),
                "full_training_elapsed_seconds": freeze["checkpoint_sets"][config_id][str(seed)].get("full_training_elapsed_seconds"),
                "peak_cuda_allocated_bytes": freeze["checkpoint_sets"][config_id][str(seed)].get("peak_cuda_allocated_bytes"),
                "optimizer_steps_per_second": freeze["checkpoint_sets"][config_id][str(seed)].get("optimizer_steps_per_second"),
                "training_status": freeze["checkpoint_sets"][config_id][str(seed)].get("training_status", "historical_frozen"),
                "simulated_test_by_evaluation_seed_and_profile": by_eval,
                "simulated_test_summary": summary,
            }
            per_training_seed[str(seed)]["_profile_metrics_for_aggregate"] = {
                key: [{"accuracy": float(m["accuracy"]), "macro_f1": float(m["macro_f1"])} for m in value]
                for key, value in per_seed_profile_metrics.items()
            }
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()

        simulation_summary: dict[str, Any] = {}
        for version in ("v9", "v10"):
            means_by_seed = [per_training_seed[str(seed)]["simulated_test_summary"][version] for seed in config_seeds]
            simulation_summary[version] = {
                "mean_single_factor_ood_macro_f1_across_training_seeds": _mean_sd(
                    [row["mean_single_factor_ood_macro_f1"] for row in means_by_seed]
                ),
                "mean_single_factor_ood_accuracy_across_training_seeds": _mean_sd(
                    [row["mean_single_factor_ood_accuracy"] for row in means_by_seed]
                ),
                "per_profile_across_training_seeds": {
                    profile: {
                        metric: _mean_sd(
                            [
                                per_training_seed[str(seed)]["simulated_test_summary"][version]["by_profile_mean_across_evaluation_seeds"][profile][metric]
                                for seed in config_seeds
                            ]
                        )
                        for metric in ("accuracy", "macro_f1")
                    }
                    for profile in TRAIN_PROFILES
                },
            }
        results["simulated_test"]["configurations"][config_id] = {
            "model_id": model_id,
            "training_seeds": list(config_seeds),
            "expected_training_seed_count": len(TRAINING_SEEDS),
            "training_status": freeze["training_status_by_configuration"][config_id],
            "per_training_seed": per_training_seed,
            "aggregate_across_training_seeds": simulation_summary,
        }

    # The user-authorized external panel is read only after all models and hashes are frozen.
    rruff_x, rruff_y, rruff_metadata = _load_rruff_panel(
        rruff_root, freeze["rruff_manifest_sha256"]
    )
    for config_id, model_id in model_definitions:
        config_seeds = tuple(
            int(seed) for seed in freeze["checkpoint_sets"][config_id].keys()
        )
        per_seed: dict[str, Any] = {}
        for seed in config_seeds:
            model, payload = _load_frozen_model(
                config_id=config_id,
                model_id=model_id,
                seed=seed,
                freeze=freeze,
                output_root=output_root,
            )
            model.to(device)
            metrics = _evaluate_one_panel(model, rruff_x, rruff_y, device=device, batch_size=70)
            per_seed[str(seed)] = {
                "checkpoint_sha256": freeze["checkpoint_sets"][config_id][str(seed)]["checkpoint_sha256"],
                "selected_step": int(payload["global_step"]),
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "per_class_f1_by_name": metrics["per_class_f1_by_name"],
                "per_class_recall_by_name": {
                    name: float(score) for name, score in zip(CRYSTAL_SYSTEMS, metrics["per_class_recall"], strict=True)
                },
                "confusion_matrix": metrics["confusion_matrix"],
                "ece": metrics["ece"],
            }
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
        results["rruff_real_pxrd_70"]["configurations"][config_id] = {
            "training_seeds": list(config_seeds),
            "expected_training_seed_count": len(TRAINING_SEEDS),
            "training_status": freeze["training_status_by_configuration"][config_id],
            "per_training_seed": per_seed,
            "aggregate_across_training_seeds": {
                metric: _mean_sd([per_seed[str(seed)][metric] for seed in config_seeds])
                for metric in ("accuracy", "macro_f1", "ece")
            },
        }
    results["rruff_real_pxrd_70"]["panel"] = rruff_metadata

    completeness = freeze["training_status_by_configuration"]
    results["training_completeness"] = completeness
    fully_replicated = all(
        len(item["observed_checkpoint_seeds"]) == len(item["expected_training_seeds"])
        and all(status in {"completed", "historical_frozen"} for status in item["run_statuses"])
        for item in completeness.values()
    )
    results["status"] = (
        "evaluation_completed" if fully_replicated else "evaluation_completed_with_incomplete_training"
    )

    historical = _read_json(PROJECT_ROOT / "reports" / "simulated_test_results.json")
    results["historical_frozen_context"] = {
        "source": "xrd_robustness/reports/simulated_test_results.json",
        "scope": "original five-seed V9 ResNet-18-GN Dynamic JS result; reported separately and unchanged",
        "training_seed_count": int(historical["paired_seed_count"]),
        "legacy_v9_js_mean_single_factor_ood_macro_f1": historical["methods"]["js_consistency"]["mean_single_factor_ood_macro_f1"],
        "legacy_v9_js_mean_single_factor_ood_accuracy": historical["methods"]["js_consistency"]["mean_single_factor_ood_accuracy"],
    }
    _write_json(REPORT_ROOT / "results.json", results)
    return results


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("smoke", "train_resnet", "train_cnn11", "freeze", "evaluate"),
        required=True,
    )
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--rruff-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "real_xrd" / "rruff70",
    )
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)
    data_root = args.data_root.resolve()
    output_root = args.output_root.resolve()
    device = _device(args.device)
    output_root.mkdir(parents=True, exist_ok=True)
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    protocol, _, sim_v10 = _load_config()
    if args.phase == "smoke":
        result = run_smoke(data_root, output_root, device)
    elif args.phase in {"train_resnet", "train_cnn11"}:
        if not (REPORT_ROOT / "smoke.json").is_file():
            raise RuntimeError("run and pass the explicit smoke phase before full training")
        smoke = _read_json(REPORT_ROOT / "smoke.json")
        if smoke.get("status") != "passed":
            raise RuntimeError("full training is blocked because the smoke phase did not pass")
        if args.phase == "train_resnet":
            model_id, config_id = "resnet18gn", "resnet18gn_v10"
        else:
            model_id, config_id = "cnn11", "cnn11_v10"
        result = train_model(
            model_id=model_id,
            config_id=config_id,
            simulator_version=SIMULATOR_VERSIONS["v10"],
            sim_config=sim_v10,
            sim_config_path=V10_SIM_PATH,
            line_profile=sim_v10["line_profile"],
            data_root=data_root,
            output_root=output_root,
            device=device,
        )
        _write_json(REPORT_ROOT / f"{config_id}_training_results.json", result)
    elif args.phase == "freeze":
        result = freeze_model_selection(
            data_root=data_root,
            output_root=output_root,
            rruff_root=args.rruff_root.resolve(),
        )
    else:
        result = evaluate_all(
            data_root=data_root,
            output_root=output_root,
            rruff_root=args.rruff_root.resolve(),
            device=device,
        )
    print(json.dumps({"phase": args.phase, "status": "completed", "result_keys": list(result)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


