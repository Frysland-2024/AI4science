import unittest

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.view_manifest import (
    FrozenEvaluationManifest,
    build_parameter_stream,
)


def _fixed(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _sampler():
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 11,
            "profiles": {
                "validation": {
                    "severity_level": 0,
                    "background_type": "flat",
                    "delta_2theta_deg": _fixed(0.0),
                    "fwhm_deg": _fixed(0.08),
                    "background_to_peak_ratio": _fixed(0.0),
                    "noise_std_ratio": _fixed(0.0),
                }
            },
        }
    )


class FrozenManifestTests(unittest.TestCase):
    def test_evaluation_manifest_is_hashable_and_indexed(self):
        rows = build_parameter_stream(
            ["mp-1", "mp-2"],
            _sampler(),
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
            _sampler(),
            profile="validation",
            epochs=1,
            steps_per_epoch=1,
            split="train",
        )
        with self.assertRaises(ValueError):
            FrozenEvaluationManifest.from_rows(rows)


if __name__ == "__main__":
    unittest.main()
