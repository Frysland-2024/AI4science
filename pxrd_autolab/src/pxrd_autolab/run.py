"""Fail-closed report-only runner for the first AutoLab increment."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import BudgetError, read_config, sha256_bytes, validate_config
from .reporting import (
    EvidenceError,
    aggregate_histories,
    load_json,
    normalize_fixture,
    read_recorded_metrics,
    verify_lambda_selection,
    write_reports,
)


class GateBlocked(RuntimeError):
    """A required protocol or physical gate did not pass."""


class BudgetBlocked(RuntimeError):
    """The configured work exceeds its explicit budget."""


class RunJournal:
    TRANSITIONS = {
        "CREATED": {"CONFIG_VALIDATED", "BLOCKED", "FAILED"},
        "CONFIG_VALIDATED": {"INPUTS_VALIDATED", "BLOCKED", "FAILED"},
        "INPUTS_VALIDATED": {"REPORTED", "BLOCKED", "FAILED"},
        "REPORTED": {"AWAITING_REVIEW", "FAILED"},
        "AWAITING_REVIEW": set(),
        "BLOCKED": set(),
        "FAILED": set(),
    }

    def __init__(self, run_dir: Path, run_id: str, logger: logging.Logger) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.logger = logger
        self.state = "CREATED"
        self._write_state("created")

    def transition(self, state: str, detail: str = "") -> None:
        if state not in self.TRANSITIONS.get(self.state, set()):
            raise RuntimeError(f"illegal run-state transition: {self.state} -> {state}")
        self.state = state
        self._write_state(detail)

    def _write_state(self, detail: str) -> None:
        event = {
            "at_utc": _utc_now(),
            "run_id": self.run_id,
            "state": self.state,
            "detail": detail,
        }
        with (self.run_dir / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
        _atomic_json(self.run_dir / "state.json", event)
        self.logger.info("state=%s %s", self.state, detail)


def run_pipeline(
    config_path: Path,
    *,
    repo_root: Path,
    input_root: Path | None = None,
    runs_root: Path | None = None,
    dry_run: bool = False,
    max_steps_override: int | None = None,
) -> tuple[str, Path]:
    config_path = config_path.resolve()
    repo_root = repo_root.resolve()
    input_root = (input_root or repo_root).resolve()
    runs_root = (runs_root or repo_root / "runs" / "pxrd_autolab").resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    config_error: Exception | None = None
    try:
        raw_config = config_path.read_bytes()
    except OSError as exc:
        raw_config = b""
        config_error = exc
    raw_digest = sha256_bytes(raw_config)
    config_value: dict[str, Any] | None = None
    canonical_digest = raw_digest
    if config_error is None:
        try:
            config_value, raw_digest, canonical_digest = read_config(config_path)
        except Exception as exc:
            config_error = exc
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{canonical_digest[:10]}-{uuid.uuid4().hex[:6]}"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    logger = _make_logger(run_dir)
    journal = RunJournal(run_dir, run_id, logger)
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "created_at_utc": _utc_now(),
        "status": "CREATED",
        "config_path_name": config_path.name,
        "config_raw_sha256": raw_digest,
        "config_canonical_sha256": canonical_digest,
        "git_commit": _git_value(repo_root, ["rev-parse", "HEAD"]),
        "git_dirty": _git_dirty(repo_root),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "mode": config_value.get("mode", "UNKNOWN") if config_value else "UNKNOWN",
        "data_role": config_value.get("data_role", "UNKNOWN") if config_value else "UNKNOWN",
        "input_root_commit": _git_value(input_root, ["rev-parse", "HEAD"]),
        "input_hashes": {},
        "artifacts": {},
        "budget": config_value.get("budget", {}) if config_value else {},
    }
    _atomic_json(run_dir / "manifest.json", manifest)
    (run_dir / "config.raw.json").write_bytes(raw_config)
    if config_value is not None:
        _atomic_json(run_dir / "config_frozen.json", config_value)

    started = time.monotonic()
    try:
        if config_error is not None:
            raise config_error
        assert config_value is not None
        validate_config(config_value)
        max_steps = int(config_value["budget"]["max_steps"])
        if max_steps_override is not None:
            if max_steps_override < 0:
                raise BudgetBlocked("--max-steps must be nonnegative")
            max_steps = min(max_steps, max_steps_override)
        planned_steps = int(config_value["execution"]["planned_steps"])
        if planned_steps > max_steps:
            raise BudgetBlocked(
                f"planned_steps ({planned_steps}) exceeds effective max_steps ({max_steps})"
            )
        journal.transition("CONFIG_VALIDATED", f"config sha256={canonical_digest}")
        _check_deadline(started, float(config_value["budget"]["max_seconds"]))

        if dry_run:
            manifest.update({"status": "CONFIG_VALIDATED", "dry_run": True})
            _atomic_json(run_dir / "manifest.json", manifest)
            return "CONFIG_VALIDATED", run_dir

        metrics, histories, input_hashes = _load_inputs(config_value, input_root)
        manifest["input_hashes"] = input_hashes
        _atomic_json(run_dir / "manifest.json", manifest)
        _check_deadline(started, float(config_value["budget"]["max_seconds"]))
        journal.transition("INPUTS_VALIDATED", "input files, forward gate, and recorded metrics verified")
        _check_deadline(started, float(config_value["budget"]["max_seconds"]))

        output_files = write_reports(
            run_dir,
            run_id,
            config_value,
            canonical_digest,
            metrics,
            histories,
            input_hashes,
        )
        for path in output_files:
            manifest["artifacts"][str(path.relative_to(run_dir)).replace("\\", "/")] = _sha256_file(path)
        _check_deadline(started, float(config_value["budget"]["max_seconds"]))
        journal.transition("REPORTED", "metrics and draft reports written")
        journal.transition("AWAITING_REVIEW", "human interpretation and approval required")
        manifest.update(
            {
                "status": "AWAITING_REVIEW",
                "completed_at_utc": _utc_now(),
                "elapsed_seconds": time.monotonic() - started,
                "artifacts": manifest["artifacts"],
                "input_hashes": input_hashes,
            }
        )
        _atomic_json(run_dir / "manifest.json", manifest)
        return "AWAITING_REVIEW", run_dir
    except GateBlocked as exc:
        _record_failure(journal, manifest, "BLOCKED", exc)
        return "BLOCKED", run_dir
    except (BudgetBlocked, BudgetError) as exc:
        _record_failure(journal, manifest, "BLOCKED", exc)
        return "BLOCKED", run_dir
    except Exception as exc:
        _record_failure(journal, manifest, "FAILED", exc)
        return "FAILED", run_dir
    finally:
        _close_logger(logger)


def _load_inputs(
    config: dict[str, Any], input_root: Path
) -> tuple[dict[str, Any], dict[str, list[dict[str, float]]], dict[str, str]]:
    hashes: dict[str, str] = {}
    if config["mode"] == "fixture_smoke":
        fixture_metrics = normalize_fixture(config["fixture"])
        return fixture_metrics, fixture_metrics.get("history", {}), hashes

    inputs = config["inputs"]
    resolved: dict[str, Path] = {}
    for name, relative in inputs.items():
        path = (input_root / relative).resolve()
        if input_root != path and input_root not in path.parents:
            raise EvidenceError(f"input path escapes input_root: {relative}")
        if not path.is_file():
            raise FileNotFoundError(f"required input file is missing: {path}")
        resolved[name] = path
        hashes[relative] = _sha256_file(path)

    results = load_json(resolved["results_json"])
    gate = load_json(resolved["forward_gate_json"])
    if not isinstance(gate, dict) or gate.get("passed") is not True:
        raise GateBlocked("recorded forward numerical gate did not pass")
    selection = load_json(resolved["lambda_selection_json"])
    verify_lambda_selection(results, selection)
    pilot_manifest = load_json(resolved["pilot_manifest_json"])
    snapshot = pilot_manifest.get("source_snapshot_sha256", {})
    if pilot_manifest.get("source_tree_dirty_at_run") is not True:
        raise EvidenceError("pilot manifest does not disclose the dirty source tree at run time")
    if not isinstance(snapshot, dict) or not snapshot:
        raise EvidenceError("pilot manifest has no source snapshot hashes")
    for relative, expected in snapshot.items():
        source_file = (input_root / relative).resolve()
        if input_root not in source_file.parents or not source_file.is_file():
            raise EvidenceError(f"recorded source file is missing: {relative}")
        actual = _sha256_file(source_file)
        if actual != expected:
            raise EvidenceError(f"recorded source hash mismatch: {relative}")
        hashes[f"source_snapshot:{relative}"] = actual
    metrics = read_recorded_metrics(results)
    histories_value = load_json(resolved["training_histories_json"])
    if not isinstance(histories_value, dict):
        raise EvidenceError("training_histories_json must be an object")
    histories = aggregate_histories(histories_value)
    return metrics, histories, hashes


def _record_failure(journal: RunJournal, manifest: dict[str, Any], state: str, exc: Exception) -> None:
    trace = traceback.format_exc()
    journal.logger.error("run stopped: %s\n%s", exc, trace)
    if journal.state not in {"FAILED", "BLOCKED", "AWAITING_REVIEW"}:
        journal.transition(state, str(exc))
    failure = {
        "run_id": journal.run_id,
        "status": state,
        "error_type": type(exc).__name__,
        "error": str(exc),
        "traceback": trace,
        "failed_at_utc": _utc_now(),
    }
    _atomic_json(journal.run_dir / "failure.json", failure)
    manifest.update({"status": state, "failure": failure, "completed_at_utc": _utc_now()})
    _atomic_json(journal.run_dir / "manifest.json", manifest)


def _make_logger(run_dir: Path) -> logging.Logger:
    logger = logging.getLogger(f"pxrd_autolab.{run_dir.name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger


def _close_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def _check_deadline(started: float, max_seconds: float) -> None:
    elapsed = time.monotonic() - started
    if elapsed > max_seconds:
        raise BudgetBlocked(f"run elapsed time {elapsed:.3f}s exceeds max_seconds {max_seconds:.3f}s")


def _atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
    os.replace(temporary, path)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git_value(root: Path, args: list[str]) -> str | None:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _git_dirty(root: Path) -> bool | None:
    value = _git_value(root, ["status", "--porcelain"])
    return None if value is None else bool(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="validate and lock config without reading results")
    parser.add_argument("--max-steps", type=int, help="additional run-time budget cap")
    args = parser.parse_args(argv)
    status, run_dir = run_pipeline(
        args.config,
        repo_root=args.repo_root,
        input_root=args.input_root,
        runs_root=args.runs_root,
        dry_run=args.dry_run,
        max_steps_override=args.max_steps,
    )
    print(f"{status}: {run_dir}")
    return 0 if status in {"CONFIG_VALIDATED", "AWAITING_REVIEW"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
