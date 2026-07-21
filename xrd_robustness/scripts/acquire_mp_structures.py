#!/usr/bin/env python3
"""Acquire and audit the formal structure-only Materials Project dataset."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping

import numpy as np
from mp_api.client import MPRester
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.structure_data import (
    PERSISTED_STRUCTURE_FIELDS,
    assign_structure_splits,
    crystal_system_from_space_group,
    exact_structure_fingerprint,
    validate_no_split_leakage,
    validate_persisted_structure_record,
)
from xrd_robustness.mp_credentials import configured_api_key
from xrd_robustness.data_layout import project_relative_path, resolve_data_root


QUERY_FIELDS = [
    "material_id",
    "structure",
    "formula_pretty",
    "symmetry",
    "is_stable",
    "energy_above_hull",
    "deprecated",
    "last_updated",
]
LIGHTWEIGHT_QUERY_FIELDS = [
    "material_id",
    "formula_pretty",
    "symmetry",
    "nsites",
    "is_stable",
    "energy_above_hull",
    "deprecated",
    "last_updated",
]

CRYSTAL_SYSTEM_SPACEGROUPS = {
    "Triclinic": list(range(1, 3)),
    "Monoclinic": list(range(3, 16)),
    "Orthorhombic": list(range(16, 75)),
    "Tetragonal": list(range(75, 143)),
    "Trigonal": list(range(143, 168)),
    "Hexagonal": list(range(168, 195)),
    "Cubic": list(range(195, 231)),
}


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def _external_standardize(
    documents: Iterable[Any],
    *,
    standardizer_python: Path,
) -> dict[str, dict[str, Any]]:
    """Use the compatible legacy environment for native symmetry operations."""
    payload = []
    for document in documents:
        payload.append(
            {
                "material_id": str(document.material_id),
                "original_structure": document.structure.as_dict(),
            }
        )
    temp_root = PROJECT_ROOT / "tmp"
    temp_root.mkdir(parents=True, exist_ok=True)
    def run_payload(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Isolate native-crashing structures without losing the whole API batch."""
        with tempfile.TemporaryDirectory(prefix="standardize_", dir=temp_root) as directory:
            directory_path = Path(directory)
            input_path = directory_path / "input.json"
            output_path = directory_path / "output.json"
            input_path.write_text(json.dumps(batch, separators=(",", ":")), encoding="utf-8")
            try:
                subprocess.run(
                    [
                        str(standardizer_python),
                        "-s",
                        str(PROJECT_ROOT / "scripts" / "standardize_structure_batch.py"),
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
                    if isinstance(error, subprocess.CalledProcessError):
                        detail = f"standardizer subprocess exit code {error.returncode}"
                    else:
                        detail = f"standardizer {type(error).__name__}"
                    return [
                        {
                            "material_id": batch[0]["material_id"],
                            "error": f"isolated standardizer failure: {detail}",
                        }
                    ]
        midpoint = len(batch) // 2
        return run_payload(batch[:midpoint]) + run_payload(batch[midpoint:])

    rows = run_payload(payload)
    return {str(row["material_id"]): row for row in rows}


def _symmetry_number(doc: Any) -> int:
    symmetry = getattr(doc, "symmetry", None)
    number = getattr(symmetry, "number", None)
    if number is None:
        raise ValueError("Materials Project symmetry.number is missing")
    return int(number)


def process_documents(
    documents: Iterable[Any],
    *,
    symprec: float,
    angle_tolerance: float,
    split_seed: int,
    split_ratios: Mapping[str, float],
    standardizer_python: Path | None = None,
    per_class_limit: int | None = None,
    allow_metastable: bool = False,
    max_energy_above_hull: float | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], list[str]]:
    retained: list[dict[str, Any]] = []
    duplicate_report: list[dict[str, Any]] = []
    mismatch_report: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    last_updated: list[str] = []
    standardized_rows = (
        _external_standardize(documents, standardizer_python=standardizer_python)
        if standardizer_python is not None
        else None
    )
    seen_ids: set[str] = set()
    fingerprint_owner: dict[str, str] = {}

    for doc in documents:
        material_id = str(getattr(doc, "material_id", "unknown"))
        try:
            if material_id in seen_ids:
                raise ValueError("duplicate material_id returned by API")
            seen_ids.add(material_id)
            if bool(getattr(doc, "deprecated", False)):
                raise ValueError("deprecated material")
            is_stable = bool(getattr(doc, "is_stable", False))
            energy = getattr(doc, "energy_above_hull", None)
            if not is_stable:
                if not allow_metastable:
                    raise ValueError("unstable material")
                if max_energy_above_hull is None or energy is None:
                    raise ValueError("unstable material without near-stable allowance")
                if float(energy) > max_energy_above_hull:
                    raise ValueError("energy above hull exceeds near-stable allowance")
            original = doc.structure
            if not original.is_ordered:
                raise ValueError("disordered or partially occupied structure")
            if standardized_rows is not None:
                standardized_row = standardized_rows.get(material_id)
                if standardized_row is None:
                    raise ValueError("external standardizer returned no row")
                if standardized_row.get("error"):
                    raise ValueError(str(standardized_row["error"]))
                from pymatgen.core import Structure

                standardized = Structure.from_dict(standardized_row["standardized_structure"])
                recomputed = int(standardized_row["space_group_recomputed"])
            else:
                analyzer = SpacegroupAnalyzer(
                    original,
                    symprec=symprec,
                    angle_tolerance=angle_tolerance,
                )
                standardized = analyzer.get_conventional_standard_structure()
                recomputed = int(
                    SpacegroupAnalyzer(
                        standardized,
                        symprec=symprec,
                        angle_tolerance=angle_tolerance,
                    ).get_space_group_number()
                )
            mp_space_group = _symmetry_number(doc)
            if mp_space_group != recomputed:
                mismatch_report.append(
                    {
                        "material_id": material_id,
                        "space_group_mp": mp_space_group,
                        "space_group_recomputed": recomputed,
                        "action": "excluded",
                    }
                )
                continue
            fingerprint = exact_structure_fingerprint(standardized)
            if fingerprint in fingerprint_owner:
                duplicate_report.append(
                    {
                        "kept_material_id": fingerprint_owner[fingerprint],
                        "skipped_material_id": material_id,
                        "structure_fingerprint": fingerprint,
                        "match_reason": "exact_standardized_cell",
                        "action": "excluded",
                    }
                )
                continue
            fingerprint_owner[fingerprint] = material_id
            row = {
                "material_id": material_id,
                "formula": str(getattr(doc, "formula_pretty", original.composition.reduced_formula)),
                "original_structure": original.as_dict(),
                "standardized_structure": standardized.as_dict(),
                "space_group_mp": mp_space_group,
                "space_group_recomputed": recomputed,
                "crystal_system": crystal_system_from_space_group(recomputed),
                "nsites": int(len(original)),
                "is_stable": is_stable,
                "energy_above_hull": float(energy) if energy is not None else 0.0,
                "selection_tier": "stable" if is_stable else "near_stable",
                "structure_fingerprint": fingerprint,
                "split": "train",
            }
            retained.append(row)
            updated = getattr(doc, "last_updated", None)
            if updated is not None:
                last_updated.append(str(updated))
        except Exception as exc:
            failures.append(
                {
                    "material_id": material_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "action": "excluded",
                }
            )

    if per_class_limit is not None:
        if per_class_limit <= 0:
            raise ValueError("per_class_limit must be positive")
        bounded: list[dict[str, Any]] = []
        for crystal_system in sorted({row["crystal_system"] for row in retained}):
            class_rows = [row for row in retained if row["crystal_system"] == crystal_system]
            class_rows.sort(
                key=lambda row: hashlib.sha256(
                    f"{split_seed}:{row['material_id']}".encode("utf-8")
                ).digest()
            )
            bounded.extend(class_rows[:per_class_limit])
        retained = bounded

    retained = assign_structure_splits(retained, ratios=split_ratios, seed=split_seed)
    for row in retained:
        validate_persisted_structure_record(row)
    validate_no_split_leakage(retained)
    reports = {
        "duplicates": duplicate_report,
        "mismatches": mismatch_report,
        "failures": failures,
    }
    return retained, reports, last_updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        default=str(PROJECT_ROOT / "data"),
        help="Project data root; writes mp_processed and manifests only",
    )
    parser.add_argument("--api-key", default=configured_api_key())
    parser.add_argument("--max-sites", type=int, default=500)
    parser.add_argument("--symprec", type=float, default=1e-3)
    parser.add_argument("--angle-tolerance", type=float, default=5.0)
    parser.add_argument("--split-seed", type=int, default=20260711)
    parser.add_argument(
        "--standardizer-python",
        default=None,
        help="Compatible Python interpreter for native pymatgen standardization",
    )
    parser.add_argument(
        "--split-ratios",
        default="0.7,0.1,0.2",
        help="train,validation,test ratios; formal 14000 uses 0.7,0.15,0.15",
    )
    parser.add_argument("--limit", type=int, default=None, help="Smoke/pilot only")
    parser.add_argument(
        "--per-class-limit",
        type=int,
        default=None,
        help="Deterministic retained count per crystal system for a balanced pilot",
    )
    parser.add_argument(
        "--max-energy-above-hull",
        type=float,
        default=None,
        help="Fill class deficits with non-stable structures up to this eV/atom threshold",
    )
    args = parser.parse_args()

    try:
        split_values = [float(value.strip()) for value in args.split_ratios.split(",")]
        if len(split_values) != 3 or any(value < 0 for value in split_values) or not np.isclose(sum(split_values), 1.0):
            raise ValueError
        split_ratios = {
            "train": split_values[0],
            "validation": split_values[1],
            "test": split_values[2],
        }
    except ValueError as error:
        raise SystemExit("--split-ratios must be three non-negative values summing to 1") from error

    if not args.api_key:
        raise SystemExit("MP_API_KEY is required; CrystDB fallback is intentionally disabled")
    try:
        output_root = resolve_data_root(PROJECT_ROOT, args.output_root)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    records_path = output_root / "mp_processed" / "structure_records.jsonl"
    if records_path.exists():
        raise SystemExit(f"refusing to overwrite existing acquisition: {records_path}")

    started = datetime.now(timezone.utc)
    standardizer_python = Path(args.standardizer_python) if args.standardizer_python else None
    if standardizer_python is None:
        legacy_python = PROJECT_ROOT.parent / ".venvs" / "xrd_legacy" / "Scripts" / "python.exe"
        if legacy_python.exists():
            standardizer_python = legacy_python
    query = {
        "deprecated": False,
        "is_stable": True,
        "num_sites": (1, args.max_sites),
        "include_gnome": False,
        "fields": QUERY_FIELDS,
    }
    if args.max_energy_above_hull is not None and args.max_energy_above_hull < 0:
        raise SystemExit("--max-energy-above-hull must be non-negative")
    if args.limit is not None and args.per_class_limit is not None:
        raise SystemExit("use either --limit or --per-class-limit, not both")
    with MPRester(args.api_key) as mpr:
        database_version = mpr.db_version
        reports = {"duplicates": [], "mismatches": [], "failures": []}
        records: list[dict[str, Any]] = []
        source_updates: list[str] = []
        if args.per_class_limit is None:
            documents = mpr.materials.summary.search(**query)
            if args.limit is not None:
                documents = documents[: args.limit]
            records, reports, source_updates = process_documents(
                documents,
                symprec=args.symprec,
                angle_tolerance=args.angle_tolerance,
                split_seed=args.split_seed,
                split_ratios=split_ratios,
                standardizer_python=standardizer_python,
                per_class_limit=None,
            )
        else:
            requested_per_class = max(100, args.per_class_limit * 3)
            candidate_chunks = 8
            api_document_count = 0
            for crystal_system, spacegroup_numbers in CRYSTAL_SYSTEM_SPACEGROUPS.items():
                # The current API accepts spacegroup_number lists but rejects
                # the client's crystal_system query parameter. Keep each
                # request below the server's practical page-size limit.
                per_spacegroup = min(
                    1000,
                    max(10, math.ceil(requested_per_class / len(spacegroup_numbers))),
                )
                class_candidates: list[dict[str, Any]] = []
                class_reports = {"duplicates": [], "mismatches": [], "failures": []}
                class_updates: list[str] = []
                target_valid = args.per_class_limit + max(20, math.ceil(args.per_class_limit * 0.15))
                candidate_specs = [("stable", dict(query))]
                if args.max_energy_above_hull is not None:
                    fallback_query = dict(query)
                    fallback_query["is_stable"] = False
                    fallback_query["energy_above_hull"] = (0.0, args.max_energy_above_hull)
                    candidate_specs.append(("near_stable", fallback_query))
                seen_candidate_ids: set[str] = set()
                for tier_name, candidate_query in candidate_specs:
                    candidate_query["fields"] = LIGHTWEIGHT_QUERY_FIELDS
                    candidate_docs = mpr.materials.summary.search(
                        **candidate_query,
                        spacegroup_number=spacegroup_numbers,
                        chunk_size=per_spacegroup,
                        num_chunks=candidate_chunks,
                    )
                    candidate_ids = sorted(
                        str(document.material_id)
                        for document in candidate_docs
                        if str(document.material_id) not in seen_candidate_ids
                    )
                    seen_candidate_ids.update(candidate_ids)
                    api_document_count += len(candidate_ids)
                    del candidate_docs
                    for start in range(0, len(candidate_ids), 100):
                        batch_ids = candidate_ids[start : start + 100]
                        documents = mpr.materials.summary.search(
                            material_ids=batch_ids,
                            fields=QUERY_FIELDS,
                            chunk_size=len(batch_ids),
                            num_chunks=1,
                        )
                        api_document_count += len(documents)
                        batch_records, batch_reports, batch_updates = process_documents(
                            documents,
                            symprec=args.symprec,
                            angle_tolerance=args.angle_tolerance,
                            split_seed=args.split_seed,
                            split_ratios=split_ratios,
                            standardizer_python=standardizer_python,
                            per_class_limit=None,
                            allow_metastable=tier_name == "near_stable",
                            max_energy_above_hull=args.max_energy_above_hull,
                        )
                        class_candidates.extend(batch_records)
                        class_updates.extend(batch_updates)
                        for name in class_reports:
                            class_reports[name].extend(batch_reports[name])
                        del documents
                        if len(class_candidates) >= target_valid:
                            break
                    if len(class_candidates) >= target_valid:
                        break
                unique_records: list[dict[str, Any]] = []
                seen_material_ids: set[str] = set()
                seen_fingerprints: dict[str, str] = {}
                for row in class_candidates:
                    material_id = str(row["material_id"])
                    fingerprint = str(row["structure_fingerprint"])
                    if material_id in seen_material_ids:
                        continue
                    if fingerprint in seen_fingerprints:
                        class_reports["duplicates"].append(
                            {
                                "kept_material_id": seen_fingerprints[fingerprint],
                                "skipped_material_id": material_id,
                                "structure_fingerprint": fingerprint,
                                "match_reason": "exact_standardized_cell",
                                "action": "excluded",
                            }
                        )
                        continue
                    seen_material_ids.add(material_id)
                    seen_fingerprints[fingerprint] = material_id
                    unique_records.append(row)
                if len(unique_records) < args.per_class_limit:
                    raise RuntimeError(
                        f"{crystal_system} returned {len(unique_records)} retained structures, "
                        f"expected {args.per_class_limit}; increase the candidate query or set "
                        f"--max-energy-above-hull for a documented near-stable fallback"
                    )
                unique_records.sort(
                    key=lambda row: hashlib.sha256(
                        f"{args.split_seed}:{row['material_id']}".encode("utf-8")
                    ).digest()
                )
                class_records = assign_structure_splits(
                    unique_records[: args.per_class_limit],
                    ratios=split_ratios,
                    seed=args.split_seed,
                )
                validate_no_split_leakage(class_records)
                records.extend(class_records)
                source_updates.extend(class_updates)
                for name in reports:
                    reports[name].extend(class_reports[name])
            validate_no_split_leakage(records)
        if args.per_class_limit is None:
            api_document_count = len(records)
    _write_jsonl(records_path, records)

    overview_fields = [
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
    manifests = output_root / "manifests"
    _write_csv(manifests / "structure_manifest.csv", records, overview_fields)
    _write_csv(
        manifests / "split_manifest.csv",
        records,
        ["material_id", "structure_fingerprint", "crystal_system", "split"],
    )
    _write_csv(
        manifests / "label_mismatch_report.csv",
        reports["mismatches"],
        ["material_id", "space_group_mp", "space_group_recomputed", "action"],
    )
    _write_csv(
        manifests / "duplicate_report.csv",
        reports["duplicates"],
        [
            "kept_material_id",
            "skipped_material_id",
            "structure_fingerprint",
            "match_reason",
            "action",
        ],
    )
    _write_csv(
        manifests / "failed_structures.csv",
        reports["failures"],
        ["material_id", "error_type", "error", "action"],
    )

    finished = datetime.now(timezone.utc)
    retrieval_manifest = {
        "source": "Materials Project official API",
        "dataset_root": project_relative_path(PROJECT_ROOT, output_root),
        "endpoint": "materials.summary.search",
        "database_version": database_version,
        "mp_api_version": importlib.metadata.version("mp-api"),
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "query": {
            "deprecated": False,
            "is_stable": True,
            "num_sites": [1, args.max_sites],
            "include_gnome": False,
            "fields": QUERY_FIELDS,
            "limit": args.limit,
            "per_class_limit": args.per_class_limit,
            "selection_policy": (
                "stable_then_near_stable_fallback"
                if args.max_energy_above_hull is not None
                else "stable_only"
            ),
            "max_energy_above_hull": args.max_energy_above_hull,
        },
        "standardization": {
            "method": "SpacegroupAnalyzer.get_conventional_standard_structure",
            "backend": "external compatible environment" if standardizer_python else "current environment",
            "symprec": args.symprec,
            "angle_tolerance": args.angle_tolerance,
        },
        "formal_fields": list(PERSISTED_STRUCTURE_FIELDS) + ["selection_tier"],
        "split_seed": args.split_seed,
        "split_ratios": split_ratios,
        "counts": {
            "api_documents": api_document_count,
            "retained": len(records),
            "duplicates": len(reports["duplicates"]),
            "label_mismatches": len(reports["mismatches"]),
            "failed": len(reports["failures"]),
            "selection_tiers": {
                tier: sum(row.get("selection_tier") == tier for row in records)
                for tier in ("stable", "near_stable")
            },
        },
        "source_last_updated_min": min(source_updates) if source_updates else None,
        "source_last_updated_max": max(source_updates) if source_updates else None,
        "spectra_persisted": False,
    }
    (manifests / "retrieval_manifest.json").write_text(
        json.dumps(retrieval_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(retrieval_manifest["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
