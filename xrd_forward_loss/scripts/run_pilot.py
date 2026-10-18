"""Run gradient gate, smoke test, validation lambda selection, and paired pilot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import torch
from pymatgen.core import __version__ as pymatgen_version

from pxrd_forward_loss.data import build_dataset, read_json, split_indices
from pxrd_forward_loss.evaluation import evaluate_model, plot_results
from pxrd_forward_loss.losses import paired_losses
from pxrd_forward_loss.model import ParameterRegressor, compose_full_q
from pxrd_forward_loss.training import fit


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def git_commit(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def json_ready(value: Any):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items() if key != "model"}
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_ready(value), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def audit_gradients(forward, arrays: dict[str, np.ndarray], device: torch.device):
    q0 = np.asarray([0.11, -0.13, 0.0, -1.0], dtype=np.float64)
    jac = forward.transformed_jacobian_numpy(q0)
    active = jac[:, :2]
    singular = np.linalg.svd(active, compute_uv=False)
    condition = float(singular[0] / singular[-1])
    finite_difference = {}
    for coordinate, name in enumerate(("du", "dv")):
        errors = []
        for step in (1e-3, 5e-4, 2.5e-4):
            plus, minus = q0.copy(), q0.copy()
            plus[coordinate] += step
            minus[coordinate] -= step
            fd = (
                forward.transformed_numpy(plus) - forward.transformed_numpy(minus)
            ) / (2.0 * step)
            errors.append(float(np.linalg.norm(fd - jac[:, coordinate]) / np.linalg.norm(jac[:, coordinate])))
        finite_difference[name] = {"relative_l2_error_by_step": errors, "best_relative_l2_error": min(errors)}

    target = torch.as_tensor(arrays["clean"][0], dtype=torch.float64, device=device)
    predicted = torch.tensor([[0.12, -0.1]], dtype=torch.float64, device=device, requires_grad=True)
    def reconstruction_scalar(q):
        rendered = forward.transformed(compose_full_q(q))
        return torch.mean((rendered - target.unsqueeze(0)) ** 2)
    loss = reconstruction_scalar(predicted)
    loss.backward()
    autograd_gradient = predicted.grad.detach().cpu().numpy()[0]
    loss_fd = []
    for coordinate in range(2):
        plus = np.asarray([0.12, -0.1], dtype=np.float64)
        minus = plus.copy()
        plus[coordinate] += 1e-4
        minus[coordinate] -= 1e-4
        plus_tensor = torch.as_tensor(plus[None, :], dtype=torch.float64, device=device)
        minus_tensor = torch.as_tensor(minus[None, :], dtype=torch.float64, device=device)
        fd = float((reconstruction_scalar(plus_tensor) - reconstruction_scalar(minus_tensor)) / 2e-4)
        relative = abs(fd - autograd_gradient[coordinate]) / max(abs(fd), abs(autograd_gradient[coordinate]), 1e-12)
        loss_fd.append({"coordinate": ("du", "dv")[coordinate], "autograd": float(autograd_gradient[coordinate]), "finite_difference": fd, "relative_error": float(relative)})
    result = {
        "anchor_q": q0.tolist(),
        "active_parameters": ["du", "dv"],
        "jacobian_column_norms": np.linalg.norm(active, axis=0).tolist(),
        "jacobian_singular_values": singular.tolist(),
        "jacobian_condition_number": condition,
        "jacobian_full_rank": bool(singular[-1] > singular[0] * 1e-3),
        "jacobian_finite_difference": finite_difference,
        "end_to_end_reconstruction_loss": float(loss.detach().cpu()),
        "end_to_end_autograd_finite": bool(np.isfinite(autograd_gradient).all()),
        "end_to_end_loss_gradient_finite_difference": loss_fd,
    }
    passed = (
        result["jacobian_full_rank"]
        and condition < 100.0
        and all(entry["best_relative_l2_error"] < 0.01 for entry in finite_difference.values())
        and result["end_to_end_autograd_finite"]
        and all(entry["relative_error"] < 0.02 for entry in loss_fd)
    )
    result["passed"] = bool(passed)
    if not passed:
        raise RuntimeError(f"forward differentiability / identifiability gate failed: {result}")
    return result


def aggregate_metrics(evaluations: list[dict[str, Any]], metric_path: tuple[str, ...]):
    values = []
    for result in evaluations:
        value: Any = result
        for key in metric_path:
            value = value[key]
        values.append(float(value))
    return {"mean": float(np.mean(values)), "sd": float(np.std(values, ddof=1)), "seed_values": values}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("xrd_forward_loss/configs/pilot.json"))
    parser.add_argument("--output", type=Path, default=Path("xrd_forward_loss/reports/pilot_20261018"))
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()
    root = repository_root()
    config = read_json((root / args.config).resolve())
    output_dir = (root / args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not torch.cuda.is_available():
        raise RuntimeError("the differentiable forward gate requires CUDA in this pilot")
    device = torch.device(config["forward_model"]["device"])
    if device.type != "cuda":
        raise RuntimeError("configured device must be CUDA")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    arrays, metadata, structure, forward, forward_config = build_dataset(root, config)
    splits = {
        key.removesuffix("_indices"): value
        for key, value in arrays.items()
        if key.endswith("_indices")
    }
    # Keep only compact provenance in the committed artifact; data regenerate from this record.
    manifest = {
        **metadata,
        "config": config,
        "source_git_commit_at_run": git_commit(root),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(device),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pymatgen": pymatgen_version,
        "split_indices": {key: value.tolist() for key, value in splits.items()},
    }
    save_json(output_dir / "run_manifest.json", manifest)
    axis = forward.axis.detach().cpu().numpy()
    gate = audit_gradients(forward, arrays, device)
    save_json(output_dir / "forward_gate.json", gate)
    train_cfg = config["training"]
    smoke = {}
    for method, weight in (("A", 0.0), ("B", 1.0)):
        result = fit(
            arrays,
            splits,
            forward_model=forward,
            device=device,
            seed=20261030,
            epochs=1,
            learning_rate=float(train_cfg["learning_rate"]),
            batch_size=int(train_cfg["batch_size"]),
            reconstruction_weight=weight,
            gradient_clip_norm=float(train_cfg["gradient_clip_norm"]),
            max_train_samples=64,
        )
        smoke[method] = {
            "finite_training_loss": bool(np.isfinite([entry["train_total_loss"] for entry in result["history"]]).all()),
            "finite_validation_mae": bool(np.isfinite(result["best_validation_q_mae"])),
            "updates": result["updates"],
            "training_seconds": result["training_seconds"],
        }
    if not all(row["finite_training_loss"] and row["finite_validation_mae"] for row in smoke.values()):
        raise RuntimeError("A/B smoke test returned non-finite values")
    save_json(output_dir / "smoke.json", smoke)
    if args.smoke_only:
        print(json.dumps({"forward_gate": gate, "smoke": smoke}, indent=2))
        return

    lambda_runs = {}
    lambda_selection_seed = 20261031
    for weight in train_cfg["lambda_candidates"]:
        result = fit(
            arrays,
            splits,
            forward_model=forward,
            device=device,
            seed=lambda_selection_seed,
            epochs=int(train_cfg["lambda_selection_epochs"]),
            learning_rate=float(train_cfg["learning_rate"]),
            batch_size=int(train_cfg["batch_size"]),
            reconstruction_weight=float(weight),
            gradient_clip_norm=float(train_cfg["gradient_clip_norm"]),
        )
        lambda_runs[str(weight)] = {
            "best_validation_q_mae": result["best_validation_q_mae"],
            "best_epoch": result["best_epoch"],
            "training_seconds": result["training_seconds"],
            "history": result["history"],
        }
    selected_lambda = min(lambda_runs, key=lambda value: lambda_runs[value]["best_validation_q_mae"])
    save_json(output_dir / "lambda_selection.json", {
        "selection_rule": "minimum validation normalized-q MAE at the validation-best epoch; test fold not read",
        "seed": lambda_selection_seed,
        "candidate_results": lambda_runs,
        "selected_lambda": float(selected_lambda),
    })

    histories = {"A": [], "B": []}
    final_by_method: dict[str, list[dict[str, Any]]] = {"A": [], "B": []}
    costs: dict[str, list[dict[str, Any]]] = {"A": [], "B": []}
    for seed in train_cfg["seeds"]:
        for method, weight in (("A", 0.0), ("B", float(selected_lambda))):
            result = fit(
                arrays,
                splits,
                forward_model=forward,
                device=device,
                seed=int(seed),
                epochs=int(train_cfg["final_epochs"]),
                learning_rate=float(train_cfg["learning_rate"]),
                batch_size=int(train_cfg["batch_size"]),
                reconstruction_weight=weight,
                gradient_clip_norm=float(train_cfg["gradient_clip_norm"]),
            )
            histories[method].append({"seed": int(seed), "history": result["history"]})
            costs[method].append({
                "seed": int(seed),
                "training_seconds": result["training_seconds"],
                "training_seconds_per_epoch": result["training_seconds_per_epoch"],
                "updates": result["updates"],
                "peak_memory_allocated_mb": result["peak_memory_allocated_mb"],
                "best_epoch": result["best_epoch"],
                "best_validation_q_mae": result["best_validation_q_mae"],
            })
            final_by_method[method].append(
                evaluate_model(
                    result["model"],
                    arrays,
                    splits["test"],
                    forward_model=forward,
                    device=device,
                    a0=float(structure.lattice.a),
                    c0=float(structure.lattice.c),
                    du_half=float(forward_config["parameterization"]["du_half_range"]),
                    dv_half=float(forward_config["parameterization"]["dv_half_range"]),
                )
            )
    aggregated = {}
    for method, results in final_by_method.items():
        aggregated[method] = {
            "seed_results": [
                {
                    "seed": int(seed),
                    "parameter_mae_normalized": result["parameter_mae_normalized"],
                    "lattice_mae_angstrom": result["lattice_mae_angstrom"],
                    "reconstruction_rmse_transformed_clean": result["reconstruction_rmse_transformed_clean"],
                    "reconstruction_rmse_transformed_noisy": result["reconstruction_rmse_transformed_noisy"],
                }
                for seed, result in zip(train_cfg["seeds"], results)
            ],
            "summary": {
                "q_mae_mean_two_parameter": aggregate_metrics(results, ("parameter_mae_normalized", "mean_two_parameter")),
                "q_mae_du": aggregate_metrics(results, ("parameter_mae_normalized", "du")),
                "q_mae_dv": aggregate_metrics(results, ("parameter_mae_normalized", "dv")),
                "lattice_a_mae_angstrom": aggregate_metrics(results, ("lattice_mae_angstrom", "a")),
                "lattice_c_mae_angstrom": aggregate_metrics(results, ("lattice_mae_angstrom", "c")),
                "clean_spectral_rmse": aggregate_metrics(results, ("reconstruction_rmse_transformed_clean",)),
                "noisy_spectral_rmse": aggregate_metrics(results, ("reconstruction_rmse_transformed_noisy",)),
            },
        }
    seed_paired = []
    for index, seed in enumerate(train_cfg["seeds"]):
        a_row = final_by_method["A"][index]
        b_row = final_by_method["B"][index]
        seed_paired.append({
            "seed": int(seed),
            "b_minus_a_q_mae": b_row["parameter_mae_normalized"]["mean_two_parameter"] - a_row["parameter_mae_normalized"]["mean_two_parameter"],
            "b_minus_a_clean_rmse": b_row["reconstruction_rmse_transformed_clean"] - a_row["reconstruction_rmse_transformed_clean"],
        })
    metrics = {
        "status": "PRELIMINARY_PAIRED_AB_PILOT",
        "selected_lambda": float(selected_lambda),
        "lambda_candidates": [float(value) for value in train_cfg["lambda_candidates"]],
        "test_metrics": aggregated,
        "paired_seed_differences_b_minus_a": seed_paired,
        "costs": costs,
        "test_case_count_per_seed": int(len(splits["test"])),
        "interpretation_boundary": "single fixed HfCd parent, simulated patterns from the same forward renderer with independent Poisson/background measurement perturbation; method engineering only, not ferroelectric or experimental-domain evidence",
    }
    save_json(output_dir / "results.json", metrics)
    history_first = {
        method: histories[method][0]["history"] for method in ("A", "B")
    }
    failure_case = plot_results(
        output_dir,
        axis,
        arrays,
        splits["test"],
        {method: final_by_method[method][0] for method in ("A", "B")},
        history_first,
    )
    save_json(output_dir / "failure_case.json", failure_case)
    prediction_path = output_dir / "seed1_test_predictions.csv"
    with prediction_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["dataset_index", "target_du", "target_dv", "A_pred_du", "A_pred_dv", "B_pred_du", "B_pred_dv"])
        a_result, b_result = final_by_method["A"][0], final_by_method["B"][0]
        for row_index, dataset_index in enumerate(splits["test"]):
            target = a_result["target_q"][row_index]
            a_pred = a_result["prediction_q"][row_index]
            b_pred = b_result["prediction_q"][row_index]
            writer.writerow([int(dataset_index), *target, *a_pred, *b_pred])
    save_json(output_dir / "training_histories.json", histories)
    print(json.dumps({"gate": gate, "smoke": smoke, "selected_lambda": selected_lambda, "metrics": metrics, "failure_case": failure_case}, indent=2))


if __name__ == "__main__":
    main()
