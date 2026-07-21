"""Peak-Aware Multi-Scale Patch Transformer (PAMPT) for PXRD."""

from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn

from .derivative_channels import DerivativeChannels
from .multiscale_peak_encoder import MultiscalePeakEncoder
from .overlap_patch_embedding_1d import OverlapPatchEmbedding1D
from .patch_transformer import BackboneOutput
from .peak_prior_attention_block import GlobalSelfAttentionBlock, PeakPriorGuidedAttentionBlock
from .peak_prior_encoder import PeakPriorEncoder


@dataclass(frozen=True)
class PAMPTConfig:
    variant: str = "b3"
    input_length: int = 3501
    patch_size: int = 16
    patch_stride: int = 8
    embed_dim: int = 128
    depth: int = 4
    num_heads: int = 4
    mlp_ratio: float = 4.0
    dropout: float = 0.1
    pooling: str = "mean"
    num_classes: int = 7
    local_kernels: tuple[int, ...] = (5, 11, 21)
    branch_channels: int = 32
    fusion_dim: int = 128

    def __post_init__(self) -> None:
        if self.variant == "b0" and self.patch_stride != self.patch_size:
            object.__setattr__(self, "patch_stride", self.patch_size)

    def validate(self) -> None:
        if self.variant not in {"b0", "b1", "b2", "b3"}:
            raise ValueError("variant must be one of b0, b1, b2, b3")
        if self.variant == "b3" and self.depth != 4:
            raise ValueError("V7 B3 uses exactly four alternating attention blocks")
        if min(self.input_length, self.patch_size, self.patch_stride, self.embed_dim, self.depth) <= 0:
            raise ValueError("model dimensions must be positive")
        if self.patch_stride > self.patch_size:
            raise ValueError("patch_stride cannot exceed patch_size")
        if self.embed_dim % self.num_heads != 0:
            raise ValueError("embed_dim must be divisible by num_heads")
        if self.pooling not in {"mean", "cls"}:
            raise ValueError("pooling must be mean or cls")
        if self.num_classes != 7:
            raise ValueError("the current task requires seven crystal-system classes")


class PAMPT(nn.Module):
    """Single configurable implementation of the V7 B0-B3 ablation chain."""

    def __init__(self, config: PAMPTConfig = PAMPTConfig()) -> None:
        super().__init__()
        config.validate()
        self.config = config
        self.variant = config.variant
        use_local = config.variant in {"b1", "b2", "b3"}
        use_prior = config.variant in {"b2", "b3"}
        self.derivatives = DerivativeChannels() if use_prior else None
        self.local_encoder = (
            MultiscalePeakEncoder(
                branch_channels=config.branch_channels,
                fusion_dim=config.fusion_dim,
                kernels=config.local_kernels,
            )
            if use_local
            else None
        )
        signal_channels = config.fusion_dim if use_local else 1
        self.signal_patch = OverlapPatchEmbedding1D(
            signal_channels,
            patch_size=config.patch_size,
            stride=config.patch_stride if use_local else config.patch_size,
            embed_dim=config.embed_dim,
        )
        self.prior_encoder = PeakPriorEncoder(out_channels=config.fusion_dim) if use_prior else None
        self.prior_patch = (
            OverlapPatchEmbedding1D(
                config.fusion_dim,
                patch_size=config.patch_size,
                stride=config.patch_stride,
                embed_dim=config.embed_dim,
            )
            if use_prior
            else None
        )
        self.prior_fusion = nn.Linear(config.embed_dim, config.embed_dim) if config.variant == "b2" else None
        token_count = self.signal_patch.token_count(config.input_length)
        special = 1 if config.pooling == "cls" else 0
        self.position_embedding = nn.Parameter(
            torch.zeros(1, token_count + special, config.embed_dim)
        )
        self.cls_token = nn.Parameter(torch.zeros(1, 1, config.embed_dim)) if special else None
        if config.variant == "b3":
            block_types = ("self", "guided", "self", "guided")
        else:
            block_types = tuple("self" for _ in range(config.depth))
        self.blocks = nn.ModuleList(
            [
                GlobalSelfAttentionBlock(config.embed_dim, config.num_heads, config.mlp_ratio, config.dropout)
                if block_type == "self"
                else PeakPriorGuidedAttentionBlock(
                    config.embed_dim, config.num_heads, config.mlp_ratio, config.dropout
                )
                for block_type in block_types
            ]
        )
        self.block_types = block_types
        self.norm = nn.LayerNorm(config.embed_dim)
        self.head = nn.Linear(config.embed_dim, config.num_classes)
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.trunc_normal_(self.position_embedding, std=0.02)
        if self.cls_token is not None:
            nn.init.trunc_normal_(self.cls_token, std=0.02)
        nn.init.trunc_normal_(self.head.weight, std=0.02)
        nn.init.zeros_(self.head.bias)

    def _add_position(self, tokens: torch.Tensor, *, has_cls: bool) -> torch.Tensor:
        expected = tokens.shape[1]
        if expected > self.position_embedding.shape[1]:
            raise ValueError(
                f"input creates {expected} tokens but model supports {self.position_embedding.shape[1]}"
            )
        return tokens + self.position_embedding[:, :expected]

    def encode(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
        if x.ndim == 2:
            x = x.unsqueeze(1)
        if x.ndim != 3 or x.shape[1] != 1:
            raise ValueError("expected XRD input with shape [batch, length] or [batch, 1, length]")
        signal = self.local_encoder(x) if self.local_encoder is not None else x
        main_tokens = self.signal_patch(signal)
        prior_tokens = None
        if self.derivatives is not None and self.prior_encoder is not None and self.prior_patch is not None:
            prior = self.prior_encoder(self.derivatives(x))
            prior_tokens = self.prior_patch(prior)
            if prior_tokens.shape[1] != main_tokens.shape[1]:
                raise RuntimeError("main and prior token counts must match")
            if self.prior_fusion is not None:
                main_tokens = main_tokens + self.prior_fusion(prior_tokens)
        if self.cls_token is not None:
            cls = self.cls_token.expand(main_tokens.shape[0], -1, -1)
            main_tokens = torch.cat((cls, main_tokens), dim=1)
        main_tokens = self._add_position(main_tokens, has_cls=self.cls_token is not None)
        if prior_tokens is not None:
            offset = 1 if self.cls_token is not None else 0
            prior_tokens = prior_tokens + self.position_embedding[:, offset : offset + prior_tokens.shape[1]]
        for block_type, block in zip(self.block_types, self.blocks, strict=True):
            if block_type == "guided":
                if prior_tokens is None:
                    raise RuntimeError("guided attention requires prior tokens")
                main_tokens = block(main_tokens, prior_tokens)
            else:
                main_tokens = block(main_tokens)
        encoded = self.norm(main_tokens)
        pooled = encoded[:, 0] if self.cls_token is not None else encoded.mean(dim=1)
        return pooled, encoded, prior_tokens

    def forward(self, x: torch.Tensor) -> BackboneOutput:
        pooled, main_tokens, prior_tokens = self.encode(x)
        return {
            "logits": self.head(pooled),
            "pooled_embedding": pooled,
            "main_tokens": main_tokens,
            "prior_tokens": prior_tokens,
        }

    @property
    def patch_count(self) -> int:
        return self.signal_patch.token_count(self.config.input_length)

    @property
    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
