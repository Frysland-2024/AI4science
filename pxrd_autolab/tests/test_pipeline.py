from __future__ import annotations

import json
from pathlib import Path

from pxrd_autolab.run import run_pipeline


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_CONFIG = PACKAGE_ROOT / "configs" / "fixture_smoke.json"


def _write_recorded_config(path: Path, inputs: dict[str, str]) -> Path:
    value = {
        "schema_version": "pxrd-autolab-p0-v1",
        "run_name": "test-recorded-input",
        "mode": "recorded_report",
        "data_role": "test only",
        "claim_scope": "test only",
        "budget": {"max_steps": 0, "max_seconds": 60},
        "execution": {"planned_steps": 0},
        "inputs": inputs,
    }
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_fixture_report_creates_unique_reviewable_run_dirs(tmp_path: Path) -> None:
    statuses_and_dirs = [
        run_pipeline(
            FIXTURE_CONFIG,
            repo_root=REPO_ROOT,
            runs_root=tmp_path / "runs",
        )
        for _ in range(2)
    ]
    assert [status for status, _ in statuses_and_dirs] == [
        "AWAITING_REVIEW",
        "AWAITING_REVIEW",
    ]
    run_dirs = [path for _, path in statuses_and_dirs]
    assert run_dirs[0] != run_dirs[1]
    for run_dir in run_dirs:
        assert (run_dir / "config.raw.json").is_file()
        assert (run_dir / "config_frozen.json").is_file()
        assert (run_dir / "run.log").is_file()
        assert (run_dir / "events.jsonl").is_file()
        assert (run_dir / "report.md").is_file()
        assert (run_dir / "biweekly_brief.md").is_file()
        assert (run_dir / "figures" / "ab_metrics.png").is_file()
        assert (run_dir / "figures" / "loss_curves.png").is_file()
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["status"] == "AWAITING_REVIEW"
        assert manifest["artifacts"]["report.md"]
        assert json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))["status"] == "PIPELINE_FIXTURE_ONLY"


def test_missing_recorded_input_fails_closed_with_run_record(tmp_path: Path) -> None:
    config = _write_recorded_config(
        tmp_path / "missing.json",
        {
            "results_json": "missing/results.json",
            "forward_gate_json": "missing/gate.json",
            "lambda_selection_json": "missing/lambda.json",
            "training_histories_json": "missing/history.json",
            "pilot_manifest_json": "missing/manifest.json",
        },
    )
    status, run_dir = run_pipeline(
        config,
        repo_root=REPO_ROOT,
        input_root=tmp_path,
        runs_root=tmp_path / "runs",
    )
    assert status == "FAILED"
    assert json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["state"] == "FAILED"
    assert "required input file is missing" in json.loads(
        (run_dir / "failure.json").read_text(encoding="utf-8")
    )["error"]


def test_missing_config_also_creates_failure_record(tmp_path: Path) -> None:
    status, run_dir = run_pipeline(
        tmp_path / "absent.json",
        repo_root=REPO_ROOT,
        runs_root=tmp_path / "runs",
    )
    assert status == "FAILED"
    assert json.loads((run_dir / "state.json").read_text(encoding="utf-8"))["state"] == "FAILED"
    assert "absent.json" in json.loads(
        (run_dir / "failure.json").read_text(encoding="utf-8")
    )["error"]


def test_failed_forward_gate_blocks_report_generation(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    names = {
        "results_json": "results.json",
        "forward_gate_json": "gate.json",
        "lambda_selection_json": "lambda.json",
        "training_histories_json": "history.json",
        "pilot_manifest_json": "manifest.json",
    }
    for name, filename in names.items():
        (evidence / filename).write_text(
            json.dumps({"passed": False} if name == "forward_gate_json" else {}),
            encoding="utf-8",
        )
    config = _write_recorded_config(tmp_path / "gate.json", names)
    status, run_dir = run_pipeline(
        config,
        repo_root=REPO_ROOT,
        input_root=evidence,
        runs_root=tmp_path / "runs",
    )
    assert status == "BLOCKED"
    assert "forward numerical gate did not pass" in json.loads(
        (run_dir / "failure.json").read_text(encoding="utf-8")
    )["error"]
    assert not (run_dir / "report.md").exists()


def test_nonzero_step_request_is_blocked_before_any_work(tmp_path: Path) -> None:
    value = json.loads(FIXTURE_CONFIG.read_text(encoding="utf-8"))
    value["execution"]["planned_steps"] = 1
    config = tmp_path / "over_budget.json"
    config.write_text(json.dumps(value), encoding="utf-8")
    status, run_dir = run_pipeline(
        config,
        repo_root=REPO_ROOT,
        runs_root=tmp_path / "runs",
    )
    assert status == "BLOCKED"
    assert "planned_steps" in json.loads(
        (run_dir / "failure.json").read_text(encoding="utf-8")
    )["error"]
    assert not (run_dir / "metrics.json").exists()
