"""Deterministic helpers for the merged 14,060-structure V7 data tier."""

from __future__ import annotations

from collections import Counter, defaultdict
import random
from typing import Any, Iterable, Mapping

FORMAL_CLASS_ORDER = (
    "cubic",
    "hexagonal",
    "tetragonal",
    "orthorhombic",
    "trigonal",
    "monoclinic",
    "triclinic",
)


def _index_unique(
    rows: Iterable[Mapping[str, Any]], *, source_name: str
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    fingerprints: dict[str, str] = {}
    for raw in rows:
        row = dict(raw)
        material_id = str(row["material_id"])
        fingerprint = str(row["structure_fingerprint"])
        if material_id in indexed:
            raise ValueError(f"{source_name} contains duplicate material_id {material_id}")
        if fingerprint in fingerprints:
            raise ValueError(
                f"{source_name} contains duplicate structure_fingerprint {fingerprint}: "
                f"{fingerprints[fingerprint]} and {material_id}"
            )
        indexed[material_id] = row
        fingerprints[fingerprint] = material_id
    return indexed


def assign_extra_evaluation_splits(
    rows: Iterable[Mapping[str, Any]], *, seed: int = 20260711
) -> dict[str, str]:
    """Split extra structures evenly between validation and test by class.

    The existing formal training split remains untouched. Odd-sized class groups
    alternate their extra item between validation and test so the global totals
    are exactly equal.
    """

    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        material_id = str(row["material_id"])
        crystal_system = str(row["crystal_system"])
        if crystal_system not in FORMAL_CLASS_ORDER:
            raise ValueError(f"unsupported crystal system {crystal_system!r}")
        grouped[crystal_system].append(material_id)
    total = sum(len(values) for values in grouped.values())
    if total == 0 or total % 2:
        raise ValueError("extra evaluation pool must contain a positive even number of structures")

    validation_target = total // 2
    validation_by_class = {
        name: len(grouped.get(name, ())) // 2 for name in FORMAL_CLASS_ORDER
    }
    remaining = validation_target - sum(validation_by_class.values())
    odd_classes = [
        name for name in FORMAL_CLASS_ORDER if len(grouped.get(name, ())) % 2
    ]
    if remaining < 0 or remaining > len(odd_classes):
        raise ValueError("cannot balance extra validation and test totals")
    for name in odd_classes[:remaining]:
        validation_by_class[name] += 1

    assignments: dict[str, str] = {}
    for class_name in FORMAL_CLASS_ORDER:
        values = sorted(grouped.get(class_name, ()))
        random.Random(f"formal_14060-extra:{seed}:{class_name}").shuffle(values)
        validation_count = validation_by_class[class_name]
        for material_id in values[:validation_count]:
            assignments[material_id] = "validation"
        for material_id in values[validation_count:]:
            assignments[material_id] = "test"

    counts = Counter(assignments.values())
    if counts != {"validation": validation_target, "test": validation_target}:
        raise ValueError(f"unbalanced extra split: {dict(counts)}")
    return assignments


def merge_formal_and_gate_records(
    formal_rows: Iterable[Mapping[str, Any]],
    gate_rows: Iterable[Mapping[str, Any]],
    *,
    split_seed: int = 20260711,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Union two audited tiers while preserving the formal training split."""

    formal = _index_unique(formal_rows, source_name="formal source")
    gate = _index_unique(gate_rows, source_name="gate source")
    overlap_ids = sorted(set(formal).intersection(gate))
    for material_id in overlap_ids:
        left = formal[material_id]
        right = gate[material_id]
        for field in ("structure_fingerprint", "crystal_system"):
            if str(left[field]) != str(right[field]):
                raise ValueError(
                    f"overlapping material {material_id} disagrees on {field}: "
                    f"{left[field]!r} != {right[field]!r}"
                )

    extra_rows = [gate[item] for item in sorted(set(gate).difference(formal))]
    formal_fingerprints = {
        str(row["structure_fingerprint"]): material_id
        for material_id, row in formal.items()
    }
    for row in extra_rows:
        fingerprint = str(row["structure_fingerprint"])
        if fingerprint in formal_fingerprints:
            raise ValueError(
                f"extra material {row['material_id']} duplicates formal fingerprint "
                f"owned by {formal_fingerprints[fingerprint]}"
            )

    extra_assignments = assign_extra_evaluation_splits(extra_rows, seed=split_seed)
    merged: list[dict[str, Any]] = [dict(row) for row in formal.values()]
    for source in extra_rows:
        row = dict(source)
        material_id = str(row["material_id"])
        is_stable = row.get("is_stable")
        if not isinstance(is_stable, bool):
            raise ValueError(
                f"extra material {material_id} has non-boolean is_stable {is_stable!r}"
            )
        row["split"] = extra_assignments[material_id]
        row["selection_tier"] = "stable" if is_stable else "near_stable"
        merged.append(row)
    merged.sort(key=lambda row: str(row["material_id"]))

    merged_index = _index_unique(merged, source_name="merged output")
    split_counts = Counter(str(row["split"]) for row in merged)
    class_counts = Counter(str(row["crystal_system"]) for row in merged)
    train_class_counts = Counter(
        str(row["crystal_system"]) for row in merged if str(row["split"]) == "train"
    )
    report = {
        "formal_count": len(formal),
        "gate_count": len(gate),
        "overlap_count": len(overlap_ids),
        "extra_count": len(extra_rows),
        "merged_count": len(merged_index),
        "split_counts": dict(sorted(split_counts.items())),
        "class_counts": {name: class_counts[name] for name in FORMAL_CLASS_ORDER},
        "train_class_counts": {
            name: train_class_counts[name] for name in FORMAL_CLASS_ORDER
        },
        "extra_split_counts": dict(sorted(Counter(extra_assignments.values()).items())),
        "extra_ids": sorted(extra_assignments),
        "overlap_ids": overlap_ids,
    }
    return merged, report
