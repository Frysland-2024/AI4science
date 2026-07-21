"""Pre-norm global and one-way peak-prior attention blocks."""

from __future__ import annotations

import torch
from torch import nn


class _FeedForward(nn.Module):
    def __init__(self, embed_dim: int, mlp_ratio: float, dropout: float) -> None:
        super().__init__()
        hidden = int(embed_dim * mlp_ratio)
        self.net = nn.Sequential(
            nn.Linear(embed_dim, hidden),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden, embed_dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class GlobalSelfAttentionBlock(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int, mlp_ratio: float, dropout: float) -> None:
        super().__init__()
        self.norm_attn = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.norm_mlp = nn.LayerNorm(embed_dim)
        self.mlp = _FeedForward(embed_dim, mlp_ratio, dropout)

    def forward(self, tokens: torch.Tensor) -> torch.Tensor:
        normalized = self.norm_attn(tokens)
        attended, _ = self.attn(normalized, normalized, normalized, need_weights=False)
        tokens = tokens + attended
        return tokens + self.mlp(self.norm_mlp(tokens))


class PeakPriorGuidedAttentionBlock(nn.Module):
    """Query main tokens with prior tokens as key/value; prior tokens stay explicit."""

    def __init__(self, embed_dim: int, num_heads: int, mlp_ratio: float, dropout: float) -> None:
        super().__init__()
        self.norm_query = nn.LayerNorm(embed_dim)
        self.norm_prior = nn.LayerNorm(embed_dim)
        self.attn = nn.MultiheadAttention(embed_dim, num_heads, dropout=dropout, batch_first=True)
        self.norm_mlp = nn.LayerNorm(embed_dim)
        self.mlp = _FeedForward(embed_dim, mlp_ratio, dropout)

    def forward(self, main_tokens: torch.Tensor, prior_tokens: torch.Tensor) -> torch.Tensor:
        query = self.norm_query(main_tokens)
        prior = self.norm_prior(prior_tokens)
        attended, _ = self.attn(query, prior, prior, need_weights=False)
        main_tokens = main_tokens + attended
        return main_tokens + self.mlp(self.norm_mlp(main_tokens))
