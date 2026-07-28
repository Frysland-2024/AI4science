#!/usr/bin/env python3
"""Train-only matched short-trajectory diagnostic for V9 P0 methods.

This diagnostic extends the one-step counterfactual test to a small fixed number
of optimizer steps. ERM, JS, and Residual branches start from the same five-epoch
in-memory ERM state and identical main-optimizer state. They receive the same
balanced Train-only update batches and are evaluated on the same fixed Train-only
in-range and single-factor-OOD panels after every step.

The middle registered lambda values are used without selection. No Validation,
simulated Test, real XRD, formal checkpoint, or original P0 report is modified.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
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


ORIGINAL_REPORT = PROJECT_ROOT / "reports" / "v9_p0_local_benefit.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_p0_short_trajectory.json"
DEFAULT_STEPS = 5
DEFAULT_REPEATS = 6
BOOTSTRAP_DRAWS = 5000
METHODS = ("erm", "js", "residual")
CANDIDATES = ("js", "residual")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _summary(values: Sequence[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0:
        raise ValueError("cannot summarize an empty sequence")
    return {
        "count": int(array.size),
        "mean": float(array.mean()),
        "median": float(np.median(array)),
        "minimum": float(array.min()),
        "maximum": float(array.max()),
        "positive_sign_rate": float((array > 0).mean()),
    }


def _cluster_bootstrap(
    repeat_values: Mapping[int, float], *, draws: int, seed: int
) -> dict[str, float]:
    ordered = np.asarray(
        [repeat_values[key] for key in sorted(repeat_values)], dtype=np.float64
    )
    if ordered.size == 0:
        raise ValueError("cannot bootstrap empty repeat values")
    generator = np.random.default_rng(seed)
    indexes = generator.integers(0, ordered.size, size=(draws, ordered.size))
    means = ordered[indexes].mean(axis=1)
    return {
        "draws": int(draws),
        "repeat_count": int(ordered.size),
        "mean": float(ordered.mean()),
        "lower_95": float(np.quantile(means, 0.025)),
        "upper_95": float(np.quantile(means, 0.975)),
    }


def _new_residual_head(
    *,
    model: p0.PAMPT,
    probe_state: Mapping[str, Any],
    device: torch.device,
    fused: bool,
) -> tuple[p0.ResidualClassifier, torch.optim.Optimizer]:
    head = p0.ResidualClassifier(model.config.embed_dim, depth=1).to(device)
    head.load_state_dict(probe_state)
    optimizer = torch.optim.AdamW(
        head.parameters(),
        lr=p0.LEARNING_RATE,
        weight_decay=p0.WEIGHT_DECAY,
        fused=fused,
    )
    return head, optimizer


def _update_branch(
    *,
    method: str,
    model: p0.PAMPT,
    optimizer_main: torch.optim.Optimizer,
    residual_head: p0.ResidualClassifier | None,
    optimizer_residual: torch.optim.Optimizer | None,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    lambda_js: float,
    lambda_res: float,
) -> dict[str, float]:
    model.train()
    if method == "erm":
        optimizer_main.zero_grad(set_to_none=True)
        result = p0.dynamic_erm(model, x1, x2, target)
        result["total"].backward()
        optimizer_main.step()
        return {
            "classification": float(result["classification"].detach()),
            "auxiliary": 0.0,
            "total": float(result["total"].detach()),
        }
    if method == "js":
        optimizer_main.zero_grad(set_to_none=True)
        result = p0.dynamic_js(model, x1, x2, target, lambda_js=lambda_js)
        result["total"].backward()
        optimizer_main.step()
        return {
            "classification": float(result["classification"].detach()),
            "auxiliary": float(result["consistency"].detach()),
            "total": float(result["total"].detach()),
        }
    if method == "residual":
        if residual_head is None or optimizer_residual is None:
            raise RuntimeError("Residual branch requires a persistent residual head")
        result = p0.dynamic_residual(
            model,
            residual_head,
            x1,
            x2,
            target,
            optimizer_main=optimizer_main,
            optimizer_res=optimizer_residual,
            lambda_res=lambda_res,
        )
        return {
            "classification": float(result["classification"]),
            "probe": float(result["probe"]),
            "auxiliary": float(result["independence"]),
            "total": float(result["total"]),
        }
    raise ValueError(f"unknown method: {method}")


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_step: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_step[int(row["step"])].append(row)

    result: dict[str, Any] = {}
    for step, step_rows in sorted(by_step.items()):
        ood_rows = [
            row
            for row in step_rows
            if str(row["profile"]) in p0.SINGLE_FACTOR_OOD_PROFILES
        ]
        step_result: dict[str, Any] = {}
        for candidate_index, candidate in enumerate(CANDIDATES):
            benefits = [
                float(row["benefit_vs_erm"][candidate]["classification_ce"])
                for row in ood_rows
            ]
            grouped: dict[int, list[float]] = defaultdict(list)
            for row in ood_rows:
                grouped[int(row["repeat"])].append(
                    float(row["benefit_vs_erm"][candidate]["classification_ce"])
                )
            repeat_means = {
                repeat: float(np.mean(values)) for repeat, values in sorted(grouped.items())
            }
            mechanism = {
                "paired_js_difference_vs_erm": float(
                    np.mean(
                        [
                            row["branches"][candidate]["paired_js"]
                            - row["branches"]["erm"]["paired_js"]
                            for row in ood_rows
                        ]
                    )
                ),
                "probe_accuracy_difference_vs_erm": float(
                    np.mean(
                        [
                            row["branches"][candidate]["fixed_audit_probe_accuracy"]
                            - row["branches"]["erm"]["fixed_audit_probe_accuracy"]
                            for row in ood_rows
                        ]
                    )
                ),
                "probe_ce_difference_vs_erm": float(
                    np.mean(
                        [
                            row["branches"][candidate]["fixed_audit_probe_ce"]
                            - row["branches"]["erm"]["fixed_audit_probe_ce"]
                            for row in ood_rows
                        ]
                    )
                ),
            }
            step_result[candidate] = {
                "raw_profile_rows": _summary(benefits),
                "repeat_level_values": repeat_means,
                "repeat_clustered_bootstrap_95": _cluster_bootstrap(
                    repeat_means,
                    draws=BOOTSTRAP_DRAWS,
                    seed=p0.SEED + 120_000 + step * 100 + candidate_index,
                ),
                "mean_mechanism_differences_vs_erm": mechanism,
            }
        result[str(step)] = step_result
    return result


def run_trajectory(
    *,
    device_name: str = "cuda",
    steps: int = DEFAULT_STEPS,
    repeats: int = DEFAULT_REPEATS,
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
    split_manifest = data_root / "manifests" / "split_manifest.json"
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
    for repeat in range(repeats):
        eval_ids = p0._balanced_repeat_batch(
            local_pools["local_eval"],
            labels,
            repeat=repeat,
            stream_offset=190_000,
        )
        panels: dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = {}
        for panel_index, profile in enumerate(p0.EVALUATION_PROFILES, start=1):
            first, second = p0._render_profile(
                batch_ids=eval_ids,
                profile=profile,
                repeat=repeat + 10_000,
                panel_index=panel_index,
                peaks=peaks,
                sampler=sampler,
                factory=factory,
            )
            panels[profile] = (
                torch.from_numpy(np.ascontiguousarray(first)).float().to(device),
                torch.from_numpy(np.ascontiguousarray(second)).float().to(device),
                p0._labels_tensor(eval_ids, labels, device),
            )

        before = {
            profile: p0._panel_metrics(base_model, audit_probe, *panel)
            for profile, panel in panels.items()
        }

        branch_models: dict[str, p0.PAMPT] = {}
        branch_optimizers: dict[str, torch.optim.Optimizer] = {}
        for method in METHODS:
            model, optimizer = p0._new_branch(
                model_state=base_model_state,
                optimizer_state=base_optimizer_state,
                device=device,
                fused=fused,
            )
            branch_models[method] = model
            branch_optimizers[method] = optimizer
        residual_head, residual_optimizer = _new_residual_head(
            model=branch_models["residual"],
            probe_state=base_probe_state,
            device=device,
            fused=fused,
        )

        for step in range(1, steps + 1):
            stream_repeat = repeat * steps + (step - 1)
            update_ids = p0._balanced_repeat_batch(
                local_pools["local_update"],
                labels,
                repeat=stream_repeat,
                stream_offset=180_000,
            )
            first, second = p0._render_profile(
                batch_ids=update_ids,
                profile="train",
                repeat=stream_repeat + 20_000,
                panel_index=0,
                peaks=peaks,
                sampler=sampler,
                factory=factory,
            )
            x1 = torch.from_numpy(np.ascontiguousarray(first)).float().to(device)
            x2 = torch.from_numpy(np.ascontiguousarray(second)).float().to(device)
            target = p0._labels_tensor(update_ids, labels, device)

            losses = {}
            for method in METHODS:
                losses[method] = _update_branch(
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
                            for candidate in CANDIDATES
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

    aggregates = _aggregate(rows)
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
        for candidate in CANDIDATES
    }

    return {
        "schema_version": "v9-p0-short-trajectory-v1",
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
            "methods": list(METHODS),
            "lambda_js": lambda_js,
            "lambda_res": lambda_res,
            "registered_grids": registered_grids,
            "same_base_model_and_optimizer_state": True,
            "same_update_batches_per_step": True,
            "fixed_evaluation_panel_within_repeat": True,
            "evaluation_profiles": list(p0.EVALUATION_PROFILES),
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
        },
        "rows": rows,
        "runtime_seconds": time.perf_counter() - started,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
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
    original_hash_before = _sha256(original) if original.is_file() else None
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
    original_hash_after = _sha256(original) if original.is_file() else None
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
