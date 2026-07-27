#!/usr/bin/env python3
"""Summarize a Clean early-stopping diagnostic from the selected best checkpoint."""

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
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    return parser.parse_args()


def slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    x_mean = (len(values) - 1) / 2.0
    y_mean = mean(values)
    denominator = sum((i - x_mean) ** 2 for i in range(len(values)))
    if denominator == 0:
        return None
    return sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values)) / denominator


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    results_path = run_dir / "results.json"
    history_path = run_dir / "history.json"
    if not results_path.is_file() or not history_path.is_file():
        raise SystemExit("results.json and history.json are required")

    results = json.loads(results_path.read_text(encoding="utf-8"))
    history = json.loads(history_path.read_text(encoding="utf-8"))
    selection = results.get("selection_evaluation")
    early = results.get("early_stopping", {})
    state = early.get("state", {})
    if not isinstance(selection, dict):
        raise SystemExit("selection_evaluation is missing; the run was not completed with early stopping")

    ood = selection.get("ood", {})
    level0 = ood.get("level0", {})
    in_range = selection.get("in_range", {})
    level0_f1 = float(level0["macro_f1"])
    in_range_f1 = float(in_range["macro_f1"])
    single_values = [
        float(ood[name]["macro_f1"])
        for name in SINGLE_FACTOR_PROFILES
        if isinstance(ood.get(name), dict)
    ]
    mean_single = mean(single_values) if single_values else None

    training_rows = [
        row for row in history
        if row.get("train_accuracy") is not None and row.get("train_loss") is not None
    ]
    recent = training_rows[-min(5, len(training_rows)):]
    acc_slope = slope([float(row["train_accuracy"]) for row in recent])
    loss_slope = slope([float(row["train_loss"]) for row in recent])
    train_still_improving = bool(
        acc_slope is not None and loss_slope is not None and acc_slope > 0 and loss_slope < 0
    )
    final_train = training_rows[-1]
    stopped_early = bool(results.get("compute_summary", {}).get("stopped_early"))

    if level0_f1 >= 0.80:
        gate = "pass"
    elif level0_f1 >= 0.65:
        gate = "partial"
    elif stopped_early:
        gate = "fail_validation_plateau"
    elif train_still_improving:
        gate = "inconclusive_max_budget"
    else:
        gate = "fail"

    per_class_f1 = level0.get("per_class_f1", [])
    per_class_recall = level0.get("per_class_recall", [])
    per_class = [
        {"class": name, "f1": float(f1), "recall": float(recall)}
        for name, f1, recall in zip(
            CRYSTAL_SYSTEMS, per_class_f1, per_class_recall, strict=False
        )
    ]

    report = {
        "schema_version": "clean_early_stopping_summary.v1",
        "run_dir": str(run_dir),
        "gate": gate,
        "early_stopping": {
            "stopped_early": stopped_early,
            "best_epoch": state.get("best_epoch"),
            "best_global_step": state.get("best_global_step"),
            "stop_epoch": state.get("stop_epoch"),
            "stop_reason": state.get("stop_reason"),
            "maximum_epochs": early.get("max_epochs"),
            "minimum_epochs": early.get("minimum_epochs"),
            "patience_validation_checks": early.get("patience_validation_checks"),
            "min_delta": early.get("min_delta"),
            "primary_profiles": early.get("primary_profiles"),
        },
        "selected_best": {
            "level0_macro_f1": level0_f1,
            "in_range_macro_f1": in_range_f1,
            "mean_single_factor_ood_macro_f1": mean_single,
            "level0_per_class": per_class,
        },
        "training_at_stop": {
            "epoch": final_train.get("epoch"),
            "global_step": final_train.get("global_step"),
            "accuracy": float(final_train["train_accuracy"]),
            "loss": float(final_train["train_loss"]),
            "recent_accuracy_slope": acc_slope,
            "recent_loss_slope": loss_slope,
            "still_improving": train_still_improving,
        },
    }

    lines = [
        "# Clean early-stopping diagnostic summary",
        "",
        f"- Gate: **{gate}**",
        f"- Stopped early: **{stopped_early}**",
        f"- Best epoch / step: **{state.get('best_epoch')} / {state.get('best_global_step')}**",
        f"- Stop epoch: **{state.get('stop_epoch')}**",
        f"- Stop reason: **{state.get('stop_reason') or 'maximum budget reached'}**",
        f"- Selected best level0 Macro-F1: **{fmt(level0_f1)}**",
        f"- Selected best in-range Macro-F1: **{fmt(in_range_f1)}**",
        f"- Selected best mean single-factor OOD Macro-F1: **{fmt(mean_single)}**",
        f"- Train accuracy/loss at stop: **{fmt(final_train['train_accuracy'])} / {fmt(final_train['train_loss'])}**",
        f"- Train still improving at stop: **{train_still_improving}**",
        "",
        "## Selected best level0 per-class metrics",
        "",
        "| Crystal system | F1 | Recall |",
        "|---|---:|---:|",
    ]
    for row in per_class:
        lines.append(f"| {row['class']} | {fmt(row['f1'])} | {fmt(row['recall'])} |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `pass`: selected best level0 Macro-F1 >= 0.80",
        "- `partial`: 0.65 <= selected best level0 Macro-F1 < 0.80",
        "- `fail_validation_plateau`: selected best level0 Macro-F1 < 0.65 and the registered early-stopping rule fired",
        "- `inconclusive_max_budget`: selected best level0 Macro-F1 < 0.65, maximum budget was reached, and Train was still improving",
        "",
        "Development-only evidence; simulated Test and real XRD remain locked.",
    ])

    output_json = args.output_json or run_dir / "clean_early_stopping_summary.json"
    output_md = args.output_md or run_dir / "clean_early_stopping_summary.md"
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"JSON: {output_json}")
    print(f"Markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
