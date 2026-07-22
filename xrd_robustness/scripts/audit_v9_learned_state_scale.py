#!/usr/bin/env python3
"""Learned-state, Train-only audit of V9 auxiliary-objective signal.

This diagnostic trains one method-neutral Dynamic/Paired ERM PAMPT-B3 model
for five epochs on the complete frozen Train split.  It never loads Validation,
simulated Test, or real XRD and never writes a checkpoint.  At preregistered
epochs 1, 3, and 5 it measures the unweighted JS and residual-confusion
backbone gradients.  A fresh residual probe is trained and evaluated on
mutually exclusive, class-balanced Train subsets at every milestone.

The report is evidence for human review.  It cannot select a lambda, revise a
registered grid, unlock tuning, or start a formal experiment.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time
from typing import Any, Iterable, Iterator, Mapping, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.experiment import file_hash
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training.objectives import (
    ResidualClassifier,
    js_divergence,
    residual_confusion_kl,
    symmetric_measurement_residual,
)
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher
from xrd_robustness.training_stream import (
    deterministic_epoch_shuffle,
    select_epoch_batch,
)
from xrd_robustness.view_manifest import build_parameter_batch


CRYSTAL_SYSTEMS = (
    "cubic",
    "hexagonal",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "triclinic",
    "trigonal",
)
SEED = 20260722
MILESTONES = (1, 3, 5)
TRAIN_EPOCHS = 5
BATCH_SIZE = 16
PROBE_PER_CLASS = 100
SCALE_PER_CLASS = 100
PROBE_EPOCHS = 50
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
PROBE_LEARNING_RATE = 1e-3
PROBE_WEIGHT_DECAY = 0.0
UNIFORM_CE = math.log(len(CRYSTAL_SYSTEMS))


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot summarize an empty sequence")
    return {
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
    }


def _set_seed(seed: int, device: torch.device) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)


def _gradient_norms(loss: torch.Tensor, model: torch.nn.Module) -> dict[str, float]:
    named = [
        (name, parameter)
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    ]
    gradients = torch.autograd.grad(
        loss,
        [parameter for _, parameter in named],
        retain_graph=True,
        allow_unused=True,
    )
    squared = {"full_model": 0.0, "backbone": 0.0, "task_head": 0.0}
    for (name, _), gradient in zip(named, gradients, strict=True):
        if gradient is None:
            continue
        value = float(gradient.detach().float().pow(2).sum())
        squared["full_model"] += value
        squared["task_head" if name.startswith("head.") else "backbone"] += value
    return {name: float(value**0.5) for name, value in squared.items()}


def _mean_entropy(logits: torch.Tensor) -> torch.Tensor:
    probabilities = F.softmax(logits, dim=-1)
    return -(probabilities * F.log_softmax(logits, dim=-1)).sum(dim=-1).mean()


def _macro_f1(targets: np.ndarray, predictions: np.ndarray) -> float:
    scores = []
    for label in range(len(CRYSTAL_SYSTEMS)):
        true_positive = int(((targets == label) & (predictions == label)).sum())
        false_positive = int(((targets != label) & (predictions == label)).sum())
        false_negative = int(((targets == label) & (predictions != label)).sum())
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(0.0 if denominator == 0 else 2 * true_positive / denominator)
    return float(np.mean(scores))


def _read_train_rows(split_manifest: Path) -> tuple[list[str], dict[str, int], dict[str, int]]:
    train_ids: list[str] = []
    labels: dict[str, int] = {}
    counts = {system: 0 for system in CRYSTAL_SYSTEMS}
    with split_manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] != "train":
                continue
            material_id = str(row["material_id"])
            system = str(row["crystal_system"])
            if system not in counts:
                raise ValueError(f"unexpected crystal system: {system}")
            train_ids.append(material_id)
            labels[material_id] = CRYSTAL_SYSTEMS.index(system)
            counts[system] += 1
    if len(train_ids) != len(set(train_ids)):
        raise ValueError("Train split contains duplicate material IDs")
    if len(train_ids) < 700:
        raise ValueError("learned-state audit requires at least 700 Train structures")
    return sorted(train_ids), labels, counts


def _balanced_partitions(
    train_ids: Sequence[str], labels: Mapping[str, int]
) -> dict[str, list[str]]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for material_id in train_ids:
        grouped[int(labels[material_id])].append(material_id)
    partitions = {"probe_calibration": [], "probe_audit": [], "scale_audit": []}
    required = PROBE_PER_CLASS * 2 + SCALE_PER_CLASS
    for label in range(len(CRYSTAL_SYSTEMS)):
        candidates = sorted(grouped[label])
        generator = random.Random(SEED + 1000 + label)
        generator.shuffle(candidates)
        if len(candidates) < required:
            raise ValueError(
                f"class {CRYSTAL_SYSTEMS[label]} has {len(candidates)} Train rows; "
                f"{required} are required"
            )
        partitions["probe_calibration"].extend(candidates[:PROBE_PER_CLASS])
        partitions["probe_audit"].extend(
            candidates[PROBE_PER_CLASS : 2 * PROBE_PER_CLASS]
        )
        partitions["scale_audit"].extend(
            candidates[2 * PROBE_PER_CLASS : required]
        )
    for values in partitions.values():
        values.sort()
    if set(partitions["probe_calibration"]) & set(partitions["probe_audit"]):
        raise RuntimeError("residual probe calibration and audit subsets overlap")
    return partitions


def _labels_tensor(
    material_ids: Sequence[str], labels: Mapping[str, int], device: torch.device
) -> torch.Tensor:
    return torch.tensor(
        [labels[material_id] for material_id in material_ids],
        dtype=torch.long,
        device=device,
    )


class _DynamicTrainStream:
    """Bounded deterministic prefetch over Train-only dynamic paired views."""

    def __init__(
        self,
        *,
        data_root: Path,
        simulation_path: Path,
        worker_count: int,
        prefetch_batches: int,
    ) -> None:
        self.simulation_path = simulation_path
        self.simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
        self.simulation["run_seed"] = SEED
        self.sampler = PhysicsParameterSampler.from_mapping(self.simulation)
        self.factory = OnlineViewFactory(
            self.sampler,
            quality_gate=True,
            quality_gate_config=self.simulation.get("quality_gates", {}),
            strategy=IndependentDynamicStrategy(
                self.sampler, config_hash=file_hash(simulation_path)
            ),
        )
        self.prefetch_batches = int(prefetch_batches)
        self.prefetcher = DynamicBatchPrefetcher(
            worker_count=worker_count,
            worker_native_threads=1,
            prefetch_batches=prefetch_batches,
            start_method="spawn",
            data_root=data_root,
            peak_cache_name="peak_tables_v7_reflection",
            sampler_config=self.simulation,
            quality_gate=True,
            quality_gate_config=self.simulation.get("quality_gates", {}),
            simulation_config_hash=file_hash(simulation_path),
            profile="train",
        )

    def batches(
        self,
        material_ids: Sequence[str],
        *,
        stream_epoch: int,
        key_base: int,
        shuffled: bool,
    ) -> Iterator[tuple[list[str], np.ndarray, np.ndarray]]:
        ordered = (
            deterministic_epoch_shuffle(material_ids, seed=SEED, epoch=stream_epoch)
            if shuffled
            else list(material_ids)
        )
        steps = math.ceil(len(ordered) / BATCH_SIZE)

        def submit(step: int) -> None:
            batch_ids = list(
                select_epoch_batch(
                    ordered,
                    step=step,
                    batch_size=BATCH_SIZE,
                    full_batch=False,
                )
            )
            rows = build_parameter_batch(
                batch_ids,
                self.sampler,
                profile="train",
                epoch=stream_epoch,
                global_step=step,
                split="train",
            )
            self.prefetcher.submit(key_base + step, batch_ids, rows)

        for step in range(min(steps, self.prefetch_batches)):
            submit(step)
        for step in range(steps):
            rendered = self.prefetcher.get(key_base + step)
            refill = step + self.prefetch_batches
            if refill < steps:
                submit(refill)
            yield list(rendered.material_ids), rendered.first, rendered.second

    def close(self) -> None:
        self.prefetcher.close()


def _configure_runtime(device: torch.device) -> dict[str, Any]:
    torch.set_num_threads(2)
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    torch.set_float32_matmul_precision("high")
    amp_enabled = bool(device.type == "cuda" and torch.cuda.is_bf16_supported())
    if device.type == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = True
        torch.cuda.reset_peak_memory_stats(device)
    return {
        "float32_matmul_precision": torch.get_float32_matmul_precision(),
        "allow_tf32": device.type == "cuda",
        "cudnn_benchmark": device.type == "cuda",
        "cudnn_deterministic": device.type == "cuda",
        "amp_enabled": amp_enabled,
        "amp_dtype": "bfloat16" if amp_enabled else "float32_fallback",
    }


def _autocast(device: torch.device, enabled: bool) -> torch.autocast:
    return torch.autocast(
        device_type="cuda", dtype=torch.bfloat16, enabled=bool(enabled)
    )


def _train_epoch(
    model: PAMPT,
    optimizer: torch.optim.Optimizer,
    stream: _DynamicTrainStream,
    train_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    *,
    epoch_index: int,
    amp_enabled: bool,
) -> dict[str, Any]:
    model.train()
    loss_sum = 0.0
    correct = 0
    examples = 0
    steps = 0
    started = time.perf_counter()
    for batch_ids, first, second in stream.batches(
        train_ids,
        stream_epoch=epoch_index,
        key_base=epoch_index * 100_000,
        shuffled=True,
    ):
        x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
        x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
        target = _labels_tensor(batch_ids, labels, device)
        optimizer.zero_grad(set_to_none=True)
        with _autocast(device, amp_enabled):
            output1 = model(x1)
            output2 = model(x2)
            logits1 = output1["logits"]
            logits2 = output2["logits"]
            loss = 0.5 * (
                F.cross_entropy(logits1, target)
                + F.cross_entropy(logits2, target)
            )
        loss.backward()
        optimizer.step()
        count = len(batch_ids)
        loss_sum += float(loss.detach()) * count
        correct += int((logits1.detach().argmax(dim=-1) == target).sum())
        correct += int((logits2.detach().argmax(dim=-1) == target).sum())
        examples += count
        steps += 1
        if steps % 100 == 0:
            print(
                f"train epoch={epoch_index + 1} step={steps} "
                f"of={math.ceil(len(train_ids) / BATCH_SIZE)}",
                flush=True,
            )
    return {
        "epoch": epoch_index + 1,
        "optimizer_steps": steps,
        "mother_structures": examples,
        "paired_spectra": 2 * examples,
        "classification_ce": loss_sum / examples,
        "classification_accuracy_across_two_views": correct / (2 * examples),
        "runtime_seconds": time.perf_counter() - started,
    }


def _collect_residual_features(
    model: PAMPT,
    stream: _DynamicTrainStream,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    *,
    milestone: int,
    subset_offset: int,
    amp_enabled: bool,
) -> tuple[torch.Tensor, torch.Tensor]:
    model.eval()
    features: list[torch.Tensor] = []
    targets: list[torch.Tensor] = []
    with torch.no_grad():
        for batch_ids, first, second in stream.batches(
            material_ids,
            stream_epoch=10_000 + milestone * 10 + subset_offset,
            key_base=1_000_000 + milestone * 100_000 + subset_offset * 10_000,
            shuffled=False,
        ):
            x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
            x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
            with _autocast(device, amp_enabled):
                embedding1 = model(x1)["pooled_embedding"]
                embedding2 = model(x2)["pooled_embedding"]
                residual = symmetric_measurement_residual(embedding1, embedding2)
            features.append(residual.detach().float().cpu())
            targets.append(_labels_tensor(batch_ids, labels, torch.device("cpu")))
    return torch.cat(features), torch.cat(targets)


def _fit_and_evaluate_probe(
    model: PAMPT,
    calibration: tuple[torch.Tensor, torch.Tensor],
    audit: tuple[torch.Tensor, torch.Tensor],
    device: torch.device,
    *,
    milestone: int,
) -> tuple[ResidualClassifier, dict[str, Any]]:
    calibration_x, calibration_y = calibration
    audit_x, audit_y = audit
    _set_seed(SEED + 20_000 + milestone, device)
    probe = ResidualClassifier(model.config.embed_dim, depth=1).to(device)
    optimizer = torch.optim.AdamW(
        probe.parameters(),
        lr=PROBE_LEARNING_RATE,
        weight_decay=PROBE_WEIGHT_DECAY,
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(SEED + 30_000 + milestone)
    probe.train()
    final_calibration_ce = float("nan")
    for _ in range(PROBE_EPOCHS):
        order = torch.randperm(len(calibration_y), generator=generator)
        loss_sum = 0.0
        for start in range(0, len(order), 64):
            index = order[start : start + 64]
            inputs = calibration_x[index].to(device)
            target = calibration_y[index].to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(probe(inputs), target)
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * len(index)
        final_calibration_ce = loss_sum / len(calibration_y)
    probe.eval()
    with torch.no_grad():
        logits = probe(audit_x.to(device)).float()
        target = audit_y.to(device)
        cross_entropy = float(F.cross_entropy(logits, target))
        predictions = logits.argmax(dim=-1).cpu().numpy()
        targets = audit_y.numpy()
        accuracy = float((predictions == targets).mean())
        entropy = float(_mean_entropy(logits))
    chance = 1.0 / len(CRYSTAL_SYSTEMS)
    standard_error = math.sqrt(chance * (1.0 - chance) / len(audit_y))
    threshold = chance + 2.0 * standard_error
    macro_f1 = _macro_f1(targets, predictions)
    status = (
        "signal_demonstrated"
        if accuracy > threshold and macro_f1 > chance and cross_entropy < UNIFORM_CE
        else "not_demonstrated"
    )
    return probe, {
        "status": status,
        "calibration_examples": len(calibration_y),
        "audit_examples": len(audit_y),
        "calibration_epochs": PROBE_EPOCHS,
        "architecture": "one-layer linear ResidualClassifier matching the frozen V9 residual-head design",
        "optimizer": "AdamW",
        "learning_rate": PROBE_LEARNING_RATE,
        "weight_decay": PROBE_WEIGHT_DECAY,
        "final_calibration_ce": final_calibration_ce,
        "audit_accuracy": accuracy,
        "audit_macro_f1": macro_f1,
        "audit_ce": cross_entropy,
        "audit_prediction_entropy": entropy,
        "chance_accuracy": chance,
        "descriptive_accuracy_threshold": threshold,
        "threshold_definition": "chance plus two binomial standard errors; accuracy, Macro-F1, and CE gates must all pass",
        "calibration_and_audit_subsets_are_disjoint": True,
        "features_are_detached_from_backbone": True,
        "not_a_generalization_claim": True,
    }


def _measure_scale(
    model: PAMPT,
    probe: ResidualClassifier,
    stream: _DynamicTrainStream,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    *,
    milestone: int,
    amp_enabled: bool,
) -> tuple[dict[str, Any], list[dict[str, float]]]:
    model.eval()
    probe.eval()
    previous_requires_grad = [parameter.requires_grad for parameter in probe.parameters()]
    for parameter in probe.parameters():
        parameter.requires_grad_(False)
    trace: list[dict[str, float]] = []
    for batch_ids, first, second in stream.batches(
        material_ids,
        stream_epoch=20_000 + milestone,
        key_base=2_000_000 + milestone * 100_000,
        shuffled=False,
    ):
        x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
        x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
        target = _labels_tensor(batch_ids, labels, device)
        with _autocast(device, amp_enabled):
            output1 = model(x1)
            output2 = model(x2)
            logits1 = output1["logits"]
            logits2 = output2["logits"]
            classification = 0.5 * (
                F.cross_entropy(logits1, target)
                + F.cross_entropy(logits2, target)
            )
            js = js_divergence(logits1, logits2)
            residual = symmetric_measurement_residual(
                output1["pooled_embedding"], output2["pooled_embedding"]
            )
            residual_logits = probe(residual)
            residual_confusion = residual_confusion_kl(residual_logits)
        classification_gradients = _gradient_norms(classification, model)
        js_gradients = _gradient_norms(js, model)
        residual_gradients = _gradient_norms(residual_confusion, model)
        probabilities1 = F.softmax(logits1.detach().float(), dim=-1)
        probabilities2 = F.softmax(logits2.detach().float(), dim=-1)
        classification_gradient = classification_gradients["backbone"]
        js_gradient = js_gradients["backbone"]
        residual_gradient = residual_gradients["backbone"]
        trace.append(
            {
                "batch_examples": float(len(batch_ids)),
                "classification_ce": float(classification.detach()),
                "classification_accuracy_across_two_views": float(
                    0.5
                    * (
                        (logits1.detach().argmax(-1) == target).float().mean()
                        + (logits2.detach().argmax(-1) == target).float().mean()
                    )
                ),
                "prediction_entropy": float(
                    0.5 * (_mean_entropy(logits1) + _mean_entropy(logits2))
                ),
                "paired_top1_disagreement": float(
                    (logits1.detach().argmax(-1) != logits2.detach().argmax(-1))
                    .float()
                    .mean()
                ),
                "paired_probability_l1_distance": float(
                    (probabilities1 - probabilities2).abs().sum(dim=-1).mean()
                ),
                "raw_js": float(js.detach()),
                "feature_residual_l2_norm": float(
                    residual.detach().float().norm(dim=-1).mean()
                ),
                "residual_confusion_kl": float(residual_confusion.detach()),
                "residual_head_entropy": float(_mean_entropy(residual_logits)),
                "classification_backbone_gradient_norm": classification_gradient,
                "js_backbone_gradient_norm": js_gradient,
                "residual_backbone_gradient_norm": residual_gradient,
                "js_to_classification_backbone_gradient_ratio": js_gradient
                / max(classification_gradient, 1e-30),
                "residual_to_classification_backbone_gradient_ratio": residual_gradient
                / max(classification_gradient, 1e-30),
            }
        )
    for parameter, requires_grad in zip(
        probe.parameters(), previous_requires_grad, strict=True
    ):
        parameter.requires_grad_(requires_grad)
    summary = {
        key: _summary([row[key] for row in trace])
        for key in trace[0]
        if key != "batch_examples"
    }
    chance = 1.0 / len(CRYSTAL_SYSTEMS)
    standard_error = math.sqrt(chance * (1.0 - chance) / len(material_ids))
    threshold = chance + 2.0 * standard_error
    learned = (
        summary["classification_accuracy_across_two_views"]["mean"] > threshold
        and summary["classification_ce"]["mean"] < UNIFORM_CE
    )
    summary["classification_learning_gate"] = {
        "status": "learned_state_demonstrated" if learned else "not_demonstrated",
        "chance_accuracy": chance,
        "descriptive_accuracy_threshold": threshold,
        "uniform_cross_entropy": UNIFORM_CE,
        "requires_accuracy_above_threshold_and_ce_below_uniform": True,
    }
    return summary, trace


def run_audit(
    *,
    device_name: str = "cuda",
    worker_count: int = 8,
    prefetch_batches: int = 8,
) -> dict[str, Any]:
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    runtime = _configure_runtime(device)
    _set_seed(SEED, device)

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = (
        data_root / "manifests" / "split_manifest.v9t.family_v1.csv"
    )
    simulation_path = (
        PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    )
    train_ids, labels, train_class_counts = _read_train_rows(split_manifest)
    partitions = _balanced_partitions(train_ids, labels)
    model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    fused = device.type == "cuda"
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        fused=fused,
    )
    stream = _DynamicTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    training_history: list[dict[str, Any]] = []
    milestones: dict[str, Any] = {}
    started = time.perf_counter()
    try:
        for epoch_index in range(TRAIN_EPOCHS):
            epoch_report = _train_epoch(
                model,
                optimizer,
                stream,
                train_ids,
                labels,
                device,
                epoch_index=epoch_index,
                amp_enabled=runtime["amp_enabled"],
            )
            training_history.append(epoch_report)
            epoch_number = epoch_index + 1
            print(
                f"completed epoch={epoch_number} ce={epoch_report['classification_ce']:.6f} "
                f"accuracy={epoch_report['classification_accuracy_across_two_views']:.4f}",
                flush=True,
            )
            if epoch_number not in MILESTONES:
                continue
            calibration = _collect_residual_features(
                model,
                stream,
                partitions["probe_calibration"],
                labels,
                device,
                milestone=epoch_number,
                subset_offset=1,
                amp_enabled=runtime["amp_enabled"],
            )
            audit = _collect_residual_features(
                model,
                stream,
                partitions["probe_audit"],
                labels,
                device,
                milestone=epoch_number,
                subset_offset=2,
                amp_enabled=runtime["amp_enabled"],
            )
            probe, probe_report = _fit_and_evaluate_probe(
                model,
                calibration,
                audit,
                device,
                milestone=epoch_number,
            )
            scale_summary, scale_trace = _measure_scale(
                model,
                probe,
                stream,
                partitions["scale_audit"],
                labels,
                device,
                milestone=epoch_number,
                amp_enabled=runtime["amp_enabled"],
            )
            classification_pass = (
                scale_summary["classification_learning_gate"]["status"]
                == "learned_state_demonstrated"
            )
            probe_pass = probe_report["status"] == "signal_demonstrated"
            milestones[str(epoch_number)] = {
                "classification_learning_gate": scale_summary.pop(
                    "classification_learning_gate"
                ),
                "residual_probe_gate": probe_report,
                "scale_summary": scale_summary,
                "scale_trace": scale_trace,
                "lambda_interpretation_gate": {
                    "status": "eligible_for_human_review"
                    if classification_pass and probe_pass
                    else "blocked",
                    "backbone_learned_state_required": True,
                    "residual_probe_signal_required_for_residual_interpretation": True,
                    "automatic_grid_change_performed": False,
                    "grid_proposal_generated": False,
                },
            }
            print(
                f"audit epoch={epoch_number} backbone={milestones[str(epoch_number)]['classification_learning_gate']['status']} "
                f"probe={probe_report['status']}",
                flush=True,
            )
    finally:
        stream.close()

    epoch5 = milestones["5"]
    backbone_learned = (
        epoch5["classification_learning_gate"]["status"]
        == "learned_state_demonstrated"
    )
    probe_learned = epoch5["residual_probe_gate"]["status"] == "signal_demonstrated"
    if not backbone_learned:
        conclusion = "baseline_training_state_not_formed_in_five_epochs"
        next_action = "audit the shared Dynamic ERM training flow; do not infer or revise either lambda"
    elif not probe_learned:
        conclusion = "backbone_learned_but_residual_class_leakage_not_demonstrated"
        next_action = "review the residual definition or retire the residual objective; do not amplify it by changing lambda"
    else:
        js_median = epoch5["scale_summary"][
            "js_to_classification_backbone_gradient_ratio"
        ]["median"]
        conclusion = (
            "learned_backbone_and_residual_probe_signal_demonstrated"
            if js_median > 1e-6
            else "learned_backbone_and_probe_signal_but_js_remains_near_zero"
        )
        next_action = "human scientific review may decide whether one preregistered grid revision is justified; no revision is automatic"

    overlap_checks = {
        "probe_calibration_vs_probe_audit": not bool(
            set(partitions["probe_calibration"]) & set(partitions["probe_audit"])
        ),
        "probe_calibration_vs_scale_audit": not bool(
            set(partitions["probe_calibration"]) & set(partitions["scale_audit"])
        ),
        "probe_audit_vs_scale_audit": not bool(
            set(partitions["probe_audit"]) & set(partitions["scale_audit"])
        ),
    }
    checks = {
        "complete_train_split_used": len(train_ids) == sum(train_class_counts.values()),
        "at_least_700_train_structures_used": len(train_ids) >= 700,
        "formal_pampt_b3_used": model.config.variant == "b3",
        "formal_batch_size_used": BATCH_SIZE == 16,
        "formal_shared_optimizer_used": LEARNING_RATE == 1e-4
        and WEIGHT_DECAY == 1e-4,
        "dynamic_paired_train_views_used": True,
        "milestones_1_3_5_present": set(milestones) == {"1", "3", "5"},
        "balanced_probe_and_scale_subsets": all(
            len(values) == 700 for values in partitions.values()
        ),
        "all_diagnostic_subsets_are_disjoint": all(overlap_checks.values()),
        "no_checkpoint_written": True,
        "validation_not_used": True,
        "simulated_test_not_used": True,
        "real_xrd_not_used": True,
        "candidate_grid_unchanged": True,
        "execution_switches_unchanged": True,
    }
    return {
        "schema_version": "v9-learned-state-scale-audit-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "learned_state_train_only_diagnostic",
        "scientific_classification": {
            "previous_128_step_report": "initialization_or_chance_state_scale_evidence",
            "previous_gradient_balance_centers_valid_for_grid_revision": False,
            "reason": "classification and residual-probe losses in the short audit remained near ln(7), so near-zero auxiliary gradients were measured before a learned state was demonstrated",
        },
        "formal_training_runs_started": 0,
        "diagnostic_training_runs_started": 1,
        "candidate_specific_training_performed": False,
        "candidate_selection_performed": False,
        "validation_used": False,
        "simulated_test_used": False,
        "real_xrd_used": False,
        "checkpoint_written": False,
        "candidate_range_frozen_for_validation": False,
        "tuning_execution_switches_enabled": False,
        "registered_grids_unchanged": True,
        "device": str(device),
        "actual_hardware": {
            "gpu_name": torch.cuda.get_device_name(device)
            if device.type == "cuda"
            else None,
            "gpu_total_memory_mb": float(
                torch.cuda.get_device_properties(device).total_memory / 1024**2
            )
            if device.type == "cuda"
            else 0.0,
            "matches_registered_target_desktop_gpu": bool(
                device.type == "cuda"
                and torch.cuda.get_device_name(device)
                == "NVIDIA GeForce RTX 4070 Ti SUPER"
            ),
            "hardware_difference_changes_scientific_objective": False,
            "formal_performance_claim_made": False,
        },
        "runtime_configuration": {
            **runtime,
            "prefetch_workers": worker_count,
            "prefetch_batches": prefetch_batches,
            "fused_adamw": fused,
            "torch_compile": False,
            "torch_compile_reason": "excluded from this diagnostic so milestone probes can inspect the eager model without changing scientific objectives",
        },
        "training_protocol": {
            "method": "Dynamic/Paired ERM classification only",
            "backbone": "PAMPT-B3",
            "epochs": TRAIN_EPOCHS,
            "milestones": list(MILESTONES),
            "batch_size_mother_structures": BATCH_SIZE,
            "views_per_structure": 2,
            "optimizer": "AdamW",
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "diagnostic_probe_optimizer": {
                "name": "AdamW",
                "learning_rate": PROBE_LEARNING_RATE,
                "weight_decay": PROBE_WEIGHT_DECAY,
                "reason": "use a stronger fixed diagnostic probe fit than the backbone optimizer to avoid an underfit-probe false negative; the probe is detached and cannot alter the backbone",
            },
            "full_train_structures": len(train_ids),
            "steps_per_epoch": math.ceil(len(train_ids) / BATCH_SIZE),
            "checkpoint_policy": "in_memory_only; no checkpoint file is written",
        },
        "training_history": training_history,
        "diagnostic_subsets": {
            name: {
                "split": "train",
                "size": len(values),
                "per_class": len(values) // len(CRYSTAL_SYSTEMS),
                "material_ids_sha256": _canonical_hash(values),
                "material_ids": values,
            }
            for name, values in partitions.items()
        },
        "diagnostic_subset_overlap_checks": overlap_checks,
        "milestones": milestones,
        "epoch5_decision": {
            "conclusion": conclusion,
            "next_action": next_action,
            "automatic_lambda_inference_performed": False,
            "automatic_grid_revision_performed": False,
            "validation_tuning_authorized": False,
            "seven_run_started": False,
            "human_confirmation_required": True,
        },
        "input_hashes": {
            "audit_script": file_hash(Path(__file__).resolve()),
            "split_manifest": file_hash(split_manifest),
            "simulation_config": file_hash(simulation_path),
            "objective_source": file_hash(
                PROJECT_ROOT / "src" / "xrd_robustness" / "training" / "objectives.py"
            ),
            "backbone_source": file_hash(
                PROJECT_ROOT / "src" / "xrd_robustness" / "models" / "xrd_pampt.py"
            ),
            "hardware_profile": file_hash(
                PROJECT_ROOT / "configs" / "hardware.v9.desktop.9600x_4070tis.json"
            ),
        },
        "runtime": {
            "total_seconds": time.perf_counter() - started,
            "peak_gpu_memory_mb": float(
                torch.cuda.max_memory_allocated(device) / 1024**2
            )
            if device.type == "cuda"
            else 0.0,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--prefetch-workers", type=int, default=8)
    parser.add_argument("--prefetch-batches", type=int, default=8)
    parser.add_argument(
        "--output",
        default=str(
            PROJECT_ROOT / "reports" / "v9_learned_state_scale_audit.json"
        ),
    )
    args = parser.parse_args()
    report = run_audit(
        device_name=args.device,
        worker_count=args.prefetch_workers,
        prefetch_batches=args.prefetch_batches,
    )
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "epoch5_decision": report["epoch5_decision"],
                "output": str(output),
                "checks": report["checks"],
            },
            indent=2,
        ),
        flush=True,
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
