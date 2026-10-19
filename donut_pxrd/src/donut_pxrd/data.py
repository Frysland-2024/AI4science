from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
from pymatgen.core import Lattice, Structure


ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(ROOT / "xrd_inversion" / "src"),
    str(ROOT / "xrd_robustness" / "src"),
    str(ROOT / "xrd_forward_loss" / "src"),
]
from pxrd_forward_loss.measurement_closure import (  # noqa: E402
    expected_intensity_profile,
    expected_profile,
)
from pxrd_forward_loss.measurement_sampling import (  # noqa: E402
    sample_q_bank,
    split_assignment,
    split_q_indices,
)
from xrd_robustness.measurement_models import apply_noise_model  # noqa: E402
from xrd_robustness.physics import PhysicsParameters  # noqa: E402
from xrd_robustness.preferred_orientation import apply_preferred_orientation  # noqa: E402
from xrd_robustness.simulator import (  # noqa: E402
    SimulationGrid,
    ideal_peak_table,
    render_gaussian_peaks,
    simulate_from_peak_table,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode("ascii"))
    digest.update(json.dumps(list(value.shape)).encode("ascii"))
    digest.update(value.tobytes())
    return digest.hexdigest()


def load_forward_driver():
    path = ROOT / "xrd_forward_loss" / "scripts" / "run_issue19_p3.py"
    spec = importlib.util.spec_from_file_location("donut_pxrd_forward_driver", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load existing PXRD forward adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_eta(
    count: int,
    *,
    rng: np.random.Generator,
    include_shift: bool,
    include_width: bool,
    include_background: bool,
) -> np.ndarray:
    eta = np.zeros((count, 3), dtype=np.float64)
    eta[:, 1] = 0.08
    if include_shift:
        eta[:, 0] = rng.uniform(-0.06, 0.06, size=count)
    if include_width:
        eta[:, 1] = rng.uniform(0.08, 0.13, size=count)
    if include_background:
        eta[:, 2] = rng.uniform(0.005, 0.008, size=count)
    return eta


def _render_expected(
    forward: Any,
    q: np.ndarray,
    eta: np.ndarray,
    *,
    background_shape_mode: str,
    batch_size: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    intensity: list[np.ndarray] = []
    transformed: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(q), batch_size):
            stop = min(len(q), start + batch_size)
            q_t = torch.as_tensor(q[start:stop], device="cuda", dtype=torch.float64)
            eta_t = torch.as_tensor(eta[start:stop], device="cuda", dtype=torch.float64)
            raw = expected_intensity_profile(
                forward, q_t, eta_t, background_shape_mode=background_shape_mode
            )
            prof = expected_profile(
                forward, q_t, eta_t, background_shape_mode=background_shape_mode
            )
            intensity.append(raw.detach().cpu().numpy())
            transformed.append(prof.detach().cpu().numpy().astype(np.float32))
    return np.concatenate(intensity), np.concatenate(transformed)


def _draw_count_noise(
    expected_intensity: np.ndarray,
    *,
    seed: int,
    count_scale: int,
    readout_bounds: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    rng = np.random.default_rng(int(seed))
    noisy_rows: list[np.ndarray] = []
    noise_records: list[dict[str, Any]] = []
    for row in expected_intensity:
        readout_sigma = float(rng.uniform(readout_bounds[0], readout_bounds[1]))
        noisy, metadata = apply_noise_model(
            np.asarray(row, dtype=np.float64),
            rng=rng,
            model="poisson_gaussian",
            poisson_count_scale=float(count_scale),
            electronic_noise_std_counts=readout_sigma,
        )
        noisy_rows.append(np.clip(noisy, 0.0, None))
        noise_records.append({"electronic_noise_std_counts": readout_sigma, **metadata})
    noisy_intensity = np.stack(noisy_rows)
    maxima = np.maximum(noisy_intensity.max(axis=1, keepdims=True), 1.0 / count_scale)
    normalized = noisy_intensity / maxima
    observed = np.log1p(100.0 * normalized) / math.log(101.0)
    return observed.astype(np.float32), normalized.astype(np.float32), noise_records


def build_study_data(
    *,
    config: dict[str, Any],
    forward: Any,
    forward_cfg: dict[str, Any],
    structure: Structure,
    output_path: Path,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    data_cfg = config["data"]
    count = int(data_cfg["max_parent_q_draws"])
    q = sample_q_bank(count, seed=int(data_cfg["q_seed"]), q_bound=0.8).astype(np.float64)
    splits = split_q_indices(
        count,
        seed=int(data_cfg["split_seed"]),
        train_fraction=float(data_cfg["split_fractions"]["train"]),
        validation_fraction=float(data_cfg["split_fractions"]["validation"]),
    )
    assignment = split_assignment(splits, count)
    seeds = data_cfg["generator_seeds"]
    shift_rng = np.random.default_rng(int(seeds["zero_shift"]))
    robust_rng = np.random.default_rng(int(seeds["broadening_background"]))

    eta_fixed = _make_eta(count, rng=shift_rng, include_shift=False, include_width=False, include_background=False)
    eta_shift = _make_eta(count, rng=shift_rng, include_shift=True, include_width=False, include_background=False)
    eta_width = _make_eta(count, rng=robust_rng, include_shift=True, include_width=True, include_background=False)
    eta_background = _make_eta(count, rng=robust_rng, include_shift=True, include_width=True, include_background=True)
    eta_noise = eta_background.copy()

    conditions = {
        "experiment_1_fixed": (eta_fixed, "v9_polynomial"),
        "experiment_2_shift": (eta_shift, "v9_polynomial"),
        "experiment_3_width": (eta_width, "v9_polynomial"),
        "experiment_3_background": (eta_background, "v9_polynomial"),
        "experiment_3_noise": (eta_noise, "v9_polynomial"),
    }
    arrays: dict[str, np.ndarray] = {
        "q": q,
        "train_indices": splits["train"].astype(np.int64),
        "validation_indices": splits["validation"].astype(np.int64),
        "test_indices": splits["test"].astype(np.int64),
        "split_assignment": np.asarray(assignment, dtype="U10"),
    }
    noise_records: list[dict[str, Any]] = []
    for name, (eta, mode) in conditions.items():
        raw, expected = _render_expected(forward, q, eta, background_shape_mode=mode)
        if name == "experiment_3_noise":
            observed, normalized, noise_records = _draw_count_noise(
                raw,
                seed=int(seeds["detector_noise"]),
                count_scale=30000,
                readout_bounds=(0.5, 1.5),
            )
        else:
            observed = expected.copy()
            normalized = np.expm1(expected.astype(np.float64) * math.log(101.0)) / 100.0
        arrays[f"{name}_observed"] = observed
        arrays[f"{name}_expected"] = expected
        arrays[f"{name}_normalized_intensity"] = normalized.astype(np.float32)
        arrays[f"{name}_eta_truth"] = eta

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **arrays)
    counts = {name: int(len(values)) for name, values in splits.items()}
    manifest = {
        "schema": "donut_pxrd_frozen_parent_data_v1",
        "config_sha256": sha256_file(Path(__file__).resolve().parents[2] / "configs" / "study_v1.json"),
        "source_cif_sha256": sha256_file(ROOT / config["sources"]["cif"]),
        "base_forward_config_sha256": sha256_file(ROOT / config["sources"]["base_forward_config"]),
        "dataset_npz_sha256": sha256_file(output_path),
        "dataset_path_local_only": str(output_path.resolve()),
        "parent_count": count,
        "split_counts": counts,
        "split_assignment_sha256": sha256_array(arrays["split_assignment"]),
        "test_indices_sha256": sha256_array(arrays["test_indices"]),
        "q_sha256": sha256_array(q),
        "split_before_nuisance_or_noise": True,
        "array_sha256": {key: sha256_array(value) for key, value in arrays.items()},
        "conditions": list(conditions),
        "generator_seeds": seeds,
        "target_transform": "max-normalize each profile then log1p(100*x)/log(101)",
        "truth_use": "generation and post-hoc scoring only; DONUT train and checkpoint selection receive observed profiles only",
        "detector_noise_records": noise_records,
    }
    return arrays, manifest


def make_texture_test(
    *,
    q: np.ndarray,
    eta: np.ndarray,
    test_indices: np.ndarray,
    structure: Structure,
    forward_cfg: dict[str, Any],
    seed: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Generate a held-out March-Dollase OOD test using existing CPU operators."""
    from xrd_robustness.simulator import SimulationGrid

    grid_cfg = forward_cfg["grid"]
    grid = SimulationGrid(
        two_theta_min=float(grid_cfg["two_theta_min"]),
        two_theta_max=float(grid_cfg["two_theta_max"]),
        step=float(grid_cfg["step"]),
        wavelength=float(grid_cfg["wavelength_angstrom"]),
    )
    parameter_cfg = forward_cfg["parameterization"]
    u0 = (2.0 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3.0
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    records: list[dict[str, Any]] = []
    profiles: list[np.ndarray] = []
    for index in np.asarray(test_indices, dtype=np.int64):
        u = u0 + float(q[index, 0]) * float(parameter_cfg["du_half_range"])
        v = v0 + float(q[index, 1]) * float(parameter_cfg["dv_half_range"])
        a = math.exp(u - v / 3.0)
        c = math.exp(u + 2.0 * v / 3.0)
        q_structure = structure.copy()
        q_structure.lattice = Lattice.tetragonal(a, c)
        table = ideal_peak_table(q_structure, grid)
        per_parent_rng = np.random.default_rng(int(seed + index))
        readout_sigma = float(per_parent_rng.uniform(0.5, 1.5))
        params = PhysicsParameters(
            delta_2theta_deg=float(eta[index, 0]),
            fwhm_deg=float(eta[index, 1]),
            background_to_peak_ratio=float(eta[index, 2]),
            noise_std_ratio=0.0,
            background_type="polynomial",
            severity_level=0,
            zero_shift_active=True,
            broadening_active=True,
            background_active=True,
            noise_active=True,
            background_order=2,
            background_variation=0.0,
            background_floor_fraction=0.10,
            noise_model="poisson_gaussian",
            noise_stage="before_normalization",
            poisson_count_scale=30000.0,
            electronic_noise_std_counts=readout_sigma,
            preferred_orientation_active=True,
            preferred_orientation_model="march_dollase",
            march_parameter=0.8,
            preferred_axis_policy="low_index_reflection",
            candidate_low_index_count=16,
            orientation_seed=int(seed + index),
            preferred_hkl=(0, 0, 1),
            preferred_orientation_apply_probability=1.0,
        )
        _, _, diagnostics = apply_preferred_orientation(table, params)
        # `simulate_from_peak_table` applies the same reflection-level factor;
        # use a per-parent seed so texture/noise realizations are reproducible.
        profile = simulate_from_peak_table(
            table.positions,
            table.intensities,
            params,
            rng_seed=int(seed + 100000 + index),
            grid=grid,
            normalize=True,
            return_diagnostics=False,
            reflection_table=table,
        )
        transformed = np.log1p(100.0 * np.asarray(profile, dtype=np.float64)) / math.log(101.0)
        profiles.append(transformed.astype(np.float32))
        records.append(
            {
                "global_index": int(index),
                "preferred_hkl": diagnostics["preferred_hkl"],
                "march_parameter": diagnostics["march_parameter"],
                "electronic_noise_std_counts": readout_sigma,
                "intensity_factor_min": diagnostics["intensity_factor_min"],
                "intensity_factor_max": diagnostics["intensity_factor_max"],
                "a_angstrom": a,
                "c_angstrom": c,
            }
        )
    return np.stack(profiles), records
