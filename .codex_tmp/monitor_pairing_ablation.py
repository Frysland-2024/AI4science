#!/usr/bin/env python3
"""Background monitor for the pairing-ablation training job.

Simpler than the previous version: just poll ``summary.json`` and commit +
push as soon as it appears.  No PID-based liveness check (the previous
implementation had a ``NoneType`` bug when the training process was killed).

Stops on either:
  - ``summary.json`` exists and has been pushed (success path)
  - the wall-clock budget is exceeded (timeout)

Logs every step to ``monitor.log``.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("E:/AI4science")
TARGET_DIR = REPO / "xrd_robustness" / "outputs" / "pairing_ablation_quick"
SUMMARY = TARGET_DIR / "summary.json"
LOG = TARGET_DIR / "monitor.log"
POLL_INTERVAL = 30  # seconds
MAX_WALL_TIME = 6 * 3600  # 6 hours


def log(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    try:
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"warn: log write failed: {exc}", flush=True)


def summary_ready() -> bool:
    if not SUMMARY.exists():
        return False
    try:
        return SUMMARY.stat().st_size > 0
    except OSError:
        return False


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", "-C", str(REPO), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def commit_and_push() -> tuple[bool, str]:
    base = "xrd_robustness/outputs/pairing_ablation_quick"
    add_paths = [
        f"{base}/summary.json",
        f"{base}/preflight.json",
    ]
    partial = TARGET_DIR / "partial_results.json"
    if partial.exists():
        add_paths.append(f"{base}/partial_results.json")

    r = git("add", "-f", *add_paths, check=False)
    if r.returncode != 0:
        return False, f"git add failed: {r.stderr.strip() or r.stdout.strip()}"

    status = git("status", "--short", "--", *add_paths, check=False)
    if not status.stdout.strip():
        return False, "nothing to commit (already tracked or no changes)"

    msg = "results(xrd): add pairing-ablation quick summary"
    commit = git("commit", "-m", msg, check=False)
    if commit.returncode != 0:
        return False, f"git commit failed: {commit.stderr.strip() or commit.stdout.strip()}"

    push = git("push", "origin", "HEAD", check=False)
    if push.returncode != 0:
        return True, f"local commit OK; push failed: {push.stderr.strip() or push.stdout.strip()}"
    return True, "pushed to origin"


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    log(f"monitor started; target={SUMMARY}")
    start = time.time()
    start_mtime_threshold = start  # ignore a summary.json left over from a previous run

    while True:
        if time.time() - start > MAX_WALL_TIME:
            log(f"max wall time {MAX_WALL_TIME}s reached, giving up")
            return 2

        if summary_ready():
            try:
                mtime = SUMMARY.stat().st_mtime
            except OSError:
                mtime = 0.0
            if mtime >= start_mtime_threshold:
                log(
                    f"summary.json detected (mtime {mtime:.0f} >= start "
                    f"{start_mtime_threshold:.0f}); staging and pushing"
                )
                ok, detail = commit_and_push()
                log(f"git outcome: ok={ok}; {detail}")
                return 0 if ok else 3
            log(
                f"poll: summary.json exists but mtime {mtime:.0f} predates start "
                f"{start_mtime_threshold:.0f} (leftover from a previous run); skipping"
            )
        else:
            log("poll: summary.json not yet present")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())