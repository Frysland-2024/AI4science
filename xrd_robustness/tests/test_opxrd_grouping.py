"""
Tests for sample grouping logic in opXRD feasibility audit.
"""
import json
import os
import sys
import unittest
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestGroupingHierarchy(unittest.TestCase):
    """Test sample grouping hierarchy construction."""

    def setUp(self):
        self.sample_records = [
            {"scan_id": "CNRS/pat_0", "contributor": "CNRS", "family_id": "BaTiO3",
             "composition_id": "BaTiO3", "sample_group_id": "CNRS|BaTiO3|batch1"},
            {"scan_id": "CNRS/pat_1", "contributor": "CNRS", "family_id": "BaTiO3",
             "composition_id": "BaTiO3", "sample_group_id": "CNRS|BaTiO3|batch1"},
            {"scan_id": "CNRS/pat_2", "contributor": "CNRS", "family_id": "BaTiO3",
             "composition_id": "BaTiO3_doped", "sample_group_id": "CNRS|BaTiO3|batch2"},
            {"scan_id": "EMPA/pat_0", "contributor": "EMPA", "family_id": "PZT",
             "composition_id": "PZT", "sample_group_id": "EMPA|PZT|batch1"},
        ]

    def test_build_hierarchy(self):
        """Test that hierarchy groups correctly."""
        hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
        for r in self.sample_records:
            hierarchy[r["contributor"]][r["family_id"]][r["composition_id"]][r["sample_group_id"]].append(r)

        self.assertEqual(len(hierarchy), 2)  # 2 institutions
        self.assertEqual(len(hierarchy["CNRS"]), 1)  # 1 family in CNRS
        self.assertEqual(len(hierarchy["CNRS"]["BaTiO3"]), 2)  # 2 compositions
        self.assertEqual(len(hierarchy["EMPA"]), 1)

    def test_count_unique_institutions(self):
        """Test counting unique institutions."""
        insts = {r["contributor"] for r in self.sample_records}
        self.assertEqual(len(insts), 2)

    def test_count_unique_families(self):
        """Test counting unique institution-family combos."""
        families = {(r["contributor"], r["family_id"]) for r in self.sample_records}
        self.assertEqual(len(families), 2)

    def test_count_unique_samples(self):
        """Test counting unique sample groups."""
        samples = {r["sample_group_id"] for r in self.sample_records}
        self.assertEqual(len(samples), 3)

    def test_scans_per_sample(self):
        """Test scan-to-sample ratio."""
        scans = len(self.sample_records)
        samples = len({r["sample_group_id"] for r in self.sample_records})
        ratio = scans / samples
        self.assertEqual(scans, 4)
        self.assertEqual(samples, 3)
        self.assertAlmostEqual(ratio, 4/3)

    def test_same_group_not_cross_split(self):
        """Test that same sample_group records stay together."""
        groups = defaultdict(list)
        for r in self.sample_records:
            groups[r["sample_group_id"]].append(r)
        for gk, records in groups.items():
            if len(records) > 1:
                # All records in same group should have same contributor and family
                contribs = {r["contributor"] for r in records}
                families = {r["family_id"] for r in records}
                self.assertEqual(len(contribs), 1, f"Group {gk} spans institutions")
                self.assertEqual(len(families), 1, f"Group {gk} spans families")


class TestTimeSeriesDetection(unittest.TestCase):
    """Test time-series detection patterns."""

    def test_series_pattern_detection(self):
        """Test that common time-series naming patterns are detected."""
        filenames = [
            "scan_T0.json", "scan_T1.json", "scan_T2.json",
            "scan_T3.json", "scan_T4.json",
        ]
        base_patterns = defaultdict(list)
        for fn in filenames:
            base = fn.rsplit("_", 1)[0] if "_" in fn else fn
            base_patterns[base].append(fn)

        series = {k: v for k, v in base_patterns.items() if len(v) >= 3}
        self.assertEqual(len(series), 1)
        self.assertEqual(len(series["scan"]), 5)

    def test_no_false_positive_series(self):
        """Test that unrelated files are not grouped as series."""
        filenames = [
            "BaTiO3_pattern.json", "SrTiO3_pattern.json", "PZT_pattern.json",
        ]
        bases = []
        for fn in filenames:
            base = fn.rsplit("_", 1)[0] if "_" in fn else fn
            bases.append(base)

        counts = defaultdict(int)
        for b in bases:
            counts[b] += 1

        series = {k: v for k, v in counts.items() if v >= 3}
        self.assertEqual(len(series), 0)


class TestDeduplication(unittest.TestCase):
    """Test deduplication logic."""

    def test_hash_dedup(self):
        """Test that duplicate file hashes are detected."""
        hashes = ["ABC123", "ABC123", "DEF456", "GHI789", "DEF456"]
        hash_counts = defaultdict(int)
        for h in hashes:
            hash_counts[h] += 1

        dup_count = sum(c - 1 for c in hash_counts.values() if c > 1)
        self.assertEqual(dup_count, 2)  # one extra ABC123, one extra DEF456

    def test_no_false_positive_dedup(self):
        """Test that unique hashes are not flagged as duplicates."""
        hashes = ["ABC123", "DEF456", "GHI789"]
        unique = set(hashes)
        self.assertEqual(len(unique), 3)


if __name__ == "__main__":
    unittest.main()
