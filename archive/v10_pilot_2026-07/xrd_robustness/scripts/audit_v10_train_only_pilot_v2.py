#!/usr/bin/env python3
"""Run V10 Pilot v2 after a full-Train learned-state pretraining phase."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_v9_learned_state_scale import (  # noqa: E402
    _balanced_partitions,
    _configure_runtime,
    _read_train_rows,
    _set_seed,
)
from v10_p0_gate_panel import (  # noqa: E402
    _balanced_take,
    _build_renderer,
    _render_panel,
)
from v10_pilot_config import (  # noqa: E402
    LAMBDA_PERTURB_TARGET,
    LAMBDA_RES_TARGET,
    PANEL_STRUCTURES_PER_CLASS,
    PERMUTATIONS,
    PILOT_EPOCHS,
    RAMP_EPOCHS,
    SEED,
    SELECTED_STRENGTH_FAMILIES,
    TARGET_NAMES,
    TARGET_SCALES,
    TRAIN_STRUCTURES_PER_CLASS,
    WARMUP_EPOCHS,
)
from v10_pilot_evaluation import (  # noqa: E402
    classification_metrics,
    evaluate_branch,
)
from v10_pilot_targets import balanced_train_take, canonical_hash  # noqa: E402
from v10_pilot_training import PilotTrainStream, new_optimizer  # noqa: E402
from v10_pilot_v2_evaluation import (  # noqa: E402
    learned_state_gate,
    pilot_v2_decision,
    premise_recheck,
)
from v10_pilot_v2_training import (  # noqa: E402
    clone_learned_branches,
    pretrain_erm_epoch,
    train_matched_branch_epoch,
)
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402

SCHEMA_VERSION = "v10-train-only-pilot-v2"
PRETRAIN_EPOCHS = 5
LEARNED_STATE_STREAM_EPOCH = 30_000
LEARNED_STATE_KEY_BASE = 30_000_000


def _render_in_range_classification_panel(
    *,
    stream: PilotTrainStream,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
) -> dict[str, np.ndarray]:
    """Render one deterministic train-profile pair per audit structure."""
    first_rows: list[np.ndarray] = []
    second_rows: list[np.ndarray] = []
    crystal_labels: list[int] = []
    sample_groups: list[str] = []
    for batch_ids, first, second, _, _ in stream.batches(
        material_ids,
        stream_epoch=LEARNED_STATE_STREAM_EPOCH,
        key_base=LEARNED_STATE_KEY_BASE,
    ):
        first_rows.append(np.asarray(first, dtype=np.float32))
        second_rows.append(np.asarray(second, dtype=np.float32))
        crystal_labels.extend(int(labels[material_id]) for material_id in batch_ids)
        sample_groups.extend(str(material_id) for material_id in batch_ids)
    return {
        "first": np.concatenate(first_rows, axis=0),
        "second": np.concatenate(second_rows, axis=0),
        "crystal_labels": np.asarray(crystal_labels, dtype=np.int64),
        "sample_groups": np.asarray(sample_groups),
        "profile": np.asarray(["train"] * len(sample_groups)),
    }


def _base_report(
    *,
    started: float,
    runtime: dict[str, Any],
    gate_path: Path,
    gate_status: str,
    data_root: Path,
    split_manifest: Path,
    simulation_path: Path,
    derived_simulation: dict[str, Any],
    train_class_counts: dict[str, int],
    train_ids_all: list[str],
    pilot_train_ids: list[str],
    calibration_ids: list[str],
    audit_ids: list[str],
    pretrain_epochs: int,
    branch_epochs: int,
    train_structures_per_class: int,
    panel_structures_per_class: int,
    permutations: int,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": (
            "Learned-state-gated matched Train-only V10 Pilot v2, run before any "
            "formal V10 hyperparameter selection"
        ),
        "status": "diagnostic_complete",
        "gate_prerequisite": {
            "required_report": str(gate_path),
            "required_report_sha256": file_hash(gate_path),
            "required_v10_premise_gate": "PASS",
            "observed_v10_premise_gate": gate_status,
        },
        "protocol": {
            "pretraining_method": "Dynamic/Paired ERM",
            "pretraining_epochs": pretrain_epochs,
            "pretraining_structures": len(train_ids_all),
            "pretraining_uses_complete_frozen_train_split": True,
            "learned_state_gate_profile": "train",
            "premise_recheck_profiles": "controlled single-factor measurement panel",
            "branch_epochs": branch_epochs,
            "branch_train_structures_per_class": train_structures_per_class,
            "branch_total_train_structures": len(pilot_train_ids),
            "panel_structures_per_class": panel_structures_per_class,
            "permutation_draws": permutations,
            "branches": ["erm", "v9_residual", "v10_supervised"],
            "branches_start_from_same_learned_model_state": True,
            "branches_start_from_same_learned_main_optimizer_state": True,
            "matched_dynamic_pairs": True,
            "matched_dropout_seed_per_batch": True,
            "lambda_res_target": LAMBDA_RES_TARGET,
            "lambda_perturb_target": LAMBDA_PERTURB_TARGET,
            "warmup_epochs_within_branch_phase": WARMUP_EPOCHS,
            "ramp_epochs_within_branch_phase": RAMP_EPOCHS,
            "not_hyperparameter_selection": True,
        },
        "perturbation_supervision": {
            "target_names": list(TARGET_NAMES),
            "target_scales": TARGET_SCALES,
            "scientific_families": list(SELECTED_STRENGTH_FAMILIES),
            "excluded_from_core_strength_target": ["shift", "texture"],
            "signed_residual_direction": "second_minus_first",
        },
        "inputs": {
            "data_root": str(data_root),
            "split_manifest": str(split_manifest),
            "split_manifest_sha256": file_hash(split_manifest),
            "simulation_config": str(simulation_path),
            "simulation_config_sha256": file_hash(simulation_path),
            "simulation_status": json.loads(
                simulation_path.read_text(encoding="utf-8")
            ).get("status"),
            "derived_panel_config_sha256": derived_simulation[
                "derived_gate_config_sha256"
            ],
            "train_class_counts": train_class_counts,
            "complete_train_ids_sha256": canonical_hash(train_ids_all),
            "branch_train_ids_sha256": canonical_hash(pilot_train_ids),
            "calibration_ids_sha256": canonical_hash(calibration_ids),
            "audit_ids_sha256": canonical_hash(audit_ids),
        },
        "data_isolation": {
            "train_only": True,
            "validation_read": False,
            "simulated_test_read": False,
            "real_xrd_read": False,
            "checkpoint_written": False,
            "v9_parameter_selection": False,
            "v10_parameter_selection": False,
            "formal_v10_training": False,
            "branch_training_calibration_audit_structures_disjoint": True,
            "learned_state_panel_is_not_a_generalization_panel": True,
        },
        "runtime": runtime,
        "pretraining_history": [],
        "learned_state_evaluation": None,
        "learned_state_gate": None,
        "premise_recheck": None,
        "branch_training_history": [],
        "branch_epoch_evaluations": [],
        "pilot_decision": None,
        "interpretation_limits": [
            "This Pilot cannot change the frozen V9 seven-run grid.",
            "The fixed Pilot weights are diagnostic constants, not selected hyperparameters.",
            "The learned-state panel checks optimization eligibility, not held-out generalization.",
            "A PASS supports designing formal V10 validation; it never authorizes it automatically.",
            "Only background, broadening, and noise are core strength-supervision families.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }


def _finalize_runtime(report: dict[str, Any], started: float, device: torch.device) -> None:
    report["runtime_seconds"] = time.perf_counter() - started
    if device.type == "cuda":
        report["runtime"]["peak_cuda_memory_bytes"] = int(
            torch.cuda.max_memory_allocated(device)
        )


def run_pilot_v2(
    *,
    device_name: str = "cuda",
    worker_count: int = 4,
    prefetch_batches: int = 4,
    pretrain_epochs: int = PRETRAIN_EPOCHS,
    branch_epochs: int = PILOT_EPOCHS,
    train_structures_per_class: int = TRAIN_STRUCTURES_PER_CLASS,
    panel_structures_per_class: int = PANEL_STRUCTURES_PER_CLASS,
    permutations: int = PERMUTATIONS,
) -> dict[str, Any]:
    if pretrain_epochs <= 0 or branch_epochs <= 0:
        raise ValueError("pretraining and branch epochs must be positive")
    if train_structures_per_class <= 0 or panel_structures_per_class <= 1:
        raise ValueError("Pilot structure counts are invalid")
    if permutations < 20:
        raise ValueError("at least 20 permutation draws are required")
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    runtime = _configure_runtime(device)
    _set_seed(SEED, device)
    started = time.perf_counter()

    gate_path = PROJECT_ROOT / "reports" / "v10_p0_measurement_information_gate.json"
    if not gate_path.exists():
        raise FileNotFoundError("V10-P0 prerequisite report is missing: " + str(gate_path))
    gate_report = json.loads(gate_path.read_text(encoding="utf-8"))
    gate_status = gate_report.get("gate_decision", {}).get("v10_premise_gate")
    if gate_status != "PASS":
        raise RuntimeError(
            f"V10 Pilot v2 requires v10_premise_gate=PASS, observed {gate_status!r}"
        )

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = data_root / "manifests" / "split_manifest.json"
    simulation_path = PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    train_ids_all, labels, train_class_counts = _read_train_rows(split_manifest)
    partitions = _balanced_partitions(train_ids_all, labels)
    reserved = set().union(*[set(values) for values in partitions.values()])
    eligible_branch_ids = [
        material_id for material_id in train_ids_all if material_id not in reserved
    ]
    pilot_train_ids = balanced_train_take(
        eligible_branch_ids,
        labels,
        per_class=train_structures_per_class,
        seed=SEED + 1000,
    )
    calibration_ids = _balanced_take(
        partitions["probe_calibration"],
        labels,
        per_class=panel_structures_per_class,
        seed=SEED + 2000,
    )
    audit_ids = _balanced_take(
        partitions["probe_audit"],
        labels,
        per_class=panel_structures_per_class,
        seed=SEED + 3000,
    )
    if set(pilot_train_ids) & (set(calibration_ids) | set(audit_ids)):
        raise RuntimeError("V10 Pilot v2 branch training and panels overlap")
    if set(calibration_ids) & set(audit_ids):
        raise RuntimeError("V10 Pilot v2 calibration and audit panels overlap")

    sampler, factory, derived_simulation = _build_renderer(simulation_path)
    calibration_panel = _render_panel(
        material_ids=calibration_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=21,
    )
    audit_panel = _render_panel(
        material_ids=audit_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=22,
    )

    report = _base_report(
        started=started,
        runtime=runtime,
        gate_path=gate_path,
        gate_status=gate_status,
        data_root=data_root,
        split_manifest=split_manifest,
        simulation_path=simulation_path,
        derived_simulation=derived_simulation,
        train_class_counts=train_class_counts,
        train_ids_all=train_ids_all,
        pilot_train_ids=pilot_train_ids,
        calibration_ids=calibration_ids,
        audit_ids=audit_ids,
        pretrain_epochs=pretrain_epochs,
        branch_epochs=branch_epochs,
        train_structures_per_class=train_structures_per_class,
        panel_structures_per_class=panel_structures_per_class,
        permutations=permutations,
    )

    base_model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    base_optimizer = new_optimizer(base_model.parameters(), device)
    pretrain_stream = PilotTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    learned_state_panel: dict[str, np.ndarray] | None = None
    try:
        for epoch_index in range(pretrain_epochs):
            epoch_report = pretrain_erm_epoch(
                model=base_model,
                optimizer=base_optimizer,
                stream=pretrain_stream,
                train_ids=train_ids_all,
                labels=labels,
                device=device,
                epoch_index=epoch_index,
                amp_enabled=runtime["amp_enabled"],
            )
            report["pretraining_history"].append(epoch_report)
            print(
                f"v10-v2 learned-state epoch={epoch_index + 1} "
                f"ce={epoch_report['classification_ce']:.6f} "
                f"accuracy={epoch_report['classification_accuracy_across_two_views']:.4f}",
                flush=True,
            )
        learned_state_panel = _render_in_range_classification_panel(
            stream=pretrain_stream,
            material_ids=audit_ids,
            labels=labels,
        )
    finally:
        pretrain_stream.close()
    if learned_state_panel is None:
        raise RuntimeError("learned-state panel was not rendered")

    learned_classification = classification_metrics(
        base_model,
        learned_state_panel,
        device,
        amp_enabled=runtime["amp_enabled"],
    )
    state_sampling_units = len(np.unique(learned_state_panel["sample_groups"]))
    state_gate = learned_state_gate(
        learned_classification,
        audit_sampling_units=state_sampling_units,
    )
    report["learned_state_evaluation"] = {
        "profile": "train",
        "classification": learned_classification,
        "sampling_units": state_sampling_units,
        "not_a_generalization_claim": True,
    }
    report["learned_state_gate"] = state_gate
    if state_gate["status"] != "PASS":
        report["pilot_decision"] = {
            "pilot_status": "INELIGIBLE_LEARNED_STATE",
            "automatic_formal_v10_authorization": False,
            "requires_human_review": True,
            "rationale": (
                "The paired-ERM backbone did not demonstrate in-range classification "
                "learning; V10 mechanism evidence is therefore not interpretable."
            ),
        }
        _finalize_runtime(report, started, device)
        return report

    learned_premise_evaluation = evaluate_branch(
        base_model,
        calibration_panel,
        audit_panel,
        device,
        amp_enabled=runtime["amp_enabled"],
        permutations=permutations,
        seed=SEED + 60_000,
    )
    premise = premise_recheck(learned_premise_evaluation)
    report["premise_recheck"] = {
        "decision": premise,
        "evaluation": learned_premise_evaluation,
    }
    if premise["status"] != "PASS":
        report["pilot_decision"] = {
            "pilot_status": "HOLD_PREMISE_RECHECK",
            "automatic_formal_v10_authorization": False,
            "requires_human_review": True,
            "rationale": (
                "The learned backbone did not reproduce the complete measurement-plus-"
                "crystal-leakage premise required for a matched V10 comparison."
            ),
        }
        _finalize_runtime(report, started, device)
        return report

    models, v9_head, v10_head, perturbation_regressor, optimizers = (
        clone_learned_branches(
            base_model=base_model,
            base_optimizer=base_optimizer,
            device=device,
        )
    )
    del base_model, base_optimizer
    if device.type == "cuda":
        torch.cuda.empty_cache()

    branch_stream = PilotTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    try:
        for branch_epoch_index in range(branch_epochs):
            report["branch_training_history"].append(
                train_matched_branch_epoch(
                    models=models,
                    v9_head=v9_head,
                    v10_head=v10_head,
                    perturbation_regressor=perturbation_regressor,
                    optimizers=optimizers,
                    stream=branch_stream,
                    train_ids=pilot_train_ids,
                    labels=labels,
                    device=device,
                    branch_epoch_index=branch_epoch_index,
                    amp_enabled=runtime["amp_enabled"],
                )
            )
            epoch_evaluation = {
                "epoch": branch_epoch_index + 1,
                "branches": {},
            }
            for branch_index, (branch, model) in enumerate(models.items()):
                epoch_evaluation["branches"][branch] = evaluate_branch(
                    model,
                    calibration_panel,
                    audit_panel,
                    device,
                    amp_enabled=runtime["amp_enabled"],
                    permutations=permutations,
                    seed=(
                        SEED
                        + 100_000
                        + branch_epoch_index * 10_000
                        + branch_index * 1000
                    ),
                )
            report["branch_epoch_evaluations"].append(epoch_evaluation)
    finally:
        branch_stream.close()

    report["pilot_decision"] = pilot_v2_decision(
        report["branch_epoch_evaluations"][-1]["branches"]
    )
    _finalize_runtime(report, started, device)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--prefetch-batches", type=int, default=4)
    parser.add_argument("--pretrain-epochs", type=int, default=PRETRAIN_EPOCHS)
    parser.add_argument("--branch-epochs", type=int, default=PILOT_EPOCHS)
    parser.add_argument(
        "--train-structures-per-class", type=int, default=TRAIN_STRUCTURES_PER_CLASS
    )
    parser.add_argument(
        "--panel-structures-per-class", type=int, default=PANEL_STRUCTURES_PER_CLASS
    )
    parser.add_argument("--permutations", type=int, default=PERMUTATIONS)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports" / "v10_train_only_pilot_v2.json",
    )
    args = parser.parse_args()
    report = run_pilot_v2(
        device_name=args.device,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
        pretrain_epochs=args.pretrain_epochs,
        branch_epochs=args.branch_epochs,
        train_structures_per_class=args.train_structures_per_class,
        panel_structures_per_class=args.panel_structures_per_class,
        permutations=args.permutations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(report["pilot_decision"], indent=2, sort_keys=True))
    print(f"report={args.output}")
    print(f"sha256={file_hash(args.output)}")


if __name__ == "__main__":
    main()
