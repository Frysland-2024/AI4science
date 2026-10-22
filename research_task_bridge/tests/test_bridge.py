from __future__ import annotations

import copy
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from research_task_bridge import bridge as bridge_module
from research_task_bridge.bridge import (
    Bridge,
    ExecutionResult,
    Executor,
    GitHubIssues,
    Task,
    create_issue_body,
    normalize_repo_url,
    redact,
    risk_reason,
)


def issue(number: int, *, action: str = "codex_read_only", scope: str = "docs", request: str = "Summarize the workflow docs.", labels: tuple[str, ...] = ("research-task", "rtb:ready")) -> dict:
    return {
        "number": number,
        "title": f"[research-task] Example {number}",
        "url": f"https://github.com/example/repo/issues/{number}",
        "body": create_issue_body(action, scope, request),
        "labels": [{"name": label} for label in labels],
        "state": "OPEN",
        "createdAt": "2026-10-18T00:00:00Z",
        "updatedAt": "2026-10-18T00:00:00Z",
        "comments": [],
    }


class MemoryIssues:
    def __init__(self, rows: list[dict]):
        self.rows = {int(row["number"]): copy.deepcopy(row) for row in rows}

    def list_tasks(self) -> list[dict]:
        return copy.deepcopy(list(self.rows.values()))

    def get_issue(self, number: int) -> dict:
        return copy.deepcopy(self.rows[number])

    def set_state(self, number: int, state: str) -> None:
        row = self.rows[number]
        labels = {item["name"] for item in row["labels"]}
        labels = {label for label in labels if not label.startswith("rtb:")}
        labels.add(state)
        row["labels"] = [{"name": name} for name in sorted(labels)]

    def comment(self, number: int, body: str) -> None:
        self.rows[number]["comments"].append({
            "body": body,
            "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })


class FakeExecutor:
    def __init__(self, result: ExecutionResult | None = None):
        self.result = result or ExecutionResult(True, "Read-only summary from the fake Codex runner.", log_path="C:/logs/issue.log")
        self.calls: list[tuple[Task, int, str]] = []

    def execute(self, task: Task, attempt: int, commit: str) -> ExecutionResult:
        self.calls.append((task, attempt, commit))
        return self.result


class ResearchTaskBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "bridge-test@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Bridge Test"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("bridge test fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "test fixture"], cwd=self.repo, check=True, capture_output=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_bridge(self, row: dict, executor: FakeExecutor | None = None) -> tuple[Bridge, MemoryIssues, FakeExecutor]:
        issues = MemoryIssues([row])
        fake_executor = executor or FakeExecutor()
        bridge = Bridge("example/repo", issues=issues, executor=fake_executor, repo_path=self.repo)
        return bridge, issues, fake_executor

    def test_form_round_trip_and_fingerprint(self) -> None:
        parsed = Task.from_issue(issue(1, request="Review the AutoLab plan."))
        self.assertEqual(parsed.action, "codex_read_only")
        self.assertEqual(parsed.scope, "docs")
        self.assertEqual(len(parsed.fingerprint), 64)
        self.assertEqual(normalize_repo_url("https://github.com/Frysland-2024/AI4science.git"), "Frysland-2024/AI4science")

    def test_request_markdown_headings_are_preserved(self) -> None:
        parsed = Task.from_issue(issue(10, request="Review these parts:\n\n### Acceptance criteria\nCite each source."))
        self.assertIn("### Acceptance criteria", parsed.request)
        self.assertIn("Cite each source.", parsed.request)

    def test_github_issue_content_uses_stdin_not_command_arguments(self) -> None:
        observed: list[dict] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            observed.append({"command": command, **kwargs})
            return subprocess.CompletedProcess(command, 0, "https://github.com/example/repo/issues/11", "")

        client = GitHubIssues("example/repo", runner=fake_run)
        body = create_issue_body("codex_read_only", "docs", "Review this documentation.")
        client.create("Safe title", body)
        self.assertIn("--body-file", observed[0]["command"])
        self.assertNotIn(body, observed[0]["command"])
        self.assertEqual(observed[0]["input"], body)

    def test_success_posts_commit_log_and_review_state(self) -> None:
        bridge, issues, executor = self.make_bridge(issue(2))
        result = bridge.once()
        row = issues.rows[2]
        labels = {item["name"] for item in row["labels"]}
        feedback = "\n".join(comment["body"] for comment in row["comments"])
        self.assertIn("awaiting_research_review", result)
        self.assertIn("rtb:review", labels)
        self.assertIn("AWAITING_RESEARCH_REVIEW", feedback)
        self.assertIn("Commit:", feedback)
        self.assertIn("C:/logs/issue.log", feedback)
        self.assertEqual(len(executor.calls), 1)

    def test_high_risk_request_is_held_without_execution(self) -> None:
        bridge, issues, executor = self.make_bridge(issue(3, request="Run a GPU formal training experiment on the test set."))
        result = bridge.once()
        labels = {item["name"] for item in issues.rows[3]["labels"]}
        self.assertIn("blocked approval", result)
        self.assertIn("rtb:blocked-approval", labels)
        self.assertEqual(executor.calls, [])

    def test_explicit_approval_required_action_is_held(self) -> None:
        bridge, issues, executor = self.make_bridge(issue(4, action="requires_user_approval"))
        bridge.once()
        self.assertIn("rtb:blocked-approval", {item["name"] for item in issues.rows[4]["labels"]})
        self.assertEqual(executor.calls, [])

    def test_active_duplicate_is_not_executed(self) -> None:
        first = issue(5, labels=("research-task", "rtb:review"))
        second = issue(6)
        issues = MemoryIssues([first, second])
        executor = FakeExecutor()
        bridge = Bridge("example/repo", issues=issues, executor=executor, repo_path=self.repo)
        result = bridge.once()
        self.assertIn("duplicate #6 of #5", result)
        self.assertIn("rtb:duplicate", {item["name"] for item in issues.rows[6]["labels"]})
        self.assertEqual(executor.calls, [])

    def test_retry_limit_is_enforced(self) -> None:
        row = issue(7)
        fingerprint = Task.from_issue(row).fingerprint
        row["comments"] = [
            {"body": f"<!-- rtb-run-start attempt={attempt} fingerprint={fingerprint} -->", "createdAt": "2026-10-18T00:00:00Z"}
            for attempt in (1, 2)
        ]
        bridge, issues, executor = self.make_bridge(row)
        self.assertIn("retry limit", bridge.once())
        self.assertIn("rtb:failed", {item["name"] for item in issues.rows[7]["labels"]})
        self.assertEqual(executor.calls, [])

    def test_changed_task_after_attempt_requires_new_issue(self) -> None:
        row = issue(12, request="Original bounded request.")
        fingerprint = Task.from_issue(row).fingerprint
        row["comments"] = [{
            "body": f"<!-- rtb-run-start attempt=1 fingerprint={fingerprint} -->",
            "createdAt": "2026-10-18T00:00:00Z",
        }]
        row["body"] = create_issue_body("codex_read_only", "docs", "Changed request after failure.")
        bridge, issues, executor = self.make_bridge(row)
        self.assertIn("blocked modified task", bridge.once())
        self.assertIn("rtb:blocked-approval", {item["name"] for item in issues.rows[12]["labels"]})
        self.assertEqual(executor.calls, [])

    def test_stale_run_is_requeued_with_audit_comment(self) -> None:
        row = issue(8, labels=("research-task", "rtb:running"))
        fingerprint = Task.from_issue(row).fingerprint
        row["comments"] = [{
            "body": f"<!-- rtb-run-start attempt=1 fingerprint={fingerprint} -->",
            "createdAt": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        }]
        bridge, issues, executor = self.make_bridge(row)
        self.assertEqual(bridge.once(), "idle: no ready tasks")
        self.assertIn("rtb:ready", {item["name"] for item in issues.rows[8]["labels"]})
        self.assertIn("Previous worker stopped", issues.rows[8]["comments"][-1]["body"])
        self.assertEqual(executor.calls, [])

    def test_codex_executor_is_sandboxed_and_snapshot_excludes_results(self) -> None:
        (self.repo / "AGENTS.md").write_text("rules\n", encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "RESEARCH_WORKFLOW.md").write_text("workflow\n", encoding="utf-8")
        (self.repo / "docs" / "PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md").write_text("plan\n", encoding="utf-8")
        (self.repo / "xrd_inversion" / "src" / "pkg").mkdir(parents=True)
        (self.repo / "xrd_inversion" / "src" / "pkg" / "module.py").write_text("value = 1\n", encoding="utf-8")
        (self.repo / "xrd_inversion" / "tests").mkdir()
        (self.repo / "xrd_inversion" / "tests" / "test_private.py").write_text("test data\n", encoding="utf-8")
        (self.repo / "xrd_inversion" / "reports").mkdir()
        (self.repo / "xrd_inversion" / "reports" / "result.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "add", "AGENTS.md", "docs", "xrd_inversion"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "add snapshot fixtures"], cwd=self.repo, check=True, capture_output=True)
        observed: dict[str, object] = {}

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            observed["command"] = command
            observed["prompt"] = kwargs["input"]
            snapshot = Path(command[command.index("--cd") + 1])
            observed["snapshot_files"] = {path.relative_to(snapshot).as_posix() for path in snapshot.rglob("*") if path.is_file()}
            output_file = Path(command[command.index("--output-last-message") + 1])
            output_file.write_text("Reviewed docs. access_token=placeholder-value should be redacted.", encoding="utf-8")
            env = kwargs["env"]
            observed["cuda"] = env.get("CUDA_VISIBLE_DEVICES")  # type: ignore[union-attr]
            observed["env_keys"] = set(env)  # type: ignore[arg-type]
            return subprocess.CompletedProcess(command, 0, "", "")

        local_state = self.repo / "local-state"
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-never-log", "OPENAI_API_KEY": "test-key-never-log"}):
            with patch.object(bridge_module, "_appdata", return_value=local_state):
                result = Executor(self.repo, codex_executable="codex-test", runner=fake_run).execute(
                    Task.from_issue(issue(9)), 1, "abc123"
                )
        command = observed["command"]
        files = observed["snapshot_files"]
        self.assertIn("--sandbox", command)  # type: ignore[operator]
        self.assertEqual(command[command.index("--sandbox") + 1], "read-only")  # type: ignore[union-attr]
        self.assertEqual(observed["cuda"], "")
        self.assertNotIn("GITHUB_TOKEN", observed["env_keys"])
        self.assertNotIn("OPENAI_API_KEY", observed["env_keys"])
        self.assertIn("docs/RESEARCH_WORKFLOW.md", files)  # type: ignore[operator]
        self.assertNotIn("xrd_inversion/tests/test_private.py", files)  # type: ignore[operator]
        self.assertNotIn("xrd_inversion/reports/result.json", files)  # type: ignore[operator]
        self.assertNotIn("placeholder-value", result.summary)
        self.assertTrue(Path(result.log_path).is_file())
        self.assertNotIn("placeholder-value", Path(result.log_path).read_text(encoding="utf-8"))

    def test_risk_gate_and_secret_redaction(self) -> None:
        self.assertIsNotNone(risk_reason("Use the held-out test set to compare checkpoints."))
        self.assertIsNotNone(risk_reason("Use the test data to compare checkpoints."))
        self.assertIsNotNone(risk_reason("CUDA formal experiment"))
        self.assertEqual(redact("access_token=placeholder-value"), "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
