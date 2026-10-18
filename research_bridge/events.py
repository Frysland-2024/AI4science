"""Durable supervisor events and deduplicated GitHub delivery.

No model calls, training, source edits, or raw local logs.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from . import worker as w

STATUSES = {"RUNNING", "REVIEW_PENDING", "BLOCKED", "FAILED", "STOPPED",
            "STALE_UNCERTAIN", "NEEDS_REVIEW"}
REASONS = {"NONE", "AUTH_NETWORK", "MISSING_DEPENDENCY", "CUDA_OOM", "TIMEOUT",
           "INTERRUPTED_SHUTDOWN", "SCIENTIFIC_GATE_FAIL", "VALIDATION_FAIL",
           "UNKNOWN"}

def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def store(root: Path) -> Path:
    folder = w.git_common_dir(root) / "research_bridge" / "supervisor_v1"
    folder.mkdir(parents=True, exist_ok=True)
    return folder

def atomic_json(path: Path, item: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    temp.write_text(json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2),
                    encoding="utf-8")
    os.replace(temp, path)

def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default

def append_audit(root: Path, item: dict):
    path = store(root) / "events.jsonl"
    line = json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as stream:
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())

def event_key(job_id: str, issue: int, status: str, reason: str) -> str:
    raw = f"supervisor-v1|{job_id}|{issue}|{status}|{reason}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def enqueue(root: Path, *, job_id: str, issue: int, status: str,
            reason: str = "NONE") -> bool:
    if status not in STATUSES or reason not in REASONS:
        raise ValueError("Unexpected supervisor status or reason")
    if type(issue) is not int or issue < 1 or not job_id or len(job_id) > 128:
        raise ValueError("Invalid issue or job ID")
    eid = event_key(job_id, issue, status, reason)
    outbox = store(root) / "outbox"
    dest = outbox / (eid + ".json")
    if dest.exists() or (store(root) / "sent" / (eid + ".json")).exists():
        return False
    event = {"schema_version": 1, "event_id": eid, "job_id": job_id,
             "issue_number": issue, "status": status, "reason": reason,
             "created_at_utc": utc_now()}
    atomic_json(dest, event)
    append_audit(root, event)
    return True

def public_message(event: dict) -> str:
    return ("<!-- research-supervisor:" + event["event_id"] + " -->\n"
            "**Research Supervisor**: " + event["status"] + "\n\n"
            "Run: " + event["job_id"].replace("<", "").replace(">", "")
            + "; reason category: " + event["reason"] + ".\n"
            "Local observer status only, NOT scientific validation. "
            "Review primary evidence before accepting any result.")

def remote_has_event(issue: int, event_id: str) -> bool:
    marker = "<!-- research-supervisor:" + event_id + " -->"
    for page in range(1, 6):
        raw = w.gh(["api", f"repos/{w.REPO}/issues/{issue}/comments"
                    f"?per_page=100&page={page}"])
        comments = json.loads(raw)
        if any(marker in (entry.get("body") or "") for entry in comments):
            return True
        if len(comments) < 100:
            return False
    raise w.BridgeError("Cannot establish deduplication across all comments")

def flush(root: Path, limit: int = 8) -> dict:
    s = store(root)
    sent = s / "sent"
    sent.mkdir(exist_ok=True)
    result = {"delivered": 0, "pending": 0, "errors": 0}
    outbox = s / "outbox"
    if outbox.exists():
        for path in sorted(outbox.glob("*.json"))[:limit]:
            event = read_json(path)
            if not isinstance(event, dict):
                result["errors"] += 1
                continue
            receipt = sent / path.name
            if receipt.exists():
                path.unlink(missing_ok=True)
                continue
            try:
                if not remote_has_event(event["issue_number"], event["event_id"]):
                    w.comment(event["issue_number"], public_message(event))
                atomic_json(receipt, {"event_id": event["event_id"],
                                      "delivered_utc": utc_now()})
                path.unlink(missing_ok=True)
                result["delivered"] += 1
            except (OSError, ValueError, w.BridgeError):
                result["errors"] += 1
        result["pending"] = len(list(outbox.glob("*.json")))
    return result
