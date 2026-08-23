import unittest

from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.training_stream import (
    TrainingStreamAudit,
    build_training_sampler_contract,
    deterministic_epoch_shuffle,
    epoch_shuffle_hash,
    paired_manifest_ids,
    select_epoch_batch,
    training_sampler_contract_hash,
)
from xrd_robustness.view_manifest import build_parameter_batch, build_parameter_row


def _fixed(value):
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _sampler(seed=17):
    return PhysicsParameterSampler.from_mapping(
        {
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
    )


class TrainingStreamTests(unittest.TestCase):
    def test_epoch_shuffle_is_replayable_and_epoch_specific(self):
        material_ids = [f"mp-{index}" for index in range(40)]
        first = deterministic_epoch_shuffle(material_ids, seed=9, epoch=0)
        replay = deterministic_epoch_shuffle(reversed(material_ids), seed=9, epoch=0)
        second_epoch = deterministic_epoch_shuffle(material_ids, seed=9, epoch=1)
        self.assertEqual(first, replay)
        self.assertNotEqual(first, second_epoch)
        self.assertEqual(set(first), set(material_ids))
        self.assertEqual(len(first), len(material_ids))
        self.assertEqual(
            epoch_shuffle_hash(first, seed=9, epoch=0),
            epoch_shuffle_hash(replay, seed=9, epoch=0),
        )

    def test_fixed_budget_batches_wrap_after_deterministic_shuffle(self):
        order = ("a", "b", "c", "d", "e")
        self.assertEqual(
            select_epoch_batch(order, step=1, batch_size=4, full_batch=True),
            ("e", "a", "b", "c"),
        )
        self.assertEqual(
            select_epoch_batch(order, step=1, batch_size=4, full_batch=False),
            ("e",),
        )

    def test_parameter_rows_are_generated_only_for_the_consumed_batch(self):
        all_ids = [f"mp-{index}" for index in range(100)]
        order = deterministic_epoch_shuffle(all_ids, seed=17, epoch=0)
        batch_ids = select_epoch_batch(order, step=2, batch_size=16, full_batch=True)
        rows = build_parameter_batch(
            batch_ids,
            _sampler(),
            profile="train",
            epoch=0,
            global_step=2,
        )
        self.assertEqual(len(rows), 32)
        self.assertEqual(tuple(row.material_id for row in rows[::2]), batch_ids)
        self.assertEqual(len(paired_manifest_ids(rows, batch_ids)), 16)

    def test_retry_seed_coordinate_preserves_semantic_pair_identity(self):
        sampler = _sampler()
        initial = build_parameter_row(
            "mp-1",
            sampler,
            profile="train",
            epoch=2,
            global_step=7,
            view_id=1,
        )
        retry = build_parameter_row(
            "mp-1",
            sampler,
            profile="train",
            epoch=2,
            global_step=7,
            view_id=1,
            sampling_view_id=3,
        )
        replay = build_parameter_row(
            "mp-1",
            sampler,
            profile="train",
            epoch=2,
            global_step=7,
            view_id=1,
            sampling_view_id=3,
        )
        self.assertEqual(retry, replay)
        self.assertEqual(retry.view_id, initial.view_id)
        self.assertNotEqual(retry.simulation_seed, initial.simulation_seed)
        self.assertNotEqual(retry.manifest_id, initial.manifest_id)

    def test_five_methods_share_sampler_and_pair_schedule_hashes(self):
        material_ids = [f"mp-{index}" for index in range(10)]
        contract = build_training_sampler_contract(
            material_ids,
            seed=17,
            batch_size=4,
            steps_per_epoch=3,
            target_optimizer_steps=6,
            full_batches=True,
        )
        contract_hash = training_sampler_contract_hash(contract)
        modes = ("clean_erm", "offline_erm", "dynamic_erm", "dynamic_js", "dynamic_residual")
        snapshots = {}
        for mode in modes:
            audit = TrainingStreamAudit.create(contract_hash)
            for epoch in range(2):
                order = deterministic_epoch_shuffle(material_ids, seed=17, epoch=epoch)
                for step in range(3):
                    batch_ids = select_epoch_batch(
                        order,
                        step=step,
                        batch_size=4,
                        full_batch=True,
                    )
                    if mode.startswith("dynamic"):
                        rows = build_parameter_batch(
                            batch_ids,
                            _sampler(),
                            profile="train",
                            epoch=epoch,
                            global_step=step,
                        )
                        pairs = paired_manifest_ids(rows, batch_ids)
                    elif mode == "clean_erm":
                        pairs = tuple((f"clean:{value}", f"clean:{value}") for value in batch_ids)
                    else:
                        first_view = (epoch * 3 + step) * 2 % 4 + 1
                        second_view = first_view % 4 + 1
                        pairs = tuple(
                            (f"offline:{value}:{first_view}", f"offline:{value}:{second_view}")
                            for value in batch_ids
                        )
                    audit.record_batch(
                        epoch=epoch,
                        step=step,
                        absolute_step=epoch * 3 + step,
                        material_ids=batch_ids,
                        parameter_pairs=pairs,
                        views_per_structure=2,
                    )
            snapshots[mode] = audit.snapshot()

        self.assertEqual(len({value["sampler_hash"] for value in snapshots.values()}), 1)
        self.assertEqual(len({value["pair_schedule_hash"] for value in snapshots.values()}), 1)
        self.assertEqual({value["structure_exposures"] for value in snapshots.values()}, {24})
        self.assertEqual({value["spectrum_exposures"] for value in snapshots.values()}, {48})
        dynamic_pair_hashes = {
            snapshots[mode]["parameter_pair_hash"]
            for mode in ("dynamic_erm", "dynamic_js", "dynamic_residual")
        }
        self.assertEqual(len(dynamic_pair_hashes), 1)
        self.assertNotIn(snapshots["clean_erm"]["parameter_pair_hash"], dynamic_pair_hashes)
        self.assertNotIn(snapshots["offline_erm"]["parameter_pair_hash"], dynamic_pair_hashes)

    def test_audit_hash_chain_resumes_from_snapshot(self):
        contract = build_training_sampler_contract(
            ["a", "b", "c", "d"],
            seed=3,
            batch_size=2,
            steps_per_epoch=2,
            target_optimizer_steps=2,
            full_batches=True,
        )
        contract_hash = training_sampler_contract_hash(contract)
        order = deterministic_epoch_shuffle(["a", "b", "c", "d"], seed=3, epoch=0)
        uninterrupted = TrainingStreamAudit.create(contract_hash)
        resumed = TrainingStreamAudit.create(contract_hash)
        for step in range(2):
            batch_ids = select_epoch_batch(order, step=step, batch_size=2, full_batch=True)
            pairs = tuple((f"{value}:1", f"{value}:2") for value in batch_ids)
            uninterrupted.record_batch(
                epoch=0,
                step=step,
                absolute_step=step,
                material_ids=batch_ids,
                parameter_pairs=pairs,
                views_per_structure=2,
            )
            if step == 0:
                resumed.record_batch(
                    epoch=0,
                    step=step,
                    absolute_step=step,
                    material_ids=batch_ids,
                    parameter_pairs=pairs,
                    views_per_structure=2,
                )
                resumed = TrainingStreamAudit.from_snapshot(
                    resumed.snapshot(),
                    sampler_contract_hash=contract_hash,
                )
            else:
                resumed.record_batch(
                    epoch=0,
                    step=step,
                    absolute_step=step,
                    material_ids=batch_ids,
                    parameter_pairs=pairs,
                    views_per_structure=2,
                )
        self.assertEqual(uninterrupted.snapshot(), resumed.snapshot())


if __name__ == "__main__":
    unittest.main()
