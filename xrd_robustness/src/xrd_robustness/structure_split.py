"""Deterministic parent-structure-level split helpers for the V9-T PXRD study."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SPLITS = ("train", "validation", "test")
RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}
DEFAULT_SPLIT_SEED = 20260726
SPLIT_ALGORITHM = "sha256_seeded_crystal_system_stratified_random_v1"


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if set(ratios) != set(SPLITS):
        raise ValueError("ratios must define train, validation, and test")
    if any(float(value) < 0.0 for value in ratios.values()):
        raise ValueError("split ratios must be non-negative")
    if not math.isclose(sum(map(float, ratios.values())), 1.0, abs_tol=1e-12):
        raise ValueError("split ratios must sum to one")


def _global_targets(total: int, ratios: Mapping[str, float]) -> dict[str, int]:
    raw = {split: total * float(ratios[split]) for split in SPLITS}
    targets = {split: math.floor(raw[split]) for split in SPLITS}
    remainder = total - sum(targets.values())
    order = sorted(
        SPLITS,
        key=lambda split: (-(raw[split] - targets[split]), split),
    )
    for split in order[:remainder]:
        targets[split] += 1
    return targets


def _hamilton_class_targets(
    class_totals: Mapping[str, int],
    *,
    ratio: float,
    global_target: int,
) -> dict[str, int]:
    raw = {label: int(count) * float(ratio) for label, count in class_totals.items()}
    targets = {label: math.floor(value) for label, value in raw.items()}
    remainder = int(global_target) - sum(targets.values())
    if remainder < 0:
        raise ValueError("global target is smaller than the class-allocation floors")
    order = sorted(
        class_totals,
        key=lambda label: (-(raw[label] - targets[label]), str(label)),
    )
    for label in order[:remainder]:
        targets[label] += 1
    if sum(targets.values()) != int(global_target):
        raise ValueError("class allocation did not reach the global target")
    return targets


def _seeded_order(
    parent_structure_ids: Iterable[str],
    *,
    crystal_system: str,
    seed: int,
) -> list[str]:
    return sorted(
        map(str, parent_structure_ids),
        key=lambda parent_id: (
            hashlib.sha256(
                f"{seed}|{crystal_system}|{parent_id}".encode("utf-8")
            ).hexdigest(),
            parent_id,
        ),
    )


def assign_parent_structure_splits(
    records: Sequence[Mapping[str, Any]],
    *,
    seed: int = DEFAULT_SPLIT_SEED,
    ratios: Mapping[str, float] = RATIOS,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Assign unique parent structures using crystal-system stratified random sampling."""

    _validate_ratios(ratios)
    if not records:
        raise ValueError("records cannot be empty")

    material_ids: set[str] = set()
    parent_labels: dict[str, str] = {}
    parent_materials: dict[str, list[str]] = defaultdict(list)
    for row in records:
        material_id = str(row.get("material_id", "")).strip()
        parent_structure_id = str(
            row.get("parent_structure_id") or row.get("structure_fingerprint") or ""
        ).strip()
        crystal_system = str(row.get("crystal_system", "")).strip()
        if not material_id or not parent_structure_id or not crystal_system:
            raise ValueError(
                "each record requires material_id, parent_structure_id "
                "(or structure_fingerprint), and crystal_system"
            )
        if material_id in material_ids:
            raise ValueError(f"duplicate material_id: {material_id}")
        if (
            parent_structure_id in parent_labels
            and parent_labels[parent_structure_id] != crystal_system
        ):
            raise ValueError(
                f"conflicting crystal systems for parent structure {parent_structure_id}"
            )
        material_ids.add(material_id)
        parent_labels[parent_structure_id] = crystal_system
        parent_materials[parent_structure_id].append(material_id)

    by_class: dict[str, list[str]] = defaultdict(list)
    for parent_structure_id, crystal_system in parent_labels.items():
        by_class[crystal_system].append(parent_structure_id)
    class_totals = Counter(
        crystal_system for crystal_system in parent_labels.values()
    )
    split_targets = _global_targets(len(parent_labels), ratios)
    train_targets = _hamilton_class_targets(
        class_totals,
        ratio=float(ratios["train"]),
        global_target=split_targets["train"],
    )
    validation_targets = _hamilton_class_targets(
        class_totals,
        ratio=float(ratios["validation"]),
        global_target=split_targets["validation"],
    )
    test_targets = {
        label: (
            class_totals[label]
            - train_targets[label]
            - validation_targets[label]
        )
        for label in class_totals
    }
    if any(value < 0 for value in test_targets.values()):
        raise ValueError("class allocation produced a negative test count")
    if sum(test_targets.values()) != split_targets["test"]:
        raise ValueError("test class allocation does not match the global target")

    parent_assignments: dict[str, str] = {}
    class_counts: dict[str, dict[str, int]] = {}
    for crystal_system in sorted(by_class):
        ordered = _seeded_order(
            by_class[crystal_system],
            crystal_system=crystal_system,
            seed=int(seed),
        )
        train_end = train_targets[crystal_system]
        validation_end = train_end + validation_targets[crystal_system]
        for parent_structure_id in ordered[:train_end]:
            parent_assignments[parent_structure_id] = "train"
        for parent_structure_id in ordered[train_end:validation_end]:
            parent_assignments[parent_structure_id] = "validation"
        for parent_structure_id in ordered[validation_end:]:
            parent_assignments[parent_structure_id] = "test"
        class_counts[crystal_system] = {
            "train": train_targets[crystal_system],
            "validation": validation_targets[crystal_system],
            "test": test_targets[crystal_system],
        }

    output = [
        {
            "material_id": material_id,
            "parent_structure_id": parent_structure_id,
            "crystal_system": parent_labels[parent_structure_id],
            "split": parent_assignments[parent_structure_id],
        }
        for parent_structure_id in sorted(parent_materials)
        for material_id in sorted(parent_materials[parent_structure_id])
    ]
    validate_parent_structure_manifest(output)
    observed_parent_counts = Counter(parent_assignments.values())
    if dict(observed_parent_counts) != split_targets:
        raise ValueError(
            f"global split mismatch: {dict(observed_parent_counts)} != {split_targets}"
        )
    return output, {
        "seed": int(seed),
        "ratios": {split: float(ratios[split]) for split in SPLITS},
        "algorithm": SPLIT_ALGORITHM,
        "split_unit": "parent_structure",
        "stratification": "crystal_system",
        "parent_structure_count": len(parent_labels),
        "material_count": len(material_ids),
        "split_counts": split_targets,
        "per_crystal_system": class_counts,
    }


def validate_parent_structure_manifest(
    rows: Sequence[Mapping[str, Any]],
) -> None:
    """Reject duplicate materials, conflicting parents, or cross-split parents."""

    if not rows:
        raise ValueError("split manifest records cannot be empty")
    material_ids: set[str] = set()
    parent_assignments: dict[str, tuple[str, str]] = {}
    for index, row in enumerate(rows):
        material_id = str(row.get("material_id", "")).strip()
        parent_structure_id = str(row.get("parent_structure_id", "")).strip()
        crystal_system = str(row.get("crystal_system", "")).strip()
        split = str(row.get("split", "")).strip()
        if not material_id or not parent_structure_id or not crystal_system:
            raise ValueError(f"split manifest record {index} has a missing identifier")
        if split not in SPLITS:
            raise ValueError(f"split manifest record {index} has invalid split {split!r}")
        if material_id in material_ids:
            raise ValueError(f"duplicate material_id in split manifest: {material_id}")
        current = (split, crystal_system)
        if (
            parent_structure_id in parent_assignments
            and parent_assignments[parent_structure_id] != current
        ):
            raise ValueError(
                f"parent structure crosses splits or crystal systems: {parent_structure_id}"
            )
        material_ids.add(material_id)
        parent_assignments[parent_structure_id] = current


def load_split_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate the active JSON split manifest."""

    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("split manifest must be a JSON object")
    rows = payload.get("records")
    if not isinstance(rows, list):
        raise ValueError("split manifest must contain a records array")
    validate_parent_structure_manifest(rows)
    return payload
