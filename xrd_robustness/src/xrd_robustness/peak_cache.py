"""Bounded in-memory cache for reusable ideal peak tables."""

from __future__ import annotations

from collections import OrderedDict
import csv
import hashlib
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .simulator import SimulationGrid, ideal_peak_list
from .simulation_interfaces import PeakTable


def peak_cache_manifest_name(cache_name: str) -> str:
    """Return the manifest paired with a versioned peak-cache directory."""

    return (
        "peak_cache_manifest.v7.reflection.csv"
        if cache_name == "peak_tables_v7_reflection"
        else "peak_cache_manifest.csv"
    )


def validate_peak_cache_manifest(
    data_root: str | Path,
    cache_name: str,
    records: Mapping[str, Mapping[str, Any]],
    *,
    require_exact_ids: bool = False,
    verify_file_hashes: bool = False,
) -> dict[str, Any]:
    """Validate cache identity, paths, sizes, fingerprints, and optional hashes."""

    data_root = Path(data_root).resolve()
    manifest_path = data_root / "manifests" / peak_cache_manifest_name(cache_name)
    if not manifest_path.is_file():
        raise ValueError(f"missing peak-cache manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        columns = set(reader.fieldnames or ())
    required_columns = {
        "material_id",
        "structure_fingerprint",
        "file",
        "sha256",
        "bytes",
    }
    missing_columns = required_columns.difference(columns)
    if missing_columns:
        raise ValueError(
            f"peak-cache manifest is missing columns: {sorted(missing_columns)}"
        )
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        material_id = str(row["material_id"])
        if material_id in indexed:
            raise ValueError(f"duplicate peak-cache manifest material_id: {material_id}")
        indexed[material_id] = row
    record_ids = {str(value) for value in records}
    manifest_ids = set(indexed)
    missing_ids = sorted(record_ids.difference(manifest_ids))
    if missing_ids:
        raise ValueError(f"peak-cache manifest is missing IDs: {missing_ids[:3]}")
    if require_exact_ids and manifest_ids != record_ids:
        extras = sorted(manifest_ids.difference(record_ids))
        raise ValueError(f"peak-cache manifest has unexpected IDs: {extras[:3]}")

    verified_hashes = 0
    total_bytes = 0
    for material_id in sorted(record_ids):
        row = indexed[material_id]
        expected_fingerprint = str(records[material_id]["structure_fingerprint"])
        if str(row["structure_fingerprint"]) != expected_fingerprint:
            raise ValueError(f"peak-cache fingerprint mismatch: {material_id}")
        declared = Path(str(row["file"]))
        if declared.is_absolute() or ".." in declared.parts:
            raise ValueError(f"non-portable peak-cache path: {row['file']}")
        expected_suffix = Path("mp_processed") / cache_name / f"{material_id}.npz"
        if tuple(declared.parts[-3:]) != tuple(expected_suffix.parts):
            raise ValueError(f"peak-cache path does not match cache identity: {material_id}")
        cache_path = data_root / expected_suffix
        if not cache_path.is_file():
            raise ValueError(f"missing peak-cache file: {cache_path}")
        size = cache_path.stat().st_size
        if size != int(row["bytes"]):
            raise ValueError(f"peak-cache byte count mismatch: {material_id}")
        total_bytes += size
        if verify_file_hashes:
            digest = hashlib.sha256(cache_path.read_bytes()).hexdigest()
            if digest != str(row["sha256"]):
                raise ValueError(f"peak-cache SHA256 mismatch: {material_id}")
            verified_hashes += 1
    return {
        "manifest": manifest_path,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "manifest_rows": len(rows),
        "required_records": len(record_ids),
        "verified_file_hashes": verified_hashes,
        "total_bytes": total_bytes,
    }


class PeakTableCache:
    """Cache ideal reflections only; rendered or perturbed spectra are excluded."""

    def __init__(self, max_items: int = 4096):
        if max_items <= 0:
            raise ValueError("max_items must be positive")
        self.max_items = int(max_items)
        self._items: OrderedDict[str, PeakTable] = OrderedDict()

    def get_or_compute(
        self,
        key: str,
        structure: Any,
        grid: SimulationGrid,
    ) -> PeakTable:
        if key in self._items:
            value = self._items.pop(key)
            self._items[key] = value
            return value
        computed = ideal_peak_list(structure, grid, return_peak_table=True)
        if isinstance(computed, PeakTable):
            value = computed
        else:  # Compatibility for legacy adapters and lightweight test doubles.
            positions, intensities = computed
            value = PeakTable(positions=positions, intensities=intensities)
        self._items[key] = value
        if len(self._items) > self.max_items:
            self._items.popitem(last=False)
        return value

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


def load_peak_table(path: str | Path) -> PeakTable:
    """Load an allowed peak-table intermediate without pickle payloads."""
    with np.load(Path(path), allow_pickle=False) as data:
        positions = np.asarray(data["positions"], dtype=np.float64)
        intensities = np.asarray(data["intensities"], dtype=np.float64)
        metadata_keys = {
            "hkls",
            "multiplicities",
            "reciprocal_vectors",
            "reflection_peak_indices",
        }
        available = metadata_keys.intersection(data.files)
        if available and available != metadata_keys:
            raise ValueError(f"incomplete V7 reflection metadata in {path}: {sorted(available)}")
        metadata = (
            {
                "hkls": np.asarray(data["hkls"], dtype=np.int64),
                "multiplicities": np.asarray(data["multiplicities"], dtype=np.int64),
                "reciprocal_vectors": np.asarray(data["reciprocal_vectors"], dtype=np.float64),
                "reflection_peak_indices": np.asarray(
                    data["reflection_peak_indices"], dtype=np.int64
                ),
            }
            if available
            else {}
        )
    if positions.ndim != 1 or intensities.ndim != 1 or positions.shape != intensities.shape:
        raise ValueError(f"invalid peak table shape in {path}")
    if not np.isfinite(positions).all() or not np.isfinite(intensities).all():
        raise ValueError(f"non-finite peak table in {path}")
    if np.any(intensities <= 0) or np.any(np.diff(positions) < 0):
        raise ValueError(f"invalid peak order or intensity in {path}")
    return PeakTable(positions=positions, intensities=intensities, **metadata)
