#!/usr/bin/env python3
"""Build the audited V7 formal_14060 tier from existing 14,000 and 140 tiers."""

from __future__ import annotations

import argparse
import atexit
from collections import Counter
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.formal_14060 import FORMAL_CLASS_ORDER, merge_formal_and_gate_records


CACHE_NAME = "peak_tables_v7_reflection"
CACHE_MANIFEST = "peak_cache_manifest.v7.reflection.csv"
FAILURE_REPORT = "peak_cache_failures.v7.reflection.csv"
AUDIT_REPORT = "peak_cache_audit.v7.reflection.json"
STRUCTURE_FIELDS = [
    "material_id",
    "formula",
    "space_group_mp",
    "space_group_recomputed",
    "crystal_system",
    "nsites",
    "is_stable",
    "energy_above_hull",
    "selection_tier",
    "structure_fingerprint",
    "split",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _index_cache_rows(
    rows: list[dict[str, str]], *, source_name: str, expected_count: int
) -> dict[str, dict[str, str]]:
    if len(rows) != expected_count:
        raise SystemExit(
            f"{source_name} V7 cache manifest has {len(rows)} rows, expected {expected_count}"
        )
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        material_id = str(row.get("material_id", ""))
        if not material_id:
            raise SystemExit(f"{source_name} V7 cache manifest has an empty material_id")
        if material_id in indexed:
            raise SystemExit(
                f"{source_name} V7 cache manifest contains duplicate material_id {material_id}"
            )
        indexed[material_id] = row
    return indexed


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _portable_final(output_root: Path, relative: str) -> str:
    return project_relative_path(PROJECT_ROOT, output_root / relative)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-root", default="data/formal_14000")
    parser.add_argument("--gate-root", default="data")
    parser.add_argument("--output-root", default="data/formal_14060")
    parser.add_argument("--split-seed", type=int, default=20260711)
    args = parser.parse_args()

    formal_root = resolve_data_root(PROJECT_ROOT, args.formal_root)
    gate_root = resolve_data_root(PROJECT_ROOT, args.gate_root)
    output_root = resolve_data_root(PROJECT_ROOT, args.output_root)
    staging_root = output_root.with_name(output_root.name + ".tmp")
    if output_root in {formal_root, gate_root}:
        raise SystemExit("output root must differ from both source roots")
    if output_root.exists():
        raise SystemExit(f"refusing to overwrite existing output root: {output_root}")
    if staging_root.exists():
        raise SystemExit(f"refusing to overwrite existing staging root: {staging_root}")

    formal_records_path = formal_root / "mp_processed" / "structure_records.jsonl"
    gate_records_path = gate_root / "mp_processed" / "structure_records.jsonl"
    formal_rows = _load_jsonl(formal_records_path)
    gate_rows = _load_jsonl(gate_records_path)
    merged, merge_report = merge_formal_and_gate_records(
        formal_rows, gate_rows, split_seed=args.split_seed
    )
    expected = {
        "formal_count": 14000,
        "gate_count": 140,
        "overlap_count": 80,
        "extra_count": 60,
        "merged_count": 14060,
        "split_counts": {"test": 2130, "train": 9800, "validation": 2130},
    }
    for key, value in expected.items():
        if merge_report[key] != value:
            raise SystemExit(f"unexpected {key}: {merge_report[key]!r} != {value!r}")
    if set(merge_report["train_class_counts"].values()) != {1400}:
        raise SystemExit(
            f"formal training split lost class balance: {merge_report['train_class_counts']}"
        )

    staging_records = staging_root / "mp_processed" / "structure_records.jsonl"
    staging_cache = staging_root / "mp_processed" / CACHE_NAME
    staging_manifests = staging_root / "manifests"
    staging_cache.mkdir(parents=True)
    staging_manifests.mkdir(parents=True)
    cleanup_registered = True

    def _cleanup_incomplete_staging() -> None:
        if cleanup_registered and staging_root.exists():
            shutil.rmtree(staging_root)

    atexit.register(_cleanup_incomplete_staging)
    staging_records.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in merged),
        encoding="utf-8",
    )

    split_rows = [
        {
            "material_id": row["material_id"],
            "structure_fingerprint": row["structure_fingerprint"],
            "crystal_system": row["crystal_system"],
            "split": row["split"],
        }
        for row in merged
    ]
    _write_csv(
        staging_manifests / "split_manifest.csv",
        ["material_id", "structure_fingerprint", "crystal_system", "split"],
        split_rows,
    )
    _write_csv(
        staging_manifests / "structure_manifest.csv", STRUCTURE_FIELDS, merged
    )

    formal_cache_rows = _load_csv(formal_root / "manifests" / CACHE_MANIFEST)
    gate_cache_rows = _load_csv(gate_root / "manifests" / CACHE_MANIFEST)
    if list(formal_cache_rows[0]) != list(gate_cache_rows[0]):
        raise SystemExit("source V7 cache manifests have different schemas")
    formal_cache_by_id = _index_cache_rows(
        formal_cache_rows, source_name="formal", expected_count=14000
    )
    gate_cache_by_id = _index_cache_rows(
        gate_cache_rows, source_name="gate", expected_count=140
    )
    formal_record_ids = {str(row["material_id"]) for row in formal_rows}
    gate_record_ids = {str(row["material_id"]) for row in gate_rows}
    if set(formal_cache_by_id) != formal_record_ids:
        raise SystemExit("formal V7 cache manifest IDs differ from formal records")
    if set(gate_cache_by_id) != gate_record_ids:
        raise SystemExit("gate V7 cache manifest IDs differ from gate records")

    merged_cache_rows: list[dict[str, Any]] = []
    hardlinks = 0
    copies = 0
    total_bytes = 0
    for record in merged:
        material_id = str(record["material_id"])
        if material_id in formal_cache_by_id:
            source_root = formal_root
            source_row = formal_cache_by_id[material_id]
        else:
            source_root = gate_root
            source_row = gate_cache_by_id[material_id]
        if source_row["structure_fingerprint"] != record["structure_fingerprint"]:
            raise SystemExit(f"cache fingerprint mismatch for {material_id}")
        source = source_root / "mp_processed" / CACHE_NAME / f"{material_id}.npz"
        if _sha256(source) != source_row["sha256"]:
            raise SystemExit(f"source cache SHA256 mismatch for {material_id}")
        destination = staging_cache / source.name
        try:
            os.link(source, destination)
            hardlinks += 1
        except OSError:
            shutil.copy2(source, destination)
            copies += 1
        if _sha256(destination) != source_row["sha256"]:
            raise SystemExit(f"destination cache SHA256 mismatch for {material_id}")
        size = destination.stat().st_size
        total_bytes += size
        row = dict(source_row)
        row["file"] = _portable_final(
            output_root, f"mp_processed/{CACHE_NAME}/{material_id}.npz"
        )
        row["bytes"] = str(size)
        merged_cache_rows.append(row)

    cache_fields = list(formal_cache_rows[0])
    cache_manifest_path = staging_manifests / CACHE_MANIFEST
    _write_csv(cache_manifest_path, cache_fields, merged_cache_rows)
    _write_csv(
        staging_manifests / FAILURE_REPORT,
        ["material_id", "error_type", "error_message"],
        [],
    )
    aggregate_payload = "\n".join(
        f"{row['material_id']}:{row['sha256']}"
        for row in sorted(merged_cache_rows, key=lambda item: item["material_id"])
    ).encode("utf-8")

    source_hashes = {
        "formal_records_sha256": _sha256(formal_records_path),
        "formal_split_manifest_sha256": _sha256(formal_root / "manifests" / "split_manifest.csv"),
        "formal_v7_cache_manifest_sha256": _sha256(formal_root / "manifests" / CACHE_MANIFEST),
        "gate_records_sha256": _sha256(gate_records_path),
        "gate_split_manifest_sha256": _sha256(gate_root / "manifests" / "split_manifest.csv"),
        "gate_v7_cache_manifest_sha256": _sha256(gate_root / "manifests" / CACHE_MANIFEST),
    }
    merge_manifest = {
        "schema_version": "formal_14060.merge.1",
        "status": "passed",
        "algorithm": "preserve_formal_train_split_and_balance_extras_between_validation_test_v1",
        "split_seed": args.split_seed,
        "formal_source": project_relative_path(PROJECT_ROOT, formal_root),
        "gate_source": project_relative_path(PROJECT_ROOT, gate_root),
        "output_root": project_relative_path(PROJECT_ROOT, output_root),
        **merge_report,
        "source_hashes": source_hashes,
    }
    (staging_manifests / "merge_manifest.json").write_text(
        json.dumps(merge_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    selection_tiers = Counter(str(row.get("selection_tier", "legacy")) for row in merged)
    retrieval_manifest = {
        "schema_version": "retrieval-manifest-merged-v1",
        "source": "deterministic union of existing audited Materials Project tiers",
        "dataset_root": project_relative_path(PROJECT_ROOT, output_root),
        "counts": {
            "retained": len(merged),
            "formal_source": len(formal_rows),
            "gate_source": len(gate_rows),
            "overlap": merge_report["overlap_count"],
            "new_unique": merge_report["extra_count"],
            "selection_tiers": dict(sorted(selection_tiers.items())),
        },
        "split_seed": args.split_seed,
        "split_policy": "preserve formal_14000 train; assign 60 extras equally to validation and test",
        "split_ratios": {
            name: merge_report["split_counts"][name] / len(merged)
            for name in ("train", "validation", "test")
        },
        "query": {"max_energy_above_hull": 0.1},
        "source_hashes": source_hashes,
        "created_at": "deterministic_from_source_manifests_v1",
    }
    (staging_manifests / "retrieval_manifest.json").write_text(
        json.dumps(retrieval_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    records_sha = _sha256(staging_records)
    split_sha = _sha256(staging_manifests / "split_manifest.csv")
    cache_manifest_sha = _sha256(cache_manifest_path)
    failure_sha = _sha256(staging_manifests / FAILURE_REPORT)
    cache_audit = {
        "schema_version": "v7.reflection_cache.1",
        "status": "passed",
        "data_root": project_relative_path(PROJECT_ROOT, output_root),
        "cache_name": CACHE_NAME,
        "source_record_count": len(merged),
        "completed_count": len(merged_cache_rows),
        "failed_count": 0,
        "cache_files": len(list(staging_cache.glob("*.npz"))),
        "total_cache_bytes": total_bytes,
        "hardlink_count": hardlinks,
        "copy_fallback_count": copies,
        "manifest": _portable_final(output_root, f"manifests/{CACHE_MANIFEST}"),
        "manifest_sha256": cache_manifest_sha,
        "failure_report": _portable_final(output_root, f"manifests/{FAILURE_REPORT}"),
        "failure_report_sha256": failure_sha,
        "source_records": _portable_final(output_root, "mp_processed/structure_records.jsonl"),
        "source_records_sha256": records_sha,
        "split_manifest_sha256": split_sha,
        "aggregate_cache_sha256": hashlib.sha256(aggregate_payload).hexdigest(),
        "required_arrays": [
            "positions",
            "intensities",
            "hkls",
            "multiplicities",
            "reciprocal_vectors",
            "reflection_peak_indices",
        ],
        "source_hashes": source_hashes,
    }
    (staging_manifests / AUDIT_REPORT).write_text(
        json.dumps(cache_audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    class_counts = Counter(str(row["crystal_system"]) for row in merged)
    dataset_manifest = {
        "schema_version": "dataset-manifest-v1",
        "status": "built",
        "tier": "formal_14060",
        "dataset_root": project_relative_path(PROJECT_ROOT, output_root),
        "expected_size": len(merged),
        "crystal_system_count": len(FORMAL_CLASS_ORDER),
        "counts": {name: class_counts[name] for name in FORMAL_CLASS_ORDER},
        "split_counts": merge_report["split_counts"],
        "train_class_counts": merge_report["train_class_counts"],
        "split_policy": retrieval_manifest["split_policy"],
        "source": retrieval_manifest["source"],
        "spectra_persisted": False,
        "artifacts": {
            "records": _portable_final(output_root, "mp_processed/structure_records.jsonl"),
            "split_manifest": _portable_final(output_root, "manifests/split_manifest.csv"),
            "structure_manifest": _portable_final(output_root, "manifests/structure_manifest.csv"),
            "peak_cache_manifest": _portable_final(output_root, f"manifests/{CACHE_MANIFEST}"),
            "peak_cache_audit": _portable_final(output_root, f"manifests/{AUDIT_REPORT}"),
            "retrieval_manifest": _portable_final(output_root, "manifests/retrieval_manifest.json"),
            "merge_manifest": _portable_final(output_root, "manifests/merge_manifest.json"),
        },
        "hashes": {
            "records_sha256": records_sha,
            "split_manifest_sha256": split_sha,
            "peak_cache_manifest_sha256": cache_manifest_sha,
            "aggregate_cache_sha256": cache_audit["aggregate_cache_sha256"],
        },
        "created_at": "deterministic_from_source_manifests_v1",
    }
    (staging_manifests / "dataset_manifest.json").write_text(
        json.dumps(dataset_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    staging_root.replace(output_root)
    cleanup_registered = False
    atexit.unregister(_cleanup_incomplete_staging)
    result = {
        "status": "passed",
        "output_root": project_relative_path(PROJECT_ROOT, output_root),
        "records": len(merged),
        "split_counts": merge_report["split_counts"],
        "cache_files": len(merged_cache_rows),
        "hardlinks": hardlinks,
        "copies": copies,
        "manifest_sha256": cache_manifest_sha,
        "aggregate_cache_sha256": cache_audit["aggregate_cache_sha256"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
