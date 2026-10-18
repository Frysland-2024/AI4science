"""Conservative, read-only evidence inventory for a technical run.

This does not certify accuracy, physics or scientific novelty.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ALLOWED = ("run_manifest.json", "gate_report.json", "metrics.json",
           "TECHNICAL_REPORT.md", "test_summary.json")
REQUIRED = ALLOWED[:3]
MAX_FILE = 256 * 1024

def inspect_run(folder: Path) -> dict:
    result = {"status": "INCOMPLETE", "files": [], "limitations": [],
              "technical_completion_only": True, "scientifically_reviewed": False}
    if not folder.is_dir():
        result["limitations"].append("run_directory_missing")
        return result
    found = {}
    for name in ALLOWED:
        path = folder / name
        if path.is_symlink() or not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_FILE:
            result["limitations"].append("oversized:" + name)
            continue
        data = path.read_bytes()
        found[name] = path
        result["files"].append({"path": name, "sha256": hashlib.sha256(data).hexdigest(),
                                "bytes": size})
    missing = [name for name in REQUIRED if name not in found]
    if missing:
        result["limitations"].append("missing:" + ",".join(missing))
        return result
    try:
        manifest = json.loads(found["run_manifest.json"].read_text(encoding="utf-8"))
        gate = json.loads(found["gate_report.json"].read_text(encoding="utf-8"))
        metrics = json.loads(found["metrics.json"].read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        result["limitations"].append("invalid_json")
        return result
    if any(not isinstance(item, dict) for item in (manifest, gate, metrics)):
        result["limitations"].append("schema_not_object")
        return result
    result["provenance_fields"] = sorted(k for k in manifest if k in (
        "source_commit", "commit", "run_id", "config_sha256", "preset", "status"))
    result["metric_fields"] = sorted(str(k) for k in metrics.keys())
    result["gate_status"] = str(gate.get("status", "UNKNOWN"))[:40]
    result["status"] = "COMPLETED_UNREVIEWED"
    if result["gate_status"].upper().startswith(("BLOCKED", "FAIL")):
        result["status"] = "BLOCKED"
    # Do not compute, paraphrase or publish scientific metrics from this summary.
    result["limitations"].append("requires_independent_scientific_review")
    return result
