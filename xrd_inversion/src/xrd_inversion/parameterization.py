"""Canonical NumPy parameterization for tetragonal factorized inversion.

The renderer consumes a dimensionless four-vector ``q`` in the fixed order
``[q_u, q_v, q_delta, q_w]``.  Neural-network structure and measurement heads
are exact slices of that vector; there is no implicit second normalization in
this module.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray


Q_PARAMETER_ORDER = ("q_u", "q_v", "q_delta", "q_w")
STRUCTURE_PARAMETER_ORDER = Q_PARAMETER_ORDER[:2]
MEASUREMENT_PARAMETER_ORDER = Q_PARAMETER_ORDER[2:]
PHYSICAL_PARAMETER_ORDER = (
    "a_angstrom",
    "c_angstrom",
    "delta_2theta_deg",
    "fwhm_deg",
)

__all__ = [
    "MEASUREMENT_PARAMETER_ORDER",
    "PHYSICAL_PARAMETER_ORDER",
    "Q_PARAMETER_ORDER",
    "STRUCTURE_PARAMETER_ORDER",
    "compose_q",
    "decode_q",
    "encode_q",
    "resolve_reference_q",
    "split_q",
]


def _finite_vector_array(
    value: ArrayLike,
    *,
    name: str,
    width: int,
) -> NDArray[np.float64]:
    try:
        array = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a numeric NumPy-compatible array") from error
    if array.ndim < 1 or array.shape[-1] != width:
        raise ValueError(f"{name} must have shape (..., {width}); got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain only finite values")
    return array


def _positive_scalar(value: Any, *, name: str) -> float:
    try:
        scalar = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite positive scalar") from error
    if not np.isfinite(scalar) or scalar <= 0.0:
        raise ValueError(f"{name} must be a finite positive scalar")
    return scalar


def _scales(
    parameter_config: Mapping[str, Any],
) -> tuple[float, float, float, float, float, float, float]:
    if str(parameter_config.get("fwhm_transform")) != "log":
        raise ValueError("parameter_config requires fwhm_transform='log'")
    du_half_range = _positive_scalar(
        parameter_config.get("du_half_range"), name="du_half_range"
    )
    dv_half_range = _positive_scalar(
        parameter_config.get("dv_half_range"), name="dv_half_range"
    )
    delta_half_range_deg = _positive_scalar(
        parameter_config.get("delta_half_range_deg"),
        name="delta_half_range_deg",
    )
    fwhm_min_deg = _positive_scalar(
        parameter_config.get("fwhm_min_deg"), name="fwhm_min_deg"
    )
    fwhm_max_deg = _positive_scalar(
        parameter_config.get("fwhm_max_deg"), name="fwhm_max_deg"
    )
    if fwhm_min_deg >= fwhm_max_deg:
        raise ValueError("FWHM bounds must satisfy 0 < min < max")
    log_center = 0.5 * (np.log(fwhm_min_deg) + np.log(fwhm_max_deg))
    log_half_range = 0.5 * (np.log(fwhm_max_deg) - np.log(fwhm_min_deg))
    return (
        du_half_range,
        dv_half_range,
        delta_half_range_deg,
        fwhm_min_deg,
        fwhm_max_deg,
        float(log_center),
        float(log_half_range),
    )


def _reference_log_coordinates(
    reference_a_angstrom: Any,
    reference_c_angstrom: Any,
) -> tuple[float, float]:
    a0 = _positive_scalar(reference_a_angstrom, name="reference_a_angstrom")
    c0 = _positive_scalar(reference_c_angstrom, name="reference_c_angstrom")
    u0 = (2.0 * np.log(a0) + np.log(c0)) / 3.0
    v0 = np.log(c0 / a0)
    return float(u0), float(v0)


def encode_q(
    physical: ArrayLike,
    *,
    reference_a_angstrom: float,
    reference_c_angstrom: float,
    parameter_config: Mapping[str, Any],
) -> NDArray[np.float64]:
    """Encode physical parameters ``[..., a, c, delta_deg, FWHM_deg]`` to q.

    The leading dimensions are preserved.  The reference lattice is scalar and
    parent-specific, so callers must encode separate parents separately.
    """

    values = _finite_vector_array(physical, name="physical", width=4)
    a = values[..., 0]
    c = values[..., 1]
    fwhm = values[..., 3]
    if np.any(a <= 0.0) or np.any(c <= 0.0):
        raise ValueError("physical a and c must be positive")
    if np.any(fwhm <= 0.0):
        raise ValueError("physical FWHM must be positive")
    (
        du_half_range,
        dv_half_range,
        delta_half_range_deg,
        _,
        _,
        log_center,
        log_half_range,
    ) = _scales(parameter_config)
    u0, v0 = _reference_log_coordinates(
        reference_a_angstrom, reference_c_angstrom
    )
    u_abs = (2.0 * np.log(a) + np.log(c)) / 3.0
    v_abs = np.log(c / a)
    encoded = np.stack(
        (
            (u_abs - u0) / du_half_range,
            (v_abs - v0) / dv_half_range,
            values[..., 2] / delta_half_range_deg,
            (np.log(fwhm) - log_center) / log_half_range,
        ),
        axis=-1,
    )
    if not np.isfinite(encoded).all():
        raise ValueError("encoded q contains non-finite values")
    return np.asarray(encoded, dtype=np.float64)


def decode_q(
    q: ArrayLike,
    *,
    reference_a_angstrom: float,
    reference_c_angstrom: float,
    parameter_config: Mapping[str, Any],
) -> NDArray[np.float64]:
    """Decode q to ``[..., a_angstrom, c_angstrom, delta_deg, FWHM_deg]``."""

    values = _finite_vector_array(q, name="q", width=4)
    (
        du_half_range,
        dv_half_range,
        delta_half_range_deg,
        _,
        _,
        log_center,
        log_half_range,
    ) = _scales(parameter_config)
    u0, v0 = _reference_log_coordinates(
        reference_a_angstrom, reference_c_angstrom
    )
    u_abs = u0 + values[..., 0] * du_half_range
    v_abs = v0 + values[..., 1] * dv_half_range
    with np.errstate(over="ignore", invalid="ignore"):
        decoded = np.stack(
            (
                np.exp(u_abs - v_abs / 3.0),
                np.exp(u_abs + 2.0 * v_abs / 3.0),
                values[..., 2] * delta_half_range_deg,
                np.exp(log_center + values[..., 3] * log_half_range),
            ),
            axis=-1,
        )
    if not np.isfinite(decoded).all():
        raise ValueError("decoded physical parameters contain non-finite values")
    return np.asarray(decoded, dtype=np.float64)


def split_q(q: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Split ``[..., 4]`` q into structure and measurement ``[..., 2]`` arrays."""

    values = _finite_vector_array(q, name="q", width=4)
    return values[..., :2].copy(), values[..., 2:].copy()


def compose_q(
    theta_s: ArrayLike,
    theta_m: ArrayLike,
) -> NDArray[np.float64]:
    """Compose exact-shape structure/measurement heads into renderer q.

    Broadcasting is intentionally forbidden: matching leading dimensions are a
    safeguard against pairing predictions from different factorial blocks.
    """

    structure = _finite_vector_array(theta_s, name="theta_s", width=2)
    measurement = _finite_vector_array(theta_m, name="theta_m", width=2)
    if structure.shape[:-1] != measurement.shape[:-1]:
        raise ValueError(
            "theta_s and theta_m must have identical leading dimensions; "
            f"got {structure.shape} and {measurement.shape}"
        )
    return np.concatenate((structure, measurement), axis=-1).astype(
        np.float64, copy=False
    )


def resolve_reference_q(
    parameter_config: Mapping[str, Any],
    factorial_config: Mapping[str, Any] | None = None,
) -> NDArray[np.float64]:
    """Resolve and cross-check the parent-reference renderer q.

    Factorization interface v1 requires ``factorial.reference_q`` (when
    present) to equal ``parameterization.nominal_q`` exactly.  This prevents a
    silent change from the frozen minimum-FWHM reference to the q-space centre.
    """

    if "nominal_q" not in parameter_config:
        raise ValueError("parameter_config must define nominal_q")
    nominal = _finite_vector_array(
        parameter_config["nominal_q"], name="parameterization.nominal_q", width=4
    )
    if nominal.shape != (4,):
        raise ValueError(
            "parameterization.nominal_q must have shape (4,); "
            f"got {nominal.shape}"
        )
    reference = nominal
    if factorial_config is not None and "reference_q" in factorial_config:
        reference = _finite_vector_array(
            factorial_config["reference_q"],
            name="factorial.reference_q",
            width=4,
        )
        if reference.shape != (4,):
            raise ValueError(
                "factorial.reference_q must have shape (4,); "
                f"got {reference.shape}"
            )
        if not np.array_equal(reference, nominal):
            raise ValueError(
                "factorial.reference_q must exactly match parameterization.nominal_q"
            )
    if "q_bounds" in parameter_config:
        bounds = np.asarray(parameter_config["q_bounds"], dtype=np.float64)
        if bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[0] >= bounds[1]:
            raise ValueError("parameterization.q_bounds must be finite [low, high]")
        if np.any(reference < bounds[0]) or np.any(reference > bounds[1]):
            raise ValueError("reference q lies outside parameterization.q_bounds")
    return reference.astype(np.float64, copy=True)
