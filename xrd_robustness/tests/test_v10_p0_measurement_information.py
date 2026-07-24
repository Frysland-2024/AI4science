from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_v10_p0_measurement_information import (  # noqa: E402
    _classification_probe,
    _gate_decision,
    _normalized_strength,
    _pooled_absolute_spectrum_difference,
    _regression_probe,
)


class V10P0MeasurementInformationUtilityTest(unittest.TestCase):
    def test_pooled_absolute_difference_preserves_sample_order(self) -> None:
        first = np.zeros((2, 8), dtype=np.float32)
        second = np.asarray(
            [[0, 0, 1, 1, 2, 2, 3, 3], [4, 4, 3, 3, 2, 2, 1, 1]],
            dtype=np.float32,
        )
        pooled = _pooled_absolute_spectrum_difference(first, second, bins=4)
        np.testing.assert_allclose(
            pooled,
            np.asarray([[0, 1, 2, 3], [4, 3, 2, 1]], dtype=np.float32),
        )

    def test_normalized_strength_endpoints(self) -> None:
        self.assertAlmostEqual(
            _normalized_strength("shift", {"delta_2theta_deg": -0.5}), 1.0
        )
        self.assertAlmostEqual(
            _normalized_strength("broadening", {"fwhm_deg": 0.2}), 0.0
        )
        self.assertAlmostEqual(
            _normalized_strength(
                "background", {"background_to_peak_ratio": 0.05}
            ),
            1.0,
        )
        self.assertAlmostEqual(
            _normalized_strength("noise", {"poisson_count_scale": 100.0}), 1.0
        )
        self.assertAlmostEqual(
            _normalized_strength("texture", {"march_parameter": 0.5}), 1.0
        )

    def test_grouped_linear_classification_detects_signal(self) -> None:
        generator = np.random.default_rng(7)
        train_groups = np.repeat(np.arange(20), 3)
        test_groups = np.repeat(np.arange(20, 40), 3)
        train_y = np.tile(np.arange(3), 20)
        test_y = np.tile(np.arange(3), 20)
        centers = np.eye(3, dtype=np.float64)
        train_x = centers[train_y] + generator.normal(0.0, 0.01, (60, 3))
        test_x = centers[test_y] + generator.normal(0.0, 0.01, (60, 3))
        result = _classification_probe(
            train_x,
            train_y,
            test_x,
            test_y,
            classes=3,
            permutations=50,
            seed=11,
            train_groups=train_groups,
            test_groups=test_groups,
            group_constant_labels=False,
        )
        self.assertEqual(result["status"], "signal_demonstrated")
        self.assertGreater(result["accuracy"], 0.95)
        self.assertEqual(result["audit_sampling_units"], 20)

    def test_ridge_regression_detects_monotonic_signal(self) -> None:
        train_y = np.linspace(0.0, 1.0, 40)
        test_y = np.linspace(0.025, 0.975, 40)
        train_x = np.stack([train_y, train_y**2], axis=1)
        test_x = np.stack([test_y, test_y**2], axis=1)
        result = _regression_probe(
            train_x,
            train_y,
            test_x,
            test_y,
            permutations=50,
            seed=13,
        )
        self.assertEqual(result["status"], "signal_demonstrated")
        self.assertGreater(result["audit_r2"], 0.8)

    def test_gate_requires_measurement_and_crystal_signals(self) -> None:
        passed = _gate_decision(
            raw_family_signal=True,
            residual_family_signal=True,
            strength_pass_count=3,
            crystal_leakage_signal=True,
        )
        self.assertEqual(passed["v10_premise_gate"], "PASS")
        held = _gate_decision(
            raw_family_signal=True,
            residual_family_signal=False,
            strength_pass_count=0,
            crystal_leakage_signal=True,
        )
        self.assertEqual(held["v10_premise_gate"], "HOLD")
        blocked = _gate_decision(
            raw_family_signal=False,
            residual_family_signal=False,
            strength_pass_count=0,
            crystal_leakage_signal=False,
        )
        self.assertEqual(blocked["v10_premise_gate"], "BLOCK")


if __name__ == "__main__":
    unittest.main()
