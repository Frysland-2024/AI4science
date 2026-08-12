#!/usr/bin/env python3
"""Prove batch-1/batched V7 evaluation equivalence and measure GPU speed."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import time

import numpy as np
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.evaluation import classification_metrics, paired_view_metrics
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.view_manifest import build_parameter_stream, index_manifest


SPEC = importlib.util.spec_from_file_location("train_v7_benchmark", PROJECT_ROOT / "scripts" / "train_v7.py")
assert SPEC and SPEC.loader
TRAIN_V7 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TRAIN_V7)


def _timed_prediction(
    model: PAMPT,
    ids: list[str],
    records: dict[str, dict],
    *,
    index: dict,
    peaks: dict,
    factory: OnlineViewFactory,
    device: torch.device,
    batch_size: int,
) -> tuple[dict[str, np.ndarray], float]:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    started = time.perf_counter()
    result = TRAIN_V7._predict_paired_views(
        model,
        ids,
        records,
        index=index,
        peaks=peaks,
        factory=factory,
        device=device,
        evaluation_batch_size=batch_size,
    )
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    return result, time.perf_counter() - started


def _metrics(prediction: dict[str, np.ndarray]) -> dict[str, float | list]:
    result = classification_metrics(
        prediction["labels"],
        prediction["predictions"],
        probabilities=prediction["probabilities"],
        num_classes=7,
    )
    result.update(
        paired_view_metrics(
            prediction["probabilities"],
            prediction["second_probabilities"],
            prediction["labels"],
        )
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--simulation-config", default=str(PROJECT_ROOT / "configs" / "simulation.v7.candidate.json"))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", choices=["cuda", "cpu", "auto"], default="cuda")
    parser.add_argument(
        "--output",
        default=str(
            PROJECT_ROOT / "outputs" / "diagnostics" / "v7_batch_evaluation_140.json"
        ),
    )
    args = parser.parse_args()
    if args.batch_size <= 1:
        raise SystemExit("--batch-size must be greater than 1")
    data_root = Path(args.data_root).resolve()
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    rows = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = {str(row["material_id"]): row for row in rows}
    ids = sorted(records)
    if len(ids) != 140:
        raise SystemExit(f"benchmark requires the 140-structure tier, got {len(ids)}")
    device_name = "cuda" if args.device == "auto" and torch.cuda.is_available() else args.device
    if device_name == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but unavailable")
    device = torch.device(device_name)
    sampler = PhysicsParameterSampler.from_json(args.simulation_config)
    factory = OnlineViewFactory(sampler)
    manifest_rows = build_parameter_stream(
        ids,
        sampler,
        profile="in_range",
        epochs=1,
        steps_per_epoch=1,
        split="test",
    )
    manifest_index = index_manifest(manifest_rows)
    peaks = {
        material_id: load_peak_table(
            data_root / "mp_processed" / args.cache_name / f"{material_id}.npz"
        )
        for material_id in ids
    }
    if not all(table.has_reflection_metadata for table in peaks.values()):
        raise SystemExit("benchmark cache is missing V7 reflection metadata")
    torch.manual_seed(20260714)
    model = PAMPT(PAMPTConfig(variant="b3")).to(device).eval()
    # Warm GPU kernels without consuming formal results.
    TRAIN_V7._predict_paired_views(
        model,
        ids[: min(8, len(ids))],
        records,
        index=manifest_index,
        peaks=peaks,
        factory=factory,
        device=device,
        evaluation_batch_size=min(8, args.batch_size),
    )
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    sequential_first, sequential_seconds_1 = _timed_prediction(
        model,
        ids,
        records,
        index=manifest_index,
        peaks=peaks,
        factory=factory,
        device=device,
        batch_size=1,
    )
    batched_first, batched_seconds_1 = _timed_prediction(
        model,
        ids,
        records,
        index=manifest_index,
        peaks=peaks,
        factory=factory,
        device=device,
        batch_size=args.batch_size,
    )
    batched_second, batched_seconds_2 = _timed_prediction(
        model,
        ids,
        records,
        index=manifest_index,
        peaks=peaks,
        factory=factory,
        device=device,
        batch_size=args.batch_size,
    )
    sequential_second, sequential_seconds_2 = _timed_prediction(
        model,
        ids,
        records,
        index=manifest_index,
        peaks=peaks,
        factory=factory,
        device=device,
        batch_size=1,
    )
    for result in (batched_first, batched_second, sequential_second):
        if not np.array_equal(sequential_first["labels"], result["labels"]):
            raise RuntimeError("batched evaluation changed label order")
        if not np.array_equal(sequential_first["predictions"], result["predictions"]):
            raise RuntimeError("batched evaluation changed predicted classes")
    maximum_probability_difference = max(
        float(np.max(np.abs(sequential_first["probabilities"] - result["probabilities"])))
        for result in (batched_first, batched_second, sequential_second)
    )
    maximum_second_view_difference = max(
        float(
            np.max(
                np.abs(
                    sequential_first["second_probabilities"]
                    - result["second_probabilities"]
                )
            )
        )
        for result in (batched_first, batched_second, sequential_second)
    )
    probability_tolerance = 2e-5
    sequential_metrics = _metrics(sequential_first)
    batched_metrics = _metrics(batched_first)
    scalar_metric_differences = {
        key: abs(float(sequential_metrics[key]) - float(batched_metrics[key]))
        for key in (
            "accuracy",
            "balanced_accuracy",
            "macro_f1",
            "worst_group_f1",
            "ece",
            "prediction_agreement",
            "paired_js",
            "correct_and_consistent_rate",
        )
    }
    maximum_metric_difference = max(scalar_metric_differences.values())
    metric_tolerance = 1e-5
    confusion_matrices_identical = (
        sequential_metrics["confusion_matrix"] == batched_metrics["confusion_matrix"]
    )
    sequential_seconds = statistics.median([sequential_seconds_1, sequential_seconds_2])
    batched_seconds = statistics.median([batched_seconds_1, batched_seconds_2])
    report = {
        "status": (
            "passed"
            if maximum_probability_difference <= probability_tolerance
            and maximum_second_view_difference <= probability_tolerance
            and maximum_metric_difference <= metric_tolerance
            and confusion_matrices_identical
            else "failed"
        ),
        "scope": "140-structure engineering benchmark; random untrained PAMPT; no scientific metric claim",
        "structures": len(ids),
        "views": len(ids) * 2,
        "device": str(device),
        "gpu": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
        "batch_size": args.batch_size,
        "sequential_forward_calls": len(ids) * 2,
        "batched_forward_calls": math.ceil(len(ids) / args.batch_size) * 2,
        "sequential_seconds_trials": [sequential_seconds_1, sequential_seconds_2],
        "batched_seconds_trials": [batched_seconds_1, batched_seconds_2],
        "sequential_seconds_median": sequential_seconds,
        "batched_seconds_median": batched_seconds,
        "speedup": sequential_seconds / batched_seconds,
        "predicted_classes_identical": True,
        "probability_tolerance": probability_tolerance,
        "metric_tolerance": metric_tolerance,
        "maximum_first_view_probability_difference": maximum_probability_difference,
        "maximum_second_view_probability_difference": maximum_second_view_difference,
        "scalar_metric_differences": scalar_metric_differences,
        "maximum_scalar_metric_difference": maximum_metric_difference,
        "confusion_matrices_identical": confusion_matrices_identical,
        "peak_gpu_memory_mb": (
            float(torch.cuda.max_memory_allocated(device) / (1024**2))
            if device.type == "cuda"
            else None
        ),
        "formal_test_results_used": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
