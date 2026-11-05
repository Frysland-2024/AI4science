#!/usr/bin/env python
"""Run the ordered, validation-only ResNet + Dynamic JS search for Issue #55."""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.experiment import config_hash, save_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory, TrainingMode  # noqa: E402
from xrd_robustness.parent_budget_efficiency import CyclicParentSampler  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.simulator_v11 import make_peak_table_simulator  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.objectives import TrainingStepConfig, run_training_step  # noqa: E402
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher  # noqa: E402
from xrd_robustness.view_manifest import build_parameter_batch  # noqa: E402


OOD_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _material_id_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = "".join(
        f"{material_id}\n"
        for material_id in sorted(str(row["material_id"]) for row in rows)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _git_revision(repository_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _write_json(path: Path, value: Any, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(path)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    partial.replace(path)


def _log(handle: Any, event: str, **payload: Any) -> None:
    encoded = json.dumps({"event": event, **payload}, sort_keys=True, ensure_ascii=False)
    handle.write(encoded + "\n")
    handle.flush()
    print(encoded, flush=True)


def _append_event(path: Path, event: str, **payload: Any) -> None:
    encoded = json.dumps({"event": event, **payload}, sort_keys=True, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded + "\n")
        handle.flush()
    print(encoded, flush=True)


def _verify_sources(
    data_root: Path,
    contract: Mapping[str, Any],
    *,
    progress_callback: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    split_path = data_root / str(contract["split_manifest"])
    source_path = data_root / str(contract["source_records"])
    cache_manifest_path = data_root / str(contract["peak_cache_manifest"])
    expected_hashes = {
        "split_manifest_sha256": (split_path, str(contract["split_manifest_sha256"])),
        "source_records_sha256": (source_path, str(contract["source_records_sha256"])),
        "peak_cache_manifest_sha256": (
            cache_manifest_path,
            str(contract["peak_cache_manifest_sha256"]),
        ),
    }
    hashes: dict[str, str] = {}
    for name, (path, expected) in expected_hashes.items():
        if not path.is_file():
            raise FileNotFoundError(path)
        actual = _sha256(path)
        hashes[name] = actual
        if actual != expected.upper():
            raise ValueError(f"{name} mismatch: {actual} != {expected}")

    split_payload = json.loads(split_path.read_text(encoding="utf-8"))
    split_rows = split_payload.get("records")
    if not isinstance(split_rows, list):
        raise ValueError("frozen split manifest must contain a records array")
    expected_counts = {str(k): int(v) for k, v in contract["expected_counts"].items()}
    counts = {name: 0 for name in expected_counts}
    wanted: dict[str, dict[str, str]] = {}
    for row in split_rows:
        split = str(row["split"])
        if split not in counts:
            raise ValueError(f"unexpected split name: {split}")
        counts[split] += 1
        if split in {"train", "validation"}:
            material_id = str(row["material_id"])
            if material_id in wanted:
                raise ValueError(f"duplicate material in frozen split: {material_id}")
            wanted[material_id] = {
                "split": split,
                "crystal_system": str(row["crystal_system"]),
                "parent_structure_id": str(row["parent_structure_id"]),
            }
    if counts != expected_counts:
        raise ValueError(f"frozen split counts mismatch: {counts} != {expected_counts}")
    expected_tv = expected_counts["train"] + expected_counts["validation"]
    if len(wanted) != expected_tv:
        raise ValueError(f"train/validation parent count mismatch: {len(wanted)} != {expected_tv}")

    cache_manifest: dict[str, dict[str, str]] = {}
    with cache_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            material_id = str(row["material_id"])
            if material_id in wanted:
                if material_id in cache_manifest:
                    raise ValueError(f"duplicate peak-cache manifest row: {material_id}")
                cache_manifest[material_id] = {
                    "sha256": str(row["sha256"]).upper(),
                    "file": str(row["file"]),
                    "structure_fingerprint": str(row["structure_fingerprint"]),
                }
    if len(cache_manifest) != expected_tv:
        raise ValueError(f"train/validation peak-cache rows missing: {len(cache_manifest)} != {expected_tv}")

    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    records: list[dict[str, Any]] = []
    for record_index, material_id in enumerate(sorted(wanted), start=1):
        split_row = wanted[material_id]
        try:
            label = CRYSTAL_SYSTEMS.index(split_row["crystal_system"])
        except ValueError as error:
            raise ValueError(f"unknown crystal system for {material_id}") from error
        peak_path = cache_root / f"{material_id}.npz"
        if not peak_path.is_file():
            raise FileNotFoundError(peak_path)
        cache_row = cache_manifest[material_id]
        if cache_row["structure_fingerprint"] != split_row["parent_structure_id"]:
            raise ValueError(f"peak-cache/split fingerprint mismatch for {material_id}")
        expected_cache_file = Path("mp_processed") / "peak_tables_v7_reflection" / f"{material_id}.npz"
        declared_cache_file = Path(cache_row["file"])
        if (
            declared_cache_file.is_absolute()
            or ".." in declared_cache_file.parts
            or tuple(declared_cache_file.parts[-3:]) != tuple(expected_cache_file.parts)
        ):
            raise ValueError(f"peak-cache manifest path mismatch for {material_id}")
        actual_peak_hash = _sha256(peak_path)
        if actual_peak_hash != cache_row["sha256"]:
            raise ValueError(f"peak-cache hash mismatch for {material_id}")
        records.append(
            {
                "material_id": material_id,
                "label": label,
                "crystal_system": split_row["crystal_system"],
                "split": split_row["split"],
                "parent_structure_id": split_row["parent_structure_id"],
                "peak_table_path": str(peak_path.resolve()),
                "peak_table_sha256": actual_peak_hash,
            }
        )
        if progress_callback is not None and record_index % 1000 == 0:
            progress_callback(
                "peak_cache_verification_progress",
                checked=record_index,
                total=expected_tv,
            )
    if progress_callback is not None:
        progress_callback(
            "peak_cache_verification_completed",
            checked=len(records),
            train_count=expected_counts["train"],
            validation_count=expected_counts["validation"],
        )
    if any(row["split"] == "test" for row in records):
        raise AssertionError("test rows entered the training/validation manifest")
    return records, hashes


def _prepare_records(
    data_root: Path,
    output_dir: Path,
    protocol: Mapping[str, Any],
    *,
    progress_callback: Any | None = None,
) -> tuple[list[dict[str, Any]], str, dict[str, str]]:
    records, source_hashes = _verify_sources(
        data_root, protocol["data_contract"], progress_callback=progress_callback
    )
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = data_dir / "frozen_train_validation_peak_tables.jsonl"
    encoded = "".join(
        json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in records
    )
    if jsonl_path.exists():
        if jsonl_path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError(f"refusing to replace a different derived manifest: {jsonl_path}")
    else:
        jsonl_path.write_text(encoded, encoding="utf-8")
    counts = {name: sum(row["split"] == name for row in records) for name in ("train", "validation")}
    train_rows = [row for row in records if row["split"] == "train"]
    validation_rows = [row for row in records if row["split"] == "validation"]
    manifest = {
        "schema_version": "issue55-train-validation-peak-table-manifest-v1",
        "source_hashes": source_hashes,
        "derived_jsonl_sha256": _sha256(jsonl_path),
        "counts": counts,
        "train_material_ids_sha256": _material_id_hash(train_rows),
        "validation_material_ids_sha256": _material_id_hash(validation_rows),
        "split_authority": str(protocol["data_contract"]["split_manifest"]),
        "crystal_system_order": list(CRYSTAL_SYSTEMS),
        "test_rows_included": False,
    }
    manifest_path = data_dir / "frozen_train_validation_manifest.json"
    _write_json(manifest_path, manifest, overwrite=False) if not manifest_path.exists() else None
    if manifest_path.exists() and json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
        raise RuntimeError("derived train/validation manifest provenance differs")
    return records, _sha256(jsonl_path), source_hashes


def _configure_runtime(device: torch.device, runtime_config: Mapping[str, Any]) -> dict[str, Any]:
    worker_threads = int(runtime_config["worker_native_threads"])
    for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "BLIS_NUM_THREADS",
    ):
        os.environ[name] = str(worker_threads)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.set_num_threads(int(runtime_config["main_cpu_threads"]))
    torch.set_num_interop_threads(int(runtime_config["main_cpu_interop_threads"]))
    torch.use_deterministic_algorithms(True)
    if device.type == "cuda":
        torch.set_float32_matmul_precision("high")
        torch.backends.cuda.matmul.allow_tf32 = bool(runtime_config["tf32"])
        torch.backends.cudnn.allow_tf32 = bool(runtime_config["tf32"])
        torch.backends.cudnn.deterministic = bool(runtime_config["cudnn_deterministic"])
        torch.backends.cudnn.benchmark = bool(runtime_config["cudnn_benchmark"])
    bf16 = bool(device.type == "cuda" and torch.cuda.is_bf16_supported())
    return {
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "gpu_total_memory_bytes": int(torch.cuda.get_device_properties(device).total_memory)
        if device.type == "cuda"
        else None,
        "amp_dtype": "bfloat16" if bf16 else "float32",
        "deterministic_algorithms": True,
        "cudnn_deterministic": bool(runtime_config["cudnn_deterministic"]),
        "cudnn_benchmark": bool(runtime_config["cudnn_benchmark"]),
        "tf32": bool(runtime_config["tf32"]),
        "fused_adamw": device.type == "cuda",
        "worker_count": int(runtime_config["prefetch_worker_count"]),
        "prefetch_batches": int(runtime_config["prefetch_batches"]),
    }


def _autocast(device: torch.device, runtime: Mapping[str, Any]):
    if device.type == "cuda" and runtime["amp_dtype"] == "bfloat16":
        return torch.autocast(device_type="cuda", dtype=torch.bfloat16)
    from contextlib import nullcontext

    return nullcontext()


def _resolve_device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    return device


def _model_config(candidate: Mapping[str, Any]) -> ML4PXRDResNet1DConfig:
    return ML4PXRDResNet1DConfig(
        model_id="18",
        input_length=3501,
        num_classes=7,
        group_norm_groups=32,
        group_norm_eps=1e-3,
        square_kernel_size_and_stride=True,
        add_additional_dense_layer=True,
        dense_width=256,
        embed_dim=256,
        stage_downsample_stride=int(candidate["stage_downsample_stride"]),
        residual_kernel_size=int(candidate["residual_kernel_size"]),
        head_mode=str(candidate["head_mode"]),
    )


def _profile_model(model: torch.nn.Module, device: torch.device) -> dict[str, Any]:
    macs = 0
    hooks = []

    def conv_cost(module: torch.nn.Conv1d, _inputs: tuple[Any, ...], output: torch.Tensor) -> None:
        nonlocal macs
        macs += int(output.numel()) * (module.in_channels // module.groups) * module.kernel_size[0]

    def linear_cost(module: torch.nn.Linear, _inputs: tuple[Any, ...], output: torch.Tensor) -> None:
        nonlocal macs
        rows = int(output.numel()) // module.out_features
        macs += rows * module.in_features * module.out_features

    for module in model.modules():
        if isinstance(module, torch.nn.Conv1d):
            hooks.append(module.register_forward_hook(conv_cost))
        elif isinstance(module, torch.nn.Linear):
            hooks.append(module.register_forward_hook(linear_cost))
    model.eval()
    with torch.inference_mode():
        model(torch.zeros(1, 3501, device=device))
    for hook in hooks:
        hook.remove()
    params = sum(parameter.numel() for parameter in model.parameters())
    return {"parameters": int(params), "macs_per_spectrum": int(macs), "flops_per_spectrum": int(2 * macs)}


def _load_val_peaks(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        str(row["material_id"]): load_peak_table(str(row["peak_table_path"]))
        for row in records
        if str(row["split"]) == "validation"
    }


def _make_validation_panels(
    records: Sequence[Mapping[str, Any]],
    peaks: Mapping[str, Any],
    simulation_config: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    *,
    progress_callback: Any | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, int], dict[str, str]]:
    seed = int(evaluation["validation_seed"])
    sampler = PhysicsParameterSampler.from_mapping({**simulation_config, "run_seed": seed})
    renderer = make_peak_table_simulator(
        str(simulation_config["simulator_version"]),
        simulation_config.get("line_profile", {}),
    )
    factory = OnlineViewFactory(sampler, peak_table_simulator=renderer)
    validation_rows = [row for row in records if str(row["split"]) == "validation"]
    profiles = (*tuple(evaluation["validation_profiles"]), str(evaluation["tie_break_profile"]))
    panels: dict[str, np.ndarray] = {}
    labels = {str(row["material_id"]): int(row["label"]) for row in validation_rows}
    hashes: dict[str, str] = {}
    for profile_index, profile in enumerate(profiles, start=1):
        if progress_callback is not None:
            progress_callback(
                "validation_panel_started",
                profile=profile,
                profile_index=profile_index,
                profile_count=len(profiles),
                validation_parents=len(validation_rows),
            )
        values = np.empty((len(validation_rows), 3501), dtype=np.float32)
        for index, row in enumerate(validation_rows):
            material_id = str(row["material_id"])
            pair = factory.make_pair_from_peaks(
                peaks[material_id],
                material_id=material_id,
                split="validation",
                epoch=0,
                global_step=0,
                profile=profile,
            )
            values[index] = pair.first.xrd
        panels[profile] = values
        hashes[profile] = hashlib.sha256(values.tobytes(order="C")).hexdigest().upper()
        if progress_callback is not None:
            progress_callback(
                "validation_panel_completed",
                profile=profile,
                panel_sha256=hashes[profile],
            )
    return panels, labels, hashes


def _score_panels(
    model: torch.nn.Module,
    panels: Mapping[str, np.ndarray],
    labels_by_id: Mapping[str, int],
    validation_rows: Sequence[Mapping[str, Any]],
    *,
    device: torch.device,
    runtime: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    labels = np.asarray([int(row["label"]) for row in validation_rows], dtype=np.int64)
    output: dict[str, dict[str, Any]] = {}
    model.eval()
    for profile, spectra in panels.items():
        probabilities: list[np.ndarray] = []
        for start in range(0, len(spectra), 256):
            batch = torch.from_numpy(spectra[start : start + 256]).to(device)
            with torch.inference_mode(), _autocast(device, runtime):
                logits = model(batch)["logits"]
                probs = torch.softmax(logits.float(), dim=-1)
            probabilities.append(probs.cpu().numpy())
        values = np.concatenate(probabilities, axis=0)
        metrics = classification_metrics(
            labels.tolist(),
            values.argmax(axis=1).tolist(),
            probabilities=values,
            num_classes=len(CRYSTAL_SYSTEMS),
        )
        output[profile] = metrics
    if len(labels_by_id) != len(validation_rows):
        raise AssertionError("validation label manifest changed during scoring")
    return output


def _selection_key(
    metrics: Mapping[str, Mapping[str, Any]],
    profiles: Sequence[str],
    tie_profile: str,
    step: int,
    candidate_order: int,
) -> tuple[float, float, int, int]:
    ood_mean = float(np.mean([float(metrics[name]["macro_f1"]) for name in profiles]))
    in_range = float(metrics[tie_profile]["macro_f1"])
    return (ood_mean, in_range, -int(step), -int(candidate_order))


def _validation_batches(
    model: torch.nn.Module,
    panels: Mapping[str, np.ndarray],
    labels_by_id: Mapping[str, int],
    validation_rows: Sequence[Mapping[str, Any]],
    *,
    device: torch.device,
    runtime: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    return _score_panels(
        model,
        panels,
        labels_by_id,
        validation_rows,
        device=device,
        runtime=runtime,
    )


def _trial_config(
    *,
    trial_id: str,
    phase: str,
    candidate_order: int,
    model_config: ML4PXRDResNet1DConfig,
    seed: int,
    steps: int,
    batch_size: int,
    learning_rate: float,
    weight_decay: float,
    lambda_js: float,
    scheduler_name: str,
    protocol: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "phase": phase,
        "candidate_order": candidate_order,
        "training_mode": "dynamic_js",
        "seed": seed,
        "optimizer": "AdamW",
        "optimizer_steps": steps,
        "batch_size_parents": batch_size,
        "parent_occurrences": int(steps * batch_size),
        "generated_views": int(steps * batch_size * 2),
        "learning_rate": float(learning_rate),
        "weight_decay": float(weight_decay),
        "lambda_js": float(lambda_js),
        "scheduler": scheduler_name,
        "model_config": model_config.__dict__,
        "protocol_sha256": config_hash(protocol).upper(),
        "provenance": dict(provenance),
    }


def _run_trial(
    *,
    output_dir: Path,
    trial_config: Mapping[str, Any],
    model_config: ML4PXRDResNet1DConfig,
    train_rows: Sequence[Mapping[str, Any]],
    validation_rows: Sequence[Mapping[str, Any]],
    panels: Mapping[str, np.ndarray],
    panel_hashes: Mapping[str, str],
    labels_by_id: Mapping[str, int],
    simulation_config: Mapping[str, Any],
    data_root: Path,
    protocol: Mapping[str, Any],
    runtime: Mapping[str, Any],
    device: torch.device,
    validation_manifest_hash: str,
    candidate_order: int,
) -> dict[str, Any]:
    trial_id = str(trial_config["trial_id"])
    run_dir = output_dir / "trials" / trial_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing trial directory: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "resolved_config.json", dict(trial_config), overwrite=False)
    event_path = run_dir / "events.jsonl"
    with event_path.open("a", encoding="utf-8") as log:
        _log(log, "trial_started", trial_id=trial_id, config=dict(trial_config), device=str(device))
        seed = int(trial_config["seed"])
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        model = ML4PXRDResNet1D(model_config).to(device)
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        model_profile = _profile_model(model, device)
        model.train()
        fused = bool(device.type == "cuda")
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(trial_config["learning_rate"]),
            weight_decay=float(trial_config["weight_decay"]),
            fused=fused,
        )
        total_steps = int(trial_config["optimizer_steps"])
        scheduler_name = str(trial_config["scheduler"])
        if scheduler_name == "cosine_5pct_floor":
            scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                optimizer,
                T_max=total_steps,
                eta_min=float(trial_config["learning_rate"]) * 0.05,
            )
            schedulers: list[Any] = [scheduler]
        elif scheduler_name == "none":
            scheduler = None
            schedulers = []
        else:
            raise ValueError(f"unsupported scheduler: {scheduler_name}")
        step_config = TrainingStepConfig(
            mode=TrainingMode.DYNAMIC_JS,
            lambda_js=float(trial_config["lambda_js"]),
        )
        train_sampler = PhysicsParameterSampler.from_mapping(
            {**simulation_config, "run_seed": seed}
        )
        batch_sampler = CyclicParentSampler(train_rows, seed=seed)
        prefetcher = DynamicBatchPrefetcher(
            worker_count=int(runtime["prefetch_worker_count"]),
            worker_native_threads=int(runtime["worker_native_threads"]),
            prefetch_batches=int(runtime["prefetch_batches"]),
            start_method=str(runtime["multiprocessing_start_method"]),
            data_root=data_root,
            peak_cache_name="peak_tables_v7_reflection",
            sampler_config={**simulation_config, "run_seed": seed},
            quality_gate=False,
            quality_gate_config={},
            simulation_config_hash=config_hash(simulation_config),
            profile=str(protocol["simulation"]["training_profile"]),
            simulator_version=str(simulation_config["simulator_version"]),
            line_profile_config=simulation_config.get("line_profile", {}),
        )
        pending: dict[int, tuple[list[dict[str, Any]], list[Any]]] = {}
        next_submit = 1
        first_step = 1
        train_started = time.perf_counter()
        total_loss = total_ce = total_js = 0.0
        observed_structures = 0
        prefetch_wait_seconds = 0.0
        selected_key: tuple[float, float, int, int] | None = None
        selected_metrics: dict[str, Any] | None = None
        selected_step = 0
        validation_interval = int(protocol["training"]["validation_interval_steps"])
        ood_profiles = tuple(protocol["simulation"]["validation_profiles"])
        tie_profile = str(protocol["simulation"]["tie_break_profile"])
        peak_allocated = 0
        try:
            while first_step <= total_steps:
                while next_submit <= total_steps and prefetcher.in_flight_batches < int(runtime["prefetch_batches"]):
                    batch_rows = batch_sampler.next_batch(int(trial_config["batch_size_parents"]))
                    material_ids = [str(row["material_id"]) for row in batch_rows]
                    parameter_rows = build_parameter_batch(
                        material_ids,
                        train_sampler,
                        profile=str(protocol["simulation"]["training_profile"]),
                        epoch=0,
                        global_step=next_submit - 1,
                        split="train",
                    )
                    prefetcher.submit(next_submit, material_ids, parameter_rows)
                    pending[next_submit] = (batch_rows, parameter_rows)
                    next_submit += 1

                wait_started = time.perf_counter()
                rendered = prefetcher.get(first_step)
                prefetch_wait_seconds += time.perf_counter() - wait_started
                batch_rows, _ = pending.pop(first_step)
                x1 = torch.from_numpy(rendered.first).to(device)
                x2 = torch.from_numpy(rendered.second).to(device)
                target = torch.tensor(
                    [int(row["label"]) for row in batch_rows],
                    dtype=torch.long,
                    device=device,
                )
                optimizer.zero_grad(set_to_none=True)
                with _autocast(device, runtime):
                    losses = run_training_step(
                        step_config,
                        model,
                        x1=x1,
                        x2=x2,
                        target=target,
                    )
                losses["total"].backward()
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                count = len(batch_rows)
                total_ce += float(losses["classification"].detach().float().cpu()) * count
                total_js += float(losses["consistency"].detach().float().cpu()) * count
                total_loss += float(losses["total"].detach().float().cpu()) * count
                observed_structures += count
                if device.type == "cuda":
                    peak_allocated = max(peak_allocated, int(torch.cuda.max_memory_allocated(device)))
                if first_step % 500 == 0 or first_step == 1:
                    _log(
                        log,
                        "training_progress",
                        trial_id=trial_id,
                        step=first_step,
                        total_steps=total_steps,
                        mean_ce=total_ce / observed_structures,
                        mean_js=total_js / observed_structures,
                        mean_total=total_loss / observed_structures,
                        learning_rate=optimizer.param_groups[0]["lr"],
                        prefetch_wait_seconds=prefetch_wait_seconds,
                    )

                validate_now = (
                    first_step % validation_interval == 0 or first_step == total_steps
                )
                if validate_now:
                    validation_started = time.perf_counter()
                    metrics = _validation_batches(
                        model,
                        panels,
                        labels_by_id,
                        validation_rows,
                        device=device,
                        runtime=runtime,
                    )
                    validation_seconds = time.perf_counter() - validation_started
                    selection_key = _selection_key(
                        metrics, ood_profiles, tie_profile, first_step, candidate_order
                    )
                    record = {
                        "step": first_step,
                        "ood_macro_f1_mean": selection_key[0],
                        "in_range_macro_f1": selection_key[1],
                        "profile_metrics": metrics,
                        "panel_sha256": dict(panel_hashes),
                        "validation_seconds": validation_seconds,
                    }
                    with (run_dir / "validation_history.jsonl").open("a", encoding="utf-8") as out:
                        out.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
                    if selected_key is None or selection_key > selected_key:
                        selected_key = selection_key
                        selected_metrics = metrics
                        selected_step = first_step
                        save_checkpoint(
                            run_dir / "best.ckpt",
                            model=model,
                            optimizers=[optimizer],
                            schedulers=schedulers,
                            epoch=1,
                            global_step=first_step,
                            config=model_config,
                            data_manifest_hash=str(trial_config["provenance"]["derived_records_sha256"]),
                            view_manifest_hash=config_hash(simulation_config),
                            seed=seed,
                            provenance=trial_config["provenance"],
                            extra_state={"trial_config": dict(trial_config), "metrics": metrics},
                        )
                    _log(
                        log,
                        "validation",
                        trial_id=trial_id,
                        step=first_step,
                        ood_macro_f1_mean=selection_key[0],
                        in_range_macro_f1=selection_key[1],
                        selected=selected_step == first_step,
                        elapsed_seconds=time.perf_counter() - train_started,
                    )
                first_step += 1

            train_seconds = time.perf_counter() - train_started
            save_checkpoint(
                run_dir / "last.ckpt",
                model=model,
                optimizers=[optimizer],
                schedulers=schedulers,
                epoch=1,
                global_step=total_steps,
                config=model_config,
                data_manifest_hash=str(trial_config["provenance"]["derived_records_sha256"]),
                view_manifest_hash=config_hash(simulation_config),
                seed=seed,
                provenance=trial_config["provenance"],
                extra_state={"trial_config": dict(trial_config)},
            )
        finally:
            prefetcher.close()
        if selected_metrics is None or selected_key is None:
            raise RuntimeError(f"trial {trial_id} completed without validation")
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        result = {
            "status": "completed",
            "trial_id": trial_id,
            "phase": trial_config["phase"],
            "model_config": dict(trial_config["model_config"]),
            "model_profile": model_profile,
            "training_seed": seed,
            "optimizer_steps": total_steps,
            "parent_occurrences": observed_structures,
            "generated_views": observed_structures * 2,
            "selected_step": selected_step,
            "selected_validation_ood_macro_f1": selected_key[0],
            "selected_validation_in_range_macro_f1": selected_key[1],
            "selected_validation_profile_metrics": selected_metrics,
            "elapsed_seconds": train_seconds,
            "prefetch_wait_seconds": prefetch_wait_seconds,
            "optimizer_steps_per_second_including_validation": total_steps / max(train_seconds, 1e-9),
            "peak_cuda_allocated_bytes": peak_allocated or None,
            "best_checkpoint": str((run_dir / "best.ckpt").relative_to(output_dir)),
            "best_checkpoint_sha256": _sha256(run_dir / "best.ckpt"),
            "last_checkpoint": str((run_dir / "last.ckpt").relative_to(output_dir)),
            "last_checkpoint_sha256": _sha256(run_dir / "last.ckpt"),
        }
        _write_json(run_dir / "result.json", result, overwrite=False)
        _log(log, "trial_completed", **result)
        del model, optimizer
        gc.collect()
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return result


def _run_gradient_diagnostic(
    *,
    checkpoint_path: Path,
    model_config: ML4PXRDResNet1DConfig,
    train_rows: Sequence[Mapping[str, Any]],
    simulation_config: Mapping[str, Any],
    protocol: Mapping[str, Any],
    runtime: Mapping[str, Any],
    data_root: Path,
    device: torch.device,
    batch_size: int,
    seed: int,
    batches: int,
) -> dict[str, Any]:
    payload = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = ML4PXRDResNet1D(model_config).to(device)
    model.load_state_dict(payload["model"], strict=True)
    model.train()
    train_sampler = PhysicsParameterSampler.from_mapping({**simulation_config, "run_seed": seed})
    batch_sampler = CyclicParentSampler(train_rows, seed=seed + 991)
    prefetcher = DynamicBatchPrefetcher(
        worker_count=int(runtime["prefetch_worker_count"]),
        worker_native_threads=int(runtime["worker_native_threads"]),
        prefetch_batches=int(runtime["prefetch_batches"]),
        start_method=str(runtime["multiprocessing_start_method"]),
        data_root=data_root,
        peak_cache_name="peak_tables_v7_reflection",
        sampler_config={**simulation_config, "run_seed": seed},
        quality_gate=False,
        quality_gate_config={},
        simulation_config_hash=config_hash(simulation_config),
        profile=str(protocol["simulation"]["training_profile"]),
        simulator_version=str(simulation_config["simulator_version"]),
        line_profile_config=simulation_config.get("line_profile", {}),
    )
    parameter_list = [parameter for parameter in model.parameters() if parameter.requires_grad]
    ce_norms: list[float] = []
    js_norms: list[float] = []
    step = 0
    pending: dict[int, list[dict[str, Any]]] = {}
    next_submit = 1
    try:
        while step < batches:
            while next_submit <= batches and prefetcher.in_flight_batches < int(runtime["prefetch_batches"]):
                rows = batch_sampler.next_batch(batch_size)
                ids = [str(row["material_id"]) for row in rows]
                params = build_parameter_batch(
                    ids,
                    train_sampler,
                    profile=str(protocol["simulation"]["training_profile"]),
                    epoch=20,
                    global_step=next_submit,
                    split="train",
                )
                prefetcher.submit(next_submit, ids, params)
                pending[next_submit] = rows
                next_submit += 1
            rendered = prefetcher.get(step + 1)
            rows = pending.pop(step + 1)
            x1 = torch.from_numpy(rendered.first).to(device)
            x2 = torch.from_numpy(rendered.second).to(device)
            target = torch.tensor([int(row["label"]) for row in rows], dtype=torch.long, device=device)
            with _autocast(device, runtime):
                losses = run_training_step(
                    TrainingStepConfig(TrainingMode.DYNAMIC_JS, lambda_js=60.0),
                    model,
                    x1=x1,
                    x2=x2,
                    target=target,
                )
            grad_ce = torch.autograd.grad(
                losses["classification"], parameter_list, retain_graph=True, allow_unused=True
            )
            grad_js = torch.autograd.grad(
                losses["consistency"], parameter_list, retain_graph=False, allow_unused=True
            )
            ce_norm = math.sqrt(sum(float(g.detach().float().square().sum().cpu()) for g in grad_ce if g is not None))
            js_norm = math.sqrt(sum(float(g.detach().float().square().sum().cpu()) for g in grad_js if g is not None))
            if not math.isfinite(ce_norm) or not math.isfinite(js_norm):
                raise RuntimeError("non-finite CE/JS gradient diagnostic")
            ce_norms.append(ce_norm)
            js_norms.append(js_norm)
            step += 1
    finally:
        prefetcher.close()
    unweighted_ratio = float(np.mean(js_norms) / max(np.mean(ce_norms), 1e-12))
    result = {
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": _sha256(checkpoint_path),
        "batches": batches,
        "batch_size_parents": batch_size,
        "ce_gradient_norm_mean": float(np.mean(ce_norms)),
        "ce_gradient_norm_sd": float(np.std(ce_norms, ddof=1)) if len(ce_norms) > 1 else 0.0,
        "js_gradient_norm_mean": float(np.mean(js_norms)),
        "js_gradient_norm_sd": float(np.std(js_norms, ddof=1)) if len(js_norms) > 1 else 0.0,
        "unweighted_js_to_ce_gradient_norm_ratio": unweighted_ratio,
        "lambda_60_weighted_js_to_ce_gradient_norm_ratio": 60.0 * unweighted_ratio,
        "interpretation": "diagnostic only; lambda trials are judged on validation, not this ratio alone",
    }
    del model
    gc.collect()
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return result


def _choose(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    completed = [row for row in results if row.get("status") == "completed"]
    if not completed:
        raise RuntimeError("no candidate completed successfully")
    return max(
        completed,
        key=lambda row: (
            float(row["selected_validation_ood_macro_f1"]),
            float(row["selected_validation_in_range_macro_f1"]),
            -int(row["selected_step"]),
            -int(row.get("candidate_order", 0)),
        ),
    )


def _result_with_order(result: dict[str, Any], candidate_order: int) -> dict[str, Any]:
    return {**result, "candidate_order": candidate_order}


def _aggregate_final_validation(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    completed = [row for row in results if row.get("status") == "completed"]
    if not completed:
        return {"completed_seed_count": 0, "profiles": {}}
    profile_names = tuple(
        completed[0]["selected_validation_profile_metrics"].keys()
    )
    metric_names = ("accuracy", "macro_f1", "ece")
    aggregate: dict[str, Any] = {"completed_seed_count": len(completed), "profiles": {}}
    for profile in profile_names:
        aggregate["profiles"][profile] = {}
        for metric in metric_names:
            values = [
                float(row["selected_validation_profile_metrics"][profile][metric])
                for row in completed
            ]
            aggregate["profiles"][profile][metric] = {
                "mean": float(np.mean(values)),
                "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "per_seed": {
                    str(row["training_seed"]): float(
                        row["selected_validation_profile_metrics"][profile][metric]
                    )
                    for row in completed
                },
            }
    return aggregate


def _write_trial_index(output_dir: Path, results: Sequence[Mapping[str, Any]]) -> None:
    rows = [dict(row) for row in results]
    _write_json(output_dir / "trial_results.json", rows)
    path = output_dir / "trial_results.csv"
    columns = (
        "trial_id",
        "phase",
        "status",
        "training_seed",
        "optimizer_steps",
        "selected_step",
        "selected_validation_ood_macro_f1",
        "selected_validation_in_range_macro_f1",
        "elapsed_seconds",
        "optimizer_steps_per_second_including_validation",
        "best_checkpoint",
        "best_checkpoint_sha256",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _planned_resource_budget(protocol: Mapping[str, Any]) -> dict[str, int]:
    training = protocol["training"]
    runtime = protocol["runtime"]
    architecture_count = len(protocol["architecture_search"]["selection_order"])
    baseline_lr = float(training["exploration_learning_rate"])
    learning_rates = list(
        dict.fromkeys([baseline_lr, *map(float, training["learning_rate_candidates"])])
    )
    scheduler_names = list(dict.fromkeys(map(str, training["scheduler_candidates"])))
    baseline_lambda = float(training["exploration_lambda_js"])
    lambda_values = list(
        dict.fromkeys([baseline_lambda, *map(float, training["lambda_js_candidates"])])
    )
    exploration_steps = int(training["exploration_steps_per_candidate"])
    final_steps = int(training["final_optimizer_steps_per_seed"])
    batch_size = int(training["batch_size_parents"])
    diagnostic_batches = int(training["gradient_diagnostic_batches"])
    exploratory_trials = (
        architecture_count
        + len(learning_rates)
        - 1
        + max(0, len(scheduler_names) - 1)
        + len(lambda_values)
        - 1
    )
    final_trial_count = len(training["final_seeds"])
    trial_count = exploratory_trials + final_trial_count
    optimizer_steps = (
        exploratory_trials * exploration_steps
        + final_trial_count * final_steps
        + diagnostic_batches
    )
    budget = {
        "trial_count": trial_count,
        "optimizer_steps_including_gradient_diagnostic": optimizer_steps,
        "parent_occurrences_including_gradient_diagnostic": optimizer_steps * batch_size,
        "generated_views_including_gradient_diagnostic": optimizer_steps * batch_size * 2,
    }
    caps = {
        "trial_count": int(runtime["max_trials_including_final"]),
        "optimizer_steps_including_gradient_diagnostic": int(
            runtime["max_optimizer_steps_including_gradient_diagnostic"]
        ),
        "parent_occurrences_including_gradient_diagnostic": int(
            runtime["max_parent_occurrences_including_gradient_diagnostic"]
        ),
        "generated_views_including_gradient_diagnostic": int(
            runtime["max_generated_views_including_gradient_diagnostic"]
        ),
    }
    for name, value in budget.items():
        if value > caps[name]:
            raise ValueError(f"planned resource budget exceeds {name} cap: {value} > {caps[name]}")
    return budget


def run_search(args: argparse.Namespace) -> dict[str, Any]:
    protocol_path = Path(args.search_config).resolve()
    simulation_path = Path(args.simulation_config).resolve()
    data_root = Path(args.data_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    resource_budget = _planned_resource_budget(protocol)
    if str(simulation_config.get("simulator_version")) != str(protocol["simulation"]["version"]):
        raise ValueError("simulation config is not the registered V11 renderer")
    if str(args.mode) != "dynamic_js":
        raise ValueError("Issue #55 permits Dynamic JS runs only")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory must be empty to protect existing evidence: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".issue55_run_owned").write_text("issue55-resnet-js-search-v1\n", encoding="utf-8")
    search_events_path = output_dir / "search_events.jsonl"

    def emit(event: str, **payload: Any) -> None:
        _append_event(search_events_path, event, **payload)

    emit(
        "search_started",
        issue=55,
        protocol_sha256=_sha256(protocol_path),
        simulation_config_sha256=_sha256(simulation_path),
        resource_budget=resource_budget,
        data_root=str(data_root),
    )
    records, records_hash, source_hashes = _prepare_records(
        data_root, output_dir, protocol, progress_callback=emit
    )
    train_rows = [row for row in records if row["split"] == "train"]
    validation_rows = [row for row in records if row["split"] == "validation"]
    train_ids_hash = _material_id_hash(train_rows)
    validation_ids_hash = _material_id_hash(validation_rows)
    expected = protocol["data_contract"]["expected_counts"]
    if len(train_rows) != int(expected["train"]) or len(validation_rows) != int(expected["validation"]):
        raise ValueError("derived train/validation rows do not match the frozen protocol")
    if any(row["split"] == "test" for row in (*train_rows, *validation_rows)):
        raise AssertionError("test row found in train/validation access")
    if not all(Path(row["peak_table_path"]).is_file() for row in (*train_rows, *validation_rows)):
        raise FileNotFoundError("one or more official train/validation peak tables are missing")
    validation_peaks = _load_val_peaks(validation_rows)
    if len(validation_peaks) != len(validation_rows):
        raise ValueError("validation peak table count mismatch")
    panels, labels_by_id, panel_hashes = _make_validation_panels(
        records,
        validation_peaks,
        simulation_config,
        protocol["simulation"],
        progress_callback=emit,
    )
    validation_hash = config_hash(
        {
            "records_sha256": records_hash,
            "panel_sha256": panel_hashes,
            "profiles": list(panels),
            "evaluation_seed": protocol["simulation"]["validation_seed"],
        }
    ).upper()
    emit(
        "validation_panels_ready",
        panel_sha256=panel_hashes,
        validation_manifest_hash=validation_hash,
        selected_parent_count=len(validation_rows),
        test_peak_tables_loaded=False,
    )
    device = _resolve_device(args.device)
    runtime = _configure_runtime(device, protocol["runtime"])
    software = {
        "python_version": sys.version.split()[0],
        "torch_version": str(torch.__version__),
        "numpy_version": str(np.__version__),
        "cuda_runtime_version": torch.version.cuda,
        "git_revision": _git_revision(PROJECT_ROOT.parent),
        "script_sha256": _sha256(Path(__file__).resolve()),
    }
    provenance = {
        **source_hashes,
        "derived_records_sha256": records_hash,
        "validation_panel_sha256": panel_hashes,
        "validation_manifest_hash": validation_hash,
        "simulation_config_sha256": _sha256(simulation_path),
        "protocol_sha256": _sha256(protocol_path),
    }
    _write_json(
        output_dir / "run_manifest.json",
        {
            "schema_version": "issue55-run-manifest-v1",
            "status": "running",
            "issue": 55,
            "synthetic_test_peak_tables_loaded": False,
            "synthetic_test_rows_in_training_or_selection": False,
            "locked_rruff_test_loaded": False,
            "locked_rruff_evaluation": "NOT_RUN",
            "train_structures": len(train_rows),
            "validation_structures": len(validation_rows),
            "train_material_ids_sha256": train_ids_hash,
            "validation_material_ids_sha256": validation_ids_hash,
            "source_hashes": source_hashes,
            "derived_records_sha256": records_hash,
            "validation_panel_sha256": panel_hashes,
            "validation_manifest_hash": validation_hash,
            "simulation_config_sha256": provenance["simulation_config_sha256"],
            "protocol_sha256": provenance["protocol_sha256"],
            "runtime": runtime,
            "resource_budget": resource_budget,
            "software": software,
        },
        overwrite=False,
    )
    all_results: list[dict[str, Any]] = []
    start_search = time.perf_counter()
    fixed = protocol["training"]
    arch_candidates = protocol["architecture_search"]["candidates"]
    arch_results: dict[str, dict[str, Any]] = {}
    for order, candidate_id in enumerate(protocol["architecture_search"]["selection_order"]):
        model_config = _model_config(arch_candidates[candidate_id])
        model_config.validate()
        settings = {
            "trial_id": f"architecture-{candidate_id}",
            "phase": "1_architecture",
            "candidate_order": order,
            "model_config": model_config,
            "seed": int(fixed["exploration_seed"]),
            "steps": int(fixed["exploration_steps_per_candidate"]),
            "batch_size": int(fixed["batch_size_parents"]),
            "learning_rate": float(fixed["exploration_learning_rate"]),
            "weight_decay": float(fixed["weight_decay"]),
            "lambda_js": float(fixed["exploration_lambda_js"]),
            "scheduler_name": "none",
        }
        trial_config = _trial_config(**settings, protocol=protocol, provenance=provenance)
        try:
            result = _run_trial(
                output_dir=output_dir,
                trial_config=trial_config,
                model_config=model_config,
                train_rows=train_rows,
                validation_rows=validation_rows,
                panels=panels,
                panel_hashes=panel_hashes,
                labels_by_id=labels_by_id,
                simulation_config=simulation_config,
                data_root=data_root,
                protocol=protocol,
                runtime=runtime,
                device=device,
                validation_manifest_hash=validation_hash,
                candidate_order=order,
            )
            result["candidate_order"] = order
            arch_results[candidate_id] = result
        except torch.cuda.OutOfMemoryError as error:
            result = {"status": "failed", "trial_id": trial_config["trial_id"], "phase": "1_architecture", "error": repr(error)}
            _write_json(output_dir / "trials" / trial_config["trial_id"] / "failure.json", result, overwrite=False)
            if device.type == "cuda":
                torch.cuda.empty_cache()
        all_results.append(result)
        _write_trial_index(output_dir, all_results)
        emit("trial_result_recorded", phase="1_architecture", trial_id=result["trial_id"], status=result["status"])
        if result["status"] != "completed":
            raise RuntimeError(f"architecture trial did not complete: {result['trial_id']}")

    best_arch = _choose([result for result in arch_results.values()])
    best_arch_id = str(best_arch["trial_id"]).replace("architecture-", "")
    chosen_arch_map = arch_candidates[best_arch_id]
    chosen_model_config = _model_config(chosen_arch_map)

    # Phase 2: vary learning rate only; the 1e-4/no-scheduler reference is the
    # already completed selected architecture trial.
    lr_results = [{**best_arch, "candidate_order": 0}]
    lr_candidates = [float(fixed["exploration_learning_rate"]), *map(float, fixed["learning_rate_candidates"])]
    lr_candidates = list(dict.fromkeys(lr_candidates))
    for order, learning_rate in enumerate(lr_candidates):
        if math.isclose(learning_rate, float(fixed["exploration_learning_rate"])):
            continue
        trial_id = f"learning-rate-{learning_rate:.0e}"
        settings = {
            "trial_id": trial_id,
            "phase": "2_learning_rate",
            "candidate_order": order,
            "model_config": chosen_model_config,
            "seed": int(fixed["exploration_seed"]),
            "steps": int(fixed["exploration_steps_per_candidate"]),
            "batch_size": int(fixed["batch_size_parents"]),
            "learning_rate": learning_rate,
            "weight_decay": float(fixed["weight_decay"]),
            "lambda_js": float(fixed["exploration_lambda_js"]),
            "scheduler_name": "none",
        }
        trial_config = _trial_config(**settings, protocol=protocol, provenance=provenance)
        try:
            result = _run_trial(
                output_dir=output_dir,
                trial_config=trial_config,
                model_config=chosen_model_config,
                train_rows=train_rows,
                validation_rows=validation_rows,
                panels=panels,
                panel_hashes=panel_hashes,
                labels_by_id=labels_by_id,
                simulation_config=simulation_config,
                data_root=data_root,
                protocol=protocol,
                runtime=runtime,
                device=device,
                validation_manifest_hash=validation_hash,
                candidate_order=order,
            )
            result["candidate_order"] = order
        except torch.cuda.OutOfMemoryError as error:
            result = {"status": "failed", "trial_id": trial_id, "phase": "2_learning_rate", "error": repr(error), "candidate_order": order}
            _write_json(output_dir / "trials" / trial_id / "failure.json", result, overwrite=False)
            if device.type == "cuda":
                torch.cuda.empty_cache()
        lr_results.append(result)
        all_results.append(result)
        _write_trial_index(output_dir, all_results)
        emit("trial_result_recorded", phase="2_learning_rate", trial_id=result["trial_id"], status=result["status"])
        if result["status"] != "completed":
            raise RuntimeError(f"learning-rate trial did not complete: {result['trial_id']}")
    best_lr = _choose(lr_results)
    # Model fields do not carry optimizer values; recover the selected learning
    # rate from its immutable resolved config.
    best_lr_config = json.loads(
        (output_dir / "trials" / str(best_lr["trial_id"]) / "resolved_config.json").read_text(encoding="utf-8")
    )
    selected_lr = float(best_lr_config["learning_rate"])

    # Phase 3: compare cosine schedule against the selected constant-LR run.
    scheduler_results = [{**best_lr, "candidate_order": 0}]
    scheduler_candidate = str(fixed["scheduler_candidates"][1])
    schedule_id = f"scheduler-{scheduler_candidate}"
    schedule_settings = {
        "trial_id": schedule_id,
        "phase": "3_scheduler",
        "candidate_order": 1,
        "model_config": chosen_model_config,
        "seed": int(fixed["exploration_seed"]),
        "steps": int(fixed["exploration_steps_per_candidate"]),
        "batch_size": int(fixed["batch_size_parents"]),
        "learning_rate": selected_lr,
        "weight_decay": float(fixed["weight_decay"]),
        "lambda_js": float(fixed["exploration_lambda_js"]),
        "scheduler_name": scheduler_candidate,
    }
    schedule_config = _trial_config(**schedule_settings, protocol=protocol, provenance=provenance)
    try:
        schedule_result = _run_trial(
            output_dir=output_dir,
            trial_config=schedule_config,
            model_config=chosen_model_config,
            train_rows=train_rows,
            validation_rows=validation_rows,
            panels=panels,
            panel_hashes=panel_hashes,
            labels_by_id=labels_by_id,
            simulation_config=simulation_config,
            data_root=data_root,
            protocol=protocol,
            runtime=runtime,
            device=device,
            validation_manifest_hash=validation_hash,
            candidate_order=1,
        )
        schedule_result["candidate_order"] = 1
    except torch.cuda.OutOfMemoryError as error:
        schedule_result = {"status": "failed", "trial_id": schedule_id, "phase": "3_scheduler", "error": repr(error), "candidate_order": 1}
        _write_json(output_dir / "trials" / schedule_id / "failure.json", schedule_result, overwrite=False)
        if device.type == "cuda":
            torch.cuda.empty_cache()
    scheduler_results.append(schedule_result)
    all_results.append(schedule_result)
    _write_trial_index(output_dir, all_results)
    emit("trial_result_recorded", phase="3_scheduler", trial_id=schedule_result["trial_id"], status=schedule_result["status"])
    if schedule_result["status"] != "completed":
        raise RuntimeError(f"scheduler trial did not complete: {schedule_result['trial_id']}")
    best_scheduler = _choose(scheduler_results)
    best_scheduler_config = json.loads(
        (output_dir / "trials" / str(best_scheduler["trial_id"]) / "resolved_config.json").read_text(encoding="utf-8")
    )
    selected_scheduler = str(best_scheduler_config["scheduler"])
    selected_lr = float(best_scheduler_config["learning_rate"])

    # Phase 4: use measured CE/JS gradient norms before varying lambda_js.
    diagnostic = _run_gradient_diagnostic(
        checkpoint_path=output_dir / str(best_scheduler["best_checkpoint"]),
        model_config=chosen_model_config,
        train_rows=train_rows,
        simulation_config=simulation_config,
        protocol=protocol,
        runtime=runtime,
        data_root=data_root,
        device=device,
        batch_size=int(fixed["batch_size_parents"]),
        seed=int(fixed["exploration_seed"]),
        batches=int(fixed["gradient_diagnostic_batches"]),
    )
    _write_json(output_dir / "ce_js_gradient_diagnostic.json", diagnostic, overwrite=False)
    emit("gradient_diagnostic_completed", **diagnostic)
    lambda_results = [{**best_scheduler, "candidate_order": 0}]
    lambda_order = 0
    for lambda_js in map(float, fixed["lambda_js_candidates"]):
        if math.isclose(lambda_js, float(fixed["exploration_lambda_js"])):
            continue
        lambda_order += 1
        trial_id = f"lambda-js-{lambda_js:g}"
        settings = {
            "trial_id": trial_id,
            "phase": "4_lambda_js",
            "candidate_order": lambda_order,
            "model_config": chosen_model_config,
            "seed": int(fixed["exploration_seed"]),
            "steps": int(fixed["exploration_steps_per_candidate"]),
            "batch_size": int(fixed["batch_size_parents"]),
            "learning_rate": selected_lr,
            "weight_decay": float(fixed["weight_decay"]),
            "lambda_js": lambda_js,
            "scheduler_name": selected_scheduler,
        }
        trial_config = _trial_config(**settings, protocol=protocol, provenance=provenance)
        try:
            result = _run_trial(
                output_dir=output_dir,
                trial_config=trial_config,
                model_config=chosen_model_config,
                train_rows=train_rows,
                validation_rows=validation_rows,
                panels=panels,
                panel_hashes=panel_hashes,
                labels_by_id=labels_by_id,
                simulation_config=simulation_config,
                data_root=data_root,
                protocol=protocol,
                runtime=runtime,
                device=device,
                validation_manifest_hash=validation_hash,
                candidate_order=lambda_order,
            )
            result["candidate_order"] = lambda_order
        except torch.cuda.OutOfMemoryError as error:
            result = {"status": "failed", "trial_id": trial_id, "phase": "4_lambda_js", "error": repr(error), "candidate_order": lambda_order}
            _write_json(output_dir / "trials" / trial_id / "failure.json", result, overwrite=False)
            if device.type == "cuda":
                torch.cuda.empty_cache()
        lambda_results.append(result)
        all_results.append(result)
        _write_trial_index(output_dir, all_results)
        emit("trial_result_recorded", phase="4_lambda_js", trial_id=result["trial_id"], status=result["status"])
        if result["status"] != "completed":
            raise RuntimeError(f"lambda-JS trial did not complete: {result['trial_id']}")
    best_lambda = _choose(lambda_results)
    best_lambda_config = json.loads(
        (output_dir / "trials" / str(best_lambda["trial_id"]) / "resolved_config.json").read_text(encoding="utf-8")
    )

    selected = {
        "architecture_id": best_arch_id,
        "model_config": best_lambda_config["model_config"],
        "learning_rate": float(best_lambda_config["learning_rate"]),
        "weight_decay": float(best_lambda_config["weight_decay"]),
        "lambda_js": float(best_lambda_config["lambda_js"]),
        "scheduler": str(best_lambda_config["scheduler"]),
        "batch_size_parents": int(best_lambda_config["batch_size_parents"]),
        "exploration_seed": int(fixed["exploration_seed"]),
        "exploration_steps": int(fixed["exploration_steps_per_candidate"]),
        "selection_trial_id": str(best_lambda["trial_id"]),
        "validation_ood_macro_f1": float(best_lambda["selected_validation_ood_macro_f1"]),
        "validation_in_range_macro_f1": float(best_lambda["selected_validation_in_range_macro_f1"]),
        "gradient_diagnostic": diagnostic,
    }
    _write_json(output_dir / "selected_exploratory_config.json", selected, overwrite=False)

    # Final fixed-budget confirmation: preserve the selected hyperparameters and
    # vary only the training seed. No test split is loaded or scored.
    final_results: list[dict[str, Any]] = []
    final_model_map = {
        "stage_downsample_stride": best_lambda_config["model_config"]["stage_downsample_stride"],
        "residual_kernel_size": best_lambda_config["model_config"]["residual_kernel_size"],
        "head_mode": best_lambda_config["model_config"]["head_mode"],
    }
    final_model_config = _model_config(final_model_map)
    for seed_order, seed in enumerate(map(int, fixed["final_seeds"])):
        trial_id = f"final-seed-{seed}"
        settings = {
            "trial_id": trial_id,
            "phase": "5_final_fixed_budget",
            "candidate_order": seed_order,
            "model_config": final_model_config,
            "seed": seed,
            "steps": int(fixed["final_optimizer_steps_per_seed"]),
            "batch_size": int(fixed["batch_size_parents"]),
            "learning_rate": float(best_lambda_config["learning_rate"]),
            "weight_decay": float(best_lambda_config["weight_decay"]),
            "lambda_js": float(best_lambda_config["lambda_js"]),
            "scheduler_name": str(best_lambda_config["scheduler"]),
        }
        trial_config = _trial_config(**settings, protocol=protocol, provenance=provenance)
        try:
            result = _run_trial(
                output_dir=output_dir,
                trial_config=trial_config,
                model_config=final_model_config,
                train_rows=train_rows,
                validation_rows=validation_rows,
                panels=panels,
                panel_hashes=panel_hashes,
                labels_by_id=labels_by_id,
                simulation_config=simulation_config,
                data_root=data_root,
                protocol=protocol,
                runtime=runtime,
                device=device,
                validation_manifest_hash=validation_hash,
                candidate_order=seed_order,
            )
            result["candidate_order"] = seed_order
            result["training_seed"] = seed
            result["phase"] = "5_final_fixed_budget"
        except torch.cuda.OutOfMemoryError as error:
            result = {"status": "failed", "trial_id": trial_id, "phase": "5_final_fixed_budget", "training_seed": seed, "error": repr(error), "candidate_order": seed_order}
            _write_json(output_dir / "trials" / trial_id / "failure.json", result, overwrite=False)
            if device.type == "cuda":
                torch.cuda.empty_cache()
        final_results.append(result)
        all_results.append(result)
        _write_trial_index(output_dir, all_results)
        emit("trial_result_recorded", phase="5_final_fixed_budget", trial_id=result["trial_id"], status=result["status"])
        if result["status"] != "completed":
            raise RuntimeError(f"final fixed-budget trial did not complete: {result['trial_id']}")

    final_completed = [row for row in final_results if row.get("status") == "completed"]
    if not final_completed:
        raise RuntimeError("no final fixed-budget seed completed")
    final_best = _choose(final_completed)
    best_checkpoint = output_dir / str(final_best["best_checkpoint"])
    final_summary = {
        "schema_version": "issue55-resnet-dynamic-js-results-v1",
        "status": "completed",
        "issue": 55,
        "selected_config": selected,
        "final_seed_results": final_results,
        "final_validation_aggregate": _aggregate_final_validation(final_results),
        "best_final_checkpoint": str(best_checkpoint.relative_to(output_dir)),
        "best_final_checkpoint_sha256": _sha256(best_checkpoint),
        "trial_count": len(all_results),
        "completed_trial_count": sum(row.get("status") == "completed" for row in all_results),
        "failed_trial_count": sum(row.get("status") == "failed" for row in all_results),
        "synthetic_test_peak_tables_loaded": False,
        "synthetic_test_rows_in_training_or_selection": False,
        "locked_rruff_test_loaded": False,
        "locked_rruff_evaluation": "NOT_RUN_BY_ISSUE55_SEARCH",
        "total_elapsed_seconds": time.perf_counter() - start_search,
        "source_hashes": source_hashes,
        "train_material_ids_sha256": train_ids_hash,
        "validation_material_ids_sha256": validation_ids_hash,
        "derived_records_sha256": records_hash,
        "validation_panel_sha256": panel_hashes,
        "runtime": runtime,
        "resource_budget": resource_budget,
        "software": software,
    }
    _write_json(output_dir / "results.json", final_summary, overwrite=False)
    run_manifest_path = output_dir / "run_manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    run_manifest["status"] = "completed"
    run_manifest["results_sha256"] = _sha256(output_dir / "results.json")
    _write_json(run_manifest_path, run_manifest)
    emit(
        "search_completed",
        completed_trials=final_summary["completed_trial_count"],
        failed_trials=final_summary["failed_trial_count"],
        total_elapsed_seconds=final_summary["total_elapsed_seconds"],
        best_final_checkpoint=final_summary["best_final_checkpoint"],
        best_final_checkpoint_sha256=final_summary["best_final_checkpoint_sha256"],
    )
    return final_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, help="formal_14060 root containing frozen manifests and V7 peak cache")
    parser.add_argument("--search-config", default=str(PROJECT_ROOT / "configs" / "issue55_resnet_js_search.v1.json"))
    parser.add_argument("--simulation-config", default=str(PROJECT_ROOT / "configs" / "simulation.v11_tch_pseudo_voigt.json"))
    parser.add_argument("--output-dir", required=True, help="new, empty ignored output directory")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--mode", default="dynamic_js", choices=["dynamic_js"])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    marker = output_dir / ".issue55_run_owned"
    marker_existed_before_invocation = marker.is_file()
    try:
        result = run_search(args)
    except BaseException as error:
        if marker.is_file() and not marker_existed_before_invocation:
            failure_path = output_dir / "failure.json"
            failure = {
                "schema_version": "issue55-failure-v1",
                "status": "failed",
                "exception_type": type(error).__name__,
                "exception": repr(error),
                "traceback": traceback.format_exc(),
                "unix_time": time.time(),
            }
            try:
                _write_json(failure_path, failure, overwrite=False)
                manifest_path = output_dir / "run_manifest.json"
                if manifest_path.is_file():
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest["status"] = "failed"
                    manifest["failure_sha256"] = _sha256(failure_path)
                    _write_json(manifest_path, manifest)
                _append_event(
                    output_dir / "search_events.jsonl",
                    "search_failed",
                    exception_type=type(error).__name__,
                    exception=repr(error),
                    failure_sha256=_sha256(failure_path),
                )
            except OSError:
                pass
        raise
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
