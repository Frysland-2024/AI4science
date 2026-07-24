#!/usr/bin/env python3
"""Train-only P0 diagnostic for local JS/Residual benefit in V9-T.

This script is deliberately not a tuning or formal-training entry point. It:

1. rebuilds one five-epoch Dynamic/Paired ERM learned state on the frozen Train
   split, entirely in memory;
2. fits and audits a detached residual probe on mutually exclusive Train-only
   subsets;
3. measures gradient alignment between the registered auxiliary objectives and
   independent Train-structure in-range/single-factor-OOD classification losses;
4. performs matched one-step counterfactual ERM, JS, and Residual updates from
   exactly the same learned state and optimizer state;
5. writes one JSON diagnostic report and no checkpoint.

It never reads Validation, simulated Test, RRUFF, GTIIT, opXRD, or any other real
XRD corpus. It cannot choose a lambda, freeze a formal hyperparameter, enable the
7-run, or authorize any formal experiment.
"""

from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import json
import math
from pathlib import Path
import random
import sys
import time
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_v9_learned_state_scale import (  # noqa: E402
    BATCH_SIZE,
    LEARNING_RATE,
    PROBE_LEARNING_RATE,
    PROBE_WEIGHT_DECAY,
    SEED,
    TRAIN_EPOCHS,
    WEIGHT_DECAY,
    _DynamicTrainStream,
    _autocast,
    _balanced_partitions,
    _collect_residual_features,
    _configure_runtime,
    _fit_and_evaluate_probe,
    _labels_tensor,
    _read_train_rows,
    _set_seed,
    _train_epoch,
)
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402
from xrd_robustness.online_views import OnlineViewFactory  # noqa: E402
from xrd_robustness.peak_cache import load_peak_table  # noqa: E402
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy  # noqa: E402
from xrd_robustness.physics import PhysicsParameterSampler  # noqa: E402
from xrd_robustness.training.objectives import (  # noqa: E402
    ResidualClassifier,
    dynamic_erm,
    dynamic_js,
    dynamic_residual,
    js_divergence,
    residual_confusion_kl,
    symmetric_measurement_residual,
)
from xrd_robustness.training_prefetch import render_dynamic_batch  # noqa: E402
from xrd_robustness.view_manifest import build_parameter_batch  # noqa: E402


SCHEMA_VERSION = "v9-p0-local-benefit-v1"
DEFAULT_REPEATS = 12
LOCAL_PER_CLASS = 50
BATCH_PER_CLASS = 2
LOCAL_BATCH_SIZE = 7 * BATCH_PER_CLASS
BOOTSTRAP_DRAWS = 2000
SINGLE_FACTOR_OOD_PROFILES = (
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
)
EVALUATION_PROFILES = ("in_range",) + SINGLE_FACTOR_OOD_PROFILES


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot summarize an empty sequence")
    return {
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
        "positive_sign_rate": float((array > 0).mean()),
    }


def _paired_bootstrap_ci(
    values: Sequence[float],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = SEED + 90_000,
) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot bootstrap an empty sequence")
    generator = np.random.default_rng(seed)
    indexes = generator.integers(0, array.size, size=(draws, array.size))
    bootstrap_means = array[indexes].mean(axis=1)
    return {
        "draws": int(draws),
        "mean": float(array.mean()),
        "lower_95": float(np.quantile(bootstrap_means, 0.025)),
        "upper_95": float(np.quantile(bootstrap_means, 0.975)),
    }


def _split_local_pool(
    scale_ids: Sequence[str], labels: Mapping[str, int]
) -> dict[str, list[str]]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for material_id in scale_ids:
        grouped[int(labels[material_id])].append(str(material_id))
    update_ids: list[str] = []
    evaluation_ids: list[str] = []
    for label in range(7):
        candidates = sorted(grouped[label])
        if len(candidates) != 2 * LOCAL_PER_CLASS:
            raise ValueError(
                f"scale-audit class {label} must contain exactly "
                f"{2 * LOCAL_PER_CLASS} structures, got {len(candidates)}"
            )
        generator = random.Random(SEED + 40_000 + label)
        generator.shuffle(candidates)
        update_ids.extend(candidates[:LOCAL_PER_CLASS])
        evaluation_ids.extend(candidates[LOCAL_PER_CLASS:])
    update_ids.sort()
    evaluation_ids.sort()
    if set(update_ids) & set(evaluation_ids):
        raise RuntimeError("local update and local evaluation pools overlap")
    return {"local_update": update_ids, "local_eval": evaluation_ids}


def _balanced_repeat_batch(
    pool: Sequence[str],
    labels: Mapping[str, int],
    *,
    repeat: int,
    stream_offset: int,
) -> list[str]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for material_id in pool:
        grouped[int(labels[material_id])].append(str(material_id))
    selected: list[str] = []
    for label in range(7):
        candidates = sorted(grouped[label])
        generator = random.Random(
            SEED + stream_offset + repeat * 101 + label * 10_003
        )
        generator.shuffle(candidates)
        if len(candidates) < BATCH_PER_CLASS:
            raise ValueError(f"local pool lacks class {label} examples")
        selected.extend(candidates[:BATCH_PER_CLASS])
    order = random.Random(SEED + stream_offset + repeat * 997).sample(
        selected, len(selected)
    )
    if len(order) != LOCAL_BATCH_SIZE:
        raise RuntimeError("local batch is not seven-class balanced")
    return order


def _build_renderer(
    simulation_path: Path,
) -> tuple[PhysicsParameterSampler, OnlineViewFactory, dict[str, Any]]:
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation["run_seed"] = SEED + 50_000
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation.get("quality_gates", {}),
        strategy=IndependentDynamicStrategy(
            sampler, config_hash=file_hash(simulation_path)
        ),
    )
    return sampler, factory, simulation


def _render_profile(
    *,
    batch_ids: Sequence[str],
    profile: str,
    repeat: int,
    panel_index: int,
    peaks: Mapping[str, Any],
    sampler: PhysicsParameterSampler,
    factory: OnlineViewFactory,
) -> tuple[np.ndarray, np.ndarray]:
    global_step = repeat * 100 + panel_index
    epoch = 30_000 + repeat
    rows = build_parameter_batch(
        list(batch_ids),
        sampler,
        profile=profile,
        epoch=epoch,
        global_step=global_step,
        split="train",
    )
    rendered = render_dynamic_batch(
        global_step,
        list(batch_ids),
        rows,
        peaks=dict(peaks),
        factory=factory,
        sampler=sampler,
        profile=profile,
    )
    if list(rendered.material_ids) != list(batch_ids):
        raise RuntimeError("renderer changed local panel material order")
    return rendered.first, rendered.second


def _backbone_gradients(
    loss: torch.Tensor,
    model: torch.nn.Module,
    *,
    retain_graph: bool,
) -> dict[str, torch.Tensor]:
    named = [
        (name, parameter)
        for name, parameter in model.named_parameters()
        if parameter.requires_grad and not name.startswith("head.")
    ]
    gradients = torch.autograd.grad(
        loss,
        [parameter for _, parameter in named],
        retain_graph=retain_graph,
        allow_unused=True,
    )
    return {
        name: gradient.detach().float()
        for (name, _), gradient in zip(named, gradients, strict=True)
        if gradient is not None
    }


def _combine_gradients(
    first: Mapping[str, torch.Tensor],
    second: Mapping[str, torch.Tensor],
    *,
    second_weight: float,
) -> dict[str, torch.Tensor]:
    names = set(first) | set(second)
    combined: dict[str, torch.Tensor] = {}
    for name in names:
        if name in first and name in second:
            combined[name] = first[name] + second_weight * second[name]
        elif name in first:
            combined[name] = first[name].clone()
        else:
            combined[name] = second_weight * second[name]
    return combined


def _gradient_relation(
    first: Mapping[str, torch.Tensor], second: Mapping[str, torch.Tensor]
) -> dict[str, float]:
    common = sorted(set(first) & set(second))
    if not common:
        raise ValueError("gradient maps have no common parameters")
    dot = torch.zeros((), dtype=torch.float64)
    first_sq = torch.zeros((), dtype=torch.float64)
    second_sq = torch.zeros((), dtype=torch.float64)
    for name in common:
        a = first[name].detach().double().cpu()
        b = second[name].detach().double().cpu()
        dot += torch.sum(a * b)
        first_sq += torch.sum(a.square())
        second_sq += torch.sum(b.square())
    denominator = torch.sqrt(first_sq * second_sq).clamp_min(1e-30)
    return {
        "dot_product": float(dot),
        "cosine": float(dot / denominator),
        "first_norm": float(torch.sqrt(first_sq)),
        "second_norm": float(torch.sqrt(second_sq)),
        "common_parameter_tensors": len(common),
    }


def _classification_loss(
    model: PAMPT,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
    output1 = model(x1)
    output2 = model(x2)
    loss = 0.5 * (
        F.cross_entropy(output1["logits"], target)
        + F.cross_entropy(output2["logits"], target)
    )
    return loss, {"first": output1, "second": output2}


def _mean_margin(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    true_logits = logits.gather(1, target[:, None]).squeeze(1)
    masked = logits.clone()
    masked.scatter_(1, target[:, None], float("-inf"))
    return (true_logits - masked.max(dim=1).values).mean()


def _panel_metrics(
    model: PAMPT,
    audit_probe: ResidualClassifier,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
) -> dict[str, float]:
    model.eval()
    audit_probe.eval()
    with torch.no_grad():
        output1 = model(x1)
        output2 = model(x2)
        logits1 = output1["logits"].float()
        logits2 = output2["logits"].float()
        ce = 0.5 * (
            F.cross_entropy(logits1, target)
            + F.cross_entropy(logits2, target)
        )
        logp1 = F.log_softmax(logits1, dim=-1)
        logp2 = F.log_softmax(logits2, dim=-1)
        correct_log_probability = 0.5 * (
            logp1.gather(1, target[:, None]).mean()
            + logp2.gather(1, target[:, None]).mean()
        )
        margin = 0.5 * (
            _mean_margin(logits1, target) + _mean_margin(logits2, target)
        )
        accuracy = 0.5 * (
            (logits1.argmax(-1) == target).float().mean()
            + (logits2.argmax(-1) == target).float().mean()
        )
        paired_js = js_divergence(logits1, logits2)
        disagreement = (logits1.argmax(-1) != logits2.argmax(-1)).float().mean()
        residual = symmetric_measurement_residual(
            output1["pooled_embedding"].float(),
            output2["pooled_embedding"].float(),
        )
        probe_logits = audit_probe(residual).float()
        probe_ce = F.cross_entropy(probe_logits, target)
        probe_accuracy = (probe_logits.argmax(-1) == target).float().mean()
        probe_probabilities = F.softmax(probe_logits, dim=-1)
        probe_entropy = -(
            probe_probabilities * F.log_softmax(probe_logits, dim=-1)
        ).sum(dim=-1).mean()
    return {
        "classification_ce": float(ce),
        "correct_class_log_probability": float(correct_log_probability),
        "classification_margin": float(margin),
        "classification_accuracy_across_two_views": float(accuracy),
        "paired_js": float(paired_js),
        "paired_top1_disagreement": float(disagreement),
        "fixed_audit_probe_ce": float(probe_ce),
        "fixed_audit_probe_accuracy": float(probe_accuracy),
        "fixed_audit_probe_entropy": float(probe_entropy),
    }


def _clone_to_cpu(value: Any) -> Any:
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: _clone_to_cpu(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_to_cpu(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_to_cpu(item) for item in value)
    return copy.deepcopy(value)


def _new_branch(
    *,
    model_state: Mapping[str, Any],
    optimizer_state: Mapping[str, Any],
    device: torch.device,
    fused: bool,
) -> tuple[PAMPT, torch.optim.Optimizer]:
    model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    model.load_state_dict(model_state)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        fused=fused,
    )
    optimizer.load_state_dict(optimizer_state)
    return model, optimizer


def _one_step_branch(
    *,
    method: str,
    model_state: Mapping[str, Any],
    optimizer_state: Mapping[str, Any],
    probe_state: Mapping[str, Any],
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    device: torch.device,
    fused: bool,
    lambda_js: float,
    lambda_res: float,
    repeat: int,
) -> tuple[PAMPT, dict[str, float]]:
    _set_seed(SEED + 70_000 + repeat, device)
    model, optimizer_main = _new_branch(
        model_state=model_state,
        optimizer_state=optimizer_state,
        device=device,
        fused=fused,
    )
    model.train()
    if method == "erm":
        optimizer_main.zero_grad(set_to_none=True)
        result = dynamic_erm(model, x1, x2, target)
        result["total"].backward()
        optimizer_main.step()
        losses = {
            "classification": float(result["classification"].detach()),
            "auxiliary": 0.0,
            "total": float(result["total"].detach()),
        }
    elif method == "js":
        optimizer_main.zero_grad(set_to_none=True)
        result = dynamic_js(model, x1, x2, target, lambda_js=lambda_js)
        result["total"].backward()
        optimizer_main.step()
        losses = {
            "classification": float(result["classification"].detach()),
            "auxiliary": float(result["consistency"].detach()),
            "total": float(result["total"].detach()),
        }
    elif method == "residual":
        residual_head = ResidualClassifier(model.config.embed_dim, depth=1).to(device)
        residual_head.load_state_dict(probe_state)
        optimizer_res = torch.optim.AdamW(
            residual_head.parameters(),
            lr=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY,
            fused=fused,
        )
        result = dynamic_residual(
            model,
            residual_head,
            x1,
            x2,
            target,
            optimizer_main=optimizer_main,
            optimizer_res=optimizer_res,
            lambda_res=lambda_res,
        )
        losses = {
            "classification": float(result["classification"]),
            "probe": float(result["probe"]),
            "auxiliary": float(result["independence"]),
            "total": float(result["total"]),
        }
        del optimizer_res, residual_head
    else:
        raise ValueError(f"unknown branch method: {method}")
    del optimizer_main
    return model, losses


def _delta(after: Mapping[str, float], before: Mapping[str, float]) -> dict[str, float]:
    return {key: float(after[key] - before[key]) for key in before}


def _aggregate_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_profile: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_profile[str(row["profile"])].append(row)

    def summarize_group(group: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for candidate in ("js", "residual"):
            benefits = [
                float(item["benefit_vs_erm"][candidate]["classification_ce"])
                for item in group
            ]
            result[candidate] = {
                "classification_ce_benefit_vs_erm": _summary(benefits),
                "paired_bootstrap_95": _paired_bootstrap_ci(benefits),
                "mean_candidate_delta": {
                    metric: float(
                        np.mean(
                            [
                                item["branches"][candidate]["delta"][metric]
                                for item in group
                            ]
                        )
                    )
                    for metric in group[0]["branches"][candidate]["delta"]
                },
            }
        return result

    profile_summary = {
        profile: summarize_group(group) for profile, group in sorted(by_profile.items())
    }
    ood_rows = [
        row for row in rows if str(row["profile"]) in SINGLE_FACTOR_OOD_PROFILES
    ]
    return {
        "by_profile": profile_summary,
        "all_single_factor_ood": summarize_group(ood_rows),
        "in_range": summarize_group(by_profile["in_range"]),
    }


def _registered_middle_lambdas(contract_path: Path) -> tuple[float, float, dict[str, list[float]]]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    candidates = {
        str(item["parameter"]): [float(value) for value in item["values"]]
        for item in contract["development_tuning"]["candidates"]
    }
    if set(candidates) != {"lambda_js", "lambda_res"}:
        raise ValueError("V9 contract does not contain exactly the JS and Residual grids")
    for values in candidates.values():
        if len(values) != 3 or values != sorted(values):
            raise ValueError("P0 diagnostic requires frozen ordered three-point grids")
    return candidates["lambda_js"][1], candidates["lambda_res"][1], candidates


def run_audit(
    *,
    device_name: str = "cuda",
    repeats: int = DEFAULT_REPEATS,
    worker_count: int = 8,
    prefetch_batches: int = 8,
    lambda_js: float | None = None,
    lambda_res: float | None = None,
) -> dict[str, Any]:
    if repeats <= 0 or repeats > 50:
        raise ValueError("repeats must be in [1, 50]")
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    runtime = _configure_runtime(device)
    _set_seed(SEED, device)
    started = time.perf_counter()

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = data_root / "manifests" / "split_manifest.v9t.family_v1.csv"
    simulation_path = PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    contract_path = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
    middle_js, middle_res, registered_grids = _registered_middle_lambdas(contract_path)
    selected_js = middle_js if lambda_js is None else float(lambda_js)
    selected_res = middle_res if lambda_res is None else float(lambda_res)
    if selected_js not in registered_grids["lambda_js"]:
        raise ValueError("lambda_js must be one of the already frozen registered candidates")
    if selected_res not in registered_grids["lambda_res"]:
        raise ValueError("lambda_res must be one of the already frozen registered candidates")

    train_ids, labels, train_class_counts = _read_train_rows(split_manifest)
    partitions = _balanced_partitions(train_ids, labels)
    local_pools = _split_local_pool(partitions["scale_audit"], labels)
    all_local_ids = sorted(set(local_pools["local_update"] + local_pools["local_eval"]))
    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    peaks = {
        material_id: load_peak_table(cache_root / f"{material_id}.npz")
        for material_id in all_local_ids
    }

    fused = device.type == "cuda"
    base_model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    base_optimizer = torch.optim.AdamW(
        base_model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        fused=fused,
    )
    training_stream = _DynamicTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    training_history: list[dict[str, Any]] = []
    try:
        for epoch_index in range(TRAIN_EPOCHS):
            report = _train_epoch(
                base_model,
                base_optimizer,
                training_stream,
                train_ids,
                labels,
                device,
                epoch_index=epoch_index,
                amp_enabled=runtime["amp_enabled"],
            )
            training_history.append(report)
            print(
                f"P0 base epoch={epoch_index + 1} ce={report['classification_ce']:.6f} "
                f"accuracy={report['classification_accuracy_across_two_views']:.4f}",
                flush=True,
            )

        calibration = _collect_residual_features(
            base_model,
            training_stream,
            partitions["probe_calibration"],
            labels,
            device,
            milestone=TRAIN_EPOCHS,
            subset_offset=61,
            amp_enabled=runtime["amp_enabled"],
        )
        probe_audit_features = _collect_residual_features(
            base_model,
            training_stream,
            partitions["probe_audit"],
            labels,
            device,
            milestone=TRAIN_EPOCHS,
            subset_offset=62,
            amp_enabled=runtime["amp_enabled"],
        )
        audit_probe, probe_report = _fit_and_evaluate_probe(
            base_model,
            calibration,
            probe_audit_features,
            device,
            milestone=TRAIN_EPOCHS + 60,
        )
    finally:
        training_stream.close()

    if probe_report["status"] != "signal_demonstrated":
        raise RuntimeError(
            "residual probe competence was not demonstrated; local Residual benefit "
            "diagnosis is fail-closed"
        )

    base_model_state = _clone_to_cpu(base_model.state_dict())
    base_optimizer_state = _clone_to_cpu(base_optimizer.state_dict())
    base_probe_state = _clone_to_cpu(audit_probe.state_dict())
    audit_probe.eval()
    for parameter in audit_probe.parameters():
        parameter.requires_grad_(False)

    sampler, factory, simulation = _build_renderer(simulation_path)
    profile_names = set(simulation["profiles"])
    if not set(EVALUATION_PROFILES).issubset(profile_names):
        missing = sorted(set(EVALUATION_PROFILES) - profile_names)
        raise RuntimeError(f"frozen simulation config lacks P0 profiles: {missing}")

    rows: list[dict[str, Any]] = []
    for repeat in range(repeats):
        update_ids = _balanced_repeat_batch(
            local_pools["local_update"], labels, repeat=repeat, stream_offset=80_000
        )
        eval_ids = _balanced_repeat_batch(
            local_pools["local_eval"], labels, repeat=repeat, stream_offset=90_000
        )
        update_first, update_second = _render_profile(
            batch_ids=update_ids,
            profile="train",
            repeat=repeat,
            panel_index=0,
            peaks=peaks,
            sampler=sampler,
            factory=factory,
        )
        x_update_1 = torch.from_numpy(np.ascontiguousarray(update_first)).float().to(device)
        x_update_2 = torch.from_numpy(np.ascontiguousarray(update_second)).float().to(device)
        update_target = _labels_tensor(update_ids, labels, device)

        base_model.eval()
        audit_probe.eval()
        update_cls, update_outputs = _classification_loss(
            base_model, x_update_1, x_update_2, update_target
        )
        update_js = js_divergence(
            update_outputs["first"]["logits"],
            update_outputs["second"]["logits"],
        )
        update_residual = symmetric_measurement_residual(
            update_outputs["first"]["pooled_embedding"],
            update_outputs["second"]["pooled_embedding"],
        )
        update_residual_loss = residual_confusion_kl(audit_probe(update_residual))
        g_cls = _backbone_gradients(update_cls, base_model, retain_graph=True)
        g_js = _backbone_gradients(update_js, base_model, retain_graph=True)
        g_res = _backbone_gradients(update_residual_loss, base_model, retain_graph=False)
        g_js_total = _combine_gradients(g_cls, g_js, second_weight=selected_js)
        g_res_total = _combine_gradients(g_cls, g_res, second_weight=selected_res)

        panels: dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}
        for panel_index, profile in enumerate(EVALUATION_PROFILES, start=1):
            first, second = _render_profile(
                batch_ids=eval_ids,
                profile=profile,
                repeat=repeat,
                panel_index=panel_index,
                peaks=peaks,
                sampler=sampler,
                factory=factory,
            )
            panels[profile] = (
                torch.from_numpy(np.ascontiguousarray(first)).float().to(device),
                torch.from_numpy(np.ascontiguousarray(second)).float().to(device),
                _labels_tensor(eval_ids, labels, device),
            )

        before_metrics = {
            profile: _panel_metrics(base_model, audit_probe, *panel)
            for profile, panel in panels.items()
        }
        gradient_alignment: dict[str, Any] = {}
        for profile, panel in panels.items():
            base_model.eval()
            ood_loss, _ = _classification_loss(base_model, *panel)
            g_panel = _backbone_gradients(ood_loss, base_model, retain_graph=False)
            gradient_alignment[profile] = {
                "erm_total_vs_panel": _gradient_relation(g_cls, g_panel),
                "js_total_vs_panel": _gradient_relation(g_js_total, g_panel),
                "residual_total_vs_panel": _gradient_relation(g_res_total, g_panel),
                "raw_js_auxiliary_vs_panel": _gradient_relation(g_js, g_panel),
                "raw_residual_auxiliary_vs_panel": _gradient_relation(g_res, g_panel),
            }

        branch_models: dict[str, PAMPT] = {}
        branch_losses: dict[str, dict[str, float]] = {}
        for method in ("erm", "js", "residual"):
            model, losses = _one_step_branch(
                method=method,
                model_state=base_model_state,
                optimizer_state=base_optimizer_state,
                probe_state=base_probe_state,
                x1=x_update_1,
                x2=x_update_2,
                target=update_target,
                device=device,
                fused=fused,
                lambda_js=selected_js,
                lambda_res=selected_res,
                repeat=repeat,
            )
            branch_models[method] = model
            branch_losses[method] = losses

        for profile, panel in panels.items():
            before = before_metrics[profile]
            branches: dict[str, Any] = {}
            for method, model in branch_models.items():
                after = _panel_metrics(model, audit_probe, *panel)
                branches[method] = {
                    "update_losses": branch_losses[method],
                    "after": after,
                    "delta": _delta(after, before),
                }
            rows.append(
                {
                    "repeat": repeat,
                    "profile": profile,
                    "update_material_ids": update_ids,
                    "evaluation_material_ids": eval_ids,
                    "before": before,
                    "gradient_alignment": gradient_alignment[profile],
                    "branches": branches,
                    "benefit_vs_erm": {
                        "js": {
                            metric: float(
                                branches["erm"]["delta"][metric]
                                - branches["js"]["delta"][metric]
                            )
                            for metric in before
                        },
                        "residual": {
                            metric: float(
                                branches["erm"]["delta"][metric]
                                - branches["residual"]["delta"][metric]
                            )
                            for metric in before
                        },
                    },
                }
            )
        for model in branch_models.values():
            del model
        del branch_models
        if device.type == "cuda":
            torch.cuda.empty_cache()
        print(f"completed P0 repeat={repeat + 1}/{repeats}", flush=True)

    aggregates = _aggregate_rows(rows)
    ood = aggregates["all_single_factor_ood"]
    descriptive_flags = {}
    for candidate in ("js", "residual"):
        ci = ood[candidate]["paired_bootstrap_95"]
        id_summary = aggregates["in_range"][candidate][
            "classification_ce_benefit_vs_erm"
        ]
        descriptive_flags[candidate] = {
            "mean_single_factor_ood_ce_benefit_positive": ci["mean"] > 0,
            "single_factor_ood_bootstrap_lower_above_zero": ci["lower_95"] > 0,
            "in_range_mean_ce_benefit_not_negative": id_summary["mean"] >= 0,
            "interpretation": (
                "promising_local_directional_signal"
                if ci["lower_95"] > 0 and id_summary["mean"] >= 0
                else "inconclusive_or_mixed_local_signal"
            ),
            "not_a_formal_performance_conclusion": True,
        }

    checks = {
        "only_frozen_train_split_read": True,
        "validation_not_used": True,
        "simulated_test_not_used": True,
        "real_xrd_not_used": True,
        "probe_calibration_audit_and_local_pools_disjoint": not bool(
            set(partitions["probe_calibration"])
            & set(partitions["probe_audit"])
            or set(partitions["probe_calibration"])
            & set(local_pools["local_update"] + local_pools["local_eval"])
            or set(partitions["probe_audit"])
            & set(local_pools["local_update"] + local_pools["local_eval"])
        ),
        "local_update_and_eval_disjoint": not bool(
            set(local_pools["local_update"]) & set(local_pools["local_eval"])
        ),
        "all_repeats_use_balanced_14_structure_batches": all(
            len(row["update_material_ids"]) == LOCAL_BATCH_SIZE
            and len(row["evaluation_material_ids"]) == LOCAL_BATCH_SIZE
            for row in rows
        ),
        "only_registered_lambda_values_used": selected_js
        in registered_grids["lambda_js"]
        and selected_res in registered_grids["lambda_res"],
        "no_checkpoint_written": True,
        "no_formal_checkpoint_created": True,
        "candidate_selection_not_performed": True,
        "tuning_execution_not_enabled": True,
        "formal_training_not_started": True,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "Train-only local directional-benefit diagnostic",
        "scientific_role": {
            "purpose": "screen whether JS or Residual has a locally favorable optimization direction before formal Validation tuning",
            "can_demonstrate_stable_generalization_gain": False,
            "can_select_lambda": False,
            "can_rank_final_methods": False,
            "can_unlock_tuning": False,
            "formal_claim_boundary": "only the preregistered Validation tuning and multi-seed formal comparison can establish method gain",
        },
        "formal_state_changes": {
            "formal_training_runs_started": 0,
            "validation_tuning_runs_started": 0,
            "formal_checkpoints_written": 0,
            "execution_switches_changed": False,
        },
        "device": str(device),
        "runtime_configuration": {
            **runtime,
            "prefetch_workers": worker_count,
            "prefetch_batches": prefetch_batches,
            "fused_adamw": fused,
        },
        "source_hashes": {
            "split_manifest": file_hash(split_manifest),
            "simulation_config": file_hash(simulation_path),
            "method_contract": file_hash(contract_path),
        },
        "registered_grids": registered_grids,
        "diagnostic_weights": {
            "lambda_js": selected_js,
            "lambda_res": selected_res,
            "default_policy": "middle point of each already frozen three-point grid",
            "weights_are_not_selected_or_preferred": True,
        },
        "base_learned_state": {
            "method": "Dynamic/Paired ERM classification only",
            "epochs": TRAIN_EPOCHS,
            "checkpoint_policy": "in_memory_only",
            "training_history": training_history,
            "residual_probe_gate": probe_report,
        },
        "train_only_partition_counts": {
            "full_train": len(train_ids),
            "train_class_counts": train_class_counts,
            "probe_calibration": len(partitions["probe_calibration"]),
            "probe_audit": len(partitions["probe_audit"]),
            "local_update_pool": len(local_pools["local_update"]),
            "local_eval_pool": len(local_pools["local_eval"]),
        },
        "protocol": {
            "repeats": repeats,
            "batch_size": LOCAL_BATCH_SIZE,
            "batch_balance": f"{BATCH_PER_CLASS} structures per crystal system",
            "evaluation_profiles": list(EVALUATION_PROFILES),
            "gradient_diagnostic_mode": "base model eval mode; backbone parameters excluding supervised task head",
            "counterfactual_update_mode": "matched one-step AdamW branches restored from identical model and optimizer state",
            "residual_branch": "formal two-step residual-head update followed by frozen-head backbone confusion update",
            "mechanism_evaluation_probe": "fixed competent detached probe shared by all branches",
            "benefit_sign": "classification_ce benefit > 0 means candidate reduced panel CE more than ERM",
        },
        "aggregates": aggregates,
        "descriptive_flags": descriptive_flags,
        "rows": rows,
        "checks": checks,
        "runtime_seconds": time.perf_counter() - started,
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--worker-count", type=int, default=8)
    parser.add_argument("--prefetch-batches", type=int, default=8)
    parser.add_argument("--lambda-js", type=float)
    parser.add_argument("--lambda-res", type=float)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_p0_local_benefit.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    if output.suffix.lower() != ".json":
        raise SystemExit("--output must be a JSON file")
    report = run_audit(
        device_name=args.device,
        repeats=args.repeats,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
        lambda_js=args.lambda_js,
        lambda_res=args.lambda_res,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {output}", flush=True)
    print(json.dumps(report["descriptive_flags"], indent=2, sort_keys=True), flush=True)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
