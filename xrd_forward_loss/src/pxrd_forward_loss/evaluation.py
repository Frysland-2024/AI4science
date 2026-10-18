"""Metrics, physical-parameter conversion, and pilot plots."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from .model import compose_full_q
from .training import predict


def q_to_lattice(q: np.ndarray, a0: float, c0: float, du_half: float, dv_half: float):
    values = np.asarray(q, dtype=np.float64)
    u0 = (2.0 * math.log(a0) + math.log(c0)) / 3.0
    v0 = math.log(c0 / a0)
    u = u0 + values[..., 0] * du_half
    v = v0 + values[..., 1] * dv_half
    a = np.exp(u - v / 3.0)
    c = np.exp(u + 2.0 * v / 3.0)
    return a, c


@torch.no_grad()
def evaluate_model(
    model,
    arrays: dict[str, np.ndarray],
    indices: np.ndarray,
    *,
    forward_model: object,
    device: torch.device,
    a0: float,
    c0: float,
    du_half: float,
    dv_half: float,
) -> dict[str, Any]:
    index_tensor = torch.as_tensor(indices, dtype=torch.long, device=device)
    x = torch.as_tensor(arrays["noisy"], dtype=torch.float32, device=device).index_select(0, index_tensor)
    clean = np.asarray(arrays["clean"], dtype=np.float64)[indices]
    target_q = np.asarray(arrays["q"], dtype=np.float64)[indices]
    pred_q_tensor = predict(model, x)
    pred_q = pred_q_tensor.detach().cpu().numpy().astype(np.float64)
    reconstructed = []
    for start in range(0, len(pred_q), 16):
        q_batch = torch.as_tensor(pred_q[start : start + 16], dtype=torch.float64, device=device)
        profile = forward_model.transformed(compose_full_q(q_batch))
        reconstructed.append(profile.detach().cpu().numpy())
    prediction = np.concatenate(reconstructed, axis=0).astype(np.float64)
    noisy = np.asarray(arrays["noisy"], dtype=np.float64)[indices]
    q_abs_error = np.abs(pred_q - target_q)
    a_true, c_true = q_to_lattice(target_q, a0, c0, du_half, dv_half)
    a_pred, c_pred = q_to_lattice(pred_q, a0, c0, du_half, dv_half)
    clean_rmse = float(np.sqrt(np.mean((prediction - clean) ** 2)))
    noisy_rmse = float(np.sqrt(np.mean((prediction - noisy) ** 2)))
    profile_per_sample = np.sqrt(np.mean((prediction - clean) ** 2, axis=1))
    return {
        "count": int(len(indices)),
        "parameter_mae_normalized": {
            "du": float(np.mean(q_abs_error[:, 0])),
            "dv": float(np.mean(q_abs_error[:, 1])),
            "mean_two_parameter": float(np.mean(q_abs_error)),
        },
        "lattice_mae_angstrom": {
            "a": float(np.mean(np.abs(a_pred - a_true))),
            "c": float(np.mean(np.abs(c_pred - c_true))),
        },
        "reconstruction_rmse_transformed_clean": clean_rmse,
        "reconstruction_rmse_transformed_noisy": noisy_rmse,
        "per_sample_clean_rmse": profile_per_sample.tolist(),
        "prediction_q": pred_q.tolist(),
        "target_q": target_q.tolist(),
        "reconstruction_profile": prediction.tolist(),
    }


def plot_results(
    output_dir: Path,
    axis: np.ndarray,
    arrays: dict[str, np.ndarray],
    test_indices: np.ndarray,
    evaluation_by_method: dict[str, dict[str, Any]],
    histories: dict[str, list[dict[str, float]]],
):
    output_dir.mkdir(parents=True, exist_ok=True)
    colors = {"A": "#2878B5", "B": "#D9534F"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for method, history in histories.items():
        epochs = [entry["epoch"] for entry in history]
        axes[0].plot(epochs, [entry["train_parameter_mse"] for entry in history], label=f"{method} train", color=colors[method])
        axes[1].plot(epochs, [entry["validation_q_mae"] for entry in history], label=method, color=colors[method])
    axes[0].set(title="Training parameter loss", xlabel="Epoch", ylabel="MSE on normalized q")
    axes[1].set(title="Validation parameter MAE", xlabel="Epoch", ylabel="MAE on normalized q")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "training_curves.png", dpi=180)
    plt.close(fig)

    q_maes = [
        (method, np.asarray(result["target_q"]), np.asarray(result["prediction_q"]))
        for method, result in evaluation_by_method.items()
    ]
    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    for method, targets, predictions in q_maes:
        ax.scatter(targets[:, 0], predictions[:, 0], s=21, alpha=0.65, label=f"{method}: du", color=colors[method], marker="o" if method == "A" else "x")
    limits = [-0.85, 0.85]
    ax.plot(limits, limits, "k--", linewidth=1)
    ax.set(xlim=limits, ylim=limits, xlabel="True du (normalized)", ylabel="Predicted du (normalized)", title="Held-out test predictions")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "test_parameter_predictions.png", dpi=180)
    plt.close(fig)

    b_result = evaluation_by_method["B"]
    b_errors = np.mean(np.abs(np.asarray(b_result["prediction_q"]) - np.asarray(b_result["target_q"])), axis=1)
    worst_local = int(np.argmax(b_errors))
    global_idx = int(test_indices[worst_local])
    target_clean = np.asarray(arrays["clean"][global_idx], dtype=np.float64)
    target_noisy = np.asarray(arrays["noisy"][global_idx], dtype=np.float64)
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(axis, target_noisy, color="#555555", linewidth=0.9, alpha=0.75, label="Noisy measurement")
    ax.plot(axis, target_clean, color="black", linewidth=1.3, label="Clean target")
    for method, result in evaluation_by_method.items():
        ax.plot(axis, np.asarray(result["reconstruction_profile"])[worst_local], color=colors[method], linewidth=1.1, label=f"{method} reconstruction")
    ax.set(title=f"Failure case: test index {global_idx}, B mean |q error|={b_errors[worst_local]:.3f}", xlabel="2θ (degrees)", ylabel="Transformed intensity")
    ax.grid(alpha=0.2)
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(output_dir / "failure_case_overlay.png", dpi=180)
    plt.close(fig)
    return {"worst_b_test_global_index": global_idx, "worst_b_mean_abs_q_error": float(b_errors[worst_local])}
