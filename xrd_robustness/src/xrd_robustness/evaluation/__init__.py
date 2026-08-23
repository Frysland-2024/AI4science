"""Metrics and paired Dynamic JS versus Dynamic ERM statistics."""

from .metrics import (
    classification_metrics,
    expected_calibration_error,
    paired_view_metrics,
    representation_diagnostics,
    robustness_auc,
)
from .statistics import (
    build_paired_statistics_report,
    hierarchical_paired_bootstrap,
    interpret_single_contrast,
    summarize_prediction_rows,
    validate_prediction_rows,
)

__all__ = [
    "build_paired_statistics_report",
    "classification_metrics",
    "expected_calibration_error",
    "hierarchical_paired_bootstrap",
    "interpret_single_contrast",
    "paired_view_metrics",
    "representation_diagnostics",
    "robustness_auc",
    "summarize_prediction_rows",
    "validate_prediction_rows",
]
