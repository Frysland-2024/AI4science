from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "audit_formal_split_identity_overlap.py"
)
SPEC = importlib.util.spec_from_file_location("split_identity_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_separates_parent_isolation_from_formula_overlap() -> None:
    structures = [
        {"material_id": "a", "structure_fingerprint": "pa", "formula": "AB2"},
        {"material_id": "b", "structure_fingerprint": "pb", "formula": "AB2"},
        {"material_id": "c", "structure_fingerprint": "pc", "formula": "C"},
    ]
    split = [
        {"material_id": "a", "parent_structure_id": "pa", "split": "train"},
        {"material_id": "b", "parent_structure_id": "pb", "split": "test"},
        {"material_id": "c", "parent_structure_id": "pc", "split": "validation"},
    ]

    report = audit.audit_identity_overlap(structures, split)

    assert report["status"] == "pass"
    assert report["exact_parent_structure_disjoint"] is True
    assert report["cross_split_parent_structure_count"] == 0
    assert report["exact_formula_disjoint"] is False
    assert report["cross_split_exact_formula_count"] == 1
    assert report["cross_split_exact_formula_material_count"] == 2
    assert report["scope"]["strict_chemical_family_or_prototype_ood"] is False


def test_rejects_parent_crossing_splits() -> None:
    structures = [
        {"material_id": "a", "structure_fingerprint": "same", "formula": "A"},
        {"material_id": "b", "structure_fingerprint": "same", "formula": "A"},
    ]
    split = [
        {"material_id": "a", "parent_structure_id": "same", "split": "train"},
        {"material_id": "b", "parent_structure_id": "same", "split": "test"},
    ]

    report = audit.audit_identity_overlap(structures, split)
    assert report["status"] == "fail_parent_leakage"
    assert report["cross_split_parent_structure_count"] == 1


def test_rejects_mismatched_parent_fingerprint() -> None:
    structures = [
        {"material_id": "a", "structure_fingerprint": "pa", "formula": "A"}
    ]
    split = [
        {"material_id": "a", "parent_structure_id": "wrong", "split": "train"}
    ]

    with pytest.raises(audit.SplitIdentityAuditError, match="fingerprint mismatch"):
        audit.audit_identity_overlap(structures, split)
