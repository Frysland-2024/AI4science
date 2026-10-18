"""Pure local tests. No Codex / GitHub network calls."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research_bridge import worker as w

def issue(labels=None, **overrides):
    data = {"number": 42, "state": "open",
            "title": "[Bridge] Summarize evidence",
            "body": "Read committed metrics and summarize limitations.",
            "user": {"login": "Frysland-2024"},
            "labels": [{"name": x} for x in (labels or [w.READY, w.APPROVED])]}
    data.update(overrides)
    return data

class WorkerTests(unittest.TestCase):
    def test_eligible_requires_owner_two_labels_and_readable_body(self):
        self.assertTrue(w.eligible(issue()))
        self.assertFalse(w.eligible(issue(labels=[w.READY])))
        self.assertFalse(w.eligible(issue(user={"login": "stranger"})))
        self.assertFalse(w.eligible(issue(title="Do arbitrary things")))
        self.assertFalse(w.eligible(issue(body="")))
        self.assertFalse(w.eligible(issue(labels=[w.READY, w.APPROVED, w.RUNNING])))
        self.assertFalse(w.eligible(issue(pull_request={})))

    def test_candidate_sort_and_filter(self):
        data = [issue(number=7), issue(number=2), issue(number=5, user={"login": "other"})]
        with patch.object(w, "gh", return_value=json.dumps(data)):
            self.assertEqual([i["number"] for i in w.pending()], [2, 7])

    def test_auth_env_prevents_api_key_fallback(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret", "CODEX_API_KEY": "paid",
                                     "CODEX_ACCESS_TOKEN": "token"}):
            env = w.codex_env()
        for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN"):
            self.assertNotIn(key, env)

    def test_windows_codex_cmd_resolution(self):
        """Windows npm uses codex.cmd; never rely on a PowerShell alias."""
        with patch.object(w.shutil, "which", side_effect=lambda name: {
            "codex.cmd": r"C:\\Users\\student\\AppData\\Roaming\\npm\\codex.cmd"
        }.get(name)):
            self.assertTrue(w.codex_executable(windows=True).endswith("codex.cmd"))

    def test_nonwindows_codex_resolution(self):
        with patch.object(w.shutil, "which", side_effect=lambda name: {
            "codex": "/usr/bin/codex"
        }.get(name)):
            self.assertEqual(w.codex_executable(windows=False), "/usr/bin/codex")

    def test_windows_fails_without_codex_cli(self):
        with patch.object(w.shutil, "which", return_value=None):
            with self.assertRaises(w.BridgeError):
                w.codex_executable(windows=True)

    def test_dry_run_never_calls_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            with patch.object(w, "revision") as rev, patch.object(w, "review_task") as model:
                w.run_once(root, issue(), dry_run=True)
                rev.assert_not_called()
                model.assert_not_called()

    def test_success_records_review_and_posts_comment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            with patch.object(w, "revision", return_value="abcd"), \
                 patch.object(w, "review_task", return_value="Evidence: docs/CURRENT_STATE.md"), \
                 patch.object(w, "label") as label, patch.object(w, "comment") as comment:
                w.run_once(root, issue())
                self.assertEqual(label.call_count, 2)
                self.assertEqual(comment.call_count, 1)
                self.assertIn("Evidence", comment.call_args.args[1])
            data = json.loads(w.journal(root, 42).read_text())
            self.assertEqual(data["status"], "REVIEW")

    def test_failure_is_preserved_and_does_not_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            with patch.object(w, "revision", return_value="abcd"), \
                 patch.object(w, "review_task", side_effect=w.BridgeError("failed")), \
                 patch.object(w, "label") as labels, patch.object(w, "comment"):
                with self.assertRaises(w.BridgeError):
                    w.run_once(root, issue())
                w.run_once(root, issue())
                self.assertEqual(labels.call_count, 2)
            self.assertEqual(json.loads(w.journal(root, 42).read_text())["status"], "FAILED")

    def test_revision_uses_remote_commit_without_checkout(self):
        # Protect untracked/local scientific files: never pull or reset.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".git").mkdir()
            calls = []
            def cmd(argv, **kwargs):
                calls.append(argv)
                if argv[:3] == ["git", "rev-parse", "FETCH_HEAD"]:
                    return "abc123\n"
                return ""
            with patch.object(w, "command", side_effect=cmd), \
                 patch.object(w, "gh", return_value='{"sha":"abc123"}'):
                self.assertEqual(w.revision(root), "abc123")
            self.assertEqual(calls[0][:3], ["git", "fetch", "--quiet"])
            self.assertFalse(any("pull" in cmd or "reset" in cmd or "checkout" in cmd for cmd in calls))

    def test_missing_git_checkout_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(w.BridgeError):
                w.revision(Path(temp))

if __name__ == "__main__":
    unittest.main()
