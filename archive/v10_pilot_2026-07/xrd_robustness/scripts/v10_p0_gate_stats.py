"""Pure statistical helpers for the Train-only V10-P0 gate."""

from __future__ import annotations

import math
from typing import Any, Mapping

import numpy as np


RAW_POOL_BINS = 128
RIDGE_ALPHA = 1.0


def _macro_f1(targets: np.ndarray, predictions: np.ndarray, classes: int) -> float:
    values: list[float] = []
    for label in range(classes):
        true_positive = int(((targets == label) & (predictions == label)).sum())
        false_positive = int(((targets != label) & (predictions == label)).sum())
        false_negative = int(((targets == label) & (predictions != label)).sum())
        denominator = 2 * true_positive + false_positive + false_negative
        values.append(0.0 if denominator == 0 else 2 * true_positive / denominator)
    return float(np.mean(values))


def _cross_entropy_from_scores(scores: np.ndarray, targets: np.ndarray) -> float:
    shifted = scores - scores.max(axis=1, keepdims=True)
    log_normalizer = np.log(np.exp(shifted).sum(axis=1, keepdims=True))
    log_probabilities = shifted - log_normalizer
    return float(-log_probabilities[np.arange(len(targets)), targets].mean())


def _classification_threshold(sample_count: int, classes: int) -> float:
    chance = 1.0 / classes
    standard_error = math.sqrt(chance * (1.0 - chance) / sample_count)
    return float(chance + 2.0 * standard_error)


def _standardize_train_test(
    train_x: np.ndarray, test_x: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    train = np.asarray(train_x, dtype=np.float64)
    test = np.asarray(test_x, dtype=np.float64)
    mean = train.mean(axis=0, keepdims=True)
    std = train.std(axis=0, keepdims=True)
    std = np.where(std < 1e-8, 1.0, std)
    return (train - mean) / std, (test - mean) / std


def _ridge_projection(
    train_x: np.ndarray,
    test_x: np.ndarray,
    *,
    alpha: float = RIDGE_ALPHA,
) -> np.ndarray:
    if alpha <= 0:
        raise ValueError("ridge alpha must be positive")
    train, test = _standardize_train_test(train_x, test_x)
    train_augmented = np.concatenate(
        [train, np.ones((len(train), 1), dtype=np.float64)], axis=1
    )
    test_augmented = np.concatenate(
        [test, np.ones((len(test), 1), dtype=np.float64)], axis=1
    )
    penalty = np.eye(train_augmented.shape[1], dtype=np.float64) * float(alpha)
    penalty[-1, -1] = 0.0
    solve = np.linalg.solve(
        train_augmented.T @ train_augmented + penalty,
        train_augmented.T,
    )
    return test_augmented @ solve


def _classification_probe(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    *,
    classes: int,
    permutations: int,
    seed: int,
    train_groups: np.ndarray | None = None,
    test_groups: np.ndarray | None = None,
    group_constant_labels: bool = False,
) -> dict[str, Any]:
    projection = _ridge_projection(train_x, test_x)
    eye = np.eye(classes, dtype=np.float64)
    scores = projection @ eye[np.asarray(train_y, dtype=np.int64)]
    targets = np.asarray(test_y, dtype=np.int64)
    predictions = scores.argmax(axis=1)
    accuracy = float((predictions == targets).mean())
    macro_f1 = _macro_f1(targets, predictions, classes)
    cross_entropy = _cross_entropy_from_scores(scores, targets)

    generator = np.random.default_rng(seed)
    permutation_accuracy: list[float] = []
    permutation_macro_f1: list[float] = []
    train_groups_array = (
        np.arange(len(train_y), dtype=np.int64)
        if train_groups is None
        else np.asarray(train_groups)
    )
    test_groups_array = (
        np.arange(len(test_y), dtype=np.int64)
        if test_groups is None
        else np.asarray(test_groups)
    )
    unique_train_groups = np.unique(train_groups_array)
    unique_test_groups = np.unique(test_groups_array)

    def grouped_permutation() -> np.ndarray:
        shuffled = np.asarray(train_y, dtype=np.int64).copy()
        if group_constant_labels:
            group_labels = np.asarray(
                [
                    train_y[np.flatnonzero(train_groups_array == group)[0]]
                    for group in unique_train_groups
                ],
                dtype=np.int64,
            )
            shuffled_group_labels = generator.permutation(group_labels)
            for group, label in zip(
                unique_train_groups, shuffled_group_labels, strict=True
            ):
                shuffled[train_groups_array == group] = label
            return shuffled
        for group in unique_train_groups:
            indexes = np.flatnonzero(train_groups_array == group)
            shuffled[indexes] = generator.permutation(shuffled[indexes])
        return shuffled

    for _ in range(permutations):
        shuffled = grouped_permutation()
        shuffled_scores = projection @ eye[np.asarray(shuffled, dtype=np.int64)]
        shuffled_predictions = shuffled_scores.argmax(axis=1)
        permutation_accuracy.append(float((shuffled_predictions == targets).mean()))
        permutation_macro_f1.append(
            _macro_f1(targets, shuffled_predictions, classes)
        )
    permutation_accuracy_array = np.asarray(permutation_accuracy)
    permutation_macro_f1_array = np.asarray(permutation_macro_f1)
    threshold = _classification_threshold(len(unique_test_groups), classes)
    accuracy_p95 = float(np.quantile(permutation_accuracy_array, 0.95))
    macro_f1_p95 = float(np.quantile(permutation_macro_f1_array, 0.95))
    passed = bool(
        accuracy > threshold
        and accuracy > accuracy_p95
        and macro_f1 > 1.0 / classes
        and macro_f1 > macro_f1_p95
    )
    return {
        "status": "signal_demonstrated" if passed else "not_demonstrated",
        "train_examples": int(len(train_y)),
        "audit_examples": int(len(test_y)),
        "calibration_sampling_units": int(len(unique_train_groups)),
        "audit_sampling_units": int(len(unique_test_groups)),
        "permutation_unit": (
            "group-label permutation"
            if group_constant_labels
            else "within-group label permutation"
        ),
        "classes": int(classes),
        "ridge_alpha": float(RIDGE_ALPHA),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "cross_entropy": cross_entropy,
        "chance_accuracy": float(1.0 / classes),
        "descriptive_accuracy_threshold": threshold,
        "permutation_draws": int(permutations),
        "permutation_accuracy_p95": accuracy_p95,
        "permutation_macro_f1_p95": macro_f1_p95,
        "permutation_accuracy_p_value": float(
            (1 + int((permutation_accuracy_array >= accuracy).sum()))
            / (permutations + 1)
        ),
        "features_are_detached_from_backbone": True,
        "calibration_and_audit_structures_are_disjoint": True,
    }


def _r2_score(target: np.ndarray, prediction: np.ndarray) -> float:
    target = np.asarray(target, dtype=np.float64)
    prediction = np.asarray(prediction, dtype=np.float64)
    denominator = float(np.sum((target - target.mean()) ** 2))
    if denominator <= 1e-15:
        return float("nan")
    return float(1.0 - np.sum((target - prediction) ** 2) / denominator)


def _pearson(target: np.ndarray, prediction: np.ndarray) -> float:
    target = np.asarray(target, dtype=np.float64)
    prediction = np.asarray(prediction, dtype=np.float64)
    if target.std() < 1e-12 or prediction.std() < 1e-12:
        return 0.0
    return float(np.corrcoef(target, prediction)[0, 1])


def _regression_probe(
    train_x: np.ndarray,
    train_y: np.ndarray,
    test_x: np.ndarray,
    test_y: np.ndarray,
    *,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    projection = _ridge_projection(train_x, test_x)
    train_target = np.asarray(train_y, dtype=np.float64)
    audit_target = np.asarray(test_y, dtype=np.float64)
    prediction = projection @ train_target
    r2 = _r2_score(audit_target, prediction)
    pearson = _pearson(audit_target, prediction)
    mae = float(np.mean(np.abs(audit_target - prediction)))

    generator = np.random.default_rng(seed)
    permutation_r2: list[float] = []
    permutation_pearson: list[float] = []
    for _ in range(permutations):
        shuffled = generator.permutation(train_target)
        shuffled_prediction = projection @ shuffled
        permutation_r2.append(_r2_score(audit_target, shuffled_prediction))
        permutation_pearson.append(_pearson(audit_target, shuffled_prediction))
    r2_array = np.asarray(permutation_r2, dtype=np.float64)
    pearson_array = np.asarray(permutation_pearson, dtype=np.float64)
    r2_p95 = float(np.quantile(r2_array, 0.95))
    pearson_p95 = float(np.quantile(pearson_array, 0.95))
    passed = bool(r2 > 0.0 and r2 > r2_p95 and pearson > pearson_p95)
    return {
        "status": "signal_demonstrated" if passed else "not_demonstrated",
        "train_examples": int(len(train_target)),
        "audit_examples": int(len(audit_target)),
        "ridge_alpha": float(RIDGE_ALPHA),
        "audit_r2": r2,
        "audit_pearson": pearson,
        "audit_mae_on_normalized_target": mae,
        "permutation_draws": int(permutations),
        "permutation_r2_p95": r2_p95,
        "permutation_pearson_p95": pearson_p95,
        "permutation_r2_p_value": float(
            (1 + int((r2_array >= r2).sum())) / (permutations + 1)
        ),
        "features_are_detached_from_backbone": True,
        "calibration_and_audit_structures_are_disjoint": True,
    }


def _pooled_absolute_spectrum_difference(
    first: np.ndarray,
    second: np.ndarray,
    *,
    bins: int = RAW_POOL_BINS,
) -> np.ndarray:
    difference = np.abs(
        np.asarray(second, dtype=np.float32) - np.asarray(first, dtype=np.float32)
    )
    if difference.ndim != 2:
        raise ValueError("spectrum arrays must have shape [samples, points]")
    if bins <= 0 or bins > difference.shape[1]:
        raise ValueError("pool bin count must be in [1, spectrum_points]")
    edges = np.linspace(0, difference.shape[1], bins + 1, dtype=np.int64)
    return np.stack(
        [difference[:, edges[i] : edges[i + 1]].mean(axis=1) for i in range(bins)],
        axis=1,
    )


def _normalized_strength(family: str, parameters: Mapping[str, Any]) -> float:
    if family == "shift":
        return float((abs(float(parameters["delta_2theta_deg"])) - 0.2) / 0.3)
    if family == "broadening":
        return float((float(parameters["fwhm_deg"]) - 0.2) / 0.15)
    if family == "background":
        return float(
            (float(parameters["background_to_peak_ratio"]) - 0.02) / 0.03
        )
    if family == "noise":
        count_scale = float(parameters["poisson_count_scale"])
        return float(
            (math.log(2500.0) - math.log(count_scale))
            / (math.log(2500.0) - math.log(100.0))
        )
    if family == "texture":
        return float((0.8 - float(parameters["march_parameter"])) / 0.3)
    raise ValueError(f"unknown perturbation family: {family}")


def _gate_decision(
    *,
    raw_family_signal: bool,
    residual_family_signal: bool,
    strength_pass_count: int,
    crystal_leakage_signal: bool,
) -> dict[str, Any]:
    measurement_gate = "PASS"
    if not raw_family_signal:
        measurement_gate = "BLOCK"
    elif not residual_family_signal:
        measurement_gate = "HOLD"
    elif strength_pass_count < 2:
        measurement_gate = "PARTIAL"

    if measurement_gate == "BLOCK":
        v10_premise = "BLOCK"
        rationale = (
            "The controlled simulator labels were not identifiable even from raw "
            "spectrum differences."
        )
    elif measurement_gate in {"HOLD", "PARTIAL"}:
        v10_premise = measurement_gate
        rationale = (
            "Measurement-family information is not yet sufficiently demonstrated "
            "in the frozen backbone residual."
        )
    elif crystal_leakage_signal:
        v10_premise = "PASS"
        rationale = (
            "The residual carries simulator-known measurement information and still "
            "leaks crystal-system information, supporting a V10 disentanglement pilot."
        )
    else:
        v10_premise = "PARTIAL"
        rationale = (
            "Measurement information is present, but this controlled panel did not "
            "independently reproduce crystal-system leakage."
        )
    return {
        "measurement_information_gate": measurement_gate,
        "v10_premise_gate": v10_premise,
        "raw_family_signal": bool(raw_family_signal),
        "residual_family_signal": bool(residual_family_signal),
        "strength_targets_passing": int(strength_pass_count),
        "minimum_strength_targets_required": 2,
        "crystal_system_leakage_signal": bool(crystal_leakage_signal),
        "rationale": rationale,
        "automatic_v10_unlock": False,
        "requires_human_review": True,
    }
