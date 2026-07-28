"""Summarize and select the preregistered ResNet Dynamic-versus-JS four-run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = PROJECT_ROOT / "configs" / "v9_resnet_js_four_run.preregistered.json"
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


def _row(run: dict[str, Any], output_root: Path) -> dict[str, Any]:
    path = output_root / run["run_id"] / "results.json"
    result = json.loads(path.read_text(encoding="utf-8"))
    selected = result["selection_evaluation"]
    ood = selected["ood"]
    early = result["early_stopping"]
    state = early["state"]
    return {
        "run_id": run["run_id"],
        "method": run["method"],
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
        "worst_class_f1": min(
            float(value) for value in selected["in_range"]["per_class_f1"]
        ),
        "results_sha256": file_hash(path),
    }


def summarize(output_root: Path) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = [_row(run, output_root) for run in contract["runs"]]
    baseline = next(row for row in rows if row["run_id"] == "dynamic_erm")
    eligible = [
        row
        for row in rows
        if row["method"] == "js_consistency_transfer"
        and row["in_range_macro_f1"] >= baseline["in_range_macro_f1"] - 0.01
    ]
    if eligible:
        selected = sorted(
            eligible,
            key=lambda row: (
                -row["mean_single_factor_ood_macro_f1"],
                -row["in_range_macro_f1"],
                row["lambda_js"],
            ),
        )[0]
        decision = "select_js_candidate"
    else:
        selected = baseline
        decision = "retain_dynamic_erm_no_eligible_js_candidate"
    return {
        "schema_version": "v9-resnet-js-four-run-summary-v1",
        "status": "completed_selection_frozen",
        "contract_sha256": file_hash(CONTRACT),
        "run_count": len(rows),
        "runs": rows,
        "guardrail": {
            "maximum_in_range_drop_vs_dynamic": 0.01,
            "dynamic_in_range_macro_f1": baseline["in_range_macro_f1"],
            "eligible_js_lambdas": [row["lambda_js"] for row in eligible],
        },
        "selection": {
            "decision": decision,
            "run_id": selected["run_id"],
            "method": selected["method"],
            "lambda_js": selected["lambda_js"],
            "mean_single_factor_ood_macro_f1": selected[
                "mean_single_factor_ood_macro_f1"
            ],
            "in_range_macro_f1": selected["in_range_macro_f1"],
        },
        "boundaries": {
            "simulated_test_used": False,
            "real_xrd_used": False,
            "ten_run_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "v9_resnet_js_four_run_summary.json",
    )
    args = parser.parse_args()
    report = summarize(args.output_root.resolve())
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["selection"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
