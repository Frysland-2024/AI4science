"""Controlled rendering and feature extraction for the V10-P0 gate."""

from __future__ import annotations

import copy
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import time
from typing import Any, Mapping, Sequence

import numpy as np
import torch

from audit_v9_learned_state_scale import SEED, _autocast
from v10_p0_gate_stats import (
    _normalized_strength,
    _pooled_absolute_spectrum_difference,
    _regression_probe,
)
from xrd_robustness.experiment import file_hash
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training.objectives import (
    signed_measurement_residual,
    symmetric_measurement_residual,
)
from xrd_robustness.view_manifest import build_parameter_row


FAMILIES = ("shift", "broadening", "background", "noise", "texture")
PROFILE_BY_FAMILY = {
    "broadening": "ood_broadening",
    "background": "ood_background",
    "noise": "ood_noise",
    "texture": "ood_texture",
}
QUALITY_GATE_MAX_ATTEMPTS = 32
QUALITY_GATE_RETRY_VIEW_STRIDE = 2


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _balanced_take(
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
    for label in range(7):
        candidates = sorted(grouped[label])
        random.Random(seed + label * 10_003).shuffle(candidates)
        if len(candidates) < per_class:
            raise ValueError(
                f"class {label} has {len(candidates)} candidates; {per_class} required"
            )
        selected.extend(candidates[:per_class])
    return sorted(selected)


def _shift_profile(material_id: str) -> str:
    digest = hashlib.sha256(str(material_id).encode("utf-8")).digest()
    return "ood_shift_positive" if digest[0] % 2 == 0 else "ood_shift_negative"


def _profile_for(family: str, material_id: str) -> str:
    if family == "shift":
        return _shift_profile(material_id)
    return PROFILE_BY_FAMILY[family]


def _build_gate_simulation(simulation: Mapping[str, Any]) -> dict[str, Any]:
    gate = copy.deepcopy(dict(simulation))
    gate["run_seed"] = SEED + 110_000
    gate["purpose"] = (
        "Train-only V10-P0 identifiability panel derived from the frozen V9 "
        "parameter evidence; it is not a formal training configuration"
    )
    # The frozen V9 texture OOD intentionally keeps in-range nuisance variation.
    # This Gate needs a one-factor texture target, so all non-texture fields are
    # reset to level0 while preserving the frozen texture range and model.
    pure_texture = copy.deepcopy(gate["profiles"]["level0"])
    pure_texture["severity_level"] = 3
    pure_texture["preferred_orientation"] = copy.deepcopy(
        gate["profiles"]["ood_texture"]["preferred_orientation"]
    )
    gate["profiles"]["ood_texture"] = pure_texture
    return gate


def _build_renderer(
    simulation_path: Path,
) -> tuple[PhysicsParameterSampler, OnlineViewFactory, dict[str, Any]]:
    source_simulation = json.loads(simulation_path.read_text(encoding="utf-8"))
    simulation = _build_gate_simulation(source_simulation)
    sampler = PhysicsParameterSampler.from_mapping(simulation)
    gate_hash = _canonical_hash(simulation)
    factory = OnlineViewFactory(
        sampler,
        quality_gate=True,
        quality_gate_config=simulation.get("quality_gates", {}),
        strategy=IndependentDynamicStrategy(sampler, config_hash=gate_hash),
    )
    simulation["derived_gate_config_sha256"] = gate_hash
    return sampler, factory, simulation


def _render_with_retry(
    *,
    peak_table: Any,
    material_id: str,
    sampler: PhysicsParameterSampler,
    factory: OnlineViewFactory,
    profile: str,
    epoch: int,
    global_step: int,
    view_id: int,
) -> tuple[np.ndarray, dict[str, Any], int]:
    last_error: ValueError | None = None
    for attempt in range(QUALITY_GATE_MAX_ATTEMPTS):
        row = build_parameter_row(
            material_id,
            sampler,
            profile=profile,
            epoch=epoch,
            global_step=global_step,
            split="train",
            view_id=view_id,
            sampling_view_id=view_id + attempt * QUALITY_GATE_RETRY_VIEW_STRIDE,
        )
        try:
            view = factory.make_view_from_manifest(peak_table, row)
            return (
                np.asarray(view.xrd, dtype=np.float32),
                view.parameters.to_dict(),
                attempt,
            )
        except ValueError as error:
            if not str(error).startswith("quality gate rejected training view "):
                raise
            last_error = error
    raise ValueError(
        "quality gate exhausted deterministic V10-P0 resampling after "
        f"{QUALITY_GATE_MAX_ATTEMPTS} attempts for "
        f"{material_id}/{profile}/{epoch}/{global_step}/{view_id}: {last_error}"
    )


def _render_panel(
    *,
    material_ids: Sequence[str],
    labels: Mapping[str, int],
    data_root: Path,
    sampler: PhysicsParameterSampler,
    factory: OnlineViewFactory,
    subset_offset: int,
) -> dict[str, Any]:
    peak_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    peak_cache: dict[str, Any] = {}
    first: list[np.ndarray] = []
    second: list[np.ndarray] = []
    family_labels: list[int] = []
    crystal_labels: list[int] = []
    strength: list[float] = []
    row_metadata: list[dict[str, Any]] = []
    sample_groups: list[str] = []
    retry_count = 0
    started = time.perf_counter()
    for material_index, material_id in enumerate(material_ids):
        if material_id not in peak_cache:
            peak_cache[material_id] = load_peak_table(
                peak_root / f"{material_id}.npz"
            )
        peak_table = peak_cache[material_id]
        for family_index, family in enumerate(FAMILIES):
            profile = _profile_for(family, material_id)
            epoch = 40_000 + subset_offset
            global_step = material_index * len(FAMILIES) + family_index
            anchor, anchor_parameters, anchor_retry = _render_with_retry(
                peak_table=peak_table,
                material_id=material_id,
                sampler=sampler,
                factory=factory,
                profile="level0",
                epoch=epoch,
                global_step=global_step,
                view_id=1,
            )
            perturbed, perturb_parameters, perturb_retry = _render_with_retry(
                peak_table=peak_table,
                material_id=material_id,
                sampler=sampler,
                factory=factory,
                profile=profile,
                epoch=epoch,
                global_step=global_step,
                view_id=2,
            )
            first.append(anchor)
            second.append(perturbed)
            family_labels.append(family_index)
            crystal_labels.append(int(labels[material_id]))
            strength.append(_normalized_strength(family, perturb_parameters))
            sample_groups.append(material_id)
            retry_count += anchor_retry + perturb_retry
            row_metadata.append(
                {
                    "material_id": material_id,
                    "crystal_system_index": int(labels[material_id]),
                    "family": family,
                    "profile": profile,
                    "normalized_strength": strength[-1],
                    "anchor_parameters": anchor_parameters,
                    "perturbed_parameters": perturb_parameters,
                    "quality_retry_count": anchor_retry + perturb_retry,
                }
            )
    return {
        "first": np.stack(first),
        "second": np.stack(second),
        "family_labels": np.asarray(family_labels, dtype=np.int64),
        "crystal_labels": np.asarray(crystal_labels, dtype=np.int64),
        "strength": np.asarray(strength, dtype=np.float64),
        "sample_groups": np.asarray(sample_groups),
        "rows": row_metadata,
        "quality_retry_count": int(retry_count),
        "runtime_seconds": time.perf_counter() - started,
    }


def _extract_features(
    model: torch.nn.Module,
    panel: Mapping[str, Any],
    device: torch.device,
    *,
    amp_enabled: bool,
    batch_size: int = 64,
) -> dict[str, np.ndarray]:
    model.eval()
    symmetric: list[np.ndarray] = []
    signed: list[np.ndarray] = []
    first = np.asarray(panel["first"], dtype=np.float32)
    second = np.asarray(panel["second"], dtype=np.float32)
    with torch.no_grad():
        for start in range(0, len(first), batch_size):
            x1 = torch.from_numpy(
                np.ascontiguousarray(first[start : start + batch_size])
            ).to(device)
            x2 = torch.from_numpy(
                np.ascontiguousarray(second[start : start + batch_size])
            ).to(device)
            with _autocast(device, amp_enabled):
                embedding1 = model(x1)["pooled_embedding"]
                embedding2 = model(x2)["pooled_embedding"]
                symmetric_residual = symmetric_measurement_residual(
                    embedding1, embedding2
                )
                signed_residual = signed_measurement_residual(embedding1, embedding2)
            symmetric.append(symmetric_residual.float().cpu().numpy())
            signed.append(signed_residual.float().cpu().numpy())
    return {
        "symmetric_residual": np.concatenate(symmetric, axis=0),
        "signed_residual": np.concatenate(signed, axis=0),
        "raw_absolute_difference": _pooled_absolute_spectrum_difference(
            first, second
        ),
    }


def _family_regressions(
    train_features: np.ndarray,
    audit_features: np.ndarray,
    train_family: np.ndarray,
    audit_family: np.ndarray,
    train_strength: np.ndarray,
    audit_strength: np.ndarray,
    *,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for family_index, family in enumerate(FAMILIES):
        train_mask = train_family == family_index
        audit_mask = audit_family == family_index
        output[family] = _regression_probe(
            train_features[train_mask],
            train_strength[train_mask],
            audit_features[audit_mask],
            audit_strength[audit_mask],
            permutations=permutations,
            seed=seed + family_index * 1009,
        )
    return output
