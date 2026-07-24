#!/usr/bin/env python3
"""Quality-gate-resilient Train-only short-trajectory diagnostic for V9 P0.

This is a fail-closed replacement for ``audit_v9_p0_short_trajectory.py``.  It
keeps the same scientific protocol, but when a balanced Train-only batch cannot
produce a quality-valid dynamic view after the simulator's registered internal
retries, it deterministically draws another balanced batch from the same frozen
Train-only pool.  The rejected batch, failing profile, and error are recorded.

It never weakens or bypasses the quality gate, never reads Validation/Test/real
XRD, never selects lambda, never writes a checkpoint, and never overwrites the
original P0 report.
"""

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
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_v9_local_benefit as p0  # noqa: E402
import audit_v9_p0_short_trajectory as legacy  # noqa: E402


ORIGINAL_REPORT = PROJECT_ROOT / "reports" / "v9_p0_local_benefit.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_p0_short_trajectory.json"
MAX_BATCH_RESAMPLE_ATTEMPTS = 64
RESAMPLE_REPEAT_STRIDE = 1_000_003
QUALITY_GATE_MARKER = "quality gate exhausted deterministic resampling"


def _is_quality_gate_exhaustion(error: BaseException) -> bool:
    return QUALITY_GATE_MARKER in str(error).lower()


def _render_balanced_bundle_with_retry(
    *,
    pool: Sequence[str],
    labels: Mapping[str, int],
    profiles: Sequence[str],
    logical_repeat: int,
    stream_offset: int,
    render_repeat_base: int,
    panel_start: int,
    peaks: Mapping[str, Any],
    sampler: p0.PhysicsParameterSampler,
    factory: p0.OnlineViewFactory,
    phase: str,
    max_attempts: int = MAX_BATCH_RESAMPLE_ATTEMPTS,
) -> tuple[
    list[str],
    dict[str, tuple[np.ndarray, np.ndarray]],
    list[dict[str, Any]],
    int,
]:
    """Render one balanced bundle, replacing only whole rejected batches.

    All requested profiles use the same material IDs.  If any profile exhausts
    the registered quality gate, the entire candidate batch is discarded and a
    new seven-class-balanced batch is drawn deterministically.  Non-quality-gate
    exceptions propagate immediately.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if not profiles:
        raise ValueError("profiles must not be empty")

    rejections: list[dict[str, Any]] = []
    for attempt in range(max_attempts):
        candidate_repeat = logical_repeat + attempt * RESAMPLE_REPEAT_STRIDE
        batch_ids = p0._balanced_repeat_batch(
            pool,
            labels,
            repeat=candidate_repeat,
            stream_offset=stream_offset,
        )
        rendered: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        failing_profile = None
        try:
            for panel_index, profile in enumerate(profiles, start=panel_start):
                failing_profile = profile
                first, second = p0._render_profile(
                    batch_ids=batch_ids,
                    profile=profile,
                    repeat=render_repeat_base + attempt * RESAMPLE_REPEAT_STRIDE,
                    panel_index=panel_index,
                    peaks=peaks,
                    sampler=sampler,
                    factory=factory,
                )
                rendered[profile] = (first, second)
            return batch_ids, rendered, rejections, attempt
        except ValueError as error:
            if not _is_quality_gate_exhaustion(error):
                raise
            rejections.append(
                {
                    "phase": phase,
                    "logical_repeat": int(logical_repeat),
                    "attempt": int(attempt),
                    "candidate_repeat": int(candidate_repeat),
                    "failing_profile": str(failing_profile),
                    "material_ids": list(batch_ids),
                    "error": str(error),
                }
            )

    raise RuntimeError(
        f"{phase} could not find a quality-valid balanced batch after "
        f"{max_attempts} deterministic attempts"
    )


def run_trajectory(
    *,
    device_name: str = "cuda",
    steps: int = legacy.DEFAULT_STEPS,
    repeats: int = legacy.DEFAULT_REPEATS,
    worker_count: int = 4,
    prefetch_batches: int = 4,
) -> dict[str, Any]:
    if steps < 2 or steps > 10:
        raise ValueError("steps must be in [2, 10]")
    if repeats < 2 or repeats > 12:
        raise ValueError("repeats must be in [2, 12]")
    device = torch.device(device_name)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")

    runtime = p0._configure_runtime(device)
    p0._set_seed(p0.SEED, device)
    started = time.perf_counter()

    data_root = PROJECT_ROOT / "data" / "formal_14060"
    split_manifest = data_root / "manifests" / "split_manifest.v9t.family_v1.csv"
    simulation_path = PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"
    contract_path = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
    lambda_js, lambda_res, registered_grids = p0._registered_middle_lambdas(contract_path)

    train_ids, labels, train_class_counts = p0._read_train_rows(split_manifest)
    partitions = p0._balanced_partitions(train_ids, labels)
    local_pools = p0._split_local_pool(partitions["scale_audit"], labels)
    all_local_ids = sorted(set(local_pools["local_update"] + local_pools["local_eval"]))
    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    peaks = {
        material_id: p0.load_peak_table(cache_root / f"{material_id}.npz")
        for material_id in all_local_ids
    }

    fused = device.type == "cuda"
    base_model = p0.PAMPT(p0.PAMPTConfig(variant="b3")).to(device)
    base_optimizer = torch.optim.AdamW(
        base_model.parameters(),
        lr=p0.LEARNING_RATE,
        weight_decay=p0.WEIGHT_DECAY,
        fused=fused,
    )
    training_stream = p0._DynamicTrainStream(
        data_root=data_root,
        simulation_path=simulation_path,
        worker_count=worker_count,
        prefetch_batches=prefetch_batches,
    )
    training_history: list[dict[str, Any]] = []
    try:
        for epoch_index in range(p0.TRAIN_EPOCHS):
            epoch_report = p0._train_epoch(
                base_model,
                base_optimizer,
                training_stream,
                train_ids,
                labels,
                device,
                epoch_index=epoch_index,
                amp_enabled=runtime["amp_enabled"],
            )
            training_history.append(epoch_report)
            print(
                f"trajectory base epoch={epoch_index + 1} "
                f"ce={epoch_report['classification_ce']:.6f} "
                f"accuracy={epoch_report['classification_accuracy_across_two_views']:.4f}",
                flush=True,
            )

        calibration = p0._collect_residual_features(
            base_model,
            training_stream,
            partitions["probe_calibration"],
            labels,
            device,
            milestone=p0.TRAIN_EPOCHS,
            subset_offset=71,
            amp_enabled=runtime["amp_enabled"],
        )
        audit_features = p0._collect_residual_features(
            base_model,
            training_stream,
            partitions["probe_audit"],
            labels,
            device,
            milestone=p0.TRAIN_EPOCHS,
            subset_offset=72,
            amp_enabled=runtime["amp_enabled"],
        )
        audit_probe, probe_report = p0._fit_and_evaluate_probe(
            base_model,
            calibration,
            audit_features,
            device,
            milestone=p0.TRAIN_EPOCHS + 70,
        )
    finally:
        training_stream.close()

    if probe_report["status"] != "signal_demonstrated":
        raise RuntimeError("residual probe competence was not demonstrated")

    base_model_state = p0._clone_to_cpu(base_model.state_dict())
    base_optimizer_state = p0._clone_to_cpu(base_optimizer.state_dict())
    base_probe_state = p0._clone_to_cpu(audit_probe.state_dict())
    audit_probe.eval()
    for parameter in audit_probe.parameters():
        parameter.requires_grad_(False)

    sampler, factory, simulation = p0._build_renderer(simulation_path)
    if not set(p0.EVALUATION_PROFILES).issubset(set(simulation["profiles"])):
        raise RuntimeError("frozen simulation config lacks trajectory profiles")

    rows: list[dict[str, Any]] = []
    quality_gate_rejections: list[dict[str, Any]] = []
    successful_render_attempts: list[dict[str, Any]] = []

    for repeat in range(repeats):
        eval_ids, eval_numpy, rejected, eval_attempt = _render_balanced_bundle_with_retry(
            pool=local_pools["local_eval"],
            labels=labels,
            profiles=p0.EVALUATION_PROFILES,
            logical_repeat=repeat,
            stream_offset=190_000,
            render_repeat_base=repeat + 10_000,
            panel_start=1,
            peaks=peaks,
            sampler=sampler,
            factory=factory,
            phase=f"evaluation_repeat_{repeat}",
        )
        quality_gate_rejections.extend(rejected)
        successful_render_attempts.append(
            {"phase": "evaluation", "repeat": repeat, "attempt": eval_attempt}
        )
        panels = {
            profile: (
                torch.from_numpy(np.ascontiguousarray(first)).float().to(device),
                torch.from_numpy(np.ascontiguousarray(second)).float().to(device),
                p0._labels_tensor(eval_ids, labels, device),
            )
            for profile, (first, second) in eval_numpy.items()
        }
        before = {
            profile: p0._panel_metrics(base_model, audit_probe, *panel)
            for profile, panel in panels.items()
        }

        branch_models: dict[str, p0.PAMPT] = {}
        branch_optimizers: dict[str, torch.optim.Optimizer] = {}
        for method in legacy.METHODS:
            model, optimizer = p0._new_branch(
                model_state=base_model_state,
                optimizer_state=base_optimizer_state,
                device=device,
                fused=fused,
            )
            branch_models[method] = model
            branch_optimizers[method] = optimizer
        residual_head, residual_optimizer = legacy._new_residual_head(
            model=branch_models["residual"],
            probe_state=base_probe_state,
            device=device,
            fused=fused,
        )

        for step in range(1, steps + 1):
            stream_repeat = repeat * steps + (step - 1)
            update_ids, update_numpy, rejected, update_attempt = _render_balanced_bundle_with_retry(
                pool=local_pools["local_update"],
                labels=labels,
                profiles=("train",),
                logical_repeat=stream_repeat,
                stream_offset=180_000,
                render_repeat_base=stream_repeat + 20_000,
                panel_start=0,
                peaks=peaks,
                sampler=sampler,
                factory=factory,
                phase=f"update_repeat_{repeat}_step_{step}",
            )
            quality_gate_rejections.extend(rejected)
            successful_render_attempts.append(
                {
                    "phase": "update",
                    "repeat": repeat,
                    "step": step,
                    "attempt": update_attempt,
                }
            )
            first, second = update_numpy["train"]
            x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
            x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
            target = p0._labels_tensor(update_ids, labels, device)

            losses = {
                method: legacy._update_branch(
                    method=method,
                    model=branch_models[method],
                    optimizer_main=branch_optimizers[method],
                    residual_head=residual_head if method == "residual" else None,
                    optimizer_residual=residual_optimizer if method == "residual" else None,
                    x1=x1,
                    x2=x2,
                    target=target,
                    lambda_js=lambda_js,
                    lambda_res=lambda_res,
                )
                for method in legacy.METHODS
            }

            for profile, panel in panels.items():
                branch_metrics = {
                    method: p0._panel_metrics(model, audit_probe, *panel)
                    for method, model in branch_models.items()
                }
                rows.append(
                    {
                        "repeat": repeat,
                        "step": step,
                        "profile": profile,
                        "update_material_ids": update_ids,
                        "evaluation_material_ids": eval_ids,
                        "evaluation_render_attempt": eval_attempt,
                        "update_render_attempt": update_attempt,
                        "initial": before[profile],
                        "update_losses": losses,
                        "branches": branch_metrics,
                        "benefit_vs_erm": {
                            candidate: {
                                "classification_ce": float(
                                    branch_metrics["erm"]["classification_ce"]
                                    - branch_metrics[candidate]["classification_ce"]
                                )
                            }
                            for candidate in legacy.CANDIDATES
                        },
                    }
                )
            print(
                f"completed trajectory repeat={repeat + 1}/{repeats} step={step}/{steps}",
                flush=True,
            )

        del residual_optimizer, residual_head
        for optimizer in branch_optimizers.values():
            del optimizer
        for model in branch_models.values():
            del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    aggregates = legacy._aggregate(rows)
    final_step = aggregates[str(steps)]
    flags = {
        candidate: {
            "final_step_mean_ood_ce_benefit_positive": final_step[candidate][
                "repeat_clustered_bootstrap_95"
            ]["mean"]
            > 0,
            "final_step_clustered_lower_95_above_zero": final_step[candidate][
                "repeat_clustered_bootstrap_95"
            ]["lower_95"]
            > 0,
            "not_a_formal_performance_conclusion": True,
        }
        for candidate in legacy.CANDIDATES
    }

    return {
        "schema_version": "v9-p0-short-trajectory-v2-quality-gate-resilient",
        "status": "pass",
        "scope": "Train-only matched multi-step local diagnostic",
        "device": str(device),
        "runtime_configuration": {
            **runtime,
            "prefetch_workers": worker_count,
            "prefetch_batches": prefetch_batches,
            "fused_adamw": fused,
        },
        "protocol": {
            "steps": steps,
            "repeats": repeats,
            "methods": list(legacy.METHODS),
            "lambda_js": lambda_js,
            "lambda_res": lambda_res,
            "registered_grids": registered_grids,
            "same_base_model_and_optimizer_state": True,
            "same_update_batches_per_step": True,
            "fixed_evaluation_panel_within_repeat": True,
            "evaluation_profiles": list(p0.EVALUATION_PROFILES),
            "quality_gate_policy": "never bypass; reject whole batch and deterministically resample a new balanced Train-only batch",
            "max_batch_resample_attempts": MAX_BATCH_RESAMPLE_ATTEMPTS,
        },
        "quality_gate_batch_resampling": {
            "rejection_count": len(quality_gate_rejections),
            "rejections": quality_gate_rejections,
            "successful_attempts": successful_render_attempts,
        },
        "base_learned_state": {
            "epochs": p0.TRAIN_EPOCHS,
            "training_history": training_history,
            "residual_probe_gate": probe_report,
            "checkpoint_policy": "in_memory_only",
        },
        "train_only_partition_counts": {
            "full_train": len(train_ids),
            "train_class_counts": train_class_counts,
            "local_update_pool": len(local_pools["local_update"]),
            "local_eval_pool": len(local_pools["local_eval"]),
        },
        "aggregates_by_step": aggregates,
        "descriptive_flags": flags,
        "formal_boundaries": {
            "validation_used": False,
            "simulated_test_used": False,
            "real_xrd_used": False,
            "checkpoint_written": False,
            "lambda_selected": False,
            "formal_training_started": False,
            "formal_claim_allowed": False,
            "quality_gate_weakened_or_bypassed": False,
        },
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=legacy.DEFAULT_STEPS)
    parser.add_argument("--repeats", type=int, default=legacy.DEFAULT_REPEATS)
    parser.add_argument("--worker-count", type=int, default=4)
    parser.add_argument("--prefetch-batches", type=int, default=4)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    original = ORIGINAL_REPORT.resolve()
    if output == original:
        raise SystemExit("trajectory output must not overwrite the original P0 report")
    original_hash_before = legacy._sha256(original) if original.is_file() else None
    report = run_trajectory(
        device_name=args.device,
        steps=args.steps,
        repeats=args.repeats,
        worker_count=args.worker_count,
        prefetch_batches=args.prefetch_batches,
    )
    report["original_report"] = {
        "path": original.as_posix(),
        "sha256_before": original_hash_before,
        "immutable": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    original_hash_after = legacy._sha256(original) if original.is_file() else None
    if original_hash_before != original_hash_after:
        output.unlink(missing_ok=True)
        raise RuntimeError("original P0 report changed; trajectory output removed")
    report["original_report"]["sha256_after"] = original_hash_after
    report["original_report"]["unchanged"] = True
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Original preserved: {original}")
    print(f"Original SHA256: {original_hash_after}")
    print(f"Wrote: {output}")
    print(json.dumps(report["descriptive_flags"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
