"""Deterministic family-aware split helpers for the V9-T PXRD study."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from pymatgen.core import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


SPLITS = ("train", "validation", "test")
RATIOS = {"train": 0.70, "validation": 0.15, "test": 0.15}
FAMILY_SIGNATURE_VERSION = "anonymous-wyckoff-family-v1"


def anonymous_wyckoff_family_id(
    structure_payload: Mapping[str, Any],
    *,
    expected_space_group: int,
    symprec: float = 0.01,
    angle_tolerance: float = 5.0,
) -> str:
    """Return a chemistry-anonymous, conservative crystallographic family ID.

    The signature intentionally ignores element identities while retaining the
    re-analysed space group and each anonymous species' Wyckoff-orbit pattern.
    It is a reproducible family proxy, not an AFLOW/XtalFinder label.
    """

    structure = Structure.from_dict(dict(structure_payload))
    dataset = SpacegroupAnalyzer(
        structure,
        symprec=symprec,
        angle_tolerance=angle_tolerance,
    ).get_symmetry_dataset()
    observed_space_group = int(dataset.number)
    if observed_space_group != int(expected_space_group):
        raise ValueError(
            "family signature space-group mismatch: "
            f"{observed_space_group} != {expected_space_group}"
        )

    equivalent_sites: dict[int, list[int]] = defaultdict(list)
    for index, orbit in enumerate(map(int, dataset.equivalent_atoms)):
        equivalent_sites[orbit].append(index)

    species_patterns: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for indices in equivalent_sites.values():
        representative = indices[0]
        species = str(structure[representative].species)
        species_patterns[species].append(
            (len(indices), str(dataset.wyckoffs[representative]))
        )

    anonymous_patterns = sorted(
        sorted(patterns) for patterns in species_patterns.values()
    )
    payload = {
        "version": FAMILY_SIGNATURE_VERSION,
        "space_group": observed_space_group,
        "anonymous_species_wyckoff_orbits": anonymous_patterns,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hamilton_targets(
    class_totals: Mapping[str, int],
    *,
    ratio: float,
    global_target: int,
) -> dict[str, int]:
    raw = {label: int(count) * ratio for label, count in class_totals.items()}
    targets = {label: math.floor(value) for label, value in raw.items()}
    remainder = int(global_target) - sum(targets.values())
    if remainder < 0:
        raise ValueError("global target is smaller than Hamilton floor allocation")
    order = sorted(
        class_totals,
        key=lambda label: (-(raw[label] - targets[label]), str(label)),
    )
    for label in order[:remainder]:
        targets[label] += 1
    if sum(targets.values()) != int(global_target):
        raise ValueError("Hamilton allocation did not reach the requested global target")
    return targets


def _subset_exact(
    families: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    target: int,
    *,
    seed: int,
    salt: str,
) -> set[str] | None:
    ordered = sorted(
        families,
        key=lambda item: hashlib.sha256(
            f"{seed}|{salt}|{item[0]}".encode("utf-8")
        ).hexdigest(),
    )
    predecessor: list[tuple[int, int] | None] = [None] * (target + 1)
    predecessor[0] = (-1, -1)
    for index, (_, rows) in enumerate(ordered):
        weight = len(rows)
        if weight > target:
            continue
        for subtotal in range(target, weight - 1, -1):
            if predecessor[subtotal] is None and predecessor[subtotal - weight] is not None:
                predecessor[subtotal] = (subtotal - weight, index)
    if predecessor[target] is None:
        return None

    selected: set[str] = set()
    subtotal = target
    while subtotal:
        previous, index = predecessor[subtotal]  # type: ignore[misc]
        selected.add(ordered[index][0])
        subtotal = previous
    return selected


def _select_two_disjoint_exact_subsets(
    families: Sequence[tuple[str, Sequence[Mapping[str, Any]]]],
    *,
    validation_target: int,
    test_target: int,
    seed: int,
    label: str,
) -> tuple[set[str], set[str], int, int]:
    """Minimize the largest evaluation-family size, then assign exact counts."""

    maximum_size = max(len(rows) for _, rows in families)
    for cap in range(1, maximum_size + 1):
        eligible = [(family_id, rows) for family_id, rows in families if len(rows) <= cap]
        if sum(len(rows) for _, rows in eligible) < validation_target + test_target:
            continue
        for attempt in range(512):
            if attempt % 2 == 0:
                validation = _subset_exact(
                    eligible,
                    validation_target,
                    seed=seed,
                    salt=f"{label}|validation|{attempt}",
                )
                if validation is None:
                    continue
                remaining = [item for item in eligible if item[0] not in validation]
                test = _subset_exact(
                    remaining,
                    test_target,
                    seed=seed,
                    salt=f"{label}|test|{attempt}",
                )
            else:
                test = _subset_exact(
                    eligible,
                    test_target,
                    seed=seed,
                    salt=f"{label}|test|{attempt}",
                )
                if test is None:
                    continue
                remaining = [item for item in eligible if item[0] not in test]
                validation = _subset_exact(
                    remaining,
                    validation_target,
                    seed=seed,
                    salt=f"{label}|validation|{attempt}",
                )
            if validation is not None and test is not None:
                return validation, test, cap, attempt
    raise ValueError(f"cannot assign exact family-aware evaluation counts for {label}")


def assign_family_aware_splits(
    records: Sequence[Mapping[str, Any]],
    *,
    family_ids: Mapping[str, str],
    seed: int = 20260716,
    split_targets: Mapping[str, int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Assign whole families with exact global counts and class stratification."""

    targets = dict(split_targets or {"train": 9842, "validation": 2109, "test": 2109})
    if set(targets) != set(SPLITS) or sum(targets.values()) != len(records):
        raise ValueError("split targets must cover every record exactly")

    material_ids: set[str] = set()
    fingerprints: set[str] = set()
    class_totals: Counter[str] = Counter()
    family_rows: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        material_id = str(row["material_id"])
        fingerprint = str(row["structure_fingerprint"])
        label = str(row["crystal_system"])
        if material_id in material_ids:
            raise ValueError(f"duplicate material_id: {material_id}")
        if fingerprint in fingerprints:
            raise ValueError(f"duplicate structure_fingerprint: {fingerprint}")
        if material_id not in family_ids:
            raise ValueError(f"missing family ID for {material_id}")
        material_ids.add(material_id)
        fingerprints.add(fingerprint)
        class_totals[label] += 1
        family_rows[(label, str(family_ids[material_id]))].append(row)

    train_targets = _hamilton_targets(
        class_totals,
        ratio=RATIOS["train"],
        global_target=targets["train"],
    )
    validation_targets = _hamilton_targets(
        class_totals,
        ratio=RATIOS["validation"],
        global_target=targets["validation"],
    )
    test_targets = {
        label: class_totals[label] - train_targets[label] - validation_targets[label]
        for label in class_totals
    }
    if sum(test_targets.values()) != targets["test"]:
        raise ValueError("test class targets do not match the global target")

    assignment: dict[str, str] = {}
    class_report: dict[str, Any] = {}
    for label in sorted(class_totals):
        families = sorted(
            (
                (family_id, rows)
                for (family_label, family_id), rows in family_rows.items()
                if family_label == label
            ),
            key=lambda item: item[0],
        )
        validation_families, test_families, cap, attempt = (
            _select_two_disjoint_exact_subsets(
                families,
                validation_target=validation_targets[label],
                test_target=test_targets[label],
                seed=seed,
                label=label,
            )
        )
        split_family_counts: Counter[str] = Counter()
        split_structure_counts: Counter[str] = Counter()
        for family_id, rows in families:
            split = (
                "validation"
                if family_id in validation_families
                else "test"
                if family_id in test_families
                else "train"
            )
            split_family_counts[split] += 1
            split_structure_counts[split] += len(rows)
            for row in rows:
                assignment[str(row["material_id"])] = split
        expected = {
            "train": train_targets[label],
            "validation": validation_targets[label],
            "test": test_targets[label],
        }
        if dict(split_structure_counts) != expected:
            raise ValueError(f"class split mismatch for {label}: {split_structure_counts} != {expected}")
        class_report[label] = {
            "total_structures": class_totals[label],
            "structure_counts": expected,
            "family_counts": {name: split_family_counts[name] for name in SPLITS},
            "minimum_feasible_max_evaluation_family_size": cap,
            "deterministic_assignment_attempt": attempt,
        }

    output: list[dict[str, Any]] = []
    for row in records:
        material_id = str(row["material_id"])
        output.append(
            {
                "material_id": material_id,
                "structure_fingerprint": str(row["structure_fingerprint"]),
                "crystal_system": str(row["crystal_system"]),
                "family_id": str(family_ids[material_id]),
                "family_signature_version": FAMILY_SIGNATURE_VERSION,
                "split": assignment[material_id],
                "split_seed": int(seed),
            }
        )
    output.sort(key=lambda row: row["material_id"])
    observed = Counter(str(row["split"]) for row in output)
    if dict(observed) != targets:
        raise ValueError(f"global split mismatch: {observed} != {targets}")
    return output, {
        "split_seed": int(seed),
        "ratios": RATIOS,
        "split_counts": targets,
        "class_counts": class_report,
        "family_signature_version": FAMILY_SIGNATURE_VERSION,
        "family_definition": (
            "re-analysed space group plus chemistry-anonymous species-wise "
            "Wyckoff orbit letters and multiplicities"
        ),
        "family_definition_scope": "conservative deterministic proxy; not an AFLOW/XtalFinder label",
        "family_count": len({str(row["family_id"]) for row in output}),
    }
