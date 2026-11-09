"""V11 epoch-shuffle coverage, restart parity, microbatch gradient, runtime isolation."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import one_click_v11 as runner
from v11_prefetch import sample_parent_indices, enqueue_train_lookahead
from train_microbatch import paired_optimizer_step


class FakePool:
    def __init__(self, window):
        self.prefetch_batches = window
        self.pending = {}
    def submit(self, step, records, *, epoch, global_step, profile):
        self.pending[step] = (tuple(x.material_id for x in records), epoch, global_step, profile)
    def get(self, step):
        return self.pending.pop(step)


class ParentSamplerTests(unittest.TestCase):
    def test_full_epoch_unique_and_partial_final_batch(self):
        seed = 20260711
        n, batch = 23, 8
        cache = {}
        rng = np.random.default_rng(seed)
        one = [sample_parent_indices(rng,n,batch,i,sampling_mode="epoch_shuffle",
                                     sampling_seed=seed,permutation_cache=cache)[0].tolist()
               for i in range(3)]
        self.assertEqual([len(x) for x in one], [8,8,7])
        self.assertEqual(set(sum(one,[])), set(range(n)))
        self.assertEqual(len(sum(one,[])), n)
        two = [sample_parent_indices(rng,n,batch,i,sampling_mode="epoch_shuffle",
                                     sampling_seed=seed,permutation_cache=cache)[0].tolist()
               for i in range(3,6)]
        self.assertEqual(set(sum(two,[])), set(range(n)))
        self.assertNotEqual(one,two)

    def test_actual_108478_parent_coverage(self):
        n, batch = 108478, 16
        rng = np.random.default_rng(7)
        cache = {}
        counts = np.zeros(n,dtype=np.uint8)
        for step in range((n+batch-1)//batch):
            indices,epoch=sample_parent_indices(
                rng,n,batch,step,sampling_mode="epoch_shuffle",
                sampling_seed=20260711,permutation_cache=cache)
            self.assertEqual(epoch,0)
            counts[indices] += 1
        self.assertTrue(np.all(counts==1))
        self.assertEqual(len(indices),14)

    def test_resume_with_prefetched_steps_replays_identical_parent_order(self):
        items = [SimpleNamespace(material_id=f"p{i}") for i in range(23)]
        pool=FakePool(3)
        rng=np.random.default_rng(11)
        states={}
        cache={}
        enqueue_train_lookahead(pool,rng,items,batch_size=8,start_step=0,
            next_submit=0,max_steps=9,committed_states=states,
            sampling_mode="epoch_shuffle",sampling_seed=11,permutation_cache=cache)
        first=pool.get(0)
        saved=copy.deepcopy(states[0])
        pending=copy.deepcopy(pool.pending)
        restarted=FakePool(3)
        replay_rng=np.random.default_rng(999)
        replay_rng.bit_generator.state=saved
        enqueue_train_lookahead(restarted,replay_rng,items,batch_size=8,start_step=1,
            next_submit=1,max_steps=9,committed_states={},
            sampling_mode="epoch_shuffle",sampling_seed=11,permutation_cache={})
        for step in pending:
            self.assertEqual(restarted.pending[step],pending[step])
        self.assertEqual(first[1],0)
        self.assertEqual(pool.pending[2][1],0)
        # Restart directly into the next epoch, no prior permutation needed.
        later=sample_parent_indices(np.random.default_rng(0),23,8,3,
              sampling_mode="epoch_shuffle",sampling_seed=11,permutation_cache={})[0]
        actual=sample_parent_indices(np.random.default_rng(0),23,8,3,
              sampling_mode="epoch_shuffle",sampling_seed=11,permutation_cache=cache)[0]
        np.testing.assert_array_equal(later,actual)


class MicrobatchTests(unittest.TestCase):
    def test_cpu_gradient_matches_full_batch_ce_js(self):
        import torch
        torch.manual_seed(17)
        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.layer=torch.nn.Sequential(torch.nn.Linear(5,8),
                                               torch.nn.GELU(),torch.nn.Linear(8,7))
            def forward(self,x):
                return {"logits":self.layer(x)}
        first=torch.randn(8,5)
        second=torch.randn(8,5)
        labels=torch.arange(8) % 7
        reference=TinyModel()
        micro=copy.deepcopy(reference)
        opts=[torch.optim.AdamW(m.parameters(),lr=1e-3) for m in (reference,micro)]
        a=paired_optimizer_step(reference,opts[0],first,second,labels,
           lambda_js=60,microbatch_size=8,loss_fn=runner.loss_js,torch=torch,
           F=torch.nn.functional,amp=False)
        b=paired_optimizer_step(micro,opts[1],first,second,labels,
           lambda_js=60,microbatch_size=3,loss_fn=runner.loss_js,torch=torch,
           F=torch.nn.functional,amp=False)
        for x,y in zip(a,b):
            self.assertAlmostEqual(x,y,places=5)
        for key,val in reference.state_dict().items():
            torch.testing.assert_close(val,micro.state_dict()[key],rtol=1e-5,atol=1e-6)

    def test_microbatch_guard(self):
        import torch
        model=torch.nn.Linear(3,7)
        optim=torch.optim.AdamW(model.parameters())
        with self.assertRaisesRegex(ValueError,"Microbatch"):
            paired_optimizer_step(model,optim,torch.zeros(2,3),torch.zeros(2,3),
                torch.zeros(2,dtype=torch.long),lambda_js=1,microbatch_size=0,
                loss_fn=runner.loss_js,torch=torch,F=torch.nn.functional,amp=False)


class DefaultBudgetTests(unittest.TestCase):
    """Check the CLI plans longer HPO before any CUDA/HPO execution."""

    def test_default_budget_is_5_10_10_parent_epochs(self):
        for batch_size in (16, 32):
            with self.subTest(batch=batch_size), mock.patch.object(
                sys, "argv", ["one_click_v11.py", "--batch-size", str(batch_size)]
            ), mock.patch.object(runner, "run_pipeline") as plan:
                runner.main()
                args=plan.call_args.args[0]
                epoch=(108478+batch_size-1)//batch_size
                self.assertEqual(args.hpo_steps, 5*epoch)
                self.assertEqual(args.confirm_steps, 10*epoch)
                self.assertEqual(args.final_steps, 10*epoch)
                self.assertEqual(args.eval_every, epoch)
                self.assertEqual(args.sampling_mode, "epoch_shuffle")
                self.assertEqual(args.mode, "plan")

    def test_explicit_budget_overrides_are_preserved(self):
        flags=["one_click_v11.py","--hpo-steps","6780",
               "--confirm-steps","13560","--final-steps","49280",
               "--eval-every","6780"]
        with mock.patch.object(sys,"argv",flags), mock.patch.object(
            runner,"run_pipeline"
        ) as plan:
            runner.main()
            args=plan.call_args.args[0]
            self.assertEqual((args.hpo_steps,args.confirm_steps,
                              args.final_steps,args.eval_every),
                             (6780,13560,49280,6780))


class FinalRuntimeOverridesTests(unittest.TestCase):
    def fake_args(self):
        return SimpleNamespace(
            mode="final",trials=6,hpo_steps=33900,confirm_steps=67800,
            final_steps=67800,batch_size=16,microbatch_size=16,
            sampling_mode="epoch_shuffle",eval_every=6780,
            prefetch_workers=4,prefetch_batches=2,native_threads=1,
            worker_peak_cache=256,max_gpu_hours=24,validation_bf16=False)

    def test_runtime_only_override_is_accepted_before_evidence_gate(self):
        args=self.fake_args()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"server_runs/v11_a0_js_optuna/contract.json"
            p.parent.mkdir(parents=True)
            frozen={"prefetch_workers":2,"max_gpu_hours":12,
                    "batch_size_parents":16,"simulation_config_sha256":"fixed"}
            current=dict(frozen,prefetch_workers=4,max_gpu_hours=24)
            p.write_text(json.dumps(frozen),encoding="utf-8")
            with mock.patch.object(runner,"ROOT",Path(td)),mock.patch.object(
                runner,"contract",return_value=current):
                with self.assertRaisesRegex(RuntimeError,"recommendation missing"):
                    runner.run_pipeline(args)

    def test_scientific_batch_override_rejected(self):
        args=self.fake_args()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"server_runs/v11_a0_js_optuna/contract.json"
            p.parent.mkdir(parents=True)
            frozen={"prefetch_workers":2,"batch_size_parents":16}
            current={"prefetch_workers":4,"batch_size_parents":8}
            p.write_text(json.dumps(frozen),encoding="utf-8")
            with mock.patch.object(runner,"ROOT",Path(td)),mock.patch.object(
                runner,"contract",return_value=current):
                with self.assertRaisesRegex(RuntimeError,"science contract mismatch"):
                    runner.run_pipeline(args)


if __name__=="__main__":
    unittest.main()
