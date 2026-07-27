#!/usr/bin/env python3
"""Summarize one V9 training run without touching locked Test or real-XRD data.

The script reads only artifacts already present in a run directory, primarily
``history.json`` and provenance hashes. It does not load a checkpoint, render a
new spectrum, or perform model selection.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
except Exception:  # pragma: no cover - keeps the report usable in isolation
    CRYSTAL_SYSTEMS = (
        "triclinic",
        "monoclinic",
        "orthorhombic",
        "tetragonal",
        "trigonal",
        "hexagonal",
        "cubic",
    )


DEFAULT_SINGLE_FACTOR_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--single-factor-profiles",
        default=",".join(DEFAULT_SINGLE_FACTOR_PROFILES),
        help="comma-separated OOD profiles used for the mean single-factor score",
    )
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    parser.add_argument(
        "--trend-window",
        type=int,
        default=5,
        help="number of latest training epochs used for loss/accuracy slopes",
    )
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return sum(materialized) / len(materialized) if materialized else None


def _slope(values: Sequence[float]) -> float | None:
    """Return the ordinary-least-squares slope against epoch order."""

    if len(values) < 2:
        return None
    x_mean = (len(values) - 1) / 2.0
    y_mean = sum(values) / len(values)
    denominator = sum((index - x_mean) ** 2 for index in range(len(values)))
    if denominator <= 0:
        return None
    numerator = sum(
        (index - x_mean) * (value - y_mean)
        for index, value in enumerate(values)
    )
    return numerator / denominator


def _read_optional_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value or None


def _per_class(metrics: dict[str, Any] | None) -> list[dict[str, Any]] | None:
    if not isinstance(metrics, dict):
        return None
    f1 = metrics.get("per_class_f1")
    recall = metrics.get("per_class_recall")
    if not isinstance(f1, list) or not isinstance(recall, list):
        return None
    if len(f1) != len(CRYSTAL_SYSTEMS) or len(recall) != len(CRYSTAL_SYSTEMS):
        return None
    return [
        {
            "class": class_name,
            "f1": _optional_float(class_f1),
            "recall": _optional_float(class_recall),
        }
        for class_name, class_f1, class_recall in zip(
            CRYSTAL_SYSTEMS, f1, recall, strict=True
        )
    ]


def _best(rows: list[dict[str, Any]], key: str) -> dict[str, Any] | None:
    candidates = [row for row in rows if row.get(key) is not None]
    return max(candidates, key=lambda row: float(row[key])) if candidates else None


def summarize_history(
    history: list[dict[str, Any]],
    *,
    single_factor_profiles: Sequence[str],
    trend_window: int,
) -> dict[str, Any]:
    if not history:
        raise ValueError("history.json is empty")
    if trend_window < 2:
        raise ValueError("trend-window must be at least 2")

    training_rows = [
        row
        for row in history
        if _optional_float(row.get("train_loss")) is not None
        and _optional_float(row.get("train_accuracy")) is not None
    ]
    if not training_rows:
        raise ValueError("history.json contains no finite training rows")

    recent = training_rows[-min(trend_window, len(training_rows)) :]
    train_loss_slope = _slope([float(row["train_loss"]) for row in recent])
    train_accuracy_slope = _slope([float(row["train_accuracy"]) for row in recent])
    final_training = training_rows[-1]

    trajectory: list[dict[str, Any]] = []
    for row in history:
        in_range = row.get("in_range")
        ood = row.get("ood")
        if not isinstance(in_range, dict) or not isinstance(ood, dict):
            continue
        single_factor_values = [
            _optional_float(ood.get(profile, {}).get("macro_f1"))
            for profile in single_factor_profiles
            if isinstance(ood.get(profile), dict)
        ]
        single_factor_values = [value for value in single_factor_values if value is not None]
        in_range_f1 = _optional_float(in_range.get("macro_f1"))
        level0 = ood.get("level0") if isinstance(ood.get("level0"), dict) else None
        level0_f1 = _optional_float(level0.get("macro_f1")) if level0 else None
        mean_single_factor = _mean(single_factor_values)
        trajectory.append(
            {
                "epoch": int(row.get("epoch", 0)),
                "global_step": int(row.get("global_step", 0)),
                "train_loss": _optional_float(row.get("train_loss")),
                "train_accuracy": _optional_float(row.get("train_accuracy")),
                "in_range_macro_f1": in_range_f1,
                "level0_macro_f1": level0_f1,
                "mean_single_factor_ood_macro_f1": mean_single_factor,
                "id_to_ood_gap": (
                    in_range_f1 - mean_single_factor
                    if in_range_f1 is not None and mean_single_factor is not None
                    else None
                ),
                "in_range_per_class": _per_class(in_range),
                "level0_per_class": _per_class(level0),
                "worst_group_f1": _optional_float(in_range.get("worst_group_f1")),
            }
        )
    if not trajectory:
        raise ValueError("history.json contains no Validation/OOD evaluation rows")

    final_eval = trajectory[-1]
    final_train_accuracy = float(final_training["train_accuracy"])
    final_train_loss = float(final_training["train_loss"])
    train_still_improving = bool(
        train_accuracy_slope is not None
        and train_loss_slope is not None
        and train_accuracy_slope > 0.0
        and train_loss_slope < 0.0
    )
    strong_underfit_signal = bool(final_train_accuracy < 0.60 and train_still_improving)

    level0_score = final_eval.get("level0_macro_f1")
    if level0_score is None:
        clean_gate = "not_evaluated"
    elif level0_score >= 0.80:
        clean_gate = "pass"
    elif level0_score >= 0.65:
        clean_gate = "partial"
    else:
        clean_gate = "fail"

    return {
        "schema_version": "foundation_diagnostic_summary.v1",
        "single_factor_profiles": list(single_factor_profiles),
        "training": {
            "epochs_recorded": len(training_rows),
            "final_epoch": int(final_training.get("epoch", len(training_rows))),
            "final_global_step": int(final_training.get("global_step", 0)),
            "final_loss": final_train_loss,
            "final_accuracy": final_train_accuracy,
            "trend_window": len(recent),
            "loss_slope_per_epoch": train_loss_slope,
            "accuracy_slope_per_epoch": train_accuracy_slope,
            "still_improving": train_still_improving,
            "strong_underfit_signal": strong_underfit_signal,
        },
        "evaluation": {
            "trajectory": trajectory,
            "final": final_eval,
            "best_in_range": _best(trajectory, "in_range_macro_f1"),
            "best_level0": _best(trajectory, "level0_macro_f1"),
            "best_mean_single_factor_ood": _best(
                trajectory, "mean_single_factor_ood_macro_f1"
            ),
        },
        "gates": {
            "clean_level0": clean_gate,
            "thresholds": {
                "clean_pass_macro_f1": 0.80,
                "clean_partial_macro_f1": 0.65,
                "strong_underfit_train_accuracy": 0.60,
            },
        },
    }


def _format(value: Any, digits: int = 4) -> str:
    number = _optional_float(value)
    return "—" if number is None else f"{number:.{digits}f}"


def _markdown(report: dict[str, Any]) -> str:
    training = report["training"]
    evaluation = report["evaluation"]
    final_eval = evaluation["final"]
    lines = [
        "# Foundation diagnostic summary",
        "",
        "## Training state",
        "",
        f"- Final epoch / step: **{training['final_epoch']} / {training['final_global_step']}**",
        f"- Final Train accuracy: **{_format(training['final_accuracy'])}**",
        f"- Final Train loss: **{_format(training['final_loss'])}**",
        f"- Recent accuracy slope: **{_format(training['accuracy_slope_per_epoch'], 6)} per epoch**",
        f"- Recent loss slope: **{_format(training['loss_slope_per_epoch'], 6)} per epoch**",
        f"- Train still improving: **{training['still_improving']}**",
        f"- Strong underfitting signal: **{training['strong_underfit_signal']}**",
        "",
        "## Validation trajectory",
        "",
        "| Epoch | Train Acc | Train Loss | level0 F1 | in-range F1 | mean single-factor OOD | ID→OOD gap |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in evaluation["trajectory"]:
        lines.append(
            "| {epoch} | {train_accuracy} | {train_loss} | {level0} | {in_range} | {ood} | {gap} |".format(
                epoch=row["epoch"],
                train_accuracy=_format(row["train_accuracy"]),
                train_loss=_format(row["train_loss"]),
                level0=_format(row["level0_macro_f1"]),
                in_range=_format(row["in_range_macro_f1"]),
                ood=_format(row["mean_single_factor_ood_macro_f1"]),
                gap=_format(row["id_to_ood_gap"]),
            )
        )

    lines.extend(
        [
            "",
            "## Gate result",
            "",
            f"- Clean level0 Gate: **{report['gates']['clean_level0']}**",
            "- `pass`: level0 Macro-F1 ≥ 0.80",
            "- `partial`: 0.65 ≤ level0 Macro-F1 < 0.80",
            "- `fail`: level0 Macro-F1 < 0.65",
        ]
    )

    for title, key in (
        ("Final level0 per-class metrics", "level0_per_class"),
        ("Final in-range per-class metrics", "in_range_per_class"),
    ):
        class_rows = final_eval.get(key)
        if not class_rows:
            continue
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                "| Crystal system | F1 | Recall |",
                "|---|---:|---:|",
            ]
        )
        for row in class_rows:
            lines.append(
                f"| {row['class']} | {_format(row['f1'])} | {_format(row['recall'])} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This report is descriptive development evidence only. It does not select a checkpoint,",
            "open simulated Test, access real XRD, or authorize the formal 7-run stage.",
            "",
        ]
    )
    return "\n".join(lines)


def _self_test() -> None:
    history = []
    for epoch in range(1, 31):
        row: dict[str, Any] = {
            "epoch": epoch,
            "global_step": epoch * 10,
            "train_loss": 2.0 - 0.02 * epoch,
            "train_accuracy": 0.10 + 0.01 * epoch,
        }
        if epoch % 10 == 0:
            metrics = {
                "macro_f1": 0.20 + 0.01 * epoch,
                "per_class_f1": [0.2] * 7,
                "per_class_recall": [0.2] * 7,
                "worst_group_f1": 0.2,
            }
            row["in_range"] = metrics
            row["ood"] = {
                "level0": {
                    **metrics,
                    "macro_f1": 0.50 + 0.01 * epoch,
                },
                **{
                    profile: {**metrics, "macro_f1": 0.15 + 0.005 * epoch}
                    for profile in DEFAULT_SINGLE_FACTOR_PROFILES
                },
            }
        history.append(row)
    report = summarize_history(
        history,
        single_factor_profiles=DEFAULT_SINGLE_FACTOR_PROFILES,
        trend_window=5,
    )
    assert report["training"]["still_improving"] is True
    assert report["evaluation"]["final"]["level0_macro_f1"] == 0.80
    assert report["gates"]["clean_level0"] == "pass"
    assert len(report["evaluation"]["trajectory"]) == 3
    print("SELF-TEST PASS")


def main() -> int:
    args = parse_args()
    if args.self_test:
        _self_test()
        return 0

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

    report = summarize_history(
        history,
        single_factor_profiles=profiles,
        trend_window=args.trend_window,
    )
    report["run"] = {
        "run_dir": str(run_dir),
        "data_manifest_hash": _read_optional_text(run_dir / "data_manifest_hash.txt"),
        "simulation_config_hash": _read_optional_text(
            run_dir / "simulation_config_hash.txt"
        ),
        "training_sampler_contract_hash": _read_optional_text(
            run_dir / "training_sampler_contract_hash.txt"
        ),
        "git_commit": _read_optional_text(run_dir / "git_commit.txt"),
    }
    markdown = _markdown(report)

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
