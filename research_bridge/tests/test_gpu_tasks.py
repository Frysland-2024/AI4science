"""Offline GPU bridge contract tests; no CUDA training or GitHub calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_bridge import gpu_tasks as g
from research_bridge import worker as w

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "pxrd_autolab/configs/forward_ab_pilot.json"


def make_task(**options):
    config_sha = hashlib.sha256((ROOT / CONFIG).read_bytes()).hexdigest()
    body = {"preset": "forward_ab", "approved_sha": "f" * 40,
            "config": CONFIG, "config_sha256": config_sha, "run_id": "pilot_001"}
    body.update(options)
    return {"number": 100, "state": "open", "title": "[Bridge GPU] Approved A/B run",
            "user": {"login": w.OWNER}, "body": json.dumps(body),
            "labels": [{"name": w.READY}, {"name": g.LABEL}]}


def write_artifacts(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "run_manifest.json").write_text('{"status":"BLOCKED"}\n', encoding="utf-8")
    (directory / "gate_report.json").write_text('{"status":"BLOCKED_MISSING_EVIDENCE"}\n', encoding="utf-8")
    (directory / "metrics.json").write_text('{"status":"BLOCKED_MISSING_IMPLEMENTATION","metrics":{}}\n', encoding="utf-8")
    (directory / "TECHNICAL_REPORT.md").write_text("# Blocked\n\nNo training started.\n", encoding="utf-8")


class GPUContractTests(unittest.TestCase):
    def test_owner_and_two_label_gate(self):
        issue = make_task()
        self.assertTrue(g.eligible(issue))
        self.assertFalse(g.eligible({**issue, "user": {"login": "other"}}))
        self.assertFalse(g.eligible({**issue, "labels": [{"name": g.LABEL}]}))
        self.assertFalse(g.eligible({**issue, "labels": issue["labels"] + [{"name": w.APPROVED}]}))
        self.assertFalse(g.eligible({**issue, "title": "[Bridge] not GPU"}))

    def test_strict_schema_has_no_time_limit_or_extras(self):
        self.assertEqual(set(g.parse(make_task())), g.FIELDS)
        for extra in ({"max_minutes": 45}, {"python": "C:/python.exe"}, {"command": ["whoami"]}):
            data = json.loads(make_task()["body"])
            data.update(extra)
            with self.subTest(extra=extra), self.assertRaises(w.BridgeError):
                g.parse({**make_task(), "body": json.dumps(data)})
        bad = '{"preset":"forward_ab","preset":"forward_ab"}'
        with self.assertRaises(w.BridgeError):
            g.parse({**make_task(), "body": bad})

    def test_rejects_bad_sha_paths_and_run_ids(self):
        for change in ({"approved_sha": "not-a-commit"},
                       {"config_sha256": "wrong"},
                       {"config": "../../secret.json"},
                       {"config": "pxrd_autolab/configs/other.json"},
                       {"run_id": "../../windows"},
                       {"preset": "arbitrary-shell"}):
            with self.subTest(change=change), self.assertRaises(w.BridgeError):
                g.parse(make_task(**change))

    def test_dry_run_does_not_fetch_or_train(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / ".git").mkdir()
            with patch.object(w, "revision") as rev, patch.object(w, "snapshot") as snap:
                g.run(repo, make_task(), dry_run=True)
                rev.assert_not_called()
                snap.assert_not_called()

    def test_only_registered_entrypoints_are_dispatchable(self):
        self.assertEqual(g.PRESETS["forward_ab"]["entry"], "pxrd_autolab/run.py")
        self.assertEqual(g.PRESETS["forward_speed_benchmark"]["entry"],
                         "pxrd_autolab/benchmark_gpu.py")
        self.assertFalse(any(item["entry"].startswith("xrd_robustness/")
                             for item in g.PRESETS.values()))

    def test_launch_has_no_timeout_shell_or_issue_command_and_stop_kills_tree(self):
        class FakeProcess:
            pid = 1234
            returncode = None
            def poll(self):
                return None
            def wait(self, timeout=None):
                self.returncode = -9
                return self.returncode
            def kill(self):
                self.returncode = -9

        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            out.mkdir()
            stop = out / "STOP"
            stop.touch()
            with patch.object(g.subprocess, "Popen", return_value=FakeProcess()) as popen, \
                 patch.object(g, "_terminate_tree") as terminate:
                code, stopped = g._run_process(["trusted-python", "trusted-script.py"],
                                                cwd=Path(temp), out=out, stop_path=stop,
                                                env={}, poll_interval=0)
            self.assertTrue(stopped)
            self.assertEqual(code, -9)
            terminate.assert_called_once_with(1234)
            args, kwargs = popen.call_args
            self.assertEqual(args[0], ["trusted-python", "trusted-script.py"])
            self.assertIs(kwargs["shell"], False)
            self.assertNotIn("timeout", kwargs)

    def test_failure_terminates_process_tree(self):
        class FinishedProcess:
            pid = 1235
            returncode = 7
            def poll(self):
                return 7

        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "run"
            out.mkdir()
            with patch.object(g.subprocess, "Popen", return_value=FinishedProcess()), \
                 patch.object(g, "_terminate_tree") as terminate:
                code, stopped = g._run_process(["python", "run.py"], cwd=Path(temp), out=out,
                                               stop_path=out / "STOP", env={})
            self.assertEqual(code, 7)
            self.assertFalse(stopped)
            terminate.assert_called_once_with(1235)

    def test_blocked_nonzero_run_still_attempts_auto_publication(self):
        sha = "f" * 40
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / ".git").mkdir()

            def snapshot(_root, workspace, _commit):
                workspace.mkdir(parents=True)
                config_path = workspace / CONFIG
                config_path.parent.mkdir(parents=True)
                config_path.write_bytes((ROOT / CONFIG).read_bytes())
                entry = workspace / "pxrd_autolab/run.py"
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_text("# approved runner\n", encoding="utf-8")

            def run_blocked(_cmd, *, cwd, out, stop_path, env, poll_interval=g.STOP_POLL_SECONDS):
                write_artifacts(out)
                return 3, False

            published = {"status": "PUSHED_DRAFT_PR", "branch": "bridge-results/pilot_001",
                         "pull_request": "https://github.com/Frysland-2024/AI4science/pull/200"}
            with patch.object(w, "revision", return_value=sha), \
                 patch.object(w, "snapshot", side_effect=snapshot), \
                 patch.object(w, "command", return_value="abc123blob"), \
                 patch.object(g, "_run_python", return_value="C:/approved/python.exe"), \
                 patch.object(g, "_run_process", side_effect=run_blocked), \
                 patch.object(g, "publish_results", return_value=published) as publish, \
                 patch.object(w, "label"), patch.object(w, "comment"):
                result = g.run(repo, make_task(), dry_run=False)
            self.assertEqual(result["run_status"], "BLOCKED_MISSING_IMPLEMENTATION")
            self.assertEqual(result["return_code"], 3)
            publish.assert_called_once()
            manifest = json.loads((w.git_common_dir(repo) / "research_bridge/gpu_runs/pilot_001/run_manifest.json").read_text())
            self.assertEqual(manifest["source_commit"], sha)
            self.assertEqual(manifest["config_sha256"], g.parse(make_task())["config_sha256"])

    def test_publication_failure_is_recorded_and_reported(self):
        sha = "f" * 40
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / ".git").mkdir()

            def snapshot(_root, workspace, _commit):
                workspace.mkdir(parents=True)
                config_path = workspace / CONFIG
                config_path.parent.mkdir(parents=True)
                config_path.write_bytes((ROOT / CONFIG).read_bytes())
                entry = workspace / "pxrd_autolab/run.py"
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_text("# approved runner\n", encoding="utf-8")

            def run_blocked(_cmd, *, cwd, out, stop_path, env, poll_interval=g.STOP_POLL_SECONDS):
                write_artifacts(out)
                return 3, False

            comments = []
            with patch.object(w, "revision", return_value=sha), \
                 patch.object(w, "snapshot", side_effect=snapshot), \
                 patch.object(w, "command", return_value="abc123blob"), \
                 patch.object(g, "_run_python", return_value="C:/approved/python.exe"), \
                 patch.object(g, "_run_process", side_effect=run_blocked), \
                 patch.object(g, "publish_results", side_effect=w.BridgeError("push rejected")), \
                 patch.object(w, "label"), \
                 patch.object(w, "comment", side_effect=lambda _number, message: comments.append(message)):
                result = g.run(repo, make_task(), dry_run=False)

            self.assertEqual(result["run_status"], "BLOCKED_MISSING_IMPLEMENTATION")
            self.assertEqual(result["publication_error"], "push rejected")
            journal = json.loads(w.journal(repo, 100).read_text(encoding="utf-8"))
            self.assertEqual(journal["status"], "GPU_PUBLICATION_FAILED")
            self.assertTrue((w.git_common_dir(repo) / "research_bridge/gpu_runs/pilot_001/publication.json").is_file())
            self.assertIn("did not fully complete", comments[0])

    def test_public_export_uses_allowlist_redacts_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            write_artifacts(out)
            (out / "metrics.json").write_text(
                '{"status":"PASS","token":"github_pat_abcdefghijklmnopqrstuvwxyz123456",'
                '"authorization":"Bearer abcdefghijklmnopqrstuvwxyz123456",'
                '"api_key":"local-secret-value","path":"E:\\\\private\\\\run",'
                '"slash_path":"C:/private/run/output","url":"https://example.org/results"}\n',
                encoding="utf-8")
            (out / "raw.npy").write_bytes(b"private sample array")
            files = g._public_artifacts(out)
            self.assertEqual(set(files), set(g.REQUIRED_RESULT_FILES))
            public = files["metrics.json"].decode("utf-8")
            cleaned_metrics = json.loads(public)
            self.assertNotIn("github_pat_", public)
            self.assertNotIn("Bearer abcdefghijklmnopqrstuvwxyz", public)
            self.assertNotIn("private", public)
            self.assertEqual(cleaned_metrics["api_key"], "[REDACTED]")
            self.assertEqual(cleaned_metrics["url"], "https://example.org/results")
            original = Path.is_symlink
            def simulated_symlink(path):
                return path.name == "test_summary.json" or original(path)
            with patch.object(Path, "is_symlink", autospec=True, side_effect=simulated_symlink), \
                 self.assertRaises(w.BridgeError):
                g._public_artifacts(out)

    def test_public_export_enforces_size_caps(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            write_artifacts(out)
            (out / "TECHNICAL_REPORT.md").write_bytes(b"x" * (g.MAX_RESULT_FILE_BYTES + 1))
            with self.assertRaises(w.BridgeError):
                g._public_artifacts(out)

    def test_git_publication_is_mocked_source_based_and_draft_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            root.mkdir()
            out = Path(temp) / "out"
            write_artifacts(out)
            git_calls = []

            def fake_git(args, cwd):
                git_calls.append((args, Path(cwd)))
                if args[0] == "clone":
                    Path(args[-1]).mkdir()
                if args[0] == "rev-parse":
                    return "a" * 40
                return ""

            with patch.object(w, "command", return_value="https://github.com/Frysland-2024/AI4science.git"), \
                 patch.object(g, "_git", side_effect=fake_git), \
                 patch.object(w, "gh", return_value="https://github.com/Frysland-2024/AI4science/pull/201") as gh:
                result = g.publish_results(root, out, run_id="pilot_001",
                                            source_commit="f" * 40,
                                            run_status="BLOCKED_MISSING_EVIDENCE")
            self.assertEqual(result["status"], "PUSHED_DRAFT_PR")
            self.assertIn(("fetch", "--no-tags", "origin", "f" * 40),
                          [tuple(call[0]) for call in git_calls])
            push = next(call[0] for call in git_calls if call[0][0] == "push")
            self.assertEqual(push[-1], "HEAD:refs/heads/bridge-results/pilot_001")
            self.assertTrue(any(call[0][:2] == ["switch", "-c"] for call in git_calls))
            pr_args = gh.call_args.args[0]
            self.assertIn("--draft", pr_args)
            self.assertNotIn("--merge", pr_args)

    def test_linked_worktree_resolves_common_git_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            root = temp / "wt"
            root.mkdir()
            gitdir = temp / "common" / "worktrees" / "wt"
            gitdir.mkdir(parents=True)
            (gitdir / "commondir").write_text("../..", encoding="utf-8")
            (root / ".git").write_text("gitdir: ../common/worktrees/wt", encoding="utf-8")
            self.assertEqual(w.git_common_dir(root), (temp / "common").resolve())

    def test_no_120_minute_or_scheduler_kill_limit_remains(self):
        source = (ROOT / "research_bridge/gpu_tasks.py").read_text(encoding="utf-8")
        scheduler = (ROOT / "research_bridge/register_windows_task.ps1").read_text(encoding="utf-8")
        self.assertNotIn("MAX_MINUTES", source)
        self.assertNotIn("-Minutes 135", scheduler)
        self.assertIn("-Seconds 0", scheduler)


if __name__ == "__main__":
    unittest.main()
