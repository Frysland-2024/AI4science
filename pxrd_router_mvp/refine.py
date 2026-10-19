"""Bounded single-prototype lattice and nuisance fit."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from scipy.optimize import least_squares

from .candidates import Candidate
from .crystal import render


@dataclass(frozen=True)
class FitResult:
    candidate_id: str
    candidate: str
    crystal_system: str
    score_rmse: float
    a_angstrom: float
    c_angstrom: float | None
    zero_shift_deg: float
    fwhm_deg: float
    scale: float
    background: float
    success: bool
    solver_message: str
    iterations: int
    residual: np.ndarray
    predicted: np.ndarray

    def summary(self) -> dict:
        result = asdict(self)
        result.pop("residual")
        result.pop("predicted")
        return result


def fit_candidate(candidate: Candidate, two_theta: np.ndarray, intensity: np.ndarray,
                  wavelength_angstrom: float, *, prior: dict[str, float] | None = None) -> FitResult:
    crystal = candidate.load()
    x = np.asarray(two_theta, dtype=np.float64)
    y = np.asarray(intensity, dtype=np.float64)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 16 or not np.all(np.diff(x) > 0):
        raise ValueError("fit input requires matching vectors on an increasing 2theta axis")
    yn = y / float(np.max(y))
    low_scale = 1.0 - candidate.lattice_tolerance
    high_scale = 1.0 + candidate.lattice_tolerance
    if crystal.crystal_system == "cubic":
        x0 = np.array([crystal.a, 0.0, 0.14, 0.95, min(0.1, float(np.quantile(yn, 0.1)))])
        lower = [crystal.a * low_scale, -0.25, 0.05, 0.4, 0.0]
        upper = [crystal.a * high_scale, 0.25, 0.45, 1.6, 0.25]
        def render_params(p):
            lattice, shift, width, scale, background = p
            raw = render(crystal, x, wavelength_angstrom, a=lattice, c=lattice, zero_shift=shift, fwhm=width)
            return scale * raw + background
        lattice_count = 1
    else:
        x0 = np.array([crystal.a, crystal.c, 0.0, 0.14, 0.95, min(0.1, float(np.quantile(yn, 0.1)))])
        lower = [crystal.a * low_scale, crystal.c * low_scale, -0.25, 0.05, 0.4, 0.0]
        upper = [crystal.a * high_scale, crystal.c * high_scale, 0.25, 0.45, 1.6, 0.25]
        def render_params(p):
            a, c, shift, width, scale, background = p
            raw = render(crystal, x, wavelength_angstrom, a=a, c=c, zero_shift=shift, fwhm=width)
            return scale * raw + background
        lattice_count = 2
    # Use a lower-resolution internal mesh only for optimization when the input
    # exceeds 2500 points, then evaluate the final fitted model on the full axis.
    if len(x) > 2500:
        fit_x = np.linspace(x[0], x[-1], 2500)
        fit_y = np.interp(fit_x, x, yn)
        original_render = render_params
        if lattice_count == 1:
            def render_fit(p):
                lattice, shift, width, scale, background = p
                raw = render(crystal, fit_x, wavelength_angstrom, a=lattice, c=lattice, zero_shift=shift, fwhm=width)
                return scale * raw + background
        else:
            def render_fit(p):
                a, c, shift, width, scale, background = p
                raw = render(crystal, fit_x, wavelength_angstrom, a=a, c=c, zero_shift=shift, fwhm=width)
                return scale * raw + background
    else:
        fit_x, fit_y, render_fit = x, yn, render_params
    solution = least_squares(lambda p: render_fit(p) - fit_y, x0, bounds=(lower, upper),
                             x_scale="jac", max_nfev=60, ftol=2e-6, xtol=2e-6, gtol=2e-6)
    p = solution.x
    predicted = render_params(p)
    residual = yn - predicted
    rmse = float(np.sqrt(np.mean(residual**2)))
    if lattice_count == 1:
        lattice, shift, width, scale, background = p
        a, c_value = float(lattice), None
    else:
        a, c, shift, width, scale, background = p
        c_value = float(c)
    # The prior is only a tie-break sized term. It is separately logged and all
    # physical candidates remain in the returned list.
    return FitResult(candidate.id, candidate.name, candidate.crystal_system, rmse, float(a), c_value,
                     float(shift), float(width), float(scale), float(background), bool(solution.success),
                     str(solution.message), int(solution.nfev), residual, predicted)
