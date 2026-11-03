"""V11 worker sharding, bounded scheduling, and exact RNG resume contract.

These small CPU-only tests do not require the private 154975-record library or a GPU.
Full worker-vs-serial physical rendering requires the private V11 smoke data.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from v11_prefetch import enqueue_train_lookahead, iter_prefetched_batches, V11PairPrefetchPool

SOURCE = ROOT / "one_click_v11.py"
spec = importlib.util.spec_from_file_location("v11_oneclick_test", SOURCE)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class FakePool:
    def __init__(self, window):
        self.prefetch_batches = window
        self.pending = {}
        self.committed = []

    def submit(self, key, rows, *, epoch, global_step, profile):
        if len(self.pending) >= self.prefetch_batches:
            raise AssertionError("Unbounded prefetch")
        self.pending[key] = (
            tuple(row.material_id for row in rows), epoch, global_step, profile,
        )

    def get(self, key):
        values = self.pending.pop(key)
        self.committed.append((key, values))
        return values


def rows(n=17):
    return [SimpleNamespace(material_id=f"parent_{i:03d}", split="train", label=i % 7)
            for i in range(n)]


class V11PrefetchContractTests(unittest.TestCase):
    def test_bounded_validation_window_and_order(self):
        pool = FakePool(3)
        records = rows(23)
        seen = []
        for start, result in iter_prefetched_batches(
                pool, records, profile="ood_noise", batch_size=4):
            self.assertLessEqual(len(pool.pending), 3)
            self.assertEqual(start, pool.committed[-1][0])
            self.assertEqual(result[1:], (0, 0, "ood_noise"))
            seen.extend(result[0])
        self.assertEqual(seen, [r.material_id for r in records])
        self.assertEqual(pool.pending, {})

    def test_rng_committed_not_lookahead_and_resume_replays_same_parents(self):
        available = rows(59)
        seed = 20260711
        rng = np.random.default_rng(seed)
        pool = FakePool(3)
        after = {}
        next_submit = enqueue_train_lookahead(
            pool, rng, available, batch_size=8, start_step=0,
            next_submit=0, max_steps=10, committed_states=after,
        )
        self.assertEqual(next_submit, 3)
        first = pool.get(0)
        committed_state = after.pop(0)
        # The current RNG has already sampled future steps. It must NOT be saved.
        self.assertNotEqual(
            rng.bit_generator.state["state"]["state"],
            committed_state["state"]["state"],
        )
        second_prefetched = pool.pending[1][0]
        restored = np.random.default_rng(0)
        restored.bit_generator.state = committed_state
        restarted = FakePool(3)
        recovered_states = {}
        enqueue_train_lookahead(
            restarted, restored, available, batch_size=8,
            start_step=1, next_submit=1, max_steps=10,
            committed_states=recovered_states,
        )
        self.assertEqual(second_prefetched, restarted.pending[1][0])
        self.assertNotEqual(first[0], second_prefetched)
        self.assertEqual(pool.committed[0][1][3], "train")

    def test_invalid_resources_rejected_before_process_spawn(self):
        sim = {"simulator_version": "v11_tch_pseudo_voigt"}
        with self.assertRaises(ValueError):
            V11PairPrefetchPool(sim, run_seed=1, workers=0)
        with self.assertRaises(ValueError):
            V11PairPrefetchPool({"simulator_version":"v9_gaussian"},run_seed=1)

    def test_spawned_v11_workers_match_exact_serial_pair(self):
        # Synthetic V7 reflection table: no private CIF or GPU required.
        import json
        import tempfile
        from xrd_robustness.peak_cache import load_peak_table
        from xrd_robustness.training.runner import build_online_view_factory
        from xrd_robustness.physics import PhysicsParameterSampler
        config=json.loads((
            ROOT.parent/"xrd_robustness"/"configs"/
            "simulation.v11_tch_pseudo_voigt.json"
        ).read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            peak_path=Path(temp)/"synthetic_v7.npz"
            np.savez_compressed(
                peak_path,
                positions=np.array([20.,35.,50.]),
                intensities=np.array([100.,60.,30.]),
                hkls=np.array([[1,0,0],[1,1,0],[1,1,1]],dtype=np.int64),
                multiplicities=np.array([6,12,8],dtype=np.int64),
                reciprocal_vectors=np.array([
                    [0.10,0.,0.],[0.12,0.12,0.],[0.15,0.15,0.15],
                ],dtype=np.float64),
                reflection_peak_indices=np.array([0,1,2],dtype=np.int64),
            )
            record=SimpleNamespace(
                material_id="synthetic_v11_001",peak_table_path=peak_path,
                split="train",label=3,
            )
            fac,version,_=build_online_view_factory(
                PhysicsParameterSampler.from_mapping({**config,"run_seed":12345}),
                config,
            )
            self.assertEqual(version,"v11_tch_pseudo_voigt")
            serial=fac.make_pair_from_peaks(
                load_peak_table(peak_path),material_id=record.material_id,
                split="train",epoch=1,global_step=137,profile="train",
            )
            with V11PairPrefetchPool(
                config,run_seed=12345,workers=2,prefetch_batches=2,
                native_threads=1,max_cached_peaks=16,
            ) as pool:
                pool.submit(137,[record],epoch=1,global_step=137,profile="train")
                first,second,labels=pool.get(137)
            self.assertTrue(np.array_equal(first[0],serial.first.xrd))
            self.assertTrue(np.array_equal(second[0],serial.second.xrd))
            self.assertEqual(labels.tolist(),[3])

    def test_fp32_js_preserves_finite_gradients_on_extreme_logits(self):
        import torch
        from torch.nn import functional as F
        a = torch.tensor([[500., 0., -500.]], requires_grad=True, dtype=torch.bfloat16)
        b = torch.tensor([[0., 500., -500.]], requires_grad=True, dtype=torch.bfloat16)
        total, ce, js = runner.loss_js(a, b, torch.tensor([0]), 60.0, torch, F)
        self.assertTrue(bool(torch.isfinite(total)))
        self.assertEqual(total.dtype, torch.float32)
        total.backward()
        self.assertTrue(bool(torch.isfinite(a.grad).all()))
        self.assertTrue(bool(torch.isfinite(b.grad).all()))


if __name__ == "__main__":
    unittest.main()
