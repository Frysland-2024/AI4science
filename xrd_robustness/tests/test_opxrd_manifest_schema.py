"""
Tests for opXRD manifest schema validation.
"""
import csv
import json
import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class TestManifestSchema(unittest.TestCase):
    """Test the metadata manifest CSV schema."""

    REQUIRED_COLUMNS = [
        "scan_id", "contributor", "source_file",
        "two_theta_count", "intensity_count",
        "is_simulated", "num_phases",
        "chemical_composition", "space_group_number", "space_group_symbol",
        "institution",
    ]

    OPTIONAL_COLUMNS = [
        "file_sha256", "file_size_bytes",
        "two_theta_min", "two_theta_max", "two_theta_monotonic",
        "intensity_nonzero_fraction",
        "lattice_params",
        "crystallite_size_nm", "temp_K", "primary_wavelength",
        "contributor_name", "original_file_format", "measurement_date",
        "tags", "xrdpattern_version",
        "label_raw", "metadata_raw",
        "parse_error", "quality_warnings",
    ]

    def test_required_columns_present(self):
        """Test that a valid manifest has all required columns."""
        # Create a minimal valid manifest
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow({k: "" for k in self.REQUIRED_COLUMNS})
            path = f.name

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames
                for col in self.REQUIRED_COLUMNS:
                    self.assertIn(col, columns, f"Missing required column: {col}")
        finally:
            os.unlink(path)

    def test_scan_id_format(self):
        """Test scan_id follows contributor/filename format."""
        valid_ids = [
            "CNRS/pattern_0.json",
            "EMPA/pattern_1.json",
            "HKUST/HKUST-A/pattern_0.json",
            "LBNL/subdir/pattern_100.json",
        ]
        for sid in valid_ids:
            parts = sid.split("/")
            self.assertGreaterEqual(len(parts), 2, f"Invalid scan_id format: {sid}")
            self.assertTrue(parts[-1].endswith(".json"),
                            f"scan_id should end with .json: {sid}")

    def test_empty_manifest_schema(self):
        """Test that an empty manifest (header only) has valid schema."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS)
            writer.writeheader()
            path = f.name

        try:
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.assertIsNotNone(reader.fieldnames)
        finally:
            os.unlink(path)

    def test_is_simulated_values(self):
        """Test is_simulated field accepts valid values."""
        valid_values = ["True", "False", "", "None", None]
        for val in valid_values:
            if val is None:
                parsed = None
            elif val == "":
                parsed = None
            else:
                parsed = val.strip().lower() == "true"
            self.assertIn(parsed, [True, False, None])

    def test_space_group_number_type(self):
        """Test space_group_number parsing."""
        test_cases = [
            ("99", 99),
            ("225", 225),
            ("1", 1),
            ("", None),
            ("none", None),  # should fail gracefully
            ("invalid", None),
        ]
        for input_val, expected in test_cases:
            try:
                result = int(float(input_val))
            except (ValueError, TypeError):
                result = None
            self.assertEqual(result, expected,
                             f"Parsing '{input_val}' gave {result}, expected {expected}")


class TestFixtureFile(unittest.TestCase):
    """Test that fixture files exist and are valid."""

    def test_minimal_fixture_exists(self):
        """Test minimal fixture file exists."""
        fixture_path = os.path.join(FIXTURES_DIR, "opxrd_metadata_minimal.json")
        if os.path.exists(fixture_path):
            with open(fixture_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("records", data, "Fixture should have 'records' key")
            self.assertIsInstance(data["records"], list, "Records should be a list")
            if data["records"]:
                r = data["records"][0]
                self.assertIn("scan_id", r)
                self.assertIn("contributor", r)
                self.assertIn("two_theta_count", r)
        else:
            self.skipTest("Fixture file not yet created (created during actual run)")

    def test_minimal_fixture_schema(self):
        """Test that fixture records match manifest schema."""
        records = [
            {
                "scan_id": "CNRS/pattern_0.json",
                "contributor": "CNRS",
                "source_file": "pattern_0.json",
                "two_theta_count": 5000,
                "intensity_count": 5000,
                "two_theta_min": 5.0,
                "two_theta_max": 60.0,
                "two_theta_monotonic": True,
                "intensity_nonzero_fraction": 0.95,
                "is_simulated": False,
                "num_phases": 1,
                "chemical_composition": "BaTiO3",
                "space_group_number": 99,
                "space_group_symbol": "P4mm",
                "lattice_params": "(3.99, 3.99, 4.03, 90, 90, 90)",
                "crystallite_size_nm": None,
                "temp_K": 298,
                "primary_wavelength": "1.5406",
                "institution": "CNRS /PSL University",
                "contributor_name": "F-X Coudert",
                "original_file_format": "pdCIF (.cif)",
                "measurement_date": "2020-03-26",
                "tags": "",
                "xrdpattern_version": "0.9.7",
                "label_raw": "{}",
                "metadata_raw": "{}",
                "parse_error": None,
                "quality_warnings": None,
            }
        ]
        required = ["scan_id", "contributor", "two_theta_count"]
        for r in records:
            for key in required:
                self.assertIsNotNone(r.get(key), f"Missing required field: {key}")


if __name__ == "__main__":
    unittest.main()
