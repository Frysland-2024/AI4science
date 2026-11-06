#!/usr/bin/env python
"""Run the V11 acceptance checks against seven local CIF-converted structures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
from typing import Any

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parent
sys.path.insert(0, str(PACKAGE_ROOT / "src"))

from pymatgen.core import Structure
from pymatgen.io.cif import CifParser, CifWriter
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.physics import PhysicsParameterSampler, PhysicsParameters
from xrd_robustness.simulator import (
    SimulationGrid,
    ideal_peak_table,
    render_gaussian_peaks,
    simulate_from_peak_table,
)
from xrd_robustness.simulator_v11 import (
    SIMULATOR_VERSION,
    calculate_tch_width_components,
    make_peak_table_simulator,
    render_tch_pseudo_voigt_peaks,
    simulate_from_peak_table_v11,
)
from xrd_robustness.structure_data import CRYSTAL_SYSTEMS


REPRESENTATIVE_IDS = {
    "triclinic": "mp-1002571",
    "monoclinic": "mp-1001",
    "orthorhombic": "mp-1001603",
    "tetragonal": "mp-10004",
    "trigonal": "mp-1001604",
    "hexagonal": "mp-1001835",
    "cubic": "mp-1002109",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--records",
        type=Path,
        default=PACKAGE_ROOT / "data/formal_14060/mp_processed/structure_records.jsonl",
    )
    parser.add_argument(
        "--simulation-config",
        type=Path,
        default=PACKAGE_ROOT / "configs/simulation.v11_tch_pseudo_voigt.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PACKAGE_ROOT / "reports/simulator_v11/acceptance_20261103.json",
    )
    parser.add_argument("--repeats", type=int, default=3)
    return parser.parse_args()


def _read_representatives(path: Path) -> dict[str, dict[str, Any]]:
    wanted = set(REPRESENTATIVE_IDS.values())
    by_id: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["material_id"] in wanted:
                by_id[str(row["material_id"])] = row
                if len(by_id) == len(wanted):
                    break
    missing = wanted.difference(by_id)
    if missing:
        raise ValueError(f"missing representative structures: {sorted(missing)}")
    return by_id


def _cif_roundtrip(row: dict[str, Any]) -> tuple[Any, str, str]:
    source = Structure.from_dict(row["standardized_structure"])
    cif_text = str(CifWriter(source))
    parsed = CifParser.from_str(cif_text).parse_structures(primitive=False)
    if len(parsed) != 1:
        raise AssertionError(f"expected one structure from CIF for {row['material_id']}")
    structure = parsed[0]
    observed = SpacegroupAnalyzer(structure, symprec=0.01).get_crystal_system()
    expected = str(row["crystal_system"])
    if observed != expected:
        raise AssertionError(
            f"crystal-system label changed through CIF for {row['material_id']}: "
            f"{expected} -> {observed}"
        )
    return structure, cif_text, observed


def _width_trends() -> dict[str, Any]:
    fixed = {
        "kind": "tch_pseudo_voigt_v1",
        "wavelength_angstrom": 1.54184,
        "scherrer_shape_factor": 0.9,
        "caglioti_u_deg2": 0.0012,
        "caglioti_v_deg2": 0.0004,
        "crystallite_size_nm": {"distribution": "fixed", "min_value": 100, "max_value": 100},
        "microstrain": {"distribution": "fixed", "min_value": 0.0001, "max_value": 0.0001},
        "use_scherrer": True,
        "use_microstrain": True,
        "truncate_fwhm": 50.0,
    }
    low_angle = calculate_tch_width_components(
        20.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=100.0,
        microstrain=0.0001,
    )
    high_angle = calculate_tch_width_components(
        70.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=100.0,
        microstrain=0.0001,
    )
    small_crystallite = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=50.0,
        microstrain=0.0001,
    )
    large_crystallite = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=200.0,
        microstrain=0.0001,
    )
    high_strain = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=100.0,
        microstrain=0.0002,
    )
    low_strain = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=100.0,
        microstrain=0.00005,
    )
    if not high_angle["total_fwhm_deg"] > low_angle["total_fwhm_deg"]:
        raise AssertionError("angle-dependent instrumental/specimen broadening failed")
    if not small_crystallite["scherrer_fwhm_deg"] > large_crystallite["scherrer_fwhm_deg"]:
        raise AssertionError("Scherrer width did not increase as crystal size fell")
    if not high_strain["microstrain_fwhm_deg"] > low_strain["microstrain_fwhm_deg"]:
        raise AssertionError("microstrain width did not increase with strain")

    grid = SimulationGrid().values
    one_peak = render_tch_pseudo_voigt_peaks(
        [40.0],
        [2.5],
        grid,
        0.08,
        line_profile=fixed,
        crystallite_size_nm=100.0,
        microstrain=0.0001,
        normalize=False,
    )
    recovered_area = float(one_peak.sum(dtype=np.float64) * (grid[1] - grid[0]))
    if not np.isclose(recovered_area, 2.5, rtol=2e-3, atol=2e-3):
        raise AssertionError(f"area normalization failed: expected 2.5, got {recovered_area}")

    center = np.asarray([40.0])
    instrument_only = {**fixed, "use_scherrer": False, "use_microstrain": False}
    base = calculate_tch_width_components(
        40.0,
        0.08,
        line_profile=instrument_only,
        crystallite_size_nm=100.0,
        microstrain=0.0,
    )["total_fwhm_deg"]
    narrow = render_tch_pseudo_voigt_peaks(
        center, [1.0], grid, 0.08, line_profile=instrument_only,
        crystallite_size_nm=100.0, microstrain=0.0, normalize=False,
    )
    above_half = np.flatnonzero(narrow >= float(narrow.max()) / 2.0)
    observed_center = float(grid[int(narrow.argmax())])
    observed_fwhm = float(grid[above_half[-1]] - grid[above_half[0]] + (grid[1] - grid[0]))
    if abs(observed_center - center[0]) > float(grid[1] - grid[0]):
        raise AssertionError("rendered peak position drifted by more than one grid bin")
    if abs(observed_fwhm - base) > 2.1 * float(grid[1] - grid[0]):
        raise AssertionError("rendered peak FWHM disagrees with the TCH width")

    return {
        "angle_trend_20_to_70deg": {
            "fwhm_20_deg": low_angle["total_fwhm_deg"],
            "fwhm_70_deg": high_angle["total_fwhm_deg"],
        },
        "scherrer_size_trend_50_to_200nm": {
            "fwhm_50nm_deg": small_crystallite["scherrer_fwhm_deg"],
            "fwhm_200nm_deg": large_crystallite["scherrer_fwhm_deg"],
        },
        "microstrain_trend_50_to_200ppm": {
            "fwhm_50ppm_deg": low_strain["microstrain_fwhm_deg"],
            "fwhm_200ppm_deg": high_strain["microstrain_fwhm_deg"],
        },
        "single_peak_integrated_area": recovered_area,
        "single_peak_position_deg": observed_center,
        "single_peak_width_observed_deg": observed_fwhm,
        "single_peak_width_expected_deg": base,
    }


def run() -> dict[str, Any]:
    args = _args()
    if args.repeats < 1:
        raise ValueError("--repeats must be at least one")
    rows = _read_representatives(args.records.resolve())
    config_bytes = args.simulation_config.resolve().read_bytes()
    config = json.loads(config_bytes)
    if config.get("simulator_version") != SIMULATOR_VERSION:
        raise ValueError("acceptance config does not select the V11 simulator")
    sampler = PhysicsParameterSampler.from_mapping(config)
    if "train" not in sampler.profiles:
        raise ValueError("acceptance config lacks the train physics profile")
    grid = SimulationGrid()
    v11 = make_peak_table_simulator(SIMULATOR_VERSION, config.get("line_profile", {}))
    materials: list[dict[str, Any]] = []
    cached_peaks: dict[str, Any] = {}
    v9_factory = OnlineViewFactory(sampler)
    v11_factory = OnlineViewFactory(sampler, peak_table_simulator=v11)
    for system in CRYSTAL_SYSTEMS:
        material_id = REPRESENTATIVE_IDS[system]
        row = rows[material_id]
        structure, cif_text, observed_system = _cif_roundtrip(row)
        peaks = ideal_peak_table(structure, grid)
        cached_peaks[material_id] = peaks
        parent_seed = 20261103
        v9_spectrum, v9_diagnostics = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            PhysicsParameters(
                delta_2theta_deg=0.0,
                fwhm_deg=0.08,
                background_to_peak_ratio=0.0,
                noise_std_ratio=0.0,
                background_type="flat",
                severity_level=0,
                background_active=False,
                noise_active=False,
            ),
            rng_seed=parent_seed,
            grid=grid,
            return_diagnostics=True,
            reflection_table=peaks,
        )
        v11_spectrum, v11_diagnostics = simulate_from_peak_table_v11(
            peaks.positions,
            peaks.intensities,
            PhysicsParameters(
                delta_2theta_deg=0.0,
                fwhm_deg=0.08,
                background_to_peak_ratio=0.0,
                noise_std_ratio=0.0,
                background_type="flat",
                severity_level=0,
                background_active=False,
                noise_active=False,
            ),
            rng_seed=parent_seed,
            grid=grid,
            return_diagnostics=True,
            reflection_table=peaks,
            line_profile=config.get("line_profile", {}),
        )
        pair_args = {
            "material_id": material_id,
            "split": "train",
            "epoch": 2,
            "global_step": 19,
            "profile": "train",
        }
        pair = v11_factory.make_pair_from_peaks(peaks, **pair_args)
        replay = v11_factory.make_pair_from_peaks(peaks, **pair_args)
        if not np.array_equal(pair.first.xrd, replay.first.xrd):
            raise AssertionError(f"fixed-seed replay failed for {material_id} view 1")
        if not np.array_equal(pair.second.xrd, replay.second.xrd):
            raise AssertionError(f"fixed-seed replay failed for {material_id} view 2")
        if np.array_equal(pair.first.xrd, pair.second.xrd):
            raise AssertionError(f"dynamic view pair was not distinct for {material_id}")
        if pair.first.metadata["structure_id"] != pair.second.metadata["structure_id"]:
            raise AssertionError(f"view pair changed parent structure for {material_id}")
        if pair.first.metadata["view_id"] == pair.second.metadata["view_id"]:
            raise AssertionError(f"view pair repeated the same view ID for {material_id}")
        for name, signal in (
            ("v9", v9_spectrum),
            ("v11", v11_spectrum),
            ("pair_1", pair.first.xrd),
            ("pair_2", pair.second.xrd),
        ):
            if signal.shape != (3501,) or not np.isfinite(signal).all():
                raise AssertionError(f"invalid {name} spectrum for {material_id}")
        materials.append(
            {
                "material_id": material_id,
                "crystal_system_label": observed_system,
                "source_record_label": row["crystal_system"],
                "cif_sha256": hashlib.sha256(cif_text.encode("utf-8")).hexdigest(),
                "cif_bytes": len(cif_text.encode("utf-8")),
                "peak_count": int(len(peaks.positions)),
                "v9_legacy_spectrum_finite": True,
                "v11_spectrum_finite": True,
                "pair_same_parent_same_label": True,
                "pair_views_distinct": True,
                "pair_seed_replay_exact": True,
                "pair_view_seeds": [pair.first.rng_seed, pair.second.rng_seed],
                "v9_mean": float(v9_spectrum.mean()),
                "v11_mean": float(v11_spectrum.mean()),
                "v9_noise_model": v9_diagnostics["noise_model"],
                "v11_line_profile": v11_diagnostics["line_profile"],
            }
        )

    timing_by_system: dict[str, dict[str, list[float]]] = {
        system: {"v9_gaussian": [], SIMULATOR_VERSION: []}
        for system in CRYSTAL_SYSTEMS
    }
    for repeat in range(args.repeats + 1):
        for system in CRYSTAL_SYSTEMS:
            material_id = REPRESENTATIVE_IDS[system]
            peaks = cached_peaks[material_id]
            common = {
                "material_id": material_id,
                "split": "train",
                "epoch": 3,
                "global_step": 100 + repeat,
                "profile": "train",
            }
            if repeat == 0:
                v9_factory.make_pair_from_peaks(peaks, **common)
                v11_factory.make_pair_from_peaks(peaks, **common)
                continue
            start = perf_counter()
            v9_factory.make_pair_from_peaks(peaks, **common)
            timing_by_system[system]["v9_gaussian"].append(perf_counter() - start)
            start = perf_counter()
            v11_factory.make_pair_from_peaks(peaks, **common)
            timing_by_system[system][SIMULATOR_VERSION].append(perf_counter() - start)
    per_system_means = {
        system: {
            version: float(np.mean(values))
            for version, values in measurements.items()
        }
        for system, measurements in timing_by_system.items()
    }
    means = {
        version: float(
            np.mean(
                [
                    elapsed
                    for measurements in timing_by_system.values()
                    for elapsed in measurements[version]
                ]
            )
        )
        for version in ("v9_gaussian", SIMULATOR_VERSION)
    }
    speed_ratio = means[SIMULATOR_VERSION] / means["v9_gaussian"]

    grid_values = grid.values
    old_first = simulate_from_peak_table(
        cached_peaks[REPRESENTATIVE_IDS["cubic"]].positions,
        cached_peaks[REPRESENTATIVE_IDS["cubic"]].intensities,
        PhysicsParameters(
            delta_2theta_deg=0.0,
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=0,
            background_active=False,
            noise_active=False,
        ),
        rng_seed=20261103,
        grid=grid,
        reflection_table=cached_peaks[REPRESENTATIVE_IDS["cubic"]],
    )
    old_first_explicit = simulate_from_peak_table(
        cached_peaks[REPRESENTATIVE_IDS["cubic"]].positions,
        cached_peaks[REPRESENTATIVE_IDS["cubic"]].intensities,
        PhysicsParameters(
            delta_2theta_deg=0.0,
            fwhm_deg=0.08,
            background_to_peak_ratio=0.0,
            noise_std_ratio=0.0,
            background_type="flat",
            severity_level=0,
            background_active=False,
            noise_active=False,
        ),
        rng_seed=20261103,
        grid=grid,
        reflection_table=cached_peaks[REPRESENTATIVE_IDS["cubic"]],
        peak_renderer=render_gaussian_peaks,
    )
    if not np.array_equal(
        simulate_from_peak_table(
            cached_peaks[REPRESENTATIVE_IDS["cubic"]].positions,
            cached_peaks[REPRESENTATIVE_IDS["cubic"]].intensities,
            PhysicsParameters(
                delta_2theta_deg=0.0,
                fwhm_deg=0.08,
                background_to_peak_ratio=0.0,
                noise_std_ratio=0.0,
                background_type="flat",
                severity_level=0,
                background_active=False,
                noise_active=False,
            ),
            rng_seed=20261103,
            grid=grid,
            reflection_table=cached_peaks[REPRESENTATIVE_IDS["cubic"]],
        ),
        old_first,
    ):
        raise AssertionError("V9 deterministic legacy regression changed")
    if not np.array_equal(old_first, old_first_explicit):
        raise AssertionError("V9 default no longer selects its historical Gaussian renderer")

    result = {
        "schema_version": "simulator-v11-acceptance-v1",
        "simulator_version": SIMULATOR_VERSION,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "source_records_sha256": _sha256_file(args.records.resolve()),
        "grid": {
            "two_theta_min_deg": grid.two_theta_min,
            "two_theta_max_deg": grid.two_theta_max,
            "step_deg": grid.step,
            "point_count": int(len(grid_values)),
        },
        "actual_cif_materials": materials,
        "all_seven_crystal_system_labels_preserved": len(materials) == len(CRYSTAL_SYSTEMS)
        and {row["crystal_system_label"] for row in materials} == set(CRYSTAL_SYSTEMS),
        "physical_checks": _width_trends(),
        "legacy_v9_renderer_unchanged": True,
        "integration": {
            "online_views_pair_path": "OnlineViewFactory.make_pair_from_peaks",
            "training_runner_config_switch": "simulator_version=v11_tch_pseudo_voigt",
            "same_cached_peak_table_used_for_both_views": True,
            "model_input_shape": [int(len(grid_values))],
        },
        "speed": {
            "scope": "seven cached CIF-derived PeakTables, train profile, two views per pair",
            "repeats": args.repeats,
            "mean_pair_seconds_across_seven_systems": means,
            "per_crystal_system_mean_pair_seconds": per_system_means,
            "v11_over_v9_runtime_ratio": speed_ratio,
        },
        "output_arrays_bytes_per_pair_float32": int(3 * len(grid_values) * np.dtype(np.float32).itemsize),
        "materials_count": len(materials),
    }
    args.output = args.output.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
