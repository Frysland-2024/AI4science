#!/usr/bin/env python3
"""Run the preregistered Gate-3 ResNet implementation sanity checks.

The script uses only frozen Train structures. It renders one fixed ``level0``
view for a deterministic 32-structure subset, checks deterministic model
identity, runs a finite forward/backward pass at effective batch size 16, and
requires the model to overfit the fixed subset to at least 95% accuracy before
any full Validation experiment is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.experiment import config_hash, model_fingerprint  # noqa: E402
from xrd_robustness.models.ml4pxrd_resnet1d import (  # noqa: E402
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table, validate_peak_cache_manifest  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy  # noqa: E402
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS  # noqa: E402
from xrd_robustness.structure_split import load_split_manifest  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--simulation-config", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--peak-cache-name", default="peak_tables_v7_reflection")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260710)
    parser.add_argument("--tiny-size", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-overfit-steps", type=int, default=3000)
    parser.add_argument("--check-interval", type=int, default=20)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=0.0)
    parser.add_argument("--required-accuracy", type=float, default=0.95)
    parser.add_argument("--device", choices=["cuda", "cpu", "auto"], default="cuda")
    return parser.parse_args()


def _load_records(data_root: Path, split_manifest: Path) -> dict[str, dict[str, Any]]:
    records_path = data_root / "mp_processed" / "structure_records.jsonl"
    rows = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = {str(row["material_id"]): dict(row) for row in rows}
    if len(records) != len(rows):
        raise SystemExit("structure_records.jsonl contains duplicate material IDs")
    split_rows = load_split_manifest(split_manifest.resolve())["records"]
    if len(split_rows) != len(records):
        raise SystemExit("split manifest and structure records have different row counts")
    for split_row in split_rows:
        material_id = str(split_row["material_id"])
        if material_id not in records:
            raise SystemExit(f"split manifest contains unknown material ID: {material_id}")
        row = records[material_id]
        if str(split_row["crystal_system"]) != str(row["crystal_system"]):
            raise SystemExit(f"crystal-system mismatch for {material_id}")
        row["split"] = str(split_row["split"])
        row["parent_structure_id"] = str(split_row["parent_structure_id"])
    return records


def _select_balanced_train_ids(
    records: dict[str, dict[str, Any]],
    count: int,
) -> list[str]:
    if count < len(CRYSTAL_SYSTEMS):
        raise SystemExit("tiny-size must cover all seven crystal systems")
    buckets = {
        name: sorted(
            material_id
            for material_id, row in records.items()
            if row["split"] == "train" and row["crystal_system"] == name
        )
        for name in CRYSTAL_SYSTEMS
    }
    base, remainder = divmod(count, len(CRYSTAL_SYSTEMS))
    selected: list[str] = []
    for class_index, name in enumerate(CRYSTAL_SYSTEMS):
        take = base + (1 if class_index < remainder else 0)
        if len(buckets[name]) < take:
            raise SystemExit(f"not enough Train structures for {name}")
        selected.extend(buckets[name][:take])
    return selected


def _state_digest(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(np.asarray(tensor.detach().cpu()).tobytes(order="C"))
    return digest.hexdigest()


def _render_tiny_set(
    ids: list[str],
    records: dict[str, dict[str, Any]],
    *,
    data_root: Path,
    peak_cache_name: str,
    simulation_config: dict[str, Any],
    seed: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    sampler_mapping = dict(simulation_config)
    sampler_mapping["run_seed"] = int(seed)
    sampler = PhysicsParameterSampler.from_mapping(sampler_mapping)
    strategy = IndependentDynamicStrategy(sampler)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation_config.get("quality_gates", {}),
        strategy=strategy,
    )
    arrays: list[np.ndarray] = []
    labels: list[int] = []
    for material_id in ids:
        peaks = load_peak_table(
            data_root / "mp_processed" / peak_cache_name / f"{material_id}.npz"
        )
        view = factory.make_fixed_view_from_peaks(
            peaks,
            material_id=material_id,
            split="train",
            profile="level0",
        )
        arrays.append(np.asarray(view.xrd, dtype=np.float32))
        labels.append(CRYSTAL_SYSTEMS.index(records[material_id]["crystal_system"]))
    x = torch.from_numpy(np.stack(arrays, axis=0))
    y = torch.tensor(labels, dtype=torch.long)
    if not torch.isfinite(x).all():
        raise SystemExit("rendered tiny set contains non-finite values")
    return x, y


def _device(value: str) -> torch.device:
    if value == "auto":
        value = "cuda" if torch.cuda.is_available() else "cpu"
    if value == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but torch.cuda.is_available() is False")
    return torch.device(value)


def main() -> int:
    args = parse_args()
    if args.tiny_size != 32:
        raise SystemExit("Gate 3 preregisters exactly 32 structures for the tiny-set gate")
    if args.batch_size != 16:
        raise SystemExit("Gate 3 preregisters effective batch size 16")
    if not 0 < args.required_accuracy <= 1:
        raise SystemExit("required-accuracy must be in (0, 1]")
    if min(args.max_overfit_steps, args.check_interval) <= 0:
        raise SystemExit("step counts must be positive")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    simulation_path = args.simulation_config.resolve()
    data_root = args.data_root.resolve()
    split_manifest = args.split_manifest.resolve()
    simulation_config = json.loads(simulation_path.read_text(encoding="utf-8"))
    records = _load_records(data_root, split_manifest)
    validate_peak_cache_manifest(data_root, args.peak_cache_name, records)
    ids = _select_balanced_train_ids(records, args.tiny_size)
    x_cpu, y_cpu = _render_tiny_set(
        ids,
        records,
        data_root=data_root,
        peak_cache_name=args.peak_cache_name,
        simulation_config=simulation_config,
        seed=args.seed,
    )

    device = _device(args.device)
    if device.type == "cuda":
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
    config = ML4PXRDResNet1DConfig(model_id="18", input_length=int(x_cpu.shape[-1]))

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    first = ML4PXRDResNet1D(config)
    first_digest = _state_digest(first)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    second = ML4PXRDResNet1D(config)
    second_digest = _state_digest(second)
    deterministic_identity = first_digest == second_digest
    if not deterministic_identity:
        raise SystemExit("model initialization is not deterministic under the frozen seed")

    model = first.to(device)
    x = x_cpu.to(device)
    y = y_cpu.to(device)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    model.zero_grad(set_to_none=True)
    output = model(x[: args.batch_size])
    logits = output["logits"]
    loss = F.cross_entropy(logits, y[: args.batch_size])
    loss.backward()
    finite_forward = bool(torch.isfinite(logits).all() and torch.isfinite(loss))
    finite_gradients = all(
        parameter.grad is None or bool(torch.isfinite(parameter.grad).all())
        for parameter in model.parameters()
    )
    if not finite_forward or not finite_gradients:
        raise SystemExit("forward/backward gate produced non-finite values")
    peak_memory_mb = (
        float(torch.cuda.max_memory_allocated(device) / (1024**2))
        if device.type == "cuda"
        else None
    )

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    model = ML4PXRDResNet1D(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    achieved_accuracy = 0.0
    achieved_step: int | None = None
    consecutive_passes = 0
    trajectory: list[dict[str, float | int]] = []
    for step in range(1, args.max_overfit_steps + 1):
        start = ((step - 1) * args.batch_size) % args.tiny_size
        indices = torch.arange(start, start + args.batch_size, device=device) % args.tiny_size
        model.train()
        optimizer.zero_grad(set_to_none=True)
        batch_logits = model(x.index_select(0, indices))["logits"]
        batch_loss = F.cross_entropy(batch_logits, y.index_select(0, indices))
        batch_loss.backward()
        optimizer.step()

        if step % args.check_interval == 0 or step == args.max_overfit_steps:
            model.eval()
            with torch.no_grad():
                full_logits = model(x)["logits"]
                full_loss = float(F.cross_entropy(full_logits, y).detach().cpu())
                achieved_accuracy = float(
                    (full_logits.argmax(dim=-1) == y).float().mean().detach().cpu()
                )
            trajectory.append(
                {"step": step, "accuracy": achieved_accuracy, "loss": full_loss}
            )
            if achieved_accuracy >= args.required_accuracy:
                consecutive_passes += 1
            else:
                consecutive_passes = 0
            if consecutive_passes >= 3:
                achieved_step = step
                break

    tiny_overfit_passed = achieved_step is not None
    fingerprint = model_fingerprint(model, config)
    report = {
        "schema_version": "gate3_resnet_sanity.v1",
        "status": "pass" if tiny_overfit_passed else "fail",
        "scope": "Train-only fixed level0 sanity gate",
        "model": fingerprint,
        "model_config": {
            **config.__dict__,
            "config_hash": config_hash(config),
            "initial_state_sha256": first_digest,
        },
        "data": {
            "tiny_size": args.tiny_size,
            "effective_batch_size": args.batch_size,
            "material_ids": ids,
            "class_counts": {
                name: sum(records[item]["crystal_system"] == name for item in ids)
                for name in CRYSTAL_SYSTEMS
            },
            "input_shape": list(x_cpu.shape),
            "profile": "level0",
            "split": "train",
        },
        "checks": {
            "deterministic_identity": deterministic_identity,
            "finite_forward": finite_forward,
            "finite_gradients": finite_gradients,
            "memory_gate": {
                "passed": True,
                "device": str(device),
                "peak_allocated_mb": peak_memory_mb,
            },
            "tiny_set_overfit": {
                "passed": tiny_overfit_passed,
                "required_accuracy": args.required_accuracy,
                "achieved_accuracy": achieved_accuracy,
                "achieved_step": achieved_step,
                "maximum_steps": args.max_overfit_steps,
                "check_interval": args.check_interval,
                "required_consecutive_checks": 3,
                "optimizer": "AdamW",
                "learning_rate": args.learning_rate,
                "weight_decay": args.weight_decay,
                "trajectory": trajectory,
            },
        },
        "interpretation_boundary": (
            "This report validates implementation and optimization on frozen Train views only. "
            "It contains no Validation, simulated Test, or real-XRD evidence."
        ),
    }
    json_path = output_dir / "gate3_resnet_sanity.json"
    md_path = output_dir / "gate3_resnet_sanity.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    md_lines = [
        "# Gate 3 ResNet sanity report",
        "",
        f"- Status: **{report['status']}**",
        f"- Deterministic initialization: **{deterministic_identity}**",
        f"- Finite forward/backward: **{finite_forward and finite_gradients}**",
        f"- Parameter count: **{fingerprint['parameter_count']}**",
        f"- Peak allocated memory: **{peak_memory_mb if peak_memory_mb is not None else 'CPU'} MB**",
        f"- Tiny-set accuracy: **{achieved_accuracy:.4f}**",
        f"- Tiny-set pass step: **{achieved_step}**",
        "",
        report["interpretation_boundary"],
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print("\n".join(md_lines))
    print(f"JSON: {json_path}")
    print(f"Markdown: {md_path}")
    return 0 if tiny_overfit_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
