#!/usr/bin/env python3
"""Summarize the Gate-3 matched ResNet Clean run against PAMPT-B3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


SINGLE_FACTOR_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)
CRYSTAL_SYSTEMS = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--pampt-summary", type=Path, required=True)
    parser.add_argument("--sanity-report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args()


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    history = json.loads((run_dir / "history.json").read_text(encoding="utf-8"))
    pampt = json.loads(args.pampt_summary.resolve().read_text(encoding="utf-8"))
    sanity = json.loads(args.sanity_report.resolve().read_text(encoding="utf-8"))
    if sanity.get("status") != "pass":
        raise SystemExit("Gate-3 sanity report did not pass")

    selection = results.get("selection_evaluation")
    if not isinstance(selection, dict):
        raise SystemExit("selection_evaluation is missing")
    in_range = selection["in_range"]
    ood = selection["ood"]
    level0 = ood["level0"]
    resnet_level0 = float(level0["macro_f1"])
    resnet_in_range = float(in_range["macro_f1"])
    resnet_single = float(mean(float(ood[name]["macro_f1"]) for name in SINGLE_FACTOR_PROFILES))

    early = results.get("early_stopping", {})
    state = early.get("state", {}) if isinstance(early, dict) else {}
    training_rows = [
        row
        for row in history
        if row.get("train_accuracy") is not None and row.get("train_loss") is not None
    ]
    if not training_rows:
        raise SystemExit("history contains no training rows")
    final_train = training_rows[-1]
    resnet_train_acc = float(final_train["train_accuracy"])
    resnet_train_loss = float(final_train["train_loss"])

    pampt_best = pampt["selected_best"]
    pampt_train = pampt["training_at_stop"]
    pampt_level0 = float(pampt_best["level0_macro_f1"])
    pampt_train_acc = float(pampt_train["accuracy"])
    delta = resnet_level0 - pampt_level0
    delta_train = resnet_train_acc - pampt_train_acc

    if delta >= 0.05 and delta_train >= 0.10:
        verdict = "pampt_major_bottleneck"
        next_action = (
            "Freeze the CNN backbone for the next method comparison; only then reopen "
            "Dynamic training under a matched backbone contract."
        )
    elif 0.02 <= delta < 0.05:
        verdict = "mixed_backbone_optimization_evidence"
        next_action = (
            "Run one preregistered confirmation seed or a parameter-matched CNN; do not "
            "claim that the bottleneck is resolved."
        )
    elif delta < 0.02 and max(resnet_level0, pampt_level0) < 0.80:
        verdict = "backbone_not_dominant"
        next_action = "Open Gate 4 input, rendering, normalization, and task-separability diagnostics."
    elif resnet_train_acc >= 0.90 and resnet_level0 < 0.65:
        verdict = "train_fit_validation_generalization_gap"
        next_action = (
            "Inspect split-level structure similarity, class confusion, and label separability "
            "before changing rendering."
        )
    else:
        verdict = "inconclusive"
        next_action = "Interpret the full trajectories and preregister one narrowly targeted follow-up."

    per_class_f1 = level0.get("per_class_f1", [])
    per_class_recall = level0.get("per_class_recall", [])
    per_class = [
        {"class": name, "f1": float(f1), "recall": float(recall)}
        for name, f1, recall in zip(
            CRYSTAL_SYSTEMS,
            per_class_f1,
            per_class_recall,
            strict=False,
        )
    ]

    report = {
        "schema_version": "gate3_pampt_vs_resnet.v1",
        "verdict": verdict,
        "next_action": next_action,
        "resnet": {
            "run_dir": str(run_dir),
            "model": results.get("model"),
            "best_epoch": state.get("best_epoch"),
            "best_global_step": state.get("best_global_step"),
            "stop_epoch": state.get("stop_epoch"),
            "stopped_early": bool(results.get("compute_summary", {}).get("stopped_early")),
            "train_accuracy_at_stop": resnet_train_acc,
            "train_loss_at_stop": resnet_train_loss,
            "level0_macro_f1": resnet_level0,
            "in_range_macro_f1": resnet_in_range,
            "mean_single_factor_ood_macro_f1": resnet_single,
            "level0_per_class": per_class,
            "level0_confusion_matrix": level0.get("confusion_matrix"),
            "compute_summary": results.get("compute_summary"),
        },
        "pampt": {
            "summary_path": str(args.pampt_summary.resolve()),
            "level0_macro_f1": pampt_level0,
            "train_accuracy_at_stop": pampt_train_acc,
            "in_range_macro_f1": float(pampt_best["in_range_macro_f1"]),
            "mean_single_factor_ood_macro_f1": pampt_best.get(
                "mean_single_factor_ood_macro_f1"
            ),
        },
        "comparison": {
            "delta_level0_macro_f1": delta,
            "delta_train_accuracy": delta_train,
            "primary_rule": "ResNet best level0 Macro-F1 minus PAMPT best level0 Macro-F1",
        },
        "sanity_report": str(args.sanity_report.resolve()),
        "interpretation_boundary": (
            "Development-only matched-backbone evidence. Simulated Test, real XRD, the "
            "formal seven-run queue, and V10 remain locked."
        ),
    }

    lines = [
        "# Gate 3: PAMPT versus ML4pXRDs ResNet-18-GN",
        "",
        f"- Verdict: **{verdict}**",
        f"- Next action: **{next_action}**",
        "",
        "| Metric | PAMPT-B3 | ResNet-18-GN | Delta |",
        "|---|---:|---:|---:|",
        f"| level0 Macro-F1 | {_fmt(pampt_level0)} | {_fmt(resnet_level0)} | {_fmt(delta)} |",
        f"| Train accuracy at stop | {_fmt(pampt_train_acc)} | {_fmt(resnet_train_acc)} | {_fmt(delta_train)} |",
        f"| in-range Macro-F1 | {_fmt(pampt_best['in_range_macro_f1'])} | {_fmt(resnet_in_range)} | — |",
        f"| mean single-factor OOD Macro-F1 | {_fmt(pampt_best.get('mean_single_factor_ood_macro_f1'))} | {_fmt(resnet_single)} | — |",
        "",
        f"- ResNet best epoch: **{state.get('best_epoch')}**",
        f"- ResNet stop epoch: **{state.get('stop_epoch') or 'maximum budget'}**",
        f"- ResNet parameter count: **{results.get('model', {}).get('parameter_count')}**",
        "",
        "## ResNet level0 per-class metrics",
        "",
        "| Crystal system | F1 | Recall |",
        "|---|---:|---:|",
    ]
    lines.extend(
        f"| {row['class']} | {_fmt(row['f1'])} | {_fmt(row['recall'])} |"
        for row in per_class
    )
    lines.extend(["", report["interpretation_boundary"], ""])

    output_json = args.output_json or run_dir / "gate3_pampt_vs_resnet.json"
    output_md = args.output_md or run_dir / "gate3_pampt_vs_resnet.md"
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"JSON: {output_json}")
    print(f"Markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
