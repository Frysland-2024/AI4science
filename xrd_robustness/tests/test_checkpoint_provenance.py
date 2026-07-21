from pathlib import Path
import tempfile
import unittest

import torch

from xrd_robustness.experiment import (
    assert_checkpoint_provenance,
    load_checkpoint,
    save_checkpoint,
)


class CheckpointProvenanceTests(unittest.TestCase):
    def test_checkpoint_round_trip_binds_all_run_inputs(self):
        model = torch.nn.Linear(2, 2)
        optimizer = torch.optim.AdamW(model.parameters())
        provenance = {
            "method_protocol_hash": "protocol",
            "peak_cache_manifest_hash": "cache",
            "simulation_config_hash": "simulation",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "last.ckpt"
            save_checkpoint(
                path,
                model=model,
                optimizers=[optimizer],
                epoch=1,
                global_step=2,
                config={"name": "tiny"},
                data_manifest_hash="data",
                view_manifest_hash="views",
                seed=3,
                provenance=provenance,
            )
            payload = load_checkpoint(path, model=model, optimizers=[optimizer])
            assert_checkpoint_provenance(
                payload,
                data_manifest_hash="data",
                view_manifest_hash="views",
                provenance=provenance,
            )
            with self.assertRaisesRegex(ValueError, "cache"):
                assert_checkpoint_provenance(
                    payload,
                    data_manifest_hash="data",
                    view_manifest_hash="views",
                    provenance={**provenance, "peak_cache_manifest_hash": "changed"},
                )

    def test_checkpoint_rejects_optimizer_count_mismatch(self):
        model = torch.nn.Linear(2, 2)
        optimizer = torch.optim.AdamW(model.parameters())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "last.ckpt"
            save_checkpoint(
                path,
                model=model,
                optimizers=[],
                epoch=1,
                global_step=2,
                config={"name": "tiny"},
                data_manifest_hash="data",
                view_manifest_hash="views",
                seed=3,
            )
            with self.assertRaisesRegex(ValueError, "optimizer count mismatch"):
                load_checkpoint(path, model=model, optimizers=[optimizer])


if __name__ == "__main__":
    unittest.main()
