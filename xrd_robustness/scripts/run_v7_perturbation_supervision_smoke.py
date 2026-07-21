#!/usr/bin/env python3
"""CPU software smoke for the minimal V7 perturbation-supervision Pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import torch
from torch import nn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.online_views import OnlineViewFactory, TrainingMode
from xrd_robustness.physics import PhysicsParameterSampler, validate_formal_simulation_config
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.training import (
    PerturbationDeltaRegressor,
    PerturbationTargetConfig,
    ResidualClassifier,
    TrainingStepConfig,
    pilot_perturbation_delta,
    run_training_step,
)
from xrd_robustness.view_manifest import build_parameter_stream, index_manifest


class TinyStructuredBackbone(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.projection = nn.Linear(32, 16)
        self.classifier = nn.Linear(16, 7)
        self.forward_calls = 0

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor | None]:
        self.forward_calls += 1
        pooled = torch.nn.functional.adaptive_avg_pool1d(x.unsqueeze(1), 32).squeeze(1)
        embedding = torch.tanh(self.projection(pooled))
        return {
            "logits": self.classifier(embedding),
            "pooled_embedding": embedding,
            "main_tokens": embedding.unsqueeze(1),
            "prior_tokens": None,
        }


def _table(scale: float) -> PeakTable:
    return PeakTable(
        positions=np.asarray([20.0, 30.0, 40.0, 50.0]),
        intensities=np.asarray([100.0, 50.0, 70.0, 25.0]) * scale,
        hkls=np.asarray([[1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0]]),
        multiplicities=np.asarray([2, 1, 2, 4]),
        reciprocal_vectors=np.asarray(
            [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
        ),
        reflection_peak_indices=np.asarray([0, 1, 2, 3]),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(
            PROJECT_ROOT / "configs" / "simulation.v7.perturbation_supervision_pilot.json"
        ),
    )
    parser.add_argument(
        "--output",
        default=str(
            PROJECT_ROOT / "reports" / "v7_dry_run" / "perturbation_supervision_smoke.json"
        ),
    )
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_formal_simulation_config(
        config,
        train_profile="pilot_train",
        in_range_profile="pilot_in_range",
        ood_profiles=["pilot_ood_shift", "pilot_ood_width", "pilot_ood_joint_extreme"],
    )
    sampler = PhysicsParameterSampler.from_mapping(config)
    factory = OnlineViewFactory(sampler)
    material_ids = ["synthetic-cubic", "synthetic-triclinic"]
    tables = {material_ids[0]: _table(1.0), material_ids[1]: _table(0.8)}
    rows = build_parameter_stream(
        material_ids,
        sampler,
        profile="pilot_train",
        epochs=1,
        steps_per_epoch=1,
    )
    row_index = index_manifest(rows)
    pairs = [
        factory.make_pair_from_manifest(
            tables[material_id],
            row_index[(material_id, 0, 0, 1)],
            row_index[(material_id, 0, 0, 2)],
        )
        for material_id in material_ids
    ]
    x1 = torch.from_numpy(np.stack([pair.first.xrd for pair in pairs])).float()
    x2 = torch.from_numpy(np.stack([pair.second.xrd for pair in pairs])).float()
    labels = torch.tensor([0, 6], dtype=torch.long)
    target_config = PerturbationTargetConfig()
    perturbation_delta = pilot_perturbation_delta(
        [pair.first.parameters for pair in pairs],
        [pair.second.parameters for pair in pairs],
        config=target_config,
    )

    reports = []
    for mode in (
        TrainingMode.DYNAMIC_ERM,
        TrainingMode.DYNAMIC_JS,
        TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL,
    ):
        torch.manual_seed(20260715)
        model = TinyStructuredBackbone()
        optimizer_main = torch.optim.Adam(model.parameters(), lr=1e-3)
        residual_classifier = None
        perturbation_regressor = None
        optimizer_aux = None
        if mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
            residual_classifier = ResidualClassifier(16)
            perturbation_regressor = PerturbationDeltaRegressor(16, output_dim=2)
            optimizer_aux = torch.optim.Adam(
                list(residual_classifier.parameters())
                + list(perturbation_regressor.parameters()),
                lr=1e-3,
            )
        if mode is not TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
            optimizer_main.zero_grad(set_to_none=True)
        result = run_training_step(
            TrainingStepConfig(mode=mode),
            model,
            x1=x1,
            x2=x2,
            target=labels,
            perturbation_delta=(
                perturbation_delta
                if mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL
                else None
            ),
            optimizer_main=optimizer_main,
            optimizer_aux=optimizer_aux,
            residual_classifier=residual_classifier,
            perturbation_regressor=perturbation_regressor,
        )
        if mode is not TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
            result["total"].backward()
            optimizer_main.step()
        if model.forward_calls != 2:
            raise RuntimeError(f"{mode.value} used {model.forward_calls} backbone forwards")
        reports.append(
            {
                "method": mode.value,
                "loss": float(result["total"]),
                "classification_loss": float(result["classification"]),
                "perturbation_loss": (
                    float(result["perturbation"]) if "perturbation" in result else None
                ),
                "independence_loss": (
                    float(result["independence"]) if "independence" in result else None
                ),
                "backbone_forward_views": model.forward_calls,
            }
        )
    payload = {
        "status": "passed",
        "scope": "software-only; no model-quality or scientific claim",
        "config": str(config_path),
        "pilot_factors": ["delta_2theta_deg", "log_fwhm_deg"],
        "target_direction": "second_minus_first",
        "apply_probability_interpreted_as_prevalence": False,
        "methods": reports,
        "all_methods_two_backbone_views": all(
            report["backbone_forward_views"] == 2 for report in reports
        ),
        "formal_training_started": False,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
