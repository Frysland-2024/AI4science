"""Dry-run verification of the owner-approved queue; no Codex/GPU/network calls."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / "controlled_dispatcher.py"
SPEC = importlib.util.spec_from_file_location("controlled_dispatcher", FILE)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)
SHA = "a" * 40


class TestControlledDispatcher(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for k, value in {"ROOT": self.root, "PRIVATE": self.root / "_local" / "controlled_dispatcher",
                         "QUEUE": self.root / "_local" / "controlled_dispatcher" / "queue",
                         "RUNS": self.root / "_local" / "controlled_dispatcher" / "runs"}.items():
            patcher = patch.object(mod, k, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.check = patch.object(mod, "check_source", side_effect=lambda sha, **kw: sha)
        self.check.start()
        self.addCleanup(self.check.stop)

    def job(self, kind="codex_review"):
        return mod.approve(kind, SHA)

    def test_idle_has_no_side_effect(self):
        with patch.object(mod, "_execute") as exe:
            self.assertEqual(mod.tick()["status"], "IDLE")
            exe.assert_not_called()

    def test_approval_queues_one_pinned_codex_review(self):
        with patch.object(mod, "_execute", return_value=0) as exe:
            j = self.job()
            result = mod.tick()
            self.assertEqual(result["status"], "COMPLETED")
            self.assertEqual(result["kind"], "codex_review")
            self.assertEqual(exe.call_count, 1)
            self.assertEqual(mod.tick()["status"], "IDLE")
            self.assertEqual(len(mod.status()["jobs"]), 1)
            self.assertEqual(j["source_sha"], SHA)

    def test_crash_has_no_silent_retry(self):
        with patch.object(mod, "_execute", side_effect=RuntimeError("boom")) as exe:
            self.job()
            self.assertEqual(mod.tick()["status"], "BLOCKED")
            self.assertEqual(mod.tick()["status"], "IDLE")
            self.assertEqual(exe.call_count, 1)

    def test_stale_running_does_not_auto_resume(self):
        j = self.job()
        mod.write_json(mod._task_state(j), {"status": "RUNNING"})
        with patch.object(mod, "_execute") as exe:
            self.assertEqual(mod.tick()["status"], "IDLE")
            exe.assert_not_called()

    def test_reject_arbitrary_job_kind(self):
        with self.assertRaises(ValueError):
            mod.approve("shell_command", SHA)

    def test_hpo_requires_explicit_gate_and_budget(self):
        with self.assertRaises(ValueError):
            mod.approve("v11_hpo", SHA)
        with self.assertRaises(ValueError):
            mod.approve("v11_hpo", SHA, hours=12)

    def test_block_on_wrong_machine(self):
        j = self.job()
        j["hostname"] = "NOT-THIS-HOST"
        mod.write_json(mod.QUEUE / (j["id"] + ".json"), j)
        with patch.object(mod, "_execute") as exe:
            self.assertEqual(mod.tick()["status"], "BLOCKED")
            exe.assert_not_called()

    def test_block_when_pinned_source_changed(self):
        j = self.job()
        with patch.object(mod, "check_source", side_effect=RuntimeError("source drift")):
            with patch.object(mod, "_execute") as exe:
                self.assertEqual(mod.tick()["status"], "BLOCKED")
                exe.assert_not_called()

    def test_stage0_checks_are_not_inferred(self):
        private = self.root / "_local"
        private.mkdir()
        receipt = private / "stage0.json"
        receipt.write_text(json.dumps({
            "schema": "v11-cuifa-stage0-receipt-v1", "source_sha": SHA,
            "hostname": socket.gethostname(), "gpu_name": "NVIDIA GeForce RTX 4070 Ti SUPER",
            "checks": {"cuda": "PASS"}, "evidence": []
        }), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Stage0 has not passed"):
            mod.stage0_receipt(receipt, SHA, 12)

    def test_hpo_dispatch_never_auto_advances(self):
        j = self.job()
        j["kind"] = "v11_hpo"
        j["max_gpu_hours"] = 12
        j["stage0_receipt"] = "fixture"
        j["stage0_sha256"] = "b" * 64
        mod.write_json(mod.QUEUE / (j["id"] + ".json"), j)
        with patch.object(mod, "stage0_receipt", return_value="b" * 64):
            with patch.object(mod, "_execute", return_value=0) as exe:
                self.assertEqual(mod.tick()["status"], "NEEDS_DECISION")
                self.assertEqual(exe.call_count, 1)
                self.assertEqual(mod.tick()["status"], "IDLE")

    def test_lock_rejects_parallel_tick(self):
        lock, unlock = mod._exclusive_lock()
        try:
            with self.assertRaisesRegex(RuntimeError, "active"):
                mod.tick()
        finally:
            unlock()
            lock.close()


if __name__ == "__main__":
    unittest.main()
