"""Auditable, spectrum-free parameter manifests for matched view experiments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .physics import PhysicsParameterSampler, PhysicsParameters


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ViewManifestRow:
    split: str
    epoch: int
    global_step: int
    material_id: str
    view_id: int
    simulation_seed: int
    parameters: dict[str, Any]

    @property
    def manifest_id(self) -> str:
        payload = {
            "split": self.split,
            "epoch": self.epoch,
            "global_step": self.global_step,
            "material_id": self.material_id,
            "view_id": self.view_id,
            "simulation_seed": self.simulation_seed,
            "parameters": self.parameters,
        }
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "split": self.split,
            "epoch": self.epoch,
            "global_step": self.global_step,
            "material_id": self.material_id,
            "view_id": self.view_id,
            "simulation_seed": self.simulation_seed,
            "parameters": self.parameters,
            "view_manifest_id": self.manifest_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ViewManifestRow":
        row = cls(
            split=str(value["split"]),
            epoch=int(value["epoch"]),
            global_step=int(value["global_step"]),
            material_id=str(value["material_id"]),
            view_id=int(value["view_id"]),
            simulation_seed=int(value["simulation_seed"]),
            parameters=dict(value["parameters"]),
        )
        expected = value.get("view_manifest_id")
        if expected is not None and str(expected) != row.manifest_id:
            raise ValueError("view manifest row hash does not match its contents")
        return row

    def physics_parameters(self) -> PhysicsParameters:
        values = dict(self.parameters)
        values.pop("active_perturbation_count", None)
        return PhysicsParameters(**values)


@dataclass(frozen=True)
class FrozenEvaluationManifest:
    """Immutable validation/test parameter rows that can be hashed and replayed."""

    rows: tuple[ViewManifestRow, ...]

    def __post_init__(self) -> None:
        if not self.rows:
            raise ValueError("a frozen evaluation manifest cannot be empty")
        seen: set[tuple[str, int]] = set()
        for row in self.rows:
            if row.split == "train" or row.epoch != 0 or row.global_step != 0:
                raise ValueError("frozen evaluation rows require a non-train split and zero context")
            key = (row.material_id, row.view_id)
            if key in seen:
                raise ValueError(f"duplicate frozen evaluation row: {key}")
            seen.add(key)

    @property
    def manifest_hash(self) -> str:
        payload = [row.to_dict() for row in self.rows]
        return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()

    def index(self) -> dict[tuple[str, int], ViewManifestRow]:
        return {(row.material_id, row.view_id): row for row in self.rows}

    @classmethod
    def from_rows(cls, rows: Iterable[ViewManifestRow]) -> "FrozenEvaluationManifest":
        return cls(tuple(rows))


def build_parameter_stream(
    material_ids: Iterable[str],
    sampler: PhysicsParameterSampler,
    *,
    profile: str,
    epochs: int,
    steps_per_epoch: int,
    split: str = "train",
    view_ids: tuple[int, int] = (1, 2),
) -> list[ViewManifestRow]:
    """Create method-independent rows; only parameters and seeds are persisted."""
    if epochs <= 0 or steps_per_epoch <= 0:
        raise ValueError("epochs and steps_per_epoch must be positive")
    ordered_materials = tuple(sorted(str(material_id) for material_id in material_ids))
    if not ordered_materials:
        raise ValueError("material_ids cannot be empty")
    rows: list[ViewManifestRow] = []
    for epoch in range(epochs):
        for global_step in range(steps_per_epoch):
            rows.extend(
                build_parameter_batch(
                    ordered_materials,
                    sampler,
                    profile=profile,
                    epoch=epoch if split == "train" else 0,
                    global_step=global_step if split == "train" else 0,
                    split=split,
                    view_ids=view_ids,
                )
            )
    return rows


def build_parameter_batch(
    material_ids: Iterable[str],
    sampler: PhysicsParameterSampler,
    *,
    profile: str,
    epoch: int,
    global_step: int,
    split: str = "train",
    view_ids: tuple[int, ...] = (1, 2),
) -> list[ViewManifestRow]:
    """Generate parameter rows only for the structures consumed by one batch.

    Input order is preserved so the resulting row pairs can be hashed against the
    deterministic sampler order without materializing the full training stream.
    """
    ordered_materials = tuple(str(material_id) for material_id in material_ids)
    if not ordered_materials:
        raise ValueError("material_ids cannot be empty")
    if not view_ids or len(set(view_ids)) != len(view_ids):
        raise ValueError("view_ids must contain unique values")
    rows: list[ViewManifestRow] = []
    for material_id in ordered_materials:
        for view_id in view_ids:
            rows.append(
                build_parameter_row(
                    material_id,
                    sampler,
                    profile=profile,
                    epoch=epoch,
                    global_step=global_step,
                    split=split,
                    view_id=view_id,
                )
            )
    return rows


def build_parameter_row(
    material_id: str,
    sampler: PhysicsParameterSampler,
    *,
    profile: str,
    epoch: int,
    global_step: int,
    split: str = "train",
    view_id: int,
    sampling_view_id: int | None = None,
) -> ViewManifestRow:
    """Build one auditable row, optionally using an alternate seed coordinate.

    ``sampling_view_id`` supports deterministic quality-gate rejection sampling:
    the returned row retains its semantic pair identity (``view_id`` 1 or 2),
    while its stored seed and parameters record the candidate actually rendered.
    """
    semantic_view_id = int(view_id)
    seed_view_id = semantic_view_id if sampling_view_id is None else int(sampling_view_id)
    if semantic_view_id < 0 or seed_view_id < 0:
        raise ValueError("view_id and sampling_view_id must be non-negative")
    parameters, seed = sampler.sample(
        profile,
        epoch=epoch,
        global_step=global_step,
        material_id=str(material_id),
        view_id=seed_view_id,
    )
    return ViewManifestRow(
        split=split,
        epoch=epoch,
        global_step=global_step,
        material_id=str(material_id),
        view_id=semantic_view_id,
        simulation_seed=seed,
        parameters=parameters.to_dict(),
    )


def build_offline_view_manifest(
    material_ids: Iterable[str],
    sampler: PhysicsParameterSampler,
    *,
    profile: str,
    views_per_material: int,
    split: str = "train",
) -> list[ViewManifestRow]:
    """Create fixed K-view rows without persisting the rendered spectra."""
    if views_per_material <= 0:
        raise ValueError("views_per_material must be positive")
    rows: list[ViewManifestRow] = []
    for material_id in sorted(str(value) for value in material_ids):
        for view_id in range(1, views_per_material + 1):
            parameters, seed = sampler.sample(
                profile,
                epoch=0,
                global_step=0,
                material_id=material_id,
                view_id=view_id,
            )
            rows.append(
                ViewManifestRow(
                    split=split,
                    epoch=0,
                    global_step=0,
                    material_id=material_id,
                    view_id=view_id,
                    simulation_seed=seed,
                    parameters=parameters.to_dict(),
                )
            )
    return rows


def save_manifest(rows: Iterable[ViewManifestRow], path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = [row.to_dict() for row in rows]
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(_canonical_json(row) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: str | Path) -> list[ViewManifestRow]:
    path = Path(path)
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(ViewManifestRow.from_dict(json.loads(line)))
    return rows


def index_manifest(rows: Iterable[ViewManifestRow]) -> dict[tuple[str, int, int, int], ViewManifestRow]:
    index: dict[tuple[str, int, int, int], ViewManifestRow] = {}
    for row in rows:
        key = (row.material_id, row.epoch, row.global_step, row.view_id)
        if key in index:
            raise ValueError(f"duplicate view manifest key: {key}")
        index[key] = row
    return index
