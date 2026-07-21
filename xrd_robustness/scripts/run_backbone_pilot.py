#!/usr/bin/env python3
"""Run the V7 Dynamic-ERM-only B0-B3 backbone pilot.

The script requires an explicit, non-smoke simulation JSON with evidence-backed
profiles. It records parameter manifests rather than rendered spectra.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.evaluation import classification_metrics, robustness_auc
from xrd_robustness.experiment import config_hash, file_hash, model_fingerprint, save_checkpoint
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS, select_nested_structure_records
from xrd_robustness.training import dynamic_erm
from xrd_robustness.view_manifest import (
    ViewManifestRow,
    build_parameter_stream,
    index_manifest,
    save_manifest,
)
from xrd_robustness.data_layout import project_relative_path, resolve_data_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation-config", required=True)
    parser.add_argument("--train-profile", required=True)
    parser.add_argument("--in-range-profile", required=True)
    parser.add_argument("--ood-profiles", required=True, help="comma-separated profile names")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seeds", default="20260711,20260712")
    parser.add_argument("--variants", default="b0,b1,b2,b3")
    parser.add_argument("--dataset-size", type=int, choices=[140, 3500, 14000, 14060], default=140)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data"))
    parser.add_argument("--peak-cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--output-dir", default=str(PROJECT_ROOT / "outputs" / "backbone_pilot"))
    return parser.parse_args()


def _load_records(dataset_size: int, data_root: Path) -> dict[str, dict]:
    path = data_root / "mp_processed" / "structure_records.jsonl"
    all_rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = select_nested_structure_records(all_rows, dataset_size=dataset_size)
    return {row["material_id"]: row for row in rows}


def _sampler_config(path: Path, seed: int) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    purpose = str(config.get("purpose", "")).lower()
    if "smoke" in purpose:
        raise ValueError("formal backbone pilot refuses a smoke-only simulation config")
    config["run_seed"] = int(seed)
    return config


def _view_batch(
    ids: list[str],
    *,
    epoch: int,
    step: int,
    view_index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, object],
    factory: OnlineViewFactory,
) -> tuple[torch.Tensor, torch.Tensor]:
    first, second = [], []
    for material_id in ids:
        pair = factory.make_pair_from_manifest(
            peaks[material_id],
            view_index[(material_id, epoch, step, 1)],
            view_index[(material_id, epoch, step, 2)],
        )
        first.append(pair.first.xrd)
        second.append(pair.second.xrd)
    return torch.from_numpy(np.stack(first)).float(), torch.from_numpy(np.stack(second)).float()


def _evaluate(
    model: PAMPT,
    ids: list[str],
    records: dict[str, dict],
    *,
    view_index: dict[tuple[str, int, int, int], ViewManifestRow],
    peaks: dict[str, object],
    factory: OnlineViewFactory,
) -> dict:
    model.eval()
    labels, predictions, probabilities = [], [], []
    with torch.no_grad():
        for material_id in ids:
            x1, x2 = _view_batch(
                [material_id],
                epoch=0,
                step=0,
                view_index=view_index,
                peaks=peaks,
                factory=factory,
            )
            output = model(x1)
            labels.append(records[material_id]["crystal_system"])
            probabilities.append(torch.softmax(output["logits"], dim=-1)[0].cpu().numpy())
            predictions.append(int(output["logits"].argmax(dim=-1)[0]))
    # The structure pilot stores labels as ordered crystal-system strings.
    label_ids = [CRYSTAL_SYSTEMS.index(label) for label in labels]
    return classification_metrics(label_ids, predictions, probabilities=np.stack(probabilities), num_classes=7)


def _make_manifest_set(
    sampler: PhysicsParameterSampler,
    *,
    ids: list[str],
    profile: str,
    split: str,
    epochs: int,
    steps_per_epoch: int,
    run_dir: Path,
    name: str,
) -> tuple[list[ViewManifestRow], dict[tuple[str, int, int, int], ViewManifestRow], str]:
    rows = build_parameter_stream(
        ids,
        sampler,
        profile=profile,
        epochs=epochs,
        steps_per_epoch=steps_per_epoch,
        split=split,
    )
    path = run_dir / f"{name}.jsonl"
    digest = save_manifest(rows, path)
    return rows, index_manifest(rows), digest


def main() -> int:
    args = parse_args()
    simulation_path = Path(args.simulation_config).resolve()
    data_root = resolve_data_root(PROJECT_ROOT, args.data_root)
    records = _load_records(args.dataset_size, data_root)
    train_ids = sorted(material_id for material_id, row in records.items() if row["split"] == "train")
    test_ids = sorted(material_id for material_id, row in records.items() if row["split"] == "test")
    steps_per_epoch = math.ceil(len(train_ids) / args.batch_size)
    seeds = [int(value) for value in args.seeds.split(",") if value.strip()]
    variants = [value.strip() for value in args.variants.split(",") if value.strip()]
    ood_profiles = [value.strip() for value in args.ood_profiles.split(",") if value.strip()]
    split_hash = file_hash(data_root / "manifests" / "split_manifest.csv")
    run_dir = Path(args.output_dir) / time.strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "simulation_config.json").write_text(simulation_path.read_text(encoding="utf-8"), encoding="utf-8")
    all_results = []

    for seed in seeds:
        torch.manual_seed(seed)
        sampler_config = _sampler_config(simulation_path, seed)
        sampler = PhysicsParameterSampler.from_mapping(sampler_config)
        factory = OnlineViewFactory(
            sampler,
            quality_gate=True,
            quality_gate_config=sampler_config.get("quality_gates", {}),
        )
        all_ids = sorted(set(train_ids + test_ids))
        peaks = {
            material_id: load_peak_table(
                data_root / "mp_processed" / args.peak_cache_name / f"{material_id}.npz"
            )
            for material_id in all_ids
        }
        train_rows, train_index, train_hash = _make_manifest_set(
            sampler,
            ids=train_ids,
            profile=args.train_profile,
            split="train",
            epochs=args.epochs,
            steps_per_epoch=steps_per_epoch,
            run_dir=run_dir,
            name=f"seed_{seed}_train_views",
        )
        test_rows, test_index, test_hash = _make_manifest_set(
            sampler,
            ids=test_ids,
            profile=args.in_range_profile,
            split="test",
            epochs=1,
            steps_per_epoch=1,
            run_dir=run_dir,
            name=f"seed_{seed}_test_in_range_views",
        )
        ood_indexes = {}
        ood_hashes = {}
        for profile in ood_profiles:
            _, ood_indexes[profile], ood_hashes[profile] = _make_manifest_set(
                sampler,
                ids=test_ids,
                profile=profile,
                split="test",
                epochs=1,
                steps_per_epoch=1,
                run_dir=run_dir,
                name=f"seed_{seed}_test_{profile}_views",
            )
        for variant in variants:
            model_config = PAMPTConfig(variant=variant)
            model = PAMPT(model_config)
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
            epoch_losses = []
            model.train()
            for epoch in range(args.epochs):
                step_losses = []
                for step in range(steps_per_epoch):
                    batch_ids = train_ids[step * args.batch_size : (step + 1) * args.batch_size]
                    x1, x2 = _view_batch(
                        batch_ids,
                        epoch=epoch,
                        step=step,
                        view_index=train_index,
                        peaks=peaks,
                        factory=factory,
                    )
                    optimizer.zero_grad(set_to_none=True)
                    result = dynamic_erm(model, x1, x2, torch.tensor([CRYSTAL_SYSTEMS.index(records[item]["crystal_system"]) for item in batch_ids]))
                    result["total"].backward()
                    optimizer.step()
                    step_losses.append(float(result["total"].detach()))
                epoch_losses.append(float(np.mean(step_losses)))
            test_metrics = _evaluate(model, test_ids, records, view_index=test_index, peaks=peaks, factory=factory)
            ood_metrics = {}
            ood_values = []
            ood_levels = []
            for profile, index in ood_indexes.items():
                metrics = _evaluate(model, test_ids, records, view_index=index, peaks=peaks, factory=factory)
                ood_metrics[profile] = metrics
                ood_values.append(metrics["macro_f1"])
                ood_levels.append(float(next(iter(index.values())).parameters["severity_level"]))
            fingerprint = model_fingerprint(model, model_config)
            result = {
                "seed": seed,
                "variant": variant,
                "epoch_losses": epoch_losses,
                "in_range": test_metrics,
                "ood": ood_metrics,
                "ood_macro_f1": float(np.mean(ood_values)) if ood_values else None,
                "robustness_auc": robustness_auc(ood_levels, ood_values) if len(ood_values) >= 2 else None,
                "model": fingerprint,
                "data_manifest_hash": split_hash,
                "view_manifest_hashes": {"train": train_hash, "test": test_hash, **ood_hashes},
            }
            all_results.append(result)
            save_checkpoint(
                run_dir / f"{variant}_seed_{seed}_last.ckpt",
                model=model,
                optimizers=[optimizer],
                epoch=args.epochs,
                global_step=args.epochs * steps_per_epoch,
                config=model_config,
                data_manifest_hash=split_hash,
                view_manifest_hash=config_hash(result["view_manifest_hashes"]),
                seed=seed,
            )
    (run_dir / "pilot_results.json").write_text(json.dumps(all_results, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "runs": len(all_results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
