"""ResNet-18-GN training runner for Dynamic ERM and Dynamic JS."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
from typing import Any, Sequence

import numpy as np
import torch

from ..evaluation.metrics import classification_metrics
from ..experiment import config_hash, file_hash, save_checkpoint
from ..models import ML4PXRDResNet1D, ML4PXRDResNet1DConfig
from ..online_views import OnlineViewFactory, TrainingMode
from ..peak_cache import load_peak_table
from ..physics import PhysicsParameterSampler
from ..simulation_interfaces import PeakTable
from ..structure_data import CRYSTAL_SYSTEMS
from .trainer_factory import TrainingStepConfig, run_training_step


@dataclass(frozen=True)
class PeakRecord:
    """One labeled ideal peak table used for transient online rendering."""

    material_id: str
    label: int
    split: str
    peak_table_path: Path


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _label_from_row(row: dict[str, Any], line_number: int) -> int:
    if "label" in row:
        label = int(row["label"])
    elif "crystal_system" in row:
        try:
            label = CRYSTAL_SYSTEMS.index(str(row["crystal_system"]))
        except ValueError as error:
            raise ValueError(
                f"record line {line_number} has an unknown crystal_system"
            ) from error
    else:
        raise ValueError(f"record line {line_number} requires label or crystal_system")
    if not 0 <= label < len(CRYSTAL_SYSTEMS):
        raise ValueError(f"record line {line_number} label must be in [0, 6]")
    return label


def load_peak_records(path: str | Path) -> list[PeakRecord]:
    """Load the public JSONL contract without accepting embedded spectra.

    Each line requires ``material_id``, ``split`` (``train`` or
    ``validation``), ``peak_table_path`` and either ``label`` or
    ``crystal_system``.  The path points to a non-pickle ``.npz`` ideal peak
    table produced by ``scripts/precompute_peak_tables.py``.
    """

    source = Path(path).resolve()
    records: list[PeakRecord] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(
        source.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError(f"record line {line_number} must be a JSON object")
        material_id = str(row.get("material_id", "")).strip()
        if not material_id or material_id in seen:
            raise ValueError(
                f"record line {line_number} has an empty or duplicate material_id"
            )
        split = str(row.get("split", "")).strip()
        if split not in {"train", "validation"}:
            raise ValueError(
                f"record line {line_number} split must be train or validation"
            )
        raw_path = row.get("peak_table_path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"record line {line_number} requires peak_table_path")
        peak_path = Path(raw_path)
        if not peak_path.is_absolute():
            peak_path = source.parent / peak_path
        peak_path = peak_path.resolve()
        if peak_path.suffix.lower() != ".npz" or not peak_path.is_file():
            raise ValueError(f"record line {line_number} peak table is missing or not .npz")
        records.append(
            PeakRecord(
                material_id=material_id,
                label=_label_from_row(row, line_number),
                split=split,
                peak_table_path=peak_path,
            )
        )
        seen.add(material_id)
    if not records or not any(record.split == "train" for record in records):
        raise ValueError("records must contain at least one training structure")
    return records


def load_peak_tables(records: Sequence[PeakRecord]) -> dict[str, PeakTable]:
    return {
        record.material_id: load_peak_table(record.peak_table_path)
        for record in records
    }


def render_pair_batch(
    records: Sequence[PeakRecord],
    peaks: dict[str, PeakTable],
    factory: OnlineViewFactory,
    *,
    epoch: int,
    global_step: int,
    profile: str,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    if not records:
        raise ValueError("cannot render an empty batch")
    first: list[np.ndarray] = []
    second: list[np.ndarray] = []
    labels: list[int] = []
    for record in records:
        pair = factory.make_pair_from_peaks(
            peaks[record.material_id],
            material_id=record.material_id,
            split=record.split,
            epoch=epoch,
            global_step=global_step,
            profile=profile,
        )
        first.append(pair.first.xrd)
        second.append(pair.second.xrd)
        labels.append(record.label)
    return (
        torch.from_numpy(np.stack(first).astype(np.float32, copy=False)),
        torch.from_numpy(np.stack(second).astype(np.float32, copy=False)),
        torch.tensor(labels, dtype=torch.long),
    )


def train_epoch(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    records: Sequence[PeakRecord],
    peaks: dict[str, PeakTable],
    factory: OnlineViewFactory,
    step_config: TrainingStepConfig,
    *,
    epoch: int,
    global_step: int,
    batch_size: int,
    profile: str,
    device: torch.device,
    rng: np.random.Generator,
    max_steps: int | None = None,
) -> tuple[dict[str, float], int]:
    model.train()
    order = rng.permutation(len(records))
    totals = {"classification": 0.0, "consistency": 0.0, "total": 0.0}
    seen = 0
    steps = 0
    for start in range(0, len(order), batch_size):
        if max_steps is not None and global_step >= max_steps:
            break
        batch = [records[int(index)] for index in order[start : start + batch_size]]
        x1, x2, target = render_pair_batch(
            batch,
            peaks,
            factory,
            epoch=epoch,
            global_step=global_step,
            profile=profile,
        )
        x1, x2, target = x1.to(device), x2.to(device), target.to(device)
        optimizer.zero_grad(set_to_none=True)
        result = run_training_step(step_config, model, x1=x1, x2=x2, target=target)
        result["total"].backward()
        optimizer.step()
        count = len(batch)
        for key in totals:
            totals[key] += float(result[key].detach()) * count
        seen += count
        steps += 1
        global_step += 1
    if not seen:
        raise RuntimeError("no training batch was executed")
    return {
        **{key: value / seen for key, value in totals.items()},
        "structures": float(seen),
        "optimizer_steps": float(steps),
    }, global_step


def evaluate(
    model: torch.nn.Module,
    records: Sequence[PeakRecord],
    peaks: dict[str, PeakTable],
    factory: OnlineViewFactory,
    *,
    batch_size: int,
    profile: str,
    device: torch.device,
) -> dict[str, Any]:
    if not records:
        return {}
    labels: list[int] = []
    predictions: list[int] = []
    probabilities: list[np.ndarray] = []
    model.eval()
    for start in range(0, len(records), batch_size):
        batch = list(records[start : start + batch_size])
        x1, x2, target = render_pair_batch(
            batch,
            peaks,
            factory,
            epoch=0,
            global_step=0,
            profile=profile,
        )
        with torch.inference_mode():
            first = model(x1.to(device))["logits"]
            second = model(x2.to(device))["logits"]
            probability = 0.5 * (
                torch.softmax(first, dim=-1) + torch.softmax(second, dim=-1)
            )
        values = probability.cpu().numpy()
        labels.extend(target.tolist())
        predictions.extend(values.argmax(axis=1).tolist())
        probabilities.extend(values)
    return classification_metrics(
        labels,
        predictions,
        probabilities=np.asarray(probabilities),
        num_classes=len(CRYSTAL_SYSTEMS),
    )


def _device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(value)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")
    return device


def build_model(config: ML4PXRDResNet1DConfig) -> torch.nn.Module:
    """Single construction seam kept explicit for lightweight smoke tests."""

    return ML4PXRDResNet1D(config)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.epochs <= 0 or args.batch_size <= 0 or args.learning_rate <= 0:
        raise ValueError("epochs, batch_size, and learning_rate must be positive")
    if args.max_steps is not None and args.max_steps <= 0:
        raise ValueError("max_steps must be positive")
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError(f"output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    records_path = Path(args.records).resolve()
    simulation_path = Path(args.simulation_config).resolve()
    records = load_peak_records(records_path)
    peaks = load_peak_tables(records)
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation["run_seed"] = int(args.seed)
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    if args.profile not in sampler.profiles:
        raise ValueError(f"profile is absent from simulation config: {args.profile}")

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = _device(args.device)
    model_config = ML4PXRDResNet1DConfig(model_id="18")
    model = build_model(model_config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
    )
    mode = TrainingMode(args.mode)
    step_config = TrainingStepConfig(mode=mode, lambda_js=args.lambda_js)
    factory = OnlineViewFactory(sampler)
    train_records = [record for record in records if record.split == "train"]
    validation_records = [record for record in records if record.split == "validation"]
    resolved = {
        "schema_version": "xrd-resnet-training-v1",
        "architecture": "ResNet-18-GN",
        "mode": mode.value,
        "lambda_js": float(args.lambda_js),
        "seed": int(args.seed),
        "epochs": int(args.epochs),
        "batch_size": int(args.batch_size),
        "learning_rate": float(args.learning_rate),
        "weight_decay": float(args.weight_decay),
        "profile": args.profile,
        "records_path": str(records_path),
        "records_sha256": file_hash(records_path),
        "simulation_config_path": str(simulation_path),
        "simulation_config_sha256": file_hash(simulation_path),
        "model_config": asdict(model_config),
        "train_structure_count": len(train_records),
        "validation_structure_count": len(validation_records),
    }
    _write_json_atomic(output_dir / "resolved_config.json", resolved)
    provenance = {
        "records_sha256": resolved["records_sha256"],
        "simulation_config_sha256": resolved["simulation_config_sha256"],
        "training_contract_sha256": config_hash(resolved),
    }
    history: list[dict[str, Any]] = []
    global_step = 0
    best_score = float("-inf")
    rng = np.random.default_rng(args.seed)
    for epoch in range(1, args.epochs + 1):
        training, global_step = train_epoch(
            model,
            optimizer,
            train_records,
            peaks,
            factory,
            step_config,
            epoch=epoch,
            global_step=global_step,
            batch_size=args.batch_size,
            profile=args.profile,
            device=device,
            rng=rng,
            max_steps=args.max_steps,
        )
        validation = evaluate(
            model,
            validation_records,
            peaks,
            factory,
            batch_size=args.batch_size,
            profile=args.profile,
            device=device,
        )
        item = {
            "epoch": epoch,
            "global_step": global_step,
            "training": training,
            "validation": validation,
        }
        history.append(item)
        _write_json_atomic(output_dir / "history.json", history)
        checkpoint_kwargs = {
            "model": model,
            "optimizers": [optimizer],
            "epoch": epoch,
            "global_step": global_step,
            "config": model_config,
            "data_manifest_hash": str(resolved["records_sha256"]),
            "view_manifest_hash": str(resolved["simulation_config_sha256"]),
            "seed": args.seed,
            "provenance": provenance,
            "extra_state": {"training_mode": mode.value, "lambda_js": args.lambda_js},
        }
        save_checkpoint(output_dir / "last.ckpt", **checkpoint_kwargs)
        score = float(validation.get("macro_f1", -training["total"]))
        if score > best_score:
            best_score = score
            save_checkpoint(output_dir / "best.ckpt", **checkpoint_kwargs)
        if args.max_steps is not None and global_step >= args.max_steps:
            break
    result = {
        "status": "completed",
        "epochs_completed": len(history),
        "global_step": global_step,
        "best_validation_macro_f1": best_score if validation_records else None,
        "output_dir": str(output_dir),
    }
    _write_json_atomic(output_dir / "result.json", result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train ResNet-18-GN with Dynamic ERM or Dynamic JS"
    )
    parser.add_argument("--records", required=True, help="Peak-table JSONL manifest")
    parser.add_argument("--simulation-config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mode", required=True, choices=[mode.value for mode in TrainingMode])
    parser.add_argument("--profile", default="train")
    parser.add_argument("--lambda-js", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-steps", type=int)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    result = run(build_parser().parse_args(argv))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0
