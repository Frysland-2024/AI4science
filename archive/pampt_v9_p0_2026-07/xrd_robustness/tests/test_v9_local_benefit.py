from __future__ import annotations

from pathlib import Path
import sys
import unittest

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_v9_local_benefit import (  # noqa: E402
    LOCAL_PER_CLASS,
    _gradient_relation,
    _paired_bootstrap_ci,
    _split_local_pool,
)


class V9LocalBenefitUtilityTest(unittest.TestCase):
    def test_gradient_relation_recovers_parallel_and_opposite_directions(self) -> None:
        first = {
            "encoder.a": torch.tensor([1.0, 2.0]),
            "encoder.b": torch.tensor([-1.0]),
        }
        parallel = {
            "encoder.a": torch.tensor([2.0, 4.0]),
            "encoder.b": torch.tensor([-2.0]),
        }
        opposite = {
            "encoder.a": torch.tensor([-2.0, -4.0]),
            "encoder.b": torch.tensor([2.0]),
        }
        self.assertAlmostEqual(_gradient_relation(first, parallel)["cosine"], 1.0)
        self.assertAlmostEqual(_gradient_relation(first, opposite)["cosine"], -1.0)

    def test_local_pool_split_is_balanced_and_disjoint(self) -> None:
        labels = {}
        scale_ids = []
        for label in range(7):
            for index in range(2 * LOCAL_PER_CLASS):
                material_id = f"class-{label}-{index:03d}"
                labels[material_id] = label
                scale_ids.append(material_id)
        pools = _split_local_pool(scale_ids, labels)
        self.assertEqual(len(pools["local_update"]), 7 * LOCAL_PER_CLASS)
        self.assertEqual(len(pools["local_eval"]), 7 * LOCAL_PER_CLASS)
        self.assertFalse(set(pools["local_update"]) & set(pools["local_eval"]))
        for pool in pools.values():
            counts = {label: 0 for label in range(7)}
            for material_id in pool:
                counts[labels[material_id]] += 1
            self.assertEqual(set(counts.values()), {LOCAL_PER_CLASS})

    def test_bootstrap_interval_is_deterministic_and_positive(self) -> None:
        first = _paired_bootstrap_ci([0.1, 0.2, 0.3, 0.4], draws=500, seed=7)
        second = _paired_bootstrap_ci([0.1, 0.2, 0.3, 0.4], draws=500, seed=7)
        self.assertEqual(first, second)
        self.assertGreater(first["lower_95"], 0.0)
        self.assertLessEqual(first["lower_95"], first["mean"])
        self.assertGreaterEqual(first["upper_95"], first["mean"])


if __name__ == "__main__":
    unittest.main()
