"""Bounded, owner-approved Codex review / V11 HPO dispatcher.

Private queue lives only under E:/AI4science/_local/controlled_dispatcher.
It does not read GitHub Issues for executable instructions, auto-create PRs,
approve research stages, invoke the retired research_bridge, or launch final,
Test, RRUFF, cloud rental, or other arbitrary shell commands.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "_local" / "controlled_dispatcher"
QUEUE = PRIVATE / "queue"
RUNS = PRIVATE / "runs"
SHA = re.compile(r"^[a-f0-9]{40}$")
TERMINAL = {"COMPLETED", "BLOCKED", "NEEDS_DECISION"}
STAGE0_CHECKS = ("cuda", "resources", "full_validation", "checkpoint_recovery", "cache_integrity")


def utc():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return obj


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def git(*args):
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                             text=True, timeout=20, check=True)
    return process.stdout.strip()


def check_source(sha, *, clean=True):
    if not isinstance(sha, str) or not SHA.fullmatch(sha):
        raise ValueError("Expected an explicitly pinned 40-character commit SHA")
    if git("rev-parse", "HEAD") != sha:
        raise RuntimeError("Local HEAD differs from owner-approved source SHA")
    if clean and git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("Tracked working-tree changes present; do not run Codex/GPU over a dirty source")
    return sha


def stage0_receipt(path, sha, hours):
    """Verify frozen, host-specific, privately approved *evidence*, not a prose claim."""
    p = Path(path).resolve(strict=True)
    if not p.is_relative_to((ROOT / "_local").resolve()):
        raise ValueError("Stage0 receipt must be inside the private _local directory")
    receipt = read_json(p)
    if receipt.get("schema") != "v11-cuifa-stage0-receipt-v1":
        raise ValueError("Unrecognized cuifa Stage0 evidence schema")
    if receipt.get("source_sha") != sha:
        raise ValueError("Stage0 receipt is for a different source revision")
    if receipt.get("hostname", "").lower() != socket.gethostname().lower():
        raise ValueError("Stage0 receipt belongs to a different computer")
    checks = receipt.get("checks")
    if not isinstance(checks, dict) or any(checks.get(k) != "PASS" for k in STAGE0_CHECKS):
        raise ValueError("Cuifa Stage0 has not passed all required validation/restart gates")
    if receipt.get("gpu_name") != "NVIDIA GeForce RTX 4070 Ti SUPER":
        raise ValueError("Receipt is not for the intended cuifa GPU")
    evidence = receipt.get("evidence")
    if not isinstance(evidence, list) or len(evidence) < 2:
        raise ValueError("Stage0 requires at least two independently recorded local evidence files")
    for item in evidence:
        if not isinstance(item, dict) or set(item) != {"relative_path", "sha256"}:
            raise ValueError("Bad evidence entry")
        f = (ROOT / item["relative_path"]).resolve(strict=True)
        if not f.is_relative_to((ROOT / "_local").resolve()) or not f.is_file():
            raise ValueError("Evidence path must be a private local file")
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Stage0 evidence hash mismatch: {f.name}")
    if not isinstance(hours, (int, float)) or isinstance(hours, bool) or not 0 < hours <= 24:
        raise ValueError("Explicit finite owner-approved GPU budget required (0-24 hours)")
    try:
        name = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                              capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as err:
        raise RuntimeError("Cannot verify target GPU") from err
    if name != receipt["gpu_name"]:
        raise RuntimeError("Actual GPU differs from frozen Stage0 machine receipt")
    return hashlib.sha256(p.read_bytes()).hexdigest()


def approve(kind, sha, *, hours=None, receipt=None):
    """A locally invoked explicit approval. Never inferred from Issues or repo text."""
    if kind not in ("codex_review", "v11_hpo"):
        raise ValueError("Task type is not allowlisted")
    check_source(sha)
    obj = {
        "schema": "ai4science-controlled-task-v1", "id": uuid4().hex,
        "kind": kind, "source_sha": sha, "hostname": socket.gethostname(),
        "approved_at_utc": utc(), "approved_by": "explicit_local_owner_action",
    }
    if kind == "v11_hpo":
        if receipt is None or hours is None:
            raise ValueError("Owner must supply a passed private Stage0 receipt and GPU budget")
        obj["stage0_receipt"] = str(Path(receipt).resolve(strict=True))
        obj["stage0_sha256"] = stage0_receipt(receipt, sha, hours)
        obj["max_gpu_hours"] = hours
    elif receipt is not None or hours is not None:
        raise ValueError("Codex review accepts no GPU options")
    write_json(QUEUE / (obj["id"] + ".json"), obj)
    return obj


def _task_state(job):
    return RUNS / job["id"] / "status.json"


def _run_command(argv, log_path, *, timeout=None):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    process = None
    with log_path.open("ab", buffering=0) as out:
        try:
            process = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=subprocess.STDOUT,
                                       creationflags=flags)
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            else:
                process.kill()
            process.wait(timeout=30)
            raise RuntimeError("Codex review exceeded the bounded 30-minute limit")


def _validate_job(job):
    if job.get("schema") != "ai4science-controlled-task-v1":
        raise ValueError("Unknown task contract")
    if job.get("kind") not in ("codex_review", "v11_hpo"):
        raise ValueError("Unsupported task")
    if not isinstance(job.get("id"), str) or not re.fullmatch(r"[a-f0-9]{32}", job["id"]):
        raise ValueError("Unsafe job ID")
    if job.get("hostname", "").lower() != socket.gethostname().lower():
        raise ValueError("Job was approved on a different host")
    check_source(job.get("source_sha"))
    if job["kind"] == "v11_hpo":
        receipt_hash = stage0_receipt(job["stage0_receipt"], job["source_sha"], job["max_gpu_hours"])
        if receipt_hash != job["stage0_sha256"]:
            raise ValueError("Stage0 receipt has been changed after approval")
    return True


def _execute(job):
    check_source(job["source_sha"])
    if job["kind"] == "codex_review":
        cli = shutil.which("codex.cmd") or shutil.which("codex")
        if not cli:
            raise RuntimeError("Codex CLI not found")
        cmd = [cli, "exec", "review", "--commit", job["source_sha"],
               "--ignore-user-config", "--ephemeral"]
        return _run_command(cmd, RUNS / job["id"] / "codex_review.log", timeout=1800)
    if job["kind"] == "v11_hpo":
        if os.name != "nt":
            raise RuntimeError("Cuifa V11 HPO dispatcher currently supports native Windows only")
        # Existing launcher/runner enforces frozen science and stop/checkpoint policy.
        cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
               "-File", str(ROOT / "server_migration" / "start_windows.ps1"),
               "-Mode", "hpo", "--max-gpu-hours", str(job["max_gpu_hours"])]
        return _run_command(cmd, RUNS / job["id"] / "v11_hpo.log")
    raise ValueError("Unsupported task")


def _exclusive_lock():
    """Fail-closed cross-process lock; no new job if lock cannot be taken."""
    PRIVATE.mkdir(parents=True, exist_ok=True)
    lock = PRIVATE / ".dispatch.lock"
    stream = lock.open("a+b")
    if os.name == "nt":
        import msvcrt
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b"\0"); stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as err:
            stream.close()
            raise RuntimeError("Another dispatcher invocation is active") from err
        def unlock():
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as err:
            stream.close()
            raise RuntimeError("Another dispatcher invocation is active") from err
        def unlock():
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return stream, unlock


def tick():
    """Execute at most ONE queued, previously approved task; never retry failures."""
    lock, unlock = _exclusive_lock()
    try:
        QUEUE.mkdir(parents=True, exist_ok=True)
        for file in sorted(QUEUE.glob("*.json")):
            try:
                job = read_json(file)
                if file.stem != job.get("id"):
                    raise ValueError("Queue filename does not match job ID")
            except (ValueError, KeyError) as err:
                return {"status": "BLOCKED", "reason": str(err), "task": file.name}
            state_file = _task_state(job)
            if state_file.exists():
                continue  # Every attempt is one-shot; even a crash NEVER silently retries.
            try:
                _validate_job(job)
            except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as err:
                result = {"status": "BLOCKED", "id": job["id"], "kind": job["kind"],
                          "reason": str(err), "at_utc": utc()}
                write_json(state_file, result)
                return result
            write_json(state_file, {"status": "RUNNING", "id": job["id"], "kind": job["kind"], "at_utc": utc()})
            try:
                code = _execute(job)
                if code != 0:
                    raise RuntimeError(f"Task exited with code {code}; check local logs")
                if job["kind"] == "v11_hpo":
                    from research_status import summarize
                    snapshot = summarize(ROOT / "server_runs" / "v11_a0_js_optuna")
                    if snapshot["stage"] != "HPO_CONFIRMED":
                        result_status = "NEEDS_DECISION"
                        note = "HPO process exited, but independent confirmation is not proven complete; do not auto-retry"
                    else:
                        result_status = "COMPLETED"
                        note = "HPO and confirmation metadata exist; scientific evidence still needs independent acceptance"
                else:
                    result_status = "COMPLETED"
                    note = "Codex read-only review exited; inspect output; no code changes or PR"
                result = {"status": result_status, "id": job["id"], "kind": job["kind"],
                          "reason": note, "at_utc": utc()}
            except Exception as err:
                result = {"status": "BLOCKED", "id": job["id"], "kind": job["kind"],
                          "reason": str(err)[:400], "at_utc": utc()}
            write_json(state_file, result)
            return result
        return {"status": "IDLE", "reason": "No new approved work. No Codex or GPU run launched."}
    finally:
        unlock()
        lock.close()


def status():
    """Inspect approvals/results without invoking Codex, GPU or shell."""
    jobs = []
    for file in sorted(QUEUE.glob("*.json")):
        try:
            job = read_json(file)
            s = _task_state(job)
            state = read_json(s) if s.exists() else {"status": "QUEUED"}
            jobs.append({"id": job["id"], "kind": job["kind"], "source_sha": job["source_sha"],
                         "status": state.get("status"), "reason": state.get("reason")})
        except (OSError, ValueError, KeyError) as err:
            jobs.append({"status": "BLOCKED", "reason": str(err), "task": file.name})
    return {"schema": "ai4science-controlled-dispatch-v1", "jobs": jobs,
            "retired_bridge": "NOT_USED",
            "gpu_training_authorized": any(j.get("kind") == "v11_hpo" and j.get("status") in ("QUEUED", "RUNNING") for j in jobs),
            "note": "Local-only queue; no remote host inference. RUNNING can be stale after crash: no automatic retry."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "tick", "approve-codex-review", "approve-v11-hpo"))
    parser.add_argument("--sha", help="40-character pinned local HEAD")
    parser.add_argument("--stage0-receipt", type=Path)
    parser.add_argument("--max-gpu-hours", type=float)
    args = parser.parse_args()
    if args.command == "status":
        result = status()
    elif args.command == "tick":
        result = tick()
    else:
        kind = "codex_review" if args.command == "approve-codex-review" else "v11_hpo"
        result = approve(kind, args.sha, hours=args.max_gpu_hours, receipt=args.stage0_receipt)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
