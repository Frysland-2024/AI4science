"""Physics-preservation checks for candidate perturbation views."""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from .physics import PhysicsParameters
from .simulator import render_gaussian_peaks


def _top_positions(positions: Sequence[float], intensities: Sequence[float], top_k: int) -> np.ndarray:
    positions = np.asarray(positions, dtype=np.float64)
    intensities = np.asarray(intensities, dtype=np.float64)
    order = np.argsort(intensities)[::-1][: min(top_k, len(positions))]
    return np.sort(positions[order])


def _local_contrast(profile: np.ndarray, grid: np.ndarray, center: float, radius: float) -> float:
    """Estimate peak contrast against a local baseline."""
    outer = (grid >= center - radius) & (grid <= center + radius)
    if not np.any(outer):
        return 0.0
    inner_radius = max(0.04, 2.0 * float(grid[1] - grid[0]))
    inner = outer & (np.abs(grid - center) <= inner_radius)
    if not np.any(inner):
        return 0.0
    outer_baseline = outer & ~inner
    baseline = float(np.median(profile[outer_baseline])) if np.any(outer_baseline) else 0.0
    return max(0.0, float(np.max(profile[inner])) - baseline)


def inspect_perturbed_view(
    base_profile: np.ndarray,
    perturbed_profile: np.ndarray,
    *,
    peak_positions: Sequence[float],
    peak_intensities: Sequence[float],
    grid: np.ndarray,
    parameters: PhysicsParameters,
    top_k: int = 20,
    recall_threshold: float = 0.80,
    retained_threshold: float = 0.95,
    clipping_fraction_max: float = 0.55,
    simulation_diagnostics: dict[str, float | int | bool] | None = None,
    base_fwhm_deg: float = 0.08,
) -> dict[str, Any]:
    """Return auditable checks; thresholds are project gates, not physical constants."""
    base = np.asarray(base_profile, dtype=np.float64)
    perturbed = np.asarray(perturbed_profile, dtype=np.float64)
    grid = np.asarray(grid, dtype=np.float64)
    reasons: list[str] = []
    diagnostics = simulation_diagnostics or {}
    clipped_fraction = float(diagnostics.get("clipped_fraction", 0.0))
    clipping_gate_applicable = bool(diagnostics)
    negative_noise_tail = bool(
        parameters.noise_active
        and (
            (parameters.noise_model == "additive_gaussian" and parameters.noise_std_ratio > 0.0)
            or parameters.electronic_noise_std_ratio > 0.0
            or parameters.electronic_noise_std_counts > 0.0
        )
    )
    if not clipping_gate_applicable:
        clipping_ok = True
    elif not negative_noise_tail:
        clipping_ok = clipped_fraction <= 1e-12
    else:
        clipping_ok = clipped_fraction <= clipping_fraction_max
    if not clipping_ok:
        reasons.append("clipping_fraction_above_threshold")
    finite = bool(np.isfinite(perturbed).all() and np.isfinite(base).all())
    nonnegative = bool(np.min(perturbed) >= -1e-8)
    shape_ok = bool(base.shape == perturbed.shape == grid.shape)
    if not finite:
        reasons.append("non_finite")
    if not nonnegative:
        reasons.append("negative_intensity")
    if not shape_ok:
        reasons.append("shape_mismatch")
    if not shape_ok or not finite:
        return {
            "finite": finite,
            "nonnegative": nonnegative,
            "peak_order_preserved": False,
            "top20_peak_recall": 0.0,
            "window_intensity_retained": 0.0,
            "window_gate_applicable": False,
            "clipped_fraction": clipped_fraction,
            "clipping_gate_applicable": clipping_gate_applicable,
            "clipping_ok": clipping_ok,
            "passed": False,
            "reasons": reasons,
        }

    expected_positions = _top_positions(peak_positions, peak_intensities, top_k)
    expected_positions = expected_positions + parameters.delta_2theta_deg
    radius = max(0.12, 2.0 * parameters.fwhm_deg)
    matched_positions: list[float] = []
    detected = 0
    for expected in expected_positions:
        mask = (grid >= expected - radius) & (grid <= expected + radius)
        if not np.any(mask):
            continue
        local = perturbed[mask]
        local_grid = grid[mask]
        local_contrast = _local_contrast(perturbed, grid, expected, radius)
        base_contrast = _local_contrast(base, grid, expected - parameters.delta_2theta_deg, radius)
        # The floor is deliberately relative to the base profile. A global
        # threshold would erase weak but legitimate Bragg peaks.
        threshold = max(0.10 * base_contrast, 1e-6)
        if local_contrast >= threshold:
            detected += 1
            matched_positions.append(float(local_grid[int(np.argmax(local))]))
    recall = detected / max(1, len(expected_positions))
    peak_order = bool(np.all(np.diff(matched_positions) >= -float(grid[1] - grid[0]))) if matched_positions else False
    base_signal = render_gaussian_peaks(
        peak_positions,
        peak_intensities,
        grid,
        base_fwhm_deg,
        normalize=False,
    )
    perturbed_signal = render_gaussian_peaks(
        np.asarray(peak_positions, dtype=np.float64) + parameters.delta_2theta_deg,
        peak_intensities,
        grid,
        parameters.fwhm_deg,
        normalize=False,
    )
    base_signal_area = float(np.sum(np.clip(base_signal, 0.0, None)))
    perturbed_signal_area = float(np.sum(np.clip(perturbed_signal, 0.0, None)))
    retained = perturbed_signal_area / base_signal_area if base_signal_area > 0 else 0.0
    observed_base_area = float(np.sum(np.clip(base, 0.0, None)))
    observed_perturbed_area = float(np.sum(np.clip(perturbed, 0.0, None)))
    observed_area_ratio = (
        observed_perturbed_area / observed_base_area if observed_base_area > 0 else 0.0
    )
    window_gate_applicable = True
    if not peak_order:
        reasons.append("peak_order_not_preserved")
    if recall < recall_threshold:
        reasons.append("top20_recall_below_threshold")
    if window_gate_applicable and retained < retained_threshold:
        reasons.append("window_intensity_below_threshold")
    return {
        "finite": finite,
        "nonnegative": nonnegative,
        "peak_order_preserved": peak_order,
        "top20_peak_recall": float(recall),
        "window_intensity_retained": float(retained),
        "window_gate_applicable": window_gate_applicable,
        "observed_window_area_ratio": float(observed_area_ratio),
        "clipped_fraction": clipped_fraction,
        "clipping_gate_applicable": clipping_gate_applicable,
        "clipping_ok": clipping_ok,
        "passed": not reasons,
        "reasons": reasons,
    }
