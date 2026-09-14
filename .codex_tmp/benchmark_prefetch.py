"""Benchmark synchronous vs prefetch batch rendering for pairing ablation."""
from __future__ import annotations

import csv
import json
import sys
import time
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
PROFILE = "train"


def build_train_records(limit: int) -> tuple[list[PeakRecord], dict[str, str]]:
    data = json.loads(DATA_CONFIG.read_text(encoding="utf-8"))
    split_path = ROOT / str(data["split"]["path"])
    peak_manifest_path = ROOT / str(data["peak_cache"]["path"])
    split_rows = json.loads(split_path.read_text(encoding="utf-8"))["records"]
    with peak_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        peak_by_id = {str(r["material_id"]): r for r in csv.DictReader(handle)}

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
        records.append(
            PeakRecord(
                material_id=material_id,
                label=CRYSTAL_SYSTEMS.index(str(row["crystal_system"])),
                split="train",
                peak_table_path=peak_path,
            )
        )
        peak_paths[material_id] = str(peak_path)
        if len(records) >= limit:
            break
    return records, peak_paths


def main() -> int:
    records, peak_paths = build_train_records(512)
    n_batches = len(records) // BATCH_SIZE
    batches = [
        records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE] for i in range(n_batches)
    ]
    print(f"records={len(records)} batches={n_batches} batch_size={BATCH_SIZE}")

    simulation = json.loads(SIMULATION_CONFIG.read_text(encoding="utf-8"))
    sampler_config = {**simulation, "run_seed": RUN_SEED}
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    factory = OnlineViewFactory(sampler)

    # Warm up by loading peak tables into the main process once.
    peaks = {r.material_id: load_peak_table(r.peak_table_path) for r in records}
    print(f"loaded {len(peaks)} peak tables into main process")

    # Synchronous timing.
    t0 = time.perf_counter()
    sync_out = []
    for i, batch in enumerate(batches):
        sync_out.append(
            render_pair_batch(
                batch, peaks, factory, epoch=1, global_step=i, profile=PROFILE
            )
        )
    sync_time = time.perf_counter() - t0
    print(f"sync: {n_batches} batches in {sync_time:.2f}s "
          f"({n_batches * BATCH_SIZE * 2 / sync_time:.1f} spectra/s)")

    # Prefetch timing (warm up first 4 batches, then measure the rest).
    prefetcher = PairingBatchPrefetcher(
        worker_count=16,
        peak_paths=peak_paths,
        sampler_config=sampler_config,
    )
    try:
        warm = 4
        for i in range(warm):
            prefetcher.render_pair_batch(
                batches[i], epoch=1, global_step=i, profile=PROFILE
            )
        t0 = time.perf_counter()
        pre_out = []
        for i in range(warm, n_batches):
            pre_out.append(
                prefetcher.render_pair_batch(
                    batches[i], epoch=1, global_step=i, profile=PROFILE
                )
            )
        pre_time = time.perf_counter() - t0
        measured = n_batches - warm
        print(f"prefetch(16w): {measured} batches in {pre_time:.2f}s "
              f"({measured * BATCH_SIZE * 2 / pre_time:.1f} spectra/s)")
    finally:
        prefetcher.close()

    # Bit-exact cross-check on the measured batches.
    mismatch = 0
    for idx, (sync_batch, pre_batch) in enumerate(zip(sync_out[warm:], pre_out)):
        if not np.array_equal(sync_batch[0].numpy(), pre_batch[0].numpy()):
            mismatch += 1
        if not np.array_equal(sync_batch[1].numpy(), pre_batch[1].numpy()):
            mismatch += 1
    print(f"bit-exact mismatch batches: {mismatch} / {measured}")

    if sync_time > 0 and pre_time > 0:
        speedup = (sync_time / n_batches) / (pre_time / measured)
        print(f"per-batch speedup: {speedup:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
