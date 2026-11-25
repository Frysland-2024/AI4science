#!/usr/bin/env python3
"""Synchronize explicitly managed status blocks; never launch experiments."""
import argparse
import difflib
import json
import re
from datetime import date
from pathlib import Path

DOCS = ["README.md","docs/CURRENT_STATE.md","AGENTS.md","docs/README.md","docs/START_HERE_FOR_SUPERVISORS.md","server_migration/README.md","docs/REVIEWER_GUIDE.md"]
BEGIN = "<!-- DOCS_SYNC:BEGIN research_status -->"
END = "<!-- DOCS_SYNC:END research_status -->"
LABELS = {"cuifa_stage0":"Cuifa Stage 0","hpo":"HPO","confirmation":"Confirmation","final_training":"Final training","synthetic_test":"Synthetic Test","rruff_scoring":"RRUFF scoring"}
SOURCE = "research_state.json"

def load(root):
    s = json.loads((root / SOURCE).read_text(encoding="utf-8"))
    expected = {"schema", "date", "direction", "results", "manuscript_priority",
                "execution", "local_preflight", "issue61", "issue55", "benchmark", "stages"}
    if not isinstance(s, dict) or set(s) != expected or type(s["schema"]) is not int or s["schema"] != 1:
        raise ValueError("invalid state schema")
    date.fromisoformat(s["date"])
    for key, allowed in {
        "results": {"FROZEN", "OPEN"},
        "manuscript_priority": {"LOW", "NORMAL", "HIGH"},
        "execution": {"DEFERRED", "ACTIVE"},
        "local_preflight": {"PASS", "NOT_RUN", "FAIL"},
        "issue61": {"CLOSED_LOCAL_SCOPE", "OPEN"},
        "issue55": {"OPEN_DEFERRED", "OPEN_ACTIVE", "CLOSED"},
    }.items():
        if s[key] not in allowed:
            raise ValueError("invalid " + key)
    if s["direction"] != "PXRD seven-crystal-system classification" or not re.fullmatch(r"RRUFF-Cu[0-9]+", s["benchmark"]):
        raise ValueError("research direction or benchmark requires explicit schema review")
    if not isinstance(s["stages"], dict) or set(s["stages"]) != set(LABELS) or any(v not in {"NOT_RUN", "PASS", "FAIL", "RUNNING"} for v in s["stages"].values()):
        raise ValueError("invalid stage status")
    if s["results"] == "FROZEN" and s["execution"] != "DEFERRED":
        raise ValueError("frozen results require deferred execution")
    if s["execution"] == "DEFERRED" and "RUNNING" in s["stages"].values():
        raise ValueError("deferred execution cannot contain running stages")
    if s["issue61"] == "CLOSED_LOCAL_SCOPE" and s["local_preflight"] != "PASS":
        raise ValueError("closed local scope requires preflight PASS")
    if s["issue55"] == "OPEN_ACTIVE" and s["execution"] != "ACTIVE":
        raise ValueError("active issue conflicts with deferred execution")
    if any(s["stages"][k] != "NOT_RUN" for k in LABELS if k != "cuifa_stage0") and s["stages"]["cuifa_stage0"] != "PASS":
        raise ValueError("downstream execution requires Stage 0 PASS")
    return s

def render(s):
    stages = "; ".join(f"{label}: {s['stages'][key]}" for key, label in LABELS.items())
    return (f"**Research status ({s['date']}):** {s['direction']}. Results: **{s['results']}**; manuscript priority: **{s['manuscript_priority']}**; V11 execution: **{s['execution']}**.\n\n"
            f"- Issue #61: {s['issue61']}; local preflight: {s['local_preflight']}. Issue #55: {s['issue55']}.\n"
            f"- Prospective benchmark: **{s['benchmark']}**.\n"
            f"- {stages}.\n"
            "- This status is not experiment authorization. Separate owner approval and applicable evidence gates are required.")

def changes(root):
    body = render(load(root))
    result = []
    for name in DOCS:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"unsafe managed path: {name}")
        raw = path.read_bytes()
        old = raw.decode("utf-8")
        newline = "\r\n" if "\r\n" in old else "\n"
        if old.count(BEGIN) != 1 or old.count(END) != 1 or old.index(BEGIN) > old.index(END):
            raise ValueError(f"missing, duplicate or reversed markers: {name}")
        start = old.index(BEGIN) + len(BEGIN)
        stop = old.index(END)
        new = old[:start] + newline + body.replace("\n", newline) + newline + old[stop:]
        if old != new:
            result.append((path, old, new))
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    modes = p.add_mutually_exclusive_group(required=True)
    for mode in ("check", "write", "diff"):
        modes.add_argument("--" + mode, action="store_true")
    args = p.parse_args()
    try:
        pending = changes(args.root)
        for path, old, new in pending:
            if args.write:
                path.write_bytes(new.encode("utf-8"))
            elif args.diff:
                print("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=str(path), tofile=str(path))))
            else:
                print(f"::error::{path}: generated status drift; run python scripts/sync_docs.py --write")
        print(f"Docs Sync: {len(pending)} changed or drifting document(s)")
        return int(args.check and bool(pending))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Docs Sync error: {exc}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
