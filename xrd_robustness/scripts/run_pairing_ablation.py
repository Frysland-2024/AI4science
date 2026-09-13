#!/usr/bin/env python3
"""Controlled same-parent vs same-class JS pairing ablation for PXRD.

Scientific question
-------------------
Does JS benefit specifically from parent identity, or would any two different
structures from the same crystal system work similarly?

Both arms see exactly the same parent structures, exactly the same two rendered
views, the same CE supervision, optimizer, model initialization, and validation
spectra.  The only difference is which second-view prediction is paired with
the first-view prediction inside the JS term:

- ``same_parent_js``: view-1(parent A) <-> view-2(parent A)
- ``same_class_js``:  view-1(parent A) <-> view-2(parent B), A != B,
  where A and B have the same crystal-system label.

Training batches are built from adjacent same-class parent pairs.  Thus both
arms still use 16 parents x 2 views = 32 spectra/update.  The same-class arm is
implemented only by permuting already-rendered second-view logits inside JS;
it gets no extra spectra or model forwards.

This is a post-hoc mechanism ablation.  It does not replace the frozen main
ERM-vs-JS result and it deliberately does not access simulated Test.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import random
import sys
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
    render_pair_batch,
)


DATA_CONFIG = ROOT / "configs/data.method_transfer.structure_split.json"
SIMULATION_CONFIG = ROOT / "configs/simulation.method_transfer.frozen.json"
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
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_project_path(value: str) -> Path:
    path = (ROOT / value).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        raise ValueError(f"path leaves xrd_robustness root: {value}")
    return path


def load_local_records() -> tuple[list[PeakRecord], dict[str, Any]]:
    """Join the frozen split manifest to the local V7 ideal-peak cache."""
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

    train = [r for r in records if r.split == "train"]
    validation = [r for r in records if r.split == "validation"]
    expected = data["split"]["counts"]
    if len(train) != int(expected["train"]) or len(validation) != int(expected["validation"]):
        raise RuntimeError(
            f"local record counts differ from frozen split: train={len(train)}, "
            f"validation={len(validation)}"
        )
    metadata = {
        "data_config": str(DATA_CONFIG),
        "split_manifest": str(split_path),
        "peak_manifest": str(peak_manifest_path),
        "train_count": len(train),
        "validation_count": len(validation),
        "train_per_class": {
            CRYSTAL_SYSTEMS[label]: sum(r.label == label for r in train)
            for label in range(len(CRYSTAL_SYSTEMS))
        },
    }
    return records, metadata


def load_peaks(records: Sequence[PeakRecord]) -> dict[str, Any]:
    print(f"Loading {len(records)} ideal peak tables...", flush=True)
    return {
        record.material_id: load_peak_table(record.peak_table_path)
        for record in records
    }


def make_same_class_batches(
    records: Sequence[PeakRecord],
    rng: np.random.Generator,
    batch_size: int,
) -> tuple[list[list[PeakRecord]], list[str]]:
    """Make batches where adjacent records are different parents of one class.

    A class with an odd number of parents contributes one randomly rotated
    omission in that epoch.  In formal_14060 this is at most one parent per odd
    class, i.e. <0.1% of the training set, and the omitted identity changes
    with the epoch permutation.
    """
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
                raise RuntimeError("invalid same-class parent pair")
            pairs.append((first, second))

    rng.shuffle(pairs)
    pairs_per_batch = batch_size // 2
    batches: list[list[PeakRecord]] = []
    for start in range(0, len(pairs), pairs_per_batch):
        chunk = pairs[start : start + pairs_per_batch]
        batch = [record for pair in chunk for record in pair]
        for index in range(0, len(batch), 2):
            if batch[index].label != batch[index + 1].label:
                raise RuntimeError("pair adjacency was lost")
            if batch[index].material_id == batch[index + 1].material_id:
                raise RuntimeError("same parent entered a same-class pair")
        batches.append(batch)
    return batches, dropped


def logits(model: torch.nn.Module, x: torch.Tensor) -> torch.Tensor:
    output = model(x)
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
    """Keep CE/data fixed and change only the pairing used by JS."""
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
            raise RuntimeError("same-class JS partner has a different label")
        # Only this permutation differs between the two arms.
        consistency = js_divergence(first, second[partner])
    else:
        raise ValueError(f"unknown arm: {arm}")

    return {
        "classification": classification,
        "consistency": consistency,
        "total": classification + float(lambda_js) * consistency,
    }


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
        np.mean([float(output[p]["macro_f1"]) for p in SINGLE_OOD])
    )
    output["mean_single_ood_accuracy"] = float(
        np.mean([float(output[p]["accuracy"]) for p in SINGLE_OOD])
    )
    return output


def train_arm(
    *,
    arm: str,
    seed: int,
    train_records: Sequence[PeakRecord],
    validation_records: Sequence[PeakRecord],
    peaks: dict[str, Any],
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
) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reset all random state before every arm.  With the same seed, both arms
    # therefore receive the same model initialization, batch order and views.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    train_sampler = PhysicsParameterSampler.from_mapping(
        {**simulation, "run_seed": int(seed)}
    )
    eval_sampler = PhysicsParameterSampler.from_mapping(
        {**simulation, "run_seed": int(evaluation_seed)}
    )
    train_factory = OnlineViewFactory(train_sampler)
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

    for epoch in range(1, epochs + 1):
        batches, dropped = make_same_class_batches(train_records, rng, batch_size)
        model.train()
        sums = {"classification": 0.0, "consistency": 0.0, "total": 0.0}
        seen = 0

        for batch in batches:
            x1, x2, target = render_pair_batch(
                batch,
                peaks,
                train_factory,
                epoch=epoch,
                global_step=global_step,
                profile="train",
            )
            x1 = x1.to(device)
            x2 = x2.to(device)
            target = target.to(device)

            optimizer.zero_grad(set_to_none=True)
            loss = paired_loss(arm, model, x1, x2, target, lambda_js)
            loss["total"].backward()
            optimizer.step()

            n = len(batch)
            for key in sums:
                sums[key] += float(loss[key].detach()) * n
            seen += n
            global_step += 1

        item: dict[str, Any] = {
            "epoch": epoch,
            "global_step": global_step,
            "train": {key: value / seen for key, value in sums.items()},
            "train_parent_count": seen,
            "dropped_odd_class_parent_ids": dropped,
        }

        if epoch % validation_every == 0 or epoch == epochs:
            metrics = evaluate_profiles(
                model,
                validation_records,
                peaks,
                eval_factory,
                device,
                eval_batch_size,
            )
            score = float(metrics["mean_single_ood_macro_f1"])
            item["validation"] = metrics
            print(
                f"seed={seed} arm={arm} epoch={epoch}: "
                f"in={metrics['in_range']['macro_f1']:.4f}, meanOOD={score:.4f}",
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
            break

    if best_state is None:
        raise RuntimeError("no validation checkpoint was selected")

    model.load_state_dict(best_state)
    final_validation = evaluate_profiles(
        model,
        validation_records,
        peaks,
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
    parser.add_argument("--device", default="auto")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    seeds = tuple(
        args.seeds
        or (FULL_SEEDS if args.full_seeds else (20260711,))
    )
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
    if args.batch_size % 2:
        raise SystemExit("--batch-size must be even")
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
            "warning: CUDA is unavailable; this ablation is intended for a GPU and may be slow on CPU",
            file=sys.stderr,
            flush=True,
        )

    records, metadata = load_local_records()
    train_records = [record for record in records if record.split == "train"]
    validation_records = [
        record for record in records if record.split == "validation"
    ]
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
        "test_access": False,
    }
    output_root = args.output_root.resolve()
    write_json(output_root / "preflight.json", preflight)
    print(json.dumps(preflight, indent=2, sort_keys=True), flush=True)
    if args.dry_run:
        return 0

    peaks = load_peaks(records)
    all_results: list[dict[str, Any]] = []
    for seed in seeds:
        for arm in ARMS:
            result = train_arm(
                arm=arm,
                seed=int(seed),
                train_records=train_records,
                validation_records=validation_records,
                peaks=peaks,
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
