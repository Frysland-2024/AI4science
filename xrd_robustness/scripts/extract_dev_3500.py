#!/usr/bin/env python3
"""Extract the fixed, nested 3,500-structure development tier."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.structure_data import (
    PERSISTED_STRUCTURE_FIELDS,
    validate_no_split_leakage,
    validate_persisted_structure_record,
)

CRYSTAL_SYSTEMS = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)
TARGET_PER_SPLIT = {"train": 350, "validation": 75, "test": 75}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"manifest contains an absolute path: {value}")
    resolved = (PROJECT_ROOT / path).resolve()
    if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError(f"manifest path escapes project root: {value}")
    return resolved


def _rank(row: dict[str, Any], seed: int) -> str:
    payload = f"{seed}:{row['crystal_system']}:{row['split']}:{row['material_id']}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent-root", default=str(PROJECT_ROOT / "data" / "formal_14000"))
    parser.add_argument("--output-root", default=str(PROJECT_ROOT / "data" / "dev_3500"))
    parser.add_argument("--seed", type=int, default=20260711)
    args = parser.parse_args()
    parent_root = resolve_data_root(PROJECT_ROOT, args.parent_root)
    output_root = resolve_data_root(PROJECT_ROOT, args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty development root: {output_root}")
    records_path = parent_root / "mp_processed" / "structure_records.jsonl"
    parent_dataset_manifest = parent_root / "manifests" / "dataset_manifest.json"
    parent_peak_manifest = parent_root / "manifests" / "peak_cache_manifest.v7.reflection.csv"
    if not records_path.exists() or not parent_dataset_manifest.exists() or not parent_peak_manifest.exists():
        raise SystemExit("parent formal tier requires structure records, dataset manifest, and peak-cache manifest")
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    if len(records) != 14000:
        raise SystemExit(f"parent formal tier contains {len(records)} records, expected 14000")
    for row in records:
        validate_persisted_structure_record(row)
    validate_no_split_leakage(records)
    parent_by_system_split: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in records:
        parent_by_system_split.setdefault((row["crystal_system"], row["split"]), []).append(row)

    selected: list[dict[str, Any]] = []
    for system in CRYSTAL_SYSTEMS:
        for split, target in TARGET_PER_SPLIT.items():
            candidates = parent_by_system_split.get((system, split), [])
            if len(candidates) < target:
                raise SystemExit(f"parent tier lacks {target} {system}/{split} records")
            selected.extend(sorted(candidates, key=lambda row: _rank(row, args.seed))[:target])
    selected.sort(key=lambda row: (CRYSTAL_SYSTEMS.index(row["crystal_system"]), row["split"], row["material_id"]))
    if len(selected) != 3500:
        raise RuntimeError(f"selected {len(selected)} records, expected 3500")
    validate_no_split_leakage(selected)
    output_root.mkdir(parents=True, exist_ok=True)
    records_out = output_root / "mp_processed" / "structure_records.jsonl"
    records_out.parent.mkdir(parents=True, exist_ok=True)
    records_out.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in selected),
        encoding="utf-8",
    )
    overview_fields = [
        "material_id", "formula", "space_group_mp", "space_group_recomputed",
        "crystal_system", "nsites", "is_stable", "energy_above_hull",
        "selection_tier",
        "structure_fingerprint", "split",
    ]
    manifests = output_root / "manifests"
    _write_csv(manifests / "structure_manifest.csv", selected, overview_fields)
    _write_csv(
        manifests / "split_manifest.csv",
        selected,
        ["material_id", "structure_fingerprint", "crystal_system", "split"],
    )

    parent_peak_rows = {}
    with parent_peak_manifest.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            parent_peak_rows[row["material_id"]] = row
    copied_peak_rows = []
    selection_rows = []
    output_peak_dir = output_root / "mp_processed" / "peak_tables_v7_reflection"
    output_peak_dir.mkdir(parents=True, exist_ok=True)
    for row in selected:
        source_row = parent_peak_rows.get(row["material_id"])
        if source_row is None:
            raise SystemExit(f"missing parent peak table for {row['material_id']}")
        source = _project_path(source_row["file"])
        if not source.exists() or _sha256(source) != source_row["sha256"]:
            raise SystemExit(f"parent peak table is missing or hash-mismatched: {row['material_id']}")
        target = output_peak_dir / source.name
        shutil.copy2(source, target)
        copied_peak_rows.append({
            **source_row,
            "material_id": row["material_id"],
            "structure_fingerprint": row["structure_fingerprint"],
            "file": project_relative_path(PROJECT_ROOT, target),
            "sha256": _sha256(target),
        })
        selection_rows.append({
            "material_id": row["material_id"],
            "crystal_system": row["crystal_system"],
            "parent_split": row["split"],
            "selection_seed": args.seed,
            "parent_dataset_root": project_relative_path(PROJECT_ROOT, parent_root),
        })
    _write_csv(
        manifests / "peak_cache_manifest.v7.reflection.csv",
        copied_peak_rows,
        [
            "schema_version", "material_id", "structure_fingerprint", "file",
            "peak_count", "reflection_family_count", "array_fields", "sha256", "bytes",
        ],
    )
    _write_csv(
        manifests / "selection_manifest.csv",
        selection_rows,
        ["material_id", "crystal_system", "parent_split", "selection_seed", "parent_dataset_root"],
    )

    parent_manifest_hash = _sha256(parent_dataset_manifest)
    retrieval_manifest = {
        "source": "fixed nested subset of formal_14000",
        "dataset_root": project_relative_path(PROJECT_ROOT, output_root),
        "parent_dataset_root": project_relative_path(PROJECT_ROOT, parent_root),
        "parent_dataset_manifest_sha256": parent_manifest_hash,
        "selection_seed": args.seed,
        "split_ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "counts": {"retained": len(selected), "per_crystal_system": 500},
        "spectra_persisted": False,
    }
    _write_json(manifests / "retrieval_manifest.json", retrieval_manifest)
    dataset_manifest = {
        "schema_version": "dataset-manifest-v1",
        "status": "built",
        "tier": "dev_3500",
        "dataset_root": project_relative_path(PROJECT_ROOT, output_root),
        "parent_dataset_manifest": project_relative_path(PROJECT_ROOT, parent_dataset_manifest),
        "parent_dataset_manifest_sha256": parent_manifest_hash,
        "source": "fixed nested subset of formal_14000",
        "nested": True,
        "expected_size": 3500,
        "per_crystal_system": 500,
        "per_split_per_crystal_system": TARGET_PER_SPLIT,
        "selection_seed": args.seed,
        "split_ratios": {"train": 0.7, "validation": 0.15, "test": 0.15},
        "artifacts": {
            "records": project_relative_path(PROJECT_ROOT, records_out),
            "structure_manifest": project_relative_path(PROJECT_ROOT, manifests / "structure_manifest.csv"),
            "split_manifest": project_relative_path(PROJECT_ROOT, manifests / "split_manifest.csv"),
            "selection_manifest": project_relative_path(PROJECT_ROOT, manifests / "selection_manifest.csv"),
            "retrieval_manifest": project_relative_path(PROJECT_ROOT, manifests / "retrieval_manifest.json"),
            "peak_cache_manifest": project_relative_path(PROJECT_ROOT, manifests / "peak_cache_manifest.v7.reflection.csv"),
        },
        "spectra_persisted": False,
    }
    _write_json(manifests / "dataset_manifest.json", dataset_manifest)
    print(json.dumps({"status": "built", "dataset_root": project_relative_path(PROJECT_ROOT, output_root), "records": len(selected)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
