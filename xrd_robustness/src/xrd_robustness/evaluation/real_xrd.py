"""Provenance-preserving loader for single real-XRD inference spectra."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np


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
