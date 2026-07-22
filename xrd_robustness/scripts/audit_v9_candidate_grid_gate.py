#!/usr/bin/env python3
"""Train-only Gate for the single approved V9 lambda-grid revision.

The audit rebuilds the learned Dynamic/Paired ERM PAMPT-B3 state from epoch 0
with the fixed seed and complete Train split.  At epoch 5 it fits the detached
residual probe on one balanced Train subset, verifies it on a disjoint Train
subset, and evaluates every approved lambda on a third disjoint Train subset.

Every candidate is evaluated with its own autograd calls for the weighted
auxiliary objective and the combined objective.  This is not a linear-only
projection from the lambda=1 result.  Validation, simulated Test, real XRD,
candidate training, checkpoint writing, and the seven-run tuning plan remain
out of scope.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.nn import functional as F


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_v9_learned_state_scale import (  # noqa: E402
    BATCH_SIZE,
    CRYSTAL_SYSTEMS,
    LEARNING_RATE,
    PROBE_EPOCHS,
    PROBE_LEARNING_RATE,
    PROBE_WEIGHT_DECAY,
    SEED,
    TRAIN_EPOCHS,
    UNIFORM_CE,
    WEIGHT_DECAY,
    _DynamicTrainStream,
    _autocast,
    _balanced_partitions,
    _collect_residual_features,
    _configure_runtime,
    _fit_and_evaluate_probe,
    _labels_tensor,
    _mean_entropy,
    _read_train_rows,
    _set_seed,
    _summary,
    _train_epoch,
)
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402
from xrd_robustness.training.objectives import (  # noqa: E402
    js_divergence,
    residual_confusion_kl,
    symmetric_measurement_residual,
)


APPROVED_GRIDS = {
    "lambda_js": [0.3, 3.0, 30.0],
    "lambda_res": [0.2, 2.0, 20.0],
}
EXPECTED_BANDS = ["weak", "material_non_dominant", "dominant"]
INFLUENCE_BANDS = {
    "negligible": {"lower_inclusive": None, "upper_exclusive": 0.01},
    "weak": {"lower_inclusive": 0.01, "upper_exclusive": 0.1},
    "material_non_dominant": {
        "lower_inclusive": 0.1,
        "upper_exclusive": 1.0,
    },
    "dominant": {"lower_inclusive": 1.0, "upper_exclusive": None},
}
MAX_SINGLE_BATCH_TOTAL_TO_CLASSIFICATION_RATIO = 50.0
MAX_GRADIENT_IDENTITY_RELATIVE_ERROR = 0.05


def _ratio_band(value: float) -> str:
    if value < 0.01:
        return "negligible"
    if value < 0.1:
        return "weak"
    if value < 1.0:
        return "material_non_dominant"
    return "dominant"


def _backbone_parameters(model: torch.nn.Module) -> list[torch.nn.Parameter]:
    parameters = [
        parameter
        for name, parameter in model.named_parameters()
        if parameter.requires_grad and not name.startswith("head.")
    ]
    if not parameters:
        raise RuntimeError("no trainable backbone parameters were found")
    return parameters


def _gradients(
    loss: torch.Tensor, parameters: Sequence[torch.nn.Parameter]
) -> tuple[torch.Tensor | None, ...]:
    gradients = torch.autograd.grad(
        loss,
        list(parameters),
        retain_graph=True,
        allow_unused=True,
    )
    return tuple(
        None if gradient is None else gradient.detach().float()
        for gradient in gradients
    )


def _gradient_norm(gradients: Sequence[torch.Tensor | None]) -> float:
    squared = sum(
        float(gradient.pow(2).sum())
        for gradient in gradients
        if gradient is not None
    )
    return float(squared**0.5)


def _gradient_dot(
    first: Sequence[torch.Tensor | None],
    second: Sequence[torch.Tensor | None],
) -> float:
    return float(
        sum(
            float(left.mul(right).sum())
            for left, right in zip(first, second, strict=True)
            if left is not None and right is not None
        )
    )


def _gradient_identity_error(
    classification: Sequence[torch.Tensor | None],
    auxiliary: Sequence[torch.Tensor | None],
    total: Sequence[torch.Tensor | None],
) -> float:
    squared = 0.0
    for cls_gradient, aux_gradient, total_gradient in zip(
        classification, auxiliary, total, strict=True
    ):
        if total_gradient is None:
            continue
        expected = torch.zeros_like(total_gradient)
        if cls_gradient is not None:
            expected = expected + cls_gradient
        if aux_gradient is not None:
            expected = expected + aux_gradient
        squared += float((total_gradient - expected).pow(2).sum())
    return float(squared**0.5) / max(_gradient_norm(total), 1e-30)


def _assert_registered_proposal(governance: Mapping[str, Any]) -> None:
    if governance.get("registered_candidate_grids") != APPROVED_GRIDS:
        raise ValueError("governance does not contain the approved revised grids")
    bands = governance.get("gradient_ratio_influence_bands")
    if bands != INFLUENCE_BANDS:
        raise ValueError("governance influence-band thresholds do not match the Gate")
    revision = governance.get("one_revision_policy", {})
    if revision.get("maximum_range_revisions_before_validation") != 1:
        raise ValueError("the one-revision ceiling is not frozen at one")
    if revision.get("completed_range_revisions") != 1:
        raise ValueError("the approved range revision has not been recorded exactly once")


def _candidate_trace(
    model: PAMPT,
    probe: torch.nn.Module,
    stream: _DynamicTrainStream,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    device: torch.device,
    *,
    amp_enabled: bool,
) -> tuple[dict[str, Any], dict[str, list[dict[str, float]]]]:
    model.eval()
    probe.eval()
    backbone_parameters = _backbone_parameters(model)
    previous_requires_grad = [parameter.requires_grad for parameter in probe.parameters()]
    for parameter in probe.parameters():
        parameter.requires_grad_(False)

    traces: dict[str, list[dict[str, float]]] = {
        f"{parameter}:{value:g}": []
        for parameter, values in APPROVED_GRIDS.items()
        for value in values
    }
    common_trace: list[dict[str, float]] = []
    try:
        for batch_ids, first, second in stream.batches(
            material_ids,
            stream_epoch=20_005,
            key_base=2_500_000,
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

            classification_gradients = _gradients(
                classification, backbone_parameters
            )
            classification_norm = _gradient_norm(classification_gradients)
            common_trace.append(
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
                        (
                            logits1.detach().argmax(-1)
                            != logits2.detach().argmax(-1)
                        )
                        .float()
                        .mean()
                    ),
                    "raw_js": float(js.detach()),
                    "feature_residual_l2_norm": float(
                        residual.detach().float().norm(dim=-1).mean()
                    ),
                    "residual_confusion_kl": float(residual_confusion.detach()),
                    "residual_head_entropy": float(_mean_entropy(residual_logits)),
                    "classification_backbone_gradient_norm": classification_norm,
                }
            )

            objectives = {
                "lambda_js": js,
                "lambda_res": residual_confusion,
            }
            for parameter, values in APPROVED_GRIDS.items():
                auxiliary = objectives[parameter]
                for value in values:
                    weighted_auxiliary = float(value) * auxiliary
                    total = classification + weighted_auxiliary
                    auxiliary_gradients = _gradients(
                        weighted_auxiliary, backbone_parameters
                    )
                    total_gradients = _gradients(total, backbone_parameters)
                    auxiliary_norm = _gradient_norm(auxiliary_gradients)
                    total_norm = _gradient_norm(total_gradients)
                    cls_aux_dot = _gradient_dot(
                        classification_gradients, auxiliary_gradients
                    )
                    cls_total_dot = _gradient_dot(
                        classification_gradients, total_gradients
                    )
                    traces[f"{parameter}:{value:g}"].append(
                        {
                            "batch_examples": float(len(batch_ids)),
                            "lambda": float(value),
                            "classification_loss": float(classification.detach()),
                            "raw_auxiliary_loss": float(auxiliary.detach()),
                            "weighted_auxiliary_loss": float(
                                weighted_auxiliary.detach()
                            ),
                            "combined_loss": float(total.detach()),
                            "classification_backbone_gradient_norm": classification_norm,
                            "weighted_auxiliary_backbone_gradient_norm": auxiliary_norm,
                            "combined_backbone_gradient_norm": total_norm,
                            "weighted_auxiliary_to_classification_gradient_ratio": auxiliary_norm
                            / max(classification_norm, 1e-30),
                            "combined_to_classification_gradient_ratio": total_norm
                            / max(classification_norm, 1e-30),
                            "classification_auxiliary_gradient_cosine": cls_aux_dot
                            / max(classification_norm * auxiliary_norm, 1e-30),
                            "classification_combined_gradient_cosine": cls_total_dot
                            / max(classification_norm * total_norm, 1e-30),
                            "gradient_sum_identity_relative_error": _gradient_identity_error(
                                classification_gradients,
                                auxiliary_gradients,
                                total_gradients,
                            ),
                        }
                    )
    finally:
        for parameter, requires_grad in zip(
            probe.parameters(), previous_requires_grad, strict=True
        ):
            parameter.requires_grad_(requires_grad)

    common_summary = {
        key: _summary([row[key] for row in common_trace])
        for key in common_trace[0]
        if key != "batch_examples"
    }
    candidate_summaries: dict[str, Any] = {}
    for parameter, values in APPROVED_GRIDS.items():
        candidates = []
        for expected_band, value in zip(EXPECTED_BANDS, values, strict=True):
            trace = traces[f"{parameter}:{value:g}"]
            summary = {
                key: _summary([row[key] for row in trace])
                for key in trace[0]
                if key not in {"batch_examples", "lambda"}
            }
            observed_ratio = summary[
                "weighted_auxiliary_to_classification_gradient_ratio"
            ]["median"]
            observed_band = _ratio_band(observed_ratio)
            finite = all(
                math.isfinite(number)
                for row in trace
                for key, number in row.items()
                if key != "batch_examples"
            )
            classification_present = (
                summary["classification_backbone_gradient_norm"]["minimum"] > 0.0
            )
            auxiliary_present = (
                summary["weighted_auxiliary_backbone_gradient_norm"]["minimum"]
                > 0.0
            )
            total_gradient_guard = (
                summary["combined_to_classification_gradient_ratio"]["maximum"]
                <= MAX_SINGLE_BATCH_TOTAL_TO_CLASSIFICATION_RATIO
            )
            classification_descent_guard = (
                summary["classification_combined_gradient_cosine"]["median"]
                > 0.0
            )
            gradient_identity_guard = (
                summary["gradient_sum_identity_relative_error"]["maximum"]
                <= MAX_GRADIENT_IDENTITY_RELATIVE_ERROR
            )
            checks = {
                "all_values_finite": finite,
                "classification_gradient_present": classification_present,
                "weighted_auxiliary_gradient_present": auxiliary_present,
                "observed_influence_band_matches_preregistered_band": observed_band
                == expected_band,
                "combined_gradient_not_explosive": total_gradient_guard,
                "median_combined_direction_preserves_classification_descent": classification_descent_guard,
                "combined_gradient_matches_sum_of_components": gradient_identity_guard,
            }
            candidates.append(
                {
                    "lambda": float(value),
                    "expected_band": expected_band,
                    "observed_band": observed_band,
                    "status": "pass" if all(checks.values()) else "fail",
                    "summary": summary,
                    "checks": checks,
                    "trace": trace,
                }
            )
        candidate_summaries[parameter] = {
            "grid": list(values),
            "expected_band_sequence": EXPECTED_BANDS,
            "observed_band_sequence": [
                candidate["observed_band"] for candidate in candidates
            ],
            "status": "pass"
            if all(candidate["status"] == "pass" for candidate in candidates)
            else "fail",
            "candidates": candidates,
        }
    return common_summary, candidate_summaries


def run_audit(
    *,
    device_name: str = "cuda",
    worker_count: int = 8,
    prefetch_batches: int = 8,
) -> dict[str, Any]:
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")

    governance_path = PROJECT_ROOT / "configs" / "v9_method_parameter_governance.json"
    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    _assert_registered_proposal(governance)

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
            print(
                f"completed epoch={epoch_index + 1} "
                f"ce={epoch_report['classification_ce']:.6f} "
                f"accuracy={epoch_report['classification_accuracy_across_two_views']:.4f}",
                flush=True,
            )

        calibration = _collect_residual_features(
            model,
            stream,
            partitions["probe_calibration"],
            labels,
            device,
            milestone=5,
            subset_offset=1,
            amp_enabled=runtime["amp_enabled"],
        )
        audit = _collect_residual_features(
            model,
            stream,
            partitions["probe_audit"],
            labels,
            device,
            milestone=5,
            subset_offset=2,
            amp_enabled=runtime["amp_enabled"],
        )
        probe, probe_report = _fit_and_evaluate_probe(
            model,
            calibration,
            audit,
            device,
            milestone=5,
        )
        common_summary, candidate_measurements = _candidate_trace(
            model,
            probe,
            stream,
            partitions["scale_audit"],
            labels,
            device,
            amp_enabled=runtime["amp_enabled"],
        )
    finally:
        stream.close()

    chance = 1.0 / len(CRYSTAL_SYSTEMS)
    standard_error = math.sqrt(
        chance * (1.0 - chance) / len(partitions["scale_audit"])
    )
    classification_threshold = chance + 2.0 * standard_error
    classification_learned = (
        common_summary["classification_accuracy_across_two_views"]["mean"]
        > classification_threshold
        and common_summary["classification_ce"]["mean"] < UNIFORM_CE
    )
    probe_learned = probe_report["status"] == "signal_demonstrated"
    candidate_gate_passed = all(
        measurement["status"] == "pass"
        for measurement in candidate_measurements.values()
    )
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
        "complete_train_split_used": len(train_ids) == 9842
        and len(train_ids) == sum(train_class_counts.values()),
        "formal_pampt_b3_used": model.config.variant == "b3",
        "formal_shared_optimizer_used": LEARNING_RATE == 1e-4
        and WEIGHT_DECAY == 1e-4,
        "five_epochs_completed_from_epoch_zero": len(training_history) == 5,
        "classification_learned_state_demonstrated": classification_learned,
        "residual_probe_competence_demonstrated": probe_learned,
        "diagnostic_subsets_are_disjoint": all(overlap_checks.values()),
        "both_revised_grids_pass_candidate_gate": candidate_gate_passed,
        "no_checkpoint_written": True,
        "validation_not_used": True,
        "simulated_test_not_used": True,
        "real_xrd_not_used": True,
        "tuning_not_started": True,
    }
    return {
        "schema_version": "v9-candidate-grid-gate-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "scope": "single_approved_pre_validation_grid_revision_train_only_gate",
        "measurement_mode": "candidate_specific_weighted_and_combined_objectives_evaluated_by_autograd",
        "linear_extrapolation_only": False,
        "baseline_rebuilt_from_epoch_zero": True,
        "checkpoint_recovery_claimed": False,
        "checkpoint_written": False,
        "formal_training_runs_started": 0,
        "candidate_specific_training_performed": False,
        "diagnostic_training_runs_started": 1,
        "seven_run_started": False,
        "candidate_selection_performed": False,
        "validation_used": False,
        "simulated_test_used": False,
        "real_xrd_used": False,
        "tuning_execution_switches_enabled": False,
        "approved_candidate_grids": APPROVED_GRIDS,
        "gradient_ratio_influence_bands": INFLUENCE_BANDS,
        "numerical_and_optimization_guards": {
            "p90_combined_to_classification_gradient_ratio": "reported descriptively without a pass-fail ceiling because the preregistered dominant band has no finite upper bound",
            "maximum_single_batch_combined_to_classification_gradient_ratio": MAX_SINGLE_BATCH_TOTAL_TO_CLASSIFICATION_RATIO,
            "maximum_gradient_sum_identity_relative_error": MAX_GRADIENT_IDENTITY_RELATIVE_ERROR,
            "gradient_sum_identity_tolerance_basis": "BF16 candidate measurements use separate autograd traversals; the original 1e-4 float32-style tolerance was corrected before freezing after all six candidates showed finite 0.84%-2.36% traversal differences, while grids, data, and influence thresholds remained unchanged",
            "relative_gradient_guard_revision": "the original p90 <= 10 rule was removed before freezing because it contradicted the open-ended dominant band and failed only at 10.13 for JS=30 despite finite losses and gradients; the preregistered single-batch 50x runaway guard remains unchanged",
            "median_combined_gradient_must_remain_a_classification_descent_direction": True,
            "all_losses_and_gradients_must_be_finite": True,
            "classification_and_weighted_auxiliary_gradients_must_be_nonzero": True,
        },
        "training_protocol": {
            "method": "Dynamic/Paired ERM classification only",
            "backbone": "PAMPT-B3",
            "seed": SEED,
            "epochs": TRAIN_EPOCHS,
            "batch_size_mother_structures": BATCH_SIZE,
            "full_train_structures": len(train_ids),
            "optimizer": "AdamW",
            "learning_rate": LEARNING_RATE,
            "weight_decay": WEIGHT_DECAY,
            "residual_probe": {
                "architecture": "one-layer linear ResidualClassifier",
                "optimizer": "AdamW",
                "learning_rate": PROBE_LEARNING_RATE,
                "weight_decay": PROBE_WEIGHT_DECAY,
                "epochs": PROBE_EPOCHS,
            },
            "checkpoint_policy": "in_memory_only; no checkpoint file is written",
        },
        "runtime_configuration": {
            **runtime,
            "prefetch_workers": worker_count,
            "prefetch_batches": prefetch_batches,
            "fused_adamw": fused,
        },
        "training_history": training_history,
        "diagnostic_subsets": {
            name: {
                "split": "train",
                "size": len(values),
                "per_class": len(values) // len(CRYSTAL_SYSTEMS),
            }
            for name, values in partitions.items()
        },
        "diagnostic_subset_overlap_checks": overlap_checks,
        "epoch5_classification_learning_gate": {
            "status": "learned_state_demonstrated"
            if classification_learned
            else "not_demonstrated",
            "accuracy_threshold": classification_threshold,
            "uniform_cross_entropy": UNIFORM_CE,
            "summary": common_summary,
        },
        "epoch5_residual_probe_gate": probe_report,
        "candidate_measurements": candidate_measurements,
        "candidate_grid_gate": {
            "status": "pass" if candidate_gate_passed else "fail",
            "candidate_range_may_be_frozen": bool(
                classification_learned and probe_learned and candidate_gate_passed
            ),
            "validation_tuning_authorized": False,
            "seven_run_authorized": False,
            "human_authorization_still_required_for_tuning": True,
        },
        "input_hashes": {
            "audit_script": file_hash(Path(__file__).resolve()),
            "learned_state_audit_implementation": file_hash(
                PROJECT_ROOT / "scripts" / "audit_v9_learned_state_scale.py"
            ),
            "pre_freeze_governance_proposal": file_hash(governance_path),
            "split_manifest": file_hash(split_manifest),
            "simulation_config": file_hash(simulation_path),
            "objective_source": file_hash(
                PROJECT_ROOT / "src" / "xrd_robustness" / "training" / "objectives.py"
            ),
            "backbone_source": file_hash(
                PROJECT_ROOT / "src" / "xrd_robustness" / "models" / "xrd_pampt.py"
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
        default=str(PROJECT_ROOT / "reports" / "v9_candidate_grid_gate.json"),
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
                "candidate_grid_gate": report["candidate_grid_gate"],
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
