"""One-dimensional patch embedding with explicit right-edge coverage."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class OverlapPatchEmbedding1D(nn.Module):
    def __init__(self, in_channels: int, patch_size: int = 16, stride: int = 8, embed_dim: int = 128):
        super().__init__()
        if patch_size <= 0 or stride <= 0 or stride > patch_size:
            raise ValueError("patch_size must be positive and stride must be in (0, patch_size]")
        self.patch_size = int(patch_size)
        self.stride = int(stride)
        self.projection = nn.Conv1d(
            in_channels,
            embed_dim,
            kernel_size=self.patch_size,
            stride=self.stride,
        )

    def required_padding(self, length: int) -> int:
        if length <= self.patch_size:
            return self.patch_size - length
        remainder = (length - self.patch_size) % self.stride
        return (self.stride - remainder) % self.stride

    def token_count(self, length: int) -> int:
        padded = length + self.required_padding(length)
        return 1 + (padded - self.patch_size) // self.stride

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim != 3:
            raise ValueError("expected [batch, channels, length]")
        padding = self.required_padding(x.shape[-1])
        if padding:
            x = F.pad(x, (0, padding))
        return self.projection(x).transpose(1, 2)
