import math
import json
from pathlib import Path
import unittest

import torch
from torch import nn

from xrd_robustness.online_views import TrainingMode
from xrd_robustness.physics import PhysicsParameters, validate_formal_simulation_config
from xrd_robustness.training import (
    PerturbationDeltaRegressor,
    PerturbationTargetConfig,
    ResidualClassifier,
    TrainingStepConfig,
    pilot_perturbation_delta,
    run_training_step,
    signed_measurement_residual,
)


def _parameters(shift: float, fwhm: float) -> PhysicsParameters:
    return PhysicsParameters(
        delta_2theta_deg=shift,
        fwhm_deg=fwhm,
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=0,
        background_active=False,
        noise_active=False,
    )


class _CountingBackbone(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Linear(5, 8)
        self.classifier = nn.Linear(8, 7)
        self.forward_calls = 0

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor | None]:
        self.forward_calls += 1
        embedding = self.encoder(x)
        return {
            "logits": self.classifier(embedding),
            "pooled_embedding": embedding,
            "main_tokens": embedding.unsqueeze(1),
            "prior_tokens": None,
        }


class PerturbationSupervisionTests(unittest.TestCase):
    def test_pilot_config_is_traceable_and_does_not_use_coin_flip_activation(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "configs"
            / "simulation.v7.perturbation_supervision_pilot.json"
        )
        config = json.loads(path.read_text(encoding="utf-8"))
        validate_formal_simulation_config(
            config,
            train_profile="pilot_train",
            in_range_profile="pilot_in_range",
            ood_profiles=["pilot_ood_shift", "pilot_ood_width", "pilot_ood_joint_extreme"],
        )
        probabilities = {
            value["apply_probability"]
            for profile in config["profiles"].values()
            for value in profile.values()
            if isinstance(value, dict) and "apply_probability" in value
        }
        self.assertEqual(probabilities, {0.0, 1.0})
        self.assertFalse(config["real_experiment_policy"]["parameter_definition_source"])

    def test_pilot_target_is_signed_and_antisymmetric(self):
        first = [_parameters(-0.1, 0.08), _parameters(0.05, 0.16)]
        second = [_parameters(0.1, 0.16), _parameters(-0.05, 0.08)]
        config = PerturbationTargetConfig(
            zero_shift_scale_deg=0.2,
            log_fwhm_scale=1.0,
        )
        forward = pilot_perturbation_delta(first, second, config=config)
        reverse = pilot_perturbation_delta(second, first, config=config)
        torch.testing.assert_close(forward, -reverse)
        torch.testing.assert_close(
            forward,
            torch.tensor([[1.0, math.log(2.0)], [-0.5, -math.log(2.0)]]),
        )

    def test_signed_residual_reverses_with_view_order(self):
        first = torch.tensor([[1.0, 2.0, 3.0]])
        second = torch.tensor([[3.0, 1.0, 2.0]])
        torch.testing.assert_close(
            signed_measurement_residual(first, second),
            -signed_measurement_residual(second, first),
        )

    def test_training_step_uses_two_backbone_forwards_and_updates_both_sides(self):
        torch.manual_seed(19)
        model = _CountingBackbone()
        classifier = ResidualClassifier(8)
        regressor = PerturbationDeltaRegressor(8, output_dim=2)
        optimizer_main = torch.optim.SGD(model.parameters(), lr=0.05)
        optimizer_aux = torch.optim.SGD(
            list(classifier.parameters()) + list(regressor.parameters()), lr=0.05
        )
        model_before = model.encoder.weight.detach().clone()
        regressor_before = regressor.network.weight.detach().clone()
        target = torch.tensor([0, 1, 2, 3])
        result = run_training_step(
            TrainingStepConfig(
                mode=TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL,
                lambda_res=0.1,
                lambda_perturb=1.0,
            ),
            model,
            x1=torch.rand(4, 5),
            x2=torch.rand(4, 5),
            target=target,
            perturbation_delta=torch.tensor(
                [[0.2, 0.1], [-0.1, 0.3], [0.4, -0.2], [-0.3, -0.1]]
            ),
            optimizer_main=optimizer_main,
            optimizer_aux=optimizer_aux,
            residual_classifier=classifier,
            perturbation_regressor=regressor,
        )
        self.assertEqual(model.forward_calls, 2)
        self.assertEqual(result["predicted_perturbation_delta"].shape, (4, 2))
        self.assertFalse(torch.equal(model_before, model.encoder.weight.detach()))
        self.assertFalse(torch.equal(regressor_before, regressor.network.weight.detach()))
        self.assertTrue(torch.isfinite(result["total"]))


if __name__ == "__main__":
    unittest.main()
