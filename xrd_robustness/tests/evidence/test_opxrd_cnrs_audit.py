from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "audit_opxrd_cnrs_7cs.py"
SPEC = importlib.util.spec_from_file_location("opxrd_cnrs_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        (1, "triclinic"),
        (2, "triclinic"),
        (3, "monoclinic"),
        (15, "monoclinic"),
        (16, "orthorhombic"),
        (74, "orthorhombic"),
        (75, "tetragonal"),
        (142, "tetragonal"),
        (143, "trigonal"),
        (167, "trigonal"),
        (168, "hexagonal"),
        (194, "hexagonal"),
        (195, "cubic"),
        (230, "cubic"),
    ],
)
def test_space_group_boundaries(number: int, expected: str) -> None:
    assert AUDIT.crystal_system_from_space_group(number) == expected


def test_window_coverage_is_strict_unless_tolerance_is_explicit() -> None:
    assert AUDIT.covers_window(10.0, 80.0, 10.0, 80.0)
    assert not AUDIT.covers_window(10.0006, 80.0, 10.0, 80.0)
    assert AUDIT.covers_window(10.0006, 79.999, 10.0, 80.0, tolerance=0.01)


def test_manual_review_sample_is_opt_in() -> None:
    args = AUDIT.parse_args(
        ["--source-root", "source", "--output-root", "output"]
    )
    assert args.write_manual_sample is False


def test_spectrum_representative_is_selected_within_eligibility_stratum() -> None:
    rows = [
        {
            "scan_id": "unlabelled_first",
            "spectrum_sha256": "same",
            "recomputed_crystal_system": "",
            "mapped_cu_ka_10_80_broad_eligible": False,
        },
        {
            "scan_id": "eligible_second",
            "spectrum_sha256": "same",
            "recomputed_crystal_system": "cubic",
            "mapped_cu_ka_10_80_broad_eligible": True,
        },
    ]
    AUDIT.annotate_spectrum_duplicates(rows)
    assert rows[0]["mapped_cu_ka_10_80_broad_unique_eligible"] is False
    assert rows[1]["mapped_cu_ka_10_80_broad_unique_eligible"] is True


def _write_structure_record(path: Path, lattice_length: float) -> None:
    phase = {
        "lattice": [lattice_length, lattice_length, lattice_length, 90, 90, 90],
        "basis": [
            {"symbol": "Na", "x": 0.0, "y": 0.0, "z": 0.0},
            {"symbol": "Cl", "x": 0.5, "y": 0.5, "z": 0.5},
        ],
    }
    path.write_text(json.dumps({"label": {"phases": [phase]}}), encoding="utf-8")


def test_structure_parent_clustering_and_formal_group_exclusion(tmp_path: Path) -> None:
    _write_structure_record(tmp_path / "a.json", 5.64)
    _write_structure_record(tmp_path / "b.json", 5.65)
    rows = []
    for name in ("a.json", "b.json"):
        row = {
            "source_relpath": name,
            "formula_reduced": "NaCl",
            "recomputed_crystal_system": "cubic",
            "crystal_system_stable": True,
            "mapped_cu_ka_10_80_broad_unique_eligible": True,
            "formal_14060_structure_match": False,
            "formal_14060_exact_fingerprint_overlap": False,
            "formal_14060_structure_match_error": "",
        }
        rows.append(row)

    assert AUDIT.annotate_structural_parents(rows, tmp_path)
    assert rows[0]["structural_parent_group"] == rows[1]["structural_parent_group"]
    assert rows[0]["structural_parent_group_size"] == 2
    assert sum(row["mapped_cu_ka_10_80_broad_parent_eligible"] for row in rows) == 1

    rows[1]["formal_14060_structure_match"] = True
    AUDIT.annotate_independent_parent_candidates(rows, formal_overlap_audit_run=True)
    assert all(row["structural_parent_formal_14060_overlap"] for row in rows)
    assert not any(
        row["mapped_cu_ka_10_80_broad_parent_independent_eligible"] for row in rows
    )
