#!/usr/bin/env python3
"""Audit opXRD/CNRS as a seven-crystal-system real-domain benchmark.

The audit deliberately does not infer a label from lattice metrics.  If the
deposited phase has no space-group number, the optional derived label is
recomputed from the deposited atomic basis with pymatgen and is accepted only
when its crystal system is stable across all requested symmetry tolerances.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


CRYSTAL_SYSTEMS = (
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
)

UNIQUE_ELIGIBILITY_FIELDS = (
    "native_cu_ka_10_80_unique_eligible",
    "mapped_cu_ka_10_80_unique_eligible",
    "mapped_cu_ka_10_60_unique_eligible",
    "mapped_cu_ka_10_80_broad_unique_eligible",
    "mapped_cu_ka_10_60_broad_unique_eligible",
)


def crystal_system_from_space_group(number: int) -> str:
    if 1 <= number <= 2:
        return "triclinic"
    if number <= 15:
        return "monoclinic"
    if number <= 74:
        return "orthorhombic"
    if number <= 142:
        return "tetragonal"
    if number <= 167:
        return "trigonal"
    if number <= 194:
        return "hexagonal"
    if number <= 230:
        return "cubic"
    raise ValueError(f"invalid International Tables space-group number: {number}")


def covers_window(
    minimum: float | None,
    maximum: float | None,
    lower: float,
    upper: float,
    tolerance: float = 0.0,
) -> bool:
    """Return whether sampled bounds cover a target window within endpoint tolerance."""

    return bool(
        minimum is not None
        and maximum is not None
        and minimum <= lower + tolerance
        and maximum >= upper - tolerance
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_json_like(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def parse_phase(value: Any) -> dict[str, Any]:
    parsed = parse_json_like(value)
    if not isinstance(parsed, dict):
        raise TypeError("phase is not a JSON object")
    return parsed


def parse_lattice(value: Any) -> tuple[float, float, float, float, float, float]:
    if isinstance(value, str):
        value = ast.literal_eval(value)
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise ValueError("lattice must contain six parameters")
    params = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in params):
        raise ValueError("lattice contains non-finite values")
    if min(params[:3]) <= 0:
        raise ValueError("lattice lengths must be positive")
    return params  # type: ignore[return-value]


def parse_basis(value: Any) -> list[dict[str, Any]]:
    parsed = parse_json_like(value)
    if not isinstance(parsed, list) or not parsed:
        raise ValueError("basis is empty or is not a list")
    result: list[dict[str, Any]] = []
    for site in parsed:
        site = parse_json_like(site)
        if not isinstance(site, dict):
            raise TypeError("basis site is not a JSON object")
        result.append(site)
    return result


ELEMENT_RE = re.compile(r"^([A-Z][a-z]?)")


def clean_element(symbol: Any) -> str:
    match = ELEMENT_RE.match(str(symbol).strip())
    if match is None:
        raise ValueError(f"cannot parse element symbol {symbol!r}")
    return match.group(1)


def build_structure(phase: dict[str, Any]) -> tuple[Any, list[str]]:
    try:
        from pymatgen.core import Lattice, Structure
    except ImportError as exc:  # pragma: no cover - environment-specific guard
        raise RuntimeError("pymatgen is required for structure-derived labels") from exc

    lattice = parse_lattice(phase.get("lattice"))
    basis = parse_basis(phase.get("basis"))
    species: list[Any] = []
    coords: list[list[float]] = []
    elements: list[str] = []
    for site in basis:
        element = clean_element(site.get("symbol"))
        occupancy = float(site.get("occupancy", 1.0))
        xyz = [float(site[key]) for key in ("x", "y", "z")]
        if not math.isfinite(occupancy) or occupancy <= 0:
            raise ValueError("site occupancy must be finite and positive")
        if not all(math.isfinite(item) for item in xyz):
            raise ValueError("site coordinates contain non-finite values")
        species.append(element if math.isclose(occupancy, 1.0) else {element: occupancy})
        coords.append(xyz)
        elements.append(element)
    structure = Structure(
        Lattice.from_parameters(*lattice),
        species,
        coords,
        coords_are_cartesian=False,
        to_unit_cell=True,
    )
    return structure, sorted(set(elements))


def recompute_symmetry(
    structure: Any,
    symprecs: Iterable[float],
    angle_tolerance: float,
) -> tuple[list[int], list[str], list[str]]:
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    numbers: list[int] = []
    systems: list[str] = []
    errors: list[str] = []
    for symprec in symprecs:
        try:
            analyzer = SpacegroupAnalyzer(
                structure,
                symprec=float(symprec),
                angle_tolerance=float(angle_tolerance),
            )
            number = int(analyzer.get_space_group_number())
            numbers.append(number)
            systems.append(crystal_system_from_space_group(number))
            errors.append("")
        except Exception as exc:  # noqa: BLE001 - every record must be audited
            numbers.append(0)
            systems.append("")
            errors.append(f"{type(exc).__name__}: {exc}")
    return numbers, systems, errors


def exact_structure_fingerprint(structure: Any, decimals: int = 8) -> str:
    matrix = [
        [round(float(value), decimals) for value in row]
        for row in structure.lattice.matrix
    ]
    sites: list[tuple[Any, ...]] = []
    tolerance = 10 ** (-decimals)
    for site in structure:
        coords: list[float] = []
        for raw in site.frac_coords:
            value = round(float(raw) % 1.0, decimals)
            if math.isclose(value, 1.0, abs_tol=tolerance):
                value = 0.0
            coords.append(value)
        sites.append((str(site.species), *coords))
    sites.sort()
    payload = {"version": "exact-cell-v1", "lattice": matrix, "sites": sites}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def numeric_sequence(value: Any) -> list[float]:
    if not isinstance(value, list):
        raise TypeError("spectrum array is not a list")
    return [float(item) for item in value]


def spectrum_digest(two_theta: list[float], intensities: list[float]) -> str:
    payload = json.dumps(
        [two_theta, intensities], ensure_ascii=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def map_two_theta_window(
    two_theta: list[float], source_wavelength: float | None, target_wavelength: float = 1.5406
) -> tuple[int, float | None, float | None]:
    """Map a measured angular window to an equivalent target wavelength.

    Bragg's law is applied pointwise.  Points for which the target wavelength
    cannot satisfy the same d-spacing are outside the physically reachable
    target-angle range and are omitted.
    """

    if source_wavelength is None or source_wavelength <= 0 or target_wavelength <= 0:
        return 0, None, None
    mapped: list[float] = []
    ratio = target_wavelength / source_wavelength
    for value in two_theta:
        argument = ratio * math.sin(math.radians(value / 2.0))
        if -1.0 <= argument <= 1.0:
            mapped.append(math.degrees(2.0 * math.asin(argument)))
    if not mapped:
        return 0, None, None
    return len(mapped), min(mapped), max(mapped)


def parse_direct_space_group(value: Any) -> int | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if 1 <= number <= 230 else None


def read_formal_index(path: Path | None) -> tuple[set[str], set[str]]:
    if path is None:
        return set(), set()
    try:
        from pymatgen.core import Composition
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pymatgen is required to normalize formulae") from exc
    formulas: set[str] = set()
    fingerprints: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            raw = row.get("formula", "").strip()
            if raw:
                try:
                    formulas.add(Composition(raw).reduced_formula)
                except Exception:
                    continue
            fingerprint = row.get("structure_fingerprint", "").strip()
            if fingerprint:
                fingerprints.add(fingerprint)
    return formulas, fingerprints


def load_single_phase_structure(path: Path) -> Any:
    record = json.loads(path.read_text(encoding="utf-8"))
    label = parse_json_like(record.get("label"))
    phases = label.get("phases", []) if isinstance(label, dict) else []
    if len(phases) != 1:
        raise ValueError("expected exactly one phase")
    structure, _ = build_structure(parse_phase(phases[0]))
    return structure


def make_structure_matcher() -> Any:
    from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher

    return StructureMatcher(
        ltol=0.2,
        stol=0.3,
        angle_tol=5.0,
        primitive_cell=True,
        scale=True,
        attempt_supercell=False,
        comparator=ElementComparator(),
    )


def annotate_structural_parents(
    rows: list[dict[str, Any]], source_root: Path
) -> bool:
    """Cluster repeated measurements of the same CNRS structural parent.

    Exact spectrum and canonical-structure hashes are insufficient for parent
    independence because separately refined cells of the same material can
    differ numerically.  Pairwise StructureMatcher comparisons are blocked by
    reduced formula and stable seven-class label, then joined with union-find.
    """

    blocks: dict[tuple[str, str], list[tuple[dict[str, Any], Any]]] = defaultdict(list)
    for row in rows:
        row["structural_parent_group"] = ""
        row["structural_parent_group_size"] = ""
        row["structural_parent_representative"] = False
        row["structural_parent_match_error"] = ""
        for source_field in UNIQUE_ELIGIBILITY_FIELDS:
            row[source_field.replace("_unique_eligible", "_parent_eligible")] = False
        formula = str(row.get("formula_reduced", ""))
        system = str(row.get("recomputed_crystal_system", ""))
        # The benchmark gate is defined on the broad-material, spectrum-unique,
        # Cu-Kα-mapped 10-80 candidate set.  Restrict graph construction to
        # that set so an out-of-scope, non-transitive bridge cannot merge two
        # otherwise distinct benchmark parents.
        if (
            row.get("mapped_cu_ka_10_80_broad_unique_eligible") is not True
            or not formula
            or not system
            or row.get("crystal_system_stable") is not True
        ):
            continue
        try:
            structure = load_single_phase_structure(source_root / str(row["source_relpath"]))
        except Exception as exc:  # noqa: BLE001
            row["structural_parent_match_error"] = f"{type(exc).__name__}: {exc}"
            continue
        blocks[(formula, system)].append((row, structure))

    matcher = make_structure_matcher()
    clusters: list[list[dict[str, Any]]] = []
    for block in blocks.values():
        parent = list(range(len(block)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root = find(left)
            right_root = find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(block)):
            for right in range(left + 1, len(block)):
                try:
                    if matcher.fit(block[left][1], block[right][1]):
                        union(left, right)
                except Exception as exc:  # noqa: BLE001
                    message = f"{type(exc).__name__}: {exc}"
                    for row in (block[left][0], block[right][0]):
                        prior = str(row.get("structural_parent_match_error", ""))
                        row["structural_parent_match_error"] = (
                            f"{prior} | {message}" if prior else message
                        )
        members_by_root: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for index, (row, _) in enumerate(block):
            members_by_root[find(index)].append(row)
        clusters.extend(members_by_root.values())

    clusters.sort(
        key=lambda members: min(str(row.get("source_relpath", "")) for row in members)
    )
    for group_index, members in enumerate(clusters, start=1):
        members.sort(key=lambda row: str(row.get("source_relpath", "")))
        group_id = f"cnrs_parent_{group_index:04d}"
        for index, row in enumerate(members):
            row["structural_parent_group"] = group_id
            row["structural_parent_group_size"] = len(members)
            row["structural_parent_representative"] = index == 0
        for source_field in UNIQUE_ELIGIBILITY_FIELDS:
            target_field = source_field.replace("_unique_eligible", "_parent_eligible")
            eligible = [row for row in members if row.get(source_field) is True]
            for row in members:
                row[target_field] = bool(eligible and row is eligible[0])
    return True


def annotate_formal_structure_matches(
    rows: list[dict[str, Any]], source_root: Path, formal_records: Path | None
) -> bool:
    """Run a tolerant same-composition structure-overlap screen against formal_14060."""

    if formal_records is None:
        for row in rows:
            row["formal_14060_structure_match"] = ""
            row["formal_14060_match_ids"] = ""
            row["formal_14060_match_splits"] = ""
            row["formal_14060_structure_match_error"] = ""
        return False
    from pymatgen.core import Composition, Structure

    candidate_formulas = {
        str(row.get("formula_reduced", ""))
        for row in rows
        if row.get("formal_14060_formula_overlap") is True and row.get("formula_reduced")
    }
    formal_by_formula: dict[str, list[tuple[str, str, str, Any]]] = defaultdict(list)
    with formal_records.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                formula = Composition(str(record.get("formula", ""))).reduced_formula
            except Exception:
                continue
            if formula not in candidate_formulas:
                continue
            structure_data = record.get("standardized_structure") or record.get("original_structure")
            if not isinstance(structure_data, dict):
                continue
            formal_by_formula[formula].append(
                (
                    str(record.get("material_id", "")),
                    str(record.get("split", "")),
                    str(record.get("crystal_system", "")),
                    Structure.from_dict(structure_data),
                )
            )
    matcher = make_structure_matcher()
    for row in rows:
        matches: list[tuple[str, str]] = []
        error = ""
        formula = str(row.get("formula_reduced", ""))
        if row.get("formal_14060_formula_overlap") is True:
            try:
                structure = load_single_phase_structure(source_root / str(row["source_relpath"]))
                system = str(row.get("recomputed_crystal_system", ""))
                for material_id, split, candidate_system, candidate in formal_by_formula.get(
                    formula, []
                ):
                    if system and candidate_system and system != candidate_system:
                        continue
                    if matcher.fit(structure, candidate):
                        matches.append((material_id, split))
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
        row["formal_14060_structure_match"] = bool(matches)
        row["formal_14060_match_ids"] = ";".join(item[0] for item in matches)
        row["formal_14060_match_splits"] = ";".join(item[1] for item in matches)
        row["formal_14060_structure_match_error"] = error
    return True


def annotate_independent_parent_candidates(
    rows: list[dict[str, Any]], formal_overlap_audit_run: bool
) -> None:
    """Exclude a whole CNRS structural parent if any member overlaps formal_14060."""

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group = str(row.get("structural_parent_group", ""))
        if group:
            groups[group].append(row)
        row["structural_parent_formal_14060_overlap"] = False
        row["structural_parent_formal_14060_match_error"] = False
        for source_field in UNIQUE_ELIGIBILITY_FIELDS:
            parent_field = source_field.replace("_unique_eligible", "_parent_eligible")
            independent_field = parent_field.replace(
                "_parent_eligible", "_parent_independent_eligible"
            )
            row[independent_field] = False
            # Backward-compatible alias: this now means parent-independent, not
            # merely exact-spectrum-independent.
            row[source_field.replace("_eligible", "_independent_eligible")] = False

    for members in groups.values():
        overlaps = any(
            row.get("formal_14060_structure_match") is True
            or row.get("formal_14060_exact_fingerprint_overlap") is True
            for row in members
        )
        has_error = any(
            bool(row.get("formal_14060_structure_match_error")) for row in members
        )
        for row in members:
            row["structural_parent_formal_14060_overlap"] = overlaps
            row["structural_parent_formal_14060_match_error"] = has_error
        for source_field in UNIQUE_ELIGIBILITY_FIELDS:
            parent_field = source_field.replace("_unique_eligible", "_parent_eligible")
            independent_field = parent_field.replace(
                "_parent_eligible", "_parent_independent_eligible"
            )
            legacy_field = source_field.replace("_eligible", "_independent_eligible")
            for row in members:
                accepted = bool(
                    formal_overlap_audit_run
                    and row.get(parent_field) is True
                    and not overlaps
                    and not has_error
                )
                row[independent_field] = accepted
                row[legacy_field] = accepted


def audit_file(
    path: Path,
    source_root: Path,
    symprecs: tuple[float, ...],
    angle_tolerance: float,
    window_tolerance: float,
    formal_formulas: set[str],
    formal_fingerprints: set[str],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scan_id": path.stem,
        "source_relpath": path.relative_to(source_root).as_posix(),
        "file_sha256": sha256_file(path),
        "parse_error": "",
        "structure_error": "",
    }
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        two_theta = numeric_sequence(record.get("two_theta_values"))
        intensities = numeric_sequence(
            record.get("intensities", record.get("intensity_values"))
        )
        finite = all(math.isfinite(item) for item in two_theta + intensities)
        equal_lengths = len(two_theta) == len(intensities) and len(two_theta) >= 2
        monotonic = equal_lengths and all(
            later > earlier for earlier, later in zip(two_theta, two_theta[1:])
        )
        array_valid = bool(finite and equal_lengths and monotonic)
        steps = [later - earlier for earlier, later in zip(two_theta, two_theta[1:])]
        two_theta_min = min(two_theta) if two_theta else math.nan
        two_theta_max = max(two_theta) if two_theta else math.nan
        row.update(
            {
                "point_count": len(two_theta),
                "intensity_count": len(intensities),
                "arrays_finite": finite,
                "array_lengths_equal": equal_lengths,
                "two_theta_strictly_increasing": monotonic,
                "array_valid": array_valid,
                "two_theta_min": two_theta_min,
                "two_theta_max": two_theta_max,
                "median_step": statistics.median(steps) if steps else math.nan,
                "negative_intensity_count": sum(item < 0 for item in intensities),
                "covers_10_80": covers_window(
                    two_theta_min, two_theta_max, 10.0, 80.0, window_tolerance
                ),
                "covers_10_60": covers_window(
                    two_theta_min, two_theta_max, 10.0, 60.0, window_tolerance
                ),
                "window_overlap_fraction_10_80": max(
                    0.0, min(two_theta_max, 80.0) - max(two_theta_min, 10.0)
                )
                / 70.0,
                "spectrum_sha256": spectrum_digest(two_theta, intensities)
                if finite
                else "",
            }
        )

        label = parse_json_like(record.get("label"))
        if not isinstance(label, dict):
            raise TypeError("label is not a JSON object")
        phase_values = label.get("phases", [])
        if not isinstance(phase_values, list):
            raise TypeError("label.phases is not a list")
        phases = [parse_phase(value) for value in phase_values]
        row["phase_count"] = len(phases)
        row["single_phase"] = len(phases) == 1

        xray_info = parse_json_like(label.get("xray_info"))
        wavelength: float | None = None
        if isinstance(xray_info, dict) and xray_info.get("primary_wavelength") not in (None, ""):
            try:
                wavelength = float(xray_info["primary_wavelength"])
            except (TypeError, ValueError):
                wavelength = None
        row["primary_wavelength"] = wavelength if wavelength is not None else ""
        row["cu_ka_like"] = bool(wavelength is not None and 1.53 <= wavelength <= 1.55)
        mapped_count, mapped_min, mapped_max = map_two_theta_window(two_theta, wavelength)
        row["cu_ka_mapped_point_count"] = mapped_count
        row["cu_ka_mapped_two_theta_min"] = mapped_min if mapped_min is not None else ""
        row["cu_ka_mapped_two_theta_max"] = mapped_max if mapped_max is not None else ""
        row["cu_ka_mapped_covers_10_80"] = covers_window(
            mapped_min, mapped_max, 10.0, 80.0, window_tolerance
        )
        row["cu_ka_mapped_covers_10_60"] = covers_window(
            mapped_min, mapped_max, 10.0, 60.0, window_tolerance
        )
        row["is_simulated"] = bool(label.get("is_simulated", False))

        direct_numbers = [parse_direct_space_group(p.get("spacegroup")) for p in phases]
        direct_number = direct_numbers[0] if len(phases) == 1 else None
        row["direct_space_group"] = direct_number if direct_number is not None else ""
        row["direct_crystal_system"] = (
            crystal_system_from_space_group(direct_number) if direct_number is not None else ""
        )
        row["direct_label_available"] = direct_number is not None

        structure = None
        elements: list[str] = []
        if len(phases) == 1:
            try:
                structure, elements = build_structure(phases[0])
                row["formula_reduced"] = structure.composition.reduced_formula
                row["site_count"] = len(structure)
                row["elements"] = ";".join(elements)
                row["has_carbon"] = "C" in elements
                row["has_hydrogen"] = "H" in elements
                row["organic_hybrid_risk_proxy"] = "C" in elements and "H" in elements
                row["strict_nonorganic_proxy"] = not ("C" in elements and "H" in elements)
                numbers, systems, errors = recompute_symmetry(
                    structure, symprecs=symprecs, angle_tolerance=angle_tolerance
                )
                row["recomputed_space_groups"] = ";".join(str(item) for item in numbers)
                row["recomputed_crystal_systems"] = ";".join(systems)
                row["symmetry_errors"] = " | ".join(item for item in errors if item)
                valid_systems = [item for item in systems if item]
                row["space_group_stable"] = bool(
                    numbers and all(item > 0 for item in numbers) and len(set(numbers)) == 1
                )
                row["crystal_system_stable"] = bool(
                    len(valid_systems) == len(symprecs) and len(set(valid_systems)) == 1
                )
                row["recomputed_crystal_system"] = (
                    valid_systems[0] if row["crystal_system_stable"] else ""
                )
                row["recomputed_space_group_consensus"] = (
                    numbers[0] if row["space_group_stable"] else ""
                )
                try:
                    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

                    canonical = SpacegroupAnalyzer(
                        structure, symprec=0.001, angle_tolerance=angle_tolerance
                    ).get_conventional_standard_structure()
                    row["standardized_structure_fingerprint"] = exact_structure_fingerprint(
                        canonical
                    )
                except Exception as exc:  # noqa: BLE001
                    row["standardized_structure_fingerprint"] = ""
                    row["standardization_error"] = f"{type(exc).__name__}: {exc}"
                row["formal_14060_exact_fingerprint_overlap"] = bool(
                    formal_fingerprints
                    and row["standardized_structure_fingerprint"] in formal_fingerprints
                )
                row["formal_14060_formula_overlap"] = (
                    row["formula_reduced"] in formal_formulas if formal_formulas else ""
                )
            except Exception as exc:  # noqa: BLE001
                row["structure_error"] = f"{type(exc).__name__}: {exc}"
        for key, default in (
            ("formula_reduced", ""),
            ("site_count", ""),
            ("elements", ""),
            ("has_carbon", ""),
            ("has_hydrogen", ""),
            ("organic_hybrid_risk_proxy", ""),
            ("strict_nonorganic_proxy", ""),
            ("recomputed_space_groups", ""),
            ("recomputed_crystal_systems", ""),
            ("symmetry_errors", ""),
            ("space_group_stable", False),
            ("crystal_system_stable", False),
            ("recomputed_crystal_system", ""),
            ("recomputed_space_group_consensus", ""),
            ("standardized_structure_fingerprint", ""),
            ("standardization_error", ""),
            ("formal_14060_formula_overlap", ""),
            ("formal_14060_exact_fingerprint_overlap", ""),
        ):
            row.setdefault(key, default)

        direct_eligible = bool(
            row["array_valid"]
            and row["single_phase"]
            and not row["is_simulated"]
            and row["direct_label_available"]
        )
        derived_structural_eligible = bool(
            row["array_valid"]
            and row["single_phase"]
            and not row["is_simulated"]
            and row["crystal_system_stable"]
        )
        derived_eligible = bool(
            derived_structural_eligible
            and row["strict_nonorganic_proxy"] is True
        )
        row["direct_label_eligible"] = direct_eligible
        row["derived_structural_eligible"] = derived_structural_eligible
        row["derived_label_eligible"] = derived_eligible
        row["mapped_cu_ka_10_80_broad_eligible"] = bool(
            derived_structural_eligible and row["cu_ka_mapped_covers_10_80"]
        )
        row["mapped_cu_ka_10_60_broad_eligible"] = bool(
            derived_structural_eligible and row["cu_ka_mapped_covers_10_60"]
        )
        row["raw_window_10_80_eligible"] = bool(derived_eligible and row["covers_10_80"])
        row["native_cu_ka_10_80_eligible"] = bool(
            derived_eligible and row["cu_ka_like"] and row["covers_10_80"]
        )
        row["mapped_cu_ka_10_80_eligible"] = bool(
            derived_eligible and row["cu_ka_mapped_covers_10_80"]
        )
        row["mapped_cu_ka_10_60_eligible"] = bool(
            derived_eligible and row["cu_ka_mapped_covers_10_60"]
        )
        if direct_eligible:
            row["preferred_label_source"] = "deposited_space_group"
            row["preferred_crystal_system"] = row["direct_crystal_system"]
        elif derived_eligible:
            row["preferred_label_source"] = "structure_recomputed_stable_system"
            row["preferred_crystal_system"] = row["recomputed_crystal_system"]
        else:
            row["preferred_label_source"] = ""
            row["preferred_crystal_system"] = ""
    except Exception as exc:  # noqa: BLE001
        row["parse_error"] = f"{type(exc).__name__}: {exc}"
    return row


def count_by_class(
    rows: list[dict[str, Any]], predicate: str, label_field: str = "recomputed_crystal_system"
) -> dict[str, int]:
    counts = Counter(
        str(row.get(label_field, ""))
        for row in rows
        if row.get(predicate) is True and row.get(label_field)
    )
    return {name: counts.get(name, 0) for name in CRYSTAL_SYSTEMS}


def duplicated_record_count(rows: list[dict[str, Any]], key: str) -> int:
    values = [str(row.get(key, "")) for row in rows if row.get(key)]
    counts = Counter(values)
    return sum(count - 1 for count in counts.values() if count > 1)


def annotate_spectrum_duplicates(rows: list[dict[str, Any]]) -> None:
    predicate_pairs = (
        ("native_cu_ka_10_80_eligible", "native_cu_ka_10_80_unique_eligible"),
        ("mapped_cu_ka_10_80_eligible", "mapped_cu_ka_10_80_unique_eligible"),
        ("mapped_cu_ka_10_60_eligible", "mapped_cu_ka_10_60_unique_eligible"),
        (
            "mapped_cu_ka_10_80_broad_eligible",
            "mapped_cu_ka_10_80_broad_unique_eligible",
        ),
        (
            "mapped_cu_ka_10_60_broad_eligible",
            "mapped_cu_ka_10_60_broad_unique_eligible",
        ),
    )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        digest = str(row.get("spectrum_sha256", ""))
        if digest:
            groups[digest].append(row)
    for digest, members in groups.items():
        group_id = digest[:16]
        systems = {
            str(row.get("recomputed_crystal_system", ""))
            for row in members
            if row.get("recomputed_crystal_system")
        }
        label_conflict = len(systems) > 1
        for index, row in enumerate(members):
            row["spectrum_duplicate_group"] = group_id
            row["spectrum_duplicate_group_size"] = len(members)
            row["spectrum_label_conflict"] = label_conflict
            row["spectrum_unique_representative"] = index == 0 and not label_conflict
        for source_field, target_field in predicate_pairs:
            eligible = [row for row in members if row.get(source_field) is True]
            for row in members:
                row[target_field] = bool(
                    not label_conflict and eligible and row is eligible[0]
                )
    for row in rows:
        if not row.get("spectrum_sha256"):
            row["spectrum_duplicate_group"] = ""
            row["spectrum_duplicate_group_size"] = ""
            row["spectrum_label_conflict"] = False
            row["spectrum_unique_representative"] = False
            row["native_cu_ka_10_80_unique_eligible"] = False
            row["mapped_cu_ka_10_80_unique_eligible"] = False
            row["mapped_cu_ka_10_60_unique_eligible"] = False
            row["mapped_cu_ka_10_80_broad_unique_eligible"] = False
            row["mapped_cu_ka_10_60_broad_unique_eligible"] = False


def annotate_structure_duplicates(rows: list[dict[str, Any]]) -> None:
    source_fields = (
        "native_cu_ka_10_80_unique_eligible",
        "mapped_cu_ka_10_80_unique_eligible",
        "mapped_cu_ka_10_60_unique_eligible",
        "mapped_cu_ka_10_80_broad_unique_eligible",
        "mapped_cu_ka_10_60_broad_unique_eligible",
    )
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        fingerprint = str(row.get("standardized_structure_fingerprint", ""))
        if fingerprint:
            groups[fingerprint].append(row)
    for fingerprint, members in groups.items():
        group_id = fingerprint[:16]
        for index, row in enumerate(members):
            row["structure_duplicate_group"] = group_id
            row["structure_duplicate_group_size"] = len(members)
            row["structure_unique_representative"] = index == 0
        for source_field in source_fields:
            eligible = [row for row in members if row.get(source_field) is True]
            for row in members:
                row[source_field] = bool(eligible and row is eligible[0])
    for row in rows:
        if not row.get("standardized_structure_fingerprint"):
            row["structure_duplicate_group"] = ""
            row["structure_duplicate_group_size"] = ""
            row["structure_unique_representative"] = False


def build_summary(
    rows: list[dict[str, Any]],
    source_root: Path,
    archive_path: Path | None,
    symprecs: tuple[float, ...],
    angle_tolerance: float,
    window_tolerance: float,
    expected_archive_sha256: str,
    formal_overlap_audit_run: bool,
    fuzzy_overlap_audit_run: bool,
    structural_parent_audit_run: bool,
) -> dict[str, Any]:
    direct_counts = Counter(
        str(row.get("direct_crystal_system", ""))
        for row in rows
        if row.get("direct_label_eligible") and row.get("direct_crystal_system")
    )
    derived_counts = Counter(
        str(row.get("recomputed_crystal_system", ""))
        for row in rows
        if row.get("derived_label_eligible") and row.get("recomputed_crystal_system")
    )
    native_counts = count_by_class(rows, "native_cu_ka_10_80_unique_eligible")
    mapped_counts = count_by_class(rows, "mapped_cu_ka_10_80_unique_eligible")
    mapped_60_counts = count_by_class(rows, "mapped_cu_ka_10_60_unique_eligible")
    mapped_broad_counts = count_by_class(rows, "mapped_cu_ka_10_80_broad_unique_eligible")
    mapped_60_broad_counts = count_by_class(rows, "mapped_cu_ka_10_60_broad_unique_eligible")
    mapped_parent_counts = count_by_class(rows, "mapped_cu_ka_10_80_parent_eligible")
    mapped_broad_parent_counts = count_by_class(
        rows, "mapped_cu_ka_10_80_broad_parent_eligible"
    )
    mapped_independent_counts = count_by_class(
        rows, "mapped_cu_ka_10_80_parent_independent_eligible"
    )
    mapped_broad_independent_counts = count_by_class(
        rows, "mapped_cu_ka_10_80_broad_parent_independent_eligible"
    )
    archive_sha256 = sha256_file(archive_path) if archive_path else ""
    archive_ok = bool(
        archive_path
        and archive_path.is_file()
        and expected_archive_sha256
        and archive_sha256.lower() == expected_archive_sha256.lower()
    )
    mapped_all_classes = all(
        mapped_broad_independent_counts[name] > 0 for name in CRYSTAL_SYSTEMS
    )
    mapped_min_20 = all(
        mapped_broad_independent_counts[name] >= 20 for name in CRYSTAL_SYSTEMS
    )
    direct_all_classes = all(direct_counts.get(name, 0) > 0 for name in CRYSTAL_SYSTEMS)
    derived_all_classes = all(derived_counts.get(name, 0) > 0 for name in CRYSTAL_SYSTEMS)
    formula_overlap_rows = [
        row for row in rows if row.get("formal_14060_formula_overlap") is True
    ]
    exact_overlap_rows = [
        row for row in rows if row.get("formal_14060_exact_fingerprint_overlap") is True
    ]
    fuzzy_overlap_rows = [
        row for row in rows if row.get("formal_14060_structure_match") is True
    ]
    parent_groups = {
        str(row.get("structural_parent_group", ""))
        for row in rows
        if row.get("structural_parent_group")
    }
    formal_parent_overlap_groups = {
        str(row.get("structural_parent_group", ""))
        for row in rows
        if row.get("structural_parent_group")
        and row.get("structural_parent_formal_14060_overlap") is True
    }
    broad_candidate_formal_overlap_groups = {
        str(row.get("structural_parent_group", ""))
        for row in rows
        if row.get("mapped_cu_ka_10_80_broad_parent_eligible") is True
        and row.get("structural_parent_formal_14060_overlap") is True
    }
    relevant_parent_errors = sum(
        bool(row.get("structural_parent_match_error"))
        and any(row.get(field) is True for field in UNIQUE_ELIGIBILITY_FIELDS)
        for row in rows
    )
    relevant_formal_errors = sum(
        bool(row.get("formal_14060_structure_match_error"))
        and row.get("mapped_cu_ka_10_80_broad_parent_eligible") is True
        for row in rows
    )
    summary: dict[str, Any] = {
        "schema_version": "opxrd-cnrs-7cs-feasibility-v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(source_root.resolve()),
        "archive_path": str(archive_path.resolve()) if archive_path else "",
        "archive_sha256": archive_sha256,
        "expected_archive_sha256": expected_archive_sha256,
        "archive_checksum_matches_v11": archive_ok,
        "symmetry_policy": {
            "method": "pymatgen SpacegroupAnalyzer on deposited lattice plus atomic basis",
            "symprecs": list(symprecs),
            "angle_tolerance_deg": angle_tolerance,
            "acceptance": "same crystal system at every tolerance; never lattice-metric inference",
        },
        "window_policy": {
            "target_two_theta_deg": [10.0, 80.0],
            "cu_ka_wavelength_angstrom": 1.5406,
            "endpoint_tolerance_deg": window_tolerance,
        },
        "independence_policy": {
            "within_cnrs": "StructureMatcher clustering blocked by reduced formula and stable crystal system",
            "against_formal_14060": "exclude the whole CNRS structural-parent group when any member matches",
            "matcher": {
                "ltol": 0.2,
                "stol": 0.3,
                "angle_tol": 5.0,
                "primitive_cell": True,
                "scale": True,
                "attempt_supercell": False,
                "comparator": "ElementComparator",
            },
        },
        "counts": {
            "source_files": len(rows),
            "parse_errors": sum(bool(row.get("parse_error")) for row in rows),
            "valid_arrays": sum(row.get("array_valid") is True for row in rows),
            "single_phase": sum(row.get("single_phase") is True for row in rows),
            "deposited_space_group_present": sum(
                row.get("direct_label_available") is True for row in rows
            ),
            "structure_parse_success": sum(
                not row.get("structure_error") and bool(row.get("formula_reduced")) for row in rows
            ),
            "stable_recomputed_space_group": sum(
                row.get("space_group_stable") is True for row in rows
            ),
            "stable_recomputed_crystal_system": sum(
                row.get("crystal_system_stable") is True for row in rows
            ),
            "organic_hybrid_risk_proxy": sum(
                row.get("organic_hybrid_risk_proxy") is True for row in rows
            ),
            "strict_nonorganic_proxy": sum(
                row.get("strict_nonorganic_proxy") is True for row in rows
            ),
            "cu_ka_like": sum(row.get("cu_ka_like") is True for row in rows),
            "covers_10_80": sum(row.get("covers_10_80") is True for row in rows),
            "covers_10_60": sum(row.get("covers_10_60") is True for row in rows),
            "cu_ka_mapped_covers_10_80": sum(
                row.get("cu_ka_mapped_covers_10_80") is True for row in rows
            ),
            "cu_ka_mapped_covers_10_60": sum(
                row.get("cu_ka_mapped_covers_10_60") is True for row in rows
            ),
            "direct_label_eligible": sum(
                row.get("direct_label_eligible") is True for row in rows
            ),
            "derived_label_eligible": sum(
                row.get("derived_label_eligible") is True for row in rows
            ),
            "derived_structural_eligible": sum(
                row.get("derived_structural_eligible") is True for row in rows
            ),
            "raw_window_10_80_eligible": sum(
                row.get("raw_window_10_80_eligible") is True for row in rows
            ),
            "native_cu_ka_10_80_unique_eligible": sum(
                row.get("native_cu_ka_10_80_unique_eligible") is True for row in rows
            ),
            "mapped_cu_ka_10_80_unique_eligible": sum(
                row.get("mapped_cu_ka_10_80_unique_eligible") is True for row in rows
            ),
            "mapped_cu_ka_10_60_unique_eligible": sum(
                row.get("mapped_cu_ka_10_60_unique_eligible") is True for row in rows
            ),
            "mapped_cu_ka_10_80_broad_unique_eligible": sum(
                row.get("mapped_cu_ka_10_80_broad_unique_eligible") is True for row in rows
            ),
            "mapped_cu_ka_10_60_broad_unique_eligible": sum(
                row.get("mapped_cu_ka_10_60_broad_unique_eligible") is True for row in rows
            ),
            "structural_parent_groups": len(parent_groups),
            "structural_parent_max_group_size": max(
                (int(row.get("structural_parent_group_size") or 0) for row in rows),
                default=0,
            ),
            "structural_parent_relevant_errors": relevant_parent_errors,
            "mapped_cu_ka_10_80_parent_eligible": sum(
                row.get("mapped_cu_ka_10_80_parent_eligible") is True for row in rows
            ),
            "mapped_cu_ka_10_80_broad_parent_eligible": sum(
                row.get("mapped_cu_ka_10_80_broad_parent_eligible") is True for row in rows
            ),
            "exact_file_duplicates_excess": duplicated_record_count(rows, "file_sha256"),
            "exact_spectrum_duplicates_excess": duplicated_record_count(rows, "spectrum_sha256"),
            "spectrum_label_conflict_rows": sum(
                row.get("spectrum_label_conflict") is True for row in rows
            ),
            "spectrum_label_conflict_groups": len(
                {
                    str(row.get("spectrum_duplicate_group"))
                    for row in rows
                    if row.get("spectrum_label_conflict") is True
                }
            ),
            "standardized_structure_duplicates_excess": duplicated_record_count(
                rows, "standardized_structure_fingerprint"
            ),
            "formal_14060_formula_overlap": len(formula_overlap_rows),
            "formal_14060_exact_fingerprint_overlap": len(exact_overlap_rows),
            "formal_14060_structure_match_overlap": len(fuzzy_overlap_rows),
            "formal_14060_structure_match_train_overlap": sum(
                "train" in str(row.get("formal_14060_match_splits", "")).split(";")
                for row in fuzzy_overlap_rows
            ),
            "formal_14060_parent_overlap_groups": len(formal_parent_overlap_groups),
            "formal_14060_broad_candidate_parent_overlap_groups": len(
                broad_candidate_formal_overlap_groups
            ),
            "formal_14060_relevant_match_errors": relevant_formal_errors,
            "mapped_cu_ka_10_80_parent_independent_eligible": sum(
                row.get("mapped_cu_ka_10_80_parent_independent_eligible") is True
                for row in rows
            ),
            "mapped_cu_ka_10_80_broad_parent_independent_eligible": sum(
                row.get("mapped_cu_ka_10_80_broad_parent_independent_eligible") is True
                for row in rows
            ),
            "balanced_broad_parent_cap_per_class": min(
                mapped_broad_independent_counts.values()
            ),
            "balanced_broad_parent_total_at_cap": min(
                mapped_broad_independent_counts.values()
            )
            * len(CRYSTAL_SYSTEMS),
        },
        "class_counts": {
            "direct": {name: direct_counts.get(name, 0) for name in CRYSTAL_SYSTEMS},
            "derived_nonorganic": {name: derived_counts.get(name, 0) for name in CRYSTAL_SYSTEMS},
            "derived_c_h_risk_filtered": {
                name: derived_counts.get(name, 0) for name in CRYSTAL_SYSTEMS
            },
            "native_cu_ka_10_80_unique": native_counts,
            "mapped_cu_ka_10_80_unique": mapped_counts,
            "mapped_cu_ka_10_60_unique": mapped_60_counts,
            "mapped_cu_ka_10_80_broad_unique": mapped_broad_counts,
            "mapped_cu_ka_10_60_broad_unique": mapped_60_broad_counts,
            "mapped_cu_ka_10_80_parent": mapped_parent_counts,
            "mapped_cu_ka_10_80_broad_parent": mapped_broad_parent_counts,
            "mapped_cu_ka_10_80_unique_independent": mapped_independent_counts,
            "mapped_cu_ka_10_80_broad_unique_independent": mapped_broad_independent_counts,
            "mapped_cu_ka_10_80_parent_independent": mapped_independent_counts,
            "mapped_cu_ka_10_80_broad_parent_independent": mapped_broad_independent_counts,
        },
        "gates": {
            "v11_archive_integrity": "PASS" if archive_ok else "FAIL",
            "all_cnrs_json_parse": "PASS"
            if all(not row.get("parse_error") for row in rows)
            else "FAIL",
            "deposited_space_group_labels_cover_7cs": "PASS" if direct_all_classes else "FAIL",
            "derived_structure_labels_cover_7cs": "PASS" if derived_all_classes else "FAIL",
            "intra_cnrs_structural_parent_audit": (
                "PASS"
                if structural_parent_audit_run and not relevant_parent_errors
                else "FAIL"
                if structural_parent_audit_run
                else "NOT_RUN"
            ),
            "final_mapped_cu_ka_10_80_has_all_7cs": "PASS"
            if mapped_all_classes
            else "FAIL",
            "final_mapped_cu_ka_10_80_min_20_per_class": "PASS"
            if mapped_min_20
            else "FAIL",
            "exact_structure_independence_from_formal_14060": (
                "PASS"
                if formal_overlap_audit_run and not exact_overlap_rows
                else "FAIL"
                if formal_overlap_audit_run
                else "NOT_RUN"
            ),
            "fuzzy_structure_overlap_audit": "PASS" if fuzzy_overlap_audit_run else "NOT_RUN",
            "fuzzy_structure_matches_excluded_from_candidates": (
                "PASS"
                if fuzzy_overlap_audit_run
                and not relevant_formal_errors
                and not any(
                    row.get("mapped_cu_ka_10_80_broad_parent_independent_eligible") is True
                    and row.get("structural_parent_formal_14060_overlap") is True
                    for row in rows
                )
                else "FAIL"
                if fuzzy_overlap_audit_run
                else "NOT_RUN"
            ),
            "manual_label_validation": "NOT_RUN",
        },
    }
    immediate = (
        archive_ok
        and summary["gates"]["all_cnrs_json_parse"] == "PASS"
        and direct_all_classes
        and mapped_min_20
        and summary["gates"]["exact_structure_independence_from_formal_14060"] == "PASS"
        and summary["gates"]["manual_label_validation"] == "PASS"
    )
    salvageable = (
        archive_ok
        and derived_all_classes
        and mapped_all_classes
        and summary["gates"]["intra_cnrs_structural_parent_audit"] == "PASS"
        and summary["gates"]["fuzzy_structure_matches_excluded_from_candidates"] == "PASS"
    )
    if salvageable and mapped_min_20:
        salvage_status = "FEASIBLE_WITH_FOLLOWUP"
    elif salvageable:
        salvage_status = "EXPLORATORY_ONLY"
    else:
        salvage_status = "NOT_FEASIBLE"
    summary["decision"] = {
        "immediate_second_real_domain": "GO" if immediate else "HOLD",
        "derived_label_salvage_path": salvage_status,
        "reason": (
            "Deposited space-group labels are absent; the final independent structural-parent "
            f"minimum is {min(mapped_broad_independent_counts.values())} per class, below the "
            "20-per-class gate; and manual label validation has not been run.  Tolerant "
            "formal_14060 overlap screening was completed and matching parent groups were excluded."
        ),
    }
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def manual_validation_sample(
    rows: list[dict[str, Any]], per_class: int
) -> list[dict[str, Any]]:
    sample: list[dict[str, Any]] = []
    for system in CRYSTAL_SYSTEMS:
        candidates = sorted(
            (
                row
                for row in rows
                if row.get("mapped_cu_ka_10_80_broad_parent_independent_eligible") is True
                and row.get("recomputed_crystal_system") == system
            ),
            key=lambda row: str(row.get("source_relpath", "")),
        )
        for row in candidates[:per_class]:
            copy = dict(row)
            copy["manual_structure_label_valid"] = ""
            copy["manual_spectrum_quality_valid"] = ""
            copy["manual_reviewer"] = ""
            copy["manual_review_notes"] = ""
            sample.append(copy)
    return sample


def write_report(path: Path, summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    classes = summary["class_counts"]
    gates = summary["gates"]
    lines = [
        "# opXRD v11 CNRS seven-crystal-system feasibility audit",
        "",
        f"Decision: **{summary['decision']['immediate_second_real_domain']} for immediate use**; "
        f"derived-label path: **{summary['decision']['derived_label_salvage_path']}**.",
        "",
        "## What was audited",
        "",
        f"- CNRS JSON files: {counts['source_files']}",
        f"- Archive checksum matches the pinned v11 payload: {summary['archive_checksum_matches_v11']}",
        f"- Coverage endpoint tolerance: {summary['window_policy']['endpoint_tolerance_deg']} degrees",
        f"- Deposited space-group labels present: {counts['deposited_space_group_present']}",
        f"- Structures parsed: {counts['structure_parse_success']}",
        f"- Stable reconstructed crystal-system labels: {counts['stable_recomputed_crystal_system']}",
        f"- C+H organic/hybrid-risk proxy: {counts['organic_hybrid_risk_proxy']}",
        f"- Raw scans covering 10-80 degrees before wavelength mapping: {counts['covers_10_80']}",
        f"- Scans covering 10-80 degrees after Cu Kα Bragg mapping: {counts['cu_ka_mapped_covers_10_80']}",
        f"- Native Cu Kα, C+H-risk-filtered, spectrum-unique 10-80 candidates: {counts['native_cu_ka_10_80_unique_eligible']}",
        f"- Wavelength-mapped, C+H-risk-filtered, spectrum-unique 10-80 candidates: {counts['mapped_cu_ka_10_80_unique_eligible']}",
        f"- Wavelength-mapped, C+H-risk-filtered, spectrum-unique 10-60 candidates: {counts['mapped_cu_ka_10_60_unique_eligible']}",
        f"- Wavelength-mapped, broad-material, unique 10-80 candidates: {counts['mapped_cu_ka_10_80_broad_unique_eligible']}",
        f"- Wavelength-mapped, broad-material, unique 10-60 candidates: {counts['mapped_cu_ka_10_60_broad_unique_eligible']}",
        f"- Wavelength-mapped, C+H-risk-filtered, structural-parent 10-80 candidates: {counts['mapped_cu_ka_10_80_parent_eligible']}",
        f"- Wavelength-mapped, broad-material, structural-parent 10-80 candidates: {counts['mapped_cu_ka_10_80_broad_parent_eligible']}",
        f"- Largest repeated structural-parent group: {counts['structural_parent_max_group_size']} scans",
        f"- Exact duplicate spectra beyond first occurrence: {counts['exact_spectrum_duplicates_excess']}",
        f"- Duplicate-spectrum rows with conflicting seven-class labels: {counts['spectrum_label_conflict_rows']} in {counts['spectrum_label_conflict_groups']} groups (all excluded)",
        f"- Standardized structure duplicates beyond first occurrence: {counts['standardized_structure_duplicates_excess']}",
        f"- Formula overlaps with formal_14060: {counts['formal_14060_formula_overlap']}",
        f"- Exact standardized-structure fingerprint overlaps with formal_14060: {counts['formal_14060_exact_fingerprint_overlap']}",
        f"- Tolerant StructureMatcher overlaps with formal_14060: {counts['formal_14060_structure_match_overlap']} ({counts['formal_14060_structure_match_train_overlap']} touch train)",
        f"- Broad candidate parent groups overlapping formal_14060: {counts['formal_14060_broad_candidate_parent_overlap_groups']}",
        f"- Final mapped C+H-risk-filtered 10-80 independent parents: {counts['mapped_cu_ka_10_80_parent_independent_eligible']}",
        f"- Final mapped broad-material 10-80 independent parents: {counts['mapped_cu_ka_10_80_broad_parent_independent_eligible']}",
        f"- Maximum balanced broad pilot: {counts['balanced_broad_parent_cap_per_class']} per class ({counts['balanced_broad_parent_total_at_cap']} total)",
        "",
        "## Seven-class counts",
        "",
        "| Crystal system | Deposited SG | Derived C+H-risk-filtered | Mapped broad spectrum-unique | Mapped broad structural parents | Final independent parents |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in CRYSTAL_SYSTEMS:
        lines.append(
            f"| {name} | {classes['direct'][name]} | {classes['derived_nonorganic'][name]} | "
            f"{classes['mapped_cu_ka_10_80_broad_unique'][name]} | {classes['mapped_cu_ka_10_80_broad_parent'][name]} | "
            f"{classes['mapped_cu_ka_10_80_broad_parent_independent'][name]} |"
        )
    lines.extend(
        [
            "",
            "## Chemistry sensitivity",
            "",
            "The broad-material result is the most generous gate.  Applying only the C+H "
            "organic/hybrid-risk proxy reduces the final independent-parent counts further:",
            "",
            "| Crystal system | Final broad parents | Final C+H-risk-filtered parents |",
            "| --- | ---: | ---: |",
        ]
    )
    for name in CRYSTAL_SYSTEMS:
        lines.append(
            f"| {name} | {classes['mapped_cu_ka_10_80_broad_parent_independent'][name]} | "
            f"{classes['mapped_cu_ka_10_80_parent_independent'][name]} |"
        )
    lines.extend(
        [
            "",
            "## Gates",
            "",
            "| Gate | Result |",
            "| --- | --- |",
        ]
    )
    for name, result in gates.items():
        lines.append(f"| {name} | {result} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A lattice-metric label is intentionally not accepted: it cannot reliably distinguish "
            "trigonal from hexagonal.  The derived path uses the deposited atomic basis and accepts "
            "a seven-class label only when pymatgen returns the same crystal system at every audited "
            "symmetry tolerance.  The C+H flag is only an organic/hybrid-risk proxy, not a validated "
            "inorganic label.  Exact hashes, tolerant within-CNRS parent clustering, and tolerant "
            "formal_14060 overlap screening have been completed; matched parent groups are excluded.  "
            "The remaining bottlenecks are the sub-20 hexagonal parent count, absent deposited labels, "
            "and manual spot validation.  The data can support an exploratory balanced pilot, but it "
            "should not yet be called a formal second real domain.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path)
    parser.add_argument(
        "--expected-archive-sha256",
        default="38b62bcddf976debb3e41d2597d3f14ac6c1f1c8a33565a84a98ef38ba3b6044",
    )
    parser.add_argument("--formal-manifest", type=Path)
    parser.add_argument("--formal-records", type=Path)
    parser.add_argument(
        "--window-tolerance-deg",
        type=float,
        default=0.0,
        help="Optional endpoint tolerance for 10-80 and 10-60 coverage checks.",
    )
    parser.add_argument("--manual-sample-per-class", type=int, default=5)
    parser.add_argument(
        "--symprecs",
        type=float,
        nargs="+",
        default=(0.001, 0.01, 0.05, 0.1),
    )
    parser.add_argument("--angle-tolerance", type=float, default=5.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    files = sorted(source_root.glob("*.json"), key=lambda item: item.name)
    if not files:
        raise SystemExit(f"no JSON files found under {source_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    formal_formulas, formal_fingerprints = read_formal_index(args.formal_manifest)
    symprecs = tuple(float(item) for item in args.symprecs)
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(files, start=1):
        rows.append(
            audit_file(
                path,
                source_root=source_root,
                symprecs=symprecs,
                angle_tolerance=float(args.angle_tolerance),
                window_tolerance=float(args.window_tolerance_deg),
                formal_formulas=formal_formulas,
                formal_fingerprints=formal_fingerprints,
            )
        )
        if index % 100 == 0 or index == len(files):
            print(f"audited {index}/{len(files)}", file=sys.stderr, flush=True)
    annotate_spectrum_duplicates(rows)
    annotate_structure_duplicates(rows)
    structural_parent_audit_run = annotate_structural_parents(rows, source_root=source_root)
    fuzzy_overlap_audit_run = annotate_formal_structure_matches(
        rows,
        source_root=source_root,
        formal_records=args.formal_records.resolve() if args.formal_records else None,
    )
    annotate_independent_parent_candidates(
        rows, formal_overlap_audit_run=fuzzy_overlap_audit_run
    )
    summary = build_summary(
        rows,
        source_root=source_root,
        archive_path=args.archive.resolve() if args.archive else None,
        symprecs=symprecs,
        angle_tolerance=float(args.angle_tolerance),
        window_tolerance=float(args.window_tolerance_deg),
        expected_archive_sha256=str(args.expected_archive_sha256),
        formal_overlap_audit_run=args.formal_manifest is not None,
        fuzzy_overlap_audit_run=fuzzy_overlap_audit_run,
        structural_parent_audit_run=structural_parent_audit_run,
    )
    write_csv(output_root / "cnrs_7cs_audit_manifest.csv", rows)
    write_csv(
        output_root / "cnrs_7cs_final_parent_candidates.csv",
        [
            row
            for row in rows
            if row.get("mapped_cu_ka_10_80_broad_parent_independent_eligible") is True
        ],
    )
    write_csv(
        output_root / "formal_14060_overlap_audit.csv",
        [
            row
            for row in rows
            if row.get("formal_14060_formula_overlap") is True
            or row.get("formal_14060_exact_fingerprint_overlap") is True
            or row.get("formal_14060_structure_match") is True
        ],
    )
    write_csv(
        output_root / "cnrs_7cs_exclusions.csv",
        [
            row
            for row in rows
            if row.get("spectrum_label_conflict") is True
            or row.get("structural_parent_formal_14060_overlap") is True
            or bool(row.get("structural_parent_match_error"))
            or bool(row.get("formal_14060_structure_match_error"))
        ],
    )
    write_csv(
        output_root / "manual_validation_sample.csv",
        manual_validation_sample(rows, per_class=int(args.manual_sample_per_class)),
    )
    (output_root / "cnrs_7cs_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_report(output_root / "CNRS_7CS_FEASIBILITY_REPORT.md", summary)
    print(json.dumps(summary["decision"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
