"""Bounded, single-phase forward-parameter fitting for the W0 smoke demo.

This module deliberately fits only lattice metrics and a global 2theta zero
shift. It is numerical plumbing for the simulated pilot, not a calibrated
refinement method or a predictor of parameter uncertainty.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def fit_candidate_parameters(
    cif_path: str | Path,
    observed: Any,
    instrument: dict[str, Any],
    measurement: dict[str, float],
    *,
    expected_space_group: dict[str, Any],
    robustness_source: str | Path,
    lattice_fractional_span: float = 0.005,
    zero_shift_bounds_deg: tuple[float, float] = (-0.05, 0.05),
    max_nfev: int = 40,
) -> dict[str, Any]:
    """Fit one candidate's allowed cell metrics and global axis offset.

    The fit holds atomic fractional coordinates, peak width, background model,
    and background amplitude fixed. Bounds are demo search limits centered on
    the reference CIF; they are not literature uncertainty intervals or
    physically validated priors.
    """
    try:
        from pymatgen.core import Lattice, Structure
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        from scipy.optimize import least_squares
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("install xrd-pre-refinement[science] to run the bounded fit") from exc

    profile = np.asarray(observed, dtype=np.float64)
    if profile.ndim != 1 or profile.size < 2 or not np.isfinite(profile).all():
        raise ValueError("observed must be a finite one-dimensional profile")
    if not 0.0 < lattice_fractional_span < 0.1:
        raise ValueError("lattice_fractional_span must be in (0, 0.1)")
    zero_lower, zero_upper = map(float, zero_shift_bounds_deg)
    if not np.isfinite([zero_lower, zero_upper]).all() or zero_lower >= zero_upper:
        raise ValueError("zero_shift_bounds_deg must be finite and increasing")
    if max_nfev < 1:
        raise ValueError("max_nfev must be positive")

    import sys

    source = str(Path(robustness_source).resolve())
    if source not in sys.path:
        sys.path.insert(0, source)
    try:
        from xrd_robustness.physics import PhysicsParameters
        from xrd_robustness.simulator import (
            SimulationGrid,
            ideal_peak_table,
            simulate_from_peak_table,
        )
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError("could not import the repository PXRD forward simulator") from exc

    reference = Structure.from_file(str(cif_path))
    analyzer = SpacegroupAnalyzer(reference, symprec=0.01, angle_tolerance=5)
    actual_symbol = analyzer.get_space_group_symbol()
    actual_number = int(analyzer.get_space_group_number())
    if (
        actual_symbol != expected_space_group["symbol"]
        or actual_number != int(expected_space_group["number"])
    ):
        raise ValueError(
            f"CIF symmetry mismatch: expected {expected_space_group['symbol']} "
            f"({expected_space_group['number']}), found {actual_symbol} ({actual_number})"
        )

    if actual_symbol == "Pm-3m":
        variable_names = ["a_angstrom", "delta_2theta_deg"]
        reference_values = [float(reference.lattice.a), 0.0]
        metric = "cubic_a_equals_b_equals_c"
    elif actual_symbol == "P4mm":
        variable_names = ["a_angstrom", "c_angstrom", "delta_2theta_deg"]
        reference_values = [float(reference.lattice.a), float(reference.lattice.c), 0.0]
        metric = "tetragonal_a_equals_b"
    else:
        raise ValueError(f"W0 bounded fitter supports only Pm-3m and P4mm, got {actual_symbol}")

    lattice_reference = np.asarray(reference_values[:-1], dtype=np.float64)
    lower = np.concatenate(
        (lattice_reference * (1.0 - lattice_fractional_span), [zero_lower])
    )
    upper = np.concatenate(
        (lattice_reference * (1.0 + lattice_fractional_span), [zero_upper])
    )
    initial = np.asarray(reference_values, dtype=np.float64)
    if profile.shape != SimulationGrid(
        two_theta_min=float(instrument["two_theta_min_deg"]),
        two_theta_max=float(instrument["two_theta_max_deg"]),
        step=float(instrument["step_deg"]),
        wavelength=float(instrument["wavelength_angstrom"]),
    ).values.shape:
        raise ValueError("observed length does not match configured simulation grid")

    grid = SimulationGrid(
        two_theta_min=float(instrument["two_theta_min_deg"]),
        two_theta_max=float(instrument["two_theta_max_deg"]),
        step=float(instrument["step_deg"]),
        wavelength=float(instrument["wavelength_angstrom"]),
    )

    def render(parameters: np.ndarray) -> np.ndarray:
        if metric == "cubic_a_equals_b_equals_c":
            a = float(parameters[0])
            b = c = a
        else:
            a = b = float(parameters[0])
            c = float(parameters[1])
        structure = Structure(
            Lattice.from_parameters(a, b, c, 90.0, 90.0, 90.0),
            reference.species_and_occu,
            reference.frac_coords,
            site_properties=reference.site_properties,
        )
        peak_table = ideal_peak_table(structure, grid)
        params = PhysicsParameters(
            delta_2theta_deg=float(parameters[-1]),
            fwhm_deg=float(measurement["fwhm_deg"]),
            background_to_peak_ratio=float(measurement["background_to_peak_ratio"]),
            noise_std_ratio=0.0,
            background_type="polynomial",
            severity_level=0,
            zero_shift_active=True,
            broadening_active=True,
            background_active=True,
            noise_active=False,
        )
        result = simulate_from_peak_table(
            peak_table.positions,
            peak_table.intensities,
            params,
            rng_seed=0,
            grid=grid,
            reflection_table=peak_table,
        )
        return np.asarray(result, dtype=np.float64)

    target_scale = max(float(np.sqrt(np.mean(np.square(profile)))), 1e-12)

    def residual(parameters: np.ndarray) -> np.ndarray:
        return (render(parameters) - profile) / target_scale

    initial_profile = render(initial)
    initial_nrmse = float(np.sqrt(np.mean(np.square((initial_profile - profile) / target_scale))))
    result = least_squares(
        residual,
        initial,
        bounds=(lower, upper),
        x_scale="jac",
        max_nfev=int(max_nfev),
    )
    fitted_profile = render(result.x)
    fitted_nrmse = float(np.sqrt(np.mean(np.square((fitted_profile - profile) / target_scale))))
    return {
        "status": "LIMITED_FORWARD_FIT_DEMO",
        "optimizer": "scipy.optimize.least_squares",
        "objective": "normalized_rmse_on_full_profile",
        "candidate_space_group": {"symbol": actual_symbol, "number": actual_number},
        "cell_metric_constraint": metric,
        "fitted_parameter_names": variable_names,
        "initial_values": {name: float(value) for name, value in zip(variable_names, initial, strict=True)},
        "fitted_values": {name: float(value) for name, value in zip(variable_names, result.x, strict=True)},
        "search_bounds": {
            name: [float(lo), float(hi)]
            for name, lo, hi in zip(variable_names, lower, upper, strict=True)
        },
        "bound_basis": (
            f"engineering demo box: lattice metrics +/-{lattice_fractional_span:.3%} "
            f"about reference CIF; zero shift [{zero_lower}, {zero_upper}] deg; "
            "not an evidence-backed prior or prediction interval"
        ),
        "fixed_parameters": {
            "fractional_coordinates": "reference CIF",
            "fwhm_deg": float(measurement["fwhm_deg"]),
            "background_to_peak_ratio": float(measurement["background_to_peak_ratio"]),
            "noise_in_forward_reconstruction": 0.0,
        },
        "fit_success": bool(result.success),
        "optimizer_message": str(result.message),
        "function_evaluations": int(result.nfev),
        "normalized_rmse_before": initial_nrmse,
        "normalized_rmse_after": fitted_nrmse,
        "parameter_interval": None,
        "parameter_interval_status": "NOT_ESTIMATED",
        "fitted_forward_profile": fitted_profile.tolist(),
        "residual_observed_minus_fitted": (profile - fitted_profile).tolist(),
        "interpretation": (
            "One synthetic profile and one bounded single-phase fit; no calibration, "
            "identifiability assessment, uncertainty estimate, or experimental validation."
        ),
    }
