import hashlib
import json
import math
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "v9_learned_state_scale_audit.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "audit_v9_learned_state_scale.py"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
GOVERNANCE_PATH = PROJECT_ROOT / "configs" / "v9_method_parameter_governance.json"


class V9LearnedStateScaleAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))

    def test_report_is_preserved_as_retired_split_evidence(self) -> None:
        digest = hashlib.sha256(SCRIPT_PATH.read_bytes()).hexdigest()
        self.assertNotEqual(
            self.report["input_hashes"]["audit_script"].lower(), digest.lower()
        )
        self.assertEqual(
            self.report["input_hashes"]["split_manifest"].upper(),
            self.governance["candidate_grid_gate_evidence"][
                "previous_retired_split_manifest_sha256"
            ],
        )
        self.assertEqual(self.report["status"], "pass")

    def test_scope_is_full_train_only_and_writes_no_checkpoint(self) -> None:
        protocol = self.report["training_protocol"]
        self.assertEqual(protocol["method"], "Dynamic/Paired ERM classification only")
        self.assertEqual(protocol["backbone"], "PAMPT-B3")
        self.assertEqual(protocol["full_train_structures"], 9842)
        self.assertEqual(protocol["milestones"], [1, 3, 5])
        self.assertFalse(self.report["validation_used"])
        self.assertFalse(self.report["simulated_test_used"])
        self.assertFalse(self.report["real_xrd_used"])
        self.assertFalse(self.report["checkpoint_written"])
        self.assertEqual(self.report["formal_training_runs_started"], 0)
        self.assertEqual(self.report["diagnostic_training_runs_started"], 1)

    def test_probe_calibration_audit_and_scale_subsets_are_disjoint(self) -> None:
        subsets = self.report["diagnostic_subsets"]
        values = {
            name: set(details["material_ids"]) for name, details in subsets.items()
        }
        self.assertEqual(set(values), {"probe_calibration", "probe_audit", "scale_audit"})
        for details in subsets.values():
            self.assertEqual(details["split"], "train")
            self.assertEqual(details["size"], 700)
            self.assertEqual(details["per_class"], 100)
        self.assertFalse(values["probe_calibration"] & values["probe_audit"])
        self.assertFalse(values["probe_calibration"] & values["scale_audit"])
        self.assertFalse(values["probe_audit"] & values["scale_audit"])

    def test_random_state_is_separated_from_learned_state(self) -> None:
        milestones = self.report["milestones"]
        self.assertEqual(
            milestones["1"]["classification_learning_gate"]["status"],
            "not_demonstrated",
        )
        for epoch in ("3", "5"):
            self.assertEqual(
                milestones[epoch]["classification_learning_gate"]["status"],
                "learned_state_demonstrated",
            )
        self.assertEqual(
            self.report["scientific_classification"]["previous_128_step_report"],
            "initialization_or_chance_state_scale_evidence",
        )
        self.assertFalse(
            self.report["scientific_classification"][
                "previous_gradient_balance_centers_valid_for_grid_revision"
            ]
        )

    def test_residual_probe_signal_is_held_out_within_train(self) -> None:
        for epoch in ("3", "5"):
            probe = self.report["milestones"][epoch]["residual_probe_gate"]
            self.assertEqual(probe["status"], "signal_demonstrated")
            self.assertTrue(probe["calibration_and_audit_subsets_are_disjoint"])
            self.assertTrue(probe["features_are_detached_from_backbone"])
            self.assertGreater(probe["audit_accuracy"], probe["descriptive_accuracy_threshold"])
            self.assertGreater(probe["audit_macro_f1"], probe["chance_accuracy"])
            self.assertLess(probe["audit_ce"], math.log(7.0))

    def test_requested_learned_state_metrics_are_finite(self) -> None:
        expected = {
            "classification_ce",
            "prediction_entropy",
            "paired_top1_disagreement",
            "paired_probability_l1_distance",
            "raw_js",
            "feature_residual_l2_norm",
            "classification_backbone_gradient_norm",
            "js_backbone_gradient_norm",
            "residual_backbone_gradient_norm",
            "js_to_classification_backbone_gradient_ratio",
            "residual_to_classification_backbone_gradient_ratio",
        }
        for milestone in self.report["milestones"].values():
            summary = milestone["scale_summary"]
            self.assertTrue(expected <= set(summary))
            for metric in expected:
                self.assertTrue(all(math.isfinite(value) for value in summary[metric].values()))

    def test_historical_report_did_not_change_grid_and_current_authorization_is_separate(self) -> None:
        registered = self.contract["method_parameter_governance"][
            "registered_candidate_grids"
        ]
        self.assertEqual(registered["lambda_js"], [0.3, 3.0, 30.0])
        self.assertEqual(registered["lambda_res"], [0.2, 2.0, 20.0])
        self.assertTrue(self.governance["candidate_range_frozen_for_validation"])
        self.assertTrue(self.governance["current_split_gate_valid"])
        self.assertEqual(
            self.governance["one_revision_policy"]["completed_range_revisions"],
            1,
        )
        self.assertFalse(
            self.governance["tuning_gate"]["development_tuning_execution_allowed"]
        )
        self.assertFalse(
            self.contract["execution_policy"]["development_tuning_execution_enabled"]
        )
        decision = self.report["epoch5_decision"]
        self.assertFalse(decision["automatic_grid_revision_performed"])
        self.assertFalse(decision["validation_tuning_authorized"])
        self.assertFalse(decision["seven_run_started"])
        self.assertTrue(decision["human_confirmation_required"])


if __name__ == "__main__":
    unittest.main()
