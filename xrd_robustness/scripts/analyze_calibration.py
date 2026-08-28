#!/usr/bin/env python3
"""Post-hoc calibration audit for the frozen Dynamic ERM vs JS models.

This script does not train, tune, or select any model. It reuses the frozen
simulated-Test panel cache/checkpoints to save per-sample probabilities, reads
existing CNRS-318 predictions, and computes calibration/reliability metrics:

- ECE (the existing 15 equal-width top-label implementation)
- negative log-likelihood (NLL)
- multiclass Brier score
- mean confidence
- mean predictive entropy
- accuracy and Macro-F1

Outputs are written under ``outputs/calibration_analysis``. Simulated
probability files are saved condition-by-condition, so an interrupted run can
be resumed without repeating completed forward passes.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.evaluation.metrics import classification_metrics  # noqa: E402
from xrd_robustness.experiment import assert_model_fingerprint, load_checkpoint  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402


SIMULATED_RUNNER = ROOT / "scripts/run_simulated_test.py"
SIMULATED_OUTPUT = ROOT / "outputs/public_simulated_test"
CHECKPOINT_ROOT = ROOT / "outputs/simulated_test_checkpoints/checkpoints"
CNRS_PREDICTIONS = ROOT / "outputs/cnrs318_zero_shot/predictions.ndjson"
OUTPUT_ROOT = ROOT / "outputs/calibration_analysis"


METRIC_NAMES = (
    "macro_f1",
    "accuracy",
    "ece",
    "nll",
    "brier",
    "mean_confidence",
    "mean_entropy",
)


def _load_simulated_runner() -> Any:
    spec = importlib.util.spec_from_file_location(
        "public_simulated_test_runner_for_calibration", SIMULATED_RUNNER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load simulated-Test runner: {SIMULATED_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    return device


def _metric_bundle(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    labels = np.asarray(labels, dtype=np.int64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.shape != (len(labels), len(CRYSTAL_SYSTEMS)):
        raise ValueError(
            f"probability shape {probabilities.shape} does not match labels/classes"
        )
    clipped = np.clip(probabilities, 1e-12, 1.0)
    base = classification_metrics(
        labels,
        probabilities.argmax(axis=1),
        probabilities=probabilities,
        num_classes=len(CRYSTAL_SYSTEMS),
    )
    one_hot = np.eye(len(CRYSTAL_SYSTEMS), dtype=np.float64)[labels]
    nll = -float(np.mean(np.log(clipped[np.arange(len(labels)), labels])))
    brier = float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1)))
    confidence = probabilities.max(axis=1)
    entropy = -np.sum(clipped * np.log(clipped), axis=1)
    return {
        "macro_f1": float(base["macro_f1"]),
        "accuracy": float(base["accuracy"]),
        "ece": float(base["ece"]),
        "nll": nll,
        "brier": brier,
        "mean_confidence": float(confidence.mean()),
        "mean_entropy": float(entropy.mean()),
    }


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _valid_probability_file(path: Path, n_samples: int) -> bool:
    if not path.is_file():
        return False
    try:
        archive = np.load(path, allow_pickle=False)
        probabilities = archive["probabilities"]
        labels = archive["labels"]
        return (
            probabilities.shape == (n_samples, len(CRYSTAL_SYSTEMS))
            and labels.shape == (n_samples,)
            and str(probabilities.dtype) == "float32"
        )
    except Exception:
        return False


def _infer_probabilities(
    model: torch.nn.Module,
    spectra: np.ndarray,
    *,
    batch_size: int,
    device: torch.device,
) -> np.ndarray:
    probabilities = np.empty(
        (len(spectra), len(CRYSTAL_SYSTEMS)), dtype=np.float32
    )
    model.eval()
    for start in range(0, len(spectra), batch_size):
        stop = min(start + batch_size, len(spectra))
        host = torch.from_numpy(np.array(spectra[start:stop], copy=True))
        context = (
            torch.autocast(device_type="cuda", dtype=torch.float16)
            if device.type == "cuda"
            else torch.no_grad()
        )
        if device.type == "cuda":
            with torch.inference_mode(), context:
                logits = model(host.to(device))["logits"]
        else:
            with torch.inference_mode():
                logits = model(host.to(device))["logits"]
        probabilities[start:stop] = (
            torch.softmax(logits, dim=-1).float().cpu().numpy()
        )
    return probabilities


def _paired_rows(
    rows: Sequence[dict[str, Any]],
    *,
    key_fields: Sequence[str],
    method_field: str = "method",
    erm_value: str = "dynamic_erm",
    js_value: str = "dynamic_js",
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], dict[str, dict[str, Any]]] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        grouped.setdefault(key, {})[str(row[method_field])] = row
    output: list[dict[str, Any]] = []
    for key, group in sorted(grouped.items(), key=lambda item: tuple(map(str, item[0]))):
        if erm_value not in group or js_value not in group:
            continue
        erm = group[erm_value]
        js = group[js_value]
        paired: dict[str, Any] = {
            field: value for field, value in zip(key_fields, key, strict=True)
        }
        for metric in METRIC_NAMES:
            paired[f"erm_{metric}"] = float(erm[metric])
            paired[f"js_{metric}"] = float(js[metric])
            paired[f"delta_{metric}"] = float(js[metric] - erm[metric])
        output.append(paired)
    return output


def _summarize_pairs(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_pairs": 0}
    summary: dict[str, Any] = {"n_pairs": len(rows), "metrics": {}}
    for metric in METRIC_NAMES:
        values = np.asarray([row[f"delta_{metric}"] for row in rows], dtype=np.float64)
        summary["metrics"][metric] = {
            "mean_delta_js_minus_erm": float(values.mean()),
            "min_delta": float(values.min()),
            "max_delta": float(values.max()),
            "negative_pairs": int(np.sum(values < 0)),
            "positive_pairs": int(np.sum(values > 0)),
            "zero_pairs": int(np.sum(values == 0)),
        }
    return summary


def _method_means(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, float]]:
    methods = sorted({str(row["method"]) for row in rows})
    output: dict[str, dict[str, float]] = {}
    for method in methods:
        subset = [row for row in rows if str(row["method"]) == method]
        output[method] = {
            metric: float(np.mean([float(row[metric]) for row in subset]))
            for metric in METRIC_NAMES
        }
    return output


def _reliability_points(
    labels: np.ndarray, probabilities: np.ndarray, bins: int = 15
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    labels = np.asarray(labels, dtype=np.int64).reshape(-1)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    confidence = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    edges = np.linspace(0.0, 1.0, bins + 1)
    xs: list[float] = []
    ys: list[float] = []
    counts: list[int] = []
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        mask = (confidence > left) & (
            confidence <= right if right < 1.0 else confidence <= right
        )
        if not np.any(mask):
            continue
        xs.append(float(confidence[mask].mean()))
        ys.append(float((predictions[mask] == labels[mask]).mean()))
        counts.append(int(mask.sum()))
    return np.asarray(xs), np.asarray(ys), np.asarray(counts)


def _plot_reliability(
    path: Path,
    datasets: dict[str, tuple[np.ndarray, np.ndarray]],
    *,
    title: str,
) -> bool:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as error:
        print(f"warning: reliability figure skipped: {error}", file=sys.stderr)
        return False

    figure, axis = plt.subplots(figsize=(6.4, 5.6))
    axis.plot([0.0, 1.0], [0.0, 1.0], "--", label="Perfect calibration")
    for label, (labels, probabilities) in datasets.items():
        x, y, _ = _reliability_points(labels, probabilities)
        axis.plot(x, y, marker="o", label=label)
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.set_xlabel("Mean confidence")
    axis.set_ylabel("Empirical accuracy")
    axis.set_title(title)
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return True


def _run_simulated(
    *,
    output_root: Path,
    simulated_output: Path,
    checkpoint_root: Path,
    batch_size: int,
    device: torch.device,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    runner = _load_simulated_runner()
    print("[simulated] refreshing frozen preflight and validating local assets...")
    gate = runner.preflight(
        output_root=simulated_output,
        checkpoint_root=checkpoint_root,
    )
    contract, _, simulation = runner.load_public_contract()
    _, data_contract = runner.load_data_contract(contract)
    records = runner.load_records(contract, data_contract)
    cache = runner.build_panel_cache(
        records, simulation, gate, output_root=simulated_output
    )
    checkpoint_paths = runner.verify_checkpoint_bindings(
        gate, contract, checkpoint_root
    )
    labels = np.asarray(cache["labels"], dtype=np.int64)
    profiles = list(gate["profiles"])
    evaluation_seeds = [int(seed) for seed in gate["evaluation_seeds"]]
    single_factor_profiles = set(
        contract["evaluation_profiles"]["single_factor_ood"]
    )

    raw_reference: dict[str, Any] = {}
    raw_reference_path = simulated_output / "raw_results.json"
    if raw_reference_path.is_file():
        try:
            raw_reference = json.loads(raw_reference_path.read_text(encoding="utf-8"))
        except Exception:
            raw_reference = {}

    metrics_rows: list[dict[str, Any]] = []
    reliability: dict[str, dict[str, list[np.ndarray]]] = {
        "dynamic_erm": {"labels": [], "probabilities": []},
        "dynamic_js": {"labels": [], "probabilities": []},
    }
    max_ece_reference_error = 0.0
    reference_comparisons = 0

    conditions = [(seed, profile) for seed in evaluation_seeds for profile in profiles]
    for run_index, spec in enumerate(runner.run_specs(contract), start=1):
        run_id = str(spec["run_id"])
        method = str(spec["method"])
        probability_root = output_root / "simulated_probabilities" / run_id
        missing = []
        for evaluation_seed, profile in conditions:
            probability_path = (
                probability_root
                / f"eval_{evaluation_seed}"
                / f"{profile}.npz"
            )
            if not _valid_probability_file(probability_path, len(labels)):
                missing.append((evaluation_seed, profile, probability_path))

        model: torch.nn.Module | None = None
        if missing:
            print(
                f"[simulated] run {run_index}/10 {run_id}: "
                f"{len(missing)}/{len(conditions)} conditions need forward inference"
            )
            model_config = ML4PXRDResNet1DConfig(model_id="18")
            model = ML4PXRDResNet1D(model_config)
            payload = load_checkpoint(
                checkpoint_paths[run_id], model=model, map_location="cpu"
            )
            assert_model_fingerprint(
                model, model_config, payload["model_fingerprint"]
            )
            model.to(device)
        else:
            print(f"[simulated] run {run_index}/10 {run_id}: all probabilities cached")

        for condition_index, (evaluation_seed, profile) in enumerate(
            conditions, start=1
        ):
            probability_path = (
                probability_root
                / f"eval_{evaluation_seed}"
                / f"{profile}.npz"
            )
            if _valid_probability_file(probability_path, len(labels)):
                archive = np.load(probability_path, allow_pickle=False)
                probabilities = np.asarray(archive["probabilities"], dtype=np.float32)
            else:
                assert model is not None
                entry = cache["entries"][f"{evaluation_seed}:{profile}"]
                spectra = np.load(
                    simulated_output / entry["path"],
                    mmap_mode="r",
                    allow_pickle=False,
                )
                probabilities = _infer_probabilities(
                    model,
                    spectra,
                    batch_size=batch_size,
                    device=device,
                )
                probability_path.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(
                    probability_path,
                    probabilities=probabilities.astype(np.float32, copy=False),
                    labels=labels,
                )

            metrics = _metric_bundle(labels, probabilities)
            row: dict[str, Any] = {
                "training_seed": int(spec["training_seed"]),
                "run_id": run_id,
                "method": method,
                "evaluation_seed": int(evaluation_seed),
                "profile": str(profile),
                **metrics,
            }
            try:
                reference_ece = float(
                    raw_reference["runs"][run_id]["profiles_by_evaluation_seed"][
                        str(evaluation_seed)
                    ][str(profile)]["ece"]
                )
            except Exception:
                reference_ece = math.nan
            if math.isfinite(reference_ece):
                error = abs(metrics["ece"] - reference_ece)
                row["reference_ece"] = reference_ece
                row["ece_abs_error_vs_frozen_raw"] = error
                max_ece_reference_error = max(max_ece_reference_error, error)
                reference_comparisons += 1
            metrics_rows.append(row)

            if profile in single_factor_profiles:
                reliability[method]["labels"].append(labels)
                reliability[method]["probabilities"].append(probabilities)

            if condition_index % 12 == 0:
                print(
                    f"[simulated]   {run_id}: {condition_index}/{len(conditions)} conditions processed"
                )

        if model is not None:
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()

    paired = _paired_rows(
        metrics_rows,
        key_fields=("training_seed", "evaluation_seed", "profile"),
    )
    reliability_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for method, values in reliability.items():
        if values["labels"]:
            reliability_data[method] = (
                np.concatenate(values["labels"], axis=0),
                np.concatenate(values["probabilities"], axis=0),
            )
    if reliability_data:
        _plot_reliability(
            output_root / "simulated_single_factor_ood_reliability.png",
            {
                "Dynamic ERM": reliability_data["dynamic_erm"],
                "JS Consistency": reliability_data["dynamic_js"],
            },
            title="Simulated Test single-factor OOD (descriptive pooled view)",
        )

    summary = {
        "condition_count_per_method": len(metrics_rows) // 2,
        "method_means_across_conditions": _method_means(metrics_rows),
        "paired": _summarize_pairs(paired),
        "frozen_ece_reproduction": {
            "comparisons": reference_comparisons,
            "max_absolute_error": max_ece_reference_error,
        },
    }
    return metrics_rows, paired, summary


def _normalize_cnrs_method(value: str) -> str:
    text = value.strip().lower()
    if "erm" in text:
        return "dynamic_erm"
    if "js" in text:
        return "dynamic_js"
    raise ValueError(f"unknown CNRS method: {value}")


def _run_cnrs(
    *,
    output_root: Path,
    predictions_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if not predictions_path.is_file():
        raise FileNotFoundError(
            f"CNRS prediction file is missing: {predictions_path}. "
            "The calibration audit never re-runs CNRS inference automatically."
        )
    rows = [
        json.loads(line)
        for line in predictions_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for row in rows:
        seed = int(row["seed"])
        method = _normalize_cnrs_method(str(row["method_name"]))
        grouped.setdefault((seed, method), []).append(row)

    metrics_rows: list[dict[str, Any]] = []
    pooled: dict[str, dict[str, list[np.ndarray]]] = {
        "dynamic_erm": {"labels": [], "probabilities": []},
        "dynamic_js": {"labels": [], "probabilities": []},
    }
    for (seed, method), group in sorted(grouped.items()):
        labels = np.asarray([int(row["label_index"]) for row in group], dtype=np.int64)
        probabilities = np.asarray(
            [row["probabilities"] for row in group], dtype=np.float32
        )
        metrics_rows.append(
            {
                "training_seed": seed,
                "method": method,
                **_metric_bundle(labels, probabilities),
            }
        )
        pooled[method]["labels"].append(labels)
        pooled[method]["probabilities"].append(probabilities)

    paired = _paired_rows(
        metrics_rows,
        key_fields=("training_seed",),
    )
    pooled_metrics: dict[str, dict[str, float]] = {}
    reliability_data: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for method, values in pooled.items():
        labels = np.concatenate(values["labels"], axis=0)
        probabilities = np.concatenate(values["probabilities"], axis=0)
        pooled_metrics[method] = _metric_bundle(labels, probabilities)
        reliability_data[method] = (labels, probabilities)

    _plot_reliability(
        output_root / "cnrs318_reliability.png",
        {
            "Dynamic ERM": reliability_data["dynamic_erm"],
            "JS Consistency": reliability_data["dynamic_js"],
        },
        title="CNRS-318 zero-shot (descriptive pooled across 5 seeds)",
    )

    summary = {
        "n_prediction_rows": len(rows),
        "n_parents_per_seed_method": len(next(iter(grouped.values()))) if grouped else 0,
        "per_seed_paired": _summarize_pairs(paired),
        "pooled_metrics": pooled_metrics,
        "pooled_delta_js_minus_erm": {
            metric: float(
                pooled_metrics["dynamic_js"][metric]
                - pooled_metrics["dynamic_erm"][metric]
            )
            for metric in METRIC_NAMES
        },
    }
    return metrics_rows, paired, summary




def _calibration_interpretation(summary: dict[str, Any]) -> str:
    paired = summary.get("paired", {}).get("metrics", {})
    n_pairs = int(summary.get("paired", {}).get("n_pairs", 0))
    if not n_pairs:
        return "unavailable"
    ece = paired.get("ece", {})
    nll = paired.get("nll", {})
    brier = paired.get("brier", {})
    if (
        int(ece.get("negative_pairs", 0)) == n_pairs
        and int(nll.get("negative_pairs", 0)) == n_pairs
        and int(brier.get("negative_pairs", 0)) == n_pairs
    ):
        return "strong_support"
    if (
        float(ece.get("mean_delta_js_minus_erm", 0.0)) < 0
        and float(nll.get("mean_delta_js_minus_erm", 0.0)) < 0
        and float(brier.get("mean_delta_js_minus_erm", 0.0)) < 0
    ):
        return "support_with_heterogeneity"
    if float(ece.get("mean_delta_js_minus_erm", 0.0)) < 0:
        return "ece_only_or_mixed_proper_scores"
    return "not_supported"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resumable post-hoc calibration audit for frozen XRD models"
    )
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--simulated-output", type=Path, default=SIMULATED_OUTPUT)
    parser.add_argument("--checkpoint-root", type=Path, default=CHECKPOINT_ROOT)
    parser.add_argument("--cnrs-predictions", type=Path, default=CNRS_PREDICTIONS)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--skip-simulated", action="store_true")
    parser.add_argument("--skip-cnrs", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.skip_simulated and args.skip_cnrs:
        raise SystemExit("nothing to do: both domains were skipped")

    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    device = _device(args.device)
    print(f"Calibration audit starting on device={device}")
    print(f"Output directory: {output_root}")

    final: dict[str, Any] = {
        "schema_version": "calibration-audit-v1",
        "status": "in_progress",
        "device": str(device),
        "batch_size": int(args.batch_size),
    }
    _write_json(output_root / "summary.json", final)

    simulated_summary: dict[str, Any] | None = None
    cnrs_summary: dict[str, Any] | None = None

    if not args.skip_simulated:
        _simulated_metrics, simulated_pairs, simulated_summary = _run_simulated(
            output_root=output_root,
            simulated_output=args.simulated_output.resolve(),
            checkpoint_root=args.checkpoint_root.resolve(),
            batch_size=int(args.batch_size),
            device=device,
        )
        _write_csv(output_root / "simulated_paired.csv", simulated_pairs)
        final["simulated"] = simulated_summary
        _write_json(output_root / "summary.json", final)

    if not args.skip_cnrs:
        _cnrs_metrics, cnrs_pairs, cnrs_summary = _run_cnrs(
            output_root=output_root,
            predictions_path=args.cnrs_predictions.resolve(),
        )
        _write_csv(output_root / "cnrs_paired.csv", cnrs_pairs)
        final["cnrs"] = cnrs_summary
        _write_json(output_root / "summary.json", final)

    final["status"] = "completed"
    final["simulated_calibration_interpretation"] = (
        _calibration_interpretation(simulated_summary)
        if simulated_summary is not None
        else "skipped"
    )
    _write_json(output_root / "summary.json", final)
    print("Calibration audit completed.")
    print(f"Summary: {output_root / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
