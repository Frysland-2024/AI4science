"""Validated in-memory representation of a measured or simulated XRD input."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np


@dataclass(frozen=True)
class XRDObservation:
    sample_id: str
    family_id: str | None
    nominal_composition: str | None
    instrument: dict[str, Any]
    two_theta_deg: np.ndarray
    intensity: np.ndarray


def parse_observation(payload: Mapping[str, Any]) -> XRDObservation:
    """Validate axis/intensity arrays and return the package's input type.

    This checks data integrity only. It does not regrid, normalize, infer a
    material family, or validate an instrument calibration.
    """
    if payload.get("schema_version") != "xrd-observation-v1":
        raise ValueError("unsupported observation schema_version")
    sample_id = payload.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id.strip():
        raise ValueError("sample_id must be a non-empty string")
    family_id = payload.get("family_id")
    composition = payload.get("nominal_composition")
    if family_id is not None and not isinstance(family_id, str):
        raise ValueError("family_id must be a string or null")
    if composition is not None and not isinstance(composition, str):
        raise ValueError("nominal_composition must be a string or null")
    instrument = payload.get("instrument")
    if not isinstance(instrument, Mapping):
        raise ValueError("instrument must be an object")
    required_instrument = {
        "radiation", "wavelength_angstrom", "two_theta_min_deg", "two_theta_max_deg", "step_deg"
    }
    missing = required_instrument - instrument.keys()
    if missing:
        raise ValueError(f"instrument is missing fields: {sorted(missing)}")
    radiation = instrument["radiation"]
    if radiation is not None and not isinstance(radiation, str):
        raise ValueError("instrument radiation must be a string or null")
    instrument_values = np.asarray(
        [instrument[name] for name in ("wavelength_angstrom", "two_theta_min_deg", "two_theta_max_deg", "step_deg")],
        dtype=np.float64,
    )
    if not np.isfinite(instrument_values).all():
        raise ValueError("instrument numeric fields must be finite")
    if float(instrument["wavelength_angstrom"]) <= 0 or float(instrument["step_deg"]) <= 0:
        raise ValueError("instrument wavelength and step must be positive")
    if float(instrument["two_theta_max_deg"]) <= float(instrument["two_theta_min_deg"]):
        raise ValueError("instrument two-theta maximum must exceed minimum")

    axis = np.asarray(payload.get("two_theta_deg"), dtype=np.float64)
    intensity = np.asarray(payload.get("intensity"), dtype=np.float64)
    if axis.ndim != 1 or intensity.ndim != 1 or axis.size < 2:
        raise ValueError("two_theta_deg and intensity must be one-dimensional arrays with at least two points")
    if axis.shape != intensity.shape:
        raise ValueError("two_theta_deg and intensity must have the same length")
    if not np.isfinite(axis).all() or not np.isfinite(intensity).all():
        raise ValueError("two_theta_deg and intensity must contain only finite values")
    if not np.all(np.diff(axis) > 0):
        raise ValueError("two_theta_deg must be strictly increasing")
    if axis[0] < float(instrument["two_theta_min_deg"]) or axis[-1] > float(instrument["two_theta_max_deg"]):
        raise ValueError("two_theta_deg values exceed the declared instrument range")
    return XRDObservation(
        sample_id=sample_id,
        family_id=family_id,
        nominal_composition=composition,
        instrument=dict(instrument),
        two_theta_deg=axis,
        intensity=intensity,
    )
