"""Deterministic, replayable training sampling and incremental audit hashes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from .view_manifest import ViewManifestRow


TRAINING_STREAM_SCHEMA_VERSION = "training-stream-v1"
EPOCH_SHUFFLE_ALGORITHM = "sha256-key-sort-v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def deterministic_epoch_shuffle(
    material_ids: Iterable[str],
    *,
    seed: int,
    epoch: int,
) -> tuple[str, ...]:
    """Return a cross-process deterministic pseudo-random permutation."""
    values = tuple(sorted(str(material_id) for material_id in material_ids))
    if not values:
        raise ValueError("material_ids cannot be empty")
    if len(values) != len(set(values)):
        raise ValueError("material_ids must be unique")
    if epoch < 0:
        raise ValueError("epoch cannot be negative")

    def shuffle_key(material_id: str) -> tuple[bytes, str]:
        payload = (
            f"{EPOCH_SHUFFLE_ALGORITHM}:{int(seed)}:{int(epoch)}:{material_id}"
        ).encode("utf-8")
        return hashlib.sha256(payload).digest(), material_id

    return tuple(sorted(values, key=shuffle_key))


def epoch_shuffle_hash(order: Sequence[str], *, seed: int, epoch: int) -> str:
    return _hash_payload(
        {
            "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
            "algorithm": EPOCH_SHUFFLE_ALGORITHM,
            "seed": int(seed),
            "epoch": int(epoch),
            "material_ids": [str(value) for value in order],
        }
    )


def select_epoch_batch(
    epoch_order: Sequence[str],
    *,
    step: int,
    batch_size: int,
    full_batch: bool,
) -> tuple[str, ...]:
    """Select one batch, wrapping only when a fixed-step budget requires it."""
    if not epoch_order:
        raise ValueError("epoch_order cannot be empty")
    if step < 0 or batch_size <= 0:
        raise ValueError("step must be non-negative and batch_size must be positive")
    start = step * batch_size
    if full_batch:
        return tuple(
            str(epoch_order[(start + offset) % len(epoch_order)])
            for offset in range(batch_size)
        )
    batch = tuple(str(value) for value in epoch_order[start : start + batch_size])
    if not batch:
        raise ValueError("step is beyond the non-wrapping epoch order")
    return batch


def build_training_sampler_contract(
    material_ids: Iterable[str],
    *,
    seed: int,
    batch_size: int,
    steps_per_epoch: int,
    target_optimizer_steps: int,
    full_batches: bool,
) -> dict[str, Any]:
    values = tuple(sorted(str(material_id) for material_id in material_ids))
    if not values or len(values) != len(set(values)):
        raise ValueError("training sampler material_ids must be non-empty and unique")
    if batch_size <= 0 or steps_per_epoch <= 0 or target_optimizer_steps <= 0:
        raise ValueError("training sampler sizes and budgets must be positive")
    return {
        "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
        "epoch_shuffle_algorithm": EPOCH_SHUFFLE_ALGORITHM,
        "seed": int(seed),
        "batch_size": int(batch_size),
        "steps_per_epoch": int(steps_per_epoch),
        "target_optimizer_steps": int(target_optimizer_steps),
        "full_batches": bool(full_batches),
        "material_count": len(values),
        "material_ids_hash": _hash_payload(list(values)),
    }


def training_sampler_contract_hash(contract: Mapping[str, Any]) -> str:
    return _hash_payload(dict(contract))


def paired_manifest_ids(
    rows: Sequence[ViewManifestRow],
    material_ids: Sequence[str],
) -> tuple[tuple[str, str], ...]:
    if len(rows) != 2 * len(material_ids):
        raise ValueError("paired rows must contain exactly two rows per material")
    pairs: list[tuple[str, str]] = []
    for offset, material_id in enumerate(material_ids):
        first, second = rows[2 * offset : 2 * offset + 2]
        if (
            first.material_id != str(material_id)
            or second.material_id != str(material_id)
            or first.view_id != 1
            or second.view_id != 2
        ):
            raise ValueError("parameter rows do not match the sampled batch order")
        pairs.append((first.manifest_id, second.manifest_id))
    return tuple(pairs)


def _initial_chain(contract_hash: str, name: str) -> str:
    return _hash_payload(
        {
            "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
            "sampler_contract_hash": str(contract_hash),
            "chain": name,
        }
    )


def _extend_chain(previous: str, payload: Any) -> str:
    return hashlib.sha256(
        (str(previous) + "\n" + _canonical_json(payload)).encode("utf-8")
    ).hexdigest()


@dataclass
class TrainingStreamAudit:
    """O(1)-memory hash chains over the batches actually consumed by training."""

    sampler_contract_hash: str
    sampler_hash: str
    pair_schedule_hash: str
    parameter_pair_hash: str
    optimizer_steps: int = 0
    structure_exposures: int = 0
    spectrum_exposures: int = 0

    @classmethod
    def create(cls, sampler_contract_hash: str) -> "TrainingStreamAudit":
        return cls(
            sampler_contract_hash=str(sampler_contract_hash),
            sampler_hash=_initial_chain(sampler_contract_hash, "sampler"),
            pair_schedule_hash=_initial_chain(sampler_contract_hash, "pair_schedule"),
            parameter_pair_hash=_initial_chain(sampler_contract_hash, "parameter_pairs"),
        )

    @classmethod
    def from_snapshot(
        cls,
        snapshot: Mapping[str, Any],
        *,
        sampler_contract_hash: str,
    ) -> "TrainingStreamAudit":
        if str(snapshot.get("schema_version")) != TRAINING_STREAM_SCHEMA_VERSION:
            raise ValueError("training stream audit schema mismatch")
        if str(snapshot.get("sampler_contract_hash")) != str(sampler_contract_hash):
            raise ValueError("training stream sampler contract hash mismatch")
        return cls(
            sampler_contract_hash=str(sampler_contract_hash),
            sampler_hash=str(snapshot["sampler_hash"]),
            pair_schedule_hash=str(snapshot["pair_schedule_hash"]),
            parameter_pair_hash=str(snapshot["parameter_pair_hash"]),
            optimizer_steps=int(snapshot["optimizer_steps"]),
            structure_exposures=int(snapshot["structure_exposures"]),
            spectrum_exposures=int(snapshot["spectrum_exposures"]),
        )

    def record_batch(
        self,
        *,
        epoch: int,
        step: int,
        absolute_step: int,
        material_ids: Sequence[str],
        parameter_pairs: Sequence[Sequence[str]],
        views_per_structure: int,
    ) -> None:
        ids = tuple(str(value) for value in material_ids)
        pairs = tuple(tuple(str(value) for value in pair) for pair in parameter_pairs)
        if not ids or len(pairs) != len(ids):
            raise ValueError("audit parameter pairs must align with a non-empty batch")
        if views_per_structure <= 0 or any(len(pair) != views_per_structure for pair in pairs):
            raise ValueError("audit pair width must equal views_per_structure")
        context = {
            "epoch": int(epoch),
            "step": int(step),
            "absolute_step": int(absolute_step),
        }
        self.sampler_hash = _extend_chain(
            self.sampler_hash,
            {**context, "material_ids": list(ids)},
        )
        self.pair_schedule_hash = _extend_chain(
            self.pair_schedule_hash,
            {
                **context,
                "pairs": [
                    {"material_id": material_id, "slots": list(range(1, views_per_structure + 1))}
                    for material_id in ids
                ],
            },
        )
        self.parameter_pair_hash = _extend_chain(
            self.parameter_pair_hash,
            {**context, "parameter_pairs": [list(pair) for pair in pairs]},
        )
        self.optimizer_steps += 1
        self.structure_exposures += len(ids)
        self.spectrum_exposures += len(ids) * views_per_structure

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": TRAINING_STREAM_SCHEMA_VERSION,
            "sampler_contract_hash": self.sampler_contract_hash,
            "sampler_hash": self.sampler_hash,
            "pair_schedule_hash": self.pair_schedule_hash,
            "parameter_pair_hash": self.parameter_pair_hash,
            "optimizer_steps": self.optimizer_steps,
            "structure_exposures": self.structure_exposures,
            "spectrum_exposures": self.spectrum_exposures,
        }
