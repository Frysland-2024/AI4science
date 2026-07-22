"""Bounded Train-only numerical audit for V9 JS and residual objectives.

This script evaluates registered candidate scales on one frozen Train batch. It
does not optimize hyperparameters, load Validation, or touch either test set.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import time
from typing import Any, Iterable

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from torch.nn import functional as F

from audit_v9_resume_determinism import (
    PROJECT_ROOT,
    SEED,
    _formal_batch_provider,
    _set_seed,
    _small_model,
    _state_sha256,
)
from xrd_robustness.training.objectives import (
    ResidualClassifier,
    js_divergence,
    residual_confusion_kl,
    residual_lambda_schedule,
    symmetric_measurement_residual,
)
from xrd_robustness.training_stream import deterministic_epoch_shuffle, select_epoch_batch


JS_WEIGHTS = (0.1, 0.3, 1.0)
RESIDUAL_WEIGHTS = (0.01, 0.1, 1.0)


def _gradient_norm(loss: torch.Tensor, parameters: Iterable[torch.nn.Parameter]) -> float:
    trainable = [parameter for parameter in parameters if parameter.requires_grad]
    gradients = torch.autograd.grad(loss, trainable, retain_graph=True, allow_unused=True)
    squared = sum(float(gradient.detach().float().pow(2).sum()) for gradient in gradients if gradient is not None)
    return float(squared**0.5)


def _effective_rank(features: torch.Tensor) -> float:
    centered = features.detach().float() - features.detach().float().mean(dim=0, keepdim=True)
    singular = torch.linalg.svdvals(centered)
    energy = singular.square()
    if float(energy.sum()) == 0.0:
        return 0.0
    probabilities = energy / energy.sum()
    entropy = -(probabilities * probabilities.clamp_min(1e-12).log()).sum()
    return float(entropy.exp())


def _finite(values: Iterable[float]) -> bool:
    return all(np.isfinite(float(value)) for value in values)


def _erm_step_hash(
    initial_state: dict[str, torch.Tensor],
    x1: torch.Tensor,
    x2: torch.Tensor,
    labels: torch.Tensor,
    device: torch.device,
    *,
    objective: str,
) -> str:
    _set_seed(SEED + 91, device)
    model = _small_model(device)
    model.load_state_dict(initial_state)
    model.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    optimizer.zero_grad(set_to_none=True)
    first = model(x1)
    second = model(x2)
    classification = 0.5 * (F.cross_entropy(first["logits"], labels) + F.cross_entropy(second["logits"], labels))
    if objective == "erm":
        total = classification
    elif objective == "js_zero":
        total = classification + 0.0 * js_divergence(first["logits"], second["logits"])
    elif objective == "residual_zero":
        _set_seed(SEED + 92, device)
        head = ResidualClassifier(first["pooled_embedding"].shape[-1]).to(device)
        head_optimizer = torch.optim.AdamW(head.parameters(), lr=1e-4)
        detached = symmetric_measurement_residual(
            first["pooled_embedding"].detach(), second["pooled_embedding"].detach()
        )
        head_optimizer.zero_grad(set_to_none=True)
        F.cross_entropy(head(detached), labels).backward()
        head_optimizer.step()
        total = classification + 0.0 * residual_confusion_kl(
            head(symmetric_measurement_residual(first["pooled_embedding"], second["pooled_embedding"]))
        )
    else:
        raise ValueError(objective)
    total.backward()
    optimizer.step()
    return _state_sha256(model)


def run_audit(*, device_name: str = "cuda") -> dict[str, Any]:
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    torch.use_deterministic_algorithms(True)
    if device.type == "cuda":
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.cuda.reset_peak_memory_stats(device)
    _set_seed(SEED, device)
    material_ids, provider, label_map = _formal_batch_provider(
        data_root=PROJECT_ROOT / "data" / "formal_14060",
        simulation_path=PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json",
        split_manifest=PROJECT_ROOT / "data" / "formal_14060" / "manifests" / "split_manifest.v9t.family_v1.csv",
    )
    audit_batches = []
    for epoch in range(4):
        order = deterministic_epoch_shuffle(material_ids, seed=SEED, epoch=epoch)
        for step in range(2):
            batch_ids = list(select_epoch_batch(order, step=step, batch_size=4, full_batch=True))
            first_batch, second_batch, batch_pairs = provider(epoch, step, batch_ids)
            audit_batches.append((batch_ids, first_batch, second_batch, batch_pairs))
    batch_ids, first_cpu, second_cpu, pair_ids = audit_batches[0]
    x1 = first_cpu.to(device=device, dtype=torch.float32)
    x2 = second_cpu.to(device=device, dtype=torch.float32)
    labels = torch.tensor([label_map[item] for item in batch_ids], device=device, dtype=torch.long)
    _set_seed(SEED + 1, device)
    template = _small_model(device)
    initial_state = copy.deepcopy(template.state_dict())

    def aggregate_trace(trace: list[dict[str, float]], weight_name: str, weight: float) -> dict[str, Any]:
        keys = [key for key in trace[0] if key != "step_time_seconds"]
        return {
            weight_name: weight,
            "audit_steps": len(trace),
            **{key: float(np.mean([row[key] for row in trace])) for key in keys},
            "observed_ranges": {
                key: [float(min(row[key] for row in trace)), float(max(row[key] for row in trace))]
                for key in keys
            },
            "step_time_mean_seconds": float(np.mean([row["step_time_seconds"] for row in trace])),
            "step_time_p95_seconds": float(np.quantile([row["step_time_seconds"] for row in trace], 0.95)),
        }

    js_rows = []
    for weight in JS_WEIGHTS:
        _set_seed(SEED + 3, device)
        model = _small_model(device)
        model.load_state_dict(initial_state)
        model.train()
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
        trace = []
        for batch_ids_step, first_step, second_step, _ in audit_batches:
            started = time.perf_counter()
            x1_step = first_step.to(device=device, dtype=torch.float32)
            x2_step = second_step.to(device=device, dtype=torch.float32)
            labels_step = torch.tensor([label_map[item] for item in batch_ids_step], device=device, dtype=torch.long)
            optimizer.zero_grad(set_to_none=True)
            output1, output2 = model(x1_step), model(x2_step)
            classification = 0.5 * (F.cross_entropy(output1["logits"], labels_step) + F.cross_entropy(output2["logits"], labels_step))
            consistency = js_divergence(output1["logits"], output2["logits"])
            classification_grad = _gradient_norm(classification, model.parameters())
            consistency_grad = _gradient_norm(consistency, model.parameters())
            weighted_grad = _gradient_norm(weight * consistency, model.parameters())
            total = classification + weight * consistency
            total_grad = _gradient_norm(total, model.parameters())
            total.backward()
            optimizer.step()
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            trace.append({
                "classification_loss": float(classification.detach()), "js_loss": float(consistency.detach()),
                "weighted_js_loss": float((weight * consistency).detach()),
                "aux_to_classification_loss_ratio": float((weight * consistency / classification).detach()),
                "classification_gradient_norm": classification_grad, "unweighted_js_gradient_norm": consistency_grad,
                "weighted_js_gradient_norm": weighted_grad, "total_gradient_norm": total_grad,
                "step_time_seconds": time.perf_counter() - started,
            })
        js_rows.append(aggregate_trace(trace, "lambda_js", weight))

    residual_rows = []
    for weight in RESIDUAL_WEIGHTS:
        _set_seed(SEED + 4, device)
        model = _small_model(device)
        model.load_state_dict(initial_state)
        model.train()
        head = ResidualClassifier(32).to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
        head_optimizer = torch.optim.AdamW(head.parameters(), lr=1e-4)
        trace = []
        for batch_ids_step, first_step, second_step, _ in audit_batches:
            started = time.perf_counter()
            x1_step = first_step.to(device=device, dtype=torch.float32)
            x2_step = second_step.to(device=device, dtype=torch.float32)
            labels_step = torch.tensor([label_map[item] for item in batch_ids_step], device=device, dtype=torch.long)
            output1, output2 = model(x1_step), model(x2_step)
            embedding1, embedding2 = output1["pooled_embedding"], output2["pooled_embedding"]
            residual = symmetric_measurement_residual(embedding1, embedding2)
            classification = 0.5 * (F.cross_entropy(output1["logits"], labels_step) + F.cross_entropy(output2["logits"], labels_step))
            head_optimizer.zero_grad(set_to_none=True)
            probe_loss = F.cross_entropy(head(residual.detach()), labels_step)
            head_grad = _gradient_norm(probe_loss, head.parameters())
            probe_loss.backward()
            head_optimizer.step()
            previous = [parameter.requires_grad for parameter in head.parameters()]
            for parameter in head.parameters():
                parameter.requires_grad_(False)
            independence = residual_confusion_kl(head(residual))
            optimizer.zero_grad(set_to_none=True)
            classification_grad = _gradient_norm(classification, model.parameters())
            independence_grad = _gradient_norm(independence, model.parameters())
            weighted_grad = _gradient_norm(weight * independence, model.parameters())
            total = classification + weight * independence
            total_grad = _gradient_norm(total, model.parameters())
            total.backward()
            optimizer.step()
            for parameter, requires_grad in zip(head.parameters(), previous, strict=True):
                parameter.requires_grad_(requires_grad)
            features = torch.cat((embedding1, embedding2), dim=0)
            if device.type == "cuda":
                torch.cuda.synchronize(device)
            trace.append({
                "classification_loss": float(classification.detach()), "probe_loss": float(probe_loss.detach()),
                "independence_loss": float(independence.detach()),
                "weighted_independence_loss": float((weight * independence).detach()),
                "aux_to_classification_loss_ratio": float((weight * independence / classification).detach()),
                "classification_gradient_norm": classification_grad,
                "unweighted_independence_gradient_norm": independence_grad,
                "weighted_independence_gradient_norm": weighted_grad, "probe_head_gradient_norm": head_grad,
                "total_gradient_norm": total_grad, "feature_norm": float(features.detach().norm(dim=1).mean()),
                "feature_mean_variance": float(features.detach().float().var(dim=0, unbiased=False).mean()),
                "feature_effective_rank": _effective_rank(features), "residual_norm": float(residual.detach().norm(dim=1).mean()),
                "residual_mean_variance": float(residual.detach().float().var(dim=0, unbiased=False).mean()),
                "step_time_seconds": time.perf_counter() - started,
            })
        residual_rows.append(aggregate_trace(trace, "lambda_res", weight))

    with torch.no_grad():
        probe_model = _small_model(device)
        probe_model.load_state_dict(initial_state)
        a, b = probe_model(x1), probe_model(x2)
        js_forward = js_divergence(a["logits"], b["logits"])
        js_swapped = js_divergence(b["logits"], a["logits"])
        js_self = js_divergence(a["logits"], a["logits"])
        residual_forward = symmetric_measurement_residual(a["pooled_embedding"], b["pooled_embedding"])
        residual_swapped = symmetric_measurement_residual(b["pooled_embedding"], a["pooled_embedding"])

    erm_hash = _erm_step_hash(initial_state, x1, x2, labels, device, objective="erm")
    js_zero_hash = _erm_step_hash(initial_state, x1, x2, labels, device, objective="js_zero")
    residual_zero_hash = _erm_step_hash(initial_state, x1, x2, labels, device, objective="residual_zero")
    schedule = [residual_lambda_schedule(epoch, target=0.1, warmup_epochs=2, ramp_epochs=3) for epoch in range(7)]
    numeric_values = [value for row in [*js_rows, *residual_rows] for value in row.values() if isinstance(value, float)]
    checks = {
        "all_values_finite": _finite(numeric_values),
        "js_non_negative": all(row["js_loss"] >= -1e-7 for row in js_rows),
        "js_swap_symmetric": bool(torch.equal(js_forward, js_swapped)),
        "js_self_zero": bool(float(js_self) <= 1e-7),
        "js_zero_weight_reduces_to_erm": js_zero_hash == erm_hash,
        "residual_swap_invariant": bool(torch.equal(residual_forward, residual_swapped)),
        "residual_zero_weight_reduces_to_erm": residual_zero_hash == erm_hash,
        "warmup_and_ramp_exact": bool(np.allclose(schedule, [0.0, 0.0, 0.1 / 3.0, 0.2 / 3.0, 0.1, 0.1, 0.1])),
        "js_gradients_propagate": all(row["unweighted_js_gradient_norm"] > 0 for row in js_rows),
        "residual_gradients_propagate": all(row["unweighted_independence_gradient_norm"] > 0 for row in residual_rows),
        "probe_gradients_propagate": all(row["probe_head_gradient_norm"] > 0 for row in residual_rows),
        "no_feature_collapse": all(row["feature_mean_variance"] > 1e-10 and row["feature_effective_rank"] > 1.0 for row in residual_rows),
    }
    scale_observation = {
        "descriptive_threshold_only": "weighted auxiliary loss / classification loss >= 0.01",
        "js_max_weighted_loss_ratio": max(row["aux_to_classification_loss_ratio"] for row in js_rows),
        "residual_max_weighted_loss_ratio": max(row["aux_to_classification_loss_ratio"] for row in residual_rows),
    }
    scale_observation["registered_candidates_reach_one_percent_loss_scale"] = {
        "js": scale_observation["js_max_weighted_loss_ratio"] >= 0.01,
        "residual": scale_observation["residual_max_weighted_loss_ratio"] >= 0.01,
    }
    scale_observation["interpretation"] = (
        "registered candidates are numerically stable but this bounded early-training audit does not demonstrate a weak-to-strong span"
        if not all(scale_observation["registered_candidates_reach_one_percent_loss_scale"].values())
        else "registered candidates span at least one percent of classification-loss scale in this bounded audit"
    )
    return {
        "schema_version": "v9-loss-gradient-scale-audit-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "bounded_train_only_engineering_audit",
        "formal_training_runs_started": 0,
        "validation_used": False,
        "simulated_test_used": False,
        "real_test_used": False,
        "candidate_selection_performed": False,
        "device": str(device),
        "material_ids": batch_ids,
        "parameter_pair_ids": [list(pair) for pair in pair_ids],
        "js_candidates": js_rows,
        "residual_candidates": residual_rows,
        "audit_optimizer_steps_per_candidate": len(audit_batches),
        "residual_swap_contract": "absolute normalized residual is invariant, not sign-equivariant",
        "residual_schedule_epochs_0_to_6": schedule,
        "zero_weight_model_hashes": {"erm": erm_hash, "js": js_zero_hash, "residual": residual_zero_hash},
        "peak_gpu_memory_mb": float(torch.cuda.max_memory_allocated(device) / 1024**2) if device.type == "cuda" else 0.0,
        "checks": checks,
        "candidate_scale_observation": scale_observation,
        "decision": "numerical legality passed; no lambda selected; candidate-range adequacy requires a separate scientific governance decision and Validation remains the only authorized future performance source",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--output", default=str(PROJECT_ROOT / "reports" / "v9_loss_gradient_scale_audit.json"))
    args = parser.parse_args()
    report = run_audit(device_name=args.device)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output), "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
