import json
import math
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "v9_loss_gradient_scale_audit.json"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"


class V9LossGradientScaleAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_report_records_requested_diagnostics_for_all_three_phases(self) -> None:
        expected = {
            "raw_L_cls",
            "raw_L_JS",
            "raw_L_res",
            "unweighted_grad_norm_cls",
            "unweighted_grad_norm_JS",
            "unweighted_grad_norm_res",
            "prediction_JS_distance",
            "feature_residual_norm",
            "residual_head_entropy",
        }
        phases = self.report["early_middle_late_diagnostics"]
        self.assertEqual(set(phases), {"early", "middle", "late"})
        for phase in phases.values():
            self.assertEqual(set(phase["requested_diagnostics"]), expected)
            self.assertGreater(phase["steps"], 0)
            for summary in phase["requested_diagnostics"].values():
                self.assertTrue(all(math.isfinite(value) for value in summary.values()))

    def test_probe_competence_uses_pre_update_arriving_batch_predictions(self) -> None:
        assessment = self.report["residual_probe_competence"]
        self.assertIn(
            assessment["status"],
            {"diagnostic_signal_present", "not_demonstrated"},
        )
        self.assertIn("pre-update", assessment["evaluation_scope"])
        self.assertTrue(assessment["not_a_generalization_claim"])
        for phase in self.report["early_middle_late_diagnostics"].values():
            diagnostics = phase["residual_probe_diagnostics"]
            self.assertIn("residual_probe_accuracy_before_update", diagnostics)
            self.assertIn("residual_probe_entropy_after_update", diagnostics)

    def test_classification_learning_stage_is_explicit(self) -> None:
        assessment = self.report["classification_learning_signal"]
        self.assertIn(
            assessment["status"],
            {"diagnostic_signal_present", "not_demonstrated"},
        )
        self.assertTrue(assessment["not_a_formal_training_or_generalization_claim"])
        for phase in self.report["early_middle_late_diagnostics"].values():
            context = phase["trajectory_context_diagnostics"]
            self.assertIn("classification_accuracy", context)
            self.assertIn("prediction_top1_agreement", context)

    def test_inverse_gradient_ratios_do_not_authorize_grid_change(self) -> None:
        gate = self.report["gradient_compensation_interpretation_gate"]
        self.assertEqual(gate["status"], "blocked")
        self.assertFalse(gate["automatic_grid_change_performed"])
        self.assertTrue(gate["registered_grids_unchanged"])
        calibration = self.report["train_only_gradient_calibration"]
        self.assertIn("diagnostic compensation factors", calibration["interpretation"])
        for method in ("lambda_js", "lambda_res"):
            self.assertTrue(
                calibration[method]["compensation_factors_are_not_grid_proposals"]
            )

    def test_historical_audit_did_not_change_grids_or_open_data_locks(self) -> None:
        registered = self.contract["method_parameter_governance"][
            "registered_candidate_grids"
        ]
        self.assertEqual(registered["lambda_js"], [0.3, 3.0, 30.0])
        self.assertEqual(registered["lambda_res"], [0.2, 2.0, 20.0])
        self.assertFalse(
            self.report["gradient_compensation_interpretation_gate"][
                "automatic_grid_change_performed"
            ]
        )
        self.assertFalse(self.report["validation_used"])
        self.assertFalse(self.report["simulated_test_used"])
        self.assertFalse(self.report["real_test_used"])
        self.assertEqual(self.report["formal_training_runs_started"], 0)

    def test_reduction_audit_rules_out_repeated_class_mean(self) -> None:
        reduction = self.report["reduction_audit"]
        self.assertIn("no extra class mean", reduction["js"])
        self.assertIn("no repeated class mean", reduction["residual"])


if __name__ == "__main__":
    unittest.main()
