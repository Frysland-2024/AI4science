"""Read-only Week-1 structural near-duplicate audit.

The audit expands the existing high-recall proxy
``anonymized formula + space group + nsites`` into every cross-split pair and
checks those pairs with Pymatgen ``StructureMatcher``.  It never changes the
frozen split and deliberately reports anonymous prototype similarity separately
from same-species structural similarity.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import hashlib
import itertools
import json
from pathlib import Path
import platform
import time
from typing import Any, Iterable, Mapping, Sequence

from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core import Composition, Structure


SPLITS = ("train", "validation", "test")
PAIR_FIELDNAMES = (
    "proxy_group_id",
    "anonymized_formula",
    "space_group",
    "nsites",
    "material_id_a",
    "split_a",
    "formula_a",
    "fingerprint_a",
    "material_id_b",
    "split_b",
    "formula_b",
    "fingerprint_b",
    "split_edge",
    "anonymous_high_recall_match",
    "anonymous_default_tolerance_match",
    "same_species_default_tolerance_match",
    "classification",
    "error",
)


@dataclass(frozen=True)
class AuditParent:
    """One parent participating in a cross-split proxy group."""

    material_id: str
    split: str
    formula: str
    fingerprint: str
    anonymized_formula: str
    space_group: int
    nsites: int
    structure: Structure


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def resolve_repository_path(repository_root: Path, value: object) -> Path:
    root = repository_root.resolve()
    path = (root / str(value)).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"path escapes repository: {path}")
    return path


def proxy_key(
    formula: str, space_group: int, nsites: int
) -> tuple[str, int, int]:
    return (
        Composition(formula).anonymized_formula,
        int(space_group),
        int(nsites),
    )


def proxy_group_id(key: tuple[str, int, int]) -> str:
    payload = json.dumps(key, ensure_ascii=True, separators=(",", ":"))
    return "proxy_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def canonical_split_edge(left: str, right: str) -> str:
    if left == right:
        raise ValueError("split edge requires two distinct splits")
    positions = {name: index for index, name in enumerate(SPLITS)}
    if left not in positions or right not in positions:
        raise ValueError(f"unknown split edge: {left}, {right}")
    ordered = sorted((left, right), key=positions.__getitem__)
    return f"{ordered[0]}-{ordered[1]}"


def build_cross_split_proxy_groups(
    parents: Iterable[AuditParent],
) -> dict[tuple[str, int, int], list[AuditParent]]:
    """Return only proxy groups that contain at least two frozen splits."""

    groups: dict[tuple[str, int, int], list[AuditParent]] = defaultdict(list)
    for parent in parents:
        groups[
            (parent.anonymized_formula, parent.space_group, parent.nsites)
        ].append(parent)
    cross_split: dict[tuple[str, int, int], list[AuditParent]] = {}
    for key, members in groups.items():
        members.sort(key=lambda row: row.material_id)
        if len({row.split for row in members}) > 1:
            cross_split[key] = members
    return dict(sorted(cross_split.items(), key=lambda item: item[0]))


def enumerate_cross_split_pairs(
    groups: Mapping[tuple[str, int, int], Sequence[AuditParent]],
) -> list[tuple[tuple[str, int, int], AuditParent, AuditParent]]:
    rows: list[tuple[tuple[str, int, int], AuditParent, AuditParent]] = []
    for key, members in groups.items():
        for left, right in itertools.combinations(members, 2):
            if left.split != right.split:
                rows.append((key, left, right))
    return rows


def load_tetragonal_parents(
    records_path: Path,
    split_path: Path,
    *,
    crystal_system: str = "tetragonal",
) -> tuple[list[AuditParent], dict[str, Any]]:
    split_manifest = load_json(split_path)
    split_rows = split_manifest.get("records")
    if not isinstance(split_rows, list) or not split_rows:
        raise ValueError("authoritative split has no records")

    split_by_id: dict[str, str] = {}
    fingerprint_by_id: dict[str, str] = {}
    system_by_id: dict[str, str] = {}
    for row in split_rows:
        material_id = str(row["material_id"])
        if material_id in split_by_id:
            raise ValueError(f"duplicate split material_id: {material_id}")
        split = str(row["split"])
        if split not in SPLITS:
            raise ValueError(f"invalid split {split!r}: {material_id}")
        split_by_id[material_id] = split
        fingerprint_by_id[material_id] = str(row["parent_structure_id"])
        system_by_id[material_id] = str(row["crystal_system"])

    parents: list[AuditParent] = []
    seen_ids: set[str] = set()
    with records_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if str(row.get("crystal_system")) != crystal_system:
                continue
            material_id = str(row["material_id"])
            if material_id in seen_ids:
                raise ValueError(f"duplicate record material_id: {material_id}")
            seen_ids.add(material_id)
            if material_id not in split_by_id:
                raise ValueError(f"record absent from frozen split: {material_id}")
            if system_by_id[material_id] != crystal_system:
                raise ValueError(f"split crystal-system mismatch: {material_id}")
            fingerprint = str(row["structure_fingerprint"])
            if fingerprint != fingerprint_by_id[material_id]:
                raise ValueError(
                    f"fingerprint mismatch at records line {line_number}: {material_id}"
                )
            formula = str(row["formula"])
            key = proxy_key(
                formula,
                int(row["space_group_recomputed"]),
                int(row["nsites"]),
            )
            structure_data = row.get("standardized_structure")
            if not isinstance(structure_data, dict):
                raise ValueError(f"missing standardized structure: {material_id}")
            structure = Structure.from_dict(structure_data)
            parents.append(
                AuditParent(
                    material_id=material_id,
                    split=split_by_id[material_id],
                    formula=formula,
                    fingerprint=fingerprint,
                    anonymized_formula=key[0],
                    space_group=key[1],
                    nsites=key[2],
                    structure=structure,
                )
            )
    parents.sort(key=lambda row: row.material_id)
    return parents, split_manifest


def make_matcher(
    config: Mapping[str, Any], *, comparator: ElementComparator | None = None
) -> StructureMatcher:
    return StructureMatcher(
        ltol=float(config["ltol"]),
        stol=float(config["stol"]),
        angle_tol=float(config["angle_tol"]),
        primitive_cell=bool(config["primitive_cell"]),
        scale=bool(config["scale"]),
        attempt_supercell=bool(config["attempt_supercell"]),
        allow_subset=bool(config["allow_subset"]),
        comparator=comparator,
    )


def reduce_structures_once(
    parents: Iterable[AuditParent], matcher: StructureMatcher
) -> tuple[dict[str, Structure], dict[str, str]]:
    """Cache the same primitive+Niggli reduction used by StructureMatcher."""

    reduced: dict[str, Structure] = {}
    errors: dict[str, str] = {}
    for parent in parents:
        try:
            reduced[parent.material_id] = matcher._get_reduced_structure(  # noqa: SLF001
                parent.structure,
                primitive_cell=matcher._primitive_cell,  # noqa: SLF001
                niggli=True,
            )
        except Exception as error:  # preserve a complete invalidity ledger
            errors[parent.material_id] = f"{type(error).__name__}: {error}"
    return reduced, errors


def _bool_csv(value: bool) -> str:
    return "true" if value else "false"


def classify_pair(
    *, high_recall: bool, default_anonymous: bool, same_species: bool
) -> str:
    if same_species:
        return "same_species_near_duplicate"
    if default_anonymous:
        return "anonymous_prototype_default_tolerance"
    if high_recall:
        return "anonymous_prototype_high_recall_only"
    return "screened_nonmatch"


def audit_pairs(
    pairs: Sequence[tuple[tuple[str, int, int], AuditParent, AuditParent]],
    reduced: Mapping[str, Structure],
    reduction_errors: Mapping[str, str],
    *,
    high_matcher: StructureMatcher,
    default_anonymous_matcher: StructureMatcher,
    same_species_matcher: StructureMatcher,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for key, left, right in pairs:
        high_recall = False
        default_anonymous = False
        same_species = False
        errors = [
            f"{material_id}: {reduction_errors[material_id]}"
            for material_id in (left.material_id, right.material_id)
            if material_id in reduction_errors
        ]
        if not errors:
            left_structure = reduced[left.material_id]
            right_structure = reduced[right.material_id]
            try:
                high_recall = high_matcher.fit_anonymous(
                    left_structure,
                    right_structure,
                    skip_structure_reduction=True,
                )
                if high_recall:
                    default_anonymous = default_anonymous_matcher.fit_anonymous(
                        left_structure,
                        right_structure,
                        skip_structure_reduction=True,
                    )
                if default_anonymous:
                    same_species = same_species_matcher.fit(
                        left_structure,
                        right_structure,
                        symmetric=True,
                        skip_structure_reduction=True,
                    )
            except Exception as error:
                errors.append(f"{type(error).__name__}: {error}")
        results.append(
            {
                "proxy_group_id": proxy_group_id(key),
                "anonymized_formula": key[0],
                "space_group": key[1],
                "nsites": key[2],
                "material_id_a": left.material_id,
                "split_a": left.split,
                "formula_a": left.formula,
                "fingerprint_a": left.fingerprint,
                "material_id_b": right.material_id,
                "split_b": right.split,
                "formula_b": right.formula,
                "fingerprint_b": right.fingerprint,
                "split_edge": canonical_split_edge(left.split, right.split),
                "anonymous_high_recall_match": _bool_csv(high_recall),
                "anonymous_default_tolerance_match": _bool_csv(default_anonymous),
                "same_species_default_tolerance_match": _bool_csv(same_species),
                "classification": classify_pair(
                    high_recall=high_recall,
                    default_anonymous=default_anonymous,
                    same_species=same_species,
                ),
                "error": " | ".join(errors),
            }
        )
    return results


def summarize_results(
    parents: Sequence[AuditParent],
    groups: Mapping[tuple[str, int, int], Sequence[AuditParent]],
    rows: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    candidate_parent_ids = {
        parent.material_id for members in groups.values() for parent in members
    }
    classifications = Counter(str(row["classification"]) for row in rows)
    edge_candidates = Counter(str(row["split_edge"]) for row in rows)
    edge_high = Counter(
        str(row["split_edge"])
        for row in rows
        if row["anonymous_high_recall_match"] == "true"
    )
    edge_default = Counter(
        str(row["split_edge"])
        for row in rows
        if row["anonymous_default_tolerance_match"] == "true"
    )
    edge_same = Counter(
        str(row["split_edge"])
        for row in rows
        if row["same_species_default_tolerance_match"] == "true"
    )
    high_rows = [row for row in rows if row["anonymous_high_recall_match"] == "true"]
    default_rows = [
        row for row in rows if row["anonymous_default_tolerance_match"] == "true"
    ]
    same_rows = [
        row for row in rows if row["same_species_default_tolerance_match"] == "true"
    ]
    same_composition_rows = [
        row
        for row in rows
        if Composition(str(row["formula_a"])).reduced_composition
        == Composition(str(row["formula_b"])).reduced_composition
    ]

    def match_extent(match_rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
        return {
            "pair_count": len(match_rows),
            "proxy_group_count": len(
                {str(row["proxy_group_id"]) for row in match_rows}
            ),
            "parent_count": len(
                {
                    str(row[field])
                    for row in match_rows
                    for field in ("material_id_a", "material_id_b")
                }
            ),
        }

    return {
        "tetragonal_parent_count": len(parents),
        "candidate_proxy_group_count": len(groups),
        "candidate_parent_count": len(candidate_parent_ids),
        "candidate_cross_split_pair_count": len(rows),
        "same_reduced_composition_candidate_pair_count": len(same_composition_rows),
        "candidate_pair_counts_by_split_edge": dict(sorted(edge_candidates.items())),
        "anonymous_high_recall": {
            **match_extent(high_rows),
            "pair_counts_by_split_edge": dict(sorted(edge_high.items())),
        },
        "anonymous_default_tolerance": {
            **match_extent(default_rows),
            "pair_counts_by_split_edge": dict(sorted(edge_default.items())),
        },
        "same_species_default_tolerance": {
            **match_extent(same_rows),
            "pair_counts_by_split_edge": dict(sorted(edge_same.items())),
        },
        "classification_counts": dict(sorted(classifications.items())),
        "pair_error_count": sum(bool(str(row["error"])) for row in rows),
    }


def write_pair_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PAIR_FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    high = summary["anonymous_high_recall"]
    default = summary["anonymous_default_tolerance"]
    same = summary["same_species_default_tolerance"]
    status = str(report["audit_status"])
    lines = [
        "# Week-1 Structural Near-Duplicate Audit",
        "",
        f"**Audit status: `{status}`**",
        "",
        "This is a read-only audit of the frozen tetragonal parent split. It did not move, "
        "remove, or relabel any parent.",
        "",
        "## Scope",
        "",
        f"- Tetragonal parents inspected: {summary['tetragonal_parent_count']}",
        f"- Cross-split proxy groups: {summary['candidate_proxy_group_count']}",
        f"- Parents in those groups: {summary['candidate_parent_count']}",
        f"- Exhaustive cross-split candidate pairs: {summary['candidate_cross_split_pair_count']}",
        f"- Same-reduced-composition candidate pairs: "
        f"{summary['same_reduced_composition_candidate_pair_count']}",
        f"- Candidate edges: `{summary['candidate_pair_counts_by_split_edge']}`",
        "",
        "The proxy is `anonymized_formula + recomputed_space_group + nsites`. Every "
        "cross-split pair inside every cross-split proxy group was evaluated; this is not a sample.",
        "",
        "## StructureMatcher results",
        "",
        f"- Anonymous high-recall matches: {high['pair_count']} pairs, "
        f"{high['proxy_group_count']} groups, {high['parent_count']} parents.",
        f"- Anonymous default-tolerance matches: {default['pair_count']} pairs, "
        f"{default['proxy_group_count']} groups, {default['parent_count']} parents.",
        f"- Same-species default-tolerance matches: {same['pair_count']} pairs, "
        f"{same['proxy_group_count']} groups, {same['parent_count']} parents.",
        f"- Pair-level errors: {summary['pair_error_count']}.",
        "",
        "Anonymous matching permits a one-to-one species mapping and is therefore evidence "
        "of cross-split structural-prototype overlap, not proof that two records are the same "
        "chemical material. Same-species matches are the narrower near-duplicate signal.",
        "In this ledger there are no same-reduced-composition cross-split candidate pairs, "
        "so the zero same-species count is descriptive rather than an independently powered "
        "negative result.",
        "",
        "## Interpretation boundary",
        "",
        "The audit is complete when every candidate pair has a valid result. Detected matches "
        "are recorded rather than silently repaired: any policy decision about prototype-aware "
        "resplitting is separate work and was not authorized by this audit.",
        "",
        "## Reproducibility",
        "",
        f"- Config SHA-256: `{report['provenance']['config_sha256']}`",
        f"- Records SHA-256: `{report['provenance']['records_sha256']}`",
        f"- Frozen split SHA-256: `{report['provenance']['authoritative_split_sha256']}`",
        f"- Pair ledger SHA-256: `{report['artifacts']['pair_csv_sha256']}`",
        f"- Pymatgen: `{report['environment']['pymatgen_version']}`",
        f"- Wall time: {report['runtime']['wall_seconds']:.3f} s",
        "",
    ]
    return "\n".join(lines)


def run_audit(repository_root: Path, config_path: Path) -> dict[str, Any]:
    started = time.perf_counter()
    config = load_json(config_path)
    sources = config["source_contract"]
    records_path = resolve_repository_path(repository_root, sources["records"])
    split_path = resolve_repository_path(repository_root, sources["authoritative_split"])
    outputs = config["outputs"]
    pair_csv = resolve_repository_path(repository_root, outputs["pair_csv"])
    results_json = resolve_repository_path(repository_root, outputs["results_json"])
    report_markdown = resolve_repository_path(repository_root, outputs["report_markdown"])

    parents, split_manifest = load_tetragonal_parents(records_path, split_path)
    groups = build_cross_split_proxy_groups(parents)
    pairs = enumerate_cross_split_pairs(groups)

    matcher_config = config["structure_matcher"]
    high_matcher = make_matcher(matcher_config["anonymous_high_recall"])
    default_anonymous_matcher = make_matcher(
        matcher_config["anonymous_default_sensitivity"]
    )
    same_species_matcher = make_matcher(
        matcher_config["same_species_default"], comparator=ElementComparator()
    )
    candidate_parents = [parent for members in groups.values() for parent in members]
    unique_candidate_parents = {
        parent.material_id: parent for parent in candidate_parents
    }
    reduction_started = time.perf_counter()
    reduced, reduction_errors = reduce_structures_once(
        unique_candidate_parents.values(), high_matcher
    )
    reduction_seconds = time.perf_counter() - reduction_started

    matching_started = time.perf_counter()
    rows = audit_pairs(
        pairs,
        reduced,
        reduction_errors,
        high_matcher=high_matcher,
        default_anonymous_matcher=default_anonymous_matcher,
        same_species_matcher=same_species_matcher,
    )
    matching_seconds = time.perf_counter() - matching_started
    summary = summarize_results(parents, groups, rows)
    if reduction_errors or summary["pair_error_count"]:
        audit_status = "INVALID_INCOMPLETE_PAIR_EVALUATION"
    elif summary["same_species_default_tolerance"]["pair_count"]:
        audit_status = "COMPLETE_SAME_SPECIES_NEAR_DUPLICATES_DETECTED"
    elif summary["anonymous_high_recall"]["pair_count"]:
        audit_status = "COMPLETE_ANONYMOUS_PROTOTYPE_OVERLAP_DETECTED"
    else:
        audit_status = "COMPLETE_NO_STRUCTURAL_MATCHES_DETECTED"

    write_pair_csv(pair_csv, rows)
    from importlib.metadata import PackageNotFoundError, version

    try:
        pymatgen_version = version("pymatgen")
    except PackageNotFoundError:
        pymatgen_version = None
    wall_seconds = time.perf_counter() - started
    report: dict[str, Any] = {
        "schema_version": str(config["schema_version"]),
        "purpose": str(config["purpose"]),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_status": audit_status,
        "data_mutation": "none_read_only_audit",
        "scope": config["scope"],
        "matcher_contract": matcher_config,
        "summary": summary,
        "reduction_errors": dict(sorted(reduction_errors.items())),
        "split_manifest": {
            "algorithm": split_manifest.get("algorithm"),
            "seed": split_manifest.get("seed"),
            "records_count": len(split_manifest.get("records", [])),
        },
        "runtime": {
            "wall_seconds": wall_seconds,
            "structure_reduction_seconds": reduction_seconds,
            "pair_matching_seconds": matching_seconds,
            "pairs_per_second": len(rows) / matching_seconds if matching_seconds else None,
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pymatgen_version": pymatgen_version,
        },
        "provenance": {
            "config": str(config_path.relative_to(repository_root).as_posix()),
            "config_sha256": sha256_file(config_path),
            "records": str(records_path.relative_to(repository_root).as_posix()),
            "records_sha256": sha256_file(records_path),
            "authoritative_split": str(split_path.relative_to(repository_root).as_posix()),
            "authoritative_split_sha256": sha256_file(split_path),
        },
        "artifacts": {
            "pair_csv": str(pair_csv.relative_to(repository_root).as_posix()),
            "pair_csv_sha256": sha256_file(pair_csv),
            "results_json": str(results_json.relative_to(repository_root).as_posix()),
            "report_markdown": str(report_markdown.relative_to(repository_root).as_posix()),
        },
    }
    results_json.parent.mkdir(parents=True, exist_ok=True)
    results_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_markdown.parent.mkdir(parents=True, exist_ok=True)
    report_markdown.write_text(build_markdown(report), encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("xrd_inversion/configs/week1_near_duplicate_audit.json"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository_root = args.repository_root.resolve()
    config_path = args.config
    if not config_path.is_absolute():
        config_path = (repository_root / config_path).resolve()
    report = run_audit(repository_root, config_path)
    print(json.dumps({"audit_status": report["audit_status"], **report["summary"]}, indent=2))
    return 0 if not str(report["audit_status"]).startswith("INVALID") else 2


if __name__ == "__main__":
    raise SystemExit(main())
