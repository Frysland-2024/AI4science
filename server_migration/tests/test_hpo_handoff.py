"""Offline regression tests for native Windows -> Linux V11 HPO evidence handoff."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hpo_handoff
import one_click_v11 as runner


class HandoffImportTests(unittest.TestCase):
    @staticmethod
    def science_contract():
        return {
            "schema":"v11_154975_gradient_informed_three_parameter_v3",
            "payload_contract_version":"v11-gradient-gated-optuna-20261110.10",
            "implementation_sha256":{"runner":"fixture"},
            "source_manifest_sha256":"fixture",
            "simulator_config_sha256":"fixture",
            "training_rows":108483,"training_parents":108478,
            "architecture_presets":{},"fixed_optimizer":{"learning_rate":2e-4},
            "batch_size_parents":16,"sampling_mode":"epoch_shuffle",
            "training_precision":"bf16_if_supported_else_fp32",
            "gradient_gate_contract":{"warmup_min_parent_epochs":5},
        }

    def make_archive(self, path, *, tamper=False, unsafe=False, omit_gate=False):
        index = {"identity": {"parent_count": 23245}, "entries": {}}
        contract_obj=self.science_contract()
        contract=(json.dumps(contract_obj)+"\n").encode()
        gate={"status":"TRAIN_ONLY_GRADIENT_GATE_PASS",
              "science_identity_sha256":runner.gradient_science_identity(contract_obj),
              "lambda_window":{"low":3.0,"high":120.0,"anchor":60.0}}
        gate_bytes=json.dumps(gate).encode()
        recommendation = {
            "status": "hpo_and_confirmation_completed",
            "gradient_gate_sha256":hashlib.sha256(gate_bytes).hexdigest(),
            "contract_sha256": hashlib.sha256(contract).hexdigest(),
            "validation_panel_index_sha256": hpo_handoff._canonical_index_digest(index),
        }
        files = {
            "contract.json": contract,
            "final_recommendation.json": json.dumps(recommendation).encode(),
            "handoff_validation_panel_index.json": json.dumps(index).encode(),
            "optuna.sqlite3": b"fake db for transport unit test",
        }
        if not omit_gate:
            files["gradient_gate.json"] = gate_bytes
        if unsafe:
            files["../evil.txt"] = b"evil"
        manifest = {
            "version": hpo_handoff.VERSION,
            "study": hpo_handoff.STUDY_REL.as_posix(),
            "contract_sha256": hashlib.sha256(contract).hexdigest(),
            "validation_index_sha256": hpo_handoff._canonical_index_digest(index),
            "files": {name: hashlib.sha256(value).hexdigest() for name, value in files.items()},
        }
        with zipfile.ZipFile(path, "w") as archive:
            for name, data in files.items():
                archive.writestr(name, b"tampered" if tamper and name == "contract.json" else data)
            archive.writestr(hpo_handoff.MANIFEST, json.dumps(manifest))

    def test_verified_import_and_idempotence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "handoff.zip"
            self.make_archive(archive)
            first = hpo_handoff.import_handoff(root, archive)
            self.assertEqual(first["status"], "imported_unscored")
            self.assertEqual((root / hpo_handoff.STUDY_REL / "contract.json").read_bytes(),
                             (json.dumps(self.science_contract())+"\n").encode())
            self.assertEqual(hpo_handoff.import_handoff(root, archive)["imported_files"], 5)

    def test_tamper_rejected_without_files_created(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "handoff.zip"
            self.make_archive(archive, tamper=True)
            with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
                hpo_handoff.import_handoff(root, archive)
            self.assertFalse((root / hpo_handoff.STUDY_REL / "contract.json").exists())

    def test_path_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "handoff.zip"
            self.make_archive(archive, unsafe=True)
            with self.assertRaisesRegex(RuntimeError, "Unsafe"):
                hpo_handoff.import_handoff(root, archive)
            self.assertFalse((root / "evil.txt").exists())

    def test_missing_gradient_gate_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            archive=root/"missing_gate.zip"
            self.make_archive(archive,omit_gate=True)
            with self.assertRaisesRegex(RuntimeError,"TRAIN gradient prior"):
                hpo_handoff.import_handoff(root,archive)
            self.assertFalse((root/hpo_handoff.STUDY_REL/"contract.json").exists())

    def test_newline_independent_validation_index_identity(self):
        obj = {"identity": {"a": 2}, "entries": {"b": {"sha256": ["x", "y"]}}}
        self.assertEqual(hpo_handoff._canonical_index_digest(json.loads(json.dumps(obj, indent=2))),
                         hpo_handoff._canonical_index_digest(obj))


if __name__ == "__main__":
    unittest.main()
