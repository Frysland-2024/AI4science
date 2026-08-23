import unittest

from xrd_robustness.structure_data import (
    FORBIDDEN_SPECTRUM_FIELDS,
    PERSISTED_STRUCTURE_FIELDS,
    assign_structure_splits,
    crystal_system_from_space_group,
    CRYSTAL_SYSTEMS,
    select_nested_structure_records,
    validate_no_split_leakage,
    validate_persisted_structure_record,
)


def _record(index: int, crystal_system: str = "cubic") -> dict:
    return {
        "material_id": f"mp-{index}",
        "formula": "Si",
        "original_structure": {"sites": []},
        "standardized_structure": {"sites": []},
        "space_group_mp": 225,
        "space_group_recomputed": 225,
        "crystal_system": crystal_system,
        "nsites": 2,
        "is_stable": True,
        "energy_above_hull": 0.0,
        "structure_fingerprint": f"fingerprint-{index}",
        "split": "train",
    }


class StructureDataTests(unittest.TestCase):
    def test_formal_schema_contains_no_spectrum(self):
        self.assertFalse(FORBIDDEN_SPECTRUM_FIELDS.intersection(PERSISTED_STRUCTURE_FIELDS))
        validate_persisted_structure_record(_record(1))

    def test_spectrum_field_is_rejected(self):
        row = _record(1)
        row["xrd_reference"] = [0.0]
        with self.assertRaises(ValueError):
            validate_persisted_structure_record(row)

    def test_structure_splits_are_deterministic_and_disjoint(self):
        rows = [_record(i) for i in range(20)]
        first = assign_structure_splits(rows, seed=17)
        second = assign_structure_splits(rows, seed=17)
        self.assertEqual(first, second)
        validate_no_split_leakage(first)

    def test_duplicate_fingerprint_is_rejected_before_split(self):
        rows = [_record(1), _record(2)]
        rows[1]["structure_fingerprint"] = rows[0]["structure_fingerprint"]
        with self.assertRaises(ValueError):
            assign_structure_splits(rows)

    def test_material_id_crossing_splits_is_rejected(self):
        rows = [_record(1), _record(2)]
        rows[1]["material_id"] = rows[0]["material_id"]
        rows[1]["split"] = "test"
        with self.assertRaises(ValueError):
            validate_no_split_leakage(rows)

    def test_structure_fingerprint_crossing_splits_is_rejected(self):
        rows = [_record(1), _record(2)]
        rows[1]["structure_fingerprint"] = rows[0]["structure_fingerprint"]
        rows[1]["split"] = "validation"
        with self.assertRaises(ValueError):
            validate_no_split_leakage(rows)

    def test_crystal_system_boundaries(self):
        self.assertEqual(crystal_system_from_space_group(1), "triclinic")
        self.assertEqual(crystal_system_from_space_group(194), "hexagonal")
        self.assertEqual(crystal_system_from_space_group(230), "cubic")

    def test_nested_dataset_tier_selection(self):
        rows = []
        for system in CRYSTAL_SYSTEMS:
            for index in range(20):
                row = _record(index, system)
                row["material_id"] = f"{system}-{index:02d}"
                rows.append(row)
        selected = select_nested_structure_records(rows, dataset_size=140)
        self.assertEqual(len(selected), 140)
        counts = {system: sum(row["crystal_system"] == system for row in selected) for system in CRYSTAL_SYSTEMS}
        self.assertEqual(counts, {system: 20 for system in CRYSTAL_SYSTEMS})
        with self.assertRaises(ValueError):
            select_nested_structure_records(rows, dataset_size=3500)


if __name__ == "__main__":
    unittest.main()
