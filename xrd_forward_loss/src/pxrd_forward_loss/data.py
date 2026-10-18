"""Deterministic single-parent synthetic data generation and provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import torch
from scipy.stats import qmc
from pymatgen.core import Structure

from xrd_inversion.gpu_forward import CachedTetragonalGPUForward


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_parent(repository_root: Path, material_id: str) -> tuple[Structure, dict[str, Any]]:
    split_manifest = read_json(
        repository_root / "xrd_robustness/data/formal_14060/manifests/split_manifest.json"
    )
    split_rows = {str(row["material_id"]): row for row in split_manifest["records"]}
    if material_id not in split_rows:
        raise ValueError(f"parent is absent from the frozen source split: {material_id}")
    if split_rows[material_id]["split"] != "train":
        raise ValueError("pilot parent must come from the original training fold")
    records_path = (
        repository_root
        / "xrd_robustness/data/formal_14060/mp_processed/structure_records.jsonl"
    )
    for line in records_path.open("r", encoding="utf-8"):
        row = json.loads(line)
        if str(row.get("material_id")) == material_id:
            if row.get("crystal_system") != "tetragonal":
                raise ValueError("pilot parent must be tetragonal")
            return Structure.from_dict(row["standardized_structure"]), row
    raise ValueError(f"parent is missing from structure records: {material_id}")


def make_forward_model(repository_root: Path, config: dict[str, Any], structure: Structure):
    forward_config = read_json(repository_root / config["forward_model"]["config_path"])
    return CachedTetragonalGPUForward(
        structure,
        grid_config=forward_config["grid"],
        parameter_config=forward_config["parameterization"],
        device=str(config["forward_model"]["device"]),
        dtype=torch.float64,
    ), forward_config


def split_indices(n: int, *, seed: int, train_fraction: float, validation_fraction: float):
    if not 0 < train_fraction < 1 or not 0 < validation_fraction < 1:
        raise ValueError("split fractions must be strictly between zero and one")
    if train_fraction + validation_fraction >= 1:
        raise ValueError("train and validation fractions must sum to less than one")
    permutation = np.random.default_rng(seed).permutation(n)
    n_train = int(round(n * train_fraction))
    n_validation = int(round(n * validation_fraction))
    return {
        "train": permutation[:n_train],
        "validation": permutation[n_train : n_train + n_validation],
        "test": permutation[n_train + n_validation :],
    }


def _measurement_perturbation(
    profile: np.ndarray,
    axis: np.ndarray,
    *,
    rng: np.random.Generator,
    count_scale: float,
    background_min: float,
    background_span: float,
) -> np.ndarray:
    coordinate = (axis - axis.min()) / max(axis.max() - axis.min(), 1e-12)
    background = background_min + background_span * coordinate
    counts = rng.poisson(np.maximum(profile, 0.0) * count_scale + background)
    noisy = counts.astype(np.float64)
    peak = float(noisy.max())
    if not peak > 0:
        raise RuntimeError("synthetic count profile has no positive signal")
    return noisy / peak


def build_dataset(repository_root: Path, config: dict[str, Any]):
    structure, record = load_parent(repository_root, config["parent_material_id"])
    forward, forward_config = make_forward_model(repository_root, config, structure)
    power = int(config["data"]["sobol_power"])
    sampler = qmc.Sobol(d=2, scramble=True, seed=int(config["data"]["sobol_seed"]))
    unit_q = sampler.random_base2(power)
    q_bound = float(config["parameter_q_bounds"][1])
    if float(config["parameter_q_bounds"][0]) != -q_bound:
        raise ValueError("this pilot requires symmetric normalized q bounds")
    q_values = (unit_q * 2.0 - 1.0) * q_bound
    axis = forward.axis.detach().cpu().numpy()
    measurement_rng = np.random.default_rng(int(config["data"]["measurement_seed"]))
    noisy_profiles = []
    clean_profiles = []
    fixed_nuisance = torch.as_tensor(
        config["fixed_nuisance_q"], dtype=torch.float64, device=forward.device
    )
    with torch.no_grad():
        for start in range(0, len(q_values), 16):
            lattice_q = torch.as_tensor(
                q_values[start : start + 16], dtype=torch.float64, device=forward.device
            )
            nuisance = fixed_nuisance.expand(lattice_q.shape[0], -1)
            full_q = torch.cat((lattice_q, nuisance), dim=1)
            clean = forward.render(full_q, compatibility=False).cpu().numpy()
            for profile in clean:
                noisy = _measurement_perturbation(
                    profile,
                    axis,
                    rng=measurement_rng,
                    count_scale=float(config["data"]["poisson_count_scale"]),
                    background_min=float(config["data"]["background_counts_min"]),
                    background_span=float(config["data"]["background_counts_span"]),
                )
                noisy_profiles.append(
                    np.log1p(100.0 * noisy) / np.log(101.0)
                )
                clean_profiles.append(np.log1p(100.0 * profile) / np.log(101.0))
    noisy_array = np.asarray(noisy_profiles, dtype=np.float32)
    clean_array = np.asarray(clean_profiles, dtype=np.float32)
    splits = split_indices(
        len(q_values),
        seed=int(config["data"]["split_seed"]),
        train_fraction=float(config["data"]["train_fraction"]),
        validation_fraction=float(config["data"]["validation_fraction"]),
    )
    digest = hashlib.sha256()
    for array in (q_values.astype(np.float64), noisy_array, clean_array):
        digest.update(np.ascontiguousarray(array).tobytes())
    metadata = {
        "material_id": str(record["material_id"]),
        "formula": str(record["formula"]),
        "source_split": "train",
        "structure_fingerprint": str(record["structure_fingerprint"]),
        "lattice_angstrom": {
            "a": float(structure.lattice.a),
            "c": float(structure.lattice.c),
        },
        "space_group": int(record["space_group_recomputed"]),
        "nsites": int(record["nsites"]),
        "pattern_count": int(len(q_values)),
        "split_counts": {key: int(len(value)) for key, value in splits.items()},
        "two_theta_grid": {
            key: forward_config["grid"][key]
            for key in ("two_theta_min", "two_theta_max", "step", "wavelength_angstrom")
        },
        "dataset_sha256": digest.hexdigest(),
        "measurement_model": "Poisson counts plus linear 100-200 count background, independently seeded per pattern, followed by max normalization and log1p_100 transform",
        "normalization": "per-pattern intensity max; same measured input used by A and B",
        "scope": "one known fixed tetragonal parent; parameter generalization only",
    }
    arrays = {
        "q": q_values.astype(np.float32),
        "noisy": noisy_array,
        "clean": clean_array,
        **{f"{key}_indices": value.astype(np.int64) for key, value in splits.items()},
    }
    return arrays, metadata, structure, forward, forward_config
