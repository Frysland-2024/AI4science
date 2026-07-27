#!/usr/bin/env python3
"""Summarize the Dynamic ERM 100e early-stopping diagnostic.

This script reads only artifacts already written inside the run directory. It does
not load Test data, real XRD, or select any additional checkpoint.
"""

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

BASELINE_30E_ID = 0.4211557861059708
BASELINE_30E_SINGLE_FACTOR_OOD = 0.35573459057941087


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--baseline-id", type=float, default=BASELINE_30E_ID)
    parser.add_argument(
        "--baseline-single-factor-ood",
        type=float,
        default=BASELINE_30E_SINGLE_FACTOR_OOD,
    )
    return parser.parse_args()


def _f(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _fmt(value: Any, digits: int = 4) -> str:
    number = _f(value)
    return "—" if number is None else f"{number:.{digits}f}"


def _find_eval(history: list[dict[str, Any]], epoch: int | None) -> dict[str, Any]:
    if epoch is not None:
        for row in history:
            if int(row.get("epoch", -1)) == int(epoch) and isinstance(row.get("ood"), dict):
                return row
    for row in reversed(history):
        if isinstance(row.get("ood"), dict) and isinstance(row.get("in_range"), dict):
            return row
    raise SystemExit("history.json contains no evaluation row")


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    history_path = run_dir / "history.json"
    results_path = run_dir / "results.json"
    if not history_path.is_file():
        raise SystemExit(f"history.json not found: {history_path}")
    if not results_path.is_file():
        raise SystemExit(f"results.json not found: {results_path}")

    history = json.loads(history_path.read_text(encoding="utf-8"))
    results = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(history, list) or not history:
        raise SystemExit("history.json root must be a non-empty list")

    early = results.get("early_stopping", {})
    state = early.get("state", {}) if isinstance(early, dict) else {}
    best_epoch = state.get("best_epoch")
    stop_epoch = state.get("stop_epoch")
    stopped_early = bool(results.get("compute_summary", {}).get("stopped_early"))

    selected = results.get("selection_evaluation")
    if not isinstance(selected, dict):
        selected = _find_eval(history, _f(best_epoch) and int(best_epoch))

    in_range = selected.get("in_range", {})
    ood = selected.get("ood", {})
    if not isinstance(in_range, dict) or not isinstance(ood, dict):
        raise SystemExit("selected evaluation is missing in_range or ood metrics")

    single_values = [
        float(ood[name]["macro_f1"])
        for name in SINGLE_FACTOR_PROFILES
        if isinstance(ood.get(name), dict) and _f(ood[name].get("macro_f1")) is not None
    ]
    if len(single_values) != len(SINGLE_FACTOR_PROFILES):
        missing = [name for name in SINGLE_FACTOR_PROFILES if not isinstance(ood.get(name), dict)]
        raise SystemExit(f"selected evaluation is missing single-factor panels: {missing}")

    selected_id = float(in_range["macro_f1"])
    selected_ood = float(mean(single_values))
    selected_level0 = _f(ood.get("level0", {}).get("macro_f1")) if isinstance(ood.get("level0"), dict) else None
    delta_id = selected_id - float(args.baseline_id)
    delta_ood = selected_ood - float(args.baseline_single_factor_ood)

    if max(delta_id, delta_ood) >= 0.05:
        budget_signal = "substantial_gain"
    elif max(delta_id, delta_ood) >= 0.02:
        budget_signal = "modest_gain"
    else:
        budget_signal = "limited_gain"

    report = {
        "schema_version": "dynamic_early_stopping_summary.v1",
        "run_dir": str(run_dir),
        "baseline_30e": {
            "in_range_macro_f1": float(args.baseline_id),
            "mean_single_factor_ood_macro_f1": float(args.baseline_single_factor_ood),
        },
        "early_stopping": {
            "enabled": bool(early.get("enabled")) if isinstance(early, dict) else False,
            "stopped_early": stopped_early,
            "best_epoch": best_epoch,
            "best_global_step": state.get("best_global_step"),
            "stop_epoch": stop_epoch,
            "stop_reason": state.get("stop_reason"),
            "minimum_epochs": early.get("minimum_epochs") if isinstance(early, dict) else None,
            "patience_validation_checks": early.get("patience_validation_checks") if isinstance(early, dict) else None,
            "min_delta": early.get("min_delta") if isinstance(early, dict) else None,
            "primary_profiles": early.get("primary_profiles") if isinstance(early, dict) else None,
        },
        "selected_checkpoint": {
            "in_range_macro_f1": selected_id,
            "mean_single_factor_ood_macro_f1": selected_ood,
            "level0_macro_f1": selected_level0,
            "delta_vs_30e_in_range": delta_id,
            "delta_vs_30e_mean_single_factor_ood": delta_ood,
        },
        "diagnostic_signal": {
            "training_budget_effect": budget_signal,
            "definition": {
                "substantial_gain": "max(ID gain, OOD gain) >= 0.05",
                "modest_gain": "0.02 <= max(ID gain, OOD gain) < 0.05",
                "limited_gain": "max(ID gain, OOD gain) < 0.02",
            },
        },
        "interpretation_boundary": (
            "Development-only evidence. This comparison does not authorize the formal 7-run, "
            "simulated Test, real XRD, or a backbone change by itself."
        ),
    }

    lines = [
        "# Dynamic ERM 100e early-stopping diagnostic",
        "",
        "## Early stopping",
        "",
        f"- Stopped early: **{stopped_early}**",
        f"- Best epoch: **{best_epoch}**",
        f"- Stop epoch: **{stop_epoch if stop_epoch is not None else 'maximum budget'}**",
        f"- Stop reason: **{state.get('stop_reason') or 'maximum budget reached'}**",
        "",
        "## Best-checkpoint comparison with the matched Dynamic 30e pilot",
        "",
        "| Metric | Dynamic 30e | Dynamic 100e ES best | Delta |",
        "|---|---:|---:|---:|",
        f"| in-range Macro-F1 | {_fmt(args.baseline_id)} | {_fmt(selected_id)} | {_fmt(delta_id)} |",
        f"| mean single-factor OOD Macro-F1 | {_fmt(args.baseline_single_factor_ood)} | {_fmt(selected_ood)} | {_fmt(delta_ood)} |",
        f"| level0 Macro-F1 | — | {_fmt(selected_level0)} | — |",
        "",
        f"- Training-budget signal: **{budget_signal}**",
        "",
        "## Interpretation boundary",
        "",
        report["interpretation_boundary"],
        "",
    ]

    output_json = args.output_json or run_dir / "dynamic_early_stopping_summary.json"
    output_md = args.output_md or run_dir / "dynamic_early_stopping_summary.md"
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"JSON: {output_json}")
    print(f"Markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
