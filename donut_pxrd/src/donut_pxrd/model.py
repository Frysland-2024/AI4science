from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


def modified_tanh(value: torch.Tensor) -> torch.Tensor:
    return 1.7159 * torch.tanh((2.0 / 3.0) * value)


class ConvBlock(nn.Module):
    def __init__(self, channels_in: int, channels_out: int, dropout: float) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(channels_in, channels_out, kernel_size=7, stride=2, padding=3),
            nn.BatchNorm1d(channels_out),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Conv1d(channels_out, channels_out, kernel_size=3, padding=1),
            nn.BatchNorm1d(channels_out),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)


class LatentOnlyDecoder(nn.Module):
    """A convolutional decoder whose only input is the physical latent."""

    def __init__(self, latent_dim: int, output_length: int, dropout: float) -> None:
        super().__init__()
        self.output_length = int(output_length)
        self.project = nn.Sequential(nn.Linear(latent_dim, 128 * 32), nn.ReLU(inplace=True))
        self.blocks = nn.Sequential(
            nn.Conv1d(128, 96, 5, padding=2), nn.BatchNorm1d(96), nn.ReLU(inplace=True),
            nn.Dropout(dropout), nn.Conv1d(96, 64, 5, padding=2), nn.BatchNorm1d(64),
            nn.ReLU(inplace=True), nn.Conv1d(64, 32, 5, padding=2), nn.ReLU(inplace=True),
        )
        self.output = nn.Conv1d(32, 1, kernel_size=7, padding=3)

    def forward(self, latent: torch.Tensor) -> torch.Tensor:
        x = self.project(latent).view(latent.shape[0], 128, 32)
        # Nearest interpolation has a deterministic CUDA backward in the
        # frozen physics environment; the kernel learns its local smoothing.
        x = F.interpolate(x, size=self.output_length, mode="nearest")
        return self.output(self.blocks(x))


class DonutPXRD(nn.Module):
    """Encoder -> bounded physical latent -> decoder and fixed-physics branches."""

    def __init__(self, latent_names: tuple[str, ...], output_length: int = 3501, dropout: float = 0.1) -> None:
        super().__init__()
        self.latent_names = tuple(latent_names)
        self.encoder = nn.Sequential(
            ConvBlock(1, 32, dropout),
            ConvBlock(32, 64, dropout),
            ConvBlock(64, 128, dropout),
            ConvBlock(128, 128, dropout),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(128, 128), nn.ReLU(inplace=True), nn.Dropout(dropout),
            nn.Linear(128, len(self.latent_names)),
        )
        self.decoder = LatentOnlyDecoder(len(self.latent_names), output_length, dropout)

    def forward(self, observed: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if observed.ndim == 2:
            observed = observed.unsqueeze(1)
        raw = self.encoder(observed)
        latent = modified_tanh(raw)
        decoded = self.decoder(latent)
        return latent, decoded


def physical_latent(latent: torch.Tensor, latent_names: tuple[str, ...]) -> dict[str, torch.Tensor]:
    """Scale the bounded latent to the frozen PXRD physical coordinates."""
    unit = latent / 1.7159
    out = {"du": 0.8 * unit[:, 0], "dv": 0.8 * unit[:, 1]}
    if "zero_shift" in latent_names:
        out["zero_shift"] = 0.06 * unit[:, 2]
    return out
