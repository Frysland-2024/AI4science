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

    def test_missing_git_checkout_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(w.BridgeError):
                w.revision(Path(temp))

if __name__ == "__main__":
    unittest.main()
