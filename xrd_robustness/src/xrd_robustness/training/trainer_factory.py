"""One dispatch point for matched V7 training modes."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from ..online_views import TrainingMode
from .objectives import (
    PerturbationDeltaRegressor,
    ResidualClassifier,
    dynamic_erm,
    dynamic_js,
    dynamic_perturbation_supervised_residual,
    dynamic_residual,
    fixed_erm,
)


@dataclass(frozen=True)
class TrainingStepConfig:
    mode: TrainingMode
    lambda_js: float = 0.1
    lambda_res: float = 0.1
    lambda_perturb: float = 1.0


def run_training_step(
    config: TrainingStepConfig,
    model: nn.Module,
    *,
    x1: torch.Tensor,
    target: torch.Tensor,
    x2: torch.Tensor | None = None,
    optimizer_main: torch.optim.Optimizer | None = None,
    optimizer_res: torch.optim.Optimizer | None = None,
    optimizer_aux: torch.optim.Optimizer | None = None,
    residual_classifier: ResidualClassifier | None = None,
    perturbation_regressor: PerturbationDeltaRegressor | None = None,
    perturbation_delta: torch.Tensor | None = None,
) -> dict[str, torch.Tensor]:
    """Dispatch one step while keeping data exposure identical across dynamic modes."""
    if config.mode in {
        TrainingMode.CLEAN_ERM,
        TrainingMode.OFFLINE_ERM,
        TrainingMode.FIXED_VIEW_ERM,
    }:
        return fixed_erm(model, x1, target, x_fixed_second=x2)
    if x2 is None:
        raise ValueError(f"{config.mode.value} requires x2")
    if config.mode is TrainingMode.DYNAMIC_ERM:
        return dynamic_erm(model, x1, x2, target)
    if config.mode in {TrainingMode.DYNAMIC_JS, TrainingMode.DYNAMIC_CONSISTENCY}:
        return dynamic_js(model, x1, x2, target, lambda_js=config.lambda_js)
    if config.mode is TrainingMode.DYNAMIC_RESIDUAL:
        if residual_classifier is None or optimizer_main is None or optimizer_res is None:
            raise ValueError("dynamic_residual requires residual classifier and two optimizers")
        return dynamic_residual(
            model,
            residual_classifier,
            x1,
            x2,
            target,
            optimizer_main=optimizer_main,
            optimizer_res=optimizer_res,
            lambda_res=config.lambda_res,
        )
    if config.mode is TrainingMode.PERTURBATION_SUPERVISED_RESIDUAL:
        if (
            residual_classifier is None
            or perturbation_regressor is None
            or perturbation_delta is None
            or optimizer_main is None
            or optimizer_aux is None
        ):
            raise ValueError(
                "perturbation_supervised_residual requires two heads, perturbation "
                "targets, and main/auxiliary optimizers"
            )
        return dynamic_perturbation_supervised_residual(
            model,
            residual_classifier,
            perturbation_regressor,
            x1,
            x2,
            target,
            perturbation_delta,
            optimizer_main=optimizer_main,
            optimizer_aux=optimizer_aux,
            lambda_perturb=config.lambda_perturb,
            lambda_res=config.lambda_res,
        )
    raise ValueError(f"unsupported training mode: {config.mode}")
