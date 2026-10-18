"""Offline, side-effect-free tests of the guarded code task lane."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_bridge import code_tasks as c
from research_bridge import worker as w

def code_issue(**kw):
    item = {"number": 99, "state": "open", "title": "[Bridge Code] Small approved change",
        "body": json.dumps({"task": "Add a note file.", "allowed_paths":
                            ["docs/bridge_proposals/note.md"], "test_profile": "syntax"}),
        "user": {"login": "Frysland-2024"},
        "labels": [{"name": x} for x in (w.READY, c.CODE_APPROVED)]}
    item.update(kw)
    return item

class CodeGuardTests(unittest.TestCase):
    def test_explicit_owner_and_code_approval(self):
        self.assertTrue(c.eligible(code_issue()))
        self.assertFalse(c.eligible(code_issue(user={"login": "random"})))
        self.assertFalse(c.eligible(code_issue(labels=[{"name":w.READY}])))
        self.assertFalse(c.eligible(code_issue(labels=[
            {"name":w.READY},{"name":c.CODE_APPROVED},{"name":w.APPROVED}])))
        self.assertFalse(c.eligible(code_issue(title="[Bridge] Read-only task")))

    def test_spec_requires_exact_fields(self):
        invalid = [
          {"task":"ok","allowed_paths":["xrd_robustness/config.py"],"test_profile":"syntax"},
          {"task":"ok","allowed_paths":["AGENTS.md"],"test_profile":"syntax"},
          {"task":"ok","allowed_paths":["../secrets.txt"],"test_profile":"syntax"},
          {"task":"ok","allowed_paths":["pxrd_autolab/../../oops"],"test_profile":"syntax"},
          {"task":"ok","allowed_paths":["pxrd_autolab/x.py"],"test_profile":"shell"},
          {"task":"ok","allowed_paths":["pxrd_autolab/x.py"],"test_profile":"syntax","run":"gpu"},
        ]
        for i in invalid:
            with self.subTest(i=i):
                with self.assertRaises(w.BridgeError):
                    c.parse_code_spec(code_issue(body=json.dumps(i)))

    def test_rejects_changes_outside_approved_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "CURRENT_STATE.md").write_text("tampered",encoding="utf-8")
            with patch.object(c,"changed_paths",return_value=["docs/CURRENT_STATE.md"]):
                with self.assertRaises(w.BridgeError):
                    c.check_scope(root,c.parse_code_spec(code_issue()))

    def test_path_guard_accepts_scoped_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "docs" / "bridge_proposals" / "note.md"
            p.parent.mkdir(parents=True)
            p.write_text("Safe draft only",encoding="utf-8")
            with patch.object(c,"changed_paths",return_value=["docs/bridge_proposals/note.md"]):
                self.assertEqual(c.check_scope(root,c.parse_code_spec(code_issue())),["docs/bridge_proposals/note.md"])

    def test_no_execution_during_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            with patch.object(w,"revision") as revision, patch.object(c,"invoke_codex") as run:
                c.run(root,code_issue(),dry_run=True)
                revision.assert_not_called()
                run.assert_not_called()

    def test_snapshot_uses_frozen_commit(self):
        import inspect
        self.assertIn('snapshot(root, workspace, revision_sha)',inspect.getsource(w.review_task))
        self.assertIn('"archive", "--format=tar", commit',inspect.getsource(w.snapshot))

    def test_parse_disallows_protected_worker_changes(self):
        issue=code_issue(body=json.dumps({"task":"tamper", "allowed_paths":
                        ["research_bridge/tests/new_test.py"],"test_profile":"syntax"}))
        self.assertTrue(c.eligible(issue))  # Well-formed ticket may be created.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            f=root/"research_bridge"/"worker.py"
            f.parent.mkdir(parents=True)
            f.write_text("malicious",encoding="utf-8")
            with patch.object(c,"changed_paths",return_value=["research_bridge/worker.py"]):
                with self.assertRaises(w.BridgeError):
                    c.check_scope(root,c.parse_code_spec(issue))

if __name__=="__main__":
    unittest.main()
