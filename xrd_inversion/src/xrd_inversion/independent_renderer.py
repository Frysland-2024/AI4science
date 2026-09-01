"""Sealed-test PXRD renderer independent of the training forward path.

This module intentionally does not import the project simulator, the CUDA
forward implementation, or the Week-1 pilot.  It implements the tetragonal
metric, signed reciprocal-lattice enumeration, atomic structure factors, and
Gaussian profile construction directly with NumPy.  Pymatgen supplies only
its tabulated atomic X-ray scattering coefficients and ``Structure`` type.

The renderer is deterministic and noise-free.  The frozen holdout contract
keeps real validation-parent structures sealed until Week 4; tests for this
module therefore use only analytic and synthetic structures.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
from pymatgen.analysis.diffraction.xrd import ATOMIC_SCATTERING_PARAMS
from pymatgen.core import Structure


INDEPENDENT_RENDERER_CONTRACT = "numpy_signed_hkl_tetragonal_v1"


@dataclass(frozen=True)
class IndependentGrid:
    """Two-theta sampling and radiation contract for the sealed renderer."""

    two_theta_min: float = 10.0
    two_theta_max: float = 80.0
    step: float = 0.02
    wavelength_angstrom: float = 1.54184
    peak_calculation_padding_deg: float = 2.5

    def validate(self) -> None:
        if not self.two_theta_max > self.two_theta_min:
            raise ValueError("two_theta_max must exceed two_theta_min")
        if not self.step > 0.0:
            raise ValueError("grid step must be positive")
        if not self.wavelength_angstrom > 0.0:
            raise ValueError("wavelength must be positive")
        if self.peak_calculation_padding_deg < 0.0:
            raise ValueError("peak-calculation padding cannot be negative")

    @property
    def axis(self) -> np.ndarray:
        self.validate()
        count = int(round((self.two_theta_max - self.two_theta_min) / self.step)) + 1
        values = self.two_theta_min + np.arange(count, dtype=np.float64) * self.step
        values[-1] = self.two_theta_max
        return values

    @property
    def calculation_range(self) -> tuple[float, float]:
        self.validate()
        return (
            self.two_theta_min - self.peak_calculation_padding_deg,
            self.two_theta_max + self.peak_calculation_padding_deg,
        )


@dataclass(frozen=True)
class IndependentParameterization:
    """Frozen four-coordinate mapping used by the independent renderer."""

    q_min: float = -1.0
    q_max: float = 1.0
    du_half_range: float = 0.01
    dv_half_range: float = 0.01
    delta_half_range_deg: float = 0.2
    fwhm_min_deg: float = 0.08
    fwhm_max_deg: float = 0.2

    def validate(self) -> None:
        if not self.q_max > self.q_min:
            raise ValueError("q_max must exceed q_min")
        if self.du_half_range <= 0.0 or self.dv_half_range <= 0.0:
            raise ValueError("lattice-coordinate half ranges must be positive")
        if self.delta_half_range_deg <= 0.0:
            raise ValueError("zero-shift half range must be positive")
        if not self.fwhm_max_deg > self.fwhm_min_deg > 0.0:
            raise ValueError("FWHM limits must be positive and ordered")


@dataclass(frozen=True)
class IndependentPhysicalParameters:
    a: float
    c: float
    delta_two_theta_deg: float
    fwhm_deg: float


@dataclass(frozen=True)
class IndependentPeakTable:
    positions: np.ndarray
    intensities: np.ndarray
    metric_indices: np.ndarray
    reflection_count: int


def q_to_tetragonal_physical(
    q: Sequence[float],
    *,
    reference_a: float,
    reference_c: float,
    parameterization: IndependentParameterization = IndependentParameterization(),
) -> IndependentPhysicalParameters:
    """Map normalized q=(u, v, delta, log-FWHM) to physical values."""

    parameterization.validate()
    values = np.asarray(q, dtype=np.float64)
    if values.shape != (4,):
        raise ValueError("q must contain exactly four coordinates")
    if not np.isfinite(values).all():
        raise ValueError("q must be finite")
    if np.any(values < parameterization.q_min) or np.any(
        values > parameterization.q_max
    ):
        raise ValueError("q is outside the frozen domain")
    if reference_a <= 0.0 or reference_c <= 0.0:
        raise ValueError("reference lattice constants must be positive")

    u0 = (2.0 * math.log(reference_a) + math.log(reference_c)) / 3.0
    v0 = math.log(reference_c / reference_a)
    u = u0 + float(values[0]) * parameterization.du_half_range
    v = v0 + float(values[1]) * parameterization.dv_half_range
    a = math.exp(u - v / 3.0)
    c = math.exp(u + 2.0 * v / 3.0)
    delta = float(values[2]) * parameterization.delta_half_range_deg
    log_center = 0.5 * (
        math.log(parameterization.fwhm_min_deg)
        + math.log(parameterization.fwhm_max_deg)
    )
    log_half_range = 0.5 * (
        math.log(parameterization.fwhm_max_deg)
        - math.log(parameterization.fwhm_min_deg)
    )
    fwhm = math.exp(log_center + float(values[3]) * log_half_range)
    return IndependentPhysicalParameters(
        a=a,
        c=c,
        delta_two_theta_deg=delta,
        fwhm_deg=fwhm,
    )


def enumerate_signed_tetragonal_hkls(
    *,
    a: float,
    c: float,
    wavelength_angstrom: float,
    two_theta_range: tuple[float, float],
) -> np.ndarray:
    """Enumerate every signed integer hkl inside one Bragg-angle window."""

    if a <= 0.0 or c <= 0.0 or wavelength_angstrom <= 0.0:
        raise ValueError("lattice constants and wavelength must be positive")
    minimum, maximum = (float(value) for value in two_theta_range)
    if not 0.0 <= minimum < maximum < 180.0:
        raise ValueError("two-theta range must be ordered inside [0, 180)")
    minimum_g = 2.0 * math.sin(math.radians(minimum / 2.0)) / wavelength_angstrom
    maximum_g = 2.0 * math.sin(math.radians(maximum / 2.0)) / wavelength_angstrom
    h_limit = int(math.ceil(maximum_g * a))
    l_limit = int(math.ceil(maximum_g * c))

    reflections: list[tuple[int, int, int]] = []
    tolerance = 16.0 * np.finfo(np.float64).eps * max(1.0, maximum_g)
    for h in range(-h_limit, h_limit + 1):
        for k in range(-h_limit, h_limit + 1):
            for ell in range(-l_limit, l_limit + 1):
                if h == 0 and k == 0 and ell == 0:
                    continue
                g_hkl = math.sqrt((h * h + k * k) / (a * a) + ell * ell / (c * c))
                if minimum_g - tolerance <= g_hkl <= maximum_g + tolerance:
                    reflections.append((h, k, ell))
    reflections.sort(
        key=lambda value: (
            value[0] * value[0] + value[1] * value[1],
            value[2] * value[2],
            value,
        )
    )
    if not reflections:
        return np.empty((0, 3), dtype=np.int64)
    return np.asarray(reflections, dtype=np.int64)


def _flatten_structure_species(
    structure: Structure,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    atomic_numbers: list[float] = []
    coefficients: list[np.ndarray] = []
    fractional_coordinates: list[np.ndarray] = []
    occupancies: list[float] = []
    for site in structure:
        for specie, occupancy in site.species.items():
            try:
                coefficient = np.asarray(
                    ATOMIC_SCATTERING_PARAMS[specie.symbol], dtype=np.float64
                )
            except KeyError as error:
                raise ValueError(
                    f"missing Pymatgen XRD scattering coefficients for {specie.symbol}"
                ) from error
            atomic_numbers.append(float(specie.Z))
            coefficients.append(coefficient)
            fractional_coordinates.append(
                np.asarray(site.frac_coords, dtype=np.float64)
            )
            occupancies.append(float(occupancy))
    if not atomic_numbers:
        raise ValueError("structure contains no scattering species")
    return (
        np.asarray(atomic_numbers, dtype=np.float64),
        np.asarray(coefficients, dtype=np.float64),
        np.asarray(fractional_coordinates, dtype=np.float64),
        np.asarray(occupancies, dtype=np.float64),
    )


def structure_factor_modulus_squared(
    structure: Structure,
    hkls: np.ndarray,
    *,
    a: float,
    c: float,
    chunk_size: int = 4096,
) -> np.ndarray:
    """Evaluate |F_hkl|^2 directly from sites and tabulated form factors."""

    reflections = np.asarray(hkls, dtype=np.int64)
    if reflections.ndim != 2 or reflections.shape[1] != 3:
        raise ValueError("hkls must have shape (n, 3)")
    if a <= 0.0 or c <= 0.0:
        raise ValueError("lattice constants must be positive")
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if len(reflections) == 0:
        return np.empty(0, dtype=np.float64)

    atomic_numbers, coefficients, fractional_coordinates, occupancies = (
        _flatten_structure_species(structure)
    )
    output = np.empty(len(reflections), dtype=np.float64)
    for start in range(0, len(reflections), chunk_size):
        stop = min(len(reflections), start + chunk_size)
        block = reflections[start:stop].astype(np.float64, copy=False)
        g_squared = (
            (block[:, 0] * block[:, 0] + block[:, 1] * block[:, 1]) / (a * a)
            + block[:, 2] * block[:, 2] / (c * c)
        )
        s_squared = g_squared / 4.0
        exponential = np.exp(
            -s_squared[:, None, None] * coefficients[None, :, :, 1]
        )
        scattering = atomic_numbers[None, :] - 41.78214 * s_squared[:, None] * (
            coefficients[None, :, :, 0] * exponential
        ).sum(axis=2)
        phase_argument = block @ fractional_coordinates.T
        phase = np.exp(2j * math.pi * phase_argument)
        structure_factor = (
            scattering * occupancies[None, :] * phase
        ).sum(axis=1)
        output[start:stop] = np.abs(structure_factor) ** 2
    return output


def render_truncated_gaussian_profile(
    positions: Sequence[float],
    intensities: Sequence[float],
    axis: np.ndarray,
    *,
    fwhm_deg: float,
    truncate_sigma: float = 5.0,
    normalize: bool = True,
) -> np.ndarray:
    """Render area-stable Gaussian peaks without project-simulator reuse."""

    centers = np.asarray(positions, dtype=np.float64)
    amplitudes = np.asarray(intensities, dtype=np.float64)
    grid = np.asarray(axis, dtype=np.float64)
    if centers.ndim != 1 or amplitudes.shape != centers.shape:
        raise ValueError("positions and intensities must be matching vectors")
    if grid.ndim != 1 or len(grid) < 2 or not np.all(np.diff(grid) > 0.0):
        raise ValueError("axis must be a strictly increasing vector")
    if not fwhm_deg > 0.0 or not truncate_sigma > 0.0:
        raise ValueError("FWHM and truncation radius must be positive")
    if not np.isfinite(centers).all() or not np.isfinite(amplitudes).all():
        raise ValueError("peak table must be finite")

    profile = np.zeros_like(grid, dtype=np.float64)
    sigma = fwhm_deg / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    radius = truncate_sigma * sigma
    for center, amplitude in zip(centers, amplitudes, strict=True):
        lower = int(np.searchsorted(grid, center - radius, side="left"))
        upper = int(np.searchsorted(grid, center + radius, side="right"))
        if lower >= upper:
            continue
        z = (grid[lower:upper] - center) / sigma
        profile[lower:upper] += (amplitude / sigma) * np.exp(-0.5 * z * z)
    if not normalize:
        return profile
    maximum = float(np.max(profile)) if profile.size else 0.0
    if not np.isfinite(maximum) or maximum <= 0.0:
        return np.zeros_like(profile)
    return profile / maximum


class IndependentTetragonalRenderer:
    """NumPy-only physics implementation for the sealed Week-4 renderer test."""

    def __init__(
        self,
        *,
        grid: IndependentGrid = IndependentGrid(),
        parameterization: IndependentParameterization = IndependentParameterization(),
        scaled_intensity_fraction_min: float = 1.0e-5,
        gaussian_truncate_sigma: float = 5.0,
    ) -> None:
        grid.validate()
        parameterization.validate()
        if not 0.0 <= scaled_intensity_fraction_min < 1.0:
            raise ValueError("scaled-intensity cutoff must be inside [0, 1)")
        if gaussian_truncate_sigma <= 0.0:
            raise ValueError("Gaussian truncation radius must be positive")
        self.grid = grid
        self.parameterization = parameterization
        self.scaled_intensity_fraction_min = float(scaled_intensity_fraction_min)
        self.gaussian_truncate_sigma = float(gaussian_truncate_sigma)

    @staticmethod
    def _validate_reference_structure(structure: Structure) -> None:
        lattice = structure.lattice
        scale = max(abs(float(lattice.a)), abs(float(lattice.b)), 1.0)
        if abs(float(lattice.a) - float(lattice.b)) / scale > 1.0e-6:
            raise ValueError("independent renderer requires a conventional tetragonal cell")
        if any(abs(float(angle) - 90.0) > 1.0e-6 for angle in lattice.angles):
            raise ValueError("independent renderer requires orthogonal tetragonal axes")

    def ideal_peaks(
        self, structure: Structure, q: Sequence[float]
    ) -> IndependentPeakTable:
        """Build shifted ideal peaks without using XRDCalculator or cached peaks."""

        self._validate_reference_structure(structure)
        physical = q_to_tetragonal_physical(
            q,
            reference_a=float(structure.lattice.a),
            reference_c=float(structure.lattice.c),
            parameterization=self.parameterization,
        )
        hkls = enumerate_signed_tetragonal_hkls(
            a=physical.a,
            c=physical.c,
            wavelength_angstrom=self.grid.wavelength_angstrom,
            two_theta_range=self.grid.calculation_range,
        )
        if len(hkls) == 0:
            return IndependentPeakTable(
                positions=np.empty(0, dtype=np.float64),
                intensities=np.empty(0, dtype=np.float64),
                metric_indices=np.empty((0, 2), dtype=np.int64),
                reflection_count=0,
            )

        h_squared = hkls[:, 0] * hkls[:, 0] + hkls[:, 1] * hkls[:, 1]
        l_squared = hkls[:, 2] * hkls[:, 2]
        metric_keys = np.column_stack((h_squared, l_squared))
        unique_keys, inverse = np.unique(metric_keys, axis=0, return_inverse=True)
        modulus_squared = structure_factor_modulus_squared(
            structure, hkls, a=physical.a, c=physical.c
        )
        reciprocal_length = np.sqrt(
            h_squared / (physical.a * physical.a)
            + l_squared / (physical.c * physical.c)
        )
        theta = np.arcsin(
            np.clip(
                self.grid.wavelength_angstrom * reciprocal_length / 2.0,
                0.0,
                1.0,
            )
        )
        lorentz = (1.0 + np.cos(2.0 * theta) ** 2) / (
            np.sin(theta) ** 2 * np.cos(theta)
        )
        reflection_intensity = modulus_squared * lorentz
        grouped_intensity = np.bincount(
            inverse, weights=reflection_intensity, minlength=len(unique_keys)
        ).astype(np.float64, copy=False)

        grouped_reciprocal_length = np.sqrt(
            unique_keys[:, 0] / (physical.a * physical.a)
            + unique_keys[:, 1] / (physical.c * physical.c)
        )
        argument = self.grid.wavelength_angstrom * grouped_reciprocal_length / 2.0
        positions = np.degrees(2.0 * np.arcsin(np.clip(argument, 0.0, 1.0)))
        positions = positions + physical.delta_two_theta_deg
        strongest = float(np.max(grouped_intensity)) if len(grouped_intensity) else 0.0
        keep = (
            np.isfinite(grouped_intensity)
            & (grouped_intensity > strongest * self.scaled_intensity_fraction_min)
            & (argument > 0.0)
            & (argument < 1.0)
        )
        order = np.argsort(positions[keep], kind="mergesort")
        return IndependentPeakTable(
            positions=positions[keep][order],
            intensities=grouped_intensity[keep][order],
            metric_indices=unique_keys[keep][order],
            reflection_count=int(len(hkls)),
        )

    def render(self, structure: Structure, q: Sequence[float]) -> np.ndarray:
        physical = q_to_tetragonal_physical(
            q,
            reference_a=float(structure.lattice.a),
            reference_c=float(structure.lattice.c),
            parameterization=self.parameterization,
        )
        peaks = self.ideal_peaks(structure, q)
        return render_truncated_gaussian_profile(
            peaks.positions,
            peaks.intensities,
            self.grid.axis,
            fwhm_deg=physical.fwhm_deg,
            truncate_sigma=self.gaussian_truncate_sigma,
            normalize=True,
        )
