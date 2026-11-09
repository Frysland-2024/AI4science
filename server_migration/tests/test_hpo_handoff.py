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


class HandoffImportTests(unittest.TestCase):
    def make_archive(self, path, *, tamper=False, unsafe=False):
        index = {"identity": {"parent_count": 23245}, "entries": {}}
        contract = b'{"sample":1}\n'
        recommendation = {
            "status": "hpo_and_confirmation_completed",
            "contract_sha256": hashlib.sha256(contract).hexdigest(),
            "validation_panel_index_sha256": hpo_handoff._canonical_index_digest(index),
        }
        files = {
            "contract.json": contract,
            "final_recommendation.json": json.dumps(recommendation).encode(),
            "handoff_validation_panel_index.json": json.dumps(index).encode(),
            "optuna.sqlite3": b"fake db for transport unit test",
        }
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
                             b'{"sample":1}\n')
            self.assertEqual(hpo_handoff.import_handoff(root, archive)["imported_files"], 4)

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

    def test_newline_independent_validation_index_identity(self):
        obj = {"identity": {"a": 2}, "entries": {"b": {"sha256": ["x", "y"]}}}
        self.assertEqual(hpo_handoff._canonical_index_digest(json.loads(json.dumps(obj, indent=2))),
                         hpo_handoff._canonical_index_digest(obj))


if __name__ == "__main__":
    unittest.main()
