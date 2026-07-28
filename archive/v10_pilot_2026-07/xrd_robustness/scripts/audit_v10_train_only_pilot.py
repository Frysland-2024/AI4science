#!/usr/bin/env python3
"""Run the matched Train-only V10 simulator-supervised residual Pilot."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import time
from typing import Any

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
    SCHEMA_VERSION,
    SEED,
    SELECTED_STRENGTH_FAMILIES,
    TARGET_NAMES,
    TARGET_SCALES,
    TRAIN_STRUCTURES_PER_CLASS,
    WARMUP_EPOCHS,
)
from v10_pilot_evaluation import evaluate_branch, pilot_decision  # noqa: E402
from v10_pilot_targets import balanced_train_take, canonical_hash  # noqa: E402
from v10_pilot_training import PilotTrainStream, new_optimizer, train_epoch  # noqa: E402
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402
from xrd_robustness.training import (  # noqa: E402
    PerturbationDeltaRegressor,
    ResidualClassifier,
)


def run_pilot(
    *,
    device_name: str = "cuda",
    worker_count: int = 4,
    prefetch_batches: int = 4,
    epochs: int = PILOT_EPOCHS,
    train_structures_per_class: int = TRAIN_STRUCTURES_PER_CLASS,
    panel_structures_per_class: int = PANEL_STRUCTURES_PER_CLASS,
    permutations: int = PERMUTATIONS,
) -> dict[str, Any]:
    if epochs <= 0:
        raise ValueError("Pilot epochs must be positive")
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
        raise FileNotFoundError(
            "V10-P0 prerequisite report is missing: " + str(gate_path)
        )
    gate_report = json.loads(gate_path.read_text(encoding="utf-8"))
    gate_status = gate_report.get("gate_decision", {}).get("v10_premise_gate")
    if gate_status != "PASS":
        raise RuntimeError(
            f"V10 Pilot requires v10_premise_gate=PASS, observed {gate_status!r}"
        )

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = data_root / "manifests" / "split_manifest.json"
    simulation_path = (
        PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    )
    train_ids_all, labels, train_class_counts = _read_train_rows(split_manifest)
    partitions = _balanced_partitions(train_ids_all, labels)
    reserved = set().union(*[set(values) for values in partitions.values()])
    eligible_train_ids = [
        material_id for material_id in train_ids_all if material_id not in reserved
    ]
    pilot_train_ids = balanced_train_take(
        eligible_train_ids,
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
        raise RuntimeError("V10 Pilot training and controlled panels overlap")
    if set(calibration_ids) & set(audit_ids):
        raise RuntimeError("V10 Pilot calibration and audit panels overlap")

    base_model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    base_state = copy.deepcopy(base_model.state_dict())
    models = {
        "erm": PAMPT(PAMPTConfig(variant="b3")).to(device),
        "v9_residual": PAMPT(PAMPTConfig(variant="b3")).to(device),
        "v10_supervised": PAMPT(PAMPTConfig(variant="b3")).to(device),
    }
    for model in models.values():
        model.load_state_dict(base_state)
    del base_model

    _set_seed(SEED + 4000, device)
    residual_template = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(
        device
    )
    residual_state = copy.deepcopy(residual_template.state_dict())
    v9_head = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(device)
    v10_head = ResidualClassifier(models["erm"].config.embed_dim, depth=1).to(device)
    v9_head.load_state_dict(residual_state)
    v10_head.load_state_dict(residual_state)
    del residual_template
    _set_seed(SEED + 5000, device)
    perturbation_regressor = PerturbationDeltaRegressor(
        models["erm"].config.embed_dim, output_dim=len(TARGET_NAMES), depth=1
    ).to(device)

    optimizers = {
        "erm": new_optimizer(models["erm"].parameters(), device),
        "v9_main": new_optimizer(models["v9_residual"].parameters(), device),
        "v9_aux": new_optimizer(v9_head.parameters(), device),
        "v10_main": new_optimizer(models["v10_supervised"].parameters(), device),
        "v10_aux": new_optimizer(
            list(v10_head.parameters()) + list(perturbation_regressor.parameters()),
            device,
        ),
    }

    stream = PilotTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    sampler, factory, derived_simulation = _build_renderer(simulation_path)
    calibration_panel = _render_panel(
        material_ids=calibration_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=11,
    )
    audit_panel = _render_panel(
        material_ids=audit_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=12,
    )

    history: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    try:
        for epoch_index in range(epochs):
            history.append(
                train_epoch(
                    models=models,
                    v9_head=v9_head,
                    v10_head=v10_head,
                    perturbation_regressor=perturbation_regressor,
                    optimizers=optimizers,
                    stream=stream,
                    train_ids=pilot_train_ids,
                    labels=labels,
                    device=device,
                    epoch_index=epoch_index,
                    amp_enabled=runtime["amp_enabled"],
                )
            )
            epoch_evaluation = {"epoch": epoch_index + 1, "branches": {}}
            for branch_index, (branch, model) in enumerate(models.items()):
                epoch_evaluation["branches"][branch] = evaluate_branch(
                    model,
                    calibration_panel,
                    audit_panel,
                    device,
                    amp_enabled=runtime["amp_enabled"],
                    permutations=permutations,
                    seed=SEED + 10_000 + epoch_index * 10_000 + branch_index * 1000,
                )
            evaluations.append(epoch_evaluation)
    finally:
        stream.close()

    decision = pilot_decision(evaluations[-1]["branches"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "purpose": (
            "Matched Train-only V10 Pilot testing optimization feasibility and "
            "mechanism direction before any formal V10 experiment"
        ),
        "status": "diagnostic_complete",
        "gate_prerequisite": {
            "required_report": str(gate_path),
            "required_report_sha256": file_hash(gate_path),
            "required_v10_premise_gate": "PASS",
            "observed_v10_premise_gate": gate_status,
        },
        "protocol": {
            "epochs": epochs,
            "train_structures_per_class": train_structures_per_class,
            "total_train_structures": len(pilot_train_ids),
            "panel_structures_per_class": panel_structures_per_class,
            "permutation_draws": permutations,
            "branches": ["erm", "v9_residual", "v10_supervised"],
            "matched_initialization": True,
            "matched_dynamic_pairs": True,
            "matched_dropout_seed_per_batch": True,
            "lambda_res_target": LAMBDA_RES_TARGET,
            "lambda_perturb_target": LAMBDA_PERTURB_TARGET,
            "warmup_epochs": WARMUP_EPOCHS,
            "ramp_epochs": RAMP_EPOCHS,
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
            "pilot_train_ids_sha256": canonical_hash(pilot_train_ids),
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
            "formal_v10_training": False,
            "training_calibration_audit_structures_disjoint": True,
        },
        "runtime": runtime,
        "training_history": history,
        "epoch_evaluations": evaluations,
        "pilot_decision": decision,
        "interpretation_limits": [
            "PASS supports designing a formal V10 comparison; it does not authorize it automatically.",
            "This Pilot cannot change the frozen V9 grid, select V9 lambdas, or replace formal Validation selection.",
            "The fixed Pilot weights are diagnostic values and are not formal V10 hyperparameters.",
            "Only background, broadening, and noise are core strength-supervision families in this Pilot.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }
    if device.type == "cuda":
        report["runtime"]["peak_cuda_memory_bytes"] = int(
            torch.cuda.max_memory_allocated(device)
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--prefetch-batches", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=PILOT_EPOCHS)
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
        default=PROJECT_ROOT / "reports" / "v10_train_only_pilot.json",
    )
    args = parser.parse_args()
    report = run_pilot(
        device_name=args.device,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
        epochs=args.epochs,
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
