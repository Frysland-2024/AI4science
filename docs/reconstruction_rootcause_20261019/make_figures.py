from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COLORS = {"A": "#6b7280", "B": "#2563eb", "D": "#d97706"}


def rootcause_figure() -> None:
    audit = json.loads((ROOT / "overnight_pr26_20261019/validation_cause_audit.json").read_text(encoding="utf-8"))
    gradients = audit["reconstruction_vs_parameter_gradient_diagnostics"]
    groups = []
    labels = []
    for condition in ("simple", "v9"):
        records = [row for row in gradients if row["condition"] == condition]
        for key, label in (("grad_q_cosine", "q head"), ("shared_trunk_param_grad_cosine", "shared trunk")):
            vals = [batch[key] for row in records for batch in row["batches"]]
            groups.append(vals)
            labels.append(f"{condition.upper()} {label}\n(n={len(vals)})")

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    ax = axes[0]
    ax.boxplot(groups, tick_labels=labels, showfliers=False, patch_artist=True,
               boxprops={"facecolor": "#dbeafe", "edgecolor": "#334155"},
               medianprops={"color": "#b91c1c", "linewidth": 1.5})
    rng = np.random.default_rng(19)
    for index, values in enumerate(groups, start=1):
        jitter = rng.uniform(-0.08, 0.08, size=len(values))
        ax.scatter(index + jitter, values, s=17, alpha=0.65, color="#334155", linewidths=0)
    ax.axhline(0, color="#b91c1c", linewidth=1, linestyle="--")
    ax.set_ylabel("Gradient cosine: q / shared trunk")
    ax.set_title("Issue 31 validation gradient conflict")
    ax.set_ylim(-0.65, 1.0)
    ax.grid(axis="y", alpha=0.2)

    preds = [row for row in audit["validation_prediction_diagnostics"] if row["method"] == "B"]
    seeds = [20261045, 20261046, 20261047]
    x = np.arange(len(seeds))
    width = 0.34
    for offset, condition, color, label in ((-width / 2, "simple", "#64748b", "simple"),
                                            (width / 2, "v9", "#d97706", "V9")):
        vals = []
        for seed in seeds:
            row = next(item for item in preds if item["condition"] == condition and item["seed"] == seed)
            vals.append(row["q_error_vs_eta_error_pearson_matrix_diagnostic_only"][0][0])
        axes[1].bar(x + offset, vals, width=width, color=color, label=label)
        axes[1].scatter(x + offset, vals, color="#111827", s=18, zorder=3)
    axes[1].axhline(0, color="#334155", linewidth=1)
    axes[1].set_xticks(x, [str(seed) for seed in seeds])
    axes[1].set_ylim(-0.4, 1.05)
    axes[1].set_ylabel("Pearson r: du error vs zero-shift error")
    axes[1].set_title("Validation-only association by seed")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.2)
    fig.suptitle("Historical validation diagnostics; old test excluded from these analyses", fontsize=13)
    fig.savefig(HERE / "rootcause_validation_diagnostics.png", dpi=180)
    plt.close(fig)


def fresh_test_figure() -> None:
    result = json.loads((HERE / "fresh_results_per_seed.json").read_text(encoding="utf-8"))
    metrics = [
        ("q_mae", "Direct normalized q-MAE", "normalized coordinate"),
        ("a_mae_angstrom", "Lattice a MAE", "Å"),
        ("c_mae_angstrom", "Lattice c MAE", "Å"),
        ("zero_shift_rmse_deg", "Zero-shift RMSE", "degree"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    seeds = ["20261201", "20261202", "20261203"]
    offsets = np.linspace(-0.12, 0.12, len(seeds))
    for ax, (metric, title, unit) in zip(axes.flat, metrics, strict=True):
        for x, method in enumerate(("A", "B", "D")):
            for condition, shift, marker in (("simple", -0.18, "o"), ("v9", 0.18, "s")):
                values = [result["seed_summary"][condition][method][seed][metric] for seed in seeds]
                mean = float(np.mean(values))
                sd = float(np.std(values, ddof=1))
                xpos = x + shift
                ax.errorbar(xpos, mean, yerr=sd, fmt=marker, color=COLORS[method], capsize=4,
                            markersize=6, elinewidth=1.5, label=f"{method} {condition}" if ax is axes.flat[0] else None)
                ax.scatter(xpos + offsets, values, color=COLORS[method], s=24, alpha=0.65, marker=marker, zorder=3)
        ax.set_xticks([0, 1, 2], ["A", "B", "D"])
        ax.set_ylabel(f"{title} ({unit})")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.2)
    axes.flat[0].legend(ncol=3, fontsize=8, frameon=False)
    fig.suptitle("Fresh 77-parent test, opened once after validation selection\nMeans ± sample SD across three paired seeds; markers show individual seeds", fontsize=12)
    fig.savefig(HERE / "fresh_test_metrics.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    rootcause_figure()
    fresh_test_figure()
