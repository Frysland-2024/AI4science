"""Matched training and validation routines for the A/B pilot."""

from __future__ import annotations

import copy
import time
from typing import Any

import numpy as np
import torch
from torch.nn.utils import clip_grad_norm_

from .losses import clean_reference_paired_losses, paired_losses
from .model import ParameterRegressor


def _device_tensors(arrays: dict[str, np.ndarray], device: torch.device):
    return {
        "q": torch.as_tensor(arrays["q"], dtype=torch.float32, device=device),
        "noisy": torch.as_tensor(arrays["noisy"], dtype=torch.float32, device=device),
    }


@torch.no_grad()
def predict(model: ParameterRegressor, profiles: torch.Tensor, batch_size: int = 64):
    model.eval()
    return torch.cat(
        [model(profiles[start : start + batch_size]) for start in range(0, len(profiles), batch_size)],
        dim=0,
    )


def fit(
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    *,
    forward_model: object,
    device: torch.device,
    seed: int,
    epochs: int,
    learning_rate: float,
    batch_size: int,
    reconstruction_weight: float,
    gradient_clip_norm: float,
    max_train_samples: int | None = None,
    clean_reference_profiles: np.ndarray | None = None,
) -> dict[str, Any]:
    """Train one model and retain the validation-best state by q MAE.

    When ``clean_reference_profiles`` is provided, B's differentiable profile
    term targets that simulator-generated clean reference. Inputs remain the
    condition-specific profiles in ``arrays['noisy']``. Omitting the argument
    preserves the original PR #11 behavior exactly.
    """

    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    model = ParameterRegressor().to(device=device, dtype=torch.float32)
    data = _device_tensors(arrays, device)
    clean_reference = (
        torch.as_tensor(clean_reference_profiles, dtype=torch.float32, device=device)
        if clean_reference_profiles is not None
        else None
    )
    if clean_reference is not None and clean_reference.shape != data["noisy"].shape:
        raise ValueError("clean_reference_profiles must match the observed profile shape")
    train_indices = np.asarray(splits["train"], dtype=np.int64)
    if max_train_samples is not None:
        train_indices = train_indices[:max_train_samples]
    train_idx = torch.as_tensor(train_indices, dtype=torch.long, device=device)
    validation_idx = torch.as_tensor(splits["validation"], dtype=torch.long, device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate, weight_decay=0.0)
    generator = torch.Generator(device=device)
    generator.manual_seed(seed + 1000)
    best_validation_mae = float("inf")
    best_state = None
    best_epoch = 0
    history: list[dict[str, float]] = []
    started = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        order = train_idx[torch.randperm(len(train_idx), generator=generator, device=device)]
        totals = {"total": 0.0, "parameter": 0.0, "reconstruction": 0.0}
        batches = 0
        for start in range(0, len(order), batch_size):
            batch_idx = order[start : start + batch_size]
            x = data["noisy"].index_select(0, batch_idx)
            y = data["q"].index_select(0, batch_idx)
            optimizer.zero_grad(set_to_none=True)
            predicted = model(x)
            if clean_reference is None:
                losses = paired_losses(
                    predicted,
                    y,
                    x,
                    forward_model=forward_model,
                    reconstruction_weight=reconstruction_weight,
                )
            else:
                clean_target = clean_reference.index_select(0, batch_idx)
                losses = clean_reference_paired_losses(
                    predicted,
                    y,
                    clean_target,
                    forward_model=forward_model,
                    reconstruction_weight=reconstruction_weight,
                )
            if not torch.isfinite(losses["total"]):
                raise FloatingPointError("non-finite training objective")
            losses["total"].backward()
            clip_grad_norm_(model.parameters(), gradient_clip_norm)
            optimizer.step()
            for key in totals:
                totals[key] += float(losses[key].detach().cpu())
            batches += 1
        model.eval()
        val_pred = predict(model, data["noisy"].index_select(0, validation_idx))
        validation_mae = float(
            torch.mean(torch.abs(val_pred - data["q"].index_select(0, validation_idx))).cpu()
        )
        history.append(
            {
                "epoch": float(epoch),
                "train_total_loss": totals["total"] / max(batches, 1),
                "train_parameter_mse": totals["parameter"] / max(batches, 1),
                "train_reconstruction_mse": totals["reconstruction"] / max(batches, 1),
                "validation_q_mae": validation_mae,
            }
        )
        if validation_mae < best_validation_mae:
            best_validation_mae = validation_mae
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
    elapsed = time.perf_counter() - started
    if best_state is None:
        raise RuntimeError("training did not produce a validation checkpoint")
    model.load_state_dict(best_state)
    peak_memory_mb = (
        float(torch.cuda.max_memory_allocated(device) / (1024**2))
        if device.type == "cuda"
        else None
    )
    return {
        "model": model,
        "history": history,
        "best_epoch": best_epoch,
        "best_validation_q_mae": best_validation_mae,
        "training_seconds": elapsed,
        "training_seconds_per_epoch": elapsed / epochs,
        "peak_memory_allocated_mb": peak_memory_mb,
        "train_sample_count": len(train_idx),
        "updates": epochs * int(np.ceil(len(train_idx) / batch_size)),
    }
