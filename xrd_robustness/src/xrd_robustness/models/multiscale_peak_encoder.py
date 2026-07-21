"""Shallow multi-scale local peak morphology encoder for PAMPT."""

from __future__ import annotations

import torch
from torch import nn


class _ChannelLayerNorm(nn.Module):
    def __init__(self, channels: int) -> None:
        super().__init__()
        self.norm = nn.LayerNorm(channels)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.norm(x.transpose(1, 2)).transpose(1, 2)


class MultiscalePeakEncoder(nn.Module):
    """Preserve sequence length while exposing 5/11/21 local receptive fields."""

    def __init__(
        self,
        *,
        in_channels: int = 1,
        branch_channels: int = 32,
        fusion_dim: int = 128,
        kernels: tuple[int, ...] = (5, 11, 21),
    ) -> None:
        super().__init__()
        if not kernels or any(kernel % 2 == 0 for kernel in kernels):
            raise ValueError("multiscale kernels must be non-empty odd integers")
        self.kernels = tuple(kernels)
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(
                        in_channels,
                        in_channels,
                        kernel_size=kernel,
                        padding=kernel // 2,
                        groups=in_channels,
                        bias=False,
                    ),
                    nn.GELU(),
                    nn.Conv1d(in_channels, branch_channels, kernel_size=1),
                    nn.GELU(),
                )
                for kernel in self.kernels
            ]
        )
        self.fusion = nn.Sequential(
            nn.Conv1d(branch_channels * len(self.kernels), fusion_dim, kernel_size=1),
            _ChannelLayerNorm(fusion_dim),
            nn.GELU(),
        )
        self.residual = nn.Conv1d(in_channels, fusion_dim, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3:
            raise ValueError("expected [batch, channels, length]")
        branches = [branch(x) for branch in self.branches]
        fused = self.fusion(torch.cat(branches, dim=1))
        return fused + self.residual(x)
