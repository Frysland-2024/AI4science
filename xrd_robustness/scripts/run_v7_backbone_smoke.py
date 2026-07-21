#!/usr/bin/env python3
"""Run a B0-B3 forward/backward smoke using the current seven-system pilot."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.training import dynamic_erm


def main() -> int:
    records_path = PROJECT_ROOT / "data" / "mp_processed" / "structure_records.jsonl"
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    selected = [next(row for row in records if row["crystal_system"] == system) for system in CRYSTAL_SYSTEMS]
    sampler = PhysicsParameterSampler.from_json(PROJECT_ROOT / "configs" / "simulation.v7.smoke.json")
    factory = OnlineViewFactory(sampler)
    views = []
    for row in selected:
        peaks = load_peak_table(PROJECT_ROOT / "data" / "mp_processed" / "peak_tables_v7_reflection" / f"{row['material_id']}.npz")
        pair = factory.make_pair_from_peaks(
            peaks,
            material_id=row["material_id"],
            split="train",
            epoch=1,
            global_step=1,
            profile="smoke_test",
        )
        views.append((pair.first.xrd, pair.second.xrd))
    x1 = torch.from_numpy(np.stack([item[0] for item in views])).float()
    x2 = torch.from_numpy(np.stack([item[1] for item in views])).float()
    labels = torch.arange(len(selected), dtype=torch.long)
    report = {"purpose": "V7 backbone software smoke only", "variants": {}, "passed": True}
    for variant in ("b0", "b1", "b2", "b3"):
        torch.manual_seed(20260711)
        model = PAMPT(PAMPTConfig(variant=variant))
        result = dynamic_erm(model, x1, x2, labels)
        result["total"].backward()
        gradients_present = all(
            parameter.grad is not None and torch.isfinite(parameter.grad).all()
            for parameter in model.parameters()
            if parameter.requires_grad
        )
        output = model(x1)
        variant_report = {
            "passed": bool(
                output["logits"].shape == (len(selected), 7)
                and output["pooled_embedding"].shape[0] == len(selected)
                and torch.isfinite(output["logits"]).all()
                and gradients_present
            ),
            "patch_count": model.patch_count,
            "parameter_count": model.parameter_count,
            "main_token_shape": list(output["main_tokens"].shape),
            "prior_token_shape": None if output["prior_tokens"] is None else list(output["prior_tokens"].shape),
            "backward_gradients_present": gradients_present,
        }
        report["variants"][variant] = variant_report
        report["passed"] = report["passed"] and variant_report["passed"]
    output_path = PROJECT_ROOT / "reports" / "v7_backbone_smoke.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "report": str(output_path)}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
