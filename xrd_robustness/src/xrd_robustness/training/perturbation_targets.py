"""Weak-supervision targets derived from simulator-known XRD parameters."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import torch

from ..physics import PhysicsParameters


@dataclass(frozen=True)
class PerturbationTargetConfig:
    """Normalization for the minimal peak-shift/peak-width Pilot target."""

    zero_shift_scale_deg: float = 0.2
    log_fwhm_scale: float = 1.0

    def validate(self) -> None:
        if not math.isfinite(self.zero_shift_scale_deg) or self.zero_shift_scale_deg <= 0:
            raise ValueError("zero_shift_scale_deg must be finite and positive")
        if not math.isfinite(self.log_fwhm_scale) or self.log_fwhm_scale <= 0:
            raise ValueError("log_fwhm_scale must be finite and positive")

    @property
    def target_names(self) -> tuple[str, str]:
        return ("delta_zero_shift", "delta_log_fwhm")


def pilot_perturbation_delta(
    first: Sequence[PhysicsParameters],
    second: Sequence[PhysicsParameters],
    *,
    config: PerturbationTargetConfig = PerturbationTargetConfig(),
    device: torch.device | str | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    """Return normalized ``z_second - z_first`` targets for the minimal Pilot.

    Peak width is represented as a log-ratio because broadening is positive and
    multiplicative. The target order deliberately matches ``signed_measurement_residual``.
    """
    config.validate()
    if len(first) != len(second):
        raise ValueError("paired perturbation parameter sequences must have equal length")
    if not first:
        raise ValueError("paired perturbation parameter sequences cannot be empty")

    values: list[tuple[float, float]] = []
    for first_params, second_params in zip(first, second, strict=True):
        first_params.validate()
        second_params.validate()
        zero_shift_delta = (
            second_params.delta_2theta_deg - first_params.delta_2theta_deg
        ) / config.zero_shift_scale_deg
        log_fwhm_delta = (
            math.log(second_params.fwhm_deg) - math.log(first_params.fwhm_deg)
        ) / config.log_fwhm_scale
        if not math.isfinite(zero_shift_delta) or not math.isfinite(log_fwhm_delta):
            raise ValueError("perturbation targets must be finite")
        values.append((zero_shift_delta, log_fwhm_delta))
    return torch.tensor(values, dtype=dtype, device=device)
