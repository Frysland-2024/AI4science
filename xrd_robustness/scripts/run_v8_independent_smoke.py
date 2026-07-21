#!/usr/bin/env python3
"""Software-only smoke for the V8 Independent Dynamic ERM algorithm."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import torch
from torch import nn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.v8_independent import IndependentDynamicERM


def _peak_tables() -> list[tuple[str, PeakTable, int]]:
    common = {
        "hkls": np.asarray([[1, 0, 0], [2, 0, 0], [0, 1, 0], [1, 1, 0]]),
        "multiplicities": np.asarray([2, 1, 2, 4]),
        "reciprocal_vectors": np.asarray(
            [[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
        ),
        "reflection_peak_indices": np.asarray([0, 1, 2, 3]),
    }
    return [
        (
            "smoke-peaks-a",
            PeakTable(
                positions=np.asarray([20.0, 30.0, 40.0, 50.0]),
                intensities=np.asarray([100.0, 45.0, 60.0, 30.0]),
                **common,
            ),
            0,
        ),
        (
            "smoke-peaks-b",
            PeakTable(
                positions=np.asarray([24.0, 36.0, 48.0, 62.0]),
                intensities=np.asarray([70.0, 100.0, 35.0, 50.0]),
                **common,
            ),
            1,
        ),
    ]


def main() -> int:
    contract_path = PROJECT_ROOT / "configs" / "algorithm.v8.independent_dynamic_erm.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    source_path = PROJECT_ROOT / contract["marginal_profile_source"]["path"]
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
    if source_hash != contract["marginal_profile_source"]["sha256"]:
        raise SystemExit("marginal profile source hash does not match the V8 algorithm contract")
    simulation_config = json.loads(source_path.read_text(encoding="utf-8"))
    sampler = PhysicsParameterSampler.from_mapping(simulation_config)
    algorithm = IndependentDynamicERM(
        sampler,
        simulation_config_hash=source_hash,
        marginal_profile_source=(
            f"{contract['marginal_profile_source']['path']}"
            f"#{contract['marginal_profile_source']['profile']}"
        ),
    )
    factory = algorithm.build_view_factory()

    first_views: list[np.ndarray] = []
    second_views: list[np.ndarray] = []
    labels: list[int] = []
    records = []
    passed = True
    for index, (material_id, peaks, label) in enumerate(_peak_tables()):
        pair = factory.make_pair_from_peaks(
            peaks,
            material_id=material_id,
            split="train",
            epoch=0,
            global_step=index,
            profile=contract["marginal_profile_source"]["profile"],
        )
        views = (pair.first, pair.second)
        valid = all(
            view.xrd.ndim == 1
            and np.isfinite(view.xrd).all()
            and np.all(view.xrd >= 0)
            and np.isclose(view.xrd.max(), 1.0)
            and view.measurement_state["sample_state"] == {}
            and view.measurement_state["instrument_state"] == {}
            and view.measurement_state["acquisition_state"] == {}
            for view in views
        )
        distinct_seeds = pair.first.rng_seed != pair.second.rng_seed
        passed = passed and valid and distinct_seeds
        first_views.append(pair.first.xrd)
        second_views.append(pair.second.xrd)
        labels.append(label)
        records.append(
            {
                "material_id": material_id,
                "valid": valid,
                "distinct_view_seeds": distinct_seeds,
                "view_1_active": list(pair.first.parameters.active_perturbation_names),
                "view_2_active": list(pair.second.parameters.active_perturbation_names),
                "view_1_seed": pair.first.rng_seed,
                "view_2_seed": pair.second.rng_seed,
            }
        )

    x1 = torch.from_numpy(np.stack(first_views)).float()
    x2 = torch.from_numpy(np.stack(second_views)).float()
    target = torch.tensor(labels, dtype=torch.long)
    model = nn.Linear(x1.shape[1], 7)
    result = algorithm.objective(model, x1, x2, target)
    result["total"].backward()
    finite_loss = bool(torch.isfinite(result["total"]).item())
    finite_gradient = bool(torch.isfinite(model.weight.grad).all().item())
    passed = passed and finite_loss and finite_gradient and float(result["consistency"]) == 0.0

    report = {
        "passed": passed,
        "purpose": "software-only V8 Independent Dynamic ERM smoke; not a Pilot or scientific result",
        "algorithm": algorithm.descriptor(),
        "contract": str(contract_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "contract_status": contract["status"],
        "formal_training_allowed": contract["formal_training_allowed"],
        "marginal_profile_source_sha256": source_hash,
        "structures": records,
        "training_step": {
            "finite_loss": finite_loss,
            "finite_gradient": finite_gradient,
            "classification": float(result["classification"].detach()),
            "consistency": float(result["consistency"].detach()),
        },
    }
    output = PROJECT_ROOT / "reports" / "v8_independent_dynamic_erm_smoke.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": passed, "report": str(output)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
