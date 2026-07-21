#!/usr/bin/env python3
"""Audit a V7 reflection cache against its manifest and metadata contract."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.peak_cache import load_peak_table


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--manifest-name", default="peak_cache_manifest.v7.reflection.csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--failure-output", required=True)
    args = parser.parse_args()
    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    cache_dir = data_root / "mp_processed" / args.cache_name
    manifest_path = data_root / "manifests" / args.manifest_name
    with manifest_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    failures: list[dict[str, Any]] = []
    peak_counts: list[int] = []
    reflection_counts: list[int] = []
    metadata_complete = 0
    for row in rows:
        material_id = row["material_id"]
        path = cache_dir / f"{material_id}.npz"
        try:
            if _sha256(path) != row["sha256"]:
                raise ValueError("file SHA256 differs from manifest")
            table = load_peak_table(path)
            if not table.has_reflection_metadata:
                raise ValueError("reflection metadata missing")
            metadata_complete += 1
            assert table.hkls is not None
            assert table.reflection_peak_indices is not None
            if set(table.reflection_peak_indices.tolist()) != set(range(len(table.positions))):
                raise ValueError("not every peak is mapped to a reflection family")
            peak_counts.append(len(table.positions))
            reflection_counts.append(len(table.hkls))
        except Exception as error:
            failures.append(
                {
                    "material_id": material_id,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
    cache_files = sorted(cache_dir.glob("*.npz"))
    manifest_ids = {row["material_id"] for row in rows}
    cache_ids = {path.stem for path in cache_files}
    missing_files = sorted(manifest_ids - cache_ids)
    extra_files = sorted(cache_ids - manifest_ids)
    aggregate_payload = "\n".join(
        f"{row['material_id']}:{row['sha256']}" for row in sorted(rows, key=lambda item: item["material_id"])
    ).encode("utf-8")
    report = {
        "status": "passed" if not failures and not missing_files and not extra_files else "failed",
        "data_root": project_relative_path(PROJECT_ROOT, data_root),
        "cache_name": args.cache_name,
        "manifest": project_relative_path(PROJECT_ROOT, manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "manifest_rows": len(rows),
        "cache_files": len(cache_files),
        "validated_files": len(rows) - len(failures),
        "failed_files": len(failures),
        "missing_files": missing_files,
        "extra_files": extra_files,
        "reflection_metadata_complete_count": metadata_complete,
        "all_have_reflection_metadata": metadata_complete == len(rows),
        "aggregate_cache_sha256": hashlib.sha256(aggregate_payload).hexdigest(),
        "peak_count": {
            "min": min(peak_counts) if peak_counts else None,
            "median": float(np.median(peak_counts)) if peak_counts else None,
            "max": max(peak_counts) if peak_counts else None,
            "total": sum(peak_counts),
        },
        "reflection_family_count": {
            "min": min(reflection_counts) if reflection_counts else None,
            "median": float(np.median(reflection_counts)) if reflection_counts else None,
            "max": max(reflection_counts) if reflection_counts else None,
            "total": sum(reflection_counts),
        },
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    failure_output = Path(args.failure_output)
    if not failure_output.is_absolute():
        failure_output = PROJECT_ROOT / failure_output
    output.parent.mkdir(parents=True, exist_ok=True)
    failure_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with failure_output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["material_id", "error_type", "error_message"]
        )
        writer.writeheader()
        writer.writerows(failures)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
