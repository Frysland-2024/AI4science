"""Leakage-checked JS-only RRUFF benchmark runner.

The runner supports two training stages: same-parent synthetic Dynamic-JS
pretraining, followed by optional real-RRUFF cross-entropy fine-tuning. Real
spectra without audited structure-parent links are never paired for JS.

Input contracts are JSON manifests. A real sample row has ``sample_id``,
``label`` (integer in the configured class order), and ``spectrum_path``. A
precomputed synthetic row has ``parent_id``, ``label``, ``view1_path`` and
``view2_path``; alternatively, an online-parent JSONL supplies a stable
``material_id``, label, split and cached ideal peak-table path for the existing
``OnlineViewFactory`` to render two transient same-parent views.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

from .evaluation.metrics import classification_metrics
from .models.ml4pxrd_resnet1d import ML4PXRDResNet1D, ML4PXRDResNet1DConfig
from .online_views import OnlineViewFactory
from .physics import PhysicsParameterSampler
from .simulator import SimulationGrid
from .training.runner import load_peak_records, load_peak_tables, render_pair_batch
from .training.objectives import dynamic_js


CLASS_ORDER = [
    "triclinic",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "trigonal",
    "hexagonal",
    "cubic",
]


def _read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "gb18030"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise ValueError(f"Could not decode JSON manifest: {path}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _resolve(root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()


def _safe_spectrum(path: Path, expected_length: int) -> np.ndarray:
    values = np.asarray(np.load(path, allow_pickle=False), dtype=np.float32).reshape(-1)
    if values.size != expected_length:
        raise ValueError(f"{path}: expected {expected_length} points, found {values.size}")
    if not np.isfinite(values).all():
        raise ValueError(f"{path}: spectrum contains non-finite values")
    return values


def build_split_manifest(
    *, manifest_path: Path, root: Path, output_path: Path, seed: int,
    train_per_class: int, validation_per_class: int, test_per_class: int,
) -> dict[str, Any]:
    """Create a deterministic stratified split from a metadata-only source manifest."""
    source = _read_json(manifest_path)
    samples = source.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("source manifest must contain a non-empty 'samples' list")
    required = train_per_class + validation_per_class + test_per_class
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in CLASS_ORDER}
    seen: set[str] = set()
    for row in samples:
        sample_id = str(row.get("rruff_id", row.get("sample_id", ""))).strip()
        label_name = str(row.get("crystal_system", row.get("label_name", ""))).lower()
        if not sample_id or sample_id in seen:
            raise ValueError(f"missing or duplicate sample ID: {sample_id!r}")
        if label_name not in grouped:
            raise ValueError(f"unsupported crystal-system label: {label_name!r}")
        seen.add(sample_id)
        grouped[label_name].append(row)

    records: list[dict[str, Any]] = []
    split_names = ["train", "validation", "test"]
    quotas = [train_per_class, validation_per_class, test_per_class]
    for label_index, label_name in enumerate(CLASS_ORDER):
        rows = grouped[label_name]
        if len(rows) < required:
            raise ValueError(f"{label_name}: need {required} samples, have {len(rows)}")
        # A stable hash gives deterministic, order-independent assignment.
        rows = sorted(
            rows,
            key=lambda row: hashlib.sha256(
                f"{seed}:{row.get('rruff_id', row.get('sample_id'))}".encode("utf-8")
            ).hexdigest(),
        )[:required]
        requested = [name for name, count in zip(split_names, quotas, strict=True) for _ in range(count)]
        for split_name, row in zip(requested, rows, strict=True):
            relpath = str(row.get("spectrum_path", f"spectra/{row.get('rruff_id', row.get('sample_id'))}.npy"))
            path = _resolve(root, relpath)
            values = _safe_spectrum(path, int(source.get("preprocessing", {}).get("points", 3501)))
            record = {
                "sample_id": str(row.get("rruff_id", row.get("sample_id"))),
                "label": label_index,
                "label_name": label_name,
                "split": split_name,
                "spectrum_path": str(path.relative_to(root.resolve())) if path.is_relative_to(root.resolve()) else str(path),
                "spectrum_sha256": _sha256(path),
                "length": int(values.size),
                "parent_id": row.get("parent_id"),
            }
            records.append(record)

    records.sort(key=lambda row: (row["split"], row["label"], row["sample_id"]))
    manifest = {
        "schema_version": "rruff-split-manifest-v1",
        "dataset_id": source.get("dataset_id", manifest_path.stem),
        "role": source.get("role", source.get("status", "unspecified")),
        "source_manifest": str(manifest_path),
        "source_manifest_sha256": _sha256(manifest_path),
        "seed": seed,
        "class_order": CLASS_ORDER,
        "quota_per_class": {
            "train": train_per_class,
            "validation": validation_per_class,
            "test": test_per_class,
        },
        "samples": records,
    }
    manifest["split_sha256"] = _canonical_hash(records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def validate_split_manifest(manifest: dict[str, Any], root: Path, expected_length: int) -> None:
    records = manifest.get("samples")
    if not isinstance(records, list) or not records:
        raise ValueError("split manifest contains no samples")
    ids_by_split: dict[str, set[str]] = {key: set() for key in ("train", "validation", "test")}
    hashes_by_split: dict[str, set[str]] = {key: set() for key in ids_by_split}
    parents_by_split: dict[str, set[str]] = {key: set() for key in ids_by_split}
    for row in records:
        split = str(row["split"])
        if split not in ids_by_split:
            raise ValueError(f"unexpected split name: {split}")
        sample_id = str(row["sample_id"])
        if sample_id in ids_by_split[split]:
            raise ValueError(f"duplicate sample ID inside {split}: {sample_id}")
        ids_by_split[split].add(sample_id)
        path = _resolve(root, str(row["spectrum_path"]))
        actual_hash = _sha256(path)
        if actual_hash != row["spectrum_sha256"]:
            raise ValueError(f"spectrum checksum mismatch for {sample_id}")
        values = _safe_spectrum(path, expected_length)
        if int(row.get("length", values.size)) != values.size:
            raise ValueError(f"spectrum length changed for {sample_id}")
        hashes_by_split[split].add(actual_hash)
        parent = row.get("parent_id")
        if parent not in (None, ""):
            parents_by_split[split].add(str(parent))
    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if ids_by_split[left] & ids_by_split[right]:
            raise ValueError(f"sample-ID leakage between {left} and {right}")
        if hashes_by_split[left] & hashes_by_split[right]:
            raise ValueError(f"spectrum-hash leakage between {left} and {right}")
        if parents_by_split[left] & parents_by_split[right]:
            raise ValueError(f"parent-ID leakage between {left} and {right}")
    expected_hash = _canonical_hash(records)
    if manifest.get("split_sha256") != expected_hash:
        raise ValueError("split manifest content hash mismatch")


class RealSpectrumDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, rows: list[dict[str, Any]], root: Path, length: int):
        self.rows = rows
        self.root = root
        self.length = length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        values = _safe_spectrum(_resolve(self.root, row["spectrum_path"]), self.length)
        return torch.from_numpy(values), torch.tensor(int(row["label"]), dtype=torch.long)


class SyntheticPairDataset(Dataset[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]):
    def __init__(self, rows: list[dict[str, Any]], root: Path, length: int):
        self.rows = rows
        self.root = root
        self.length = length
        missing = [i for i, row in enumerate(rows) if not row.get("parent_id")]
        if missing:
            raise ValueError(f"synthetic JS rows lack parent IDs at indices {missing[:8]}")
        for row in rows:
            if not row.get("view1_path") or not row.get("view2_path"):
                raise ValueError("synthetic JS rows require both view1_path and view2_path")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        first = _safe_spectrum(_resolve(self.root, row["view1_path"]), self.length)
        second = _safe_spectrum(_resolve(self.root, row["view2_path"]), self.length)
        return (
            torch.from_numpy(first),
            torch.from_numpy(second),
            torch.tensor(int(row["label"]), dtype=torch.long),
        )


def _load_synthetic_manifest(path: Path) -> tuple[list[dict[str, Any]], str]:
    manifest = _read_json(path)
    rows = manifest.get("samples")
    if not isinstance(rows, list) or not rows:
        raise ValueError("synthetic manifest must contain a non-empty 'samples' list")
    return rows, _sha256(path)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _load_model(config: dict[str, Any], checkpoint_path: Path | None, device: torch.device) -> ML4PXRDResNet1D:
    model_cfg = ML4PXRDResNet1DConfig(
        model_id=str(config.get("model_id", "18")),
        input_length=int(config.get("input_length", 3501)),
        num_classes=int(config.get("num_classes", 7)),
        group_norm_groups=int(config.get("group_norm_groups", 32)),
        group_norm_eps=float(config.get("group_norm_eps", 1e-3)),
        square_kernel_size_and_stride=bool(config.get("square_kernel_size_and_stride", True)),
        add_additional_dense_layer=True,
    )
    model = ML4PXRDResNet1D(model_cfg)
    if checkpoint_path is not None:
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        saved_cfg = checkpoint.get("config", {})
        for key, expected in (("input_length", model_cfg.input_length), ("num_classes", model_cfg.num_classes), ("model_id", model_cfg.model_id)):
            if key in saved_cfg and saved_cfg[key] != expected:
                raise ValueError(f"checkpoint {key}={saved_cfg[key]!r} does not match {expected!r}")
        state = checkpoint.get("model", checkpoint.get("state_dict", checkpoint))
        model.load_state_dict(state, strict=True)
    return model.to(device)


def _train_synthetic_js(
    model: ML4PXRDResNet1D, rows: list[dict[str, Any]], root: Path, *, length: int,
    batch_size: int, epochs: int, learning_rate: float, weight_decay: float,
    lambda_js: float, seed: int, device: torch.device, log_path: Path,
) -> dict[str, Any]:
    dataset = SyntheticPairDataset(rows, root, length)
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator, num_workers=0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    model.train()
    start = time.perf_counter()
    steps = 0
    views = 0
    with log_path.open("a", encoding="utf-8") as log:
        for epoch in range(1, epochs + 1):
            for x1, x2, y in loader:
                x1, x2, y = x1.to(device), x2.to(device), y.to(device)
                optimizer.zero_grad(set_to_none=True)
                losses = dynamic_js(model, x1, x2, y, lambda_js=lambda_js)
                losses["total"].backward()
                optimizer.step()
                steps += 1
                views += 2 * int(y.shape[0])
                row = {
                    "stage": "synthetic_dynamic_js",
                    "epoch": epoch,
                    "step": steps,
                    "parents_in_batch": int(y.shape[0]),
                    "views_processed_total": views,
                    "loss": float(losses["total"].detach().cpu()),
                    "ce": float(losses["classification"].detach().cpu()),
                    "js": float(losses["consistency"].detach().cpu()),
                    "elapsed_seconds": time.perf_counter() - start,
                }
                log.write(json.dumps(row) + "\n")
    return {
        "unique_parent_rows": len(rows),
        "epochs": epochs,
        "optimizer_steps": steps,
        "online_generated_views": 0,
        "synthetic_pair_view_exposures": views,
        "view_source": "precomputed_manifest",
        "lambda_js": lambda_js,
        "elapsed_seconds": time.perf_counter() - start,
    }


def _train_synthetic_js_online(
    model: ML4PXRDResNet1D, records_path: Path, simulation_path: Path, *, root: Path,
    length: int, batch_size: int, epochs: int, learning_rate: float,
    weight_decay: float, lambda_js: float, seed: int, device: torch.device,
    log_path: Path, profile: str, grid_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train Dynamic JS while rendering two views per parent from cached peak tables."""
    records = load_peak_records(records_path)
    train_records = [record for record in records if record.split == "train"]
    if not train_records:
        raise ValueError("online Dynamic JS records must include training parents")
    peaks = load_peak_tables(train_records)
    simulation = _read_json(simulation_path)
    simulation["run_seed"] = seed
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    if profile not in sampler.profiles:
        raise ValueError(f"online Dynamic JS profile {profile!r} is absent from simulation config")
    grid = SimulationGrid(**(grid_config or {}))
    factory = OnlineViewFactory(sampler, grid=grid)
    order_rng = np.random.default_rng(seed)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)
    steps = 0
    views = 0
    start = time.perf_counter()
    with log_path.open("a", encoding="utf-8") as log:
        for epoch in range(1, epochs + 1):
            order = order_rng.permutation(len(train_records))
            for offset in range(0, len(order), batch_size):
                batch = [train_records[int(i)] for i in order[offset : offset + batch_size]]
                x1, x2, labels = render_pair_batch(
                    batch,
                    peaks,
                    factory,
                    epoch=epoch,
                    global_step=steps,
                    profile=profile,
                )
                x1, x2, labels = x1.to(device), x2.to(device), labels.to(device)
                if x1.shape[-1] != length or x2.shape[-1] != length:
                    raise ValueError(
                        f"online simulator produced {x1.shape[-1]} points; model expects {length}"
                    )
                optimizer.zero_grad(set_to_none=True)
                losses = dynamic_js(model, x1, x2, labels, lambda_js=lambda_js)
                losses["total"].backward()
                optimizer.step()
                steps += 1
                views += 2 * int(labels.shape[0])
                log.write(json.dumps({
                    "stage": "synthetic_dynamic_js_online",
                    "epoch": epoch,
                    "step": steps,
                    "unique_parents_in_batch": int(labels.shape[0]),
                    "online_generated_views_total": views,
                    "loss": float(losses["total"].detach().cpu()),
                    "ce": float(losses["classification"].detach().cpu()),
                    "js": float(losses["consistency"].detach().cpu()),
                    "elapsed_seconds": time.perf_counter() - start,
                }) + "\n")
    return {
        "unique_parent_rows": len(train_records),
        "unique_parent_ids_sha256": _canonical_hash(sorted(record.material_id for record in train_records)),
        "records_sha256": _sha256(records_path),
        "simulation_config_sha256": _sha256(simulation_path),
        "epochs": epochs,
        "optimizer_steps": steps,
        "online_generated_views": views,
        "synthetic_pair_view_exposures": views,
        "view_source": "OnlineViewFactory_from_frozen_peak_tables",
        "lambda_js": lambda_js,
        "elapsed_seconds": time.perf_counter() - start,
    }


@torch.inference_mode()
def _predict(model: ML4PXRDResNet1D, loader: DataLoader, device: torch.device) -> tuple[list[int], np.ndarray]:
    labels: list[int] = []
    probabilities: list[np.ndarray] = []
    model.eval()
    for values, target in loader:
        logits = model(values.to(device))["logits"]
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        probabilities.append(probs)
        labels.extend(int(x) for x in target.numpy())
    return labels, np.concatenate(probabilities, axis=0)


def run_benchmark(config_path: Path, split_path: Path, output_dir: Path, *, device_arg: str | None = None) -> dict[str, Any]:
    run_start = time.perf_counter()
    config = _read_json(config_path)
    root = Path(config.get("project_root", ".")).resolve()
    length = int(config.get("input_length", 3501))
    num_classes = int(config.get("num_classes", 7))
    if config.get("class_order", CLASS_ORDER) != CLASS_ORDER:
        raise ValueError("class_order must match the project's fixed seven-system order")
    split_manifest = _read_json(split_path)
    validate_split_manifest(split_manifest, root, length)
    rows = split_manifest["samples"]
    train_rows = [row for row in rows if row["split"] == "train"]
    val_rows = [row for row in rows if row["split"] == "validation"]
    test_rows = [row for row in rows if row["split"] == "test"]
    if not test_rows:
        raise ValueError("the RRUFF test split must contain samples")
    output_dir.mkdir(parents=True, exist_ok=False)
    log_path = output_dir / "training_steps.jsonl"
    seed = int(config.get("seed", split_manifest.get("seed", 0)))
    _set_seed(seed)
    device = torch.device(device_arg or ("cuda" if torch.cuda.is_available() else "cpu"))
    checkpoint_value = config.get("initialize_from_checkpoint")
    checkpoint_path = _resolve(root, checkpoint_value) if checkpoint_value else None
    checkpoint_hash = _sha256(checkpoint_path) if checkpoint_path and checkpoint_path.is_file() else None
    if checkpoint_path is not None and not checkpoint_path.is_file():
        raise FileNotFoundError(checkpoint_path)
    model = _load_model(config, checkpoint_path, device)

    training = config.get("training", {})
    checkpoint_selection = str(config.get("checkpoint_selection", "validation_accuracy"))
    if checkpoint_selection not in {"validation_accuracy", "fixed_final_state"}:
        raise ValueError("checkpoint_selection must be validation_accuracy or fixed_final_state")
    synthetic_summary: dict[str, Any] | None = None
    if training.get("synthetic_js_manifest") and training.get("synthetic_online_records"):
        raise ValueError("choose either a precomputed JS pair manifest or online parent records")
    if training.get("synthetic_online_records"):
        records_path = _resolve(root, training["synthetic_online_records"])
        simulation_path = _resolve(root, training["synthetic_simulation_config"])
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        synthetic_summary = _train_synthetic_js_online(
            model,
            records_path,
            simulation_path,
            root=root,
            length=length,
            batch_size=int(training.get("synthetic_batch_size", 8)),
            epochs=int(training.get("synthetic_epochs", 1)),
            learning_rate=float(training.get("synthetic_learning_rate", 1e-4)),
            weight_decay=float(training.get("weight_decay", 1e-4)),
            lambda_js=float(training.get("lambda_js", 60.0)),
            seed=seed,
            device=device,
            log_path=log_path,
            profile=str(training.get("synthetic_profile", "train")),
            grid_config=training.get("synthetic_grid"),
        )
    elif training.get("synthetic_js_manifest"):
        js_manifest_path = _resolve(root, training["synthetic_js_manifest"])
        js_rows, js_hash = _load_synthetic_manifest(js_manifest_path)
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        synthetic_summary = _train_synthetic_js(
            model,
            js_rows,
            root,
            length=length,
            batch_size=int(training.get("synthetic_batch_size", 8)),
            epochs=int(training.get("synthetic_epochs", 1)),
            learning_rate=float(training.get("synthetic_learning_rate", 1e-4)),
            weight_decay=float(training.get("weight_decay", 1e-4)),
            lambda_js=float(training.get("lambda_js", 60.0)),
            seed=seed,
            device=device,
            log_path=log_path,
        )
        synthetic_summary["manifest_sha256"] = js_hash

    epochs = int(training.get("real_epochs", 1))
    if epochs < 0:
        raise ValueError("real_epochs cannot be negative")
    if epochs > 0 and not train_rows:
        raise ValueError("real_epochs > 0 requires RRUFF training rows")
    if checkpoint_selection == "validation_accuracy" and (not train_rows or not val_rows or epochs == 0):
        raise ValueError(
            "validation_accuracy selection requires real train/validation rows and real_epochs > 0; "
            "use fixed_final_state for an externally evaluated fixed training schedule"
        )
    if epochs == 0 and checkpoint_selection != "fixed_final_state":
        raise ValueError("real_epochs=0 requires checkpoint_selection=fixed_final_state")
    if epochs == 0 and synthetic_summary is None and checkpoint_path is None:
        raise ValueError("evaluation without RRUFF training requires synthetic training or an initial checkpoint")

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    real_start = time.perf_counter()
    real_steps = 0
    real_views = 0
    best_val_accuracy = -math.inf
    best_state: dict[str, torch.Tensor] | None = None
    if epochs > 0:
        model.train()
        real_dataset = RealSpectrumDataset(train_rows, root, length)
        generator = torch.Generator().manual_seed(seed)
        train_loader = DataLoader(
            real_dataset,
            batch_size=int(training.get("real_batch_size", 2)),
            shuffle=True,
            generator=generator,
            num_workers=0,
        )
        optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=float(training.get("real_learning_rate", 1e-5)),
            weight_decay=float(training.get("weight_decay", 1e-4)),
        )
        with log_path.open("a", encoding="utf-8") as log:
            for epoch in range(1, epochs + 1):
                model.train()
                epoch_start = time.perf_counter()
                loss_sum = 0.0
                for values, labels in train_loader:
                    values, labels = values.to(device), labels.to(device)
                    optimizer.zero_grad(set_to_none=True)
                    logits = model(values)["logits"]
                    loss = torch.nn.functional.cross_entropy(logits, labels)
                    loss.backward()
                    optimizer.step()
                    real_steps += 1
                    real_views += int(labels.shape[0])
                    loss_sum += float(loss.detach().cpu())
                    log.write(json.dumps({
                        "stage": "real_rruff_ce_finetune",
                        "epoch": epoch,
                        "step": real_steps,
                        "real_samples_in_batch": int(labels.shape[0]),
                        "real_views_processed_total": real_views,
                        "loss": float(loss.detach().cpu()),
                        "elapsed_seconds": time.perf_counter() - real_start,
                    }) + "\n")
                if checkpoint_selection == "validation_accuracy":
                    val_loader = DataLoader(RealSpectrumDataset(val_rows, root, length), batch_size=16, shuffle=False, num_workers=0)
                    val_labels, val_probs = _predict(model, val_loader, device)
                    val_metrics = classification_metrics(
                        val_labels,
                        val_probs.argmax(axis=1),
                        probabilities=val_probs,
                        num_classes=num_classes,
                    )
                    # Checkpoint selection uses validation only; test is evaluated once below.
                    if val_metrics["accuracy"] > best_val_accuracy:
                        best_val_accuracy = val_metrics["accuracy"]
                        best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                    log.write(json.dumps({
                        "stage": "validation",
                        "epoch": epoch,
                        "loss_mean": loss_sum / max(1, len(train_loader)),
                        "accuracy": val_metrics["accuracy"],
                        "macro_f1": val_metrics["macro_f1"],
                        "ece": val_metrics["ece"],
                        "epoch_elapsed_seconds": time.perf_counter() - epoch_start,
                    }) + "\n")
                else:
                    # Fixed training schedules do not consult RRUFF validation or test scores.
                    best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                    log.write(json.dumps({
                        "stage": "fixed_schedule_epoch",
                        "epoch": epoch,
                        "loss_mean": loss_sum / max(1, len(train_loader)),
                        "epoch_elapsed_seconds": time.perf_counter() - epoch_start,
                    }) + "\n")
    else:
        best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("no validation checkpoint was selected")
    model.load_state_dict(best_state, strict=True)
    test_loader = DataLoader(RealSpectrumDataset(test_rows, root, length), batch_size=16, shuffle=False, num_workers=0)
    test_labels, test_probs = _predict(model, test_loader, device)
    test_predictions = test_probs.argmax(axis=1)
    test_metrics = classification_metrics(
        test_labels,
        test_predictions,
        probabilities=test_probs,
        num_classes=num_classes,
    )
    final_checkpoint_path = output_dir / "final_model.ckpt"
    torch.save(
        {
            "model": model.state_dict(),
            "config": {
                "model_id": str(config.get("model_id", "18")),
                "input_length": length,
                "num_classes": num_classes,
                "group_norm_groups": int(config.get("group_norm_groups", 32)),
                "group_norm_eps": float(config.get("group_norm_eps", 1e-3)),
                "square_kernel_size_and_stride": bool(config.get("square_kernel_size_and_stride", True)),
            },
            "experiment_id": config.get("experiment_id", output_dir.name),
            "source_checkpoint_sha256": checkpoint_hash,
            "split_manifest_sha256": split_manifest["split_sha256"],
        },
        final_checkpoint_path,
    )
    prediction_path = output_dir / "test_predictions.csv"
    with prediction_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id_sha256", "true_label", "predicted_label", "confidence"])
        writer.writeheader()
        for row, true_label, predicted_label, probabilities in zip(test_rows, test_labels, test_predictions, test_probs, strict=True):
            writer.writerow({
                "sample_id_sha256": hashlib.sha256(str(row["sample_id"]).encode("utf-8")).hexdigest(),
                "true_label": CLASS_ORDER[true_label],
                "predicted_label": CLASS_ORDER[int(predicted_label)],
                "confidence": float(probabilities.max()),
            })
    peak_memory = int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
    summary = {
        "schema_version": "rruff-js-benchmark-result-v1",
        "experiment_id": config.get("experiment_id", output_dir.name),
        "role": config.get("role", "benchmark"),
        "protocol_status": config.get("protocol_status", "unclassified"),
        "paper_comparable": bool(config.get("paper_comparable", False)),
        "seed": seed,
        "config_sha256": _sha256(config_path),
        "runner_source_sha256": _sha256(Path(__file__)),
        "device": str(device),
        "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else "CPU",
        "torch_version": torch.__version__,
        "split_manifest_sha256": split_manifest["split_sha256"],
        "split_counts": {split: sum(row["split"] == split for row in rows) for split in ("train", "validation", "test")},
        "real_training_unique_samples": len(train_rows) if epochs > 0 else 0,
        "real_training_unique_parent_ids_with_audited_links": (
            len({row["parent_id"] for row in train_rows if row.get("parent_id")}) if epochs > 0 else 0
        ),
        "synthetic_dynamic_js": synthetic_summary,
        "online_generated_js_views": int(synthetic_summary["online_generated_views"]) if synthetic_summary else 0,
        "synthetic_pair_view_exposures": int(synthetic_summary["synthetic_pair_view_exposures"]) if synthetic_summary else 0,
        "total_optimizer_steps": int(synthetic_summary["optimizer_steps"]) + real_steps if synthetic_summary else real_steps,
        "real_finetune": {
            "loss": "cross_entropy_only when real_epochs > 0; no fabricated real-spectrum JS pairs",
            "epochs": epochs,
            "optimizer_steps": real_steps,
            "real_training_spectrum_views": real_views,
            "elapsed_seconds": time.perf_counter() - real_start,
            "mean_train_step_samples_per_second": real_views / max(time.perf_counter() - real_start, 1e-9),
            "batch_size": int(training.get("real_batch_size", 2)),
            "learning_rate": float(training.get("real_learning_rate", 1e-5)),
        },
        "initial_checkpoint": {
            "path": str(checkpoint_path) if checkpoint_path else None,
            "sha256": checkpoint_hash,
        },
        "final_model_checkpoint": {
            "path": str(final_checkpoint_path),
            "sha256": _sha256(final_checkpoint_path),
            "model_state_role": "fine_tuned" if epochs > 0 or synthetic_summary is not None else "initialization_for_evaluation",
        },
        "model_parameters": model.parameter_count,
        "peak_allocated_gpu_bytes": peak_memory,
        "validation_selection": {
            "method": checkpoint_selection,
            "metric": "accuracy" if checkpoint_selection == "validation_accuracy" else None,
            "best_accuracy": best_val_accuracy if math.isfinite(best_val_accuracy) else None,
            "validation_samples": len(val_rows) if checkpoint_selection == "validation_accuracy" else 0,
        },
        "test_metrics_single_evaluation": test_metrics,
        "accuracy_definition": "top-1 correct predictions divided by all test predictions",
        "macro_f1_definition": "unweighted mean of per-class F1 across the configured seven classes",
        "ece_definition": "15 equal-width confidence bins",
        "prediction_file": prediction_path.name,
        "runtime_seconds_total": time.perf_counter() - run_start,
        "warnings": [
            "This output is not a paper reproduction unless all protocol-specific data and preprocessing fields are verified.",
            "Real spectra without audited parent identity use CE fine-tuning only; no real JS pairs are invented.",
        ],
    }
    (output_dir / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (output_dir / "result_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["experiment_id", "n_test", "accuracy", "macro_f1", "ece", "runtime_seconds_total", "peak_allocated_gpu_bytes"])
        writer.writeheader()
        writer.writerow({
            "experiment_id": summary["experiment_id"],
            "n_test": len(test_rows),
            "accuracy": test_metrics["accuracy"],
            "macro_f1": test_metrics["macro_f1"],
            "ece": test_metrics["ece"],
            "runtime_seconds_total": summary["runtime_seconds_total"],
            "peak_allocated_gpu_bytes": peak_memory,
        })
    return summary


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    split_parser = subparsers.add_parser("make-split", help="create a stratified split manifest")
    split_parser.add_argument("--source-manifest", type=Path, required=True)
    split_parser.add_argument("--root", type=Path, default=Path("."))
    split_parser.add_argument("--output", type=Path, required=True)
    split_parser.add_argument("--seed", type=int, required=True)
    split_parser.add_argument("--train-per-class", type=int, required=True)
    split_parser.add_argument("--validation-per-class", type=int, required=True)
    split_parser.add_argument("--test-per-class", type=int, required=True)
    run_parser = subparsers.add_parser("run", help="train, infer once, evaluate and export a run")
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--split-manifest", type=Path, required=True)
    run_parser.add_argument("--output-dir", type=Path, required=True)
    run_parser.add_argument("--device", choices=("cpu", "cuda"), default=None)
    args = parser.parse_args(argv)
    if args.command == "make-split":
        result = build_split_manifest(
            manifest_path=args.source_manifest,
            root=args.root.resolve(),
            output_path=args.output,
            seed=args.seed,
            train_per_class=args.train_per_class,
            validation_per_class=args.validation_per_class,
            test_per_class=args.test_per_class,
        )
        print(json.dumps({"split_sha256": result["split_sha256"], "sample_count": len(result["samples"])}))
        return 0
    result = run_benchmark(args.config, args.split_manifest, args.output_dir, device_arg=args.device)
    print(json.dumps({"experiment_id": result["experiment_id"], "metrics": result["test_metrics_single_evaluation"], "runtime_seconds": result["runtime_seconds_total"]}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
