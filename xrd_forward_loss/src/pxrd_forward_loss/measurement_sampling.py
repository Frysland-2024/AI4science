"""Frozen q, split and nuisance sampling helpers for Issue #19."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import qmc


def sample_q_bank(
    count: int,
    *,
    seed: int,
    q_bound: float = 0.8,
) -> np.ndarray:
    """Draw lattice-only Sobol labels independently from all measurement draws."""
    if count <= 0 or q_bound <= 0:
        raise ValueError("count and q_bound must be positive")
    sampler = qmc.Sobol(d=2, scramble=True, seed=int(seed))
    exponent = int(np.ceil(np.log2(count)))
    unit = sampler.random_base2(exponent)[:count]
    return ((2.0 * unit - 1.0) * float(q_bound)).astype(np.float64)


def split_q_indices(
    count: int,
    *,
    seed: int,
    train_fraction: float = 0.70,
    validation_fraction: float = 0.15,
) -> dict[str, np.ndarray]:
    """Split q rows before any observed-view or nuisance random draws."""
    if count < 3 or train_fraction <= 0 or validation_fraction <= 0:
        raise ValueError("invalid count or split fractions")
    if train_fraction + validation_fraction >= 1.0:
        raise ValueError("train and validation fractions must sum to less than one")
    order = np.random.default_rng(int(seed)).permutation(count)
    n_train = int(round(count * train_fraction))
    n_validation = int(round(count * validation_fraction))
    return {
        "train": order[:n_train],
        "validation": order[n_train : n_train + n_validation],
        "test": order[n_train + n_validation :],
    }


def sample_v9_nuisance_bank(count: int, *, seed: int) -> np.ndarray:
    """Draw bounded V9 stress eta independently of q.

    Returns columns delta[deg], FWHM[deg], and background peak ratio. The V9
    polynomial shape is deterministic (variation=0) and is not sampled as an
    unknown parameter.
    """
    if count <= 0:
        raise ValueError("count must be positive")
    rng = np.random.default_rng(int(seed))
    return np.column_stack(
        (
            rng.uniform(-0.06, 0.06, count),
            rng.uniform(0.11, 0.13, count),
            rng.uniform(0.005, 0.008, count),
        )
    ).astype(np.float64)


def split_assignment(indices: dict[str, np.ndarray], count: int) -> list[str]:
    """Return one split label per q index, rejecting duplicate assignments."""
    labels: list[str | None] = [None] * int(count)
    for split, rows in indices.items():
        for index in np.asarray(rows, dtype=np.int64).tolist():
            if not 0 <= index < count or labels[index] is not None:
                raise ValueError("split indices overlap or are out of bounds")
            labels[index] = str(split)
    if any(label is None for label in labels):
        raise ValueError("split indices do not cover the q bank")
    return [str(label) for label in labels]
