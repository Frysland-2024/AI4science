from pathlib import Path
import tempfile
import unittest

import numpy as np

from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.perturbation_strategy import IndependentDynamicStrategy
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training_prefetch import (
    DynamicBatchPrefetcher,
    FixedBatchPrefetcher,
    deterministic_worker_shard,
    render_dynamic_batch,
    render_fixed_batch,
)
from xrd_robustness.view_manifest import build_offline_view_manifest, build_parameter_batch


def _fixed(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _sampler_config(seed=17):
    return {
        "run_seed": seed,
        "profiles": {
            "train": {
                "severity_level": 1,
                "background_type": "flat",
                "delta_2theta_deg": _fixed(0.01),
                "fwhm_deg": _fixed(0.08),
                "background_to_peak_ratio": _fixed(0.01),
                "noise_std_ratio": _fixed(0.01),
            }
        },
    }


class DynamicTrainingPrefetchTests(unittest.TestCase):
    def test_worker_sharding_is_stable_and_bounded(self):
        material_ids = [f"mp-{index}" for index in range(100)]
        first = [deterministic_worker_shard(value, 4) for value in material_ids]
        replay = [deterministic_worker_shard(value, 4) for value in material_ids]
        self.assertEqual(first, replay)
        self.assertTrue(set(first).issubset({0, 1, 2, 3}))
        self.assertGreater(len(set(first)), 1)
        with self.assertRaisesRegex(ValueError, "positive"):
            deterministic_worker_shard("mp-1", 0)

    def test_spawn_prefetch_matches_sequential_rendering_exactly(self):
        config = _sampler_config()
        sampler = PhysicsParameterSampler.from_mapping(config)
        strategy = IndependentDynamicStrategy(sampler, config_hash="test-config")
        factory = OnlineViewFactory(
            sampler,
            quality_gate=False,
            strategy=strategy,
        )
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            cache_root = data_root / "mp_processed" / "test-cache"
            cache_root.mkdir(parents=True)
            material_ids = ("mp-a", "mp-b", "mp-c", "mp-d")
            peaks = {}
            for index, material_id in enumerate(material_ids):
                path = cache_root / f"{material_id}.npz"
                np.savez(
                    path,
                    positions=np.array([20.0 + index, 40.0 + index]),
                    intensities=np.array([1.0, 0.5]),
                )
                from xrd_robustness.peak_cache import load_peak_table

                peaks[material_id] = load_peak_table(path)

            first_ids = material_ids[:3]
            second_ids = tuple(reversed(material_ids[1:]))
            first_rows = build_parameter_batch(
                first_ids,
                sampler,
                profile="train",
                epoch=2,
                global_step=5,
            )
            second_rows = build_parameter_batch(
                second_ids,
                sampler,
                profile="train",
                epoch=2,
                global_step=6,
            )
            expected_first = render_dynamic_batch(
                25,
                first_ids,
                first_rows,
                peaks=peaks,
                factory=factory,
                sampler=sampler,
                profile="train",
            )
            expected_second = render_dynamic_batch(
                26,
                second_ids,
                second_rows,
                peaks=peaks,
                factory=factory,
                sampler=sampler,
                profile="train",
            )
            prefetcher = DynamicBatchPrefetcher(
                worker_count=2,
                worker_native_threads=1,
                prefetch_batches=2,
                start_method="spawn",
                data_root=data_root,
                peak_cache_name="test-cache",
                sampler_config=config,
                quality_gate=False,
                quality_gate_config={},
                simulation_config_hash="test-config",
                profile="train",
            )
            try:
                prefetcher.submit(25, first_ids, first_rows)
                prefetcher.submit(26, second_ids, second_rows)
                observed_first = prefetcher.get(25)
                observed_second = prefetcher.get(26)
            finally:
                prefetcher.close()

            for expected, observed in (
                (expected_first, observed_first),
                (expected_second, observed_second),
            ):
                self.assertEqual(observed.material_ids, expected.material_ids)
                self.assertEqual(observed.accepted_rows, expected.accepted_rows)
                self.assertEqual(observed.parameters_first, expected.parameters_first)
                self.assertEqual(observed.parameters_second, expected.parameters_second)
                np.testing.assert_array_equal(observed.first, expected.first)
                np.testing.assert_array_equal(observed.second, expected.second)
                self.assertEqual(observed.quality_checked_count, 0)
                self.assertEqual(observed.quality_rejected_count, 0)

    def test_fixed_spawn_prefetch_matches_clean_and_offline_rendering_exactly(self):
        config = _sampler_config()
        sampler = PhysicsParameterSampler.from_mapping(config)
        strategy = IndependentDynamicStrategy(sampler, config_hash="test-config")
        factory = OnlineViewFactory(sampler, quality_gate=False, strategy=strategy)
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            cache_root = data_root / "mp_processed" / "test-cache"
            cache_root.mkdir(parents=True)
            material_ids = ("mp-a", "mp-b", "mp-c", "mp-d")
            peaks = {}
            for index, material_id in enumerate(material_ids):
                path = cache_root / f"{material_id}.npz"
                np.savez(
                    path,
                    positions=np.array([20.0 + index, 40.0 + index]),
                    intensities=np.array([1.0, 0.5]),
                )
                from xrd_robustness.peak_cache import load_peak_table

                peaks[material_id] = load_peak_table(path)

            rows = build_offline_view_manifest(
                material_ids,
                sampler,
                profile="train",
                views_per_material=2,
            )
            row_index = {(row.material_id, row.view_id): row for row in rows}
            clean_ids = material_ids[:3]
            offline_ids = tuple(reversed(material_ids[1:]))
            clean_first = tuple(row_index[(material_id, 1)] for material_id in clean_ids)
            offline_first = tuple(
                row_index[(material_id, 1)] for material_id in offline_ids
            )
            offline_second = tuple(
                row_index[(material_id, 2)] for material_id in offline_ids
            )
            expected_clean = render_fixed_batch(
                25,
                clean_ids,
                clean_first,
                None,
                peaks=peaks,
                factory=factory,
            )
            expected_offline = render_fixed_batch(
                26,
                offline_ids,
                offline_first,
                offline_second,
                peaks=peaks,
                factory=factory,
            )
            prefetcher = FixedBatchPrefetcher(
                worker_count=2,
                worker_native_threads=1,
                prefetch_batches=2,
                start_method="spawn",
                data_root=data_root,
                peak_cache_name="test-cache",
                sampler_config=config,
                quality_gate=False,
                quality_gate_config={},
                simulation_config_hash="test-config",
                profile="train",
            )
            try:
                prefetcher.submit(25, clean_ids, clean_first)
                prefetcher.submit(
                    26,
                    offline_ids,
                    offline_first,
                    offline_second,
                )
                observed_clean = prefetcher.get(25)
                observed_offline = prefetcher.get(26)
            finally:
                prefetcher.close()

            for expected, observed in (
                (expected_clean, observed_clean),
                (expected_offline, observed_offline),
            ):
                self.assertEqual(observed.material_ids, expected.material_ids)
                np.testing.assert_array_equal(observed.first, expected.first)
                if expected.second is None:
                    self.assertIsNone(observed.second)
                else:
                    np.testing.assert_array_equal(observed.second, expected.second)
                self.assertEqual(observed.quality_checked_count, 0)
                self.assertEqual(observed.quality_rejected_count, 0)


if __name__ == "__main__":
    unittest.main()
