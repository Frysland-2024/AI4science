"""Verify that make_view_from_manifest (quality_gate=False) is bit-exact
with the online make_pair_from_peaks path for the same (material_id, epoch,
global_step, view_id, profile). This is the correctness premise for moving
the pairing-ablation training renderer into prefetch workers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("E:/AI4science/xrd_robustness")
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.view_manifest import build_parameter_row  # noqa: E402

SIMULATION_CONFIG = ROOT / "configs/simulation.method_transfer.frozen.json"
PEAK_ROOT = ROOT / "data/formal_14060/mp_processed/peak_tables_v7_reflection"

# A few train materials (from split manifest, split == train).
MATERIAL_IDS = ["mp-555488", "mp-1077925", "mp-31054", "mp-1212496"]
RUN_SEED = 20260711
EPOCHS_TO_CHECK = [1, 7, 13]
GLOBAL_STEPS_TO_CHECK = [0, 3, 42]


def load_peaks(material_id: str):
    return load_peak_table(PEAK_ROOT / f"{material_id}.npz")


def main() -> int:
    simulation = json.loads(SIMULATION_CONFIG.read_text(encoding="utf-8"))
    sampler = PhysicsParameterSampler.from_mapping(
        {**simulation, "run_seed": RUN_SEED}
    )
    factory = OnlineViewFactory(sampler)  # quality_gate=False, like train_arm

    mismatches = 0
    checks = 0
    for material_id in MATERIAL_IDS:
        peaks = load_peaks(material_id)
        for epoch in EPOCHS_TO_CHECK:
            for global_step in GLOBAL_STEPS_TO_CHECK:
                for view_id in (1, 2):
                    checks += 1
                    # Online path (what train_arm uses today).
                    online_view = factory._peak_view(
                        peaks,
                        material_id=material_id,
                        split="train",
                        epoch=epoch,
                        global_step=global_step,
                        view_id=view_id,
                        profile="train",
                    )
                    # Manifest replay path (what prefetch workers would use).
                    row = build_parameter_row(
                        material_id,
                        sampler,
                        profile="train",
                        epoch=epoch,
                        global_step=global_step,
                        split="train",
                        view_id=view_id,
                    )
                    replay_view = factory.make_view_from_manifest(peaks, row)

                    xrd_equal = np.array_equal(
                        online_view.xrd, replay_view.xrd
                    )
                    params_equal = (
                        online_view.parameters == replay_view.parameters
                    )
                    seed_equal = (
                        online_view.rng_seed == replay_view.rng_seed
                        == row.simulation_seed
                    )
                    if not (xrd_equal and params_equal and seed_equal):
                        mismatches += 1
                        print(
                            f"MISMATCH {material_id} epoch={epoch} "
                            f"step={global_step} view={view_id}: "
                            f"xrd_equal={xrd_equal} "
                            f"params_equal={params_equal} "
                            f"seed_equal={seed_equal}"
                        )
                        if not xrd_equal:
                            delta = float(
                                np.max(np.abs(online_view.xrd - replay_view.xrd))
                            )
                            print(f"  max abs diff = {delta:.6e}")

    print(f"checks={checks} mismatches={mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
