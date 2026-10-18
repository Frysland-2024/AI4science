"""Independent Research Supervisor: observe, classify, notify. NEVER execute jobs."""
from __future__ import annotations
import argparse
import ctypes
import datetime as dt
import json
import os
import re
import socket
import sys
from pathlib import Path

from . import events, evidence, worker as w

RUNNING = {"RUNNING", "RUNNING_CODE", "GPU_RUNNING", "GPU_PREPARING"}
REVIEW = {"REVIEW", "REVIEW_CODE", "GPU_REVIEW", "REVIEW_PENDING", "GPU_SUCCESS"}
FAILED = {"FAILED", "FAILED_CODE", "GPU_FAILED", "GPU_PRECHECK_FAILED", "GPU_PUBLICATION_FAILED"}
STOPPED = {"STOPPED", "GPU_STOPPED"}
BLOCKED = {"BLOCKED", "GPU_BLOCKED"}
STALE_SECONDS = 600

def process_birth(pid: int):
    """Return process creation epoch timestamp or None (no process / no access)."""
    if os.name != "nt":
        return None
    from ctypes import wintypes
    class Filetime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    api.OpenProcess.restype = wintypes.HANDLE
    api.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(Filetime),
                                   ctypes.POINTER(Filetime), ctypes.POINTER(Filetime),
                                   ctypes.POINTER(Filetime)]
    api.GetProcessTimes.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = api.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    c, e, kernel, user = Filetime(), Filetime(), Filetime(), Filetime()
    try:
        if not api.GetProcessTimes(handle, ctypes.byref(c), ctypes.byref(e),
                                   ctypes.byref(kernel), ctypes.byref(user)):
            return None
        ticks = (c.high << 32) | c.low
        return (ticks - 116444736000000000) / 10000000
    finally:
        api.CloseHandle(handle)

def parse_time(value):
    try:
        moment = dt.datetime.fromisoformat(value)
        if moment.tzinfo is None:
            return None
        return moment.timestamp()
    except (ValueError, TypeError):
        return None

def classify_failure(raw):
    text = str(raw or "").lower()
    if any(k in text for k in ("oom", "out of memory", "cuda allocation")):
        return "CUDA_OOM"
    if any(k in text for k in ("connection refused", "network", "401", "403",
                              "authentication", "token expired")):
        return "AUTH_NETWORK"
    if any(k in text for k in ("modulenotfounderror", "not found", "missing dependency")):
        return "MISSING_DEPENDENCY"
    if any(k in text for k in ("timeout", "timed out", "time limit")):
        return "TIMEOUT"
    if any(k in text for k in ("gate failed", "physics gate", "finite difference failed")):
        return "SCIENTIFIC_GATE_FAIL"
    if any(k in text for k in ("assertionerror", "validation error", "test failed")):
        return "VALIDATION_FAIL"
    return "UNKNOWN"

def journal_dir(root):
    return w.git_common_dir(root) / "research_bridge"

def registrations(root):
    return journal_dir(root) / "supervisor_v1" / "registrations"

def observe(reg, raw, *, now=None, birth_probe=process_birth):
    """Conservative mapping: lack of evidence is UNCERTAIN, never a failed run."""
    now = dt.datetime.now(dt.timezone.utc).timestamp() if now is None else now
    status = str(raw.get("status", "")).upper()
    if status in REVIEW:
        return "REVIEW_PENDING", "NONE"
    if status in BLOCKED or status.startswith("GPU_BLOCKED"):
        return "BLOCKED", "SCIENTIFIC_GATE_FAIL"
    if status in STOPPED:
        return "STOPPED", "NONE"
    if status in FAILED:
        return "FAILED", classify_failure(raw.get("error"))
    if status not in RUNNING:
        return "NEEDS_REVIEW", "UNKNOWN"
    heartbeat = raw.get("heartbeat", {})
    timestamp = parse_time(heartbeat.get("updated_utc")) if isinstance(heartbeat, dict) else None
    if timestamp is None:
        timestamp = parse_time(raw.get("updated_utc"))
    stale = timestamp is None or now - timestamp > STALE_SECONDS or timestamp > now + 120
    pid, expected_birth = reg.get("pid"), reg.get("process_started_epoch")
    if isinstance(pid, int) and isinstance(expected_birth, (int, float)):
        actual = birth_probe(pid)
        # Permissions, PID reuse, process gone or missed wake-up all yield uncertainty.
        if actual is None or abs(actual - expected_birth) > 2:
            return "STALE_UNCERTAIN", "INTERRUPTED_SHUTDOWN"
    if stale:
        return "STALE_UNCERTAIN", "UNKNOWN"
    return "RUNNING", "NONE"

def scan_journals(root):
    folder = journal_dir(root)
    entries = {}
    for f in folder.glob("issue-*.json"):
        match = re.fullmatch(r"issue-(\d+)\.json", f.name)
        if not match:
            continue
        obj = events.read_json(f)
        if isinstance(obj, dict):
            entries[int(match.group(1))] = obj
    return entries

def bootstrap(root):
    folder = registrations(root)
    folder.mkdir(parents=True, exist_ok=True)
    metadata = folder.parent / "bootstrap.json"
    if metadata.exists():
        return False
    issues = sorted(scan_journals(root))
    events.atomic_json(metadata, {"created_utc": events.utc_now(),
                                  "ignored_preexisting_issues": issues,
                                  "policy": "never enroll historical journals automatically"})
    return True

def register_external(root, *, issue, run_id, pid, worktree=None):
    """Register a FUTURE or currently active job explicitly. Never claim history."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
        raise ValueError("Invalid run ID")
    if issue < 1 or pid < 1:
        raise ValueError("Invalid Issue or PID")
    started = process_birth(pid)
    if started is None:
        raise ValueError("Cannot verify Windows process creation timestamp")
    dest = registrations(root) / ("ext-" + run_id + ".json")
    if dest.exists():
        raise ValueError("Registration already exists; never overwrite")
    entry = {"schema_version": 1, "source": "external", "issue": issue,
             "job_id": "ext-" + run_id, "pid": pid,
             "process_started_epoch": started,
             "registered_at_utc": events.utc_now(),
             "host": socket.gethostname(),
             "worktree_local_only": str(worktree) if worktree else None}
    events.atomic_json(dest, entry)
    return entry

def run_once(root, *, dry_run=False):
    folder = registrations(root)
    meta = folder.parent / "bootstrap.json"
    existing = scan_journals(root)
    if not meta.exists():
        if not dry_run:
            bootstrap(root)
        return {"status": "BOOTSTRAP_REQUIRED" if dry_run else "BOOTSTRAPPED",
                "ignored_old_issues": sorted(existing), "new_events": 0}
    baseline = events.read_json(meta, {})
    ignored = set(baseline.get("ignored_preexisting_issues", []))
    observed = {}
    for issue, raw in existing.items():
        if issue in ignored:
            continue
        key = "bridge-" + str(issue)
        observed[key] = ({"schema_version": 1, "source": "bridge", "issue": issue,
                          "job_id": key, "host": socket.gethostname()}, raw)
    for f in folder.glob("ext-*.json"):
        reg = events.read_json(f)
        if not isinstance(reg, dict):
            continue
        issue = reg.get("issue")
        if type(issue) is not int:
            continue
        # External Codex must supply fresh heartbeats from its wrapper,
        # otherwise it becomes uncertain. It cannot be silently called DONE.
        marker = folder.parent / "external_heartbeats" / (f.stem + ".json")
        signal = events.read_json(marker, {})
        raw = {"status": signal.get("status", "RUNNING"),
               "updated_utc": signal.get("updated_utc", reg.get("registered_at_utc"))}
        observed[f.stem] = (reg, raw)
    changes = []
    for key, (reg, raw) in sorted(observed.items()):
        if reg["source"] == "bridge":
            run_id = raw.get("run_id")
            if isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
                heartbeat = events.read_json(journal_dir(root) /
                                              "gpu_runs" / run_id / "heartbeat.json")
                if isinstance(heartbeat, dict):
                    raw = dict(raw, heartbeat=heartbeat)
        state, reason = observe(reg, raw)
        if reg["source"] == "bridge" and state == "REVIEW_PENDING":
            run_id = raw.get("run_id")
            if isinstance(run_id, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
                audit = evidence.inspect_run(journal_dir(root) / "gpu_runs" / run_id)
                if audit["status"] == "INCOMPLETE":
                    reason = "UNKNOWN"
        current = folder.parent / "observed" / (key + ".json")
        prior = events.read_json(current, {})
        if prior.get("state") == state and prior.get("reason") == reason:
            continue
        changes.append({"job_id": key, "issue": reg["issue"], "state": state, "reason": reason})
        if not dry_run:
            events.atomic_json(current, {"state": state, "reason": reason,
                                         "observed_utc": events.utc_now()})
            events.enqueue(root, job_id=key, issue=reg["issue"], status=state, reason=reason)
    outcome = {"status": "OK", "observed_jobs": len(observed),
               "new_events": len(changes), "transitions": changes}
    if not dry_run:
        outcome["delivery"] = events.flush(root)
    return outcome

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path,
                        default=Path(__file__).resolve().parents[1])
    p = parser.add_mutually_exclusive_group(required=True)
    p.add_argument("--once", action="store_true")
    p.add_argument("--bootstrap", action="store_true")
    p.add_argument("--register-external", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--run-id")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--worktree")
    args = parser.parse_args(argv)
    root = args.repo_root.resolve()
    try:
        if args.bootstrap:
            value = {"bootstrap_created": bootstrap(root)}
        elif args.register_external:
            if args.issue is None or args.run_id is None or args.pid is None:
                parser.error("--register-external needs --issue, --run-id and --pid")
            value = register_external(root, issue=args.issue, run_id=args.run_id,
                                      pid=args.pid, worktree=args.worktree)
        else:
            value = run_once(root, dry_run=args.dry_run)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, w.BridgeError) as exc:
        print("SUPERVISOR ERROR:", type(exc).__name__, str(exc)[:200], file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
