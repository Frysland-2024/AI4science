"""Lightweight encoder for derivative-based peak morphology priors."""

from __future__ import annotations

import torch
from torch import nn


class PeakPriorEncoder(nn.Module):
    def __init__(self, *, out_channels: int = 128) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(2, 32, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(32, 64, kernel_size=11, padding=5),
            nn.GELU(),
            nn.Conv1d(64, out_channels, kernel_size=1),
        )

    def forward(self, derivatives: torch.Tensor) -> torch.Tensor:
        if derivatives.ndim != 3 or derivatives.shape[1] != 2:
            raise ValueError("expected derivative channels with shape [batch, 2, length]")
        return self.encoder(derivatives)
