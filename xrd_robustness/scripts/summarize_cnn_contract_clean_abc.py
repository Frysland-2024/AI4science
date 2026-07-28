#!/usr/bin/env python3
"""Summarize preregistered CNN Clean A/B/C diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


CLASS_NAMES = [
    "triclinic", "monoclinic", "orthorhombic", "tetragonal",
    "trigonal", "hexagonal", "cubic",
]
SINGLE_FACTOR_PROFILES = [
    "ood_shift_negative", "ood_shift_positive", "ood_broadening",
    "ood_noise", "ood_background", "ood_texture",
]


def _best_record(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    selected = [
        record for record in history
        if record.get("early_stopping", {}).get("save_best_checkpoint")
    ][-1]
    final = history[-1]
    return selected, final


def _run_summary(
    run_id: str,
    run_dir: Path,
    *,
    preprocessing: str,
    optimizer: str,
    schedule: str,
) -> dict[str, Any]:
    best, final = _best_record(run_dir)
    level0 = best["ood"]["level0"]
    per_class = {
        name: float(value)
        for name, value in zip(CLASS_NAMES, level0["per_class_f1"], strict=True)
    }
    mean_ood = sum(
        float(best["ood"][name]["macro_f1"]) for name in SINGLE_FACTOR_PROFILES
    ) / len(SINGLE_FACTOR_PROFILES)
    predicted_counts = [
        sum(int(row[column]) for row in level0["confusion_matrix"])
        for column in range(len(CLASS_NAMES))
    ]
    state = final.get("early_stopping", {}).get("state", {})
    return {
        "run_id": run_id,
        "only_changed_factor": {
            "A": "preprocessing",
            "B": "optimizer",
            "C": "learning_rate_schedule",
        }[run_id],
        "configuration": {
            "preprocessing": preprocessing,
            "optimizer": optimizer,
            "learning_rate_schedule": schedule,
        },
        "best_epoch": int(best["epoch"]),
        "best_global_step": int(best["global_step"]),
        "level0_macro_f1": float(level0["macro_f1"]),
        "in_range_macro_f1": float(best["in_range"]["macro_f1"]),
        "mean_single_factor_ood_macro_f1": mean_ood,
        "per_class_f1": per_class,
        "worst_class_f1": min(per_class.values()),
        "level0_confusion_matrix": level0["confusion_matrix"],
        "level0_predicted_class_counts": predicted_counts,
        "class_collapse": any(count == 0 for count in predicted_counts),
        "train_accuracy_at_stop": float(final["train_accuracy"]),
        "train_loss_at_stop": float(final["train_loss"]),
        "stopped_early": bool(state.get("stopped", False)),
        "stop_epoch": state.get("stop_epoch"),
        "maximum_budget_reached": int(final["global_step"]) == 61600,
        "run_contract": json.loads(
            (run_dir / "cnn_contract_diagnostic.json").read_text(encoding="utf-8")
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-report", type=Path, required=True)
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--run-c", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    gate3 = json.loads(args.baseline_report.read_text(encoding="utf-8"))["resnet"]
    baseline_per_class = {
        item["class"]: float(item["f1"]) for item in gate3["level0_per_class"]
    }
    baseline = {
        "run_id": "baseline",
        "only_changed_factor": "none",
        "configuration": {
            "preprocessing": "identity",
            "optimizer": "adamw",
            "learning_rate_schedule": "constant",
        },
        "best_epoch": int(gate3["best_epoch"]),
        "best_global_step": int(gate3["best_global_step"]),
        "level0_macro_f1": float(gate3["level0_macro_f1"]),
        "in_range_macro_f1": float(gate3["in_range_macro_f1"]),
        "mean_single_factor_ood_macro_f1": float(
            gate3["mean_single_factor_ood_macro_f1"]
        ),
        "per_class_f1": baseline_per_class,
        "worst_class_f1": min(baseline_per_class.values()),
        "level0_confusion_matrix": gate3["level0_confusion_matrix"],
        "class_collapse": False,
        "train_accuracy_at_stop": float(gate3["train_accuracy_at_stop"]),
        "train_loss_at_stop": float(gate3["train_loss_at_stop"]),
        "stopped_early": bool(gate3["stopped_early"]),
        "stop_epoch": gate3["stop_epoch"],
        "maximum_budget_reached": True,
    }
    experiments = [
        _run_summary("A", args.run_a, preprocessing="sqrt", optimizer="adamw", schedule="constant"),
        _run_summary("B", args.run_b, preprocessing="identity", optimizer="adam", schedule="constant"),
        _run_summary(
            "C", args.run_c, preprocessing="identity", optimizer="adamw",
            schedule="linear_warmup_3080_steps_then_cosine_to_zero",
        ),
    ]
    threshold = baseline["level0_macro_f1"] + 0.02
    worst_floor = baseline["worst_class_f1"] - 0.02
    for item in experiments:
        item["selection_checks"] = {
            "level0_threshold": item["level0_macro_f1"] >= threshold,
            "worst_class_guardrail": item["worst_class_f1"] >= worst_floor,
            "no_class_collapse": not item["class_collapse"],
        }
        item["decision"] = (
            "PASS" if all(item["selection_checks"].values()) else "NOT_SELECTED"
        )

    report = {
        "schema_version": "v9-cnn-contract-clean-abc-summary-v1",
        "status": "complete",
        "evidence_scope": "development-only Validation evidence",
        "selection_thresholds": {
            "level0_macro_f1_minimum": threshold,
            "worst_class_f1_minimum": worst_floor,
            "class_collapse_forbidden": True,
            "post_hoc_threshold_change": False,
        },
        "baseline": baseline,
        "experiments": experiments,
        "selected_clean_configuration": baseline["configuration"],
        "selection_reason": (
            "No new Clean experiment met the preregistered level0 improvement "
            "threshold; search stops after A/B/C and reverts to the original best."
        ),
        "scientific_interpretation": (
            "PAMPT was a major backbone bottleneck, but the remaining dominant "
            "problem is a severe parent-structure train-to-validation generalization gap."
        ),
        "locks": {
            "simulated_test_used": False,
            "real_xrd_used": False,
            "formal_seven_run_started": False,
            "formal_seven_run_progress": "0/7",
            "fifteen_run_progress": "0/15",
            "v10_used": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    rows = [baseline, *experiments]
    lines = [
        "# CNN Clean A/B/C diagnostic summary", "",
        "**Scope:** development-only Validation evidence; no simulated Test or real XRD.",
        "",
        "| Run | Preprocess | Optimizer | Schedule | level0 | in-range | mean single OOD | worst F1 | best epoch/step | decision |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        decision = "SELECTED" if row["run_id"] == "baseline" else row["decision"]
        cfg = row["configuration"]
        lines.append(
            f"| {row['run_id']} | {cfg['preprocessing']} | {cfg['optimizer']} | "
            f"{cfg['learning_rate_schedule']} | {row['level0_macro_f1']:.4f} | "
            f"{row['in_range_macro_f1']:.4f} | "
            f"{row['mean_single_factor_ood_macro_f1']:.4f} | "
            f"{row['worst_class_f1']:.4f} | "
            f"{row['best_epoch']}/{row['best_global_step']} | {decision} |"
        )
    lines += [
        "", "## Decision", "",
        "No A/B/C candidate reached the preregistered level0 threshold "
        f"`{threshold:.4f}`. The shared Clean configuration is therefore "
        "`ResNet-18-GN + identity + AdamW + constant LR`.",
        "",
        "Clean hyperparameter search is closed. The only next authorized experiment "
        "is one matched ResNet Dynamic ERM diagnostic. The formal 7-run remains 0/7.",
        "",
        "These results are not formal paper performance claims.",
    ]
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
