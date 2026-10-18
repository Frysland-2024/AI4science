"""HfCd data adapter that reuses the V9 peak-table measurement simulator.

The differentiable forward model creates the clean reference and lattice labels.
V9's NumPy sampler/renderer creates observed views only; it is never placed on
the autograd path. Measurement nuisance draws do not modify ``theta_true``.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import torch
from pymatgen.core import Lattice, Structure
from scipy.stats import qmc

from xrd_robustness.physics import PhysicsParameterSampler, PhysicsParameters
from xrd_robustness.simulator import (
    SimulationGrid,
    ideal_peak_table,
    simulate_from_peak_table,
)

from .data import load_parent, make_forward_model, read_json, split_indices


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_sha256(array: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(array).tobytes())


def _seed_from_parts(*parts: object) -> int:
    payload = ":".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "little")


def transform_profile(profile: np.ndarray) -> np.ndarray:
    values = np.asarray(profile, dtype=np.float64)
    if values.ndim != 1 or not np.isfinite(values).all() or np.min(values, initial=0.0) < 0:
        raise ValueError("profile transform requires finite non-negative one-dimensional data")
    return (np.log1p(100.0 * values) / math.log(101.0)).astype(np.float32)


def q_to_lattice(q: np.ndarray, structure: Structure, forward_config: dict[str, Any]):
    parameterization = forward_config["parameterization"]
    du_half = float(parameterization["du_half_range"])
    dv_half = float(parameterization["dv_half_range"])
    u0 = (2.0 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3.0
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    u = u0 + float(q[0]) * du_half
    v = v0 + float(q[1]) * dv_half
    return math.exp(u - v / 3.0), math.exp(u + 2.0 * v / 3.0)


def structure_at_q(structure: Structure, q: np.ndarray, forward_config: dict[str, Any]):
    a, c = q_to_lattice(q, structure, forward_config)
    return Structure(
        lattice=Lattice.tetragonal(a, c),
        species=[site.species for site in structure],
        coords=structure.frac_coords,
        coords_are_cartesian=False,
        charge=structure.charge,
        site_properties=structure.site_properties,
        labels=structure.labels,
        properties=structure.properties,
    )


def _grid_from_forward_config(forward_config: dict[str, Any]) -> tuple[SimulationGrid, SimulationGrid]:
    raw = forward_config["grid"]
    wavelength = float(raw["wavelength_angstrom"])
    grid = SimulationGrid(
        two_theta_min=float(raw["two_theta_min"]),
        two_theta_max=float(raw["two_theta_max"]),
        step=float(raw["step"]),
        wavelength=wavelength,
    )
    padding = float(raw.get("peak_calculation_padding_deg", 0.0))
    padded_grid = SimulationGrid(
        two_theta_min=grid.two_theta_min - padding,
        two_theta_max=grid.two_theta_max + padding,
        step=grid.step,
        wavelength=wavelength,
    )
    return grid, padded_grid


def _padded_peak_table(structure: Structure, padded_grid: SimulationGrid):
    """Use the V9 reflection-aware peak-table builder over the forward padding."""
    return ideal_peak_table(structure, padded_grid)


def _clean_v9_params() -> PhysicsParameters:
    return PhysicsParameters(
        delta_2theta_deg=0.0,
        fwhm_deg=0.08,
        background_to_peak_ratio=0.0,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=0,
        zero_shift_active=False,
        broadening_active=False,
        background_active=False,
        noise_active=False,
        preferred_orientation_active=False,
    )


def _baseline_v9_profile(
    structure: Structure,
    *,
    grid: SimulationGrid,
    padded_grid: SimulationGrid,
) -> np.ndarray:
    peaks = _padded_peak_table(structure, padded_grid)
    return simulate_from_peak_table(
        peaks.positions,
        peaks.intensities,
        _clean_v9_params(),
        rng_seed=0,
        grid=grid,
        normalize=True,
        reflection_table=peaks,
    )


def _legacy_observation(
    clean_profile: np.ndarray,
    *,
    rng_seed: int,
    count_scale: float,
    background_min: float,
    background_span: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    coordinate = np.linspace(0.0, 1.0, clean_profile.size, dtype=np.float64)
    background_counts = background_min + background_span * coordinate
    expected_counts = np.clip(clean_profile, 0.0, None) * count_scale + background_counts
    counts = np.random.default_rng(rng_seed).poisson(expected_counts)
    maximum = float(counts.max(initial=0))
    if maximum <= 0:
        raise RuntimeError("legacy Poisson observation has no positive counts")
    observed = counts.astype(np.float64) / maximum
    return observed.astype(np.float32), {
        "perturbation_types": ["poisson_count_noise", "linear_count_background"],
        "strengths": {
            "poisson_count_scale": float(count_scale),
            "background_counts_min": float(background_min),
            "background_counts_max": float(background_min + background_span),
        },
        "renderer_seed": int(rng_seed),
        "normalization": "single per-pattern maximum normalization after background and Poisson sampling",
    }


def audit_clean_renderer_compatibility(
    structure: Structure,
    forward: Any,
    forward_config: dict[str, Any],
    q_probes: list[np.ndarray],
    *,
    max_abs_tolerance: float,
    rmse_tolerance: float,
) -> dict[str, Any]:
    grid, padded_grid = _grid_from_forward_config(forward_config)
    rows = []
    with torch.no_grad():
        for q in q_probes:
            q_tensor = torch.as_tensor(
                [float(q[0]), float(q[1]), 0.0, -1.0],
                dtype=torch.float64,
                device=forward.device,
            )
            forward_profile = forward.render(q_tensor, compatibility=False).cpu().numpy()
            q_structure = structure_at_q(structure, q, forward_config)
            v9_profile = _baseline_v9_profile(
                q_structure, grid=grid, padded_grid=padded_grid
            )
            difference = np.asarray(forward_profile, dtype=np.float64) - np.asarray(
                v9_profile, dtype=np.float64
            )
            rows.append(
                {
                    "q": np.asarray(q, dtype=np.float64).tolist(),
                    "max_abs_error": float(np.max(np.abs(difference))),
                    "rmse": float(np.sqrt(np.mean(difference**2))),
                    "v9_max": float(np.max(v9_profile)),
                    "forward_max": float(np.max(forward_profile)),
                }
            )
    max_abs = max(row["max_abs_error"] for row in rows)
    worst_rmse = max(row["rmse"] for row in rows)
    return {
        "gate": "baseline V9 renderer vs differentiable forward at same q, no measurement nuisance",
        "passed": bool(max_abs <= max_abs_tolerance and worst_rmse <= rmse_tolerance),
        "max_abs_tolerance": float(max_abs_tolerance),
        "rmse_tolerance": float(rmse_tolerance),
        "max_abs_error": max_abs,
        "max_probe_rmse": worst_rmse,
        "probes": rows,
    }


def build_perturbation_dataset(
    repository_root: Path,
    source_root: Path,
    config: dict[str, Any],
    *,
    config_sha256: str,
    phase: str,
) -> tuple[dict[str, np.ndarray], dict[str, Any], list[dict[str, Any]], Any, dict[str, Any]]:
    if phase not in {"phase1_noise_background", "phase2_add_broadening_and_zero_shift"}:
        raise ValueError(f"unsupported perturbation phase: {phase}")
    structure, record = load_parent(source_root, config["parent_material_id"])
    forward, forward_config = make_forward_model(repository_root, config, structure)
    data_config = config["data"]
    qmc_sampler = qmc.Sobol(d=2, scramble=True, seed=int(data_config["sobol_seed"]))
    unit_q = qmc_sampler.random_base2(int(data_config["sobol_power"]))
    q_bounds = np.asarray(config["parameter_q_bounds"], dtype=np.float64)
    if q_bounds.shape != (2,) or not np.isclose(q_bounds[0], -q_bounds[1]):
        raise ValueError("parameter q bounds must be symmetric")
    q_values = (unit_q * 2.0 - 1.0) * float(q_bounds[1])

    grid, padded_grid = _grid_from_forward_config(forward_config)
    split_map = split_indices(
        len(q_values),
        seed=int(data_config["split_seed"]),
        train_fraction=float(data_config["train_fraction"]),
        validation_fraction=float(data_config["validation_fraction"]),
    )
    index_to_split = {
        int(index): split for split, indices in split_map.items() for index in indices
    }

    q_probe_indices = sorted(set([0, len(q_values) // 2, len(q_values) - 1]))
    q_probes = [q_values[index] for index in q_probe_indices]
    parity = audit_clean_renderer_compatibility(
        structure,
        forward,
        forward_config,
        q_probes,
        max_abs_tolerance=float(
            config["physical_gates"]["baseline_v9_forward_profile_max_abs_tolerance"]
        ),
        rmse_tolerance=float(
            config["physical_gates"]["baseline_v9_forward_profile_rmse_tolerance"]
        ),
    )
    if not parity["passed"]:
        raise RuntimeError(f"V9 clean-render compatibility gate failed: {parity}")

    v9_sampler = PhysicsParameterSampler.from_mapping(
        {
            "run_seed": int(data_config["v9_sampler_seed"]),
            "profiles": {phase: config["v9_profiles"][phase]},
        }
    )
    fixed_nuisance = torch.as_tensor(
        config["fixed_nuisance_q"], dtype=torch.float64, device=forward.device
    )
    clean_raw_rows: list[np.ndarray] = []
    simple_raw_rows: list[np.ndarray] = []
    v9_raw_rows: list[np.ndarray] = []
    sample_records: list[dict[str, Any]] = []
    transform_started_profiles: list[np.ndarray] = []
    with torch.no_grad():
        for index, q in enumerate(q_values):
            lattice_q = torch.as_tensor(q[None, :], dtype=torch.float64, device=forward.device)
            full_q = torch.cat((lattice_q, fixed_nuisance.expand(1, -1)), dim=1)
            clean_raw = forward.render(full_q, compatibility=False)[0].cpu().numpy()
            clean = transform_profile(clean_raw)

            simple_seed = _seed_from_parts(
                data_config["legacy_measurement_seed"], config["parent_material_id"], index
            )
            simple_raw, simple_nuisance = _legacy_observation(
                clean_raw,
                rng_seed=simple_seed,
                count_scale=float(data_config["legacy_poisson_count_scale"]),
                background_min=float(data_config["legacy_background_counts_min"]),
                background_span=float(data_config["legacy_background_counts_span"]),
            )

            context_index = v9_sampler.sample(
                phase,
                epoch=0,
                global_step=index,
                material_id=str(record["material_id"]),
                view_id=1,
            )
            parameters, sampler_seed = context_index
            renderer_seed = _seed_from_parts(sampler_seed, "renderer")
            q_structure = structure_at_q(structure, q, forward_config)
            peak_table = _padded_peak_table(q_structure, padded_grid)
            v9_raw = simulate_from_peak_table(
                peak_table.positions,
                peak_table.intensities,
                parameters,
                rng_seed=renderer_seed,
                grid=grid,
                normalize=True,
                return_diagnostics=False,
                reflection_table=peak_table,
            )
            if not np.isfinite(v9_raw).all() or np.min(v9_raw, initial=0.0) < 0:
                raise RuntimeError(f"V9 renderer produced an invalid profile at sample {index}")
            clean_raw_rows.append(np.asarray(clean_raw, dtype=np.float32))
            simple_raw_rows.append(np.asarray(simple_raw, dtype=np.float32))
            v9_raw_rows.append(np.asarray(v9_raw, dtype=np.float32))
            transform_started_profiles.append(clean)
            # Keep the input transform explicitly separate from the raw count/intensity domain.
            simple_observed = transform_profile(simple_raw)
            v9_observed = transform_profile(v9_raw)
            parameter_dict = parameters.to_dict()
            sample_records.append(
                {
                    "sample_id": f"sample-{index:04d}",
                    "sample_index": int(index),
                    "split": index_to_split[index],
                    "theta_true": {
                        "du_normalized": float(q[0]),
                        "dv_normalized": float(q[1]),
                    },
                    "lattice_true_angstrom": {
                        "a": float(q_to_lattice(q, structure, forward_config)[0]),
                        "c": float(q_to_lattice(q, structure, forward_config)[1]),
                    },
                    "clean_profile_sha256": array_sha256(clean),
                    "observed_profile_simple_sha256": array_sha256(simple_observed),
                    "observed_profile_v9_sha256": array_sha256(v9_observed),
                    "structure_source": (
                        "xrd_robustness/data/formal_14060/mp_processed/structure_records.jsonl"
                        f"#material_id={record['material_id']}"
                    ),
                    "cif_source": None,
                    "structure_fingerprint": str(record["structure_fingerprint"]),
                    "simulator_versions": {
                        "clean_forward_contract": "tetragonal_torch_dense_v1",
                        "v9_renderer_contract": "xrd_robustness_v7_independent_implementation",
                    },
                    "config_sha256": config_sha256,
                    "nuisance_metadata": {
                        "simple": simple_nuisance,
                        "v9": {
                            "perturbation_types": list(parameters.active_perturbation_names),
                            "strengths": parameter_dict,
                            "sampler_seed": int(sampler_seed),
                            "renderer_seed": int(renderer_seed),
                            "phase": phase,
                            "config_profile": phase,
                        },
                    },
                }
            )
    clean_raw_array = np.asarray(clean_raw_rows, dtype=np.float32)
    simple_raw_array = np.asarray(simple_raw_rows, dtype=np.float32)
    v9_raw_array = np.asarray(v9_raw_rows, dtype=np.float32)
    clean_array = np.asarray(transform_started_profiles, dtype=np.float32)
    simple_array = np.asarray([transform_profile(row) for row in simple_raw_array], dtype=np.float32)
    v9_array = np.asarray([transform_profile(row) for row in v9_raw_array], dtype=np.float32)
    arrays = {
        "q": q_values.astype(np.float32),
        "clean_profile": clean_array,
        "clean_profile_raw": clean_raw_array,
        "observed_profile_simple": simple_array,
        "observed_profile_simple_raw": simple_raw_array,
        "observed_profile_v9": v9_array,
        "observed_profile_v9_raw": v9_raw_array,
        **{f"{key}_indices": value.astype(np.int64) for key, value in split_map.items()},
    }
    all_digest = hashlib.sha256()
    for key in sorted(arrays):
        all_digest.update(key.encode("utf-8"))
        all_digest.update(np.ascontiguousarray(arrays[key]).tobytes())
    v9_source_config = source_root / "xrd_robustness/configs/simulation.method_transfer.frozen.json"
    metadata = {
        "material_id": str(record["material_id"]),
        "formula": str(record["formula"]),
        "source_split": "train",
        "structure_fingerprint": str(record["structure_fingerprint"]),
        "structure_source": "xrd_robustness/data/formal_14060/mp_processed/structure_records.jsonl",
        "cif_source": None,
        "cif_source_note": "The selected local source stores standardized_structure JSON, not a CIF file.",
        "lattice_angstrom": {
            "a": float(structure.lattice.a),
            "c": float(structure.lattice.c),
        },
        "space_group": int(record["space_group_recomputed"]),
        "nsites": int(record["nsites"]),
        "pattern_count": int(len(q_values)),
        "split_counts": {key: int(len(value)) for key, value in split_map.items()},
        "split_indices": {key: value.astype(int).tolist() for key, value in split_map.items()},
        "two_theta_grid": {
            "two_theta_min": grid.two_theta_min,
            "two_theta_max": grid.two_theta_max,
            "step": grid.step,
            "wavelength_angstrom": float(forward_config["grid"]["wavelength_angstrom"]),
        },
        "dataset_sha256": all_digest.hexdigest(),
        "q_storage_dtype": "float32",
        "max_q_float32_rounding": float(
            np.max(np.abs(q_values - q_values.astype(np.float32).astype(np.float64)))
        ),
        "config_sha256": config_sha256,
        "v9_frozen_config_sha256": (
            sha256_bytes(v9_source_config.read_bytes()) if v9_source_config.exists() else None
        ),
        "clean_forward_contract": "tetragonal_torch_dense_v1",
        "v9_renderer_contract": "xrd_robustness_v7_independent_implementation",
        "clean_renderer_compatibility": parity,
        "profile_transform": "log1p(100 * per-pattern-max-normalized profile) / log(101)",
        "ordering": "clean expected intensity -> measurement background -> Poisson plus count-domain Gaussian readout -> clip -> one max normalization -> log1p transform",
        "normalization_policy": "One final max normalization per measured profile; no normalization is applied between background and count sampling.",
        "scope": "single known tetragonal HfCd parent; parameter samples are split, not parent structures",
    }
    return arrays, metadata, sample_records, forward, forward_config


def condition_arrays(arrays: dict[str, np.ndarray], condition: str) -> dict[str, np.ndarray]:
    if condition not in {"simple", "v9"}:
        raise ValueError(f"unknown condition: {condition}")
    key = "observed_profile_simple" if condition == "simple" else "observed_profile_v9"
    return {
        "q": arrays["q"],
        "clean": arrays["clean_profile"],
        "noisy": arrays[key],
    }
