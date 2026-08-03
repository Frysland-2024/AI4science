#!/usr/bin/env python3
"""Audit that an expanded RRUFF manifest preserves its frozen parent collection.

This audit is deliberately model-blind. It reads manifest metadata and hashes only;
it does not import the training stack, load checkpoints, or run XRD inference.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


CLASS_ORDER = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "rruff_id",
        "mineral_name",
        "crystal_system",
        "dataset_role",
        "spectrum_sha256",
        "raw_member_sha256",
        "dif_member_sha256",
    }
    missing = sorted(required.difference(rows[0] if rows else {}))
    if missing:
        raise ValueError(f"manifest missing required columns: {missing}")
    return rows


def normalized_mineral(value: str) -> str:
    return " ".join(value.casefold().split())


def build_report(
    parent_path: Path,
    expanded_path: Path,
    *,
    expected_added_per_class: int,
) -> dict[str, Any]:
    parent_rows = read_manifest(parent_path)
    expanded_rows = read_manifest(expanded_path)
    parent_by_id = {row["rruff_id"]: row for row in parent_rows}
    expanded_by_id = {row["rruff_id"]: row for row in expanded_rows}

    duplicate_parent_ids = len(parent_rows) - len(parent_by_id)
    duplicate_expanded_ids = len(expanded_rows) - len(expanded_by_id)
    missing_parent_ids = sorted(set(parent_by_id).difference(expanded_by_id))
    shared_ids = sorted(set(parent_by_id).intersection(expanded_by_id))
    hash_fields = (
        "spectrum_sha256",
        "raw_member_sha256",
        "dif_member_sha256",
    )
    hash_mismatches = {
        field: [
            rruff_id
            for rruff_id in shared_ids
            if parent_by_id[rruff_id][field] != expanded_by_id[rruff_id][field]
        ]
        for field in hash_fields
    }

    added_ids = sorted(set(expanded_by_id).difference(parent_by_id))
    added_rows = [expanded_by_id[rruff_id] for rruff_id in added_ids]
    added_class_counts = Counter(row["crystal_system"] for row in added_rows)
    expanded_class_counts = Counter(row["crystal_system"] for row in expanded_rows)
    role_counts = Counter(row["dataset_role"] for row in expanded_rows)

    legacy_rows = [
        row for row in expanded_rows if row["dataset_role"] == "legacy_rruff70"
    ]
    extension_rows = [
        row for row in expanded_rows if row["dataset_role"] != "legacy_rruff70"
    ]
    legacy_minerals = {normalized_mineral(row["mineral_name"]) for row in legacy_rows}
    overlapping_extension_rows = [
        row
        for row in extension_rows
        if normalized_mineral(row["mineral_name"]) in legacy_minerals
    ]
    overlapping_names = sorted(
        {row["mineral_name"] for row in overlapping_extension_rows}, key=str.casefold
    )
    overlap_by_class = Counter(
        row["crystal_system"] for row in overlapping_extension_rows
    )

    expected_classes = set(CLASS_ORDER)
    status = "pass"
    if (
        duplicate_parent_ids
        or duplicate_expanded_ids
        or missing_parent_ids
        or any(hash_mismatches.values())
        or set(added_class_counts) != expected_classes
        or set(added_class_counts.values()) != {expected_added_per_class}
        or set(expanded_class_counts) != expected_classes
        or len(legacy_rows) != 70
    ):
        status = "fail"

    return {
        "schema_version": "rruff-collection-expansion-audit-v1",
        "status": status,
        "parent": {
            "manifest": str(parent_path.resolve()),
            "manifest_sha256": sha256_file(parent_path),
            "sample_count": len(parent_rows),
            "duplicate_rruff_ids": duplicate_parent_ids,
        },
        "expanded": {
            "manifest": str(expanded_path.resolve()),
            "manifest_sha256": sha256_file(expanded_path),
            "sample_count": len(expanded_rows),
            "duplicate_rruff_ids": duplicate_expanded_ids,
            "class_counts": dict(sorted(expanded_class_counts.items())),
            "role_counts": dict(sorted(role_counts.items())),
        },
        "inheritance": {
            "missing_parent_ids": missing_parent_ids,
            "shared_sample_count": len(shared_ids),
            "hash_mismatches": hash_mismatches,
            "all_parent_hashes_preserved": (
                not missing_parent_ids and not any(hash_mismatches.values())
            ),
        },
        "addition": {
            "sample_count": len(added_rows),
            "expected_per_class": expected_added_per_class,
            "class_counts": dict(sorted(added_class_counts.items())),
            "samples": [
                {
                    "rruff_id": row["rruff_id"],
                    "mineral_name": row["mineral_name"],
                    "crystal_system": row["crystal_system"],
                }
                for row in sorted(
                    added_rows,
                    key=lambda row: (
                        CLASS_ORDER.index(row["crystal_system"]),
                        row["rruff_id"],
                    ),
                )
            ],
        },
        "development_test_group_overlap_audit": {
            "group_key": "normalized mineral_name",
            "legacy_sample_count": len(legacy_rows),
            "extension_sample_count": len(extension_rows),
            "overlapping_extension_sample_count": len(overlapping_extension_rows),
            "overlapping_unique_mineral_count": len(overlapping_names),
            "overlapping_extension_samples_by_class": dict(
                sorted(overlap_by_class.items())
            ),
            "overlapping_mineral_names": overlapping_names,
            "interpretation": (
                "The extension is a measurement-domain test, not an unseen-mineral "
                "test, unless a separately frozen group-disjoint sensitivity cohort "
                "is used."
            ),
        },
        "model_loaded": False,
        "model_outputs_used": False,
        "real_xrd_inference_run": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-manifest", type=Path, required=True)
    parser.add_argument("--expanded-manifest", type=Path, required=True)
    parser.add_argument("--expected-added-per-class", type=int, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.expected_added_per_class < 1:
        raise ValueError("expected-added-per-class must be positive")
    report = build_report(
        args.parent_manifest,
        args.expanded_manifest,
        expected_added_per_class=args.expected_added_per_class,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
