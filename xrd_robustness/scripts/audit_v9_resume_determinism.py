"""Bounded end-to-end checkpoint/resume determinism audit for V9-T.

This is an engineering audit, not a tuning run.  It uses a tiny PAMPT model,
real cached reflection tables, and the frozen V9 dynamic renderer for six
optimizer steps.  Simulated Test and real XRD are never loaded.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np

# Required by PyTorch for deterministic CUDA GEMM on CUDA >= 10.2.  Set it
# before importing torch or creating any CUDA context.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]

from xrd_robustness.experiment import file_hash, load_checkpoint, save_checkpoint
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.structure_split import load_split_manifest
from xrd_robustness.training import dynamic_erm
from xrd_robustness.training_prefetch import render_dynamic_batch
from xrd_robustness.training_stream import (
    TrainingStreamAudit,
    build_training_sampler_contract,
    deterministic_epoch_shuffle,
    paired_manifest_ids,
    select_epoch_batch,
    training_sampler_contract_hash,
)
from xrd_robustness.view_manifest import build_parameter_batch


SCHEMA_VERSION = "v9-resume-determinism-audit-v1"
SEED = 20260722
EPOCHS = 3
STEPS_PER_EPOCH = 2
BATCH_SIZE = 4
INTERRUPT_AFTER_EPOCH = 1


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _state_sha256(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        array = tensor.detach().cpu().contiguous().numpy()
        digest.update(name.encode("utf-8"))
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes())
    return digest.hexdigest().upper()


def _set_seed(seed: int, device: torch.device) -> None:
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)


def _small_model(device: torch.device) -> PAMPT:
    config = PAMPTConfig(
        variant="b0",
        embed_dim=32,
        depth=1,
        num_heads=4,
        mlp_ratio=2.0,
        dropout=0.1,
    )
    return PAMPT(config).to(device)


def _label_map(split_manifest: Path) -> tuple[list[str], dict[str, int]]:
    systems = (
        "cubic",
        "hexagonal",
        "monoclinic",
        "orthorhombic",
        "tetragonal",
        "triclinic",
        "trigonal",
    )
    rows = load_split_manifest(split_manifest)["records"]
    train_rows = sorted(
        (row for row in rows if row["split"] == "train"),
        key=lambda row: row["material_id"],
    )
    chosen = [row["material_id"] for row in train_rows[: 2 * BATCH_SIZE]]
    labels = {
        row["material_id"]: systems.index(row["crystal_system"])
        for row in train_rows
        if row["material_id"] in set(chosen)
    }
    if len(chosen) != 2 * BATCH_SIZE or len(labels) != len(chosen):
        raise ValueError("resume audit could not select eight labeled Train structures")
    return chosen, labels


def _formal_batch_provider(
    *,
    data_root: Path,
    simulation_path: Path,
    split_manifest: Path,
) -> tuple[Sequence[str], Callable[[int, int, Sequence[str]], tuple[torch.Tensor, torch.Tensor, Sequence[Sequence[str]]]], Mapping[str, int]]:
    material_ids, labels = _label_map(split_manifest)
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation["run_seed"] = SEED
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation.get("quality_gates", {}),
        strategy=IndependentDynamicStrategy(sampler, config_hash=file_hash(simulation_path)),
    )
    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    peaks = {material_id: load_peak_table(cache_root / f"{material_id}.npz") for material_id in material_ids}

    def provide(epoch: int, step: int, batch_ids: Sequence[str]) -> tuple[torch.Tensor, torch.Tensor, Sequence[Sequence[str]]]:
        rows = build_parameter_batch(
            batch_ids,
            sampler,
            profile="train",
            epoch=epoch,
            global_step=step,
            split="train",
        )
        rendered = render_dynamic_batch(
            epoch * STEPS_PER_EPOCH + step,
            batch_ids,
            rows,
            peaks=peaks,
            factory=factory,
            sampler=sampler,
            profile="train",
        )
        return (
            torch.from_numpy(rendered.first),
            torch.from_numpy(rendered.second),
            paired_manifest_ids(rendered.accepted_rows, batch_ids),
        )

    return material_ids, provide, labels


def _synthetic_batch_provider() -> tuple[Sequence[str], Callable[[int, int, Sequence[str]], tuple[torch.Tensor, torch.Tensor, Sequence[Sequence[str]]]], Mapping[str, int]]:
    material_ids = [f"synthetic-{index}" for index in range(2 * BATCH_SIZE)]
    labels = {material_id: index % 7 for index, material_id in enumerate(material_ids)}

    def provide(epoch: int, step: int, batch_ids: Sequence[str]) -> tuple[torch.Tensor, torch.Tensor, Sequence[Sequence[str]]]:
        arrays = []
        pairs = []
        for material_id in batch_ids:
            views = []
            ids = []
            for view_id in (1, 2):
                key = f"{SEED}:{epoch}:{step}:{material_id}:{view_id}"
                digest = hashlib.sha256(key.encode("utf-8")).digest()
                generator = torch.Generator().manual_seed(int.from_bytes(digest[:8], "big"))
                views.append(torch.rand(3501, generator=generator))
                ids.append(hashlib.sha256(("manifest:" + key).encode("utf-8")).hexdigest())
            arrays.append(views)
            pairs.append(tuple(ids))
        return (
            torch.stack([item[0] for item in arrays]),
            torch.stack([item[1] for item in arrays]),
            tuple(pairs),
        )

    return material_ids, provide, labels


def _run_segment(
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    audit: TrainingStreamAudit,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    provider: Callable[[int, int, Sequence[str]], tuple[torch.Tensor, torch.Tensor, Sequence[Sequence[str]]]],
    device: torch.device,
    start_epoch: int,
    stop_epoch: int,
) -> list[dict[str, Any]]:
    trace = []
    model.train()
    for epoch in range(start_epoch, stop_epoch):
        order = deterministic_epoch_shuffle(material_ids, seed=SEED, epoch=epoch)
        for step in range(STEPS_PER_EPOCH):
            batch_ids = select_epoch_batch(
                order,
                step=step,
                batch_size=BATCH_SIZE,
                full_batch=True,
            )
            first, second, parameter_pairs = provider(epoch, step, batch_ids)
            first = first.to(device=device, dtype=torch.float32)
            second = second.to(device=device, dtype=torch.float32)
            target = torch.tensor([labels[value] for value in batch_ids], device=device)
            optimizer.zero_grad(set_to_none=True)
            result = dynamic_erm(model, first, second, target)
            result["total"].backward()
            optimizer.step()
            absolute_step = epoch * STEPS_PER_EPOCH + step
            audit.record_batch(
                epoch=epoch,
                step=step,
                absolute_step=absolute_step,
                material_ids=batch_ids,
                parameter_pairs=parameter_pairs,
                views_per_structure=2,
            )
            trace.append(
                {
                    "epoch": epoch,
                    "step": step,
                    "global_step": absolute_step + 1,
                    "material_ids": list(batch_ids),
                    "parameter_pairs": [list(pair) for pair in parameter_pairs],
                    "loss": float(result["total"].detach().cpu()),
                    "stream_audit": audit.snapshot(),
                }
            )
    return trace


def run_audit(
    *,
    device: str = "cpu",
    synthetic: bool = False,
    data_root: Path | None = None,
    simulation_path: Path | None = None,
    split_manifest: Path | None = None,
) -> dict[str, Any]:
    resolved_device = torch.device(device)
    if resolved_device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    if resolved_device.type == "cuda":
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True

    if synthetic:
        material_ids, provider, labels = _synthetic_batch_provider()
        input_kind = "deterministic_synthetic_spectra"
    else:
        assert data_root is not None and simulation_path is not None and split_manifest is not None
        material_ids, provider, labels = _formal_batch_provider(
            data_root=data_root,
            simulation_path=simulation_path,
            split_manifest=split_manifest,
        )
        input_kind = "real_reflection_cache_plus_frozen_v9_dynamic_renderer"

    contract = build_training_sampler_contract(
        material_ids,
        seed=SEED,
        batch_size=BATCH_SIZE,
        steps_per_epoch=STEPS_PER_EPOCH,
        target_optimizer_steps=EPOCHS * STEPS_PER_EPOCH,
        full_batches=True,
    )
    contract_hash = training_sampler_contract_hash(contract)
    model_config = asdict(_small_model(torch.device("cpu")).config)
    started = time.perf_counter()

    _set_seed(SEED, resolved_device)
    uninterrupted_model = _small_model(resolved_device)
    uninterrupted_optimizer = torch.optim.AdamW(uninterrupted_model.parameters(), lr=1e-3)
    uninterrupted_audit = TrainingStreamAudit.create(contract_hash)
    uninterrupted_trace = _run_segment(
        model=uninterrupted_model,
        optimizer=uninterrupted_optimizer,
        audit=uninterrupted_audit,
        material_ids=material_ids,
        labels=labels,
        provider=provider,
        device=resolved_device,
        start_epoch=0,
        stop_epoch=EPOCHS,
    )

    _set_seed(SEED, resolved_device)
    interrupted_model = _small_model(resolved_device)
    interrupted_optimizer = torch.optim.AdamW(interrupted_model.parameters(), lr=1e-3)
    interrupted_audit = TrainingStreamAudit.create(contract_hash)
    prefix_trace = _run_segment(
        model=interrupted_model,
        optimizer=interrupted_optimizer,
        audit=interrupted_audit,
        material_ids=material_ids,
        labels=labels,
        provider=provider,
        device=resolved_device,
        start_epoch=0,
        stop_epoch=INTERRUPT_AFTER_EPOCH,
    )

    with tempfile.TemporaryDirectory(prefix="v9_resume_audit_") as directory:
        checkpoint = Path(directory) / "last.ckpt"
        save_checkpoint(
            checkpoint,
            model=interrupted_model,
            optimizers=[interrupted_optimizer],
            epoch=INTERRUPT_AFTER_EPOCH,
            global_step=INTERRUPT_AFTER_EPOCH * STEPS_PER_EPOCH,
            config=model_config,
            data_manifest_hash="resume-audit-data",
            view_manifest_hash="resume-audit-views",
            seed=SEED,
            provenance={"input_kind": input_kind},
            extra_state={
                "training_stream_audit": interrupted_audit.snapshot(),
                "training_sampler_contract_hash": contract_hash,
            },
        )
        checkpoint_hash = file_hash(checkpoint).upper()

        _set_seed(SEED + 999, resolved_device)
        resumed_model = _small_model(resolved_device)
        resumed_optimizer = torch.optim.AdamW(resumed_model.parameters(), lr=1e-3)
        payload = load_checkpoint(
            checkpoint,
            model=resumed_model,
            optimizers=[resumed_optimizer],
            map_location=resolved_device,
        )
        saved_extra = payload.get("extra_state", {})
        resumed_audit = TrainingStreamAudit.from_snapshot(
            saved_extra["training_stream_audit"],
            sampler_contract_hash=contract_hash,
        )
        suffix_trace = _run_segment(
            model=resumed_model,
            optimizer=resumed_optimizer,
            audit=resumed_audit,
            material_ids=material_ids,
            labels=labels,
            provider=provider,
            device=resolved_device,
            start_epoch=int(payload["epoch"]),
            stop_epoch=EPOCHS,
        )

    cut = INTERRUPT_AFTER_EPOCH * STEPS_PER_EPOCH
    expected_suffix = uninterrupted_trace[cut:]
    checks = {
        "checkpoint_epoch": int(payload["epoch"]) == INTERRUPT_AFTER_EPOCH,
        "checkpoint_global_step": int(payload["global_step"]) == cut,
        "checkpoint_contains_stream_audit": bool(saved_extra.get("training_stream_audit")),
        "subsequent_material_id_sequence": [row["material_ids"] for row in suffix_trace]
        == [row["material_ids"] for row in expected_suffix],
        "subsequent_parameter_pairs": [row["parameter_pairs"] for row in suffix_trace]
        == [row["parameter_pairs"] for row in expected_suffix],
        "next_loss_exact": suffix_trace[0]["loss"] == expected_suffix[0]["loss"],
        "final_global_step": suffix_trace[-1]["global_step"]
        == uninterrupted_trace[-1]["global_step"],
        "final_sampler_hash": resumed_audit.sampler_hash == uninterrupted_audit.sampler_hash,
        "final_pair_schedule_hash": resumed_audit.pair_schedule_hash
        == uninterrupted_audit.pair_schedule_hash,
        "final_parameter_pair_hash": resumed_audit.parameter_pair_hash
        == uninterrupted_audit.parameter_pair_hash,
        "final_stream_audit_snapshot": resumed_audit.snapshot() == uninterrupted_audit.snapshot(),
        "final_model_parameter_hash": _state_sha256(resumed_model)
        == _state_sha256(uninterrupted_model),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "bounded_engineering_audit_no_validation_no_simulated_test_no_real_test",
        "input_kind": input_kind,
        "device": str(resolved_device),
        "seed": SEED,
        "epochs": EPOCHS,
        "steps_per_epoch": STEPS_PER_EPOCH,
        "batch_size": BATCH_SIZE,
        "optimizer_steps": EPOCHS * STEPS_PER_EPOCH,
        "structure_exposures": EPOCHS * STEPS_PER_EPOCH * BATCH_SIZE,
        "spectrum_exposures": EPOCHS * STEPS_PER_EPOCH * BATCH_SIZE * 2,
        "interrupted_after_epoch": INTERRUPT_AFTER_EPOCH,
        "sampler_contract": contract,
        "sampler_contract_hash": contract_hash.upper(),
        "checkpoint_sha256": checkpoint_hash,
        "checks": checks,
        "next_step": {
            "uninterrupted": expected_suffix[0],
            "resumed": suffix_trace[0],
        },
        "final": {
            "uninterrupted_stream_audit": uninterrupted_audit.snapshot(),
            "resumed_stream_audit": resumed_audit.snapshot(),
            "uninterrupted_model_parameter_sha256": _state_sha256(uninterrupted_model),
            "resumed_model_parameter_sha256": _state_sha256(resumed_model),
        },
        "prefix_trace": prefix_trace,
        "elapsed_seconds": time.perf_counter() - started,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    parser.add_argument("--synthetic", action="store_true", help="portable test mode without project data")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_resume_determinism_audit.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    report = run_audit(
        device=device,
        synthetic=args.synthetic,
        data_root=PROJECT_ROOT / "data" / "formal_14060",
        simulation_path=PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json",
        split_manifest=PROJECT_ROOT / "data" / "formal_14060" / "manifests" / "split_manifest.json",
    )
    report["source_hashes"] = {
        "script": file_hash(Path(__file__)).upper(),
        "experiment": file_hash(PROJECT_ROOT / "src" / "xrd_robustness" / "experiment.py").upper(),
        "training_stream": file_hash(PROJECT_ROOT / "src" / "xrd_robustness" / "training_stream.py").upper(),
        "view_manifest": file_hash(PROJECT_ROOT / "src" / "xrd_robustness" / "view_manifest.py").upper(),
        "simulation_config": file_hash(PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json").upper(),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
