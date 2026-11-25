import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sync_docs", ROOT / "scripts/sync_docs.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class SyncTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.state = json.loads((ROOT / sync.SOURCE).read_text())
        self.save()
        for name in sync.DOCS:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("before\n" + sync.BEGIN + "\nstale\n" + sync.END + "\nafter\n")

    def save(self):
        (self.root / sync.SOURCE).write_text(json.dumps(self.state))

    def test_drift_and_idempotence(self):
        pending = sync.changes(self.root)
        self.assertEqual(len(pending), len(sync.DOCS))
        for path, old, new in pending:
            self.assertTrue(new.startswith("before\n"))
            self.assertTrue(new.endswith("\nafter\n"))
            path.write_bytes(new.encode())
        self.assertEqual(sync.changes(self.root), [])
        self.state["manuscript_priority"] = "HIGH"
        self.save()
        self.assertEqual(len(sync.changes(self.root)), len(sync.DOCS))

    def test_missing_marker(self):
        (self.root / sync.DOCS[-1]).write_text("no markers")
        with self.assertRaises(ValueError):
            sync.changes(self.root)

    def test_duplicate_marker(self):
        p = self.root / sync.DOCS[0]
        p.write_text(p.read_text() + sync.BEGIN)
        with self.assertRaises(ValueError):
            sync.changes(self.root)

    def test_invalid_state(self):
        self.state["execution"] = "ACTIVE"
        self.save()
        with self.assertRaises(ValueError):
            sync.changes(self.root)

    def test_downstream_gate(self):
        self.state["stages"]["hpo"] = "PASS"
        self.save()
        with self.assertRaises(ValueError):
            sync.changes(self.root)

    def test_live_repo(self):
        self.assertEqual(sync.changes(ROOT), [])
