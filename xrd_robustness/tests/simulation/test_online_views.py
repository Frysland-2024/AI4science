import unittest

import numpy as np

from xrd_robustness.online_views import OnlineViewFactory, TrainingMode
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.view_manifest import (
    FrozenEvaluationManifest,
    build_parameter_stream,
)


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


def _manifest_fixed(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _manifest_sampler():
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 11,
            "profiles": {
                "validation": {
                    "severity_level": 0,
                    "background_type": "flat",
                    "delta_2theta_deg": _manifest_fixed(0.0),
                    "fwhm_deg": _manifest_fixed(0.08),
                    "background_to_peak_ratio": _manifest_fixed(0.0),
                    "noise_std_ratio": _manifest_fixed(0.0),
                }
            },
        }
    )


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

    def test_only_public_dynamic_modes_are_exposed(self):
        self.assertEqual(
            {mode.value for mode in TrainingMode},
            {"dynamic_erm", "dynamic_js"},
        )


class FrozenManifestTests(unittest.TestCase):
    def test_evaluation_manifest_is_hashable_and_indexed(self):
        rows = build_parameter_stream(
            ["mp-1", "mp-2"],
            _manifest_sampler(),
            profile="validation",
            epochs=1,
            steps_per_epoch=1,
            split="validation",
        )
        manifest = FrozenEvaluationManifest.from_rows(rows)
        replay = FrozenEvaluationManifest.from_rows(rows)
        self.assertEqual(manifest.manifest_hash, replay.manifest_hash)
        self.assertEqual(len(manifest.index()), 4)

    def test_training_rows_cannot_be_mislabeled_as_frozen_evaluation(self):
        rows = build_parameter_stream(
            ["mp-1"],
            _manifest_sampler(),
            profile="validation",
            epochs=1,
            steps_per_epoch=1,
            split="train",
        )
        with self.assertRaises(ValueError):
            FrozenEvaluationManifest.from_rows(rows)


if __name__ == "__main__":
    unittest.main()
