from __future__ import annotations

import math

import torch
from torch import nn
import torch.nn.functional as F

from pxrd_forward_loss.measurement_closure import expected_profile


def modified_tanh(values: torch.Tensor) -> torch.Tensor:
    """LeCun's bounded bottleneck activation used in the DONUT source."""
    return 1.7159 * torch.tanh((2.0 / 3.0) * values)


def map_latent_to_physics(
    constrained: torch.Tensor,
    *,
    phase: str,
    q_bound: float = 0.8,
    shift_bound_deg: float = 0.06,
    width_min_deg: float = 0.08,
    width_max_deg: float = 0.13,
    background_max: float = 0.01,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Map the common DONUT latent to lattice q and physical nuisance eta."""
    unit = constrained / 1.7159
    q = q_bound * unit[:, :2]
    batch = constrained.shape[0]
    zero = torch.zeros((batch,), device=constrained.device, dtype=constrained.dtype)
    width = torch.full_like(zero, float(width_min_deg))
    background = torch.zeros_like(zero)
    shift = zero

    if phase in {"experiment_2_shift", "experiment_3_width", "experiment_3_background", "experiment_3_noise", "experiment_3_texture"}:
        shift = shift_bound_deg * unit[:, 2]
    if phase in {"experiment_3_width", "experiment_3_background", "experiment_3_noise", "experiment_3_texture"}:
        width = width_min_deg + (unit[:, 3] + 1.0) * 0.5 * (width_max_deg - width_min_deg)
    if phase in {"experiment_3_background", "experiment_3_noise", "experiment_3_texture"}:
        background = (unit[:, 4] + 1.0) * 0.5 * background_max
    eta = torch.stack((shift, width, background), dim=1)
    return q, eta


class DoubleConv1d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, dropout: float = 0.0) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.layers(values)


class DONUTEncoderDecoder(nn.Module):
    """1D six-block DONUT encoder and symmetric latent-only decoder.

    Only the physically constrained latent reaches the decoder. The PXRD
    renderer is deliberately external and fixed, matching the source design's
    parallel reconstruction and physics branches.
    """

    channels = (1, 16, 32, 64, 128, 256, 256)
    pool_count = 6

    def __init__(
        self,
        *,
        input_length: int = 3501,
        latent_dim: int,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        if input_length < 64 or latent_dim not in {2, 3, 4, 5}:
            raise ValueError("input_length must be >=64 and latent_dim must be 2..5")
        self.input_length = int(input_length)
        self.latent_dim = int(latent_dim)
        down_lengths = [self.input_length]
        for _ in range(self.pool_count):
            down_lengths.append(down_lengths[-1] // 2)
        self.bottleneck_length = down_lengths[-1]
        if self.bottleneck_length < 1:
            raise ValueError("input is too short for six encoder pooling blocks")

        self.encoder_blocks = nn.ModuleList(
            [
                DoubleConv1d(self.channels[i], self.channels[i + 1], dropout)
                for i in range(self.pool_count)
            ]
        )
        self.pool = nn.MaxPool1d(kernel_size=2, stride=2)
        flattened = self.channels[-1] * self.bottleneck_length
        self.encoder_fc = nn.Linear(flattened, self.latent_dim)

        self.decoder_fc = nn.Linear(self.latent_dim, flattened)
        decoder_channels = (256, 256, 128, 64, 32, 16, 1)
        self.decoder_blocks = nn.ModuleList(
            [
                DoubleConv1d(decoder_channels[i], decoder_channels[i + 1], dropout)
                for i in range(self.pool_count)
            ]
        )

    def encode(self, profile: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if profile.ndim == 2:
            profile = profile.unsqueeze(1)
        if profile.ndim != 3 or profile.shape[1] != 1 or profile.shape[-1] != self.input_length:
            raise ValueError("profile must have shape [batch, input_length] or [batch, 1, input_length]")
        values = profile
        for block in self.encoder_blocks:
            values = self.pool(block(values))
        raw = self.encoder_fc(torch.flatten(values, start_dim=1))
        constrained = modified_tanh(raw)
        return raw, constrained

    def decode(self, constrained: torch.Tensor) -> torch.Tensor:
        values = self.decoder_fc(constrained)
        values = values.view(values.shape[0], self.channels[-1], self.bottleneck_length)
        for block in self.decoder_blocks:
            values = F.interpolate(values, scale_factor=2.0, mode="linear", align_corners=False)
            values = block(values)
        if values.shape[-1] != self.input_length:
            values = F.interpolate(values, size=self.input_length, mode="linear", align_corners=False)
        return values[:, 0, :]

    def forward(self, profile: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        raw, constrained = self.encode(profile)
        reconstruction = self.decode(constrained)
        return reconstruction, raw, constrained


def physical_profile(
    forward_model: object,
    constrained: torch.Tensor,
    *,
    phase: str,
    background_shape_mode: str = "v9_polynomial",
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    q, eta = map_latent_to_physics(constrained, phase=phase)
    profile = expected_profile(
        forward_model,
        q.to(torch.float64),
        eta.to(torch.float64),
        background_shape_mode=background_shape_mode,
    )
    return profile.to(torch.float32), q, eta
