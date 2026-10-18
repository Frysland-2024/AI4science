"""Approved, bounded GPU run lane. No arbitrary commands in Issues."""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path
from . import worker as w

LABEL = "bridge-gpu-approved"
PREFIX = "[Bridge GPU] "
PRESETS = {
    # Named, code-reviewed training entrypoint. Fails closed until this
    # script and a hashed config exist on the approved commit.
    "forward_ab": ("pxrd_autolab/run.py", "pxrd_autolab/configs/"),
    "forward_speed_benchmark": ("pxrd_autolab/benchmark_gpu.py", "pxrd_autolab/configs/"),
}
MAX_MINUTES = 120

def parse(issue):
    try:
        d = json.loads(issue["body"])
    except (KeyError, ValueError, TypeError) as exc:
        raise w.BridgeError("GPU task body must contain JSON") from exc
    keys = {"preset", "approved_sha", "config", "config_sha256", "run_id", "max_minutes"}
    if not isinstance(d, dict) or set(d) != keys:
        raise w.BridgeError("GPU task fields mismatch")
    for key in ("preset", "approved_sha", "config", "config_sha256", "run_id"):
        if not isinstance(d[key], str):
            raise w.BridgeError("GPU task requires string fields")
    if not re.fullmatch("[a-z0-9_-]{1,40}", d["preset"]):
        raise w.BridgeError("Invalid preset ID")
    if not re.fullmatch("[0-9a-f]{40}", d["approved_sha"]):
        raise w.BridgeError("Invalid SHA")
    if not re.fullmatch("[0-9a-f]{64}", d["config_sha256"]):
        raise w.BridgeError("Invalid config digest")
    if not re.fullmatch("[A-Za-z0-9_-]{1,60}", d["run_id"]):
        raise w.BridgeError("Invalid run identifier")
    if type(d["max_minutes"]) is not int or not 1 <= d["max_minutes"] <= MAX_MINUTES:
        raise w.BridgeError("Invalid bounded time budget")
    if d["preset"] not in PRESETS:
        raise w.BridgeError("GPU preset not yet registered and scientifically approved")
    if not w.safe_relpath(d["config"]):
        raise w.BridgeError("Config path invalid")
    return d

def eligible(issue):
    labels = {x.get("name") for x in issue.get("labels", [])}
    if issue.get("state") != "open" or "pull_request" in issue:
        return False
    if issue.get("user", {}).get("login", "").lower() != w.OWNER.lower():
        return False
    if not issue.get("title", "").startswith(PREFIX):
        return False
    if not {w.READY, LABEL}.issubset(labels):
        return False
    if {w.APPROVED, "bridge-code-approved", w.RUNNING, w.REVIEW, w.FAILED}.intersection(labels):
        return False
    try:
        parse(issue)
        return True
    except w.BridgeError:
        return False

def pending():
    raw = w.gh(["api", "repos/" + w.REPO + "/issues?state=open&labels=" + w.READY
                + "%2C" + LABEL + "&per_page=50"])
    return sorted((i for i in json.loads(raw) if eligible(i)), key=lambda i: i["number"])

def run(root, issue, dry_run=False):
    info = parse(issue)
    number = issue["number"]
    if w.journal(root, number).exists():
        return
    if dry_run:
        print("DRY RUN GPU", number, info["preset"], "up to", info["max_minutes"], "minutes")
        return
    base = w.revision(root)
    if base != info["approved_sha"]:
        raise w.BridgeError("Main changed; GPU run requires fresh approval")
    entry, config_root = PRESETS[info["preset"]]
    if not info["config"].startswith(config_root):
        raise w.BridgeError("Config does not match preset")
    # GPU tasks only use git-tracked files from the exact approved commit.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="research-bridge-gpu-") as tmp:
        workspace = Path(tmp) / "source"
        w.snapshot(root, workspace, base)
        cfg = workspace / info["config"]
        exe = workspace / entry
        if not cfg.is_file() or not exe.is_file():
            raise w.BridgeError("Approved runner/config missing")
        if hashlib.sha256(cfg.read_bytes()).hexdigest() != info["config_sha256"]:
            raise w.BridgeError("Config fingerprint mismatch")
        out = root / ".git" / "research_bridge" / "gpu_runs" / info["run_id"]
        if out.exists():
            raise w.BridgeError("Run ID already exists; no overwrite")
        out.mkdir(parents=True, exist_ok=False)
        w.label(number, w.RUNNING, w.READY)
        w.record(root, number, "GPU_RUNNING", commit=base, run_id=info["run_id"])
        try:
            # Never accept executable, flags or shell fragments from the Issue.
            cmd = [sys.executable, str(exe), "--config", str(cfg), "--output-dir", str(out)]
            result = w.command(cmd, cwd=workspace, timeout=info["max_minutes"] * 60,
                               env=w.codex_env())
            (out / "launcher.txt").write_text(result[-2000:], encoding="utf-8")
            (out / "bridge_manifest.json").write_text(json.dumps({
                "status":"AWAITING_SCIENTIFIC_REVIEW",
                "issue": number,
                "source_commit": base,
                "config_sha256": info["config_sha256"],
                "preset":info["preset"],
                "max_minutes":info["max_minutes"],
                "metrics_verified":False,
                "run_id":info["run_id"]
            }, indent=2), encoding="utf-8")
            w.comment(number, "GPU runner exited successfully. Manual validation of real "
                      "metrics/physical gates still required. Run ID: " + info["run_id"])
            w.label(number, w.REVIEW, w.RUNNING)
            w.record(root, number, "GPU_REVIEW", commit=base, run_id=info["run_id"])
        except Exception as exc:
            w.record(root, number, "GPU_FAILED", commit=base, error=str(exc)[:400])
            try:
                w.comment(number, "GPU execution blocked/failed. Inspect local run records.")
                w.label(number, w.FAILED, w.RUNNING)
            except Exception:
                pass
            raise
