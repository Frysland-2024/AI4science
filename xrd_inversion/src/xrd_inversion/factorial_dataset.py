"""Train-only 2x2 factorial data for Stage-1 factorization.

This module intentionally does not call :func:`run_week1_pilot`.  It reuses
only the audited parent/decode helpers and the cached GPU physics primitive,
retains only authoritative Train records, and never imports the independent
renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import torch
from torch.utils.data import Dataset

from .gpu_forward import CachedTetragonalGPUForward
from .parameterization import resolve_reference_q
from .week1_pilot import (
    ParentContext,
    audit_tetragonal_pool,
    build_parent_context,
    is_conventional_tetragonal_lattice,
    load_authoritative_split,
    load_csv_index,
    load_json,
    select_representative_parents,
    sha256_file,
    stable_seed,
)


CORNER_ORDER = ("x11", "x12", "x21", "x22")
MANIFEST_SCHEMA = "xrd-inversion-factorial-manifest-v1"
BUNDLE_SCHEMA = "xrd-inversion-factorial-profile-bundle-v1"


@dataclass(frozen=True)
class FactorialTensorBundle:
    """Dense block-first profile bundle.

    ``inputs`` has shape ``[block, 2, 2, 3, L]``.  The two factorial axes are
    structure then measurement.  The channel order is obs/ref/diff.
    """

    inputs: np.ndarray
    theta_s: np.ndarray
    theta_m: np.ndarray
    parent_id: np.ndarray
    parent_a: np.ndarray
    parent_c: np.ndarray
    block_id: np.ndarray
    subset: np.ndarray
    manifest_sha256: str

    @property
    def block_count(self) -> int:
        return int(self.inputs.shape[0])

    @property
    def profile_length(self) -> int:
        return int(self.inputs.shape[-1])


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def payload_sha256(value: Mapping[str, Any]) -> str:
    """Hash a JSON object while excluding its optional self-hash field."""

    payload = dict(value)
    payload.pop("payload_sha256", None)
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def resolve_source_paths(
    repository_root: Path, config: Mapping[str, Any]
) -> dict[str, Path]:
    root = repository_root.resolve()
    paths: dict[str, Path] = {}
    for name, value in config["source_contract"].items():
        path = (root / str(value)).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"source path escapes repository: {path}")
        if not path.exists():
            raise FileNotFoundError(f"missing source_contract path {name}: {path}")
        paths[name] = path
    return paths


def _validate_source_hashes(paths: Mapping[str, Path]) -> dict[str, str]:
    contract = load_json(paths["split_contract"])
    expected = {
        "records": str(contract["source_records"]["sha256"]).lower(),
        "authoritative_split": str(contract["split"]["sha256"]).lower(),
        "peak_cache_manifest": str(contract["peak_cache"]["sha256"]).lower(),
    }
    actual = {
        "records": sha256_file(paths["records"]).lower(),
        "authoritative_split": sha256_file(paths["authoritative_split"]).lower(),
        "peak_cache_manifest": sha256_file(paths["peak_cache_manifest"]).lower(),
    }
    for name, digest in expected.items():
        if actual[name] != digest:
            raise ValueError(f"{name} SHA-256 disagrees with frozen split contract")
    return actual


def _load_train_tetragonal_records(
    records_path: Path,
    split_by_id: Mapping[str, str],
    fingerprint_by_id: Mapping[str, str],
    crystal_system_by_id: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Retain and decode structures only for authoritative Train tetragonal IDs."""

    train_ids = {
        material_id
        for material_id, split in split_by_id.items()
        if split == "train" and crystal_system_by_id[material_id] == "tetragonal"
    }
    records: list[dict[str, Any]] = []
    with records_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            material_id = str(row["material_id"])
            if material_id not in train_ids:
                continue
            if str(row.get("crystal_system")) != "tetragonal":
                raise ValueError(
                    f"Train crystal-system mismatch at line {line_number}: {material_id}"
                )
            if str(row["structure_fingerprint"]) != fingerprint_by_id[material_id]:
                raise ValueError(
                    f"Train fingerprint mismatch at line {line_number}: {material_id}"
                )
            item = dict(row)
            item["authoritative_split"] = "train"
            records.append(item)
    records.sort(key=lambda row: str(row["material_id"]))
    if len(records) != len(train_ids):
        present = {str(row["material_id"]) for row in records}
        missing = sorted(train_ids - present)
        raise ValueError(f"missing {len(missing)} Train tetragonal records")
    return records


def load_train_parent_contexts(
    repository_root: Path,
    config: Mapping[str, Any],
    *,
    parent_count: int,
) -> tuple[list[ParentContext], list[dict[str, Any]], dict[str, Any]]:
    """Select conventional tetragonal parents without retaining non-Train records."""

    if parent_count < 1:
        raise ValueError("parent_count must be positive")
    if str(config["factorial"]["split"]) != "train":
        raise ValueError("Stage-1 factorial data are frozen to the Train split")
    paths = resolve_source_paths(repository_root, config)
    source_hashes = _validate_source_hashes(paths)
    split_by_id, fingerprint_by_id, crystal_system_by_id, split_manifest = (
        load_authoritative_split(paths["authoritative_split"])
    )
    records = _load_train_tetragonal_records(
        paths["records"], split_by_id, fingerprint_by_id, crystal_system_by_id
    )
    peak_manifest = load_csv_index(paths["peak_cache_manifest"], "material_id")
    audit, features = audit_tetragonal_pool(
        records, peak_manifest, config["canonical_cell"]
    )
    selected = select_representative_parents(
        features, count=parent_count, split="train"
    )
    if any(bool(row.get("restandardized", True)) for row in selected):
        raise RuntimeError("non-conventional parent escaped the Stage-1 selection gate")
    contexts = [
        build_parent_context(row, peak_manifest, paths, config["canonical_cell"])
        for row in selected
    ]
    if len(contexts) != parent_count:
        raise RuntimeError("parent selection returned an incomplete sample")
    if any(context.split != "train" for context in contexts):
        raise RuntimeError("non-Train parent escaped the Stage-1 selection gate")
    if any(
        not is_conventional_tetragonal_lattice(
            context.structure.lattice, config["canonical_cell"]
        )
        for context in contexts
    ):
        raise RuntimeError("selected parent context is not conventional tetragonal")
    provenance = {
        "source_sha256": source_hashes,
        "split_algorithm": split_manifest.get("algorithm"),
        "split_seed": split_manifest.get("seed"),
        "train_tetragonal_parent_count": len(records),
        "conventional_candidate_count": sum(
            not bool(row["restandardized"]) for row in features
        ),
        "excluded_nonconventional_parent_count": int(
            audit["stored_nonconventional_count"]
        ),
        "selected_parent_count": len(contexts),
        "structure_splits_retained": ["train"],
    }
    return contexts, selected, provenance


def _sample_block_states(
    *,
    dataset_seed: int,
    parent_id: str,
    block_id: int,
    q_low: float,
    q_high: float,
) -> tuple[np.ndarray, np.ndarray]:
    seed = stable_seed(dataset_seed, "factorial-block", parent_id, block_id)
    rng = np.random.default_rng(seed)
    structure = rng.uniform(q_low, q_high, size=(2, 2))
    measurement = rng.uniform(q_low, q_high, size=(2, 2))
    if np.array_equal(structure[0], structure[1]):
        raise RuntimeError("independently sampled structure states are identical")
    if np.array_equal(measurement[0], measurement[1]):
        raise RuntimeError("independently sampled measurement states are identical")
    return structure, measurement


def build_factorial_manifest(
    contexts: Sequence[ParentContext],
    selected: Sequence[Mapping[str, Any]],
    provenance: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    blocks_per_parent: int | None = None,
    training_blocks_per_parent: int | None = None,
    purpose: str = "full_pilot",
    artifact_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    factorial = config["factorial"]
    total_blocks = int(
        factorial["blocks_per_parent"]
        if blocks_per_parent is None
        else blocks_per_parent
    )
    train_blocks = int(
        factorial["training_blocks_per_parent"]
        if training_blocks_per_parent is None
        else training_blocks_per_parent
    )
    if not 0 < train_blocks <= total_blocks:
        raise ValueError("training block count must lie in [1, blocks_per_parent]")
    if len(contexts) != len(selected):
        raise ValueError("selected parent metadata are misaligned with contexts")
    resolved_reference_q = resolve_reference_q(
        config["parameterization"], config["factorial"]
    )
    q_low, q_high = [
        float(value) for value in config["parameterization"]["truth_q_range"]
    ]
    domain_low, domain_high = [
        float(value) for value in config["parameterization"]["q_bounds"]
    ]
    if not domain_low <= q_low < q_high <= domain_high:
        raise ValueError("truth_q_range must lie within q_bounds")
    blocks: list[dict[str, Any]] = []
    for parent_index, context in enumerate(contexts):
        for block_id in range(total_blocks):
            theta_s, theta_m = _sample_block_states(
                dataset_seed=int(config["dataset_seed"]),
                parent_id=context.material_id,
                block_id=block_id,
                q_low=q_low,
                q_high=q_high,
            )
            blocks.append(
                {
                    "parent_id": context.material_id,
                    "parent_index": parent_index,
                    "block_id": block_id,
                    "sampling_seed": int(
                        stable_seed(
                            int(config["dataset_seed"]),
                            "factorial-block",
                            context.material_id,
                            block_id,
                        )
                    ),
                    "subset": "training" if block_id < train_blocks else "sanity_eval",
                    "structure_state_ids": [
                        f"{context.material_id}:b{block_id:02d}:s1",
                        f"{context.material_id}:b{block_id:02d}:s2",
                    ],
                    "measurement_state_ids": [
                        f"{context.material_id}:b{block_id:02d}:m1",
                        f"{context.material_id}:b{block_id:02d}:m2",
                    ],
                    "theta_s": theta_s.tolist(),
                    "theta_m": theta_m.tolist(),
                    "corner_order": list(CORNER_ORDER),
                }
            )
    parent_rows = []
    for context, row in zip(contexts, selected, strict=True):
        parent_rows.append(
            {
                "parent_id": context.material_id,
                "formula": context.formula,
                "split": context.split,
                "space_group": context.space_group,
                "fingerprint": context.fingerprint,
                "a0_angstrom": float(context.structure.lattice.a),
                "c0_angstrom": float(context.structure.lattice.c),
                "peak_count": context.peak_count,
                "selection_rank": int(row["selection_rank"]),
                "stored_cell_conventional": True,
                "restandardized": False,
            }
        )
    effective_factorial = dict(factorial)
    effective_factorial.update(
        {
            "blocks_per_parent": total_blocks,
            "training_blocks_per_parent": train_blocks,
            "evaluation_blocks_per_parent": total_blocks - train_blocks,
        }
    )
    payload: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA,
        "purpose": purpose,
        "dataset_seed": int(config["dataset_seed"]),
        "source_provenance": dict(provenance),
        "artifact_provenance": (
            {} if artifact_provenance is None else dict(artifact_provenance)
        ),
        "config_contract": {
            "parameterization": dict(config["parameterization"]),
            "grid": dict(config["grid"]),
            "factorial": effective_factorial,
        },
        "execution_boundary": dict(config["execution_boundary"]),
        "counts": {
            "parents": len(contexts),
            "blocks_per_parent": total_blocks,
            "training_blocks_per_parent": train_blocks,
            "evaluation_blocks_per_parent": total_blocks - train_blocks,
            "blocks": len(blocks),
            "spectra": len(blocks) * 4,
        },
        "parents": parent_rows,
        "blocks": blocks,
        "sampling_rejections": [],
        "resolved_reference_q": resolved_reference_q.tolist(),
    }
    payload["payload_sha256"] = payload_sha256(payload)
    validate_factorial_manifest(payload)
    return payload


def corner_q_values(block: Mapping[str, Any]) -> np.ndarray:
    theta_s = np.asarray(block["theta_s"], dtype=np.float64)
    theta_m = np.asarray(block["theta_m"], dtype=np.float64)
    if theta_s.shape != (2, 2) or theta_m.shape != (2, 2):
        raise ValueError("factorial states must each have shape (2, 2)")
    output = np.empty((2, 2, 4), dtype=np.float64)
    for structure_index in range(2):
        for measurement_index in range(2):
            output[structure_index, measurement_index, :2] = theta_s[structure_index]
            output[structure_index, measurement_index, 2:] = theta_m[measurement_index]
    return output


def validate_factorial_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("unsupported factorial manifest schema")
    if manifest.get("payload_sha256") != payload_sha256(manifest):
        raise ValueError("factorial manifest self-hash mismatch")
    counts = manifest["counts"]
    parents = manifest["parents"]
    blocks = manifest["blocks"]
    if int(counts["parents"]) != len(parents):
        raise ValueError("parent count mismatch")
    if int(counts["blocks"]) != len(blocks):
        raise ValueError("block count mismatch")
    if int(counts["spectra"]) != 4 * len(blocks):
        raise ValueError("spectrum count mismatch")
    parent_ids = {str(row["parent_id"]) for row in parents}
    if len(parent_ids) != len(parents):
        raise ValueError("duplicate parent ID")
    if any(str(row["split"]) != "train" for row in parents):
        raise ValueError("manifest contains a non-Train parent")
    if any(
        not bool(row.get("stored_cell_conventional", False))
        or bool(row.get("restandardized", True))
        for row in parents
    ):
        raise ValueError("manifest contains a non-conventional parent")
    parameterization = manifest["config_contract"]["parameterization"]
    resolved_reference_q = resolve_reference_q(
        parameterization, manifest["config_contract"]["factorial"]
    )
    np.testing.assert_array_equal(
        resolved_reference_q,
        np.asarray(manifest["resolved_reference_q"], dtype=np.float64),
    )
    q_low, q_high = [float(value) for value in parameterization["truth_q_range"]]
    seen: set[tuple[str, int]] = set()
    subset_counts: dict[str, int] = {"training": 0, "sanity_eval": 0}
    for block in blocks:
        key = (str(block["parent_id"]), int(block["block_id"]))
        if key in seen:
            raise ValueError(f"duplicate factorial block: {key}")
        seen.add(key)
        if key[0] not in parent_ids:
            raise ValueError("factorial block references an unknown parent")
        subset = str(block["subset"])
        if subset not in subset_counts:
            raise ValueError(f"invalid factorial subset: {subset}")
        subset_counts[subset] += 1
        if tuple(block["corner_order"]) != CORNER_ORDER:
            raise ValueError("factorial corner order is not x11/x12/x21/x22")
        expected_seed = stable_seed(
            int(manifest["dataset_seed"]), "factorial-block", key[0], key[1]
        )
        if int(block.get("sampling_seed", -1)) != expected_seed:
            raise ValueError("factorial block sampling seed mismatch")
        q = corner_q_values(block)
        if not np.isfinite(q).all() or np.any(q < q_low) or np.any(q > q_high):
            raise ValueError("factorial block contains invalid q values")
        np.testing.assert_array_equal(q[0, 0, :2], q[0, 1, :2])
        np.testing.assert_array_equal(q[1, 0, :2], q[1, 1, :2])
        np.testing.assert_array_equal(q[0, 0, 2:], q[1, 0, 2:])
        np.testing.assert_array_equal(q[0, 1, 2:], q[1, 1, 2:])
        if np.array_equal(q[0, 0, :2], q[1, 0, :2]):
            raise ValueError("factorial structure states are identical")
        if np.array_equal(q[0, 0, 2:], q[0, 1, 2:]):
            raise ValueError("factorial measurement states are identical")
    parent_count = int(counts["parents"])
    expected_training = parent_count * int(counts["training_blocks_per_parent"])
    expected_eval = parent_count * int(counts["evaluation_blocks_per_parent"])
    if subset_counts != {"training": expected_training, "sanity_eval": expected_eval}:
        raise ValueError("factorial 12/4 block split count mismatch")


def build_eval_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    validate_factorial_manifest(manifest)
    blocks = [dict(row) for row in manifest["blocks"] if row["subset"] == "sanity_eval"]
    payload: dict[str, Any] = {
        "schema_version": "xrd-inversion-factorial-eval-manifest-v1",
        "source_manifest_payload_sha256": manifest["payload_sha256"],
        "scope": "train_parent_internal_unseen_intervention_sanity_only",
        "formal_generalization_claim": False,
        "parents": list(manifest["parents"]),
        "blocks": blocks,
        "counts": {"blocks": len(blocks), "spectra": 4 * len(blocks)},
        "corner_order": list(CORNER_ORDER),
        "resolved_reference_q": list(manifest["resolved_reference_q"]),
        "artifact_provenance": dict(manifest.get("artifact_provenance", {})),
        "source_provenance": dict(manifest["source_provenance"]),
        "structure_parameter_order": ["q_u", "q_v"],
        "measurement_parameter_order": ["q_delta", "q_w"],
    }
    payload["payload_sha256"] = payload_sha256(payload)
    return payload


def _render_parent_blocks(
    context: ParentContext,
    blocks: Sequence[Mapping[str, Any]],
    config: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    runtime = config["runtime"]
    model = CachedTetragonalGPUForward(
        context.structure,
        grid_config=config["grid"],
        parameter_config=config["parameterization"],
        device=str(runtime["device"]),
        dtype=torch.float64,
    )
    q = np.concatenate([corner_q_values(block).reshape(4, 4) for block in blocks], axis=0)
    chunks: list[np.ndarray] = []
    batch_size = int(runtime["render_batch_size"])
    with torch.no_grad(), torch.autocast(device_type="cuda", enabled=False):
        for start in range(0, len(q), batch_size):
            tensor = torch.as_tensor(
                q[start : start + batch_size], device=model.device, dtype=model.dtype
            )
            chunks.append(model.transformed(tensor).cpu().numpy())
        reference_q = torch.as_tensor(
            resolve_reference_q(config["parameterization"], config["factorial"]),
            device=model.device,
            dtype=model.dtype,
        )
        reference = model.transformed(reference_q).cpu().numpy()
    observed = np.concatenate(chunks, axis=0).reshape(len(blocks), 2, 2, -1)
    reference_grid = np.broadcast_to(
        reference.reshape(1, 1, 1, -1), observed.shape
    )
    inputs = np.stack((observed, reference_grid, observed - reference_grid), axis=3)
    theta_s = np.stack(
        [corner_q_values(block)[..., :2] for block in blocks], axis=0
    )
    theta_m = np.stack(
        [corner_q_values(block)[..., 2:] for block in blocks], axis=0
    )
    return (
        np.asarray(inputs, dtype=np.float32),
        np.asarray(theta_s, dtype=np.float64),
        np.asarray(theta_m, dtype=np.float64),
    )


def render_factorial_bundle(
    manifest: Mapping[str, Any],
    contexts: Sequence[ParentContext],
    config: Mapping[str, Any],
    output_path: Path,
) -> FactorialTensorBundle:
    validate_factorial_manifest(manifest)
    context_by_id = {context.material_id: context for context in contexts}
    if set(context_by_id) != {str(row["parent_id"]) for row in manifest["parents"]}:
        raise ValueError("render contexts do not match the factorial manifest")
    all_inputs: list[np.ndarray] = []
    all_theta_s: list[np.ndarray] = []
    all_theta_m: list[np.ndarray] = []
    parent_ids: list[str] = []
    parent_a: list[float] = []
    parent_c: list[float] = []
    block_ids: list[int] = []
    subsets: list[str] = []
    for parent_number, parent in enumerate(manifest["parents"], start=1):
        parent_id = str(parent["parent_id"])
        blocks = [
            block for block in manifest["blocks"] if str(block["parent_id"]) == parent_id
        ]
        print(
            f"factorization: render parent {parent_number}/{len(manifest['parents'])} "
            f"{parent_id} ({len(blocks) * 4} spectra)",
            flush=True,
        )
        inputs, theta_s, theta_m = _render_parent_blocks(
            context_by_id[parent_id], blocks, config
        )
        all_inputs.append(inputs)
        all_theta_s.append(theta_s)
        all_theta_m.append(theta_m)
        parent_ids.extend([parent_id] * len(blocks))
        parent_a.extend([float(parent["a0_angstrom"])] * len(blocks))
        parent_c.extend([float(parent["c0_angstrom"])] * len(blocks))
        block_ids.extend(int(block["block_id"]) for block in blocks)
        subsets.extend(str(block["subset"]) for block in blocks)
        del inputs, theta_s, theta_m
        torch.cuda.empty_cache()
    bundle = FactorialTensorBundle(
        inputs=np.concatenate(all_inputs, axis=0),
        theta_s=np.concatenate(all_theta_s, axis=0),
        theta_m=np.concatenate(all_theta_m, axis=0),
        parent_id=np.asarray(parent_ids),
        parent_a=np.asarray(parent_a, dtype=np.float64),
        parent_c=np.asarray(parent_c, dtype=np.float64),
        block_id=np.asarray(block_ids, dtype=np.int64),
        subset=np.asarray(subsets),
        manifest_sha256=str(manifest["payload_sha256"]),
    )
    validate_tensor_bundle(bundle)
    validate_bundle_against_manifest(bundle, manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            schema_version=np.asarray(BUNDLE_SCHEMA),
            inputs=bundle.inputs,
            theta_s=bundle.theta_s,
            theta_m=bundle.theta_m,
            parent_id=bundle.parent_id,
            parent_a=bundle.parent_a,
            parent_c=bundle.parent_c,
            block_id=bundle.block_id,
            subset=bundle.subset,
            manifest_sha256=np.asarray(bundle.manifest_sha256),
        )
    os.replace(temporary, output_path)
    return bundle


def load_factorial_bundle(path: Path) -> FactorialTensorBundle:
    with np.load(path, allow_pickle=False) as archive:
        if str(archive["schema_version"].item()) != BUNDLE_SCHEMA:
            raise ValueError("unsupported factorial bundle schema")
        bundle = FactorialTensorBundle(
            inputs=archive["inputs"],
            theta_s=archive["theta_s"],
            theta_m=archive["theta_m"],
            parent_id=archive["parent_id"],
            parent_a=archive["parent_a"],
            parent_c=archive["parent_c"],
            block_id=archive["block_id"],
            subset=archive["subset"],
            manifest_sha256=str(archive["manifest_sha256"].item()),
        )
    validate_tensor_bundle(bundle)
    return bundle


def validate_tensor_bundle(bundle: FactorialTensorBundle) -> None:
    inputs = np.asarray(bundle.inputs)
    if inputs.ndim != 5 or inputs.shape[1:4] != (2, 2, 3):
        raise ValueError("inputs must have shape [block,2,2,3,L]")
    expected_targets = inputs.shape[:3] + (2,)
    if bundle.theta_s.shape != expected_targets or bundle.theta_m.shape != expected_targets:
        raise ValueError("target grids must have shape [block,2,2,2]")
    count = inputs.shape[0]
    for name in ("parent_id", "parent_a", "parent_c", "block_id", "subset"):
        if np.asarray(getattr(bundle, name)).shape != (count,):
            raise ValueError(f"{name} must have one value per block")
    if not (
        np.isfinite(inputs).all()
        and np.isfinite(bundle.theta_s).all()
        and np.isfinite(bundle.theta_m).all()
        and np.isfinite(bundle.parent_a).all()
        and np.isfinite(bundle.parent_c).all()
    ):
        raise ValueError("factorial bundle contains NaN or Inf")
    np.testing.assert_allclose(
        inputs[:, :, :, 2],
        inputs[:, :, :, 0] - inputs[:, :, :, 1],
        rtol=0.0,
        atol=2e-7,
    )
    np.testing.assert_array_equal(bundle.theta_s[:, :, 0], bundle.theta_s[:, :, 1])
    np.testing.assert_array_equal(bundle.theta_m[:, 0, :], bundle.theta_m[:, 1, :])
    if not set(np.unique(bundle.subset)).issubset({"training", "sanity_eval"}):
        raise ValueError("factorial bundle has an invalid subset")
    if inputs.dtype != np.float32:
        raise ValueError("profile cache inputs must be float32")
    if bundle.theta_s.dtype != np.float64 or bundle.theta_m.dtype != np.float64:
        raise ValueError("canonical profile-cache targets must be float64")
    if not bundle.manifest_sha256 or len(bundle.manifest_sha256) != 64:
        raise ValueError("factorial bundle has no valid manifest digest")


def validate_bundle_against_manifest(
    bundle: FactorialTensorBundle, manifest: Mapping[str, Any]
) -> None:
    """Reject stale or reordered profile caches before training."""

    validate_factorial_manifest(manifest)
    validate_tensor_bundle(bundle)
    if bundle.manifest_sha256 != str(manifest["payload_sha256"]):
        raise ValueError("tensor bundle does not belong to the active manifest")
    blocks = list(manifest["blocks"])
    if bundle.block_count != len(blocks):
        raise ValueError("profile cache block count disagrees with manifest")
    expected_parent = np.asarray([str(row["parent_id"]) for row in blocks])
    expected_block = np.asarray([int(row["block_id"]) for row in blocks], dtype=np.int64)
    expected_subset = np.asarray([str(row["subset"]) for row in blocks])
    np.testing.assert_array_equal(bundle.parent_id, expected_parent)
    np.testing.assert_array_equal(bundle.block_id, expected_block)
    np.testing.assert_array_equal(bundle.subset, expected_subset)
    expected_q = np.stack([corner_q_values(row) for row in blocks], axis=0)
    np.testing.assert_array_equal(bundle.theta_s, expected_q[..., :2])
    np.testing.assert_array_equal(bundle.theta_m, expected_q[..., 2:])
    parent_by_id = {
        str(row["parent_id"]): row for row in manifest["parents"]
    }
    expected_a = np.asarray(
        [float(parent_by_id[parent]["a0_angstrom"]) for parent in expected_parent],
        dtype=np.float64,
    )
    expected_c = np.asarray(
        [float(parent_by_id[parent]["c0_angstrom"]) for parent in expected_parent],
        dtype=np.float64,
    )
    np.testing.assert_array_equal(bundle.parent_a, expected_a)
    np.testing.assert_array_equal(bundle.parent_c, expected_c)


def subset_indices(bundle: FactorialTensorBundle, subset: str) -> np.ndarray:
    if subset not in {"training", "sanity_eval"}:
        raise ValueError("subset must be 'training' or 'sanity_eval'")
    indices = np.flatnonzero(bundle.subset == subset)
    if indices.size == 0:
        raise ValueError(f"factorial bundle has no {subset} blocks")
    return indices


def training_channel_statistics(
    bundle: FactorialTensorBundle, indices: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(bundle.inputs[np.asarray(indices, dtype=np.int64)], dtype=np.float64)
    mean = values.mean(axis=(0, 1, 2, 4))
    std = values.std(axis=(0, 1, 2, 4))
    if mean.shape != (3,) or std.shape != (3,) or np.any(std <= 1e-8):
        raise ValueError("invalid Train-only channel statistics")
    return mean.astype(np.float32), std.astype(np.float32)


class FactorialBlockDataset(Dataset[dict[str, torch.Tensor | str | int]]):
    """Torch view that preserves complete 2x2 intervention blocks."""

    def __init__(
        self,
        bundle: FactorialTensorBundle,
        indices: Sequence[int],
        channel_mean: Sequence[float],
        channel_std: Sequence[float],
    ) -> None:
        self.bundle = bundle
        self.indices = np.asarray(indices, dtype=np.int64)
        self.mean = np.asarray(channel_mean, dtype=np.float32).reshape(1, 1, 3, 1)
        self.std = np.asarray(channel_std, dtype=np.float32).reshape(1, 1, 3, 1)
        if self.mean.shape != (1, 1, 3, 1) or np.any(self.std <= 0):
            raise ValueError("channel statistics must contain three positive scales")

    def __len__(self) -> int:
        return int(self.indices.size)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor | str | int]:
        index = int(self.indices[item])
        inputs = (self.bundle.inputs[index] - self.mean) / self.std
        return {
            "inputs": torch.from_numpy(np.asarray(inputs, dtype=np.float32)),
            "theta_s": torch.from_numpy(self.bundle.theta_s[index]),
            "theta_m": torch.from_numpy(self.bundle.theta_m[index]),
            "parent_a": torch.tensor(self.bundle.parent_a[index], dtype=torch.float64),
            "parent_c": torch.tensor(self.bundle.parent_c[index], dtype=torch.float64),
            "parent_id": str(self.bundle.parent_id[index]),
            "block_id": int(self.bundle.block_id[index]),
        }
