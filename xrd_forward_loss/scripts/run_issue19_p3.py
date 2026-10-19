"""Run the bounded Issue #19 A/B smoke and formal BaTiO3 pilot."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F
from pymatgen.core import Structure

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
]
from pxrd_forward_loss.measurement_closure import (  # noqa: E402
    expected_intensity_profile,
    expected_profile,
    map_nuisance_logits,
)
from pxrd_forward_loss.measurement_sampling import (  # noqa: E402
    sample_q_bank,
    sample_v9_nuisance_bank,
    split_assignment,
    split_q_indices,
)
from pxrd_forward_loss.model import MeasurementAwareRegressor, ParameterRegressor  # noqa: E402
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward  # noqa: E402


LOG101 = math.log(101.0)
METHODS = ("A", "B")
CONDITIONS = {
    "simple": "simple_linear_counts",
    "v9": "v9_polynomial",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(json.dumps(list(value.shape)).encode("ascii"))
    digest.update(value.tobytes())
    return digest.hexdigest()


def make_forward(config: dict[str, Any]):
    forward_cfg = read_json(ROOT / config["forward"]["config"])
    structure = Structure.from_file(ROOT / config["source"]["cif"])
    forward = CachedTetragonalGPUForward(
        structure,
        grid_config=forward_cfg["grid"],
        parameter_config=forward_cfg["parameterization"],
        device="cuda",
        dtype=torch.float64,
    )
    return forward, forward_cfg, structure


def q_to_lattice(q: np.ndarray, structure: Structure, forward_cfg: dict[str, Any]):
    parameterization = forward_cfg["parameterization"]
    u0 = (2.0 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3.0
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    values = np.asarray(q, dtype=np.float64)
    u = u0 + values[..., 0] * float(parameterization["du_half_range"])
    v = v0 + values[..., 1] * float(parameterization["dv_half_range"])
    return np.exp(u - v / 3.0), np.exp(u + 2.0 * v / 3.0)


def _build_expected_arrays(
    q_values: np.ndarray,
    eta_values: np.ndarray,
    *,
    forward: Any,
    background_mode: str,
    batch_size: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    raw_rows: list[np.ndarray] = []
    expected_rows: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(q_values), batch_size):
            q = torch.as_tensor(
                q_values[start : start + batch_size], device="cuda", dtype=torch.float64
            )
            eta = torch.as_tensor(
                eta_values[start : start + batch_size], device="cuda", dtype=torch.float64
            )
            raw = expected_intensity_profile(
                forward, q, eta, background_shape_mode=background_mode
            )
            profile = expected_profile(
                forward, q, eta, background_shape_mode=background_mode
            )
            raw_rows.append(raw.cpu().numpy())
            expected_rows.append(profile.cpu().numpy())
    return np.concatenate(raw_rows), np.concatenate(expected_rows)


def _draw_observations(
    expected_intensity: np.ndarray,
    *,
    condition: str,
    seed: int,
    noise_config: dict[str, Any],
) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    count_scale = float(noise_config["poisson_count_scale"])
    expected_counts = np.maximum(expected_intensity, 0.0) * count_scale
    counts = rng.poisson(expected_counts).astype(np.float64)
    if condition == "v9":
        sigma = rng.uniform(
            float(noise_config["electronic_noise_std_counts"][0]),
            float(noise_config["electronic_noise_std_counts"][1]),
            size=(len(expected_intensity), 1),
        )
        counts += rng.normal(0.0, sigma, size=counts.shape)
    counts = np.clip(counts, 0.0, None)
    intensity = counts / count_scale
    maxima = np.maximum(np.max(intensity, axis=1, keepdims=True), 1.0 / count_scale)
    normalized = intensity / maxima
    return (np.log1p(100.0 * normalized) / LOG101).astype(np.float32)


def build_data(
    *,
    config: dict[str, Any],
    forward: Any,
    count: int,
    sobol_seed: int,
    split_seed: int,
    nuisance_seed: int,
    noise_seed: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    data_cfg = config["data"]
    q_bound = float(config["forward"]["q_bounds"][1])
    q_values = sample_q_bank(count, seed=sobol_seed, q_bound=q_bound)
    splits = split_q_indices(
        count,
        seed=split_seed,
        train_fraction=float(data_cfg["split_fractions"]["train"]),
        validation_fraction=float(data_cfg["split_fractions"]["validation"]),
    )
    assignments = split_assignment(splits, count)

    # Split assignment is frozen above before either measurement nuisance or
    # detector-noise stream is sampled.
    simple_cfg = data_cfg["simple_view"]
    simple_eta = np.tile(
        np.asarray(
            [
                float(simple_cfg["zero_shift_deg"][0]),
                float(simple_cfg["fwhm_deg"][0]),
                float(simple_cfg["background_counts"][1])
                / float(simple_cfg["poisson_count_scale"]),
            ],
            dtype=np.float64,
        ),
        (count, 1),
    )
    v9_cfg = data_cfg["v9_view"]
    v9_eta = sample_v9_nuisance_bank(count, seed=nuisance_seed)

    simple_raw, simple_expected = _build_expected_arrays(
        q_values,
        simple_eta,
        forward=forward,
        background_mode=str(simple_cfg["background_shape_mode"]),
    )
    v9_raw, v9_expected = _build_expected_arrays(
        q_values,
        v9_eta,
        forward=forward,
        background_mode=str(v9_cfg["background_shape_mode"]),
    )
    simple_observed = _draw_observations(
        simple_raw,
        condition="simple",
        seed=noise_seed,
        noise_config=simple_cfg,
    )
    v9_observed = _draw_observations(
        v9_raw,
        condition="v9",
        seed=noise_seed + 1,
        noise_config=v9_cfg,
    )
    clean_eta = np.tile(np.asarray([0.0, 0.08, 0.0], dtype=np.float64), (count, 1))
    _, clean = _build_expected_arrays(
        q_values,
        clean_eta,
        forward=forward,
        background_mode="v9_polynomial",
    )

    arrays: dict[str, np.ndarray] = {
        "q": q_values.astype(np.float64),
        "simple_observed": simple_observed,
        "simple_expected": simple_expected.astype(np.float32),
        "simple_eta_true": simple_eta,
        "v9_observed": v9_observed,
        "v9_expected": v9_expected.astype(np.float32),
        "v9_eta_true": v9_eta,
        "clean_profile": clean.astype(np.float32),
        **{f"{key}_indices": value.astype(np.int64) for key, value in splits.items()},
    }
    array_hashes = {key: sha256_array(value) for key, value in arrays.items()}
    metadata = {
        "sample_count": int(count),
        "q_bounds": [-q_bound, q_bound],
        "sobol_seed": int(sobol_seed),
        "split_seed": int(split_seed),
        "nuisance_seed": int(nuisance_seed),
        "simple_noise_seed": int(noise_seed),
        "v9_noise_seed": int(noise_seed + 1),
        "split_counts": {key: int(len(value)) for key, value in splits.items()},
        "split_assignment": assignments,
        "split_before_measurement_draws": True,
        "measurement_truth_storage": "eta_true is kept in a separate diagnostic-only array and excluded from all train/validation/test model inputs and losses",
        "observed_generation": {
            "simple": "fixed zero shift and 0.08 degree FWHM; linear 100-to-200 count background; Poisson counts; per-pattern max normalization; log1p_100",
            "v9": "independent uniform zero shift, 0.11-to-0.13 degree FWHM and 0.005-to-0.008 background; fixed V9 quadratic shape; Poisson counts plus 0.5-to-1.5 count Gaussian readout; per-pattern max normalization; log1p_100",
            "preferred_orientation": False,
        },
        "array_sha256": array_hashes,
    }
    return arrays, metadata


def _tensor_data(arrays: dict[str, np.ndarray], condition: str, device: torch.device):
    # Deliberately excludes both nuisance-truth arrays and expected-profile
    # arrays; only observed inputs and q supervision enter optimization.
    return (
        torch.as_tensor(arrays[f"{condition}_observed"], device=device, dtype=torch.float32),
        torch.as_tensor(arrays["q"], device=device, dtype=torch.float32),
    )


def _validation_mae(model: torch.nn.Module, x: torch.Tensor, q: torch.Tensor, indices: np.ndarray) -> float:
    index = torch.as_tensor(indices, device=x.device, dtype=torch.long)
    model.eval()
    with torch.no_grad():
        prediction = model(x.index_select(0, index))
        pred_q = prediction[0] if isinstance(prediction, tuple) else prediction
        return float(torch.mean(torch.abs(pred_q - q.index_select(0, index))).cpu())


def _torch_load(path: Path, device: torch.device) -> dict[str, Any]:
    return torch.load(path, map_location=device, weights_only=False)


def fit_model(
    *,
    method: str,
    condition: str,
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    forward: Any,
    config: dict[str, Any],
    seed: int,
    reconstruction_weight: float,
    total_epochs: int,
    output_checkpoint: Path,
    resume_checkpoint: Path | None = None,
    prior_validation_best: float = float("inf"),
    prior_best_epoch: int = 0,
    prior_history: list[dict[str, float]] | None = None,
    smoke_gradient_check: bool = False,
) -> dict[str, Any]:
    device = torch.device("cuda")
    training_cfg = config["training"]
    batch_size = int(training_cfg["batch_size"])
    torch.manual_seed(int(seed))
    torch.cuda.manual_seed_all(int(seed))
    np.random.seed(int(seed))
    torch.cuda.reset_peak_memory_stats(device)
    x, q = _tensor_data(arrays, condition, device)
    model = (
        ParameterRegressor(input_length=x.shape[1])
        if method == "A"
        else MeasurementAwareRegressor(input_length=x.shape[1])
    ).to(device)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(training_cfg["learning_rate"]),
        weight_decay=float(training_cfg["weight_decay"]),
    )
    first_epoch = 1
    best_validation = float(prior_validation_best)
    best_epoch = int(prior_best_epoch)
    history = list(prior_history or [])
    best_state: dict[str, torch.Tensor] | None = None
    generator = torch.Generator(device=device)
    generator.manual_seed(int(seed) + 1000)
    if resume_checkpoint is not None:
        checkpoint = _torch_load(resume_checkpoint, device)
        model.load_state_dict(checkpoint["last_model_state"])
        optimizer.load_state_dict(checkpoint["optimizer_state"])
        best_state = checkpoint["best_model_state"]
        first_epoch = int(checkpoint["completed_epochs"]) + 1
        best_validation = float(checkpoint["best_validation_q_mae"])
        best_epoch = int(checkpoint["best_epoch"])
        history = list(checkpoint["history"])
        # Checkpoints are loaded onto the training device for model and optimizer
        # state. Torch's Generator.set_state requires a CPU ByteTensor even when
        # the generator itself targets CUDA.
        generator.set_state(checkpoint["shuffle_generator_state"].cpu())

    train_idx = torch.as_tensor(splits["train"], device=device, dtype=torch.long)
    max_grad = float(training_cfg["gradient_clip_norm"])
    started = time.perf_counter()
    reconstruction_gradient = None
    for epoch in range(first_epoch, total_epochs + 1):
        model.train()
        order = train_idx[torch.randperm(len(train_idx), generator=generator, device=device)]
        sums = {"total": 0.0, "parameter": 0.0, "reconstruction": 0.0}
        batch_count = 0
        for start in range(0, len(order), batch_size):
            batch = order[start : start + batch_size]
            observed = x.index_select(0, batch)
            target_q = q.index_select(0, batch)
            optimizer.zero_grad(set_to_none=True)
            output = model(observed)
            if method == "A":
                predicted_q = output
                parameter_loss = F.mse_loss(predicted_q, target_q)
                reconstruction_loss = parameter_loss.new_zeros(())
                total_loss = parameter_loss
            else:
                predicted_q, predicted_eta = output
                expected = expected_profile(
                    forward,
                    predicted_q.to(dtype=torch.float64),
                    predicted_eta.to(dtype=torch.float64),
                    background_shape_mode=CONDITIONS[condition],
                )
                reconstruction_loss = F.mse_loss(
                    expected.to(dtype=observed.dtype), observed
                )
                parameter_loss = F.mse_loss(predicted_q, target_q)
                total_loss = parameter_loss + float(reconstruction_weight) * reconstruction_loss
                if smoke_gradient_check and reconstruction_gradient is None:
                    grad_q, grad_eta = torch.autograd.grad(
                        reconstruction_loss,
                        (predicted_q, predicted_eta),
                        retain_graph=True,
                    )
                    reconstruction_gradient = {
                        "q_l2": float(torch.linalg.vector_norm(grad_q).detach().cpu()),
                        "eta_l2": float(torch.linalg.vector_norm(grad_eta).detach().cpu()),
                        "q_finite": bool(torch.isfinite(grad_q).all().item()),
                        "eta_finite": bool(torch.isfinite(grad_eta).all().item()),
                    }
            if not torch.isfinite(total_loss):
                raise FloatingPointError(f"non-finite {method} loss at epoch {epoch}")
            total_loss.backward()
            parameters = [parameter for parameter in model.parameters() if parameter.grad is not None]
            if not parameters or not all(torch.isfinite(parameter.grad).all() for parameter in parameters):
                raise FloatingPointError(f"non-finite {method} model gradient at epoch {epoch}")
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad)
            optimizer.step()
            sums["total"] += float(total_loss.detach().cpu())
            sums["parameter"] += float(parameter_loss.detach().cpu())
            sums["reconstruction"] += float(reconstruction_loss.detach().cpu())
            batch_count += 1

        validation = _validation_mae(model, x, q, splits["validation"])
        history.append(
            {
                "epoch": float(epoch),
                "train_total_loss": sums["total"] / max(batch_count, 1),
                "train_parameter_mse": sums["parameter"] / max(batch_count, 1),
                "train_reconstruction_mse": sums["reconstruction"] / max(batch_count, 1),
                "validation_q_mae": validation,
            }
        )
        if validation < best_validation:
            best_validation = validation
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())

    if best_state is None:
        best_state = copy.deepcopy(model.state_dict())
        best_validation = _validation_mae(model, x, q, splits["validation"])
        best_epoch = total_epochs
    elapsed = time.perf_counter() - started
    checkpoint = {
        "method": method,
        "condition": condition,
        "seed": int(seed),
        "lambda": float(reconstruction_weight),
        "completed_epochs": int(total_epochs),
        "best_epoch": int(best_epoch),
        "best_validation_q_mae": float(best_validation),
        "last_model_state": model.state_dict(),
        "best_model_state": best_state,
        "optimizer_state": optimizer.state_dict(),
        "shuffle_generator_state": generator.get_state(),
        "history": history,
        "elapsed_seconds_this_segment": elapsed,
        "peak_memory_allocated_mb": float(torch.cuda.max_memory_allocated(device) / (1024**2)),
        "parameter_count": int(sum(parameter.numel() for parameter in model.parameters())),
        "reconstruction_gradient": reconstruction_gradient,
    }
    output_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, output_checkpoint)
    model.load_state_dict(best_state)
    return {
        "checkpoint": output_checkpoint,
        "history": history,
        "best_validation_q_mae": float(best_validation),
        "best_epoch": int(best_epoch),
        "elapsed_seconds": elapsed,
        "peak_memory_allocated_mb": checkpoint["peak_memory_allocated_mb"],
        "parameter_count": checkpoint["parameter_count"],
        "updates_in_segment": max(0, total_epochs - first_epoch + 1)
        * int(math.ceil(len(train_idx) / batch_size)),
        "reconstruction_gradient": reconstruction_gradient,
    }


def save_final_checkpoint(source: Path, destination: Path) -> dict[str, Any]:
    checkpoint = torch.load(source, map_location="cpu", weights_only=False)
    final = {
        key: checkpoint[key]
        for key in (
            "method",
            "condition",
            "seed",
            "lambda",
            "completed_epochs",
            "best_epoch",
            "best_validation_q_mae",
            "best_model_state",
            "history",
            "elapsed_seconds_this_segment",
            "peak_memory_allocated_mb",
            "parameter_count",
            "reconstruction_gradient",
        )
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save(final, destination)
    return final


def load_best_model(checkpoint_path: Path, method: str, input_length: int) -> torch.nn.Module:
    checkpoint = torch.load(checkpoint_path, map_location="cuda", weights_only=False)
    model = (
        ParameterRegressor(input_length=input_length)
        if method == "A"
        else MeasurementAwareRegressor(input_length=input_length)
    ).to("cuda")
    model.load_state_dict(checkpoint["best_model_state"])
    model.eval()
    return model


def _predict(model: torch.nn.Module, profiles: np.ndarray, batch_size: int = 16):
    q_rows: list[np.ndarray] = []
    eta_rows: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(profiles), batch_size):
            x = torch.as_tensor(
                profiles[start : start + batch_size], device="cuda", dtype=torch.float32
            )
            output = model(x)
            if isinstance(output, tuple):
                q, eta = output
                eta_rows.append(eta.cpu().numpy().astype(np.float64))
            else:
                q = output
            q_rows.append(q.cpu().numpy().astype(np.float64))
    q_all = np.concatenate(q_rows)
    eta_all = np.concatenate(eta_rows) if eta_rows else None
    return q_all, eta_all


def _eta_from_scaled(z: np.ndarray) -> np.ndarray:
    return np.asarray(
        [0.06 * z[0], 0.08 + 0.05 * (z[1] + 1.0) / 2.0, 0.01 * (z[2] + 1.0) / 2.0],
        dtype=np.float64,
    )


def profile_fit_eta(
    forward: Any,
    q_value: np.ndarray,
    observed: np.ndarray,
    *,
    background_mode: str,
    maxiter: int = 80,
) -> dict[str, Any]:
    """Bounded non-oracle eta estimate with q fixed to the method prediction."""
    q_tensor = torch.as_tensor(q_value[None, :], device="cuda", dtype=torch.float64)
    target = torch.as_tensor(observed[None, :], device="cuda", dtype=torch.float32)

    def objective(z: np.ndarray):
        eta = torch.as_tensor(_eta_from_scaled(z)[None, :], device="cuda", dtype=torch.float64)
        eta.requires_grad_(True)
        expected = expected_profile(
            forward, q_tensor, eta, background_shape_mode=background_mode
        ).to(dtype=torch.float32)
        loss = F.mse_loss(expected, target)
        grad = torch.autograd.grad(loss, eta)[0][0]
        scaled_grad = np.asarray(
            [
                float(grad[0].cpu()) * 0.06,
                float(grad[1].cpu()) * 0.025,
                float(grad[2].cpu()) * 0.005,
            ],
            dtype=np.float64,
        )
        return float(loss.detach().cpu()), scaled_grad

    result = scipy.optimize.minimize(
        objective,
        np.asarray([0.0, 0.0, 0.0], dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        bounds=[(-0.999, 0.999)] * 3,
        options={"maxiter": maxiter, "ftol": 1e-10, "gtol": 1e-7, "maxls": 25},
    )
    return {
        "eta": _eta_from_scaled(result.x).tolist(),
        "scaled_z": result.x.tolist(),
        "loss": float(result.fun),
        "success": bool(result.success),
        "iterations": int(result.nit),
        "at_bound": bool(np.any(np.isclose(np.abs(result.x), 0.999, atol=1e-5))),
    }


def eta_to_scaled(eta: np.ndarray) -> np.ndarray:
    values = np.asarray(eta, dtype=np.float64)
    return np.stack(
        (
            values[..., 0] / 0.06,
            2.0 * (values[..., 1] - 0.08) / 0.05 - 1.0,
            2.0 * values[..., 2] / 0.01 - 1.0,
        ),
        axis=-1,
    )


def evaluate_method(
    *,
    method: str,
    condition: str,
    model: torch.nn.Module,
    arrays: dict[str, np.ndarray],
    test_indices: np.ndarray,
    forward: Any,
    structure: Structure,
    forward_cfg: dict[str, Any],
) -> dict[str, Any]:
    observed_all = arrays[f"{condition}_observed"]
    q_prediction, eta_prediction = _predict(model, observed_all[test_indices])
    q_true = arrays["q"][test_indices]
    eta_true = arrays[f"{condition}_eta_true"][test_indices]
    observed = observed_all[test_indices]
    clean_reference = arrays["clean_profile"][test_indices]
    q_error = np.abs(q_prediction - q_true)
    a_true, c_true = q_to_lattice(q_true, structure, forward_cfg)
    a_pred, c_pred = q_to_lattice(q_prediction, structure, forward_cfg)

    if method == "B":
        assert eta_prediction is not None
        eta_for_reconstruction = eta_prediction
    else:
        eta_fits = [
            profile_fit_eta(
                forward,
                q_value,
                profile,
                background_mode=CONDITIONS[condition],
            )
            for q_value, profile in zip(q_prediction, observed, strict=True)
        ]
        eta_for_reconstruction = np.asarray([row["eta"] for row in eta_fits], dtype=np.float64)

    predicted_expected: list[np.ndarray] = []
    predicted_clean: list[np.ndarray] = []
    for start in range(0, len(q_prediction), 8):
        q_batch = torch.as_tensor(q_prediction[start : start + 8], device="cuda", dtype=torch.float64)
        eta_batch = torch.as_tensor(
            eta_for_reconstruction[start : start + 8], device="cuda", dtype=torch.float64
        )
        with torch.no_grad():
            expected = expected_profile(
                forward,
                q_batch,
                eta_batch,
                background_shape_mode=CONDITIONS[condition],
            )
            clean_eta = torch.as_tensor(
                np.tile([0.0, 0.08, 0.0], (len(q_batch), 1)),
                device="cuda",
                dtype=torch.float64,
            )
            clean = expected_profile(forward, q_batch, clean_eta)
        predicted_expected.append(expected.cpu().numpy())
        predicted_clean.append(clean.cpu().numpy())
    expected_profiles = np.concatenate(predicted_expected)
    clean_profiles = np.concatenate(predicted_clean)
    observed_rmse = float(np.sqrt(np.mean((expected_profiles - observed) ** 2)))
    clean_rmse = float(np.sqrt(np.mean((clean_profiles - clean_reference) ** 2)))

    result: dict[str, Any] = {
        "method": method,
        "condition": condition,
        "test_count": int(len(test_indices)),
        "parameter_mae_normalized_q": {
            "du": float(q_error[:, 0].mean()),
            "dv": float(q_error[:, 1].mean()),
            "mean_two_coordinate": float(q_error.mean()),
        },
        "lattice_mae_angstrom": {
            "a": float(np.mean(np.abs(a_pred - a_true))),
            "c": float(np.mean(np.abs(c_pred - c_true))),
        },
        "observed_expected_profile_rmse_transformed": observed_rmse,
        "clean_reference_residual_rmse_transformed_auxiliary": clean_rmse,
        "prediction_q": q_prediction.tolist(),
        "target_q_for_scoring_only": q_true.tolist(),
        "prediction_eta_used_for_observed_reconstruction": eta_for_reconstruction.tolist(),
        "eta_true_used_for_diagnostic_comparison_only": eta_true.tolist(),
        "predicted_expected_profiles": expected_profiles.tolist(),
        "clean_reconstructed_profiles": clean_profiles.tolist(),
        "observed_profiles": observed.tolist(),
        "clean_reference_profiles": clean_reference.tolist(),
    }
    if eta_prediction is not None:
        scaled_error = np.abs(eta_to_scaled(eta_prediction) - eta_to_scaled(eta_true))
        worst = np.argsort(np.mean(scaled_error, axis=1))[::-1][: min(5, len(scaled_error))]
        result["nuisance_error_diagnostic_only"] = {
            "scaled_coordinate_mae": np.mean(scaled_error, axis=0).tolist(),
            "mean_scaled_coordinate_mae": float(np.mean(scaled_error)),
            "largest_error_examples": [
                {
                    "global_index": int(test_indices[index]),
                    "eta_pred": eta_prediction[index].tolist(),
                    "eta_true_diagnostic_only": eta_true[index].tolist(),
                    "scaled_absolute_error": scaled_error[index].tolist(),
                }
                for index in worst
            ],
        }
    else:
        fit_errors = np.abs(eta_to_scaled(eta_for_reconstruction) - eta_to_scaled(eta_true))
        result["profile_fit_nuisance_diagnostic_only"] = {
            "scaled_coordinate_mae": np.mean(fit_errors, axis=0).tolist(),
            "mean_scaled_coordinate_mae": float(np.mean(fit_errors)),
            "fit_success_count": int(sum(row["success"] for row in eta_fits)),
            "fit_iterations_mean": float(np.mean([row["iterations"] for row in eta_fits])),
            "fit_at_bound_count": int(sum(row["at_bound"] for row in eta_fits)),
            "per_sample_fit": eta_fits,
        }
    return result


def _aggregate(values: list[float]) -> dict[str, float]:
    return {
        "mean": float(np.mean(values)),
        "sd_sample": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "values": [float(value) for value in values],
    }


def save_plots(
    output_dir: Path,
    results: dict[str, Any],
    histories: dict[str, list[dict[str, float]]],
    axis: np.ndarray,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    colors = {"A": "#2878B5", "B": "#D9534F"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.2))
    for condition in CONDITIONS:
        for method in METHODS:
            key = f"{condition}_{method}"
            history = histories[key]
            label = f"{condition} {method}"
            axes[0, 0].plot(
                [row["epoch"] for row in history],
                [row["train_parameter_mse"] for row in history],
                color=colors[method],
                alpha=0.65 if condition == "simple" else 1.0,
                linestyle="-" if condition == "simple" else "--",
                label=label,
            )
            axes[0, 1].plot(
                [row["epoch"] for row in history],
                [row["validation_q_mae"] for row in history],
                color=colors[method],
                alpha=0.65 if condition == "simple" else 1.0,
                linestyle="-" if condition == "simple" else "--",
                label=label,
            )
    axes[0, 0].set(title="Training parameter loss", xlabel="Epoch", ylabel="MSE on q")
    axes[0, 1].set(title="Validation q MAE", xlabel="Epoch", ylabel="Mean absolute error")
    labels = []
    means = []
    errors = []
    for condition in CONDITIONS:
        for method in METHODS:
            aggregate = results["aggregate"][condition][method]["parameter_mae_normalized_q"]["mean_two_coordinate"]
            labels.append(f"{condition}\n{method}")
            means.append(aggregate["mean"])
            errors.append(aggregate["sd_sample"])
    axes[1, 0].bar(labels, means, yerr=errors, color=[colors[label.split("\n")[1]] for label in labels], alpha=0.85)
    axes[1, 0].set(title="Test normalized-q MAE", ylabel="Mean over seeds")
    axes[1, 0].grid(axis="y", alpha=0.25)

    condition = "v9"
    method = "B"
    seed_key = sorted(results["per_seed"][condition][method])[0]
    first = results["per_seed"][condition][method][seed_key]
    case_index = int(np.argmax(np.mean(np.abs(np.asarray(first["prediction_q"]) - np.asarray(first["target_q_for_scoring_only"])), axis=1)))
    axes[1, 1].plot(axis, np.asarray(first["observed_profiles"])[case_index], color="#555555", label="V9 observed")
    axes[1, 1].plot(axis, np.asarray(first["predicted_expected_profiles"])[case_index], color=colors["B"], label="B expected profile")
    axes[1, 1].set(title="V9 test example", xlabel="2θ (degrees)", ylabel="Transformed intensity")
    axes[1, 1].grid(alpha=0.2)
    axes[1, 1].legend(fontsize=8)
    axes[0, 0].legend(fontsize=7, ncol=2)
    axes[0, 1].legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "p3_training_and_test_summary.png", dpi=180)
    plt.close(fig)


def smoke_stage(
    *,
    output_root: Path,
    config: dict[str, Any],
    config_path: Path,
    p1_report_path: Path,
    forward: Any,
) -> dict[str, Any]:
    p1 = read_json(p1_report_path)
    if not p1.get("passed"):
        raise RuntimeError("P1/P2 physical and unknown-nuisance Gates failed; P3 is blocked")
    if output_root.exists():
        raise FileExistsError(f"P3 output root already exists: {output_root}")
    output_root.mkdir(parents=True)
    smoke_dir = output_root / "smoke"
    smoke_dir.mkdir()
    data_cfg = config["data"]
    arrays, data_manifest = build_data(
        config=config,
        forward=forward,
        count=int(config["training"]["smoke_samples"]),
        sobol_seed=int(data_cfg["smoke_sobol_seed"]),
        split_seed=int(data_cfg["smoke_split_seed"]),
        nuisance_seed=int(data_cfg["nuisance_seed"]) + 20,
        noise_seed=int(data_cfg["nuisance_seed"]) + 30,
    )
    np.savez_compressed(smoke_dir / "smoke_data.npz", **arrays)
    write_json(smoke_dir / "data_manifest.json", data_manifest)

    started = time.perf_counter()
    smoke_rows = []
    histories = {}
    seed = int(config["training"]["seeds"][0])
    for condition in CONDITIONS:
        for method in METHODS:
            run_id = f"{condition}_{method}"
            result = fit_model(
                method=method,
                condition=condition,
                arrays=arrays,
                splits={
                    "train": arrays["train_indices"],
                    "validation": arrays["validation_indices"],
                    "test": arrays["test_indices"],
                },
                forward=forward,
                config=config,
                seed=seed,
                reconstruction_weight=1.0 if method == "B" else 0.0,
                total_epochs=int(config["training"]["smoke_max_epochs"]),
                output_checkpoint=smoke_dir / "checkpoints" / f"{run_id}.pt",
                smoke_gradient_check=(method == "B"),
            )
            checkpoint = torch.load(result["checkpoint"], map_location="cpu", weights_only=False)
            histories[run_id] = result["history"]
            smoke_rows.append(
                {
                    "condition": condition,
                    "method": method,
                    "seed": seed,
                    "epochs": int(config["training"]["smoke_max_epochs"]),
                    "best_validation_q_mae": result["best_validation_q_mae"],
                    "elapsed_seconds": result["elapsed_seconds"],
                    "peak_memory_allocated_mb": result["peak_memory_allocated_mb"],
                    "parameter_count": result["parameter_count"],
                    "final_total_loss_finite": bool(
                        np.isfinite([row["train_total_loss"] for row in result["history"]]).all()
                    ),
                    "reconstruction_gradient": checkpoint["reconstruction_gradient"],
                    "checkpoint": str(result["checkpoint"].relative_to(output_root)),
                }
            )
    elapsed = time.perf_counter() - started
    gate = all(row["final_total_loss_finite"] for row in smoke_rows)
    b_rows = [row for row in smoke_rows if row["method"] == "B"]
    for row in b_rows:
        gradients = row["reconstruction_gradient"]
        gate = gate and bool(
            gradients
            and gradients["q_finite"]
            and gradients["eta_finite"]
            and gradients["q_l2"] > 0.0
            and gradients["eta_l2"] > 0.0
        )
    report = {
        "stage": "P3_NN_SMOKE",
        "status": "PASS" if gate else "BLOCKED_SMOKE",
        "source_config": str(config_path.resolve().relative_to(ROOT)),
        "source_config_sha256": sha256_file(config_path),
        "p1_report": str(p1_report_path.resolve().relative_to(ROOT)),
        "q_count": int(config["training"]["smoke_samples"]),
        "one_seed": seed,
        "maximum_epochs": int(config["training"]["smoke_max_epochs"]),
        "conditions": list(CONDITIONS),
        "runs": smoke_rows,
        "training_wallclock_seconds": elapsed,
        "gate_passed": bool(gate),
        "known_label_leakage": False,
        "eta_true_accessed_by_training_path": False,
        "data_generation_seconds_excluded_from_training_budget": True,
    }
    write_json(smoke_dir / "smoke_report.json", report)
    histories_path = smoke_dir / "training_history.json"
    write_json(histories_path, histories)
    if not gate:
        write_json(
            output_root / "gate_report.json",
            {"status": "BLOCKED_SMOKE", "p1_report": p1, "smoke": report},
        )
        raise RuntimeError("P3 smoke Gate failed; formal A/B training was not run")
    write_json(
        output_root / "gate_report.json",
        {
            "status": "P3_SMOKE_PASS_FORMAL_PENDING",
            "p1_p2_passed": bool(p1.get("passed")),
            "smoke_passed": True,
            "smoke_report": str((smoke_dir / "smoke_report.json").relative_to(output_root)),
        },
    )
    return report


def formal_stage(
    *,
    output_root: Path,
    config: dict[str, Any],
    config_path: Path,
    p1_report_path: Path,
    forward: Any,
    forward_cfg: dict[str, Any],
    structure: Structure,
    prior_training_seconds: float = 0.0,
) -> dict[str, Any]:
    smoke_path = output_root / "smoke" / "smoke_report.json"
    if not smoke_path.exists():
        raise FileNotFoundError("formal training requires a completed P3 smoke report")
    smoke = read_json(smoke_path)
    if smoke.get("status") != "PASS":
        raise RuntimeError("P3 smoke failed; formal A/B training is blocked")
    p1 = read_json(p1_report_path)
    if not p1.get("passed"):
        raise RuntimeError("P1/P2 physical and unknown-nuisance Gates failed; P3 is blocked")
    formal_dir = output_root / "formal"
    if formal_dir.exists():
        raise FileExistsError(f"formal result directory already exists: {formal_dir}")
    formal_dir.mkdir(parents=True)
    training_cfg = config["training"]
    data_cfg = config["data"]
    arrays, data_manifest = build_data(
        config=config,
        forward=forward,
        count=int(config["data"]["q_count_max"]),
        sobol_seed=int(data_cfg["sobol_seed"]),
        split_seed=int(data_cfg["split_seed"]),
        nuisance_seed=int(data_cfg["nuisance_seed"]),
        noise_seed=int(data_cfg["nuisance_seed"]) + 10,
    )
    data_path = formal_dir / "formal_data.npz"
    np.savez_compressed(data_path, **arrays)
    write_json(formal_dir / "data_manifest.json", data_manifest)
    split_payload = {
        "train": arrays["train_indices"].tolist(),
        "validation": arrays["validation_indices"].tolist(),
        "test": arrays["test_indices"].tolist(),
        "counts": data_manifest["split_counts"],
        "q_split_seed": int(data_cfg["split_seed"]),
        "q_sample_seed": int(data_cfg["sobol_seed"]),
        "split_created_before_nuisance_and_noise_draws": True,
    }
    write_json(formal_dir / "split_indices.json", split_payload)

    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    environment = {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda_runtime": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "numpy": np.__version__,
        "scipy": importlib.metadata.version("scipy"),
        "pymatgen": importlib.metadata.version("pymatgen"),
        "source_commit_before_training": source_commit,
    }
    write_json(formal_dir / "environment.json", environment)
    write_json(
        formal_dir / "config_manifest.json",
        {
            "path": str(config_path.resolve().relative_to(ROOT)),
            "sha256": sha256_file(config_path),
            "full_config": config,
            "data_sha256": sha256_file(data_path),
        },
    )

    checkpoint_dir = formal_dir / "checkpoints"
    candidate_dir = checkpoint_dir / "lambda_candidates"
    final_dir = checkpoint_dir / "selected_final"
    candidate_dir.mkdir(parents=True)
    final_dir.mkdir(parents=True)
    lambda_candidates = [float(value) for value in training_cfg["validation_lambda_candidates"]]
    if len(lambda_candidates) != 2:
        raise ValueError("Issue #19 registers exactly two candidate lambdas")
    seeds = [int(value) for value in training_cfg["seeds"]]
    candidate_rows: dict[str, list[dict[str, Any]]] = {condition: [] for condition in CONDITIONS}
    run_costs: list[dict[str, Any]] = []
    histories: dict[str, list[dict[str, float]]] = {}
    training_started = time.perf_counter()
    prior_smoke_seconds = float(smoke["training_wallclock_seconds"])
    prior_training_seconds = float(prior_training_seconds)
    budget_seconds = float(training_cfg["wallclock_budget_hours"]) * 3600.0

    def assert_budget():
        elapsed = (
            prior_smoke_seconds
            + prior_training_seconds
            + (time.perf_counter() - training_started)
        )
        if elapsed > budget_seconds:
            partial = {
                "status": "BLOCKED_BUDGET",
                "training_plus_smoke_wallclock_seconds": elapsed,
                "hard_budget_seconds": budget_seconds,
                "completed_run_costs": run_costs,
                "candidate_results": candidate_rows,
            }
            write_json(formal_dir / "partial_training_status.json", partial)
            raise RuntimeError("two-hour cumulative training budget was reached")

    # A is trained once per condition and paired seed.
    for condition in CONDITIONS:
        for seed in seeds:
            assert_budget()
            path = final_dir / f"{condition}_A_seed{seed}.pt"
            fit = fit_model(
                method="A",
                condition=condition,
                arrays=arrays,
                splits={
                    "train": arrays["train_indices"],
                    "validation": arrays["validation_indices"],
                    "test": arrays["test_indices"],
                },
                forward=forward,
                config=config,
                seed=seed,
                reconstruction_weight=0.0,
                total_epochs=int(training_cfg["max_epochs"]),
                output_checkpoint=path,
            )
            histories[f"{condition}_A_seed{seed}"] = fit["history"]
            run_costs.append(
                {
                    "condition": condition,
                    "method": "A",
                    "seed": seed,
                    "lambda": 0.0,
                    "epochs": int(training_cfg["max_epochs"]),
                    "elapsed_seconds": fit["elapsed_seconds"],
                    "peak_memory_allocated_mb": fit["peak_memory_allocated_mb"],
                    "updates": fit["updates_in_segment"],
                    "checkpoint": str(path.relative_to(output_root)),
                }
            )
            assert_budget()

    # Compare the two registered lambdas on validation only. Each candidate
    # gets the same four-epoch warm-up per seed; selected runs continue to 24.
    warmup_epochs = min(4, int(training_cfg["max_epochs"]))
    candidate_checkpoints: dict[tuple[str, int, float], Path] = {}
    for condition in CONDITIONS:
        for seed in seeds:
            for weight in lambda_candidates:
                assert_budget()
                path = candidate_dir / f"{condition}_B_lambda{weight:g}_seed{seed}.pt"
                fit = fit_model(
                    method="B",
                    condition=condition,
                    arrays=arrays,
                    splits={
                        "train": arrays["train_indices"],
                        "validation": arrays["validation_indices"],
                        "test": arrays["test_indices"],
                    },
                    forward=forward,
                    config=config,
                    seed=seed,
                    reconstruction_weight=weight,
                    total_epochs=warmup_epochs,
                    output_checkpoint=path,
                )
                candidate_checkpoints[(condition, seed, weight)] = path
                row = {
                    "condition": condition,
                    "seed": seed,
                    "lambda": weight,
                    "warmup_epochs": warmup_epochs,
                    "best_validation_q_mae": fit["best_validation_q_mae"],
                    "best_epoch": fit["best_epoch"],
                    "elapsed_seconds": fit["elapsed_seconds"],
                }
                candidate_rows[condition].append(row)
                run_costs.append(
                    {
                        **row,
                        "method": "B_lambda_candidate",
                        "peak_memory_allocated_mb": fit["peak_memory_allocated_mb"],
                        "updates": fit["updates_in_segment"],
                        "checkpoint": str(path.relative_to(output_root)),
                    }
                )
                assert_budget()

    selected_lambda: dict[str, float] = {}
    lambda_scores: dict[str, Any] = {}
    for condition in CONDITIONS:
        score_by_lambda = {
            weight: float(
                np.mean(
                    [
                        row["best_validation_q_mae"]
                        for row in candidate_rows[condition]
                        if row["lambda"] == weight
                    ]
                )
            )
            for weight in lambda_candidates
        }
        chosen = min(lambda_candidates, key=lambda weight: (score_by_lambda[weight], weight))
        selected_lambda[condition] = float(chosen)
        lambda_scores[condition] = {
            "mean_validation_q_mae_by_lambda": {str(k): v for k, v in score_by_lambda.items()},
            "selected_lambda": float(chosen),
            "selection_rule": "lowest mean best-epoch validation normalized-q MAE over the three paired seeds; exact ties choose smaller lambda",
            "test_used": False,
        }
    write_json(formal_dir / "validation_lambda_selection.json", lambda_scores)

    selected_b_paths: dict[tuple[str, int], Path] = {}
    for condition in CONDITIONS:
        weight = selected_lambda[condition]
        for seed in seeds:
            assert_budget()
            warmup_path = candidate_checkpoints[(condition, seed, weight)]
            candidate_payload = _torch_load(warmup_path, torch.device("cuda"))
            final_path = final_dir / f"{condition}_B_lambda{weight:g}_seed{seed}.pt"
            fit = fit_model(
                method="B",
                condition=condition,
                arrays=arrays,
                splits={
                    "train": arrays["train_indices"],
                    "validation": arrays["validation_indices"],
                    "test": arrays["test_indices"],
                },
                forward=forward,
                config=config,
                seed=seed,
                reconstruction_weight=weight,
                total_epochs=int(training_cfg["max_epochs"]),
                output_checkpoint=final_path,
                resume_checkpoint=warmup_path,
            )
            selected_b_paths[(condition, seed)] = final_path
            histories[f"{condition}_B_seed{seed}"] = fit["history"]
            run_costs.append(
                {
                    "condition": condition,
                    "method": "B_selected",
                    "seed": seed,
                    "lambda": weight,
                    "epochs": int(training_cfg["max_epochs"]),
                    "continued_from_candidate_epochs": warmup_epochs,
                    "elapsed_seconds_continuation": fit["elapsed_seconds"],
                    "peak_memory_allocated_mb": fit["peak_memory_allocated_mb"],
                    "updates_continuation": fit["updates_in_segment"],
                    "checkpoint": str(final_path.relative_to(output_root)),
                }
            )
            assert_budget()

    # Retain only each selected candidate's validation evidence in the summary;
    # all checkpoint files remain available for exact reruns.
    test_indices = arrays["test_indices"]
    per_seed: dict[str, dict[str, dict[str, Any]]] = {
        condition: {method: {} for method in METHODS} for condition in CONDITIONS
    }
    test_started = time.perf_counter()
    for condition in CONDITIONS:
        for seed in seeds:
            for method in METHODS:
                path = (
                    final_dir / f"{condition}_A_seed{seed}.pt"
                    if method == "A"
                    else selected_b_paths[(condition, seed)]
                )
                model = load_best_model(path, method, int(arrays[f"{condition}_observed"].shape[1]))
                result = evaluate_method(
                    method=method,
                    condition=condition,
                    model=model,
                    arrays=arrays,
                    test_indices=test_indices,
                    forward=forward,
                    structure=structure,
                    forward_cfg=forward_cfg,
                )
                per_seed[condition][method][str(seed)] = result
                del model
                torch.cuda.empty_cache()
    evaluation_seconds = time.perf_counter() - test_started
    current_training_seconds = max(
        0.0, time.perf_counter() - training_started - evaluation_seconds
    )

    aggregate: dict[str, Any] = {}
    for condition in CONDITIONS:
        aggregate[condition] = {}
        for method in METHODS:
            rows = list(per_seed[condition][method].values())
            metric_names = (
                "parameter_mae_normalized_q",
                "lattice_mae_angstrom",
            )
            summary: dict[str, Any] = {}
            for metric in metric_names:
                keys = rows[0][metric].keys()
                summary[metric] = {
                    key: _aggregate([row[metric][key] for row in rows]) for key in keys
                }
            summary["observed_expected_profile_rmse_transformed"] = _aggregate(
                [row["observed_expected_profile_rmse_transformed"] for row in rows]
            )
            summary["clean_reference_residual_rmse_transformed_auxiliary"] = _aggregate(
                [row["clean_reference_residual_rmse_transformed_auxiliary"] for row in rows]
            )
            if method == "B":
                summary["nuisance_scaled_coordinate_mae_diagnostic_only"] = {
                    "by_coordinate": np.mean(
                        [row["nuisance_error_diagnostic_only"]["scaled_coordinate_mae"] for row in rows],
                        axis=0,
                    ).tolist(),
                    "mean": float(
                        np.mean(
                            [row["nuisance_error_diagnostic_only"]["mean_scaled_coordinate_mae"] for row in rows]
                        )
                    ),
                }
            aggregate[condition][method] = summary

    results = {
        "status": "COMPLETED_EXPLORATORY_PILOT",
        "design": {
            "material": "BaTiO3 P4mm, COD 9014273",
            "condition_scope": "simple linear count baseline vs V9 zero shift, broadening, polynomial background, Poisson-Gaussian readout",
            "q_scope": "single known CIF; interpolation in du,dv, not unseen-structure generalization",
            "test_scope": "exploratory follow-up; prior BaTiO3 test history exists, not blind confirmatory evidence",
            "a_objective": "MSE(q_pred,q_true)",
            "b_objective": "MSE(q_pred,q_true) + selected lambda * MSE(mu(q_pred,eta_pred), observed_profile)",
            "profile_metric": "MSE on max-normalized log1p_100 profiles; deterministic expected profile, not a noise realization",
            "eta_truth_policy": "eta_true never enters the model, train/validation/test model input, B loss, or lambda selection; used only for generation/metadata and post-prediction nuisance mismatch diagnostics",
            "backbone": "same ML4PXRD ResNet-18-GN trunk; A has 2 q outputs and B has 2 q plus 3 nuisance outputs",
            "parameter_count_note": "B has a 3-output wider final linear head (771 additional parameters); no nuisance truth supervision",
            "validation_rule": "for each condition select lambda with lowest mean best-epoch validation normalized-q MAE across the three paired seeds; ties choose smaller lambda; test is evaluated once after selection",
            "epochs": int(training_cfg["max_epochs"]),
            "seeds": seeds,
            "lambda_candidates": lambda_candidates,
            "selected_lambda": selected_lambda,
        },
        "split_counts": data_manifest["split_counts"],
        "per_seed": per_seed,
        "aggregate": aggregate,
        "training_runs": run_costs,
        "prior_failed_attempt_training_wallclock_seconds": prior_training_seconds,
        "training_plus_smoke_wallclock_seconds": prior_smoke_seconds
        + prior_training_seconds
        + current_training_seconds,
        "training_only_wallclock_seconds_formal": current_training_seconds,
        "test_evaluation_wallclock_seconds_excluded_from_training_budget": evaluation_seconds,
        "hard_budget_seconds": budget_seconds,
        "test_used_for_selection": False,
    }
    write_json(formal_dir / "training_history.json", histories)
    plot_histories: dict[str, list[dict[str, float]]] = {}
    for condition in CONDITIONS:
        for method in METHODS:
            seed_histories = [histories[f"{condition}_{method}_seed{seed}"] for seed in seeds]
            plot_histories[f"{condition}_{method}"] = [
                {
                    key: float(np.mean([history[index][key] for history in seed_histories]))
                    for key in seed_histories[0][index]
                }
                for index in range(len(seed_histories[0]))
            ]
    save_plots(
        formal_dir / "figures",
        results,
        plot_histories,
        forward.axis.detach().cpu().numpy(),
    )
    profile_store: dict[str, np.ndarray] = {}
    for condition in CONDITIONS:
        for method in METHODS:
            for seed_key, row in per_seed[condition][method].items():
                for field in (
                    "predicted_expected_profiles",
                    "clean_reconstructed_profiles",
                    "observed_profiles",
                    "clean_reference_profiles",
                ):
                    profile_store[f"{condition}_{method}_seed{seed_key}_{field}"] = np.asarray(
                        row.pop(field), dtype=np.float32
                    )
    np.savez_compressed(formal_dir / "test_profile_predictions.npz", **profile_store)
    results["test_profile_predictions"] = {
        "file": "formal/test_profile_predictions.npz",
        "arrays": {key: {"shape": list(value.shape), "sha256": sha256_array(value)} for key, value in profile_store.items()},
    }
    write_json(formal_dir / "ab_results.json", results)
    gate_report = {
        "status": "PASS",
        "p0_passed": True,
        "p1_p2_passed": True,
        "smoke_passed": True,
        "formal_pilot_completed": True,
        "training_plus_smoke_within_two_hour_budget": bool(
            results["training_plus_smoke_wallclock_seconds"] <= budget_seconds
        ),
        "no_gate_threshold_lowering": True,
        "no_test_selection": True,
        "p1_report": str(p1_report_path.resolve().relative_to(ROOT)),
        "smoke_report": str(smoke_path.resolve().relative_to(ROOT)),
        "formal_results": "formal/ab_results.json",
    }
    write_json(output_root / "gate_report.json", gate_report)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("smoke", "formal"), required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("xrd_forward_loss/measurement_closure/configs/issue19_batio3_v2.json"),
    )
    parser.add_argument(
        "--p1-report",
        type=Path,
        default=Path("xrd_forward_loss/measurement_closure/results/p1p2_v2_final_20261018/p1_numeric_gates.json"),
    )
    parser.add_argument(
        "--prior-training-seconds",
        type=float,
        default=0.0,
        help="training seconds consumed by a preserved failed formal attempt in the same budget",
    )
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    p1_path = args.p1_report if args.p1_report.is_absolute() else ROOT / args.p1_report
    output_root = args.output_root if args.output_root.is_absolute() else ROOT / args.output_root
    config = read_json(config_path)
    forward, forward_cfg, structure = make_forward(config)
    if args.stage == "smoke":
        smoke_stage(
            output_root=output_root,
            config=config,
            config_path=config_path,
            p1_report_path=p1_path,
            forward=forward,
        )
    else:
        formal_stage(
            output_root=output_root,
            config=config,
            config_path=config_path,
            p1_report_path=p1_path,
            forward=forward,
            forward_cfg=forward_cfg,
            structure=structure,
            prior_training_seconds=args.prior_training_seconds,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
