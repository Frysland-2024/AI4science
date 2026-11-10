"""Fail-closed local scheduler for *approved* read-only Codex and V11 preflights.

No bridge reinstatement, no HPO/final/Test/RRUFF, no arbitrary shell, no PR writes.
The queue, approvals and journals live inside the existing repository's .git dir.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

LANES = {"codex_review", "v11_plan", "v11_smoke"}
TASK_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
STATES = {"COMPLETED", "BLOCKED", "RUNNING"}
MAX_CODEX_SECONDS = 900
MAX_PREFLIGHT_SECONDS = 1800


def json_read(path: Path) -> dict:
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("task JSON must be an object")
    return content


def sha256_object(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()


def write_atomic(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8") as out:
            json.dump(obj, out, ensure_ascii=False, sort_keys=True, indent=2)
            out.write("\n")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                       text=True, timeout=20, check=True)
    return r.stdout.strip()


def state_root(root: Path) -> Path:
    location = Path(git(root, "rev-parse", "--git-common-dir"))
    if not location.is_absolute():
        location = root / location
    return location.resolve() / "controlled_dispatch_v1"


def verify(task: dict) -> None:
    if set(task) - {"version", "task_id", "lane", "source_sha", "prompt", "expected_hostname"}:
        raise ValueError("unexpected task field")
    if (task.get("version") != 1 or not isinstance(task.get("task_id"), str)
            or not TASK_ID.fullmatch(task["task_id"])):
        raise ValueError("invalid version or task ID")
    if task.get("lane") not in LANES:
        raise ValueError("lane not allowlisted; HPO/final are never dispatched")
    if not isinstance(task.get("source_sha"), str) or not SHA.fullmatch(task["source_sha"]):
        raise ValueError("source_sha must pin an exact lowercase 40-character Git commit")
    if (not isinstance(task.get("expected_hostname"), str)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{2,100}", task["expected_hostname"])):
        raise ValueError("expected_hostname is required")
    if task["lane"] == "codex_review":
        prompt = task.get("prompt")
        if not isinstance(prompt, str) or not (10 <= len(prompt) <= 6000):
            raise ValueError("Codex read-only review needs a bounded prompt")
    elif "prompt" in task:
        raise ValueError("GPU preflight tasks cannot supply arbitrary prompts")


def preflight(root: Path, task: dict) -> None:
    verify(task)
    if os.environ.get("COMPUTERNAME", "").lower() != task["expected_hostname"].lower():
        raise ValueError("job belongs to a different host")
    if git(root, "rev-parse", "HEAD") != task["source_sha"]:
        raise ValueError("local HEAD differs from approved source SHA")
    if git(root, "status", "--porcelain"):
        raise ValueError("worktree contains changes; refusing to run against mixed code")
    if sys.platform != "win32" and task["lane"] in {"v11_plan", "v11_smoke"}:
        raise ValueError("the V11 native Windows preflight requires Windows")


def command(root: Path, task: dict, journal: Path) -> tuple[list[str], int]:
    if task["lane"] == "codex_review":
        exe = shutil.which("codex")
        if not exe:
            raise ValueError("Codex CLI not installed")
        return ([exe, "exec", "-s", "read-only", "--ephemeral",
                 "--ignore-user-config", "--color", "never",
                 "-C", str(root), "-o", str(journal / "codex_last_message.txt"), "-"],
                MAX_CODEX_SECONDS)
    launcher = root / "server_migration" / "start_windows.ps1"
    if not launcher.is_file():
        raise ValueError("V11 native Windows launcher missing")
    exe = shutil.which("powershell.exe") or shutil.which("powershell")
    if not exe:
        raise ValueError("PowerShell unavailable")
    mode = "plan" if task["lane"] == "v11_plan" else "smoke"
    return ([exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(launcher), "-Mode", mode], MAX_PREFLIGHT_SECONDS)


def records(root: Path) -> list[dict]:
    home = state_root(root)
    answer = []
    for path in sorted((home / "tasks").glob("*.json")) if (home / "tasks").exists() else []:
        ident = path.stem
        status = home / "runs" / (ident + ".json")
        approval = home / "approvals" / (ident + ".json")
        if status.exists():
            row = json_read(status)
            label = row.get("status", "BLOCKED")
            if label == "RUNNING":
                stamp = row.get("heartbeat_utc", row.get("started_utc", ""))
                try:
                    age = time.time() - time.mktime(time.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ"))
                except (ValueError, TypeError, OverflowError):
                    age = float("inf")
                if age > 180:
                    label = "NEEDS_DECISION"  # not proof of a dead process; never auto-retry
        else:
            label = "APPROVED" if approval.exists() else "AWAITING_APPROVAL"
        answer.append({"task": ident, "status": label})
    return answer


def approve(root: Path, ident: str) -> dict:
    if not TASK_ID.fullmatch(ident):
        raise ValueError("invalid task ID")
    home = state_root(root)
    path = home / "tasks" / (ident + ".json")
    task = json_read(path)
    if task["task_id"] != ident:
        raise ValueError("task ID mismatch")
    preflight(root, task)
    if (home / "runs" / (ident + ".json")).exists():
        raise ValueError("task already attempted: do not reuse an ID")
    approval_path = home / "approvals" / (ident + ".json")
    if approval_path.exists():
        raise ValueError("approval already exists; inspect instead of overwriting")
    stamp = {"version": 1, "task_id": ident, "approved_sha256": sha256_object(task),
             "source_sha": task["source_sha"], "approved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    write_atomic(approval_path, stamp)
    return stamp


def run_once(root: Path, *, dry_run: bool = False) -> dict:
    home = state_root(root)
    if dry_run:
        return _run_once_unlocked(root, home, dry_run=True)
    home.mkdir(parents=True, exist_ok=True)
    lock = home / "dispatch.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        return {"status": "BLOCKED", "note": "another worker or stale lock; inspect locally, do not auto-retry"}
    try:
        return _run_once_unlocked(root, home, dry_run=False)
    finally:
        lock.rmdir()


def _run_once_unlocked(root: Path, home: Path, *, dry_run: bool = False) -> dict:
    pending = (home / "tasks")
    if not pending.exists():
        return {"status": "IDLE", "note": "empty queue; nothing launched"}
    for path in sorted(pending.glob("*.json")):
        ident = path.stem
        if not TASK_ID.fullmatch(ident):
            continue
        run_path = home / "runs" / (ident + ".json")
        if run_path.exists():  # includes aborted or uncertain former RUNNING
            continue
        approval_path = home / "approvals" / (ident + ".json")
        if not approval_path.exists():
            continue
        try:
            task = json_read(path)
            approval = json_read(approval_path)
            verify(task)
            if (task["task_id"] != ident or approval.get("task_id") != ident
                    or approval.get("source_sha") != task["source_sha"]
                    or approval.get("approved_sha256") != sha256_object(task)):
                raise ValueError("authorization hash does not match task")
            preflight(root, task)
            args, cap = command(root, task, home / "runs" / ident)
            if dry_run:
                return {"status": "DRY_RUN", "task_id": ident,
                        "lane": task["lane"], "planned_executable": Path(args[0]).name}
            journal = home / "runs" / ident
            journal.mkdir(parents=True, exist_ok=True)
            meta = {"task_id": ident, "lane": task["lane"], "source_sha": task["source_sha"],
                    "approval_sha256": approval["approved_sha256"], "status": "RUNNING",
                    "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            write_atomic(run_path, meta)  # fail closed on crash: never auto-repeat
            try:
                with (journal / "console.txt").open("w", encoding="utf-8") as log:
                    flags = (subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
                    proc = subprocess.Popen(args, cwd=root, text=True, stdout=log,
                                            stderr=subprocess.STDOUT,
                                            stdin=subprocess.PIPE if task["lane"] == "codex_review" else subprocess.DEVNULL,
                                            creationflags=flags)
                    if task["lane"] == "codex_review":
                        proc.stdin.write(task["prompt"])
                        proc.stdin.close()
                    started = time.monotonic()
                    meta["pid"] = proc.pid
                    while proc.poll() is None:
                        meta["heartbeat_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                        write_atomic(run_path, meta)
                        if time.monotonic() - started > cap:
                            if sys.platform == "win32":
                                subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                                               capture_output=True, timeout=30, check=False)
                            else:
                                proc.kill()
                            try:
                                proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                pass
                            raise subprocess.TimeoutExpired(args, cap)
                        time.sleep(3)
                    exit_code = proc.wait()
                meta["status"] = "COMPLETED" if exit_code == 0 else "BLOCKED"
                meta["exit_code"] = exit_code
                meta["note"] = ("Execution exited successfully; evidence needs owner review."
                                if exit_code == 0 else "Nonzero exit: review private log; no retry.")
            except subprocess.TimeoutExpired:
                meta.update(status="BLOCKED", note="Bounded execution timeout; no automatic retry.")
            except Exception as exc:
                meta.update(status="BLOCKED", note="Execution exception: " + type(exc).__name__)
            meta["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            write_atomic(run_path, meta)
            return {"status": meta["status"], "task_id": ident, "note": meta["note"]}
        except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            if dry_run:
                return {"status": "BLOCKED", "task_id": ident, "reason": str(exc)}
            write_atomic(run_path, {"task_id": ident, "status": "BLOCKED",
                                    "reason": str(exc), "note": "Authorization/preflight failed; do not retry automatically."})
            return {"status": "BLOCKED", "task_id": ident, "reason": str(exc)}
    return {"status": "IDLE", "note": "no unattempted approved tasks"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="run a single explicitly approved queued task")
    mode.add_argument("--dry-run", action="store_true", help="preview without writing, launching or approving")
    mode.add_argument("--status", action="store_true", help="list local task states only")
    mode.add_argument("--approve", metavar="TASK_ID", help="OWNER-ACTION ONLY: pin one queued task")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.status:
        result = {"tasks": records(root)}
    elif args.approve:
        result = approve(root, args.approve)
    else:
        result = run_once(root, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
