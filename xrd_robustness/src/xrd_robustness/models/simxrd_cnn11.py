"""1D CNN11-style PXRD classifier following the published SimXRD design."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class SimXRDCNN11Config:
    input_length: int = 3501
    num_classes: int = 7
    conv_channels: int = 80
    dropout_conv: float = 0.3
    dropout_dense: float = 0.5
    dense_widths: tuple[int, int] = (2300, 1150)

    def validate(self) -> None:
        if self.input_length <= 0 or self.num_classes <= 1 or self.conv_channels <= 0:
            raise ValueError("invalid CNN11 dimensions")
        if not 0.0 <= self.dropout_conv < 1.0 or not 0.0 <= self.dropout_dense < 1.0:
            raise ValueError("dropout probabilities must be in [0, 1)")
        length = self.input_length
        for kernel, stride in ((100, 5), (50, 5), (25, 2)):
            length = (length - kernel) // stride + 1
        if length <= 0:
            raise ValueError("input is too short for CNN11 valid convolutions")


class SimXRDCNN11(nn.Module):
    """No-pooling Conv1d stack and dense head; returns raw class logits."""

    def __init__(self, config: SimXRDCNN11Config = SimXRDCNN11Config()):
        super().__init__()
        config.validate()
        self.config = config
        channels = config.conv_channels
        self.features = nn.Sequential(
            nn.Conv1d(1, channels, kernel_size=100, stride=5, padding=0),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout_conv),
            nn.Conv1d(channels, channels, kernel_size=50, stride=5, padding=0),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout_conv),
            nn.Conv1d(channels, channels, kernel_size=25, stride=2, padding=0),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout_conv),
        )
        length = config.input_length
        for kernel, stride in ((100, 5), (50, 5), (25, 2)):
            length = (length - kernel) // stride + 1
        self.final_length = length
        flattened = channels * length
        first, second = config.dense_widths
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flattened, first),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout_dense),
            nn.Linear(first, second),
            nn.ReLU(inplace=True),
            nn.Dropout(config.dropout_dense),
            nn.Linear(second, config.num_classes),
        )
        self._check_numerics = False

    def enable_numerical_checks(self, enabled: bool = True) -> None:
        """Enable one-sync-per-forward checks for every CNN activation."""

        self._check_numerics = bool(enabled)

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor | None]:
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3 or x.shape[1] != 1 or x.shape[-1] != self.config.input_length:
            raise ValueError(
                f"expected [batch, 1, {self.config.input_length}] or "
                f"[batch, {self.config.input_length}] input"
            )
        if not self._check_numerics:
            features = self.features(x)
            flat = torch.flatten(features, 1)
            logits = self.classifier(flat)
        else:
            checks: list[tuple[str, torch.Tensor]] = [("input", x)]
            features = x
            for name, layer in self.features.named_children():
                features = layer(features)
                checks.append((f"features.{name}", features))
            flat = torch.flatten(features, 1)
            checks.append(("flatten", flat))
            logits = flat
            for name, layer in self.classifier.named_children():
                logits = layer(logits)
                checks.append((f"classifier.{name}", logits))

            finite_flags = torch.stack([torch.isfinite(value).all() for _, value in checks])
            if not bool(finite_flags.all().item()):
                bad_stages = [
                    name
                    for (name, _), finite in zip(checks, finite_flags)
                    if not bool(finite.item())
                ]
                raise FloatingPointError(
                    "nonfinite CNN11 activation(s): " + ", ".join(bad_stages)
                )
        return {
            "logits": logits,
            "pooled_embedding": flat,
            "main_tokens": features.transpose(1, 2),
            "prior_tokens": None,
        }

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
