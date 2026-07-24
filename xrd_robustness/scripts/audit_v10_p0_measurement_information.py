#!/usr/bin/env python3
"""Train-only V10-P0 gate for simulator-known measurement information.

This diagnostic rebuilds one five-epoch Dynamic/Paired ERM PAMPT-B3 state in
memory, freezes it, and tests whether its feature residual contains
simulator-known measurement information on unseen Train structures. It reads no
Validation, simulated Test, or real XRD, writes no checkpoint, changes no V9
parameter, and cannot automatically authorize V10.
"""

from __future__ import annotations

import argparse
import hashlib
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
    LEARNING_RATE,
    SEED,
    TRAIN_EPOCHS,
    WEIGHT_DECAY,
    _DynamicTrainStream,
    _balanced_partitions,
    _configure_runtime,
    _read_train_rows,
    _set_seed,
    _train_epoch,
)
from v10_p0_gate_panel import (  # noqa: E402
    FAMILIES,
    _balanced_take,
    _build_renderer,
    _extract_features,
    _family_regressions,
    _render_panel,
)
from v10_p0_gate_stats import (  # noqa: E402
    RAW_POOL_BINS,
    RIDGE_ALPHA,
    _classification_probe,
    _gate_decision,
    _normalized_strength,
    _pooled_absolute_spectrum_difference,
    _regression_probe,
)
from xrd_robustness.experiment import file_hash  # noqa: E402
from xrd_robustness.models import PAMPT, PAMPTConfig  # noqa: E402


SCHEMA_VERSION = "v10-p0-measurement-information-gate-v1"
DEFAULT_STRUCTURES_PER_CRYSTAL_SYSTEM = 10
DEFAULT_PERMUTATIONS = 200


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def run_gate(
    *,
    device_name: str = "cuda",
    worker_count: int = 4,
    prefetch_batches: int = 4,
    structures_per_crystal_system: int = DEFAULT_STRUCTURES_PER_CRYSTAL_SYSTEM,
    permutations: int = DEFAULT_PERMUTATIONS,
) -> dict[str, Any]:
    if structures_per_crystal_system <= 1:
        raise ValueError("structures_per_crystal_system must be greater than one")
    if permutations < 20:
        raise ValueError("at least 20 permutation draws are required")
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable")
    runtime = _configure_runtime(device)
    _set_seed(SEED + 100_000, device)

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = (
        data_root / "manifests" / "split_manifest.v9t.family_v1.csv"
    )
    simulation_path = (
        PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    )
    train_ids, labels, train_class_counts = _read_train_rows(split_manifest)
    partitions = _balanced_partitions(train_ids, labels)
    calibration_ids = _balanced_take(
        partitions["probe_calibration"],
        labels,
        per_class=structures_per_crystal_system,
        seed=SEED + 101_000,
    )
    audit_ids = _balanced_take(
        partitions["probe_audit"],
        labels,
        per_class=structures_per_crystal_system,
        seed=SEED + 102_000,
    )
    if set(calibration_ids) & set(audit_ids):
        raise RuntimeError("V10-P0 calibration and audit structures overlap")

    model = PAMPT(PAMPTConfig(variant="b3")).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        fused=device.type == "cuda",
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
            training_history.append(
                _train_epoch(
                    model,
                    optimizer,
                    stream,
                    train_ids,
                    labels,
                    device,
                    epoch_index=epoch_index,
                    amp_enabled=runtime["amp_enabled"],
                )
            )
    finally:
        stream.close()

    sampler, factory, simulation = _build_renderer(simulation_path)
    calibration_panel = _render_panel(
        material_ids=calibration_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=1,
    )
    audit_panel = _render_panel(
        material_ids=audit_ids,
        labels=labels,
        data_root=data_root,
        sampler=sampler,
        factory=factory,
        subset_offset=2,
    )
    calibration_features = _extract_features(
        model,
        calibration_panel,
        device,
        amp_enabled=runtime["amp_enabled"],
    )
    audit_features = _extract_features(
        model,
        audit_panel,
        device,
        amp_enabled=runtime["amp_enabled"],
    )

    family_classification: dict[str, Any] = {}
    for feature_name in (
        "raw_absolute_difference",
        "symmetric_residual",
        "signed_residual",
    ):
        family_classification[feature_name] = _classification_probe(
            calibration_features[feature_name],
            calibration_panel["family_labels"],
            audit_features[feature_name],
            audit_panel["family_labels"],
            classes=len(FAMILIES),
            permutations=permutations,
            seed=SEED + 103_000 + len(family_classification) * 1000,
            train_groups=calibration_panel["sample_groups"],
            test_groups=audit_panel["sample_groups"],
            group_constant_labels=False,
        )

    crystal_leakage = _classification_probe(
        calibration_features["symmetric_residual"],
        calibration_panel["crystal_labels"],
        audit_features["symmetric_residual"],
        audit_panel["crystal_labels"],
        classes=7,
        permutations=permutations,
        seed=SEED + 105_000,
        train_groups=calibration_panel["sample_groups"],
        test_groups=audit_panel["sample_groups"],
        group_constant_labels=True,
    )

    strength_regression = {
        "raw_absolute_difference": _family_regressions(
            calibration_features["raw_absolute_difference"],
            audit_features["raw_absolute_difference"],
            calibration_panel["family_labels"],
            audit_panel["family_labels"],
            calibration_panel["strength"],
            audit_panel["strength"],
            permutations=permutations,
            seed=SEED + 106_000,
        ),
        "signed_residual": _family_regressions(
            calibration_features["signed_residual"],
            audit_features["signed_residual"],
            calibration_panel["family_labels"],
            audit_panel["family_labels"],
            calibration_panel["strength"],
            audit_panel["strength"],
            permutations=permutations,
            seed=SEED + 107_000,
        ),
    }
    residual_strength_pass_count = sum(
        result["status"] == "signal_demonstrated"
        for result in strength_regression["signed_residual"].values()
    )
    decision = _gate_decision(
        raw_family_signal=(
            family_classification["raw_absolute_difference"]["status"]
            == "signal_demonstrated"
        ),
        residual_family_signal=(
            family_classification["signed_residual"]["status"]
            == "signal_demonstrated"
        ),
        strength_pass_count=residual_strength_pass_count,
        crystal_leakage_signal=(
            crystal_leakage["status"] == "signal_demonstrated"
        ),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "purpose": "Train-only non-performance gate for simulator-known measurement information in the current residual representation",
        "gate_decision": decision,
        "protocol": {
            "backbone": "PAMPT-B3",
            "backbone_state": "five-epoch Dynamic/Paired ERM rebuilt in memory",
            "train_epochs": TRAIN_EPOCHS,
            "families": list(FAMILIES),
            "pair_definition": "level0 anchor versus one controlled OOD perturbation family",
            "family_probe_residuals": "both absolute normalized V9 residual and signed normalized V10 residual; the Gate decision uses the signed residual",
            "strength_probe_residual": "signed normalized residual, matching the V10 perturbation-delta direction",
            "raw_identifiability_baseline": f"{RAW_POOL_BINS}-bin pooled absolute spectrum difference",
            "probe": "detached closed-form ridge linear probe",
            "ridge_alpha": RIDGE_ALPHA,
            "permutation_draws": permutations,
            "structures_per_crystal_system_per_subset": structures_per_crystal_system,
            "calibration_structures": len(calibration_ids),
            "audit_structures": len(audit_ids),
            "calibration_and_audit_structures_are_disjoint": True,
            "same_structures_are_rendered_under_all_families_within_each_subset": True,
        },
        "data_isolation": {
            "train_only": True,
            "validation_read": False,
            "simulated_test_read": False,
            "real_xrd_read": False,
            "checkpoint_written": False,
            "v9_parameter_selection": False,
            "formal_v10_training": False,
        },
        "inputs": {
            "data_root": str(data_root),
            "split_manifest": str(split_manifest),
            "split_manifest_sha256": file_hash(split_manifest).upper(),
            "simulation_config": str(simulation_path),
            "simulation_config_sha256": file_hash(simulation_path).upper(),
            "simulation_status": simulation.get("status"),
            "derived_gate_config_sha256": simulation.get(
                "derived_gate_config_sha256"
            ),
            "derived_profile_note": "ood_texture is reset to level0 for all non-texture operators; other OOD family profiles already isolate their target operator",
            "train_structure_count": len(train_ids),
            "train_class_counts": train_class_counts,
            "calibration_structure_ids_sha256": _canonical_hash(calibration_ids),
            "audit_structure_ids_sha256": _canonical_hash(audit_ids),
        },
        "runtime": runtime,
        "training_history": training_history,
        "panels": {
            "calibration": {
                "structures": len(calibration_ids),
                "paired_examples": len(calibration_panel["family_labels"]),
                "quality_retry_count": calibration_panel["quality_retry_count"],
                "runtime_seconds": calibration_panel["runtime_seconds"],
                "rows": calibration_panel["rows"],
            },
            "audit": {
                "structures": len(audit_ids),
                "paired_examples": len(audit_panel["family_labels"]),
                "quality_retry_count": audit_panel["quality_retry_count"],
                "runtime_seconds": audit_panel["runtime_seconds"],
                "rows": audit_panel["rows"],
            },
        },
        "measurement_family_classification": family_classification,
        "measurement_strength_regression": strength_regression,
        "crystal_system_leakage_probe": crystal_leakage,
        "interpretation_limits": [
            "Passing supports a V10 pilot; it does not prove disentanglement or final performance benefit.",
            "Failure at a five-epoch backbone state does not permanently falsify V10 and should be rechecked after formal V9 training if Residual remains scientifically relevant.",
            "The gate must not be used to change V9 lambdas, the backbone, the frozen OOD profiles, or the formal V9 comparison.",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--prefetch-batches", type=int, default=4)
    parser.add_argument(
        "--structures-per-crystal-system",
        type=int,
        default=DEFAULT_STRUCTURES_PER_CRYSTAL_SYSTEM,
    )
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT / "reports" / "v10_p0_measurement_information_gate.json"
        ),
    )
    args = parser.parse_args()
    report = run_gate(
        device_name=args.device,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
        structures_per_crystal_system=args.structures_per_crystal_system,
        permutations=args.permutations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(report["gate_decision"], indent=2, sort_keys=True))
    print(f"report={args.output}")
    print(f"sha256={file_hash(args.output).upper()}")


if __name__ == "__main__":
    main()
