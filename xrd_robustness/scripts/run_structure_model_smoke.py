#!/usr/bin/env python3
"""Run the structure-to-model software loop without persisting spectrum arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import torch
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.models import PatchTransformerConfig, XRDPatchTransformer
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.training import dynamic_consistency, dynamic_erm, fixed_erm
from xrd_robustness.data_layout import resolve_data_root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    args = parser.parse_args()
    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    if not records_path.exists():
        raise SystemExit(f"Materials Project structure pilot is missing: {records_path}")
    records = [json.loads(line) for line in records_path.read_text(encoding="utf-8").splitlines()]
    selected = []
    for crystal_system in CRYSTAL_SYSTEMS:
        selected.append(next(row for row in records if row["crystal_system"] == crystal_system))

    sampler = PhysicsParameterSampler.from_json(
        PROJECT_ROOT / "configs" / "simulation.v7.smoke.json"
    )
    factory = OnlineViewFactory(sampler)
    fixed_profiles = []
    dynamic_first = []
    dynamic_second = []
    view_audit = []
    for row in selected:
        peaks = load_peak_table(
            data_root / "mp_processed" / "peak_tables_v7_reflection" / f"{row['material_id']}.npz"
        )
        fixed = factory.make_fixed_view_from_peaks(
            peaks,
            material_id=row["material_id"],
            split="train",
            profile="smoke_test",
        )
        pair = factory.make_pair_from_peaks(
            peaks,
            material_id=row["material_id"],
            split="train",
            epoch=1,
            global_step=1,
            profile="smoke_test",
        )
        fixed_profiles.append(fixed.xrd)
        dynamic_first.append(pair.first.xrd)
        dynamic_second.append(pair.second.xrd)
        view_audit.append(
            {
                "material_id": row["material_id"],
                "crystal_system": row["crystal_system"],
                "view_1_seed": pair.first.rng_seed,
                "view_2_seed": pair.second.rng_seed,
                "view_1_sha256": hashlib.sha256(pair.first.xrd.tobytes()).hexdigest(),
                "view_2_sha256": hashlib.sha256(pair.second.xrd.tobytes()).hexdigest(),
            }
        )

    x_fixed = torch.from_numpy(np.stack(fixed_profiles)).float()
    x1 = torch.from_numpy(np.stack(dynamic_first)).float()
    x2 = torch.from_numpy(np.stack(dynamic_second)).float()
    targets = torch.arange(7, dtype=torch.long)
    torch.manual_seed(20260711)
    model = XRDPatchTransformer(PatchTransformerConfig())
    model.eval()

    fixed_result = fixed_erm(model, x_fixed, targets)
    erm_result = dynamic_erm(model, x1, x2, targets)
    consistency_result = dynamic_consistency(
        model,
        x1,
        x2,
        targets,
        consistency_weight=0.1,
    )
    classification_delta = float(
        torch.abs(erm_result["classification"] - consistency_result["classification"])
    )
    consistency_result["total"].backward()
    gradients_present = any(
        parameter.grad is not None and torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    )
    passed = bool(
        x1.shape == (7, 3501)
        and torch.isfinite(x1).all()
        and classification_delta == 0.0
        and gradients_present
    )
    report = {
        "passed": passed,
        "purpose": "software integration smoke only; no spectrum arrays persisted",
        "materials_project_structures": len(selected),
        "one_per_crystal_system": True,
        "peak_tables_loaded": len(selected),
        "model": {
            "name": "1D Patch Transformer",
            "patch_count": model.patch_count,
            "parameter_count": model.parameter_count,
            "output_classes": 7,
            "backward_gradients_present": gradients_present,
        },
        "losses": {
            "fixed_erm": float(fixed_result["total"].detach()),
            "dynamic_erm": float(erm_result["total"].detach()),
            "dynamic_consistency": float(consistency_result["total"].detach()),
            "consistency_term": float(consistency_result["consistency"].detach()),
            "dynamic_classification_delta": classification_delta,
        },
        "dynamic_modes_received_same_tensor_objects": True,
        "views": view_audit,
    }
    output = PROJECT_ROOT / "reports" / "structure_model_smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": passed, "report": str(output)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
