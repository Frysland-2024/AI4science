#!/usr/bin/env python
"""Render V9 reference and V11 dynamic views from one CIF.

Example from the repository root::

    python xrd_robustness/scripts/generate_dynamic_pair.py \
      --cif xrd_robustness/data/example.cif \
      --simulation-config xrd_robustness/configs/simulation.v11_tch_pseudo_voigt.json \
      --output xrd_robustness/reports/simulator_v11/example_pair.npz
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pymatgen.io.cif import CifParser
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, simulate_from_peak_table
from xrd_robustness.simulator_v11 import make_peak_table_simulator
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cif", required=True, type=Path)
    parser.add_argument("--simulation-config", required=True, type=Path)
    parser.add_argument("--material-id")
    parser.add_argument("--profile", default="train")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--epoch", type=int, default=0)
    parser.add_argument("--global-step", type=int, default=0)
    parser.add_argument("--output", type=Path, help="optional NPZ output path")
    return parser.parse_args()


def render_pair(
    cif_path: Path,
    simulation_config_path: Path,
    *,
    material_id: str | None = None,
    profile: str = "train",
    seed: int | None = None,
    epoch: int = 0,
    global_step: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    """Read one CIF and render its original V9 spectrum and V11 JS pair."""
    cif_path = cif_path.resolve()
    config = json.loads(simulation_config_path.resolve().read_text(encoding="utf-8"))
    if seed is not None:
        config["run_seed"] = int(seed)
    sampler = PhysicsParameterSampler.from_mapping(config)
    if profile not in sampler.profiles:
        raise ValueError(f"profile {profile!r} is absent from simulation config")

    structures = CifParser(str(cif_path)).parse_structures(primitive=False)
    if not structures:
        raise ValueError(f"CIF contains no structures: {cif_path}")
    structure = structures[0]
    crystal_system = SpacegroupAnalyzer(structure, symprec=0.01).get_crystal_system()
    if crystal_system not in CRYSTAL_SYSTEMS:
        raise ValueError(f"unsupported crystal system in CIF: {crystal_system}")
    resolved_material_id = material_id or cif_path.stem
    grid = SimulationGrid()
    peaks = ideal_peak_table(structure, grid)
    simulator_version = str(config.get("simulator_version", "v9_gaussian"))
    if simulator_version != "v11_tch_pseudo_voigt":
        raise ValueError("this pair demo expects simulator_version=v11_tch_pseudo_voigt")
    factory = OnlineViewFactory(
        sampler,
        grid=grid,
        peak_table_simulator=make_peak_table_simulator(
            simulator_version,
            config.get("line_profile", {}),
        ),
    )
    pair = factory.make_pair_from_peaks(
        peaks,
        material_id=resolved_material_id,
        split="train",
        epoch=epoch,
        global_step=global_step,
        profile=profile,
    )
    replay = factory.make_pair_from_peaks(
        peaks,
        material_id=resolved_material_id,
        split="train",
        epoch=epoch,
        global_step=global_step,
        profile=profile,
    )
    original = simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        pair.first.parameters,
        rng_seed=pair.first.rng_seed,
        grid=grid,
        reflection_table=peaks,
    )
    summary = {
        "cif_path": str(cif_path),
        "cif_sha256": hashlib.sha256(cif_path.read_bytes()).hexdigest(),
        "material_id": resolved_material_id,
        "crystal_system": crystal_system,
        "label_pair": [crystal_system, crystal_system],
        "simulator_version": simulator_version,
        "shape": list(pair.first.xrd.shape),
        "peak_count": int(len(peaks.positions)),
        "view_seeds": [pair.first.rng_seed, pair.second.rng_seed],
        "views_distinct": not np.array_equal(pair.first.xrd, pair.second.xrd),
        "views_replayable": bool(
            np.array_equal(pair.first.xrd, replay.first.xrd)
            and np.array_equal(pair.second.xrd, replay.second.xrd)
        ),
        "view_1_line_profile": pair.first.diagnostics.get("line_profile"),
        "view_2_line_profile": pair.second.diagnostics.get("line_profile"),
    }
    if summary["label_pair"][0] != summary["label_pair"][1]:
        raise AssertionError("the paired views do not share the CIF crystal-system label")
    if not summary["views_distinct"]:
        raise AssertionError("the dynamic view sampler produced identical spectra")
    if not summary["views_replayable"]:
        raise AssertionError("the fixed-seed dynamic pair did not replay exactly")
    return np.asarray(original), pair.first.xrd, pair.second.xrd, summary


def main() -> None:
    args = _parse_args()
    original, first, second, summary = render_pair(
        args.cif,
        args.simulation_config,
        material_id=args.material_id,
        profile=args.profile,
        seed=args.seed,
        epoch=args.epoch,
        global_step=args.global_step,
    )
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            args.output,
            two_theta=SimulationGrid().values.astype(np.float32),
            v9_reference=original,
            v11_view_1=first,
            v11_view_2=second,
        )
        summary["output_path"] = str(args.output.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
