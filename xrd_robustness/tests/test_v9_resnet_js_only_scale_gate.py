from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_v9_resnet_js_only_scale_gate as gate


class ResNetJsOnlyScaleGateTests(unittest.TestCase):
    def test_registered_grid_and_boundaries_are_fixed(self) -> None:
        payload = json.loads(
            (
                PROJECT_ROOT
                / "configs"
                / "v9_resnet_js_only_scale_gate.preregistered.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(payload["js_scale_probes"], [3.0, 30.0, 60.0])
        self.assertEqual(
            payload["expected_influence_bands"],
            ["weak", "material_non_dominant", "dominant"],
        )
        self.assertTrue(payload["boundaries"]["train_only"])
        self.assertFalse(payload["boundaries"]["four_run_started"])
        self.assertFalse(payload["authorization"]["four_run_tuning_authorized"])
        self.assertFalse(
            payload["authorization"]["residual_v1_reopening_authorized"]
        )

    def test_ratio_band_boundaries(self) -> None:
        self.assertEqual(gate._ratio_band(0.009999), "negligible")
        self.assertEqual(gate._ratio_band(0.01), "weak")
        self.assertEqual(gate._ratio_band(0.1), "material_non_dominant")
        self.assertEqual(gate._ratio_band(1.0), "dominant")

    def test_exact_lambda_60_rescaling(self) -> None:
        source = json.loads(
            (
                PROJECT_ROOT / "reports" / "v9_resnet_candidate_grid_gate.json"
            ).read_text(encoding="utf-8")
        )
        lambda_30 = next(
            item
            for item in source["candidate_measurements"]["lambda_js"][
                "candidates"
            ]
            if float(item["lambda"]) == 30.0
        )
        derived = gate._derive_lambda_60_trace(lambda_30["trace"])
        self.assertEqual(len(derived), len(lambda_30["trace"]))
        for old, new in zip(lambda_30["trace"], derived, strict=True):
            self.assertAlmostEqual(
                new["weighted_auxiliary_backbone_gradient_norm"],
                2.0 * old["weighted_auxiliary_backbone_gradient_norm"],
            )
            self.assertAlmostEqual(
                new["weighted_auxiliary_to_classification_gradient_ratio"],
                2.0
                * old[
                    "weighted_auxiliary_to_classification_gradient_ratio"
                ],
            )
            self.assertEqual(new["lambda"], 60.0)

    def test_audit_passes_without_opening_four_run(self) -> None:
        report = gate.run_audit(
            PROJECT_ROOT
            / "configs"
            / "v9_resnet_js_only_scale_gate.preregistered.json",
            PROJECT_ROOT / "reports" / "v9_resnet_candidate_grid_gate.json",
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            report["observed_influence_bands"],
            ["weak", "material_non_dominant", "dominant"],
        )
        self.assertTrue(report["candidate_range_may_be_frozen"])
        self.assertFalse(report["four_run_started"])
        self.assertFalse(report["four_run_tuning_authorized"])
        self.assertFalse(report["validation_used"])
        self.assertFalse(report["simulated_test_used"])
        self.assertFalse(report["real_xrd_used"])


if __name__ == "__main__":
    unittest.main()
