"""Frozen constants for the Train-only V10 Pilot."""
from __future__ import annotations

import math

SCHEMA_VERSION = "v10-train-only-pilot-v1"
SEED = 20260724
PILOT_EPOCHS = 3
TRAIN_STRUCTURES_PER_CLASS = 200
PANEL_STRUCTURES_PER_CLASS = 10
PERMUTATIONS = 100
LAMBDA_RES_TARGET = 0.2
LAMBDA_PERTURB_TARGET = 1.0
WARMUP_EPOCHS = 1
RAMP_EPOCHS = 2
SELECTED_STRENGTH_FAMILIES = ("background", "broadening", "noise")
TARGET_NAMES = (
    "delta_log_fwhm",
    "delta_background_ratio",
    "delta_log_inverse_count_scale",
    "delta_electronic_noise_counts",
)
TARGET_SCALES = {
    "log_fwhm": math.log(0.20 / 0.08),
    "background_ratio": 0.02,
    "log_inverse_count_scale": math.log(40000.0 / 2500.0),
    "electronic_noise_counts": 2.0,
}
