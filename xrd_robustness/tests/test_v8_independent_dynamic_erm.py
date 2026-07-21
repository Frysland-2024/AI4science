import hashlib
import json
from pathlib import Path
import unittest

import numpy as np
import torch
from torch import nn

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.v8_independent import IndependentDynamicERM


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _fixed(value: float) -> dict[str, float | str]:
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _all_five_sampler() -> PhysicsParameterSampler:
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 20260715,
            "profiles": {
                "train": {
                    "severity_level": 1,
                    "background_type": "flat",
                    "delta_2theta_deg": _fixed(0.2),
                    "fwhm_deg": _fixed(0.2),
                    "background_to_peak_ratio": _fixed(0.02),
                    "noise_std_ratio": _fixed(0.01),
                    "preferred_orientation": {
                        "enabled": True,
                        "model": "march_dollase",
                        "distribution": "fixed",
                        "min_value": 0.8,
                        "max_value": 0.8,
                        "apply_probability": 1.0,
                    },
                }
            },
        }
    )


def _fake_simulator(source, parameters, *, rng_seed, grid):
    return np.asarray(
        [rng_seed % 997, parameters.delta_2theta_deg, parameters.fwhm_deg],
        dtype=np.float64,
    )


class V8IndependentDynamicERMTests(unittest.TestCase):
    def test_all_five_operators_can_be_active_without_cross_operator_rejection(self):
        sampler = _all_five_sampler()
        parameters, _ = sampler.sample(
            "train",
            epoch=0,
            global_step=0,
            material_id="mp-all-five",
            view_id=1,
        )
        self.assertEqual(parameters.active_perturbation_count, 5)
        self.assertEqual(
            set(parameters.active_perturbation_names),
            {
                "zero_shift",
                "peak_broadening",
                "preferred_orientation",
                "background",
                "noise",
            },
        )

    def test_algorithm_binds_online_pair_generation_and_plain_erm(self):
        algorithm = IndependentDynamicERM(
            _all_five_sampler(),
            simulation_config_hash="abc123",
            marginal_profile_source="configs/simulation.v7.candidate.json#train",
        )
        factory = algorithm.build_view_factory(simulator=_fake_simulator)
        pair = factory.make_pair(
            object(),
            material_id="mp-1",
            split="train",
            epoch=1,
            global_step=2,
            profile="train",
        )
        self.assertNotEqual(pair.first.rng_seed, pair.second.rng_seed)
        self.assertEqual(pair.first.measurement_state["sample_state"], {})
        self.assertEqual(pair.first.measurement_state["instrument_state"], {})
        self.assertEqual(pair.first.measurement_state["acquisition_state"], {})

        model = nn.Linear(3, 7)
        x1 = torch.tensor(np.stack([pair.first.xrd, pair.first.xrd])).float()
        x2 = torch.tensor(np.stack([pair.second.xrd, pair.second.xrd])).float()
        target = torch.tensor([0, 1])
        result = algorithm.objective(model, x1, x2, target)
        result["total"].backward()
        self.assertTrue(torch.isfinite(result["total"]))
        self.assertEqual(float(result["consistency"]), 0.0)
        self.assertIsNotNone(model.weight.grad)

    def test_machine_readable_contract_matches_source_hash_and_algorithm(self):
        contract = json.loads(
            (
                PROJECT_ROOT
                / "configs"
                / "algorithm.v8.independent_dynamic_erm.json"
            ).read_text(encoding="utf-8")
        )
        source = PROJECT_ROOT / contract["marginal_profile_source"]["path"]
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        self.assertEqual(source_hash, contract["marginal_profile_source"]["sha256"])

        simulation_config = json.loads(source.read_text(encoding="utf-8"))
        algorithm = IndependentDynamicERM(
            PhysicsParameterSampler.from_mapping(simulation_config),
            simulation_config_hash=source_hash,
            marginal_profile_source=(
                f"{contract['marginal_profile_source']['path']}"
                f"#{contract['marginal_profile_source']['profile']}"
            ),
        )
        descriptor = algorithm.descriptor()
        self.assertEqual(descriptor["algorithm_name"], contract["algorithm_name"])
        self.assertEqual(descriptor["software_status"], contract["status"])
        self.assertEqual(
            descriptor["formal_training_allowed"],
            contract["formal_training_allowed"],
        )
        self.assertEqual(descriptor["training_mode"], contract["training_mode"])
        self.assertEqual(
            descriptor["operator_names"],
            contract["perturbation_strategy"]["operator_names"],
        )
        self.assertFalse(descriptor["shared_measurement_state"])
        self.assertEqual(
            descriptor["sampling_distribution"],
            contract["perturbation_strategy"]["sampling_distribution"],
        )


if __name__ == "__main__":
    unittest.main()
