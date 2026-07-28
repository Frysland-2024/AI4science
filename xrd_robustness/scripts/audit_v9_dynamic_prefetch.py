#!/usr/bin/env python3
"""Benchmark and audit deterministic dynamic-view process prefetch on real V9 data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training_prefetch import (
    DynamicBatchPrefetcher,
    render_dynamic_batch,
)
from xrd_robustness.training_stream import deterministic_epoch_shuffle, select_epoch_batch
from xrd_robustness.view_manifest import build_parameter_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--batches", type=int, default=16)
    parser.add_argument(
        "--repeat-passes",
        type=int,
        default=1,
        help="repeat the same structure batches with new global steps to measure invariant caches",
    )
    parser.add_argument("--workers", type=int, help="override the contract worker count for a benchmark")
    parser.add_argument(
        "--prefetch-batches",
        type=int,
        help="override the contract prefetch window for a benchmark",
    )
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "v9_dynamic_prefetch_audit.json"))
    return parser.parse_args()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _array_hash(first: np.ndarray, second: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in (first, second):
        digest.update(str(value.dtype).encode("ascii"))
        digest.update(json.dumps(value.shape).encode("ascii"))
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest().upper()


def main() -> int:
    args = parse_args()
    if args.batches <= 1:
        raise SystemExit("--batches must be greater than one")
    if args.repeat_passes <= 0:
        raise SystemExit("--repeat-passes must be positive")
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    experiment = contract["experiment"]
    prefetch = experiment["dynamic_view_prefetch"]
    batch_size = int(experiment["batch_size"])
    worker_count = (
        int(args.workers) if args.workers is not None else int(prefetch["worker_processes"])
    )
    prefetch_batches = (
        int(args.prefetch_batches)
        if args.prefetch_batches is not None
        else int(prefetch["prefetch_batches"])
    )
    if worker_count <= 0 or prefetch_batches <= 0:
        raise SystemExit("worker and prefetch counts must be positive")
    worker_native_threads = int(prefetch["worker_native_threads"])
    tuning_seed = int(contract["development_tuning"]["seed"])
    simulation_path = PROJECT_ROOT / contract["simulation"]["path"]
    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    sampler_config = dict(simulation_config)
    sampler_config["run_seed"] = tuning_seed
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    strategy = IndependentDynamicStrategy(
        sampler,
        config_hash=str(contract["simulation"]["sha256"]),
    )
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        strategy=strategy,
    )
    split_path = PROJECT_ROOT / contract["data"]["split_manifest"]
    if split_path.suffix.lower() == ".json":
        split_payload = json.loads(split_path.read_text(encoding="utf-8"))
        split_rows = split_payload["records"]
    else:
        with split_path.open("r", encoding="utf-8", newline="") as handle:
            split_rows = list(csv.DictReader(handle))
    train_ids = sorted(
        str(row["material_id"])
        for row in split_rows
        if row["split"] == "train"
    )
    epoch_order = deterministic_epoch_shuffle(train_ids, seed=tuning_seed, epoch=0)
    batches: list[tuple[int, tuple[str, ...], tuple[Any, ...]]] = []
    for pass_index in range(args.repeat_passes):
        for step in range(args.batches):
            material_ids = select_epoch_batch(
                epoch_order,
                step=step,
                batch_size=batch_size,
                full_batch=True,
            )
            global_step = pass_index * args.batches + step
            rows = tuple(
                build_parameter_batch(
                    material_ids,
                    sampler,
                    profile=str(contract["simulation"]["train_profile"]),
                    epoch=pass_index,
                    global_step=global_step,
                    split="train",
                )
            )
            batches.append((global_step, material_ids, rows))

    data_root = PROJECT_ROOT / contract["data"]["root"]
    peak_root = data_root / "mp_processed" / contract["data"]["peak_cache_name"]
    unique_ids = sorted({material_id for _, ids, _ in batches for material_id in ids})
    peaks = {
        material_id: load_peak_table(peak_root / f"{material_id}.npz")
        for material_id in unique_ids
    }

    sequential_results = []
    sequential_batch_seconds = []
    sequential_started = time.perf_counter()
    for batch_key, material_ids, rows in batches:
        started = time.perf_counter()
        sequential_results.append(
            render_dynamic_batch(
                batch_key,
                material_ids,
                rows,
                peaks=peaks,
                factory=factory,
                sampler=sampler,
                profile=str(contract["simulation"]["train_profile"]),
            )
        )
        sequential_batch_seconds.append(time.perf_counter() - started)
    sequential_seconds = time.perf_counter() - sequential_started

    prefetcher = DynamicBatchPrefetcher(
        worker_count=worker_count,
        worker_native_threads=worker_native_threads,
        prefetch_batches=prefetch_batches,
        start_method=str(prefetch["multiprocessing_start_method"]),
        data_root=data_root,
        peak_cache_name=str(contract["data"]["peak_cache_name"]),
        sampler_config=sampler_config,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        simulation_config_hash=str(contract["simulation"]["sha256"]),
        profile=str(contract["simulation"]["train_profile"]),
    )
    observed_results = []
    prefetch_batch_seconds = []
    prefetch_started = time.perf_counter()
    try:
        for batch_key, material_ids, rows in batches[:prefetch_batches]:
            prefetcher.submit(batch_key, material_ids, rows)
        for index, (batch_key, _, _) in enumerate(batches):
            started = time.perf_counter()
            observed_results.append(prefetcher.get(batch_key))
            prefetch_batch_seconds.append(time.perf_counter() - started)
            refill_index = index + prefetch_batches
            if refill_index < len(batches):
                refill_key, refill_ids, refill_rows = batches[refill_index]
                prefetcher.submit(refill_key, refill_ids, refill_rows)
    finally:
        prefetcher.close()
    prefetch_seconds = time.perf_counter() - prefetch_started

    exact_arrays = True
    exact_rows = True
    exact_parameters = True
    exact_material_order = True
    maximum_absolute_difference = 0.0
    sequential_array_hashes = []
    prefetch_array_hashes = []
    sequential_manifest_ids = []
    prefetch_manifest_ids = []
    for expected, observed in zip(sequential_results, observed_results, strict=True):
        exact_material_order &= expected.material_ids == observed.material_ids
        exact_rows &= expected.accepted_rows == observed.accepted_rows
        exact_parameters &= (
            expected.parameters_first == observed.parameters_first
            and expected.parameters_second == observed.parameters_second
        )
        exact_arrays &= np.array_equal(expected.first, observed.first)
        exact_arrays &= np.array_equal(expected.second, observed.second)
        maximum_absolute_difference = max(
            maximum_absolute_difference,
            float(np.max(np.abs(expected.first - observed.first))),
            float(np.max(np.abs(expected.second - observed.second))),
        )
        sequential_array_hashes.append(_array_hash(expected.first, expected.second))
        prefetch_array_hashes.append(_array_hash(observed.first, observed.second))
        sequential_manifest_ids.extend(row.manifest_id for row in expected.accepted_rows)
        prefetch_manifest_ids.extend(row.manifest_id for row in observed.accepted_rows)

    sequential_pair_hash = _canonical_hash(sequential_manifest_ids)
    prefetch_pair_hash = _canonical_hash(prefetch_manifest_ids)
    quality_counts_match = (
        factory.quality_gate_checked_count == prefetcher.quality_gate_checked_count
        and factory.quality_gate_rejected_count == prefetcher.quality_gate_rejected_count
    )
    status = "passed" if all(
        (
            exact_arrays,
            exact_rows,
            exact_parameters,
            exact_material_order,
            quality_counts_match,
            sequential_pair_hash == prefetch_pair_hash,
        )
    ) else "failed"
    report = {
        "schema_version": "v9-dynamic-prefetch-audit-v1",
        "status": status,
        "contract": str(contract_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest().upper(),
        "configuration": {
            "seed": tuning_seed,
            "batch_size": batch_size,
            "audited_batches": len(batches),
            "audited_structures": len(batches) * batch_size,
            "audited_views": len(batches) * batch_size * 2,
            "repeat_passes": args.repeat_passes,
            "worker_processes": worker_count,
            "worker_native_threads": worker_native_threads,
            "worker_thread_policy": prefetch["worker_thread_policy"],
            "prefetch_batches": prefetch_batches,
            "multiprocessing_start_method": prefetch["multiprocessing_start_method"],
            "sharding_algorithm": prefetch["sharding_algorithm"],
            "result_order": prefetch["result_order"],
            "worker_peak_cache": prefetch["worker_peak_cache"],
            "pin_memory": prefetch["pin_memory"],
            "non_blocking_h2d": prefetch["non_blocking_h2d"],
            "contract_worker_override": args.workers,
            "contract_prefetch_override": args.prefetch_batches,
            "maximum_live_parameter_rows": 2 * batch_size * prefetch_batches,
        },
        "equivalence": {
            "exact_material_order": exact_material_order,
            "exact_accepted_manifest_rows": exact_rows,
            "exact_parameters": exact_parameters,
            "exact_spectrum_arrays": exact_arrays,
            "maximum_absolute_spectrum_difference": maximum_absolute_difference,
            "sequential_parameter_pair_hash": sequential_pair_hash,
            "prefetch_parameter_pair_hash": prefetch_pair_hash,
            "sequential_array_stream_hash": _canonical_hash(sequential_array_hashes),
            "prefetch_array_stream_hash": _canonical_hash(prefetch_array_hashes),
            "quality_gate_counts_match": quality_counts_match,
            "quality_gate_checked_views": factory.quality_gate_checked_count,
            "quality_gate_rejected_views": factory.quality_gate_rejected_count,
        },
        "performance": {
            "sequential_seconds": sequential_seconds,
            "prefetch_seconds": prefetch_seconds,
            "speedup": sequential_seconds / prefetch_seconds,
            "sequential_batches_per_second": args.batches / sequential_seconds,
            "prefetch_batches_per_second": len(batches) / prefetch_seconds,
            "sequential_first_batch_seconds": sequential_batch_seconds[0],
            "prefetch_first_batch_wait_seconds": prefetch_batch_seconds[0],
            "sequential_steady_median_batch_seconds": float(
                np.median(sequential_batch_seconds[1:])
            ),
            "prefetch_steady_median_wait_seconds": float(
                np.median(prefetch_batch_seconds[1:])
            ),
            "note": (
                "Prefetch time includes worker initialization and lazy worker peak loads; "
                "main-process peak loading and deterministic parameter-row construction are excluded from both paths."
            ),
        },
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
