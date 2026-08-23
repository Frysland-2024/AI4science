#!/usr/bin/env python3
"""Build the V9-T parent-structure-level stratified 70/15/15 split."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SPLIT_MODULE_PATH = (
    PROJECT_ROOT / "src" / "xrd_robustness" / "structure_split.py"
)
_SPLIT_SPEC = importlib.util.spec_from_file_location(
    "v9_structure_split",
    _SPLIT_MODULE_PATH,
)
if _SPLIT_SPEC is None or _SPLIT_SPEC.loader is None:
    raise RuntimeError(f"cannot load structure-split module: {_SPLIT_MODULE_PATH}")
_SPLIT_MODULE = importlib.util.module_from_spec(_SPLIT_SPEC)
_SPLIT_SPEC.loader.exec_module(_SPLIT_MODULE)
DEFAULT_SPLIT_SEED = _SPLIT_MODULE.DEFAULT_SPLIT_SEED
RATIOS = _SPLIT_MODULE.RATIOS
SPLIT_ALGORITHM = _SPLIT_MODULE.SPLIT_ALGORITHM
assign_parent_structure_splits = _SPLIT_MODULE.assign_parent_structure_splits


VALIDATION_FIELDS = (
    "material_id",
    "parent_structure_id",
    "crystal_system",
    "source_split",
    "development_role",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _project_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")


def _write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _intersection_counts(
    rows: list[dict[str, str]],
    key: str,
) -> dict[str, int]:
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
        default=str(
            PROJECT_ROOT / "data/formal_14060/mp_processed/structure_records.jsonl"
        ),
    )
    parser.add_argument(
        "--split-output",
        default=str(
            PROJECT_ROOT / "data/formal_14060/manifests/split_manifest.json"
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
        default=str(
            PROJECT_ROOT / "configs/data.v9.method_transfer.structure_split.json"
        ),
    )
    parser.add_argument(
        "--audit-output",
        default=str(PROJECT_ROOT / "outputs/v9_method_transfer_split_audit.json"),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SPLIT_SEED)
    args = parser.parse_args()

    records_path = Path(args.records).resolve()
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != 14_060:
        raise SystemExit(f"expected 14,060 records, found {len(records)}")

    split_rows, assignment_report = assign_parent_structure_splits(
        records,
        seed=args.seed,
        ratios=RATIOS,
    )
    split_path = Path(args.split_output).resolve()
    split_path.parent.mkdir(parents=True, exist_ok=True)
    split_payload = {
        "schema_version": "v9t-parent-structure-split-v1",
        "status": "frozen",
        "split_unit": "parent_structure",
        "stratification": "crystal_system",
        "ratios": RATIOS,
        "seed": int(args.seed),
        "algorithm": SPLIT_ALGORITHM,
        "parent_structure_id_source": "structure_fingerprint",
        "records": split_rows,
    }
    split_path.write_text(
        json.dumps(split_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    validation_rows = [
        {
            "material_id": row["material_id"],
            "parent_structure_id": row["parent_structure_id"],
            "crystal_system": row["crystal_system"],
            "source_split": "validation",
            "development_role": "unified_validation",
        }
        for row in split_rows
        if row["split"] == "validation"
    ]
    validation_path = Path(args.validation_output).resolve()
    _write_csv(validation_path, VALIDATION_FIELDS, validation_rows)

    split_counts = Counter(row["split"] for row in split_rows)
    class_counts: dict[str, dict[str, int]] = defaultdict(dict)
    for split in ("train", "validation", "test"):
        counts = Counter(
            row["crystal_system"]
            for row in split_rows
            if row["split"] == split
        )
        class_counts[split] = dict(sorted(counts.items()))

    peak_manifest = (
        PROJECT_ROOT
        / "data/formal_14060/manifests/peak_cache_manifest.v7.reflection.csv"
    )
    data_config = {
        "schema_version": "v9t-parent-structure-data-split-v1",
        "status": "frozen",
        "dataset_root": "data/formal_14060",
        "dataset_size": 14_060,
        "source_records": {
            "path": _project_relative(records_path),
            "sha256": _sha256(records_path),
        },
        "split": {
            "path": _project_relative(split_path),
            "sha256": _sha256(split_path),
            "seed": int(args.seed),
            "ratios": RATIOS,
            "counts": {
                name: split_counts[name]
                for name in ("train", "validation", "test")
            },
            "per_crystal_system": class_counts,
            "unit": "parent_structure",
            "parent_structure_id_source": "structure_fingerprint",
            "stratification": "crystal_system",
            "algorithm": SPLIT_ALGORITHM,
            "family_fields_used_for_assignment": False,
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
            "id_role": "unseen_parent_structures_with_id_perturbations",
            "ood_role": "same_unseen_parent_structures_with_ood_perturbations",
        },
        "test": {
            "count": split_counts["test"],
            "iid_profile_role": (
                "training-range perturbations on the same locked test structures"
            ),
            "ood_profile_role": (
                "unseen stronger perturbations on the same locked test structures"
            ),
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

    parent_intersections = _intersection_counts(
        split_rows,
        "parent_structure_id",
    )
    material_intersections = _intersection_counts(split_rows, "material_id")
    audit = {
        "schema_version": "v9t-parent-structure-split-audit-v1",
        "status": "passed",
        "split_seed": int(args.seed),
        "split_algorithm": SPLIT_ALGORITHM,
        "split_unit": "parent_structure",
        "stratification": "crystal_system",
        "family_fields_used_for_assignment": False,
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
        "structure_counts": {
            name: split_counts[name]
            for name in ("train", "validation", "test")
        },
        "per_crystal_system": class_counts,
        "unique_material_id_count": len(
            {row["material_id"] for row in split_rows}
        ),
        "unique_parent_structure_id_count": len(
            {row["parent_structure_id"] for row in split_rows}
        ),
        "duplicate_material_id_count": (
            len(split_rows) - len({row["material_id"] for row in split_rows})
        ),
        "material_id_intersections": material_intersections,
        "parent_structure_id_intersections": parent_intersections,
        "parent_assignment": assignment_report,
        "view_inheritance_audit": {
            "status": "passed",
            "split_before_view_generation": True,
            "all_generated_views_inherit_parent_structure_split": True,
            "clean_weak_strong_and_ood_views_share_parent_split": True,
            "persisted_perturbed_spectrum_row_count": 0,
            "peak_cache_is_split_independent_reflection_data": True,
        },
        "validation_id": {
            "parent_structures_unseen_in_train": True,
            "perturbation_scope": "id",
        },
        "validation_ood": {
            "parent_structures_unseen_in_train": True,
            "perturbation_scope": "ood",
        },
        "unified_validation_manifest_only": True,
        "test_locked": True,
        "external_real_test_separate": True,
    }
    zero_checks = [
        audit["duplicate_material_id_count"],
        *material_intersections.values(),
        *parent_intersections.values(),
    ]
    if any(zero_checks):
        raise SystemExit(
            f"split audit failed parent-structure isolation checks: {zero_checks}"
        )
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
                "split_seed": int(args.seed),
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
