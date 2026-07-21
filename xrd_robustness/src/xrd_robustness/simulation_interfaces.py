"""Stable contracts separating ideal peaks, physics parameters, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .physics import PhysicsParameters


@dataclass(frozen=True)
class PeakTable:
    """Structure-level ideal reflections; rendered spectra are never stored here."""

    positions: np.ndarray
    intensities: np.ndarray
    # Optional V7 reflection metadata.  Arrays are flattened over reflection
    # families; ``reflection_peak_indices`` maps each family back to the
    # possibly-overlapped peak in positions/intensities.
    hkls: np.ndarray | None = None
    multiplicities: np.ndarray | None = None
    reciprocal_vectors: np.ndarray | None = None
    reflection_peak_indices: np.ndarray | None = None

    def __post_init__(self) -> None:
        positions = np.asarray(self.positions, dtype=np.float64)
        intensities = np.asarray(self.intensities, dtype=np.float64)
        if positions.ndim != 1 or intensities.ndim != 1 or positions.shape != intensities.shape:
            raise ValueError("peak positions and intensities must be matching one-dimensional arrays")
        if not np.isfinite(positions).all() or not np.isfinite(intensities).all():
            raise ValueError("peak tables must contain only finite values")
        if np.any(np.diff(positions) < 0) or np.any(intensities <= 0):
            raise ValueError("peak positions must be sorted and intensities must be positive")
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "intensities", intensities)
        metadata = (
            self.hkls,
            self.multiplicities,
            self.reciprocal_vectors,
            self.reflection_peak_indices,
        )
        if all(value is None for value in metadata):
            return
        if any(value is None for value in metadata):
            raise ValueError("V7 reflection metadata must be supplied as one complete set")
        hkls = np.asarray(self.hkls, dtype=np.int64)
        multiplicities = np.asarray(self.multiplicities, dtype=np.int64)
        vectors = np.asarray(self.reciprocal_vectors, dtype=np.float64)
        indices = np.asarray(self.reflection_peak_indices, dtype=np.int64)
        count = len(hkls)
        if hkls.shape != (count, 3) or vectors.shape != (count, 3):
            raise ValueError("hkls and reciprocal_vectors must have shape (reflection_count, 3)")
        if multiplicities.shape != (count,) or indices.shape != (count,):
            raise ValueError("multiplicities and reflection_peak_indices must be one-dimensional")
        if count == 0 or np.any(multiplicities <= 0):
            raise ValueError("reflection metadata must contain positive multiplicities")
        if np.any(indices < 0) or np.any(indices >= len(positions)):
            raise ValueError("reflection_peak_indices contains an invalid peak index")
        if set(indices.tolist()) != set(range(len(positions))):
            raise ValueError("every peak must have at least one hkl reflection family")
        norms = np.linalg.norm(vectors, axis=1)
        if not np.isfinite(vectors).all() or np.any(norms <= 0):
            raise ValueError("reciprocal_vectors must be finite and non-zero")
        if np.any(np.all(hkls == 0, axis=1)):
            raise ValueError("hkl=(0,0,0) is not a Bragg reflection")
        object.__setattr__(self, "hkls", hkls)
        object.__setattr__(self, "multiplicities", multiplicities)
        object.__setattr__(self, "reciprocal_vectors", vectors)
        object.__setattr__(self, "reflection_peak_indices", indices)

    @property
    def has_reflection_metadata(self) -> bool:
        return self.hkls is not None


class IdealPeakCalculator(Protocol):
    """Calculate one reusable ideal peak table from a crystal structure."""

    def calculate(self, structure: Any) -> PeakTable: ...


class XRDRenderer(Protocol):
    """Render one transient XRD profile from ideal peaks and explicit parameters."""

    def render(
        self,
        peak_table: PeakTable,
        params: PhysicsParameters,
        *,
        rng_seed: int,
    ) -> np.ndarray: ...
