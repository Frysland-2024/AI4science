import unittest

from xrd_robustness.formal_14060 import (
    FORMAL_CLASS_ORDER,
    assign_extra_evaluation_splits,
    merge_formal_and_gate_records,
)


def _row(material_id, fingerprint, crystal_system, split="train"):
    return {
        "material_id": material_id,
        "structure_fingerprint": fingerprint,
        "crystal_system": crystal_system,
        "split": split,
        "is_stable": True,
    }


class Formal14060Tests(unittest.TestCase):
    def test_extra_splits_are_deterministic_class_aware_and_balanced(self):
        sizes = {
            "cubic": 12,
            "hexagonal": 9,
            "tetragonal": 9,
            "orthorhombic": 16,
            "trigonal": 2,
            "monoclinic": 12,
            "triclinic": 0,
        }
        rows = []
        for class_name in FORMAL_CLASS_ORDER:
            rows.extend(
                _row(f"{class_name}-{index}", f"fp-{class_name}-{index}", class_name)
                for index in range(sizes[class_name])
            )
        first = assign_extra_evaluation_splits(rows, seed=17)
        second = assign_extra_evaluation_splits(rows, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(list(first.values()).count("validation"), 30)
        self.assertEqual(list(first.values()).count("test"), 30)
        self.assertNotIn("train", first.values())

    def test_merge_preserves_formal_rows_and_adds_only_new_fingerprints(self):
        formal = [
            _row("formal-a", "fp-a", "cubic", "train"),
            _row("overlap", "fp-overlap", "triclinic", "test"),
        ]
        gate = [
            _row("overlap", "fp-overlap", "triclinic", "train"),
            _row("extra-a", "fp-extra-a", "cubic", "train"),
            _row("extra-b", "fp-extra-b", "hexagonal", "test"),
        ]
        merged, report = merge_formal_and_gate_records(formal, gate, split_seed=17)
        by_id = {row["material_id"]: row for row in merged}
        self.assertEqual(report["overlap_count"], 1)
        self.assertEqual(report["extra_count"], 2)
        self.assertEqual(by_id["formal-a"]["split"], "train")
        self.assertEqual(by_id["overlap"]["split"], "test")
        self.assertIn(by_id["extra-a"]["split"], {"validation", "test"})
        self.assertIn(by_id["extra-b"]["split"], {"validation", "test"})
        self.assertEqual(by_id["extra-a"]["selection_tier"], "stable")
        self.assertEqual(by_id["extra-b"]["selection_tier"], "stable")

    def test_merge_rejects_extra_fingerprint_already_in_formal(self):
        formal = [_row("formal-a", "shared", "cubic")]
        gate = [
            _row("extra-a", "shared", "cubic"),
            _row("extra-b", "other", "hexagonal"),
        ]
        with self.assertRaisesRegex(ValueError, "duplicates formal fingerprint"):
            merge_formal_and_gate_records(formal, gate)


if __name__ == "__main__":
    unittest.main()
