"""Explicit background and detector-noise models for PXRD simulation.

The V7 reference path explicitly supports polynomial or smooth stochastic
backgrounds together with Gaussian, Poisson, and Poisson-Gaussian observation
models. Every run records the selected model in its resolved configuration.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np


BACKGROUND_MODELS = frozenset({"flat", "polynomial", "gaussian_process"})
NOISE_MODELS = frozenset({"additive_gaussian", "poisson", "poisson_gaussian"})
NOISE_STAGES = frozenset({"before_normalization", "after_normalization"})


def _validate_axis(axis: np.ndarray) -> np.ndarray:
    values = np.asarray(axis, dtype=np.float64)
    if values.ndim != 1 or values.size == 0:
        raise ValueError("simulation axis must be a non-empty one-dimensional array")
    if not np.isfinite(values).all() or np.any(np.diff(values) <= 0):
        raise ValueError("simulation axis must be finite and strictly increasing")
    return values


def _normalized_axis(axis: np.ndarray) -> np.ndarray:
    values = _validate_axis(axis)
    span = float(values[-1] - values[0])
    if span <= 0:
        raise ValueError("simulation axis must span a positive range")
    return (values - values[0]) / span


def _normalize_nonnegative_shape(values: np.ndarray) -> np.ndarray:
    shape = np.asarray(values, dtype=np.float64)
    if not np.isfinite(shape).all():
        raise ValueError("background shape contains non-finite values")
    shape = shape - float(np.min(shape))
    maximum = float(np.max(shape)) if shape.size else 0.0
    if maximum <= 1e-12:
        return np.ones(shape.shape, dtype=np.float64)
    return shape / maximum


def _polynomial_shape(
    normalized_axis: np.ndarray,
    *,
    order: int,
    variation: float,
    rng: np.random.Generator,
) -> np.ndarray:
    centered = 2.0 * normalized_axis - 1.0
    base_coefficients = {0: 0.8, 1: 0.15, 2: 0.05}
    coefficients = np.zeros(order + 1, dtype=np.float64)
    for power, coefficient in base_coefficients.items():
        if power <= order:
            coefficients[power] = coefficient
    if variation > 0.0:
        # Coefficients are perturbed in coefficient space, not at individual
        # detector bins.  This keeps the baseline smooth and reproducible.
        scales = np.asarray(
            [0.10 if power == 0 else 0.12 / (power + 1.0) for power in range(order + 1)],
            dtype=np.float64,
        )
        coefficients += rng.normal(0.0, variation * scales)
    powers = np.vstack([centered**power for power in range(order + 1)])
    return np.sum(coefficients[:, None] * powers, axis=0)


def _gaussian_process_shape(
    normalized_axis: np.ndarray,
    *,
    variation: float,
    anchor_count: int,
    length_scale: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if anchor_count < 8:
        raise ValueError("background_anchor_count must be at least 8")
    if length_scale <= 0:
        raise ValueError("background_gp_length_scale must be positive")
    anchors, cholesky = _gaussian_process_basis(int(anchor_count), float(length_scale))
    latent = cholesky @ rng.standard_normal(len(anchors))
    interpolated = np.interp(normalized_axis, anchors, latent)
    return 1.0 + float(variation) * interpolated


@lru_cache(maxsize=64)
def _gaussian_process_basis(
    anchor_count: int,
    length_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Cache the fixed GP covariance factor used by many simulated views."""
    anchors = np.linspace(0.0, 1.0, int(anchor_count), dtype=np.float64)
    distances = anchors[:, None] - anchors[None, :]
    covariance = np.exp(-0.5 * (distances / float(length_scale)) ** 2)
    covariance += 1e-8 * np.eye(len(anchors), dtype=np.float64)
    cholesky = np.linalg.cholesky(covariance)
    anchors.setflags(write=False)
    cholesky.setflags(write=False)
    return anchors, cholesky


def generate_background_profile(
    axis: np.ndarray,
    amplitude: float,
    *,
    model: str = "polynomial",
    order: int = 2,
    variation: float = 0.0,
    anchor_count: int = 33,
    length_scale: float = 0.20,
    floor_fraction: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Generate a non-negative smooth background and its quality metadata.

    ``amplitude`` is relative to the clean reference peak height.  The shape
    is normalized to a maximum of one before that amplitude is applied.  The
    default polynomial path defines the stable quadratic baseline; non-zero
    ``variation`` or the GP path creates view-specific but
    angle-correlated background structure.
    """
    values = _validate_axis(axis)
    if not np.isfinite(amplitude) or amplitude < 0:
        raise ValueError("background amplitude must be finite and non-negative")
    if model not in BACKGROUND_MODELS:
        raise ValueError(f"unsupported background model: {model}")
    if int(order) < 0 or int(order) > 6:
        raise ValueError("background_order must be in [0, 6]")
    if not np.isfinite(variation) or variation < 0:
        raise ValueError("background_variation must be finite and non-negative")
    if not np.isfinite(floor_fraction) or not 0.0 <= floor_fraction <= 1.0:
        raise ValueError("background_floor_fraction must be in [0, 1]")
    generator = rng if rng is not None else np.random.default_rng(0)
    normalized = _normalized_axis(values)
    if model == "flat":
        raw_shape = np.ones_like(normalized)
    elif model == "polynomial":
        raw_shape = _polynomial_shape(
            normalized,
            order=int(order),
            variation=float(variation),
            rng=generator,
        )
    else:
        raw_shape = _gaussian_process_shape(
            normalized,
            variation=float(variation),
            anchor_count=int(anchor_count),
            length_scale=float(length_scale),
            rng=generator,
        )
    shape = _normalize_nonnegative_shape(raw_shape)
    shape = float(floor_fraction) + (1.0 - float(floor_fraction)) * shape
    profile = float(amplitude) * shape
    metadata = {
        "background_model": model,
        "background_order": int(order),
        "background_variation": float(variation),
        "background_anchor_count": int(anchor_count),
        "background_gp_length_scale": float(length_scale),
        "background_floor_fraction": float(floor_fraction),
        "background_min": float(np.min(profile)) if profile.size else 0.0,
        "background_max": float(np.max(profile)) if profile.size else 0.0,
        "background_mean": float(np.mean(profile)) if profile.size else 0.0,
        "background_integral": (
            float(
                np.trapezoid(profile, values)
                if hasattr(np, "trapezoid")
                else np.trapz(profile, values)
            )
            if profile.size
            else 0.0
        ),
    }
    return profile.astype(np.float64), metadata


def apply_noise_model(
    signal: np.ndarray,
    *,
    rng: np.random.Generator,
    model: str = "additive_gaussian",
    gaussian_std: float = 0.0,
    poisson_count_scale: float = 1000.0,
    electronic_noise_std: float = 0.0,
    electronic_noise_std_counts: float = 0.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply detector noise to a non-negative expected intensity profile.

    ``additive_gaussian`` is the direct intensity-space model. ``poisson`` samples
    counts from the total expected signal and converts them back to the same
    intensity scale.  Electronic readout noise can be specified either in the
    legacy normalized-intensity scale or, preferably, directly in detector
    count units via ``electronic_noise_std_counts``.
    """
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("noise input must be a finite one-dimensional array")
    if np.min(values, initial=0.0) < 0:
        raise ValueError("noise input must be non-negative before counting")
    if model not in NOISE_MODELS:
        raise ValueError(f"unsupported noise model: {model}")
    if not np.isfinite(gaussian_std) or gaussian_std < 0:
        raise ValueError("gaussian_std must be finite and non-negative")
    if not np.isfinite(poisson_count_scale) or poisson_count_scale <= 0:
        raise ValueError("poisson_count_scale must be finite and positive")
    if not np.isfinite(electronic_noise_std) or electronic_noise_std < 0:
        raise ValueError("electronic_noise_std must be finite and non-negative")
    if not np.isfinite(electronic_noise_std_counts) or electronic_noise_std_counts < 0:
        raise ValueError("electronic_noise_std_counts must be finite and non-negative")

    if model == "additive_gaussian":
        if electronic_noise_std_counts > 0.0:
            raise ValueError(
                "electronic_noise_std_counts requires a Poisson-based noise model"
            )
        random_component = rng.normal(0.0, float(gaussian_std), size=values.shape)
        output = values + random_component
        metadata = {
            "noise_model": model,
            "poisson_count_scale": None,
            "expected_count_mean": None,
            "shot_noise_std": 0.0,
            "electronic_noise_std": float(gaussian_std),
            "electronic_noise_std_counts": 0.0,
            "electronic_noise_std_intensity": float(gaussian_std),
            "expected_count_min": None,
            "expected_count_max": None,
            "sampled_count_sum": None,
            "zero_count_fraction": None,
            "noise_std_empirical": float(np.std(random_component)) if values.size else 0.0,
        }
        return output, metadata

    expected_counts = np.clip(values, 0.0, None) * float(poisson_count_scale)
    counts = rng.poisson(expected_counts)
    count_readout = (
        rng.normal(0.0, float(electronic_noise_std_counts), size=values.shape)
        if electronic_noise_std_counts > 0.0
        else np.zeros(values.shape, dtype=np.float64)
    )
    output = (counts.astype(np.float64) + count_readout) / float(poisson_count_scale)
    shot_component = counts.astype(np.float64) / float(poisson_count_scale) - values
    intensity_readout = (
        rng.normal(0.0, float(electronic_noise_std), size=values.shape)
        if electronic_noise_std > 0.0
        else np.zeros(values.shape, dtype=np.float64)
    )
    output += intensity_readout
    readout = count_readout / float(poisson_count_scale) + intensity_readout
    metadata = {
        "noise_model": model,
        "poisson_count_scale": float(poisson_count_scale),
        "expected_count_mean": float(np.mean(expected_counts)) if values.size else 0.0,
        "shot_noise_std": float(np.std(shot_component)) if values.size else 0.0,
        "electronic_noise_std": float(electronic_noise_std),
        "electronic_noise_std_counts": float(electronic_noise_std_counts),
        "electronic_noise_std_intensity": float(
            np.hypot(
                electronic_noise_std,
                electronic_noise_std_counts / float(poisson_count_scale),
            )
        ),
        "expected_count_min": float(np.min(expected_counts)) if values.size else 0.0,
        "expected_count_max": float(np.max(expected_counts)) if values.size else 0.0,
        "sampled_count_sum": int(np.sum(counts, dtype=np.int64)) if values.size else 0,
        "zero_count_fraction": float(np.mean(counts == 0)) if values.size else 0.0,
        "noise_std_empirical": float(np.std(shot_component + readout)) if values.size else 0.0,
    }
    return output, metadata
