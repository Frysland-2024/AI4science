"""Small two-head models for the Stage-1 factorization pilot.

The public tensor contract is intentionally narrow:

* spectra: ``[N, 3, L]`` with channels ``x_obs, x_ref, x_diff``;
* structure prediction: ``[N, 2]`` ordered as ``q_u, q_v``;
* measurement prediction: ``[N, 2]`` ordered as ``q_delta, q_w``;
* factorial blocks: ``[B, 2, 2, 3, L]``, where the middle axes are
  structure state then measurement state.

Predictions are mapped through ``tanh`` into the renderer's normalized
``q`` domain.  Physical-unit decoding belongs in ``parameterization.py``.
"""

from __future__ import annotations

import math
from typing import Final

import torch
from torch import Tensor, nn
from torch.nn import functional as F


INPUT_CHANNEL_ORDER: Final[tuple[str, str, str]] = ("x_obs", "x_ref", "x_diff")
STRUCTURE_PARAMETER_ORDER: Final[tuple[str, str]] = ("q_u", "q_v")
MEASUREMENT_PARAMETER_ORDER: Final[tuple[str, str]] = ("q_delta", "q_w")
FACTORIAL_BLOCK_AXIS_ORDER: Final[tuple[str, ...]] = (
    "batch",
    "structure_state",
    "measurement_state",
    "channel",
    "two_theta",
)


class DeterministicSegmentMean1d(nn.Module):
    """Pool contiguous segments using deterministic reductions only.

    CUDA does not provide a deterministic backward for adaptive average pool
    on the pilot runtime.  This finite replacement pads on the right with
    zeros, reshapes to equally sized contiguous segments, and divides each
    segment by its actual (unpadded) count.  It preserves every input position
    and has the same fixed output-size role without using adaptive-pool CUDA.
    """

    def __init__(self, output_size: int) -> None:
        super().__init__()
        if not isinstance(output_size, int) or output_size <= 0:
            raise ValueError("output_size must be a positive integer")
        self.output_size = output_size

    def forward(self, values: Tensor) -> Tensor:
        if values.ndim != 3:
            raise ValueError("segment pooling expects [N,C,L]")
        length = int(values.shape[-1])
        if length < self.output_size:
            raise ValueError(
                "encoded profile length must be at least the pooled output size"
            )
        segment_width = math.ceil(length / self.output_size)
        padded_length = segment_width * self.output_size
        padded = F.pad(values, (0, padded_length - length), mode="constant", value=0.0)
        segments = padded.reshape(
            values.shape[0], values.shape[1], self.output_size, segment_width
        )
        starts = torch.arange(
            self.output_size, device=values.device, dtype=torch.long
        ) * segment_width
        counts = (length - starts).clamp(min=1, max=segment_width).to(values.dtype)
        return segments.sum(dim=-1) / counts.reshape(1, 1, self.output_size)


class TwoHeadFactorizationModel(nn.Module):
    """Compact shared 1D CNN with separate structure and measurement heads."""

    def __init__(
        self,
        *,
        input_channels: int = 3,
        base_channels: int = 16,
        latent_dim: int = 64,
        pooled_length: int = 16,
        output_bound: float = 1.0,
    ) -> None:
        super().__init__()
        if input_channels != len(INPUT_CHANNEL_ORDER):
            raise ValueError(
                f"input_channels must be {len(INPUT_CHANNEL_ORDER)} for "
                f"{INPUT_CHANNEL_ORDER}"
            )
        if not isinstance(base_channels, int) or base_channels <= 0:
            raise ValueError("base_channels must be a positive integer")
        if not isinstance(latent_dim, int) or latent_dim <= 0:
            raise ValueError("latent_dim must be a positive integer")
        if not isinstance(pooled_length, int) or pooled_length <= 0:
            raise ValueError("pooled_length must be a positive integer")
        output_bound = float(output_bound)
        if not math.isfinite(output_bound) or output_bound <= 0.0:
            raise ValueError("output_bound must be finite and positive")

        hidden_channels = 2 * base_channels
        self.encoder = nn.Sequential(
            nn.Conv1d(
                input_channels,
                base_channels,
                kernel_size=9,
                stride=2,
                padding=4,
            ),
            nn.GELU(),
            nn.Conv1d(
                base_channels,
                hidden_channels,
                kernel_size=7,
                stride=2,
                padding=3,
            ),
            nn.GELU(),
            nn.Conv1d(
                hidden_channels,
                hidden_channels,
                kernel_size=5,
                stride=2,
                padding=2,
            ),
            nn.GELU(),
            DeterministicSegmentMean1d(pooled_length),
            nn.Flatten(),
            nn.Linear(hidden_channels * pooled_length, latent_dim),
            nn.GELU(),
        )
        self.structure_head = nn.Linear(latent_dim, len(STRUCTURE_PARAMETER_ORDER))
        self.measurement_head = nn.Linear(
            latent_dim, len(MEASUREMENT_PARAMETER_ORDER)
        )

        self.register_buffer(
            "output_bound",
            torch.tensor(output_bound, dtype=torch.float32),
        )

    def _validate_flat_input(self, spectra: Tensor) -> None:
        if not isinstance(spectra, Tensor):
            raise TypeError("spectra must be a torch.Tensor")
        if spectra.ndim != 3:
            raise ValueError(
                "spectra must have shape [N, 3, L]; "
                f"received {tuple(spectra.shape)}"
            )
        batch_size, channels, profile_length = spectra.shape
        if batch_size <= 0 or profile_length <= 0:
            raise ValueError("spectra batch and profile dimensions must be non-empty")
        if channels != len(INPUT_CHANNEL_ORDER):
            raise ValueError(
                f"spectra channel axis must be {INPUT_CHANNEL_ORDER}; "
                f"received {channels} channels"
            )
        if not spectra.is_floating_point():
            raise TypeError("spectra must use a floating-point dtype")
        reference = self.structure_head.weight
        if spectra.device != reference.device:
            raise ValueError(
                f"spectra are on {spectra.device}, but the model is on {reference.device}"
            )
        if spectra.dtype != reference.dtype:
            raise TypeError(
                f"spectra dtype {spectra.dtype} does not match model dtype {reference.dtype}"
            )
        if not bool(torch.isfinite(spectra).all()):
            raise ValueError("spectra must contain only finite values")

    def _bound_to_q_domain(self, raw: Tensor) -> Tensor:
        bounded = self.output_bound * torch.tanh(raw)
        if not bool(torch.isfinite(bounded).all()):
            raise FloatingPointError("model produced non-finite q predictions")
        return bounded

    def forward(self, spectra: Tensor) -> tuple[Tensor, Tensor]:
        """Predict normalized structure and measurement parameters.

        Args:
            spectra: Float tensor with shape ``[N, 3, L]``.

        Returns:
            ``(pred_s, pred_m)``, each with shape ``[N, 2]``.  ``pred_s`` is
            ordered ``[q_u, q_v]`` and ``pred_m`` is ordered ``[q_delta, q_w]``.
        """

        self._validate_flat_input(spectra)
        embedding = self.encoder(spectra)
        if not bool(torch.isfinite(embedding).all()):
            raise FloatingPointError("shared encoder produced non-finite activations")
        pred_s = self._bound_to_q_domain(self.structure_head(embedding))
        pred_m = self._bound_to_q_domain(self.measurement_head(embedding))
        expected_shape = (spectra.shape[0], 2)
        if pred_s.shape != expected_shape or pred_m.shape != expected_shape:
            raise RuntimeError(
                "two-head output contract was violated: "
                f"pred_s={tuple(pred_s.shape)}, pred_m={tuple(pred_m.shape)}"
            )
        return pred_s, pred_m

    def forward_blocks(self, block: Tensor) -> tuple[Tensor, Tensor]:
        """Predict a complete 2x2 intervention block without changing corner order.

        The input shape is ``[B, 2, 2, 3, L]``.  Axis 1 indexes structure
        states and axis 2 indexes measurement states, so ``[:, 0, 1]`` is
        ``x12``.  Both returned tensors have shape ``[B, 2, 2, 2]``.
        """

        if not isinstance(block, Tensor):
            raise TypeError("block must be a torch.Tensor")
        if block.ndim != 5:
            raise ValueError(
                "block must have shape [B, 2, 2, 3, L]; "
                f"received {tuple(block.shape)}"
            )
        batch_size, structure_states, measurement_states, channels, length = (
            block.shape
        )
        if batch_size <= 0 or length <= 0:
            raise ValueError("block batch and profile dimensions must be non-empty")
        if (structure_states, measurement_states) != (2, 2):
            raise ValueError(
                "block axes 1 and 2 must contain exactly two structure and two "
                "measurement states"
            )
        if channels != len(INPUT_CHANNEL_ORDER):
            raise ValueError(
                f"block channel axis must be {INPUT_CHANNEL_ORDER}; "
                f"received {channels} channels"
            )

        flat = block.reshape(batch_size * 4, channels, length)
        pred_s, pred_m = self.forward(flat)
        output_shape = (batch_size, 2, 2, 2)
        return pred_s.reshape(output_shape), pred_m.reshape(output_shape)


__all__ = [
    "FACTORIAL_BLOCK_AXIS_ORDER",
    "INPUT_CHANNEL_ORDER",
    "DeterministicSegmentMean1d",
    "MEASUREMENT_PARAMETER_ORDER",
    "STRUCTURE_PARAMETER_ORDER",
    "TwoHeadFactorizationModel",
]
