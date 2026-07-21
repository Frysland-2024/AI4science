"""Deterministic, leakage-safe structure-level split construction."""

from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


DEFAULT_RATIOS = {"train": 0.7, "validation": 0.1, "test": 0.2}


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if set(ratios) != {"train", "validation", "test"}:
        raise ValueError("ratios must define train, validation, and test")
    if any(value < 0 for value in ratios.values()):
        raise ValueError("split ratios must be non-negative")
    if not math.isclose(sum(ratios.values()), 1.0, abs_tol=1e-9):
        raise ValueError("split ratios must sum to 1")


def _allocate_counts(count: int, ratios: Mapping[str, float]) -> dict[str, int]:
    raw = {name: count * ratios[name] for name in ratios}
    allocated = {name: int(math.floor(value)) for name, value in raw.items()}
    remainder = count - sum(allocated.values())
    order = sorted(
        ratios,
        key=lambda name: (raw[name] - allocated[name], ratios[name], name),
        reverse=True,
    )
    for name in order[:remainder]:
        allocated[name] += 1
    return allocated


def build_structure_split_manifest(
    records: Iterable[Mapping[str, Any]],
    *,
    structure_key: str = "structure_id",
    label_key: str = "crystal_system",
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = 20260711,
) -> list[dict[str, Any]]:
    """Assign structures to deterministic label-stratified splits.

    Repeated views of one structure are collapsed before assignment. Conflicting
    labels for the same structure are rejected.
    """
    _validate_ratios(ratios)
    structure_labels: dict[str, Any] = {}
    view_counts: dict[str, int] = defaultdict(int)
    for record in records:
        if structure_key not in record or label_key not in record:
            raise KeyError(f"records require {structure_key!r} and {label_key!r}")
        structure_id = str(record[structure_key])
        label = record[label_key]
        if structure_id in structure_labels and structure_labels[structure_id] != label:
            raise ValueError(f"conflicting labels for structure {structure_id}")
        structure_labels[structure_id] = label
        view_counts[structure_id] += 1

    by_label: dict[Any, list[str]] = defaultdict(list)
    for structure_id, label in structure_labels.items():
        by_label[label].append(structure_id)

    assignments: dict[str, str] = {}
    for label in sorted(by_label, key=str):
        structure_ids = sorted(by_label[label])
        label_seed = f"{seed}:{label}"
        random.Random(label_seed).shuffle(structure_ids)
        counts = _allocate_counts(len(structure_ids), ratios)
        cursor = 0
        for split in ("train", "validation", "test"):
            next_cursor = cursor + counts[split]
            for structure_id in structure_ids[cursor:next_cursor]:
                assignments[structure_id] = split
            cursor = next_cursor

    manifest = [
        {
            "structure_id": structure_id,
            "crystal_system": structure_labels[structure_id],
            "split": assignments[structure_id],
            "view_count": view_counts[structure_id],
            "seed": seed,
        }
        for structure_id in sorted(structure_labels)
    ]
    validate_split_manifest(manifest)
    return manifest


def validate_split_manifest(manifest: Sequence[Mapping[str, Any]]) -> None:
    """Raise when a structure is assigned to multiple splits or labels."""
    seen: dict[str, tuple[str, Any]] = {}
    for row in manifest:
        structure_id = str(row["structure_id"])
        current = (str(row["split"]), row["crystal_system"])
        if current[0] not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split {current[0]!r}")
        if structure_id in seen and seen[structure_id] != current:
            raise ValueError(f"structure {structure_id} crosses splits or labels")
        seen[structure_id] = current


def write_split_manifest(path: str | Path, manifest: Sequence[Mapping[str, Any]]) -> None:
    """Write a stable CSV manifest after validation."""
    validate_split_manifest(manifest)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["structure_id", "crystal_system", "split", "view_count", "seed"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)

