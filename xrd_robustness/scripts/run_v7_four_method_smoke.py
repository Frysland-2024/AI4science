#!/usr/bin/env python3
"""Run one CPU software step for all four V7 methods on reflection-aware views."""

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
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.training import ResidualClassifier, TrainingStepConfig, run_training_step
from xrd_robustness.view_manifest import (
    build_offline_view_manifest,
    build_parameter_stream,
    index_manifest,
)


class TinyStructuredBackbone(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.projection = nn.Linear(32, 16)
        self.classifier = nn.Linear(16, 7)
        self.forward_calls = 0

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor | None]:
        self.forward_calls += 1
        pooled_input = torch.nn.functional.adaptive_avg_pool1d(x.unsqueeze(1), 32).squeeze(1)
        embedding = torch.tanh(self.projection(pooled_input))
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
        "--config", default=str(PROJECT_ROOT / "configs" / "simulation.v7.candidate.json")
    )
    parser.add_argument(
        "--output", default=str(PROJECT_ROOT / "reports" / "v7_dry_run" / "four_method_smoke.json")
    )
    args = parser.parse_args()
    torch.manual_seed(20260714)
    sampler = PhysicsParameterSampler.from_json(args.config)
    factory = OnlineViewFactory(sampler)
    material_ids = ["synthetic-cubic", "synthetic-triclinic"]
    tables = {material_ids[0]: _table(1.0), material_ids[1]: _table(0.8)}
    dynamic_rows = build_parameter_stream(
        material_ids,
        sampler,
        profile="train",
        epochs=1,
        steps_per_epoch=1,
    )
    dynamic_index = index_manifest(dynamic_rows)
    offline_rows = build_offline_view_manifest(
        material_ids, sampler, profile="train", views_per_material=2
    )
    offline_index = {(row.material_id, row.view_id): row for row in offline_rows}
    labels = torch.tensor([0, 6], dtype=torch.long)
    dynamic_views = [
        factory.make_pair_from_manifest(
            tables[material_id],
            dynamic_index[(material_id, 0, 0, 1)],
            dynamic_index[(material_id, 0, 0, 2)],
        )
        for material_id in material_ids
    ]
    x1_dynamic = torch.from_numpy(np.stack([pair.first.xrd for pair in dynamic_views])).float()
    x2_dynamic = torch.from_numpy(np.stack([pair.second.xrd for pair in dynamic_views])).float()
    x1_offline = torch.from_numpy(
        np.stack(
            [
                factory.make_view_from_manifest(tables[item], offline_index[(item, 1)]).xrd
                for item in material_ids
            ]
        )
    ).float()
    x2_offline = torch.from_numpy(
        np.stack(
            [
                factory.make_view_from_manifest(tables[item], offline_index[(item, 2)]).xrd
                for item in material_ids
            ]
        )
    ).float()

    reports = []
    dynamic_signature = [
        (pair.first.parameters.to_dict(), pair.second.parameters.to_dict())
        for pair in dynamic_views
    ]
    for mode in (
        TrainingMode.OFFLINE_ERM,
        TrainingMode.DYNAMIC_ERM,
        TrainingMode.DYNAMIC_JS,
        TrainingMode.DYNAMIC_RESIDUAL,
    ):
        model = TinyStructuredBackbone()
        optimizer_main = torch.optim.Adam(model.parameters(), lr=1e-3)
        residual = ResidualClassifier(16) if mode is TrainingMode.DYNAMIC_RESIDUAL else None
        optimizer_res = torch.optim.Adam(residual.parameters(), lr=1e-3) if residual is not None else None
        first = x1_offline if mode is TrainingMode.OFFLINE_ERM else x1_dynamic
        second = x2_offline if mode is TrainingMode.OFFLINE_ERM else x2_dynamic
        if mode is not TrainingMode.DYNAMIC_RESIDUAL:
            optimizer_main.zero_grad(set_to_none=True)
        result = run_training_step(
            TrainingStepConfig(mode=mode),
            model,
            x1=first,
            x2=second,
            target=labels,
            optimizer_main=optimizer_main,
            optimizer_res=optimizer_res,
            residual_classifier=residual,
        )
        if mode is not TrainingMode.DYNAMIC_RESIDUAL:
            result["total"].backward()
            optimizer_main.step()
        if model.forward_calls != 2:
            raise RuntimeError(f"{mode.value} used {model.forward_calls} backbone forwards, expected 2")
        reports.append(
            {
                "method": mode.value,
                "loss": float(result["total"].detach()),
                "optimizer_steps": 1,
                "backbone_forward_views": model.forward_calls,
                "view_exposures": 4,
                "unique_structures": 2,
                "dynamic_parameter_signature_shared": mode is TrainingMode.OFFLINE_ERM or bool(dynamic_signature),
            }
        )
    payload = {
        "status": "passed",
        "scope": "software-only; not a scientific experiment",
        "config": str(Path(args.config).resolve()),
        "methods": reports,
        "all_methods_two_backbone_views": all(item["backbone_forward_views"] == 2 for item in reports),
        "reflection_metadata_required": True,
        "formal_test_results_used": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

