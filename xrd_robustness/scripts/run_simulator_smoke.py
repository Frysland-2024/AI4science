#!/usr/bin/env python3
"""Run a five-structure simulator gate without persisting any spectrum arrays."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from pymatgen.core import Lattice, Structure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulator import SimulationGrid, simulate_structure


def smoke_structures() -> list[tuple[str, Structure]]:
    return [
        ("smoke-si", Structure(Lattice.cubic(5.43), ["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]])),
        ("smoke-nacl", Structure(Lattice.cubic(5.64), ["Na", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])),
        ("smoke-cscl", Structure(Lattice.cubic(4.12), ["Cs", "Cl"], [[0, 0, 0], [0.5, 0.5, 0.5]])),
        ("smoke-mg", Structure(Lattice.hexagonal(3.21, 5.21), ["Mg", "Mg"], [[0, 0, 0], [1 / 3, 2 / 3, 0.5]])),
        ("smoke-tio2", Structure(Lattice.tetragonal(4.59, 2.96), ["Ti", "O", "O"], [[0, 0, 0], [0.3, 0.3, 0], [0.7, 0.7, 0]])),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "simulation.v7.smoke.json"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "simulator_smoke.json"),
    )
    args = parser.parse_args()

    sampler = PhysicsParameterSampler.from_json(args.config)
    grid = SimulationGrid()
    records = []
    passed = True
    for material_id, structure in smoke_structures():
        params, seed = sampler.sample(
            "smoke_test",
            epoch=0,
            global_step=0,
            material_id=material_id,
            view_id=0,
        )
        first = simulate_structure(structure, params, rng_seed=seed, grid=grid)
        second = simulate_structure(structure, params, rng_seed=seed, grid=grid)
        reproducible = bool(np.array_equal(first, second))
        valid = bool(
            first.shape == grid.values.shape
            and np.isfinite(first).all()
            and np.all(first >= 0)
            and np.isclose(first.max(), 1.0)
        )
        passed = passed and reproducible and valid
        records.append(
            {
                "material_id": material_id,
                "profile_sha256": hashlib.sha256(first.tobytes()).hexdigest(),
                "points": int(first.size),
                "reproducible": reproducible,
                "valid": valid,
                "simulation_seed": seed,
                "parameters": params.to_dict(),
            }
        )

    report = {
        "passed": passed,
        "purpose": "simulator smoke test only; no spectrum arrays persisted",
        "grid": {
            "two_theta_min": grid.two_theta_min,
            "two_theta_max": grid.two_theta_max,
            "step": grid.step,
            "points": len(grid.values),
        },
        "structures": records,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"passed": passed, "structures": len(records), "report": str(output)}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
