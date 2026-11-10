"""Guardrails for the opt-in local dispatcher; does not launch Codex/GPU."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "controlled_dispatch.py"
SPEC = importlib.util.spec_from_file_location("controlled_dispatch", SRC)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class DispatcherTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.home = self.root / "private"
        self.scope = patch.object(mod, "state_root", return_value=self.home)
        self.scope.start()
        self.addCleanup(self.scope.stop)
        self.task = {"version": 1, "task_id": "review_001", "lane": "codex_review",
                     "source_sha": "a" * 40, "expected_hostname": "LAPTOP-TEST",
                     "prompt": "Review the repository's execution policy. Do not change anything."}

    def install(self, task=None):
        task = task or self.task
        p = self.home / "tasks" / (task["task_id"] + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(task), encoding="utf-8")
        return p

    def authorize(self, task=None):
        task = task or self.task
        p = self.home / "approvals" / (task["task_id"] + ".json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"task_id": task["task_id"], "source_sha": task["source_sha"],
                                 "approved_sha256": mod.sha256_object(task)}), encoding="utf-8")

    def test_empty_queue_never_launches(self):
        self.assertEqual(mod.run_once(self.root)["status"], "IDLE")
        self.assertFalse((self.home / "runs").exists())

    def test_unapproved_queue_is_idle(self):
        self.install()
        self.assertEqual(mod.run_once(self.root)["status"], "IDLE")

    def test_strict_allowlist_and_no_hpo(self):
        for lane in ("v11_hpo", "final", "shell", "codex_write"):
            with self.subTest(lane=lane):
                x = {**self.task, "lane": lane}
                with self.assertRaises(ValueError):
                    mod.verify(x)

    def test_unknown_task_field_forbidden(self):
        with self.assertRaises(ValueError):
            mod.verify({**self.task, "shell_command": "echo risky"})

    def test_tampering_after_approval_is_blocked(self):
        self.install()
        self.authorize()
        x = {**self.task, "prompt": "Execute arbitrary changes to all files please"}
        self.install(x)
        result = mod.run_once(self.root, dry_run=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse((self.home / "runs").exists())

    def test_dry_run_has_no_side_effects(self):
        self.install()
        self.authorize()
        with patch.object(mod, "preflight"), patch.object(mod, "command", return_value=(["python"], 10)):
            result = mod.run_once(self.root, dry_run=True)
        self.assertEqual(result["status"], "DRY_RUN")
        self.assertFalse((self.home / "runs").exists())

    def test_once_records_and_does_not_retry(self):
        self.install()
        self.authorize()
        with patch.object(mod, "preflight"), patch.object(mod, "command", return_value=([sys.executable, "-c", "print('ok')"], 10)):
            result = mod.run_once(self.root)
            second = mod.run_once(self.root)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(second["status"], "IDLE")
        journal = json.loads((self.home / "runs" / "review_001.json").read_text(encoding="utf-8"))
        self.assertEqual(journal["status"], "COMPLETED")

    def test_nonzero_process_does_not_retry(self):
        self.install()
        self.authorize()
        with patch.object(mod, "preflight"), patch.object(mod, "command", return_value=([sys.executable, "-c", "raise SystemExit(7)"], 10)):
            self.assertEqual(mod.run_once(self.root)["status"], "BLOCKED")
            self.assertEqual(mod.run_once(self.root)["status"], "IDLE")

    def test_approval_only_after_preflight(self):
        self.install()
        with patch.object(mod, "preflight", side_effect=ValueError("dirty worktree")):
            with self.assertRaisesRegex(ValueError, "dirty worktree"):
                mod.approve(self.root, "review_001")
        self.assertFalse((self.home / "approvals").exists())

    def test_gpu_preflight_is_fixed_mode_and_cannot_have_prompt(self):
        item = {k: v for k, v in self.task.items() if k != "prompt"}
        item["lane"] = "v11_smoke"
        mod.verify(item)
        with self.assertRaises(ValueError):
            mod.verify({**item, "prompt": "overwrite labels"})

    def test_status_does_not_assume_running_without_journal(self):
        self.install()
        self.assertEqual(mod.records(self.root)[0]["status"], "AWAITING_APPROVAL")

    def test_wrong_machine_fails_closed(self):
        with patch.dict(os.environ, {"COMPUTERNAME": "OTHER"}):
            with self.assertRaisesRegex(ValueError, "different host"):
                mod.preflight(self.root, self.task)


if __name__ == "__main__":
    unittest.main()
