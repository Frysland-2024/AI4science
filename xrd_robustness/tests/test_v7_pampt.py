import unittest
from pathlib import Path
import tempfile

import numpy as np
import torch
from torch import nn

from xrd_robustness.evaluation import RealXRDConfig, classification_metrics, load_real_xrd, paired_view_metrics, residual_diagnostics, robustness_auc
from xrd_robustness.experiment import assert_model_fingerprint, model_fingerprint
from xrd_robustness.models import DerivativeChannels, PAMPT, PAMPTConfig
from xrd_robustness.physics import PhysicsParameterSampler, validate_formal_simulation_config
from xrd_robustness.training import (
    ResidualClassifier,
    dynamic_residual,
    residual_confusion_kl,
    symmetric_measurement_residual,
)
from xrd_robustness.view_manifest import build_offline_view_manifest, build_parameter_stream, load_manifest, save_manifest


class V7PAMPTTests(unittest.TestCase):
    def test_derivatives_are_deterministic_and_finite(self):
        module = DerivativeChannels()
        x = torch.arange(16, dtype=torch.float32).view(1, -1)
        first = module(x)
        second = module(x)
        torch.testing.assert_close(first, second)
        self.assertTrue(torch.isfinite(first).all())

    def test_local_encoders_do_not_use_pooling(self):
        model = PAMPT(PAMPTConfig(variant="b3", input_length=65, embed_dim=32, num_heads=4, branch_channels=8, fusion_dim=16, dropout=0.0))
        forbidden = (nn.MaxPool1d, nn.AvgPool1d, nn.AdaptiveAvgPool1d, nn.AdaptiveMaxPool1d)
        self.assertFalse(any(isinstance(module, forbidden) for module in model.modules()))

    def test_residual_is_symmetric(self):
        first = torch.rand(4, 8)
        second = torch.rand(4, 8)
        torch.testing.assert_close(
            symmetric_measurement_residual(first, second),
            symmetric_measurement_residual(second, first),
        )

    def test_residual_confusion_is_zero_for_uniform(self):
        logits = torch.zeros(3, 7)
        self.assertAlmostEqual(float(residual_confusion_kl(logits)), 0.0, places=6)

    def test_residual_step_freezes_head_and_updates_main(self):
        torch.manual_seed(3)
        model = PAMPT(PAMPTConfig(variant="b0", input_length=32, embed_dim=16, depth=1, num_heads=4, dropout=0.0))
        residual_head = ResidualClassifier(16, depth=1)
        main_optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        residual_optimizer = torch.optim.AdamW(residual_head.parameters(), lr=1e-3)
        before = [parameter.detach().clone() for parameter in residual_head.parameters()]
        result = dynamic_residual(
            model,
            residual_head,
            torch.rand(4, 32),
            torch.rand(4, 32),
            torch.tensor([0, 1, 2, 3]),
            optimizer_main=main_optimizer,
            optimizer_res=residual_optimizer,
            lambda_res=0.1,
        )
        self.assertIn("residual", result)
        self.assertTrue(any(not torch.equal(old, new) for old, new in zip(before, residual_head.parameters(), strict=True)))

    def test_metrics_interfaces(self):
        probabilities = torch.tensor([[0.8, 0.2], [0.3, 0.7]]).numpy()
        metrics = classification_metrics([0, 1], [0, 1], probabilities=probabilities, num_classes=2)
        self.assertEqual(metrics["accuracy"], 1.0)
        paired = paired_view_metrics(probabilities, probabilities, [0, 1])
        self.assertEqual(paired["prediction_agreement"], 1.0)
        self.assertAlmostEqual(robustness_auc([0, 1, 2], [1, 0.8, 0.6]), 0.8)
        self.assertGreater(residual_diagnostics(np.ones((2, 4)))['residual_norm'], 0.0)

    def test_manifest_round_trip_and_real_xrd_grid(self):
        sampler = PhysicsParameterSampler.from_mapping(
            {
                "run_seed": 3,
                "profiles": {
                    "test": {
                        "severity_level": 0,
                        "background_type": "flat",
                        "delta_2theta_deg": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                        "fwhm_deg": {"distribution": "fixed", "min_value": 0.08, "max_value": 0.08},
                        "background_to_peak_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                        "noise_std_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
                    }
                },
            }
        )
        rows = build_parameter_stream(["mp-1"], sampler, profile="test", epochs=1, steps_per_epoch=1)
        offline_rows = build_offline_view_manifest(["mp-1"], sampler, profile="test", views_per_material=4)
        self.assertEqual([row.view_id for row in offline_rows], [1, 2, 3, 4])
        with self.assertRaises(ValueError):
            validate_formal_simulation_config(
                {"purpose": "software smoke test", "profiles": {"test": {}}},
                train_profile="test",
                in_range_profile="test",
                ood_profiles=["test"],
            )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "views.jsonl"
            save_manifest(rows, path)
            self.assertEqual(load_manifest(path)[0].manifest_id, rows[0].manifest_id)
            source = Path(directory) / "real.txt"
            source.write_text("10 0\n20 2\n30 0\n", encoding="utf-8")
            spectrum, provenance = load_real_xrd(source, config=RealXRDConfig(two_theta_min=10, two_theta_max=30, step=10))
            self.assertEqual(spectrum.shape, (3,))
            self.assertEqual(provenance["raw_points"], 3)

    def test_formal_config_requires_parameter_sources_and_rejects_device_binding(self):
        profile = {
            "severity_level": 1,
            "background_type": "flat",
            "delta_2theta_deg": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
            "fwhm_deg": {"distribution": "fixed", "min_value": 0.08, "max_value": 0.08},
            "background_to_peak_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
            "noise_std_ratio": {"distribution": "fixed", "min_value": 0.0, "max_value": 0.0},
        }
        config = {
            "run_seed": 7,
            "purpose": "literature-anchored formal test",
            "profiles": {"train": profile, "in_range": profile, "ood": profile},
        }
        with self.assertRaisesRegex(ValueError, "parameter_evidence"):
            validate_formal_simulation_config(
                config,
                train_profile="train",
                in_range_profile="in_range",
                ood_profiles=["ood"],
            )
        config["parameter_evidence"] = {
            name: {"code_source": "tests/test_v7_pampt.py"}
            for name in (
                "background_type",
                "delta_2theta_deg",
                "fwhm_deg",
                "background_to_peak_ratio",
                "noise_std_ratio",
            )
        }
        validate_formal_simulation_config(
            config,
            train_profile="train",
            in_range_profile="in_range",
            ood_profiles=["ood"],
        )
        config["instrument_model"] = "forbidden-device"
        with self.assertRaisesRegex(ValueError, "instrument-agnostic"):
            validate_formal_simulation_config(
                config,
                train_profile="train",
                in_range_profile="in_range",
                ood_profiles=["ood"],
            )

    def test_model_fingerprint_is_enforced(self):
        model = PAMPT(PAMPTConfig(variant="b0", input_length=32, embed_dim=16, depth=1, num_heads=4, dropout=0.0))
        fingerprint = model_fingerprint(model, model.config)
        self.assertEqual(assert_model_fingerprint(model, model.config, fingerprint), fingerprint)


if __name__ == "__main__":
    unittest.main()
