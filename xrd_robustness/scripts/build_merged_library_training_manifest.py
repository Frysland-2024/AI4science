#!/usr/bin/env python3
"""Build the ResNet runner manifest from merged-library shards and V7 caches.

This emits only train and validation records. The held-out test shard is never
added to the training runner manifest.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.structure_data import CRYSTAL_SYSTEMS


def _resolve(path: str | Path, base: Path) -> Path:
    value = Path(path)
    if not value.is_absolute():
        value = base / value
    return value.resolve()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl_rows(path: Path):
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{line_number} must contain a JSON object")
                yield line_number, row


def _load_cache_index(
    split_root: Path,
    *,
    cache_name: str,
    manifest_name: str,
    summary_name: str,
    split: str,
    expected_count: int,
) -> dict[str, dict[str, str]]:
    manifest_path = split_root / "manifests" / manifest_name
    summary_path = split_root / "manifests" / summary_name
    if not manifest_path.is_file() or not summary_path.is_file():
        raise ValueError(f"{split} cache manifest/summary is missing under {split_root}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "completed":
        raise ValueError(f"{split} cache is not complete: {summary.get('status')}")
    if summary.get("cache_name") != cache_name:
        raise ValueError(f"{split} cache summary names a different cache")
    if int(summary.get("source_record_count", -1)) != expected_count:
        raise ValueError(
            f"{split} cache source count {summary.get('source_record_count')} "
            f"does not match shard count {expected_count}"
        )
    if int(summary.get("completed_count", -1)) != expected_count:
        raise ValueError(f"{split} cache completed count does not match shard count")
    if int(summary.get("skipped_count", -1)) != 0:
        raise ValueError(f"{split} cache reports skipped records")
    declared_manifest_sha = str(summary.get("manifest_sha256", ""))
    if declared_manifest_sha and _sha256(manifest_path) != declared_manifest_sha:
        raise ValueError(f"{split} cache manifest SHA256 does not match its summary")

    indexed: dict[str, dict[str, str]] = {}
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"material_id", "structure_fingerprint", "bytes", "sha256"}
        if not required.issubset(set(reader.fieldnames or ())):
            raise ValueError(f"{split} cache manifest is missing required columns")
        for row in reader:
            material_id = str(row["material_id"])
            if material_id in indexed:
                raise ValueError(f"{split} cache manifest duplicates {material_id}")
            indexed[material_id] = row
    if len(indexed) != expected_count:
        raise ValueError(
            f"{split} cache manifest has {len(indexed)} rows; expected {expected_count}"
        )
    return indexed


def _read_split_metadata(path: Path, split: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, row in _jsonl_rows(path):
        material_id = str(row.get("material_id", "")).strip()
        row_split = str(row.get("split", "")).strip()
        crystal_system = str(row.get("crystal_system", "")).strip()
        fingerprint = str(
            row.get("structure_fingerprint")
            or row.get("source_structure_fingerprint")
            or ""
        ).strip()
        parent_id = str(row.get("parent_structure_id", "")).strip()
        if not material_id or material_id in seen:
            raise ValueError(f"{path}:{line_number} has an empty or duplicate material_id")
        if row_split != split:
            raise ValueError(
                f"{path}:{line_number} declares split={row_split!r}; expected {split!r}"
            )
        if crystal_system not in CRYSTAL_SYSTEMS:
            raise ValueError(f"{path}:{line_number} has unknown crystal_system")
        if not fingerprint or not parent_id:
            raise ValueError(
                f"{path}:{line_number} requires structure fingerprint and parent_structure_id"
            )
        rows.append(
            {
                "material_id": material_id,
                "split": split,
                "crystal_system": crystal_system,
                "label": CRYSTAL_SYSTEMS.index(crystal_system),
                "structure_fingerprint": fingerprint,
                "parent_structure_id": parent_id,
            }
        )
        seen.add(material_id)
    if not rows:
        raise ValueError(f"{path} contains no records")
    rows.sort(key=lambda row: row["material_id"])
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir", required=True,
        help="directory containing the three gzipped split shards",
    )
    parser.add_argument(
        "--cache-root", required=True,
        help="root with train/validation/test cache roots",
    )
    parser.add_argument("--cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--manifest-name", default="peak_cache_manifest.v7.reflection.csv")
    parser.add_argument("--summary-name", default="peak_cache_summary.v7.reflection.json")
    parser.add_argument(
        "--output",
        help="runner JSONL path; defaults to <cache-root>/training_records.v1.jsonl",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if Path(args.cache_name).name != args.cache_name:
        raise SystemExit("--cache-name must be one directory name")

    source_dir = _resolve(args.source_dir, PROJECT_ROOT)
    cache_root = _resolve(args.cache_root, PROJECT_ROOT)
    output_path = (
        _resolve(args.output, PROJECT_ROOT)
        if args.output
        else cache_root / "training_records.v1.jsonl"
    )
    if not source_dir.is_dir():
        raise SystemExit(f"source directory is missing: {source_dir}")
    try:
        output_path.relative_to(cache_root)
    except ValueError as error:
        raise SystemExit("output must be inside --cache-root for portable relative cache paths") from error

    summary_path = output_path.with_suffix(".summary.json")
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_summary_path = summary_path.with_suffix(summary_path.suffix + ".tmp")
    occupied = [path for path in (output_path, summary_path, temp_path, temp_summary_path) if path.exists()]
    if occupied and not args.overwrite:
        raise SystemExit("refusing to overwrite existing manifest artifacts: " + ", ".join(map(str, occupied)))
    if temp_path.exists() or temp_summary_path.exists():
        raise SystemExit("temporary manifest artifact exists; inspect it before resuming")

    rows_by_split: dict[str, list[dict[str, Any]]] = {}
    source_paths: dict[str, Path] = {}
    seen_ids: set[str] = set()
    parent_splits: dict[str, str] = {}
    for split in ("train", "validation", "test"):
        source_path = source_dir / f"{split}_structures.jsonl.gz"
        if not source_path.is_file():
            raise SystemExit(f"source shard is missing: {source_path}")
        rows = _read_split_metadata(source_path, split)
        duplicate = seen_ids.intersection(row["material_id"] for row in rows)
        if duplicate:
            raise SystemExit(f"material IDs occur in multiple splits: {sorted(duplicate)[:3]}")
        seen_ids.update(row["material_id"] for row in rows)
        for row in rows:
            parent_id = row["parent_structure_id"]
            prior_split = parent_splits.get(parent_id)
            if prior_split is not None and prior_split != split:
                raise SystemExit(
                    f"parent {parent_id} leaks across {prior_split} and {split}"
                )
            parent_splits[parent_id] = split
        rows_by_split[split] = rows
        source_paths[split] = source_path

    cache_indexes: dict[str, dict[str, dict[str, str]]] = {}
    cache_manifest_paths: dict[str, Path] = {}
    for split in ("train", "validation"):
        rows = rows_by_split[split]
        split_root = cache_root / split
        cache_index = _load_cache_index(
            split_root,
            cache_name=args.cache_name,
            manifest_name=args.manifest_name,
            summary_name=args.summary_name,
            split=split,
            expected_count=len(rows),
        )
        source_ids = {row["material_id"] for row in rows}
        cache_ids = set(cache_index)
        if source_ids != cache_ids:
            raise ValueError(
                f"{split} cache ID set differs from source shard "
                f"(missing={len(source_ids - cache_ids)}, extra={len(cache_ids - source_ids)})"
            )
        cache_dir = split_root / "mp_processed" / args.cache_name
        for row in rows:
            material_id = row["material_id"]
            cache_row = cache_index[material_id]
            if str(cache_row["structure_fingerprint"]) != row["structure_fingerprint"]:
                raise ValueError(f"{split} fingerprint mismatch for {material_id}")
            cache_path = cache_dir / f"{material_id}.npz"
            if not cache_path.is_file():
                raise ValueError(f"{split} peak table is missing: {cache_path}")
            if cache_path.stat().st_size != int(cache_row["bytes"]):
                raise ValueError(f"{split} peak table byte count mismatch: {material_id}")
            if _sha256(cache_path).lower() != str(cache_row["sha256"]).lower():
                raise ValueError(f"{split} peak table SHA256 mismatch: {material_id}")
            row["peak_table_path"] = cache_path.relative_to(cache_root).as_posix()
        cache_indexes[split] = cache_index
        cache_manifest_paths[split] = split_root / "manifests" / args.manifest_name

    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_rows = rows_by_split["train"] + rows_by_split["validation"]
    all_rows.sort(key=lambda row: (row["split"], row["material_id"]))
    _write_jsonl(temp_path, all_rows)
    class_counts = {
        split: {
            crystal_system: sum(row["crystal_system"] == crystal_system for row in rows)
            for crystal_system in CRYSTAL_SYSTEMS
        }
        for split, rows in rows_by_split.items()
    }
    summary = {
        "schema_version": "xrd-resnet-training-v1",
        "status": "completed",
        "output_manifest": output_path.relative_to(cache_root).as_posix(),
        "output_manifest_sha256": _sha256(temp_path),
        "cache_name": args.cache_name,
        "source_shards": {
            split: {
                "path": path.name,
                "sha256": _sha256(path),
                "rows": len(rows_by_split[split]),
            }
            for split, path in source_paths.items()
        },
        "peak_cache_manifests": {
            split: {
                "path": path.relative_to(cache_root).as_posix(),
                "sha256": _sha256(path),
                "rows": len(cache_indexes[split]),
            }
            for split, path in cache_manifest_paths.items()
        },
        "record_counts": {split: len(rows) for split, rows in rows_by_split.items()},
        "class_counts": class_counts,
        "test_split_included": False,
        "path_encoding": "relative to this manifest so the cache-root can move as a unit",
    }
    temp_summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temp_path, output_path)
    os.replace(temp_summary_path, summary_path)
    print(
        json.dumps(
            {
                "status": summary["status"],
                "training_records": len(all_rows),
                "train": len(rows_by_split["train"]),
                "validation": len(rows_by_split["validation"]),
                "test_included": False,
                "manifest": output_path.relative_to(cache_root).as_posix(),
                "sha256": summary["output_manifest_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
