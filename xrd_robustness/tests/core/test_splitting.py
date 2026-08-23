import sys
import unittest
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.splitting import (
    build_structure_split_manifest,
    validate_split_manifest,
)
from xrd_robustness.structure_split import assign_parent_structure_splits


class StructureSplitTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        for label in range(1, 8):
            for index in range(20):
                structure_id = f"class-{label}-structure-{index:02d}"
                for view in range(3):
                    self.records.append(
                        {
                            "structure_id": structure_id,
                            "crystal_system": label,
                            "view": view,
                        }
                    )

    def test_views_are_collapsed_to_one_manifest_row(self):
        manifest = build_structure_split_manifest(self.records)
        self.assertEqual(len(manifest), 140)
        self.assertTrue(all(row["view_count"] == 3 for row in manifest))

    def test_split_is_deterministic_and_disjoint(self):
        first = build_structure_split_manifest(self.records, seed=17)
        second = build_structure_split_manifest(self.records, seed=17)
        self.assertEqual(first, second)
        validate_split_manifest(first)
        self.assertEqual(len({row["structure_id"] for row in first}), len(first))

    def test_each_class_uses_70_10_20_allocation(self):
        manifest = build_structure_split_manifest(self.records)
        for label in range(1, 8):
            counts = Counter(
                row["split"] for row in manifest if row["crystal_system"] == label
            )
            self.assertEqual(counts, {"train": 14, "validation": 2, "test": 4})

    def test_conflicting_labels_are_rejected(self):
        records = [
            {"structure_id": "same", "crystal_system": 1},
            {"structure_id": "same", "crystal_system": 2},
        ]
        with self.assertRaises(ValueError):
            build_structure_split_manifest(records)


class ParentStructureSplitTests(unittest.TestCase):
    """Parent-identity checks merged from the retired standalone module."""

    def test_parent_split_is_exact_and_reproducible(self):
        records = [
            {
                "material_id": f"{label}-{index}",
                "structure_fingerprint": f"fp-{label}-{index}",
                "crystal_system": label,
            }
            for label in ("cubic", "triclinic")
            for index in range(20)
        ]
        first, report = assign_parent_structure_splits(records, seed=17)
        second, _ = assign_parent_structure_splits(records, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(report["split_counts"], {"train": 28, "validation": 6, "test": 6})

    def test_materials_for_one_parent_share_a_split(self):
        records = [
            {
                "material_id": f"m-{index}",
                "parent_structure_id": f"parent-{index // 2}",
                "crystal_system": "cubic",
            }
            for index in range(20)
        ]
        rows, report = assign_parent_structure_splits(records, seed=23)
        parent_splits = {}
        for row in rows:
            previous = parent_splits.setdefault(row["parent_structure_id"], row["split"])
            self.assertEqual(previous, row["split"])
        self.assertEqual(report["parent_structure_count"], 10)

    def test_conflicting_parent_labels_are_rejected(self):
        records = [
            {"material_id": "a", "parent_structure_id": "same", "crystal_system": "cubic"},
            {"material_id": "b", "parent_structure_id": "same", "crystal_system": "triclinic"},
        ]
        with self.assertRaisesRegex(ValueError, "conflicting crystal systems"):
            assign_parent_structure_splits(records)


if __name__ == "__main__":
    unittest.main()
