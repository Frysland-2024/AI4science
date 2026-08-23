import unittest
from unittest.mock import patch
import csv
import hashlib
import tempfile
from pathlib import Path

import numpy as np

from xrd_robustness.peak_cache import (
    PeakTableCache,
    load_peak_table,
    validate_peak_cache_manifest,
)
from xrd_robustness.simulator import SimulationGrid


class PeakCacheTests(unittest.TestCase):
    def test_cache_stores_peak_tables_and_is_bounded(self):
        cache = PeakTableCache(max_items=1)
        with patch(
            "xrd_robustness.peak_cache.ideal_peak_list",
            return_value=(np.asarray([20.0]), np.asarray([100.0])),
        ) as compute:
            first = cache.get_or_compute("mp-1", object(), SimulationGrid())
            second = cache.get_or_compute("mp-1", object(), SimulationGrid())
            self.assertIs(first, second)
            self.assertEqual(compute.call_count, 1)
            cache.get_or_compute("mp-2", object(), SimulationGrid())
            self.assertEqual(len(cache), 1)

    def test_v7_npz_round_trip_requires_complete_reflection_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.npz"
            np.savez_compressed(
                path,
                positions=np.asarray([20.0, 30.0]),
                intensities=np.asarray([100.0, 50.0]),
                hkls=np.asarray([[1, 0, 0], [0, 1, 0]]),
                multiplicities=np.asarray([2, 2]),
                reciprocal_vectors=np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
                reflection_peak_indices=np.asarray([0, 1]),
            )
            table = load_peak_table(path)
            self.assertTrue(table.has_reflection_metadata)
            np.testing.assert_array_equal(table.hkls, [[1, 0, 0], [0, 1, 0]])

    def test_incomplete_v7_npz_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "table.npz"
            np.savez_compressed(
                path,
                positions=np.asarray([20.0]),
                intensities=np.asarray([100.0]),
                hkls=np.asarray([[1, 0, 0]]),
            )
            with self.assertRaisesRegex(ValueError, "incomplete V7 reflection metadata"):
                load_peak_table(path)

    def test_manifest_gate_binds_fingerprint_size_and_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            data_root = Path(directory)
            cache_dir = data_root / "mp_processed" / "peak_tables_v7_reflection"
            manifest_dir = data_root / "manifests"
            cache_dir.mkdir(parents=True)
            manifest_dir.mkdir()
            cache_path = cache_dir / "mp-1.npz"
            np.savez_compressed(
                cache_path,
                positions=np.asarray([20.0]),
                intensities=np.asarray([100.0]),
                hkls=np.asarray([[1, 0, 0]]),
                multiplicities=np.asarray([2]),
                reciprocal_vectors=np.asarray([[1.0, 0.0, 0.0]]),
                reflection_peak_indices=np.asarray([0]),
            )
            digest = hashlib.sha256(cache_path.read_bytes()).hexdigest()
            manifest_path = manifest_dir / "peak_cache_manifest.v7.reflection.csv"
            with manifest_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "material_id",
                        "structure_fingerprint",
                        "file",
                        "sha256",
                        "bytes",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "material_id": "mp-1",
                        "structure_fingerprint": "fp-1",
                        "file": "data/example/mp_processed/peak_tables_v7_reflection/mp-1.npz",
                        "sha256": digest,
                        "bytes": cache_path.stat().st_size,
                    }
                )
            report = validate_peak_cache_manifest(
                data_root,
                "peak_tables_v7_reflection",
                {"mp-1": {"structure_fingerprint": "fp-1"}},
                require_exact_ids=True,
                verify_file_hashes=True,
            )
            self.assertEqual(report["verified_file_hashes"], 1)
            with cache_path.open("ab") as handle:
                handle.write(b"corrupt")
            with self.assertRaisesRegex(ValueError, "byte count mismatch"):
                validate_peak_cache_manifest(
                    data_root,
                    "peak_tables_v7_reflection",
                    {"mp-1": {"structure_fingerprint": "fp-1"}},
                )


if __name__ == "__main__":
    unittest.main()
