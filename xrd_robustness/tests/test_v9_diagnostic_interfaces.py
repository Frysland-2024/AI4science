from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from xrd_robustness.evaluation.metrics import representation_diagnostics, residual_diagnostics
from xrd_robustness.evaluation.real_xrd import audit_real_xrd_contract


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class V9DiagnosticInterfaceTests(unittest.TestCase):
    def test_representation_and_residual_diagnostics(self) -> None:
        features = np.asarray([[1.0, 0.0], [0.8, 0.4], [0.0, 1.0], [0.4, 0.8]])
        labels = [0, 0, 1, 1]
        result = representation_diagnostics(features, labels=labels)
        self.assertGreater(result["feature_effective_rank"], 1.0)
        self.assertGreater(result["feature_class_separation_ratio"], 0.0)
        residual = residual_diagnostics(features, labels=labels)
        self.assertIn("residual_mean_variance", residual)

    def test_real_test_contract_stays_disabled_and_preprocessing_matches_loader(self) -> None:
        result = audit_real_xrd_contract(
            PROJECT_ROOT / "configs" / "real_test.v9.method_transfer.template.json"
        )
        self.assertEqual(result["status"], "locked_ready_for_future_manifest")
        self.assertFalse(result["model_loaded"])
        self.assertFalse(result["real_test_used"])
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
