#!/usr/bin/env python3
"""Private-data smoke: compare serial and multiprocessing V11 pairs bitwise.

Use on the laptop before rebuilding the private ZIP and on the rented server
before any Optuna/final run. No optimizer step, held-out Test or RRUFF access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"xrd_robustness"/"src"))
from v11_prefetch import V11PairPrefetchPool


def main() -> None:
    import numpy as np
    from xrd_robustness.training.runner import (
        PeakRecord, load_peak_tables, render_pair_batch, build_online_view_factory,
    )
    from xrd_robustness.physics import PhysicsParameterSampler

    ap=argparse.ArgumentParser()
    ap.add_argument("--workers",type=int,default=4)
    ap.add_argument("--batch-size",type=int,default=16)
    args=ap.parse_args()
    sim=json.loads(
        (ROOT/"xrd_robustness"/"configs"/"simulation.v11_tch_pseudo_voigt.json").read_text(
            encoding="utf-8"
        )
    )
    path=ROOT/"xrd_robustness"/"data"/"merged_154975_v11"/"training_records.v1.jsonl"
    rows=[]
    with path.open(encoding="utf-8") as source:
        for raw in source:
            obj=json.loads(raw)
            if obj["split"]!="train":
                continue
            rows.append(PeakRecord(
                obj["material_id"],int(obj["label"]),obj["split"],
                (path.parent/obj["peak_table_path"]).resolve(),
            ))
            if len(rows)>=args.batch_size:
                break
    if len(rows)!=args.batch_size:
        raise RuntimeError("Insufficient private train smoke rows")
    sampler=PhysicsParameterSampler.from_mapping({**sim,"run_seed":20261103})
    factory,version,_=build_online_view_factory(sampler,sim)
    if version!="v11_tch_pseudo_voigt":
        raise RuntimeError("Unexpected simulator")
    start=time.perf_counter()
    a,b,y=render_pair_batch(
        rows,load_peak_tables(rows),factory,
        epoch=1,global_step=101,profile="train",
    )
    serial_seconds=time.perf_counter()-start
    start=time.perf_counter()
    with V11PairPrefetchPool(sim,run_seed=20261103,workers=args.workers,
                             prefetch_batches=2,native_threads=1) as pool:
        pool.submit(101,rows,epoch=1,global_step=101,profile="train")
        other_a,other_b,labels=pool.get(101)
    parallel_seconds=time.perf_counter()-start
    if not (np.array_equal(a.numpy(),other_a) and
            np.array_equal(b.numpy(),other_b) and
            np.array_equal(y.numpy(),labels)):
        raise RuntimeError("BLOCKED: V11 serial/prefetch spectra differ; do not run HPO")
    print(json.dumps({
        "status":"PASS","source":"private Train only",
        "parent_count":len(rows),"workers":args.workers,
        "pair_views_bitwise_equal":True,
        "serial_seconds_single_batch":round(serial_seconds,4),
        "parallel_seconds_including_spawn":round(parallel_seconds,4),
        "warning":"Small startup-dominated smoke: NOT an accelerator speedup claim",
    },indent=2),flush=True)


if __name__=="__main__":
    main()
