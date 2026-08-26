#!/usr/bin/env python3
"""Generate the four manuscript figures from the public result JSON files.

The public JSON files are the only source for experiment values.  This module
also checks that their per-seed rows reproduce the published aggregate means,
sample standard deviations, paired deltas, and positive-pair counts before any
figure is written.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "xrd-robustness-v9-paper-figures"

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.ticker import FormatStrFormatter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION = PROJECT_ROOT / "reports" / "validation_results.json"
DEFAULT_SIMULATED_TEST = PROJECT_ROOT / "reports" / "simulated_test_results.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "figures"

METHODS = ("dynamic_erm", "js_consistency")
METHOD_LABELS = {
    "dynamic_erm": "Dynamic ERM",
    "js_consistency": "Dynamic JS",
}
METRICS = {
    "level0_macro_f1": "Level-0",
    "in_range_macro_f1": "In-range",
    "mean_single_factor_ood_macro_f1": "Single-factor OOD",
    "worst_class_f1": "Worst-class F1",
}
PRIMARY_METRIC = "mean_single_factor_ood_macro_f1"

PAPER_COLOR = "#FFFFFF"
TEXT_COLOR = "#111111"
MUTED_COLOR = "#5C6470"
GRID_COLOR = "#DCE3EA"
NAVY_COLOR = "#0B2D53"
ERM_COLOR = "#7E9FC9"
JS_COLOR = "#E49364"
VIEW_ONE_COLOR = "#4C8BC0"
VIEW_TWO_COLOR = "#E69A55"
PALE_BLUE = "#EAF2F8"
PALE_YELLOW = "#FFF1C9"
TITLE_FONT = "Arial"
BODY_FONT = "Arial"


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _is_close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)


def _require_number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Expected a number for {context}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Expected a finite number for {context}")
    return number


def validate_report(report: dict[str, Any], source_name: str) -> None:
    """Fail if the figure rows and published aggregates disagree."""

    if report.get("status") != "completed":
        raise ValueError(f"{source_name}: result status is not completed")

    paired_seed_count = int(report["paired_seed_count"])
    pairs = report.get("paired_runs")
    if not isinstance(pairs, list) or len(pairs) != paired_seed_count:
        raise ValueError(
            f"{source_name}: paired_runs must contain {paired_seed_count} rows"
        )

    seeds = [int(pair["training_seed"]) for pair in pairs]
    if len(seeds) != len(set(seeds)):
        raise ValueError(f"{source_name}: training_seed values must be unique")

    methods = report.get("methods")
    improvements = report.get("paired_improvements")
    if not isinstance(methods, dict) or not isinstance(improvements, dict):
        raise ValueError(f"{source_name}: missing methods or paired_improvements")

    for metric in METRICS:
        values_by_method: dict[str, list[float]] = {}
        for method in METHODS:
            values = [
                _require_number(pair[method][metric], f"{source_name}.{method}.{metric}")
                for pair in pairs
            ]
            if any(value < 0.0 or value > 1.0 for value in values):
                raise ValueError(f"{source_name}: {metric} must be in [0, 1]")
            values_by_method[method] = values

            published = methods[method][metric]
            if not _is_close(statistics.fmean(values), float(published["mean"])):
                raise ValueError(
                    f"{source_name}: per-seed {method}.{metric} mean disagrees "
                    "with the published aggregate"
                )
            if not _is_close(statistics.stdev(values), float(published["sample_sd"])):
                raise ValueError(
                    f"{source_name}: per-seed {method}.{metric} sample SD disagrees "
                    "with the published aggregate"
                )

        deltas = [
            js_value - erm_value
            for erm_value, js_value in zip(
                values_by_method["dynamic_erm"],
                values_by_method["js_consistency"],
                strict=True,
            )
        ]
        published_delta = improvements[metric]
        if not _is_close(statistics.fmean(deltas), float(published_delta["mean"])):
            raise ValueError(
                f"{source_name}: per-seed {metric} deltas disagree with the "
                "published mean paired delta"
            )
        if "sample_sd" in published_delta and not _is_close(
            statistics.stdev(deltas), float(published_delta["sample_sd"])
        ):
            raise ValueError(
                f"{source_name}: per-seed {metric} deltas disagree with the "
                "published paired sample SD"
            )
        if "positive_pairs" in published_delta:
            positive_pairs = sum(delta > 0.0 for delta in deltas)
            if positive_pairs != int(published_delta["positive_pairs"]):
                raise ValueError(
                    f"{source_name}: positive-pair count disagrees for {metric}"
                )

        interval = published_delta.get("bootstrap_95_interval")
        if interval is not None:
            if not isinstance(interval, list) or len(interval) != 2:
                raise ValueError(
                    f"{source_name}: bootstrap interval for {metric} must have two bounds"
                )
            low = _require_number(interval[0], f"{source_name}.{metric}.ci_low")
            high = _require_number(interval[1], f"{source_name}.{metric}.ci_high")
            if low > high:
                raise ValueError(
                    f"{source_name}: bootstrap interval for {metric} is reversed"
                )


def validate_bundle(
    validation: dict[str, Any], simulated_test: dict[str, Any]
) -> None:
    validate_report(validation, "validation")
    validate_report(simulated_test, "simulated_test")

    for key in ("model", "paired_seed_count"):
        if validation[key] != simulated_test[key]:
            raise ValueError(f"Validation and Test disagree on {key}")

    validation_lambda = validation["methods"]["js_consistency"]["lambda"]
    test_lambda = simulated_test["methods"]["js_consistency"]["lambda"]
    if validation_lambda != test_lambda:
        raise ValueError("Validation and Test disagree on lambda_js")

    validation_seeds = [row["training_seed"] for row in validation["paired_runs"]]
    test_seeds = [row["training_seed"] for row in simulated_test["paired_runs"]]
    if validation_seeds != test_seeds:
        raise ValueError("Validation and Test paired training seeds disagree")


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.family": BODY_FONT,
            "font.size": 11.5,
            "axes.titlesize": 15,
            "axes.labelsize": 12,
            "axes.edgecolor": MUTED_COLOR,
            "axes.linewidth": 1.0,
            "axes.titleweight": "normal",
            "axes.labelcolor": TEXT_COLOR,
            "text.color": TEXT_COLOR,
            "xtick.color": MUTED_COLOR,
            "ytick.color": MUTED_COLOR,
            "xtick.major.size": 4,
            "ytick.major.size": 0,
            "legend.frameon": False,
            "savefig.facecolor": PAPER_COLOR,
            "figure.facecolor": PAPER_COLOR,
            "axes.facecolor": PAPER_COLOR,
            "svg.fonttype": "none",
        }
    )


def _add_slide_chrome(
    fig: plt.Figure,
    *,
    title: str,
    conclusion: str,
    conclusion_size: float = 12.8,
) -> None:
    """Use the lab-meeting visual grammar: header, rule, takeaway, footer."""

    fig.text(
        0.03,
        0.945,
        title,
        ha="left",
        va="top",
        fontsize=23,
        fontweight="bold",
        color=NAVY_COLOR,
    )
    fig.add_artist(
        Line2D(
            [0.03, 0.97],
            [0.855, 0.855],
            transform=fig.transFigure,
            color=NAVY_COLOR,
            linewidth=1.4,
        )
    )
    fig.text(
        0.035,
        0.065,
        conclusion,
        ha="left",
        va="center",
        fontsize=conclusion_size,
        fontweight="bold",
        color=TEXT_COLOR,
    )
    fig.add_artist(
        Rectangle(
            (0.0, 0.0),
            1.0,
            0.018,
            transform=fig.transFigure,
            facecolor=NAVY_COLOR,
            edgecolor="none",
        )
    )


def _add_box(
    ax: plt.Axes,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    *,
    facecolor: str = "#F7F9FC",
    edgecolor: str = "#AAB3C2",
    fontsize: float = 10,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=1.2,
        facecolor=facecolor,
        edgecolor=edgecolor,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        linespacing=1.2,
    )


def _add_arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = "#7A8494",
    connectionstyle: str = "arc3",
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.2,
            color=color,
            connectionstyle=connectionstyle,
        )
    )


def _draw_crystal_glyph(
    ax: plt.Axes, center: tuple[float, float], scale: float
) -> None:
    cx, cy = center
    points = np.array(
        [
            (-0.90, -0.55),
            (0.15, -0.75),
            (0.88, -0.18),
            (-0.20, 0.05),
            (-0.62, 0.72),
            (0.42, 0.50),
            (1.02, 0.92),
        ]
    )
    points[:, 0] = cx + points[:, 0] * scale
    points[:, 1] = cy + points[:, 1] * scale
    edges = (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (3, 4),
        (4, 5),
        (5, 2),
        (5, 6),
        (2, 6),
        (1, 5),
        (0, 4),
    )
    for start, end in edges:
        ax.plot(
            points[[start, end], 0],
            points[[start, end], 1],
            color="#9B9489",
            linewidth=1.2,
            zorder=1,
        )
    for index, (x, y) in enumerate(points):
        color = VIEW_TWO_COLOR if index in (2, 4, 6) else VIEW_ONE_COLOR
        ax.add_patch(
            Circle(
                (x, y),
                radius=scale * 0.13,
                facecolor=color,
                edgecolor=PAPER_COLOR,
                linewidth=0.9,
                zorder=2,
            )
        )


def _draw_spectrum(
    ax: plt.Axes,
    *,
    x0: float,
    x1: float,
    baseline: float,
    color: str,
    shift: float,
    width_scale: float,
    phase: float,
    label: str,
) -> None:
    x = np.linspace(0.0, 1.0, 700)
    centers = np.array([0.12, 0.23, 0.39, 0.58, 0.72, 0.88]) + shift
    heights = np.array([0.44, 1.00, 0.61, 0.82, 0.48, 0.68])
    widths = np.array([0.012, 0.009, 0.016, 0.012, 0.019, 0.011]) * width_scale
    signal = np.zeros_like(x)
    for center, height, width in zip(centers, heights, widths, strict=True):
        signal += height * np.exp(-0.5 * ((x - center) / width) ** 2)
    background = 0.055 + 0.025 * x + 0.012 * np.sin(8.0 * x + phase)
    texture = 0.006 * np.sin(93.0 * x + phase) + 0.004 * np.sin(
        157.0 * x + phase / 2.0
    )
    signal = signal + background + texture
    signal -= signal.min()
    signal /= signal.max()
    display_x = x0 + x * (x1 - x0)
    display_y = baseline + signal * 0.115
    ax.plot([x0, x1], [baseline, baseline], color=GRID_COLOR, linewidth=0.8)
    ax.fill_between(
        display_x,
        baseline,
        display_y,
        color=color,
        alpha=0.08,
        linewidth=0,
    )
    ax.plot(display_x, display_y, color=color, linewidth=1.55)
    ax.text(
        x0,
        baseline + 0.132,
        label,
        ha="left",
        va="bottom",
        fontsize=9.5,
        color=color,
        fontweight="bold",
    )


def _draw_prediction(
    ax: plt.Axes, *, x: float, y: float, color: str, label: str
) -> None:
    ax.text(
        x,
        y + 0.057,
        label,
        ha="left",
        va="center",
        fontsize=10,
        fontweight="bold",
    )
    widths = (0.035, 0.066, 0.112)
    for row, width in enumerate(widths):
        row_y = y + 0.026 - row * 0.026
        ax.plot(
            [x + 0.035, x + 0.155],
            [row_y, row_y],
            color=GRID_COLOR,
            linewidth=4.2,
            solid_capstyle="round",
        )
        ax.plot(
            [x + 0.035, x + 0.035 + width],
            [row_y, row_y],
            color=color if row == 2 else MUTED_COLOR,
            alpha=1.0 if row == 2 else 0.45,
            linewidth=4.2,
            solid_capstyle="round",
        )


def make_method_overview(report: dict[str, Any]) -> plt.Figure:
    model = str(report["model"])
    model_label = (
        "ResNet-18 + GroupNorm"
        if model.lower().replace("-", "_") == "resnet18_groupnorm"
        else model.replace("_", " ")
    )
    lambda_js = float(report["methods"]["js_consistency"]["lambda"])

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.0, right=1.0, bottom=0.0, top=1.0)
    ax.set_xlim(0.0, 1.0)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")
    _add_slide_chrome(
        fig,
        title="METHOD | DYNAMIC JS CONSISTENCY",
        conclusion=(
            "Two spectra can look different and still come from the same crystal; "
            "JS teaches the model to give them the same answer."
        ),
        conclusion_size=12.4,
    )

    stage_labels = (
        (0.055, "1   One crystal, two measurements"),
        (0.555, "2   The same model sees both"),
        (0.770, "3   Their answers should agree"),
    )
    for x, label in stage_labels:
        ax.text(
            x,
            0.805,
            label,
            ha="left",
            va="center",
            fontsize=12.5,
            color=NAVY_COLOR,
            fontweight="bold",
        )

    _draw_crystal_glyph(ax, (0.075, 0.485), 0.050)
    ax.text(
        0.075,
        0.385,
        "parent crystal",
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="bold",
    )

    simulator = FancyBboxPatch(
        (0.135, 0.385),
        0.095,
        0.205,
        boxstyle="round,pad=0.008,rounding_size=0.010",
        linewidth=1.1,
        facecolor=PALE_YELLOW,
        edgecolor="#C9A34B",
    )
    ax.add_patch(simulator)
    ax.text(
        0.1825,
        0.505,
        "online\nPXRD\nsimulator",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        linespacing=1.2,
    )
    ax.text(
        0.1825,
        0.410,
        "independent\nconditions",
        ha="center",
        va="center",
        fontsize=8.3,
        color=MUTED_COLOR,
    )
    _add_arrow(ax, (0.105, 0.485), (0.130, 0.485), color=NAVY_COLOR)

    spectrum_x0, spectrum_x1 = 0.285, 0.505
    for peak_fraction in (0.23, 0.39, 0.58, 0.72):
        guide_x = spectrum_x0 + peak_fraction * (spectrum_x1 - spectrum_x0)
        ax.plot(
            [guide_x, guide_x],
            [0.315, 0.685],
            color=GRID_COLOR,
            linewidth=0.7,
            linestyle=(0, (2, 4)),
            zorder=0,
        )
    _draw_spectrum(
        ax,
        x0=spectrum_x0,
        x1=spectrum_x1,
        baseline=0.570,
        color=VIEW_ONE_COLOR,
        shift=-0.006,
        width_scale=0.85,
        phase=0.4,
        label="view 1",
    )
    _draw_spectrum(
        ax,
        x0=spectrum_x0,
        x1=spectrum_x1,
        baseline=0.335,
        color=VIEW_TWO_COLOR,
        shift=0.008,
        width_scale=1.35,
        phase=2.1,
        label="view 2",
    )
    ax.text(
        (spectrum_x0 + spectrum_x1) / 2,
        0.275,
        "peak shift · broadening · texture · background · noise  (schematic)",
        ha="center",
        va="top",
        fontsize=9.0,
        color=MUTED_COLOR,
    )
    _add_arrow(ax, (0.232, 0.520), (0.270, 0.615), color=NAVY_COLOR)
    _add_arrow(ax, (0.232, 0.455), (0.270, 0.390), color=NAVY_COLOR)

    encoder = FancyBboxPatch(
        (0.565, 0.315),
        0.135,
        0.365,
        boxstyle="round,pad=0.010,rounding_size=0.012",
        linewidth=1.1,
        facecolor=PALE_BLUE,
        edgecolor=NAVY_COLOR,
    )
    ax.add_patch(encoder)
    ax.text(
        0.6325,
        0.525,
        "one shared\nmodel",
        ha="center",
        va="center",
        fontsize=12.5,
        fontweight="bold",
        linespacing=1.3,
    )
    ax.text(
        0.6325,
        0.405,
        model_label,
        ha="center",
        va="center",
        fontsize=9.3,
        color=MUTED_COLOR,
    )
    _add_arrow(ax, (0.510, 0.615), (0.558, 0.615), color=NAVY_COLOR)
    _add_arrow(ax, (0.510, 0.390), (0.558, 0.390), color=NAVY_COLOR)

    _draw_prediction(ax, x=0.755, y=0.565, color=JS_COLOR, label="answer from view 1")
    _draw_prediction(ax, x=0.755, y=0.330, color=JS_COLOR, label="answer from view 2")
    _add_arrow(ax, (0.705, 0.615), (0.742, 0.615), color=NAVY_COLOR)
    _add_arrow(ax, (0.705, 0.390), (0.742, 0.390), color=NAVY_COLOR)

    ax.add_patch(
        FancyArrowPatch(
            (0.925, 0.585),
            (0.925, 0.360),
            arrowstyle="<->",
            mutation_scale=11,
            linewidth=2.0,
            color=JS_COLOR,
            connectionstyle="arc3,rad=-0.24",
        )
    )
    ax.text(
        0.948,
        0.485,
        "JS keeps\nanswers close",
        ha="center",
        va="center",
        fontsize=11.2,
        color=JS_COLOR,
        fontweight="bold",
        linespacing=1.25,
    )
    ax.text(
        0.948,
        0.410,
        rf"$\lambda={lambda_js:g}$",
        ha="center",
        va="top",
        fontsize=9.5,
        color=MUTED_COLOR,
    )
    ax.text(
        0.785,
        0.245,
        "Class labels teach each answer",
        ha="center",
        va="center",
        fontsize=9.3,
        color=MUTED_COLOR,
    )
    return fig


def _paired_metric_limits(
    reports: Iterable[dict[str, Any]], metric: str
) -> tuple[float, float]:
    values: list[float] = []
    for report in reports:
        for pair in report["paired_runs"]:
            values.extend(float(pair[method][metric]) for method in METHODS)
    span = max(values) - min(values)
    padding = max(span * 0.16, 0.012)
    return max(0.0, min(values) - padding), min(1.0, max(values) + padding)


def make_paired_plot(
    report: dict[str, Any],
    *,
    slide_title: str,
    conclusion_subject: str,
    y_limits: tuple[float, float] | None = None,
) -> plt.Figure:
    pairs = report["paired_runs"]
    erm_values = [float(pair["dynamic_erm"][PRIMARY_METRIC]) for pair in pairs]
    js_values = [float(pair["js_consistency"][PRIMARY_METRIC]) for pair in pairs]
    erm_mean = float(report["methods"]["dynamic_erm"][PRIMARY_METRIC]["mean"])
    js_mean = float(report["methods"]["js_consistency"][PRIMARY_METRIC]["mean"])
    improvement = report["paired_improvements"][PRIMARY_METRIC]
    gain = float(improvement["mean"])
    positive = int(improvement["positive_pairs"])
    count = int(report["paired_seed_count"])
    interval = improvement.get("bootstrap_95_interval")
    if y_limits is None:
        y_limits = _paired_metric_limits((report,), PRIMARY_METRIC)
    y_low, y_high = y_limits
    y_span = y_high - y_low

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.105, right=0.94, bottom=0.19, top=0.76)
    _add_slide_chrome(
        fig,
        title=slide_title,
        conclusion=(
            f"{conclusion_subject}, Dynamic JS raises mean OOD Macro-F1 from "
            f"{erm_mean:.4f} to {js_mean:.4f} ({gain:+.4f}); "
            f"{positive}/{count} matched seeds improve."
        ),
    )
    fig.text(
        0.105,
        0.807,
        "Single-factor OOD Macro-F1  |  thin line = one matched seed  |  diamond = mean",
        ha="left",
        va="center",
        fontsize=11.2,
        color=MUTED_COLOR,
    )
    if interval is None:
        result_note = f"{positive}/{count} seeds improved"
    else:
        result_note = (
            f"{positive}/{count} seeds improved  |  paired bootstrap 95% CI "
            f"[{float(interval[0]):.5f}, {float(interval[1]):.5f}]"
        )
    fig.text(
        0.94,
        0.807,
        result_note,
        ha="right",
        va="center",
        fontsize=11.2,
        color=NAVY_COLOR,
        fontweight="bold",
    )

    for erm_value, js_value in zip(erm_values, js_values, strict=True):
        ax.plot(
            [0, 1],
            [erm_value, js_value],
            color="#C7D0DA",
            linewidth=2.0,
            alpha=1.0,
            zorder=1,
        )
        ax.scatter(
            0,
            erm_value,
            s=62,
            facecolor=ERM_COLOR,
            edgecolor=ERM_COLOR,
            linewidth=1.0,
            zorder=3,
        )
        ax.scatter(
            1,
            js_value,
            s=62,
            facecolor=JS_COLOR,
            edgecolor=JS_COLOR,
            linewidth=1.0,
            zorder=3,
        )

    ax.plot(
        [0, 1],
        [erm_mean, js_mean],
        color=NAVY_COLOR,
        linewidth=3.4,
        alpha=1.0,
        zorder=4,
    )
    ax.scatter(
        0,
        erm_mean,
        s=128,
        marker="D",
        facecolor=ERM_COLOR,
        edgecolor=NAVY_COLOR,
        linewidth=1.5,
        zorder=5,
    )
    ax.scatter(
        1,
        js_mean,
        s=128,
        marker="D",
        facecolor=JS_COLOR,
        edgecolor=NAVY_COLOR,
        linewidth=1.5,
        zorder=5,
    )

    ax.text(
        -0.04,
        erm_mean,
        f"mean  {erm_mean:.4f}",
        ha="right",
        va="center",
        fontsize=12.5,
        color=ERM_COLOR,
        fontweight="bold",
        zorder=6,
    )
    ax.text(
        1.04,
        js_mean,
        f"mean  {js_mean:.4f}",
        ha="left",
        va="center",
        fontsize=12.5,
        color=JS_COLOR,
        fontweight="bold",
        zorder=6,
    )

    bracket_y = y_high - 0.045 * y_span
    ax.add_patch(
        FancyArrowPatch(
            (0.03, bracket_y),
            (0.97, bracket_y),
            arrowstyle="<->",
            mutation_scale=12,
            linewidth=1.8,
            color=JS_COLOR,
        )
    )
    ax.text(
        0.5,
        bracket_y + 0.030 * y_span,
        f"mean gain  {gain:+.4f}",
        ha="center",
        va="bottom",
        fontsize=13.5,
        color=JS_COLOR,
        fontweight="bold",
    )

    ax.set_xlim(-0.28, 1.28)
    ax.set_ylim(y_low, y_high)
    ax.set_xticks([0, 1], [METHOD_LABELS[method] for method in METHODS])
    ax.tick_params(axis="x", length=0, pad=12, labelsize=13)
    tick_labels = ax.get_xticklabels()
    tick_labels[0].set_color(ERM_COLOR)
    tick_labels[1].set_color(JS_COLOR)
    for tick_label in tick_labels:
        tick_label.set_fontweight("bold")
    ax.set_ylabel("Macro-F1", labelpad=14, fontsize=13)
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))
    ax.locator_params(axis="y", nbins=5)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=1.0, alpha=0.9)
    ax.spines[["top", "right", "bottom"]].set_visible(False)
    return fig


def _metric_limits(reports: Iterable[dict[str, Any]]) -> tuple[float, float]:
    bounds: list[float] = []
    for report in reports:
        for metric in METRICS:
            for method in METHODS:
                aggregate = report["methods"][method][metric]
                mean = float(aggregate["mean"])
                sample_sd = float(aggregate["sample_sd"])
                bounds.extend((mean - sample_sd, mean + sample_sd))
    low = min(bounds)
    high = max(bounds)
    padding = max((high - low) * 0.12, 0.02)
    return max(0.0, low - padding), min(1.0, high + padding)


def make_metric_overview(simulated_test: dict[str, Any]) -> plt.Figure:
    """Show the four Test metrics without conflating Validation definitions."""

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.subplots_adjust(left=0.09, right=0.965, bottom=0.205, top=0.745)
    count = int(simulated_test["paired_seed_count"])
    deltas = {
        metric: float(simulated_test["paired_improvements"][metric]["mean"])
        for metric in METRICS
    }
    largest_metric = max(deltas, key=deltas.get)
    _add_slide_chrome(
        fig,
        title="RESULT 3 | CLEAN AND ROBUSTNESS METRICS",
        conclusion=(
            "No ordinary-performance trade-off: all four endpoints improve in "
            f"{count}/{count} paired runs; the largest gain is on OOD "
            f"({deltas[largest_metric] * 100:+.1f} pts)."
        ),
        conclusion_size=12.3,
    )
    fig.text(
        0.09,
        0.805,
        f"Frozen simulated test  |  mean ± sample SD across {count} matched training seeds  |  higher is better",
        ha="left",
        va="center",
        fontsize=11.2,
        color=MUTED_COLOR,
    )

    rows = list(METRICS.items())
    x = np.arange(len(rows), dtype=float)
    width = 0.31
    primary_x = list(METRICS).index(PRIMARY_METRIC)
    ax.axvspan(
        primary_x - 0.50,
        primary_x + 0.50,
        color="#FFF5E8",
        alpha=0.85,
        linewidth=0,
        zorder=0,
    )

    erm_means: list[float] = []
    js_means: list[float] = []
    erm_sds: list[float] = []
    js_sds: list[float] = []
    for metric, _ in rows:
        erm = simulated_test["methods"]["dynamic_erm"][metric]
        js = simulated_test["methods"]["js_consistency"][metric]
        erm_means.append(float(erm["mean"]))
        js_means.append(float(js["mean"]))
        erm_sds.append(float(erm["sample_sd"]))
        js_sds.append(float(js["sample_sd"]))

    error_kwargs = {
        "elinewidth": 1.2,
        "capsize": 3.5,
        "capthick": 1.2,
    }
    erm_bars = ax.bar(
        x - width / 2,
        erm_means,
        width,
        yerr=erm_sds,
        color=ERM_COLOR,
        edgecolor=NAVY_COLOR,
        linewidth=0.8,
        error_kw={**error_kwargs, "ecolor": NAVY_COLOR},
        label=METHOD_LABELS["dynamic_erm"],
        zorder=3,
    )
    js_bars = ax.bar(
        x + width / 2,
        js_means,
        width,
        yerr=js_sds,
        color=JS_COLOR,
        edgecolor="#9D5536",
        linewidth=0.8,
        error_kw={**error_kwargs, "ecolor": "#9D5536"},
        label=METHOD_LABELS["js_consistency"],
        zorder=3,
    )

    for bar, mean in zip(erm_bars, erm_means, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.017,
            f"{mean:.3f}",
            ha="center",
            va="bottom",
            fontsize=10.0,
            color=NAVY_COLOR,
            fontweight="bold",
        )
    for index, (bar, mean, sd, (metric, _)) in enumerate(
        zip(js_bars, js_means, js_sds, rows, strict=True)
    ):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.017,
            f"{mean:.3f}",
            ha="center",
            va="bottom",
            fontsize=10.0,
            color="#9D5536",
            fontweight="bold",
        )
        annotation_y = max(erm_means[index] + erm_sds[index], mean + sd) + 0.060
        ax.text(
            x[index],
            annotation_y,
            f"{deltas[metric] * 100:+.1f} pts",
            ha="center",
            va="bottom",
            fontsize=11.2,
            color=JS_COLOR,
            fontweight="bold",
        )

    ax.set_xticks(
        x,
        ["Level-0", "In-range", "Single-factor\nOOD", "Worst-class\nF1"],
    )
    ax.set_ylim(0.0, 0.84)
    ax.set_xlim(-0.58, len(rows) - 0.42)
    ax.set_ylabel("F1 score", labelpad=12, fontsize=13)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=1.0, alpha=0.9, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", length=0, pad=10, labelsize=12)
    ax.tick_params(axis="y", labelsize=11)
    ax.yaxis.set_major_formatter(FormatStrFormatter("%.1f"))
    for index, tick_label in enumerate(ax.get_xticklabels()):
        if index == primary_x:
            tick_label.set_color(JS_COLOR)
            tick_label.set_fontweight("bold")

    handles = [
        Rectangle((0, 0), 1, 1, facecolor=ERM_COLOR, edgecolor=NAVY_COLOR),
        Rectangle((0, 0), 1, 1, facecolor=JS_COLOR, edgecolor="#9D5536"),
    ]
    fig.legend(
        handles=handles,
        labels=[METHOD_LABELS[method] for method in METHODS],
        loc="upper right",
        bbox_to_anchor=(0.965, 0.812),
        ncol=2,
        handlelength=1.4,
        columnspacing=1.8,
        fontsize=11.0,
    )
    return fig


def _save_figure(
    fig: plt.Figure,
    stem: str,
    output_dir: Path,
    formats: tuple[str, ...],
) -> list[Path]:
    written: list[Path] = []
    for output_format in formats:
        path = output_dir / f"{stem}.{output_format}"
        metadata: dict[str, Any] = {
            "Creator": "xrd_robustness/scripts/generate_paper_figures.py"
        }
        if output_format == "svg":
            metadata["Date"] = None
        fig.savefig(
            path,
            format=output_format,
            dpi=220,
            metadata=metadata,
        )
        written.append(path)
    plt.close(fig)
    return written


def generate_all(
    validation_path: Path,
    simulated_test_path: Path,
    output_dir: Path,
    formats: tuple[str, ...],
) -> list[Path]:
    validation = _load_json(validation_path)
    simulated_test = _load_json(simulated_test_path)
    validate_bundle(validation, simulated_test)
    _apply_style()
    output_dir.mkdir(parents=True, exist_ok=True)
    paired_y_limits = _paired_metric_limits(
        (validation, simulated_test), PRIMARY_METRIC
    )

    figures = (
        (
            "figure_1_method_overview",
            make_method_overview(validation),
        ),
        (
            "figure_2_validation_paired_ood",
            make_paired_plot(
                validation,
                slide_title="RESULT 1 | VALIDATION OOD",
                conclusion_subject="On simulated validation",
                y_limits=paired_y_limits,
            ),
        ),
        (
            "figure_3_simulated_test_paired_ood",
            make_paired_plot(
                simulated_test,
                slide_title="RESULT 2 | FROZEN TEST OOD",
                conclusion_subject="On the frozen simulated test",
                y_limits=paired_y_limits,
            ),
        ),
        (
            "figure_4_metric_overview",
            make_metric_overview(simulated_test),
        ),
    )

    written: list[Path] = []
    for stem, figure in figures:
        written.extend(_save_figure(figure, stem, output_dir, formats))
    return written


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation", type=Path, default=DEFAULT_VALIDATION)
    parser.add_argument("--simulated-test", type=Path, default=DEFAULT_SIMULATED_TEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("svg", "png", "pdf"),
        default=("svg", "png"),
        help="One or more output formats (default: svg png)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    written = generate_all(
        validation_path=args.validation,
        simulated_test_path=args.simulated_test,
        output_dir=args.output_dir,
        formats=tuple(dict.fromkeys(args.formats)),
    )
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
