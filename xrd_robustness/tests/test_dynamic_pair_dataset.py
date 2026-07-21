import unittest

import numpy as np

from xrd_robustness.dynamic_pair_dataset import (
    DynamicPairDataset,
    DynamicStructureSample,
)
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulation_interfaces import PeakTable


def _uniform(min_value, max_value):
    return {
        "distribution": "uniform",
        "min_value": min_value,
        "max_value": max_value,
        "apply_probability": 1.0,
    }


def _fixed(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _factory():
    sampler = PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 20260713,
            "profiles": {
                "train": {
                    "severity_level": 1,
                    "background_type": "flat",
                    "delta_2theta_deg": _uniform(-0.1, 0.1),
                    "fwhm_deg": _uniform(0.08, 0.16),
                    "background_to_peak_ratio": _fixed(0.0),
                    "noise_std_ratio": _uniform(0.0, 0.02),
                }
            },
        }
    )
    return OnlineViewFactory(sampler)


def _samples():
    return [
        DynamicStructureSample(
            material_id=f"mp-{index}",
            label=index,
            peak_table=PeakTable(
                positions=np.asarray([20.0 + index, 40.0]),
                intensities=np.asarray([100.0, 50.0]),
            ),
        )
        for index in range(2)
    ]


class DynamicPairDatasetTests(unittest.TestCase):
    def test_structure_sample_can_be_built_through_peak_calculator_contract(self):
        class Calculator:
            def calculate(self, structure):
                self.seen = structure
                return PeakTable(np.asarray([30.0]), np.asarray([100.0]))

        calculator = Calculator()
        structure = object()
        sample = DynamicStructureSample.from_structure(
            material_id="mp-structure",
            label=3,
            structure=structure,
            calculator=calculator,
        )
        self.assertIs(calculator.seen, structure)
        self.assertEqual(sample.material_id, "mp-structure")
        self.assertEqual(sample.label, 3)

    def test_two_mp_samples_produce_replayable_paired_views(self):
        dataset = DynamicPairDataset(_samples(), _factory(), profile="train")
        first = dataset[0]
        replay = dataset[0]

        self.assertEqual(len(dataset), 2)
        self.assertEqual(first.material_id, "mp-0")
        self.assertEqual(first.y, 0)
        self.assertNotEqual(first.view_seed1, first.view_seed2)
        self.assertNotEqual(first.params1, first.params2)
        np.testing.assert_array_equal(first.x1, replay.x1)
        np.testing.assert_array_equal(first.x2, replay.x2)
        self.assertEqual(first.pair_seed, replay.pair_seed)

    def test_train_context_changes_pair_but_validation_context_is_frozen(self):
        training = DynamicPairDataset(_samples(), _factory(), profile="train", split="train")
        before = training[0]
        training.set_context(epoch=1, global_step=4)
        after = training[0]
        self.assertNotEqual(before.pair_seed, after.pair_seed)
        self.assertFalse(np.array_equal(before.x1, after.x1))

        validation = DynamicPairDataset(
            _samples(), _factory(), profile="train", split="validation"
        )
        frozen = validation[0]
        validation.set_context(epoch=99, global_step=999)
        replay = validation[0]
        np.testing.assert_array_equal(frozen.x1, replay.x1)
        np.testing.assert_array_equal(frozen.x2, replay.x2)
        self.assertEqual(frozen.pair_seed, replay.pair_seed)


if __name__ == "__main__":
    unittest.main()
