"""Deterministic all-candidate physical ranking and conditional refinement."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .candidates import Candidate, available_candidates
from .classifier_adapter import soft_system_adjustment
from .refine import FitResult, fit_candidate


@dataclass(frozen=True)
class RouteResult:
    results: tuple[FitResult, ...]
    evaluated_candidate_ids: tuple[str, ...]
    classifier_prior_used: bool
    warning: str


def route(two_theta: np.ndarray, intensity: np.ndarray, wavelength_angstrom: float, *,
          candidates: tuple[Candidate, ...] | None = None,
          crystal_system_prior: dict[str, float] | None = None,
          prior_weight: float = 0.02) -> RouteResult:
    selected = candidates or available_candidates()
    if not selected:
        raise ValueError("no verified candidate CIFs are available")
    # Every supported CIF is fitted regardless of classifier output.
    fits = [fit_candidate(c, two_theta, intensity, wavelength_angstrom) for c in selected]
    fits.sort(key=lambda result: (result.score_rmse + soft_system_adjustment(result.crystal_system, crystal_system_prior, prior_weight),
                                  result.score_rmse, result.candidate_id))
    best = fits[0]
    warning = ""
    if best.score_rmse >= 0.12:
        warning = "Low profile agreement: candidate set may not contain this phase, or data/instrument effects exceed this MVP."
    elif best.score_rmse >= 0.06:
        warning = "Moderate profile mismatch: inspect alternatives, axis, wavelength, background, and phase assumptions."
    return RouteResult(tuple(fits), tuple(c.id for c in selected), bool(crystal_system_prior), warning)


def top_three(result: RouteResult) -> tuple[FitResult, ...]:
    return result.results[:3]
