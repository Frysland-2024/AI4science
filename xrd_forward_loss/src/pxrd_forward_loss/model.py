"""Regression wrapper around the repository's established 1D ResNet-GN."""

from __future__ import annotations

import torch
from torch import nn

from xrd_robustness.models.ml4pxrd_resnet1d import (
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)


class ParameterRegressor(nn.Module):
    """Same ResNet backbone for A/B, with two bounded continuous outputs."""

    def __init__(self, *, input_length: int = 3501, bound: float = 0.8) -> None:
        super().__init__()
        self.bound = float(bound)
        if self.bound <= 0:
            raise ValueError("output bound must be positive")
        self.backbone = ML4PXRDResNet1D(
            ML4PXRDResNet1DConfig(
                model_id="18",
                input_length=int(input_length),
                num_classes=2,
                group_norm_groups=32,
                add_additional_dense_layer=True,
                dense_width=256,
                embed_dim=256,
            )
        )
        # The source classifier's Xavier head saturates a tanh regression
        # output immediately on this narrow single-parent task. Start the
        # continuous head near zero so both objectives receive usable output
        # gradients while retaining the same backbone and head for A/B.
        nn.init.normal_(self.backbone.head.weight, mean=0.0, std=1e-3)
        if self.backbone.head.bias is not None:
            nn.init.zeros_(self.backbone.head.bias)

    def forward(self, profile: torch.Tensor) -> torch.Tensor:
        return self.bound * torch.tanh(self.backbone(profile)["logits"])


def compose_full_q(q_lattice: torch.Tensor) -> torch.Tensor:
    """Append fixed zero-shift and minimum-width nuisance coordinates."""

    if q_lattice.ndim != 2 or q_lattice.shape[1] != 2:
        raise ValueError("lattice parameter tensor must have shape [batch, 2]")
    zero = torch.zeros_like(q_lattice[:, :1])
    narrow_width = -torch.ones_like(q_lattice[:, :1])
    return torch.cat((q_lattice, zero, narrow_width), dim=1)
