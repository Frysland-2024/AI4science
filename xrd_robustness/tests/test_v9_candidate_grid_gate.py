import hashlib
import json
import math
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "v9_candidate_grid_gate.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "audit_v9_candidate_grid_gate.py"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
GOVERNANCE_PATH = PROJECT_ROOT / "configs" / "v9_method_parameter_governance.json"


class V9CandidateGridGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))

    def test_report_and_script_hash_match(self) -> None:
        digest = hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            self.report["input_hashes"]["audit_script"].lower(), digest.lower()
        )
        self.assertEqual(self.report["status"], "pass")
        self.assertTrue(all(self.report["checks"].values()))

    def test_scope_is_rebuilt_train_only_without_checkpoint_or_tuning(self) -> None:
        self.assertTrue(self.report["baseline_rebuilt_from_epoch_zero"])
        self.assertFalse(self.report["checkpoint_recovery_claimed"])
        self.assertFalse(self.report["checkpoint_written"])
        self.assertEqual(
            self.report["training_protocol"]["full_train_structures"], 9842
        )
        self.assertEqual(self.report["training_protocol"]["epochs"], 5)
        self.assertFalse(self.report["candidate_specific_training_performed"])
        self.assertFalse(self.report["validation_used"])
        self.assertFalse(self.report["simulated_test_used"])
        self.assertFalse(self.report["real_xrd_used"])
        self.assertFalse(self.report["seven_run_started"])

    def test_every_candidate_was_directly_measured_in_the_expected_band(self) -> None:
        self.assertFalse(self.report["linear_extrapolation_only"])
        self.assertEqual(
            self.report["measurement_mode"],
            "candidate_specific_weighted_and_combined_objectives_evaluated_by_autograd",
        )
        expected = {
            "lambda_js": [0.3, 3.0, 30.0],
            "lambda_res": [0.2, 2.0, 20.0],
        }
        for parameter, grid in expected.items():
            measurement = self.report["candidate_measurements"][parameter]
            self.assertEqual(measurement["grid"], grid)
            self.assertEqual(measurement["status"], "pass")
            self.assertEqual(
                measurement["observed_band_sequence"],
                ["weak", "material_non_dominant", "dominant"],
            )
            for candidate in measurement["candidates"]:
                self.assertEqual(candidate["status"], "pass")
                self.assertTrue(all(candidate["checks"].values()))
                for metric in candidate["summary"].values():
                    self.assertTrue(all(math.isfinite(value) for value in metric.values()))

    def test_grid_is_frozen_but_tuning_remains_locked(self) -> None:
        gate = self.report["candidate_grid_gate"]
        self.assertTrue(gate["candidate_range_may_be_frozen"])
        self.assertFalse(gate["validation_tuning_authorized"])
        self.assertFalse(gate["seven_run_authorized"])
        self.assertTrue(self.governance["candidate_range_frozen_for_validation"])
        self.assertEqual(
            self.governance["status"], "candidate_range_frozen_for_validation"
        )
        self.assertEqual(
            self.governance["one_revision_policy"]["completed_range_revisions"],
            1,
        )
        self.assertFalse(
            self.governance["tuning_gate"][
                "development_tuning_execution_allowed"
            ]
        )
        self.assertFalse(self.contract["development_tuning"]["execution_enabled"])
        self.assertFalse(
            self.contract["execution_policy"][
                "development_tuning_execution_enabled"
            ]
        )


if __name__ == "__main__":
    unittest.main()
