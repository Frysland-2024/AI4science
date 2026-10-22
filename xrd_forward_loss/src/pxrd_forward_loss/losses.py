"""Only the two pre-registered objective functions used in the pilot."""

from __future__ import annotations

import torch
from torch.nn import functional as F

from .model import compose_full_q


def paired_losses(
    predicted_q: torch.Tensor,
    target_q: torch.Tensor,
    observed_profile: torch.Tensor,
    *,
    forward_model: object | None = None,
    reconstruction_weight: float = 0.0,
) -> dict[str, torch.Tensor]:
    """Return supervised loss and, when requested, differentiable reconstruction loss."""

    parameter_loss = F.mse_loss(predicted_q, target_q)
    if reconstruction_weight < 0:
        raise ValueError("reconstruction weight must be nonnegative")
    if reconstruction_weight == 0:
        reconstruction_loss = parameter_loss.new_zeros(())
        total = parameter_loss
    else:
        if forward_model is None:
            raise ValueError("forward_model is required when reconstruction is active")
        reconstructed = forward_model.transformed(compose_full_q(predicted_q))
        reconstruction_loss = F.mse_loss(
            reconstructed.to(dtype=observed_profile.dtype), observed_profile
        )
        total = parameter_loss + float(reconstruction_weight) * reconstruction_loss
    return {
        "total": total,
        "parameter": parameter_loss,
        "reconstruction": reconstruction_loss,
    }
