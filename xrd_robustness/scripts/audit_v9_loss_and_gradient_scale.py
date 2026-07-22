"""Train-only V9-T method-loss and backbone-gradient scale calibration.

The calibration follows one method-neutral Dynamic/Paired ERM trajectory on a
small, class-balanced subset of the frozen Train split.  It never reads
Validation, simulated Test, or real XRD, and it never selects a hyperparameter
from performance.  Auxiliary losses are measured at coefficient one so the
registered candidate weights can be evaluated as weak, material, or dominant
relative to the classification gradient.  The audit also follows the raw
losses, unweighted backbone-gradient norms, view distances, and residual-probe
competence over early/middle/late thirds of the diagnostic trajectory.  An
inverse gradient ratio is reported only as a diagnostic compensation factor;
it is not interpreted as a theoretically correct loss weight.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Iterable, Sequence

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch
from torch.nn import functional as F

from audit_v9_resume_determinism import PROJECT_ROOT, SEED, _set_seed
from xrd_robustness.experiment import file_hash
from xrd_robustness.models import PAMPT, PAMPTConfig
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training.objectives import (
    ResidualClassifier,
    js_divergence,
    residual_confusion_kl,
    symmetric_measurement_residual,
)
from xrd_robustness.training_prefetch import render_dynamic_batch
from xrd_robustness.training_stream import (
    deterministic_epoch_shuffle,
    paired_manifest_ids,
    select_epoch_batch,
)
from xrd_robustness.view_manifest import build_parameter_batch


CLASS_SYSTEMS = (
    "cubic",
    "hexagonal",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "triclinic",
    "trigonal",
)
DEFAULT_STEPS = 128
DEFAULT_BURN_IN_STEPS = 64
DEFAULT_BATCH_SIZE = 7
DEFAULT_AUDIT_EPOCHS = math.ceil(DEFAULT_STEPS / 2)
AUDIT_BATCHES_PER_EPOCH = 2
REQUESTED_DIAGNOSTICS = {
    "raw_L_cls": "classification_loss",
    "raw_L_JS": "js_loss",
    "raw_L_res": "residual_confusion_loss",
    "unweighted_grad_norm_cls": "classification_gradient_norm",
    "unweighted_grad_norm_JS": "js_gradient_norm",
    "unweighted_grad_norm_res": "residual_confusion_gradient_norm",
    "prediction_JS_distance": "prediction_js_distance",
    "feature_residual_norm": "feature_residual_l2_norm",
    "residual_head_entropy": "residual_head_entropy",
}


def _gradient_norms(
    loss: torch.Tensor, model: torch.nn.Module
) -> dict[str, float]:
    """Return full-model and encoder-only norms from one autograd traversal.

    PAMPT calls its supervised classifier ``head``.  Previous audit versions
    described a norm over all model parameters as a backbone norm.  Keeping the
    scopes separate prevents the classifier head from obscuring the encoder
    scale that the auxiliary objectives actually regularize.
    """

    named_trainable = [
        (name, parameter)
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    ]
    gradients = torch.autograd.grad(
        loss,
        [parameter for _, parameter in named_trainable],
        retain_graph=True,
        allow_unused=True,
    )
    full_squared = 0.0
    backbone_squared = 0.0
    task_head_squared = 0.0
    for (name, _), gradient in zip(named_trainable, gradients, strict=True):
        if gradient is None:
            continue
        squared = float(gradient.detach().float().pow(2).sum())
        full_squared += squared
        if name.startswith("head."):
            task_head_squared += squared
        else:
            backbone_squared += squared
    return {
        "full_model": float(full_squared**0.5),
        "backbone": float(backbone_squared**0.5),
        "task_head": float(task_head_squared**0.5),
    }


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _finite(values: Iterable[float]) -> bool:
    return all(np.isfinite(float(value)) for value in values)


def _round_significant(value: float, digits: int = 3) -> float:
    if value == 0.0:
        return 0.0
    return float(f"{value:.{digits}g}")


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
    }


def _mean_entropy(logits: torch.Tensor) -> torch.Tensor:
    probabilities = F.softmax(logits, dim=-1)
    return -(probabilities * F.log_softmax(logits, dim=-1)).sum(dim=-1).mean()


def _mean_accuracy(logits: torch.Tensor, labels: torch.Tensor) -> float:
    return float((logits.argmax(dim=-1) == labels).float().mean().detach())


def _phase_diagnostics(trace: Sequence[dict[str, float]]) -> dict[str, Any]:
    """Summarize non-overlapping early/middle/late audit-trajectory thirds."""

    length = len(trace)
    boundaries = (0, length // 3, (2 * length) // 3, length)
    phases: dict[str, Any] = {}
    for name, start, stop in zip(
        ("early", "middle", "late"), boundaries[:-1], boundaries[1:], strict=True
    ):
        rows = trace[start:stop]
        phases[name] = {
            "start_step": int(rows[0]["calibration_step"]),
            "end_step_inclusive": int(rows[-1]["calibration_step"]),
            "steps": len(rows),
            "requested_diagnostics": {
                output_name: _summary([row[source_name] for row in rows])
                for output_name, source_name in REQUESTED_DIAGNOSTICS.items()
            },
            "residual_probe_diagnostics": {
                key: _summary([row[key] for row in rows])
                for key in (
                    "residual_probe_loss_before_update",
                    "residual_probe_accuracy_before_update",
                    "residual_probe_entropy_before_update",
                    "residual_probe_loss_after_update",
                    "residual_probe_accuracy_after_update",
                    "residual_probe_entropy_after_update",
                )
            },
            "trajectory_context_diagnostics": {
                key: _summary([row[key] for row in rows])
                for key in (
                    "classification_accuracy",
                    "prediction_top1_agreement",
                )
            },
        }
    return phases


def _gradient_band(ratio: float) -> str:
    if ratio < 0.01:
        return "negligible_lt_1pct"
    if ratio < 0.1:
        return "weak_1_to_10pct"
    if ratio < 1.0:
        return "material_non_dominant_10_to_100pct"
    return "dominant_ge_100pct"


def _balanced_train_subset(
    split_manifest: Path, *, per_class: int = 2
) -> tuple[list[str], dict[str, int], dict[str, int]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    with split_manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["split"] == "train":
                grouped[str(row["crystal_system"])].append(str(row["material_id"]))
    unknown = set(grouped) - set(CLASS_SYSTEMS)
    if unknown:
        raise ValueError(f"unexpected crystal systems in Train split: {sorted(unknown)}")
    selected: list[str] = []
    labels: dict[str, int] = {}
    counts: dict[str, int] = {}
    for system in CLASS_SYSTEMS:
        candidates = sorted(grouped.get(system, []))
        if len(candidates) < per_class:
            raise ValueError(f"Train split lacks {per_class} examples for {system}")
        chosen = candidates[:per_class]
        selected.extend(chosen)
        counts[system] = len(chosen)
        labels.update({material_id: CLASS_SYSTEMS.index(system) for material_id in chosen})
    return selected, labels, counts


def _build_fixed_train_batches(
    *,
    material_ids: Sequence[str],
    data_root: Path,
    simulation_path: Path,
    batch_size: int,
    audit_epochs: int,
) -> list[dict[str, Any]]:
    if len(material_ids) != 2 * batch_size:
        raise ValueError("balanced audit subset must contain exactly two full batches")
    simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation["run_seed"] = SEED
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation.get("quality_gates", {}),
        strategy=IndependentDynamicStrategy(
            sampler, config_hash=file_hash(simulation_path)
        ),
    )
    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    peaks = {
        material_id: load_peak_table(cache_root / f"{material_id}.npz")
        for material_id in material_ids
    }
    batches: list[dict[str, Any]] = []
    for epoch in range(audit_epochs):
        order = deterministic_epoch_shuffle(material_ids, seed=SEED, epoch=epoch)
        for step in range(AUDIT_BATCHES_PER_EPOCH):
            batch_ids = list(
                select_epoch_batch(
                    order, step=step, batch_size=batch_size, full_batch=True
                )
            )
            rows = build_parameter_batch(
                batch_ids,
                sampler,
                profile="train",
                epoch=epoch,
                global_step=step,
                split="train",
            )
            absolute_step = epoch * AUDIT_BATCHES_PER_EPOCH + step
            rendered = render_dynamic_batch(
                absolute_step,
                batch_ids,
                rows,
                peaks=peaks,
                factory=factory,
                sampler=sampler,
                profile="train",
            )
            batches.append(
                {
                    "epoch": epoch,
                    "step": step,
                    "material_ids": batch_ids,
                    "first": torch.from_numpy(rendered.first),
                    "second": torch.from_numpy(rendered.second),
                    "parameter_pair_ids": [
                        list(pair)
                        for pair in paired_manifest_ids(
                            rendered.accepted_rows, batch_ids
                        )
                    ],
                }
            )
    return batches


def _registered_grids() -> dict[str, list[float]]:
    contract_path = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    grids = {
        str(item["parameter"]): [float(value) for value in item["values"]]
        for item in contract["development_tuning"]["candidates"]
    }
    if set(grids) != {"lambda_js", "lambda_res"}:
        raise ValueError("method-transfer contract must register JS and residual grids")
    return grids


def _candidate_scale_rows(
    trace: Sequence[dict[str, float]],
    *,
    weights: Sequence[float],
    weight_name: str,
    auxiliary_loss_name: str,
    auxiliary_gradient_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classification_losses = [row["classification_loss"] for row in trace]
    classification_gradients = [row["classification_gradient_norm"] for row in trace]
    auxiliary_losses = [row[auxiliary_loss_name] for row in trace]
    auxiliary_gradients = [row[auxiliary_gradient_name] for row in trace]
    rows = []
    for weight in weights:
        loss_ratios = [
            weight * auxiliary / max(classification, 1e-30)
            for auxiliary, classification in zip(
                auxiliary_losses, classification_losses, strict=True
            )
        ]
        gradient_ratios = [
            weight * auxiliary / max(classification, 1e-30)
            for auxiliary, classification in zip(
                auxiliary_gradients, classification_gradients, strict=True
            )
        ]
        gradient_summary = _summary(gradient_ratios)
        rows.append(
            {
                weight_name: float(weight),
                "analysis_steps": len(trace),
                "weighted_auxiliary_to_classification_loss_ratio": _summary(
                    loss_ratios
                ),
                "weighted_auxiliary_to_classification_gradient_ratio": gradient_summary,
                "median_gradient_band": _gradient_band(gradient_summary["median"]),
            }
        )
    lambda_balance_values = [
        classification / max(auxiliary, 1e-30)
        for classification, auxiliary in zip(
            classification_gradients, auxiliary_gradients, strict=True
        )
    ]
    lambda_center = float(np.median(lambda_balance_values))
    medians = [
        row["weighted_auxiliary_to_classification_gradient_ratio"]["median"]
        for row in rows
    ]
    coverage = {
        "has_weak_or_negligible_candidate": min(medians) < 0.1,
        "has_material_non_dominant_candidate": any(0.1 <= value < 1.0 for value in medians),
        "has_dominant_candidate": max(medians) >= 1.0,
    }
    coverage["covers_weak_material_and_dominant"] = all(coverage.values())
    calibration = {
        "lambda_gradient_balance_median": lambda_center,
        "lambda_gradient_balance_distribution": _summary(lambda_balance_values),
        "diagnostic_decade_compensation_factors": [
            _round_significant(lambda_center * factor) for factor in (0.1, 1.0, 10.0)
        ],
        "diagnostic_local_compensation_factors": [
            _round_significant(lambda_center * factor) for factor in (0.3, 1.0, 3.0)
        ],
        "compensation_factors_are_not_grid_proposals": True,
        "compensation_factors_are_not_validation_selection": True,
        "coverage": coverage,
    }
    return rows, calibration


def run_audit(
    *,
    device_name: str = "cuda",
    steps: int = DEFAULT_STEPS,
    burn_in_steps: int = DEFAULT_BURN_IN_STEPS,
    batch_size: int = DEFAULT_BATCH_SIZE,
    audit_epochs: int = DEFAULT_AUDIT_EPOCHS,
) -> dict[str, Any]:
    if steps < 100 or steps > 300:
        raise ValueError("method-scale calibration requires 100 to 300 Train-only steps")
    if burn_in_steps < 0 or burn_in_steps >= steps:
        raise ValueError("burn_in_steps must be in [0, steps)")
    if batch_size != 7:
        raise ValueError("the registered audit uses one example per crystal system per batch")
    if audit_epochs <= 0:
        raise ValueError("audit_epochs must be positive")
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    torch.use_deterministic_algorithms(True)
    if device.type == "cuda":
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        torch.cuda.reset_peak_memory_stats(device)

    split_manifest = (
        PROJECT_ROOT
        / "data"
        / "formal_14060"
        / "manifests"
        / "split_manifest.v9t.family_v1.csv"
    )
    simulation_path = (
        PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    )
    data_root = PROJECT_ROOT / "data" / "formal_14060"
    material_ids, label_map, class_counts = _balanced_train_subset(
        split_manifest, per_class=2
    )
    fixed_batches = _build_fixed_train_batches(
        material_ids=material_ids,
        data_root=data_root,
        simulation_path=simulation_path,
        batch_size=batch_size,
        audit_epochs=audit_epochs,
    )

    _set_seed(SEED + 401, device)
    model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    model.train()
    _set_seed(SEED + 402, device)
    residual_head = ResidualClassifier(
        model.config.embed_dim, depth=1, num_classes=len(CLASS_SYSTEMS)
    ).to(device)
    residual_head.train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    head_optimizer = torch.optim.AdamW(residual_head.parameters(), lr=1e-4)
    trace: list[dict[str, float]] = []

    for calibration_step in range(steps):
        started = time.perf_counter()
        batch = fixed_batches[calibration_step % len(fixed_batches)]
        x1 = batch["first"].to(device=device, dtype=torch.float32)
        x2 = batch["second"].to(device=device, dtype=torch.float32)
        labels = torch.tensor(
            [label_map[item] for item in batch["material_ids"]],
            device=device,
            dtype=torch.long,
        )

        optimizer.zero_grad(set_to_none=True)
        output1, output2 = model(x1), model(x2)
        embedding1 = output1["pooled_embedding"]
        embedding2 = output2["pooled_embedding"]
        classification = 0.5 * (
            F.cross_entropy(output1["logits"], labels)
            + F.cross_entropy(output2["logits"], labels)
        )
        classification_accuracy = 0.5 * (
            _mean_accuracy(output1["logits"], labels)
            + _mean_accuracy(output2["logits"], labels)
        )
        prediction_top1_agreement = float(
            (
                output1["logits"].argmax(dim=-1)
                == output2["logits"].argmax(dim=-1)
            )
            .float()
            .mean()
            .detach()
        )
        consistency = js_divergence(output1["logits"], output2["logits"])
        residual_detached = symmetric_measurement_residual(
            embedding1.detach(), embedding2.detach()
        )
        head_optimizer.zero_grad(set_to_none=True)
        probe_logits_before = residual_head(residual_detached)
        probe_loss = F.cross_entropy(probe_logits_before, labels)
        probe_accuracy_before = _mean_accuracy(probe_logits_before, labels)
        probe_entropy_before = float(_mean_entropy(probe_logits_before).detach())
        probe_loss.backward()
        head_optimizer.step()

        previous_requires_grad = [
            parameter.requires_grad for parameter in residual_head.parameters()
        ]
        for parameter in residual_head.parameters():
            parameter.requires_grad_(False)
        residual = symmetric_measurement_residual(embedding1, embedding2)
        probe_logits_after = residual_head(residual)
        probe_loss_after = F.cross_entropy(probe_logits_after, labels)
        probe_accuracy_after = _mean_accuracy(probe_logits_after, labels)
        probe_entropy_after = float(_mean_entropy(probe_logits_after).detach())
        independence = residual_confusion_kl(probe_logits_after)
        classification_gradients = _gradient_norms(classification, model)
        js_gradients = _gradient_norms(consistency, model)
        residual_gradients = _gradient_norms(independence, model)
        classification_gradient = classification_gradients["backbone"]
        js_gradient = js_gradients["backbone"]
        residual_gradient = residual_gradients["backbone"]

        classification.backward()
        optimizer.step()
        for parameter, requires_grad in zip(
            residual_head.parameters(), previous_requires_grad, strict=True
        ):
            parameter.requires_grad_(requires_grad)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        trace.append(
            {
                "calibration_step": float(calibration_step),
                "fixed_batch_index": float(calibration_step % len(fixed_batches)),
                "classification_loss": float(classification.detach()),
                "classification_accuracy": classification_accuracy,
                "js_loss": float(consistency.detach()),
                "residual_confusion_loss": float(independence.detach()),
                "residual_probe_loss": float(probe_loss.detach()),
                "residual_probe_loss_before_update": float(probe_loss.detach()),
                "residual_probe_accuracy_before_update": probe_accuracy_before,
                "residual_probe_entropy_before_update": probe_entropy_before,
                "residual_probe_loss_after_update": float(probe_loss_after.detach()),
                "residual_probe_accuracy_after_update": probe_accuracy_after,
                "residual_probe_entropy_after_update": probe_entropy_after,
                "prediction_js_distance": float(consistency.detach()),
                "prediction_top1_agreement": prediction_top1_agreement,
                "feature_residual_l2_norm": float(
                    residual.detach().float().norm(dim=-1).mean()
                ),
                "residual_head_entropy": probe_entropy_after,
                "classification_gradient_norm": classification_gradient,
                "js_gradient_norm": js_gradient,
                "residual_confusion_gradient_norm": residual_gradient,
                "classification_full_model_gradient_norm": classification_gradients[
                    "full_model"
                ],
                "js_full_model_gradient_norm": js_gradients["full_model"],
                "residual_confusion_full_model_gradient_norm": residual_gradients[
                    "full_model"
                ],
                "classification_task_head_gradient_norm": classification_gradients[
                    "task_head"
                ],
                "js_task_head_gradient_norm": js_gradients["task_head"],
                "residual_confusion_task_head_gradient_norm": residual_gradients[
                    "task_head"
                ],
                "js_to_classification_loss_ratio_at_lambda_1": float(
                    (consistency / classification).detach()
                ),
                "residual_to_classification_loss_ratio_at_lambda_1": float(
                    (independence / classification).detach()
                ),
                "js_to_classification_gradient_ratio_at_lambda_1": js_gradient
                / max(classification_gradient, 1e-30),
                "residual_to_classification_gradient_ratio_at_lambda_1": residual_gradient
                / max(classification_gradient, 1e-30),
                "step_time_seconds": time.perf_counter() - started,
            }
        )

    analysis_trace = trace[burn_in_steps:]
    phase_diagnostics = _phase_diagnostics(trace)
    late_context = phase_diagnostics["late"]["trajectory_context_diagnostics"]
    late_probe = phase_diagnostics["late"]["residual_probe_diagnostics"]
    late_examples = phase_diagnostics["late"]["steps"] * batch_size
    chance_accuracy = 1.0 / len(CLASS_SYSTEMS)
    chance_standard_error = math.sqrt(
        chance_accuracy * (1.0 - chance_accuracy) / late_examples
    )
    diagnostic_accuracy_threshold = chance_accuracy + 2.0 * chance_standard_error
    late_probe_accuracy = late_probe["residual_probe_accuracy_before_update"]["mean"]
    late_probe_loss = late_probe["residual_probe_loss_before_update"]["mean"]
    uniform_cross_entropy = math.log(float(len(CLASS_SYSTEMS)))
    late_classification_accuracy = late_context["classification_accuracy"]["mean"]
    late_classification_loss = phase_diagnostics["late"]["requested_diagnostics"][
        "raw_L_cls"
    ]["mean"]
    classification_learning_signal = {
        "status": "diagnostic_signal_present"
        if late_classification_accuracy > diagnostic_accuracy_threshold
        and late_classification_loss < uniform_cross_entropy
        else "not_demonstrated",
        "late_examples_per_view": late_examples,
        "chance_accuracy": chance_accuracy,
        "descriptive_accuracy_threshold": diagnostic_accuracy_threshold,
        "late_accuracy_mean_across_two_views": late_classification_accuracy,
        "uniform_cross_entropy": uniform_cross_entropy,
        "late_classification_loss_mean": late_classification_loss,
        "not_a_formal_training_or_generalization_claim": True,
    }
    residual_probe_competence = {
        "status": "diagnostic_signal_present"
        if late_probe_accuracy > diagnostic_accuracy_threshold
        and late_probe_loss < uniform_cross_entropy
        else "not_demonstrated",
        "evaluation_scope": "pre-update predictions on each arriving batch in the late third of the repeated-structure Train-only audit stream",
        "late_examples": late_examples,
        "chance_accuracy": chance_accuracy,
        "descriptive_accuracy_threshold": diagnostic_accuracy_threshold,
        "threshold_definition": "chance accuracy plus two binomial standard errors; descriptive screen only because batches and structures are not independent held-out observations",
        "late_pre_update_accuracy_mean": late_probe_accuracy,
        "uniform_cross_entropy": uniform_cross_entropy,
        "late_pre_update_cross_entropy_mean": late_probe_loss,
        "required_before_residual_weight_interpretation": "the residual head must show a non-trivial class-prediction signal before a near-uniform confusion output can be interpreted as successful backbone decorrelation",
        "not_a_generalization_claim": True,
    }
    grids = _registered_grids()
    js_candidates, js_calibration = _candidate_scale_rows(
        analysis_trace,
        weights=grids["lambda_js"],
        weight_name="lambda_js",
        auxiliary_loss_name="js_loss",
        auxiliary_gradient_name="js_gradient_norm",
    )
    residual_candidates, residual_calibration = _candidate_scale_rows(
        analysis_trace,
        weights=grids["lambda_res"],
        weight_name="lambda_res",
        auxiliary_loss_name="residual_confusion_loss",
        auxiliary_gradient_name="residual_confusion_gradient_norm",
    )
    numerical_values = [
        value
        for row in trace
        for key, value in row.items()
        if key != "step_time_seconds"
    ]
    checks = {
        "all_recorded_values_finite": _finite(numerical_values),
        "train_subset_has_all_seven_crystal_systems": set(class_counts)
        == set(CLASS_SYSTEMS),
        "train_subset_is_balanced": set(class_counts.values()) == {2},
        "formal_pampt_b3_used": model.config.variant == "b3"
        and model.config.embed_dim == 128
        and model.config.depth == 4,
        "classification_only_backbone_trajectory": True,
        "residual_head_uses_detached_features_for_probe_update": True,
        "backbone_gradient_scope_excludes_supervised_task_head": True,
        "analysis_window_excludes_initial_burn_in": burn_in_steps > 0,
        "js_gradients_observed": all(row["js_gradient_norm"] > 0.0 for row in analysis_trace),
        "residual_gradients_observed": all(
            row["residual_confusion_gradient_norm"] > 0.0
            for row in analysis_trace
        ),
    }
    candidate_range_gate = {
        "status": "pass"
        if js_calibration["coverage"]["covers_weak_material_and_dominant"]
        and residual_calibration["coverage"]["covers_weak_material_and_dominant"]
        else "blocked",
        "criterion": "each registered grid must include weak-or-negligible, material non-dominant, and dominant median backbone-gradient influence on the Train-only analysis window",
        "js": js_calibration["coverage"],
        "residual": residual_calibration["coverage"],
        "automatic_grid_change_performed": False,
        "validation_performance_used": False,
    }
    pair_manifest = [
        {
            "epoch": batch["epoch"],
            "step": batch["step"],
            "material_ids": batch["material_ids"],
            "parameter_pair_ids": batch["parameter_pair_ids"],
        }
        for batch in fixed_batches
    ]
    deterministic_trace = [
        {key: value for key, value in row.items() if key != "step_time_seconds"}
        for row in trace
    ]
    return {
        "schema_version": "v9-loss-gradient-scale-audit-v3",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "train_only_method_parameter_scale_calibration",
        "formal_training_runs_started": 0,
        "validation_used": False,
        "simulated_test_used": False,
        "real_test_used": False,
        "candidate_selection_performed": False,
        "candidate_specific_training_performed": False,
        "device": str(device),
        "precision": "float32",
        "backbone": {
            "variant": model.config.variant,
            "embedding_dim": model.config.embed_dim,
            "depth": model.config.depth,
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "matches_formal_architecture": True,
        },
        "calibration_protocol": {
            "optimizer_trajectory": "Dynamic/Paired ERM classification only",
            "backbone_optimizer": "AdamW(lr=1e-4)",
            "residual_probe_optimizer": "AdamW(lr=1e-4)",
            "optimizer_steps": steps,
            "burn_in_steps": burn_in_steps,
            "analysis_steps": len(analysis_trace),
            "batch_size_mother_structures": batch_size,
            "paired_spectra_per_step": 2 * batch_size,
            "fixed_train_subset_size": len(material_ids),
            "fixed_pair_batches": len(fixed_batches),
            "fixed_pair_batches_repeated": len(fixed_batches) < steps,
            "maximum_batch_reuse_count": int(math.ceil(steps / len(fixed_batches))),
            "residual_probe_head_training": "one detached-feature update per calibration step; pre-update predictions measure whether earlier probe updates learned a class signal; no probe gradient reaches the backbone",
            "auxiliary_coefficient_during_measurement": 1.0,
            "performance_metric_used": False,
        },
        "reduction_audit": {
            "classification": "PyTorch cross_entropy default reduction=mean over batch",
            "js": "each KL uses reduction=batchmean: sum over seven classes and divide by batch size; the two KL directions are averaged; there is no extra class mean",
            "residual": "KL(q || Uniform) sums over seven classes per sample and then takes one batch mean; there is no repeated class mean",
        },
        "training_data": {
            "split": "train",
            "material_ids": material_ids,
            "class_counts": class_counts,
            "pair_manifest_sha256": _canonical_hash(pair_manifest),
            "pair_manifest": pair_manifest,
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
        },
        "gradient_ratio_bands": {
            "negligible": "R < 0.01",
            "weak": "0.01 <= R < 0.1",
            "material_non_dominant": "0.1 <= R < 1",
            "dominant": "R >= 1",
            "role": "descriptive preregistered calibration bands, not a universal law or performance criterion",
        },
        "js_candidates": js_candidates,
        "residual_candidates": residual_candidates,
        "train_only_gradient_calibration": {
            "lambda_js": js_calibration,
            "lambda_res": residual_calibration,
            "interpretation": "inverse gradient ratios are trajectory-specific diagnostic compensation factors, not theoretically correct or automatically admissible loss weights",
        },
        "gradient_compensation_interpretation_gate": {
            "status": "blocked",
            "reason": "the inverse ratios are large diagnostic signals; loss definitions, view strength, backbone learning stage, and residual-probe competence must be interpreted before any one-time grid revision",
            "automatic_grid_change_performed": False,
            "registered_grids_unchanged": True,
        },
        "candidate_range_gate": candidate_range_gate,
        "trajectory_phase_definition": "three non-overlapping equal-count thirds of the 128-step diagnostic trajectory; these are audit early/middle/late phases, not epochs from a formal 50-epoch run",
        "early_middle_late_diagnostics": phase_diagnostics,
        "classification_learning_signal": classification_learning_signal,
        "residual_probe_competence": residual_probe_competence,
        "full_trace_summary": {
            key: _summary([row[key] for row in trace])
            for key in (
                "classification_loss",
                "classification_accuracy",
                "js_loss",
                "residual_confusion_loss",
                "prediction_js_distance",
                "prediction_top1_agreement",
                "feature_residual_l2_norm",
                "residual_head_entropy",
                "residual_probe_loss_before_update",
                "residual_probe_accuracy_before_update",
                "residual_probe_loss_after_update",
                "residual_probe_accuracy_after_update",
                "classification_gradient_norm",
                "js_gradient_norm",
                "residual_confusion_gradient_norm",
            )
        },
        "analysis_trace": analysis_trace,
        "deterministic_trace_sha256": _canonical_hash(deterministic_trace),
        "runtime": {
            "step_time_seconds": _summary(
                [row["step_time_seconds"] for row in trace]
            ),
            "peak_gpu_memory_mb": float(
                torch.cuda.max_memory_allocated(device) / 1024**2
            )
            if device.type == "cuda"
            else 0.0,
        },
        "checks": checks,
        "decision": "diagnostic audit completed; do not infer a formal lambda from inverse gradient ratios, do not change either registered grid, and keep Validation tuning blocked pending scientific review of the phase diagnostics and residual-probe competence",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--burn-in-steps", type=int, default=DEFAULT_BURN_IN_STEPS)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--audit-epochs", type=int, default=DEFAULT_AUDIT_EPOCHS)
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_loss_gradient_scale_audit.json"),
    )
    args = parser.parse_args()
    report = run_audit(
        device_name=args.device,
        steps=args.steps,
        burn_in_steps=args.burn_in_steps,
        batch_size=args.batch_size,
        audit_epochs=args.audit_epochs,
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
                "candidate_range_gate": report["candidate_range_gate"]["status"],
                "gradient_compensation_interpretation_gate": report[
                    "gradient_compensation_interpretation_gate"
                ]["status"],
                "classification_learning_signal": report[
                    "classification_learning_signal"
                ]["status"],
                "residual_probe_competence": report[
                    "residual_probe_competence"
                ]["status"],
                "output": str(output),
                "checks": report["checks"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
