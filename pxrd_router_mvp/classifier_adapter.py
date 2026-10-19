"""Optional read-only adapter contract for the frozen 7-system classifier."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClassifierStatus:
    available: bool
    message: str
    classes: tuple[str, ...] = ("triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic")
    checkpoint: str | None = None
    checkpoint_sha256: str | None = None
    input_contract: str = "3501 points, 10–80° 2theta, 0.02° spacing, Cu Kalpha 1.5406 A wavelength mapping, max normalized"


def load_optional_prior(checkpoint: str | Path | None = None) -> ClassifierStatus:
    """Report unavailable unless a future audited adapter is implemented.

    This worktree contains no weights or PyTorch. The function deliberately
    never invents probabilities or reads stored predictions as model output.
    """
    if checkpoint is None or not Path(checkpoint).is_file():
        return ClassifierStatus(False, "classifier unavailable: no verified local frozen checkpoint")
    return ClassifierStatus(False, "classifier unavailable: this MVP has no verified inference adapter")


def soft_system_adjustment(system: str, prior: dict[str, float] | None, weight: float = 0.02) -> float:
    """Return a small optional ranking penalty; never filters a candidate."""
    if not prior:
        return 0.0
    if not 0 <= weight <= 0.05:
        raise ValueError("prior weight must be between zero and 0.05")
    probability = min(1.0, max(0.0, float(prior.get(system, 0.0))))
    return weight * (1.0 - probability)
