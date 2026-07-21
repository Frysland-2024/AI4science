import unittest

from xrd_robustness.family_split import assign_family_aware_splits


class FamilyAwareSplitTests(unittest.TestCase):
    def test_whole_families_are_assigned_with_exact_targets(self):
        records = []
        family_ids = {}
        for label in ("cubic", "triclinic"):
            for index in range(20):
                material_id = f"{label}-{index}"
                records.append(
                    {
                        "material_id": material_id,
                        "structure_fingerprint": f"fp-{material_id}",
                        "crystal_system": label,
                    }
                )
                family_ids[material_id] = (
                    f"family-{label}-pair-{index // 2}"
                    if index < 8
                    else f"family-{label}-single-{index}"
                )

        rows, report = assign_family_aware_splits(
            records,
            family_ids=family_ids,
            seed=17,
            split_targets={"train": 28, "validation": 6, "test": 6},
        )
        self.assertEqual(report["split_counts"], {"train": 28, "validation": 6, "test": 6})
        family_splits = {}
        for row in rows:
            previous = family_splits.setdefault(row["family_id"], row["split"])
            self.assertEqual(previous, row["split"])
        self.assertEqual(
            {split: sum(row["split"] == split for row in rows) for split in ("train", "validation", "test")},
            {"train": 28, "validation": 6, "test": 6},
        )

    def test_duplicate_fingerprints_are_rejected(self):
        records = [
            {"material_id": "a", "structure_fingerprint": "same", "crystal_system": "cubic"},
            {"material_id": "b", "structure_fingerprint": "same", "crystal_system": "cubic"},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate structure_fingerprint"):
            assign_family_aware_splits(
                records,
                family_ids={"a": "fa", "b": "fb"},
                split_targets={"train": 0, "validation": 1, "test": 1},
            )


if __name__ == "__main__":
    unittest.main()
