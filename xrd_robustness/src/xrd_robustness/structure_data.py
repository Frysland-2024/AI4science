"""Structure-only records and leakage-safe manifest helpers.

Formal datasets in this project persist structures and provenance only. XRD
arrays are deliberately excluded because training views are generated online.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .splitting import DEFAULT_RATIOS, build_structure_split_manifest


PERSISTED_STRUCTURE_FIELDS = (
    "material_id",
    "formula",
    "original_structure",
    "standardized_structure",
    "space_group_mp",
    "space_group_recomputed",
    "crystal_system",
    "nsites",
    "is_stable",
    "energy_above_hull",
    "structure_fingerprint",
    "split",
)

FORBIDDEN_SPECTRUM_FIELDS = frozenset(
    {
        "xrd_reference",
        "xrd_clean",
        "canonical_profile",
        "canonical_reference_spectrum",
        "clean_mother_spectrum",
    }
)

CRYSTAL_SYSTEMS = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)

SUPPORTED_DATASET_SIZES = (140, 3500, 14000)


def select_nested_structure_records(
    records: Sequence[Mapping[str, Any]],
    *,
    dataset_size: int,
) -> list[dict[str, Any]]:
    """Select the fixed class-balanced 140/3500/14000 nested tier."""
    if dataset_size not in SUPPORTED_DATASET_SIZES:
        raise ValueError(f"dataset_size must be one of {SUPPORTED_DATASET_SIZES}")
    per_class = dataset_size // len(CRYSTAL_SYSTEMS)
    grouped: dict[str, list[Mapping[str, Any]]] = {name: [] for name in CRYSTAL_SYSTEMS}
    for record in records:
        system = str(record["crystal_system"])
        if system not in grouped:
            raise ValueError(f"unknown crystal system: {system}")
        grouped[system].append(record)
    selected: list[dict[str, Any]] = []
    for system in CRYSTAL_SYSTEMS:
        candidates = sorted(grouped[system], key=lambda row: str(row["material_id"]))
        if len(candidates) < per_class:
            raise ValueError(
                f"dataset tier {dataset_size} requires {per_class} {system} structures, "
                f"but only {len(candidates)} are available"
            )
        selected.extend(dict(row) for row in candidates[:per_class])
    return sorted(selected, key=lambda row: str(row["material_id"]))


def crystal_system_from_space_group(space_group: int) -> str:
    """Map an international space-group number to its crystal system."""
    sg = int(space_group)
    bounds = ((2, 0), (15, 1), (74, 2), (142, 3), (167, 4), (194, 5), (230, 6))
    for upper, index in bounds:
        if 1 <= sg <= upper:
            return CRYSTAL_SYSTEMS[index]
    raise ValueError(f"invalid space-group number: {sg}")


def exact_structure_fingerprint(structure: Any, decimals: int = 8) -> str:
    """Fingerprint an exact cell independent of site ordering.

    This is an exact-cell duplicate screen, not a claim of symmetry
    equivalence. The input is expected to follow pymatgen's Structure API.
    """
    lattice = np.round(np.asarray(structure.lattice.matrix, dtype=np.float64), decimals)
    sites: list[tuple[Any, ...]] = []
    for site in structure:
        frac = np.mod(np.asarray(site.frac_coords, dtype=np.float64), 1.0)
        frac = np.round(frac, decimals)
        frac[np.isclose(frac, 1.0, atol=10 ** (-decimals))] = 0.0
        sites.append((str(site.species), *frac.tolist()))
    sites.sort()
    payload = {
        "version": "exact-cell-v1",
        "lattice": lattice.tolist(),
        "sites": sites,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MaterialStructureRecord:
    material_id: str
    formula: str
    original_structure: Mapping[str, Any]
    standardized_structure: Mapping[str, Any]
    space_group_mp: int
    space_group_recomputed: int
    crystal_system: str
    nsites: int
    is_stable: bool
    energy_above_hull: float
    structure_fingerprint: str
    split: str

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        validate_persisted_structure_record(row)
        return row


def validate_persisted_structure_record(record: Mapping[str, Any]) -> None:
    """Validate the formal structure-only storage contract."""
    forbidden = FORBIDDEN_SPECTRUM_FIELDS.intersection(record)
    if forbidden:
        raise ValueError(f"formal structure record contains spectrum fields: {sorted(forbidden)}")
    missing = set(PERSISTED_STRUCTURE_FIELDS).difference(record)
    if missing:
        raise ValueError(f"formal structure record is missing fields: {sorted(missing)}")
    if str(record["split"]) not in {"train", "validation", "test"}:
        raise ValueError(f"invalid split: {record['split']!r}")
    if crystal_system_from_space_group(int(record["space_group_recomputed"])) != str(
        record["crystal_system"]
    ):
        raise ValueError("crystal_system disagrees with space_group_recomputed")
    if "selection_tier" in record:
        tier = str(record["selection_tier"])
        if tier not in {"stable", "near_stable"}:
            raise ValueError(f"invalid selection_tier: {tier!r}")
        if bool(record["is_stable"]) != (tier == "stable"):
            raise ValueError("selection_tier disagrees with is_stable")


def assign_structure_splits(
    records: Sequence[Mapping[str, Any]],
    *,
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = 20260711,
) -> list[dict[str, Any]]:
    """Attach deterministic splits after enforcing ID and fingerprint uniqueness."""
    material_ids: set[str] = set()
    fingerprints: set[str] = set()
    for record in records:
        material_id = str(record["material_id"])
        fingerprint = str(record["structure_fingerprint"])
        if material_id in material_ids:
            raise ValueError(f"duplicate material_id: {material_id}")
        if fingerprint in fingerprints:
            raise ValueError(f"duplicate structure_fingerprint: {fingerprint}")
        material_ids.add(material_id)
        fingerprints.add(fingerprint)

    split_rows = build_structure_split_manifest(
        (
            {
                "structure_fingerprint": row["structure_fingerprint"],
                "crystal_system": row["crystal_system"],
            }
            for row in records
        ),
        structure_key="structure_fingerprint",
        ratios=ratios,
        seed=seed,
    )
    split_by_fingerprint = {row["structure_id"]: row["split"] for row in split_rows}
    output = []
    for row in records:
        item = dict(row)
        item["split"] = split_by_fingerprint[str(row["structure_fingerprint"])]
        output.append(item)
    return output


def validate_no_split_leakage(records: Iterable[Mapping[str, Any]]) -> None:
    """Ensure neither source IDs nor exact structure identities cross splits."""
    id_splits: dict[str, str] = {}
    fingerprint_splits: dict[str, str] = {}
    for row in records:
        split = str(row["split"])
        for key, seen in (
            (str(row["material_id"]), id_splits),
            (str(row["structure_fingerprint"]), fingerprint_splits),
        ):
            previous = seen.setdefault(key, split)
            if previous != split:
                raise ValueError(f"identity {key} crosses {previous} and {split}")
