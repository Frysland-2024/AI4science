"""Pre-registered V9 evaluation statistics at the parent-structure level.

The formal experiment has only three registered random seeds.  Those seeds are
not treated as the bootstrap sample.  Instead, each bootstrap replicate samples
independent parent structures within every seed, computes a
paired method contrast, and then averages the three seed-level contrasts.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np

from .metrics import classification_metrics


PREDICTION_ROW_REQUIRED_FIELDS = (
    "seed",
    "method_id",
    "profile",
    "material_id",
    "parent_structure_id",
    "label",
    "prediction",
)


def validate_prediction_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize per-spectrum rows used by the final analysis."""
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str, str]] = set()
    for index, row in enumerate(rows):
        missing = [key for key in PREDICTION_ROW_REQUIRED_FIELDS if key not in row]
        if missing:
            raise ValueError(f"prediction row {index} is missing fields: {missing}")
        item = dict(row)
        item["seed"] = int(item["seed"])
        item["method_id"] = str(item["method_id"])
        item["profile"] = str(item["profile"])
        item["material_id"] = str(item["material_id"])
        item["parent_structure_id"] = str(item["parent_structure_id"])
        item["label"] = int(item["label"])
        item["prediction"] = int(item["prediction"])
        if not item["parent_structure_id"]:
            raise ValueError(
                f"prediction row {index} has an empty parent_structure_id"
            )
        if "probabilities" in item and item["probabilities"] is not None:
            probabilities = np.asarray(item["probabilities"], dtype=np.float64)
            if probabilities.ndim != 1 or probabilities.size < 2:
                raise ValueError(f"prediction row {index} has malformed probabilities")
            if not np.isfinite(probabilities).all() or np.any(probabilities < 0):
                raise ValueError(f"prediction row {index} has invalid probabilities")
            if not np.isclose(float(probabilities.sum()), 1.0, atol=1e-5):
                raise ValueError(f"prediction row {index} probabilities do not sum to one")
            item["probabilities"] = probabilities.tolist()
        identity = (item["seed"], item["method_id"], item["profile"], item["material_id"])
        if identity in seen:
            raise ValueError(f"duplicate prediction identity: {identity}")
        seen.add(identity)
        normalized.append(item)
    if not normalized:
        raise ValueError("prediction rows cannot be empty")
    return normalized


def _num_classes(rows: Sequence[Mapping[str, Any]]) -> int:
    widths = {
        len(row["probabilities"])
        for row in rows
        if row.get("probabilities") is not None
    }
    if len(widths) > 1:
        raise ValueError("probability vectors have inconsistent class counts")
    inferred = max(max(int(row["label"]), int(row["prediction"])) for row in rows) + 1
    return max(next(iter(widths), inferred), inferred)


def summarize_prediction_rows(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Return method/seed/profile metrics without selecting a method."""
    normalized = validate_prediction_rows(rows)
    grouped: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        grouped[(row["seed"], row["method_id"], row["profile"])].append(row)
    output: dict[str, Any] = {}
    for (seed, method_id, profile), group in sorted(grouped.items()):
        probabilities = None
        if all(row.get("probabilities") is not None for row in group):
            probabilities = np.asarray([row["probabilities"] for row in group], dtype=np.float64)
        metrics = classification_metrics(
            [row["label"] for row in group],
            [row["prediction"] for row in group],
            probabilities=probabilities,
            num_classes=_num_classes(group),
            groups=[row["parent_structure_id"] for row in group],
        )
        output[f"{method_id}__seed_{seed}__{profile}"] = {
            "seed": seed,
            "method_id": method_id,
            "profile": profile,
            "independent_parent_structure_count": len(
                {row["parent_structure_id"] for row in group}
            ),
            "spectrum_count": len(group),
            "metrics": metrics,
        }
    return output


def _structure_confusion(
    rows: Sequence[Mapping[str, Any]],
    num_classes: int,
) -> np.ndarray:
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    for row in rows:
        matrix[int(row["label"]), int(row["prediction"])] += 1
    return matrix


def _macro_f1_from_confusion(matrix: np.ndarray) -> float:
    scores = []
    for index in range(matrix.shape[0]):
        tp = float(matrix[index, index])
        fp = float(matrix[:, index].sum() - matrix[index, index])
        fn = float(matrix[index].sum() - matrix[index, index])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(2.0 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return float(np.mean(scores))


def _macro_f1_from_confusion_batch(matrices: np.ndarray) -> np.ndarray:
    diagonal = np.diagonal(matrices, axis1=1, axis2=2).astype(np.float64)
    predicted = matrices.sum(axis=1, dtype=np.float64)
    actual = matrices.sum(axis=2, dtype=np.float64)
    precision = np.divide(diagonal, predicted, out=np.zeros_like(diagonal), where=predicted > 0)
    recall = np.divide(diagonal, actual, out=np.zeros_like(diagonal), where=actual > 0)
    denominator = precision + recall
    f1 = np.divide(2.0 * precision * recall, denominator, out=np.zeros_like(denominator), where=denominator > 0)
    return f1.mean(axis=1)


def hierarchical_paired_bootstrap(
    rows: Iterable[Mapping[str, Any]],
    *,
    focus_method_id: str,
    comparator_method_id: str,
    profiles: Sequence[str],
    replicates: int = 10_000,
    random_seed: int = 20260722,
) -> dict[str, Any]:
    """Paired cluster bootstrap within each seed, followed by seed averaging."""
    if replicates < 100:
        raise ValueError("at least 100 bootstrap replicates are required")
    profile_names = tuple(map(str, profiles))
    if not profile_names:
        raise ValueError("at least one profile is required")
    normalized = validate_prediction_rows(rows)
    relevant = [
        row
        for row in normalized
        if row["method_id"] in {focus_method_id, comparator_method_id}
        and row["profile"] in profile_names
    ]
    seeds = sorted({row["seed"] for row in relevant})
    if not seeds:
        raise ValueError("no rows match the requested methods and profiles")
    grouped: dict[tuple[int, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in relevant:
        grouped[
            (
                row["seed"],
                row["method_id"],
                row["profile"],
                row["parent_structure_id"],
            )
        ].append(row)

    seed_structures: dict[int, list[str]] = {}
    for seed in seeds:
        structure_sets = [
            {
                key[3]
                for key in grouped
                if key[0] == seed and key[1] == method and key[2] == profile
            }
            for method in (focus_method_id, comparator_method_id)
            for profile in profile_names
        ]
        common = sorted(set.intersection(*structure_sets)) if structure_sets else []
        if len(common) < 2:
            raise ValueError(
                f"seed {seed} has fewer than two paired parent structures "
                "across all profiles"
            )
        seed_structures[seed] = common

    num_classes = _num_classes(relevant)
    structure_confusions = {
        key: _structure_confusion(group, num_classes)
        for key, group in grouped.items()
    }

    def contrast_for(seed: int, sampled_structures: Sequence[str]) -> float:
        method_scores: dict[str, list[float]] = {focus_method_id: [], comparator_method_id: []}
        for method in method_scores:
            for profile in profile_names:
                sampled_confusion = np.zeros((num_classes, num_classes), dtype=np.int64)
                for parent_structure_id in sampled_structures:
                    sampled_confusion += structure_confusions[
                        (seed, method, profile, parent_structure_id)
                    ]
                method_scores[method].append(_macro_f1_from_confusion(sampled_confusion))
        return float(np.mean(method_scores[focus_method_id]) - np.mean(method_scores[comparator_method_id]))

    observed_seed_deltas = {
        str(seed): contrast_for(seed, seed_structures[seed]) for seed in seeds
    }
    rng = np.random.default_rng(random_seed)
    bootstrap_deltas = np.zeros(replicates, dtype=np.float64)
    for seed in seeds:
        structures = seed_structures[seed]
        counts = rng.multinomial(
            len(structures),
            np.full(len(structures), 1.0 / len(structures)),
            size=replicates,
        )
        method_scores: dict[str, np.ndarray] = {}
        for method in (focus_method_id, comparator_method_id):
            profile_scores = []
            for profile in profile_names:
                matrices = np.stack(
                    [
                        structure_confusions[
                            (seed, method, profile, parent_structure_id)
                        ]
                        for parent_structure_id in structures
                    ]
                )
                sampled_confusions = np.tensordot(counts, matrices, axes=(1, 0))
                profile_scores.append(_macro_f1_from_confusion_batch(sampled_confusions))
            method_scores[method] = np.mean(np.stack(profile_scores), axis=0)
        bootstrap_deltas += (
            method_scores[focus_method_id] - method_scores[comparator_method_id]
        ) / len(seeds)
    low, high = np.quantile(bootstrap_deltas, [0.025, 0.975])
    return {
        "focus_method_id": focus_method_id,
        "comparator_method_id": comparator_method_id,
        "metric": "mean_profile_macro_f1",
        "profiles": list(profile_names),
        "seed_ids": seeds,
        "independent_unit": "parent_structure",
        "bootstrap_design": (
            "paired_parent_structure_cluster_within_seed_"
            "then_mean_across_registered_seeds"
        ),
        "seed_resampling_forbidden": True,
        "independent_parent_structure_count_by_seed": {
            str(seed): len(seed_structures[seed]) for seed in seeds
        },
        "paired_seed_deltas": observed_seed_deltas,
        "mean_delta": float(np.mean(list(observed_seed_deltas.values()))),
        "hierarchical_bootstrap_95_ci": [float(low), float(high)],
        "bootstrap_replicates": replicates,
        "random_seed": random_seed,
    }


def class_stratified_paired_bootstrap(
    rows: Iterable[Mapping[str, Any]],
    *,
    focus_method_id: str,
    comparator_method_id: str,
    num_classes: int,
    replicates: int = 10_000,
    random_seed: int = 20260827,
) -> dict[str, Any]:
    """Paired parent bootstrap stratified by crystal system.

    Unlike :func:`hierarchical_paired_bootstrap` (which resamples parents uniformly
    across all classes), this resamples parents independently within each class so the
    natural class composition is preserved exactly at every replicate.  It is intended
    for naturally imbalanced external domains such as CNRS-318, where a uniform
    resampling would let large classes dominate the bootstrap.

    Each row must provide ``seed`` (int), ``method_id`` (str), ``parent_structure_id``
    (str), and either ``label``/``prediction`` or ``label_index``/``prediction_index``.
    """
    if replicates < 100:
        raise ValueError("at least 100 bootstrap replicates are required")
    if num_classes < 2:
        raise ValueError("num_classes must be at least two")

    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        item = dict(row)
        label = item.get("label", item.get("label_index"))
        prediction = item.get("prediction", item.get("prediction_index"))
        if label is None or prediction is None:
            raise ValueError(f"prediction row {index} is missing label/prediction")
        item["label"] = int(label)
        item["prediction"] = int(prediction)
        item["seed"] = int(item["seed"])
        item["method_id"] = str(item["method_id"])
        item["parent_structure_id"] = str(item["parent_structure_id"])
        if not item["parent_structure_id"]:
            raise ValueError(f"prediction row {index} has an empty parent_structure_id")
        normalized.append(item)

    relevant = [
        row
        for row in normalized
        if row["method_id"] in {focus_method_id, comparator_method_id}
    ]
    seeds = sorted({int(row["seed"]) for row in relevant})
    if not seeds:
        raise ValueError("no rows match the requested methods")

    grouped: dict[tuple[int, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in relevant:
        grouped[(row["seed"], row["method_id"], row["parent_structure_id"])].append(row)

    structure_confusions = {
        key: _structure_confusion(group, num_classes)
        for key, group in grouped.items()
    }

    seed_structures: dict[int, list[str]] = {}
    seed_class_of: dict[int, dict[str, int]] = {}
    for seed in seeds:
        method_parents = {
            method: {
                key[2] for key in grouped if key[0] == seed and key[1] == method
            }
            for method in (focus_method_id, comparator_method_id)
        }
        common = sorted(set.intersection(*method_parents.values()))
        if len(common) < 2:
            raise ValueError(
                f"seed {seed} has fewer than two paired parent structures"
            )
        seed_structures[seed] = common
        class_of: dict[str, int] = {}
        for parent in common:
            rows_for_parent = [
                row
                for row in relevant
                if row["seed"] == seed and row["parent_structure_id"] == parent
            ]
            class_of[parent] = int(rows_for_parent[0]["label"])
        seed_class_of[seed] = class_of

    def contrast_for(seed: int, sampled: Sequence[str]) -> float:
        scores: dict[str, float] = {}
        for method in (focus_method_id, comparator_method_id):
            matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
            for parent in sampled:
                matrix += structure_confusions[(seed, method, parent)]
            scores[method] = _macro_f1_from_confusion(matrix)
        return float(scores[focus_method_id] - scores[comparator_method_id])

    observed_seed_deltas = {
        str(seed): contrast_for(seed, seed_structures[seed]) for seed in seeds
    }

    rng = np.random.default_rng(random_seed)
    bootstrap_deltas = np.zeros(replicates, dtype=np.float64)
    for seed in seeds:
        structures = seed_structures[seed]
        class_of = seed_class_of[seed]
        by_class: dict[int, list[str]] = defaultdict(list)
        for parent in structures:
            by_class[class_of[parent]].append(parent)
        class_keys = sorted(by_class)
        method_scores: dict[str, np.ndarray] = {}
        for method in (focus_method_id, comparator_method_id):
            sampled_confusions = np.zeros(
                (replicates, num_classes, num_classes), dtype=np.float64
            )
            for cls in class_keys:
                members = by_class[cls]
                count = len(members)
                matrices = np.stack(
                    [structure_confusions[(seed, method, parent)] for parent in members]
                )
                counts = rng.multinomial(
                    count, np.full(count, 1.0 / count), size=replicates
                )
                sampled_confusions += np.tensordot(counts, matrices, axes=(1, 0))
            method_scores[method] = _macro_f1_from_confusion_batch(
                sampled_confusions.astype(np.int64)
            )
        bootstrap_deltas += (
            method_scores[focus_method_id] - method_scores[comparator_method_id]
        ) / len(seeds)

    low, high = np.quantile(bootstrap_deltas, [0.025, 0.975])
    return {
        "focus_method_id": focus_method_id,
        "comparator_method_id": comparator_method_id,
        "metric": "class_stratified_parent_macro_f1",
        "seed_ids": seeds,
        "independent_unit": "parent_structure",
        "bootstrap_design": (
            "class_stratified_paired_parent_within_seed_"
            "then_mean_across_registered_seeds"
        ),
        "seed_resampling_forbidden": True,
        "independent_parent_structure_count_by_seed": {
            str(seed): len(seed_structures[seed]) for seed in seeds
        },
        "paired_seed_deltas": observed_seed_deltas,
        "mean_delta": float(np.mean(list(observed_seed_deltas.values()))),
        "class_stratified_bootstrap_95_ci": [float(low), float(high)],
        "bootstrap_replicates": replicates,
        "random_seed": random_seed,
    }


def interpret_single_contrast(
    contrast: Mapping[str, Any],
    *,
    mean_id_delta: float | None = None,
    material_id_drop_threshold: float = -0.02,
    practical_tie_threshold: float = 0.005,
) -> str:
    """Return a deliberately restrained text label for one paired contrast."""
    mean_delta = float(contrast["mean_delta"])
    low, high = map(float, contrast["hierarchical_bootstrap_95_ci"])
    raw_seed_deltas = contrast.get("paired_seed_deltas", {})
    seed_deltas = list(raw_seed_deltas.values()) if isinstance(raw_seed_deltas, Mapping) else list(raw_seed_deltas)
    if mean_id_delta is not None and mean_delta > 0 and mean_id_delta <= material_id_drop_threshold:
        return "ood_gain_with_material_id_tradeoff"
    if abs(mean_delta) <= practical_tie_threshold and low <= 0 <= high:
        return "no_clear_difference"
    if mean_delta > 0 and low > 0 and seed_deltas and all(float(value) > 0 for value in seed_deltas):
        return "stable_positive_across_registered_seeds"
    if mean_delta > 0 and seed_deltas and any(float(value) <= 0 for value in seed_deltas):
        return "average_positive_but_mixed_seed_direction"
    if low <= 0 <= high:
        return "no_clear_difference"
    if mean_delta < 0 and high < 0:
        return "stable_negative"
    return "inconclusive"


def build_paired_statistics_report(
    rows: Iterable[Mapping[str, Any]],
    *,
    erm_method_id: str,
    js_method_id: str,
    profiles: Sequence[str],
    replicates: int = 10_000,
    random_seed: int = 20260722,
) -> dict[str, Any]:
    """Build a generic paired Dynamic JS minus Dynamic ERM report."""

    normalized = validate_prediction_rows(rows)
    js_minus_erm = hierarchical_paired_bootstrap(
        normalized,
        focus_method_id=js_method_id,
        comparator_method_id=erm_method_id,
        profiles=profiles,
        replicates=replicates,
        random_seed=random_seed,
    )
    return {
        "schema_version": "paired-js-vs-erm-parent-structure-statistics-v1",
        "analysis_scope": "prediction_rows_only",
        "selection_or_tuning_performed": False,
        "row_schema": list(PREDICTION_ROW_REQUIRED_FIELDS) + ["probabilities"],
        "summaries": summarize_prediction_rows(normalized),
        "paired_comparisons": {
            "js_minus_erm": {
                **js_minus_erm,
                "interpretation": interpret_single_contrast(js_minus_erm),
            }
        },
    }
