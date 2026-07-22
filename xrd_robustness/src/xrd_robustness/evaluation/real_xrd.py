"""Provenance-preserving loader for single real-XRD inference spectra."""

from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


REAL_TEST_REQUIRED_COLUMNS = (
    "sample_id",
    "spectrum_path",
    "crystal_system",
    "source",
    "license_or_permission",
    "phase_purity_status",
    "label_evidence",
    "structure_identifier",
    "spectrum_sha256",
)


@dataclass(frozen=True)
class RealXRDConfig:
    two_theta_min: float = 10.0
    two_theta_max: float = 80.0
    step: float = 0.02
    normalization: str = "max"

    @property
    def grid(self) -> np.ndarray:
        count = int(round((self.two_theta_max - self.two_theta_min) / self.step)) + 1
        return self.two_theta_min + np.arange(count, dtype=np.float64) * self.step


def load_real_xrd(path: str | Path, *, config: RealXRDConfig = RealXRDConfig()) -> tuple[np.ndarray, dict[str, Any]]:
    """Load two-column 2theta/intensity text and interpolate onto the frozen training grid."""
    source = Path(path)
    raw = np.loadtxt(source, comments="#", delimiter=None)
    if raw.ndim != 2 or raw.shape[1] < 2:
        raise ValueError("real-XRD input must contain at least two columns: 2theta and intensity")
    two_theta = np.asarray(raw[:, 0], dtype=np.float64)
    intensity = np.asarray(raw[:, 1], dtype=np.float64)
    valid = np.isfinite(two_theta) & np.isfinite(intensity)
    two_theta = two_theta[valid]
    intensity = intensity[valid]
    order = np.argsort(two_theta, kind="mergesort")
    two_theta = two_theta[order]
    intensity = intensity[order]
    unique, indices = np.unique(two_theta, return_index=True)
    intensity = intensity[indices]
    grid = config.grid
    interpolated = np.interp(grid, unique, intensity, left=0.0, right=0.0)
    if config.normalization == "max":
        maximum = float(np.max(interpolated)) if interpolated.size else 0.0
        if maximum > 0:
            interpolated = interpolated / maximum
    elif config.normalization != "none":
        raise ValueError("normalization must be max or none")
    if not np.isfinite(interpolated).all():
        raise ValueError("real-XRD interpolation produced non-finite values")
    provenance = {
        "source_path": str(source.resolve()),
        "config": asdict(config),
        "raw_points": int(raw.shape[0]),
        "grid_points": int(grid.size),
    }
    return interpolated.astype(np.float32), provenance


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def audit_real_xrd_contract(path: str | Path) -> dict[str, Any]:
    """Audit the locked preprocessing contract without loading a model or spectra."""
    source = Path(path).resolve()
    contract = json.loads(source.read_text(encoding="utf-8"))
    preprocessing = contract["preprocessing"]
    expected = RealXRDConfig()
    checks = {
        "real_test_disabled": contract.get("enabled") is False,
        "selection_use_forbidden": contract.get("selection_use_forbidden") is True,
        "required_columns_exact": tuple(contract["data_manifest"]["required_columns"]) == REAL_TEST_REQUIRED_COLUMNS,
        "grid_matches_loader": (
            float(preprocessing["two_theta_min"]) == expected.two_theta_min
            and float(preprocessing["two_theta_max"]) == expected.two_theta_max
            and float(preprocessing["step"]) == expected.step
            and preprocessing["normalization"] == expected.normalization
        ),
        "linear_interpolation_frozen": preprocessing.get("interpolation") == "linear",
        "out_of_range_fill_zero": float(preprocessing.get("out_of_range_fill")) == 0.0,
        "no_unregistered_signal_editing": (
            preprocessing.get("baseline_subtraction") == "none"
            and preprocessing.get("smoothing") == "none"
            and preprocessing.get("manual_peak_editing") is False
        ),
        "overlap_audit_required": contract.get("overlap_audit", {}).get("required") is True,
    }
    return {
        "schema_version": "v9-real-test-preprocessing-readiness-v1",
        "status": "locked_ready_for_future_manifest" if all(checks.values()) else "fail",
        "contract_path": str(source),
        "contract_sha256": _sha256(source),
        "model_loaded": False,
        "spectra_loaded": False,
        "real_test_used": False,
        "checks": checks,
        "remaining_blocker": "real-test manifest is intentionally absent/unfrozen and explicit authorization is required",
    }


def audit_real_xrd_manifest(path: str | Path) -> dict[str, Any]:
    """Validate a future manifest and its file hashes without running inference."""
    source = Path(path).resolve()
    with source.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != REAL_TEST_REQUIRED_COLUMNS:
            raise ValueError("real-test manifest columns do not match the frozen contract")
        rows = list(reader)
    if not rows:
        raise ValueError("real-test manifest is empty")
    sample_ids: set[str] = set()
    verified = []
    for row in rows:
        if row["sample_id"] in sample_ids:
            raise ValueError(f"duplicate real-test sample_id: {row['sample_id']}")
        sample_ids.add(row["sample_id"])
        spectrum = (source.parent / row["spectrum_path"]).resolve()
        if not spectrum.is_file():
            raise ValueError(f"missing real-test spectrum: {spectrum}")
        actual = _sha256(spectrum)
        if actual != row["spectrum_sha256"].upper():
            raise ValueError(f"real-test spectrum hash mismatch: {row['sample_id']}")
        verified.append({"sample_id": row["sample_id"], "spectrum_sha256": actual})
    return {"manifest_path": str(source), "manifest_sha256": _sha256(source), "sample_count": len(rows), "verified": verified}
