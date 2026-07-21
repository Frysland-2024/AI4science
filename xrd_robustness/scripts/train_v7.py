#!/usr/bin/env python3
"""Unified V7 training entry point for matched baseline and candidate modes."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import platform
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.evaluation import (
    classification_metrics,
    frozen_model_residuals,
    paired_view_metrics,
    robustness_auc,
    train_posthoc_residual_probe,
)
from xrd_robustness.experiment import (
    assert_checkpoint_provenance,
    assert_model_fingerprint,
    config_hash,
    file_hash,
    load_checkpoint,
    model_fingerprint,
    save_checkpoint,
)
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory, TrainingMode
from xrd_robustness.peak_cache import load_peak_table, validate_peak_cache_manifest
from xrd_robustness.physics import PhysicsParameterSampler, validate_formal_simulation_config
from xrd_robustness.perturbation_strategy import (
    IndependentDynamicStrategy,
    strategy_descriptor,
)
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS, select_nested_structure_records
from xrd_robustness.training import (
    PerturbationDeltaRegressor,
    PerturbationTargetConfig,
    ResidualClassifier,
    TrainingStepConfig,
    pilot_perturbation_delta,
    run_training_step,
    signed_measurement_residual,
)
from xrd_robustness.training_stream import (
    TRAINING_STREAM_SCHEMA_VERSION,
    TrainingStreamAudit,
    build_training_sampler_contract,
    deterministic_epoch_shuffle,
    epoch_shuffle_hash,
    paired_manifest_ids,
    select_epoch_batch,
    training_sampler_contract_hash,
)
from xrd_robustness.training_prefetch import (
    PREFETCH_GENERATION,
    PREFETCH_RESULT_ORDER,
    PREFETCH_SHARDING_ALGORITHM,
    PREFETCH_WORKER_THREAD_POLICY,
    PREFETCH_WORKER_PEAK_CACHE,
    QUALITY_GATE_MAX_ATTEMPTS,
    QUALITY_GATE_RETRY_ALGORITHM,
    QUALITY_GATE_RETRY_VIEW_STRIDE,
    DynamicBatchPrefetcher,
    FixedBatchPrefetcher,
    render_dynamic_batch,
    render_fixed_batch,
)
from xrd_robustness.view_manifest import (
    ViewManifestRow,
    build_offline_view_manifest,
    build_parameter_batch,
    build_parameter_stream,
    index_manifest,
    save_manifest,
)
from xrd_robustness.data_layout import project_relative_path, resolve_data_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=[mode.value for mode in TrainingMode if mode.name != "FIXED_VIEW_ERM"])
    parser.add_argument("--simulation-config", required=True)
    parser.add_argument("--train-profile", required=True)
    parser.add_argument("--in-range-profile", required=True)
    parser.add_argument("--ood-profiles", required=True, help="comma-separated profile names")
    parser.add_argument("--variant", default="b3", choices=["b0", "b1", "b2", "b3"])
    parser.add_argument("--dataset-size", type=int, choices=[140, 3500, 14000, 14060], default=140)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument(
        "--split-manifest",
        help=(
            "optional authoritative structure-level split overlay; required by V9-T "
            "to keep the immutable formal_14060 records/cache while using its frozen family split"
        ),
    )
    parser.add_argument(
        "--peak-cache-name",
        default="peak_tables_v7_reflection",
        help="versioned directory below <data-root>/mp_processed",
    )
    parser.add_argument("--expected-model-config-hash")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--max-optimizer-steps", type=int, help="fixed V7 training budget; cycles full batches deterministically")
    parser.add_argument("--validation-interval-steps", type=int, default=0)
    parser.add_argument(
        "--evaluation-batch-size",
        type=int,
        default=1,
        help="batch size for validation/test inference",
    )
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--dynamic-prefetch-workers",
        type=int,
        default=0,
        help=(
            "persistent CPU workers for dynamic and fixed Clean/Offline view rendering; "
            "zero keeps the sequential fallback"
        ),
    )
    parser.add_argument(
        "--dynamic-prefetch-batches",
        type=int,
        default=6,
        help="maximum number of deterministic training batches generated ahead of consumption",
    )
    parser.add_argument(
        "--dynamic-prefetch-worker-native-threads",
        type=int,
        default=1,
        help="native NumPy/BLAS threads allowed inside each training-view worker",
    )
    parser.add_argument(
        "--dynamic-prefetch-start-method",
        default="spawn",
        choices=["spawn"],
        help="portable multiprocessing start method used by training-view workers",
    )
    parser.add_argument(
        "--pin-memory",
        action="store_true",
        help="stage training batches in page-locked host memory before CUDA transfer",
    )
    parser.add_argument(
        "--non-blocking-h2d",
        action="store_true",
        help="use non-blocking host-to-device copies; requires --pin-memory",
    )
    parser.add_argument(
        "--main-process-intraop-threads",
        type=int,
        default=0,
        help="PyTorch intra-op threads in the training process; zero keeps the runtime default",
    )
    parser.add_argument(
        "--main-process-interop-threads",
        type=int,
        default=0,
        help="PyTorch inter-op threads in the training process; zero keeps the runtime default",
    )
    parser.add_argument(
        "--float32-matmul-precision",
        choices=["highest", "high", "medium"],
        default="highest",
        help="PyTorch float32 matrix-multiplication precision policy",
    )
    parser.add_argument(
        "--allow-tf32",
        action="store_true",
        help="allow TF32 matrix multiplication and cuDNN kernels on supported CUDA GPUs",
    )
    parser.add_argument(
        "--cudnn-benchmark",
        action="store_true",
        help="benchmark fixed-shape cuDNN kernels once and reuse the fastest choice",
    )
    parser.add_argument(
        "--cudnn-deterministic",
        action="store_true",
        help="restrict cuDNN to deterministic algorithms",
    )
    parser.add_argument(
        "--fused-adamw",
        action="store_true",
        help="use the fused CUDA AdamW implementation",
    )
    parser.add_argument(
        "--amp",
        action="store_true",
        help="enable CUDA automatic mixed precision for model forward passes",
    )
    parser.add_argument(
        "--amp-dtype",
        choices=["bfloat16"],
        default="bfloat16",
        help="registered autocast dtype; BF16 does not require gradient scaling",
    )
    parser.add_argument(
        "--amp-fallback-to-float32",
        action="store_true",
        help="fall back to float32 when the target CUDA device lacks BF16 support",
    )
    parser.add_argument(
        "--torch-compile",
        action="store_true",
        help="compile trainable modules with torch.compile before the first training step",
    )
    parser.add_argument("--torch-compile-backend", default="inductor")
    parser.add_argument(
        "--torch-compile-mode",
        choices=["default", "reduce-overhead", "max-autotune"],
        default="default",
    )
    parser.add_argument("--torch-compile-fullgraph", action="store_true")
    parser.add_argument("--torch-compile-dynamic", action="store_true")
    parser.add_argument(
        "--torch-compile-fallback-to-eager",
        action="store_true",
        help="allow Dynamo/Inductor graph failures to fall back to eager execution",
    )
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument(
        "--evaluation-seed",
        type=int,
        help="fixed evaluation-panel seed, independent of the training seed",
    )
    parser.add_argument(
        "--development-subset-manifest",
        help="optional frozen CSV containing the unified Validation material IDs",
    )
    parser.add_argument("--study-contract", help="machine-readable study contract recorded by hash")
    parser.add_argument("--evaluation-contract", help="frozen evaluation contract recorded by hash")
    parser.add_argument("--run-id", help="pre-registered run identifier")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--lambda-js", type=float, default=0.1)
    parser.add_argument("--lambda-res", type=float, default=0.1)
    parser.add_argument("--lambda-perturb", type=float, default=1.0)
    parser.add_argument("--residual-head-depth", type=int, choices=[1, 2], default=1)
    parser.add_argument("--perturbation-head-depth", type=int, choices=[1, 2], default=1)
    parser.add_argument("--zero-shift-target-scale-deg", type=float, default=0.2)
    parser.add_argument("--log-fwhm-target-scale", type=float, default=1.0)
    parser.add_argument("--warmup-epochs", type=int, default=5)
    parser.add_argument("--ramp-epochs", type=int, default=5)
    parser.add_argument("--offline-views", type=int, default=4)
    parser.add_argument(
        "--clean-profile",
        default="level0",
        help="fixed minimally perturbed profile used by clean_erm",
    )
    parser.add_argument(
        "--paired-offline-views",
        action="store_true",
        help="V7 fairness mode: consume two deterministic fixed offline views per optimizer step",
    )
    parser.add_argument("--probe-epochs", type=int, default=50)
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cuda", "cpu", "auto"],
        help="training device; GPU is the default, use cpu only for an explicit comparison",
    )
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs"))
    parser.add_argument(
        "--run-dir-exact",
        action="store_true",
        help="write artifacts directly into --output-dir (used by the V7 matrix runner)",
    )
    parser.add_argument(
        "--development-only",
        action="store_true",
        help=(
            "lock the simulated test split: build in-range/OOD panels from validation "
            "structures and keep test structures entirely out of training artifacts"
        ),
    )
    parser.add_argument(
        "--resume",
        help="resume from a checkpoint; the checkpoint directory is reused and manifests are regenerated deterministically",
    )
    return parser.parse_args()


def _load_records(
    dataset_size: int,
    data_root: Path,
    split_manifest: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    path = data_root / "mp_processed" / "structure_records.jsonl"
    all_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_id = {str(row["material_id"]): row for row in all_rows}
    if len(by_id) != len(all_rows):
        raise ValueError("structure records contain duplicate material IDs")
    if dataset_size == 14060:
        if len(all_rows) != dataset_size:
            raise ValueError(
                f"formal_14060 root contains {len(all_rows)} records, expected {dataset_size}"
            )
        rows = all_rows
    else:
        rows = select_nested_structure_records(all_rows, dataset_size=dataset_size)
    selected = {str(row["material_id"]): dict(row) for row in rows}
    if split_manifest is None:
        return selected

    import csv

    manifest = Path(split_manifest).resolve()
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        split_rows = list(csv.DictReader(handle))
    split_by_id: dict[str, dict[str, str]] = {}
    for split_row in split_rows:
        material_id = str(split_row.get("material_id", "")).strip()
        if not material_id or material_id in split_by_id:
            raise ValueError("split manifest contains a missing or duplicate material_id")
        split = str(split_row.get("split", ""))
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"split manifest contains invalid split: {split!r}")
        split_by_id[material_id] = split_row
    if set(split_by_id) != set(selected):
        missing = sorted(set(selected) - set(split_by_id))
        extras = sorted(set(split_by_id) - set(selected))
        raise ValueError(
            f"split manifest IDs do not match selected records; missing={missing[:3]}, extras={extras[:3]}"
        )
    for material_id, row in selected.items():
        split_row = split_by_id[material_id]
        if str(split_row.get("structure_fingerprint")) != str(row["structure_fingerprint"]):
            raise ValueError(f"split manifest fingerprint mismatch: {material_id}")
        if str(split_row.get("crystal_system")) != str(row["crystal_system"]):
            raise ValueError(f"split manifest crystal-system mismatch: {material_id}")
        row["split"] = str(split_row["split"])
    return selected


def _load_development_subset(
    path: str | Path,
    records: dict[str, dict[str, Any]],
) -> tuple[list[str], str]:
    import csv

    manifest = Path(path).resolve()
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [str(row.get("material_id", "")).strip() for row in rows]
    if not ids or any(not material_id for material_id in ids):
        raise ValueError("development subset manifest must contain material_id rows")
    if len(ids) != len(set(ids)):
        raise ValueError("development subset manifest contains duplicate material IDs")
    missing = sorted(set(ids) - set(records))
    if missing:
        raise ValueError(f"development subset contains unknown material IDs: {missing[:3]}")
    wrong_split = sorted(
        material_id for material_id in ids if records[material_id]["split"] != "validation"
    )
    if wrong_split:
        raise ValueError(f"development subset contains non-validation IDs: {wrong_split[:3]}")
    systems = {str(records[material_id]["crystal_system"]) for material_id in ids}
    if systems != set(CRYSTAL_SYSTEMS):
        raise ValueError("development subset must cover all seven crystal systems")
    return sorted(ids), file_hash(manifest)


def _labels(ids: list[str], records: dict[str, dict[str, Any]]) -> torch.Tensor:
    return torch.tensor([CRYSTAL_SYSTEMS.index(records[item]["crystal_system"]) for item in ids], dtype=torch.long)


def _configure_hardware_runtime(
    args: argparse.Namespace,
    device: torch.device,
) -> dict[str, Any]:
    if args.main_process_intraop_threads > 0:
        torch.set_num_threads(args.main_process_intraop_threads)
    if args.main_process_interop_threads > 0:
        torch.set_num_interop_threads(args.main_process_interop_threads)
    torch.set_float32_matmul_precision(args.float32_matmul_precision)
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = bool(args.allow_tf32)
        torch.backends.cudnn.allow_tf32 = bool(args.allow_tf32)
        torch.backends.cudnn.benchmark = bool(args.cudnn_benchmark)
        torch.backends.cudnn.deterministic = bool(args.cudnn_deterministic)
    amp_enabled = False
    amp_fallback_reason = None
    if args.amp:
        if device.type != "cuda":
            raise SystemExit("--amp requires a CUDA device")
        if args.amp_dtype != "bfloat16":
            raise SystemExit("only bfloat16 AMP is registered for this study")
        if torch.cuda.is_bf16_supported():
            amp_enabled = True
        elif args.amp_fallback_to_float32:
            amp_fallback_reason = "cuda_device_does_not_support_bfloat16"
        else:
            raise SystemExit(
                "the CUDA device does not support BF16; use --amp-fallback-to-float32 "
                "for an audited FP32 fallback"
            )
    if args.torch_compile and device.type != "cuda":
        raise SystemExit("--torch-compile requires a CUDA device in the registered profile")
    return {
        "main_process_intraop_threads": torch.get_num_threads(),
        "main_process_interop_threads": torch.get_num_interop_threads(),
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "allow_tf32_matmul": (
            bool(torch.backends.cuda.matmul.allow_tf32) if device.type == "cuda" else False
        ),
        "allow_tf32_cudnn": (
            bool(torch.backends.cudnn.allow_tf32) if device.type == "cuda" else False
        ),
        "cudnn_benchmark": (
            bool(torch.backends.cudnn.benchmark) if device.type == "cuda" else False
        ),
        "cudnn_deterministic": (
            bool(torch.backends.cudnn.deterministic) if device.type == "cuda" else False
        ),
        "fused_adamw": bool(args.fused_adamw),
        "automatic_mixed_precision": {
            "requested": bool(args.amp),
            "enabled": amp_enabled,
            "dtype": args.amp_dtype if args.amp else None,
            "gradient_scaler": False,
            "fallback_to_float32": bool(args.amp_fallback_to_float32),
            "fallback_reason": amp_fallback_reason,
        },
        "torch_compile": {
            "requested": bool(args.torch_compile),
            "enabled": False,
            "backend": args.torch_compile_backend if args.torch_compile else None,
            "mode": args.torch_compile_mode if args.torch_compile else None,
            "fullgraph": bool(args.torch_compile_fullgraph),
            "dynamic": bool(args.torch_compile_dynamic),
            "fallback_to_eager": bool(args.torch_compile_fallback_to_eager),
            "initialized_modules": [],
            "initialization_error": None,
        },
    }


def _initialize_torch_compile(
    modules: dict[str, torch.nn.Module],
    args: argparse.Namespace,
    hardware_runtime: dict[str, Any],
) -> None:
    """Compile modules in place while keeping their state-dict/checkpoint identity stable."""

    if not args.torch_compile:
        return
    compile_runtime = hardware_runtime["torch_compile"]
    try:
        if args.torch_compile_fallback_to_eager:
            import torch._dynamo as torch_dynamo

            torch_dynamo.config.suppress_errors = True
        initialized = []
        for name, module in modules.items():
            module.compile(
                backend=args.torch_compile_backend,
                mode=args.torch_compile_mode,
                fullgraph=bool(args.torch_compile_fullgraph),
                dynamic=bool(args.torch_compile_dynamic),
            )
            initialized.append(name)
        compile_runtime["enabled"] = True
        compile_runtime["initialized_modules"] = initialized
    except Exception as error:
        compile_runtime["initialization_error"] = f"{type(error).__name__}: {error}"
        if not args.torch_compile_fallback_to_eager:
            raise SystemExit(
                f"torch.compile initialization failed: {compile_runtime['initialization_error']}"
            ) from error


def _adamw(
    parameters: Any,
    *,
    learning_rate: float,
    weight_decay: float,
    fused: bool,
) -> torch.optim.AdamW:
    return torch.optim.AdamW(
        parameters,
        lr=learning_rate,
        weight_decay=weight_decay,
        fused=fused,
    )


def _tensor_to_device(
    tensor: torch.Tensor,
    device: torch.device,
    *,
    pin_memory: bool = False,
    non_blocking_h2d: bool = False,
) -> torch.Tensor:
    use_pinned_transfer = bool(pin_memory and device.type == "cuda")
    if use_pinned_transfer and not tensor.is_pinned():
        tensor = tensor.pin_memory()
    return tensor.to(
        device,
        non_blocking=bool(non_blocking_h2d and use_pinned_transfer),
    )


def _numpy_batch_to_device(
    values: np.ndarray,
    device: torch.device,
    *,
    pin_memory: bool = False,
    non_blocking_h2d: bool = False,
) -> torch.Tensor:
    return _tensor_to_device(
        torch.from_numpy(np.ascontiguousarray(values)).float(),
        device,
        pin_memory=pin_memory,
        non_blocking_h2d=non_blocking_h2d,
    )


def _make_pair_batch(
    ids: list[str],
    *,
    epoch: int,
    step: int,
    index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    return_parameters: bool = False,
) -> tuple[Any, ...]:
    first, second = [], []
    parameters_first, parameters_second = [], []
    for material_id in ids:
        pair = factory.make_pair_from_manifest(
            peaks[material_id],
            index[(material_id, epoch, step, 1)],
            index[(material_id, epoch, step, 2)],
        )
        first.append(pair.first.xrd)
        second.append(pair.second.xrd)
        parameters_first.append(pair.first.parameters)
        parameters_second.append(pair.second.parameters)
    tensors = (
        torch.from_numpy(np.stack(first)).float().to(device),
        torch.from_numpy(np.stack(second)).float().to(device),
    )
    if return_parameters:
        return tensors + (tuple(parameters_first), tuple(parameters_second))
    return tensors


def _make_pair_batch_from_rows(
    ids: Sequence[str],
    rows: Sequence[ViewManifestRow],
    *,
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    sampler: PhysicsParameterSampler,
    profile: str,
    device: torch.device,
    pin_memory: bool = False,
    non_blocking_h2d: bool = False,
    return_parameters: bool = False,
) -> tuple[Any, ...]:
    """Render one dynamic batch with deterministic quality-gate resampling."""
    rendered = render_dynamic_batch(
        rows[0].global_step if rows else 0,
        ids,
        rows,
        peaks=peaks,
        factory=factory,
        sampler=sampler,
        profile=profile,
    )
    tensors = (
        _numpy_batch_to_device(
            rendered.first,
            device,
            pin_memory=pin_memory,
            non_blocking_h2d=non_blocking_h2d,
        ),
        _numpy_batch_to_device(
            rendered.second,
            device,
            pin_memory=pin_memory,
            non_blocking_h2d=non_blocking_h2d,
        ),
        rendered.accepted_rows,
    )
    if return_parameters:
        return tensors + (rendered.parameters_first, rendered.parameters_second)
    return tensors


def _select_fixed_batch_rows(
    ids: Sequence[str],
    *,
    mode: TrainingMode,
    absolute_step: int,
    offline_views: int,
    paired_offline_views: bool,
    index: dict[tuple[str, int], ViewManifestRow],
) -> tuple[
    tuple[ViewManifestRow, ...],
    tuple[ViewManifestRow, ...] | None,
    tuple[tuple[str, ...], ...],
    int,
]:
    """Resolve the frozen rows and audit identities for one Clean/Offline batch."""

    if mode is TrainingMode.CLEAN_ERM:
        first_view_id = 1
    elif mode is TrainingMode.OFFLINE_ERM:
        first_view_id = (
            absolute_step * (2 if paired_offline_views else 1)
        ) % offline_views + 1
    else:
        raise ValueError(f"fixed-row selection does not support {mode.value}")
    first_rows = tuple(index[(material_id, first_view_id)] for material_id in ids)
    if mode is TrainingMode.CLEAN_ERM:
        second_rows = None
        parameter_pairs = tuple(
            (row.manifest_id, row.manifest_id) for row in first_rows
        )
        views_per_structure = 2
    elif paired_offline_views:
        second_view_id = (first_view_id % offline_views) + 1
        second_rows = tuple(index[(material_id, second_view_id)] for material_id in ids)
        parameter_pairs = tuple(
            (first.manifest_id, second.manifest_id)
            for first, second in zip(first_rows, second_rows, strict=True)
        )
        views_per_structure = 2
    else:
        second_rows = None
        parameter_pairs = tuple((row.manifest_id,) for row in first_rows)
        views_per_structure = 1
    return first_rows, second_rows, parameter_pairs, views_per_structure


def _predict_paired_views(
    model: PAMPT,
    ids: list[str],
    records: dict[str, dict[str, Any]],
    *,
    index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    evaluation_batch_size: int = 1,
) -> dict[str, np.ndarray]:
    if evaluation_batch_size <= 0:
        raise ValueError("evaluation_batch_size must be positive")
    model.eval()
    labels, predictions, probabilities = [], [], []
    first_probabilities, second_probabilities = [], []
    with torch.no_grad():
        for start in range(0, len(ids), evaluation_batch_size):
            batch_ids = ids[start : start + evaluation_batch_size]
            x1, x2 = _make_pair_batch(
                batch_ids,
                epoch=0,
                step=0,
                index=index,
                peaks=peaks,
                factory=factory,
                device=device,
            )
            output1 = model(x1)
            output2 = model(x2)
            first_batch = torch.softmax(output1["logits"], dim=-1).cpu().numpy()
            second_batch = torch.softmax(output2["logits"], dim=-1).cpu().numpy()
            first_probabilities.extend(first_batch)
            second_probabilities.extend(second_batch)
            probabilities.extend(first_batch)
            predictions.extend(first_batch.argmax(axis=1).astype(int).tolist())
            labels.extend(
                CRYSTAL_SYSTEMS.index(records[material_id]["crystal_system"])
                for material_id in batch_ids
            )
    return {
        "labels": np.asarray(labels, dtype=np.int64),
        "predictions": np.asarray(predictions, dtype=np.int64),
        "probabilities": np.stack(probabilities),
        "second_probabilities": np.stack(second_probabilities),
    }


def _evaluate(
    model: PAMPT,
    ids: list[str],
    records: dict[str, dict[str, Any]],
    *,
    index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    evaluation_batch_size: int = 1,
) -> dict[str, Any]:
    prediction = _predict_paired_views(
        model,
        ids,
        records,
        index=index,
        peaks=peaks,
        factory=factory,
        device=device,
        evaluation_batch_size=evaluation_batch_size,
    )
    metrics = classification_metrics(
        prediction["labels"],
        prediction["predictions"],
        probabilities=prediction["probabilities"],
        num_classes=7,
    )
    metrics.update(
        paired_view_metrics(
            prediction["probabilities"],
            prediction["second_probabilities"],
            prediction["labels"],
        )
    )
    return metrics


def _collect_residuals(
    model: PAMPT,
    ids: list[str],
    records: dict[str, dict[str, Any]],
    *,
    index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    evaluation_batch_size: int = 1,
    signed: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    residuals = []
    labels = []
    if evaluation_batch_size <= 0:
        raise ValueError("evaluation_batch_size must be positive")
    for start in range(0, len(ids), evaluation_batch_size):
        batch_ids = ids[start : start + evaluation_batch_size]
        x1, x2 = _make_pair_batch(
            batch_ids,
            epoch=0,
            step=0,
            index=index,
            peaks=peaks,
            factory=factory,
            device=device,
        )
        residuals.append(frozen_model_residuals(model, x1, x2, signed=signed).cpu())
        labels.extend(
            CRYSTAL_SYSTEMS.index(records[material_id]["crystal_system"])
            for material_id in batch_ids
        )
    return torch.cat(residuals), torch.tensor(labels, dtype=torch.long)


def _evaluate_perturbation_decoder(
    model: PAMPT,
    perturbation_regressor: PerturbationDeltaRegressor,
    ids: list[str],
    *,
    index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    target_config: PerturbationTargetConfig,
    evaluation_batch_size: int = 1,
) -> dict[str, Any]:
    if evaluation_batch_size <= 0:
        raise ValueError("evaluation_batch_size must be positive")
    model.eval()
    perturbation_regressor.eval()
    predictions, targets = [], []
    with torch.no_grad():
        for start in range(0, len(ids), evaluation_batch_size):
            batch_ids = ids[start : start + evaluation_batch_size]
            x1, x2, parameters1, parameters2 = _make_pair_batch(
                batch_ids,
                epoch=0,
                step=0,
                index=index,
                peaks=peaks,
                factory=factory,
                device=device,
                return_parameters=True,
            )
            output1 = model(x1)
            output2 = model(x2)
            residual = signed_measurement_residual(
                output1["pooled_embedding"], output2["pooled_embedding"]
            )
            targets.append(
                pilot_perturbation_delta(
                    parameters1,
                    parameters2,
                    config=target_config,
                    device=device,
                    dtype=residual.dtype,
                )
            )
            predictions.append(perturbation_regressor(residual))
    prediction = torch.cat(predictions)
    target = torch.cat(targets)
    error = prediction - target
    per_target_mae = error.abs().mean(dim=0)
    zero_baseline_mae = target.abs().mean()
    per_target_zero_baseline_mae = target.abs().mean(dim=0)
    return {
        "target_names": list(target_config.target_names),
        "sample_count": int(target.shape[0]),
        "mae": float(error.abs().mean()),
        "zero_predictor_mae": float(zero_baseline_mae),
        "mae_skill_vs_zero": float(
            1.0 - error.abs().mean() / zero_baseline_mae.clamp_min(1e-12)
        ),
        "rmse": float(torch.sqrt(torch.mean(error.square()))),
        "per_target_mae": {
            name: float(value)
            for name, value in zip(target_config.target_names, per_target_mae, strict=True)
        },
        "per_target_mae_skill_vs_zero": {
            name: float(1.0 - value / baseline.clamp_min(1e-12))
            for name, value, baseline in zip(
                target_config.target_names,
                per_target_mae,
                per_target_zero_baseline_mae,
                strict=True,
            )
        },
    }


def main() -> int:
    args = parse_args()
    if args.epochs <= 0 or args.batch_size <= 0 or args.evaluation_batch_size <= 0:
        raise SystemExit("epochs and batch-size must be positive")
    if args.dynamic_prefetch_workers < 0:
        raise SystemExit("dynamic-prefetch-workers cannot be negative")
    if args.dynamic_prefetch_worker_native_threads <= 0:
        raise SystemExit("dynamic-prefetch-worker-native-threads must be positive")
    if args.dynamic_prefetch_batches <= 0:
        raise SystemExit("dynamic-prefetch-batches must be positive")
    if args.dynamic_prefetch_workers > args.batch_size:
        raise SystemExit("dynamic-prefetch-workers cannot exceed batch-size")
    if args.non_blocking_h2d and not args.pin_memory:
        raise SystemExit("--non-blocking-h2d requires --pin-memory")
    if args.main_process_intraop_threads < 0 or args.main_process_interop_threads < 0:
        raise SystemExit("main-process thread counts cannot be negative")
    if args.max_optimizer_steps is not None and args.max_optimizer_steps <= 0:
        raise SystemExit("max-optimizer-steps must be positive")
    if args.validation_interval_steps < 0:
        raise SystemExit("validation-interval-steps cannot be negative")
    if args.lambda_js < 0 or args.lambda_res < 0 or args.lambda_perturb < 0:
        raise SystemExit("objective weights must be non-negative")
    target_config = PerturbationTargetConfig(
        zero_shift_scale_deg=args.zero_shift_target_scale_deg,
        log_fwhm_scale=args.log_fwhm_target_scale,
    )
    try:
        target_config.validate()
    except ValueError as error:
        raise SystemExit(f"perturbation target configuration: {error}") from error
    if Path(args.peak_cache_name).name != args.peak_cache_name:
        raise SystemExit("--peak-cache-name must be one directory name")
    simulation_path = Path(args.simulation_config).resolve()
    simulation_config_hash = file_hash(simulation_path)
    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    ood_profiles = [value.strip() for value in args.ood_profiles.split(",") if value.strip()]
    try:
        validate_formal_simulation_config(
            simulation_config,
            train_profile=args.train_profile,
            in_range_profile=args.in_range_profile,
            ood_profiles=ood_profiles,
        )
    except ValueError as error:
        raise SystemExit(f"formal configuration gate: {error}") from error
    try:
        records = _load_records(args.dataset_size, data_root, args.split_manifest)
    except ValueError as error:
        raise SystemExit(f"V7 data gate: {error}") from error
    train_ids = sorted(item for item, row in records.items() if row["split"] == "train")
    validation_ids = sorted(item for item, row in records.items() if row["split"] == "validation")
    test_ids = sorted(item for item, row in records.items() if row["split"] == "test")
    all_ids = sorted(set(train_ids + validation_ids + test_ids))
    if not train_ids or not validation_ids or not test_ids:
        raise SystemExit("active data tier must contain non-empty train, validation, and test splits")
    development_subset_manifest_hash = None
    if args.development_subset_manifest:
        if not args.development_only:
            raise SystemExit("--development-subset-manifest requires --development-only")
        try:
            validation_ids, development_subset_manifest_hash = _load_development_subset(
                args.development_subset_manifest,
                records,
            )
        except ValueError as error:
            raise SystemExit(f"development subset gate: {error}") from error
    evaluation_ids = validation_ids if args.development_only else test_ids
    evaluation_split = "validation" if args.development_only else "test"
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA GPU is required by default, but torch.cuda.is_available() is False")
    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    device = torch.device(device_name)
    if args.fused_adamw and device.type != "cuda":
        raise SystemExit("--fused-adamw requires a CUDA device")
    hardware_runtime = _configure_hardware_runtime(args, device)
    torch.manual_seed(args.seed)
    mode = TrainingMode(args.mode)
    evaluation_seed = int(args.evaluation_seed) if args.evaluation_seed is not None else int(args.seed)
    sampler_config = dict(simulation_config)
    sampler_config["run_seed"] = args.seed
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    evaluation_sampler_config = dict(simulation_config)
    evaluation_sampler_config["run_seed"] = evaluation_seed
    evaluation_sampler = PhysicsParameterSampler.from_mapping(evaluation_sampler_config)
    perturbation_strategy = IndependentDynamicStrategy(
        sampler,
        config_hash=simulation_config_hash,
    )
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        strategy=perturbation_strategy,
    )
    try:
        cache_validation = validate_peak_cache_manifest(
            data_root,
            args.peak_cache_name,
            records,
        )
    except ValueError as error:
        raise SystemExit(f"peak-cache manifest gate: {error}") from error
    peak_cache_manifest_hash = str(cache_validation["manifest_sha256"])
    dynamic_train_mode = mode not in {TrainingMode.CLEAN_ERM, TrainingMode.OFFLINE_ERM}
    main_process_peak_ids = set(validation_ids) | set(evaluation_ids)
    if args.dynamic_prefetch_workers == 0:
        main_process_peak_ids.update(train_ids)
    peaks = {
        material_id: load_peak_table(
            data_root / "mp_processed" / args.peak_cache_name / f"{material_id}.npz"
        )
        for material_id in sorted(main_process_peak_ids)
    }
    steps_per_epoch = math.ceil(len(train_ids) / args.batch_size)
    fixed_budget = args.max_optimizer_steps is not None
    target_optimizer_steps = int(args.max_optimizer_steps) if fixed_budget else args.epochs * steps_per_epoch
    training_epochs = math.ceil(target_optimizer_steps / steps_per_epoch) if fixed_budget else args.epochs
    active_train_profile = args.clean_profile if mode is TrainingMode.CLEAN_ERM else args.train_profile
    sampler_contract = build_training_sampler_contract(
        train_ids,
        seed=args.seed,
        batch_size=args.batch_size,
        steps_per_epoch=steps_per_epoch,
        target_optimizer_steps=target_optimizer_steps,
        full_batches=fixed_budget,
    )
    sampler_contract_hash = training_sampler_contract_hash(sampler_contract)
    run_config = {
        **vars(args),
        "simulation_config": project_relative_path(PROJECT_ROOT, simulation_path),
        "data_root": project_relative_path(PROJECT_ROOT, data_root),
        "split_manifest": (
            project_relative_path(PROJECT_ROOT, Path(args.split_manifest).resolve())
            if args.split_manifest
            else project_relative_path(PROJECT_ROOT, data_root / "manifests" / "split_manifest.csv")
        ),
        "ood_profiles": ood_profiles,
        "device": str(device),
        "max_optimizer_steps": args.max_optimizer_steps,
        "validation_interval_steps": args.validation_interval_steps,
        "unique_train_structures": len(train_ids),
        "simulation_config_hash": simulation_config_hash,
        "peak_cache_manifest_hash": peak_cache_manifest_hash,
        "active_train_profile": active_train_profile,
        "training_sampler_contract_hash": sampler_contract_hash,
        "evaluation_seed": evaluation_seed,
        "development_subset_manifest": (
            project_relative_path(PROJECT_ROOT, Path(args.development_subset_manifest).resolve())
            if args.development_subset_manifest
            else None
        ),
        "development_subset_manifest_hash": development_subset_manifest_hash,
        "perturbation_strategy": strategy_descriptor(perturbation_strategy),
    }
    model_config = PAMPTConfig(variant=args.variant)
    run_config["model_config"] = asdict(model_config)
    run_hash = config_hash(run_config)
    if args.resume:
        resume_path = Path(args.resume).resolve()
        if not resume_path.is_file():
            raise SystemExit(f"resume checkpoint does not exist: {resume_path}")
        run_dir = resume_path.parent
    elif args.run_dir_exact:
        run_dir = Path(args.output_dir)
    else:
        run_dir = Path(args.output_dir) / args.mode / f"{time.strftime('%Y%m%d_%H%M%S')}_{args.seed}_{run_hash[:10]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    resolved_config_path = run_dir / "config_resolved.json"
    resolved_config_path.write_text(
        json.dumps(run_config, indent=2, sort_keys=True), encoding="utf-8"
    )
    resolved_config_hash = file_hash(resolved_config_path)
    active_split_manifest = (
        Path(args.split_manifest).resolve()
        if args.split_manifest
        else data_root / "manifests" / "split_manifest.csv"
    )
    data_manifest_hash = file_hash(active_split_manifest)
    (run_dir / "data_manifest_hash.txt").write_text(data_manifest_hash, encoding="utf-8")
    (run_dir / "peak_cache_manifest_hash.txt").write_text(
        peak_cache_manifest_hash, encoding="utf-8"
    )
    (run_dir / "simulation_config_hash.txt").write_text(
        simulation_config_hash, encoding="utf-8"
    )
    (run_dir / "training_sampler_contract.json").write_text(
        json.dumps(sampler_contract, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "training_sampler_contract_hash.txt").write_text(
        sampler_contract_hash, encoding="utf-8"
    )
    (run_dir / "git_commit.txt").write_text("unavailable: workspace has no git repository\n", encoding="utf-8")

    train_stream_contract = None
    if dynamic_train_mode:
        train_stream_contract = {
            "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
            "sampler_contract_hash": sampler_contract_hash,
            "simulation_config_hash": simulation_config_hash,
            "parameter_seed": args.seed,
            "profile": active_train_profile,
            "view_ids": [1, 2],
            "perturbation_strategy": strategy_descriptor(perturbation_strategy),
            "generation": PREFETCH_GENERATION,
            "dynamic_prefetch": {
                "enabled": args.dynamic_prefetch_workers > 0,
                "worker_processes": args.dynamic_prefetch_workers,
                "worker_native_threads": args.dynamic_prefetch_worker_native_threads,
                "worker_thread_policy": PREFETCH_WORKER_THREAD_POLICY,
                "prefetch_batches": args.dynamic_prefetch_batches,
                "multiprocessing_start_method": args.dynamic_prefetch_start_method,
                "sharding_algorithm": PREFETCH_SHARDING_ALGORITHM,
                "result_order": PREFETCH_RESULT_ORDER,
                "worker_peak_cache": PREFETCH_WORKER_PEAK_CACHE,
                "pin_memory": args.pin_memory,
                "non_blocking_h2d": args.non_blocking_h2d,
                "maximum_live_parameter_rows": (
                    2 * args.batch_size * args.dynamic_prefetch_batches
                    if args.dynamic_prefetch_workers > 0
                    else 2 * args.batch_size
                ),
            },
        }
        train_hash = config_hash(train_stream_contract)
        (run_dir / "train_view_stream_contract.json").write_text(
            json.dumps(train_stream_contract, indent=2, sort_keys=True), encoding="utf-8"
        )
        (run_dir / "train_view_stream_contract_hash.txt").write_text(
            train_hash, encoding="utf-8"
        )
    else:
        train_hash = None
    validation_rows = build_parameter_stream(
        validation_ids,
        evaluation_sampler,
        profile=args.in_range_profile,
        epochs=1,
        steps_per_epoch=1,
        split="validation",
    )
    validation_hash = save_manifest(validation_rows, run_dir / "validation_view_manifest.jsonl")
    validation_index = index_manifest(validation_rows)
    if args.development_only:
        evaluation_hash = validation_hash
        evaluation_index = validation_index
    else:
        test_rows = build_parameter_stream(
            test_ids,
            evaluation_sampler,
            profile=args.in_range_profile,
            epochs=1,
            steps_per_epoch=1,
            split="test",
        )
        evaluation_hash = save_manifest(test_rows, run_dir / "test_view_manifest.jsonl")
        evaluation_index = index_manifest(test_rows)
    ood_indexes: dict[str, dict[tuple[str, int, int, int], ViewManifestRow]] = {}
    ood_hashes = {}
    for profile in ood_profiles:
        rows = build_parameter_stream(
            evaluation_ids,
            evaluation_sampler,
            profile=profile,
            epochs=1,
            steps_per_epoch=1,
            split=evaluation_split,
        )
        ood_indexes[profile] = index_manifest(rows)
        panel_prefix = "development" if args.development_only else "test"
        ood_hashes[profile] = save_manifest(
            rows, run_dir / f"{panel_prefix}_{profile}_view_manifest.jsonl"
        )

    offline_index = None
    if mode in {TrainingMode.CLEAN_ERM, TrainingMode.OFFLINE_ERM}:
        offline_profile = args.clean_profile if mode is TrainingMode.CLEAN_ERM else args.train_profile
        offline_view_count = 1 if mode is TrainingMode.CLEAN_ERM else args.offline_views
        offline_rows = build_offline_view_manifest(
            train_ids,
            sampler,
            profile=offline_profile,
            views_per_material=offline_view_count,
        )
        offline_hash = save_manifest(offline_rows, run_dir / "offline_view_manifest.jsonl")
        offline_index = {(row.material_id, row.view_id): row for row in offline_rows}
    else:
        offline_hash = None

    model = PAMPT(model_config).to(device)
    fingerprint = model_fingerprint(model, model_config)
    if args.expected_model_config_hash:
        assert_model_fingerprint(
            model,
            model_config,
            {
                "backbone_class_name": "PAMPT",
                "model_config_hash": args.expected_model_config_hash,
                "parameter_count": fingerprint["parameter_count"],
            },
        )
    residual_classifier = None
    perturbation_regressor = None
    optimizer_res = None
    optimizer_aux = None
    residual_modes = {
        TrainingMode.DYNAMIC_RESIDUAL,
        TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL,
    }
    if mode in residual_modes:
        residual_classifier = ResidualClassifier(
            model_config.embed_dim, depth=args.residual_head_depth
        ).to(device)
    if mode is TrainingMode.DYNAMIC_RESIDUAL:
        optimizer_res = _adamw(
            residual_classifier.parameters(),
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            fused=args.fused_adamw,
        )
    if mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
        perturbation_regressor = PerturbationDeltaRegressor(
            model_config.embed_dim,
            output_dim=len(target_config.target_names),
            depth=args.perturbation_head_depth,
        ).to(device)
        optimizer_aux = _adamw(
            list(residual_classifier.parameters()) + list(perturbation_regressor.parameters()),
            learning_rate=args.learning_rate,
            weight_decay=args.weight_decay,
            fused=args.fused_adamw,
        )
    optimizer_main = _adamw(
        model.parameters(),
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        fused=args.fused_adamw,
    )
    auxiliary_optimizers = [
        optimizer
        for optimizer in (optimizer_res, optimizer_aux)
        if optimizer is not None
    ]
    extra_modules = {
        name: module
        for name, module in (
            ("residual_classifier", residual_classifier),
            ("perturbation_regressor", perturbation_regressor),
        )
        if module is not None
    }
    view_manifest_hash = config_hash(
        {
            "training_sampler": sampler_contract_hash,
            "train": train_hash,
            "offline": offline_hash,
            "validation": validation_hash,
            "evaluation": evaluation_hash,
            "evaluation_split": evaluation_split,
            **ood_hashes,
        }
    )
    evaluation_manifest_hash = config_hash(
        {
            "validation": validation_hash,
            "evaluation": evaluation_hash,
            "evaluation_split": evaluation_split,
            "evaluation_seed": evaluation_seed,
            "development_subset_manifest_hash": development_subset_manifest_hash,
            **ood_hashes,
        }
    )
    start_epoch = 0
    resume_payload = None
    if args.resume:
        resume_payload = load_checkpoint(
            args.resume,
            model=model,
            optimizers=[optimizer_main] + auxiliary_optimizers,
            extra_modules=extra_modules or None,
            map_location=device,
        )
        start_epoch = int(resume_payload.get("epoch", 0))
        if start_epoch > training_epochs:
            raise SystemExit(
                f"checkpoint epoch {start_epoch} is beyond requested target epochs {training_epochs}"
            )
        current_provenance = {
            "peak_cache_manifest_hash": peak_cache_manifest_hash,
            "simulation_config_hash": simulation_config_hash,
        }
        try:
            assert_checkpoint_provenance(
                resume_payload,
                data_manifest_hash=data_manifest_hash,
                view_manifest_hash=view_manifest_hash,
                provenance=current_provenance,
            )
        except ValueError as error:
            raise SystemExit(f"resume checkpoint gate: {error}") from error

    _initialize_torch_compile(
        {"model": model, **extra_modules},
        args,
        hardware_runtime,
    )

    history_path = run_dir / "history.json"
    if args.resume and history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    else:
        history = []
    if len(history) < start_epoch:
        raise SystemExit(
            "resume checkpoint is ahead of history.json; training stream audit cannot be restored"
        )
    if len(history) > start_epoch:
        history = history[:start_epoch]
        history_path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
    if start_epoch:
        try:
            stream_audit = TrainingStreamAudit.from_snapshot(
                history[-1]["training_stream_audit"],
                sampler_contract_hash=sampler_contract_hash,
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SystemExit(f"resume training-stream audit gate: {error}") from error
        if resume_payload is None or stream_audit.optimizer_steps != int(
            resume_payload.get("global_step", -1)
        ):
            raise SystemExit("resume training-stream audit does not match checkpoint global_step")
    else:
        stream_audit = TrainingStreamAudit.create(sampler_contract_hash)
    stream_audit_path = run_dir / "training_stream_audit.json"
    dynamic_prefetcher = None
    fixed_prefetcher = None
    if args.dynamic_prefetch_workers > 0:
        prefetch_kwargs = {
            "worker_count": args.dynamic_prefetch_workers,
            "worker_native_threads": args.dynamic_prefetch_worker_native_threads,
            "prefetch_batches": args.dynamic_prefetch_batches,
            "start_method": args.dynamic_prefetch_start_method,
            "data_root": data_root,
            "peak_cache_name": args.peak_cache_name,
            "sampler_config": sampler_config,
            "quality_gate": factory.quality_gate,
            "quality_gate_config": factory.quality_gate_config,
            "simulation_config_hash": simulation_config_hash,
            "profile": active_train_profile,
        }
        if dynamic_train_mode:
            dynamic_prefetcher = DynamicBatchPrefetcher(**prefetch_kwargs)
        else:
            fixed_prefetcher = FixedBatchPrefetcher(**prefetch_kwargs)
    training_prefetcher = dynamic_prefetcher or fixed_prefetcher
    rendered_views_per_structure = (
        2
        if dynamic_train_mode
        or (mode is TrainingMode.OFFLINE_ERM and args.paired_offline_views)
        else 1
    )
    training_prefetch_contract = {
        "enabled": training_prefetcher is not None,
        "view_source": "dynamic" if dynamic_train_mode else "fixed_manifest",
        "worker_processes": args.dynamic_prefetch_workers,
        "worker_native_threads": args.dynamic_prefetch_worker_native_threads,
        "worker_thread_policy": PREFETCH_WORKER_THREAD_POLICY,
        "prefetch_batches": args.dynamic_prefetch_batches,
        "multiprocessing_start_method": args.dynamic_prefetch_start_method,
        "sharding_algorithm": PREFETCH_SHARDING_ALGORITHM,
        "result_order": PREFETCH_RESULT_ORDER,
        "worker_peak_cache": PREFETCH_WORKER_PEAK_CACHE,
        "main_process_loads_training_peak_tables": training_prefetcher is None,
        "pin_memory": args.pin_memory,
        "non_blocking_h2d": args.non_blocking_h2d,
        "maximum_live_parameter_rows": (
            rendered_views_per_structure
            * args.batch_size
            * (args.dynamic_prefetch_batches if training_prefetcher is not None else 1)
        ),
    }
    train_started = time.perf_counter()
    training_prefetch_wait_seconds = 0.0
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    for epoch in range(start_epoch, training_epochs):
        model.train()
        if residual_classifier is not None:
            residual_classifier.train()
        if perturbation_regressor is not None:
            perturbation_regressor.train()
        step_losses: list[torch.Tensor] = []
        step_objectives: dict[str, list[torch.Tensor]] = {}
        step_correct = torch.zeros((), dtype=torch.long, device=device)
        step_total = 0
        steps_this_epoch = min(steps_per_epoch, target_optimizer_steps - epoch * steps_per_epoch)
        epoch_order = deterministic_epoch_shuffle(train_ids, seed=args.seed, epoch=epoch)
        epoch_order_hash = epoch_shuffle_hash(epoch_order, seed=args.seed, epoch=epoch)
        epoch_start_steps = stream_audit.optimizer_steps
        epoch_start_structures = stream_audit.structure_exposures
        epoch_start_spectra = stream_audit.spectrum_exposures
        if dynamic_prefetcher is not None:
            for queued_step in range(
                min(args.dynamic_prefetch_batches, steps_this_epoch)
            ):
                queued_ids = list(
                    select_epoch_batch(
                        epoch_order,
                        step=queued_step,
                        batch_size=args.batch_size,
                        full_batch=fixed_budget,
                    )
                )
                queued_rows = build_parameter_batch(
                    queued_ids,
                    sampler,
                    profile=active_train_profile,
                    epoch=epoch,
                    global_step=queued_step,
                    split="train",
                )
                dynamic_prefetcher.submit(
                    epoch * steps_per_epoch + queued_step,
                    queued_ids,
                    queued_rows,
                )
        elif fixed_prefetcher is not None:
            assert offline_index is not None
            for queued_step in range(
                min(args.dynamic_prefetch_batches, steps_this_epoch)
            ):
                queued_ids = list(
                    select_epoch_batch(
                        epoch_order,
                        step=queued_step,
                        batch_size=args.batch_size,
                        full_batch=fixed_budget,
                    )
                )
                queued_key = epoch * steps_per_epoch + queued_step
                queued_first, queued_second, _, _ = _select_fixed_batch_rows(
                    queued_ids,
                    mode=mode,
                    absolute_step=queued_key,
                    offline_views=args.offline_views,
                    paired_offline_views=args.paired_offline_views,
                    index=offline_index,
                )
                fixed_prefetcher.submit(
                    queued_key,
                    queued_ids,
                    queued_first,
                    queued_second,
                )
        for step in range(steps_this_epoch):
            batch_ids = list(
                select_epoch_batch(
                    epoch_order,
                    step=step,
                    batch_size=args.batch_size,
                    full_batch=fixed_budget,
                )
            )
            target = _tensor_to_device(
                _labels(batch_ids, records),
                device,
                pin_memory=args.pin_memory,
                non_blocking_h2d=args.non_blocking_h2d,
            )
            perturbation_delta = None
            if mode in {TrainingMode.CLEAN_ERM, TrainingMode.OFFLINE_ERM}:
                assert offline_index is not None
                absolute_step = epoch * steps_per_epoch + step
                (
                    fixed_first_rows,
                    fixed_second_rows,
                    parameter_pairs_for_audit,
                    views_per_structure,
                ) = _select_fixed_batch_rows(
                    batch_ids,
                    mode=mode,
                    absolute_step=absolute_step,
                    offline_views=args.offline_views,
                    paired_offline_views=args.paired_offline_views,
                    index=offline_index,
                )
                if fixed_prefetcher is not None:
                    prefetch_wait_started = time.perf_counter()
                    rendered_fixed = fixed_prefetcher.get(absolute_step)
                    training_prefetch_wait_seconds += (
                        time.perf_counter() - prefetch_wait_started
                    )
                    refill_step = step + args.dynamic_prefetch_batches
                    if refill_step < steps_this_epoch:
                        refill_ids = list(
                            select_epoch_batch(
                                epoch_order,
                                step=refill_step,
                                batch_size=args.batch_size,
                                full_batch=fixed_budget,
                            )
                        )
                        refill_key = epoch * steps_per_epoch + refill_step
                        refill_first, refill_second, _, _ = _select_fixed_batch_rows(
                            refill_ids,
                            mode=mode,
                            absolute_step=refill_key,
                            offline_views=args.offline_views,
                            paired_offline_views=args.paired_offline_views,
                            index=offline_index,
                        )
                        fixed_prefetcher.submit(
                            refill_key,
                            refill_ids,
                            refill_first,
                            refill_second,
                        )
                    if rendered_fixed.material_ids != tuple(batch_ids):
                        raise RuntimeError(
                            f"fixed prefetch batch identity mismatch at step {absolute_step}"
                        )
                else:
                    rendered_fixed = render_fixed_batch(
                        absolute_step,
                        batch_ids,
                        fixed_first_rows,
                        fixed_second_rows,
                        peaks=peaks,
                        factory=factory,
                    )
                x1 = _numpy_batch_to_device(
                    rendered_fixed.first,
                    device,
                    pin_memory=args.pin_memory,
                    non_blocking_h2d=args.non_blocking_h2d,
                )
                if mode is TrainingMode.CLEAN_ERM:
                    x2 = x1
                elif rendered_fixed.second is not None:
                    x2 = _numpy_batch_to_device(
                        rendered_fixed.second,
                        device,
                        pin_memory=args.pin_memory,
                        non_blocking_h2d=args.non_blocking_h2d,
                    )
                else:
                    x2 = None
            else:
                views_per_structure = 2
                if dynamic_prefetcher is not None:
                    absolute_step = epoch * steps_per_epoch + step
                    prefetch_wait_started = time.perf_counter()
                    rendered = dynamic_prefetcher.get(absolute_step)
                    training_prefetch_wait_seconds += (
                        time.perf_counter() - prefetch_wait_started
                    )
                    refill_step = step + args.dynamic_prefetch_batches
                    if refill_step < steps_this_epoch:
                        refill_ids = list(
                            select_epoch_batch(
                                epoch_order,
                                step=refill_step,
                                batch_size=args.batch_size,
                                full_batch=fixed_budget,
                            )
                        )
                        refill_rows = build_parameter_batch(
                            refill_ids,
                            sampler,
                            profile=active_train_profile,
                            epoch=epoch,
                            global_step=refill_step,
                            split="train",
                        )
                        dynamic_prefetcher.submit(
                            epoch * steps_per_epoch + refill_step,
                            refill_ids,
                            refill_rows,
                        )
                    if rendered.material_ids != tuple(batch_ids):
                        raise RuntimeError(
                            f"dynamic prefetch batch identity mismatch at step {absolute_step}"
                        )
                    x1 = _numpy_batch_to_device(
                        rendered.first,
                        device,
                        pin_memory=args.pin_memory,
                        non_blocking_h2d=args.non_blocking_h2d,
                    )
                    x2 = _numpy_batch_to_device(
                        rendered.second,
                        device,
                        pin_memory=args.pin_memory,
                        non_blocking_h2d=args.non_blocking_h2d,
                    )
                    accepted_dynamic_rows = rendered.accepted_rows
                    parameters1 = rendered.parameters_first
                    parameters2 = rendered.parameters_second
                else:
                    dynamic_rows = build_parameter_batch(
                        batch_ids,
                        sampler,
                        profile=active_train_profile,
                        epoch=epoch,
                        global_step=step,
                        split="train",
                    )
                    pair_batch = _make_pair_batch_from_rows(
                        batch_ids,
                        dynamic_rows,
                        peaks=peaks,
                        factory=factory,
                        sampler=sampler,
                        profile=active_train_profile,
                        device=device,
                        pin_memory=args.pin_memory,
                        non_blocking_h2d=args.non_blocking_h2d,
                        return_parameters=(
                            mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL
                        ),
                    )
                    x1, x2, accepted_dynamic_rows = pair_batch[:3]
                    if mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
                        parameters1, parameters2 = pair_batch[3:]
                parameter_pairs_for_audit = paired_manifest_ids(
                    accepted_dynamic_rows,
                    batch_ids,
                )
                if mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
                    perturbation_delta = pilot_perturbation_delta(
                        parameters1,
                        parameters2,
                        config=target_config,
                        device=device,
                        dtype=x1.dtype,
                    )
                else:
                    perturbation_delta = None
            if mode not in residual_modes:
                optimizer_main.zero_grad(set_to_none=True)
            lambda_res = args.lambda_res if epoch >= args.warmup_epochs else 0.0
            if mode in residual_modes and args.ramp_epochs > 0:
                lambda_res *= min(1.0, (epoch - args.warmup_epochs + 1) / args.ramp_epochs)
            with torch.autocast(
                device_type="cuda",
                dtype=torch.bfloat16,
                enabled=bool(
                    hardware_runtime["automatic_mixed_precision"]["enabled"]
                ),
            ):
                result = run_training_step(
                    TrainingStepConfig(
                        mode=mode,
                        lambda_js=args.lambda_js,
                        lambda_res=lambda_res,
                        lambda_perturb=args.lambda_perturb,
                    ),
                    model,
                    x1=x1,
                    x2=x2,
                    target=target,
                    optimizer_main=optimizer_main,
                    optimizer_res=optimizer_res,
                    optimizer_aux=optimizer_aux,
                    residual_classifier=residual_classifier,
                    perturbation_regressor=perturbation_regressor,
                    perturbation_delta=perturbation_delta,
                )
            if mode not in residual_modes:
                result["total"].backward()
                optimizer_main.step()
            stream_audit.record_batch(
                epoch=epoch,
                step=step,
                absolute_step=epoch * steps_per_epoch + step,
                material_ids=batch_ids,
                parameter_pairs=parameter_pairs_for_audit,
                views_per_structure=views_per_structure,
            )
            step_losses.append(result["total"].detach())
            for name in (
                "classification",
                "consistency",
                "probe",
                "decoder",
                "perturbation",
                "independence",
            ):
                value = result.get(name)
                if value is not None and value.numel() == 1:
                    step_objectives.setdefault(name, []).append(value.detach())
            logits_first = result.get("logits_first")
            if logits_first is not None:
                step_correct += (
                    logits_first.detach().argmax(dim=-1) == target
                ).sum()
                step_total += int(target.numel())
        global_step_total = min((epoch + 1) * steps_per_epoch, target_optimizer_steps)
        should_evaluate = (
            not fixed_budget
            or args.validation_interval_steps <= 0
            or global_step_total % args.validation_interval_steps == 0
            or global_step_total == target_optimizer_steps
        )
        epoch_stream_audit = {
            **stream_audit.snapshot(),
            "epoch": epoch + 1,
            "epoch_shuffle_hash": epoch_order_hash,
            "epoch_optimizer_steps": stream_audit.optimizer_steps - epoch_start_steps,
            "epoch_structure_exposures": (
                stream_audit.structure_exposures - epoch_start_structures
            ),
            "epoch_spectrum_exposures": stream_audit.spectrum_exposures - epoch_start_spectra,
        }
        epoch_result = {
            "epoch": epoch + 1,
            "global_step": global_step_total,
            "train_loss": float(torch.stack(step_losses).mean().cpu()),
            "train_accuracy": float(step_correct.cpu()) / max(1, step_total),
            "train_objectives": {
                name: float(torch.stack(values).mean().cpu())
                for name, values in sorted(step_objectives.items())
            },
            "training_stream_audit": epoch_stream_audit,
        }
        if should_evaluate:
            epoch_result["validation"] = _evaluate(
                model,
                validation_ids,
                records,
                index=validation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
            )
            epoch_result["in_range"] = _evaluate(
                model,
                evaluation_ids,
                records,
                index=evaluation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
            )
            epoch_result["ood"] = {
                profile: _evaluate(
                    model,
                    evaluation_ids,
                    records,
                    index=index,
                    peaks=peaks,
                    factory=factory,
                    device=device,
                    evaluation_batch_size=args.evaluation_batch_size,
                )
                for profile, index in ood_indexes.items()
            }
        history.append(epoch_result)
        history_path.write_text(json.dumps(history, indent=2, sort_keys=True), encoding="utf-8")
        stream_audit_path.write_text(
            json.dumps(
                {
                    "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
                    "sampler_contract": sampler_contract,
                    "sampler_contract_hash": sampler_contract_hash,
                    "epochs": [item["training_stream_audit"] for item in history],
                    "final": epoch_stream_audit,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        save_checkpoint(
            run_dir / "last.ckpt",
            model=model,
            optimizers=[optimizer_main] + auxiliary_optimizers,
            epoch=epoch + 1,
            global_step=global_step_total,
            config=model_config,
            data_manifest_hash=data_manifest_hash,
            view_manifest_hash=view_manifest_hash,
            seed=args.seed,
            extra_modules=extra_modules or None,
            provenance={
                "peak_cache_manifest_hash": peak_cache_manifest_hash,
                "simulation_config_hash": simulation_config_hash,
            },
        )

    if training_prefetcher is not None:
        if training_prefetcher.in_flight_batches:
            raise RuntimeError(
                "training prefetch ended with unconsumed batches: "
                f"{training_prefetcher.in_flight_batches}"
            )
        training_prefetcher.close()

    posthoc_train_probe_hash = None
    posthoc_train_probe_index = None
    if residual_classifier is not None or perturbation_regressor is not None:
        missing_train_peak_ids = [
            material_id for material_id in train_ids if material_id not in peaks
        ]
        peaks.update(
            {
                material_id: load_peak_table(
                    data_root
                    / "mp_processed"
                    / args.peak_cache_name
                    / f"{material_id}.npz"
                )
                for material_id in missing_train_peak_ids
            }
        )
        posthoc_train_probe_rows = build_parameter_stream(
            train_ids,
            sampler,
            profile=active_train_profile,
            epochs=1,
            steps_per_epoch=1,
            split="posthoc_train",
        )
        posthoc_train_probe_hash = save_manifest(
            posthoc_train_probe_rows,
            run_dir / "posthoc_train_probe_view_manifest.jsonl",
        )
        posthoc_train_probe_index = index_manifest(posthoc_train_probe_rows)

    probe_report = None
    if residual_classifier is not None:
        assert posthoc_train_probe_index is not None
        use_signed_residual = mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL
        train_residual, train_labels = _collect_residuals(
            model,
            train_ids,
            records,
            index=posthoc_train_probe_index,
            peaks=peaks,
            factory=factory,
            device=device,
            evaluation_batch_size=args.evaluation_batch_size,
            signed=use_signed_residual,
        )
        if args.development_only:
            split_at = len(validation_ids) // 2
            probe_validation_ids = validation_ids[:split_at]
            probe_holdout_ids = validation_ids[split_at:]
            validation_residual, validation_labels = _collect_residuals(
                model,
                probe_validation_ids,
                records,
                index=validation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
                signed=use_signed_residual,
            )
            test_residual, test_labels = _collect_residuals(
                model,
                probe_holdout_ids,
                records,
                index=validation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
                signed=use_signed_residual,
            )
        else:
            validation_residual, validation_labels = _collect_residuals(
                model,
                validation_ids,
                records,
                index=validation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
                signed=use_signed_residual,
            )
            test_residual, test_labels = _collect_residuals(
                model,
                test_ids,
                records,
                index=evaluation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                evaluation_batch_size=args.evaluation_batch_size,
                signed=use_signed_residual,
            )
        probe_report = train_posthoc_residual_probe(
            train_residual,
            train_labels,
            validation_residual,
            validation_labels,
            test_residual,
            test_labels,
            seed=args.seed,
        )
        probe_report.pop("probe", None)
        probe_report["evaluation_split"] = (
            "validation_holdout" if args.development_only else "test"
        )
        probe_report["simulated_test_used"] = not args.development_only
        probe_report["residual_definition"] = (
            "signed_normalized_second_minus_first"
            if use_signed_residual
            else "absolute_normalized_difference"
        )
    perturbation_decoder_report = None
    if perturbation_regressor is not None:
        assert posthoc_train_probe_index is not None
        perturbation_decoder_report = {
            "train": _evaluate_perturbation_decoder(
                model,
                perturbation_regressor,
                train_ids,
                index=posthoc_train_probe_index,
                peaks=peaks,
                factory=factory,
                device=device,
                target_config=target_config,
                evaluation_batch_size=args.evaluation_batch_size,
            ),
            "validation": _evaluate_perturbation_decoder(
                model,
                perturbation_regressor,
                validation_ids,
                index=validation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                target_config=target_config,
                evaluation_batch_size=args.evaluation_batch_size,
            ),
            "development_or_test": _evaluate_perturbation_decoder(
                model,
                perturbation_regressor,
                evaluation_ids,
                index=evaluation_index,
                peaks=peaks,
                factory=factory,
                device=device,
                target_config=target_config,
                evaluation_batch_size=args.evaluation_batch_size,
            ),
        }
    study_contract_hash = (
        file_hash(Path(args.study_contract).resolve()) if args.study_contract else None
    )
    evaluation_contract_hash = (
        file_hash(Path(args.evaluation_contract).resolve())
        if args.evaluation_contract
        else None
    )
    source_paths = [Path(__file__).resolve(), *sorted((PROJECT_ROOT / "src").rglob("*.py"))]
    source_tree_hash = config_hash(
        {
            project_relative_path(PROJECT_ROOT, path): file_hash(path)
            for path in source_paths
        }
    )
    checkpoint_path = run_dir / "last.ckpt"
    report = {
        "run_id": args.run_id or run_dir.name,
        "mode": args.mode,
        "seed": args.seed,
        "evaluation_seed": evaluation_seed,
        "model": fingerprint,
        "study_contract_hash": study_contract_hash,
        "evaluation_contract_hash": evaluation_contract_hash,
        "resolved_config_hash": resolved_config_hash,
        "source_tree_hash": source_tree_hash,
        "git_commit": "unavailable: workspace has no git repository",
        "data_manifest_hash": data_manifest_hash,
        "development_subset_manifest_hash": development_subset_manifest_hash,
        "peak_cache_manifest_hash": peak_cache_manifest_hash,
        "simulation_config_hash": simulation_config_hash,
        "unique_train_structures": len(train_ids),
        "training_sampler_contract_hash": sampler_contract_hash,
        "training_stream_audit": stream_audit.snapshot(),
        "training_stream_audit_hash": file_hash(stream_audit_path),
        "train_view_stream_contract_hash": train_hash,
        "posthoc_train_probe_manifest_hash": posthoc_train_probe_hash,
        "view_manifest_hash": view_manifest_hash,
        "evaluation_manifest_hash": evaluation_manifest_hash,
        "evaluation_manifest_hashes": {
            "validation": validation_hash,
            "evaluation": evaluation_hash,
            "ood": ood_hashes,
        },
        "checkpoint_hash": file_hash(checkpoint_path),
        "resumed_from": str(Path(args.resume).resolve()) if args.resume else None,
        "quality_gate": {
            "enabled": factory.quality_gate,
            "checked_splits": sorted(factory.quality_gate_splits),
            "checked_view_count": (
                factory.quality_gate_checked_count
                + (
                    training_prefetcher.quality_gate_checked_count
                    if training_prefetcher is not None
                    else 0
                )
            ),
            "rejected_view_count": (
                factory.quality_gate_rejected_count
                + (
                    training_prefetcher.quality_gate_rejected_count
                    if training_prefetcher is not None
                    else 0
                )
            ),
            "deterministic_resampling": {
                "algorithm": QUALITY_GATE_RETRY_ALGORITHM,
                "max_attempts_per_view": QUALITY_GATE_MAX_ATTEMPTS,
                "sampling_view_id_stride": QUALITY_GATE_RETRY_VIEW_STRIDE,
                "accepted_parameter_rows_are_stream_hashed": True,
            },
            "config": factory.quality_gate_config,
        },
        "dynamic_prefetch": (
            train_stream_contract["dynamic_prefetch"]
            if train_stream_contract is not None
            else {
                "enabled": False,
                "reason": "training mode uses the fixed-view prefetch path",
            }
        ),
        "training_prefetch": training_prefetch_contract,
        "offline_manifest_hash": offline_hash,
        "history": history,
        "posthoc_residual_probe": probe_report,
        "perturbation_decoder": perturbation_decoder_report,
        "perturbation_target": (
            {
                "names": list(target_config.target_names),
                "zero_shift_scale_deg": target_config.zero_shift_scale_deg,
                "log_fwhm_scale": target_config.log_fwhm_scale,
                "direction": "second_minus_first",
            }
            if perturbation_regressor is not None
            else None
        ),
        "formal_config": str(simulation_path),
        "metric_contract": {
            "required_classification_metrics": [
                "accuracy",
                "balanced_accuracy",
                "macro_f1",
                "per_class_recall",
                "per_class_f1",
                "confusion_matrix",
                "worst_group_f1",
                "ece",
            ],
            "calibration_bins": 15,
        },
        "runtime_provenance": {
            "python_version": platform.python_version(),
            "torch_version": str(torch.__version__),
            "cuda_runtime": str(torch.version.cuda),
            "device": str(device),
            "gpu_name": (
                torch.cuda.get_device_name(device) if device.type == "cuda" else None
            ),
            "hardware_optimization": hardware_runtime,
            "main_process_initial_peak_table_count": len(main_process_peak_ids),
            "all_structure_peak_table_count": len(all_ids),
        },
        "evaluation_scope": {
            "development_only": bool(args.development_only),
            "selection_split": evaluation_split,
            "simulated_test_locked": bool(args.development_only),
            "real_test_locked": True,
        },
    }
    latest_evaluation = next(
        (item for item in reversed(history) if "in_range" in item and "ood" in item),
        None,
    )
    if latest_evaluation is not None:
        in_range_metrics = latest_evaluation["in_range"]
        ood_metrics = latest_evaluation["ood"]
        severity_values: dict[int, list[float]] = {
            int(simulation_config["profiles"][args.in_range_profile]["severity_level"]): [
                float(in_range_metrics["macro_f1"])
            ]
        }
        for profile_name, metrics in ood_metrics.items():
            severity = int(simulation_config["profiles"][profile_name]["severity_level"])
            severity_values.setdefault(severity, []).append(float(metrics["macro_f1"]))
        severity_curve = sorted(
            (severity, float(np.mean(values)))
            for severity, values in severity_values.items()
        )
        ood_primary = ood_metrics.get("ood_all") or ood_metrics.get("ood_combined")
        if ood_primary is None:
            ood_primary = {
                "macro_f1": float(np.mean([item["macro_f1"] for item in ood_metrics.values()])),
                "worst_group_f1": float(
                    min(item["worst_group_f1"] for item in ood_metrics.values())
                ),
            }
        report["evaluation_summary"] = {
            "in_range_macro_f1": float(in_range_metrics["macro_f1"]),
            "ood_macro_f1": float(ood_primary["macro_f1"]),
            "ood_texture_macro_f1": (
                float(ood_metrics["ood_texture"]["macro_f1"])
                if "ood_texture" in ood_metrics
                else None
            ),
            "worst_group_f1": float(ood_primary["worst_group_f1"]),
            "robustness_auc": (
                robustness_auc(
                    [item[0] for item in severity_curve],
                    [item[1] for item in severity_curve],
                )
                if len(severity_curve) >= 2
                else None
            ),
            "severity_curve": [
                {"severity": severity, "macro_f1": value}
                for severity, value in severity_curve
            ],
            "real_xrd_macro_f1": None,
            "simulated_test_macro_f1": (
                None if args.development_only else float(in_range_metrics["macro_f1"])
            ),
        }
    elapsed = time.perf_counter() - train_started
    training_views_per_step = (
        2 if mode is not TrainingMode.OFFLINE_ERM or args.paired_offline_views else 1
    )
    report["compute_summary"] = {
        "optimizer_steps": stream_audit.optimizer_steps,
        "training_backbone_forward_views": stream_audit.optimizer_steps * training_views_per_step,
        "training_structure_exposures": stream_audit.structure_exposures,
        "training_view_exposures": stream_audit.spectrum_exposures,
        "total_processed_spectra": stream_audit.spectrum_exposures,
        "wall_clock_seconds": elapsed,
        "gpu_hours": elapsed / 3600.0 if device.type == "cuda" else None,
        "peak_gpu_memory_mb": (
            float(torch.cuda.max_memory_allocated(device) / (1024 ** 2)) if device.type == "cuda" else None
        ),
        "training_prefetch_wait_seconds": training_prefetch_wait_seconds,
        "training_prefetch_wait_fraction": (
            training_prefetch_wait_seconds / elapsed
            if training_prefetcher is not None and elapsed > 0
            else None
        ),
        "dynamic_prefetch_wait_seconds": (
            training_prefetch_wait_seconds if dynamic_prefetcher is not None else None
        ),
        "dynamic_prefetch_wait_fraction": (
            training_prefetch_wait_seconds / elapsed
            if dynamic_prefetcher is not None and elapsed > 0
            else None
        ),
        "per_step_cuda_scalar_synchronization": "epoch_aggregate_only",
        "fixed_budget": fixed_budget,
        "paired_offline_views": bool(args.paired_offline_views),
        "auxiliary_head_forward_views": (
            target_optimizer_steps * 2 if mode in residual_modes else 0
        ),
    }
    (run_dir / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (run_dir / "quality_gate_audit.json").write_text(
        json.dumps(report["quality_gate"], indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({"run_dir": str(run_dir), "mode": args.mode, "model_config_hash": fingerprint["model_config_hash"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
