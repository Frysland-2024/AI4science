#!/usr/bin/env python3
"""Validate a structure-only database tier and its portable manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.structure_data import (
    CRYSTAL_SYSTEMS,
    validate_no_split_leakage,
    validate_persisted_structure_record,
)

ABSOLUTE_PATH = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\)")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _allocate_counts(count: int, ratios: dict[str, float]) -> dict[str, int]:
    raw = {name: count * ratios[name] for name in ratios}
    allocated = {name: int(value) for name, value in raw.items()}
    remainder = count - sum(allocated.values())
    order = sorted(ratios, key=lambda name: (raw[name] - allocated[name], ratios[name], name), reverse=True)
    for name in order[:remainder]:
        allocated[name] += 1
    return allocated


def _project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"absolute manifest path: {value}")
    resolved = (PROJECT_ROOT / path).resolve()
    if not resolved.is_relative_to(PROJECT_ROOT.resolve()):
        raise ValueError(f"manifest path escapes project root: {value}")
    return resolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--expected-size", type=int, default=14000)
    parser.add_argument("--per-class", type=int, default=None)
    parser.add_argument("--parent-root", default=None)
    parser.add_argument(
        "--peak-manifest-name",
        default=None,
        help="peak manifest below <data-root>/manifests; auto-prefers the V7 reflection manifest",
    )
    args = parser.parse_args()
    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    errors: list[str] = []
    warnings: list[str] = []
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    manifests = data_root / "manifests"
    if not records_path.exists():
        errors.append(f"missing records: {project_relative_path(PROJECT_ROOT, records_path)}")
        print(json.dumps({"ok": False, "errors": errors, "warnings": warnings}, sort_keys=True))
        return 1
    try:
        records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    except Exception as error:
        errors.append(f"records are not valid JSONL: {error}")
        records = []
    if len(records) != args.expected_size:
        errors.append(f"record count {len(records)} != expected {args.expected_size}")
    per_class = args.per_class if args.per_class is not None else (args.expected_size // 7 if args.expected_size % 7 == 0 else None)
    class_counts: dict[str, int] = {system: 0 for system in CRYSTAL_SYSTEMS}
    split_counts: dict[str, dict[str, int]] = {system: {"train": 0, "validation": 0, "test": 0} for system in CRYSTAL_SYSTEMS}
    ids: set[str] = set()
    fingerprints: set[str] = set()
    for row in records:
        try:
            validate_persisted_structure_record(row)
        except Exception as error:
            errors.append(f"invalid record {row.get('material_id', '<unknown>')}: {error}")
        material_id = str(row.get("material_id", ""))
        fingerprint = str(row.get("structure_fingerprint", ""))
        if material_id in ids:
            errors.append(f"duplicate material_id: {material_id}")
        ids.add(material_id)
        if fingerprint in fingerprints:
            errors.append(f"duplicate structure_fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)
        system = str(row.get("crystal_system", ""))
        split = str(row.get("split", ""))
        if system not in class_counts:
            errors.append(f"unknown crystal system: {system}")
        else:
            class_counts[system] += 1
            if split in split_counts[system]:
                split_counts[system][split] += 1
    try:
        validate_no_split_leakage(records)
    except Exception as error:
        errors.append(f"split leakage: {error}")
    if per_class is not None:
        for system in CRYSTAL_SYSTEMS:
            if class_counts[system] != per_class:
                errors.append(f"{system} count {class_counts[system]} != expected {per_class}")
    retrieval_manifest = manifests / "retrieval_manifest.json"
    ratios = (
        {"train": 0.7, "validation": 0.15, "test": 0.15}
        if args.expected_size >= 3500
        else {"train": 0.7, "validation": 0.1, "test": 0.2}
    )
    if retrieval_manifest.exists():
        try:
            retrieval = json.loads(retrieval_manifest.read_text(encoding="utf-8"))
            if "split_ratios" in retrieval:
                ratios = {name: float(retrieval["split_ratios"][name]) for name in ratios}
            else:
                warnings.append("legacy retrieval manifest has no split_ratios; using tier default")
        except Exception as error:
            errors.append(f"invalid retrieval manifest: {error}")
    elif args.expected_size >= 3500:
        errors.append("missing retrieval_manifest.json")
    if per_class is not None and len(records) == args.expected_size:
        expected_splits = _allocate_counts(per_class, ratios)
        for system in CRYSTAL_SYSTEMS:
            if split_counts[system] != expected_splits:
                errors.append(f"{system} split counts {split_counts[system]} != expected {expected_splits}")

    tier_counts: dict[str, int] = {}
    for row in records:
        tier = str(row.get("selection_tier", "legacy"))
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    if retrieval_manifest.exists():
        try:
            retrieval = json.loads(retrieval_manifest.read_text(encoding="utf-8"))
            max_eh = retrieval.get("query", {}).get("max_energy_above_hull")
            if max_eh is not None:
                for row in records:
                    if str(row.get("selection_tier", "stable")) == "near_stable":
                        if float(row.get("energy_above_hull", float("inf"))) > float(max_eh) + 1e-9:
                            errors.append(
                                f"near-stable energy exceeds manifest threshold: {row.get('material_id')}"
                            )
        except Exception as error:
            errors.append(f"invalid near-stable selection metadata: {error}")

    if args.peak_manifest_name:
        peak_manifest = manifests / args.peak_manifest_name
    else:
        peak_manifest = manifests / "peak_cache_manifest.v7.reflection.csv"
    if not peak_manifest.exists():
        errors.append(f"missing peak manifest: {peak_manifest.name}")
    else:
        peak_rows: dict[str, dict[str, str]] = {}
        with peak_manifest.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["material_id"] in peak_rows:
                    errors.append(f"duplicate peak manifest material_id: {row['material_id']}")
                peak_rows[row["material_id"]] = row
        if set(peak_rows) != ids:
            errors.append(f"peak manifest IDs differ from records: {len(peak_rows)} vs {len(ids)}")
        for material_id, row in peak_rows.items():
            try:
                path = _project_path(row["file"])
                if not path.exists():
                    errors.append(f"missing peak table: {row['file']}")
                elif _sha256(path) != row["sha256"]:
                    errors.append(f"peak hash mismatch: {material_id}")
            except Exception as error:
                errors.append(f"invalid peak path for {material_id}: {error}")

    if manifests.exists():
        for path in manifests.rglob("*"):
            if path.is_file():
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    warnings.append(f"manifest is not UTF-8 text: {project_relative_path(PROJECT_ROOT, path)}")
                    continue
                if ABSOLUTE_PATH.search(text):
                    errors.append(f"absolute path found in manifest: {project_relative_path(PROJECT_ROOT, path)}")

    if args.parent_root is not None:
        parent_root = resolve_data_root(PROJECT_ROOT, args.parent_root)
        parent_records_path = parent_root / "mp_processed" / "structure_records.jsonl"
        if not parent_records_path.exists():
            errors.append("parent records are missing")
        else:
            parent_ids = {
                str(json.loads(line)["material_id"])
                for line in parent_records_path.read_text(encoding="utf-8").splitlines()
            }
            if not ids.issubset(parent_ids):
                errors.append("derived tier contains structures absent from parent tier")

    result = {
        "ok": not errors,
        "data_root": project_relative_path(PROJECT_ROOT, data_root),
        "expected_size": args.expected_size,
        "counts": {"records": len(records), "per_crystal_system": class_counts, "per_system_split": split_counts},
        "selection_tiers": tier_counts,
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
