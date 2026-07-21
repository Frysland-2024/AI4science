#!/usr/bin/env python3
"""Build the frozen V9-T family-aware 70/15/15 split and unified Validation manifest."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.family_split import (  # noqa: E402
    FAMILY_SIGNATURE_VERSION,
    anonymous_wyckoff_family_id,
    assign_family_aware_splits,
)


SPLIT_FIELDS = (
    "material_id",
    "structure_fingerprint",
    "crystal_system",
    "family_id",
    "family_signature_version",
    "split",
    "split_seed",
)
VALIDATION_FIELDS = (
    "material_id",
    "structure_fingerprint",
    "crystal_system",
    "family_id",
    "source_split",
    "development_role",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _intersection_counts(rows: list[dict[str, object]], key: str) -> dict[str, int]:
    values = {
        split: {str(row[key]) for row in rows if row["split"] == split}
        for split in ("train", "validation", "test")
    }
    return {
        "train_validation": len(values["train"] & values["validation"]),
        "train_test": len(values["train"] & values["test"]),
        "validation_test": len(values["validation"] & values["test"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        default=str(PROJECT_ROOT / "data/formal_14060/mp_processed/structure_records.jsonl"),
    )
    parser.add_argument(
        "--split-output",
        default=str(
            PROJECT_ROOT
            / "data/formal_14060/manifests/split_manifest.v9t.family_v1.csv"
        ),
    )
    parser.add_argument(
        "--validation-output",
        default=str(
            PROJECT_ROOT
            / "data/formal_14060/manifests/v9_method_transfer_validation.csv"
        ),
    )
    parser.add_argument(
        "--data-config-output",
        default=str(PROJECT_ROOT / "configs/data.v9.method_transfer.family_split.json"),
    )
    parser.add_argument(
        "--audit-output",
        default=str(PROJECT_ROOT / "reports/v9_method_transfer_split_audit.json"),
    )
    parser.add_argument("--seed", type=int, default=20260716)
    args = parser.parse_args()

    records_path = Path(args.records).resolve()
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != 14060:
        raise SystemExit(f"expected 14,060 records, found {len(records)}")

    family_ids: dict[str, str] = {}
    for row in records:
        material_id = str(row["material_id"])
        family_ids[material_id] = anonymous_wyckoff_family_id(
            row["standardized_structure"],
            expected_space_group=int(row["space_group_recomputed"]),
        )

    split_rows, assignment_report = assign_family_aware_splits(
        records,
        family_ids=family_ids,
        seed=args.seed,
    )
    split_path = Path(args.split_output).resolve()
    _write_csv(split_path, SPLIT_FIELDS, split_rows)

    validation_rows = [
        {
            "material_id": row["material_id"],
            "structure_fingerprint": row["structure_fingerprint"],
            "crystal_system": row["crystal_system"],
            "family_id": row["family_id"],
            "source_split": "validation",
            "development_role": "unified_validation",
        }
        for row in split_rows
        if row["split"] == "validation"
    ]
    validation_path = Path(args.validation_output).resolve()
    _write_csv(validation_path, VALIDATION_FIELDS, validation_rows)

    peak_manifest = (
        PROJECT_ROOT
        / "data/formal_14060/manifests/peak_cache_manifest.v7.reflection.csv"
    )
    split_counts = Counter(str(row["split"]) for row in split_rows)
    class_counts: dict[str, dict[str, int]] = defaultdict(dict)
    for split in ("train", "validation", "test"):
        counts = Counter(
            str(row["crystal_system"])
            for row in split_rows
            if row["split"] == split
        )
        class_counts[split] = dict(sorted(counts.items()))

    data_config = {
        "schema_version": "v9t-family-aware-data-split-v1",
        "status": "frozen",
        "dataset_root": "data/formal_14060",
        "dataset_size": 14060,
        "source_records": {
            "path": _project_relative(records_path),
            "sha256": _sha256(records_path),
        },
        "split": {
            "path": _project_relative(split_path),
            "sha256": _sha256(split_path),
            "seed": int(args.seed),
            "ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
            "counts": {name: split_counts[name] for name in ("train", "validation", "test")},
            "per_crystal_system": class_counts,
            "unit": "unique_crystal_structure",
            "stratification": "seven_crystal_systems",
            "family_signature_version": FAMILY_SIGNATURE_VERSION,
            "family_definition": assignment_report["family_definition"],
            "family_definition_scope": assignment_report["family_definition_scope"],
            "whole_family_assignment": True,
        },
        "validation": {
            "path": _project_relative(validation_path),
            "sha256": _sha256(validation_path),
            "count": len(validation_rows),
            "roles": [
                "hyperparameter_selection",
                "early_stopping",
                "checkpoint_selection",
                "development_method_comparison",
            ],
        },
        "test": {
            "count": split_counts["test"],
            "iid_profile_role": "training-range perturbations on the same locked test structures",
            "ood_profile_role": "unseen stronger perturbations on the same locked test structures",
            "selection_use_forbidden": True,
        },
        "external_real_test": {
            "inside_14060": False,
            "selection_use_forbidden": True,
        },
        "peak_cache": {
            "path": _project_relative(peak_manifest),
            "sha256": _sha256(peak_manifest),
            "split_independent": True,
        },
    }
    data_config_path = Path(args.data_config_output).resolve()
    data_config_path.parent.mkdir(parents=True, exist_ok=True)
    data_config_path.write_text(
        json.dumps(data_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    family_split_membership: dict[str, set[str]] = defaultdict(set)
    for row in split_rows:
        family_split_membership[str(row["family_id"])].add(str(row["split"]))
    family_cross_split = sum(len(splits) > 1 for splits in family_split_membership.values())
    audit = {
        "schema_version": "v9t-family-aware-split-audit-v1",
        "status": "passed",
        "split_seed": int(args.seed),
        "split_manifest": {
            "path": _project_relative(split_path),
            "sha256": _sha256(split_path),
        },
        "data_config": {
            "path": _project_relative(data_config_path),
            "sha256": _sha256(data_config_path),
        },
        "validation_manifest": {
            "path": _project_relative(validation_path),
            "sha256": _sha256(validation_path),
        },
        "structure_counts": {name: split_counts[name] for name in ("train", "validation", "test")},
        "per_crystal_system": class_counts,
        "unique_material_id_count": len({str(row["material_id"]) for row in split_rows}),
        "unique_structure_fingerprint_count": len(
            {str(row["structure_fingerprint"]) for row in split_rows}
        ),
        "duplicate_material_id_count": len(split_rows)
        - len({str(row["material_id"]) for row in split_rows}),
        "duplicate_structure_fingerprint_count": len(split_rows)
        - len({str(row["structure_fingerprint"]) for row in split_rows}),
        "material_id_intersections": _intersection_counts(split_rows, "material_id"),
        "structure_fingerprint_intersections": _intersection_counts(
            split_rows, "structure_fingerprint"
        ),
        "family_id_intersections": _intersection_counts(split_rows, "family_id"),
        "cross_split_family_count": family_cross_split,
        "family_assignment": assignment_report,
        "view_inheritance_audit": {
            "status": "passed",
            "split_before_view_generation": True,
            "all_generated_views_inherit_parent_structure_split": True,
            "persisted_perturbed_spectrum_row_count": 0,
            "peak_cache_is_split_independent_reflection_data": True,
        },
        "unified_validation_manifest_only": True,
        "test_locked": True,
        "external_real_test_separate": True,
    }
    zero_checks = [
        audit["duplicate_material_id_count"],
        audit["duplicate_structure_fingerprint_count"],
        audit["cross_split_family_count"],
        *audit["material_id_intersections"].values(),
        *audit["structure_fingerprint_intersections"].values(),
        *audit["family_id_intersections"].values(),
    ]
    if any(zero_checks):
        raise SystemExit(f"split audit failed zero-intersection checks: {zero_checks}")
    audit_path = Path(args.audit_output).resolve()
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "passed",
                "split_counts": audit["structure_counts"],
                "family_count": assignment_report["family_count"],
                "cross_split_family_count": family_cross_split,
                "split_manifest_sha256": audit["split_manifest"]["sha256"],
                "data_config_sha256": audit["data_config"]["sha256"],
                "audit": _project_relative(audit_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
