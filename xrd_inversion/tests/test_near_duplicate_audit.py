from __future__ import annotations

from pymatgen.analysis.structure_matcher import ElementComparator, StructureMatcher
from pymatgen.core import Lattice, Structure

from xrd_inversion.near_duplicate_audit import (
    AuditParent,
    build_cross_split_proxy_groups,
    canonical_split_edge,
    classify_pair,
    enumerate_cross_split_pairs,
    proxy_key,
    reduce_structures_once,
)


def parent(material_id: str, split: str, formula: str = "NaCl") -> AuditParent:
    structure = Structure(
        Lattice.cubic(5.6),
        [formula[:-2] if formula in {"NaCl", "KBr"} else "Na", formula[-2:]],
        [[0, 0, 0], [0.5, 0.5, 0.5]],
    )
    key = proxy_key(formula, 123, len(structure))
    return AuditParent(
        material_id=material_id,
        split=split,
        formula=formula,
        fingerprint=f"fingerprint-{material_id}",
        anonymized_formula=key[0],
        space_group=key[1],
        nsites=key[2],
        structure=structure,
    )


def test_proxy_group_pair_enumeration_is_cross_split_and_exhaustive():
    parents = [
        parent("a", "train"),
        parent("b", "train"),
        parent("c", "validation"),
        parent("d", "test"),
    ]
    groups = build_cross_split_proxy_groups(parents)
    pairs = enumerate_cross_split_pairs(groups)
    assert len(groups) == 1
    assert len(pairs) == 5
    assert all(left.split != right.split for _, left, right in pairs)


def test_anonymous_matching_is_distinct_from_same_species_matching():
    nacl = parent("nacl", "train", "NaCl").structure
    kbr = parent("kbr", "test", "KBr").structure
    anonymous = StructureMatcher()
    same_species = StructureMatcher(comparator=ElementComparator())
    assert anonymous.fit_anonymous(nacl, kbr)
    assert not same_species.fit(nacl, kbr)


def test_classification_preserves_high_recall_sensitivity_band():
    assert (
        classify_pair(high_recall=True, default_anonymous=False, same_species=False)
        == "anonymous_prototype_high_recall_only"
    )
    assert (
        classify_pair(high_recall=True, default_anonymous=True, same_species=True)
        == "same_species_near_duplicate"
    )
    assert canonical_split_edge("test", "train") == "train-test"


def test_cached_reduction_preserves_public_match_result():
    left = parent("left", "train", "NaCl")
    right = parent("right", "test", "KBr")
    matcher = StructureMatcher()
    reduced, errors = reduce_structures_once([left, right], matcher)
    assert errors == {}
    assert matcher.fit_anonymous(left.structure, right.structure)
    assert matcher.fit_anonymous(
        reduced[left.material_id],
        reduced[right.material_id],
        skip_structure_reduction=True,
    )
