"""Losses for the Stage-1 2x2 structure--measurement factorial pilot.

The public loss boundary is deliberately block based.  Every tensor has shape
``[B, 2, 2, 2]`` with axes ``[block, structure_state, measurement_state,
coordinate]``.  Keeping the two intervention axes explicit prevents the two
paired invariance terms from being silently swapped after flattening the four
spectra.
"""

from __future__ import annotations

from dataclasses import dataclass

import torch


FACTORIAL_BLOCK_SHAPE_SUFFIX = (2, 2, 2)


def _validate_block_tensor(name: str, value: torch.Tensor) -> None:
    if not isinstance(value, torch.Tensor):
        raise TypeError(f"{name} must be a torch.Tensor")
    if value.ndim != 4 or tuple(value.shape[1:]) != FACTORIAL_BLOCK_SHAPE_SUFFIX:
        raise ValueError(
            f"{name} must have shape [B,2,2,2] with axes "
            "[block,structure_state,measurement_state,coordinate]; "
            f"got {tuple(value.shape)}"
        )
    if value.shape[0] < 1:
        raise ValueError(f"{name} must contain at least one factorial block")
    if not value.is_floating_point():
        raise TypeError(f"{name} must have a floating dtype")
    if not bool(torch.isfinite(value).all().item()):
        raise ValueError(f"{name} contains NaN or Inf")


def _validate_matching_tensors(**values: torch.Tensor) -> None:
    for name, value in values.items():
        _validate_block_tensor(name, value)
    shapes = {tuple(value.shape) for value in values.values()}
    if len(shapes) != 1:
        rendered = ", ".join(f"{name}={tuple(value.shape)}" for name, value in values.items())
        raise ValueError(f"factorial tensors must have identical shapes; {rendered}")
    devices = {value.device for value in values.values()}
    if len(devices) != 1:
        raise ValueError("factorial tensors must be on the same device")
    dtypes = {value.dtype for value in values.values()}
    if len(dtypes) != 1:
        raise ValueError("factorial tensors must have the same dtype")


def parameter_supervision_loss(
    pred_s: torch.Tensor,
    pred_m: torch.Tensor,
    target_s: torch.Tensor,
    target_m: torch.Tensor,
) -> torch.Tensor:
    """Return MSE over all four standardized parameter coordinates.

    This is exactly the elementwise mean after concatenating the two heads, so
    the structure and measurement heads receive equal weight (two coordinates
    each).  Targets are view-level grids; the dataset contract is responsible
    for repeating a structure label across the measurement axis and a
    measurement label across the structure axis.
    """

    _validate_matching_tensors(
        pred_s=pred_s,
        pred_m=pred_m,
        target_s=target_s,
        target_m=target_m,
    )
    squared_error = torch.cat(
        ((pred_s - target_s).square(), (pred_m - target_m).square()), dim=-1
    )
    return squared_error.mean()


# Backward-compatible descriptive alias used by some small diagnostics.
parameter_mse_loss = parameter_supervision_loss


@dataclass(frozen=True)
class PairedInvarianceLosses:
    """The two axis-specific paired penalties and their unweighted sum."""

    structure: torch.Tensor
    measurement: torch.Tensor

    @property
    def total(self) -> torch.Tensor:
        return self.structure + self.measurement

    def __iter__(self):
        """Allow explicit ``structure, measurement = losses`` unpacking."""

        yield self.structure
        yield self.measurement


def paired_invariance_losses(
    pred_s: torch.Tensor,
    pred_m: torch.Tensor,
) -> PairedInvarianceLosses:
    """Return ``(L_s_inv, L_m_inv)`` for a canonical factorial block.

    ``L_s_inv`` changes the measurement axis while holding structure fixed:
    ``(x11,x12)`` and ``(x21,x22)``.  ``L_m_inv`` changes the structure axis
    while holding measurement fixed: ``(x11,x21)`` and ``(x12,x22)``.
    Each component is an elementwise mean squared difference, including both
    paired edges and both head coordinates.
    """

    _validate_matching_tensors(pred_s=pred_s, pred_m=pred_m)
    structure_across_measurement = pred_s[:, :, 1, :] - pred_s[:, :, 0, :]
    measurement_across_structure = pred_m[:, 1, :, :] - pred_m[:, 0, :, :]
    return PairedInvarianceLosses(
        structure=structure_across_measurement.square().mean(),
        measurement=measurement_across_structure.square().mean(),
    )


@dataclass(frozen=True)
class FactorizationLossBreakdown:
    """Differentiable scalar components of the Stage-1 objective."""

    total: torch.Tensor
    parameter: torch.Tensor
    structure_invariance: torch.Tensor
    measurement_invariance: torch.Tensor
    lambda_pair: float

    @property
    def pair(self) -> torch.Tensor:
        return self.structure_invariance + self.measurement_invariance

    def detached_scalars(self) -> dict[str, float]:
        """Return JSON-safe diagnostics without altering the training graph."""

        return {
            "total": float(self.total.detach().cpu().item()),
            "parameter": float(self.parameter.detach().cpu().item()),
            "structure_invariance": float(
                self.structure_invariance.detach().cpu().item()
            ),
            "measurement_invariance": float(
                self.measurement_invariance.detach().cpu().item()
            ),
            "pair": float(self.pair.detach().cpu().item()),
            "lambda_pair": self.lambda_pair,
        }


def factorization_loss(
    pred_s: torch.Tensor,
    pred_m: torch.Tensor,
    target_s: torch.Tensor,
    target_m: torch.Tensor,
    *,
    lambda_pair: float,
) -> FactorizationLossBreakdown:
    """Compute the matched baseline/factorized objective.

    Use ``lambda_pair=0.0`` for the two-head supervised baseline and
    ``lambda_pair=1.0`` for the frozen Stage-1 factorized model.  No other code
    path, batch shape, or reduction changes between the two conditions.
    """

    weight = float(lambda_pair)
    if not torch.isfinite(torch.tensor(weight)) or weight < 0.0:
        raise ValueError("lambda_pair must be a finite non-negative scalar")
    parameter = parameter_supervision_loss(pred_s, pred_m, target_s, target_m)
    paired = paired_invariance_losses(pred_s, pred_m)
    total = parameter + weight * paired.total
    return FactorizationLossBreakdown(
        total=total,
        parameter=parameter,
        structure_invariance=paired.structure,
        measurement_invariance=paired.measurement,
        lambda_pair=weight,
    )


__all__ = [
    "FACTORIAL_BLOCK_SHAPE_SUFFIX",
    "FactorizationLossBreakdown",
    "PairedInvarianceLosses",
    "factorization_loss",
    "paired_invariance_losses",
    "parameter_mse_loss",
    "parameter_supervision_loss",
]
