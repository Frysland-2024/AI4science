"""Deterministic Validation-only checkpoint selection and early stopping."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass
class EarlyStoppingState:
    best_epoch: int | None = None
    best_global_step: int | None = None
    best_primary: float | None = None
    best_id: float | None = None
    primary_improvement_reference: float | None = None
    checks_without_primary_improvement: int = 0
    validation_checks: int = 0
    stopped: bool = False
    stop_epoch: int | None = None
    stop_reason: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EarlyStoppingState":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value[key] for key in allowed if key in value})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def update_early_stopping(
    state: EarlyStoppingState,
    *,
    epoch: int,
    global_step: int,
    primary: float,
    validation_id: float,
    min_delta: float,
    patience: int,
    min_epochs: int,
) -> tuple[bool, bool]:
    """Update state and return ``(save_best_checkpoint, stop_now)``.

    A primary improvement larger than ``min_delta`` resets patience. Values
    within ``min_delta`` are treated as tied for checkpoint selection, where
    Validation-ID Macro-F1 is the first tie-break and the earlier epoch wins the
    remaining tie. A tie-break-only checkpoint update does not reset patience.
    """

    if epoch <= 0 or global_step <= 0:
        raise ValueError("epoch and global_step must be positive")
    if min_delta < 0:
        raise ValueError("min_delta cannot be negative")
    if patience <= 0 or min_epochs <= 0:
        raise ValueError("patience and min_epochs must be positive")

    state.validation_checks += 1
    first = state.primary_improvement_reference is None
    meaningful_primary = (
        first
        or primary > float(state.primary_improvement_reference) + min_delta
    )
    tied_primary = (
        not first
        and abs(primary - float(state.primary_improvement_reference)) <= min_delta
    )
    better_id_tie = tied_primary and (
        state.best_id is None or validation_id > float(state.best_id)
    )
    save_best = bool(meaningful_primary or better_id_tie)

    if meaningful_primary:
        state.primary_improvement_reference = float(primary)
        state.checks_without_primary_improvement = 0
    else:
        state.checks_without_primary_improvement += 1

    if save_best:
        state.best_epoch = int(epoch)
        state.best_global_step = int(global_step)
        state.best_primary = float(primary)
        state.best_id = float(validation_id)

    stop_now = (
        epoch >= min_epochs
        and state.checks_without_primary_improvement >= patience
    )
    if stop_now:
        state.stopped = True
        state.stop_epoch = int(epoch)
        state.stop_reason = (
            f"no primary improvement greater than {min_delta} for "
            f"{patience} validation checks"
        )
    return save_best, stop_now
