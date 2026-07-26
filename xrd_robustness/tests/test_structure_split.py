import unittest

from xrd_robustness.structure_split import assign_parent_structure_splits


class ParentStructureSplitTests(unittest.TestCase):
    def test_stratified_split_is_exact_and_reproducible(self):
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
        self.assertEqual(
            report["split_counts"],
            {"train": 28, "validation": 6, "test": 6},
        )
        self.assertEqual(
            {
                split: sum(row["split"] == split for row in first)
                for split in ("train", "validation", "test")
            },
            {"train": 28, "validation": 6, "test": 6},
        )
        for label in ("cubic", "triclinic"):
            self.assertEqual(
                {
                    split: sum(
                        row["crystal_system"] == label and row["split"] == split
                        for row in first
                    )
                    for split in ("train", "validation", "test")
                },
                {"train": 14, "validation": 3, "test": 3},
            )

    def test_all_material_rows_for_one_parent_share_a_split(self):
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
            previous = parent_splits.setdefault(
                row["parent_structure_id"],
                row["split"],
            )
            self.assertEqual(previous, row["split"])
        self.assertEqual(report["parent_structure_count"], 10)

    def test_conflicting_parent_labels_are_rejected(self):
        records = [
            {
                "material_id": "a",
                "parent_structure_id": "same",
                "crystal_system": "cubic",
            },
            {
                "material_id": "b",
                "parent_structure_id": "same",
                "crystal_system": "triclinic",
            },
        ]
        with self.assertRaisesRegex(ValueError, "conflicting crystal systems"):
            assign_parent_structure_splits(records)


if __name__ == "__main__":
    unittest.main()
