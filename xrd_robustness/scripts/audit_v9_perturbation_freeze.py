#!/usr/bin/env python3
"""Audit the frozen V9 method-transfer perturbation ranges without training."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.physics import (
    PhysicsParameterSampler,
    PhysicsParameters,
    validate_formal_simulation_config,
)
from xrd_robustness.preferred_orientation import resolve_preferred_orientation
from xrd_robustness.simulation_quality import inspect_perturbed_view
from xrd_robustness.simulator import SimulationGrid, simulate_from_peak_table


PROFILES = (
    "train",
    "in_range",
    "ood_shift_negative",
    "ood_shift_positive",
    "ood_broadening",
    "ood_noise",
    "ood_background",
    "ood_texture",
    "ood_combo_shift_broadening",
    "ood_combo_background_noise",
    "ood_combo_texture_shift",
    "ood_all",
)
NUMERIC_FIELDS = (
    "delta_2theta_deg",
    "fwhm_deg",
    "background_to_peak_ratio",
    "background_variation",
    "poisson_count_scale",
    "electronic_noise_std_counts",
    "march_parameter",
    "active_perturbation_count",
)
ACTIVITY_FIELDS = (
    "zero_shift_active",
    "broadening_active",
    "background_active",
    "noise_active",
    "preferred_orientation_active",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "configs" / "simulation.v9.method_transfer.frozen.json"),
    )
    parser.add_argument(
        "--data-root",
        default=str(PROJECT_ROOT / "data" / "dev_3500"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "v9_method_transfer_perturbation_freeze.json"),
    )
    parser.add_argument("--views-per-material", type=int, default=2)
    parser.add_argument("--quality-structures-per-system", type=int, default=3)
    return parser.parse_args()


def _load_records(data_root: Path) -> list[dict[str, Any]]:
    path = data_root / "mp_processed" / "structure_records.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _distribution_audit(
    config: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    views_per_material: int,
) -> tuple[dict[str, Any], list[str]]:
    sampler = PhysicsParameterSampler.from_mapping(config)
    values: dict[str, dict[str, list[float]]] = {
        profile: {field: [] for field in NUMERIC_FIELDS} for profile in PROFILES
    }
    activity: dict[str, Counter[str]] = {profile: Counter() for profile in PROFILES}
    violations: list[str] = []

    for record_index, record in enumerate(records):
        material_id = str(record["material_id"])
        for profile in PROFILES:
            for view_id in range(1, views_per_material + 1):
                parameters, _ = sampler.sample(
                    profile,
                    epoch=0,
                    global_step=record_index,
                    material_id=material_id,
                    view_id=view_id,
                )
                payload = parameters.to_dict()
                for field in NUMERIC_FIELDS:
                    number = float(payload[field])
                    if not np.isfinite(number):
                        violations.append(f"{profile}/{material_id}/{view_id}/{field}:non_finite")
                    values[profile][field].append(number)
                for field in ACTIVITY_FIELDS:
                    activity[profile][field] += int(bool(payload[field]))

    summary: dict[str, Any] = {}
    expected_n = len(records) * views_per_material
    for profile in PROFILES:
        fields: dict[str, Any] = {}
        for field, raw_values in values[profile].items():
            array = np.asarray(raw_values, dtype=np.float64)
            fields[field] = {
                "min": float(np.min(array)),
                "q05": float(np.quantile(array, 0.05)),
                "median": float(np.median(array)),
                "q95": float(np.quantile(array, 0.95)),
                "max": float(np.max(array)),
            }
        summary[profile] = {
            "sample_count": expected_n,
            "numeric": fields,
            "activation_rate": {
                field: float(activity[profile][field] / expected_n)
                for field in ACTIVITY_FIELDS
            },
        }
    return summary, violations


def _quality_audit(
    config: dict[str, Any],
    data_root: Path,
    records: list[dict[str, Any]],
    *,
    views_per_material: int,
    structures_per_system: int,
) -> tuple[dict[str, Any], int]:
    by_system: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_system[str(record["crystal_system"])].append(record)
    selected = [
        record
        for system in sorted(by_system)
        for record in sorted(by_system[system], key=lambda row: str(row["material_id"]))[
            :structures_per_system
        ]
    ]
    sampler = PhysicsParameterSampler.from_mapping(config)
    grid = SimulationGrid()
    gates = config["quality_gates"]
    aggregates: dict[str, dict[str, Any]] = {
        profile: {
            "checked": 0,
            "rejected": 0,
            "min_top20_peak_recall": 1.0,
            "min_window_intensity_retained": float("inf"),
            "max_clipped_fraction": 0.0,
            "reasons": Counter(),
        }
        for profile in PROFILES
    }

    cache_root = data_root / "mp_processed" / "peak_tables_v7_reflection"
    base_parameters = PhysicsParameters(0.0, 0.08, 0.0, 0.0, "flat", 0)
    for record_index, record in enumerate(selected):
        material_id = str(record["material_id"])
        peaks = load_peak_table(cache_root / f"{material_id}.npz")
        base = simulate_from_peak_table(
            peaks.positions,
            peaks.intensities,
            base_parameters,
            rng_seed=1,
            grid=grid,
            normalize=False,
            reflection_table=peaks,
        )
        for profile in PROFILES:
            for view_id in range(1, views_per_material + 1):
                parameters, seed = sampler.sample(
                    profile,
                    epoch=0,
                    global_step=record_index,
                    material_id=material_id,
                    view_id=view_id,
                )
                parameters = resolve_preferred_orientation(peaks, parameters)
                perturbed, diagnostics = simulate_from_peak_table(
                    peaks.positions,
                    peaks.intensities,
                    parameters,
                    rng_seed=seed,
                    grid=grid,
                    normalize=False,
                    return_diagnostics=True,
                    reflection_table=peaks,
                )
                quality = inspect_perturbed_view(
                    base,
                    perturbed,
                    peak_positions=peaks.positions,
                    peak_intensities=peaks.intensities,
                    grid=grid.values,
                    parameters=parameters,
                    recall_threshold=float(gates["top20_peak_recall_min"]),
                    retained_threshold=float(gates["retained_integrated_intensity_min"]),
                    clipping_fraction_max=float(gates["clipped_fraction_max"]),
                    simulation_diagnostics=diagnostics,
                )
                aggregate = aggregates[profile]
                aggregate["checked"] += 1
                aggregate["rejected"] += int(not quality["passed"])
                aggregate["min_top20_peak_recall"] = min(
                    aggregate["min_top20_peak_recall"], quality["top20_peak_recall"]
                )
                aggregate["min_window_intensity_retained"] = min(
                    aggregate["min_window_intensity_retained"],
                    quality["window_intensity_retained"],
                )
                aggregate["max_clipped_fraction"] = max(
                    aggregate["max_clipped_fraction"], quality["clipped_fraction"]
                )
                aggregate["reasons"].update(quality["reasons"])

    for aggregate in aggregates.values():
        aggregate["reasons"] = dict(aggregate["reasons"])
    return aggregates, len(selected)


def main() -> int:
    args = _parse_args()
    config_path = Path(args.config).resolve()
    data_root = Path(args.data_root).resolve()
    output_path = Path(args.output).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("status") != "formal_frozen":
        raise SystemExit("freeze audit requires a simulation config with status=formal_frozen")
    if args.views_per_material <= 0 or args.quality_structures_per_system <= 0:
        raise SystemExit("audit sample counts must be positive")

    validate_formal_simulation_config(
        config,
        train_profile="train",
        in_range_profile="in_range",
        ood_profiles=list(PROFILES[2:]),
    )
    records = _load_records(data_root)
    systems = Counter(str(record["crystal_system"]) for record in records)
    distribution, violations = _distribution_audit(
        config,
        records,
        views_per_material=args.views_per_material,
    )
    quality, selected_count = _quality_audit(
        config,
        data_root,
        records,
        views_per_material=args.views_per_material,
        structures_per_system=args.quality_structures_per_system,
    )

    train_matches_in_range = config["profiles"]["train"] == config["profiles"]["in_range"]
    training_quality_passed = all(
        quality[profile]["rejected"] == 0 for profile in ("train", "in_range")
    )
    balanced_dev_set = len(records) == 3500 and set(systems.values()) == {500}
    passed = (
        not violations
        and train_matches_in_range
        and training_quality_passed
        and balanced_dev_set
        and config["real_experiment_policy"]["parameter_definition_source"] is False
    )
    report = {
        "schema_version": "v9.0-method-transfer-perturbation-freeze-audit",
        "status": "passed" if passed else "failed",
        "config": {
            "path": str(config_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "sha256": _sha256(config_path),
            "scientific_range_status": config["status"],
            "run_seed": config["run_seed"],
        },
        "freeze_decision": {
            "selected_ranges": config["profiles"],
            "parameter_source_hierarchy": config["methodology_policy"][
                "parameter_source_hierarchy"
            ],
            "real_xrd_used": False,
            "training_executed": False,
            "ood_quality_failures_are_reported_as_stress_diagnostics_not_training_rejections": True,
        },
        "dev_3500": {
            "record_count": len(records),
            "per_crystal_system": dict(sorted(systems.items())),
            "balanced": balanced_dev_set,
            "views_per_material_per_profile": args.views_per_material,
        },
        "distribution_audit": distribution,
        "spectrum_quality_audit": {
            "structures": selected_count,
            "selection": f"{args.quality_structures_per_system} deterministic material IDs per crystal system",
            "profiles": quality,
        },
        "acceptance": {
            "config_is_formal_frozen": True,
            "train_profile_equals_in_range_profile": train_matches_in_range,
            "sample_violations": violations,
            "train_and_in_range_quality_passed": training_quality_passed,
            "balanced_dev_3500": balanced_dev_set,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(_jsonable(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(output_path),
                "records": len(records),
                "quality_structures": selected_count,
            },
            sort_keys=True,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
