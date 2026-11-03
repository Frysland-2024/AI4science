"""Versioned pseudo-Voigt/Caglioti peak-profile renderer for the pilot.

The peak positions and integrated intensities still come from the existing
pymatgen V7 peak table. This module changes only the line-profile response.
"""

from __future__ import annotations

from functools import partial
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .physics import PhysicsParameters
from .simulation_interfaces import PeakTable
from .simulator import SimulationGrid, simulate_from_peak_table


DEFAULT_LINE_PROFILE: dict[str, Any] = {
    "kind": "pseudo_voigt_caglioti_v1",
    "lorentz_fraction": 0.5,
    "caglioti_u_deg2": 0.0012,
    "caglioti_v_deg2": 0.0004,
    "truncate_fwhm": 20.0,
}


def render_pseudo_voigt_caglioti_peaks(
    positions: Sequence[float],
    intensities: Sequence[float],
    grid: np.ndarray,
    fwhm_deg: float,
    *,
    line_profile: Mapping[str, Any] | None = None,
    normalize: bool = True,
) -> np.ndarray:
    """Render area-normalized pseudo-Voigt lines with a Caglioti width term.

    ``fwhm_deg**2`` is W in H^2 = U tan(theta)^2 + V tan(theta) + W.
    U and V are fixed instrument-agnostic pilot sensitivity coefficients;
    they are not fitted to a named diffractometer. Integrated reflection
    intensity is conserved up to the explicit finite-tail truncation.
    """
    config = {**DEFAULT_LINE_PROFILE, **dict(line_profile or {})}
    if config.get("kind") != "pseudo_voigt_caglioti_v1":
        raise ValueError(f"unsupported V10 line-profile kind: {config.get('kind')!r}")
    eta = float(config["lorentz_fraction"])
    c_u = float(config["caglioti_u_deg2"])
    c_v = float(config["caglioti_v_deg2"])
    truncate_fwhm = float(config["truncate_fwhm"])
    if not (0.0 <= eta <= 1.0):
        raise ValueError("lorentz_fraction must be in [0, 1]")
    if c_u < 0 or c_v < 0 or fwhm_deg <= 0 or truncate_fwhm <= 0:
        raise ValueError("width terms and truncate_fwhm must be positive/non-negative")

    axis = np.asarray(grid, dtype=np.float64)
    centers = np.asarray(positions, dtype=np.float64)
    areas = np.asarray(intensities, dtype=np.float64)
    if centers.ndim != 1 or areas.shape != centers.shape:
        raise ValueError("peak positions and intensities must be same-length vectors")
    if axis.ndim != 1 or axis.size < 2 or not np.all(np.diff(axis) > 0):
        raise ValueError("grid must be a strictly increasing one-dimensional axis")
    if not np.isfinite(centers).all() or not np.isfinite(areas).all() or np.any(areas < 0):
        raise ValueError("peak inputs must be finite and intensities non-negative")

    output = np.zeros(axis.shape, dtype=np.float64)
    step = float(axis[1] - axis[0])
    for center, area in zip(centers, areas, strict=True):
        if area <= 0:
            continue
        theta_rad = math.radians(float(center) / 2.0)
        tan_theta = math.tan(theta_rad)
        width_sq = fwhm_deg * fwhm_deg + c_u * tan_theta * tan_theta + c_v * tan_theta
        width = math.sqrt(width_sq)
        radius = truncate_fwhm * width
        lo = max(0, int(math.floor((center - radius - axis[0]) / step)))
        hi = min(axis.size, int(math.ceil((center + radius - axis[0]) / step)) + 1)
        if lo >= hi:
            continue
        offset = axis[lo:hi] - center
        # Unit-area Gaussian and Lorentzian densities, each parameterized by FWHM.
        gaussian = (
            2.0 * math.sqrt(math.log(2.0))
            / (width * math.sqrt(math.pi))
            * np.exp(-4.0 * math.log(2.0) * (offset / width) ** 2)
        )
        half_width = width / 2.0
        lorentzian = (half_width / math.pi) / (offset * offset + half_width * half_width)
        output[lo:hi] += area * ((1.0 - eta) * gaussian + eta * lorentzian) * math.sqrt(
            2.0 * math.pi
        )
    if normalize:
        maximum = float(output.max()) if output.size else 0.0
        return (output / maximum).astype(np.float32) if maximum > 0 else np.zeros(
            output.shape, dtype=np.float32
        )
    return output.astype(np.float32)


def simulate_from_peak_table_v10(
    positions: Sequence[float],
    intensities: Sequence[float],
    params: PhysicsParameters,
    *,
    rng_seed: int,
    grid: SimulationGrid = SimulationGrid(),
    normalize: bool = True,
    return_diagnostics: bool = False,
    reflection_table: PeakTable | None = None,
    line_profile: Mapping[str, Any] | None = None,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """V10 profile simulation with V9 shift/orientation/background/noise stages."""
    renderer = partial(render_pseudo_voigt_caglioti_peaks, line_profile=line_profile)
    return simulate_from_peak_table(
        positions,
        intensities,
        params,
        rng_seed=rng_seed,
        grid=grid,
        normalize=normalize,
        return_diagnostics=return_diagnostics,
        reflection_table=reflection_table,
        peak_renderer=renderer,
    )
