import unittest
import json
from pathlib import Path

import numpy as np

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.perturbation_strategy import (
    IndependentDynamicStrategy,
    PerturbationContext,
    StructuredDynamicStrategy,
    StructuredStrategyNotFrozenError,
    strategy_descriptor,
)
from xrd_robustness.physics import (
    PhysicsParameterSampler,
    validate_formal_simulation_config,
)
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.view_manifest import ViewManifestRow


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _fixed(value, probability=1.0):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": probability,
    }


def _sampler():
    return PhysicsParameterSampler.from_mapping(
        {
            "run_seed": 20260715,
            "profiles": {
                "train": {
                    "severity_level": 1,
                    "background_type": "flat",
                    "delta_2theta_deg": _fixed(0.1, 0.5),
                    "fwhm_deg": _fixed(0.12),
                    "background_to_peak_ratio": _fixed(0.0, 0.0),
                    "noise_std_ratio": _fixed(0.01),
                }
            },
        }
    )


def _fake_renderer(source, parameters, rng_seed):
    return (
        np.asarray([rng_seed % 1000, parameters.fwhm_deg], dtype=np.float64),
        parameters,
        {"source_seen": source == "clean"},
    )


class V8PerturbationStrategyTests(unittest.TestCase):
    def test_independent_adapter_preserves_sampler_draw_exactly(self):
        sampler = _sampler()
        strategy = IndependentDynamicStrategy(sampler, config_hash="abc123")
        context = PerturbationContext(
            material_id="mp-1",
            split="train",
            epoch=2,
            global_step=7,
            view_id=1,
            profile="train",
        )
        expected_parameters, expected_seed = sampler.sample(
            "train",
            epoch=2,
            global_step=7,
            material_id="mp-1",
            view_id=1,
        )
        generated = strategy.generate("clean", context, renderer=_fake_renderer)
        self.assertEqual(generated.parameters, expected_parameters)
        self.assertEqual(generated.rng_seed, expected_seed)
        self.assertEqual(generated.metadata["config_hash"], "abc123")
        self.assertEqual(generated.metadata["strategy_name"], "independent_dynamic")
        self.assertEqual(
            generated.metadata["measurement_state"]["status"],
            "independent_baseline_no_shared_latent_state",
        )
        self.assertEqual(generated.metadata["measurement_state"]["sample_state"], {})
        self.assertEqual(generated.metadata["measurement_state"]["instrument_state"], {})
        self.assertEqual(generated.metadata["measurement_state"]["acquisition_state"], {})
        self.assertEqual(
            generated.metadata["perturbation_parameters"],
            expected_parameters.to_dict(),
        )
        self.assertIn("generated_at_utc", generated.metadata)
        descriptor = strategy_descriptor(strategy)
        self.assertEqual(descriptor["status"], "v8_independent_baseline_ready")
        self.assertFalse(descriptor["shared_measurement_state"])
        self.assertEqual(len(descriptor["operator_names"]), 5)
        metadata_schema = json.loads(
            (PROJECT_ROOT / "configs" / "perturbation_metadata.v8.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(set(metadata_schema["required"]).issubset(generated.metadata))

    def test_online_factory_records_metadata_without_changing_view_seed(self):
        sampler = _sampler()
        strategy = IndependentDynamicStrategy(sampler, config_hash="bound-config")

        def simulator(structure, params, *, rng_seed, grid):
            return np.asarray([rng_seed % 1000, params.fwhm_deg], dtype=np.float64)

        factory = OnlineViewFactory(sampler, simulator=simulator, strategy=strategy)
        view = factory.make_pair(
            object(),
            material_id="mp-2",
            split="validation",
            epoch=99,
            global_step=99,
            profile="train",
        ).first
        expected, expected_seed = sampler.sample(
            "train", epoch=0, global_step=0, material_id="mp-2", view_id=1
        )
        self.assertEqual(view.parameters, expected)
        self.assertEqual(view.rng_seed, expected_seed)
        self.assertEqual(view.strategy_name, "independent_dynamic")
        self.assertEqual(view.metadata["config_hash"], "bound-config")
        self.assertEqual(view.metadata["split"], "validation")
        self.assertEqual(view.metadata["epoch"], 0)
        self.assertEqual(view.metadata["global_step"], 0)

    def test_structured_strategy_is_a_fail_closed_placeholder(self):
        strategy = StructuredDynamicStrategy(config_hash="placeholder")
        descriptor = strategy_descriptor(strategy)
        self.assertFalse(descriptor["formal_use_allowed"])
        self.assertEqual(descriptor["status"], "not_frozen")
        self.assertFalse(
            descriptor["measurement_state"]["sample_state"]["frozen"]
        )
        context = PerturbationContext(
            material_id="mp-3",
            split="train",
            epoch=0,
            global_step=0,
            view_id=1,
            profile="train",
        )
        with self.assertRaises(StructuredStrategyNotFrozenError):
            strategy.generate("clean", context, renderer=_fake_renderer)

    def test_manifest_replay_gets_v8_metadata_without_changing_manifest(self):
        sampler = _sampler()
        strategy = IndependentDynamicStrategy(sampler, config_hash="manifest-config")
        parameters, seed = sampler.sample(
            "train", epoch=0, global_step=0, material_id="mp-4", view_id=1
        )
        row = ViewManifestRow(
            split="test",
            epoch=0,
            global_step=0,
            material_id="mp-4",
            view_id=1,
            simulation_seed=seed,
            parameters=parameters.to_dict(),
        )
        manifest_id_before = row.manifest_id
        view = OnlineViewFactory(sampler, strategy=strategy).make_view_from_manifest(
            PeakTable(
                positions=np.asarray([20.0, 40.0]),
                intensities=np.asarray([100.0, 50.0]),
            ),
            row,
        )
        self.assertEqual(row.manifest_id, manifest_id_before)
        self.assertEqual(view.metadata["strategy_name"], "independent_dynamic")
        self.assertEqual(view.metadata["config_hash"], "manifest-config")
        self.assertEqual(
            view.metadata["profile"], "legacy_manifest_profile_not_recorded"
        )
        self.assertEqual(view.metadata["perturbation_parameters"], parameters.to_dict())

    def test_formal_gate_rejects_unfrozen_structured_config_first(self):
        with self.assertRaisesRegex(ValueError, "not frozen for formal experiments"):
            validate_formal_simulation_config(
                {
                    "purpose": "V8 structured dynamic experiment",
                    "perturbation_strategy": {
                        "name": "structured_dynamic",
                        "status": "not_frozen",
                        "formal_use_allowed": False,
                    },
                },
                train_profile="train",
                in_range_profile="in_range",
                ood_profiles=["ood"],
            )

    def test_placeholder_config_explicitly_contains_no_frozen_joint_model(self):
        placeholder = json.loads(
            (
                PROJECT_ROOT
                / "configs"
                / "simulation.v8.structured.placeholder.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(placeholder["schema_version"], "v8.0-interface")
        self.assertEqual(
            placeholder["perturbation_strategy"]["name"], "structured_dynamic"
        )
        self.assertFalse(placeholder["perturbation_strategy"]["formal_use_allowed"])
        self.assertFalse(placeholder["joint_distribution"]["frozen"])
        self.assertFalse(placeholder["generation_order"]["frozen"])
        self.assertNotIn("profiles", placeholder)


if __name__ == "__main__":
    unittest.main()
