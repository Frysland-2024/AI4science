#!/usr/bin/env python3
"""Build an atomic, versioned ideal-reflection cache with audit artifacts."""

from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np
from pymatgen.core import Structure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.data_layout import project_relative_path, resolve_data_root
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.simulator import SimulationGrid, ideal_peak_table


CACHE_SCHEMA_VERSION = "v7.reflection_cache.1"
REQUIRED_ARRAYS = (
    "positions",
    "intensities",
    "hkls",
    "multiplicities",
    "reciprocal_vectors",
    "reflection_peak_indices",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _table_from_payload(row: dict[str, Any]) -> PeakTable:
    return PeakTable(
        positions=np.asarray(row["positions"], dtype=np.float64),
        intensities=np.asarray(row["intensities"], dtype=np.float64),
        hkls=np.asarray(row["hkls"], dtype=np.int64),
        multiplicities=np.asarray(row["multiplicities"], dtype=np.int64),
        reciprocal_vectors=np.asarray(row["reciprocal_vectors"], dtype=np.float64),
        reflection_peak_indices=np.asarray(row["reflection_peak_indices"], dtype=np.int64),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--manifest-name", default="peak_cache_manifest.v7.reflection.csv")
    parser.add_argument("--failure-name", default="peak_cache_failures.v7.reflection.csv")
    parser.add_argument("--audit-name", default="peak_cache_audit.v7.reflection.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force-local", action="store_true")
    parser.add_argument(
        "--resume-staging",
        action="store_true",
        help="validate and reuse files in <cache-name>.tmp after an interrupted build",
    )
    args = parser.parse_args()
    if args.workers <= 0 or args.batch_size <= 0:
        raise SystemExit("--workers and --batch-size must be positive")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if Path(args.cache_name).name != args.cache_name:
        raise SystemExit("--cache-name must be one directory name")
    for name in (args.manifest_name, args.failure_name, args.audit_name):
        if Path(name).name != name:
            raise SystemExit("manifest, failure, and audit names must be plain file names")

    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    output_dir = data_root / "mp_processed" / args.cache_name
    staging_dir = output_dir.with_name(output_dir.name + ".tmp")
    manifest_path = data_root / "manifests" / args.manifest_name
    failure_path = data_root / "manifests" / args.failure_name
    audit_path = data_root / "manifests" / args.audit_name
    if not records_path.exists():
        raise SystemExit(f"structure records are missing: {records_path}")
    protected_paths = [output_dir, manifest_path, failure_path, audit_path]
    if not args.resume_staging:
        protected_paths.append(staging_dir)
    occupied = [path for path in protected_paths if path.exists()]
    if occupied:
        raise SystemExit("refusing to overwrite existing cache artifacts: " + ", ".join(map(str, occupied)))
    if args.resume_staging and not staging_dir.exists():
        raise SystemExit(f"--resume-staging requested but staging cache is absent: {staging_dir}")

    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records.sort(key=lambda row: str(row["material_id"]))
    if args.limit is not None:
        records = records[: args.limit]
    if not records:
        raise SystemExit("no structure records selected")
    records_by_id = {str(row["material_id"]): row for row in records}
    if len(records_by_id) != len(records):
        raise SystemExit("structure records contain duplicate material_id values")

    if not args.resume_staging:
        staging_dir.mkdir(parents=True)
    started = time.perf_counter()
    grid = SimulationGrid()
    external_python = PROJECT_ROOT.parent / ".venvs" / "xrd_legacy" / "Scripts" / "python.exe"
    use_external = external_python.exists() and not args.force_local

    def compute_external(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compute in the compatible pymatgen interpreter and isolate process crashes."""
        temp_root = PROJECT_ROOT / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="peak_table_v7_", dir=temp_root) as directory:
            directory_path = Path(directory)
            input_path = directory_path / "input.json"
            output_path = directory_path / "output.json"
            input_path.write_text(json.dumps(batch, separators=(",", ":")), encoding="utf-8")
            try:
                subprocess.run(
                    [
                        str(external_python),
                        "-s",
                        str(PROJECT_ROOT / "scripts" / "precompute_peak_table_batch.py"),
                        "--input",
                        str(input_path),
                        "--output",
                        str(output_path),
                    ],
                    cwd=PROJECT_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                return json.loads(output_path.read_text(encoding="utf-8"))
            except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as error:
                if len(batch) == 1:
                    return [
                        {
                            "material_id": batch[0]["material_id"],
                            "error_type": type(error).__name__,
                            "error": str(error),
                        }
                    ]
        midpoint = len(batch) // 2
        return compute_external(batch[:midpoint]) + compute_external(batch[midpoint:])

    manifest: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    def make_manifest_row(
        record: dict[str, Any], output: Path, table: PeakTable
    ) -> dict[str, Any]:
        assert table.hkls is not None
        return {
            "schema_version": CACHE_SCHEMA_VERSION,
            "material_id": record["material_id"],
            "structure_fingerprint": record["structure_fingerprint"],
            "file": project_relative_path(PROJECT_ROOT, output_dir / output.name),
            "peak_count": int(len(table.positions)),
            "reflection_family_count": int(len(table.hkls)),
            "array_fields": ";".join(REQUIRED_ARRAYS),
            "sha256": _sha256(output),
            "bytes": output.stat().st_size,
        }

    def persist_peak(record: dict[str, Any], table: PeakTable) -> None:
        if not table.has_reflection_metadata:
            raise RuntimeError("V7 peak table is missing reflection metadata")
        output = staging_dir / f"{record['material_id']}.npz"
        np.savez_compressed(
            output,
            positions=table.positions,
            intensities=table.intensities,
            hkls=table.hkls,
            multiplicities=table.multiplicities,
            reciprocal_vectors=table.reciprocal_vectors,
            reflection_peak_indices=table.reflection_peak_indices,
        )
        reloaded = load_peak_table(output)
        if not reloaded.has_reflection_metadata:
            raise RuntimeError("persisted V7 peak table lost reflection metadata")
        manifest.append(make_manifest_row(record, output, reloaded))

    if args.resume_staging:
        for output in sorted(staging_dir.glob("*.npz")):
            material_id = output.stem
            if material_id not in records_by_id:
                raise SystemExit(f"staging cache contains an unknown material ID: {material_id}")
            table = load_peak_table(output)
            if not table.has_reflection_metadata:
                raise SystemExit(f"staging cache lacks reflection metadata: {output}")
            manifest.append(make_manifest_row(records_by_id[material_id], output, table))
        print(
            json.dumps(
                {
                    "resume_staging": str(staging_dir),
                    "validated_existing": len(manifest),
                    "remaining": len(records) - len(manifest),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    expected_record_count = len(records)
    completed_ids = {str(row["material_id"]) for row in manifest}
    records = [row for row in records if str(row["material_id"]) not in completed_ids]

    batches = [
        records[start : start + args.batch_size]
        for start in range(0, len(records), args.batch_size)
    ]
    if use_external and batches:
        with ThreadPoolExecutor(max_workers=min(args.workers, len(batches))) as executor:
            batch_results = executor.map(compute_external, batches)
            for batch_number, rows in enumerate(batch_results, start=1):
                for payload in rows:
                    material_id = str(payload["material_id"])
                    if payload.get("error"):
                        failures.append(
                            {
                                "material_id": material_id,
                                "error_type": str(payload.get("error_type", "StructureCalculationError")),
                                "error_message": str(payload["error"]),
                            }
                        )
                        continue
                    try:
                        persist_peak(records_by_id[material_id], _table_from_payload(payload))
                    except Exception as error:
                        failures.append(
                            {
                                "material_id": material_id,
                                "error_type": type(error).__name__,
                                "error_message": str(error),
                            }
                        )
                print(
                    json.dumps(
                        {
                            "batch": batch_number,
                            "batches": len(batches),
                            "completed": len(manifest),
                            "failed": len(failures),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
    elif batches:
        for index, record in enumerate(records, start=1):
            try:
                structure = Structure.from_dict(record["standardized_structure"])
                persist_peak(record, ideal_peak_table(structure, grid))
            except Exception as error:
                failures.append(
                    {
                        "material_id": str(record["material_id"]),
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )
            if index % args.batch_size == 0 or index == len(records):
                print(
                    json.dumps(
                        {
                            "completed": len(manifest),
                            "failed": len(failures),
                            "processed": index,
                            "total": len(records),
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

    manifest.sort(key=lambda row: row["material_id"])
    failures.sort(key=lambda row: row["material_id"])
    failure_fields = ["material_id", "error_type", "error_message"]
    _write_csv(failure_path, failures, failure_fields)
    elapsed = time.perf_counter() - started
    aggregate_payload = "\n".join(
        f"{row['material_id']}:{row['sha256']}" for row in manifest
    ).encode("utf-8")
    aggregate_cache_hash = hashlib.sha256(aggregate_payload).hexdigest()
    audit = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "status": (
            "passed"
            if not failures and len(manifest) == expected_record_count
            else "failed"
        ),
        "data_root": project_relative_path(PROJECT_ROOT, data_root),
        "source_records": project_relative_path(PROJECT_ROOT, records_path),
        "source_records_sha256": _sha256(records_path),
        "source_record_count": expected_record_count,
        "cache_name": args.cache_name,
        "required_arrays": list(REQUIRED_ARRAYS),
        "completed_count": len(manifest),
        "failed_count": len(failures),
        "aggregate_cache_sha256": aggregate_cache_hash,
        "total_cache_bytes": int(sum(int(row["bytes"]) for row in manifest)),
        "grid": {
            "two_theta_min": grid.two_theta_min,
            "two_theta_max": grid.two_theta_max,
            "step": grid.step,
            "wavelength": grid.wavelength,
        },
        "workers": args.workers,
        "batch_size": args.batch_size,
        "external_python_runtime": external_python.parent.parent.name if use_external else None,
        "elapsed_seconds": elapsed,
        "resumed_staging_file_count": len(completed_ids),
    }

    if failures or len(manifest) != expected_record_count:
        audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit(
            f"V7 cache build failed: {len(manifest)}/{expected_record_count} complete; "
            f"see {failure_path} and {audit_path}; staging cache retained at {staging_dir}"
        )

    staging_dir.replace(output_dir)
    manifest_fields = list(manifest[0])
    _write_csv(manifest_path, manifest, manifest_fields)
    audit["manifest"] = project_relative_path(PROJECT_ROOT, manifest_path)
    audit["manifest_sha256"] = _sha256(manifest_path)
    audit["failure_report"] = project_relative_path(PROJECT_ROOT, failure_path)
    audit["failure_report_sha256"] = _sha256(failure_path)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": audit["status"],
                "peak_tables": len(manifest),
                "manifest": str(manifest_path),
                "manifest_sha256": audit["manifest_sha256"],
                "aggregate_cache_sha256": aggregate_cache_hash,
                "audit": str(audit_path),
                "elapsed_seconds": elapsed,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
