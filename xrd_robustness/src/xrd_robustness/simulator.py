"""Transient PXRD simulation for online training views."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Sequence

import numpy as np

from .measurement_models import apply_noise_model, generate_background_profile
from .physics import PhysicsParameters
from .preferred_orientation import apply_preferred_orientation
from .simulation_interfaces import PeakTable


@dataclass(frozen=True)
class PerturbationProvenance:
    name: str
    source: str
    formula_version: str
    config_hash: str


@dataclass(frozen=True)
class SimulationGrid:
    two_theta_min: float = 10.0
    two_theta_max: float = 80.0
    step: float = 0.02
    wavelength: str | float = "CuKa"

    @property
    def values(self) -> np.ndarray:
        if self.two_theta_max <= self.two_theta_min or self.step <= 0:
            raise ValueError("invalid two-theta grid")
        count = int(round((self.two_theta_max - self.two_theta_min) / self.step)) + 1
        grid = self.two_theta_min + np.arange(count, dtype=np.float64) * self.step
        grid[-1] = self.two_theta_max
        return grid


def _three_index_hkl(value: Sequence[int]) -> tuple[int, int, int]:
    hkl = tuple(int(item) for item in value)
    if len(hkl) == 3:
        return hkl
    if len(hkl) == 4:
        # Miller-Bravais (h, k, i, l), with i=-(h+k).
        return hkl[0], hkl[1], hkl[3]
    raise ValueError(f"unsupported hkl rank: {hkl}")


def ideal_peak_table(structure: Any, grid: SimulationGrid) -> PeakTable:
    """Compute ideal peaks plus the reflection metadata required by V7."""
    from pymatgen.analysis.diffraction.xrd import XRDCalculator

    calculator = XRDCalculator(wavelength=grid.wavelength)
    pattern = calculator.get_pattern(
        structure,
        two_theta_range=(grid.two_theta_min, grid.two_theta_max),
        scaled=True,
    )
    raw_positions = np.asarray(pattern.x, dtype=np.float64)
    raw_intensities = np.asarray(pattern.y, dtype=np.float64)
    valid_indices = np.flatnonzero(
        np.isfinite(raw_positions) & np.isfinite(raw_intensities) & (raw_intensities > 0)
    )
    ordered_indices = valid_indices[
        np.argsort(raw_positions[valid_indices], kind="mergesort")
    ]
    positions = raw_positions[ordered_indices]
    intensities = raw_intensities[ordered_indices]
    reciprocal = structure.lattice.reciprocal_lattice_crystallographic
    hkls: list[tuple[int, int, int]] = []
    multiplicities: list[int] = []
    vectors: list[np.ndarray] = []
    peak_indices: list[int] = []
    for new_peak_index, raw_peak_index in enumerate(ordered_indices.tolist()):
        families = pattern.hkls[raw_peak_index]
        if not families:
            raise ValueError("pymatgen returned a Bragg peak without hkl metadata")
        for family in families:
            hkl = _three_index_hkl(family["hkl"])
            hkls.append(hkl)
            multiplicities.append(int(family.get("multiplicity", 1)))
            vectors.append(np.asarray(reciprocal.get_cartesian_coords(hkl), dtype=np.float64))
            peak_indices.append(new_peak_index)
    return PeakTable(
        positions=positions,
        intensities=intensities,
        hkls=np.asarray(hkls, dtype=np.int64),
        multiplicities=np.asarray(multiplicities, dtype=np.int64),
        reciprocal_vectors=np.asarray(vectors, dtype=np.float64),
        reflection_peak_indices=np.asarray(peak_indices, dtype=np.int64),
    )


def ideal_peak_list(
    structure: Any,
    grid: SimulationGrid,
    *,
    return_peak_table: bool = False,
) -> tuple[np.ndarray, np.ndarray] | PeakTable:
    """Backward-compatible two-array view, with an opt-in metadata return."""
    table = ideal_peak_table(structure, grid)
    if return_peak_table:
        return table
    return table.positions, table.intensities


def _max_normalize(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    maximum = float(np.max(values)) if values.size else 0.0
    if not np.isfinite(maximum) or maximum <= 0:
        return np.zeros(values.shape, dtype=np.float32)
    return (values / maximum).astype(np.float32)


def _inactive_noise_diagnostics(model: str) -> dict[str, Any]:
    return {
        "noise_model": model,
        "poisson_count_scale": None,
        "expected_count_mean": None,
        "expected_count_min": None,
        "expected_count_max": None,
        "sampled_count_sum": None,
        "zero_count_fraction": None,
        "shot_noise_std": 0.0,
        "electronic_noise_std": 0.0,
        "electronic_noise_std_counts": 0.0,
        "electronic_noise_std_intensity": 0.0,
        "noise_std_empirical": 0.0,
    }


def render_gaussian_peaks(
    positions: Sequence[float],
    intensities: Sequence[float],
    grid: np.ndarray,
    fwhm_deg: float,
    *,
    truncate_sigma: float = 5.0,
    normalize: bool = True,
) -> np.ndarray:
    """Render a peak table with one explicit Gaussian FWHM."""
    if fwhm_deg <= 0:
        raise ValueError("fwhm_deg must be positive")
    x = np.asarray(positions, dtype=np.float64)
    y = np.asarray(intensities, dtype=np.float64)
    output = np.zeros(grid.shape, dtype=np.float64)
    sigma = fwhm_deg / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    radius = truncate_sigma * sigma
    step = float(grid[1] - grid[0])
    # Treat peak-table intensities as integrated peak strengths. Dividing by
    # sigma keeps the integrated area stable when only FWHM changes.
    for center, amplitude in zip(x, y, strict=False):
        lower = max(0, int(math.floor((center - radius - grid[0]) / step)))
        upper = min(len(grid), int(math.ceil((center + radius - grid[0]) / step)) + 1)
        if lower >= upper:
            continue
        z = (grid[lower:upper] - center) / sigma
        output[lower:upper] += (amplitude / sigma) * np.exp(-0.5 * z * z)
    return _max_normalize(output) if normalize else output.astype(np.float32)


def simulate_from_peak_table(
    positions: Sequence[float],
    intensities: Sequence[float],
    params: PhysicsParameters,
    *,
    rng_seed: int,
    grid: SimulationGrid = SimulationGrid(),
    normalize: bool = True,
    return_diagnostics: bool = False,
    reflection_table: PeakTable | None = None,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Generate one in-memory view and return no persistent intermediate data."""
    params.validate()
    axis = grid.values
    working_intensities = np.asarray(intensities, dtype=np.float64)
    orientation_diagnostics: dict[str, Any]
    if params.preferred_orientation_active:
        if reflection_table is None:
            raise ValueError("active preferred orientation requires a reflection-aware PeakTable")
        working_intensities, params, orientation_diagnostics = apply_preferred_orientation(
            reflection_table, params
        )
    else:
        orientation_diagnostics = {
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
    # Instrument zero offset: one scalar moves the complete 2theta axis.
    # Independent random jitter of individual Bragg positions is not physical.
    shifted = np.asarray(positions, dtype=np.float64) + params.delta_2theta_deg
    raw_signal = render_gaussian_peaks(
        shifted, working_intensities, axis, params.fwhm_deg, normalize=False
    ).astype(np.float64)
    intensities_array = working_intensities
    reference_sigma = 0.08 / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    reference_scale = float(np.max(intensities_array)) / reference_sigma if intensities_array.size else 0.0
    signal = raw_signal / reference_scale if reference_scale > 0 else raw_signal
    rng = np.random.default_rng(rng_seed)
    background_amplitude = params.background_to_peak_ratio if params.background_active else 0.0
    background, background_diagnostics = generate_background_profile(
        axis,
        background_amplitude,
        model=params.background_type,
        order=params.background_order,
        variation=params.background_variation,
        anchor_count=params.background_anchor_count,
        length_scale=params.background_gp_length_scale,
        floor_fraction=params.background_floor_fraction,
        rng=rng,
    )
    signal += background

    noise_diagnostics: dict[str, Any]
    if params.noise_stage == "before_normalization":
        if params.noise_active:
            signal, noise_diagnostics = apply_noise_model(
                signal,
                rng=rng,
                model=params.noise_model,
                gaussian_std=params.noise_std_ratio,
                poisson_count_scale=params.poisson_count_scale,
                electronic_noise_std=params.electronic_noise_std_ratio,
                electronic_noise_std_counts=params.electronic_noise_std_counts,
            )
        else:
            noise_diagnostics = _inactive_noise_diagnostics(params.noise_model)
    else:
        if not normalize:
            raise ValueError("noise_stage='after_normalization' requires normalize=True")
        normalized_clean = _max_normalize(signal).astype(np.float64)
        if params.noise_active:
            signal, noise_diagnostics = apply_noise_model(
                normalized_clean,
                rng=rng,
                model=params.noise_model,
                gaussian_std=params.noise_std_ratio,
                poisson_count_scale=params.poisson_count_scale,
                electronic_noise_std=params.electronic_noise_std_ratio,
                electronic_noise_std_counts=params.electronic_noise_std_counts,
            )
        else:
            signal = normalized_clean
            noise_diagnostics = _inactive_noise_diagnostics(params.noise_model)
    clipped_mask = signal < 0.0
    diagnostics: dict[str, Any] = {
        "preclip_min": float(np.min(signal)) if signal.size else 0.0,
        "preclip_max": float(np.max(signal)) if signal.size else 0.0,
        "clipped_low_count": int(np.count_nonzero(clipped_mask)),
        "clipped_fraction": float(np.mean(clipped_mask)) if signal.size else 0.0,
        "clipped_high_count": 0,
        "noise_stage": params.noise_stage,
    }
    diagnostics.update(background_diagnostics)
    diagnostics.update(noise_diagnostics)
    diagnostics.update(orientation_diagnostics)
    signal = np.clip(signal, 0.0, None)
    result = (
        _max_normalize(signal)
        if normalize and params.noise_stage == "before_normalization"
        else signal.astype(np.float32)
    )
    if result.shape != axis.shape or not np.isfinite(result).all():
        raise RuntimeError("simulator produced an invalid profile")
    if return_diagnostics:
        return result, diagnostics
    return result


def simulate_structure(
    structure: Any,
    params: PhysicsParameters,
    *,
    rng_seed: int,
    grid: SimulationGrid = SimulationGrid(),
) -> np.ndarray:
    peak_table = ideal_peak_table(structure, grid)
    return simulate_from_peak_table(
        peak_table.positions,
        peak_table.intensities,
        params,
        rng_seed=rng_seed,
        grid=grid,
        reflection_table=peak_table,
    )


@dataclass(frozen=True)
class PymatgenIdealPeakCalculator:
    """V7 ideal-peak adapter backed by pymatgen's diffraction calculator."""

    grid: SimulationGrid = SimulationGrid()

    def calculate(self, structure: Any) -> PeakTable:
        return ideal_peak_table(structure, self.grid)


@dataclass(frozen=True)
class GaussianProfileRenderer:
    """Renderer for zero shift, broadening, background, and detector noise."""

    grid: SimulationGrid = SimulationGrid()

    def provenance(
        self, *, config_hash: str, include_v7: bool = False
    ) -> tuple[PerturbationProvenance, ...]:
        """Bind the active V7 operators to one resolved config hash."""
        if not config_hash:
            raise ValueError("config_hash cannot be empty")
        source = "xrd_robustness_v7_independent_implementation"
        versions = (
            ("zero_shift", "axis-offset-v1"),
            ("peak_broadening", "gaussian-area-stable-v1"),
            ("background", "smooth-floor-polynomial-or-gp-v2"),
            ("noise", "gaussian-or-poisson-count-readout-v2"),
        )
        if include_v7:
            versions = versions + (("preferred_orientation", "march-dollase-reflection-v1"),)
        return tuple(
            PerturbationProvenance(
                name=name,
                source=source,
                formula_version=formula_version,
                config_hash=str(config_hash),
            )
            for name, formula_version in versions
        )

    def render(
        self,
        peak_table: PeakTable,
        params: PhysicsParameters,
        *,
        rng_seed: int,
    ) -> np.ndarray:
        return simulate_from_peak_table(
            peak_table.positions,
            peak_table.intensities,
            params,
            rng_seed=rng_seed,
            grid=self.grid,
            reflection_table=peak_table,
        )
