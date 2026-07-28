from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_v9_resnet_residual_stability as stability


class ResNetResidualStabilityTests(unittest.TestCase):
    def test_preregistered_seeds_and_milestones_are_fixed(self) -> None:
        self.assertEqual(stability.STABILITY_SEEDS, (20260722, 20260723, 20260724))
        self.assertEqual(stability.MILESTONES, (3, 5, 10))
        self.assertEqual(stability.TRAIN_EPOCHS, 10)

    def test_preregistration_preserves_train_only_boundary(self) -> None:
        path = PROJECT_ROOT / "configs" / "v9_resnet_residual_stability.preregistered.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["seeds"], list(stability.STABILITY_SEEDS))
        self.assertEqual(payload["milestones"], list(stability.MILESTONES))
        self.assertTrue(payload["boundaries"]["seven_run_forbidden"])
        self.assertFalse(payload["boundaries"]["validation_used"])


if __name__ == "__main__":
    unittest.main()
