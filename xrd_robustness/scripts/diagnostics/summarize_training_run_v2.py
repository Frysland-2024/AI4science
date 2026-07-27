#!/usr/bin/env python3
"""Corrected foundation summary wrapper.

This keeps the existing report calculations but distinguishes an undertrained
clean run from a genuine clean-task failure:

- level0 >= 0.80: pass
- 0.65 <= level0 < 0.80: partial
- level0 < 0.65 while Train is still improving: inconclusive_undertrained
- level0 < 0.65 after Train plateaus: fail
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import summarize_training_run as base  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--single-factor-profiles",
        default=",".join(base.DEFAULT_SINGLE_FACTOR_PROFILES),
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument("--trend-window", type=int, default=5)
    return parser.parse_args()


def corrected_gate(report: dict) -> str:
    final = report["evaluation"]["final"]
    level0 = final.get("level0_macro_f1")
    if level0 is None:
        return "not_evaluated"
    if float(level0) >= 0.80:
        return "pass"
    if float(level0) >= 0.65:
        return "partial"
    if bool(report["training"].get("still_improving")):
        return "inconclusive_undertrained"
    return "fail"


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    history_path = run_dir / "history.json"
    if not history_path.is_file():
        raise SystemExit(f"history.json not found: {history_path}")

    history = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(history, list):
        raise SystemExit("history.json root must be a list")

    profiles = tuple(
        profile.strip()
        for profile in args.single_factor_profiles.split(",")
        if profile.strip()
    )
    if not profiles:
        raise SystemExit("at least one single-factor profile is required")

    report = base.summarize_history(
        history,
        single_factor_profiles=profiles,
        trend_window=args.trend_window,
    )
    report["schema_version"] = "foundation_diagnostic_summary.v2"
    report["gates"]["clean_level0"] = corrected_gate(report)
    report["gates"]["decision_policy"] = {
        "pass": "level0 Macro-F1 >= 0.80",
        "partial": "0.65 <= level0 Macro-F1 < 0.80",
        "inconclusive_undertrained": (
            "level0 Macro-F1 < 0.65 while recent Train accuracy rises and "
            "Train loss falls"
        ),
        "fail": "level0 Macro-F1 < 0.65 after Train plateaus",
    }
    report["run"] = {
        "run_dir": str(run_dir),
        "data_manifest_hash": base._read_optional_text(run_dir / "data_manifest_hash.txt"),
        "simulation_config_hash": base._read_optional_text(
            run_dir / "simulation_config_hash.txt"
        ),
        "training_sampler_contract_hash": base._read_optional_text(
            run_dir / "training_sampler_contract_hash.txt"
        ),
        "git_commit": base._read_optional_text(run_dir / "git_commit.txt"),
    }

    markdown = base._markdown(report)
    markdown = markdown.replace(
        "- `fail`: level0 Macro-F1 < 0.65",
        "- `inconclusive_undertrained`: level0 Macro-F1 < 0.65 while Train is still improving\n"
        "- `fail`: level0 Macro-F1 < 0.65 after Train plateaus",
    )

    output_json = args.output_json or run_dir / "foundation_diagnostic_summary.json"
    output_md = args.output_md or run_dir / "foundation_diagnostic_summary.md"
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    output_md.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"JSON: {output_json}")
    print(f"Markdown: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
