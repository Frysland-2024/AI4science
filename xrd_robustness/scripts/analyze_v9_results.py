"""Analyze frozen V9 prediction rows with family-level hierarchical bootstrap."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from xrd_robustness.evaluation.statistics import build_method_transfer_statistics_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions-jsonl", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--profiles", nargs="+", required=True)
    parser.add_argument("--dynamic-method", default="dynamic_erm")
    parser.add_argument("--js-method", default="js_consistency_transfer")
    parser.add_argument("--residual-method", default="residual_decorrelation_transfer")
    parser.add_argument("--replicates", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260722)
    args = parser.parse_args()
    input_paths = [Path(value).resolve() for value in args.predictions_jsonl]
    rows = [
        json.loads(line)
        for input_path in input_paths
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = build_method_transfer_statistics_report(
        rows,
        dynamic_method_id=args.dynamic_method,
        js_method_id=args.js_method,
        residual_method_id=args.residual_method,
        profiles=args.profiles,
        replicates=args.replicates,
        random_seed=args.seed,
    )
    report["input_paths"] = [str(path) for path in input_paths]
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = output.parent / f"{output.stem}_artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    with (artifacts / "method_profile_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["seed", "method_id", "profile", "independent_family_count", "spectrum_count", "accuracy", "balanced_accuracy", "macro_f1", "worst_group_f1", "ece"],
        )
        writer.writeheader()
        for item in report["summaries"].values():
            metrics = item["metrics"]
            writer.writerow({
                "seed": item["seed"], "method_id": item["method_id"], "profile": item["profile"],
                "independent_family_count": item["independent_family_count"], "spectrum_count": item["spectrum_count"],
                "accuracy": metrics["accuracy"], "balanced_accuracy": metrics["balanced_accuracy"],
                "macro_f1": metrics["macro_f1"], "worst_group_f1": metrics["worst_group_f1"], "ece": metrics.get("ece"),
            })
    with (artifacts / "paired_comparisons.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["contrast", "mean_delta", "ci_low", "ci_high", "interpretation"])
        writer.writeheader()
        for name, item in report["paired_comparisons"].items():
            writer.writerow({"contrast": name, "mean_delta": item["mean_delta"], "ci_low": item["hierarchical_bootstrap_95_ci"][0], "ci_high": item["hierarchical_bootstrap_95_ci"][1], "interpretation": item["interpretation"]})
    (artifacts / "figure_data.json").write_text(
        json.dumps({"paired_comparisons": report["paired_comparisons"], "paper_outcome": report["paper_outcome"]}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report["generated_artifacts"] = [
        str(artifacts / "method_profile_metrics.csv"),
        str(artifacts / "paired_comparisons.csv"),
        str(artifacts / "figure_data.json"),
    ]
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "paper_outcome": report["paper_outcome"], "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
