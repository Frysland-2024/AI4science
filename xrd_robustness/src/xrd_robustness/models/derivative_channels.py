"""Deterministic derivative priors computed directly from one XRD signal."""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class DerivativeChannels(nn.Module):
    """Return first and second finite differences with reflect boundaries."""

    def __init__(self) -> None:
        super().__init__()
        self.register_buffer(
            "first_kernel",
            torch.tensor([-0.5, 0.0, 0.5], dtype=torch.float32).view(1, 1, 3),
        )
        self.register_buffer(
            "second_kernel",
            torch.tensor([1.0, -2.0, 1.0], dtype=torch.float32).view(1, 1, 3),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3 or x.shape[1] != 1:
            raise ValueError("expected XRD input with shape [batch, length] or [batch, 1, length]")
        if x.shape[-1] < 2:
            padded = F.pad(x, (1, 1), mode="replicate")
        else:
            padded = F.pad(x, (1, 1), mode="reflect")
        first = F.conv1d(padded, self.first_kernel.to(dtype=x.dtype, device=x.device))
        second = F.conv1d(padded, self.second_kernel.to(dtype=x.dtype, device=x.device))
        return torch.cat((first, second), dim=1)
