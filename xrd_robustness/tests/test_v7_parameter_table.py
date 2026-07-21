import csv
import hashlib
import json
from pathlib import Path
import unittest

from xrd_robustness.physics import PARAMETER_UNITS, parameter_registry_rows


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class V7ParameterTableTests(unittest.TestCase):
    def test_report_table_matches_v7_candidate_config(self):
        config_path = PROJECT_ROOT / "configs" / "simulation.v7.candidate.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest().upper()
        expected = parameter_registry_rows(
            config,
            source_config="configs/simulation.v7.candidate.json",
            config_sha256=config_sha256,
        )
        with (PROJECT_ROOT / "reports" / "v7_active_parameter_table.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            actual = list(csv.DictReader(handle))

        self.assertEqual(len(actual), len(config["profiles"]) * len(PARAMETER_UNITS))
        self.assertEqual(
            [(row["profile"], row["parameter"]) for row in actual],
            [(row["profile"], row["parameter"]) for row in expected],
        )
        for actual_row, expected_row in zip(actual, expected, strict=True):
            for key, expected_value in expected_row.items():
                self.assertEqual(actual_row[key], str(expected_value))


if __name__ == "__main__":
    unittest.main()
