#!/usr/bin/env python3
"""Controlled same-parent vs same-class JS pairing ablation for PXRD.

The two arms see exactly the same parents, the same two rendered views, the
same CE supervision, optimizer, model initialization and Validation spectra.
Only the JS pairing changes:

- same_parent_js: view1(A) <-> view2(A)
- same_class_js:  view1(A) <-> view2(B), A != B, same crystal-system label

Training uses the restored deterministic multiprocessing online-rendering
pipeline: 16 persistent workers by default, six batches prefetched ahead,
per-worker lazy ideal-peak caching, cached structure-invariant reflection
metadata, deterministic quality-gate retry, pinned host memory and non-blocking
CUDA transfer.  The optimization changes execution speed, not the scientific
view stream or the JS comparison.

This is a post-hoc Validation-only mechanism ablation.  It never accesses the
frozen simulated Test split.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from typing import Any, Sequence

import numpy as np
import torch
from torch.nn import functional as F


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.models import ML4PXRDResNet1DConfig  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.training.objectives import js_divergence  # noqa: E402
from xrd_robustness.training.runner import (  # noqa: E402
    PeakRecord,
    build_model,
    evaluate,
)
from xrd_robustness.training_prefetch import (  # noqa: E402
    DynamicBatchPrefetcher,
    PREFETCH_GENERATION,
    PREFETCH_RESULT_ORDER,
    PREFETCH_SHARDING_ALGORITHM,
    PREFETCH_WORKER_PEAK_CACHE,
    PREFETCH_WORKER_THREAD_POLICY,
)
from xrd_robustness.view_manifest import build_parameter_batch  # noqa: E402


DATA_CONFIG = ROOT / "configs/data.method_transfer.structure_split.json"
SIMULATION_CONFIG = ROOT / "configs/simulation.method_transfer.frozen.json"
DATA_ROOT = ROOT / "data/formal_14060"
PEAK_CACHE_NAME = "peak_tables_v7_reflection"
DEFAULT_OUTPUT = ROOT / "outputs/pairing_ablation"
SINGLE_OOD = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)
ARMS = ("same_parent_js", "same_class_js")
FULL_SEEDS = (20260711, 20260712, 20260713, 20260714, 20260715)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def resolve_project_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        raise ValueError(f"path leaves xrd_robustness root: {value}")
    return path


def load_local_records() -> tuple[list[PeakRecord], dict[str, Any]]:
    """Join the frozen Train/Validation split to the local V7 ideal-peak cache."""

    data = json.loads(DATA_CONFIG.read_text(encoding="utf-8"))
    split_path = resolve_project_path(str(data["split"]["path"]))
    peak_manifest_path = resolve_project_path(str(data["peak_cache"]["path"]))

    split_payload = json.loads(split_path.read_text(encoding="utf-8"))
    split_rows = split_payload.get("records")
    if not isinstance(split_rows, list):
        raise RuntimeError("split manifest does not contain records")

    with peak_manifest_path.open("r", encoding="utf-8", newline="") as handle:
        peak_rows = list(csv.DictReader(handle))
    peak_by_id = {str(row["material_id"]): row for row in peak_rows}

    records: list[PeakRecord] = []
    missing: list[str] = []
    for row in split_rows:
        split = str(row["split"])
        if split not in {"train", "validation"}:
            continue
        material_id = str(row["material_id"])
        peak_row = peak_by_id.get(material_id)
        if peak_row is None:
            missing.append(material_id)
            continue
        crystal_system = str(row["crystal_system"])
        try:
            label = CRYSTAL_SYSTEMS.index(crystal_system)
        except ValueError as error:
            raise RuntimeError(f"unknown crystal system: {crystal_system}") from error
        peak_path = resolve_project_path(str(peak_row["file"]))
        if not peak_path.is_file():
            missing.append(material_id)
            continue
        records.append(
            PeakRecord(
                material_id=material_id,
                label=label,
                split=split,
                peak_table_path=peak_path,
            )
        )
    if missing:
        raise RuntimeError(f"missing local peak tables, first IDs: {missing[:5]}")

    train = [record for record in records if record.split == "train"]
    validation = [record for record in records if record.split == "validation"]
    expected = data["split"]["counts"]
    if len(train) != int(expected["train"]):
        raise RuntimeError(f"train count differs from frozen split: {len(train)}")
    if len(validation) != int(expected["validation"]):
        raise RuntimeError(
            f"validation count differs from frozen split: {len(validation)}"
        )

    metadata = {
        "data_config": str(DATA_CONFIG),
        "split_manifest": str(split_path),
        "peak_manifest": str(peak_manifest_path),
        "train_count": len(train),
        "validation_count": len(validation),
        "train_per_class": {
            CRYSTAL_SYSTEMS[label]: sum(record.label == label for record in train)
            for label in range(len(CRYSTAL_SYSTEMS))
        },
    }
    return records, metadata


def load_validation_peaks(
    records: Sequence[PeakRecord],
) -> dict[str, Any]:
    """Only Validation peaks live in the training process; workers own Train peaks."""

    print(f"Loading {len(records)} Validation ideal peak tables...", flush=True)
    return {
        record.material_id: load_peak_table(record.peak_table_path)
        for record in records
    }


def make_same_class_batches(
    records: Sequence[PeakRecord],
    rng: np.random.Generator,
    batch_size: int,
) -> tuple[list[list[PeakRecord]], list[str]]:
    """Build batches where adjacent parents are different members of one class."""

    if batch_size <= 0 or batch_size % 2:
        raise ValueError("batch_size must be a positive even number")
    grouped: dict[int, list[PeakRecord]] = defaultdict(list)
    for record in records:
        grouped[record.label].append(record)

    pairs: list[tuple[PeakRecord, PeakRecord]] = []
    dropped: list[str] = []
    for label in sorted(grouped):
        group = grouped[label]
        order = rng.permutation(len(group)).tolist()
        if len(order) % 2:
            dropped.append(group[order[-1]].material_id)
            order = order[:-1]
        for start in range(0, len(order), 2):
            first = group[order[start]]
            second = group[order[start + 1]]
            if first.material_id == second.material_id or first.label != second.label:
                raise RuntimeError("invalid same-class different-parent pair")
            pairs.append((first, second))

    rng.shuffle(pairs)
    pairs_per_batch = batch_size // 2
    batches: list[list[PeakRecord]] = []
    for start in range(0, len(pairs), pairs_per_batch):
        chunk = pairs[start : start + pairs_per_batch]
        batch = [record for pair in chunk for record in pair]
        for index in range(0, len(batch), 2):
            if batch[index].label != batch[index + 1].label:
                raise RuntimeError("same-class pair adjacency was lost")
            if batch[index].material_id == batch[index + 1].material_id:
                raise RuntimeError("same parent entered a same-class pair")
        batches.append(batch)
    return batches, dropped


def logits(model: torch.nn.Module, values: torch.Tensor) -> torch.Tensor:
    output = model(values)
    if isinstance(output, dict):
        value = output.get("logits")
        if not isinstance(value, torch.Tensor):
            raise RuntimeError("model output does not contain tensor logits")
        return value
    if not isinstance(output, torch.Tensor):
        raise RuntimeError("model output is not a tensor")
    return output


def paired_loss(
    arm: str,
    model: torch.nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    lambda_js: float,
) -> dict[str, torch.Tensor]:
    first = logits(model, x1)
    second = logits(model, x2)
    classification = 0.5 * (
        F.cross_entropy(first, target) + F.cross_entropy(second, target)
    )

    if arm == "same_parent_js":
        consistency = js_divergence(first, second)
    elif arm == "same_class_js":
        if len(target) % 2:
            raise RuntimeError("same-class JS requires an even parent count")
        partner = torch.arange(len(target), device=target.device)
        partner[0::2] += 1
        partner[1::2] -= 1
        if not torch.equal(target, target[partner]):
            raise RuntimeError("same-class JS partner has a different class label")
        consistency = js_divergence(first, second[partner])
    else:
        raise ValueError(f"unknown arm: {arm}")

    return {
        "classification": classification,
        "consistency": consistency,
        "total": classification + float(lambda_js) * consistency,
    }


def numpy_to_device(
    values: np.ndarray,
    device: torch.device,
    *,
    pin_memory: bool,
    non_blocking: bool,
) -> torch.Tensor:
    tensor = torch.from_numpy(np.asarray(values, dtype=np.float32))
    if pin_memory and device.type == "cuda":
        tensor = tensor.pin_memory()
    return tensor.to(device, non_blocking=non_blocking)


def labels_to_device(
    batch: Sequence[PeakRecord],
    device: torch.device,
    *,
    pin_memory: bool,
    non_blocking: bool,
) -> torch.Tensor:
    tensor = torch.tensor([record.label for record in batch], dtype=torch.long)
    if pin_memory and device.type == "cuda":
        tensor = tensor.pin_memory()
    return tensor.to(device, non_blocking=non_blocking)


def evaluate_profiles(
    model: torch.nn.Module,
    validation_records: Sequence[PeakRecord],
    peaks: dict[str, Any],
    factory: OnlineViewFactory,
    device: torch.device,
    batch_size: int,
) -> dict[str, Any]:
    profiles = ("in_range",) + SINGLE_OOD
    output = {
        profile: evaluate(
            model,
            validation_records,
            peaks,
            factory,
            batch_size=batch_size,
            profile=profile,
            device=device,
        )
        for profile in profiles
    }
    output["mean_single_ood_macro_f1"] = float(
        np.mean([float(output[profile]["macro_f1"]) for profile in SINGLE_OOD])
    )
    output["mean_single_ood_accuracy"] = float(
        np.mean([float(output[profile]["accuracy"]) for profile in SINGLE_OOD])
    )
    return output


def train_arm(
    *,
    arm: str,
    seed: int,
    train_records: Sequence[PeakRecord],
    validation_records: Sequence[PeakRecord],
    validation_peaks: dict[str, Any],
    simulation: dict[str, Any],
    output_dir: Path,
    device: torch.device,
    epochs: int,
    batch_size: int,
    eval_batch_size: int,
    learning_rate: float,
    weight_decay: float,
    lambda_js: float,
    validation_every: int,
    min_epochs: int,
    patience: int,
    min_delta: float,
    evaluation_seed: int,
    prefetch_workers: int,
    prefetch_batches: int,
    prefetch_worker_native_threads: int,
    pin_memory: bool,
    non_blocking_h2d: bool,
    quality_gate: bool,
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    sampler_config = {**simulation, "run_seed": int(seed)}
    train_sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    eval_sampler = PhysicsParameterSampler.from_mapping(
        {**simulation, "run_seed": int(evaluation_seed)}
    )
    eval_factory = OnlineViewFactory(eval_sampler)

    model = build_model(ML4PXRDResNet1DConfig(model_id="18")).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    rng = np.random.default_rng(seed)
    global_step = 0
    best_score = float("-inf")
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    patience_anchor = float("-inf")
    stale_checks = 0
    history: list[dict[str, Any]] = []
    total_prefetch_wait = 0.0
    training_started = time.perf_counter()

    simulation_hash = hashlib.sha256(SIMULATION_CONFIG.read_bytes()).hexdigest()
    prefetcher = DynamicBatchPrefetcher(
        worker_count=prefetch_workers,
        worker_native_threads=prefetch_worker_native_threads,
        prefetch_batches=prefetch_batches,
        start_method="spawn",
        data_root=DATA_ROOT,
        peak_cache_name=PEAK_CACHE_NAME,
        sampler_config=sampler_config,
        quality_gate=quality_gate,
        quality_gate_config=simulation.get("quality_gates", {}),
        simulation_config_hash=simulation_hash,
        profile="train",
    )

    try:
        for epoch in range(1, epochs + 1):
            epoch_started = time.perf_counter()
            batches, dropped = make_same_class_batches(
                train_records, rng, batch_size
            )
            model.train()
            sums = {"classification": 0.0, "consistency": 0.0, "total": 0.0}
            seen = 0
            epoch_prefetch_wait = 0.0
            epoch_base_key = global_step

            def submit(batch_index: int) -> None:
                batch = batches[batch_index]
                material_ids = [record.material_id for record in batch]
                # Match the historical formal-training coordinate convention:
                # epoch and step together identify a view; step resets each epoch.
                rows = build_parameter_batch(
                    material_ids,
                    train_sampler,
                    profile="train",
                    epoch=epoch - 1,
                    global_step=batch_index,
                    split="train",
                )
                prefetcher.submit(
                    epoch_base_key + batch_index,
                    material_ids,
                    rows,
                )

            initial = min(prefetch_batches, len(batches))
            for batch_index in range(initial):
                submit(batch_index)

            for batch_index, batch in enumerate(batches):
                wait_started = time.perf_counter()
                rendered = prefetcher.get(epoch_base_key + batch_index)
                waited = time.perf_counter() - wait_started
                epoch_prefetch_wait += waited
                total_prefetch_wait += waited

                refill = batch_index + prefetch_batches
                if refill < len(batches):
                    submit(refill)

                expected_ids = tuple(record.material_id for record in batch)
                if rendered.material_ids != expected_ids:
                    raise RuntimeError(
                        f"prefetch batch identity mismatch: "
                        f"{rendered.material_ids} != {expected_ids}"
                    )

                x1 = numpy_to_device(
                    rendered.first,
                    device,
                    pin_memory=pin_memory,
                    non_blocking=non_blocking_h2d,
                )
                x2 = numpy_to_device(
                    rendered.second,
                    device,
                    pin_memory=pin_memory,
                    non_blocking=non_blocking_h2d,
                )
                target = labels_to_device(
                    batch,
                    device,
                    pin_memory=pin_memory,
                    non_blocking=non_blocking_h2d,
                )

                optimizer.zero_grad(set_to_none=True)
                loss = paired_loss(arm, model, x1, x2, target, lambda_js)
                loss["total"].backward()
                optimizer.step()

                count = len(batch)
                for key in sums:
                    sums[key] += float(loss[key].detach()) * count
                seen += count
                global_step += 1

            epoch_seconds = time.perf_counter() - epoch_started
            item: dict[str, Any] = {
                "epoch": epoch,
                "global_step": global_step,
                "train": {key: value / seen for key, value in sums.items()},
                "train_parent_count": seen,
                "dropped_odd_class_parent_ids": dropped,
                "runtime": {
                    "epoch_seconds": epoch_seconds,
                    "prefetch_wait_seconds": epoch_prefetch_wait,
                    "quality_checked_count_total": prefetcher.quality_gate_checked_count,
                    "quality_rejected_count_total": prefetcher.quality_gate_rejected_count,
                },
            }

            print(
                f"seed={seed} arm={arm} epoch={epoch}/{epochs} "
                f"train={epoch_seconds:.1f}s prefetch_wait={epoch_prefetch_wait:.1f}s",
                flush=True,
            )

            if epoch % validation_every == 0 or epoch == epochs:
                metrics = evaluate_profiles(
                    model,
                    validation_records,
                    validation_peaks,
                    eval_factory,
                    device,
                    eval_batch_size,
                )
                score = float(metrics["mean_single_ood_macro_f1"])
                item["validation"] = metrics
                print(
                    f"  Validation: in={metrics['in_range']['macro_f1']:.4f}, "
                    f"meanOOD={score:.4f}",
                    flush=True,
                )

                if score > best_score:
                    best_score = score
                    best_epoch = epoch
                    best_state = {
                        key: value.detach().cpu().clone()
                        for key, value in model.state_dict().items()
                    }
                if score > patience_anchor + min_delta:
                    patience_anchor = score
                    stale_checks = 0
                else:
                    stale_checks += 1

            history.append(item)
            write_json(output_dir / "history.json", history)

            if epoch >= min_epochs and stale_checks >= patience:
                print(
                    f"early stop: seed={seed} arm={arm} epoch={epoch}",
                    flush=True,
                )
                break
    finally:
        prefetcher.close()

    if best_state is None:
        raise RuntimeError("no validation checkpoint was selected")

    model.load_state_dict(best_state)
    final_validation = evaluate_profiles(
        model,
        validation_records,
        validation_peaks,
        eval_factory,
        device,
        eval_batch_size,
    )
    torch.save(
        {
            "model": best_state,
            "seed": seed,
            "arm": arm,
            "best_epoch": best_epoch,
            "lambda_js": lambda_js,
            "pairing": (
                "same-parent"
                if arm == "same_parent_js"
                else "same-class-different-parent"
            ),
        },
        output_dir / "best.pt",
    )

    result = {
        "arm": arm,
        "seed": seed,
        "best_epoch": best_epoch,
        "epochs_completed": len(history),
        "global_step": global_step,
        "lambda_js": lambda_js,
        "validation": final_validation,
        "runtime": {
            "training_seconds": time.perf_counter() - training_started,
            "prefetch_wait_seconds": total_prefetch_wait,
        },
        "optimization": {
            "prefetch_workers": prefetch_workers,
            "prefetch_batches": prefetch_batches,
            "worker_native_threads": prefetch_worker_native_threads,
            "pin_memory": pin_memory,
            "non_blocking_h2d": non_blocking_h2d,
            "quality_gate": quality_gate,
        },
    }
    write_json(output_dir / "result.json", result)
    return result


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_seed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        by_seed[int(result["seed"])][str(result["arm"])] = result

    comparisons: list[dict[str, Any]] = []
    for seed in sorted(by_seed):
        arms = by_seed[seed]
        if not all(name in arms for name in ARMS):
            continue
        parent = arms["same_parent_js"]["validation"]
        same_class = arms["same_class_js"]["validation"]
        comparisons.append(
            {
                "seed": seed,
                "same_parent_mean_ood_macro_f1": parent[
                    "mean_single_ood_macro_f1"
                ],
                "same_class_mean_ood_macro_f1": same_class[
                    "mean_single_ood_macro_f1"
                ],
                "parent_minus_same_class_mean_ood_macro_f1": (
                    parent["mean_single_ood_macro_f1"]
                    - same_class["mean_single_ood_macro_f1"]
                ),
                "same_parent_in_range_macro_f1": parent["in_range"]["macro_f1"],
                "same_class_in_range_macro_f1": same_class["in_range"]["macro_f1"],
                "profile_delta_macro_f1": {
                    profile: (
                        parent[profile]["macro_f1"]
                        - same_class[profile]["macro_f1"]
                    )
                    for profile in SINGLE_OOD
                },
            }
        )

    deltas = [
        row["parent_minus_same_class_mean_ood_macro_f1"]
        for row in comparisons
    ]
    return {
        "scientific_question": (
            "Is parent identity better than generic same-class consistency?"
        ),
        "interpretation_rule": (
            "same_parent_js > same_class_js supports parent-specific relational "
            "information; similar performance means parent specificity is not "
            "established by this ablation"
        ),
        "comparisons": comparisons,
        "mean_parent_minus_same_class_macro_f1": (
            float(np.mean(deltas)) if deltas else None
        ),
        "all_compared_seeds_parent_higher": bool(
            deltas and all(delta > 0 for delta in deltas)
        ),
        "note": (
            "Validation-only post-hoc mechanism ablation; frozen simulated Test "
            "is not accessed."
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seeds", type=int, nargs="+", default=None)
    parser.add_argument(
        "--full-seeds",
        action="store_true",
        help="run all five original training seeds",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="one-night pilot: 60 epochs, min 40, patience 2",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate local data and pair construction without training",
    )
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--min-epochs", type=int, default=None)
    parser.add_argument("--patience", type=int, default=None)
    parser.add_argument("--validation-every", type=int, default=10)
    parser.add_argument("--min-delta", type=float, default=0.002)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--eval-batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--lambda-js", type=float, default=60.0)
    parser.add_argument("--evaluation-seed", type=int, default=20260720)
    parser.add_argument("--prefetch-workers", type=int, default=16)
    parser.add_argument("--prefetch-batches", type=int, default=6)
    parser.add_argument("--prefetch-worker-native-threads", type=int, default=1)
    parser.add_argument(
        "--pin-memory",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--non-blocking-h2d",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--quality-gate",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--device", default="auto")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    seeds = tuple(args.seeds or (FULL_SEEDS if args.full_seeds else (20260711,)))
    epochs = int(
        args.epochs if args.epochs is not None else (60 if args.quick else 100)
    )
    min_epochs = int(
        args.min_epochs
        if args.min_epochs is not None
        else (40 if args.quick else 50)
    )
    patience = int(
        args.patience if args.patience is not None else (2 if args.quick else 3)
    )

    if args.batch_size <= 0 or args.batch_size % 2:
        raise SystemExit("--batch-size must be a positive even number")
    if args.prefetch_workers <= 0:
        raise SystemExit("--prefetch-workers must be positive")
    if args.prefetch_workers > args.batch_size:
        raise SystemExit("--prefetch-workers cannot exceed --batch-size")
    if args.prefetch_batches <= 0 or args.prefetch_worker_native_threads <= 0:
        raise SystemExit("prefetch settings must be positive")
    if args.non_blocking_h2d and not args.pin_memory:
        raise SystemExit("--non-blocking-h2d requires --pin-memory")
    if epochs <= 0 or min_epochs <= 0 or min_epochs > epochs:
        raise SystemExit("invalid epoch settings")

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but unavailable")
    if device.type == "cpu" and not args.dry_run:
        print(
            "warning: CUDA is unavailable; this ablation is intended for GPU use",
            file=sys.stderr,
            flush=True,
        )

    records, metadata = load_local_records()
    train_records = [record for record in records if record.split == "train"]
    validation_records = [record for record in records if record.split == "validation"]
    simulation = json.loads(SIMULATION_CONFIG.read_text(encoding="utf-8"))

    probe_rng = np.random.default_rng(seeds[0])
    probe_batches, dropped = make_same_class_batches(
        train_records, probe_rng, args.batch_size
    )
    first_batch = probe_batches[0]
    preflight = {
        **metadata,
        "device": str(device),
        "seeds": list(seeds),
        "epochs": epochs,
        "min_epochs": min_epochs,
        "patience": patience,
        "lambda_js": args.lambda_js,
        "batch_size": args.batch_size,
        "spectra_per_update": args.batch_size * 2,
        "pairing_check": [
            {
                "a": first_batch[index].material_id,
                "b": first_batch[index + 1].material_id,
                "class": CRYSTAL_SYSTEMS[first_batch[index].label],
                "different_parent": (
                    first_batch[index].material_id
                    != first_batch[index + 1].material_id
                ),
            }
            for index in range(0, min(len(first_batch), 8), 2)
        ],
        "odd_class_parents_dropped_in_probe_epoch": dropped,
        "important_control": (
            "both arms use identical parents, identical two rendered views and "
            "identical CE; same_class_js only permutes second-view logits inside JS"
        ),
        "optimization": {
            "restored_historical_dynamic_prefetch": True,
            "generation": PREFETCH_GENERATION,
            "prefetch_workers": args.prefetch_workers,
            "prefetch_batches": args.prefetch_batches,
            "worker_native_threads": args.prefetch_worker_native_threads,
            "worker_thread_policy": PREFETCH_WORKER_THREAD_POLICY,
            "sharding": PREFETCH_SHARDING_ALGORITHM,
            "result_order": PREFETCH_RESULT_ORDER,
            "worker_peak_cache": PREFETCH_WORKER_PEAK_CACHE,
            "pin_memory": args.pin_memory,
            "non_blocking_h2d": args.non_blocking_h2d,
            "quality_gate": args.quality_gate,
        },
        "test_access": False,
    }

    output_root = args.output_root.resolve()
    write_json(output_root / "preflight.json", preflight)
    print(json.dumps(preflight, indent=2, sort_keys=True), flush=True)
    if args.dry_run:
        return 0

    validation_peaks = load_validation_peaks(validation_records)
    all_results: list[dict[str, Any]] = []
    for seed in seeds:
        for arm in ARMS:
            result = train_arm(
                arm=arm,
                seed=int(seed),
                train_records=train_records,
                validation_records=validation_records,
                validation_peaks=validation_peaks,
                simulation=simulation,
                output_dir=output_root / f"seed_{seed}" / arm,
                device=device,
                epochs=epochs,
                batch_size=args.batch_size,
                eval_batch_size=args.eval_batch_size,
                learning_rate=args.learning_rate,
                weight_decay=args.weight_decay,
                lambda_js=args.lambda_js,
                validation_every=args.validation_every,
                min_epochs=min_epochs,
                patience=patience,
                min_delta=args.min_delta,
                evaluation_seed=args.evaluation_seed,
                prefetch_workers=args.prefetch_workers,
                prefetch_batches=args.prefetch_batches,
                prefetch_worker_native_threads=args.prefetch_worker_native_threads,
                pin_memory=args.pin_memory,
                non_blocking_h2d=args.non_blocking_h2d,
                quality_gate=args.quality_gate,
            )
            all_results.append(result)
            write_json(output_root / "partial_results.json", all_results)

    summary = summarize(all_results)
    write_json(output_root / "summary.json", summary)
    print("\n=== Pairing ablation summary ===")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
