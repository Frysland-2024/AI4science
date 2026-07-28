"""Reflection-level March-Dollase preferred-orientation perturbation for V7."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from .physics import PhysicsParameters
from .simulation_interfaces import PeakTable


def canonical_hkl(hkl: np.ndarray | tuple[int, int, int]) -> tuple[int, int, int]:
    """Make Friedel pairs share one stable, human-readable direction."""
    values = tuple(int(value) for value in np.asarray(hkl, dtype=np.int64).tolist())
    for value in values:
        if value < 0:
            return tuple(-item for item in values)
        if value > 0:
            return values
    raise ValueError("hkl=(0,0,0) cannot define a preferred direction")


def march_dollase_factor(cos_alpha: np.ndarray, r: float) -> np.ndarray:
    """Return P(alpha;r) with sign-invariant scattering-vector angles."""
    if not np.isfinite(r) or r <= 0:
        raise ValueError("March-Dollase r must be finite and positive")
    cosine = np.clip(np.abs(np.asarray(cos_alpha, dtype=np.float64)), 0.0, 1.0)
    denominator = (r * r * cosine * cosine) + ((1.0 / r) * (1.0 - cosine * cosine))
    return denominator ** (-1.5)


def _candidate_reflections(table: PeakTable, count: int) -> list[int]:
    assert table.hkls is not None and table.reflection_peak_indices is not None
    cached = getattr(table, "_candidate_reflection_indices", None)
    if cached is not None:
        return list(cached[: min(int(count), len(cached))])
    unique: dict[tuple[int, int, int], int] = {}
    for index, hkl in enumerate(table.hkls):
        key = canonical_hkl(hkl)
        unique.setdefault(key, index)
    ranked = sorted(
        unique.values(),
        key=lambda index: (
            int(np.sum(np.abs(table.hkls[index]))),
            int(np.max(np.abs(table.hkls[index]))),
            float(table.positions[table.reflection_peak_indices[index]]),
            canonical_hkl(table.hkls[index]),
        ),
    )
    return ranked[: min(int(count), len(ranked))]


def resolve_preferred_orientation(
    table: PeakTable,
    params: PhysicsParameters,
) -> PhysicsParameters:
    """Resolve the deterministic preferred hkl against one structure's table."""
    if not params.preferred_orientation_active:
        return params
    if not table.has_reflection_metadata:
        raise ValueError(
            "preferred orientation requires reflection metadata: hkl, multiplicity, reciprocal-vector, "
            "and peak-index metadata; pointwise scaling is forbidden"
        )
    assert table.hkls is not None
    candidates = _candidate_reflections(table, params.candidate_low_index_count)
    if not candidates:
        raise ValueError("peak table has no legal low-index preferred-direction candidates")
    if params.preferred_hkl is None:
        rng = np.random.default_rng(params.orientation_seed)
        selected = candidates[int(rng.integers(0, len(candidates)))]
        preferred_hkl = canonical_hkl(table.hkls[selected])
    else:
        preferred_hkl = canonical_hkl(params.preferred_hkl)
        cached = getattr(table, "_hkl_to_indices", None)
        matches = (
            list(cached.get(preferred_hkl, ()))
            if cached is not None
            else [
                index
                for index, hkl in enumerate(table.hkls)
                if canonical_hkl(hkl) == preferred_hkl
            ]
        )
        if not matches:
            raise ValueError(f"preferred_hkl {preferred_hkl} is absent from this peak table")
    resolved = replace(params, preferred_hkl=preferred_hkl)
    resolved.validate()
    return resolved


def apply_preferred_orientation(
    table: PeakTable,
    params: PhysicsParameters,
) -> tuple[np.ndarray, PhysicsParameters, dict[str, Any]]:
    """Modify integrated reflection intensities before peak-shape rendering."""
    if not params.preferred_orientation_active:
        return table.intensities.copy(), params, {
            "preferred_orientation_enabled": False,
            "preferred_orientation_model": params.preferred_orientation_model,
            "preferred_hkl": None,
            "march_parameter": 1.0,
            "orientation_seed": int(params.orientation_seed),
            "apply_probability": float(params.preferred_orientation_apply_probability),
            "severity_level": int(params.severity_level),
            "intensity_factor_min": 1.0,
            "intensity_factor_max": 1.0,
        }
    resolved = resolve_preferred_orientation(table, params)
    assert table.hkls is not None
    assert table.multiplicities is not None
    assert table.reciprocal_vectors is not None
    assert table.reflection_peak_indices is not None
    assert resolved.preferred_hkl is not None

    preferred_hkl = canonical_hkl(resolved.preferred_hkl)
    cached = getattr(table, "_hkl_to_indices", None)
    matching = (
        list(cached.get(preferred_hkl, ()))
        if cached is not None
        else [
            index
            for index, hkl in enumerate(table.hkls)
            if canonical_hkl(hkl) == preferred_hkl
        ]
    )
    axis_vector = table.reciprocal_vectors[matching[0]]
    axis_unit = axis_vector / np.linalg.norm(axis_vector)
    vectors = table.reciprocal_vectors
    units = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    family_factors = march_dollase_factor(units @ axis_unit, resolved.march_parameter)

    peak_factors = np.ones(len(table.positions), dtype=np.float64)
    for peak_index in range(len(table.positions)):
        mask = table.reflection_peak_indices == peak_index
        weights = table.multiplicities[mask].astype(np.float64)
        peak_factors[peak_index] = float(np.average(family_factors[mask], weights=weights))
    modified = table.intensities * peak_factors
    if not np.isfinite(modified).all() or np.any(modified <= 0):
        raise RuntimeError("preferred orientation produced invalid reflection intensities")
    diagnostics = {
        "preferred_orientation_enabled": True,
        "preferred_orientation_model": resolved.preferred_orientation_model,
        "preferred_hkl": list(resolved.preferred_hkl),
        "march_parameter": float(resolved.march_parameter),
        "orientation_seed": int(resolved.orientation_seed),
        "apply_probability": float(resolved.preferred_orientation_apply_probability),
        "severity_level": int(resolved.severity_level),
        "intensity_factor_min": float(np.min(peak_factors)),
        "intensity_factor_max": float(np.max(peak_factors)),
    }
    return modified, resolved, diagnostics
