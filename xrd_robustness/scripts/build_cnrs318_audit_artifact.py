#!/usr/bin/env python3
"""Build the portable CNRS-318 audit-report artifact from reviewed outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_DIR = PROJECT_ROOT / "outputs" / "cnrs318_zero_shot" / "audit"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _number(value: str) -> int | float:
    parsed = float(value)
    return int(parsed) if parsed.is_integer() else parsed


def _typed_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    typed: list[dict[str, Any]] = []
    for row in rows:
        current: dict[str, Any] = {}
        for key, value in row.items():
            try:
                current[key] = _number(value)
            except ValueError:
                current[key] = value
        typed.append(current)
    return typed


def _source(
    source_id: str,
    label: str,
    path: str,
    description: str,
    metric_definitions: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, Any]]:
    manifest_source = {"id": source_id, "label": label, "path": path}
    query: dict[str, Any] = {
        "engine": "local_reviewed_artifacts",
        "sql": (
            f"SELECT * FROM read_json_auto('{path}')"
            if path.endswith(".json")
            else f"SELECT * FROM read_csv_auto('{path}', header = true)"
        ),
        "description": description,
        "tables_used": [path],
    }
    if metric_definitions:
        query["metric_definitions"] = metric_definitions
    return manifest_source, {"id": source_id, "query": query}


def build_artifact(audit_dir: Path) -> dict[str, Any]:
    summary = json.loads((audit_dir / "summary.json").read_text(encoding="utf-8"))
    funnel = _typed_rows(_read_csv(audit_dir / "construction_funnel.csv"))
    class_distribution = _typed_rows(_read_csv(audit_dir / "class_distribution.csv"))
    paired_seed = _typed_rows(_read_csv(audit_dir / "paired_seed_macro_f1.csv"))
    per_class = _typed_rows(_read_csv(audit_dir / "per_class_metrics.csv"))
    pooled = _typed_rows(_read_csv(audit_dir / "pooled_metrics.csv"))

    for index, row in enumerate(funnel, start=1):
        row["stage_order"] = index
        row["retained_fraction_of_raw"] = row["count"] / funnel[0]["count"]

    total_parents = sum(row["support_parents"] for row in class_distribution)
    for row in class_distribution:
        row["share_of_domain"] = row["support_parents"] / total_parents
        row["balanced_equivalent_minimum"] = 20
        row["meets_minimum_20"] = row["support_parents"] >= 20

    seed_long: list[dict[str, Any]] = []
    for row in paired_seed:
        for method, field in (("Dynamic ERM", "erm_macro_f1"), ("JS Consistency", "js_macro_f1")):
            seed_long.append(
                {
                    "seed": row["seed"],
                    "method": method,
                    "macro_f1": row[field],
                    "paired_delta_js_minus_erm": row["delta_macro_f1"],
                    "js_wins_pair": row["delta_macro_f1"] > 0,
                }
            )

    class_long: list[dict[str, Any]] = []
    for row in per_class:
        for method, prefix in (("Dynamic ERM", "erm"), ("JS Consistency", "js")):
            class_long.append(
                {
                    "class_index": row["class_index"],
                    "crystal_system": row["crystal_system"],
                    "support_parents": row["support_parents"],
                    "method": method,
                    "precision": row[f"{prefix}_precision"],
                    "recall": row[f"{prefix}_recall"],
                    "f1": row[f"{prefix}_f1"],
                    "delta_f1_js_minus_erm": row["delta_f1"],
                }
            )

    headline = summary["headline"]
    erm = next(row for row in pooled if row["method_id"] == "ordinary_dynamic_augmentation")
    js = next(row for row in pooled if row["method_id"] == "js_consistency_transfer")
    majority_baseline = 87 / 318
    overview = [
        {
            "n_parents": total_parents,
            "n_prediction_rows": summary["integrity"]["prediction_rows"],
            "n_checkpoints": summary["integrity"]["checkpoint_hashes_verified"],
            "mean_paired_delta_macro_f1": headline["mean_seed_paired_delta_macro_f1"],
            "positive_seed_pairs": headline["positive_seed_pairs"],
            "total_seed_pairs": headline["total_seed_pairs"],
            "ci_low": headline["class_stratified_paired_bootstrap_95_ci"][0],
            "ci_high": headline["class_stratified_paired_bootstrap_95_ci"][1],
            "erm_macro_f1": erm["macro_f1"],
            "js_macro_f1": js["macro_f1"],
            "pooled_delta_macro_f1": js["macro_f1"] - erm["macro_f1"],
            "erm_ece": erm["ece"],
            "js_ece": js["ece"],
            "ece_change": js["ece"] - erm["ece"],
            "erm_accuracy": erm["accuracy"],
            "js_accuracy": js["accuracy"],
            "majority_accuracy_baseline": majority_baseline,
        }
    ]

    source_specs = [
        _source(
            "audit_summary",
            "CNRS-318 machine-readable audit summary",
            "outputs/cnrs318_zero_shot/audit/summary.json",
            "Independent reconstruction, integrity checks, metrics, and corrected paired bootstrap.",
            {
                "mean paired delta": "Mean across the five fixed seeds of Macro-F1(JS) - Macro-F1(ERM).",
                "paired bootstrap CI": "Class-stratified parent resampling shared by ERM, JS, and all fixed seeds; 10,000 replicates.",
                "ECE": "Expected calibration error with 15 equal-width confidence bins.",
            },
        ),
        _source(
            "construction_funnel",
            "CNRS-318 construction funnel",
            "outputs/cnrs318_zero_shot/audit/construction_funnel.csv",
            "Counts at each deterministic dataset-construction stage.",
        ),
        _source(
            "class_distribution",
            "CNRS-318 crystal-system distribution",
            "outputs/cnrs318_zero_shot/audit/class_distribution.csv",
            "Frozen parent counts for the seven crystal systems.",
        ),
        _source(
            "paired_seed_metrics",
            "Seed-paired Macro-F1",
            "outputs/cnrs318_zero_shot/audit/paired_seed_macro_f1.csv",
            "Macro-F1 for the frozen ERM/JS checkpoint pair at each registered seed.",
            {"delta": "Macro-F1(JS Consistency) - Macro-F1(Dynamic ERM) within the same seed."},
        ),
        _source(
            "per_class_metrics",
            "Pooled per-class metrics",
            "outputs/cnrs318_zero_shot/audit/per_class_metrics.csv",
            "Precision, recall, and F1 pooled across five model seeds for each crystal system.",
        ),
        _source(
            "pooled_metrics",
            "Pooled aggregate metrics",
            "outputs/cnrs318_zero_shot/audit/pooled_metrics.csv",
            "Descriptive metrics pooled across all five seeds and 318 frozen parents.",
        ),
    ]
    manifest_sources = [item[0] for item in source_specs]
    canonical_sources = [item[1] for item in source_specs]

    cards = [
        {
            "id": "domain_size_card",
            "description": "Frozen, structure-parent-deduplicated external-domain evaluation set.",
            "dataset": "overview",
            "sourceId": "audit_summary",
            "metrics": [
                {"label": "Independent parents", "field": "n_parents", "format": "number"},
                {"label": "Prediction rows", "field": "n_prediction_rows", "format": "number"},
                {"label": "Verified checkpoints", "field": "n_checkpoints", "format": "number"},
            ],
        },
        {
            "id": "paired_delta_card",
            "description": "Primary seed-paired effect; the corrected 95% interval crosses zero.",
            "dataset": "overview",
            "sourceId": "audit_summary",
            "metrics": [
                {"label": "Mean paired Δ Macro-F1", "field": "mean_paired_delta_macro_f1", "format": "percent", "signed": True},
                {"label": "95% CI low", "field": "ci_low", "format": "percent", "signed": True},
                {"label": "95% CI high", "field": "ci_high", "format": "percent", "signed": True},
            ],
        },
        {
            "id": "pooled_f1_card",
            "description": "Descriptive pooled Macro-F1 across all five seeds.",
            "dataset": "overview",
            "sourceId": "pooled_metrics",
            "metrics": [
                {"label": "JS pooled Macro-F1", "field": "js_macro_f1", "format": "percent"},
                {"label": "ERM", "field": "erm_macro_f1", "format": "percent"},
                {"label": "Δ", "field": "pooled_delta_macro_f1", "format": "percent", "signed": True},
            ],
        },
        {
            "id": "calibration_card",
            "description": "Lower ECE is better; both methods remain overconfident.",
            "dataset": "overview",
            "sourceId": "pooled_metrics",
            "metrics": [
                {"label": "JS ECE", "field": "js_ece", "format": "percent"},
                {"label": "ERM ECE", "field": "erm_ece", "format": "percent"},
                {"label": "Change", "field": "ece_change", "format": "percent", "signed": True},
            ],
        },
    ]

    charts = [
        {
            "id": "funnel_chart",
            "title": "CNRS-318 construction funnel",
            "subtitle": "1,052 raw files become 318 structure-independent parents.",
            "type": "bar",
            "dataset": "construction_funnel",
            "sourceId": "construction_funnel",
            "valueFormat": "number",
            "encodings": {
                "x": {"field": "label", "type": "nominal", "label": "Construction stage"},
                "y": {"field": "count", "type": "quantitative", "label": "Records"},
                "tooltip": [
                    {"field": "count", "type": "quantitative", "label": "Records", "format": "number"},
                    {"field": "retained_fraction_of_raw", "type": "quantitative", "label": "Retained vs raw", "format": "percent"},
                ],
            },
        },
        {
            "id": "class_distribution_chart",
            "title": "Natural class imbalance",
            "subtitle": "Hexagonal has 12 parents; the formal domain is not a balanced RRUFF replica.",
            "type": "bar",
            "dataset": "class_distribution",
            "sourceId": "class_distribution",
            "valueFormat": "number",
            "encodings": {
                "x": {"field": "crystal_system", "type": "nominal", "label": "Crystal system"},
                "y": {"field": "support_parents", "type": "quantitative", "label": "Independent parents"},
                "tooltip": [
                    {"field": "support_parents", "type": "quantitative", "label": "Parents", "format": "number"},
                    {"field": "share_of_domain", "type": "quantitative", "label": "Domain share", "format": "percent"},
                    {"field": "meets_minimum_20", "type": "nominal", "label": "At least 20"},
                ],
            },
        },
        {
            "id": "seed_pair_chart",
            "title": "Frozen seed-paired Macro-F1",
            "subtitle": "JS exceeds ERM for each of the five registered seeds.",
            "type": "line",
            "dataset": "seed_f1_long",
            "sourceId": "paired_seed_metrics",
            "valueFormat": "percent",
            "encodings": {
                "x": {"field": "seed", "type": "ordinal", "label": "Registered seed"},
                "y": {"field": "macro_f1", "type": "quantitative", "label": "Macro-F1"},
                "color": {"field": "method", "type": "nominal", "label": "Method"},
                "tooltip": [
                    {"field": "method", "type": "nominal", "label": "Method"},
                    {"field": "macro_f1", "type": "quantitative", "label": "Macro-F1", "format": "percent"},
                    {"field": "paired_delta_js_minus_erm", "type": "quantitative", "label": "Paired Δ", "format": "percent"},
                ],
            },
        },
        {
            "id": "per_class_f1_chart",
            "title": "Pooled F1 by crystal system",
            "subtitle": "JS improves five classes; monoclinic and tetragonal decline.",
            "type": "bar",
            "dataset": "per_class_long",
            "sourceId": "per_class_metrics",
            "valueFormat": "percent",
            "encodings": {
                "x": {"field": "crystal_system", "type": "nominal", "label": "Crystal system"},
                "y": {"field": "f1", "type": "quantitative", "label": "Pooled F1"},
                "color": {"field": "method", "type": "nominal", "label": "Method"},
                "tooltip": [
                    {"field": "method", "type": "nominal", "label": "Method"},
                    {"field": "f1", "type": "quantitative", "label": "F1", "format": "percent"},
                    {"field": "support_parents", "type": "quantitative", "label": "Parents", "format": "number"},
                    {"field": "delta_f1_js_minus_erm", "type": "quantitative", "label": "JS − ERM", "format": "percent"},
                ],
            },
        },
    ]

    tables = [
        {
            "id": "paired_seed_table",
            "title": "Seed-paired primary metric",
            "subtitle": "All five deltas are positive; the inferential interval is computed over parents.",
            "dataset": "paired_seed_macro_f1",
            "sourceId": "paired_seed_metrics",
            "columns": [
                {"field": "seed", "label": "Seed", "format": "number"},
                {"field": "erm_macro_f1", "label": "ERM Macro-F1", "format": "percent"},
                {"field": "js_macro_f1", "label": "JS Macro-F1", "format": "percent"},
                {"field": "delta_macro_f1", "label": "Δ", "format": "percent"},
            ],
        },
        {
            "id": "per_class_table",
            "title": "Per-class pooled metrics",
            "subtitle": "Class-level results are descriptive; hexagonal is underpowered at n=12.",
            "dataset": "per_class_metrics",
            "sourceId": "per_class_metrics",
            "columns": [
                {"field": "crystal_system", "label": "Crystal system", "type": "text"},
                {"field": "support_parents", "label": "Parents", "format": "number"},
                {"field": "erm_f1", "label": "ERM F1", "format": "percent"},
                {"field": "js_f1", "label": "JS F1", "format": "percent"},
                {"field": "delta_f1", "label": "JS − ERM", "format": "percent"},
            ],
        },
        {
            "id": "pooled_metrics_table",
            "title": "Pooled descriptive metrics",
            "subtitle": "Accuracy is below the 27.36% majority-class baseline for both methods.",
            "dataset": "pooled_metrics",
            "sourceId": "pooled_metrics",
            "columns": [
                {"field": "method_name", "label": "Method", "type": "text"},
                {"field": "macro_f1", "label": "Macro-F1", "format": "percent"},
                {"field": "balanced_accuracy", "label": "Balanced accuracy", "format": "percent"},
                {"field": "accuracy", "label": "Accuracy", "format": "percent"},
                {"field": "ece", "label": "ECE", "format": "percent"},
                {"field": "nll", "label": "NLL", "format": "number"},
                {"field": "brier", "label": "Brier", "format": "number"},
                {"field": "mean_confidence", "label": "Mean confidence", "format": "percent"},
            ],
        },
    ]

    blocks = [
        {"id": "title", "type": "markdown", "body": "# CNRS-318 第二真实域：零样本外部域审计"},
        {
            "id": "executive_summary",
            "type": "markdown",
            "sourceId": "audit_summary",
            "body": (
                "## 执行摘要\n\n"
                "**判定：可作为正式第二真实实验域，但应称为零样本外部域压力测试，不能称为 CNRS 域适配。** "
                "318 个冻结结构母体、3,180 条预测和 10 个 checkpoint 均通过完整性核验；原始谱重建到冻结输入的最大绝对误差为 0。"
                "JS 在 5/5 个固定 seed 上优于 ERM，平均配对 ΔMacro-F1 为 +1.87 个百分点；但修正后的 95% CI 为 "
                "[−0.93, +4.61] 个百分点并跨 0，因此证据是方向性支持，而非统计稳定复现。"
            ),
        },
        {"id": "headline_metrics", "type": "metric-strip", "cardIds": ["domain_size_card", "paired_delta_card", "pooled_f1_card", "calibration_card"]},
        {
            "id": "scope_heading",
            "type": "markdown",
            "body": (
                "## 范围与指标\n\n"
                "主效应是五个冻结 seed 的配对 Macro-F1 差值均值；置信区间按晶系分层，对父样本执行共享配对 bootstrap。"
                "Pooled Macro-F1、balanced accuracy、accuracy 与校准指标只作为描述性补充。"
            ),
        },
        {"id": "funnel", "type": "chart", "chartId": "funnel_chart"},
        {
            "id": "funnel_note",
            "type": "markdown",
            "sourceId": "construction_funnel",
            "body": (
                "去重和独立性筛选是必要的，不能把 1,052 条原始文件直接当作独立样本。最终口径为：稳定结构标签 → 谱线唯一候选 → 结构母体去重 → 剔除与 formal_14060 重叠的 5 个母体。"
            ),
        },
        {"id": "class_distribution", "type": "chart", "chartId": "class_distribution_chart"},
        {
            "id": "imbalance_note",
            "type": "markdown",
            "sourceId": "class_distribution",
            "body": (
                "自然不均衡是该外部域的真实属性，不是构建失败。每类至少 20 条只适用于“均衡等价复刻 RRUFF”的更强命题；正式第二域允许保留全部 318 条，"
                "但六方晶系 n=12 的逐类结论必须视为低功效描述。"
            ),
        },
        {
            "id": "findings_heading",
            "type": "markdown",
            "body": "## 核心结果\n\n下面先看固定 seed 的成对结果，再看 pooled 描述统计与逐类异质性。",
        },
        {"id": "seed_pair", "type": "chart", "chartId": "seed_pair_chart"},
        {
            "id": "seed_note",
            "type": "markdown",
            "sourceId": "paired_seed_metrics",
            "body": (
                "5/5 个 seed 的方向一致，是最强的正向信号；但配对 bootstrap 的区间仍跨 0。不能把“所有 seed 都变好”写成“效应已统计确认”。"
            ),
        },
        {"id": "paired_seed_table_block", "type": "table", "tableId": "paired_seed_table"},
        {"id": "pooled_metrics_table_block", "type": "table", "tableId": "pooled_metrics_table"},
        {
            "id": "absolute_performance_note",
            "type": "markdown",
            "sourceId": "pooled_metrics",
            "body": (
                "JS 同时改善 pooled Macro-F1、balanced accuracy、ECE、NLL 与 Brier，但绝对性能仍弱。ERM/JS accuracy 分别约 20.0%/21.0%，"
                "均低于多数类基线 27.36%；两者平均置信度又高达约 88.3%/82.2%，说明仍明显过度自信。"
            ),
        },
        {"id": "per_class", "type": "chart", "chartId": "per_class_f1_chart"},
        {
            "id": "class_note",
            "type": "markdown",
            "sourceId": "per_class_metrics",
            "body": (
                "提升并非全类一致：orthorhombic 与 hexagonal 增幅最大，而 monoclinic 和 tetragonal 下降。尤其 hexagonal 只有 12 个父样本，不能据此宣称稳定的类别级优势。"
            ),
        },
        {"id": "per_class_table_block", "type": "table", "tableId": "per_class_table"},
        {
            "id": "methodology",
            "type": "markdown",
            "sourceId": "audit_summary",
            "body": (
                "## 方法与完整性\n\n"
                "冻结评测使用 10–80° 2θ、0.02° 网格、Cu Kα 等效波长映射和逐谱最大值归一化。审计重新读取 318 个原始 JSON，重建输入并逐元素对照 NPZ；"
                "同时核对三个 manifest 的样本顺序与标签、3,180 条预测身份与概率、以及冻结配置中的 10 个 checkpoint SHA-256。所有硬完整性检查均通过。"
            ),
        },
        {
            "id": "limitations",
            "type": "markdown",
            "sourceId": "audit_summary",
            "body": (
                "## 局限与稳健性\n\n"
                "- CNRS 标签由结构派生，未做逐谱人工物相核验。\n"
                "- CNRS 数据没有参与训练、微调、模型选择或阈值选择；因此这是 zero-shot external evaluation，不是 adaptation。\n"
                "- 数据天然不均衡，hexagonal 仅 12 个父样本。\n"
                "- 两条冻结谱保留负强度，因为冻结预处理没有裁零；这是已记录的域差异，不是事后清洗依据。\n"
                "- 原始 prediction report 没有嵌入 input NPZ 哈希、设备或 Git commit；当前 run record 是事后完整性审计绑定，不能冒充原始运行时 provenance。\n"
                "- 冻结输入、预测、manifest、checkpoint 和分析代码的当前哈希均已记录且相互核验，未发现内容不一致。"
            ),
        },
        {
            "id": "next_steps",
            "type": "markdown",
            "body": (
                "## 建议的论文定位\n\n"
                "保留 RRUFF 作为均衡、策展式的 few-shot adaptation 主证据；把 CNRS-318 作为自然不均衡、独立来源的 zero-shot 外推压力测试。"
                "论文主张应限定为：JS 正则在两个互补真实域上呈现一致的总体方向，其中 RRUFF 提供适配证据，CNRS 提供域外泛化证据；CNRS 单独不足以证明稳定跨域优势。"
            ),
        },
    ]

    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "CNRS-318 第二真实域：零样本外部域审计",
            "description": "CNRS-318 construction, integrity, performance, calibration, and claim-boundary audit.",
            "generatedAt": summary["generated_at"],
            "cards": cards,
            "charts": charts,
            "tables": tables,
            "sources": manifest_sources,
            "blocks": blocks,
        },
        "snapshot": {
            "version": 1,
            "generatedAt": summary["generated_at"],
            "status": "ready",
            "datasets": {
                "overview": overview,
                "construction_funnel": funnel,
                "class_distribution": class_distribution,
                "seed_f1_long": seed_long,
                "paired_seed_macro_f1": paired_seed,
                "per_class_long": class_long,
                "per_class_metrics": per_class,
                "pooled_metrics": pooled,
            },
            "accessIssues": [],
        },
        "sources": canonical_sources,
        "package_info": {
            "originUrl": "artifact://cnrs318-zero-shot-audit",
            "controls": {"edit": False, "refresh": False, "share": False},
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, default=DEFAULT_AUDIT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_AUDIT_DIR / "artifact.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifact = build_artifact(args.audit_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output.resolve()}")


if __name__ == "__main__":
    main()
