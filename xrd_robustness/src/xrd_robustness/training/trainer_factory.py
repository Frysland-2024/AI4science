"""Dispatch the two public dynamic-training objectives."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from ..online_views import TrainingMode
from .objectives import dynamic_erm, dynamic_js


@dataclass(frozen=True)
class TrainingStepConfig:
    mode: TrainingMode
    lambda_js: float = 60.0

    def validate(self) -> None:
        if self.lambda_js < 0:
            raise ValueError("lambda_js must be non-negative")


def run_training_step(
    config: TrainingStepConfig,
    model: nn.Module,
    *,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
) -> dict[str, torch.Tensor]:
    """Compute one matched two-view loss without stepping an optimizer."""

    config.validate()
    if config.mode is TrainingMode.DYNAMIC_ERM:
        return dynamic_erm(model, x1, x2, target)
    if config.mode is TrainingMode.DYNAMIC_JS:
        return dynamic_js(model, x1, x2, target, lambda_js=config.lambda_js)
    raise ValueError(f"unsupported training mode: {config.mode}")
