#!/usr/bin/env python
"""Validate formal data provenance and freeze deterministic nested parent IDs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.parent_budget_efficiency import (  # noqa: E402
    BUDGETS,
    SELECTION_SEED,
    PROTOCOL_VERSION,
    budget_prefixes,
    build_nested_parent_order,
    canonical_json_bytes,
    identity_hash,
    load_source_record_index,
    load_split_rows,
    sha256_bytes,
    sha256_file,
    validate_parent_split,
    verify_source_against_split,
    write_ranked_csv,
)


def _write_immutable(path: Path, content: bytes) -> None:
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"refusing to replace frozen manifest: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_bytes(content)
    temporary.replace(path)


def _verify_cache(data_root: Path, expected_manifest_hash: str) -> dict[str, Any]:
    path = data_root / "manifests" / "peak_cache_manifest.v7.reflection.csv"
    actual_manifest_hash = sha256_file(path)
    if actual_manifest_hash != expected_manifest_hash:
        raise ValueError("peak cache manifest SHA-256 differs from frozen data config")
    total_bytes = 0
    checked = 0
    with path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            material_id = str(row["material_id"])
            target = data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{material_id}.npz"
            if not target.is_file() or target.stat().st_size != int(row["bytes"]):
                raise FileNotFoundError(f"missing or size-mismatched peak table: {target}")
            if sha256_file(target) != str(row["sha256"]).upper():
                raise ValueError(f"peak table SHA-256 mismatch: {material_id}")
            total_bytes += target.stat().st_size
            checked += 1
    if checked != 14060:
        raise ValueError(f"expected 14,060 peak tables; verified {checked}")
    return {"manifest_sha256": actual_manifest_hash, "verified_files": checked, "bytes": total_bytes}


def freeze(data_root: Path, output_dir: Path) -> dict[str, Any]:
    config_path = PROJECT_ROOT / "configs" / "data.method_transfer.structure_split.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_path = data_root / config["source_records"]["path"].split("data/formal_14060/", 1)[-1]
    split_path = data_root / config["split"]["path"].split("data/formal_14060/", 1)[-1]
    source_hash = sha256_file(source_path)
    split_hash = sha256_file(split_path)
    if source_hash != config["source_records"]["sha256"].upper():
        raise ValueError("structure_records.jsonl SHA-256 differs from frozen data config")
    if split_hash != config["split"]["sha256"].upper():
        raise ValueError("split manifest SHA-256 differs from frozen data config")
    cache = _verify_cache(data_root, config["peak_cache"]["sha256"].upper())

    split_rows = load_split_rows(data_root)
    split_index = validate_parent_split(split_rows)
    source_index = load_source_record_index(data_root)
    source_split_audit = verify_source_against_split(split_rows, source_index)
    source_split_audit["source_split_cross_tab"] = {
        f"{source_split}_to_{frozen_split}": count
        for (source_split, frozen_split), count in sorted(
            Counter(
                (str(source_index[str(row["material_id"])]["split"]), str(row["split"]))
                for row in split_rows
            ).items()
        )
    }
    ranked, quotas = build_nested_parent_order(split_rows, selection_seed=SELECTION_SEED)
    prefixes = budget_prefixes(ranked, quotas)
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked_path = output_dir / "ranked_train_parents.v1.csv"
    if ranked_path.exists():
        if sha256_file(ranked_path) != sha256_bytes(_csv_bytes(ranked)):
            raise FileExistsError(f"refusing to replace frozen manifest: {ranked_path}")
    else:
        _write_immutable(ranked_path, _csv_bytes(ranked))

    subsets: dict[str, Any] = {}
    for key in ("10", "25", "50", "100"):
        members = prefixes[key]
        subsets[key] = {
            "percent": int(key),
            "count": len(members),
            "class_counts": {name: int(quotas[key][name]) for name in quotas[key]},
            "parent_ids_sha256": identity_hash(row["parent_structure_id"] for row in members),
            "ordered_parent_ids_sha256": sha256_bytes(
                canonical_json_bytes([row["parent_structure_id"] for row in members])
            ),
            "material_ids_sha256": identity_hash(row["material_id"] for row in members),
            "parent_structure_ids": [row["parent_structure_id"] for row in members],
            "material_ids": [row["material_id"] for row in members],
        }
    validation = split_index["validation"]
    test = split_index["test"]
    payload = {
        "schema_version": PROTOCOL_VERSION,
        "status": "frozen_before_training",
        "selection_seed": SELECTION_SEED,
        "selection_rule": "sha256_rank_by_class_then_hamilton_per_class_prefix",
        "class_order": list(quotas["100"]),
        "apportionment": "Hamilton largest remainder; tie order is class_order; prefixes by class_rank",
        "source": {
            "records_sha256": source_hash,
            "split_manifest_sha256": split_hash,
            "peak_cache": cache,
            "data_split_config_sha256": sha256_file(config_path),
            "source_split_field_audit": {
                **source_split_audit,
                "policy": "split_manifest.json is authoritative; source_records split field is retained only for discrepancy audit",
            },
        },
        "official_split": {
            "train_count": len(split_index["train"]),
            "train_material_ids_sha256": identity_hash(row["material_id"] for row in split_index["train"]),
            "validation_count": len(validation),
            "validation_parent_ids_sha256": identity_hash(row["parent_structure_id"] for row in validation),
            "validation_material_ids_sha256": identity_hash(row["material_id"] for row in validation),
            "test_count": len(test),
            "test_parent_ids_sha256": identity_hash(row["parent_structure_id"] for row in test),
            "test_material_ids_sha256": identity_hash(row["material_id"] for row in test),
        },
        "ranked_train_file": {
            "path": ranked_path.name,
            "sha256": sha256_file(ranked_path),
            "rows": len(ranked),
        },
        "budgets": subsets,
    }
    manifest_path = output_dir / "parent_subsets.v1.json"
    encoded = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    _write_immutable(manifest_path, encoded)
    return {
        "status": "PASS",
        "verified_source_records": len(source_index),
        "source_split_field_disagreements": source_split_audit["source_split_field_disagreements"],
        "verified_peak_tables": cache["verified_files"],
        "subsets": {key: value["count"] for key, value in subsets.items()},
        "ranked_csv_sha256": sha256_file(ranked_path),
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_path": str(manifest_path),
    }


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    import io

    buffer = io.StringIO(newline="")
    fields = ("class_rank", "crystal_system", "material_id", "parent_structure_id", "selection_rank")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({field: row[field] for field in fields})
    return buffer.getvalue().encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True, help="formal_14060 local data root")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "manifests" / "parent_budget_efficiency",
    )
    args = parser.parse_args()
    result = freeze(args.data_root.resolve(), args.output_dir.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
