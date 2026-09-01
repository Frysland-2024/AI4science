"""Week-1 P0-P2 gates for tetragonal PXRD quantitative inversion.

The module is intentionally training-free. It reads the frozen parent structures,
authoritative split, and reflection cache from ``xrd_robustness`` and writes an
auditable pilot report under ``xrd_inversion``.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version as package_version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Iterable, Mapping, Sequence

import numpy as np
from pymatgen.core import Composition, Lattice, Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from scipy import __version__ as scipy_version
from scipy.optimize import least_squares

from xrd_robustness.peak_cache import load_peak_table, validate_peak_cache_manifest
from xrd_robustness.physics import PhysicsParameters
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.simulator import (
    SimulationGrid,
    ideal_peak_table,
    render_gaussian_peaks,
    simulate_from_peak_table,
)

if TYPE_CHECKING:
    from .gpu_forward import CachedTetragonalGPUForward


PARAMETER_NAMES = ("du", "dv", "delta", "fwhm")
STAIRCASES = {"S1": (0, 1), "S2": (0, 1, 2), "S3": (0, 1, 2, 3)}


@dataclass(frozen=True)
class ParentContext:
    material_id: str
    formula: str
    split: str
    space_group: int
    fingerprint: str
    structure: Structure
    peak_count: int
    cache_path: Path
    cache_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_seed(*values: object) -> int:
    payload = ":".join(str(value) for value in values).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def git_head(repository_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_status(repository_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=normal"],
            cwd=repository_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def installed_version(distribution: str) -> str | None:
    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def resolve_source_paths(
    repository_root: Path, config: Mapping[str, Any]
) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, value in config["source_contract"].items():
        if name == "data_root":
            paths[name] = (repository_root / str(value)).resolve()
        else:
            path = (repository_root / str(value)).resolve()
            if not path.is_relative_to(repository_root.resolve()):
                raise ValueError(f"source path escapes repository: {path}")
            paths[name] = path
    return paths


def resolve_output_path(
    repository_root: Path,
    config: Mapping[str, Any],
    name: str,
    fallback: str,
) -> Path:
    """Resolve a configured artifact path without permitting repository escape."""

    configured = config.get("outputs", {})
    value = configured.get(name, fallback) if isinstance(configured, Mapping) else fallback
    path = (repository_root / str(value)).resolve()
    if not path.is_relative_to(repository_root):
        raise ValueError(f"output path escapes repository: {path}")
    return path


def load_authoritative_split(
    path: Path,
) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, Any]]:
    manifest = load_json(path)
    rows = manifest.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("authoritative split manifest has no records")
    split_by_id: dict[str, str] = {}
    fingerprint_by_id: dict[str, str] = {}
    crystal_system_by_id: dict[str, str] = {}
    owner_by_fingerprint: dict[str, str] = {}
    for row in rows:
        material_id = str(row["material_id"])
        if material_id in split_by_id:
            raise ValueError(f"duplicate split material_id: {material_id}")
        split = str(row["split"])
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split {split!r} for {material_id}")
        fingerprint = str(row["parent_structure_id"])
        if fingerprint in owner_by_fingerprint:
            raise ValueError(
                "authoritative split assigns one parent fingerprint more than once: "
                f"{owner_by_fingerprint[fingerprint]} and {material_id}"
            )
        owner_by_fingerprint[fingerprint] = material_id
        split_by_id[material_id] = split
        fingerprint_by_id[material_id] = fingerprint
        crystal_system_by_id[material_id] = str(row["crystal_system"])
    return split_by_id, fingerprint_by_id, crystal_system_by_id, manifest


def load_tetragonal_records(
    records_path: Path,
    split_by_id: Mapping[str, str],
    fingerprint_by_id: Mapping[str, str],
    crystal_system_by_id: Mapping[str, str],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with records_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("crystal_system")) != "tetragonal":
                continue
            material_id = str(row["material_id"])
            if material_id not in split_by_id:
                raise ValueError(f"record missing from authoritative split: {material_id}")
            if crystal_system_by_id[material_id] != "tetragonal":
                raise ValueError(
                    "crystal-system mismatch between records and authoritative split: "
                    f"{material_id}"
                )
            fingerprint = str(row["structure_fingerprint"])
            if fingerprint != fingerprint_by_id[material_id]:
                raise ValueError(
                    f"fingerprint mismatch between records and split at line {line_number}: "
                    f"{material_id}"
                )
            item = dict(row)
            item["authoritative_split"] = split_by_id[material_id]
            records.append(item)
    records.sort(key=lambda row: str(row["material_id"]))
    return records


def load_csv_index(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [dict(row) for row in csv.DictReader(handle)]
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        value = str(row[key])
        if value in indexed:
            raise ValueError(f"duplicate {key} in {path}: {value}")
        indexed[value] = row
    return indexed


def is_conventional_tetragonal_lattice(
    lattice: Lattice,
    canonical_config: Mapping[str, Any],
) -> bool:
    a, b, _ = lattice.abc
    alpha, beta, gamma = lattice.angles
    relative_ab = abs(a - b) / max(a, b)
    angle_error = max(abs(alpha - 90.0), abs(beta - 90.0), abs(gamma - 90.0))
    return (
        relative_ab <= float(canonical_config["relative_a_b_tolerance"])
        and angle_error <= float(canonical_config["angle_tolerance_deg"])
    )


def canonicalize_tetragonal_record(
    record: Mapping[str, Any],
    canonical_config: Mapping[str, Any],
) -> tuple[Structure, bool]:
    stored = Structure.from_dict(record["standardized_structure"])
    if is_conventional_tetragonal_lattice(stored.lattice, canonical_config):
        return stored, False
    original = Structure.from_dict(record["original_structure"])
    analyzer = SpacegroupAnalyzer(
        original,
        symprec=float(canonical_config["symprec"]),
        angle_tolerance=float(canonical_config["angle_tolerance_for_restandardization_deg"]),
    )
    conventional = analyzer.get_conventional_standard_structure()
    space_group = int(analyzer.get_space_group_number())
    if not 75 <= space_group <= 142:
        raise ValueError(
            f"restandardization changed {record['material_id']} to non-tetragonal SG {space_group}"
        )
    if not is_conventional_tetragonal_lattice(conventional.lattice, canonical_config):
        raise ValueError(f"could not obtain conventional tetragonal cell: {record['material_id']}")
    return conventional, True


def offsets_to_lattice(a0: float, c0: float, du: float, dv: float) -> tuple[float, float]:
    """Apply offsets in cell-volume and tetragonal-distortion coordinates."""
    u0 = (2.0 * math.log(a0) + math.log(c0)) / 3.0
    v0 = math.log(c0 / a0)
    u = u0 + float(du)
    v = v0 + float(dv)
    return math.exp(u - v / 3.0), math.exp(u + 2.0 * v / 3.0)


def parameter_vector_to_physical(
    q: Sequence[float],
    structure: Structure,
    parameter_config: Mapping[str, Any],
) -> dict[str, float]:
    vector = np.asarray(q, dtype=np.float64)
    if vector.shape != (4,) or not np.isfinite(vector).all():
        raise ValueError("q must be a finite four-vector")
    if str(parameter_config.get("fwhm_transform")) != "log":
        raise ValueError("the Week-1 pilot requires fwhm_transform='log'")
    du = float(vector[0]) * float(parameter_config["du_half_range"])
    dv = float(vector[1]) * float(parameter_config["dv_half_range"])
    a, c = offsets_to_lattice(structure.lattice.a, structure.lattice.c, du, dv)
    delta = float(vector[2]) * float(parameter_config["delta_half_range_deg"])
    fwhm_min = float(parameter_config["fwhm_min_deg"])
    fwhm_max = float(parameter_config["fwhm_max_deg"])
    if not 0.0 < fwhm_min < fwhm_max:
        raise ValueError("FWHM bounds must satisfy 0 < min < max")
    log_center = 0.5 * (math.log(fwhm_min) + math.log(fwhm_max))
    log_half_range = 0.5 * (math.log(fwhm_max) - math.log(fwhm_min))
    fwhm = math.exp(log_center + float(vector[3]) * log_half_range)
    if fwhm <= 0:
        raise ValueError("parameter vector produced non-positive FWHM")
    return {
        "du": du,
        "dv": dv,
        "a": a,
        "c": c,
        "delta_2theta_deg": delta,
        "fwhm_deg": fwhm,
    }


def structure_with_tetragonal_lattice(structure: Structure, a: float, c: float) -> Structure:
    return Structure(
        Lattice.tetragonal(float(a), float(c)),
        structure.species,
        structure.frac_coords,
        coords_are_cartesian=False,
        site_properties=structure.site_properties,
        properties=structure.properties,
    )


def percentile_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        return {"count": 0, "min": None, "median": None, "p90": None, "max": None}
    return {
        "count": int(array.size),
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "p90": float(np.percentile(array, 90)),
        "max": float(np.max(array)),
    }


def audit_tetragonal_pool(
    records: Sequence[Mapping[str, Any]],
    peak_manifest: Mapping[str, Mapping[str, str]],
    canonical_config: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    split_counts = {name: 0 for name in ("train", "validation", "test")}
    space_groups: dict[str, int] = {}
    selection_tiers: dict[str, int] = {}
    fingerprints: set[str] = set()
    duplicate_fingerprints: list[str] = []
    nonconventional: list[dict[str, Any]] = []
    canonicalization_failures: list[dict[str, str]] = []
    features: list[dict[str, Any]] = []
    a_values: list[float] = []
    c_values: list[float] = []
    ratios: list[float] = []
    nsites_values: list[float] = []
    peak_counts: list[float] = []
    proxy_groups: dict[tuple[str, int, int], list[tuple[str, str]]] = {}

    for record in records:
        material_id = str(record["material_id"])
        split = str(record["authoritative_split"])
        split_counts[split] += 1
        space_group = str(record["space_group_recomputed"])
        space_groups[space_group] = space_groups.get(space_group, 0) + 1
        tier = str(record.get("selection_tier", "unspecified"))
        selection_tiers[tier] = selection_tiers.get(tier, 0) + 1
        fingerprint = str(record["structure_fingerprint"])
        if fingerprint in fingerprints:
            duplicate_fingerprints.append(fingerprint)
        fingerprints.add(fingerprint)
        if material_id not in peak_manifest:
            raise ValueError(f"tetragonal parent missing peak-cache manifest row: {material_id}")
        stored_lattice = Lattice.from_dict(record["standardized_structure"]["lattice"])
        restandardized = False
        if not is_conventional_tetragonal_lattice(stored_lattice, canonical_config):
            try:
                structure, restandardized = canonicalize_tetragonal_record(
                    record, canonical_config
                )
                nonconventional.append(
                    {
                        "material_id": material_id,
                        "stored_abc": [float(value) for value in stored_lattice.abc],
                        "stored_angles": [float(value) for value in stored_lattice.angles],
                        "restandardized_abc": [float(value) for value in structure.lattice.abc],
                        "restandardized_angles": [
                            float(value) for value in structure.lattice.angles
                        ],
                        "status": "restandardized",
                    }
                )
            except Exception as error:  # report all bad parents before failing the gate
                canonicalization_failures.append(
                    {"material_id": material_id, "error": f"{type(error).__name__}: {error}"}
                )
                continue
        else:
            structure = None
        peak_count = int(peak_manifest[material_id]["peak_count"])
        lattice = structure.lattice if structure is not None else stored_lattice
        a = float(lattice.a)
        c = float(lattice.c)
        ratio = c / a
        a_values.append(a)
        c_values.append(c)
        ratios.append(ratio)
        nsites_values.append(float(record["nsites"]))
        peak_counts.append(float(peak_count))
        proxy_key = (
            Composition(str(record["formula"])).anonymized_formula,
            int(record["space_group_recomputed"]),
            int(record["nsites"]),
        )
        proxy_groups.setdefault(proxy_key, []).append((material_id, split))
        features.append(
            {
                "material_id": material_id,
                "formula": str(record["formula"]),
                "split": split,
                "space_group": int(record["space_group_recomputed"]),
                "fingerprint": fingerprint,
                "a": a,
                "c": c,
                "c_over_a": ratio,
                "nsites": int(record["nsites"]),
                "peak_count": peak_count,
                "restandardized": restandardized,
                "record": record,
            }
        )

    repeated_proxy_groups = {
        key: members for key, members in proxy_groups.items() if len(members) > 1
    }
    cross_split_proxy_groups = {
        key: members
        for key, members in repeated_proxy_groups.items()
        if len({split for _, split in members}) > 1
    }
    cross_split_proxy_parent_ids = sorted(
        {material_id for members in cross_split_proxy_groups.values() for material_id, _ in members}
    )
    report = {
        "total_tetragonal_parents": len(records),
        "authoritative_split_counts": split_counts,
        "space_group_counts": dict(sorted(space_groups.items(), key=lambda item: int(item[0]))),
        "selection_tier_counts": dict(sorted(selection_tiers.items())),
        "duplicate_fingerprint_count": len(duplicate_fingerprints),
        "duplicate_fingerprints": sorted(set(duplicate_fingerprints)),
        "stored_nonconventional_count": len(nonconventional),
        "stored_nonconventional": nonconventional,
        "canonicalization_failure_count": len(canonicalization_failures),
        "canonicalization_failures": canonicalization_failures,
        "a_angstrom": percentile_summary(a_values),
        "c_angstrom": percentile_summary(c_values),
        "c_over_a": percentile_summary(ratios),
        "nsites": percentile_summary(nsites_values),
        "peak_count": percentile_summary(peak_counts),
        "prototype_audit_status": "space_group_proxy_only_no_prototype_labels_in_source",
        "composition_spacegroup_nsites_proxy": {
            "definition": "anonymized_formula + space_group + nsites; high-recall flag, not proof of near duplication",
            "repeated_group_count": len(repeated_proxy_groups),
            "cross_split_group_count": len(cross_split_proxy_groups),
            "cross_split_parent_count": len(cross_split_proxy_parent_ids),
            "cross_split_parent_ids_sha256": hashlib.sha256(
                "\n".join(cross_split_proxy_parent_ids).encode("utf-8")
            ).hexdigest(),
        },
    }
    return report, features


def select_representative_parents(
    features: Sequence[Mapping[str, Any]],
    *,
    count: int,
    split: str,
) -> list[dict[str, Any]]:
    candidates = [
        dict(row)
        for row in features
        if str(row["split"]) == split and not bool(row["restandardized"])
    ]
    candidates.sort(key=lambda row: str(row["material_id"]))
    if len(candidates) < count:
        raise ValueError(f"only {len(candidates)} eligible {split} parents for count={count}")
    matrix = np.asarray(
        [
            [
                math.log(float(row["a"])),
                math.log(float(row["c_over_a"])),
                math.log1p(float(row["nsites"])),
                math.log1p(float(row["peak_count"])),
            ]
            for row in candidates
        ],
        dtype=np.float64,
    )
    center = np.median(matrix, axis=0)
    q25, q75 = np.percentile(matrix, [25, 75], axis=0)
    scale = q75 - q25
    scale[scale <= 1e-12] = 1.0
    normalized = (matrix - center) / scale
    first = min(
        range(len(candidates)),
        key=lambda index: (float(np.linalg.norm(normalized[index])), candidates[index]["material_id"]),
    )
    selected = [first]
    while len(selected) < count:
        selected_set = set(selected)
        used_space_groups = {int(candidates[index]["space_group"]) for index in selected}
        best_index = None
        best_score = -math.inf
        for index, row in enumerate(candidates):
            if index in selected_set:
                continue
            distances = [
                float(np.linalg.norm(normalized[index] - normalized[chosen]))
                for chosen in selected
            ]
            novelty_bonus = 0.25 if int(row["space_group"]) not in used_space_groups else 0.0
            score = min(distances) + novelty_bonus
            if best_index is None or score > best_score + 1e-12 or (
                abs(score - best_score) <= 1e-12
                and str(row["material_id"]) < str(candidates[best_index]["material_id"])
            ):
                best_index = index
                best_score = score
        assert best_index is not None
        selected.append(best_index)
    output: list[dict[str, Any]] = []
    for rank, index in enumerate(selected, start=1):
        row = dict(candidates[index])
        row["selection_rank"] = rank
        row["selection_feature_vector"] = normalized[index].tolist()
        output.append(row)
    return output


def build_parent_context(
    selected: Mapping[str, Any],
    peak_manifest: Mapping[str, Mapping[str, str]],
    paths: Mapping[str, Path],
    canonical_config: Mapping[str, Any],
) -> ParentContext:
    record = selected["record"]
    structure, _ = canonicalize_tetragonal_record(record, canonical_config)
    material_id = str(record["material_id"])
    manifest_row = peak_manifest[material_id]
    cache_path = paths["peak_cache_dir"] / f"{material_id}.npz"
    if str(manifest_row["structure_fingerprint"]) != str(record["structure_fingerprint"]):
        raise ValueError(f"selected cache fingerprint mismatch: {material_id}")
    declared = Path(str(manifest_row["file"]))
    if declared.name != cache_path.name:
        raise ValueError(f"selected cache path mismatch: {material_id}")
    return ParentContext(
        material_id=material_id,
        formula=str(record["formula"]),
        split=str(record["authoritative_split"]),
        space_group=int(record["space_group_recomputed"]),
        fingerprint=str(record["structure_fingerprint"]),
        structure=structure,
        peak_count=int(manifest_row["peak_count"]),
        cache_path=cache_path,
        cache_sha256=str(manifest_row["sha256"]),
    )


def analytic_tetragonal_d(a: float, c: float, hkls: np.ndarray) -> np.ndarray:
    values = np.asarray(hkls, dtype=np.float64)
    h, k, ell = values.T
    inverse_d_squared = (h * h + k * k) / (a * a) + (ell * ell) / (c * c)
    if np.any(inverse_d_squared <= 0):
        raise ValueError("encountered zero-index reflection")
    return 1.0 / np.sqrt(inverse_d_squared)


def bragg_two_theta(d: np.ndarray, wavelength: float) -> np.ndarray:
    argument = float(wavelength) / (2.0 * np.asarray(d, dtype=np.float64))
    if np.any(argument <= 0) or np.any(argument >= 1):
        raise ValueError("reflection lies outside Bragg domain")
    return np.degrees(2.0 * np.arcsin(argument))


def bragg_errors_for_table(
    table: PeakTable,
    *,
    a: float,
    c: float,
    wavelength: float,
) -> tuple[np.ndarray, np.ndarray]:
    if table.hkls is None or table.reflection_peak_indices is None:
        raise ValueError("P0 requires reflection-aware cache tables")
    d_metric = analytic_tetragonal_d(a, c, table.hkls)
    if table.reciprocal_vectors is None:
        raise ValueError("P0 requires reciprocal vectors")
    d_reciprocal = 1.0 / np.linalg.norm(table.reciprocal_vectors, axis=1)
    predicted = bragg_two_theta(d_metric, wavelength)
    observed = table.positions[table.reflection_peak_indices]
    return np.abs(d_metric - d_reciprocal), np.abs(predicted - observed)


def fit_gaussian_profile(axis: np.ndarray, profile: np.ndarray) -> tuple[float, float]:
    values = np.asarray(profile, dtype=np.float64)
    maximum = float(np.max(values))
    mask = values > maximum * math.exp(-10.0)
    if np.count_nonzero(mask) < 5:
        raise ValueError("too few points for Gaussian profile fit")
    coefficients = np.polyfit(axis[mask], np.log(values[mask]), deg=2)
    quadratic, linear, _ = coefficients
    if quadratic >= 0:
        raise ValueError("profile fit is not a concave Gaussian")
    center = -linear / (2.0 * quadratic)
    sigma = math.sqrt(-1.0 / (2.0 * quadratic))
    fwhm = sigma * 2.0 * math.sqrt(2.0 * math.log(2.0))
    return float(center), float(fwhm)


def run_p0(
    records: Sequence[Mapping[str, Any]],
    contexts: Sequence[ParentContext],
    peak_manifest: Mapping[str, Mapping[str, str]],
    cache_validation: Mapping[str, Any],
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    canonical_config = config["canonical_cell"]
    p0_config = config["p0"]
    wavelength = float(config["grid"]["wavelength_angstrom"])
    grid = SimulationGrid(
        two_theta_min=float(config["grid"]["two_theta_min"]),
        two_theta_max=float(config["grid"]["two_theta_max"]),
        step=float(config["grid"]["step"]),
        wavelength=str(config["grid"]["wavelength_name"]),
    )
    metric_max = 0.0
    metric_tolerance_ratio_max = 0.0
    bragg_max = 0.0
    family_count = 0
    merged_family_count = 0
    conventional_count = 0
    nonconventional_ids: list[str] = []
    restandardized_ids: list[str] = []
    restandardization_failures: list[dict[str, str]] = []

    for record in records:
        material_id = str(record["material_id"])
        stored_lattice = Lattice.from_dict(record["standardized_structure"]["lattice"])
        if not is_conventional_tetragonal_lattice(stored_lattice, canonical_config):
            nonconventional_ids.append(material_id)
            try:
                canonicalize_tetragonal_record(record, canonical_config)
                restandardized_ids.append(material_id)
            except Exception as error:
                restandardization_failures.append(
                    {"material_id": material_id, "error": f"{type(error).__name__}: {error}"}
                )
            continue
        conventional_count += 1
        table = load_peak_table(paths["peak_cache_dir"] / f"{material_id}.npz")
        metric_errors, bragg_errors = bragg_errors_for_table(
            table,
            a=float(stored_lattice.a),
            c=float(stored_lattice.c),
            wavelength=wavelength,
        )
        assert table.reciprocal_vectors is not None
        reciprocal_d = 1.0 / np.linalg.norm(table.reciprocal_vectors, axis=1)
        metric_tolerances = float(p0_config["metric_d_atol_angstrom"]) + float(
            p0_config["metric_d_rtol"]
        ) * np.abs(reciprocal_d)
        metric_tolerance_ratio_max = max(
            metric_tolerance_ratio_max,
            float(np.max(metric_errors / metric_tolerances, initial=0.0)),
        )
        family_count += int(len(metric_errors))
        merged_family_count += int(np.count_nonzero(bragg_errors > 1e-8))
        metric_max = max(metric_max, float(np.max(metric_errors, initial=0.0)))
        bragg_max = max(bragg_max, float(np.max(bragg_errors, initial=0.0)))

    selected_rows: list[dict[str, Any]] = []
    measured_shifts: list[float] = []
    fwhm_errors: list[float] = []
    center_drifts: list[float] = []
    area_relative_errors: list[float] = []
    dynamic_bragg_max = 0.0
    dynamic_family_count = 0
    fresh_cache_position_max = 0.0
    fresh_cache_intensity_relative_max = 0.0
    metadata_mismatch_count = 0
    cache_hash_mismatch_count = 0
    fraction_step = float(p0_config["lattice_fraction_step"])
    axis = grid.values

    for context in contexts:
        cache = load_peak_table(context.cache_path)
        fresh = ideal_peak_table(context.structure, grid)
        if fresh.positions.shape != cache.positions.shape:
            raise ValueError(f"fresh/cache peak-count mismatch: {context.material_id}")
        fresh_cache_position_max = max(
            fresh_cache_position_max,
            float(np.max(np.abs(fresh.positions - cache.positions), initial=0.0)),
        )
        denominator = np.maximum(np.abs(cache.intensities), 1e-12)
        fresh_cache_intensity_relative_max = max(
            fresh_cache_intensity_relative_max,
            float(
                np.max(
                    np.abs(fresh.intensities - cache.intensities) / denominator,
                    initial=0.0,
                )
            ),
        )
        for attribute in (
            "hkls",
            "multiplicities",
            "reciprocal_vectors",
            "reflection_peak_indices",
        ):
            if not np.array_equal(getattr(fresh, attribute), getattr(cache, attribute)):
                metadata_mismatch_count += 1
        if sha256_file(context.cache_path).lower() != context.cache_sha256.lower():
            cache_hash_mismatch_count += 1

        a0, c0 = context.structure.lattice.a, context.structure.lattice.c
        for label, a, c in (
            ("a_plus", a0 * (1.0 + fraction_step), c0),
            ("c_plus", a0, c0 * (1.0 + fraction_step)),
        ):
            deformed = structure_with_tetragonal_lattice(context.structure, a, c)
            table = ideal_peak_table(deformed, grid)
            _, bragg_errors = bragg_errors_for_table(
                table, a=a, c=c, wavelength=wavelength
            )
            dynamic_bragg_max = max(
                dynamic_bragg_max, float(np.max(bragg_errors, initial=0.0))
            )
            dynamic_family_count += int(len(bragg_errors))
            selected_rows.append(
                {
                    "material_id": context.material_id,
                    "deformation": label,
                    "reflection_family_count": int(len(bragg_errors)),
                    "max_bragg_error_deg": float(np.max(bragg_errors, initial=0.0)),
                }
            )

        candidate_indices = np.flatnonzero(
            (cache.positions > grid.two_theta_min + 2.0)
            & (cache.positions < grid.two_theta_max - 2.0)
        )
        ranked = candidate_indices[
            np.argsort(cache.intensities[candidate_indices], kind="mergesort")[::-1]
        ][:3]
        for peak_index in ranked:
            center = float(cache.positions[peak_index])
            intensity = float(cache.intensities[peak_index])
            base = render_gaussian_peaks(
                [center], [intensity], axis, 0.08, normalize=False
            )
            shifted = render_gaussian_peaks(
                [center + float(p0_config["zero_shift_probe_deg"])],
                [intensity],
                axis,
                0.08,
                normalize=False,
            )
            fitted_base, _ = fit_gaussian_profile(axis, base)
            fitted_shifted, _ = fit_gaussian_profile(axis, shifted)
            measured_shifts.append(fitted_shifted - fitted_base)

        strongest = int(ranked[0])
        center = float(cache.positions[strongest])
        intensity = float(cache.intensities[strongest])
        fits: list[tuple[float, float, float]] = []
        for fwhm in p0_config["fwhm_probe_deg"]:
            profile = render_gaussian_peaks(
                [center], [intensity], axis, float(fwhm), normalize=False
            )
            fitted_center, fitted_fwhm = fit_gaussian_profile(axis, profile)
            area = float(np.trapezoid(profile.astype(np.float64), axis))
            fits.append((fitted_center, fitted_fwhm, area))
            fwhm_errors.append(abs(fitted_fwhm - float(fwhm)))
        center_drifts.append(abs(fits[1][0] - fits[0][0]))
        area_relative_errors.append(abs(fits[1][2] / fits[0][2] - 1.0))

    expected_shift = float(p0_config["zero_shift_probe_deg"])
    shift_errors = [abs(value - expected_shift) for value in measured_shifts]
    shift_dispersion = float(np.std(measured_shifts, ddof=1)) if len(measured_shifts) > 1 else 0.0
    quarantined_split_counts = {name: 0 for name in ("train", "validation", "test")}
    split_by_material = {
        str(record["material_id"]): str(record["authoritative_split"]) for record in records
    }
    for material_id in nonconventional_ids:
        quarantined_split_counts[split_by_material[material_id]] += 1
    checks = {
        "full_cache_identity_and_hashes_match": int(
            cache_validation["verified_file_hashes"]
        )
        == len(records),
        "nonconventional_cells_excluded_from_dynamic_use": not any(
            context.material_id in set(nonconventional_ids) for context in contexts
        ),
        "metric_formula_matches_reciprocal_vectors": metric_tolerance_ratio_max <= 1.0,
        "bragg_formula_matches_cached_positions": bragg_max
        <= float(p0_config["bragg_two_theta_atol_deg"]),
        "deformed_bragg_formula_matches_fresh_renderer": dynamic_bragg_max
        <= float(p0_config["bragg_two_theta_atol_deg"]),
        "fresh_cache_positions_match": fresh_cache_position_max
        <= float(p0_config["fresh_cache_position_atol_deg"]),
        "fresh_cache_intensities_match": fresh_cache_intensity_relative_max
        <= float(p0_config["fresh_cache_intensity_rtol"]),
        "fresh_cache_metadata_match": metadata_mismatch_count == 0,
        "selected_cache_hashes_match": cache_hash_mismatch_count == 0,
        "zero_shift_matches_probe": max(shift_errors, default=0.0)
        <= float(p0_config["center_error_max_deg"]),
        "zero_shift_is_global": shift_dispersion
        <= float(p0_config["center_shift_dispersion_max_deg"]),
        "fwhm_matches_requested_width": max(fwhm_errors, default=0.0)
        <= float(p0_config["fwhm_error_max_deg"]),
        "fwhm_does_not_move_center": max(center_drifts, default=0.0)
        <= float(p0_config["center_error_max_deg"]),
        "fwhm_preserves_integrated_area": max(area_relative_errors, default=0.0)
        <= float(p0_config["area_relative_error_max"]),
    }
    passed = all(checks.values())
    status = (
        "PASS_WITH_QUARANTINE"
        if passed and nonconventional_ids
        else "PASS"
        if passed
        else "FAIL"
    )
    return {
        "status": status,
        "checks": checks,
        "conventional_cached_parent_count": conventional_count,
        "nonconventional_parent_count": len(nonconventional_ids),
        "nonconventional_parent_ids": nonconventional_ids,
        "quarantined_parent_ids": nonconventional_ids,
        "quarantined_split_counts": quarantined_split_counts,
        "quarantine_policy": (
            "exclude until conventional-cell structures receive matching regenerated "
            "fingerprints and reflection caches"
        ),
        "restandardized_parent_ids": restandardized_ids,
        "restandardization_failures": restandardization_failures,
        "cached_reflection_family_count": family_count,
        "merged_near_degenerate_family_count": merged_family_count,
        "max_metric_d_error_angstrom": metric_max,
        "max_metric_tolerance_ratio": metric_tolerance_ratio_max,
        "max_cached_bragg_error_deg": bragg_max,
        "dynamic_deformation_family_count": dynamic_family_count,
        "max_dynamic_bragg_error_deg": dynamic_bragg_max,
        "max_fresh_cache_position_error_deg": fresh_cache_position_max,
        "max_fresh_cache_intensity_relative_error": fresh_cache_intensity_relative_max,
        "fresh_cache_metadata_mismatch_count": metadata_mismatch_count,
        "selected_cache_hash_mismatch_count": cache_hash_mismatch_count,
        "zero_shift_probe_deg": expected_shift,
        "zero_shift_error_deg": percentile_summary(shift_errors),
        "zero_shift_measured_dispersion_deg": shift_dispersion,
        "fwhm_error_deg": percentile_summary(fwhm_errors),
        "fwhm_center_drift_deg": percentile_summary(center_drifts),
        "fwhm_area_relative_error": percentile_summary(area_relative_errors),
        "selected_deformation_checks": selected_rows,
    }


def profile_transform(values: np.ndarray) -> np.ndarray:
    return np.log1p(100.0 * np.asarray(values, dtype=np.float64)) / math.log(101.0)


def sample_range(specification: Any, rng: np.random.Generator) -> float:
    if isinstance(specification, Mapping):
        probability = float(specification.get("apply_probability", 1.0))
        if rng.random() >= probability:
            return 0.0
        low = float(specification["min_value"])
        high = float(specification["max_value"])
        distribution = str(specification["distribution"])
        if distribution == "fixed":
            return low
        if distribution == "log_uniform":
            return float(np.exp(rng.uniform(math.log(low), math.log(high))))
        if distribution == "uniform":
            return float(rng.uniform(low, high))
        raise ValueError(f"unsupported range distribution: {distribution}")
    return float(specification)


def sample_nuisance(
    measurement_config: Mapping[str, Any], rng: np.random.Generator
) -> dict[str, float | int | str]:
    profile = measurement_config["profiles"]["train"]
    return {
        "background_to_peak_ratio": sample_range(
            profile["background_to_peak_ratio"], rng
        ),
        "background_type": str(profile["background_type"]),
        "background_order": int(profile["background_order"]),
        "background_variation": sample_range(profile["background_variation"], rng),
        "background_floor_fraction": float(profile["background_floor_fraction"]),
        "poisson_count_scale": sample_range(profile["poisson_count_scale"], rng),
        "electronic_noise_std_counts": sample_range(
            profile["electronic_noise_std_counts"], rng
        ),
        "noise_model": str(profile["noise_model"]),
        "noise_stage": str(profile["noise_stage"]),
    }


def peak_calculation_grid(config: Mapping[str, Any]) -> SimulationGrid:
    """Use a padded peak window before rendering/cropping to the observed grid."""
    padding = float(config["grid"].get("peak_calculation_padding_deg", 0.0))
    return SimulationGrid(
        two_theta_min=float(config["grid"]["two_theta_min"]) - padding,
        two_theta_max=float(config["grid"]["two_theta_max"]) + padding,
        step=float(config["grid"]["step"]),
        wavelength=str(config["grid"]["wavelength_name"]),
    )


def render_profile(
    context: ParentContext,
    q: Sequence[float],
    *,
    config: Mapping[str, Any],
    grid: SimulationGrid,
    rng_seed: int,
    nuisance: Mapping[str, Any] | None = None,
) -> np.ndarray:
    physical = parameter_vector_to_physical(q, context.structure, config["parameterization"])
    structure = structure_with_tetragonal_lattice(
        context.structure, physical["a"], physical["c"]
    )
    table = ideal_peak_table(structure, peak_calculation_grid(config))
    nuisance = nuisance or {}
    background_ratio = float(nuisance.get("background_to_peak_ratio", 0.0))
    noise_active = bool(nuisance)
    params = PhysicsParameters(
        delta_2theta_deg=physical["delta_2theta_deg"],
        fwhm_deg=physical["fwhm_deg"],
        background_to_peak_ratio=background_ratio,
        noise_std_ratio=0.0,
        background_type=str(nuisance.get("background_type", "flat")),
        severity_level=1 if nuisance else 0,
        background_active=background_ratio > 0.0,
        noise_active=noise_active,
        background_order=int(nuisance.get("background_order", 0)),
        background_variation=float(nuisance.get("background_variation", 0.0)),
        background_floor_fraction=float(nuisance.get("background_floor_fraction", 0.0)),
        noise_model=str(nuisance.get("noise_model", "additive_gaussian")),
        noise_stage=str(nuisance.get("noise_stage", "before_normalization")),
        poisson_count_scale=float(nuisance.get("poisson_count_scale", 40000.0)),
        electronic_noise_std_counts=float(
            nuisance.get("electronic_noise_std_counts", 0.0)
        ),
        preferred_orientation_active=False,
    )
    return simulate_from_peak_table(
        table.positions,
        table.intensities,
        params,
        rng_seed=int(rng_seed),
        grid=grid,
        normalize=True,
        reflection_table=table,
    )


def build_gpu_forward_models(
    contexts: Sequence[ParentContext], config: Mapping[str, Any]
) -> dict[str, "CachedTetragonalGPUForward"]:
    from .gpu_forward import CachedTetragonalGPUForward

    runtime = config.get("runtime", {})
    device = str(runtime.get("device", "cuda"))
    dtype = str(runtime.get("dtype", "float64"))
    if dtype != "float64":
        raise ValueError("Week-1 numerical gates require runtime.dtype='float64'")
    return {
        context.material_id: CachedTetragonalGPUForward(
            context.structure,
            grid_config=config["grid"],
            parameter_config=config["parameterization"],
            device=device,
        )
        for context in contexts
    }


def run_gpu_forward_parity(
    contexts: Sequence[ParentContext],
    models: Mapping[str, "CachedTetragonalGPUForward"],
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    parity_config = config.get("gpu_forward", {}).get("parity", {})
    maximum_allowed = float(parity_config.get("profile_max_abs_max", 5e-6))
    rmse_allowed = float(parity_config.get("profile_rmse_max", 1e-7))
    configured_probes = parity_config.get("q_probes")
    if not isinstance(configured_probes, list) or not configured_probes:
        configured_probes = [anchor["q"] for anchor in config["p1"]["anchors"]]
    grid = SimulationGrid(
        two_theta_min=float(config["grid"]["two_theta_min"]),
        two_theta_max=float(config["grid"]["two_theta_max"]),
        step=float(config["grid"]["step"]),
        wavelength=str(config["grid"]["wavelength_name"]),
    )
    rows: list[dict[str, Any]] = []
    maximum_error = 0.0
    maximum_rmse = 0.0
    for context in contexts:
        model = models[context.material_id]
        for probe_index, probe in enumerate(configured_probes):
            q = np.asarray(probe, dtype=np.float64)
            gpu = model.render_numpy(q)
            cpu = render_profile(
                context,
                q,
                config=config,
                grid=grid,
                rng_seed=stable_seed(config["seed"], "gpu-parity", context.material_id),
            ).astype(np.float64)
            difference = gpu - cpu
            max_abs = float(np.max(np.abs(difference), initial=0.0))
            rmse = float(np.sqrt(np.mean(difference * difference)))
            maximum_error = max(maximum_error, max_abs)
            maximum_rmse = max(maximum_rmse, rmse)
            rows.append(
                {
                    "material_id": context.material_id,
                    "probe_index": probe_index,
                    "q": q.tolist(),
                    "profile_max_abs": max_abs,
                    "profile_rmse": rmse,
                    "passed": max_abs <= maximum_allowed and rmse <= rmse_allowed,
                }
            )
    passed = bool(rows) and all(bool(row["passed"]) for row in rows)
    first_model = models[contexts[0].material_id] if contexts else None
    return {
        "status": "PASS" if passed else "INVALID",
        "contract": (
            first_model.provenance().contract if first_model is not None else None
        ),
        "profile_max_abs_max": maximum_error,
        "profile_rmse_max": maximum_rmse,
        "thresholds": {
            "profile_max_abs_max": maximum_allowed,
            "profile_rmse_max": rmse_allowed,
        },
        "probe_count": len(rows),
        "models": {
            material_id: asdict(model.provenance())
            for material_id, model in models.items()
        },
        "probes": rows,
    }


def _second_order_finite_difference(
    model: "CachedTetragonalGPUForward",
    q0: np.ndarray,
    parameter_index: int,
    step: float,
    *,
    q_low: float,
    q_high: float,
    normalization_index: int | None = None,
) -> tuple[np.ndarray, str]:
    if step <= 0.0:
        raise ValueError("finite-difference step must be positive")

    def evaluate(offset: float) -> np.ndarray:
        q = q0.copy()
        q[parameter_index] += offset
        return model.transformed_numpy(
            q, normalization_index=normalization_index
        )

    tolerance = 1e-12
    if q0[parameter_index] - step >= q_low - tolerance and q0[
        parameter_index
    ] + step <= q_high + tolerance:
        return (evaluate(step) - evaluate(-step)) / (2.0 * step), "central_2point"
    base = evaluate(0.0)
    if q0[parameter_index] + 2.0 * step <= q_high + tolerance:
        return (
            -3.0 * base + 4.0 * evaluate(step) - evaluate(2.0 * step)
        ) / (2.0 * step), "forward_3point"
    if q0[parameter_index] - 2.0 * step >= q_low - tolerance:
        return (
            3.0 * base - 4.0 * evaluate(-step) + evaluate(-2.0 * step)
        ) / (2.0 * step), "backward_3point"
    raise ValueError("finite-difference stencil has insufficient room inside q bounds")


def jacobian_for_parent(
    model: "CachedTetragonalGPUForward",
    *,
    config: Mapping[str, Any],
    anchor_q: Sequence[float] | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    p1_config = config["p1"]
    q_low, q_high = [
        float(value) for value in config["parameterization"]["q_bounds"]
    ]
    q0 = np.asarray(
        np.zeros(4, dtype=np.float64) if anchor_q is None else anchor_q,
        dtype=np.float64,
    )
    if q0.shape != (4,):
        raise ValueError("P1 anchor must be a four-vector")
    if np.any(q0 < q_low) or np.any(q0 > q_high):
        raise ValueError("P1 anchor lies outside q_bounds")
    h_values = [
        float(value)
        for value in p1_config.get(
            "finite_difference_h_q_values", [0.005, 0.01, 0.02, 0.04]
        )
    ]
    if h_values != sorted(set(h_values)) or len(h_values) < 2:
        raise ValueError("P1 finite-difference h values must be unique and increasing")
    normalization_index = model.smooth_normalization_index(q0)
    autograd = model.transformed_jacobian_numpy(
        q0, normalization_index=normalization_index
    )
    threshold = float(
        p1_config.get(
            "finite_difference_autograd_relative_max",
            p1_config["finite_difference_convergence_relative_max"],
        )
    )
    required_pairs = int(
        p1_config.get("finite_difference_required_adjacent_pair_count", 1)
    )
    audits: list[dict[str, Any]] = []
    for parameter_index, name in enumerate(PARAMETER_NAMES):
        reference = autograd[:, parameter_index]
        reference_norm = max(float(np.linalg.norm(reference)), 1e-12)
        sweep: list[dict[str, Any]] = []
        passing_steps: list[bool] = []
        for step in h_values:
            derivative, stencil = _second_order_finite_difference(
                model,
                q0,
                parameter_index,
                step,
                q_low=q_low,
                q_high=q_high,
                normalization_index=normalization_index,
            )
            derivative_norm = float(np.linalg.norm(derivative))
            relative = float(np.linalg.norm(derivative - reference)) / reference_norm
            cosine = float(
                np.dot(derivative, reference)
                / max(derivative_norm * reference_norm, 1e-15)
            )
            passed = relative <= threshold
            passing_steps.append(passed)
            sweep.append(
                {
                    "h_q": step,
                    "stencil": stencil,
                    "finite_difference_column_norm": derivative_norm,
                    "autograd_relative_error": relative,
                    "autograd_cosine": cosine,
                    "passed": passed,
                }
            )
        passing_pairs = [
            [h_values[index], h_values[index + 1]]
            for index in range(len(h_values) - 1)
            if passing_steps[index] and passing_steps[index + 1]
        ]
        audits.append(
            {
                "parameter": name,
                "normalization_branch_index": normalization_index,
                "autograd_column_norm": float(np.linalg.norm(reference)),
                "sweep": sweep,
                "passing_adjacent_pairs": passing_pairs,
                "required_adjacent_pair_count": required_pairs,
                "numerical_stability_passed": len(passing_pairs) >= required_pairs,
            }
        )
    return autograd, audits


def matrix_identifiability(
    jacobian: np.ndarray,
    active_indices: Sequence[int],
    *,
    rank_rcond: float,
) -> dict[str, Any]:
    matrix = np.asarray(jacobian[:, active_indices], dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=0)
    nonzero = bool(np.all(norms > 1e-12))
    normalized = matrix / np.maximum(norms, 1e-15)
    cosine = normalized.T @ normalized
    off_diagonal = np.abs(cosine - np.eye(len(active_indices)))
    max_cosine = float(np.max(off_diagonal, initial=0.0))
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    if singular_values.size:
        rank = int(np.count_nonzero(singular_values > singular_values[0] * rank_rcond))
        condition = (
            float(singular_values[0] / singular_values[-1])
            if singular_values[-1] > 0
            else math.inf
        )
    else:
        rank = 0
        condition = math.inf
    return {
        "active_parameters": [PARAMETER_NAMES[index] for index in active_indices],
        "column_norms": {PARAMETER_NAMES[index]: float(norms[offset]) for offset, index in enumerate(active_indices)},
        "minimum_column_norm": float(np.min(norms, initial=math.inf)),
        "cosine_matrix": cosine.tolist(),
        "max_abs_pairwise_cosine": max_cosine,
        "singular_values": singular_values.tolist(),
        "rank": rank,
        "full_rank": rank == len(active_indices),
        "condition_number": condition,
        "all_columns_nonzero": nonzero,
    }


def run_p1(
    contexts: Sequence[ParentContext],
    models: Mapping[str, "CachedTetragonalGPUForward"],
    forward_parity: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    p1_config = config["p1"]
    parents: list[dict[str, Any]] = []
    eligible_ids: list[str] = []
    numerical_failure_ids: set[str] = set()
    identifiability_failure_ids: set[str] = set()
    configured_anchors = p1_config.get("anchors")
    if not isinstance(configured_anchors, list) or not configured_anchors:
        configured_anchors = [{"name": "center", "q": [0.0, 0.0, 0.0, 0.0]}]
    for context in contexts:
        if context.material_id not in models:
            raise ValueError(f"missing GPU forward for {context.material_id}")
        model = models[context.material_id]
        anchor_rows: list[dict[str, Any]] = []
        for anchor in configured_anchors:
            anchor_name = str(anchor["name"])
            anchor_q = [float(value) for value in anchor["q"]]
            jacobian, numerical_audit = jacobian_for_parent(
                model,
                config=config,
                anchor_q=anchor_q,
            )
            staircases: dict[str, Any] = {}
            for name, indices in STAIRCASES.items():
                metrics = matrix_identifiability(
                    jacobian,
                    indices,
                    rank_rcond=float(p1_config["rank_rcond"]),
                )
                numerical_passed = all(
                    bool(numerical_audit[index]["numerical_stability_passed"])
                    for index in indices
                )
                identifiability_passed = bool(
                    metrics["minimum_column_norm"]
                    >= float(p1_config["column_norm_min"])
                    and metrics["full_rank"]
                    and metrics["condition_number"]
                    <= float(p1_config["condition_number_max"])
                    and metrics["max_abs_pairwise_cosine"]
                    <= float(p1_config["max_abs_cosine"])
                )
                metrics["numerical_stability_passed"] = numerical_passed
                metrics["identifiability_passed"] = identifiability_passed
                metrics["eligible"] = numerical_passed and identifiability_passed
                staircases[name] = metrics
            anchor_rows.append(
                {
                    "name": anchor_name,
                    "q": anchor_q,
                    "jacobian_source": "torch.func.jacfwd",
                    "finite_difference_role": "numerical audit only; not the gate Jacobian",
                    "finite_difference_sweep": numerical_audit,
                    "staircases": staircases,
                }
            )
        parent_numerical = all(
            staircase["numerical_stability_passed"]
            for anchor in anchor_rows
            for staircase in anchor["staircases"].values()
        )
        parent_identifiable = all(
            staircase["identifiability_passed"]
            for anchor in anchor_rows
            for staircase in anchor["staircases"].values()
        )
        parent_eligible = parent_numerical and parent_identifiable
        if parent_eligible:
            eligible_ids.append(context.material_id)
        if not parent_numerical:
            numerical_failure_ids.add(context.material_id)
        if not parent_identifiable:
            identifiability_failure_ids.add(context.material_id)
        parents.append(
            {
                "material_id": context.material_id,
                "formula": context.formula,
                "space_group": context.space_group,
                "numerical_stability_at_all_anchors": parent_numerical,
                "identifiable_at_all_anchors": parent_identifiable,
                "eligible_at_all_anchors": parent_eligible,
                "anchors": anchor_rows,
            }
        )
    fraction = len(eligible_ids) / len(contexts) if contexts else 0.0
    formal = str(config.get("run_kind", "smoke")) == "formal_gate"
    minimum = int(config["formal_gate_minimums"]["representative_parent_count"])
    sample_valid = not formal or len(contexts) == minimum
    global_valid = (
        str(forward_parity.get("status")) == "PASS"
        and sample_valid
        and len(models) == len(contexts)
    )
    passed = global_valid and fraction >= float(p1_config["eligible_parent_fraction_min"])
    return {
        "status": "PASS" if passed else "FAIL" if global_valid else "INVALID",
        "representative_parent_count": len(contexts),
        "eligible_parent_count": len(eligible_ids),
        "eligible_parent_fraction": fraction,
        "eligible_parent_ids": eligible_ids,
        "numerical_stability_failure_count": len(numerical_failure_ids),
        "numerical_stability_failure_ids": sorted(numerical_failure_ids),
        "identifiability_failure_count": len(identifiability_failure_ids),
        "identifiability_failure_ids": sorted(identifiability_failure_ids),
        "anchor_count": len(configured_anchors),
        "anchors": configured_anchors,
        "jacobian_backend": "torch.func.jacfwd",
        "matrix_metrics_source": "raw range-normalized autograd J_q",
        "finite_difference_gate_rule": (
            "for every active column, at least the configured number of adjacent "
            "h pairs must both agree with autograd within the unchanged threshold"
        ),
        "forward_parity_status": forward_parity.get("status"),
        "formal_sample_valid": sample_valid,
        "thresholds": dict(p1_config),
        "parents": parents,
    }


def optimize_case(
    model: "CachedTetragonalGPUForward",
    start_q: np.ndarray,
    active_indices: Sequence[int],
    observed: np.ndarray,
    *,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, Any, dict[str, Any]]:
    baseline = np.asarray(
        config["parameterization"]["nominal_q"], dtype=np.float64
    )
    if baseline.shape != (4,):
        raise ValueError("nominal_q must be a four-vector")
    start = np.asarray(start_q, dtype=np.float64)
    if start.shape != (4,):
        raise ValueError("optimizer start_q must be a four-vector")
    x0 = start[list(active_indices)]
    target = profile_transform(observed)
    q_low, q_high = [float(value) for value in config["parameterization"]["q_bounds"]]
    cached_active: np.ndarray | None = None
    cached_residual: np.ndarray | None = None
    cached_jacobian: np.ndarray | None = None

    def evaluate(active: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nonlocal cached_active, cached_residual, cached_jacobian
        active_array = np.asarray(active, dtype=np.float64)
        if cached_active is not None and np.array_equal(active_array, cached_active):
            assert cached_residual is not None and cached_jacobian is not None
            return cached_residual, cached_jacobian
        q = baseline.copy()
        q[list(active_indices)] = active_array
        predicted, full_jacobian = model.transformed_and_jacobian_numpy(q)
        cached_active = active_array.copy()
        cached_residual = predicted - target
        cached_jacobian = full_jacobian[:, list(active_indices)]
        return cached_residual, cached_jacobian

    def residual(active: np.ndarray) -> np.ndarray:
        return evaluate(active)[0]

    def autograd_jacobian(active: np.ndarray) -> np.ndarray:
        return evaluate(active)[1]

    initial_residual = residual(x0)
    initial_cost = 0.5 * float(np.dot(initial_residual, initial_residual))
    optimizer_config = config["p2"].get("local_optimizer", config["p2"])
    result = least_squares(
        residual,
        x0,
        jac=autograd_jacobian,
        bounds=(
            np.full(len(active_indices), q_low),
            np.full(len(active_indices), q_high),
        ),
        method="trf",
        loss="linear",
        x_scale=1.0,
        max_nfev=int(optimizer_config["max_nfev"]),
        ftol=float(optimizer_config.get("ftol", 1e-8)),
        xtol=float(optimizer_config.get("xtol", 1e-8)),
        gtol=float(optimizer_config.get("gtol", 1e-8)),
    )
    recovered = baseline.copy()
    recovered[list(active_indices)] = result.x
    diagnostics = {
        "start_q": start.tolist(),
        "initial_cost": initial_cost,
        "initial_profile_rmse": math.sqrt(
            2.0 * initial_cost / max(int(observed.size), 1)
        )
    }
    return recovered, result, diagnostics


def deterministic_sobol_candidates(
    active_indices: Sequence[int],
    *,
    config: Mapping[str, Any],
) -> np.ndarray:
    import torch

    baseline = np.asarray(config["parameterization"]["nominal_q"], dtype=np.float64)
    recovery = config["p2"]["recoverability"]
    q_low, q_high = [
        float(value)
        for value in recovery.get(
            "candidate_q_range", config["parameterization"]["q_bounds"]
        )
    ]
    domain_low, domain_high = [
        float(value) for value in config["parameterization"]["q_bounds"]
    ]
    if not (domain_low <= q_low < q_high <= domain_high):
        raise ValueError("P2-R candidate_q_range must lie inside q_bounds")
    stage = next(
        (name for name, indices in STAIRCASES.items() if tuple(active_indices) == indices),
        None,
    )
    if stage is None:
        raise ValueError("P2-R active indices do not match a frozen staircase")
    stage_counts = recovery.get("stage_candidate_counts")
    candidate_count = int(
        stage_counts[stage]
        if isinstance(stage_counts, Mapping)
        else recovery["sobol_candidate_count"]
    )
    if candidate_count < 1:
        raise ValueError("P2-R sobol_candidate_count must be positive")
    maximum_count = int(
        max(int(value) for value in stage_counts.values())
        if isinstance(stage_counts, Mapping)
        else candidate_count
    )
    sobol_seed = int(recovery["sobol_seed"])
    engine = torch.quasirandom.SobolEngine(
        dimension=4,
        scramble=True,
        seed=sobol_seed,
    )
    frozen_design = (
        engine.draw(maximum_count).to(dtype=torch.float64).cpu().numpy()
    )
    active = q_low + (q_high - q_low) * frozen_design[
        :candidate_count, : len(active_indices)
    ]
    candidates = np.repeat(baseline[None, :], candidate_count, axis=0)
    candidates[:, list(active_indices)] = active
    return candidates


def render_candidate_bank(
    model: "CachedTetragonalGPUForward",
    candidates: np.ndarray,
    *,
    batch_size: int,
) -> np.ndarray:
    import torch

    if batch_size < 1:
        raise ValueError("P2-R score_batch_size must be positive")
    profile_chunks: list[np.ndarray] = []
    with torch.no_grad(), torch.autocast(device_type="cuda", enabled=False):
        for start in range(0, len(candidates), batch_size):
            stop = min(start + batch_size, len(candidates))
            q = torch.as_tensor(
                candidates[start:stop], device=model.device, dtype=model.dtype
            )
            profile_chunks.append(model.transformed(q).cpu().numpy())
    profiles = np.concatenate(profile_chunks, axis=0)
    expected = (len(candidates), len(model.axis))
    if profiles.shape != expected or not np.isfinite(profiles).all():
        raise RuntimeError("P2-R candidate rendering produced invalid profiles")
    return profiles


def rank_multistart_candidates(
    candidates: np.ndarray,
    candidate_profiles: np.ndarray,
    observed: np.ndarray,
    *,
    top_k: int,
    score_batch_size: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, float]]:
    if top_k < 1 or top_k > len(candidates):
        raise ValueError("P2-R top_k is outside the candidate set")
    if candidate_profiles.shape[0] != len(candidates):
        raise ValueError("candidate profile bank is misaligned")
    target = profile_transform(observed)
    cost_values = np.empty(len(candidates), dtype=np.float64)
    for start in range(0, len(candidates), score_batch_size):
        stop = min(start + score_batch_size, len(candidates))
        residual = candidate_profiles[start:stop] - target[None, :]
        cost_values[start:stop] = 0.5 * np.einsum(
            "ij,ij->i", residual, residual, optimize=True
        )
    if cost_values.shape != (len(candidates),) or not np.isfinite(cost_values).all():
        raise RuntimeError("P2-R candidate scoring produced invalid costs")
    candidate_indices = np.arange(len(candidates), dtype=np.int64)
    ranked = np.lexsort((candidate_indices, cost_values))
    selected_indices = ranked[:top_k]
    rows = [
        {
            "candidate_index": int(index),
            "q": candidates[index].tolist(),
            "cost": float(cost_values[index]),
            "profile_rmse": math.sqrt(
                2.0 * float(cost_values[index]) / max(int(observed.size), 1)
            ),
        }
        for index in selected_indices.tolist()
    ]
    score_summary = {
        "minimum": float(np.min(cost_values)),
        "median": float(np.median(cost_values)),
        "p90": float(np.percentile(cost_values, 90.0)),
        "maximum": float(np.max(cost_values)),
    }
    return candidates[selected_indices], selected_indices, rows, score_summary


def optimize_recoverability_case(
    model: "CachedTetragonalGPUForward",
    active_indices: Sequence[int],
    observed: np.ndarray,
    *,
    config: Mapping[str, Any],
    candidates: np.ndarray,
    candidate_profiles: np.ndarray,
    nominal_solution: tuple[np.ndarray, Any, Mapping[str, Any]] | None = None,
) -> tuple[np.ndarray, Any, dict[str, Any]]:
    recovery = config["p2"]["recoverability"]
    if nominal_solution is None:
        raise ValueError("P2-R requires the reused P2-L nominal solution")
    starts, selected_indices, candidate_rows, score_summary = rank_multistart_candidates(
        candidates,
        candidate_profiles,
        observed,
        top_k=int(recovery["top_k"]),
        score_batch_size=int(recovery.get("score_batch_size", 16)),
    )
    nominal_recovered, nominal_result, nominal_diagnostics = nominal_solution
    local_rows: list[dict[str, Any]] = [
        {
            "start_rank": 0,
            "candidate_kind": "nominal",
            "candidate_index": None,
            "reused_p2_l_nominal_solution": True,
            **dict(nominal_diagnostics),
            "final_q": nominal_recovered.tolist(),
            "final_cost": float(nominal_result.cost),
            "optimizer_success": bool(nominal_result.success),
            "optimizer_status": int(nominal_result.status),
            "nfev": int(nominal_result.nfev),
            "njev": (
                int(nominal_result.njev)
                if nominal_result.njev is not None
                else None
            ),
        }
    ]
    results: list[tuple[np.ndarray, Any, dict[str, Any]]] = [
        (nominal_recovered, nominal_result, dict(nominal_diagnostics))
    ]
    for start_rank, (candidate_index, start) in enumerate(
        zip(selected_indices.tolist(), starts, strict=True), start=1
    ):
        recovered, result, diagnostics = optimize_case(
            model,
            start,
            active_indices,
            observed,
            config=config,
        )
        results.append((recovered, result, diagnostics))
        local_rows.append(
            {
                "start_rank": start_rank,
                "candidate_kind": "sobol",
                "candidate_index": candidate_index,
                "reused_p2_l_nominal_solution": False,
                **diagnostics,
                "final_q": recovered.tolist(),
                "final_cost": float(result.cost),
                "optimizer_success": bool(result.success),
                "optimizer_status": int(result.status),
                "nfev": int(result.nfev),
                "njev": int(result.njev) if result.njev is not None else None,
            }
        )
    best_index = min(
        range(len(results)),
        key=lambda index: (float(results[index][1].cost), index),
    )
    final_costs = [float(item[1].cost) for item in results]
    if not all(math.isfinite(value) for value in final_costs):
        raise RuntimeError("P2-R local refinement produced a non-finite cost")
    recovered, result, diagnostics = results[best_index]
    nominal_cost = float(nominal_result.cost)
    if float(result.cost) > nominal_cost + 1e-12 * max(1.0, abs(nominal_cost)):
        raise RuntimeError("P2-R selected result is worse than its reused P2-L baseline")
    candidate_sha256 = hashlib.sha256(
        np.ascontiguousarray(candidates, dtype=np.float64).tobytes()
    ).hexdigest()
    diagnostics = {
        **diagnostics,
        "candidate_design": str(recovery["candidate_design"]),
        "sobol_candidate_count_excluding_nominal": len(candidates),
        "top_k_sobol_excluding_nominal": len(starts),
        "score_batch_size": int(recovery.get("score_batch_size", 16)),
        "nominal_solution_always_reused": True,
        "selected_best_local_rank": best_index,
        "candidate_bank_sha256": candidate_sha256,
        "selected_sobol_candidates": candidate_rows,
        "candidate_score_summary": score_summary,
        "local_refinements": local_rows,
    }
    return recovered, result, diagnostics


def summarize_recovery_cases(
    cases: Sequence[Mapping[str, Any]],
    *,
    case_threshold: float,
    success_fraction_min: float,
    median_max: float,
    p90_max: float | None,
) -> dict[str, Any]:
    success_fraction = (
        sum(bool(case["success"]) for case in cases) / len(cases) if cases else 0.0
    )
    by_parameter: dict[str, Any] = {}
    parameter_pass = True
    for name in PARAMETER_NAMES:
        errors = [
            float(case["normalized_absolute_errors"][name])
            for case in cases
            if name in case["normalized_absolute_errors"]
        ]
        if not errors:
            continue
        summary = percentile_summary(errors)
        passed = bool(summary["median"] is not None and summary["median"] <= median_max)
        if p90_max is not None:
            passed = passed and bool(summary["p90"] is not None and summary["p90"] <= p90_max)
        summary["passed"] = passed
        parameter_pass = parameter_pass and passed
        by_parameter[name] = summary
    passed = success_fraction >= success_fraction_min and parameter_pass
    return {
        "status": "PASS" if passed else "FAIL",
        "case_count": len(cases),
        "case_success_nae_max": case_threshold,
        "case_success_count": sum(bool(case["success"]) for case in cases),
        "case_success_fraction": success_fraction,
        "case_success_fraction_min": success_fraction_min,
        "parameter_errors": by_parameter,
        "parameter_median_nae_max": median_max,
        "parameter_p90_nae_max": p90_max,
    }


def summarize_recovery_by_staircase(
    cases: Sequence[Mapping[str, Any]],
    *,
    case_threshold: float,
    success_fraction_min: float,
    median_max: float,
    p90_max: float | None,
) -> dict[str, Any]:
    staircases: dict[str, Any] = {}
    for staircase in STAIRCASES:
        subset = [case for case in cases if str(case["staircase"]) == staircase]
        staircases[staircase] = summarize_recovery_cases(
            subset,
            case_threshold=case_threshold,
            success_fraction_min=success_fraction_min,
            median_max=median_max,
            p90_max=p90_max,
        )
    pooled = summarize_recovery_cases(
        cases,
        case_threshold=case_threshold,
        success_fraction_min=success_fraction_min,
        median_max=median_max,
        p90_max=p90_max,
    )
    passed = all(summary["status"] == "PASS" for summary in staircases.values())
    pooled["status"] = "PASS" if passed else "FAIL"
    pooled["gate_rule"] = "every staircase must pass independently"
    pooled["staircases"] = staircases
    return pooled


def build_recovery_case(
    *,
    protocol: str,
    domain: str,
    context: ParentContext,
    model: "CachedTetragonalGPUForward",
    staircase: str,
    trial: int,
    seed: int,
    active_indices: Sequence[int],
    truth: np.ndarray,
    recovered: np.ndarray,
    observed: np.ndarray,
    result: Any,
    optimizer_diagnostics: Mapping[str, Any],
    config: Mapping[str, Any],
    nuisance_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    q_low, q_high = [
        float(value) for value in config["parameterization"]["q_bounds"]
    ]
    normalized_errors = {
        PARAMETER_NAMES[index]: float(
            abs(recovered[index] - truth[index]) / (q_high - q_low)
        )
        for index in active_indices
    }
    threshold = float(config["p2"][domain]["case_success_nae_max"])
    profile_rmse = math.sqrt(2.0 * float(result.cost) / observed.size)
    profile_rmse_max = float(config["p2"][domain]["profile_rmse_max"])
    truth_physical = parameter_vector_to_physical(
        truth, context.structure, config["parameterization"]
    )
    recovered_physical = parameter_vector_to_physical(
        recovered, context.structure, config["parameterization"]
    )
    truth_residual = model.transformed_numpy(truth) - profile_transform(observed)
    truth_cost = 0.5 * float(np.dot(truth_residual, truth_residual))
    boundary_tolerance = float(
        config["p2"].get("boundary_diagnostic_tolerance_q", 1e-6)
    )
    boundary_flags = {
        PARAMETER_NAMES[index]: bool(
            abs(recovered[index] - q_low) <= boundary_tolerance
            or abs(recovered[index] - q_high) <= boundary_tolerance
        )
        for index in active_indices
    }
    return {
        "protocol": protocol,
        "domain": domain,
        "material_id": context.material_id,
        "formula": context.formula,
        "staircase": staircase,
        "trial": trial,
        "seed": seed,
        "active_parameters": [PARAMETER_NAMES[index] for index in active_indices],
        "truth_q": truth.tolist(),
        "recovered_q": recovered.tolist(),
        "normalized_absolute_errors": normalized_errors,
        "max_normalized_absolute_error": max(normalized_errors.values()),
        "success": bool(
            result.success
            and max(normalized_errors.values()) <= threshold
            and profile_rmse <= profile_rmse_max
        ),
        "optimizer_success": bool(result.success),
        "optimizer_status": int(result.status),
        "optimizer_message": str(result.message),
        "nfev": int(result.nfev),
        "njev": int(result.njev) if result.njev is not None else None,
        "cost": float(result.cost),
        "truth_cost": truth_cost,
        "profile_rmse": profile_rmse,
        "profile_rmse_max": profile_rmse_max,
        "optimality": float(result.optimality),
        "boundary_flags": boundary_flags,
        "hit_any_q_bound": any(boundary_flags.values()),
        "a_relative_error": abs(recovered_physical["a"] / truth_physical["a"] - 1.0),
        "c_relative_error": abs(recovered_physical["c"] / truth_physical["c"] - 1.0),
        "delta_absolute_error_deg": abs(
            recovered_physical["delta_2theta_deg"]
            - truth_physical["delta_2theta_deg"]
        ),
        "fwhm_relative_error": abs(
            recovered_physical["fwhm_deg"] / truth_physical["fwhm_deg"] - 1.0
        ),
        "optimizer_diagnostics": dict(optimizer_diagnostics),
        "nuisance": nuisance_payload,
    }


def run_p2(
    contexts: Sequence[ParentContext],
    p1_report: Mapping[str, Any],
    models: Mapping[str, "CachedTetragonalGPUForward"],
    *,
    config: Mapping[str, Any],
    measurement_config: Mapping[str, Any],
    checkpoint_dir: Path | None = None,
) -> dict[str, Any]:
    eligible = set(str(value) for value in p1_report["eligible_parent_ids"])
    requested = int(config["sampling"]["classical_recovery_parent_count"])
    # Freeze the P2 sample independently of the P1 outcome.  P1 eligibility is
    # retained as an analysis label; filtering or backfilling here would change
    # the formal 24-parent estimand after seeing a Gate result.
    selected = list(contexts[:requested])
    grid = SimulationGrid(
        two_theta_min=float(config["grid"]["two_theta_min"]),
        two_theta_max=float(config["grid"]["two_theta_max"]),
        step=float(config["grid"]["step"]),
        wavelength=str(config["grid"]["wavelength_name"]),
    )
    truth_low, truth_high = [float(value) for value in config["parameterization"]["truth_q_range"]]
    q_low, q_high = [float(value) for value in config["parameterization"]["q_bounds"]]
    trials = int(config["sampling"]["trials_per_parent"])
    del q_low, q_high  # bounds are consumed by helpers; retain one source of truth
    recoverability_clean_cases: list[dict[str, Any]] = []
    local_clean_cases: list[dict[str, Any]] = []
    local_nuisance_cases: list[dict[str, Any]] = []
    resumed_parent_ids: list[str] = []
    checkpoint_contract = {
        "schema_version": "xrd-inversion-p2-parent-checkpoint-v1",
        "config_sha256": hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "week1_module_sha256": sha256_file(Path(__file__).resolve()),
        "selected_parent_ids": [context.material_id for context in selected],
        "trials_per_parent": trials,
    }
    if checkpoint_dir is not None:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

    formal = str(config.get("run_kind", "smoke")) == "formal_gate"
    formal_minimum = int(
        config["formal_gate_minimums"]["classical_recovery_parent_count"]
    )
    formal_trial_minimum = int(config["formal_gate_minimums"]["trials_per_parent"])
    sample_valid = (
        len(selected) == requested
        and (
            not formal
            or (
                requested == formal_minimum
                and len(contexts) == formal_minimum
                and trials == formal_trial_minimum
            )
        )
    )
    if str(p1_report.get("status")) != "PASS" or not sample_valid:
        return {
            "status": "INVALID",
            "reason": (
                "P2 requires a valid P1 PASS and the complete configured parent/trial sample"
            ),
            "requested_parent_count": requested,
            "eligible_parent_count_available": len(eligible),
            "executed_parent_count": 0,
            "executed_parent_ids": [],
            "trials_per_parent": trials,
            "recoverability": {"status": "INVALID", "clean": {"status": "INVALID"}},
            "local_capture": {
                "status": "NOT_A_GATE",
                "clean": {"status": "NOT_RUN"},
                "nuisance": {"status": "NOT_RUN"},
            },
            "clean": {"status": "INVALID"},
            "nuisance": {"status": "NOT_RUN"},
            "recoverability_clean_cases": [],
            "local_clean_cases": [],
            "local_nuisance_cases": [],
        }

    for parent_index, context in enumerate(selected, start=1):
        model = models[context.material_id]
        checkpoint_path = (
            checkpoint_dir / f"{parent_index:03d}_{context.material_id}.json"
            if checkpoint_dir is not None
            else None
        )
        if checkpoint_path is not None and checkpoint_path.exists():
            checkpoint = load_json(checkpoint_path)
            if checkpoint.get("contract") != checkpoint_contract:
                raise ValueError(
                    f"P2 checkpoint contract mismatch: {checkpoint_path}"
                )
            if checkpoint.get("material_id") != context.material_id:
                raise ValueError(
                    f"P2 checkpoint parent mismatch: {checkpoint_path}"
                )
            recoverability_clean_cases.extend(checkpoint["recoverability_clean_cases"])
            local_clean_cases.extend(checkpoint["local_clean_cases"])
            local_nuisance_cases.extend(checkpoint["local_nuisance_cases"])
            resumed_parent_ids.append(context.material_id)
            print(
                f"week1: P2 resume parent {parent_index}/{len(selected)} "
                f"from {checkpoint_path.name}",
                flush=True,
            )
            continue
        parent_recoverability_start = len(recoverability_clean_cases)
        parent_local_start = len(local_clean_cases)
        parent_nuisance_start = len(local_nuisance_cases)
        candidate_banks: dict[str, np.ndarray] = {}
        candidate_profile_banks: dict[str, np.ndarray] = {}
        for staircase, active_indices in STAIRCASES.items():
            candidates = deterministic_sobol_candidates(
                active_indices, config=config
            )
            candidate_banks[staircase] = candidates
            candidate_profile_banks[staircase] = render_candidate_bank(
                model,
                candidates,
                batch_size=int(
                    config["p2"]["recoverability"].get("score_batch_size", 16)
                ),
            )
        for trial in range(trials):
            print(
                f"week1: P2 parent {parent_index}/{len(selected)} trial {trial + 1}/{trials}",
                flush=True,
            )
            seed = stable_seed(config["seed"], "p2", context.material_id, trial)
            rng = np.random.default_rng(seed)
            nominal = np.asarray(
                config["parameterization"]["nominal_q"], dtype=np.float64
            )
            full_truth = rng.uniform(truth_low, truth_high, size=4)
            nuisance = sample_nuisance(measurement_config, rng)
            for staircase, active_indices in STAIRCASES.items():
                truth = nominal.copy()
                truth[list(active_indices)] = full_truth[list(active_indices)]
                clean_observed = model.render_numpy(truth, compatibility=False)
                local_clean_recovered, local_clean_result, local_clean_diagnostics = (
                    optimize_case(
                        model,
                        nominal,
                        active_indices,
                        clean_observed,
                        config=config,
                    )
                )
                local_clean_cases.append(
                    build_recovery_case(
                        protocol="P2-L_nominal_local_capture",
                        domain="clean",
                        context=context,
                        model=model,
                        staircase=staircase,
                        trial=trial,
                        seed=seed,
                        active_indices=active_indices,
                        truth=truth,
                        recovered=local_clean_recovered,
                        observed=clean_observed,
                        result=local_clean_result,
                        optimizer_diagnostics=local_clean_diagnostics,
                        config=config,
                        nuisance_payload=None,
                    )
                )

                recovered, result, diagnostics = optimize_recoverability_case(
                    model,
                    active_indices,
                    clean_observed,
                    config=config,
                    candidates=candidate_banks[staircase],
                    candidate_profiles=candidate_profile_banks[staircase],
                    nominal_solution=(
                        local_clean_recovered,
                        local_clean_result,
                        local_clean_diagnostics,
                    ),
                )
                recoverability_clean_cases.append(
                    build_recovery_case(
                        protocol="P2-R_deterministic_multistart",
                        domain="clean",
                        context=context,
                        model=model,
                        staircase=staircase,
                        trial=trial,
                        seed=seed,
                        active_indices=active_indices,
                        truth=truth,
                        recovered=recovered,
                        observed=clean_observed,
                        result=result,
                        optimizer_diagnostics=diagnostics,
                        config=config,
                        nuisance_payload=None,
                    )
                )

                if staircase == "S3":
                    nuisance_observed = render_profile(
                        context,
                        truth,
                        config=config,
                        grid=grid,
                        rng_seed=seed,
                        nuisance=nuisance,
                    )
                    nuisance_recovered, nuisance_result, nuisance_diagnostics = (
                        optimize_case(
                            model,
                            nominal,
                            active_indices,
                            nuisance_observed,
                            config=config,
                        )
                    )
                    local_nuisance_cases.append(
                        build_recovery_case(
                            protocol="P2-L_nominal_local_capture",
                            domain="nuisance",
                            context=context,
                            model=model,
                            staircase=staircase,
                            trial=trial,
                            seed=seed,
                            active_indices=active_indices,
                            truth=truth,
                            recovered=nuisance_recovered,
                            observed=nuisance_observed,
                            result=nuisance_result,
                            optimizer_diagnostics=nuisance_diagnostics,
                            config=config,
                            nuisance_payload=nuisance,
                        )
                    )
        if checkpoint_path is not None:
            payload = {
                "contract": checkpoint_contract,
                "material_id": context.material_id,
                "recoverability_clean_cases": recoverability_clean_cases[
                    parent_recoverability_start:
                ],
                "local_clean_cases": local_clean_cases[parent_local_start:],
                "local_nuisance_cases": local_nuisance_cases[parent_nuisance_start:],
            }
            temporary = checkpoint_path.with_suffix(".json.tmp")
            with temporary.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(temporary, checkpoint_path)

    clean_cfg = config["p2"]["clean"]
    nuisance_cfg = config["p2"]["nuisance"]
    recoverability_clean_summary = summarize_recovery_by_staircase(
        recoverability_clean_cases,
        case_threshold=float(clean_cfg["case_success_nae_max"]),
        success_fraction_min=float(clean_cfg["case_success_fraction_min"]),
        median_max=float(clean_cfg["parameter_median_nae_max"]),
        p90_max=float(clean_cfg["parameter_p90_nae_max"]),
    )
    local_clean_summary = summarize_recovery_by_staircase(
        local_clean_cases,
        case_threshold=float(clean_cfg["case_success_nae_max"]),
        success_fraction_min=float(clean_cfg["case_success_fraction_min"]),
        median_max=float(clean_cfg["parameter_median_nae_max"]),
        p90_max=float(clean_cfg["parameter_p90_nae_max"]),
    )
    local_nuisance_summary = summarize_recovery_cases(
        local_nuisance_cases,
        case_threshold=float(nuisance_cfg["case_success_nae_max"]),
        success_fraction_min=float(nuisance_cfg["case_success_fraction_min"]),
        median_max=float(nuisance_cfg["parameter_median_nae_max"]),
        p90_max=None,
    )
    local_nuisance_summary["gate_role"] = "diagnostic_only"
    local_nuisance_summary["executed_staircase"] = "S3_full_four_parameter"
    local_nuisance_summary["staircases"] = {
        "S1": {"status": "NOT_RUN"},
        "S2": {"status": "NOT_RUN"},
        "S3": dict(local_nuisance_summary),
    }
    expected_clean_cases = requested * trials * len(STAIRCASES)
    expected_nuisance_cases = requested * trials
    execution_counts_valid = bool(
        len(recoverability_clean_cases) == expected_clean_cases
        and len(local_clean_cases) == expected_clean_cases
        and len(local_nuisance_cases) == expected_nuisance_cases
    )
    if formal and not execution_counts_valid:
        raise RuntimeError("formal P2 case counts disagree with the frozen 24x4 design")
    return {
        "status": recoverability_clean_summary["status"],
        "gate_definition": "P2-R clean deterministic multistart recoverability",
        "requested_parent_count": requested,
        "eligible_parent_count_available": len(eligible),
        "executed_p1_eligible_parent_count": sum(
            context.material_id in eligible for context in selected
        ),
        "executed_p1_ineligible_parent_ids": [
            context.material_id
            for context in selected
            if context.material_id not in eligible
        ],
        "executed_parent_count": len(selected),
        "executed_parent_ids": [context.material_id for context in selected],
        "trials_per_parent": trials,
        "execution_counts": {
            "expected_clean_cases_per_protocol": expected_clean_cases,
            "recoverability_clean_cases": len(recoverability_clean_cases),
            "local_clean_cases": len(local_clean_cases),
            "expected_full_parameter_nuisance_cases": expected_nuisance_cases,
            "local_nuisance_cases": len(local_nuisance_cases),
            "valid": execution_counts_valid,
        },
        "checkpointing": {
            "enabled": checkpoint_dir is not None,
            "directory": checkpoint_dir.as_posix() if checkpoint_dir is not None else None,
            "resumed_parent_count": len(resumed_parent_ids),
            "resumed_parent_ids": resumed_parent_ids,
            "contract": checkpoint_contract,
        },
        "recoverability": {
            "status": recoverability_clean_summary["status"],
            "clean": recoverability_clean_summary,
            "candidate_design": dict(config["p2"]["recoverability"]),
            "candidate_bank_scope": (
                "one deterministic scrambled-Sobol bank per staircase, shared "
                "across every parent and trial"
            ),
            "interpretation": (
                "numerical recoverability gate; deterministic multistart is permitted"
            ),
        },
        "local_capture": {
            "status": "NOT_A_PROJECT_GATE",
            "clean": local_clean_summary,
            "nuisance": local_nuisance_summary,
            "interpretation": (
                "nominal single-start baseline measuring basin and initialization sensitivity"
            ),
        },
        "clean": recoverability_clean_summary,
        "nuisance": local_nuisance_summary,
        "nuisance_interpretation": (
            "P2-L full-four-parameter unmodelled-nuisance stress diagnostic; "
            "not a fair project gate"
        ),
        "paired_design": (
            "each parent/trial reuses one full truth vector and one nuisance realization; "
            "S1-S3 progressively unmask parameters"
        ),
        "nuisance_amplitude_reference": (
            "CPU oracle generates the nuisance observation once; CUDA clean forward is fitted"
        ),
        "recoverability_clean_cases": recoverability_clean_cases,
        "local_clean_cases": local_clean_cases,
        "local_nuisance_cases": local_nuisance_cases,
        "clean_cases": recoverability_clean_cases,
        "nuisance_cases": local_nuisance_cases,
    }


def write_selected_manifest(path: Path, selected: Sequence[Mapping[str, Any]]) -> None:
    fields = (
        "selection_rank",
        "material_id",
        "formula",
        "split",
        "space_group",
        "fingerprint",
        "a",
        "c",
        "c_over_a",
        "nsites",
        "peak_count",
        "restandardized",
    )
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in selected:
            writer.writerow({field: row[field] for field in fields})


def format_float(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}g}"


def build_markdown_report(report: Mapping[str, Any]) -> str:
    def recovery_result(summary: Mapping[str, Any]) -> str:
        if "case_count" not in summary:
            return str(summary.get("status", "UNKNOWN"))
        return (
            f"{summary['status']}; success={summary['case_success_count']}/"
            f"{summary['case_count']} ({float(summary['case_success_fraction']):.1%})"
        )

    audit = report["data_audit"]
    p0 = report["p0"]
    gpu = report["gpu_forward"]
    p1 = report["p1"]
    p2 = report["p2"]
    p2r = p2["recoverability"]["clean"]
    p2l_clean = p2["local_capture"]["clean"]
    p2l_nuisance = p2["local_capture"]["nuisance"]
    administrative = report.get("administrative_audits", {})
    near_duplicate = administrative.get("structural_near_duplicates", {})
    independent = administrative.get("independent_renderer_holdout", {})
    formal = report.get("run_kind") == "formal_gate"
    lines = [
        "# Week-1 PXRD inversion numerical-gate report",
        "",
        f"- Overall decision: **{report['overall_decision']}**",
        (
            "- Scope: **formal 24-parent x 4-trial numerical gate**."
            if formal
            else "- Scope: **repaired smoke only; not the formal Week-1 gate**."
        ),
        "- P2-R is the recoverability gate; P2-L is a nominal-start basin diagnostic.",
        "- P1/P2 physics ran on CUDA float64 with TF32 and autocast disabled.",
        f"- Repository HEAD anchor: `{report['provenance'].get('git_head')}` "
        f"(dirty={report['provenance']['working_tree_dirty']}; exact source hashes are in JSON).",
        f"- Config SHA-256: `{report['provenance']['config_sha256']}`",
        "- No neural-network training was run.",
        "",
        "## Data audit",
        "",
        f"The authoritative tetragonal pool contains **{audit['total_tetragonal_parents']}** parents: "
        f"train={audit['authoritative_split_counts']['train']}, "
        f"validation={audit['authoritative_split_counts']['validation']}, "
        f"test={audit['authoritative_split_counts']['test']}.",
        "",
        f"Exact duplicate fingerprints: {audit['duplicate_fingerprint_count']}. "
        f"Stored non-conventional tetragonal cells: {audit['stored_nonconventional_count']}; "
        f"restandardization failures: {audit['canonicalization_failure_count']}.",
        "",
        (
            "The structural audit is complete: "
            f"{near_duplicate.get('candidate_pair_count', 'n/a')} proxy candidate pairs, "
            f"{near_duplicate.get('same_species_near_duplicate_pair_count', 'n/a')} "
            "same-species matches in that proxy scope, and "
            f"{near_duplicate.get('anonymous_prototype_pair_count', 'n/a')} "
            "default-tolerance anonymous-prototype matches. Anonymous overlap is a "
            "pre-ML split-policy annotation, not a P0-P2 numerical failure."
            if near_duplicate.get("complete")
            else "The structural near-duplicate audit is not complete."
        ),
        f"The high-recall composition/space-group/nsites proxy flags "
        f"{audit['composition_spacegroup_nsites_proxy']['cross_split_group_count']} "
        "cross-split groups involving "
        f"{audit['composition_spacegroup_nsites_proxy']['cross_split_parent_count']} parents; "
        "this is a triage signal, not proof of structural duplication.",
        "",
        "## Gate summary",
        "",
        "| Gate | Status | Key result |",
        "|---|---|---|",
        f"| P0 forward correctness | {p0['status']} | "
        f"{p0['cached_reflection_family_count']} cached reflection families; "
        f"max Bragg error={format_float(p0['max_cached_bragg_error_deg'])} deg |",
        f"| CUDA/CPU forward parity | {gpu['status']} | "
        f"max abs={format_float(gpu['profile_max_abs_max'])}; "
        f"RMSE={format_float(gpu['profile_rmse_max'])} |",
        f"| P1 identifiability | {p1['status']} | "
        f"eligible={p1['eligible_parent_count']}/{p1['representative_parent_count']} "
        f"({p1['eligible_parent_fraction']:.1%}); numerical failures="
        f"{p1['numerical_stability_failure_count']} |",
        f"| P2-R clean recoverability gate | {p2r['status']} | "
        f"{recovery_result(p2r)} |",
        f"| P2-L clean nominal capture | {p2l_clean['status']} (diagnostic) | "
        f"{recovery_result(p2l_clean)} |",
        f"| P2-L nuisance stress | {p2l_nuisance['status']} (diagnostic) | "
        f"{recovery_result(p2l_nuisance)} |",
        "",
        "## P0 notes",
        "",
        f"- Non-conventional stored cells: {', '.join(p0['nonconventional_parent_ids']) or 'none'}.",
        f"- Quarantine by split: {p0['quarantined_split_counts']}; these parents are excluded "
        "until structure fingerprints and reflection caches are regenerated together.",
        f"- Maximum metric-d error: {format_float(p0['max_metric_d_error_angstrom'])} angstrom.",
        f"- Near-degenerate merged reflection families: {p0['merged_near_degenerate_family_count']}.",
        f"- Maximum dynamic-deformation Bragg error: {format_float(p0['max_dynamic_bragg_error_deg'])} deg.",
        f"- Zero-shift maximum error: {format_float(p0['zero_shift_error_deg']['max'])} deg.",
        f"- FWHM maximum error: {format_float(p0['fwhm_error_deg']['max'])} deg.",
        f"- Independent renderer holdout: {independent.get('status', 'NOT_AVAILABLE')}; "
        f"validly frozen unopened={independent.get('validly_frozen_unopened', False)}; "
        f"outcomes opened={independent.get('outcomes_opened')}.",
        "",
    ]
    lines.extend(["## Per-staircase P2", ""])
    if all("staircases" in summary for summary in (p2r, p2l_clean, p2l_nuisance)):
        for staircase in STAIRCASES:
            recovery = p2r["staircases"][staircase]
            local = p2l_clean["staircases"][staircase]
            nuisance = p2l_nuisance["staircases"][staircase]
            lines.append(
                f"- {staircase}: P2-R {recovery_result(recovery)}; "
                f"P2-L clean {recovery_result(local)}; "
                f"P2-L nuisance {recovery_result(nuisance)}."
            )
    else:
        lines.append(f"- P2 was not executed: {p2.get('reason', 'upstream Gate invalid')}.")
    lines.extend(["", "## Decision boundary", ""])
    if report["overall_decision"] in {
        "REPAIRED_SMOKE_PASS_FORMAL_GATE_PENDING",
        "FORMAL_WEEK1_NUMERICAL_GATES_PASS_ADMIN_PENDING",
        "FORMAL_WEEK1_GATE_PASS",
    }:
        lines.extend(
            [
                "The numerical forward, Jacobian, and recoverability checks passed for this "
                "run's scope. This does not authorize formal ML: the full sample requirement, "
                "near-duplicate audit, and frozen unopened independent-renderer boundary must "
                "all be satisfied first.",
            ]
        )
    else:
        lines.extend(
            [
                "At least one P0, CUDA parity, P1 numerical/identifiability, or P2-R "
                "recoverability requirement failed. Do not start formal ML training; inspect "
                "the typed failure before changing the scientific task.",
            ]
        )
    lines.extend(
        [
            "",
            "Full per-parent parity, Jacobian, candidate-ranking, and recovery records are "
            "retained in the JSON artifact; the exact selected parent identities are retained "
            "in the configured CSV manifest.",
            "",
        ]
    )
    return "\n".join(lines)


def run_week1_pilot(repository_root: Path, config_path: Path) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    config_path = config_path.resolve()
    config = load_json(config_path)
    inversion_root = repository_root / "xrd_inversion"
    independent_config_path = (
        inversion_root / "configs" / "independent_renderer_holdout.frozen.json"
    )
    independent_manifest_path = (
        inversion_root / "manifests" / "independent_renderer_holdout.frozen.json"
    )
    independent_source_path = (
        inversion_root / "src" / "xrd_inversion" / "independent_renderer.py"
    )
    independent_config = (
        load_json(independent_config_path) if independent_config_path.exists() else {}
    )
    independent_manifest = (
        load_json(independent_manifest_path) if independent_manifest_path.exists() else {}
    )
    independent_ready = bool(
        independent_config.get("status") == "frozen_unopened"
        and independent_manifest.get("status") == "frozen_unopened"
        and independent_config.get("seal", {}).get("profiles_rendered") is False
        and independent_config.get("seal", {}).get("metrics_computed") is False
        and independent_config.get("seal", {}).get("outcomes_opened") is False
        and independent_source_path.exists()
        and independent_config.get("renderer", {}).get("source_sha256")
        == sha256_file(independent_source_path)
    )
    near_duplicate_report_path = (
        inversion_root / "reports" / "week1_structural_near_duplicate_audit.json"
    )
    near_duplicate_audit = (
        load_json(near_duplicate_report_path)
        if near_duplicate_report_path.exists()
        else {}
    )
    near_duplicate_summary = near_duplicate_audit.get("summary", {})
    near_duplicate_complete = bool(
        str(near_duplicate_audit.get("audit_status", "")).startswith("COMPLETE")
        and int(near_duplicate_summary.get("pair_error_count", 1)) == 0
    )
    paths = resolve_source_paths(repository_root, config)
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"missing source_contract path {name}: {path}")

    split_by_id, fingerprint_by_id, crystal_system_by_id, split_manifest = load_authoritative_split(
        paths["authoritative_split"]
    )
    split_contract = load_json(paths["split_contract"])
    expected_hashes = {
        "records": str(split_contract["source_records"]["sha256"]).lower(),
        "authoritative_split": str(split_contract["split"]["sha256"]).lower(),
        "peak_cache_manifest": str(split_contract["peak_cache"]["sha256"]).lower(),
    }
    actual_hashes = {
        "records": sha256_file(paths["records"]),
        "authoritative_split": sha256_file(paths["authoritative_split"]),
        "peak_cache_manifest": sha256_file(paths["peak_cache_manifest"]),
    }
    for name, expected in expected_hashes.items():
        if actual_hashes[name].lower() != expected:
            raise ValueError(f"{name} SHA-256 disagrees with frozen split contract")
    actual_split_hash = sha256_file(paths["authoritative_split"])
    records = load_tetragonal_records(
        paths["records"], split_by_id, fingerprint_by_id, crystal_system_by_id
    )
    records_by_id = {str(record["material_id"]): record for record in records}
    expected_cache_dir = (
        paths["data_root"] / "mp_processed" / "peak_tables_v7_reflection"
    ).resolve()
    expected_cache_manifest = (
        paths["data_root"]
        / "manifests"
        / "peak_cache_manifest.v7.reflection.csv"
    ).resolve()
    if paths["peak_cache_dir"].resolve() != expected_cache_dir:
        raise ValueError("configured peak_cache_dir is not the validated V7 cache directory")
    if paths["peak_cache_manifest"].resolve() != expected_cache_manifest:
        raise ValueError("configured peak_cache_manifest is not the validated V7 manifest")
    cache_validation = validate_peak_cache_manifest(
        paths["data_root"],
        "peak_tables_v7_reflection",
        records_by_id,
        require_exact_ids=False,
        verify_file_hashes=True,
    )
    cache_validation = {
        key: value.as_posix() if isinstance(value, Path) else value
        for key, value in cache_validation.items()
    }
    peak_manifest = load_csv_index(paths["peak_cache_manifest"], "material_id")
    data_audit, features = audit_tetragonal_pool(
        records, peak_manifest, config["canonical_cell"]
    )
    data_audit["peak_cache_validation"] = cache_validation
    data_audit["near_duplicate_audit_status"] = (
        near_duplicate_audit.get("audit_status")
        if near_duplicate_complete
        else "pending_structural_near_duplicate_audit"
    )
    selected = select_representative_parents(
        features,
        count=int(config["sampling"]["representative_parent_count"]),
        split=str(config["sampling"]["split"]),
    )
    contexts = [
        build_parent_context(
            row, peak_manifest, paths, config["canonical_cell"]
        )
        for row in selected
    ]
    print("week1: P0 forward audit", flush=True)
    p0_report = run_p0(
        records, contexts, peak_manifest, cache_validation, config, paths
    )
    p0_report["scope"] = "smoke/provenance forward audit, not formal full-semantic P0"
    p0_report["scope_limitations"] = [
        "fresh cache semantic equality is checked on selected representatives, not all conventional parents",
        "zero-shift and FWHM primitives are checked below the full q-to-PhysicsParameters chain",
    ]
    print("week1: compile CUDA forward caches", flush=True)
    models = build_gpu_forward_models(contexts, config)
    print("week1: strict CUDA/CPU forward parity", flush=True)
    gpu_forward_report = run_gpu_forward_parity(contexts, models, config=config)
    print("week1: P1 autograd Jacobian and fixed finite-difference audit", flush=True)
    p1_report = run_p1(
        contexts,
        models,
        gpu_forward_report,
        config=config,
    )
    measurement_config = load_json(paths["measurement_config"])
    print("week1: P2-R recoverability and P2-L local-capture baseline", flush=True)
    checkpoint_dir = None
    if bool(config.get("runtime", {}).get("parent_checkpointing", False)):
        checkpoint_dir = resolve_output_path(
            repository_root,
            config,
            "checkpoint_dir",
            "xrd_inversion/checkpoints/week1_formal",
        )
    p2_report = run_p2(
        contexts,
        p1_report,
        models,
        config=config,
        measurement_config=measurement_config,
        checkpoint_dir=checkpoint_dir,
    )
    core_passed = (
        p0_report["status"] in {"PASS", "PASS_WITH_QUARANTINE"}
        and gpu_forward_report["status"] == "PASS"
        and p1_report["status"] == "PASS"
        and p2_report["recoverability"]["clean"]["status"] == "PASS"
    )
    manifest_path = resolve_output_path(
        repository_root,
        config,
        "selected_manifest",
        "xrd_inversion/manifests/week1_selected_parents.csv",
    )
    results_path = resolve_output_path(
        repository_root,
        config,
        "results",
        "xrd_inversion/reports/week1_pilot_results.json",
    )
    markdown_path = resolve_output_path(
        repository_root,
        config,
        "markdown",
        "xrd_inversion/reports/WEEK1_PILOT_REPORT.md",
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    write_selected_manifest(manifest_path, selected)
    source_paths = {
        "week1_module": Path(__file__).resolve(),
        "gpu_forward": Path(__file__).resolve().with_name("gpu_forward.py"),
        "independent_renderer": independent_source_path,
        "independent_renderer_config": independent_config_path,
        "independent_renderer_manifest": independent_manifest_path,
        "near_duplicate_audit": near_duplicate_report_path,
        "runner": inversion_root / "scripts" / "run_week1_pilot.py",
        "renderer": repository_root
        / "xrd_robustness"
        / "src"
        / "xrd_robustness"
        / "simulator.py",
        "physics": repository_root
        / "xrd_robustness"
        / "src"
        / "xrd_robustness"
        / "physics.py",
        "peak_cache": repository_root
        / "xrd_robustness"
        / "src"
        / "xrd_robustness"
        / "peak_cache.py",
        "measurement_models": repository_root
        / "xrd_robustness"
        / "src"
        / "xrd_robustness"
        / "measurement_models.py",
        "simulation_interfaces": repository_root
        / "xrd_robustness"
        / "src"
        / "xrd_robustness"
        / "simulation_interfaces.py",
        "split_contract": paths["split_contract"],
    }
    current_git_status = git_status(repository_root)
    run_kind = str(config.get("run_kind", "smoke"))
    formal = run_kind == "formal_gate"
    anonymous_overlap_count = int(
        near_duplicate_summary.get("anonymous_default_tolerance", {}).get(
            "pair_count", 0
        )
    )
    same_species_near_duplicate_count = int(
        near_duplicate_summary.get("same_species_default_tolerance", {}).get(
            "pair_count", 0
        )
    )
    formal_pending_reasons: list[str] = []
    if not formal:
        formal_pending_reasons.append("smoke sample is below the frozen formal minimum")
    if not near_duplicate_complete:
        formal_pending_reasons.append("structural near-duplicate audit is incomplete")
    elif same_species_near_duplicate_count:
        formal_pending_reasons.append(
            "same-species cross-split structural near-duplicates require split repair"
        )
    if near_duplicate_complete and anonymous_overlap_count:
        formal_pending_reasons.append(
            "anonymous prototype overlap across splits requires a pre-ML split-policy decision"
        )
    if not independent_ready:
        formal_pending_reasons.append(
            "independent-renderer holdout is not validly frozen and unopened"
        )
    formal_ready = bool(formal and core_passed and not formal_pending_reasons)
    overall_decision = (
        "FORMAL_WEEK1_GATE_PASS"
        if formal_ready
        else "FORMAL_WEEK1_NUMERICAL_GATES_PASS_ADMIN_PENDING"
        if formal and core_passed
        else "REPAIRED_SMOKE_PASS_FORMAL_GATE_PENDING"
        if core_passed
        else "HOLD_REPAIR_BEFORE_FORMAL_GATE"
    )
    report = {
        "schema_version": "xrd-inversion-week1-results-v3",
        "run_kind": run_kind,
        "overall_decision": overall_decision,
        "formal_week1_numerical_gate_passed": bool(formal and core_passed),
        "formal_week1_gate_ready": formal_ready,
        "formal_gate_pending_reasons": formal_pending_reasons,
        "provenance": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_head": git_head(repository_root),
            "git_status_short": current_git_status,
            "working_tree_dirty": bool(current_git_status),
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy_version,
            "pymatgen": installed_version("pymatgen"),
            "torch": installed_version("torch"),
            "config": config_path.relative_to(repository_root).as_posix(),
            "config_sha256": sha256_file(config_path),
            "records_sha256": actual_hashes["records"],
            "authoritative_split_sha256": actual_split_hash,
            "peak_cache_manifest_sha256": actual_hashes["peak_cache_manifest"],
            "measurement_config_sha256": sha256_file(paths["measurement_config"]),
            "structure_manifest_sha256": sha256_file(paths["structure_manifest"]),
            "split_contract_sha256": sha256_file(paths["split_contract"]),
            "selected_manifest_sha256": sha256_file(manifest_path),
            "source_file_sha256": {
                name: sha256_file(path) for name, path in source_paths.items()
            },
            "frozen_source_hash_validation": {
                name: {
                    "expected": expected_hashes[name],
                    "actual": actual_hashes[name],
                    "matched": actual_hashes[name].lower() == expected_hashes[name],
                }
                for name in expected_hashes
            },
            "authoritative_split_algorithm": split_manifest.get("algorithm"),
            "authoritative_split_seed": split_manifest.get("seed"),
        },
        "config": config,
        "data_audit": data_audit,
        "selected_parents": [
            {
                key: value
                for key, value in row.items()
                if key not in {"record", "selection_feature_vector"}
            }
            for row in selected
        ],
        "p0": p0_report,
        "gpu_forward": gpu_forward_report,
        "p1": p1_report,
        "p2": p2_report,
        "administrative_audits": {
            "nonconventional_cells": {
                "status": "RESOLVED_BY_EXPLICIT_V0_QUARANTINE",
                "count": len(p0_report["quarantined_parent_ids"]),
                "parent_ids": p0_report["quarantined_parent_ids"],
            },
            "structural_near_duplicates": {
                "status": near_duplicate_audit.get("audit_status", "NOT_AVAILABLE"),
                "complete": near_duplicate_complete,
                "candidate_pair_count": near_duplicate_summary.get(
                    "candidate_cross_split_pair_count"
                ),
                "same_species_near_duplicate_pair_count": (
                    same_species_near_duplicate_count
                ),
                "anonymous_prototype_pair_count": anonymous_overlap_count,
                "report_sha256": (
                    sha256_file(near_duplicate_report_path)
                    if near_duplicate_report_path.exists()
                    else None
                ),
            },
            "independent_renderer_holdout": {
                "status": independent_config.get("status", "NOT_AVAILABLE"),
                "validly_frozen_unopened": independent_ready,
                "renderer_source_sha256": (
                    sha256_file(independent_source_path)
                    if independent_source_path.exists()
                    else None
                ),
                "candidate_parent_count": independent_config.get(
                    "selection", {}
                ).get("candidate_parent_count"),
                "outcomes_opened": independent_config.get("seal", {}).get(
                    "outcomes_opened"
                ),
            },
        },
        "execution_boundary": {
            "neural_network_training_run": False,
            "dataset_integrity_audit_splits_accessed": ["train", "validation", "test"],
            "p0_formula_audit_splits_accessed": ["train", "validation", "test"],
            "representative_selection_splits_accessed": ["train"],
            "p1_splits_accessed": ["train"],
            "p2_splits_accessed": ["train"],
            "validation_or_test_used_for_selection_or_tuning": False,
            "gpu_primary_for_p1_p2": True,
            "cpu_roles": [
                "authoritative P0 oracle",
                "one-time P2 nuisance observation generation",
                "SciPy trust-region optimizer control flow",
            ],
            "independent_renderer_test_status": independent_config.get(
                "status", "not_available"
            ),
            "independent_renderer_test_opened": False,
        },
    }
    with results_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    markdown_path.write_text(build_markdown_report(report), encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--repository-root", type=Path, default=default_root)
    parser.add_argument(
        "--config",
        type=Path,
        default=(
            default_root
            / "xrd_inversion"
            / "configs"
            / "week1_repaired_smoke.json"
        ),
    )
    args = parser.parse_args(argv)
    report = run_week1_pilot(args.repository_root, args.config)
    print(json.dumps(
        {
            "overall_decision": report["overall_decision"],
            "p0": report["p0"]["status"],
            "p1": report["p1"]["status"],
            "p2_clean": report["p2"]["clean"]["status"],
            "p2_nuisance": report["p2"]["nuisance"]["status"],
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
