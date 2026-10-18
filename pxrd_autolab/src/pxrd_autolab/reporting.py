"""Evidence-only metrics loading and draft report generation."""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class EvidenceError(ValueError):
    """Raised when stored metrics or provenance cannot be verified."""


METRIC_KEYS = {
    "parameter_mae_normalized.mean_two_parameter": "q_mae_mean_two_parameter",
    "parameter_mae_normalized.du": "q_mae_du",
    "parameter_mae_normalized.dv": "q_mae_dv",
    "lattice_mae_angstrom.a": "lattice_a_mae_angstrom",
    "lattice_mae_angstrom.c": "lattice_c_mae_angstrom",
    "reconstruction_rmse_transformed_clean": "clean_spectral_rmse",
    "reconstruction_rmse_transformed_noisy": "noisy_spectral_rmse",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot read JSON evidence {path}: {exc}") from exc


def _path_value(record: dict[str, Any], dotted: str) -> float:
    value: Any = record
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise EvidenceError(f"missing metric field: {dotted}")
        value = value[part]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"metric {dotted} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise EvidenceError(f"metric {dotted} is not finite")
    return number


def _summary_from_seeds(seed_results: list[dict[str, Any]], dotted: str) -> dict[str, Any]:
    if not seed_results:
        raise EvidenceError("results JSON contains no seed-level test metrics")
    values = [_path_value(item, dotted) for item in seed_results]
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "seed_values": values,
    }


def read_recorded_metrics(results: dict[str, Any]) -> dict[str, Any]:
    """Recompute report summaries from seed-level values and verify stored summaries."""

    try:
        test_metrics = results["test_metrics"]
        arm_seeds = {arm: test_metrics[arm]["seed_results"] for arm in ("A", "B")}
    except (KeyError, TypeError) as exc:
        raise EvidenceError("results JSON lacks A/B seed-level test metrics") from exc
    if not all(isinstance(items, list) for items in arm_seeds.values()):
        raise EvidenceError("A/B seed_results must be lists")
    seed_ids = {
        arm: [row.get("seed") for row in rows if isinstance(row, dict)]
        for arm, rows in arm_seeds.items()
    }
    if seed_ids["A"] != seed_ids["B"] or not seed_ids["A"]:
        raise EvidenceError("A/B seed ids differ or are missing; paired comparison is invalid")

    recomputed: dict[str, dict[str, dict[str, Any]]] = {"A": {}, "B": {}}
    for arm in ("A", "B"):
        stored_summary = test_metrics[arm].get("summary", {})
        for dotted, key in METRIC_KEYS.items():
            calculated = _summary_from_seeds(arm_seeds[arm], dotted)
            stored = stored_summary.get(key)
            if not isinstance(stored, dict):
                raise EvidenceError(f"stored summary is missing {arm}.{key}")
            for field in ("mean", "sd"):
                stored_number = _path_value(stored, field)
                if not math.isclose(
                    stored_number, calculated[field], rel_tol=1e-10, abs_tol=1e-12
                ):
                    raise EvidenceError(
                        f"stored summary mismatch for {arm}.{key}.{field}: "
                        f"stored={stored_number}, recomputed={calculated[field]}"
                    )
            recomputed[arm][key] = calculated

    paired: dict[str, dict[str, Any]] = {}
    for dotted, key in METRIC_KEYS.items():
        differences = [
            _path_value(b, dotted) - _path_value(a, dotted)
            for a, b in zip(arm_seeds["A"], arm_seeds["B"], strict=True)
        ]
        paired[key] = {
            "mean_b_minus_a": statistics.fmean(differences),
            "seed_differences": differences,
        }
    return {
        "status": results.get("status", "UNKNOWN"),
        "selected_lambda": results.get("selected_lambda", "UNKNOWN"),
        "seed_ids": seed_ids["A"],
        "metrics": recomputed,
        "paired_differences": paired,
    }


def verify_lambda_selection(results: dict[str, Any], selection: dict[str, Any]) -> None:
    candidates = selection.get("candidate_results")
    selected = selection.get("selected_lambda")
    if not isinstance(candidates, dict) or not candidates:
        raise EvidenceError("lambda selection JSON has no candidate_results")
    try:
        best_key = min(
            candidates,
            key=lambda key: float(candidates[key]["best_validation_q_mae"]),
        )
        best_lambda = float(best_key)
        recorded_selected = float(selected)
        result_selected = float(results["selected_lambda"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EvidenceError("lambda selection JSON is incomplete") from exc
    if not math.isclose(best_lambda, recorded_selected, abs_tol=1e-12):
        raise EvidenceError("selected lambda is not the validation-best candidate")
    if not math.isclose(recorded_selected, result_selected, abs_tol=1e-12):
        raise EvidenceError("results JSON and lambda selection disagree")


def normalize_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Shape an explicitly synthetic fixture like the recorded-results report data."""

    metrics = fixture.get("metrics")
    if not isinstance(metrics, dict) or not all(arm in metrics for arm in ("A", "B")):
        raise EvidenceError("fixture metrics must contain A and B")
    for arm in ("A", "B"):
        for field in ("q_mae_mean_two_parameter", "clean_spectral_rmse"):
            number = metrics[arm].get(field)
            if isinstance(number, bool) or not isinstance(number, (int, float)):
                raise EvidenceError(f"fixture metric {arm}.{field} must be numeric")
            if not math.isfinite(float(number)):
                raise EvidenceError(f"fixture metric {arm}.{field} must be finite")
    return {
        "status": "PIPELINE_FIXTURE_ONLY",
        "selected_lambda": "NOT_APPLICABLE",
        "seed_ids": ["fixture"],
        "metrics": {
            arm: {
                "q_mae_mean_two_parameter": {
                    "mean": float(metrics[arm]["q_mae_mean_two_parameter"]),
                    "sd": 0.0,
                    "seed_values": [float(metrics[arm]["q_mae_mean_two_parameter"])],
                },
                "clean_spectral_rmse": {
                    "mean": float(metrics[arm]["clean_spectral_rmse"]),
                    "sd": 0.0,
                    "seed_values": [float(metrics[arm]["clean_spectral_rmse"])],
                },
            }
            for arm in ("A", "B")
        },
        "paired_differences": {},
        "history": fixture.get("history", {}),
    }


def aggregate_histories(history_json: dict[str, Any] | None) -> dict[str, list[dict[str, float]]]:
    if not history_json:
        return {}
    aggregate: dict[str, list[dict[str, float]]] = {}
    for arm in ("A", "B"):
        runs = history_json.get(arm, [])
        if not isinstance(runs, list) or not runs:
            continue
        by_epoch: dict[float, dict[str, list[float]]] = {}
        for run in runs:
            if not isinstance(run, dict) or not isinstance(run.get("history"), list):
                continue
            for row in run["history"]:
                if not isinstance(row, dict) or "epoch" not in row:
                    continue
                epoch = float(row["epoch"])
                values = by_epoch.setdefault(epoch, {})
                for metric in (
                    "train_parameter_mse",
                    "train_reconstruction_mse",
                    "validation_q_mae",
                ):
                    value = row.get(metric)
                    if isinstance(value, (int, float)) and math.isfinite(float(value)):
                        values.setdefault(metric, []).append(float(value))
        if by_epoch:
            aggregate[arm] = [
                {
                    "epoch": epoch,
                    **{
                        metric: statistics.fmean(values)
                        for metric, values in metrics.items()
                    },
                }
                for epoch, metrics in sorted(by_epoch.items())
            ]
    return aggregate


def write_metrics_plot(
    path: Path,
    run_id: str,
    data_role: str,
    metrics: dict[str, Any],
    histories: dict[str, list[dict[str, float]]],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    arms = ["A", "B"]
    colors = ["#3b6fb6", "#d17b27"]
    metric_panels = [
        ("q_mae_mean_two_parameter", "Normalized two-parameter MAE"),
        ("clean_spectral_rmse", "Clean transformed-profile RMSE"),
    ]
    for axis, (key, title) in zip(axes, metric_panels, strict=True):
        values = [metrics.get(arm, {}).get(key, {}).get("mean") for arm in arms]
        if all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in values):
            errors = [metrics[arm][key].get("sd", 0.0) for arm in arms]
            axis.bar(arms, values, yerr=errors, color=colors, capsize=4)
            axis.set_ylabel("mean ± seed SD")
        else:
            axis.text(0.5, 0.5, "UNKNOWN / NOT_RUN", ha="center", va="center")
            axis.set_xticks([])
        axis.set_title(title)
        axis.grid(axis="y", alpha=0.2)
    fig.suptitle(f"{run_id} | {data_role}")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)

    curve_path = path.with_name("loss_curves.png")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    curve_specs = (
        ("train_parameter_mse", "Training parameter MSE"),
        ("train_reconstruction_mse", "Training reconstruction MSE"),
        ("validation_q_mae", "Validation normalized-q MAE"),
    )
    for axis, (metric, title) in zip(axes, curve_specs, strict=True):
        plotted = False
        for arm, color in zip(arms, colors, strict=True):
            rows = histories.get(arm, [])
            valid = [row for row in rows if metric in row]
            if valid:
                axis.plot(
                    [row["epoch"] for row in valid],
                    [row[metric] for row in valid],
                    label=arm,
                    color=color,
                )
                plotted = True
        if plotted:
            axis.set_xlabel("epoch")
            axis.legend()
        else:
            axis.text(0.5, 0.5, "UNKNOWN / NOT_RUN", ha="center", va="center")
            axis.set_xticks([])
        axis.set_title(title)
        axis.grid(alpha=0.2)
    fig.suptitle(f"{run_id} | {data_role} | seed-mean histories")
    fig.tight_layout()
    fig.savefig(curve_path, dpi=160)
    plt.close(fig)


def write_reports(
    run_dir: Path,
    run_id: str,
    config: dict[str, Any],
    config_digest: str,
    metrics: dict[str, Any],
    histories: dict[str, list[dict[str, float]]],
    source_hashes: dict[str, str],
) -> list[Path]:
    figures = run_dir / "figures"
    figures.mkdir()
    metric_plot = figures / "ab_metrics.png"
    write_metrics_plot(metric_plot, run_id, config["data_role"], metrics["metrics"], histories)
    summary_path = run_dir / "metrics.json"
    summary_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    rows = []
    for label, key in (
        ("Normalized two-parameter MAE", "q_mae_mean_two_parameter"),
        ("Clean transformed-profile RMSE", "clean_spectral_rmse"),
    ):
        values = []
        for arm in ("A", "B"):
            value = metrics["metrics"].get(arm, {}).get(key)
            values.append(
                f"{value['mean']:.6g} ± {value['sd']:.3g}" if isinstance(value, dict) else "UNKNOWN / NOT_RUN"
            )
        rows.append(f"| {label} | {values[0]} | {values[1]} |")
    table = "\n".join(rows)
    sources = "\n".join(f"- `{name}` SHA-256: `{digest}`" for name, digest in sorted(source_hashes.items()))
    report = f"""# AutoLab report draft

**Run:** `{run_id}`<br>
**Status:** `AWAITING_REVIEW`<br>
**Data role:** `{config['data_role']}`<br>
**Claim boundary:** {config['claim_scope']}<br>
**Canonical config SHA-256:** `{config_digest}`<br>
**Selected lambda:** `{metrics.get('selected_lambda', 'UNKNOWN')}`

## Recorded A/B metrics

| Metric | A | B |
|---|---:|---:|
{table}

These values were read from machine-readable result files and recomputed from the stored seed-level values. They are not new experimental results. The figure files identify the run and data role.

## Training and validation curves

![A/B metrics](figures/ab_metrics.png)

![Training and validation curves](figures/loss_curves.png)

## Inputs and provenance

{sources or '- No external input files; explicit synthetic pipeline fixture.'}

Review the underlying result JSON and the scientific claim boundary before using this draft.
"""
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    brief_path = run_dir / "biweekly_brief.md"
    brief_path.write_text(
        f"""# Biweekly research brief draft

**Run:** `{run_id}` · **Status:** `DRAFT — HUMAN REVIEW REQUIRED`

## Goal and protocol

{config['claim_scope']}

Recorded mode: `{config['mode']}`. AutoLab P0 did not run a trainer or generate new scientific data.

## A/B evidence

{table}

Selected lambda: `{metrics.get('selected_lambda', 'UNKNOWN')}`. See `report.md` and `metrics.json` for seed-level evidence.

## Failures and diagnostics

No new training failures were generated by this report-only run. Review the source pilot failure record separately.

## Questions for the researcher

- Does the underlying evidence support the intended interpretation?
- Are the data role and limits stated accurately?
- Which next step, if any, should be proposed for approval?

This draft has not been sent to anyone and does not authorize another experiment.
""",
        encoding="utf-8",
    )
    return [summary_path, metric_plot, metric_plot.with_name("loss_curves.png"), report_path, brief_path]
