#!/usr/bin/env python3
"""Audit Clean/Offline process prefetch on real V9 peak tables without training."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training_prefetch import FixedBatchPrefetcher, render_fixed_batch
from xrd_robustness.training_stream import deterministic_epoch_shuffle, select_epoch_batch
from xrd_robustness.view_manifest import ViewManifestRow, build_offline_view_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--batches", type=int, default=16)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--prefetch-batches", type=int)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_fixed_prefetch_audit.json"),
    )
    return parser.parse_args()


def _stream_hash(results: Sequence[Any]) -> str:
    digest = hashlib.sha256()
    for result in results:
        second = result.first if result.second is None else result.second
        for value in (result.first, second):
            contiguous = np.ascontiguousarray(value)
            digest.update(str(contiguous.dtype).encode("ascii"))
            digest.update(json.dumps(contiguous.shape).encode("ascii"))
            digest.update(contiguous.tobytes())
    return digest.hexdigest().upper()


def _pair_hash(
    batches: Sequence[
        tuple[int, tuple[str, ...], tuple[ViewManifestRow, ...], tuple[ViewManifestRow, ...] | None]
    ],
) -> str:
    pairs = []
    for _, _, first_rows, second_rows in batches:
        for offset, first in enumerate(first_rows):
            second = first if second_rows is None else second_rows[offset]
            pairs.append([first.manifest_id, second.manifest_id])
    payload = json.dumps(pairs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _audit_mode(
    mode: str,
    *,
    train_ids: Sequence[str],
    batch_count: int,
    batch_size: int,
    worker_count: int,
    prefetch_batches: int,
    prefetch_config: dict[str, Any],
    sampler: PhysicsParameterSampler,
    sampler_config: dict[str, Any],
    simulation_config: dict[str, Any],
    simulation_hash: str,
    data_root: Path,
    peak_cache_name: str,
    seed: int,
    profile: str,
) -> dict[str, Any]:
    epoch_order = deterministic_epoch_shuffle(train_ids, seed=seed, epoch=0)
    id_batches = [
        select_epoch_batch(
            epoch_order,
            step=step,
            batch_size=batch_size,
            full_batch=True,
        )
        for step in range(batch_count)
    ]
    unique_ids = sorted({material_id for ids in id_batches for material_id in ids})
    views_per_material = 1 if mode == "clean_erm" else 4
    rows = build_offline_view_manifest(
        unique_ids,
        sampler,
        profile=profile,
        views_per_material=views_per_material,
    )
    row_index = {(row.material_id, row.view_id): row for row in rows}
    batches = []
    for step, material_ids in enumerate(id_batches):
        first_view_id = 1 if mode == "clean_erm" else (step * 2) % 4 + 1
        first_rows = tuple(
            row_index[(material_id, first_view_id)] for material_id in material_ids
        )
        second_rows = None
        if mode == "offline_erm":
            second_view_id = first_view_id % 4 + 1
            second_rows = tuple(
                row_index[(material_id, second_view_id)] for material_id in material_ids
            )
        batches.append((step, tuple(material_ids), first_rows, second_rows))

    peak_root = data_root / "mp_processed" / peak_cache_name
    peaks = {
        material_id: load_peak_table(peak_root / f"{material_id}.npz")
        for material_id in unique_ids
    }
    strategy = IndependentDynamicStrategy(sampler, config_hash=simulation_hash)
    sequential_factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        strategy=strategy,
    )
    sequential_started = time.perf_counter()
    sequential = [
        render_fixed_batch(
            batch_key,
            material_ids,
            first_rows,
            second_rows,
            peaks=peaks,
            factory=sequential_factory,
        )
        for batch_key, material_ids, first_rows, second_rows in batches
    ]
    sequential_seconds = time.perf_counter() - sequential_started

    prefetcher = FixedBatchPrefetcher(
        worker_count=worker_count,
        worker_native_threads=int(prefetch_config["worker_native_threads"]),
        prefetch_batches=prefetch_batches,
        start_method=str(prefetch_config["multiprocessing_start_method"]),
        data_root=data_root,
        peak_cache_name=peak_cache_name,
        sampler_config=sampler_config,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        simulation_config_hash=simulation_hash,
        profile=profile,
    )
    observed = []
    prefetch_started = time.perf_counter()
    try:
        for batch in batches[:prefetch_batches]:
            prefetcher.submit(*batch)
        for index, (batch_key, _, _, _) in enumerate(batches):
            observed.append(prefetcher.get(batch_key))
            refill_index = index + prefetch_batches
            if refill_index < len(batches):
                prefetcher.submit(*batches[refill_index])
    finally:
        prefetcher.close()
    prefetch_seconds = time.perf_counter() - prefetch_started

    exact_arrays = all(
        np.array_equal(expected.first, actual.first)
        and (
            expected.second is None
            and actual.second is None
            or expected.second is not None
            and actual.second is not None
            and np.array_equal(expected.second, actual.second)
        )
        for expected, actual in zip(sequential, observed, strict=True)
    )
    exact_order = all(
        expected.material_ids == actual.material_ids
        for expected, actual in zip(sequential, observed, strict=True)
    )
    sequential_hash = _stream_hash(sequential)
    prefetch_hash = _stream_hash(observed)
    quality_counts_match = (
        sequential_factory.quality_gate_checked_count
        == prefetcher.quality_gate_checked_count
        and sequential_factory.quality_gate_rejected_count
        == prefetcher.quality_gate_rejected_count
    )
    gates = {
        "exact_spectrum_arrays": exact_arrays,
        "exact_material_order": exact_order,
        "exact_array_stream_hash": sequential_hash == prefetch_hash,
        "exact_quality_gate_counts": quality_counts_match,
        "all_batches_consumed": len(observed) == len(batches),
    }
    return {
        "status": "pass" if all(gates.values()) else "fail",
        "mode": mode,
        "batches": batch_count,
        "structures_per_batch": batch_size,
        "rendered_spectra": batch_count
        * batch_size
        * (1 if mode == "clean_erm" else 2),
        "parameter_pair_hash": _pair_hash(batches),
        "sequential_array_stream_sha256": sequential_hash,
        "prefetch_array_stream_sha256": prefetch_hash,
        "sequential_seconds": sequential_seconds,
        "prefetch_seconds": prefetch_seconds,
        "sequential_batches_per_second": batch_count / sequential_seconds,
        "prefetch_batches_per_second": batch_count / prefetch_seconds,
        "speedup": sequential_seconds / prefetch_seconds,
        "quality_gate_checked_count": prefetcher.quality_gate_checked_count,
        "quality_gate_rejected_count": prefetcher.quality_gate_rejected_count,
        "gates": gates,
    }


def main() -> int:
    args = parse_args()
    if args.batches <= 1:
        raise SystemExit("--batches must be greater than one")
    contract = load_contract(Path(args.contract).resolve())
    experiment = contract["experiment"]
    prefetch_config = dict(experiment["dynamic_view_prefetch"])
    worker_count = int(args.workers or prefetch_config["worker_processes"])
    prefetch_batches = int(args.prefetch_batches or prefetch_config["prefetch_batches"])
    if prefetch_batches > args.batches:
        prefetch_batches = args.batches
    seed = int(contract["development_tuning"]["seed"])
    simulation_path = PROJECT_ROOT / contract["simulation"]["path"]
    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    sampler_config = dict(simulation_config)
    sampler_config["run_seed"] = seed
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    split_path = PROJECT_ROOT / contract["data"]["split_manifest"]
    with split_path.open("r", encoding="utf-8", newline="") as handle:
        train_ids = sorted(
            str(row["material_id"])
            for row in csv.DictReader(handle)
            if row["split"] == "train"
        )
    common = {
        "train_ids": train_ids,
        "batch_count": int(args.batches),
        "batch_size": int(experiment["batch_size"]),
        "worker_count": worker_count,
        "prefetch_batches": prefetch_batches,
        "prefetch_config": prefetch_config,
        "sampler": sampler,
        "sampler_config": sampler_config,
        "simulation_config": simulation_config,
        "simulation_hash": str(contract["simulation"]["sha256"]),
        "data_root": PROJECT_ROOT / contract["data"]["root"],
        "peak_cache_name": str(contract["data"]["peak_cache_name"]),
        "seed": seed,
    }
    audits = {
        "clean_erm": _audit_mode(
            "clean_erm",
            profile=str(contract["simulation"]["clean_profile"]),
            **common,
        ),
        "offline_erm": _audit_mode(
            "offline_erm",
            profile=str(contract["simulation"]["train_profile"]),
            **common,
        ),
    }
    status = "pass" if all(item["status"] == "pass" for item in audits.values()) else "fail"
    report = {
        "schema_version": "v9-fixed-prefetch-audit-v1",
        "status": status,
        "purpose": "rendering equivalence and throughput audit only; no training",
        "workers": worker_count,
        "prefetch_batches": prefetch_batches,
        "audits": audits,
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "output": str(output)}, ensure_ascii=False))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
