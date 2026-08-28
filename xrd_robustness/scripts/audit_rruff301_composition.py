#!/usr/bin/env python3
"""Read-only composition audit for the frozen RRUFF-301 few-shot split.

This script answers a narrow descriptive question using the already-built local
RRUFF database: how much exact metadata overlap exists between the 70-sample
adaptation pool and the 231-sample locked test set, and are there very highly
correlated stored spectra across the split?

It does not load models, inspect predictions, alter the split, remove samples, or
change any reported result. Overlap is descriptive rather than a pass/fail gate.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER = ROOT / "data/real_xrd/rruff371/manifests/rruff371_master_manifest.csv"
DEFAULT_SPLIT = ROOT / "data/real_xrd/rruff371/splits/rruff301_adaptation_test_split.csv"
DEFAULT_OUTPUT_PREFIX = ROOT / "reports/RRUFF301_COMPOSITION_AUDIT"
REQUIRED_SPLIT_COLUMNS = {"rruff_id", "crystal_system", "split", "rank"}
REQUIRED_MASTER_COLUMNS = {
    "rruff_id",
    "mineral_name",
    "crystal_system",
    "spectrum_path",
    "spectrum_sha256",
    "ideal_chemistry",
    "measured_chemistry",
    "space_group",
}
ROLES = ("adaptation_pool", "locked_test")
CORRELATION_THRESHOLDS = (0.95, 0.98, 0.995)


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"{path.name} missing required columns: {missing}")
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").strip().casefold()
    return re.sub(r"\s+", " ", text)


def normalize_formula_string(value: str) -> str:
    # Exact-string comparison after Unicode/whitespace normalization only.
    # This intentionally does not perform chemistry parsing or formula reduction.
    return re.sub(r"\s+", "", normalize_text(value))


def normalize_space_group(value: str) -> str:
    return re.sub(r"\s+", "", normalize_text(value))


def build_index(
    rows: list[dict[str, str]],
    master_by_id: dict[str, dict[str, str]],
    field: str,
    normalizer: Callable[[str], str],
) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        sample_id = row["rruff_id"]
        value = normalizer(master_by_id[sample_id].get(field, ""))
        if value:
            index[value].append(sample_id)
    return dict(index)


def overlap_summary(
    adaptation_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    master_by_id: dict[str, dict[str, str]],
    field: str,
    normalizer: Callable[[str], str],
) -> dict[str, Any]:
    adaptation_index = build_index(adaptation_rows, master_by_id, field, normalizer)
    test_index = build_index(test_rows, master_by_id, field, normalizer)
    shared = sorted(set(adaptation_index) & set(test_index))

    details: list[dict[str, Any]] = []
    adaptation_ids: set[str] = set()
    test_ids: set[str] = set()
    pair_count = 0
    for key in shared:
        a_ids = sorted(adaptation_index[key])
        t_ids = sorted(test_index[key])
        adaptation_ids.update(a_ids)
        test_ids.update(t_ids)
        pairs = len(a_ids) * len(t_ids)
        pair_count += pairs
        representative = master_by_id[a_ids[0]].get(field, "") or key
        details.append(
            {
                "normalized_value": key,
                "display_value": representative,
                "adaptation_ids": a_ids,
                "locked_test_ids": t_ids,
                "cross_split_pairs": pairs,
            }
        )

    details.sort(
        key=lambda item: (-item["cross_split_pairs"], item["normalized_value"])
    )
    return {
        "field": field,
        "overlapping_unique_values": len(shared),
        "adaptation_samples_in_overlap": len(adaptation_ids),
        "locked_test_samples_in_overlap": len(test_ids),
        "cross_split_pair_count": pair_count,
        "details": details,
    }


def load_profile(dataset_root: Path, manifest_row: dict[str, str]) -> np.ndarray:
    relative = Path(manifest_row["spectrum_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(
            f"unsafe spectrum_path for {manifest_row['rruff_id']}: {relative}"
        )
    path = dataset_root / relative
    if not path.is_file():
        raise FileNotFoundError(
            f"missing stored spectrum for {manifest_row['rruff_id']}: {path}"
        )
    array = np.loadtxt(path, delimiter=",", skiprows=1)
    if array.ndim != 2 or array.shape[1] < 2:
        raise ValueError(f"unexpected spectrum shape for {path}: {array.shape}")
    profile = np.asarray(array[:, 1], dtype=np.float64)
    if not np.isfinite(profile).all() or profile.size < 2:
        raise ValueError(f"invalid spectrum values for {path}")
    return profile


def standardized_rows(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - matrix.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    if np.any(norms <= 0):
        raise ValueError("at least one stored spectrum has zero variance")
    return centered / norms


def spectral_overlap(
    adaptation_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    master_by_id: dict[str, dict[str, str]],
    dataset_root: Path,
    *,
    top_n: int,
) -> dict[str, Any]:
    adaptation_profiles = [
        load_profile(dataset_root, master_by_id[row["rruff_id"]])
        for row in adaptation_rows
    ]
    test_profiles = [
        load_profile(dataset_root, master_by_id[row["rruff_id"]])
        for row in test_rows
    ]
    lengths = {profile.size for profile in adaptation_profiles + test_profiles}
    if len(lengths) != 1:
        raise ValueError(f"stored spectra do not share one grid length: {sorted(lengths)}")

    a = standardized_rows(np.stack(adaptation_profiles))
    b = standardized_rows(np.stack(test_profiles))
    corr = np.clip(a @ b.T, -1.0, 1.0)

    a_classes = np.array([row["crystal_system"].casefold() for row in adaptation_rows])
    t_classes = np.array([row["crystal_system"].casefold() for row in test_rows])
    same_class = a_classes[:, None] == t_classes[None, :]

    threshold_stats: dict[str, Any] = {}
    for threshold in CORRELATION_THRESHOLDS:
        mask = corr >= threshold
        same_class_mask = mask & same_class
        threshold_stats[f"ge_{threshold}"] = {
            "all_cross_split_pairs": int(mask.sum()),
            "same_class_pairs": int(same_class_mask.sum()),
            "adaptation_samples_with_any_match": int(mask.any(axis=1).sum()),
            "locked_test_samples_with_any_match": int(mask.any(axis=0).sum()),
        }

    flat_order = np.argsort(corr, axis=None)[::-1][: max(1, top_n)]
    top_pairs: list[dict[str, Any]] = []
    for flat_index in flat_order:
        i, j = np.unravel_index(int(flat_index), corr.shape)
        a_id = adaptation_rows[i]["rruff_id"]
        t_id = test_rows[j]["rruff_id"]
        a_meta = master_by_id[a_id]
        t_meta = master_by_id[t_id]
        top_pairs.append(
            {
                "pearson": float(corr[i, j]),
                "same_crystal_system": bool(same_class[i, j]),
                "adaptation_id": a_id,
                "adaptation_mineral": a_meta.get("mineral_name", ""),
                "adaptation_ideal_chemistry": a_meta.get("ideal_chemistry", ""),
                "locked_test_id": t_id,
                "locked_test_mineral": t_meta.get("mineral_name", ""),
                "locked_test_ideal_chemistry": t_meta.get("ideal_chemistry", ""),
            }
        )

    same_class_values = corr[same_class]
    return {
        "grid_points": int(next(iter(lengths))),
        "cross_split_pair_count": int(corr.size),
        "maximum_pearson": float(corr.max()),
        "maximum_same_class_pearson": (
            float(same_class_values.max()) if same_class_values.size else None
        ),
        "thresholds": threshold_stats,
        "top_pairs": top_pairs,
    }


def build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# RRUFF-301 Composition Audit",
        "",
        "> 这是对现有本地 RRUFF-301 数据库的**只读描述性检查**，不是新的实验 Gate。",
        "> 不改变 adaptation/test split，不删除样本，不读取模型预测，也不改变已经报告的 few-shot 结果。",
        "",
        "## 1. Split integrity",
        "",
        f"- adaptation pool: **{summary['counts']['adaptation_pool']}**",
        f"- locked test: **{summary['counts']['locked_test']}**",
        f"- unique RRUFF IDs: **{summary['counts']['unique_rruff_ids']}**",
        f"- exact RRUFF-ID overlap: **{summary['id_overlap_count']}**",
        f"- exact spectrum-SHA overlap: **{summary['spectrum_sha_overlap_count']}**",
        "",
        "## 2. Metadata overlap",
        "",
        "| 字段 | 共享唯一值 | adaptation 中涉及样本 | locked test 中涉及样本 | 跨 split 配对数 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("mineral_name", "ideal_chemistry", "measured_chemistry", "space_group"):
        item = summary["metadata_overlap"][name]
        lines.append(
            f"| `{name}` | {item['overlapping_unique_values']} | "
            f"{item['adaptation_samples_in_overlap']} | "
            f"{item['locked_test_samples_in_overlap']} | "
            f"{item['cross_split_pair_count']} |"
        )

    mineral = summary["metadata_overlap"]["mineral_name"]
    if mineral["details"]:
        lines.extend(["", "### 共享 mineral name", ""])
        for item in mineral["details"]:
            lines.append(
                f"- **{item['display_value']}** — adaptation: "
                f"{', '.join(item['adaptation_ids'])}; locked test: "
                f"{', '.join(item['locked_test_ids'])}"
            )

    spectral = summary.get("spectral_overlap")
    if spectral is not None:
        lines.extend(
            [
                "",
                "## 3. Stored-spectrum similarity",
                "",
                f"- cross-split pairs: **{spectral['cross_split_pair_count']}**",
                f"- maximum Pearson correlation: **{spectral['maximum_pearson']:.6f}**",
                f"- maximum same-crystal-system Pearson: **{spectral['maximum_same_class_pearson']:.6f}**",
                "",
                "| 阈值 | 全部跨 split pairs | 同晶系 pairs | adaptation 样本有匹配 | test 样本有匹配 |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for threshold in CORRELATION_THRESHOLDS:
            item = spectral["thresholds"][f"ge_{threshold}"]
            lines.append(
                f"| ≥ {threshold} | {item['all_cross_split_pairs']} | "
                f"{item['same_class_pairs']} | "
                f"{item['adaptation_samples_with_any_match']} | "
                f"{item['locked_test_samples_with_any_match']} |"
            )

        lines.extend(
            [
                "",
                "### 最高相关的跨 split 谱图对",
                "",
                "| Pearson | 同晶系 | adaptation | mineral | locked test | mineral |",
                "|---:|:---:|---|---|---|---|",
            ]
        )
        for pair in spectral["top_pairs"]:
            lines.append(
                f"| {pair['pearson']:.6f} | "
                f"{'yes' if pair['same_crystal_system'] else 'no'} | "
                f"{pair['adaptation_id']} | {pair['adaptation_mineral']} | "
                f"{pair['locked_test_id']} | {pair['locked_test_mineral']} |"
            )

    lines.extend(
        [
            "",
            "## 4. Interpretation boundary",
            "",
            "- 相同 mineral name / chemistry string 的存在**不等于数据泄漏**；RRUFF-301 的任务是同一实验域内的 few-shot adaptation，而不是 unseen-mineral benchmark。",
            "- `ideal_chemistry` / `measured_chemistry` 这里只做规范化后的**精确字符串比较**，不是化学式约简、原型识别或结构等价判定。",
            "- Pearson correlation 只检查已经存储的一维规范化谱图是否近似重复，不是结构同构性证明。",
            "- 本报告的用途是把数据组成讲清楚；无论结果如何，都不事后修改 frozen split 或重跑模型。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, default=DEFAULT_MASTER)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--output-prefix", type=Path, default=DEFAULT_OUTPUT_PREFIX)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument(
        "--skip-spectra",
        action="store_true",
        help="Only audit IDs/metadata/hashes; do not load spectrum CSV files.",
    )
    args = parser.parse_args()

    master_rows = read_csv(args.master.resolve(), REQUIRED_MASTER_COLUMNS)
    split_rows = read_csv(args.split.resolve(), REQUIRED_SPLIT_COLUMNS)

    if len(split_rows) != 301:
        raise ValueError(f"expected 301 split rows, got {len(split_rows)}")
    split_ids = [row["rruff_id"] for row in split_rows]
    if len(set(split_ids)) != 301:
        raise ValueError("RRUFF-301 split contains duplicate or empty IDs")

    master_by_id = {row["rruff_id"]: row for row in master_rows}
    missing_ids = sorted(set(split_ids) - set(master_by_id))
    if missing_ids:
        raise ValueError(f"split IDs missing from master manifest: {missing_ids[:10]}")

    rows_by_role = {
        role: [row for row in split_rows if row["split"] == role] for role in ROLES
    }
    unexpected_roles = sorted(set(row["split"] for row in split_rows) - set(ROLES))
    if unexpected_roles:
        raise ValueError(f"unexpected split roles: {unexpected_roles}")
    if len(rows_by_role["adaptation_pool"]) != 70:
        raise ValueError("adaptation_pool must contain 70 samples")
    if len(rows_by_role["locked_test"]) != 231:
        raise ValueError("locked_test must contain 231 samples")

    adaptation_ids = {row["rruff_id"] for row in rows_by_role["adaptation_pool"]}
    test_ids = {row["rruff_id"] for row in rows_by_role["locked_test"]}
    id_overlap = sorted(adaptation_ids & test_ids)

    adaptation_hashes = {
        master_by_id[sample_id]["spectrum_sha256"].upper()
        for sample_id in adaptation_ids
        if master_by_id[sample_id]["spectrum_sha256"]
    }
    test_hashes = {
        master_by_id[sample_id]["spectrum_sha256"].upper()
        for sample_id in test_ids
        if master_by_id[sample_id]["spectrum_sha256"]
    }
    sha_overlap = sorted(adaptation_hashes & test_hashes)

    metadata_overlap = {
        "mineral_name": overlap_summary(
            rows_by_role["adaptation_pool"],
            rows_by_role["locked_test"],
            master_by_id,
            "mineral_name",
            normalize_text,
        ),
        "ideal_chemistry": overlap_summary(
            rows_by_role["adaptation_pool"],
            rows_by_role["locked_test"],
            master_by_id,
            "ideal_chemistry",
            normalize_formula_string,
        ),
        "measured_chemistry": overlap_summary(
            rows_by_role["adaptation_pool"],
            rows_by_role["locked_test"],
            master_by_id,
            "measured_chemistry",
            normalize_formula_string,
        ),
        "space_group": overlap_summary(
            rows_by_role["adaptation_pool"],
            rows_by_role["locked_test"],
            master_by_id,
            "space_group",
            normalize_space_group,
        ),
    }

    summary: dict[str, Any] = {
        "schema_version": "rruff301-composition-audit-v1",
        "purpose": "read_only_descriptive_composition_audit_not_a_gate",
        "source_files": {
            "master_manifest": str(args.master.resolve()),
            "split": str(args.split.resolve()),
        },
        "counts": {
            "adaptation_pool": len(rows_by_role["adaptation_pool"]),
            "locked_test": len(rows_by_role["locked_test"]),
            "unique_rruff_ids": len(set(split_ids)),
        },
        "id_overlap_count": len(id_overlap),
        "id_overlap": id_overlap,
        "spectrum_sha_overlap_count": len(sha_overlap),
        "spectrum_sha_overlap": sha_overlap,
        "metadata_overlap": metadata_overlap,
        "interpretation": {
            "not_a_gate": True,
            "no_split_changes": True,
            "no_model_outputs_used": True,
            "mineral_or_formula_overlap_does_not_invalidate_fewshot_claim": True,
        },
    }

    if not args.skip_spectra:
        dataset_root = args.master.resolve().parent.parent
        summary["spectral_overlap"] = spectral_overlap(
            rows_by_role["adaptation_pool"],
            rows_by_role["locked_test"],
            master_by_id,
            dataset_root,
            top_n=args.top_n,
        )

    prefix = args.output_prefix.resolve()
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    md_path.write_text(build_report(summary), encoding="utf-8")

    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    print(
        "mineral-name overlap: "
        f"{metadata_overlap['mineral_name']['overlapping_unique_values']} shared names; "
        f"{metadata_overlap['mineral_name']['locked_test_samples_in_overlap']} test samples involved"
    )
    if summary.get("spectral_overlap"):
        print(
            "maximum cross-split Pearson: "
            f"{summary['spectral_overlap']['maximum_pearson']:.6f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
