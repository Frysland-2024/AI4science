"""V7 evaluation utilities."""

from .metrics import (
    classification_metrics,
    expected_calibration_error,
    paired_view_metrics,
    residual_diagnostics,
    robustness_auc,
)
from .residual_probe import (
    PostHocResidualProbe,
    ProbeConfig,
    frozen_model_residuals,
    train_posthoc_residual_probe,
)
from .real_xrd import RealXRDConfig, load_real_xrd

__all__ = [
    "PostHocResidualProbe",
    "ProbeConfig",
    "RealXRDConfig",
    "classification_metrics",
    "expected_calibration_error",
    "frozen_model_residuals",
    "paired_view_metrics",
    "residual_diagnostics",
    "load_real_xrd",
    "robustness_auc",
    "train_posthoc_residual_probe",
]
