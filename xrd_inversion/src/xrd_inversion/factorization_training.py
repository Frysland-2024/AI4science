"""Matched deterministic training utilities for the Stage-1 factorization pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from .factorial_dataset import FactorialTensorBundle
from .factorization_losses import FactorizationLossBreakdown, factorization_loss
from .models import TwoHeadFactorizationModel
from .week1_pilot import stable_seed


@dataclass
class TrainingRun:
    model: TwoHeadFactorizationModel
    seed: int
    lambda_pair: float
    steps: int
    initial_state_sha256: str
    batch_schedule_sha256: str
    channel_mean: np.ndarray
    channel_std: np.ndarray
    initial_losses: dict[str, float]
    final_losses: dict[str, float]
    history: list[dict[str, float | int]]
    optimizer_state_dict: dict[str, Any]


def configure_determinism(seed: int, runtime: Mapping[str, Any]) -> torch.device:
    device = torch.device(str(runtime["device"]))
    if bool(runtime.get("require_cuda", True)) and device.type != "cuda":
        raise ValueError("Stage-1 runtime requires a CUDA device")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available to PyTorch")
    resolved_seed = int(seed) % (2**63 - 1)
    random.seed(resolved_seed)
    np.random.seed(resolved_seed % (2**32 - 1))
    torch.manual_seed(resolved_seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(resolved_seed)
    torch.backends.cuda.matmul.allow_tf32 = bool(runtime.get("allow_tf32", False))
    torch.backends.cudnn.allow_tf32 = bool(runtime.get("allow_tf32", False))
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(
        bool(runtime.get("deterministic_algorithms", True))
    )
    torch.set_float32_matmul_precision("highest")
    return device


def model_state_sha256(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        values = tensor.detach().cpu().contiguous().numpy()
        digest.update(name.encode("utf-8"))
        digest.update(str(values.dtype).encode("ascii"))
        digest.update(np.asarray(values.shape, dtype=np.int64).tobytes())
        digest.update(values.tobytes())
    return digest.hexdigest()


def fixed_batch_schedule(
    sample_count: int, steps: int, batch_size: int, seed: int
) -> np.ndarray:
    if sample_count < 1 or steps < 1 or batch_size < 1:
        raise ValueError("sample_count, steps, and batch_size must be positive")
    rng = np.random.default_rng(stable_seed(seed, "factorization-batch-schedule"))
    required = steps * batch_size
    values: list[np.ndarray] = []
    size = 0
    while size < required:
        permutation = rng.permutation(sample_count).astype(np.int64, copy=False)
        values.append(permutation)
        size += len(permutation)
    return np.concatenate(values)[:required].reshape(steps, batch_size)


def schedule_sha256(schedule: np.ndarray) -> str:
    values = np.ascontiguousarray(schedule, dtype=np.int64)
    return hashlib.sha256(values.tobytes()).hexdigest()


def _normalized_inputs(
    bundle: FactorialTensorBundle,
    indices: np.ndarray,
    channel_mean: np.ndarray,
    channel_std: np.ndarray,
    device: torch.device,
) -> torch.Tensor:
    inputs = torch.as_tensor(bundle.inputs[indices], device=device, dtype=torch.float32)
    mean = torch.as_tensor(
        channel_mean, device=device, dtype=torch.float32
    ).reshape(1, 1, 1, 3, 1)
    std = torch.as_tensor(
        channel_std, device=device, dtype=torch.float32
    ).reshape(1, 1, 1, 3, 1)
    normalized = (inputs - mean) / std
    if not bool(torch.isfinite(normalized).all()):
        raise ValueError("input normalization produced NaN or Inf")
    return normalized


def _losses_from_predictions(
    pred_s: np.ndarray,
    pred_m: np.ndarray,
    target_s: np.ndarray,
    target_m: np.ndarray,
    lambda_pair: float,
) -> dict[str, float]:
    with torch.no_grad():
        breakdown = factorization_loss(
            torch.from_numpy(np.asarray(pred_s, dtype=np.float32)),
            torch.from_numpy(np.asarray(pred_m, dtype=np.float32)),
            torch.from_numpy(np.asarray(target_s, dtype=np.float32)),
            torch.from_numpy(np.asarray(target_m, dtype=np.float32)),
            lambda_pair=lambda_pair,
        )
    return breakdown.detached_scalars()


def predict_blocks(
    model: TwoHeadFactorizationModel,
    bundle: FactorialTensorBundle,
    indices: Sequence[int],
    channel_mean: Sequence[float],
    channel_std: Sequence[float],
    *,
    batch_size_blocks: int = 32,
) -> tuple[np.ndarray, np.ndarray]:
    selected = np.asarray(indices, dtype=np.int64)
    if selected.ndim != 1 or selected.size == 0:
        raise ValueError("prediction indices must be a non-empty vector")
    device = next(model.parameters()).device
    mean = np.asarray(channel_mean, dtype=np.float32)
    std = np.asarray(channel_std, dtype=np.float32)
    outputs_s: list[np.ndarray] = []
    outputs_m: list[np.ndarray] = []
    model.eval()
    with torch.no_grad(), torch.autocast(
        device_type=device.type, enabled=False
    ):
        for start in range(0, len(selected), batch_size_blocks):
            batch_indices = selected[start : start + batch_size_blocks]
            inputs = _normalized_inputs(bundle, batch_indices, mean, std, device)
            pred_s, pred_m = model.forward_blocks(inputs)
            outputs_s.append(pred_s.cpu().numpy())
            outputs_m.append(pred_m.cpu().numpy())
    pred_s = np.concatenate(outputs_s, axis=0)
    pred_m = np.concatenate(outputs_m, axis=0)
    expected = (len(selected), 2, 2, 2)
    if pred_s.shape != expected or pred_m.shape != expected:
        raise RuntimeError("prediction output shape violates the factorial contract")
    if not np.isfinite(pred_s).all() or not np.isfinite(pred_m).all():
        raise RuntimeError("prediction output contains NaN or Inf")
    return pred_s, pred_m


def train_two_head_model(
    bundle: FactorialTensorBundle,
    train_indices: Sequence[int],
    channel_mean: Sequence[float],
    channel_std: Sequence[float],
    config: Mapping[str, Any],
    *,
    seed: int,
    lambda_pair: float,
    training_override: Mapping[str, Any] | None = None,
) -> TrainingRun:
    runtime = config["runtime"]
    device = configure_determinism(seed, runtime)
    model_config = dict(config["model"])
    model = TwoHeadFactorizationModel(**model_config).to(device=device, dtype=torch.float32)
    initial_hash = model_state_sha256(model)

    training = dict(config["training"])
    if training_override is not None:
        training.update(training_override)
    steps = int(training["steps"])
    batch_size = int(training["batch_size_blocks"])
    learning_rate = float(training["learning_rate"])
    weight_decay = float(training["weight_decay"])
    gradient_clip = float(training.get("gradient_clip_norm", 5.0))
    log_interval = int(training.get("log_interval_steps", max(steps // 10, 1)))
    selected = np.asarray(train_indices, dtype=np.int64)
    if selected.ndim != 1 or selected.size == 0:
        raise ValueError("train_indices must be a non-empty vector")
    mean = np.asarray(channel_mean, dtype=np.float32)
    std = np.asarray(channel_std, dtype=np.float32)
    if mean.shape != (3,) or std.shape != (3,) or np.any(std <= 0):
        raise ValueError("channel statistics must have shape (3,) and positive std")
    schedule = fixed_batch_schedule(len(selected), steps, batch_size, seed)
    schedule_digest = schedule_sha256(schedule)

    before_s, before_m = predict_blocks(
        model, bundle, selected, mean, std, batch_size_blocks=batch_size
    )
    initial_losses = _losses_from_predictions(
        before_s,
        before_m,
        bundle.theta_s[selected],
        bundle.theta_m[selected],
        lambda_pair,
    )
    del before_s, before_m

    inputs = _normalized_inputs(bundle, selected, mean, std, device)
    target_s = torch.as_tensor(
        bundle.theta_s[selected], device=device, dtype=torch.float32
    )
    target_m = torch.as_tensor(
        bundle.theta_m[selected], device=device, dtype=torch.float32
    )
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    history: list[dict[str, float | int]] = []
    model.train()
    with torch.autocast(device_type=device.type, enabled=False):
        for step in range(steps):
            local_indices = torch.as_tensor(
                schedule[step], device=device, dtype=torch.long
            )
            pred_s, pred_m = model.forward_blocks(inputs[local_indices])
            breakdown = factorization_loss(
                pred_s,
                pred_m,
                target_s[local_indices],
                target_m[local_indices],
                lambda_pair=lambda_pair,
            )
            if not bool(torch.isfinite(breakdown.total)):
                raise FloatingPointError(f"non-finite loss at training step {step + 1}")
            optimizer.zero_grad(set_to_none=True)
            breakdown.total.backward()
            for name, parameter in model.named_parameters():
                if parameter.grad is not None and not bool(
                    torch.isfinite(parameter.grad).all()
                ):
                    raise FloatingPointError(
                        f"non-finite gradient for {name} at step {step + 1}"
                    )
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                model.parameters(), max_norm=gradient_clip
            )
            if not bool(torch.isfinite(gradient_norm)):
                raise FloatingPointError(f"non-finite gradient norm at step {step + 1}")
            optimizer.step()
            if step == 0 or (step + 1) % log_interval == 0 or step + 1 == steps:
                row: dict[str, float | int] = {"step": step + 1}
                row.update(breakdown.detached_scalars())
                row["gradient_norm"] = float(gradient_norm.detach().cpu().item())
                history.append(row)

    after_s, after_m = predict_blocks(
        model, bundle, selected, mean, std, batch_size_blocks=batch_size
    )
    final_losses = _losses_from_predictions(
        after_s,
        after_m,
        bundle.theta_s[selected],
        bundle.theta_m[selected],
        lambda_pair,
    )
    del after_s, after_m, inputs, target_s, target_m
    return TrainingRun(
        model=model,
        seed=int(seed),
        lambda_pair=float(lambda_pair),
        steps=steps,
        initial_state_sha256=initial_hash,
        batch_schedule_sha256=schedule_digest,
        channel_mean=mean,
        channel_std=std,
        initial_losses=initial_losses,
        final_losses=final_losses,
        history=history,
        optimizer_state_dict=optimizer.state_dict(),
    )


def save_training_checkpoint(
    path: Path,
    run: TrainingRun,
    config: Mapping[str, Any],
    *,
    manifest_sha256: str,
    condition: str,
    metrics: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any],
) -> None:
    required_provenance = {
        "interface_version",
        "interface_sha256",
        "config_sha256",
        "manifest_sha256",
        "source_sha256",
        "dataset_source_sha256",
        "corner_order",
        "structure_parameter_order",
        "measurement_parameter_order",
        "reference_q",
        "profile_transform",
        "profile_view",
        "scope",
    }
    missing = sorted(required_provenance.difference(provenance))
    if missing:
        raise ValueError(f"checkpoint provenance is incomplete: {missing}")
    if str(provenance["manifest_sha256"]) != str(manifest_sha256):
        raise ValueError("checkpoint provenance manifest hash mismatch")
    payload = {
        "schema_version": "xrd-inversion-factorization-checkpoint-v1",
        "model_kind": "two_head_shared_encoder",
        "condition": str(condition),
        "seed": run.seed,
        "lambda_pair": run.lambda_pair,
        "steps": run.steps,
        "model_config": dict(config["model"]),
        "model_state_dict": run.model.state_dict(),
        "optimizer_state_dict": run.optimizer_state_dict,
        "channel_mean": run.channel_mean.tolist(),
        "channel_std": run.channel_std.tolist(),
        "initial_state_sha256": run.initial_state_sha256,
        "batch_schedule_sha256": run.batch_schedule_sha256,
        "manifest_sha256": str(manifest_sha256),
        "checkpoint_policy": str(config["training"]["checkpoint_policy"]),
        "initial_losses": dict(run.initial_losses),
        "final_losses": dict(run.final_losses),
        "metrics": None if metrics is None else dict(metrics),
        "interface_version": str(provenance["interface_version"]),
        "config_sha256": str(provenance["config_sha256"]),
        "corner_order": list(provenance["corner_order"]),
        "structure_parameter_order": list(provenance["structure_parameter_order"]),
        "measurement_parameter_order": list(
            provenance["measurement_parameter_order"]
        ),
        "provenance": dict(provenance),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    os.replace(temporary, path)


def load_training_checkpoint(
    path: Path, *, device: str | torch.device = "cpu"
) -> tuple[TwoHeadFactorizationModel, dict[str, Any]]:
    payload = torch.load(path, map_location=device, weights_only=False)
    if payload.get("schema_version") != "xrd-inversion-factorization-checkpoint-v1":
        raise ValueError("unsupported factorization checkpoint schema")
    model = TwoHeadFactorizationModel(**payload["model_config"]).to(
        device=device, dtype=torch.float32
    )
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.eval()
    return model, payload


__all__ = [
    "TrainingRun",
    "configure_determinism",
    "fixed_batch_schedule",
    "load_training_checkpoint",
    "model_state_sha256",
    "predict_blocks",
    "save_training_checkpoint",
    "schedule_sha256",
    "train_two_head_model",
]
