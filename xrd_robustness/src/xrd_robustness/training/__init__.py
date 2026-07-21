"""Matched supervised objectives for the V7 experiment modes."""

from .objectives import (
    PerturbationDeltaRegressor,
    ResidualClassifier,
    dynamic_consistency,
    dynamic_erm,
    dynamic_js,
    dynamic_perturbation_supervised_residual,
    dynamic_residual,
    fixed_erm,
    js_divergence,
    l2_normalize_embedding,
    residual_confusion_kl,
    residual_lambda_schedule,
    signed_measurement_residual,
    symmetric_measurement_residual,
)
from .perturbation_targets import PerturbationTargetConfig, pilot_perturbation_delta
from .trainer_factory import TrainingStepConfig, run_training_step

__all__ = [
    "PerturbationDeltaRegressor",
    "ResidualClassifier",
    "dynamic_consistency",
    "dynamic_erm",
    "dynamic_js",
    "dynamic_perturbation_supervised_residual",
    "dynamic_residual",
    "fixed_erm",
    "js_divergence",
    "l2_normalize_embedding",
    "residual_confusion_kl",
    "residual_lambda_schedule",
    "signed_measurement_residual",
    "symmetric_measurement_residual",
    "PerturbationTargetConfig",
    "pilot_perturbation_delta",
    "TrainingStepConfig",
    "run_training_step",
]
