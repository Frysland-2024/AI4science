#!/usr/bin/env python3
"""Audit what the frozen formal split does and does not isolate.

The active split is defined at exact parent-structure fingerprint level.  This
script verifies that contract and separately reports exact-formula overlap. It
does not resplit data and does not infer unrecorded prototype or chemical-family
membership.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS = ROOT / "data/formal_14060/mp_processed/structure_records.jsonl"
DEFAULT_SPLIT = ROOT / "data/formal_14060/manifests/split_manifest.json"
DEFAULT_OUTPUT = ROOT / "reports/v9_formal_split_identity_overlap_audit.json"
SPLITS = ("train", "validation", "test")


class SplitIdentityAuditError(ValueError):
    """Raised when source records and the frozen split cannot be reconciled."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def audit_identity_overlap(
    structure_records: list[dict[str, Any]],
    split_records: list[dict[str, Any]],
    *,
    example_limit: int = 20,
) -> dict[str, Any]:
    if not structure_records or not split_records:
        raise SplitIdentityAuditError("structure and split records must be non-empty")

    by_material: dict[str, dict[str, Any]] = {}
    for row in structure_records:
        material_id = str(row.get("material_id", "")).strip()
        if not material_id or material_id in by_material:
            raise SplitIdentityAuditError(
                f"missing or duplicate structure material_id: {material_id!r}"
            )
        by_material[material_id] = row

    split_by_material: dict[str, dict[str, Any]] = {}
    for row in split_records:
        material_id = str(row.get("material_id", "")).strip()
        split = str(row.get("split", "")).strip()
        if not material_id or material_id in split_by_material or split not in SPLITS:
            raise SplitIdentityAuditError(
                f"invalid or duplicate split row for material_id: {material_id!r}"
            )
        split_by_material[material_id] = row
    if set(by_material) != set(split_by_material):
        raise SplitIdentityAuditError("structure records and split manifest IDs differ")

    parent_splits: dict[str, set[str]] = defaultdict(set)
    formula_splits: dict[str, set[str]] = defaultdict(set)
    formula_materials: dict[str, list[str]] = defaultdict(list)
    split_counts: Counter[str] = Counter()
    formula_counts_by_split: dict[str, Counter[str]] = {
        split: Counter() for split in SPLITS
    }
    for material_id, record in by_material.items():
        split_row = split_by_material[material_id]
        split = str(split_row["split"])
        parent = str(split_row.get("parent_structure_id", "")).strip()
        fingerprint = str(record.get("structure_fingerprint", "")).strip()
        formula = str(record.get("formula", "")).strip()
        if not parent or not fingerprint or parent != fingerprint:
            raise SplitIdentityAuditError(
                f"parent fingerprint mismatch for {material_id}"
            )
        if not formula:
            raise SplitIdentityAuditError(f"missing formula for {material_id}")
        parent_splits[parent].add(split)
        formula_splits[formula].add(split)
        formula_materials[formula].append(material_id)
        formula_counts_by_split[split][formula] += 1
        split_counts[split] += 1

    crossing_parents = {
        parent: sorted(splits)
        for parent, splits in parent_splits.items()
        if len(splits) > 1
    }
    crossing_formulas = {
        formula: sorted(splits)
        for formula, splits in formula_splits.items()
        if len(splits) > 1
    }
    three_way = sorted(
        formula for formula, splits in formula_splits.items() if len(splits) == 3
    )
    crossing_material_ids = {
        material_id
        for formula in crossing_formulas
        for material_id in formula_materials[formula]
    }
    examples = []
    for formula in sorted(
        crossing_formulas,
        key=lambda value: (-len(formula_materials[value]), value),
    )[:example_limit]:
        examples.append(
            {
                "formula": formula,
                "splits": crossing_formulas[formula],
                "material_count": len(formula_materials[formula]),
                "counts_by_split": {
                    split: formula_counts_by_split[split][formula]
                    for split in SPLITS
                    if formula_counts_by_split[split][formula]
                },
                "material_ids": sorted(formula_materials[formula]),
            }
        )

    exact_parent_disjoint = not crossing_parents
    exact_formula_disjoint = not crossing_formulas
    return {
        "schema_version": "v9-formal-split-identity-overlap-audit-v1",
        "status": "pass" if exact_parent_disjoint else "fail_parent_leakage",
        "material_count": len(by_material),
        "split_counts": {split: split_counts[split] for split in SPLITS},
        "unique_parent_structure_count": len(parent_splits),
        "cross_split_parent_structure_count": len(crossing_parents),
        "exact_parent_structure_disjoint": exact_parent_disjoint,
        "unique_exact_formula_count": len(formula_splits),
        "cross_split_exact_formula_count": len(crossing_formulas),
        "cross_split_exact_formula_material_count": len(crossing_material_ids),
        "three_way_exact_formula_count": len(three_way),
        "three_way_exact_formulas": three_way,
        "exact_formula_disjoint": exact_formula_disjoint,
        "cross_split_exact_formula_examples": examples,
        "scope": {
            "established": "exact parent-structure fingerprints do not cross splits",
            "not_established": [
                "exact-formula-disjoint evaluation",
                "chemical-family-disjoint evaluation",
                "structure-prototype-disjoint evaluation",
                "symmetry-equivalence-disjoint evaluation",
            ],
            "strict_chemical_family_or_prototype_ood": False,
            "reason": (
                "the frozen manifest contains exact-cell fingerprints but no frozen "
                "chemical-family, prototype, or symmetry-equivalence group IDs"
            ),
        },
    }


def load_and_audit(records_path: str | Path, split_path: str | Path) -> dict[str, Any]:
    records_source = Path(records_path).resolve()
    split_source = Path(split_path).resolve()
    structure_records = [
        json.loads(line)
        for line in records_source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    split_payload = json.loads(split_source.read_text(encoding="utf-8"))
    split_records = split_payload.get("records")
    if not isinstance(split_records, list):
        raise SplitIdentityAuditError("split manifest has no records array")
    report = audit_identity_overlap(structure_records, split_records)
    report.update(
        {
            "structure_records_path": _display_path(records_source),
            "structure_records_sha256": sha256(records_source),
            "split_manifest_path": _display_path(split_source),
            "split_manifest_sha256": sha256(split_source),
            "frozen_split_modified": False,
        }
    )
    return report


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--split", default=str(DEFAULT_SPLIT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        report = load_and_audit(args.records, args.split)
    except (OSError, json.JSONDecodeError, SplitIdentityAuditError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
        return 1
    if not args.check_only:
        write_json_atomic(Path(args.output).resolve(), report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "cross_split_parent_structure_count": report[
                    "cross_split_parent_structure_count"
                ],
                "cross_split_exact_formula_count": report[
                    "cross_split_exact_formula_count"
                ],
                "cross_split_exact_formula_material_count": report[
                    "cross_split_exact_formula_material_count"
                ],
                "three_way_exact_formula_count": report[
                    "three_way_exact_formula_count"
                ],
                "output": None if args.check_only else str(Path(args.output).resolve()),
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
