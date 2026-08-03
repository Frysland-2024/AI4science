#!/usr/bin/env python3
"""Summarize the preregistered five-seed paired ResNet Dynamic-ERM versus JS study."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean, stdev
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "configs" / "v9_resnet_js_ten_run.preregistered.json"
PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sample_std(values: list[float]) -> float:
    return stdev(values) if len(values) >= 2 else 0.0


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate percentile of an empty sequence")
    position = (len(sorted_values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    fraction = position - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def paired_bootstrap_ci(values: list[float], *, repetitions: int = 10000) -> list[float]:
    if not values:
        raise ValueError("paired bootstrap requires at least one delta")
    rng = random.Random(20260729)
    draws = [
        mean(rng.choice(values) for _ in range(len(values)))
        for _ in range(repetitions)
    ]
    draws.sort()
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def load_row(run: dict[str, Any], output_root: Path) -> dict[str, Any]:
    result_path = output_root / str(run["run_id"]) / "results.json"
    if not result_path.is_file():
        raise FileNotFoundError(f"missing completed result: {result_path}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    selected = result["selection_evaluation"]
    ood = selected["ood"]
    state = result["early_stopping"]["state"]
    return {
        "run_id": str(run["run_id"]),
        "pair_id": str(run["pair_id"]),
        "training_seed": int(run["training_seed"]),
        "evaluation_seed": int(run["evaluation_seed"]),
        "method": str(run["method"]),
        "lambda_js": float(run["lambda_js"]),
        "best_epoch": int(state["best_epoch"]),
        "best_global_step": int(state["best_global_step"]),
        "stop_epoch": state.get("stop_epoch"),
        "stopped_early": bool(result["compute_summary"]["stopped_early"]),
        "level0_macro_f1": float(ood["level0"]["macro_f1"]),
        "in_range_macro_f1": float(selected["in_range"]["macro_f1"]),
        "mean_single_factor_ood_macro_f1": mean(
            float(ood[name]["macro_f1"]) for name in PROFILES
        ),
        "worst_class_f1": min(float(x) for x in selected["in_range"]["per_class_f1"]),
        "results_sha256": file_hash(result_path),
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "level0_macro_f1",
        "in_range_macro_f1",
        "mean_single_factor_ood_macro_f1",
        "worst_class_f1",
    )
    payload: dict[str, Any] = {"run_count": len(rows)}
    for metric in metrics:
        values = [float(row[metric]) for row in rows]
        payload[metric] = {
            "mean": mean(values),
            "sample_std": sample_std(values),
            "values": values,
        }
    return payload


def summarize(output_root: Path) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = [load_row(run, output_root) for run in contract["runs"]]
    if len(rows) != 10:
        raise ValueError(f"expected 10 completed runs, found {len(rows)}")

    erm_rows = sorted(
        (row for row in rows if row["method"] == "ordinary_dynamic_augmentation"),
        key=lambda row: row["training_seed"],
    )
    js_rows = sorted(
        (row for row in rows if row["method"] == "js_consistency_transfer"),
        key=lambda row: row["training_seed"],
    )
    if len(erm_rows) != 5 or len(js_rows) != 5:
        raise ValueError("expected exactly five ERM and five JS runs")

    erm_by_seed = {row["training_seed"]: row for row in erm_rows}
    js_by_seed = {row["training_seed"]: row for row in js_rows}
    if set(erm_by_seed) != set(js_by_seed):
        raise ValueError("paired seed sets do not match")

    paired = []
    for seed in sorted(erm_by_seed):
        erm = erm_by_seed[seed]
        js = js_by_seed[seed]
        paired.append(
            {
                "training_seed": seed,
                "erm_run_id": erm["run_id"],
                "js_run_id": js["run_id"],
                "delta_mean_single_factor_ood_macro_f1": (
                    js["mean_single_factor_ood_macro_f1"]
                    - erm["mean_single_factor_ood_macro_f1"]
                ),
                "delta_in_range_macro_f1": (
                    js["in_range_macro_f1"] - erm["in_range_macro_f1"]
                ),
                "delta_level0_macro_f1": (
                    js["level0_macro_f1"] - erm["level0_macro_f1"]
                ),
                "delta_worst_class_f1": (
                    js["worst_class_f1"] - erm["worst_class_f1"]
                ),
            }
        )

    ood_deltas = [row["delta_mean_single_factor_ood_macro_f1"] for row in paired]
    in_range_deltas = [row["delta_in_range_macro_f1"] for row in paired]
    erm_aggregate = aggregate(erm_rows)
    js_aggregate = aggregate(js_rows)
    guardrail_pass = (
        js_aggregate["in_range_macro_f1"]["mean"]
        >= erm_aggregate["in_range_macro_f1"]["mean"] - 0.01
    )

    return {
        "schema_version": "v9-resnet-js-ten-run-summary-v1",
        "status": "completed_validation_replication",
        "contract_sha256": file_hash(CONTRACT),
        "output_root": str(output_root),
        "run_count": len(rows),
        "runs": rows,
        "aggregate": {
            "dynamic_erm": erm_aggregate,
            "js_lambda_60": js_aggregate,
        },
        "paired_effect": {
            "pairs": paired,
            "mean_delta_mean_single_factor_ood_macro_f1": mean(ood_deltas),
            "sample_std_delta_mean_single_factor_ood_macro_f1": sample_std(ood_deltas),
            "paired_bootstrap_95_percent_interval_ood": paired_bootstrap_ci(ood_deltas),
            "mean_delta_in_range_macro_f1": mean(in_range_deltas),
            "sample_std_delta_in_range_macro_f1": sample_std(in_range_deltas),
            "paired_bootstrap_95_percent_interval_in_range": paired_bootstrap_ci(
                in_range_deltas
            ),
        },
        "guardrail": {
            "rule": "mean_js_in_range_macro_f1 >= mean_dynamic_erm_in_range_macro_f1 - 0.01",
            "passed": guardrail_pass,
        },
        "boundaries": {
            "simulated_test_used": False,
            "real_xrd_used": False,
            "lambda_retuned": False,
            "seed_excluded_posthoc": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "v9_resnet_js_ten_run_summary.json",
    )
    args = parser.parse_args()
    report = summarize(args.output_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["paired_effect"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
