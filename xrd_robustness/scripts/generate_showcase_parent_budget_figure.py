#!/usr/bin/env python3
"""Generate the supervisor-showcase parent-budget learning curve from archived JSON."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE = Path(__file__).resolve().parents[1]
RESULTS = PACKAGE / "reports" / "parent_budget_efficiency" / "results.json"
OUTPUT = PACKAGE / "figures" / "figure_5_parent_budget_efficiency.png"
BUDGET_ORDER = [("10", 984), ("25", 2460), ("50", 4921), ("100", 9842)]
SERIES = [
    ("dynamic_erm", "Dynamic ERM", "#285F8F", "o"),
    ("dynamic_js", "Dynamic JS (weight 60)", "#D77828", "D"),
]


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    by_budget = data["summary"]["by_budget"]
    x = np.arange(len(BUDGET_ORDER))

    fig, ax = plt.subplots(figsize=(11.2, 6.8), dpi=200)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    for key, label, color, marker in SERIES:
        means = [
            by_budget[percent]["methods"][key]["mean"]["single_factor_ood_macro_f1"]
            for percent, _ in BUDGET_ORDER
        ]
        sds = [
            by_budget[percent]["methods"][key]["sample_sd"]["single_factor_ood_macro_f1"]
            for percent, _ in BUDGET_ORDER
        ]
        ax.errorbar(
            x,
            means,
            yerr=sds,
            label=label,
            color=color,
            marker=marker,
            markersize=8,
            linewidth=2.6,
            elinewidth=1.4,
            capsize=4,
            capthick=1.4,
            markeredgecolor="white",
            markeredgewidth=0.9,
            zorder=3,
        )

    ax.set_xticks(x, [f"{percent}%\n({parents:,} parents)" for percent, parents in BUDGET_ORDER])
    ax.set_xlabel("Independent training-parent budget", labelpad=12, fontsize=11)
    ax.set_ylabel("Single-factor simulated OOD Macro-F1", labelpad=10, fontsize=11)
    ax.set_ylim(0.405, 0.725)
    ax.set_yticks(np.arange(0.40, 0.721, 0.05))
    ax.grid(axis="y", color="#DCE3E8", linewidth=0.8)
    ax.grid(axis="x", visible=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#7F8C96")
    ax.spines["bottom"].set_color("#7F8C96")
    ax.tick_params(axis="both", colors="#28343C", labelsize=10)
    ax.legend(frameon=False, loc="upper left", fontsize=10.5, ncols=2)

    fig.suptitle(
        "Dynamic JS is higher at every matched parent budget",
        x=0.08,
        y=0.975,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color="#1F2D36",
    )
    fig.text(
        0.08,
        0.925,
        "Mean of six OOD profiles and three evaluation seeds per training seed; equal 49,280 optimizer steps per model",
        ha="left",
        fontsize=10.5,
        color="#4D5B64",
    )
    fig.text(
        0.08,
        0.025,
        "Five paired training seeds per budget; error bars show sample SD. Post-main supplement on the previously evaluated simulated Test.",
        ha="left",
        fontsize=8.8,
        color="#4D5B64",
    )
    fig.subplots_adjust(left=0.10, right=0.98, top=0.86, bottom=0.17)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=200, facecolor="white")
    plt.close(fig)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
