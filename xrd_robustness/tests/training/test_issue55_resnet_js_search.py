from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.peak_cache import load_peak_table
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.simulation_interfaces import PeakTable
from xrd_robustness.simulator_v11 import make_peak_table_simulator
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher
from xrd_robustness.view_manifest import build_parameter_batch
from xrd_robustness.experiment import config_hash

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_issue55_resnet_js_search.py"
SEARCH_CONFIG_PATH = PROJECT_ROOT / "configs" / "issue55_resnet_js_search.v1.json"
_SPEC = importlib.util.spec_from_file_location("issue55_search", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
issue55_search = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(issue55_search)


def _protocol() -> dict:
    return json.loads(SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))


def test_issue55_planned_work_stays_within_frozen_step_budget() -> None:
    protocol = _protocol()
    budget = issue55_search._planned_resource_budget(protocol)
    assert budget == {
        "trial_count": 11,
        "optimizer_steps_including_gradient_diagnostic": 209472,
        "parent_occurrences_including_gradient_diagnostic": 3351552,
        "generated_views_including_gradient_diagnostic": 6703104,
    }


def test_issue55_budget_rejects_a_candidate_plan_over_the_cap() -> None:
    protocol = copy.deepcopy(_protocol())
    protocol["runtime"]["max_trials_including_final"] = 10
    with pytest.raises(ValueError, match="trial_count cap"):
        issue55_search._planned_resource_budget(protocol)


def test_issue55_final_metrics_keep_seed_values_and_report_aggregate() -> None:
    profiles = ("ood", "in_range")
    results = []
    for seed, offset in ((11, 0.0), (22, 0.2)):
        metrics = {
            name: {"accuracy": 0.5 + offset, "macro_f1": 0.4 + offset, "ece": 0.1 + offset}
            for name in profiles
        }
        results.append(
            {
                "status": "completed",
                "training_seed": seed,
                "selected_validation_profile_metrics": metrics,
            }
        )
    aggregate = issue55_search._aggregate_final_validation(results)
    assert aggregate["completed_seed_count"] == 2
    assert aggregate["profiles"]["ood"]["macro_f1"]["mean"] == pytest.approx(0.5)
    assert aggregate["profiles"]["ood"]["macro_f1"]["sample_sd"] == pytest.approx(0.02**0.5)
    assert aggregate["profiles"]["ood"]["ece"]["per_seed"] == {"11": 0.1, "22": 0.30000000000000004}


def test_dynamic_prefetch_worker_uses_versioned_v11_renderer(tmp_path: Path) -> None:
    material_id = "mp-prefetch-v11"
    data_root = tmp_path
    cache_root = data_root / "mp_processed" / "peak_tables_v11_worker_test"
    cache_root.mkdir(parents=True)
    peak_table = PeakTable(
        positions=np.asarray([24.31, 35.07, 51.82], dtype=np.float64),
        intensities=np.asarray([1.0, 0.62, 0.31], dtype=np.float64),
        hkls=np.asarray([[1, 0, 0], [1, 1, 0], [2, 0, 0]], dtype=np.int64),
        multiplicities=np.asarray([6, 12, 6], dtype=np.int64),
        reciprocal_vectors=np.asarray(
            [[1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [2.0, 0.0, 0.0]],
            dtype=np.float64,
        ),
        reflection_peak_indices=np.arange(3, dtype=np.int64),
    )
    cache_path = cache_root / f"{material_id}.npz"
    np.savez_compressed(
        cache_path,
        positions=peak_table.positions,
        intensities=peak_table.intensities,
        hkls=peak_table.hkls,
        multiplicities=peak_table.multiplicities,
        reciprocal_vectors=peak_table.reciprocal_vectors,
        reflection_peak_indices=peak_table.reflection_peak_indices,
    )
    loaded_peak_table = load_peak_table(cache_path)
    sampler_config = {
        "run_seed": 721,
        "profiles": {
            "train": {
                "severity_level": 1,
                "background_type": "flat",
                "delta_2theta_deg": {
                    "distribution": "uniform",
                    "min_value": -0.15,
                    "max_value": 0.15,
                    "apply_probability": 1.0,
                },
                "fwhm_deg": {
                    "distribution": "uniform",
                    "min_value": 0.08,
                    "max_value": 0.12,
                    "apply_probability": 1.0,
                },
                "background_to_peak_ratio": {
                    "distribution": "fixed",
                    "min_value": 0.0,
                    "max_value": 0.0,
                    "apply_probability": 0.0,
                },
                "noise_std_ratio": {
                    "distribution": "fixed",
                    "min_value": 0.0,
                    "max_value": 0.0,
                    "apply_probability": 0.0,
                },
            }
        },
    }
    line_profile = {
        "kind": "tch_pseudo_voigt_v1",
        "wavelength_angstrom": 1.54184,
        "scherrer_shape_factor": 0.9,
        "caglioti_u_deg2": 0.0012,
        "caglioti_v_deg2": 0.0004,
        "crystallite_size_nm": {"distribution": "fixed", "min_value": 100.0, "max_value": 100.0},
        "microstrain": {"distribution": "fixed", "min_value": 0.0001, "max_value": 0.0001},
        "use_scherrer": True,
        "use_microstrain": True,
        "truncate_fwhm": 50.0,
    }
    sampler = PhysicsParameterSampler.from_mapping(sampler_config)
    sampler_config_hash = config_hash(sampler_config)
    parameter_rows = build_parameter_batch(
        [material_id],
        sampler,
        profile="train",
        epoch=0,
        global_step=7,
        split="train",
    )
    prefetcher = DynamicBatchPrefetcher(
        worker_count=1,
        worker_native_threads=1,
        prefetch_batches=1,
        start_method="spawn",
        data_root=data_root,
        peak_cache_name="peak_tables_v11_worker_test",
        sampler_config=sampler_config,
        quality_gate=False,
        quality_gate_config={},
        simulation_config_hash=sampler_config_hash,
        profile="train",
        simulator_version="v11_tch_pseudo_voigt",
        line_profile_config=line_profile,
    )
    try:
        prefetcher.submit(1, [material_id], parameter_rows)
        batch = prefetcher.get(1)
    finally:
        prefetcher.close()

    assert batch.material_ids == (material_id,)
    assert batch.first.shape == batch.second.shape == (1, 3501)
    assert not np.array_equal(batch.first[0], batch.second[0])
    v11_factory = OnlineViewFactory(
        sampler,
        peak_table_simulator=make_peak_table_simulator(
            "v11_tch_pseudo_voigt", line_profile
        ),
        strategy=IndependentDynamicStrategy(sampler, config_hash=sampler_config_hash),
    )
    replay = v11_factory.make_view_from_manifest(loaded_peak_table, batch.accepted_rows[0])
    np.testing.assert_array_equal(batch.first[0], replay.xrd)
