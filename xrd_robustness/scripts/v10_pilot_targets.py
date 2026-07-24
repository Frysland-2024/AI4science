"""Balanced Train sampling and simulator-delta targets for the V10 Pilot."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from audit_v9_learned_state_scale import CRYSTAL_SYSTEMS
from v10_pilot_config import TARGET_SCALES
from xrd_robustness.physics import PhysicsParameters


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def balanced_train_take(
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    *,
    per_class: int,
    seed: int,
) -> list[str]:
    grouped: dict[int, list[str]] = defaultdict(list)
    for material_id in material_ids:
        grouped[int(labels[material_id])].append(str(material_id))
    selected: list[str] = []
    for label in range(len(CRYSTAL_SYSTEMS)):
        candidates = sorted(grouped[label])
        generator = np.random.default_rng(seed + label * 1009)
        order = generator.permutation(len(candidates))
        if len(candidates) < per_class:
            raise ValueError(
                f"class {label} has {len(candidates)} candidates; {per_class} required"
            )
        selected.extend(candidates[int(index)] for index in order[:per_class])
    return sorted(selected)


def measurement_delta_rows(
    first: Sequence[PhysicsParameters],
    second: Sequence[PhysicsParameters],
) -> np.ndarray:
    """Return normalized simulator deltas in signed second-minus-first order."""
    if len(first) != len(second):
        raise ValueError("paired perturbation parameter sequences must have equal length")
    if not first:
        raise ValueError("paired perturbation parameter sequences cannot be empty")
    rows: list[tuple[float, float, float, float]] = []
    for first_params, second_params in zip(first, second, strict=True):
        first_params.validate()
        second_params.validate()
        delta_log_fwhm = (
            math.log(second_params.fwhm_deg) - math.log(first_params.fwhm_deg)
        ) / TARGET_SCALES["log_fwhm"]
        delta_background = (
            second_params.background_to_peak_ratio
            - first_params.background_to_peak_ratio
        ) / TARGET_SCALES["background_ratio"]
        delta_inverse_count = (
            -math.log(second_params.poisson_count_scale)
            + math.log(first_params.poisson_count_scale)
        ) / TARGET_SCALES["log_inverse_count_scale"]
        delta_electronic = (
            second_params.electronic_noise_std_counts
            - first_params.electronic_noise_std_counts
        ) / TARGET_SCALES["electronic_noise_counts"]
        row = (
            delta_log_fwhm,
            delta_background,
            delta_inverse_count,
            delta_electronic,
        )
        if not all(math.isfinite(value) for value in row):
            raise ValueError("V10 Pilot perturbation targets must be finite")
        rows.append(row)
    return np.asarray(rows, dtype=np.float32)


def measurement_delta_tensor(
    first: Sequence[PhysicsParameters],
    second: Sequence[PhysicsParameters],
    *,
    device: torch.device,
) -> torch.Tensor:
    return torch.from_numpy(measurement_delta_rows(first, second)).to(device)
