"""Shared-batch optimizer update for the parent-budget matched objectives."""

from __future__ import annotations

from typing import Mapping

import torch

from .objectives import TrainingStepConfig, run_training_step


def paired_optimizer_step(
    models: Mapping[str, torch.nn.Module],
    optimizers: Mapping[str, torch.optim.Optimizer],
    configs: Mapping[str, TrainingStepConfig],
    *,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    autocast_dtype: torch.dtype | None = None,
) -> dict[str, dict[str, torch.Tensor]]:
    """Update ERM and JS from the same already-rendered tensors exactly once."""
    methods = {"dynamic_erm", "dynamic_js"}
    if set(models) != methods:
        raise ValueError("paired update requires exactly dynamic_erm and dynamic_js models")
    if set(optimizers) != methods or set(configs) != methods:
        raise ValueError("models, optimizers, and objective configs must have identical keys")
    results: dict[str, dict[str, torch.Tensor]] = {}
    for method in ("dynamic_erm", "dynamic_js"):
        model = models[method]
        optimizer = optimizers[method]
        model.train()
        optimizer.zero_grad(set_to_none=True)
        amp_enabled = autocast_dtype is not None and x1.device.type == "cuda"
        if amp_enabled:
            amp_context = torch.autocast(
                device_type="cuda", dtype=autocast_dtype, enabled=True
            )
        else:
            from contextlib import nullcontext

            amp_context = nullcontext()
        with amp_context:
            result = run_training_step(
                configs[method], model, x1=x1, x2=x2, target=target
            )
        result["total"].backward()
        optimizer.step()
        results[method] = result
    return results
