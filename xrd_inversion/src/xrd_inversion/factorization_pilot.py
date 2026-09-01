"""Train-only Stage-1 structure/measurement factorization mechanism pilot.

The formal path is deliberately finite: a tiny overfit Gate, followed (only on
PASS) by one frozen 32-parent factorial manifest and two matched models over
three fixed seeds.  This module never invokes the Week-1 top-level pilot and
never imports the independent renderer.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .factorial_dataset import (
    CORNER_ORDER,
    FactorialTensorBundle,
    build_eval_manifest,
    build_factorial_manifest,
    load_factorial_bundle,
    load_train_parent_contexts,
    render_factorial_bundle,
    subset_indices,
    training_channel_statistics,
    validate_bundle_against_manifest,
    validate_factorial_manifest,
    write_json_atomic,
)
from .factorization_metrics import (
    compute_factorization_metrics,
    decide_factorization_gate,
    summarize_seed_metrics,
)
from .factorization_training import (
    TrainingRun,
    predict_blocks,
    save_training_checkpoint,
    train_two_head_model,
)
from .parameterization import compose_q, decode_q, resolve_reference_q
from .week1_pilot import load_json, sha256_file


INTERFACE_VERSION = "factorization-interface-v1"
CONDITIONS = ("baseline", "factorized")
PHYSICAL_KEYS = ("a_angstrom", "c_angstrom", "delta_2theta_deg", "fwhm_deg")
STANDARDIZED_KEYS = ("q_u", "q_v", "q_delta", "q_w")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_repository_path(repository_root: Path, value: str | Path) -> Path:
    root = repository_root.resolve()
    path = (root / Path(value)).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"configured path escapes the repository: {path}")
    return path


def _relative(repository_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repository_root.resolve()).as_posix()


def _load_or_write_exact_json(
    path: Path, payload: Mapping[str, Any], *, replace: bool = False
) -> None:
    if path.exists():
        existing = load_json(path)
        if existing != payload:
            if replace:
                write_json_atomic(path, payload)
                return
            raise FileExistsError(
                f"refusing to overwrite a non-identical frozen artefact: {path}"
            )
        return
    write_json_atomic(path, payload)


def _load_or_render_bundle(
    path: Path,
    manifest: Mapping[str, Any],
    contexts: Sequence[Any],
    config: Mapping[str, Any],
) -> FactorialTensorBundle:
    if path.exists():
        bundle = load_factorial_bundle(path)
        if bundle.manifest_sha256 != str(manifest["payload_sha256"]):
            raise FileExistsError(
                f"cached tensor bundle belongs to a different manifest: {path}"
            )
        validate_bundle_against_manifest(bundle, manifest)
        return bundle
    return render_factorial_bundle(manifest, contexts, config, path)


def _loss_reduction(initial: float, final: float) -> float:
    if not (math.isfinite(initial) and math.isfinite(final) and initial > 0.0):
        raise ValueError("tiny-overfit losses must be finite and initially positive")
    return float((initial - final) / initial)


def evaluate_tiny_overfit_gate(
    baseline: TrainingRun,
    factorized: TrainingRun,
    tiny_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the frozen engineering Gate before any formal Stage-1 training."""

    threshold_parameter = float(tiny_config["parameter_mse_max"])
    threshold_pair = float(tiny_config["paired_invariance_mse_max"])
    threshold_reduction = float(tiny_config["loss_reduction_fraction_min"])
    reductions = {
        "baseline_parameter": _loss_reduction(
            baseline.initial_losses["parameter"], baseline.final_losses["parameter"]
        ),
        "factorized_parameter": _loss_reduction(
            factorized.initial_losses["parameter"],
            factorized.final_losses["parameter"],
        ),
        "factorized_pair": _loss_reduction(
            factorized.initial_losses["pair"], factorized.final_losses["pair"]
        ),
    }
    checks = {
        "matched_initial_state": (
            baseline.initial_state_sha256 == factorized.initial_state_sha256
        ),
        "matched_batch_schedule": (
            baseline.batch_schedule_sha256 == factorized.batch_schedule_sha256
        ),
        "baseline_parameter_mse": (
            baseline.final_losses["parameter"] <= threshold_parameter
        ),
        "factorized_parameter_mse": (
            factorized.final_losses["parameter"] <= threshold_parameter
        ),
        "factorized_pair_mse": factorized.final_losses["pair"] <= threshold_pair,
        "baseline_parameter_reduction": (
            reductions["baseline_parameter"] >= threshold_reduction
        ),
        "factorized_parameter_reduction": (
            reductions["factorized_parameter"] >= threshold_reduction
        ),
        "factorized_pair_reduction": (
            reductions["factorized_pair"] >= threshold_reduction
        ),
    }
    finite_values = [
        *baseline.initial_losses.values(),
        *baseline.final_losses.values(),
        *factorized.initial_losses.values(),
        *factorized.final_losses.values(),
        *reductions.values(),
    ]
    checks["finite_no_nan_inf"] = all(
        math.isfinite(float(value)) for value in finite_values
    )
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "thresholds": {
            "parameter_mse_max": threshold_parameter,
            "paired_invariance_mse_max": threshold_pair,
            "loss_reduction_fraction_min": threshold_reduction,
        },
        "checks": checks,
        "loss_reduction_fraction": reductions,
        "baseline": {
            "initial_losses": baseline.initial_losses,
            "final_losses": baseline.final_losses,
            "initial_state_sha256": baseline.initial_state_sha256,
            "batch_schedule_sha256": baseline.batch_schedule_sha256,
        },
        "factorized": {
            "initial_losses": factorized.initial_losses,
            "final_losses": factorized.final_losses,
            "initial_state_sha256": factorized.initial_state_sha256,
            "batch_schedule_sha256": factorized.batch_schedule_sha256,
        },
    }


def _decode_physical(
    bundle: FactorialTensorBundle,
    indices: np.ndarray,
    theta_s: np.ndarray,
    theta_m: np.ndarray,
    parameter_config: Mapping[str, Any],
) -> np.ndarray:
    q = compose_q(theta_s, theta_m)
    if q.shape != (len(indices), 2, 2, 4):
        raise ValueError("decoded q input violates the block-first interface")
    output = np.empty_like(q, dtype=np.float64)
    for local_index, bundle_index in enumerate(indices):
        output[local_index] = decode_q(
            q[local_index],
            reference_a_angstrom=float(bundle.parent_a[bundle_index]),
            reference_c_angstrom=float(bundle.parent_c[bundle_index]),
            parameter_config=parameter_config,
        )
    if not np.isfinite(output).all():
        raise RuntimeError("physical decode produced NaN or Inf")
    return output


def _standardized_mae(
    pred_s: np.ndarray,
    pred_m: np.ndarray,
    true_s: np.ndarray,
    true_m: np.ndarray,
) -> dict[str, float]:
    error = np.abs(compose_q(pred_s, pred_m) - compose_q(true_s, true_m))
    return {
        name: float(error[..., index].mean())
        for index, name in enumerate(STANDARDIZED_KEYS)
    }


def _condition_metrics(
    bundle: FactorialTensorBundle,
    eval_indices: np.ndarray,
    pred_s: np.ndarray,
    pred_m: np.ndarray,
    parameter_config: Mapping[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray]:
    true_s = np.asarray(bundle.theta_s[eval_indices], dtype=np.float64)
    true_m = np.asarray(bundle.theta_m[eval_indices], dtype=np.float64)
    predicted_physical = _decode_physical(
        bundle, eval_indices, pred_s, pred_m, parameter_config
    )
    true_physical = _decode_physical(
        bundle, eval_indices, true_s, true_m, parameter_config
    )
    metrics = compute_factorization_metrics(
        pred_s,
        pred_m,
        true_s,
        true_m,
        predicted_physical=predicted_physical,
        true_physical=true_physical,
    )
    metrics["standardized_parameter_mae"] = _standardized_mae(
        pred_s, pred_m, true_s, true_m
    )
    return metrics, predicted_physical, true_physical


def _write_prediction_dump(
    path: Path,
    *,
    bundle: FactorialTensorBundle,
    indices: np.ndarray,
    pred_s: np.ndarray,
    pred_m: np.ndarray,
    predicted_physical: np.ndarray,
    true_physical: np.ndarray,
    metadata: Mapping[str, Any],
) -> None:
    expected = (len(indices), 2, 2, 2)
    if pred_s.shape != expected or pred_m.shape != expected:
        raise ValueError("prediction dump inputs violate the canonical block shape")
    true_s = np.asarray(bundle.theta_s[indices], dtype=np.float64)
    true_m = np.asarray(bundle.theta_m[indices], dtype=np.float64)
    required_metadata = {
        "interface_version",
        "interface_sha256",
        "config_sha256",
        "manifest_sha256",
        "source_sha256",
        "dataset_source_sha256",
        "reference_q",
        "profile_transform",
        "profile_view",
    }
    missing = sorted(required_metadata.difference(metadata))
    if missing:
        raise ValueError(f"prediction dump metadata is incomplete: {missing}")
    arrays: dict[str, Any] = {
        "schema_version": np.asarray("xrd-inversion-factorization-predictions-v1"),
        "pred_s": np.asarray(pred_s, dtype=np.float64),
        "pred_m": np.asarray(pred_m, dtype=np.float64),
        "true_s_grid": true_s,
        "true_m_grid": true_m,
        "theta_s": true_s[:, :, 0, :],
        "theta_m": true_m[:, 0, :, :],
        "true_s": true_s[:, :, 0, :],
        "true_m": true_m[:, 0, :, :],
        "predicted_physical": predicted_physical,
        "true_physical": true_physical,
        "parent_id": bundle.parent_id[indices],
        "parent_a_angstrom": bundle.parent_a[indices],
        "parent_c_angstrom": bundle.parent_c[indices],
        "block_id": bundle.block_id[indices],
        "subset": bundle.subset[indices],
        "corner_order": np.asarray(CORNER_ORDER),
        "structure_parameter_order": np.asarray(("q_u", "q_v")),
        "measurement_parameter_order": np.asarray(("q_delta", "q_w")),
        "physical_parameter_order": np.asarray(PHYSICAL_KEYS),
        "interface_version": np.asarray(str(metadata["interface_version"])),
        "interface_sha256": np.asarray(str(metadata["interface_sha256"])),
        "config_sha256": np.asarray(str(metadata["config_sha256"])),
        "manifest_sha256": np.asarray(str(metadata["manifest_sha256"])),
        "reference_q": np.asarray(metadata["reference_q"], dtype=np.float64),
        "profile_transform": np.asarray(str(metadata["profile_transform"])),
        "profile_view": np.asarray(str(metadata["profile_view"])),
        "metadata_json": np.asarray(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        ),
    }
    for structure_index, measurement_index, corner in (
        (0, 0, "x11"),
        (0, 1, "x12"),
        (1, 0, "x21"),
        (1, 1, "x22"),
    ):
        arrays[f"{corner}_pred_s"] = np.asarray(
            pred_s[:, structure_index, measurement_index], dtype=np.float64
        )
        arrays[f"{corner}_pred_m"] = np.asarray(
            pred_m[:, structure_index, measurement_index], dtype=np.float64
        )
        arrays[f"{corner}_true_s"] = true_s[
            :, structure_index, measurement_index
        ]
        arrays[f"{corner}_true_m"] = true_m[
            :, structure_index, measurement_index
        ]
    for name, value in arrays.items():
        array = np.asarray(value)
        if array.dtype.kind in "fci" and not np.isfinite(array).all():
            raise ValueError(f"prediction dump field {name} contains NaN or Inf")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(temporary, path)


def _mean_response_matrix(
    reports: Mapping[str, Mapping[str, Any]], key: str
) -> list[list[float]]:
    matrices = np.asarray(
        [report["response_matrix"][key] for report in reports.values()],
        dtype=np.float64,
    )
    if matrices.shape != (len(reports), 2, 2):
        raise ValueError("response matrices do not have shape [seed,2,2]")
    return matrices.mean(axis=0).tolist()


def _artifact_record(repository_root: Path, path: Path) -> dict[str, str]:
    return {
        "path": _relative(repository_root, path),
        "sha256": sha256_file(path),
    }


def _base_provenance(
    repository_root: Path,
    config_path: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    interface_path = repository_root / "xrd_inversion/contracts/factorization_interface_v1.md"
    source_paths = [
        repository_root / "xrd_inversion/src/xrd_inversion/gpu_forward.py",
        repository_root / "xrd_inversion/src/xrd_inversion/week1_pilot.py",
        repository_root / "xrd_inversion/src/xrd_inversion/factorial_dataset.py",
        repository_root / "xrd_inversion/src/xrd_inversion/parameterization.py",
        repository_root / "xrd_inversion/src/xrd_inversion/models.py",
        repository_root / "xrd_inversion/src/xrd_inversion/factorization_losses.py",
        repository_root / "xrd_inversion/src/xrd_inversion/factorization_metrics.py",
        repository_root / "xrd_inversion/src/xrd_inversion/factorization_training.py",
        repository_root / "xrd_inversion/src/xrd_inversion/factorization_pilot.py",
    ]
    return {
        "interface_version": INTERFACE_VERSION,
        "interface_sha256": sha256_file(interface_path),
        "config_sha256": sha256_file(config_path),
        "source_sha256": {
            _relative(repository_root, path): sha256_file(path) for path in source_paths
        },
        "corner_order": list(CORNER_ORDER),
        "structure_parameter_order": ["q_u", "q_v"],
        "measurement_parameter_order": ["q_delta", "q_w"],
        "reference_q": resolve_reference_q(
            config["parameterization"], config["factorial"]
        ).tolist(),
        "profile_transform": str(config["factorial"]["profile_transform"]),
        "profile_view": str(config["factorial"]["profile_view"]),
        "canonical_label_dtype": "float64",
        "training_dtype": str(config["runtime"]["training_dtype"]),
        "scope": "Train-only; internal held-out intervention blocks only",
    }


def _provenance(
    repository_root: Path,
    config_path: Path,
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        **_base_provenance(repository_root, config_path, config),
        "manifest_sha256": str(manifest["payload_sha256"]),
        "manifest_hash_kind": "canonical_json_payload_excluding_self_hash_field",
        "dataset_source_sha256": dict(
            manifest["source_provenance"]["source_sha256"]
        ),
    }


def _assert_formal_outputs_absent(
    repository_root: Path, config: Mapping[str, Any]
) -> None:
    outputs = config["outputs"]
    checkpoint_root = _resolve_repository_path(repository_root, outputs["checkpoint_dir"])
    prediction_root = _resolve_repository_path(repository_root, outputs["prediction_dir"])
    expected = [
        checkpoint_root / "checkpoint_baseline.pt",
        checkpoint_root / "checkpoint_factorized.pt",
        prediction_root / "prediction_dump_baseline.npz",
        prediction_root / "prediction_dump_factorized.npz",
        _resolve_repository_path(repository_root, outputs["results"]),
        _resolve_repository_path(repository_root, outputs["figure_data"]),
        _resolve_repository_path(repository_root, outputs["report"]),
    ]
    for seed in config["training_seeds"]:
        for condition in CONDITIONS:
            expected.extend(
                (
                    checkpoint_root
                    / f"seed_{int(seed)}"
                    / f"checkpoint_{condition}.pt",
                    prediction_root
                    / f"seed_{int(seed)}"
                    / f"prediction_dump_{condition}.npz",
                )
            )
    collisions = [path for path in expected if path.exists()]
    if collisions:
        rendered = "\n".join(str(path) for path in collisions)
        raise FileExistsError(f"refusing to overwrite formal artefacts:\n{rendered}")


def _run_tiny_gate(
    repository_root: Path,
    config: Mapping[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    tiny = config["tiny_overfit"]
    run_dir = _resolve_repository_path(repository_root, config["outputs"]["tiny_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    print("Phase 3: selecting two Train parents and rendering 16 tiny spectra", flush=True)
    contexts, selected, source_provenance = load_train_parent_contexts(
        repository_root, config, parent_count=int(tiny["parent_count"])
    )
    manifest = build_factorial_manifest(
        contexts,
        selected,
        source_provenance,
        config,
        blocks_per_parent=int(tiny["blocks_per_parent"]),
        training_blocks_per_parent=int(tiny["training_blocks_per_parent"]),
        purpose="tiny_overfit_engineering_gate",
        artifact_provenance=_base_provenance(repository_root, config_path, config),
    )
    manifest_tag = str(manifest["payload_sha256"])[:16]
    manifest_path = run_dir / f"tiny_factorial_manifest_{manifest_tag}.json"
    _load_or_write_exact_json(manifest_path, manifest)
    bundle_path = run_dir / f"tiny_factorial_profiles_{manifest_tag}.npz"
    bundle = _load_or_render_bundle(
        bundle_path, manifest, contexts, config
    )
    train_indices = subset_indices(bundle, "training")
    mean, std = training_channel_statistics(bundle, train_indices)
    override = {
        "steps": int(tiny["steps"]),
        "batch_size_blocks": int(tiny["batch_size_blocks"]),
        "learning_rate": float(tiny["learning_rate"]),
        "weight_decay": float(tiny["weight_decay"]),
        "log_interval_steps": max(int(tiny["steps"]) // 12, 1),
    }
    seed = int(config["primary_handoff_seed"])
    print("Phase 4: tiny baseline overfit", flush=True)
    baseline = train_two_head_model(
        bundle,
        train_indices,
        mean,
        std,
        config,
        seed=seed,
        lambda_pair=float(config["training"]["lambda_pair_baseline"]),
        training_override=override,
    )
    baseline.model.to("cpu")
    torch.cuda.empty_cache()
    print("Phase 4: tiny paired-factorization overfit", flush=True)
    factorized = train_two_head_model(
        bundle,
        train_indices,
        mean,
        std,
        config,
        seed=seed,
        lambda_pair=float(config["training"]["lambda_pair_factorized"]),
        training_override=override,
    )
    factorized.model.to("cpu")
    torch.cuda.empty_cache()
    gate = evaluate_tiny_overfit_gate(baseline, factorized, tiny)
    manifest_record = _artifact_record(repository_root, manifest_path)
    profile_record = _artifact_record(repository_root, bundle_path)
    gate.update(
        {
            "completed_utc": _timestamp(),
            "config_sha256": sha256_file(config_path),
            "manifest_payload_sha256": manifest["payload_sha256"],
            "manifest_payload_hash_definition": (
                "SHA-256 of canonical JSON excluding the payload_sha256 self-hash field"
            ),
            "manifest_path": _relative(repository_root, manifest_path),
            "profile_bundle_path": _relative(repository_root, bundle_path),
            "artifacts": {
                "tiny_factorial_manifest": manifest_record,
                "tiny_factorial_profiles": profile_record,
            },
            "counts": manifest["counts"],
            "channel_mean": mean.tolist(),
            "channel_std": std.tolist(),
            "execution_boundary": dict(config["execution_boundary"]),
            "artifact_provenance": _base_provenance(
                repository_root, config_path, config
            ),
        }
    )
    write_json_atomic(run_dir / "tiny_overfit_results.json", gate)
    print(f"Phase 4 tiny-overfit Gate: {gate['status']}", flush=True)
    return gate


def _validated_config(config_path: Path) -> dict[str, Any]:
    config = load_json(config_path)
    if config.get("schema_version") != "xrd-inversion-factorization-pilot-v1":
        raise ValueError("unsupported factorization pilot config schema")
    if any(bool(value) for value in config["execution_boundary"].values()):
        raise ValueError("Stage-1 execution boundary must disable every expansion")
    if config["factorial"]["split"] != "train":
        raise ValueError("Stage-1 is frozen to Train")
    gate = config["gate"]
    required_improved = int(gate["minimum_leakage_improved_seed_count"])
    seed_count = int(gate["seed_count"])
    if not 1 <= required_improved <= seed_count:
        raise ValueError(
            "minimum_leakage_improved_seed_count must be between 1 and seed_count"
        )
    if len(config["training_seeds"]) != seed_count:
        raise ValueError("training_seeds length must equal gate.seed_count")
    resolve_reference_q(config["parameterization"], config["factorial"])
    return config


def run_tiny_overfit_only(
    repository_root: Path, config_path: Path
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    config_path = config_path.resolve()
    config = _validated_config(config_path)
    return _run_tiny_gate(repository_root, config, config_path)


def _load_passing_tiny_result(
    repository_root: Path,
    config_path: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    run_dir = _resolve_repository_path(repository_root, config["outputs"]["tiny_run_dir"])
    result_path = run_dir / "tiny_overfit_results.json"
    if not result_path.exists():
        raise FileNotFoundError("no tiny-overfit result is available to resume")
    result = load_json(result_path)
    if result.get("status") != "PASS":
        raise RuntimeError("the saved tiny-overfit result is not PASS")
    if result.get("config_sha256") != sha256_file(config_path):
        raise RuntimeError("the saved tiny-overfit result uses a different config")
    expected_provenance = _base_provenance(repository_root, config_path, config)
    if result.get("artifact_provenance") != expected_provenance:
        raise RuntimeError("code or interface changed after the tiny-overfit PASS")
    manifest_path = _resolve_repository_path(
        repository_root, str(result.get("manifest_path", ""))
    )
    if not manifest_path.is_relative_to(run_dir.resolve()):
        raise RuntimeError("saved tiny manifest path escapes its run directory")
    tiny_manifest = load_json(manifest_path)
    validate_factorial_manifest(tiny_manifest)
    if tiny_manifest["payload_sha256"] != result.get("manifest_payload_sha256"):
        raise RuntimeError("saved tiny result and manifest disagree")
    if result.get("manifest_payload_hash_definition") != (
        "SHA-256 of canonical JSON excluding the payload_sha256 self-hash field"
    ):
        raise RuntimeError("saved tiny result has an unknown payload-hash definition")
    profile_path = _resolve_repository_path(
        repository_root, str(result.get("profile_bundle_path", ""))
    )
    if not profile_path.is_relative_to(run_dir.resolve()):
        raise RuntimeError("saved tiny profile path escapes its run directory")
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise RuntimeError("saved tiny result has no artifact inventory")
    expected_records = {
        "tiny_factorial_manifest": (manifest_path, result.get("manifest_path")),
        "tiny_factorial_profiles": (profile_path, result.get("profile_bundle_path")),
    }
    for name, (path, expected_relative) in expected_records.items():
        record = artifacts.get(name)
        if not isinstance(record, Mapping):
            raise RuntimeError(f"saved tiny result is missing artifact record: {name}")
        if record.get("path") != expected_relative:
            raise RuntimeError(f"saved tiny artifact path mismatch: {name}")
        if not path.is_file() or record.get("sha256") != sha256_file(path):
            raise RuntimeError(f"saved tiny artifact file hash mismatch: {name}")
    tiny_bundle = load_factorial_bundle(profile_path)
    if tiny_bundle.manifest_sha256 != tiny_manifest["payload_sha256"]:
        raise RuntimeError("saved tiny profile belongs to a different manifest")
    validate_bundle_against_manifest(tiny_bundle, tiny_manifest)
    return result


def _run_one_condition(
    *,
    repository_root: Path,
    config: Mapping[str, Any],
    provenance: Mapping[str, Any],
    bundle: FactorialTensorBundle,
    train_indices: np.ndarray,
    eval_indices: np.ndarray,
    channel_mean: np.ndarray,
    channel_std: np.ndarray,
    seed: int,
    condition: str,
    checkpoint_path: Path,
    prediction_path: Path,
) -> tuple[TrainingRun, dict[str, Any]]:
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    lambda_pair = float(
        config["training"][
            "lambda_pair_baseline" if condition == "baseline" else "lambda_pair_factorized"
        ]
    )
    print(f"seed {seed}: train {condition} (lambda_pair={lambda_pair:g})", flush=True)
    started = time.perf_counter()
    run = train_two_head_model(
        bundle,
        train_indices,
        channel_mean,
        channel_std,
        config,
        seed=seed,
        lambda_pair=lambda_pair,
    )
    pred_s, pred_m = predict_blocks(
        run.model,
        bundle,
        eval_indices,
        channel_mean,
        channel_std,
        batch_size_blocks=int(config["training"]["batch_size_blocks"]),
    )
    metrics, predicted_physical, true_physical = _condition_metrics(
        bundle,
        eval_indices,
        pred_s,
        pred_m,
        config["parameterization"],
    )
    metrics["training_final_losses"] = dict(run.final_losses)
    metrics["elapsed_seconds"] = float(time.perf_counter() - started)
    dump_metadata = {
        **dict(provenance),
        "condition": condition,
        "seed": int(seed),
        "lambda_pair": lambda_pair,
        "evaluation_scope": "Train-parent internal unseen interventions",
    }
    _write_prediction_dump(
        prediction_path,
        bundle=bundle,
        indices=eval_indices,
        pred_s=pred_s,
        pred_m=pred_m,
        predicted_physical=predicted_physical,
        true_physical=true_physical,
        metadata=dump_metadata,
    )
    save_training_checkpoint(
        checkpoint_path,
        run,
        config,
        manifest_sha256=bundle.manifest_sha256,
        condition=condition,
        metrics=metrics,
        provenance=provenance,
    )
    return run, metrics


def _build_figure_data(
    baseline_by_seed: Mapping[str, Mapping[str, Any]],
    factorized_by_seed: Mapping[str, Mapping[str, Any]],
    summary: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "xrd-inversion-factorization-figure-data-v1",
        "provenance": dict(provenance),
        "seeds": list(summary["seeds"]),
        "leakage": {
            condition: {
                "measurement_to_structure": [
                    reports[seed]["leakage"]["measurement_to_structure"]
                    for seed in summary["seeds"]
                ],
                "structure_to_measurement": [
                    reports[seed]["leakage"]["structure_to_measurement"]
                    for seed in summary["seeds"]
                ],
            }
            for condition, reports in (
                ("baseline", baseline_by_seed),
                ("factorized", factorized_by_seed),
            )
        },
        "physical_parameter_mae": {
            condition: {
                key: [reports[seed]["parameter_mae"][key] for seed in summary["seeds"]]
                for key in PHYSICAL_KEYS
            }
            for condition, reports in (
                ("baseline", baseline_by_seed),
                ("factorized", factorized_by_seed),
            )
        },
        "own_factor_response": {
            condition: {
                factor: [
                    reports[seed]["own_factor_response"][factor]
                    for seed in summary["seeds"]
                ]
                for factor in ("structure", "measurement")
            }
            for condition, reports in (
                ("baseline", baseline_by_seed),
                ("factorized", factorized_by_seed),
            )
        },
        "response_matrix_mean": {
            condition: {
                "raw_mean_l2": _mean_response_matrix(reports, "raw_mean_l2"),
                "normalized": _mean_response_matrix(
                    reports, "normalized_by_true_own_factor_response"
                ),
            }
            for condition, reports in (
                ("baseline", baseline_by_seed),
                ("factorized", factorized_by_seed),
            )
        },
    }


def _gate_seed_consistency_audit(
    summary: Mapping[str, Any], gate_config: Mapping[str, Any]
) -> dict[str, Any]:
    seeds = list(summary["seeds"])
    response_limit = float(
        gate_config["own_response_error_relative_degradation_max"]
    )
    mae_limit = float(
        gate_config["physical_parameter_mae_relative_degradation_max"]
    )

    def safeguard(name: str, limit: float) -> dict[str, Any]:
        baseline = np.asarray(summary["baseline"][name]["values"], dtype=np.float64)
        factorized = np.asarray(summary["factorized"][name]["values"], dtype=np.float64)
        passed = factorized <= baseline * (1.0 + limit)
        return {
            "pass_by_seed": {
                seed: bool(value) for seed, value in zip(seeds, passed, strict=True)
            },
            "pass_seed_count": int(passed.sum()),
            "allowed_relative_degradation": limit,
        }

    leakage_names = (
        "leakage_measurement_to_structure",
        "leakage_structure_to_measurement",
    )
    response_names = ("response_error_structure", "response_error_measurement")
    mae_names = tuple(f"mae_{name}" for name in PHYSICAL_KEYS)
    return {
        "rule": (
            "leakage improvement requires the configured seed count; own-response "
            "and physical-MAE Gates use matched-seed means, with per-seed safeguard "
            "counts reported as diagnostics"
        ),
        "leakage_required_improved_seed_count": int(
            gate_config["minimum_leakage_improved_seed_count"]
        ),
        "leakage_improved_seed_count": {
            name: int(summary["comparison"][name]["improved_seed_count"])
            for name in leakage_names
        },
        "own_factor_response_safeguard": {
            name: safeguard(name, response_limit) for name in response_names
        },
        "parameter_mae_safeguard": {
            name: safeguard(name, mae_limit) for name in mae_names
        },
    }


def _format_value(value: float) -> str:
    magnitude = abs(float(value))
    return f"{value:.3e}" if magnitude != 0.0 and magnitude < 1e-3 else f"{value:.6f}"


def _markdown_report(results: Mapping[str, Any]) -> str:
    summary = results["summary"]
    gate = results["gate"]
    seeds = summary["seeds"]
    lines = [
        "# Structure–Measurement Factorization Pilot",
        "",
        f"**Decision: {gate['decision']}**",
        "",
        "This is a finite mechanism test on authoritative Train parents only. "
        "The four held-out blocks per parent are internal unseen-intervention "
        "sanity evaluation, not Validation/Test evidence or a formal "
        "generalization result.",
        "",
        "## Frozen scope and matched comparison",
        "",
        f"- Parents: {results['dataset']['parents']} conventional tetragonal Train parents",
        f"- Blocks/spectra: {results['dataset']['blocks']} / {results['dataset']['spectra']}",
        f"- Training/internal-eval blocks: {results['dataset']['training_blocks']} / {results['dataset']['evaluation_blocks']}",
        f"- Seeds: {', '.join(seeds)}",
        "- Interface status: v1 frozen after the successful tiny-overfit Gate.",
        "- Channels: `[x_obs, x_ref, x_obs-x_ref]`; structure order: `[q_u,q_v]`; measurement order: `[q_delta,q_w]`.",
        "- Manifest labels, handoff truth, decoded truth, and metrics are canonical float64; model training casts labels to float32.",
        "- Same data, initialization policy, optimizer, steps, and batch schedule; "
        "the only condition difference is `lambda_pair=0` versus `lambda_pair=1`.",
        "",
        "## Tiny-overfit engineering Gate",
        "",
        f"Status: **{results['tiny_overfit']['status']}**. All pairing, finite-value, "
        "matched-initialization/schedule, supervised-overfit, and paired-loss "
        "checks passed before the formal manifest was generated.",
        "",
        "## Three-seed aggregate metrics",
        "",
        "| Metric | Baseline mean ± sample SD | Paired mean ± sample SD | Relative reduction | Improved seeds |",
        "|---|---:|---:|---:|---:|",
    ]
    display_metrics = (
        ("E_s<-m", "leakage_measurement_to_structure"),
        ("E_m<-s", "leakage_structure_to_measurement"),
        ("Structure response error", "response_error_structure"),
        ("Measurement response error", "response_error_measurement"),
        ("a MAE (Å)", "mae_a_angstrom"),
        ("c MAE (Å)", "mae_c_angstrom"),
        ("delta MAE (deg 2theta)", "mae_delta_2theta_deg"),
        ("FWHM MAE (deg)", "mae_fwhm_deg"),
    )
    for label, key in display_metrics:
        baseline = summary["baseline"][key]
        paired = summary["factorized"][key]
        comparison = summary["comparison"][key]
        reduction = comparison["relative_reduction_of_means"]
        reduction_text = "undefined" if reduction is None else f"{100.0 * reduction:.2f}%"
        lines.append(
            f"| {label} | {_format_value(baseline['mean'])} ± {_format_value(baseline['sample_std'])} "
            f"| {_format_value(paired['mean'])} ± {_format_value(paired['sample_std'])} "
            f"| {reduction_text} | {comparison['improved_seed_count']}/{len(seeds)} |"
        )
    lines.extend(
        [
            "",
            "`Improved seeds` counts strictly lower paired values. The pre-registered 2/3 direction-consistency requirement applies to leakage improvements; own-response and physical-MAE checks are matched-seed mean degradation safeguards. Per-seed safeguard pass counts are serialized in `gate.seed_consistency_audit`.",
            "",
            "## Per-seed leakage and own-factor response",
            "",
            "| Seed | Model | E_s<-m | E_m<-s | Structure response error | Measurement response error |",
            "|---:|---|---:|---:|---:|---:|",
        ]
    )
    for seed in seeds:
        for condition in CONDITIONS:
            metrics = results["seed_results"][seed][condition]["metrics"]
            lines.append(
                f"| {seed} | {condition} | "
                f"{_format_value(metrics['leakage']['measurement_to_structure'])} | "
                f"{_format_value(metrics['leakage']['structure_to_measurement'])} | "
                f"{_format_value(metrics['own_factor_response']['structure']['mean_l2_error'])} | "
                f"{_format_value(metrics['own_factor_response']['measurement']['mean_l2_error'])} |"
            )
    lines.extend(["", "## Mean 2×2 intervention response matrices", ""])
    for condition in CONDITIONS:
        matrix = results["figure_data"]["response_matrix_mean"][condition]
        lines.extend(
            [
                f"### {condition.capitalize()}",
                "",
                "Rows are true interventions `[structure, measurement]`; columns are predicted heads `[structure, measurement]`.",
                "",
                "Raw mean L2 response:",
                "",
                "| Intervention \\ head | Structure | Measurement |",
                "|---|---:|---:|",
                f"| Structure | {_format_value(matrix['raw_mean_l2'][0][0])} | {_format_value(matrix['raw_mean_l2'][0][1])} |",
                f"| Measurement | {_format_value(matrix['raw_mean_l2'][1][0])} | {_format_value(matrix['raw_mean_l2'][1][1])} |",
                "",
                "Normalized by the corresponding true own-factor response:",
                "",
                "| Intervention \\ head | Structure | Measurement |",
                "|---|---:|---:|",
                f"| Structure | {_format_value(matrix['normalized'][0][0])} | {_format_value(matrix['normalized'][0][1])} |",
                f"| Measurement | {_format_value(matrix['normalized'][1][0])} | {_format_value(matrix['normalized'][1][1])} |",
                "",
            ]
        )
    lines.extend(
        [
            "## Gate interpretation",
            "",
            f"Decision: **{gate['decision']}**.",
            "",
            "Passed checks: "
            + ", ".join(
                key
                for group in gate["checks"].values()
                for key, passed in group.items()
                if passed
            )
            + ".",
            "",
            "Failed checks: "
            + (", ".join(gate["failed_checks"]) if gate["failed_checks"] else "none")
            + ".",
            "",
            "No lambda search, backbone search, forward reconstruction loss, real spectra, "
            "refinement, or new rescue loss was used.",
            "",
            "## Boundary audit",
            "",
            "The formal dataset, training, predictions, metrics, and Gate used Train only and "
            "did not read Validation, Test, or independent-renderer outcomes. During implementation "
            "QA, one broad read-only search echoed frozen independent-renderer config metadata, and "
            "a delegated agent mistakenly ran `pytest -q xrd_inversion/tests`, which executed "
            "`test_independent_renderer.py`. Neither event supplied data or metrics to this Pilot; "
            "the broad test result is excluded from Stage-1 evidence and produced no formal artefact.",
            "",
            "## Provenance",
            "",
            f"- Interface: `{results['provenance']['interface_version']}` (`sha256={results['provenance']['interface_sha256']}`)",
            f"- Config SHA-256: `{results['provenance']['config_sha256']}`",
            f"- Factorial manifest canonical payload SHA-256 (self-hash field excluded): `{results['dataset']['manifest_payload_sha256']}`",
            f"- Eval manifest canonical payload SHA-256 (self-hash field excluded): `{results['dataset']['eval_manifest_payload_sha256']}`",
            f"- Reference q: `{results['provenance']['reference_q']}`",
            f"- Profile view/transform: `{results['provenance']['profile_view']}` / `{results['provenance']['profile_transform']}`",
            "- Source closure:",
            *[
                f"  - `{path}`: `{digest}`"
                for path, digest in results["provenance"]["source_sha256"].items()
            ],
            "",
            "## Handoff artefacts",
            "",
        ]
    )
    for name, record in results["artifacts"].items():
        lines.append(f"- `{name}`: `{record['path']}` (`sha256={record['sha256']}`)")
    lines.extend(
        [
            "",
            "The canonical handoff checkpoint and prediction dump use the primary fixed seed. "
            "All per-seed artefacts remain available in seed-specific subdirectories.",
            "",
            "Reporting outputs:",
            "",
            f"- Results JSON: `{results['reporting_outputs']['results']}`",
            f"- Figure-data JSON: `{results['reporting_outputs']['figure_data']}`",
            f"- This report: `{results['reporting_outputs']['report']}`",
            f"- Per-seed checkpoints: `{results['reporting_outputs']['per_seed_checkpoint_pattern']}`",
            f"- Per-seed prediction dumps: `{results['reporting_outputs']['per_seed_prediction_pattern']}`",
            (
                f"- Tiny manifest: `{results['reporting_outputs']['tiny_manifest']}` "
                f"(canonical payload sha256={results['tiny_overfit']['manifest_payload_sha256']}; "
                f"file sha256={results['tiny_overfit']['artifacts']['tiny_factorial_manifest']['sha256']})"
            ),
            (
                f"- Tiny profile bundle: `{results['reporting_outputs']['tiny_profile_bundle']}` "
                f"(file sha256={results['tiny_overfit']['artifacts']['tiny_factorial_profiles']['sha256']})"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_factorization_pilot(
    repository_root: Path,
    config_path: Path,
    *,
    reuse_passing_tiny: bool = False,
    replace_current_run_artifacts: bool = False,
) -> dict[str, Any]:
    repository_root = repository_root.resolve()
    config_path = config_path.resolve()
    config = _validated_config(config_path)

    print("Phase 1-2 checks complete; entering tiny engineering Gate", flush=True)
    tiny_gate = (
        _load_passing_tiny_result(repository_root, config_path, config)
        if reuse_passing_tiny
        else _run_tiny_gate(repository_root, config, config_path)
    )
    if tiny_gate["status"] != "PASS":
        return {
            "status": "STOPPED_TINY_OVERFIT_FAIL",
            "tiny_overfit": tiny_gate,
            "continuation_allowed": False,
        }

    if not replace_current_run_artifacts:
        _assert_formal_outputs_absent(repository_root, config)
    outputs = config["outputs"]
    print("Phase 5: selecting 32 Train parents and freezing the 2048-spectrum manifest", flush=True)
    contexts, selected, source_provenance = load_train_parent_contexts(
        repository_root,
        config,
        parent_count=int(config["factorial"]["parent_count"]),
    )
    manifest = build_factorial_manifest(
        contexts,
        selected,
        source_provenance,
        config,
        purpose="formal_factorization_pilot",
        artifact_provenance=_base_provenance(repository_root, config_path, config),
    )
    expected_counts = {
        "parents": 32,
        "blocks_per_parent": 16,
        "training_blocks_per_parent": 12,
        "evaluation_blocks_per_parent": 4,
        "blocks": 512,
        "spectra": 2048,
    }
    if {key: int(manifest["counts"][key]) for key in expected_counts} != expected_counts:
        raise RuntimeError("formal factorial manifest does not contain 32x16x4 spectra")
    manifest_path = _resolve_repository_path(repository_root, outputs["manifest"])
    eval_manifest_path = _resolve_repository_path(repository_root, outputs["eval_manifest"])
    _load_or_write_exact_json(
        manifest_path, manifest, replace=replace_current_run_artifacts
    )
    eval_manifest = build_eval_manifest(manifest)
    _load_or_write_exact_json(
        eval_manifest_path, eval_manifest, replace=replace_current_run_artifacts
    )
    validate_factorial_manifest(manifest)

    full_run_dir = _resolve_repository_path(repository_root, outputs["full_run_dir"])
    full_run_dir.mkdir(parents=True, exist_ok=True)
    bundle = _load_or_render_bundle(
        full_run_dir
        / f"factorial_profiles_{str(manifest['payload_sha256'])[:16]}.npz",
        manifest,
        contexts,
        config,
    )
    train_indices = subset_indices(bundle, "training")
    eval_indices = subset_indices(bundle, "sanity_eval")
    if (len(train_indices), len(eval_indices)) != (384, 128):
        raise RuntimeError("formal bundle does not preserve the 12/4 block split")
    channel_mean, channel_std = training_channel_statistics(bundle, train_indices)
    provenance = _provenance(repository_root, config_path, config, manifest)

    checkpoint_root = _resolve_repository_path(repository_root, outputs["checkpoint_dir"])
    prediction_root = _resolve_repository_path(repository_root, outputs["prediction_dir"])
    baseline_by_seed: dict[str, dict[str, Any]] = {}
    factorized_by_seed: dict[str, dict[str, Any]] = {}
    seed_results: dict[str, dict[str, Any]] = {}
    primary_seed = int(config["primary_handoff_seed"])
    primary_paths: dict[str, tuple[Path, Path]] = {}
    for seed_value in config["training_seeds"]:
        seed = int(seed_value)
        seed_key = str(seed)
        seed_results[seed_key] = {}
        runs: dict[str, TrainingRun] = {}
        for condition in CONDITIONS:
            checkpoint_path = (
                checkpoint_root / f"seed_{seed}" / f"checkpoint_{condition}.pt"
            )
            prediction_path = (
                prediction_root
                / f"seed_{seed}"
                / f"prediction_dump_{condition}.npz"
            )
            run, metrics = _run_one_condition(
                repository_root=repository_root,
                config=config,
                provenance=provenance,
                bundle=bundle,
                train_indices=train_indices,
                eval_indices=eval_indices,
                channel_mean=channel_mean,
                channel_std=channel_std,
                seed=seed,
                condition=condition,
                checkpoint_path=checkpoint_path,
                prediction_path=prediction_path,
            )
            runs[condition] = run
            seed_results[seed_key][condition] = {
                "metrics": metrics,
                "initial_state_sha256": run.initial_state_sha256,
                "batch_schedule_sha256": run.batch_schedule_sha256,
                "checkpoint": _artifact_record(repository_root, checkpoint_path),
                "prediction_dump": _artifact_record(repository_root, prediction_path),
            }
            if condition == "baseline":
                baseline_by_seed[seed_key] = metrics
            else:
                factorized_by_seed[seed_key] = metrics
            if seed == primary_seed:
                primary_paths[condition] = (checkpoint_path, prediction_path)
            run.model.to("cpu")
            torch.cuda.empty_cache()
        if (
            runs["baseline"].initial_state_sha256
            != runs["factorized"].initial_state_sha256
        ):
            raise RuntimeError(f"seed {seed} conditions did not share initialization")
        if (
            runs["baseline"].batch_schedule_sha256
            != runs["factorized"].batch_schedule_sha256
        ):
            raise RuntimeError(f"seed {seed} conditions did not share batch schedule")
        history_payload = {
            "seed": seed,
            "provenance": provenance,
            "conditions": {
                condition: {
                    "initial_losses": runs[condition].initial_losses,
                    "final_losses": runs[condition].final_losses,
                    "history": runs[condition].history,
                }
                for condition in CONDITIONS
            }
        }
        write_json_atomic(
            full_run_dir / f"seed_{seed}" / "training_history.json", history_payload
        )

    summary = summarize_seed_metrics(baseline_by_seed, factorized_by_seed)
    gate_config = config["gate"]
    gate = decide_factorization_gate(
        summary,
        leakage_reduction_min=float(gate_config["leakage_reduction_fraction_min"]),
        own_response_degradation_max=float(
            gate_config["own_response_error_relative_degradation_max"]
        ),
        parameter_mae_degradation_max=float(
            gate_config["physical_parameter_mae_relative_degradation_max"]
        ),
        improved_seed_fraction_min=(
            int(gate_config["minimum_leakage_improved_seed_count"])
            / int(gate_config["seed_count"])
        ),
        required_seed_count=int(gate_config["seed_count"]),
    )
    gate["seed_consistency_audit"] = _gate_seed_consistency_audit(
        summary, gate_config
    )
    figure_data = _build_figure_data(
        baseline_by_seed, factorized_by_seed, summary, provenance
    )

    canonical_paths: dict[str, Path] = {}
    for condition in CONDITIONS:
        source_checkpoint, source_prediction = primary_paths[condition]
        canonical_checkpoint = checkpoint_root / f"checkpoint_{condition}.pt"
        canonical_prediction = prediction_root / f"prediction_dump_{condition}.npz"
        canonical_checkpoint.parent.mkdir(parents=True, exist_ok=True)
        canonical_prediction.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_checkpoint, canonical_checkpoint)
        shutil.copy2(source_prediction, canonical_prediction)
        canonical_paths[f"checkpoint_{condition}"] = canonical_checkpoint
        canonical_paths[f"prediction_dump_{condition}"] = canonical_prediction

    results_path = _resolve_repository_path(repository_root, outputs["results"])
    figure_path = _resolve_repository_path(repository_root, outputs["figure_data"])
    report_path = _resolve_repository_path(repository_root, outputs["report"])
    write_json_atomic(figure_path, figure_data)

    artifacts = {
        "factorization_pilot_manifest": _artifact_record(repository_root, manifest_path),
        "factorial_eval_manifest": _artifact_record(repository_root, eval_manifest_path),
        "tiny_factorial_manifest": dict(
            tiny_gate["artifacts"]["tiny_factorial_manifest"]
        ),
        "tiny_factorial_profiles": dict(
            tiny_gate["artifacts"]["tiny_factorial_profiles"]
        ),
        "factorization_interface_v1": _artifact_record(
            repository_root,
            repository_root / "xrd_inversion/contracts/factorization_interface_v1.md",
        ),
        "factorization_pilot_figure_data": _artifact_record(
            repository_root, figure_path
        ),
        **{
            name: _artifact_record(repository_root, path)
            for name, path in canonical_paths.items()
        },
    }
    results: dict[str, Any] = {
        "schema_version": "xrd-inversion-factorization-pilot-results-v1",
        "completed_utc": _timestamp(),
        "status": "COMPLETE",
        "decision": gate["decision"],
        "continuation_allowed": gate["continuation_allowed"],
        "tiny_overfit": tiny_gate,
        "dataset": {
            "parents": int(manifest["counts"]["parents"]),
            "blocks": int(manifest["counts"]["blocks"]),
            "spectra": int(manifest["counts"]["spectra"]),
            "training_blocks": len(train_indices),
            "evaluation_blocks": len(eval_indices),
            "evaluation_scope": "Train-parent internal unseen interventions only",
            "manifest_payload_sha256": manifest["payload_sha256"],
            "eval_manifest_payload_sha256": eval_manifest["payload_sha256"],
            "payload_hash_definition": (
                "SHA-256 of canonical JSON excluding the payload_sha256 self-hash field"
            ),
        },
        "matched_design": {
            "model": dict(config["model"]),
            "training": dict(config["training"]),
            "seeds": [int(value) for value in config["training_seeds"]],
            "channel_mean": channel_mean.tolist(),
            "channel_std": channel_std.tolist(),
            "only_condition_difference": "lambda_pair: 0 vs 1",
        },
        "provenance": provenance,
        "seed_results": seed_results,
        "summary": summary,
        "gate": gate,
        "figure_data": figure_data,
        "execution_boundary": {
            **dict(config["execution_boundary"]),
            "formal_pipeline_splits_accessed": ["train"],
            "formal_pipeline_independent_renderer_access": False,
            "formal_generalization_claim": False,
            "development_qa_incidents": [
                (
                    "A broad read-only search echoed frozen independent-renderer config "
                    "metadata; no renderer source, profiles, metrics, or outcomes were opened."
                ),
                (
                    "A delegated `pytest -q xrd_inversion/tests` command executed "
                    "test_independent_renderer.py; excluded from Stage-1 evidence and "
                    "produced no formal Pilot artefact."
                ),
            ],
        },
        "artifacts": artifacts,
        "reporting_outputs": {
            "results": _relative(repository_root, results_path),
            "figure_data": _relative(repository_root, figure_path),
            "report": _relative(repository_root, report_path),
            "tiny_manifest": str(tiny_gate["manifest_path"]),
            "tiny_profile_bundle": str(tiny_gate["profile_bundle_path"]),
            "per_seed_checkpoint_pattern": (
                _relative(repository_root, checkpoint_root)
                + "/seed_<seed>/checkpoint_<condition>.pt"
            ),
            "per_seed_prediction_pattern": (
                _relative(repository_root, prediction_root)
                + "/seed_<seed>/prediction_dump_<condition>.npz"
            ),
        },
    }
    write_json_atomic(results_path, results)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_markdown_report(results), encoding="utf-8")
    print(f"Phase 10 complete: {gate['decision']}", flush=True)
    return results


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[3]
    parser.add_argument("--repository-root", type=Path, default=default_root)
    parser.add_argument(
        "--config",
        type=Path,
        default=default_root / "xrd_inversion/configs/factorization_pilot.json",
    )
    parser.add_argument(
        "--tiny-only",
        action="store_true",
        help="run and persist only the engineering tiny-overfit Gate",
    )
    parser.add_argument(
        "--resume-after-tiny-pass",
        action="store_true",
        help="require and reuse an unchanged saved tiny PASS before the formal run",
    )
    parser.add_argument(
        "--replace-current-run-artifacts",
        action="store_true",
        help=(
            "replace artefacts from this Pilot run after an implementation-only "
            "correction; incompatible with --tiny-only"
        ),
    )
    args = parser.parse_args(argv)
    if args.tiny_only and args.resume_after_tiny_pass:
        parser.error("--tiny-only and --resume-after-tiny-pass are mutually exclusive")
    if args.tiny_only and args.replace_current_run_artifacts:
        parser.error(
            "--tiny-only and --replace-current-run-artifacts are mutually exclusive"
        )
    if args.tiny_only:
        tiny = run_tiny_overfit_only(args.repository_root, args.config)
        result = {
            "status": "TINY_OVERFIT_" + tiny["status"],
            "decision": None,
            "continuation_allowed": tiny["status"] == "PASS",
        }
    else:
        result = run_factorization_pilot(
            args.repository_root,
            args.config,
            reuse_passing_tiny=args.resume_after_tiny_pass,
            replace_current_run_artifacts=args.replace_current_run_artifacts,
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result.get("decision"),
                "continuation_allowed": result.get("continuation_allowed", False),
            },
            indent=2,
        )
    )
    if result["status"] in {"STOPPED_TINY_OVERFIT_FAIL", "TINY_OVERFIT_FAIL"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()


__all__ = [
    "evaluate_tiny_overfit_gate",
    "run_factorization_pilot",
    "run_tiny_overfit_only",
]
