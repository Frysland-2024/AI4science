"""1D Patch Transformer for crystal-system classification from PXRD."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TypedDict

import torch
from torch import nn
from torch.nn import functional as F


class BackboneOutput(TypedDict):
    logits: torch.Tensor
    pooled_embedding: torch.Tensor
    main_tokens: torch.Tensor
    prior_tokens: torch.Tensor | None


@dataclass(frozen=True)
class PatchTransformerConfig:
    input_length: int = 3501
    patch_size: int = 16
    patch_stride: int | None = None
    embed_dim: int = 128
    depth: int = 4
    num_heads: int = 4
    mlp_ratio: float = 4.0
    dropout: float = 0.1
    num_classes: int = 7
    pooling: str = "mean"

    def validate(self) -> None:
        stride = self.patch_stride or self.patch_size
        if min(self.input_length, self.patch_size, stride, self.embed_dim, self.depth) <= 0:
            raise ValueError("model dimensions must be positive")
        if self.embed_dim % self.num_heads != 0:
            raise ValueError("embed_dim must be divisible by num_heads")
        if self.mlp_ratio <= 0 or not 0 <= self.dropout < 1:
            raise ValueError("invalid MLP ratio or dropout")
        if self.pooling not in {"mean", "cls"}:
            raise ValueError("pooling must be 'mean' or 'cls'")
        if self.num_classes != 7:
            raise ValueError("the current task requires seven crystal-system classes")


class PatchEmbedding1D(nn.Module):
    def __init__(self, patch_size: int, stride: int, embed_dim: int):
        super().__init__()
        self.patch_size = int(patch_size)
        self.stride = int(stride)
        self.projection = nn.Conv1d(
            1,
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
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3 or x.shape[1] != 1:
            raise ValueError("expected XRD input with shape [batch, length] or [batch, 1, length]")
        padding = self.required_padding(x.shape[-1])
        if padding:
            x = F.pad(x, (0, padding))
        return self.projection(x).transpose(1, 2)


class XRDPatchTransformer(nn.Module):
    """Patch XRD sequences before attention; this is not point-wise vanilla attention."""

    def __init__(self, config: PatchTransformerConfig = PatchTransformerConfig()):
        super().__init__()
        config.validate()
        self.config = config
        stride = config.patch_stride or config.patch_size
        self.patch_embedding = PatchEmbedding1D(config.patch_size, stride, config.embed_dim)
        patch_count = self.patch_embedding.token_count(config.input_length)
        special_tokens = 1 if config.pooling == "cls" else 0
        self.position_embedding = nn.Parameter(
            torch.zeros(1, patch_count + special_tokens, config.embed_dim)
        )
        self.cls_token = (
            nn.Parameter(torch.zeros(1, 1, config.embed_dim))
            if config.pooling == "cls"
            else None
        )
        layer = nn.TransformerEncoderLayer(
            d_model=config.embed_dim,
            nhead=config.num_heads,
            dim_feedforward=int(config.embed_dim * config.mlp_ratio),
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            layer,
            num_layers=config.depth,
            enable_nested_tensor=False,
        )
        self.norm = nn.LayerNorm(config.embed_dim)
        self.head = nn.Linear(config.embed_dim, config.num_classes)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.trunc_normal_(self.position_embedding, std=0.02)
        if self.cls_token is not None:
            nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.head.weight, std=0.02)
        nn.init.zeros_(self.head.bias)

    def _forward_features(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        tokens = self.patch_embedding(x)
        if self.cls_token is not None:
            cls = self.cls_token.expand(tokens.shape[0], -1, -1)
            tokens = torch.cat((cls, tokens), dim=1)
        if tokens.shape[1] > self.position_embedding.shape[1]:
            raise ValueError(
                f"input creates {tokens.shape[1]} tokens but model supports "
                f"{self.position_embedding.shape[1]}"
            )
        tokens = tokens + self.position_embedding[:, : tokens.shape[1]]
        encoded = self.norm(self.encoder(tokens))
        if self.cls_token is not None:
            return encoded[:, 0], encoded
        return encoded.mean(dim=1), encoded

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        pooled, _ = self._forward_features(x)
        return pooled

    def forward(self, x: torch.Tensor) -> BackboneOutput:
        pooled, tokens = self._forward_features(x)
        return {
            "logits": self.head(pooled),
            "pooled_embedding": pooled,
            "main_tokens": tokens,
            "prior_tokens": None,
        }

    @property
    def patch_count(self) -> int:
        return self.patch_embedding.token_count(self.config.input_length)

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
