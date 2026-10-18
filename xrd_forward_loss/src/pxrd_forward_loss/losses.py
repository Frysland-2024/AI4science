"""Only the two pre-registered objective functions used in the pilot."""

from __future__ import annotations

import torch
from torch.nn import functional as F

from .model import compose_full_q
from .measurement_closure import measurement_reconstruction_loss


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


def clean_reference_paired_losses(
    predicted_q: torch.Tensor,
    target_q: torch.Tensor,
    clean_reference_profile: torch.Tensor,
    *,
    forward_model: object | None = None,
    reconstruction_weight: float = 0.0,
) -> dict[str, torch.Tensor]:
    """Use the explicitly named simulator-supervised clean-reference objective.

    ``clean_reference_profile`` is the simulator's transformed, unperturbed
    profile. It is distinct from the noisy or nuisance-perturbed network input.
    This loss is appropriate only when such a clean simulator target exists;
    it does not imply an unsupervised loss on real measured spectra.
    """

    parameter_loss = F.mse_loss(predicted_q, target_q)
    if reconstruction_weight < 0:
        raise ValueError("reconstruction weight must be nonnegative")
    if reconstruction_weight == 0:
        reconstruction_loss = parameter_loss.new_zeros(())
        total = parameter_loss
    else:
        if forward_model is None:
            raise ValueError("forward_model is required when reconstruction is active")
        reconstructed_clean = forward_model.transformed(compose_full_q(predicted_q))
        reconstruction_loss = F.mse_loss(
            reconstructed_clean.to(dtype=clean_reference_profile.dtype),
            clean_reference_profile,
        )
        total = parameter_loss + float(reconstruction_weight) * reconstruction_loss
    return {
        "total": total,
        "parameter": parameter_loss,
        "reconstruction": reconstruction_loss,
    }


def measurement_aware_paired_losses(
    predicted_q: torch.Tensor,
    predicted_eta: torch.Tensor,
    target_q: torch.Tensor,
    observed_profile: torch.Tensor,
    *,
    forward_model: object,
    reconstruction_weight: float = 1.0,
    background_shape_mode: str = "v9_polynomial",
) -> dict[str, torch.Tensor]:
    """Supervised q plus expected measurement-profile reconstruction.

    This deployable loss deliberately receives predicted nuisance estimates and
    the observed profile only; simulator nuisance truth is excluded.
    """
    if reconstruction_weight < 0:
        raise ValueError("reconstruction weight must be nonnegative")
    parameter_loss = F.mse_loss(predicted_q, target_q)
    reconstruction_loss = measurement_reconstruction_loss(
        forward_model,
        predicted_q,
        predicted_eta,
        observed_profile,
        background_shape_mode=background_shape_mode,
    )
    return {
        "total": parameter_loss + float(reconstruction_weight) * reconstruction_loss,
        "parameter": parameter_loss,
        "reconstruction": reconstruction_loss,
    }
