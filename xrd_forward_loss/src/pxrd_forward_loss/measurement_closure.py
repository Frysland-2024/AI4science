"""Differentiable expected measurement profile for the one-parent closure pilot.

The forward input is lattice-only q=(du,dv) plus three identifiable measurement
nuisance coordinates eta=(zero shift, FWHM, background amplitude). The smooth
quadratic V9 background shape is fixed by the simulator configuration. This
module never accepts nuisance truth in its reconstruction loss.
"""

from __future__ import annotations

import math

import torch


def expected_intensity_profile(
    forward_model: object,
    q_lattice: torch.Tensor,
    eta: torch.Tensor,
    *,
    normalization_index: int | None = None,
    background_shape_mode: str = "v9_polynomial",
) -> torch.Tensor:
    """Return expected counts-scale intensity before noise and normalization.

    ``q_lattice`` has normalized lattice coordinates. ``eta`` uses degrees for
    shift and FWHM and relative-to-peak units for background amplitude. The
    deterministic smooth background shape is fixed by the known data condition:
    the V9 configured polynomial (variation zero, floor fraction 0.10), or the
    legacy simple-view linear count baseline (100 to 200 counts at scale 30000).
    The signal is rendered
    first, a nonnegative background is added on the reference clean-peak scale.
    No random noise realization is modeled.
    """
    if q_lattice.ndim != 2 or q_lattice.shape[-1] != 2:
        raise ValueError("q_lattice must have shape [batch, 2]")
    if eta.ndim != 2 or eta.shape != (q_lattice.shape[0], 3):
        raise ValueError("eta must have shape [batch, 3]")
    if q_lattice.device != eta.device or q_lattice.dtype != eta.dtype:
        raise ValueError("q_lattice and eta must share device and dtype")

    parameter_config = forward_model.parameter_config
    delta_half_range = float(parameter_config["delta_half_range_deg"])
    width_min = float(parameter_config["fwhm_min_deg"])
    width_max = float(parameter_config["fwhm_max_deg"])
    if not 0 < width_min <= width_max or delta_half_range <= 0:
        raise ValueError("invalid frozen nuisance bounds in forward configuration")

    delta = eta[:, 0]
    fwhm = eta[:, 1]
    width_center = 0.5 * (math.log(width_min) + math.log(width_max))
    width_half_range = 0.5 * (math.log(width_max) - math.log(width_min))
    if width_half_range == 0:
        width_coordinate = torch.zeros_like(fwhm)
    else:
        width_coordinate = (torch.log(fwhm) - width_center) / width_half_range
    full_q = torch.cat(
        (q_lattice, (delta / delta_half_range)[:, None], width_coordinate[:, None]),
        dim=1,
    )
    signal = forward_model.render(
        full_q,
        compatibility=False,
        normalization_index=normalization_index,
        truncate_support=True,
        reference_scale_width_deg=0.08,
    )

    axis = forward_model.axis
    t = 2.0 * (axis - axis[0]) / (axis[-1] - axis[0]) - 1.0
    if background_shape_mode == "v9_polynomial":
        base = 0.8 + 0.15 * t + 0.05 * t.square()
        # V9 background_variation=0 freezes its polynomial coefficients.
        shape = base[None, :].expand(q_lattice.shape[0], -1)
        shape = shape - shape.amin(dim=1, keepdim=True)
        shape_range = shape.amax(dim=1, keepdim=True)
        shape = 0.10 + 0.90 * shape / torch.clamp_min(
            shape_range, torch.finfo(shape.dtype).tiny
        )
    elif background_shape_mode == "simple_linear_counts":
        # The pre-registered simple condition adds a deterministic 100-to-200
        # count ramp before Poisson sampling. Its peak-relative amplitude is
        # eta; the shape is fixed to the corresponding 0.5-to-1.0 ramp.
        coordinate = 0.5 * (t + 1.0)
        shape = (0.5 + 0.5 * coordinate)[None, :].expand(q_lattice.shape[0], -1)
    else:
        raise ValueError(f"unknown background shape mode: {background_shape_mode}")
    background = eta[:, 2:3] * shape
    return torch.clamp_min(signal + background, 0.0)


def expected_profile(
    forward_model: object,
    q_lattice: torch.Tensor,
    eta: torch.Tensor,
    *,
    normalization_index: int | None = None,
    background_shape_mode: str = "v9_polynomial",
) -> torch.Tensor:
    """Normalize and transform the deterministic measurement expectation."""
    expected_raw = expected_intensity_profile(
        forward_model,
        q_lattice,
        eta,
        normalization_index=normalization_index,
        background_shape_mode=background_shape_mode,
    )
    expected_raw = expected_raw / torch.clamp_min(
        expected_raw.amax(dim=1, keepdim=True), torch.finfo(expected_raw.dtype).tiny
    )
    return torch.log1p(100.0 * expected_raw) / math.log(101.0)


def measurement_reconstruction_loss(
    forward_model: object,
    predicted_q: torch.Tensor,
    predicted_eta: torch.Tensor,
    observed_profile: torch.Tensor,
    *,
    background_shape_mode: str = "v9_polynomial",
) -> torch.Tensor:
    """Approximate expected-profile loss; intentionally takes no eta truth."""
    expected = expected_profile(
        forward_model,
        predicted_q,
        predicted_eta,
        background_shape_mode=background_shape_mode,
    )
    if expected.shape != observed_profile.shape:
        raise ValueError("expected and observed profiles must have matching shapes")
    # The input preprocessing max-normalizes after Poisson/readout noise. MSE in
    # the documented log domain is a bounded quasi-likelihood, not a count
    # likelihood and does not fit a particular noise realization.
    return torch.nn.functional.mse_loss(
        expected.to(dtype=observed_profile.dtype), observed_profile
    )


def map_nuisance_logits(
    logits: torch.Tensor,
    *,
    shift_bound_deg: float = 0.06,
    width_min_deg: float = 0.08,
    width_max_deg: float = 0.13,
    background_max: float = 0.01,
) -> torch.Tensor:
    """Map three unconstrained outputs into the pre-registered eta box."""
    if logits.ndim != 2 or logits.shape[1] != 3:
        raise ValueError("nuisance logits must have shape [batch, 3]")
    shift = shift_bound_deg * torch.tanh(logits[:, 0])
    width_fraction = torch.sigmoid(logits[:, 1])
    width = width_min_deg + (width_max_deg - width_min_deg) * width_fraction
    amplitude = background_max * torch.sigmoid(logits[:, 2])
    return torch.stack((shift, width, amplitude), dim=1)
