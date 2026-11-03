"""Versioned physical pseudo-Voigt renderer for cached PXRD peak tables.

This is an opt-in renderer. It keeps the V9 peak calculation, global zero
shift, March-Dollase reflection weighting, background, and detector-noise
stages, and replaces only the line-profile kernel. No upstream source code is
copied. The implementation was independently written after reviewing:

* SimXRD/Pysimxrd v1.0.0, commit 821f145ac3f04a1dfe91cc813a31216c14cd74a5
  (MIT, https://github.com/Bin-Cao/SimXRD/tree/821f145ac3f04a1dfe91cc813a31216c14cd74a5):
  unit-area Voigt/profile accumulation patterns.
* GSAS-II v5.10.3/5848, commit c2d75dd05041a1710acdb942827f1d2a00a62a59
  (Argonne open-source license,
  https://github.com/AdvancedPhotonSource/GSAS-II/tree/c2d75dd05041a1710acdb942827f1d2a00a62a59):
  separation of instrumental and specimen broadening, Caglioti U/V/W,
  crystallite size, and microstrain terms.
* ML4pXRDs commit a50f2a0ff87c122c0bbf25755268966618832396 (MIT,
  https://github.com/aimat-lab/ML4pXRDs/tree/a50f2a0ff87c122c0bbf25755268966618832396):
  localized peak accumulation and the benefit of keeping ideal peaks cached.
* PhaseSmith 0.7.0, commit 447a869c6a58632a338739829c9772fb55668cb2 (MIT):
  normalized pseudo-Voigt and Thompson-Cox-Hastings (TCH) equations
  (https://github.com/CPrescher/PhaseSmith/tree/447a869c6a58632a338739829c9772fb55668cb2).

All widths below are in degrees of 2theta except where explicitly converted:
lambda and crystallite size use Angstrom and nanometre, respectively;
microstrain is dimensionless delta-d/d. The default wavelength 1.54184 A is
the effective CuKa wavelength used by pymatgen's existing ``CuKa`` grid.
"""

from __future__ import annotations

from functools import partial
import hashlib
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .physics import PhysicsParameters
from .simulation_interfaces import PeakTable
from .simulator import SimulationGrid, simulate_from_peak_table


SIMULATOR_VERSION = "v11_tch_pseudo_voigt"

DEFAULT_LINE_PROFILE: dict[str, Any] = {
    "kind": "tch_pseudo_voigt_v1",
    "wavelength_angstrom": 1.54184,
    "scherrer_shape_factor": 0.9,
    "caglioti_u_deg2": 0.0012,
    "caglioti_v_deg2": 0.0004,
    "crystallite_size_nm": {
        "distribution": "uniform",
        "min_value": 50.0,
        "max_value": 200.0,
    },
    "microstrain": {
        "distribution": "uniform",
        "min_value": 1.0e-5,
        "max_value": 2.0e-4,
    },
    "use_scherrer": True,
    "use_microstrain": True,
    "truncate_fwhm": 50.0,
}


def resolve_line_profile(config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Merge and validate one explicit V11 line-profile configuration."""
    raw = dict(config or {})
    result = {**DEFAULT_LINE_PROFILE, **raw}
    for key in ("crystallite_size_nm", "microstrain"):
        if key in raw:
            result[key] = dict(raw[key])
        else:
            result[key] = dict(DEFAULT_LINE_PROFILE[key])
    if result["kind"] != "tch_pseudo_voigt_v1":
        raise ValueError(f"unsupported V11 line-profile kind: {result['kind']!r}")
    numeric = (
        "wavelength_angstrom",
        "scherrer_shape_factor",
        "caglioti_u_deg2",
        "caglioti_v_deg2",
        "truncate_fwhm",
    )
    for name in numeric:
        result[name] = float(result[name])
        if not math.isfinite(result[name]):
            raise ValueError(f"{name} must be finite")
    if result["wavelength_angstrom"] <= 0.0:
        raise ValueError("wavelength_angstrom must be positive")
    if result["scherrer_shape_factor"] <= 0.0:
        raise ValueError("scherrer_shape_factor must be positive")
    if result["caglioti_u_deg2"] < 0.0 or result["caglioti_v_deg2"] < 0.0:
        raise ValueError("Caglioti U and V must be non-negative in this isotropic model")
    if result["truncate_fwhm"] < 10.0:
        raise ValueError("truncate_fwhm must be at least 10 to retain Lorentzian tails")
    for key, allow_zero in (("crystallite_size_nm", False), ("microstrain", True)):
        _validate_range(result[key], key, allow_zero=allow_zero)
    result["use_scherrer"] = bool(result["use_scherrer"])
    result["use_microstrain"] = bool(result["use_microstrain"])
    return result


def _validate_range(value: Mapping[str, Any], name: str, *, allow_zero: bool) -> None:
    distribution = str(value.get("distribution", ""))
    if distribution not in {"fixed", "uniform", "log_uniform"}:
        raise ValueError(f"{name}.distribution must be fixed, uniform, or log_uniform")
    minimum = float(value["min_value"])
    maximum = float(value["max_value"])
    if not math.isfinite(minimum) or not math.isfinite(maximum) or maximum < minimum:
        raise ValueError(f"{name} range must be finite and ordered")
    if not allow_zero and minimum <= 0.0:
        raise ValueError(f"{name} must be positive")
    if allow_zero and minimum < 0.0:
        raise ValueError(f"{name} cannot be negative")
    if distribution == "fixed" and minimum != maximum:
        raise ValueError(f"fixed {name} range requires identical min/max")
    if distribution == "log_uniform" and minimum <= 0.0:
        raise ValueError(f"log_uniform {name} requires a positive minimum")


def _sample_range(value: Mapping[str, Any], rng: np.random.Generator) -> float:
    distribution = str(value["distribution"])
    minimum = float(value["min_value"])
    maximum = float(value["max_value"])
    if distribution == "fixed":
        return minimum
    if distribution == "log_uniform":
        return float(np.exp(rng.uniform(np.log(minimum), np.log(maximum))))
    return float(rng.uniform(minimum, maximum))


def sample_line_profile_parameters(
    line_profile: Mapping[str, Any] | None,
    *,
    rng_seed: int,
) -> dict[str, float]:
    """Sample specimen size/strain from a seed-specific independent stream."""
    config = resolve_line_profile(line_profile)
    seed_bytes = hashlib.sha256(
        f"{int(rng_seed)}:v11-line-profile-parameters".encode("ascii")
    ).digest()[:8]
    rng = np.random.default_rng(int.from_bytes(seed_bytes, "little", signed=False))
    return {
        "crystallite_size_nm": _sample_range(config["crystallite_size_nm"], rng),
        "microstrain": (
            _sample_range(config["microstrain"], rng)
            if config["use_microstrain"]
            else 0.0
        ),
    }


def calculate_tch_width_components(
    two_theta_deg: float,
    base_fwhm_deg: float,
    *,
    line_profile: Mapping[str, Any] | None = None,
    crystallite_size_nm: float,
    microstrain: float,
) -> dict[str, float]:
    """Return Caglioti Gaussian + Scherrer/strain Lorentzian TCH widths.

    ``H_G**2 = U*tan(theta)**2 + V*tan(theta) + W`` with degrees squared;
    ``W = base_fwhm_deg**2``. Isotropic Scherrer and Williamson-Hall terms are
    ``beta_size = K*lambda/(D*cos(theta))`` and
    ``beta_strain = 4*epsilon*tan(theta)`` in radians of 2theta, converted to
    degrees before the Lorentzian widths are added.
    """
    config = resolve_line_profile(line_profile)
    return _calculate_tch_width_components_resolved(
        two_theta_deg,
        base_fwhm_deg,
        config=config,
        crystallite_size_nm=crystallite_size_nm,
        microstrain=microstrain,
    )


def _calculate_tch_width_components_resolved(
    two_theta_deg: float,
    base_fwhm_deg: float,
    *,
    config: Mapping[str, Any],
    crystallite_size_nm: float,
    microstrain: float,
) -> dict[str, float]:
    """Inner width calculation for a validated profile config."""
    values = (two_theta_deg, base_fwhm_deg, crystallite_size_nm, microstrain)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("profile angle, base width, size, and strain must be finite")
    if not 0.0 < float(two_theta_deg) < 180.0:
        raise ValueError("two_theta_deg must be strictly between 0 and 180")
    if base_fwhm_deg <= 0.0 or crystallite_size_nm <= 0.0 or microstrain < 0.0:
        raise ValueError("base width and size must be positive; strain cannot be negative")

    theta = math.radians(float(two_theta_deg) / 2.0)
    tan_theta = math.tan(theta)
    cos_theta = math.cos(theta)
    h_g_sq = (
        config["caglioti_u_deg2"] * tan_theta * tan_theta
        + config["caglioti_v_deg2"] * tan_theta
        + float(base_fwhm_deg) ** 2
    )
    if not math.isfinite(h_g_sq) or h_g_sq <= 0.0:
        raise ValueError("Caglioti Gaussian variance must be positive at every peak")
    h_g = math.sqrt(h_g_sq)
    beta_size = 0.0
    if config["use_scherrer"]:
        # Convert D from nm to Angstrom to match wavelength units.
        beta_size_rad = (
            config["scherrer_shape_factor"]
            * config["wavelength_angstrom"]
            / (float(crystallite_size_nm) * 10.0 * cos_theta)
        )
        beta_size = math.degrees(beta_size_rad)
    beta_strain = (
        math.degrees(4.0 * float(microstrain) * tan_theta)
        if config["use_microstrain"]
        else 0.0
    )
    h_l = beta_size + beta_strain

    if h_l <= 1.0e-15:
        h = h_g
        eta = 0.0
    else:
        h = (
            h_g**5
            + 2.69269 * h_g**4 * h_l
            + 2.42843 * h_g**3 * h_l**2
            + 4.47163 * h_g**2 * h_l**3
            + 0.07842 * h_g * h_l**4
            + h_l**5
        ) ** 0.2
        ratio = h_l / h
        eta = min(
            1.0,
            max(
                0.0,
                1.36603 * ratio - 0.47719 * ratio**2 + 0.11116 * ratio**3,
            ),
        )
    return {
        "instrument_gaussian_fwhm_deg": h_g,
        "scherrer_fwhm_deg": beta_size,
        "microstrain_fwhm_deg": beta_strain,
        "specimen_lorentzian_fwhm_deg": h_l,
        "total_fwhm_deg": h,
        "lorentz_fraction": eta,
    }


def render_tch_pseudo_voigt_peaks(
    positions: Sequence[float],
    intensities: Sequence[float],
    grid: np.ndarray,
    base_fwhm_deg: float,
    *,
    line_profile: Mapping[str, Any] | None = None,
    crystallite_size_nm: float,
    microstrain: float,
    normalize: bool = True,
) -> np.ndarray:
    """Accumulate discretely area-normalized TCH pseudo-Voigt reflections."""
    config = resolve_line_profile(line_profile)
    axis = np.asarray(grid, dtype=np.float64)
    centers = np.asarray(positions, dtype=np.float64)
    areas = np.asarray(intensities, dtype=np.float64)
    if axis.ndim != 1 or axis.size < 2 or not np.isfinite(axis).all():
        raise ValueError("grid must be a finite one-dimensional axis with at least two points")
    steps = np.diff(axis)
    if not np.all(steps > 0.0) or not np.allclose(steps, steps[0], rtol=1e-7, atol=1e-10):
        raise ValueError("grid must be uniformly spaced and strictly increasing")
    if centers.ndim != 1 or areas.shape != centers.shape:
        raise ValueError("peak positions and intensities must be same-length vectors")
    if not np.isfinite(centers).all() or not np.isfinite(areas).all() or np.any(areas < 0.0):
        raise ValueError("peak positions/intensities must be finite and intensities non-negative")

    step = float(steps[0])
    output = np.zeros(axis.shape, dtype=np.float64)
    for center, area in zip(centers, areas, strict=True):
        if area <= 0.0:
            continue
        widths = _calculate_tch_width_components_resolved(
            float(center),
            float(base_fwhm_deg),
            config=config,
            crystallite_size_nm=float(crystallite_size_nm),
            microstrain=float(microstrain),
        )
        fwhm = widths["total_fwhm_deg"]
        eta = widths["lorentz_fraction"]
        radius = config["truncate_fwhm"] * fwhm

        # Normalize on a virtual grid extending beyond the measured window,
        # aligned to the output bins. This conserves integrated area without
        # incorrectly renormalizing the visible half of an edge peak.
        first = math.floor((float(center) - radius - float(axis[0])) / step)
        last = math.ceil((float(center) + radius - float(axis[0])) / step)
        indices = np.arange(first, last + 1, dtype=np.int64)
        offset = (float(axis[0]) + indices * step) - float(center)
        gaussian = (
            math.sqrt(4.0 * math.log(2.0) / math.pi)
            / fwhm
            * np.exp(-4.0 * math.log(2.0) * (offset / fwhm) ** 2)
        )
        lorentzian = (
            2.0
            / (math.pi * fwhm * (1.0 + 4.0 * (offset / fwhm) ** 2))
        )
        kernel = (1.0 - eta) * gaussian + eta * lorentzian
        discrete_area = float(kernel.sum(dtype=np.float64) * step)
        if not math.isfinite(discrete_area) or discrete_area <= 0.0:
            raise RuntimeError("pseudo-Voigt peak has invalid discrete area")
        kernel *= float(area) / discrete_area
        visible = (indices >= 0) & (indices < axis.size)
        output[indices[visible]] += kernel[visible]

    if normalize:
        maximum = float(output.max()) if output.size else 0.0
        return (output / maximum).astype(np.float32) if maximum > 0.0 else np.zeros(
            output.shape, dtype=np.float32
        )
    return output.astype(np.float32)


def simulate_from_peak_table_v11(
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
    """Render one V11 spectrum while reusing the stable V9 nuisance stages."""
    config = resolve_line_profile(line_profile)
    sampled = sample_line_profile_parameters(config, rng_seed=rng_seed)
    renderer = partial(
        render_tch_pseudo_voigt_peaks,
        line_profile=config,
        crystallite_size_nm=sampled["crystallite_size_nm"],
        microstrain=sampled["microstrain"],
    )
    result = simulate_from_peak_table(
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
    if not return_diagnostics:
        return result
    profile = {
        "simulator_version": SIMULATOR_VERSION,
        "wavelength_angstrom": config["wavelength_angstrom"],
        "crystallite_size_nm": sampled["crystallite_size_nm"],
        "microstrain_delta_d_over_d": sampled["microstrain"],
        "caglioti_u_deg2": config["caglioti_u_deg2"],
        "caglioti_v_deg2": config["caglioti_v_deg2"],
        "caglioti_w_deg2_source": "sampled_physics_fwhm_deg_squared",
        "scherrer_shape_factor": config["scherrer_shape_factor"],
        "truncate_fwhm": config["truncate_fwhm"],
        "peak_profile": "area_normalized_tch_pseudo_voigt_v1",
    }
    spectrum, diagnostics = result
    diagnostics = dict(diagnostics)
    diagnostics["line_profile"] = profile
    return spectrum, diagnostics


def make_peak_table_simulator(
    simulator_version: str,
    line_profile: Mapping[str, Any] | None = None,
):
    """Resolve a config version to a peak-table renderer; V9 remains default."""
    from .simulator import simulate_from_peak_table as legacy_renderer

    version = str(simulator_version or "v9_gaussian")
    if version == "v9_gaussian":
        return legacy_renderer
    if version == SIMULATOR_VERSION:
        config = resolve_line_profile(line_profile)
        return partial(simulate_from_peak_table_v11, line_profile=config)
    raise ValueError(f"unsupported simulator_version={version!r}")
