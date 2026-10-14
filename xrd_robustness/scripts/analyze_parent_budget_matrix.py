#!/usr/bin/env python
"""Evaluate selected checkpoints on the frozen post-main Test and summarize the matrix."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_parent_budget_pair import (  # noqa: E402
    PROFILES,
    _configure_training_runtime,
    _ensure_eval_cache,
    _evaluate_model,
)
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.parent_budget_efficiency import BUDGETS, load_split_rows, sha256_file  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402


SEEDS = (20260711, 20260712, 20260713, 20260714, 20260715)
EVALUATION_SEEDS = (20260721, 20260722, 20260723)
BUDGET_ORDER = ("10", "25", "50", "100")
OOD_PROFILES = PROFILES[:6]
REPORT_DIR = PROJECT_ROOT / "reports" / "parent_budget_efficiency"


def _pair_dir(output_root: Path, seed: int, budget: str) -> Path:
    return output_root / f"seed_{seed}" / f"parents_{BUDGETS[budget]}"


def _load_checkpoint(model: torch.nn.Module, path: Path, device: torch.device) -> int:
    payload = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(payload["model"])
    model.eval()
    return int(payload["global_step"])


def _method_summary(metrics: Mapping[str, Any]) -> dict[str, Any]:
    eval_rows = [metrics[str(seed)] for seed in EVALUATION_SEEDS]
    ood_values = [
        eval_rows[seed_index][profile]["macro_f1"]
        for seed_index in range(len(EVALUATION_SEEDS))
        for profile in OOD_PROFILES
    ]
    ood_accuracy = [
        eval_rows[seed_index][profile]["accuracy"]
        for seed_index in range(len(EVALUATION_SEEDS))
        for profile in OOD_PROFILES
    ]
    per_class = {
        crystal: float(
            np.mean(
                [
                    eval_rows[seed_index][profile]["per_class_f1_by_name"][crystal]
                    for seed_index in range(len(EVALUATION_SEEDS))
                    for profile in OOD_PROFILES
                ]
            )
        )
        for crystal in CRYSTAL_SYSTEMS
    }
    profile_macro = {
        profile: float(np.mean([row[profile]["macro_f1"] for row in eval_rows]))
        for profile in OOD_PROFILES
    }
    profile_accuracy = {
        profile: float(np.mean([row[profile]["accuracy"] for row in eval_rows]))
        for profile in OOD_PROFILES
    }
    return {
        "single_factor_ood_macro_f1": float(np.mean(ood_values)),
        "single_factor_ood_accuracy": float(np.mean(ood_accuracy)),
        "in_range_macro_f1": float(np.mean([row["in_range"]["macro_f1"] for row in eval_rows])),
        "in_range_accuracy": float(np.mean([row["in_range"]["accuracy"] for row in eval_rows])),
        "level0_macro_f1": float(np.mean([row["level0"]["macro_f1"] for row in eval_rows])),
        "level0_accuracy": float(np.mean([row["level0"]["accuracy"] for row in eval_rows])),
        "ood_macro_f1_by_profile": profile_macro,
        "ood_accuracy_by_profile": profile_accuracy,
        "per_class_f1": per_class,
    }


def _bootstrap_ci(values: Sequence[float], *, seed: int) -> list[float] | None:
    array = np.asarray(values, dtype=np.float64)
    if len(array) < 2:
        return None
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(20_000, len(array)), replace=True).mean(axis=1)
    return [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))]


def _summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "single_factor_ood_macro_f1",
        "single_factor_ood_accuracy",
        "in_range_macro_f1",
        "in_range_accuracy",
        "level0_macro_f1",
        "level0_accuracy",
    )
    by_budget: dict[str, Any] = {}
    paired: list[dict[str, Any]] = []
    for budget in BUDGET_ORDER:
        budget_rows = [row for row in rows if row["budget_percent"] == int(budget)]
        methods: dict[str, Any] = {}
        for method in ("dynamic_erm", "dynamic_js"):
            method_rows = [row for row in budget_rows if row["method"] == method]
            per_class_values = {
                crystal: [row["per_class_f1"][crystal] for row in method_rows]
                for crystal in CRYSTAL_SYSTEMS
            }
            methods[method] = {
                "n_training_seeds": len(method_rows),
                "mean": {
                    metric: float(np.mean([row[metric] for row in method_rows]))
                    if method_rows
                    else None
                    for metric in metrics
                },
                "sample_sd": {
                    metric: float(np.std([row[metric] for row in method_rows], ddof=1))
                    if len(method_rows) > 1
                    else None
                    for metric in metrics
                },
                "per_seed": {
                    str(row["training_seed"]): {metric: row[metric] for metric in metrics}
                    for row in method_rows
                },
                "ood_macro_f1_by_profile": {
                    profile: float(
                        np.mean(
                            [row["ood_macro_f1_by_profile"][profile] for row in method_rows]
                        )
                    )
                    if method_rows
                    else None
                    for profile in OOD_PROFILES
                },
                "per_class_f1": {
                    crystal: float(np.mean(per_class_values[crystal]))
                    if method_rows
                    else None
                    for crystal in CRYSTAL_SYSTEMS
                },
                "per_class_f1_sample_sd": {
                    crystal: float(np.std(per_class_values[crystal], ddof=1))
                    if len(per_class_values[crystal]) > 1
                    else None
                    for crystal in CRYSTAL_SYSTEMS
                },
            }
        common_seeds = sorted(
            set(methods["dynamic_erm"]["per_seed"]).intersection(
                methods["dynamic_js"]["per_seed"]
            )
        )
        delta_rows = []
        for seed in common_seeds:
            erm = methods["dynamic_erm"]["per_seed"][seed]
            js = methods["dynamic_js"]["per_seed"][seed]
            delta_rows.append(
                {
                    "training_seed": int(seed),
                    **{metric: float(js[metric] - erm[metric]) for metric in metrics},
                }
            )
            paired.append({"budget_percent": int(budget), **delta_rows[-1]})
        primary_deltas = [row["single_factor_ood_macro_f1"] for row in delta_rows]
        by_budget[budget] = {
            "parent_count": BUDGETS[budget],
            "methods": methods,
            "paired_deltas": delta_rows,
            "paired_primary_delta": {
                "n_training_seeds": len(primary_deltas),
                "mean": float(np.mean(primary_deltas)) if primary_deltas else None,
                "sample_sd": float(np.std(primary_deltas, ddof=1)) if len(primary_deltas) > 1 else None,
                "bootstrap_95_percent_interval": _bootstrap_ci(
                    primary_deltas, seed=20261013 + int(budget)
                ),
                "positive_pairs": sum(value > 0 for value in primary_deltas),
            },
        }
    return {"by_budget": by_budget, "paired_deltas": paired}


def _equivalent_parent_estimates(summary: Mapping[str, Any], complete_matrix: bool) -> dict[str, Any]:
    if not complete_matrix:
        return {
            "status": "not_estimable_incomplete_training_seed_matrix",
            "estimates": [],
            "rule": "No extrapolation; interpolation requires a complete frozen matrix and a target bracketed by measured points.",
        }
    budgets = [int(key) for key in BUDGET_ORDER]
    estimates: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []
    for target_index, erm_budget in enumerate(BUDGET_ORDER):
        erm = summary["by_budget"][erm_budget]["methods"]["dynamic_erm"]
        target = erm["mean"]["single_factor_ood_macro_f1"]
        erm_by_seed = erm["per_seed"]
        for candidate_index in range(target_index):
            candidate_budget = BUDGET_ORDER[candidate_index]
            candidate = summary["by_budget"][candidate_budget]["methods"]["dynamic_js"]
            common_seeds = sorted(set(candidate["per_seed"]).intersection(erm_by_seed))
            differences = [
                candidate["per_seed"][seed]["single_factor_ood_macro_f1"]
                - erm_by_seed[seed]["single_factor_ood_macro_f1"]
                for seed in common_seeds
            ]
            interval = _bootstrap_ci(
                differences,
                seed=20261013 + budgets[target_index] + budgets[candidate_index],
            )
            if candidate["mean"]["single_factor_ood_macro_f1"] >= target:
                crossing = {
                    "target_erm_macro_f1": float(target),
                    "erm_parent_count": budgets[target_index],
                    "js_parent_count": budgets[candidate_index],
                    "paired_delta_mean": float(np.mean(differences)) if differences else None,
                    "paired_delta_bootstrap_95_percent_interval": interval,
                    "n_paired_training_seeds": len(differences),
                }
                exploratory.append(crossing)
                if interval is not None and interval[0] > 0:
                    estimates.append(crossing)
                    break
    return {
        "status": "supported_discrete_parent_saving" if estimates else "no_supported_parent_saving",
        "estimates": estimates,
        "exploratory_mean_curve_crossings": exploratory,
        "rule": "A parent-saving target is supported only when a lower-budget JS measured mean reaches the larger-budget ERM mean and the paired 95% bootstrap interval for JS minus ERM is entirely above zero. No extrapolation or interpolated counts are used as evidence.",
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _plots(summary: Mapping[str, Any], out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    xs = [BUDGETS[key] for key in BUDGET_ORDER]
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    colors = {"dynamic_erm": "#3b6fb6", "dynamic_js": "#d47a2c"}
    labels = {"dynamic_erm": "Dynamic ERM", "dynamic_js": "Dynamic JS (λ=60)"}
    for method in ("dynamic_erm", "dynamic_js"):
        means, spreads = [], []
        for key in BUDGET_ORDER:
            item = summary["by_budget"][key]["methods"][method]
            means.append(item["mean"]["single_factor_ood_macro_f1"] if item["n_training_seeds"] else np.nan)
            spreads.append(item["sample_sd"]["single_factor_ood_macro_f1"] or 0.0 if item["n_training_seeds"] > 1 else 0.0)
        ax.errorbar(xs, means, yerr=spreads, marker="o", linewidth=2, capsize=4, color=colors[method], label=labels[method])
    ax.set_xscale("log")
    ax.set_xticks(xs, [f"{key}%\n({BUDGETS[key]:,})" for key in BUDGET_ORDER])
    ax.set_xlabel("Unique training parent structures")
    ax.set_ylabel("Single-factor OOD Macro-F1")
    ax.set_title("Parent-structure learning curve")
    ax.grid(True, alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "learning_curve.png", dpi=200)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    means, spreads = [], []
    for key in BUDGET_ORDER:
        item = summary["by_budget"][key]["paired_primary_delta"]
        means.append(item["mean"] if item["mean"] is not None else np.nan)
        spreads.append(item["sample_sd"] or 0.0 if item["sample_sd"] is not None else 0.0)
    ax.errorbar(xs, means, yerr=spreads, marker="o", linewidth=2, capsize=4, color="#6f4a8e")
    ax.axhline(0, color="#444444", linewidth=1, linestyle="--")
    ax.set_xscale("log")
    ax.set_xticks(xs, [f"{key}%\n({BUDGETS[key]:,})" for key in BUDGET_ORDER])
    ax.set_xlabel("Unique training parent structures")
    ax.set_ylabel("Paired Δ Macro-F1 (JS − ERM)")
    ax.set_title("Matched-seed improvement by budget")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_dir / "paired_deltas.png", dpi=200)
    plt.close(fig)


def _write_report(
    path: Path,
    *,
    summary: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    completed_pairs: Sequence[str],
    complete_matrix: bool,
    data_savings: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> None:
    total_runs = len(results)
    lines = [
        "# Parent-Structure Sample Efficiency Supplementary Experiment",
        "",
        f"**Status:** {'COMPLETED' if complete_matrix else 'PARTIAL'}; post-main supplementary analysis.",
        "",
        "## Gate summary",
        "",
        "| Gate | Status | Evidence |",
        "|---|---|---|",
        "| A — data, historical provenance, frozen protocol | PASS | Official split and peak-cache hashes verified; local GPU available; historical terminal steps unavailable and a new shared budget was frozen before scores. |",
        "| B — implementation and fairness smoke | PASS | Deterministic stratified nested subsets, fixed-step paired runner, direct-versus-prefetch bitwise rendering check, tests, and matched-view smoke completed. |",
        f"| C — fixed matrix and uniform Test evaluation | {'PASS' if complete_matrix else 'PARTIAL'} | {len(completed_pairs)}/20 seed-by-budget pairs completed ({total_runs}/40 method runs); incomplete cells are listed below. |",
        f"| D — paired statistics and plots | {'PASS' if results else 'PARTIAL'} | Per-seed, profile-level, per-class, and matched-seed metrics are summarized; parent-saving claims require paired uncertainty support. |",
        "| E — archive | PASS | Independent Markdown, JSON/CSV, figures, frozen configs, and exact subset manifests are prepared for Git. |",
        "",
        "## Frozen protocol",
        "",
        "Four nested Train subsets contain 984, 2,460, 4,921, and 9,842 unique parent structures. Per-class counts use Hamilton largest-remainder rounding with the repository crystal-system order as the tie order. The selection seed is 20261013. Dynamic ERM and Dynamic JS (λ=60) share their initial weights and receive the same ordered batch and the same two rendered views at every optimizer step.",
        "",
        "Each method receives 49,280 optimizer steps, batch size 16, 788,480 parent occurrences, and 1,576,960 generated views. The optimizer is AdamW (learning rate 1e-4, weight decay 1e-4) with no scheduler. Validation runs every 6,160 steps; the selected checkpoint maximizes mean Macro-F1 across six single-factor OOD Validation profiles at evaluation seed 20260721, with in-range Macro-F1 as the tie-break and the earlier step as the final tie-break.",
        "",
        "This is a new fixed-budget supplementary protocol. Available historical checkpoints record selected best-checkpoint steps, not each original run's terminal step. The 49,280-step budget is the median selected-checkpoint step across the 10 historical checkpoints and does not claim to reproduce their stopping behavior.",
        "",
        "## Data identity and split audit",
        "",
        f"Verified source records: {provenance.get('source_records_count', '14,060')}; verified peak tables: {provenance.get('peak_tables_verified', '14,060')}. Train/Validation/Test counts are 9,842/2,109/2,109. The official split is the hash-bound `split_manifest.json` referenced by the frozen data config. The original structure records' embedded `split` field disagrees with that manifest for **6,601/14,060** records; it is stale and was not used for assignment. Material IDs, crystal systems, parent fingerprints, uniqueness, and all peak-table hashes were checked. Full split-field cross-tab: `test→test 318, test→train 1,469, test→validation 343; train→test 1,469, train→train 6,853, train→validation 1,478; validation→test 322, validation→train 1,520, validation→validation 288`.",
        "",
        "The Test split and all original frozen configs, checkpoints, reports, and source split files remain unchanged. The frozen simulated Test was already used by the main study; these results are a post-main follow-up, not an untouched confirmatory test.",
        "",
        "## Training matrix status",
        "",
        "| Parents | Seed | ERM | JS λ=60 |",
        "|---:|---:|---|---|",
    ]
    done = set(completed_pairs)
    for seed in SEEDS:
        for budget in BUDGET_ORDER:
            key = f"seed_{seed}:parents_{BUDGETS[budget]}"
            status = "completed" if key in done else "not completed"
            lines.append(f"| {BUDGETS[budget]:,} | {seed} | {status} | {status} |")
    lines.extend(["", f"Actual method runs: **{total_runs}/40**.", ""])

    lines.extend(
        [
            "## Results",
            "",
            "Primary outcome is the mean Macro-F1 across six single-factor simulated OOD profiles, averaged over the three frozen evaluation seeds. In-range, level0, accuracy, profile-level, and per-class metrics are reported as secondary outcomes.",
            "",
            "| Parents | Training seeds | ERM OOD Macro-F1 | JS OOD Macro-F1 | Paired Δ (JS − ERM) | 95% paired CI | Positive pairs |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for key in BUDGET_ORDER:
        row = summary["by_budget"][key]
        erm = row["methods"]["dynamic_erm"]
        js = row["methods"]["dynamic_js"]
        delta = row["paired_primary_delta"]
        def fmt(value: Any) -> str:
            return "—" if value is None else f"{float(value):.4f}"
        def mean_sd(method_row: Mapping[str, Any]) -> str:
            if not method_row["n_training_seeds"]:
                return "—"
            value = method_row["mean"]["single_factor_ood_macro_f1"]
            spread = method_row["sample_sd"]["single_factor_ood_macro_f1"]
            return fmt(value) + (f" ± {float(spread):.4f}" if spread is not None else "")
        interval = delta["bootstrap_95_percent_interval"]
        interval_text = "—" if interval is None else f"[{interval[0]:.4f}, {interval[1]:.4f}]"
        lines.append(
            f"| {row['parent_count']:,} | {delta['n_training_seeds']} | "
            f"{mean_sd(erm)} | {mean_sd(js)} | "
            f"{fmt(delta['mean'])} ± {fmt(delta['sample_sd'])} | {interval_text} | "
            f"{delta['positive_pairs']}/{delta['n_training_seeds']} |"
        )
    lines.extend(["", f"Data-saving assessment: **{data_savings['status']}**."])
    if data_savings.get("estimates"):
        for estimate in data_savings["estimates"]:
            lines.append(
                f"At ERM target {estimate['target_erm_macro_f1']:.4f} observed with "
                f"{estimate['erm_parent_count']:,} parents, JS reached or exceeded the target with "
                f"{estimate['js_parent_count']:,} parents; paired difference was "
                f"{estimate['paired_delta_mean']:.4f}, 95% interval "
                f"[{estimate['paired_delta_bootstrap_95_percent_interval'][0]:.4f}, "
                f"{estimate['paired_delta_bootstrap_95_percent_interval'][1]:.4f}]."
            )
    else:
        lines.append(
            "No parent reduction is supported. Same-budget gains, if any, remain distinct from measured structure savings. Mean-curve crossings without a positive paired 95% interval are exploratory only; no target was extrapolated."
        )
    if data_savings.get("exploratory_mean_curve_crossings"):
        lines.extend(["", "Exploratory mean-curve crossings (not evidence of a saving):"])
        for estimate in data_savings["exploratory_mean_curve_crossings"]:
            interval = estimate["paired_delta_bootstrap_95_percent_interval"]
            interval_text = "unavailable" if interval is None else f"[{interval[0]:.4f}, {interval[1]:.4f}]"
            lines.append(
                f"- ERM {estimate['erm_parent_count']:,} parents: JS mean at "
                f"{estimate['js_parent_count']:,} parents reaches the target; paired Δ "
                f"{estimate['paired_delta_mean']:.4f}, 95% interval {interval_text}."
            )
    lines.extend(
        [
            "",
            "## Per-seed primary and in-range results",
            "",
            "| Parents | Seed | Method | OOD Macro-F1 | In-range Macro-F1 |",
            "|---:|---:|---|---:|---:|",
        ]
    )
    for item in sorted(
        results,
        key=lambda value: (value["budget_percent"], value["training_seed"], value["method"]),
    ):
        lines.append(
            f"| {item['parent_count']:,} | {item['training_seed']} | {item['method']} | "
            f"{item['single_factor_ood_macro_f1']:.4f} | {item['in_range_macro_f1']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Per-class OOD Macro-F1",
            "",
            "Values are mean ± sample SD across available training seeds. Each seed value averages the six OOD profiles and three evaluation seeds.",
            "",
            "| Parents | Crystal system | ERM | JS λ=60 |",
            "|---:|---|---:|---:|",
        ]
    )
    for budget in BUDGET_ORDER:
        row = summary["by_budget"][budget]
        for crystal in CRYSTAL_SYSTEMS:
            values = []
            for method in ("dynamic_erm", "dynamic_js"):
                method_row = row["methods"][method]
                mean = method_row["per_class_f1"][crystal]
                sd = method_row["per_class_f1_sample_sd"][crystal]
                values.append(
                    "—" if mean is None else f"{mean:.4f}" + (f" ± {sd:.4f}" if sd is not None else "")
                )
            lines.append(f"| {row['parent_count']:,} | {crystal} | {values[0]} | {values[1]} |")

    benchmark = provenance.get("benchmark") or {}
    if benchmark:
        runtime = provenance.get("performance_runtime") or {}
        workers = runtime.get("prefetch_workers", "unknown")
        prefetch = runtime.get("prefetch_batches", "unknown")
        lines.extend(
            [
                "",
                "## GPU and measured runtime",
                "",
                f"GPU: **{benchmark.get('gpu', {}).get('torch_name', 'unavailable')}**; device record: {benchmark.get('gpu', {}).get('nvidia_smi', 'unavailable')}.",
                "",
                "| Workers / queued batches | Paired steps/s | Views/s | Validation pair seconds | 8 method runs | 24 method runs | 40 method runs |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for setting in benchmark.get("settings", []):
            estimates = setting["time_estimates"]
            lines.append(
                f"| {setting['workers']}/{setting['prefetch_batches']} | "
                f"{setting['paired_optimizer_steps_per_second']:.3f} | "
                f"{setting['generated_views_per_second']:.1f} | "
                f"{setting['validation_pair_seconds_per_checkpoint']:.2f} | "
                f"{estimates['8']['training_plus_validation_hours']:.2f} h | "
                f"{estimates['24']['training_plus_validation_hours']:.2f} h | "
                f"{estimates['40']['training_plus_validation_hours']:.2f} h |"
            )
        lines.extend(
            [
                "",
                f"Each paired cell updates ERM and JS together; estimates therefore count 4/12/20 paired cells for 8/24/40 individual method runs. One-time Validation panel-cache construction took {benchmark.get('validation_panel_cache_seconds', float('nan')):.1f} s. Estimates include eight FP32 Validation passes per paired cell and exclude one-time panel construction, checkpoint I/O, Test panel construction/evaluation, and machine contention. The ~8 h historical figure is user recollection, not verified wall-time; compare it with these measurements rather than treating it as a benchmark.",
                "",
                f"The selected training setup used {workers}/{prefetch} workers/queued batches, as recorded before the formal runs. It reuses the V9 online physical-rendering prefetcher, worker-local peak cache, structure-invariant reflection/preferred-orientation work, pinned memory, non-blocking H2D, two CPU intra-op threads, BF16 autocast, fused AdamW, and TF32. Validation and Test inference use FP32.",
            ]
        )

    runtime_audit = provenance.get("runtime_audit") or {}
    source_comparison = provenance.get("source_benchmark_comparison") or {}
    if runtime_audit:
        lines.extend(
            [
                "",
                "## Executed runtime",
                "",
                f"The matrix ran from {runtime_audit.get('matrix_started_at', 'unavailable')} to {runtime_audit.get('matrix_completed_at', 'unavailable')} ({runtime_audit.get('end_to_end_wall_hours', float('nan')):.2f} h end-to-end wall time). The 20 completed paired cells sum to {runtime_audit.get('completed_pair_wall_seconds', 0) / 3600:.2f} h; one interrupted 10% cell attempt added {runtime_audit.get('interrupted_partial_pair_wall_seconds', 0) / 3600:.2f} h before that cell was restarted from step 0.",
                "",
                f"Sampled whole-device telemetry integrates to {runtime_audit.get('device_wide_gpu_busy_equivalent_seconds', 0) / 3600:.2f} GPU-busy-equivalent hours over {runtime_audit.get('gpu_telemetry_sample_count', 0):,} samples. This is device-wide utilization and may include other processes; it is not attributable solely to this experiment.",
            ]
        )
    if source_comparison:
        source = source_comparison.get("source_machine", {})
        target = source_comparison.get("cuifa_machine", {})
        observed = source_comparison.get("observed_comparison", {})
        lines.extend(
            [
                "",
                "## Source-machine benchmark comparison",
                "",
                f"The source Windows laptop (RTX 4060 Laptop GPU, {source.get('workers')}/{source.get('prefetch_batches')}) measured {source.get('paired_optimizer_steps_per_second', float('nan')):.3f} paired optimizer steps/s and projected {source.get('40_method_training_plus_validation_hours', float('nan')):.2f} h for 40 method runs. CUIFA (RTX 4070 Ti SUPER, {target.get('workers')}/{target.get('prefetch_batches')}) measured {target.get('paired_optimizer_steps_per_second', float('nan')):.3f} paired steps/s and projected {target.get('40_method_training_plus_validation_hours', float('nan')):.2f} h; the measured paired-step rate ratio is {observed.get('paired_step_rate_ratio', float('nan')):.2f}×.",
                "",
                f"Observed completed-cell wall time was {observed.get('actual_completed_pair_wall_hours', float('nan')):.2f} h, plus {observed.get('interrupted_partial_pair_hours', float('nan')):.2f} h for the interrupted partial attempt; end-to-end wall time was {observed.get('end_to_end_wall_hours', float('nan')):.2f} h. The historical ~8-hour run is an unverified recollection. The rate comparison includes both a GPU change and runtime-setting change, so it is not a software-only speedup estimate.",
            ]
        )

    lines.extend(
        [
            "",
            "## Figures and machine-readable results",
            "",
            "- [Learning curve](parent_budget_efficiency/learning_curve.png)",
            "  Error bars show sample SD across the five training seeds.",
            "- [Paired differences](parent_budget_efficiency/paired_deltas.png)",
            "  Error bars show sample SD across the five matched training-seed differences; the dashed line marks zero.",
            "- [Summary JSON](parent_budget_efficiency/results.json)",
            "- [Per-seed metrics CSV](parent_budget_efficiency/per_seed_metrics.csv)",
            "- [Paired-difference CSV](parent_budget_efficiency/paired_deltas.csv)",
            "- Checkpoints, panel caches, and per-parent predictions are retained in the ignored local output directory, outside Git.",
            "",
            "## Provenance and interpretation limits",
            "",
            f"Parent subset manifest SHA-256: `{provenance.get('subset_manifest_sha256', 'pending')}`. Protocol config SHA-256: `{provenance.get('protocol_config_sha256', 'pending')}`. Local output root: `{provenance.get('output_root', 'pending')}`.",
            "",
            "All available cells were retained regardless of outcome. Paired uncertainty is summarized over training seeds; intervals crossing zero are reported as uncertain evidence, not erased or treated as a binary experiment failure. This experiment evaluates simulated parent-structure budget efficiency only; it does not estimate RRUFF real-label efficiency.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    output_root = args.output_root.resolve()
    config = json.loads((PROJECT_ROOT / "configs" / "parent_budget_efficiency.v1.json").read_text(encoding="utf-8"))
    runtime = _configure_training_runtime(config, device)
    runtime_selection_path = output_root / "runtime_selection.json"
    runtime_selection = (
        json.loads(runtime_selection_path.read_text(encoding="utf-8"))
        if runtime_selection_path.is_file()
        else {}
    )
    runtime["prefetch_workers"] = int(
        runtime_selection.get("selected_workers", runtime.get("prefetch_workers", 0))
    )
    runtime["prefetch_batches"] = int(
        runtime_selection.get("selected_prefetch_batches", runtime.get("prefetch_batches", 0))
    )
    simulation_path = PROJECT_ROOT / "configs" / "simulation.method_transfer.frozen.json"
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    split_rows = load_split_rows(args.data_root.resolve())
    test_profiles = config["evaluation"]["test_profiles"]
    panel_index, panels, labels = _ensure_eval_cache(
        data_root=args.data_root.resolve(),
        cache_root=output_root / "evaluation_cache",
        split_rows=split_rows,
        simulation=simulation,
        eval_seeds=EVALUATION_SEEDS,
        profiles=test_profiles,
        split="test",
        input_length=ML4PXRDResNet1DConfig().input_length,
    )
    material_ids = panel_index["material_ids"]
    test_rows: list[dict[str, Any]] = []
    run_records: list[dict[str, Any]] = []
    completed_pairs: list[str] = []
    model_config = ML4PXRDResNet1DConfig(model_id="18")
    for seed in SEEDS:
        for budget in BUDGET_ORDER:
            pair_dir = _pair_dir(output_root, seed, budget)
            result_path = pair_dir / "result.json"
            key = f"seed_{seed}:parents_{BUDGETS[budget]}"
            if not result_path.is_file():
                continue
            run_result = json.loads(result_path.read_text(encoding="utf-8"))
            if run_result.get("status") != "completed":
                continue
            completed_pairs.append(key)
            test_metrics_path = pair_dir / "test_metrics.json"
            if test_metrics_path.is_file():
                pair_test = json.loads(test_metrics_path.read_text(encoding="utf-8"))
            else:
                pair_test = {
                    "schema_version": "parent-budget-test-results-v1",
                    "status": "completed",
                    "training_seed": seed,
                    "budget_percent": int(budget),
                    "parent_count": BUDGETS[budget],
                    "selected_checkpoints": {},
                    "methods": {},
                }
                for method in ("dynamic_erm", "dynamic_js"):
                    checkpoint_path = pair_dir / f"{method}.best.ckpt"
                    model = ML4PXRDResNet1D(model_config).to(device)
                    selected_step = _load_checkpoint(model, checkpoint_path, device)
                    prediction_path = (
                        output_root
                        / "predictions"
                        / f"seed_{seed}"
                        / f"parents_{BUDGETS[budget]}"
                        / f"{method}.csv.gz"
                    )
                    prediction_path.parent.mkdir(parents=True, exist_ok=True)
                    metrics = _evaluate_model(
                        model,
                        panels,
                        labels,
                        seeds=EVALUATION_SEEDS,
                        profiles=test_profiles,
                        batch_size=int(config["evaluation"]["batch_size"]),
                        device=device,
                        material_ids=material_ids,
                        prediction_path=prediction_path,
                        prediction_context={
                            "training_seed": seed,
                            "budget_percent": int(budget),
                            "method": method,
                        },
                    )
                    pair_test["selected_checkpoints"][method] = {
                        "global_step": selected_step,
                        "sha256": sha256_file(checkpoint_path),
                    }
                    pair_test["methods"][method] = metrics
                    pair_test.setdefault("prediction_files", {})[method] = {
                        "path": str(prediction_path),
                        "sha256": sha256_file(prediction_path),
                        "rows": len(EVALUATION_SEEDS) * len(test_profiles) * len(material_ids),
                    }
                    del model
                temporary = test_metrics_path.with_suffix(".partial")
                temporary.write_text(json.dumps(pair_test, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                temporary.replace(test_metrics_path)

            record: dict[str, Any] = {
                "training_seed": seed,
                "budget_percent": int(budget),
                "parent_count": BUDGETS[budget],
            }
            for method in ("dynamic_erm", "dynamic_js"):
                summary = _method_summary(pair_test["methods"][method])
                row = {
                    **record,
                    "method": method,
                    "selected_step": int(
                        pair_test["selected_checkpoints"][method]["global_step"]
                    ),
                    "validation_best_ood_macro_f1": float(
                        run_result["best_validation"][method]["single_factor_ood_macro_f1"]
                    ),
                    "validation_best_in_range_macro_f1": float(
                        run_result["best_validation"][method]["in_range_macro_f1"]
                    ),
                    **{
                        key: summary[key]
                        for key in (
                            "single_factor_ood_macro_f1",
                            "single_factor_ood_accuracy",
                            "in_range_macro_f1",
                            "in_range_accuracy",
                            "level0_macro_f1",
                            "level0_accuracy",
                        )
                    },
                }
                row.update(
                    {
                        f"ood_macro_f1_{profile}": summary["ood_macro_f1_by_profile"][profile]
                        for profile in OOD_PROFILES
                    }
                )
                row.update(
                    {
                        f"ood_accuracy_{profile}": summary["ood_accuracy_by_profile"][profile]
                        for profile in OOD_PROFILES
                    }
                )
                row.update(
                    {
                        f"per_class_ood_f1_{crystal}": summary["per_class_f1"][crystal]
                        for crystal in CRYSTAL_SYSTEMS
                    }
                )
                # Keep the nested aggregation inputs alongside the flat report
                # columns. _summarize consumes per_seed rows and expects both
                # mappings to compute cross-seed/profile summaries.
                row["ood_macro_f1_by_profile"] = summary["ood_macro_f1_by_profile"]
                row["per_class_f1"] = summary["per_class_f1"]
                test_rows.append(row)
                run_records.append(
                    {
                        **row,
                        "selected_checkpoint": pair_test["selected_checkpoints"][method],
                        "test_metrics": pair_test["methods"][method],
                    }
                )
    summary = _summarize(test_rows)
    complete_matrix = len(completed_pairs) == len(SEEDS) * len(BUDGET_ORDER) and len(test_rows) == 40
    savings = _equivalent_parent_estimates(summary, complete_matrix)
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(report_dir / "per_seed_metrics.csv", test_rows)
    _write_csv(
        report_dir / "paired_deltas.csv",
        summary["paired_deltas"],
    )
    _plots(summary, report_dir)
    benchmark_path = next(
        (
            path
            for path in (output_root / "benchmark.json", output_root / "cuiFA_benchmark.json")
            if path.is_file()
        ),
        None,
    )
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path else None
    if benchmark is not None:
        benchmark["benchmark_run_sources"] = [
            Path(value).name for value in benchmark.get("benchmark_run_sources", [])
        ]
        benchmark["resource_telemetry_csv"] = [
            Path(value).name for value in benchmark.get("resource_telemetry_csv", [])
        ]
        benchmark["validation_panel_cache_path"] = "local benchmark cache (excluded from Git)"
        for setting in benchmark.get("settings", []):
            for measurement in setting.get("replicate_measurements", []):
                if measurement.get("source"):
                    measurement["source"] = Path(measurement["source"]).name
    runtime_audit_path = output_root / "execution_time_audit.json"
    runtime_audit = (
        json.loads(runtime_audit_path.read_text(encoding="utf-8"))
        if runtime_audit_path.is_file()
        else None
    )
    source_comparison_path = output_root / "source_benchmark_comparison.json"
    source_comparison = (
        json.loads(source_comparison_path.read_text(encoding="utf-8"))
        if source_comparison_path.is_file()
        else None
    )
    provenance = {
        "source_records_count": 14060,
        "peak_tables_verified": 14060,
        "subset_manifest_sha256": sha256_file(PROJECT_ROOT / "manifests" / "parent_budget_efficiency" / "parent_subsets.v1.json"),
        "protocol_config_sha256": sha256_file(PROJECT_ROOT / "configs" / "parent_budget_efficiency.v1.json"),
        "output_root": "CUIFA local ignored output directory (excluded from Git)",
        "performance_runtime": runtime,
        "benchmark": benchmark,
        "runtime_audit": runtime_audit,
        "source_benchmark_comparison": source_comparison,
    }
    results = {
        "schema_version": "parent-budget-efficiency-results-v1",
        "status": "completed" if complete_matrix else "partial",
        "completed_seed_budget_pairs": completed_pairs,
        "completed_method_runs": len(test_rows),
        "planned_seed_budget_pairs": 20,
        "planned_method_runs": 40,
        "evaluation_seeds": list(EVALUATION_SEEDS),
        "primary_metric": "mean Macro-F1 across six simulated single-factor OOD profiles and three evaluation seeds",
        "summary": summary,
        "data_savings_assessment": savings,
        "provenance": provenance,
        "run_metrics": run_records,
    }
    (report_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(
        PROJECT_ROOT / "reports" / "PARENT_BUDGET_EFFICIENCY.md",
        summary=summary,
        results=run_records,
        completed_pairs=completed_pairs,
        complete_matrix=complete_matrix,
        data_savings=savings,
        provenance=provenance,
    )
    print(
        json.dumps(
            {
                "status": results["status"],
                "completed_method_runs": len(test_rows),
                "completed_pairs": len(completed_pairs),
                "data_savings": savings["status"],
                "report": str(PROJECT_ROOT / "reports" / "PARENT_BUDGET_EFFICIENCY.md"),
                "analysis_time_unix": time.time(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
