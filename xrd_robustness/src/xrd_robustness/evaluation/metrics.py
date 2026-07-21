"""Dependency-light metrics for in-range, OOD, and paired-view evaluation."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import numpy as np


def _confusion(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for truth, prediction in zip(y_true.reshape(-1), y_pred.reshape(-1), strict=True):
        if not 0 <= int(truth) < num_classes or not 0 <= int(prediction) < num_classes:
            raise ValueError("class index outside configured range")
        matrix[int(truth), int(prediction)] += 1
    return matrix


def expected_calibration_error(probabilities: np.ndarray, labels: np.ndarray, bins: int = 15) -> float:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64).reshape(-1)
    confidence = probabilities.max(axis=1)
    predictions = probabilities.argmax(axis=1)
    edges = np.linspace(0.0, 1.0, bins + 1)
    error = 0.0
    for left, right in zip(edges[:-1], edges[1:], strict=True):
        mask = (confidence > left) & (confidence <= right if right < 1.0 else confidence <= right)
        if not np.any(mask):
            continue
        error += float(mask.mean()) * abs(float(confidence[mask].mean()) - float((predictions[mask] == labels[mask]).mean()))
    return error


def classification_metrics(
    labels: Iterable[int],
    predictions: Iterable[int],
    *,
    probabilities: np.ndarray | None = None,
    num_classes: int = 7,
    groups: Iterable[Any] | None = None,
) -> dict[str, Any]:
    y_true = np.asarray(list(labels), dtype=np.int64)
    y_pred = np.asarray(list(predictions), dtype=np.int64)
    if y_true.shape != y_pred.shape or y_true.size == 0:
        raise ValueError("labels and predictions must be non-empty and have identical shape")
    matrix = _confusion(y_true, y_pred, num_classes)
    recalls: list[float] = []
    f1s: list[float] = []
    for index in range(num_classes):
        tp = float(matrix[index, index])
        fn = float(matrix[index].sum() - matrix[index, index])
        fp = float(matrix[:, index].sum() - matrix[index, index])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        recalls.append(recall)
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    output: dict[str, Any] = {
        "accuracy": float(np.mean(y_true == y_pred)),
        "balanced_accuracy": float(np.mean(recalls)),
        "macro_f1": float(np.mean(f1s)),
        "per_class_recall": recalls,
        "per_class_f1": f1s,
        "confusion_matrix": matrix.tolist(),
        "worst_group_f1": float(min(f1s)),
    }
    if probabilities is not None:
        probabilities = np.asarray(probabilities, dtype=np.float64)
        if probabilities.shape[0] != y_true.shape[0]:
            raise ValueError("probabilities and labels have different batch sizes")
        output["ece"] = expected_calibration_error(probabilities, y_true)
    if groups is not None:
        group_values = np.asarray(list(groups))
        group_f1 = []
        for group in np.unique(group_values):
            mask = group_values == group
            if np.any(mask):
                group_f1.append(
                    classification_metrics(y_true[mask], y_pred[mask], num_classes=num_classes)["macro_f1"]
                )
        if group_f1:
            output["worst_group_f1"] = float(min(group_f1))
    return output


def paired_view_metrics(
    first_probabilities: np.ndarray,
    second_probabilities: np.ndarray,
    labels: Iterable[int],
) -> dict[str, float]:
    first = np.asarray(first_probabilities, dtype=np.float64)
    second = np.asarray(second_probabilities, dtype=np.float64)
    labels = np.asarray(list(labels), dtype=np.int64)
    if first.shape != second.shape or first.shape[0] != labels.shape[0]:
        raise ValueError("paired probability arrays must have identical batch sizes")
    first = np.clip(first, 1e-12, 1.0)
    second = np.clip(second, 1e-12, 1.0)
    midpoint = 0.5 * (first + second)
    js = 0.5 * np.sum(first * (np.log(first) - np.log(midpoint)), axis=1)
    js += 0.5 * np.sum(second * (np.log(second) - np.log(midpoint)), axis=1)
    first_pred = first.argmax(axis=1)
    second_pred = second.argmax(axis=1)
    correct_and_consistent = (first_pred == labels) & (second_pred == labels) & (first_pred == second_pred)
    return {
        "prediction_agreement": float(np.mean(first_pred == second_pred)),
        "paired_js": float(np.mean(js)),
        "correct_and_consistent_rate": float(np.mean(correct_and_consistent)),
    }


def robustness_auc(severity: Iterable[float], values: Iterable[float]) -> float:
    x = np.asarray(list(severity), dtype=np.float64)
    y = np.asarray(list(values), dtype=np.float64)
    if x.size != y.size or x.size < 2:
        raise ValueError("at least two severity/value pairs are required")
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    span = float(x[-1] - x[0])
    integral = np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x)
    return float(integral / span) if span > 0 else float(y.mean())


def residual_diagnostics(
    residual: np.ndarray,
    *,
    probe_logits: np.ndarray | None = None,
) -> dict[str, float]:
    residual = np.asarray(residual, dtype=np.float64)
    if residual.ndim != 2:
        raise ValueError("residual must have shape [batch, embedding_dim]")
    output = {"residual_norm": float(np.linalg.norm(residual, axis=1).mean())}
    if probe_logits is not None:
        logits = np.asarray(probe_logits, dtype=np.float64)
        shifted = logits - logits.max(axis=1, keepdims=True)
        probabilities = np.exp(shifted)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        entropy = -np.sum(probabilities * np.log(np.clip(probabilities, 1e-12, 1.0)), axis=1)
        output["residual_prediction_entropy"] = float(entropy.mean())
    return output
