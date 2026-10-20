"""Fixed Issue 44 sequence architectures; no architecture or seed search."""
from __future__ import annotations

import torch
from torch import nn


class ResidualBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, out_channels, 5, stride=stride, padding=2, bias=False)
        self.norm1 = nn.GroupNorm(4, out_channels)
        self.conv2 = nn.Conv1d(out_channels, out_channels, 5, padding=2, bias=False)
        self.norm2 = nn.GroupNorm(4, out_channels)
        self.skip = (nn.Identity() if in_channels == out_channels and stride == 1 else
                     nn.Sequential(nn.Conv1d(in_channels, out_channels, 1, stride=stride, bias=False),
                                   nn.GroupNorm(4, out_channels)))
        self.act = nn.SiLU()

    def forward(self, x):
        residual = self.skip(x)
        x = self.act(self.norm1(self.conv1(x)))
        x = self.norm2(self.conv2(x))
        return self.act(x + residual)


class ResNet1D(nn.Module):
    def __init__(self, ndim: int):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv1d(1, 24, 9, stride=4, padding=4, bias=False),
                                  nn.GroupNorm(4, 24), nn.SiLU())
        self.blocks = nn.Sequential(ResidualBlock(24, 24), ResidualBlock(24, 24),
                                    ResidualBlock(24, 48, stride=2), ResidualBlock(48, 48),
                                    ResidualBlock(48, 48))
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(48, ndim), nn.Tanh())

    def forward(self, x):
        return self.head(self.pool(self.blocks(self.stem(x[:, None, :]))))


class PatchTransformer(nn.Module):
    def __init__(self, ndim: int, input_length: int = 1024, patch_size: int = 16,
                 embedding_dim: int = 32, layers: int = 2, heads: int = 4,
                 feedforward_dim: int = 64):
        super().__init__()
        if input_length % patch_size:
            raise ValueError("input length must be divisible by patch size")
        self.patch = nn.Conv1d(1, embedding_dim, kernel_size=patch_size, stride=patch_size)
        self.position = nn.Parameter(torch.zeros(1, input_length // patch_size, embedding_dim))
        layer = nn.TransformerEncoderLayer(d_model=embedding_dim, nhead=heads,
                 dim_feedforward=feedforward_dim, dropout=0.0, activation="gelu",
                 batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=layers, enable_nested_tensor=False)
        self.head = nn.Sequential(nn.LayerNorm(embedding_dim), nn.Linear(embedding_dim, ndim), nn.Tanh())
        nn.init.trunc_normal_(self.position, std=0.02)

    def forward(self, x):
        if x.shape[-1] != self.position.shape[1] * self.patch.stride[0]:
            raise ValueError("profile length differs from frozen transformer input length")
        tokens = self.patch(x[:, None, :]).transpose(1, 2)
        return self.head(self.encoder(tokens + self.position).mean(dim=1))


def build(name: str, ndim: int, input_length: int = 1024) -> nn.Module:
    if name == "resnet1d":
        return ResNet1D(ndim)
    if name == "transformer":
        return PatchTransformer(ndim, input_length=input_length)
    raise ValueError(f"unregistered architecture: {name}")
