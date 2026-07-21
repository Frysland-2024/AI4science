#!/usr/bin/env python3
"""Audit the V9 training sampler and online parameter stream without training."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training_stream import (
    TrainingStreamAudit,
    build_training_sampler_contract,
    deterministic_epoch_shuffle,
    epoch_shuffle_hash,
    paired_manifest_ids,
    select_epoch_batch,
    training_sampler_contract_hash,
)
from xrd_robustness.view_manifest import (
    build_offline_view_manifest,
    build_parameter_batch,
)


MODES = ("clean_erm", "offline_erm", "dynamic_erm", "dynamic_js", "dynamic_residual")
DYNAMIC_MODES = ("dynamic_erm", "dynamic_js", "dynamic_residual")


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--seed", type=int, help="defaults to the registered tuning seed")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_training_stream_preflight_audit.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    seed = int(args.seed) if args.seed is not None else int(contract["development_tuning"]["seed"])
    batch_size = int(contract["experiment"]["batch_size"])
    prefetch_config = contract["experiment"]["dynamic_view_prefetch"]
    configured_prefetch_batches = (
        int(prefetch_config["prefetch_batches"])
        if prefetch_config.get("enabled") is True
        else 1
    )
    target_optimizer_steps = int(contract["development_tuning"]["max_optimizer_steps"])
    split_path = PROJECT_ROOT / contract["data"]["split_manifest"]
    simulation_path = PROJECT_ROOT / contract["simulation"]["path"]
    with split_path.open("r", encoding="utf-8", newline="") as handle:
        split_rows = list(csv.DictReader(handle))
    split_id_sets = {
        split: {
            str(row["material_id"])
            for row in split_rows
            if str(row["split"]) == split
        }
        for split in ("train", "validation", "test")
    }
    train_ids = sorted(split_id_sets["train"])
    train_id_set = set(train_ids)
    expected_train = int(contract["data"]["expected_split_counts"]["train"])
    if len(train_ids) != expected_train or len(train_ids) != len(set(train_ids)):
        raise SystemExit("training split count or uniqueness gate failed")

    steps_per_epoch = math.ceil(len(train_ids) / batch_size)
    training_epochs = math.ceil(target_optimizer_steps / steps_per_epoch)
    sampler_contract = build_training_sampler_contract(
        train_ids,
        seed=seed,
        batch_size=batch_size,
        steps_per_epoch=steps_per_epoch,
        target_optimizer_steps=target_optimizer_steps,
        full_batches=True,
    )
    sampler_contract_digest = training_sampler_contract_hash(sampler_contract)
    audits = {mode: TrainingStreamAudit.create(sampler_contract_digest) for mode in MODES}
    exposure_counts: Counter[str] = Counter()

    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation_config["run_seed"] = seed
    sampler = PhysicsParameterSampler.from_mapping(simulation_config)
    clean_rows = build_offline_view_manifest(
        train_ids,
        sampler,
        profile=str(contract["simulation"]["clean_profile"]),
        views_per_material=1,
    )
    offline_rows = build_offline_view_manifest(
        train_ids,
        sampler,
        profile=str(contract["simulation"]["train_profile"]),
        views_per_material=4,
    )
    clean_index = {(row.material_id, row.view_id): row for row in clean_rows}
    offline_index = {(row.material_id, row.view_id): row for row in offline_rows}

    maximum_dynamic_rows_per_batch = 0
    shuffle_hashes = []
    completed_steps = 0
    dynamic_rows_are_train_scoped = True
    dynamic_parameter_replay_is_exact = None
    for epoch in range(training_epochs):
        order = deterministic_epoch_shuffle(train_ids, seed=seed, epoch=epoch)
        shuffle_hashes.append(epoch_shuffle_hash(order, seed=seed, epoch=epoch))
        steps_this_epoch = min(steps_per_epoch, target_optimizer_steps - completed_steps)
        for step in range(steps_this_epoch):
            batch_ids = select_epoch_batch(
                order,
                step=step,
                batch_size=batch_size,
                full_batch=True,
            )
            absolute_step = epoch * steps_per_epoch + step
            exposure_counts.update(batch_ids)

            clean_pairs = tuple(
                (
                    clean_index[(material_id, 1)].manifest_id,
                    clean_index[(material_id, 1)].manifest_id,
                )
                for material_id in batch_ids
            )
            first_view_id = (absolute_step * 2) % 4 + 1
            second_view_id = first_view_id % 4 + 1
            offline_pairs = tuple(
                (
                    offline_index[(material_id, first_view_id)].manifest_id,
                    offline_index[(material_id, second_view_id)].manifest_id,
                )
                for material_id in batch_ids
            )
            dynamic_rows = build_parameter_batch(
                batch_ids,
                sampler,
                profile=str(contract["simulation"]["train_profile"]),
                epoch=epoch,
                global_step=step,
            )
            dynamic_rows_are_train_scoped = dynamic_rows_are_train_scoped and all(
                row.split == "train" and row.material_id in train_id_set
                for row in dynamic_rows
            )
            if dynamic_parameter_replay_is_exact is None:
                replay_rows = build_parameter_batch(
                    batch_ids,
                    sampler,
                    profile=str(contract["simulation"]["train_profile"]),
                    epoch=epoch,
                    global_step=step,
                )
                dynamic_parameter_replay_is_exact = dynamic_rows == replay_rows
            maximum_dynamic_rows_per_batch = max(
                maximum_dynamic_rows_per_batch,
                len(dynamic_rows),
            )
            dynamic_pairs = paired_manifest_ids(dynamic_rows, batch_ids)
            pairs_by_mode = {
                "clean_erm": clean_pairs,
                "offline_erm": offline_pairs,
                **{mode: dynamic_pairs for mode in DYNAMIC_MODES},
            }
            for mode, audit in audits.items():
                audit.record_batch(
                    epoch=epoch,
                    step=step,
                    absolute_step=absolute_step,
                    material_ids=batch_ids,
                    parameter_pairs=pairs_by_mode[mode],
                    views_per_structure=2,
                )
            completed_steps += 1

    snapshots = {mode: audit.snapshot() for mode, audit in audits.items()}
    sampler_hashes = {value["sampler_hash"] for value in snapshots.values()}
    pair_schedule_hashes = {value["pair_schedule_hash"] for value in snapshots.values()}
    exposure_tuples = {
        (
            value["optimizer_steps"],
            value["structure_exposures"],
            value["spectrum_exposures"],
        )
        for value in snapshots.values()
    }
    dynamic_parameter_hashes = {
        snapshots[mode]["parameter_pair_hash"] for mode in DYNAMIC_MODES
    }
    gates = {
        "train_split_count_matches_contract": len(train_ids) == expected_train,
        "train_validation_test_ids_are_disjoint": not (
            split_id_sets["train"] & split_id_sets["validation"]
            or split_id_sets["train"] & split_id_sets["test"]
            or split_id_sets["validation"] & split_id_sets["test"]
        ),
        "validation_and_test_are_excluded_from_dynamic_training": (
            dynamic_rows_are_train_scoped
        ),
        "same_dynamic_coordinate_replays_exact_parameters": (
            dynamic_parameter_replay_is_exact is True
        ),
        "all_five_sampler_hashes_match": len(sampler_hashes) == 1,
        "all_five_pair_schedule_hashes_match": len(pair_schedule_hashes) == 1,
        "all_five_exposure_counts_match": len(exposure_tuples) == 1,
        "three_dynamic_parameter_pair_hashes_match": len(dynamic_parameter_hashes) == 1,
        "all_train_structures_are_exposed": set(exposure_counts) == set(train_ids),
        "dynamic_rows_are_batch_bounded": (
            maximum_dynamic_rows_per_batch == batch_size * 2
        ),
        "dynamic_rows_are_prefetch_bounded": (
            maximum_dynamic_rows_per_batch * configured_prefetch_batches
            == batch_size * 2 * configured_prefetch_batches
        ),
    }
    report = {
        "status": "pass" if all(gates.values()) else "fail",
        "contract": str(contract_path),
        "contract_sha256": _file_hash(contract_path),
        "split_manifest": str(split_path),
        "split_manifest_sha256": _file_hash(split_path),
        "split_counts": {
            split: len(material_ids)
            for split, material_ids in split_id_sets.items()
        },
        "simulation_config": str(simulation_path),
        "simulation_config_sha256": _file_hash(simulation_path),
        "seed": seed,
        "sampler_contract": sampler_contract,
        "sampler_contract_hash": sampler_contract_digest,
        "training_epochs": training_epochs,
        "steps_per_epoch": steps_per_epoch,
        "target_optimizer_steps": target_optimizer_steps,
        "epoch_shuffle_hashes": shuffle_hashes,
        "exposure_distribution": {
            "unique_structures": len(exposure_counts),
            "total_structure_exposures": sum(exposure_counts.values()),
            "minimum_per_structure": min(exposure_counts.values()),
            "maximum_per_structure": max(exposure_counts.values()),
        },
        "maximum_dynamic_parameter_rows_per_batch": maximum_dynamic_rows_per_batch,
        "configured_prefetch_batches": configured_prefetch_batches,
        "maximum_live_dynamic_parameter_rows": (
            maximum_dynamic_rows_per_batch * configured_prefetch_batches
        ),
        "legacy_eager_dynamic_parameter_rows": (
            len(train_ids) * training_epochs * steps_per_epoch * 2
        ),
        "methods": snapshots,
        "gates": gates,
    }
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output_path), "gates": gates}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
