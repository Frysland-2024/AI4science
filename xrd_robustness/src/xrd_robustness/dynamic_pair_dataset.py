"""Minimal deterministic paired-view dataset for V7 dynamic training."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Sequence

import numpy as np

from .online_views import OnlineViewFactory
from .physics import PhysicsParameters
from .simulation_interfaces import IdealPeakCalculator, PeakTable


def stable_pair_seed(
    run_seed: int,
    split: str,
    epoch: int,
    global_step: int,
    sample_index: int,
    material_id: str,
) -> int:
    """Derive method-independent pair identity without changing renderer seeds."""
    payload = (
        f"{int(run_seed)}:{split}:{int(epoch)}:{int(global_step)}:"
        f"{int(sample_index)}:{material_id}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


@dataclass(frozen=True)
class DynamicStructureSample:
    material_id: str
    label: int
    peak_table: PeakTable

    @classmethod
    def from_structure(
        cls,
        *,
        material_id: str,
        label: int,
        structure: Any,
        calculator: IdealPeakCalculator,
    ) -> "DynamicStructureSample":
        """Create a sample from an MP structure while retaining peak-table caching."""
        return cls(
            material_id=str(material_id),
            label=int(label),
            peak_table=calculator.calculate(structure),
        )


@dataclass(frozen=True)
class DynamicPairItem:
    x1: np.ndarray
    x2: np.ndarray
    y: int
    material_id: str
    params1: PhysicsParameters
    params2: PhysicsParameters
    pair_seed: int
    view_seed1: int
    view_seed2: int
    metadata1: dict[str, Any]
    metadata2: dict[str, Any]


@dataclass(frozen=True)
class DynamicPairBatch:
    x1: Any
    x2: Any
    y: Any
    material_id: tuple[str, ...]
    params1: tuple[PhysicsParameters, ...]
    params2: tuple[PhysicsParameters, ...]
    pair_seed: Any
    metadata1: tuple[dict[str, Any], ...]
    metadata2: tuple[dict[str, Any], ...]


class DynamicPairDataset:
    """Produce replayable paired views from structure-anchored ideal peak tables."""

    def __init__(
        self,
        samples: Sequence[DynamicStructureSample],
        factory: OnlineViewFactory,
        *,
        profile: str,
        split: str = "train",
        epoch: int = 0,
        global_step: int = 0,
    ):
        if not samples:
            raise ValueError("samples cannot be empty")
        material_ids = [sample.material_id for sample in samples]
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("material_id values must be unique within one dataset")
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid split: {split!r}")
        self.samples = tuple(samples)
        self.factory = factory
        self.profile = str(profile)
        self.split = split
        self.epoch = int(epoch)
        self.global_step = int(global_step)

    def __len__(self) -> int:
        return len(self.samples)

    def set_context(self, *, epoch: int, global_step: int) -> None:
        """Set deterministic training context before the next DataLoader pass."""
        if epoch < 0 or global_step < 0:
            raise ValueError("epoch and global_step must be non-negative")
        self.epoch = int(epoch)
        self.global_step = int(global_step)

    def __getitem__(self, index: int) -> DynamicPairItem:
        sample = self.samples[index]
        pair = self.factory.make_pair_from_peaks(
            sample.peak_table,
            material_id=sample.material_id,
            split=self.split,
            epoch=self.epoch,
            global_step=self.global_step,
            profile=self.profile,
        )
        effective_epoch = self.factory.effective_epoch(self.split, self.epoch)
        effective_step = self.global_step if self.split == "train" else 0
        pair_seed = stable_pair_seed(
            self.factory.sampler.run_seed,
            self.split,
            effective_epoch,
            effective_step,
            index,
            sample.material_id,
        )
        return DynamicPairItem(
            x1=pair.first.xrd,
            x2=pair.second.xrd,
            y=int(sample.label),
            material_id=sample.material_id,
            params1=pair.first.parameters,
            params2=pair.second.parameters,
            pair_seed=pair_seed,
            view_seed1=pair.first.rng_seed,
            view_seed2=pair.second.rng_seed,
            metadata1=dict(pair.first.metadata),
            metadata2=dict(pair.second.metadata),
        )


def collate_dynamic_pairs(items: Sequence[DynamicPairItem]) -> DynamicPairBatch:
    """Collate to torch tensors only when the optional training dependency exists."""
    if not items:
        raise ValueError("cannot collate an empty batch")
    import torch

    return DynamicPairBatch(
        x1=torch.from_numpy(np.stack([item.x1 for item in items])).float(),
        x2=torch.from_numpy(np.stack([item.x2 for item in items])).float(),
        y=torch.as_tensor([item.y for item in items], dtype=torch.long),
        material_id=tuple(item.material_id for item in items),
        params1=tuple(item.params1 for item in items),
        params2=tuple(item.params2 for item in items),
        pair_seed=torch.as_tensor([item.pair_seed for item in items], dtype=torch.uint64),
        metadata1=tuple(item.metadata1 for item in items),
        metadata2=tuple(item.metadata2 for item in items),
    )
