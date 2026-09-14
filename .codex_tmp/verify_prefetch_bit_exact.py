"""End-to-end bit-exact check: PairingBatchPrefetcher vs synchronous render_pair_batch.

Renders the same train batch through both paths and asserts the spectra and
labels are bit-identical. Must be run as the main module (spawn protection).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("E:/AI4science/xrd_robustness")
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.runner import PeakRecord, render_pair_batch  # noqa: E402
from xrd_robustness.training.pairing_prefetch import (  # noqa: E402
    PairingBatchPrefetcher,
)

DATA_CONFIG = ROOT / "configs/data.method_transfer.structure_split.json"
SIMULATION_CONFIG = ROOT / "configs/simulation.method_transfer.frozen.json"
RUN_SEED = 20260711
BATCH_SIZE = 16
EPOCH = 1
GLOBAL_STEP = 0
PROFILE = "train"


def build_train_records() -> tuple[list[PeakRecord], dict[str, str]]:
    data = json.loads(DATA_CONFIG.read_text(encoding="utf-8"))
    split_path = ROOT / str(data["split"]["path"])
    peak_manifest_path = ROOT / str(data["peak_cache"]["path"])

    split_payload = json.loads(split_path.read_text(encoding="utf-8"))
    split_rows = split_payload["records"]

    with peak_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        peak_rows = list(csv.DictReader(handle))
    peak_by_id = {str(r["material_id"]): r for r in peak_rows}

    records: list[PeakRecord] = []
    peak_paths: dict[str, str] = {}
    for row in split_rows:
        if str(row["split"]) != "train":
            continue
        material_id = str(row["material_id"])
        peak_row = peak_by_id.get(material_id)
        if peak_row is None:
            continue
        peak_path = (ROOT / str(peak_row["file"])).resolve()
        if not peak_path.is_file():
            continue
        label = CRYSTAL_SYSTEMS.index(str(row["crystal_system"]))
        records.append(
            PeakRecord(
                material_id=material_id,
                label=label,
                split="train",
                peak_table_path=peak_path,
            )
        )
        peak_paths[material_id] = str(peak_path)
    return records, peak_paths


def main() -> int:
    records, peak_paths = build_train_records()
    batch = records[:BATCH_SIZE]
    print(f"batch size = {len(batch)}")

    simulation = json.loads(SIMULATION_CONFIG.read_text(encoding="utf-8"))
    sampler_config = {**simulation, "run_seed": RUN_SEED}
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    factory = OnlineViewFactory(sampler)

    # Synchronous reference (what train_arm uses today).
    peaks = {r.material_id: load_peak_table(r.peak_table_path) for r in batch}
    x1_sync, x2_sync, target_sync = render_pair_batch(
        batch, peaks, factory,
        epoch=EPOCH, global_step=GLOBAL_STEP, profile=PROFILE,
    )

    # Prefetch path.
    prefetcher = PairingBatchPrefetcher(
        worker_count=8,
        peak_paths=peak_paths,
        sampler_config=sampler_config,
    )
    try:
        x1_pre, x2_pre, target_pre = prefetcher.render_pair_batch(
            batch, epoch=EPOCH, global_step=GLOBAL_STEP, profile=PROFILE
        )
    finally:
        prefetcher.close()

    x1_equal = np.array_equal(x1_sync.numpy(), x1_pre.numpy())
    x2_equal = np.array_equal(x2_sync.numpy(), x2_pre.numpy())
    target_equal = np.array_equal(target_sync.numpy(), target_pre.numpy())

    print(f"x1 bit-exact: {x1_equal}")
    print(f"x2 bit-exact: {x2_equal}")
    print(f"target bit-exact: {target_equal}")
    if not (x1_equal and x2_equal and target_equal):
        for name, a, b in (("x1", x1_sync, x1_pre), ("x2", x2_sync, x2_pre)):
            if not np.array_equal(a.numpy(), b.numpy()):
                delta = float(np.max(np.abs(a.numpy() - b.numpy())))
                print(f"  {name} max abs diff = {delta:.6e}")
        return 1
    print("ALL BIT-EXACT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
