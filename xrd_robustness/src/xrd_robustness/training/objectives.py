"""Differentiable objectives for Dynamic ERM and Dynamic JS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import torch
from torch import nn
from torch.nn import functional as F

from ..online_views import TrainingMode


@dataclass(frozen=True)
class TrainingStepConfig:
    mode: TrainingMode
    lambda_js: float = 60.0

    def validate(self) -> None:
        if self.lambda_js < 0:
            raise ValueError("lambda_js must be non-negative")


def _logits(model: nn.Module, values: torch.Tensor) -> torch.Tensor:
    output = model(values)
    if isinstance(output, dict):
        logits = output.get("logits")
        if not isinstance(logits, torch.Tensor):
            raise ValueError("backbone output must contain tensor logits")
        return logits
    if not isinstance(output, torch.Tensor):
        raise ValueError("model must return logits or a mapping containing logits")
    return output


def js_divergence(first_logits: torch.Tensor, second_logits: torch.Tensor) -> torch.Tensor:
    """Return the batch-mean Jensen-Shannon divergence between predictions."""

    first_log = F.log_softmax(first_logits, dim=-1)
    second_log = F.log_softmax(second_logits, dim=-1)
    first = first_log.exp()
    second = second_log.exp()
    midpoint_log = (0.5 * (first + second)).clamp_min(1e-12).log()
    return 0.5 * (
        F.kl_div(midpoint_log, first, reduction="batchmean")
        + F.kl_div(midpoint_log, second, reduction="batchmean")
    )


def dynamic_erm(
    model: nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    """Supervise two independently rendered views with equal weight."""

    logits1 = _logits(model, x1)
    logits2 = _logits(model, x2)
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    return {
        "logits_first": logits1,
        "logits_second": logits2,
        "classification": classification,
        "consistency": classification.new_zeros(()),
        "total": classification,
    }


def dynamic_js(
    model: nn.Module,
    x1: torch.Tensor,
    x2: torch.Tensor,
    target: torch.Tensor,
    *,
    lambda_js: float,
    classification_loss: Callable = F.cross_entropy,
) -> dict[str, torch.Tensor]:
    """Dynamic ERM plus output-level Jensen-Shannon consistency."""

    if lambda_js < 0:
        raise ValueError("lambda_js must be non-negative")
    logits1 = _logits(model, x1)
    logits2 = _logits(model, x2)
    classification = 0.5 * (
        classification_loss(logits1, target) + classification_loss(logits2, target)
    )
    consistency = js_divergence(logits1, logits2)
    return {
        "logits_first": logits1,
        "logits_second": logits2,
        "classification": classification,
        "consistency": consistency,
        "total": classification + float(lambda_js) * consistency,
    }


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
