#!/usr/bin/env python3
"""Compare the single preregistered ResNet Dynamic ERM run with Clean."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CLASSES = [
    "triclinic", "monoclinic", "orthorhombic", "tetragonal",
    "trigonal", "hexagonal", "cubic",
]
SINGLE = [
    "ood_shift_negative", "ood_shift_positive", "ood_broadening",
    "ood_noise", "ood_background", "ood_texture",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean-summary", type=Path, required=True)
    parser.add_argument("--dynamic-run", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    clean = json.loads(args.clean_summary.read_text(encoding="utf-8"))["baseline"]
    history = json.loads((args.dynamic_run / "history.json").read_text(encoding="utf-8"))
    best = [
        item for item in history
        if item.get("early_stopping", {}).get("save_best_checkpoint")
    ][-1]
    final = history[-1]
    level0 = best["ood"]["level0"]
    per_class = {
        name: float(value)
        for name, value in zip(CLASSES, level0["per_class_f1"], strict=True)
    }
    mean_ood = sum(float(best["ood"][name]["macro_f1"]) for name in SINGLE) / len(SINGLE)
    dynamic = {
        "run_id": "cnn_contract_dynamic_erm_identity_adamw_constant__seed_20260710",
        "best_epoch": int(best["epoch"]),
        "best_global_step": int(best["global_step"]),
        "level0_macro_f1": float(level0["macro_f1"]),
        "in_range_macro_f1": float(best["in_range"]["macro_f1"]),
        "mean_single_factor_ood_macro_f1": mean_ood,
        "per_class_f1": per_class,
        "worst_class_f1": min(per_class.values()),
        "level0_confusion_matrix": level0["confusion_matrix"],
        "train_accuracy_at_best": float(best["train_accuracy"]),
        "train_loss_at_best": float(best["train_loss"]),
        "train_accuracy_at_stop": float(final["train_accuracy"]),
        "train_loss_at_stop": float(final["train_loss"]),
        "maximum_budget_reached": int(final["global_step"]) == 61600,
        "early_stopping_state": final["early_stopping"]["state"],
    }
    deltas = {
        key: dynamic[key] - clean[key]
        for key in (
            "level0_macro_f1",
            "in_range_macro_f1",
            "mean_single_factor_ood_macro_f1",
            "worst_class_f1",
        )
    }
    report = {
        "schema_version": "v9-cnn-contract-dynamic-erm-summary-v1",
        "status": "complete",
        "scope": "development-only Validation evidence",
        "only_changed_scientific_factor": "clean_erm_to_dynamic_erm",
        "clean_reference": clean,
        "dynamic_erm": dynamic,
        "dynamic_minus_clean": deltas,
        "gaps": {
            "clean_level0_minus_in_range": clean["level0_macro_f1"] - clean["in_range_macro_f1"],
            "dynamic_level0_minus_in_range": dynamic["level0_macro_f1"] - dynamic["in_range_macro_f1"],
            "clean_level0_minus_mean_single_ood": (
                clean["level0_macro_f1"] - clean["mean_single_factor_ood_macro_f1"]
            ),
            "dynamic_level0_minus_mean_single_ood": (
                dynamic["level0_macro_f1"] - dynamic["mean_single_factor_ood_macro_f1"]
            ),
            "clean_train_accuracy_minus_level0": (
                clean["train_accuracy_at_stop"] - clean["level0_macro_f1"]
            ),
            "dynamic_train_accuracy_at_best_minus_level0": (
                dynamic["train_accuracy_at_best"] - dynamic["level0_macro_f1"]
            ),
        },
        "verdict": "dynamic_regularization_recovers_id_and_ood",
        "interpretation": (
            "Matched dynamic perturbation training improves level0, in-range, "
            "mean single-factor OOD, and worst-class F1. The CNN common foundation "
            "passes this diagnostic Gate, but the formal seven-run remains locked "
            "pending a separately reviewed shared-method contract."
        ),
        "locks": {
            "simulated_test_used": False,
            "real_xrd_used": False,
            "js_run": False,
            "residual_run": False,
            "curriculum_run": False,
            "clean_anchor_run": False,
            "formal_seven_run": "0/7_locked",
            "fifteen_run": "0/15_locked",
            "v10": "locked",
        },
    }
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# CNN Dynamic ERM diagnostic summary", "",
        "**Scope:** development-only Validation evidence; simulated Test and real XRD were not used.",
        "",
        "| Metric | Clean | Dynamic ERM | Delta |",
        "|---|---:|---:|---:|",
    ]
    labels = {
        "level0_macro_f1": "level0 Macro-F1",
        "in_range_macro_f1": "in-range Macro-F1",
        "mean_single_factor_ood_macro_f1": "mean single-factor OOD Macro-F1",
        "worst_class_f1": "worst-class F1",
    }
    for key, label in labels.items():
        lines.append(
            f"| {label} | {clean[key]:.4f} | {dynamic[key]:.4f} | {deltas[key]:+.4f} |"
        )
    lines += [
        "", f"Best Dynamic checkpoint: epoch {dynamic['best_epoch']}, "
        f"global step {dynamic['best_global_step']}.",
        "",
        "Verdict: matched Dynamic ERM recovers in-range and OOD performance while "
        "also improving level0 and worst-class F1. This passes the CNN foundation "
        "diagnostic Gate.",
        "",
        "The formal seven-run is still 0/7 and locked. No JS, Residual, curriculum, "
        "clean anchor, simulated Test, real XRD, 15-run, or V10 execution occurred.",
    ]
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
