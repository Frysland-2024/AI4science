"""Metrics and finite mechanism Gate for Stage-1 factorized inversion.

All factorization-space arrays use the canonical block axes
``[B, 2, 2, 2] = [block, structure_state, measurement_state, coordinate]``.
Distances are computed in the standardized ``q`` space.  Physical MAE is a
separate decoded view with final order ``[a, c, delta, FWHM]``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

import numpy as np


BLOCK_SUFFIX = (2, 2, 2)
PHYSICAL_PARAMETER_KEYS = (
    "a_angstrom",
    "c_angstrom",
    "delta_2theta_deg",
    "fwhm_deg",
)


def _as_block_array(name: str, value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 4 or tuple(array.shape[1:]) != BLOCK_SUFFIX:
        raise ValueError(
            f"{name} must have shape [B,2,2,2] with axes "
            "[block,structure_state,measurement_state,coordinate]; "
            f"got {array.shape}"
        )
    if array.shape[0] < 1:
        raise ValueError(f"{name} must contain at least one factorial block")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains NaN or Inf")
    return array


def _as_physical_array(name: str, value: Any) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim < 2 or array.shape[-1] != 4 or array.size == 0:
        raise ValueError(
            f"{name} must be a non-empty array ending in four physical "
            f"parameters [a,c,delta,FWHM]; got {array.shape}"
        )
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains NaN or Inf")
    if np.any(array[..., 0] <= 0.0) or np.any(array[..., 1] <= 0.0):
        raise ValueError(f"{name} contains non-positive lattice parameters")
    if np.any(array[..., 3] <= 0.0):
        raise ValueError(f"{name} contains non-positive FWHM")
    return array


def validate_factorial_targets(
    true_s: Any,
    true_m: Any,
    *,
    equality_atol: float = 1e-12,
    distinct_atol: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    """Validate the four simulator-known pairing relations.

    Structure labels must be identical along the measurement axis,
    measurement labels identical along the structure axis, and both sampled
    state pairs must be genuinely distinct in every block.
    """

    structure = _as_block_array("true_s", true_s)
    measurement = _as_block_array("true_m", true_m)
    if structure.shape != measurement.shape:
        raise ValueError("true_s and true_m must have identical block shapes")
    if not np.allclose(
        structure[:, :, 0, :], structure[:, :, 1, :], rtol=0.0, atol=equality_atol
    ):
        raise ValueError("structure targets change along the measurement axis")
    if not np.allclose(
        measurement[:, 0, :, :],
        measurement[:, 1, :, :],
        rtol=0.0,
        atol=equality_atol,
    ):
        raise ValueError("measurement targets change along the structure axis")

    structure_delta = structure[:, 1, 0, :] - structure[:, 0, 0, :]
    measurement_delta = measurement[:, 0, 1, :] - measurement[:, 0, 0, :]
    if np.any(np.linalg.norm(structure_delta, axis=-1) <= distinct_atol):
        raise ValueError("at least one block has indistinguishable structure states")
    if np.any(np.linalg.norm(measurement_delta, axis=-1) <= distinct_atol):
        raise ValueError("at least one block has indistinguishable measurement states")
    return structure, measurement


def physical_parameter_mae(
    predicted_physical: Any,
    true_physical: Any,
) -> dict[str, float]:
    """Return decoded MAE in Angstrom/degrees for ``[a,c,delta,FWHM]``."""

    predicted = _as_physical_array("predicted_physical", predicted_physical)
    target = _as_physical_array("true_physical", true_physical)
    if predicted.shape != target.shape:
        raise ValueError(
            "predicted_physical and true_physical must have identical shapes"
        )
    values = np.mean(np.abs(predicted - target), axis=tuple(range(predicted.ndim - 1)))
    return {name: float(value) for name, value in zip(PHYSICAL_PARAMETER_KEYS, values)}


def _flatten_edges(values: np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.float64).reshape(-1, 2)


def _mean_l2(values: np.ndarray) -> float:
    flat = _flatten_edges(values)
    return float(np.mean(np.linalg.norm(flat, axis=-1)))


def _pearson(predicted: np.ndarray, target: np.ndarray, *, atol: float = 1e-15) -> float | None:
    x = np.asarray(predicted, dtype=np.float64).reshape(-1)
    y = np.asarray(target, dtype=np.float64).reshape(-1)
    if x.size < 2:
        return None
    x_centered = x - x.mean()
    y_centered = y - y.mean()
    denominator = float(np.linalg.norm(x_centered) * np.linalg.norm(y_centered))
    if denominator <= atol:
        return None
    return float(np.dot(x_centered, y_centered) / denominator)


def _through_origin_slope(
    predicted: np.ndarray, target: np.ndarray, *, atol: float = 1e-15
) -> float | None:
    x = np.asarray(target, dtype=np.float64).reshape(-1)
    y = np.asarray(predicted, dtype=np.float64).reshape(-1)
    denominator = float(np.dot(x, x))
    if denominator <= atol:
        return None
    return float(np.dot(x, y) / denominator)


def _own_response_statistics(
    predicted_delta: np.ndarray,
    true_delta: np.ndarray,
    *,
    coordinate_names: tuple[str, str],
) -> dict[str, Any]:
    predicted = _flatten_edges(predicted_delta)
    target = _flatten_edges(true_delta)
    error = predicted - target
    slopes: dict[str, float | None] = {}
    correlations: dict[str, float | None] = {}
    signed_bias: dict[str, float] = {}
    for index, name in enumerate(coordinate_names):
        slopes[name] = _through_origin_slope(predicted[:, index], target[:, index])
        correlations[name] = _pearson(predicted[:, index], target[:, index])
        signed_bias[name] = float(np.mean(error[:, index]))
    return {
        "mean_l2_error": _mean_l2(error),
        "component_rmse": float(np.sqrt(np.mean(error**2))),
        "signed_bias_by_coordinate": signed_bias,
        "through_origin_slope": _through_origin_slope(predicted, target),
        "through_origin_slope_by_coordinate": slopes,
        "pearson_correlation": _pearson(predicted, target),
        "pearson_correlation_by_coordinate": correlations,
        "true_mean_l2_response": _mean_l2(target),
        "predicted_mean_l2_response": _mean_l2(predicted),
    }


def compute_factorization_metrics(
    pred_s: Any,
    pred_m: Any,
    true_s: Any,
    true_m: Any,
    *,
    predicted_physical: Any | None = None,
    true_physical: Any | None = None,
) -> dict[str, Any]:
    """Compute leakage, signed own response, and the 2x2 response matrix.

    Matrix rows are true interventions ``[structure, measurement]`` and columns
    are predicted heads ``[structure, measurement]``.  The raw matrix contains
    mean L2 predicted changes.  Each normalized row is divided by the mean L2
    true own-factor change for that intervention, giving an ideal identity
    matrix without hiding sign/direction errors (reported separately).
    """

    predicted_s = _as_block_array("pred_s", pred_s)
    predicted_m = _as_block_array("pred_m", pred_m)
    target_s, target_m = validate_factorial_targets(true_s, true_m)
    expected_shape = target_s.shape
    if predicted_s.shape != expected_shape or predicted_m.shape != expected_shape:
        raise ValueError("predictions and targets must have identical block shapes")

    # Measurement intervention: x12-x11 and x22-x21 (axis 2).
    pred_s_under_m = predicted_s[:, :, 1, :] - predicted_s[:, :, 0, :]
    pred_m_under_m = predicted_m[:, :, 1, :] - predicted_m[:, :, 0, :]
    true_m_delta = target_m[:, :, 1, :] - target_m[:, :, 0, :]

    # Structure intervention: x21-x11 and x22-x12 (axis 1).
    pred_s_under_s = predicted_s[:, 1, :, :] - predicted_s[:, 0, :, :]
    pred_m_under_s = predicted_m[:, 1, :, :] - predicted_m[:, 0, :, :]
    true_s_delta = target_s[:, 1, :, :] - target_s[:, 0, :, :]

    leakage_s_from_m = _mean_l2(pred_s_under_m)
    leakage_m_from_s = _mean_l2(pred_m_under_s)
    true_s_scale = _mean_l2(true_s_delta)
    true_m_scale = _mean_l2(true_m_delta)
    if true_s_scale <= 0.0 or true_m_scale <= 0.0:
        raise ValueError("true intervention response scale must be positive")

    raw_matrix = np.asarray(
        [
            [_mean_l2(pred_s_under_s), _mean_l2(pred_m_under_s)],
            [_mean_l2(pred_s_under_m), _mean_l2(pred_m_under_m)],
        ],
        dtype=np.float64,
    )
    normalized_matrix = raw_matrix / np.asarray(
        [[true_s_scale], [true_m_scale]], dtype=np.float64
    )

    output: dict[str, Any] = {
        "leakage": {
            "measurement_to_structure": leakage_s_from_m,
            "structure_to_measurement": leakage_m_from_s,
        },
        "own_factor_response": {
            "structure": _own_response_statistics(
                pred_s_under_s,
                true_s_delta,
                coordinate_names=("q_u", "q_v"),
            ),
            "measurement": _own_response_statistics(
                pred_m_under_m,
                true_m_delta,
                coordinate_names=("q_delta", "q_w"),
            ),
        },
        "response_matrix": {
            "row_interventions": ["structure", "measurement"],
            "column_heads": ["structure", "measurement"],
            "raw_mean_l2": raw_matrix.tolist(),
            "normalized_by_true_own_factor_response": normalized_matrix.tolist(),
            "true_own_factor_response_scale": {
                "structure": true_s_scale,
                "measurement": true_m_scale,
            },
        },
    }
    if (predicted_physical is None) != (true_physical is None):
        raise ValueError(
            "predicted_physical and true_physical must be supplied together"
        )
    if predicted_physical is not None:
        output["parameter_mae"] = physical_parameter_mae(
            predicted_physical, true_physical
        )
    return output


def _coerce_seed_reports(
    values: Mapping[Any, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    if isinstance(values, Mapping):
        reports = {str(seed): report for seed, report in values.items()}
    else:
        reports = {}
        for report in values:
            if "seed" not in report:
                raise ValueError("sequence seed reports must contain a 'seed' field")
            seed = str(report["seed"])
            if seed in reports:
                raise ValueError(f"duplicate seed report: {seed}")
            reports[seed] = report
    if not reports:
        raise ValueError("at least one seed report is required")
    if not all(isinstance(report, Mapping) for report in reports.values()):
        raise TypeError("every seed report must be a mapping")
    return dict(sorted(reports.items()))


def _extract_scalar_metrics(report: Mapping[str, Any]) -> dict[str, float]:
    try:
        scalars = {
            "leakage_measurement_to_structure": float(
                report["leakage"]["measurement_to_structure"]
            ),
            "leakage_structure_to_measurement": float(
                report["leakage"]["structure_to_measurement"]
            ),
            "response_error_structure": float(
                report["own_factor_response"]["structure"]["mean_l2_error"]
            ),
            "response_error_measurement": float(
                report["own_factor_response"]["measurement"]["mean_l2_error"]
            ),
        }
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("seed report is missing canonical factorization metrics") from error
    if "parameter_mae" in report:
        for key in PHYSICAL_PARAMETER_KEYS:
            try:
                scalars[f"mae_{key}"] = float(report["parameter_mae"][key])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(
                    f"seed report has incomplete physical parameter MAE: {key}"
                ) from error
    if not all(math.isfinite(value) and value >= 0.0 for value in scalars.values()):
        raise ValueError("Gate scalar metrics must be finite and non-negative")
    return scalars


def _sample_summary(values: Sequence[float]) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "values": [float(value) for value in array],
        "mean": float(array.mean()),
        "sample_std": float(array.std(ddof=1)) if len(array) > 1 else 0.0,
        "min": float(array.min()),
        "max": float(array.max()),
    }


def _relative_reduction(baseline: float, factorized: float, *, atol: float = 1e-15) -> float | None:
    if abs(baseline) <= atol:
        return 0.0 if abs(factorized) <= atol else None
    return float((baseline - factorized) / baseline)


def _summarize_one_model(reports: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    extracted = {seed: _extract_scalar_metrics(report) for seed, report in reports.items()}
    key_sets = {frozenset(values) for values in extracted.values()}
    if len(key_sets) != 1:
        raise ValueError("all seed reports must contain the same scalar metrics")
    metric_names = sorted(next(iter(key_sets)))
    return {
        "seeds": list(reports),
        "metrics": {
            name: _sample_summary([extracted[seed][name] for seed in reports])
            for name in metric_names
        },
    }


def summarize_seed_metrics(
    baseline_by_seed: Mapping[Any, Mapping[str, Any]]
    | Sequence[Mapping[str, Any]],
    factorized_by_seed: Mapping[Any, Mapping[str, Any]]
    | Sequence[Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Summarize one model or a seed-matched baseline/factorized comparison."""

    baseline_reports = _coerce_seed_reports(baseline_by_seed)
    baseline_summary = _summarize_one_model(baseline_reports)
    if factorized_by_seed is None:
        return baseline_summary

    factorized_reports = _coerce_seed_reports(factorized_by_seed)
    if set(baseline_reports) != set(factorized_reports):
        raise ValueError("baseline and factorized models must use identical seed sets")
    factorized_summary = _summarize_one_model(factorized_reports)
    baseline_metrics = baseline_summary["metrics"]
    factorized_metrics = factorized_summary["metrics"]
    if set(baseline_metrics) != set(factorized_metrics):
        raise ValueError("baseline and factorized reports must contain identical metrics")

    comparison: dict[str, Any] = {}
    seeds = baseline_summary["seeds"]
    baseline_scalars = {
        seed: _extract_scalar_metrics(baseline_reports[seed]) for seed in seeds
    }
    factorized_scalars = {
        seed: _extract_scalar_metrics(factorized_reports[seed]) for seed in seeds
    }
    for name in sorted(baseline_metrics):
        baseline_values = np.asarray(
            [baseline_scalars[seed][name] for seed in seeds], dtype=np.float64
        )
        factorized_values = np.asarray(
            [factorized_scalars[seed][name] for seed in seeds], dtype=np.float64
        )
        paired_delta = factorized_values - baseline_values
        per_seed_relative = [
            _relative_reduction(float(baseline), float(factorized))
            for baseline, factorized in zip(baseline_values, factorized_values)
        ]
        comparison[name] = {
            "factorized_minus_baseline": _sample_summary(paired_delta.tolist()),
            "relative_reduction_of_means": _relative_reduction(
                float(baseline_values.mean()), float(factorized_values.mean())
            ),
            "relative_reduction_by_seed": per_seed_relative,
            "improved_seed_count": int(np.sum(factorized_values < baseline_values)),
            "improved_seed_fraction": float(np.mean(factorized_values < baseline_values)),
        }
    return {
        "seeds": seeds,
        "baseline": baseline_summary["metrics"],
        "factorized": factorized_summary["metrics"],
        "comparison": comparison,
    }


def decide_factorization_gate(
    summary_or_baseline: Mapping[str, Any]
    | Mapping[Any, Mapping[str, Any]]
    | Sequence[Mapping[str, Any]],
    factorized_by_seed: Mapping[Any, Mapping[str, Any]]
    | Sequence[Mapping[str, Any]]
    | None = None,
    *,
    leakage_reduction_min: float = 0.20,
    own_response_degradation_max: float = 0.10,
    parameter_mae_degradation_max: float = 0.05,
    improved_seed_fraction_min: float = 2.0 / 3.0,
    required_seed_count: int = 3,
) -> dict[str, Any]:
    """Apply the pre-registered finite GO/PARTIAL/NO-GO mechanism Gate.

    GO requires both leakage reductions, both own-response safeguards, all four
    physical-MAE safeguards, and seed-wise direction consistency.  PARTIAL
    requires at least one stable leakage signal but fails one or more GO
    conditions.  With no stable leakage signal the result is NO-GO.
    """

    if factorized_by_seed is not None:
        summary = summarize_seed_metrics(summary_or_baseline, factorized_by_seed)
    else:
        summary = dict(summary_or_baseline)  # type: ignore[arg-type]
    if not {"seeds", "comparison"}.issubset(summary):
        raise ValueError("decide_factorization_gate requires a matched-seed summary")
    seeds = list(summary["seeds"])
    if len(seeds) != int(required_seed_count):
        raise ValueError(
            f"the pre-registered Gate requires exactly {required_seed_count} seeds"
        )
    comparison = summary["comparison"]

    leakage_keys = (
        "leakage_measurement_to_structure",
        "leakage_structure_to_measurement",
    )
    response_keys = ("response_error_structure", "response_error_measurement")
    mae_keys = tuple(f"mae_{key}" for key in PHYSICAL_PARAMETER_KEYS)
    required = set(leakage_keys + response_keys + mae_keys)
    missing = sorted(required.difference(comparison))
    if missing:
        raise ValueError(f"Gate summary is missing required metrics: {missing}")

    def reduction(key: str) -> float | None:
        value = comparison[key]["relative_reduction_of_means"]
        return None if value is None else float(value)

    leakage_checks = {
        key: bool(
            reduction(key) is not None
            and reduction(key) >= leakage_reduction_min
            and float(comparison[key]["improved_seed_fraction"])
            >= improved_seed_fraction_min
        )
        for key in leakage_keys
    }
    response_checks = {
        key: bool(
            reduction(key) is not None
            and reduction(key) >= -own_response_degradation_max
        )
        for key in response_keys
    }
    mae_checks = {
        key: bool(
            reduction(key) is not None
            and reduction(key) >= -parameter_mae_degradation_max
        )
        for key in mae_keys
    }

    leakage_pass_count = sum(leakage_checks.values())
    safeguards_pass = all(response_checks.values()) and all(mae_checks.values())
    if leakage_pass_count == len(leakage_keys) and safeguards_pass:
        decision = "GO"
    elif leakage_pass_count >= 1:
        decision = "PARTIAL"
    else:
        decision = "NO-GO"

    failed = [
        key
        for group in (leakage_checks, response_checks, mae_checks)
        for key, passed in group.items()
        if not passed
    ]
    return {
        "decision": decision,
        "thresholds": {
            "leakage_reduction_min": float(leakage_reduction_min),
            "own_response_degradation_max": float(own_response_degradation_max),
            "parameter_mae_degradation_max": float(parameter_mae_degradation_max),
            "improved_seed_fraction_min": float(improved_seed_fraction_min),
            "required_seed_count": int(required_seed_count),
        },
        "checks": {
            "leakage": leakage_checks,
            "own_factor_response": response_checks,
            "parameter_mae": mae_checks,
        },
        "failed_checks": failed,
        "continuation_allowed": decision == "GO",
    }


__all__ = [
    "BLOCK_SUFFIX",
    "PHYSICAL_PARAMETER_KEYS",
    "compute_factorization_metrics",
    "decide_factorization_gate",
    "physical_parameter_mae",
    "summarize_seed_metrics",
    "validate_factorial_targets",
]
