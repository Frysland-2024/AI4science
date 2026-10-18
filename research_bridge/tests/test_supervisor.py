"""No network or model calls. Simulates states, outages, restart and stale workers."""
import datetime as dt
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_bridge import evidence, events, recovery, supervisor as s
from research_bridge import worker as w

NOW = 1792368000.0

def iso(seconds):
    return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat()

def repo(tmp):
    root = Path(tmp)
    (root / ".git").mkdir(exist_ok=True)
    return root

def write_issue(root, num, status, seconds=NOW, **fields):
    p = root / ".git" / "research_bridge" / ("issue-%d.json" % num)
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps({"issue": num, "status": status,
                             "updated_utc": iso(seconds), **fields}), encoding="utf-8")
    return p

class SupervisorTests(unittest.TestCase):
    def test_stale_alive_process_is_uncertain_not_failed(self):
        reg = {"pid": 333, "process_started_epoch": 100}
        raw = {"status": "RUNNING", "updated_utc": iso(NOW-900)}
        self.assertEqual(s.observe(reg, raw, now=NOW, birth_probe=lambda _: 100)[0],
                         "STALE_UNCERTAIN")

    def test_pid_reuse_mismatch_is_uncertain(self):
        reg = {"pid": 333, "process_started_epoch": 100}
        raw = {"status": "RUNNING", "updated_utc": iso(NOW)}
        self.assertEqual(s.observe(reg, raw, now=NOW, birth_probe=lambda _: 200)[0],
                         "STALE_UNCERTAIN")

    def test_dead_process_is_uncertain_not_restarted(self):
        reg = {"pid": 333, "process_started_epoch": 100}
        self.assertEqual(s.observe(reg, {"status": "RUNNING",
                         "updated_utc": iso(NOW)}, now=NOW,
                         birth_probe=lambda _: None)[0], "STALE_UNCERTAIN")

    def test_recent_heartbeat_overrides_old_initial_journal(self):
        reg = {"job_id": "bridge-1"}
        raw = {"status": "GPU_RUNNING", "updated_utc": iso(NOW-4000),
               "heartbeat": {"updated_utc": iso(NOW-20)}}
        self.assertEqual(s.observe(reg, raw, now=NOW), ("RUNNING", "NONE"))

    def test_missing_report_is_not_scientific_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(evidence.inspect_run(Path(tmp))["status"], "INCOMPLETE")

    def test_complete_synthetic_metadata_still_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for name,obj in [("run_manifest.json",{"source_commit":"a"*40}),
                             ("gate_report.json",{"status":"PASS"}),
                             ("metrics.json",{"accuracy":0.5})]:
                (p/name).write_text(json.dumps(obj),encoding="utf-8")
            data = evidence.inspect_run(p)
            self.assertEqual(data["status"], "COMPLETED_UNREVIEWED")
            self.assertFalse(data["scientifically_reviewed"])
            self.assertEqual(len(data["files"]), 3)

    def test_gate_fail_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name,d in [("run_manifest.json",{}),("gate_report.json",{"status":"BLOCKED_GATE"}),
                           ("metrics.json",{})]:
                (p/name).write_text(json.dumps(d), encoding="utf-8")
            self.assertEqual(evidence.inspect_run(p)["status"], "BLOCKED")

    def test_bootstrap_ignores_preexisting_journals(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            write_issue(root,15,"REVIEW")
            report=s.run_once(root,dry_run=True)
            self.assertEqual(report["status"], "BOOTSTRAP_REQUIRED")
            self.assertFalse((root/".git"/"research_bridge"/"supervisor_v1").exists())
            s.bootstrap(root)
            write_issue(root,23,"GPU_RUNNING")
            with patch.object(events,"flush",return_value={"delivered":0}):
                result=s.run_once(root)
            self.assertEqual(result["observed_jobs"],1)
            self.assertEqual(result["new_events"],1)
            self.assertEqual(result["transitions"][0]["issue"],23)

    def test_repeated_check_does_not_spam(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            s.bootstrap(root)
            write_issue(root,24,"REVIEW")
            with patch.object(events,"flush",return_value={"delivered":0}):
                first=s.run_once(root)
                second=s.run_once(root)
            self.assertEqual(first["new_events"],1)
            self.assertEqual(second["new_events"],0)

    def test_dry_run_has_no_disk_or_network_side_effect(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            s.bootstrap(root)
            write_issue(root,25,"RUNNING")
            with patch.object(events,"enqueue") as queue, \
                 patch.object(events,"flush") as publish:
                result=s.run_once(root,dry_run=True)
                self.assertEqual(result["new_events"],1)
                queue.assert_not_called()
                publish.assert_not_called()

    def test_offline_delivery_persists_and_avoids_duplicates(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            self.assertTrue(events.enqueue(root,job_id="bridge-28",issue=28,status="RUNNING"))
            self.assertFalse(events.enqueue(root,job_id="bridge-28",issue=28,status="RUNNING"))
            with patch.object(w,"gh",side_effect=w.BridgeError("offline")):
                self.assertEqual(events.flush(root)["pending"],1)
            with patch.object(w,"gh",return_value="[]"), patch.object(w,"comment") as posted:
                self.assertEqual(events.flush(root)["delivered"],1)
                self.assertEqual(posted.call_count,1)
            with patch.object(w,"comment") as posted:
                self.assertEqual(events.flush(root)["delivered"],0)
                posted.assert_not_called()

    def test_ack_lost_remote_marker_prevents_second_comment(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            events.enqueue(root,job_id="bridge-29",issue=29,status="FAILED",reason="UNKNOWN")
            with patch.object(w,"gh",return_value="[]"), \
                 patch.object(w,"comment",side_effect=w.BridgeError("after post")):
                self.assertEqual(events.flush(root)["pending"],1)
            eid=events.event_key("bridge-29",29,"FAILED","UNKNOWN")
            with patch.object(w,"gh",return_value=json.dumps([{
                    "body":"<!-- research-supervisor:"+eid+" -->"}])), \
                 patch.object(w,"comment") as comment:
                self.assertEqual(events.flush(root)["delivered"],1)
                comment.assert_not_called()

    def test_real_gpu_runner_terminal_states(self):
        self.assertEqual(s.observe({}, {"status":"GPU_SUCCESS"})[0], "REVIEW_PENDING")
        self.assertEqual(s.observe({}, {"status":"GPU_BLOCKED_PHYSICS"})[0], "BLOCKED")
        self.assertEqual(s.observe({}, {"status":"GPU_PUBLICATION_FAILED"})[0], "FAILED")
        self.assertEqual(s.observe({}, {"status":"GPU_STOPPED"})[0], "STOPPED")

    def test_failure_categories(self):
        self.assertEqual(s.classify_failure("CUDA out of memory"),"CUDA_OOM")
        self.assertEqual(s.classify_failure("ModuleNotFoundError"),"MISSING_DEPENDENCY")
        self.assertEqual(s.classify_failure("physics gate failed"),"SCIENTIFIC_GATE_FAIL")
        self.assertEqual(s.classify_failure("unexpected stack"),"UNKNOWN")

    def test_resume_is_always_manual_even_complete_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/"checkpoint.bin"
            file.write_bytes(b"model")
            sha=hashlib.sha256(b"model").hexdigest()
            record={"source_sha":"a"*40,"config_sha256":sha,"split_sha256":sha,
                    "checkpoint_sha256":sha,"optimizer_sha256":sha,"rng_sha256":sha,
                    "completed_step":5,"total_steps":10,"approved_budget_steps":10,
                    "seed":1,"attempt":0}
            plan=recovery.assess_resume(record,file)
            self.assertFalse(plan["resume_allowed"])
            self.assertTrue(plan["validated_checkpoint"])
            self.assertEqual(plan["reason"],"MANUAL_APPROVAL_REQUIRED")

    def test_external_registration_requires_known_pid_birth(self):
        with tempfile.TemporaryDirectory() as td:
            root=repo(td)
            with patch.object(s,"process_birth",return_value=None):
                with self.assertRaises(ValueError):
                    s.register_external(root,issue=19,run_id="nuisance",pid=111)
            self.assertFalse((root/".git"/"research_bridge"/"supervisor_v1").exists())

if __name__ == "__main__":
    unittest.main()
