import unittest

import numpy as np

from xrd_robustness.online_views import OnlineViewFactory, TrainingMode, training_objective
from xrd_robustness.physics import PhysicsParameterSampler


def _sampler():
    fixed = lambda value: {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 5,
            "profiles": {
                "test": {
                    "severity_level": 1,
                    "background_type": "flat",
                    "delta_2theta_deg": fixed(0.0),
                    "fwhm_deg": fixed(0.08),
                    "background_to_peak_ratio": fixed(0.0),
                    "noise_std_ratio": fixed(0.01),
                }
            },
        }
    )


def _fake_simulator(structure, params, *, rng_seed, grid):
    return np.asarray([rng_seed % 1000, params.fwhm_deg], dtype=np.float64)


class OnlineViewTests(unittest.TestCase):
    def setUp(self):
        self.factory = OnlineViewFactory(_sampler(), simulator=_fake_simulator)

    def test_train_pair_changes_with_epoch_and_step(self):
        first = self.factory.make_pair(
            object(), material_id="mp-1", split="train", epoch=1, global_step=10, profile="test"
        )
        second = self.factory.make_pair(
            object(), material_id="mp-1", split="train", epoch=2, global_step=10, profile="test"
        )
        self.assertNotEqual(first.first.rng_seed, second.first.rng_seed)
        self.assertNotEqual(first.first.rng_seed, first.second.rng_seed)

    def test_validation_pair_is_frozen(self):
        first = self.factory.make_pair(
            object(), material_id="mp-1", split="validation", epoch=1, global_step=10, profile="test"
        )
        second = self.factory.make_pair(
            object(), material_id="mp-1", split="validation", epoch=99, global_step=999, profile="test"
        )
        np.testing.assert_array_equal(first.first.xrd, second.first.xrd)

    def test_fixed_view_is_constant(self):
        first = self.factory.make_fixed_view(
            object(), material_id="mp-1", split="train", profile="test"
        )
        second = self.factory.make_fixed_view(
            object(), material_id="mp-1", split="train", profile="test"
        )
        np.testing.assert_array_equal(first.xrd, second.xrd)

    def test_dynamic_consistency_only_adds_consistency_loss(self):
        logits_1 = np.asarray([[2.0, 0.0]])
        logits_2 = np.asarray([[0.5, 1.0]])
        erm = training_objective(
            TrainingMode.DYNAMIC_ERM, logits_1, [0], logits_second=logits_2
        )
        consistent = training_objective(
            TrainingMode.DYNAMIC_CONSISTENCY,
            logits_1,
            [0],
            logits_second=logits_2,
            consistency_weight=0.4,
        )
        self.assertEqual(erm["classification"], consistent["classification"])
        self.assertAlmostEqual(
            consistent["total"],
            erm["total"] + 0.4 * consistent["consistency"],
        )
        self.assertNotIn("consistency_only", {mode.value for mode in TrainingMode})


if __name__ == "__main__":
    unittest.main()
