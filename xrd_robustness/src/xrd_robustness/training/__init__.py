"""Public ResNet dynamic-training API."""

from .objectives import dynamic_erm, dynamic_js, js_divergence
from .trainer_factory import TrainingStepConfig, run_training_step

__all__ = [
    "TrainingStepConfig",
    "dynamic_erm",
    "dynamic_js",
    "js_divergence",
    "run_training_step",
]
