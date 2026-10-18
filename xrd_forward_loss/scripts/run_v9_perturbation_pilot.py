"""Run a small paired A/B pilot with V9-generated measurement nuisance views."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.metadata
import inspect
import json
import logging
import platform
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import torch

from pxrd_forward_loss.data import read_json
from pxrd_forward_loss.evaluation import evaluate_model
from pxrd_forward_loss.losses import clean_reference_paired_losses
from pxrd_forward_loss.model import compose_full_q
from pxrd_forward_loss.perturbation_data import (
    build_perturbation_dataset,
    condition_arrays,
)
from pxrd_forward_loss.training import fit
from xrd_robustness.measurement_models import (
    apply_noise_model,
    generate_background_profile,
)
from xrd_robustness.physics import PhysicsParameters
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def json_ready(value: Any):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().tolist()
    return value


def save_json(path: Path, value: Any):
    path.write_bytes(json_bytes(value))


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(json_ready(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def compact_results(results: dict[str, Any]) -> dict[str, Any]:
    """Keep review-facing metrics small; full predictions are archived as gzip JSON."""
    conditions = {}
    for condition, condition_rows in results["conditions"].items():
        conditions[condition] = {}
        for method, method_rows in condition_rows.items():
            compact_seeds = []
            for seed_row in method_rows["seeds"]:
                test_metrics = {
                    key: value
                    for key, value in seed_row["test"].items()
                    if key not in {
                        "prediction_q",
                        "target_q",
                        "reconstruction_profile",
                        "per_sample_clean_rmse",
                    }
                }
                compact_seeds.append(
                    {key: value for key, value in seed_row.items() if key != "test"}
                    | {"test": test_metrics}
                )
            conditions[condition][method] = {
                "summary": method_rows["summary"],
                "seeds": compact_seeds,
            }
    return {
        "schema_version": "pxrd-forward-loss-v9-pilot-results-summary-v1",
        "conditions": conditions,
        "paired_differences_b_minus_a": results["paired_differences_b_minus_a"],
        "failure_cases": results["failure_cases"],
        "full_prediction_archive": "results_full.json.gz",
    }


def audit_forward_and_clean_loss(forward: Any, config: dict[str, Any], device: torch.device):
    gates = config["physical_gates"]
    q0 = np.asarray([0.11, -0.13, 0.0, -1.0], dtype=np.float64)
    jacobian = forward.transformed_jacobian_numpy(q0)
    active = jacobian[:, :2]
    singular_values = np.linalg.svd(active, compute_uv=False)
    condition = float(singular_values[0] / singular_values[-1])
    jacobian_fd: dict[str, dict[str, Any]] = {}
    for coordinate, name in enumerate(("du", "dv")):
        errors = []
        for step in (1e-3, 5e-4, 2.5e-4):
            plus, minus = q0.copy(), q0.copy()
            plus[coordinate] += step
            minus[coordinate] -= step
            finite_difference = (
                forward.transformed_numpy(plus) - forward.transformed_numpy(minus)
            ) / (2.0 * step)
            errors.append(
                float(
                    np.linalg.norm(finite_difference - jacobian[:, coordinate])
                    / max(np.linalg.norm(jacobian[:, coordinate]), 1e-12)
                )
            )
        jacobian_fd[name] = {
            "relative_l2_error_by_step": errors,
            "best_relative_l2_error": min(errors),
        }

    predicted = torch.tensor(
        [[0.12, -0.10]], dtype=torch.float64, device=device, requires_grad=True
    )
    target_q = torch.tensor([[-0.08, 0.06]], dtype=torch.float64, device=device)
    reference_q = torch.tensor([[0.18, 0.11]], dtype=torch.float64, device=device)
    with torch.no_grad():
        clean_reference = forward.transformed(compose_full_q(reference_q))

    def scalar(q_value: torch.Tensor) -> torch.Tensor:
        return clean_reference_paired_losses(
            q_value,
            target_q,
            clean_reference,
            forward_model=forward,
            reconstruction_weight=float(config["training"]["reconstruction_weight"]),
        )["total"]

    objective = scalar(predicted)
    objective.backward()
    autograd_gradient = predicted.grad.detach().cpu().numpy()[0]
    loss_fd = []
    for coordinate, name in enumerate(("du", "dv")):
        plus = np.asarray([0.12, -0.10], dtype=np.float64)
        minus = plus.copy()
        plus[coordinate] += 1e-4
        minus[coordinate] -= 1e-4
        plus_tensor = torch.as_tensor(plus[None, :], dtype=torch.float64, device=device)
        minus_tensor = torch.as_tensor(minus[None, :], dtype=torch.float64, device=device)
        finite_difference = float((scalar(plus_tensor) - scalar(minus_tensor)) / 2e-4)
        relative_error = abs(finite_difference - autograd_gradient[coordinate]) / max(
            abs(finite_difference), abs(autograd_gradient[coordinate]), 1e-12
        )
        loss_fd.append(
            {
                "coordinate": name,
                "autograd": float(autograd_gradient[coordinate]),
                "finite_difference": finite_difference,
                "relative_error": float(relative_error),
            }
        )
    result = {
        "gate": "differentiable clean-reference reconstruction and lattice identifiability",
        "active_parameters": ["du", "dv"],
        "jacobian_singular_values": singular_values.tolist(),
        "jacobian_condition_number": condition,
        "jacobian_full_rank": bool(singular_values[-1] > singular_values[0] * 1e-3),
        "jacobian_finite_difference": jacobian_fd,
        "clean_reference_objective": float(objective.detach().cpu()),
        "clean_reference_autograd_gradient": autograd_gradient.tolist(),
        "clean_reference_loss_gradient_finite_difference": loss_fd,
    }
    result["passed"] = bool(
        result["jacobian_full_rank"]
        and condition < float(gates["parameter_jacobian_condition_max"])
        and all(
            item["best_relative_l2_error"]
            < float(gates["jacobian_finite_difference_relative_max"])
            for item in jacobian_fd.values()
        )
        and np.isfinite(autograd_gradient).all()
        and all(
            item["relative_error"] < float(gates["clean_loss_gradient_relative_max"])
            for item in loss_fd
        )
    )
    if not result["passed"]:
        raise RuntimeError(f"clean-reference forward gradient gate failed: {result}")
    return result


def _centroid(axis: np.ndarray, profile: np.ndarray, center: float) -> float:
    mask = np.abs(axis - center) <= 0.30
    weights = np.asarray(profile)[mask]
    return float(np.sum(axis[mask] * weights) / np.sum(weights))


def audit_v9_operators(config: dict[str, Any]):
    gate_config = config["physical_gates"]
    axis = np.linspace(10.0, 80.0, 3501)
    background, background_meta = generate_background_profile(
        axis,
        0.008,
        model="polynomial",
        order=2,
        variation=0.2,
        floor_fraction=0.1,
        rng=np.random.default_rng(9301),
    )
    expected = np.full(50000, 0.5, dtype=np.float64)
    noisy, noise_meta = apply_noise_model(
        expected,
        rng=np.random.default_rng(9302),
        model="poisson_gaussian",
        poisson_count_scale=5000.0,
        electronic_noise_std_counts=2.0,
    )
    expected_variance = 0.5 / 5000.0 + (2.0 / 5000.0) ** 2

    grid = SimulationGrid()
    common = dict(
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=2,
        background_active=False,
        noise_active=False,
        preferred_orientation_active=False,
    )
    narrow = PhysicsParameters(0.0, 0.08, **common)
    broad = PhysicsParameters(0.0, 0.12, **common)
    narrow_profile = simulate_from_peak_table(
        [25.0, 43.0], [100.0, 60.0], narrow,
        rng_seed=9303, grid=grid, normalize=False,
    )
    broad_profile = simulate_from_peak_table(
        [25.0, 43.0], [100.0, 60.0], broad,
        rng_seed=9303, grid=grid, normalize=False,
    )
    integrate = np.trapezoid
    narrow_area = float(integrate(narrow_profile, grid.values))
    broad_area = float(integrate(broad_profile, grid.values))
    shift_deg = 0.05
    unshifted = PhysicsParameters(0.0, 0.08, **common)
    shifted = PhysicsParameters(shift_deg, 0.08, **common)
    base = simulate_from_peak_table(
        [30.0, 46.0], [100.0, 70.0], unshifted,
        rng_seed=9304, grid=grid, normalize=False,
    )
    moved = simulate_from_peak_table(
        [30.0, 46.0], [100.0, 70.0], shifted,
        rng_seed=9304, grid=grid, normalize=False,
    )
    centroid_errors = [
        abs((_centroid(grid.values, moved, center) - _centroid(grid.values, base, center)) - shift_deg)
        for center in (30.0, 46.0)
    ]
    result = {
        "gate": "V9 noise/background/broadening/global-shift operator checks",
        "generation_order": [
            "optional_reflection_aware_orientation_disabled",
            "global_2theta_shift",
            "area_stable_gaussian_broadening",
            "smooth_nonnegative_background",
            "poisson_plus_count_domain_gaussian_readout",
            "clip_negative_values",
            "single_max_normalization",
        ],
        "poisson_gaussian": {
            "passed": bool(
                abs(float(np.mean(noisy)) - 0.5) < 2.5e-4
                and abs(float(np.var(noisy)) - expected_variance) < expected_variance * 0.03
            ),
            "observed_mean": float(np.mean(noisy)),
            "observed_variance": float(np.var(noisy)),
            "expected_variance": expected_variance,
            "metadata": noise_meta,
        },
        "smooth_background": {
            "passed": bool(
                np.isfinite(background).all()
                and float(np.min(background)) >= 0.0
                and abs(float(np.max(background)) - 0.008) < 1e-7
                and float(np.max(np.abs(np.diff(background, n=2)))) < 1e-5
            ),
            "max_second_difference": float(np.max(np.abs(np.diff(background, n=2)))),
            "metadata": background_meta,
        },
        "peak_broadening": {
            "passed": bool(
                abs(broad_area / narrow_area - 1.0)
                < float(gate_config["broadening_area_relative_error_max"])
            ),
            "area_relative_error": abs(broad_area / narrow_area - 1.0),
        },
        "whole_pattern_zero_shift": {
            "passed": bool(
                max(centroid_errors)
                < float(gate_config["global_shift_centroid_error_deg_max"])
            ),
            "shift_deg": shift_deg,
            "peak_centroid_errors_deg": centroid_errors,
        },
        "march_dollase": {
            "enabled": False,
            "reason": "not needed for this one-parent pilot; no orientation nuisance is sampled",
        },
    }
    result["passed"] = all(
        result[key]["passed"]
        for key in (
            "poisson_gaussian",
            "smooth_background",
            "peak_broadening",
            "whole_pattern_zero_shift",
        )
    )
    if not result["passed"]:
        raise RuntimeError(f"V9 perturbation physical gate failed: {result}")
    return result


def _init_runtime(device: torch.device):
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)


def _save_dataset(output_dir: Path, arrays: dict[str, np.ndarray], records: list[dict[str, Any]]):
    np.savez_compressed(output_dir / "pilot_samples.npz", **arrays)
    with (output_dir / "sample_records.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def _run_smoke(
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    forward: Any,
    device: torch.device,
    config: dict[str, Any],
):
    training = config["training"]
    results = {}
    for condition in ("simple", "v9"):
        condition_data = condition_arrays(arrays, condition)
        for method, weight in (("A", 0.0), ("B", float(training["reconstruction_weight"]))):
            fit_result = fit(
                condition_data,
                splits,
                forward_model=forward,
                device=device,
                seed=int(training["seeds"][0]),
                epochs=int(training["smoke_epochs"]),
                learning_rate=float(training["learning_rate"]),
                batch_size=int(training["batch_size"]),
                reconstruction_weight=weight,
                gradient_clip_norm=float(training["gradient_clip_norm"]),
                max_train_samples=int(training["smoke_max_train_samples"]),
                clean_reference_profiles=condition_data["clean"],
            )
            results[f"{condition}_{method}"] = {
                "finite_training_loss": bool(
                    np.isfinite([row["train_total_loss"] for row in fit_result["history"]]).all()
                ),
                "finite_validation_mae": bool(np.isfinite(fit_result["best_validation_q_mae"])),
                "updates": int(fit_result["updates"]),
                "training_seconds": float(fit_result["training_seconds"]),
                "peak_memory_allocated_mb": fit_result["peak_memory_allocated_mb"],
                "train_sample_count": int(fit_result["train_sample_count"]),
            }
    if not all(row["finite_training_loss"] and row["finite_validation_mae"] for row in results.values()):
        raise RuntimeError("one or more 2x2 smoke fits produced non-finite losses")
    return results


def _aggregate(values: list[float]):
    return {
        "mean": float(np.mean(values)),
        "sd_sample": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "seed_values": [float(value) for value in values],
    }


def run_paired_pilot(
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    forward: Any,
    forward_config: dict[str, Any],
    device: torch.device,
    config: dict[str, Any],
    sample_records: list[dict[str, Any]],
    parent_lattice: dict[str, float],
    logger: logging.Logger | None = None,
):
    training = config["training"]
    q_bounds = forward_config["parameterization"]
    split_test = np.asarray(splits["test"], dtype=np.int64)
    results: dict[str, Any] = {"conditions": {}, "paired_differences_b_minus_a": {}}
    histories: dict[str, Any] = {}
    all_abs_errors: dict[str, list[np.ndarray]] = {}

    for condition in ("simple", "v9"):
        condition_data = condition_arrays(arrays, condition)
        condition_rows: dict[str, Any] = {"A": {"seeds": []}, "B": {"seeds": []}}
        for seed in training["seeds"]:
            for method, weight in (("A", 0.0), ("B", float(training["reconstruction_weight"]))):
                if logger is not None:
                    logger.info("Training start condition=%s method=%s seed=%s", condition, method, seed)
                fit_result = fit(
                    condition_data,
                    splits,
                    forward_model=forward,
                    device=device,
                    seed=int(seed),
                    epochs=int(training["final_epochs"]),
                    learning_rate=float(training["learning_rate"]),
                    batch_size=int(training["batch_size"]),
                    reconstruction_weight=weight,
                    gradient_clip_norm=float(training["gradient_clip_norm"]),
                    clean_reference_profiles=condition_data["clean"],
                )
                if logger is not None:
                    logger.info(
                        "Training complete condition=%s method=%s seed=%s seconds=%.3f peak_memory_mib=%s",
                        condition,
                        method,
                        seed,
                        fit_result["training_seconds"],
                        fit_result["peak_memory_allocated_mb"],
                    )
                evaluation = evaluate_model(
                    fit_result["model"],
                    condition_data,
                    split_test,
                    forward_model=forward,
                    device=device,
                    a0=float(parent_lattice["a"]),
                    c0=float(parent_lattice["c"]),
                    du_half=float(q_bounds["du_half_range"]),
                    dv_half=float(q_bounds["dv_half_range"]),
                )
                seed_row = {
                    "seed": int(seed),
                    "best_epoch": int(fit_result["best_epoch"]),
                    "best_validation_q_mae": float(fit_result["best_validation_q_mae"]),
                    "updates": int(fit_result["updates"]),
                    "training_seconds": float(fit_result["training_seconds"]),
                    "training_seconds_per_epoch": float(fit_result["training_seconds_per_epoch"]),
                    "peak_memory_allocated_mb": fit_result["peak_memory_allocated_mb"],
                    "train_sample_count": int(fit_result["train_sample_count"]),
                    "test": evaluation,
                }
                condition_rows[method]["seeds"].append(seed_row)
                history_key = f"{condition}_{method}_seed{seed}"
                histories[history_key] = fit_result["history"]
                all_abs_errors.setdefault(f"{condition}_{method}", []).append(
                    np.abs(
                        np.asarray(evaluation["prediction_q"], dtype=np.float64)
                        - np.asarray(evaluation["target_q"], dtype=np.float64)
                    )
                )

        metric_paths = {
            "normalized_du_mae": ("parameter_mae_normalized", "du"),
            "normalized_dv_mae": ("parameter_mae_normalized", "dv"),
            "normalized_mean_two_parameter_mae": (
                "parameter_mae_normalized", "mean_two_parameter"
            ),
            "a_mae_angstrom": ("lattice_mae_angstrom", "a"),
            "c_mae_angstrom": ("lattice_mae_angstrom", "c"),
            "reconstruction_rmse_transformed_clean": (
                "reconstruction_rmse_transformed_clean",
            ),
            "reconstruction_rmse_transformed_observed": (
                "reconstruction_rmse_transformed_noisy",
            ),
        }
        for method in ("A", "B"):
            seed_rows = condition_rows[method]["seeds"]
            summaries = {}
            for metric_name, path in metric_paths.items():
                values = []
                for seed_row in seed_rows:
                    value: Any = seed_row["test"]
                    for key in path:
                        value = value[key]
                    values.append(float(value))
                summaries[metric_name] = _aggregate(values)
            summaries["training_seconds"] = _aggregate(
                [row["training_seconds"] for row in seed_rows]
            )
            memory_values = [
                float(row["peak_memory_allocated_mb"])
                for row in seed_rows
                if row["peak_memory_allocated_mb"] is not None
            ]
            summaries["peak_memory_allocated_mb"] = (
                _aggregate(memory_values) if memory_values else None
            )
            condition_rows[method]["summary"] = summaries
        results["conditions"][condition] = condition_rows
        results["paired_differences_b_minus_a"][condition] = {}
        for metric_name in metric_paths:
            a_values = condition_rows["A"]["summary"][metric_name]["seed_values"]
            b_values = condition_rows["B"]["summary"][metric_name]["seed_values"]
            results["paired_differences_b_minus_a"][condition][metric_name] = _aggregate(
                [b - a for a, b in zip(a_values, b_values, strict=True)]
            )

    failures = []
    for condition in ("simple", "v9"):
        b_rows = results["conditions"][condition]["B"]["seeds"]
        for seed_row in b_rows:
            eval_row = seed_row["test"]
            errors = np.mean(
                np.abs(
                    np.asarray(eval_row["prediction_q"], dtype=np.float64)
                    - np.asarray(eval_row["target_q"], dtype=np.float64)
                ),
                axis=1,
            )
            local_index = int(np.argmax(errors))
            global_index = int(split_test[local_index])
            failures.append(
                {
                    "condition": condition,
                    "seed": int(seed_row["seed"]),
                    "test_index": global_index,
                    "mean_absolute_q_error": float(errors[local_index]),
                    "theta_true": eval_row["target_q"][local_index],
                    "theta_predicted": eval_row["prediction_q"][local_index],
                    "nuisance_metadata": sample_records[global_index]["nuisance_metadata"],
                }
            )
    results["failure_cases"] = failures
    return results, histories, all_abs_errors


def save_plots(
    output_dir: Path,
    arrays: dict[str, np.ndarray],
    results: dict[str, Any],
    abs_errors: dict[str, list[np.ndarray]],
    axis: np.ndarray,
    test_indices: np.ndarray,
):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for coordinate, name in enumerate(("du", "dv")):
        labels = []
        values = []
        for condition in ("simple", "v9"):
            for method in ("A", "B"):
                stack = np.concatenate(abs_errors[f"{condition}_{method}"], axis=0)
                values.append(stack[:, coordinate])
                labels.append(f"{condition.upper()}-{method}")
        boxplot_kwargs = {"showmeans": True}
        label_argument = "tick_labels" if "tick_labels" in inspect.signature(axes[coordinate].boxplot).parameters else "labels"
        boxplot_kwargs[label_argument] = labels
        axes[coordinate].boxplot(values, **boxplot_kwargs)
        axes[coordinate].set_title(f"Absolute normalized {name} error")
        axes[coordinate].set_ylabel("Absolute q error")
        axes[coordinate].grid(axis="y", alpha=0.25)
        axes[coordinate].tick_params(axis="x", rotation=20)
    seed_counts = len(results["conditions"]["simple"]["A"]["seeds"])
    fig.suptitle(f"HfCd test parameter errors across {seed_counts} paired seed(s)")
    fig.tight_layout()
    fig.savefig(output_dir / "parameter_error.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
    colors = {"A": "#2878B5", "B": "#D9534F"}
    for panel, condition in enumerate(("simple", "v9")):
        row = results["failure_cases"]
        worst = max(
            (entry for entry in row if entry["condition"] == condition),
            key=lambda entry: entry["mean_absolute_q_error"],
        )
        idx = int(worst["test_index"])
        observed_key = "observed_profile_simple" if condition == "simple" else "observed_profile_v9"
        axes[panel].plot(
            axis,
            arrays[observed_key][idx],
            color="#777777",
            linewidth=0.8,
            alpha=0.7,
            label="Observed input",
        )
        axes[panel].plot(
            axis,
            arrays["clean_profile"][idx],
            color="black",
            linewidth=1.2,
            label="Clean simulator reference",
        )
        local_index = int(np.flatnonzero(np.asarray(test_indices) == idx)[0])
        for method in ("A", "B"):
            seed_row = next(
                item
                for item in results["conditions"][condition][method]["seeds"]
                if item["seed"] == worst["seed"]
            )
            axes[panel].plot(
                axis,
                np.asarray(seed_row["test"]["reconstruction_profile"])[local_index],
                linewidth=1.0,
                label=f"{method} reconstructed profile",
            )
        axes[panel].set_title(
            f"{condition.upper()} worst B case: sample {idx}; |q| MAE={worst['mean_absolute_q_error']:.3f}"
        )
        axes[panel].set_xlabel("2θ (degrees)")
        axes[panel].grid(alpha=0.2)
        axes[panel].legend()
    axes[0].set_ylabel("Transformed intensity")
    fig.tight_layout()
    fig.savefig(output_dir / "xrd_overlay.png", dpi=180)
    plt.close(fig)


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _configure_logger(path: Path):
    logger = logging.getLogger("v9_forward_loss_pilot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _verify_prior_stage(path: Path, required_phase: str):
    manifest = _load_json(path)
    if manifest.get("status") != "complete" or manifest.get("phase") != required_phase:
        raise ValueError(
            f"evidence {path} must be a completed run for phase {required_phase}"
        )
    if not manifest.get("smoke_only", False):
        raise ValueError(f"evidence {path} must be a smoke-only run")
    gates = manifest.get("gates", {})
    if not all(bool(value.get("passed")) for value in gates.values()):
        raise ValueError(f"evidence {path} does not contain passing physical gates")
    return manifest


def _write_report(
    output_dir: Path,
    *,
    phase: str,
    metadata: dict[str, Any],
    gates: dict[str, Any],
    smoke: dict[str, Any],
    results: dict[str, Any] | None,
    config: dict[str, Any],
):
    lines = [
        "# V9 扰动与 clean-reference Forward Loss 工程 Pilot",
        "",
        "> 这是单一已知 HfCd 母结构上的模拟器工程 Pilot，不代表铁电陶瓷或真实实验谱验证。B 使用模拟器生成的 clean reference；不得解释为真实实验谱上的无监督物理重建。",
        "",
        "## 数据与接口",
        "",
        f"- 材料：{metadata['formula']}（{metadata['material_id']}），来源 split={metadata['source_split']}；共 {metadata['pattern_count']} 个晶格参数样本，train/validation/test={metadata['split_counts']['train']}/{metadata['split_counts']['validation']}/{metadata['split_counts']['test']}。",
        f"- CIF：未提供；从本地冻结 structure_records.jsonl 的 standardized_structure JSON 重建结构，指纹 `{metadata['structure_fingerprint']}`。",
        f"- `sample_records.jsonl` 保留 Sobol float64 的 `theta_true` 和晶格真值；NN 输入数组中的 q 按现有训练接口存为 float32，本次两者最大舍入差为 {metadata.get('max_q_float32_rounding', 'not recorded')}。",
        f"- 配置 SHA-256：`{metadata['config_sha256']}`；数据阵列 SHA-256：`{metadata['dataset_sha256']}`。逐样本 q、lattice truth、扰动参数/类型/采样 seed、结构来源与配置哈希在 `sample_records.jsonl`；profile 阵列按同一 sample_index 存于 `pilot_samples.npz`。",
        "- A/B 汇总值由 `validate_v9_pilot_results.py` 从逐 seed 预测、保存谱阵列及 JSON 结果重新计算；复算状态和 SHA-256 见 `results_validation.json`。",
        f"- 谱顺序：干净相对强度（峰值归一化）→ V9 平滑背景 → Poisson 计数和计数域 Gaussian 读出 → clip → 每谱单次 max 归一化 → log1p 变换。背景与噪声前不做归一化。原始绝对计数未建模，因此是相对计数工程模拟。",
        f"- Forward/V9 clean renderer 兼容 Gate：{'通过' if gates['renderer_compatibility']['passed'] else '失败'}，max abs={gates['renderer_compatibility']['max_abs_error']:.3g}，RMSE={gates['renderer_compatibility']['max_probe_rmse']:.3g}。",
        "",
        "## V9 接入范围与物理检查",
        "",
        f"- 操作 Gate 总体：{'通过' if gates['v9_operators']['passed'] else '失败'}。noise={gates['v9_operators']['poisson_gaussian']['passed']}，smooth background={gates['v9_operators']['smooth_background']['passed']}，area-stable broadening={gates['v9_operators']['peak_broadening']['passed']}，whole-pattern zero shift={gates['v9_operators']['whole_pattern_zero_shift']['passed']}。",
        f"- Forward lattice Jacobian rank/condition：full-rank={gates['forward_loss']['jacobian_full_rank']}，condition={gates['forward_loss']['jacobian_condition_number']:.4g}；有限差分与 autograd Gate={'通过' if gates['forward_loss']['passed'] else '失败'}。Loss 名称为 `{config['interpretation']['clean_reference_loss_name']}`。",
        "- March–Dollase 保持关闭：当前 pilot 不需要择优取向，且没有将随机逐峰缩放伪装成晶面择优取向。",
        "- 扰动范围是工程压力测试范围，不是任何仪器标定范围。零点偏移和峰宽只改变输入谱，不改变 q 标签。",
        "",
        "## 运行结果",
        "",
        f"- 本报告阶段：`{phase}`。四格单 seed smoke 的有限损失检查：{'通过' if all(row['finite_training_loss'] and row['finite_validation_mae'] for row in smoke.values()) else '失败'}。Smoke 只跑 {config['training']['smoke_epochs']} epoch，最多 {config['training']['smoke_max_train_samples']} 个训练样本，不作为效果结论。",
    ]
    if results is None:
        lines.extend([
            "- 当前目录仅保存 smoke 与 Gate 记录；未执行三 seed 主 Pilot。",
            "",
            "## 后续材料迁移条件",
            "",
            "迁移到铁电陶瓷前，至少需要：经授权且可追溯的陶瓷结构/CIF 与相组成、反射/晶面族元数据和可信空间群、实验仪器波长/几何/标准样品零点及峰宽标定、背景和噪声统计、样品择优取向证据、适用于陶瓷的结构扰动边界、独立于参数抽样的样本级 train/validation/test 划分，以及预注册的优化预算和失败判据。需先验证 forward renderer 对真实标准谱的误差，再决定是否训练；本 HfCd 结果不能替代这些验证。",
        ])
    else:
        lines.extend(["", "### 测试集聚合指标（每 seed 独立评估；报告 mean ± sample SD）", ""])
        lines.append("| 条件 | 方法 | normalized-q MAE | a MAE (Å) | c MAE (Å) | clean谱 RMSE | observed谱 RMSE | 秒/训练 | 峰值显存 MiB |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for condition in ("simple", "v9"):
            for method in ("A", "B"):
                summary = results["conditions"][condition][method]["summary"]

                def fmt(metric):
                    item = summary[metric]
                    if item is None:
                        return "n/a"
                    return f"{item['mean']:.5g} ± {item['sd_sample']:.2g}"

                lines.append(
                    f"| {condition} | {method} | {fmt('normalized_mean_two_parameter_mae')} | {fmt('a_mae_angstrom')} | {fmt('c_mae_angstrom')} | {fmt('reconstruction_rmse_transformed_clean')} | {fmt('reconstruction_rmse_transformed_observed')} | {fmt('training_seconds')} | {fmt('peak_memory_allocated_mb')} |"
                )
        lines.extend([
            "",
            "A 为普通监督参数回归；B 为相同网络、数据和预算的监督回归加 clean-reference Forward Loss。`paired_differences_b_minus_a` 中负数表示 B 的该误差更低，正数表示更高。三组 seed 是预先配置的配对 Pilot，不做测试集超参选择。逐 seed 指标见 `results_summary.json`；完整预测和重建谱保存在 `results_full.json.gz`，训练过程见 `training_histories.json`，失败样本见 `failure_cases.json`。",
            "",
            "## 结果解释与迁移限制",
            "",
            "少量单父结构结果只用于工程可运行性与 A/B 初步诊断。不能将测试集差异解释成材料泛化、铁电陶瓷表现或真实谱物理有效性；无论正负均完整保留。迁移前置条件见上节。",
        ])
    (output_dir / "TECHNICAL_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None):
    root = repository_root()
    default_config = root / "xrd_forward_loss/configs/v9_disturbance_clean_reference_pilot.json"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--source-root", type=Path, default=root)
    parser.add_argument("--output", type=Path, required=True, help="New output directory; it must not already exist")
    parser.add_argument("--phase", choices=("phase1_noise_background", "phase2_add_broadening_and_zero_shift"), required=True)
    parser.add_argument("--smoke-only", action="store_true", help="Run gates and the tiny four-cell smoke only")
    parser.add_argument("--phase1-evidence", type=Path, help="Completed phase-1 smoke run_manifest.json required before phase 2")
    parser.add_argument("--smoke-evidence", type=Path, help="Completed phase-2 smoke run_manifest.json required before the 3-seed pilot")
    args = parser.parse_args(argv)

    output_dir = args.output if args.output.is_absolute() else root / args.output
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(exist_ok=False)
    logger = _configure_logger(output_dir / "run.log")
    config_path = args.config if args.config.is_absolute() else root / args.config
    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes.decode("utf-8"))
    config_hash = hashlib.sha256(config_bytes).hexdigest()
    started_at = datetime.now(timezone.utc).isoformat()
    manifest: dict[str, Any] = {
        "run_id": output_dir.name,
        "status": "running",
        "phase": args.phase,
        "smoke_only": bool(args.smoke_only),
        "started_at_utc": started_at,
        "finished_at_utc": None,
        "config_path": str(config_path.relative_to(root)) if config_path.is_relative_to(root) else config_path.name,
        "config_sha256": config_hash,
        "source_root_label": "authorized local dataset source" if args.source_root.resolve() != root.resolve() else "worktree",
        "git_head": git_commit(root),
        "device_requested": config["forward_model"]["device"],
        "gates": {},
        "artifacts": {},
    }
    save_json(output_dir / "run_manifest.json", manifest)
    try:
        if args.phase == "phase2_add_broadening_and_zero_shift":
            if args.phase1_evidence is None:
                raise ValueError("phase 2 requires a completed phase-1 smoke manifest")
            phase1_manifest = _verify_prior_stage(args.phase1_evidence, "phase1_noise_background")
            manifest["phase1_evidence_run_id"] = phase1_manifest["run_id"]
        elif not args.smoke_only:
            raise ValueError("full paired pilot is reserved for phase 2 after both smoke gates")
        if not args.smoke_only:
            if args.smoke_evidence is None:
                raise ValueError("the 3-seed phase-2 pilot requires completed phase-2 smoke evidence")
            smoke_manifest = _verify_prior_stage(args.smoke_evidence, "phase2_add_broadening_and_zero_shift")
            manifest["phase2_smoke_evidence_run_id"] = smoke_manifest["run_id"]

        device = torch.device(config["forward_model"]["device"])
        if device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("configured CUDA device is unavailable; GPU pilot cannot run")
        if config["forward_model"].get("require_cuda", True) and device.type != "cuda":
            raise RuntimeError("this configured pilot requires CUDA; CPU fallback is disabled")
        if device.type == "cuda":
            device = torch.device(f"cuda:{torch.cuda.current_device()}")
            manifest["cuda"] = {
                "available": True,
                "device_name": torch.cuda.get_device_name(device),
                "device_index": torch.cuda.current_device(),
                "runtime": torch.version.cuda,
            }
        manifest["runtime"] = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "scipy": scipy.__version__,
            "pymatgen": importlib.metadata.version("pymatgen"),
            "numpy": np.__version__,
            "device": str(device),
            "tf32": False,
            "deterministic_algorithms": True,
        }
        _init_runtime(device)
        logger.info("Running V9 physical operator gates")
        operator_gate = audit_v9_operators(config)
        manifest["gates"]["v9_operators"] = operator_gate
        save_json(output_dir / "run_manifest.json", manifest)
        logger.info("Building deterministic %s dataset", args.phase)
        arrays, metadata, records, forward, forward_config = build_perturbation_dataset(
            root,
            args.source_root.resolve(),
            config,
            config_sha256=config_hash,
            phase=args.phase,
        )
        logger.info("Running differentiability and clean-reference gradient gates")
        forward_gate = audit_forward_and_clean_loss(forward, config, device)
        manifest["phase"] = args.phase
        save_json(output_dir / "run_manifest.json", manifest)
        manifest["dataset"] = metadata
        manifest["gates"]["renderer_compatibility"] = metadata["clean_renderer_compatibility"]
        manifest["gates"]["forward_loss"] = forward_gate
        splits = {name: arrays[f"{name}_indices"] for name in ("train", "validation", "test")}
        _save_dataset(output_dir, arrays, records)
        manifest["artifacts"].update({
            "dataset_npz": "pilot_samples.npz",
            "sample_provenance": "sample_records.jsonl",
            "config_copy": "pilot_config.json",
        })
        (output_dir / "pilot_config.json").write_bytes(config_bytes)
        save_json(output_dir / "clean_renderer_compatibility.json", metadata["clean_renderer_compatibility"])
        if forward_gate is not None:
            save_json(output_dir / "forward_loss_gradient_gate.json", forward_gate)
        save_json(output_dir / "v9_operator_gates.json", operator_gate)
        manifest["dataset"]["npz_sha256"] = sha256_file(output_dir / "pilot_samples.npz")
        manifest["dataset"]["sample_records_sha256"] = sha256_file(output_dir / "sample_records.jsonl")

        smoke = _run_smoke(arrays, splits, forward, device, config)
        save_json(output_dir / "smoke_results.json", smoke)
        manifest["smoke"] = smoke
        manifest["artifacts"]["smoke_results"] = "smoke_results.json"
        if not args.smoke_only:
            logger.info("Running the preconfigured three paired seeds; no test-driven tuning")
            results, histories, abs_errors = run_paired_pilot(
                arrays,
                splits,
                forward,
                forward_config,
                device,
                config,
                records,
                metadata["lattice_angstrom"],
                logger,
            )
            save_json(output_dir / "results_summary.json", compact_results(results))
            (output_dir / "results_full.json.gz").write_bytes(
                gzip.compress(json_bytes(results), compresslevel=6, mtime=0)
            )
            save_json(output_dir / "training_histories.json", histories)
            save_json(output_dir / "failure_cases.json", results["failure_cases"])
            axis = forward.axis.detach().cpu().numpy()
            save_plots(output_dir, arrays, results, abs_errors, axis, splits["test"])
            validation = subprocess.run(
                [
                    sys.executable,
                    str(root / "xrd_forward_loss/scripts/validate_v9_pilot_results.py"),
                    str(output_dir),
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            if validation.returncode != 0:
                raise RuntimeError(
                    "saved pilot result recomputation failed: "
                    + validation.stdout[-2000:]
                    + validation.stderr[-2000:]
                )
            manifest["artifacts"].update({
                "results": "results_summary.json",
                "full_results_archive": "results_full.json.gz",
                "histories": "training_histories.json",
                "failure_cases": "failure_cases.json",
                "results_validation": "results_validation.json",
                "parameter_error_plot": "parameter_error.png",
                "xrd_overlay_plot": "xrd_overlay.png",
                "technical_report": "TECHNICAL_REPORT.md",
            })
        _write_report(
            output_dir,
            phase=args.phase,
            metadata=metadata,
            gates=manifest["gates"],
            smoke=smoke,
            results=manifest.get("results"),
            config=config,
        )
        manifest["status"] = "complete"
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["artifacts"]["technical_report"] = "TECHNICAL_REPORT.md"
        save_json(output_dir / "run_manifest.json", manifest)
        logger.info("Run complete: %s", output_dir)
        return 0
    except Exception as error:
        manifest["status"] = "failed"
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["error"] = {"type": type(error).__name__, "message": str(error)}
        (output_dir / "error_traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        manifest["artifacts"]["error_traceback"] = "error_traceback.txt"
        save_json(output_dir / "run_manifest.json", manifest)
        logger.exception("Run failed; stopping without relaxing a gate")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
