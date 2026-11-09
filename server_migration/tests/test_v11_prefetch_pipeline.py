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

    def test_cpu_interrupted_run_matches_uninterrupted_run(self):
        import torch

        self._assert_interrupted_run_matches_uninterrupted_run(torch.device("cpu"))

    def test_cuda_interrupted_run_matches_uninterrupted_run(self):
        import torch

        if not torch.cuda.is_available():
            self.skipTest("CUDA checkpoint parity requires an available GPU")
        self._assert_interrupted_run_matches_uninterrupted_run(torch.device("cuda"))

    def _assert_interrupted_run_matches_uninterrupted_run(self, device):
        import copy
        import tempfile
        import torch

        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.linear = torch.nn.Linear(3, 2)

            def forward(self, values):
                return self.linear(values)

        def make_run(seed):
            torch.manual_seed(seed)
            if device.type == "cuda":
                torch.cuda.manual_seed_all(seed)
            model = TinyModel().to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=0.003)
            rng = np.random.default_rng(20261109)
            return model, optimizer, rng, []

        def train(model, optimizer, rng, history, start, stop):
            for step in range(start + 1, stop + 1):
                parents = rng.integers(0, 41, size=5).tolist()
                inputs = torch.tensor(
                    [[parent / 41, (parent % 7) / 7, 1.0] for parent in parents],
                    dtype=torch.float32, device=device,
                )
                inputs = inputs + torch.rand_like(inputs) * 0.01
                targets = torch.tensor([parent % 2 for parent in parents],device=device)
                optimizer.zero_grad(set_to_none=True)
                loss = torch.nn.functional.cross_entropy(model(inputs), targets)
                loss.backward()
                optimizer.step()
                history.append({"step": step, "parents": parents,
                                "loss": float(loss.detach())})

        def assert_nested_equal(test, left, right):
            if torch.is_tensor(left):
                test.assertTrue(torch.equal(left.cpu(), right.cpu()))
            elif isinstance(left, dict):
                test.assertEqual(left.keys(), right.keys())
                for key in left:
                    assert_nested_equal(test, left[key], right[key])
            elif isinstance(left, (tuple, list)):
                test.assertEqual(len(left), len(right))
                for a, b in zip(left, right):
                    assert_nested_equal(test, a, b)
            else:
                test.assertEqual(left, right)

        total_steps = 9
        split_step = 4
        full_model, full_optimizer, full_rng, full_history = make_run(1234)
        train(full_model, full_optimizer, full_rng, full_history, 0, total_steps)
        full_torch_rng = torch.get_rng_state().clone()
        full_cuda_rngs = torch.cuda.get_rng_state_all() if device.type == "cuda" else []

        partial_model, partial_optimizer, partial_rng, partial_history = make_run(1234)
        train(partial_model, partial_optimizer, partial_rng, partial_history, 0, split_step)
        committed_rng = copy.deepcopy(partial_rng.bit_generator.state)
        checkpoint = {
            "step": split_step,
            "best": 0.625,
            "best_step": split_step,
            "history": partial_history,
        }

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "last.pt"
            runner.save_trial_checkpoint(
                path, model=partial_model, optimizer=partial_optimizer,
                step=checkpoint["step"], best=checkpoint["best"],
                best_step=checkpoint["best_step"], numpy_rng_state=committed_rng,
                history=partial_history, contract={"seed": 1234},
                device=device, torch=torch,
            )

            # Simulate process restart, including new model construction and unrelated RNG use.
            torch.manual_seed(9999)
            resumed_model, resumed_optimizer, resumed_rng, _ = make_run(8765)
            restored = runner.restore_trial_checkpoint(
                path, model=resumed_model, optimizer=resumed_optimizer,
                rng=resumed_rng, expected_contract={"seed": 1234},
                device=device, torch=torch,
            )
            step, best, best_step, resumed_history = restored
            self.assertEqual((step, best, best_step), (split_step, 0.625, split_step))
            train(resumed_model, resumed_optimizer, resumed_rng, resumed_history,
                  step, total_steps)

        assert_nested_equal(self, full_model.state_dict(), resumed_model.state_dict())
        assert_nested_equal(self, full_optimizer.state_dict(), resumed_optimizer.state_dict())
        self.assertEqual(full_history, resumed_history)
        self.assertTrue(torch.equal(full_torch_rng, torch.get_rng_state()))
        if device.type == "cuda":
            resumed_cuda_rngs = torch.cuda.get_rng_state_all()
            self.assertEqual(len(full_cuda_rngs), len(resumed_cuda_rngs))
            for expected, actual in zip(full_cuda_rngs, resumed_cuda_rngs):
                self.assertTrue(torch.equal(expected, actual))

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
        from xrd_robustness.training.runner import build_online_view_factory,render_pair_batch
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
            peak=load_peak_table(peak_path)
            serial_first,serial_second,serial_labels=render_pair_batch(
                [record],{record.material_id:peak},fac,
                epoch=1,global_step=137,profile="train",
            )
            with V11PairPrefetchPool(
                config,run_seed=12345,workers=2,prefetch_batches=2,
                native_threads=1,max_cached_peaks=16,
            ) as pool:
                pool.submit(137,[record],epoch=1,global_step=137,profile="train")
                first,second,labels=pool.get(137)
            self.assertTrue(np.array_equal(first[0],serial_first.numpy()[0]))
            self.assertTrue(np.array_equal(second[0],serial_second.numpy()[0]))
            self.assertTrue(np.array_equal(labels,serial_labels.numpy()))
            self.assertEqual(labels.tolist(),[3])
            # Changing Windows/Cloud CPU worker count must not change physics.
            with V11PairPrefetchPool(
                config,run_seed=12345,workers=1,prefetch_batches=2,
                native_threads=1,max_cached_peaks=16,
            ) as single_worker:
                single_worker.submit(137,[record],epoch=1,global_step=137,profile="train")
                one_a,one_b,one_y=single_worker.get(137)
            self.assertTrue(np.array_equal(first,one_a))
            self.assertTrue(np.array_equal(second,one_b))
            self.assertTrue(np.array_equal(labels,one_y))

    def test_worker_startup_failure_is_reported_and_children_are_joined(self):
        import json
        import multiprocessing as mp
        config=json.loads((
            ROOT.parent/"xrd_robustness"/"configs"/
            "simulation.v11_tch_pseudo_voigt.json"
        ).read_text(encoding="utf-8"))
        config["profiles"]={}
        with self.assertRaisesRegex(RuntimeError,"failed during startup"):
            V11PairPrefetchPool(config,run_seed=19,workers=2,worker_start_timeout_seconds=20)
        leftovers=[child.name for child in mp.active_children()
                   if child.name.startswith("v11-pair-worker-")]
        self.assertEqual(leftovers,[])

    def test_worker_task_error_is_returned_to_parent(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            config=json.loads((
                ROOT.parent/"xrd_robustness"/"configs"/
                "simulation.v11_tch_pseudo_voigt.json"
            ).read_text(encoding="utf-8"))
            record=SimpleNamespace(
                material_id="synthetic_missing_peak",peak_table_path=Path(temp)/"absent.npz",
                split="train",label=2,
            )
            with V11PairPrefetchPool(config,run_seed=7,workers=2,prefetch_batches=1) as pool:
                pool.submit(0,[record],epoch=0,global_step=0,profile="train")
                with self.assertRaisesRegex(RuntimeError,"FileNotFoundError"):
                    pool.get(0)

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



class ValidationPanelRecoveryTests(unittest.TestCase):
    def test_unindexed_complete_and_partial_files_are_removed_for_regeneration(self):
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            profile = "ood_noise"
            names = [
                profile + ".first.npy",
                profile + ".second.npy",
                profile + ".first.partial.npy",
                profile + ".second.partial.npy",
            ]
            for name in names:
                (base / name).write_bytes(b"orphan")
            runner.remove_unindexed_validation_panel_files(base, profile)
            self.assertTrue(all(not (base / name).exists() for name in names))
