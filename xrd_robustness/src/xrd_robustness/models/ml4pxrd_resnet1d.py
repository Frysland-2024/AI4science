"""PyTorch port of the ML4pXRDs 1D ResNet family.

The port follows ``training/utils/resnet_keras_1D.py`` and
``training/models.py::build_model_resnet_i`` from ML4pXRDs.  The operational
Gate-3 baseline is ResNet-18 with GroupNorm, the source ``square_kernel_size_and_stride``
policy, a flattened final feature map, a linear 256-unit layer, and a final
linear seven-class classifier.  No activation is inserted between the two
Dense layers because the source implementation does not add one.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Final

import torch
from torch import nn
from torch.nn import functional as F

from .patch_transformer import BackboneOutput


_RESNET_SPECS: Final[dict[str, tuple[tuple[int, int], ...]]] = {
    "10": ((64, 1), (128, 1), (256, 1), (512, 1)),
    "18": ((64, 2), (128, 2), (256, 2), (512, 2)),
    "custom_10": ((16, 1), (32, 1), (64, 1), (128, 1)),
}


@dataclass(frozen=True)
class ML4PXRDResNet1DConfig:
    """Configuration for the source-faithful basic-block ML4pXRDs ResNet."""

    model_id: str = "18"
    input_length: int = 3501
    num_classes: int = 7
    group_norm_groups: int = 32
    group_norm_eps: float = 1e-3
    square_kernel_size_and_stride: bool = True
    add_additional_dense_layer: bool = True
    dense_width: int = 256
    embed_dim: int = 256

    def validate(self) -> None:
        if self.model_id not in _RESNET_SPECS:
            raise ValueError(f"model_id must be one of {sorted(_RESNET_SPECS)}")
        if self.input_length <= 0 or self.num_classes <= 1:
            raise ValueError("input_length and num_classes must be positive")
        if self.group_norm_groups <= 0 or self.group_norm_eps <= 0:
            raise ValueError("GroupNorm settings must be positive")
        if self.dense_width <= 0 or self.embed_dim != self.dense_width:
            raise ValueError("embed_dim must equal the source dense_width")
        for channels, _ in _RESNET_SPECS[self.model_id]:
            groups = min(self.group_norm_groups, channels)
            if channels % groups != 0:
                raise ValueError(
                    f"channels={channels} is not divisible by resolved GroupNorm groups={groups}"
                )


class _SamePadConv1d(nn.Module):
    """Conv1d with TensorFlow/Keras ``padding='same'`` semantics."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int = 1,
        *,
        bias: bool = False,
    ) -> None:
        super().__init__()
        self.kernel_size = int(kernel_size)
        self.stride = int(stride)
        self.conv = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size=self.kernel_size,
            stride=self.stride,
            padding=0,
            bias=bias,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        length = int(x.shape[-1])
        output_length = math.ceil(length / self.stride)
        total_padding = max(
            (output_length - 1) * self.stride + self.kernel_size - length,
            0,
        )
        left = total_padding // 2
        right = total_padding - left
        if total_padding:
            x = F.pad(x, (left, right))
        return self.conv(x)


class _SamePadMaxPool1d(nn.Module):
    """MaxPool1d with TensorFlow/Keras ``padding='same'`` semantics."""

    def __init__(self, kernel_size: int, stride: int) -> None:
        super().__init__()
        self.kernel_size = int(kernel_size)
        self.stride = int(stride)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        length = int(x.shape[-1])
        output_length = math.ceil(length / self.stride)
        total_padding = max(
            (output_length - 1) * self.stride + self.kernel_size - length,
            0,
        )
        left = total_padding // 2
        right = total_padding - left
        if total_padding:
            x = F.pad(x, (left, right), value=float("-inf"))
        return F.max_pool1d(x, kernel_size=self.kernel_size, stride=self.stride)


def _group_norm(channels: int, config: ML4PXRDResNet1DConfig) -> nn.GroupNorm:
    groups = min(config.group_norm_groups, channels)
    if channels % groups != 0:
        raise ValueError(f"channels={channels} is not divisible by groups={groups}")
    return nn.GroupNorm(groups, channels, eps=config.group_norm_eps, affine=True)


class _BasicResidualBlock1D(nn.Module):
    """Post-activation residual block matching ML4pXRDs ``ResidualBlock``."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        stride: int,
        config: ML4PXRDResNet1DConfig,
        *,
        use_projection: bool,
    ) -> None:
        super().__init__()
        kernel = 9 if config.square_kernel_size_and_stride else 3
        self.projection = None
        self.projection_norm = None
        if use_projection:
            self.projection = _SamePadConv1d(
                in_channels,
                out_channels,
                kernel_size=1,
                stride=stride,
                bias=False,
            )
            self.projection_norm = _group_norm(out_channels, config)
        self.conv1 = _SamePadConv1d(
            in_channels,
            out_channels,
            kernel_size=kernel,
            stride=stride,
            bias=False,
        )
        self.norm1 = _group_norm(out_channels, config)
        self.conv2 = _SamePadConv1d(
            out_channels,
            out_channels,
            kernel_size=kernel,
            stride=1,
            bias=False,
        )
        self.norm2 = _group_norm(out_channels, config)
        self.activation = nn.ReLU(inplace=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        shortcut = x
        if self.projection is not None:
            shortcut = self.projection(x)
            assert self.projection_norm is not None
            shortcut = self.projection_norm(shortcut)
        y = self.activation(self.norm1(self.conv1(x)))
        y = self.norm2(self.conv2(y))
        return self.activation(y + shortcut)


class ML4PXRDResNet1D(nn.Module):
    """Source-faithful basic-block ML4pXRDs ResNet with a compatible output API."""

    def __init__(self, config: ML4PXRDResNet1DConfig = ML4PXRDResNet1DConfig()) -> None:
        super().__init__()
        config.validate()
        self.config = config
        self.stem = _SamePadConv1d(1, 64, kernel_size=7, stride=2, bias=False)
        self.stem_norm = _group_norm(64, config)
        self.stem_activation = nn.ReLU(inplace=False)
        self.stem_pool = _SamePadMaxPool1d(kernel_size=3, stride=2)

        groups: list[nn.Module] = []
        in_channels = 64
        stage_stride = 4 if config.square_kernel_size_and_stride else 2
        for stage_index, (out_channels, repeats) in enumerate(_RESNET_SPECS[config.model_id]):
            stride = 1 if stage_index == 0 else stage_stride
            blocks: list[nn.Module] = [
                _BasicResidualBlock1D(
                    in_channels,
                    out_channels,
                    stride,
                    config,
                    use_projection=True,
                )
            ]
            for _ in range(1, repeats):
                blocks.append(
                    _BasicResidualBlock1D(
                        out_channels,
                        out_channels,
                        1,
                        config,
                        use_projection=False,
                    )
                )
            groups.append(nn.Sequential(*blocks))
            in_channels = out_channels
        self.stages = nn.ModuleList(groups)

        final_length = self._feature_length(config.input_length)
        self.final_channels = in_channels
        self.final_length = final_length
        flattened = self.final_channels * self.final_length
        if config.add_additional_dense_layer:
            self.embedding = nn.Linear(flattened, config.dense_width)
            self.head = nn.Linear(config.dense_width, config.num_classes)
        else:
            self.embedding = nn.Identity()
            self.head = nn.Linear(flattened, config.num_classes)
        self.reset_parameters()

    def _feature_length(self, length: int) -> int:
        length = math.ceil(length / 2)
        length = math.ceil(length / 2)
        stride = 4 if self.config.square_kernel_size_and_stride else 2
        for stage_index in range(len(_RESNET_SPECS[self.config.model_id])):
            if stage_index > 0:
                length = math.ceil(length / stride)
        return length

    @staticmethod
    def _keras_variance_scaling_(weight: torch.Tensor) -> None:
        fan_in, _ = nn.init._calculate_fan_in_and_fan_out(weight)
        corrected_std = math.sqrt(1.0 / fan_in) / 0.87962566103423978
        nn.init.trunc_normal_(
            weight,
            mean=0.0,
            std=corrected_std,
            a=-2 * corrected_std,
            b=2 * corrected_std,
        )

    def reset_parameters(self) -> None:
        for module in self.modules():
            if isinstance(module, nn.Conv1d):
                self._keras_variance_scaling_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.GroupNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3 or x.shape[1] != 1:
            raise ValueError("expected XRD input with shape [batch, length] or [batch, 1, length]")
        if x.shape[-1] != self.config.input_length:
            raise ValueError(
                f"expected input length {self.config.input_length}, got {x.shape[-1]}"
            )
        features = self.stem_pool(self.stem_activation(self.stem_norm(self.stem(x))))
        for stage in self.stages:
            features = stage(features)
        flat = torch.flatten(features, 1)
        embedding = self.embedding(flat)
        return embedding, features

    def forward(self, x: torch.Tensor) -> BackboneOutput:
        embedding, features = self.encode(x)
        return {
            "logits": self.head(embedding),
            "pooled_embedding": embedding,
            "main_tokens": features.transpose(1, 2),
            "prior_tokens": None,
        }

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
