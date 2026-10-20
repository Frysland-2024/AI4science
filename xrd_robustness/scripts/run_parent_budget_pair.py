#!/usr/bin/env python
"""Train matched Dynamic ERM and Dynamic JS for one frozen parent budget."""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.experiment import save_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory, TrainingMode  # noqa: E402
from xrd_robustness.parent_budget_efficiency import (  # noqa: E402
    BUDGETS,
    CyclicParentSampler,
    canonical_json_bytes,
    expected_exposure,
    identity_hash,
    load_split_rows,
    normalized_text_file_hash,
    read_ranked_csv,
    sha256_bytes,
    sha256_file,
    validate_parent_split,
)
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.objectives import TrainingStepConfig  # noqa: E402
from xrd_robustness.training.paired import paired_optimizer_step  # noqa: E402
from xrd_robustness.training_prefetch import (  # noqa: E402
    DynamicBatchPrefetcher,
    PREFETCH_GENERATION,
    PREFETCH_RESULT_ORDER,
    PREFETCH_SHARDING_ALGORITHM,
    PREFETCH_WORKER_PEAK_CACHE,
    PREFETCH_WORKER_THREAD_POLICY,
)
from xrd_robustness.training.runner import PeakRecord, build_model  # noqa: E402
from xrd_robustness.view_manifest import (  # noqa: E402
    build_offline_view_manifest,
    build_parameter_batch,
)


PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
    "in_range",
    "level0",
)
_RUNTIME_CONFIGURED = False


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _record_from_split(row: Mapping[str, Any], data_root: Path) -> PeakRecord:
    material_id = str(row["material_id"])
    return PeakRecord(
        material_id=material_id,
        label=CRYSTAL_SYSTEMS.index(str(row["crystal_system"])),
        split=str(row["split"]),
        peak_table_path=(
            data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{material_id}.npz"
        ),
    )


def _records_for_split(
    rows: Sequence[Mapping[str, Any]], split: str, data_root: Path
) -> list[PeakRecord]:
    return [
        _record_from_split(row, data_root)
        for row in sorted(rows, key=lambda item: str(item["material_id"]))
        if str(row["split"]) == split
    ]


def _load_subset_rows(
    data_root: Path, manifest_path: Path, ranked_path: Path, budget_key: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "frozen_before_training":
        raise ValueError("parent subset manifest is not marked frozen before training")
    official_rows = load_split_rows(data_root)
    split_index = validate_parent_split(official_rows)
    split_by_material = {str(row["material_id"]): row for row in official_rows}
    selected = manifest["budgets"][budget_key]
    selected_ids = list(selected["material_ids"])
    if len(selected_ids) != BUDGETS[budget_key] or len(set(selected_ids)) != len(selected_ids):
        raise ValueError(f"frozen {budget_key}% subset contains bad count or duplicate material IDs")
    expected_ids = {
        str(row["material_id"])
        for row in split_index["train"]
        if str(row["material_id"]) in set(selected_ids)
    }
    if expected_ids != set(selected_ids):
        raise ValueError("subset includes a material outside the official frozen Train split")
    selected_parents = {
        str(split_by_material[material_id]["parent_structure_id"]): material_id
        for material_id in selected_ids
    }
    if set(selected_parents) != set(selected["parent_structure_ids"]):
        raise ValueError("subset parent fingerprints do not match the frozen parent list")
    if identity_hash(selected_parents) != selected["parent_ids_sha256"]:
        raise ValueError("subset parent identity hash does not match the frozen manifest")
    train_rows = [split_by_material[material_id] for material_id in selected_ids]
    validation_rows = list(split_index["validation"])
    if set(selected_ids).intersection(str(row["material_id"]) for row in validation_rows):
        raise ValueError("validation contamination detected in selected Train subset")
    if set(selected_ids).intersection(str(row["material_id"]) for row in split_index["test"]):
        raise ValueError("test contamination detected in selected Train subset")

    ranked = read_ranked_csv(ranked_path)
    canonical_subset_ids = [
        str(row["material_id"])
        for row in ranked
        if str(row["material_id"]) in set(selected_ids)
    ]
    if canonical_subset_ids != selected_ids:
        raise ValueError("ranked CSV prefix and frozen subset list differ")
    return train_rows, validation_rows, manifest


def _preflight_data_bindings(data_root: Path, manifest: Mapping[str, Any]) -> None:
    source = data_root / "mp_processed" / "structure_records.jsonl"
    split = data_root / "manifests" / "split_manifest.json"
    cache_manifest = data_root / "manifests" / "peak_cache_manifest.v7.reflection.csv"
    expected = manifest["source"]
    checks = (
        (source, expected["records_sha256"]),
        (split, expected["split_manifest_sha256"]),
        (cache_manifest, expected["peak_cache"]["manifest_sha256"]),
    )
    for path, digest in checks:
        if sha256_file(path) != str(digest).upper():
            raise ValueError(f"data provenance SHA-256 mismatch: {path}")


def _ensure_eval_cache(
    *,
    data_root: Path,
    cache_root: Path,
    split_rows: Sequence[Mapping[str, Any]],
    simulation: Mapping[str, Any],
    simulation_config_sha256: str,
    eval_seeds: Sequence[int],
    profiles: Sequence[str],
    split: str,
    input_length: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray], np.ndarray]:
    rows = [row for row in split_rows if str(row["split"]) == split]
    rows.sort(key=lambda row: str(row["material_id"]))
    material_ids = [str(row["material_id"]) for row in rows]
    labels = np.asarray(
        [CRYSTAL_SYSTEMS.index(str(row["crystal_system"])) for row in rows], dtype=np.int64
    )
    binding = {
        "schema_version": "parent-budget-eval-panels-v1",
        "split": split,
        "official_split_manifest_sha256": sha256_file(
            data_root / "manifests" / "split_manifest.json"
        ),
        "material_ids_sha256": identity_hash(material_ids),
        "simulation_config_sha256": simulation_config_sha256,
        "evaluation_seeds": [int(value) for value in eval_seeds],
        "profiles": list(profiles),
        "view_count_per_parent": 1,
        "input_length": int(input_length),
    }
    manifest_path = cache_root / split / "panel_index.json"
    if manifest_path.exists():
        index = json.loads(manifest_path.read_text(encoding="utf-8"))
        if index.get("bindings") != binding:
            raise ValueError(f"cached {split} panel bindings changed; refusing reuse")
    else:
        index = {"bindings": binding, "material_ids": material_ids, "labels": labels.tolist(), "entries": {}}

    needs_panel_generation = any(
        f"{int(seed)}:{profile}" not in index["entries"]
        for seed in eval_seeds
        for profile in profiles
    )
    peaks = (
        {
            material_id: load_peak_table(
                data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{material_id}.npz"
            )
            for material_id in material_ids
        }
        if needs_panel_generation
        else {}
    )
    panels: dict[str, np.ndarray] = {}
    for seed in eval_seeds:
        sampler = PhysicsParameterSampler.from_mapping({**simulation, "run_seed": int(seed)})
        factory = OnlineViewFactory(sampler)
        for profile in profiles:
            key = f"{int(seed)}:{profile}"
            entry = index["entries"].get(key)
            cache_file = cache_root / split / f"seed_{seed}" / f"{profile}.npy"
            if entry:
                if not cache_file.is_file() or sha256_file(cache_file) != entry["sha256"]:
                    raise ValueError(f"cached evaluation panel failed integrity check: {cache_file}")
            else:
                view_rows = build_offline_view_manifest(
                    material_ids,
                    sampler,
                    profile=profile,
                    views_per_material=1,
                    split=split,
                )
                view_by_id = {row.material_id: row for row in view_rows}
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                partial = cache_file.with_suffix(".partial.npy")
                matrix = np.lib.format.open_memmap(
                    partial, mode="w+", dtype=np.float32, shape=(len(rows), input_length)
                )
                for position, material_id in enumerate(material_ids):
                    matrix[position] = factory.make_view_from_manifest(
                        peaks[material_id], view_by_id[material_id]
                    ).xrd
                matrix.flush()
                del matrix
                partial.replace(cache_file)
                entry = {
                    "path": cache_file.relative_to(cache_root).as_posix(),
                    "sha256": sha256_file(cache_file),
                    "shape": [len(rows), input_length],
                    "dtype": "float32",
                }
                index["entries"][key] = entry
                _write_json_atomic(manifest_path, index)
            panels[key] = np.load(cache_file, mmap_mode="r", allow_pickle=False)
    index["material_ids"] = material_ids
    index["labels"] = labels.tolist()
    _write_json_atomic(manifest_path, index)
    return index, panels, labels


def _evaluate_model(
    model: torch.nn.Module,
    panels: Mapping[str, np.ndarray],
    labels: np.ndarray,
    *,
    seeds: Sequence[int],
    profiles: Sequence[str],
    batch_size: int,
    device: torch.device,
    amp_dtype: torch.dtype | None = None,
    pin_memory: bool = True,
    non_blocking_h2d: bool = True,
    material_ids: Sequence[str] | None = None,
    prediction_path: Path | None = None,
    prediction_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    model.eval()
    if material_ids is not None and len(material_ids) != len(labels):
        raise ValueError("prediction material IDs and labels differ in length")
    prediction_handle = gzip.open(prediction_path, "wt", encoding="utf-8", newline="") if prediction_path else None
    writer = None
    if prediction_handle:
        if material_ids is None or prediction_context is None:
            prediction_handle.close()
            raise ValueError("prediction export requires material IDs and run context")
        writer = csv.writer(prediction_handle, lineterminator="\n")
        writer.writerow(
            ["training_seed", "budget_percent", "method", "evaluation_seed", "profile", "material_id", "label", "prediction"]
            + [f"probability_{name}" for name in CRYSTAL_SYSTEMS]
        )
    try:
        for seed in seeds:
            output[str(seed)] = {}
            for profile in profiles:
                spectra = panels[f"{int(seed)}:{profile}"]
                probabilities = np.empty((len(labels), len(CRYSTAL_SYSTEMS)), dtype=np.float32)
                for start in range(0, len(labels), batch_size):
                    stop = min(start + batch_size, len(labels))
                    batch = torch.from_numpy(np.array(spectra[start:stop], copy=True))
                    context = (
                        torch.autocast(device_type="cuda", dtype=amp_dtype)
                        if device.type == "cuda" and amp_dtype is not None
                        else torch.autocast(device_type="cpu", enabled=False)
                    )
                    if pin_memory and device.type == "cuda":
                        batch = batch.pin_memory()
                    with torch.inference_mode(), context:
                        logits = model(
                            batch.to(
                                device,
                                non_blocking=bool(non_blocking_h2d and device.type == "cuda"),
                            )
                        )["logits"]
                        probabilities[start:stop] = torch.softmax(logits, dim=-1).float().cpu().numpy()
                predictions = probabilities.argmax(axis=1)
                metrics = classification_metrics(
                    labels,
                    predictions,
                    probabilities=probabilities,
                    num_classes=len(CRYSTAL_SYSTEMS),
                )
                metrics["per_class_f1_by_name"] = {
                    name: float(score)
                    for name, score in zip(CRYSTAL_SYSTEMS, metrics["per_class_f1"], strict=True)
                }
                output[str(seed)][profile] = metrics
                if writer:
                    for position in range(len(labels)):
                        writer.writerow(
                            [
                                prediction_context["training_seed"],
                                prediction_context["budget_percent"],
                                prediction_context["method"],
                                int(seed),
                                profile,
                                material_ids[position],
                                int(labels[position]),
                                int(predictions[position]),
                            ]
                            + [f"{value:.9g}" for value in probabilities[position]]
                        )
    finally:
        if prediction_handle:
            prediction_handle.close()
    return output


def _validation_selection(metrics: Mapping[str, Any], seed: int) -> tuple[float, float]:
    by_profile = metrics[str(seed)]
    ood = [by_profile[name]["macro_f1"] for name in PROFILES[:6]]
    return float(np.mean(ood)), float(by_profile["in_range"]["macro_f1"])


def _batch_digest(
    step: int,
    records: Sequence[PeakRecord],
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
) -> tuple[str, str]:
    id_payload = canonical_json_bytes(
        [(record.material_id, record.label) for record in records]
    )
    sample_hash = hashlib.sha256(id_payload).hexdigest().upper()
    digest = hashlib.sha256()
    digest.update(int(step).to_bytes(8, "big", signed=False))
    digest.update(id_payload)
    for tensor in (x1, x2, target):
        array = np.ascontiguousarray(tensor.detach().cpu().numpy())
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(memoryview(array).cast("B"))
    return sample_hash, digest.hexdigest().upper()


def _configure_training_runtime(
    config: Mapping[str, Any], device: torch.device
) -> dict[str, Any]:
    global _RUNTIME_CONFIGURED
    performance = config["performance"]
    threads = performance["cpu_threads"]
    native_threads = int(threads["main_intraop"])
    if not _RUNTIME_CONFIGURED:
        for name in (
            "OMP_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "VECLIB_MAXIMUM_THREADS",
            "BLIS_NUM_THREADS",
        ):
            os.environ[name] = str(native_threads)
        torch.set_num_threads(native_threads)
        torch.set_num_interop_threads(int(threads["main_interop"]))
        _RUNTIME_CONFIGURED = True

    cuda_math = performance["cuda_math"]
    if device.type == "cuda":
        torch.set_float32_matmul_precision(str(cuda_math["float32_matmul_precision"]))
        torch.backends.cuda.matmul.allow_tf32 = bool(cuda_math["allow_tf32_matmul"])
        torch.backends.cudnn.allow_tf32 = bool(cuda_math["allow_tf32_cudnn"])
        torch.backends.cudnn.benchmark = bool(cuda_math["cudnn_benchmark"])
        torch.backends.cudnn.deterministic = bool(cuda_math["cudnn_deterministic"])

    amp = performance["automatic_mixed_precision"]
    bf16_supported = bool(device.type == "cuda" and torch.cuda.is_bf16_supported())
    amp_enabled = bool(amp["enabled"] and bf16_supported)
    if amp["enabled"] and not bf16_supported and not amp["fallback_to_float32"]:
        raise RuntimeError("BF16 is required by the frozen runtime but unavailable")
    optimizer_config = performance["optimizer"]
    fused = bool(optimizer_config["fused"] and device.type == "cuda")
    return {
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "gpu_memory_bytes": int(torch.cuda.get_device_properties(device).total_memory)
        if device.type == "cuda"
        else None,
        "bf16_supported": bf16_supported,
        "amp_enabled": amp_enabled,
        "amp_dtype": "bfloat16" if amp_enabled else "float32",
        "fused_adamw": fused,
        "tf32_matmul": bool(cuda_math["allow_tf32_matmul"]) if device.type == "cuda" else False,
        "tf32_cudnn": bool(cuda_math["allow_tf32_cudnn"]) if device.type == "cuda" else False,
        "main_intraop_threads": native_threads,
        "main_interop_threads": int(threads["main_interop"]),
        "prefetch_workers": int(performance["dynamic_prefetch"]["worker_processes"]),
        "prefetch_batches": int(performance["dynamic_prefetch"]["prefetch_batches"]),
        "worker_native_threads": int(performance["dynamic_prefetch"]["worker_native_threads"]),
        "pin_memory": bool(performance["dynamic_prefetch"]["pin_memory"]),
        "non_blocking_h2d": bool(performance["dynamic_prefetch"]["non_blocking_h2d"]),
        "quality_gate": bool(performance["dynamic_prefetch"]["quality_gate"]),
        "prefetch_generation": PREFETCH_GENERATION,
        "prefetch_sharding": PREFETCH_SHARDING_ALGORITHM,
        "prefetch_result_order": PREFETCH_RESULT_ORDER,
        "worker_peak_cache": PREFETCH_WORKER_PEAK_CACHE,
        "worker_thread_policy": PREFETCH_WORKER_THREAD_POLICY,
    }


def _tensor_to_device(
    tensor: torch.Tensor,
    device: torch.device,
    *,
    pin_memory: bool,
    non_blocking: bool,
) -> torch.Tensor:
    if pin_memory and device.type == "cuda":
        tensor = tensor.pin_memory()
    return tensor.to(device, non_blocking=non_blocking)


def _run_pair(
    *,
    data_root: Path,
    config_path: Path,
    subset_manifest_path: Path,
    ranked_path: Path,
    simulation_path: Path,
    output_root: Path,
    budget_key: str,
    seed: int,
    device: torch.device,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    manifest = json.loads(subset_manifest_path.read_text(encoding="utf-8"))
    _preflight_data_bindings(data_root, manifest)
    train_rows, val_rows, manifest = _load_subset_rows(
        data_root, subset_manifest_path, ranked_path, budget_key
    )
    selected_by_material = {str(row["material_id"]): row for row in train_rows}
    train_records = [
        _record_from_split(selected_by_material[mid], data_root)
        for mid in manifest["budgets"][budget_key]["material_ids"]
    ]
    validation_records = [
        _record_from_split(row, data_root)
        for row in sorted(val_rows, key=lambda item: str(item["material_id"]))
    ]
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    sim_hash = normalized_text_file_hash(simulation_path)
    sampler = PhysicsParameterSampler.from_mapping({**simulation, "run_seed": int(seed)})
    if "train" not in sampler.profiles:
        raise ValueError("frozen simulation config is missing train profile")
    model_config = ML4PXRDResNet1DConfig(model_id="18")
    steps = int(config["training"]["optimizer_steps_per_model"])
    batch_size = int(config["training"]["batch_size_parents"])
    validation_interval = int(config["training"]["validation_interval_steps"])
    eval_seed = int(config["evaluation"]["validation_evaluation_seed"])
    expected = expected_exposure(steps, batch_size)
    try:
        code_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT.parent, text=True
        ).strip()
    except Exception:
        code_commit = None

    run_dir = output_root / f"seed_{seed}" / f"parents_{BUDGETS[budget_key]}"
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"pair output already exists; no implicit resume: {run_dir}")
    run_dir.mkdir(parents=True, exist_ok=True)
    cache_root = output_root / "evaluation_cache"
    full_split_rows = load_split_rows(data_root)
    _, val_panels, val_labels = _ensure_eval_cache(
        data_root=data_root,
        cache_root=cache_root,
        split_rows=full_split_rows,
        simulation=simulation,
        simulation_config_sha256=sim_hash,
        eval_seeds=[eval_seed],
        profiles=PROFILES[:7],
        split="validation",
        input_length=model_config.input_length,
    )

    runtime = _configure_training_runtime(config, device)
    torch.manual_seed(int(seed))
    np.random.seed(int(seed))
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(int(seed))
    base_model = build_model(model_config)
    model_erm = copy.deepcopy(base_model).to(device)
    model_js = copy.deepcopy(base_model).to(device)
    del base_model
    optimizer_options = {
        "lr": float(config["training"]["learning_rate"]),
        "weight_decay": float(config["training"]["weight_decay"]),
        "fused": runtime["fused_adamw"],
    }
    optimizers = {
        "dynamic_erm": torch.optim.AdamW(model_erm.parameters(), **optimizer_options),
        "dynamic_js": torch.optim.AdamW(model_js.parameters(), **optimizer_options),
    }
    modes = {
        "dynamic_erm": TrainingStepConfig(mode=TrainingMode.DYNAMIC_ERM, lambda_js=0.0),
        "dynamic_js": TrainingStepConfig(
            mode=TrainingMode.DYNAMIC_JS, lambda_js=float(config["matrix"]["lambda_js"])
        ),
    }
    models = {"dynamic_erm": model_erm, "dynamic_js": model_js}
    run_metadata = {
        "schema_version": "parent-budget-paired-run-v1",
        "budget_percent": int(budget_key),
        "unique_parent_count": len(train_records),
        "training_seed": int(seed),
        "methods": ["dynamic_erm", "dynamic_js"],
        "initial_weights_shared": True,
        "paired_batch_rendering": True,
        "lambda_js": float(config["matrix"]["lambda_js"]),
        "training_steps_per_method": steps,
        "batch_size_parents": batch_size,
        "expected_exposure_per_method": expected,
        "data_subset_sha256": manifest["budgets"][budget_key]["ordered_parent_ids_sha256"],
        "parent_subset_manifest_sha256": normalized_text_file_hash(subset_manifest_path),
        "ranked_train_file_sha256": normalized_text_file_hash(ranked_path),
        "simulation_config_sha256": sim_hash,
        "text_config_hash_basis": "UTF-8 file bytes with CRLF/CR normalized to LF before SHA-256",
        "protocol_config_sha256": normalized_text_file_hash(config_path),
        "source_code_sha256": {
            "runner": sha256_file(Path(__file__)),
            "subset_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "parent_budget_efficiency.py"),
            "objective_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "training" / "objectives.py"),
            "paired_update_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "training" / "paired.py"),
            "model_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "models" / "ml4pxrd_resnet1d.py"),
            "online_views_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "online_views.py"),
            "physics_module": sha256_file(PROJECT_ROOT / "src" / "xrd_robustness" / "physics.py"),
        },
        "code_commit": code_commit,
        "validation_selection": config["training"]["checkpoint_selection"],
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "performance_runtime": runtime,
        "started_unix_time": time.time(),
    }
    _write_json_atomic(run_dir / "resolved_config.json", run_metadata)
    sampler_order = CyclicParentSampler(train_rows, seed=int(seed))
    rolling_samples = hashlib.sha256()
    rolling_views = hashlib.sha256()
    representative_steps = {1, validation_interval, steps // 2, steps}
    representative: dict[str, Any] = {}
    history: list[dict[str, Any]] = []
    best_scores: dict[str, tuple[float, float, int]] = {
        method: (float("-inf"), float("-inf"), 0) for method in models
    }
    view_count = 0
    parent_occurrences = 0
    render_calls = 0
    prefetch_wait_seconds = 0.0
    start_time = time.monotonic()
    prefetch = config["performance"]["dynamic_prefetch"]
    prefetcher = DynamicBatchPrefetcher(
        worker_count=int(prefetch["worker_processes"]),
        worker_native_threads=int(prefetch["worker_native_threads"]),
        prefetch_batches=int(prefetch["prefetch_batches"]),
        start_method=str(prefetch["multiprocessing_start_method"]),
        data_root=data_root,
        peak_cache_name=str(prefetch["peak_cache_name"]),
        sampler_config={**simulation, "run_seed": int(seed)},
        quality_gate=bool(prefetch["quality_gate"]),
        quality_gate_config=simulation.get("quality_gates", {}),
        simulation_config_hash=sim_hash,
        profile="train",
    )
    batch_by_step: dict[int, list[PeakRecord]] = {}

    def submit_batch(step_index: int) -> None:
        batch_rows = sampler_order.next_batch(batch_size)
        batch = [_record_from_split(row, data_root) for row in batch_rows]
        material_ids = [record.material_id for record in batch]
        parameter_rows = build_parameter_batch(
            material_ids,
            sampler,
            profile="train",
            epoch=0,
            global_step=step_index,
            split="train",
        )
        prefetcher.submit(step_index, material_ids, parameter_rows)
        batch_by_step[step_index] = batch

    try:
        window = int(prefetch["prefetch_batches"])
        for step_index in range(min(window, steps)):
            submit_batch(step_index)
        for step_index in range(steps):
            wait_started = time.monotonic()
            rendered = prefetcher.get(step_index)
            prefetch_wait_seconds += time.monotonic() - wait_started
            batch = batch_by_step.pop(step_index)
            expected_ids = tuple(record.material_id for record in batch)
            if rendered.material_ids != expected_ids:
                raise RuntimeError("prefetch result changed the frozen parent order")
            next_index = step_index + window
            if next_index < steps:
                submit_batch(next_index)

            x1_cpu = torch.from_numpy(np.asarray(rendered.first, dtype=np.float32))
            x2_cpu = torch.from_numpy(np.asarray(rendered.second, dtype=np.float32))
            target_cpu = torch.tensor([record.label for record in batch], dtype=torch.long)
            sample_hash, view_hash = _batch_digest(
                step_index + 1, batch, x1_cpu, x2_cpu, target_cpu
            )
            rolling_samples.update(bytes.fromhex(sample_hash))
            rolling_views.update(bytes.fromhex(view_hash))
            if step_index + 1 in representative_steps:
                representative[str(step_index + 1)] = {
                    "sample_hash": sample_hash,
                    "paired_two_view_hash": view_hash,
                    "material_ids": list(expected_ids),
                    "accepted_parameter_rows_sha256": sha256_bytes(
                        canonical_json_bytes(
                            [row.to_dict() for row in rendered.accepted_rows]
                        )
                    ),
                }
            x1 = _tensor_to_device(
                x1_cpu,
                device,
                pin_memory=bool(prefetch["pin_memory"]),
                non_blocking=bool(prefetch["non_blocking_h2d"]),
            )
            x2 = _tensor_to_device(
                x2_cpu,
                device,
                pin_memory=bool(prefetch["pin_memory"]),
                non_blocking=bool(prefetch["non_blocking_h2d"]),
            )
            target = _tensor_to_device(
                target_cpu,
                device,
                pin_memory=bool(prefetch["pin_memory"]),
                non_blocking=bool(prefetch["non_blocking_h2d"]),
            )
            amp_dtype = torch.bfloat16 if runtime["amp_enabled"] else None
            paired_results = paired_optimizer_step(
                models,
                optimizers,
                modes,
                x1=x1,
                x2=x2,
                target=target,
                autocast_dtype=amp_dtype,
            )
            losses_device: dict[str, dict[str, torch.Tensor]] = {
                method: {
                    name: result[name].detach().float()
                    for name in ("classification", "consistency", "total")
                }
                for method, result in paired_results.items()
            }
            render_calls += batch_size
            parent_occurrences += batch_size
            view_count += 2 * batch_size

            global_step = step_index + 1
            if global_step % validation_interval == 0 or global_step == steps:
                losses = {
                    method: {
                        name: float(value.cpu()) for name, value in method_losses.items()
                    }
                    for method, method_losses in losses_device.items()
                }
                checkpoint_row: dict[str, Any] = {"global_step": global_step, "training": losses}
                for method, model in models.items():
                    val_metrics = _evaluate_model(
                        model,
                        val_panels,
                        val_labels,
                        seeds=[eval_seed],
                        profiles=PROFILES[:7],
                        batch_size=int(config["evaluation"]["batch_size"]),
                        device=device,
                        # Match the frozen evaluation convention: BF16 is used for
                        # training only; validation and Test inference stay FP32.
                        amp_dtype=None,
                        pin_memory=bool(prefetch["pin_memory"]),
                        non_blocking_h2d=bool(prefetch["non_blocking_h2d"]),
                    )
                    ood_score, inrange_score = _validation_selection(val_metrics, eval_seed)
                    score_tuple = (ood_score, inrange_score, -global_step)
                    previous = best_scores[method]
                    improved = score_tuple > (previous[0], previous[1], -previous[2])
                    if improved:
                        best_scores[method] = (ood_score, inrange_score, global_step)
                        save_checkpoint(
                            run_dir / f"{method}.best.ckpt",
                            model=model,
                            optimizers=[optimizers[method]],
                            epoch=0,
                            global_step=global_step,
                            config=model_config,
                            data_manifest_hash=manifest["budgets"][budget_key]["ordered_parent_ids_sha256"],
                            view_manifest_hash=sim_hash,
                            seed=int(seed),
                            provenance={
                                "pair_run_id": f"seed_{seed}_parents_{BUDGETS[budget_key]}",
                                "training_mode": method,
                                "parent_budget_manifest_sha256": sha256_file(subset_manifest_path),
                                "source_records_sha256": manifest["source"]["records_sha256"],
                                "official_split_manifest_sha256": manifest["source"]["split_manifest_sha256"],
                            },
                            extra_state={
                                "training_mode": method,
                                "lambda_js": float(config["matrix"]["lambda_js"] if method == "dynamic_js" else 0.0),
                                "budget_percent": int(budget_key),
                                "best_validation_single_factor_ood_macro_f1": ood_score,
                                "validation_in_range_macro_f1": inrange_score,
                            },
                        )
                    save_checkpoint(
                        run_dir / f"{method}.last.ckpt",
                        model=model,
                        optimizers=[optimizers[method]],
                        epoch=0,
                        global_step=global_step,
                        config=model_config,
                        data_manifest_hash=manifest["budgets"][budget_key]["ordered_parent_ids_sha256"],
                        view_manifest_hash=sim_hash,
                        seed=int(seed),
                        provenance={
                            "pair_run_id": f"seed_{seed}_parents_{BUDGETS[budget_key]}",
                            "training_mode": method,
                            "parent_budget_manifest_sha256": sha256_file(subset_manifest_path),
                            "source_records_sha256": manifest["source"]["records_sha256"],
                            "official_split_manifest_sha256": manifest["source"]["split_manifest_sha256"],
                        },
                        extra_state={"training_mode": method, "budget_percent": int(budget_key)},
                    )
                    checkpoint_row[method] = {
                        "validation": val_metrics,
                        "selection_score": ood_score,
                        "in_range_macro_f1": inrange_score,
                        "best_checkpoint_updated": improved,
                    }
                history.append(checkpoint_row)
                _write_json_atomic(run_dir / "validation_history.json", history)
                print(
                    json.dumps(
                        {
                            "event": "validation",
                            "seed": seed,
                            "budget_percent": int(budget_key),
                            "step": global_step,
                            "erm_ood_macro_f1": checkpoint_row["dynamic_erm"]["selection_score"],
                            "js_ood_macro_f1": checkpoint_row["dynamic_js"]["selection_score"],
                            "elapsed_seconds": round(time.monotonic() - start_time, 1),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
    finally:
        prefetcher.close()

    actual = {
        "optimizer_steps_per_method": global_step,
        "parent_occurrences_per_method": parent_occurrences,
        "rendered_parent_pairs": render_calls,
        "views_per_method": view_count,
        "batch_size": batch_size,
        "full_batches_only": True,
        "expected": expected,
        "samples_stream_sha256": rolling_samples.hexdigest().upper(),
        "paired_two_view_stream_sha256": rolling_views.hexdigest().upper(),
        "representative_batches": representative,
        "same_shared_batch_for_erm_and_js": True,
        "rendered_once_for_pair": True,
        "prefetch_wait_seconds": prefetch_wait_seconds,
        "views_per_optimizer_step": batch_size * 2,
        "prefetch_quality_gate_checked_count": prefetcher.quality_gate_checked_count,
        "prefetch_quality_gate_rejected_count": prefetcher.quality_gate_rejected_count,
    }
    if actual["optimizer_steps_per_method"] != expected["optimizer_steps"]:
        raise AssertionError("actual optimizer-step count differs from frozen budget")
    if actual["parent_occurrences_per_method"] != expected["parent_occurrences"]:
        raise AssertionError("actual parent occurrence count differs from frozen budget")
    if actual["views_per_method"] != expected["views"]:
        raise AssertionError("actual view count differs from frozen budget")
    run_result = {
        **run_metadata,
        "status": "completed",
        "elapsed_seconds": time.monotonic() - start_time,
        "paired_optimizer_steps_per_second": global_step / max(time.monotonic() - start_time, 1e-9),
        "actual_exposure": actual,
        "best_validation": {
            method: {
                "single_factor_ood_macro_f1": best_scores[method][0],
                "in_range_macro_f1": best_scores[method][1],
                "selected_step": best_scores[method][2],
            }
            for method in models
        },
        "validation_history_path": "validation_history.json",
    }
    _write_json_atomic(run_dir / "result.json", run_result)
    return run_result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--budget", choices=("10", "25", "50", "100"), required=True)
    parser.add_argument("--seed", type=int, choices=(20260711, 20260712, 20260713, 20260714, 20260715), required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument(
        "--protocol-config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "parent_budget_efficiency.v1.json",
    )
    parser.add_argument(
        "--subset-manifest",
        type=Path,
        default=PROJECT_ROOT / "manifests" / "parent_budget_efficiency" / "parent_subsets.v1.json",
    )
    parser.add_argument(
        "--ranked-parents",
        type=Path,
        default=PROJECT_ROOT / "manifests" / "parent_budget_efficiency" / "ranked_train_parents.v1.csv",
    )
    parser.add_argument(
        "--simulation-config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "simulation.method_transfer.frozen.json",
    )
    args = parser.parse_args()
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    result = _run_pair(
        data_root=args.data_root.resolve(),
        config_path=args.protocol_config.resolve(),
        subset_manifest_path=args.subset_manifest.resolve(),
        ranked_path=args.ranked_parents.resolve(),
        simulation_path=args.simulation_config.resolve(),
        output_root=args.output_root.resolve(),
        budget_key=args.budget,
        seed=args.seed,
        device=device,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
