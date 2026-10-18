"""Fail-closed PXRD pilot preflight; does not contain a training loop."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    from .physics_gates import REQUIRED_GATES, run_required_gates
except ImportError:  # Support direct execution from an approved source snapshot.
    from physics_gates import REQUIRED_GATES, run_required_gates

REQUIRED_CONFIG_KEYS = {
    "schema_version", "preset", "experiment_id", "scope", "split", "seeds",
    "smoke", "pilot", "scientific_training_budget_seconds", "reviewed_backend",
}
REVIEWED_TRAINING_BACKEND = None


def read_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != REQUIRED_CONFIG_KEYS:
        raise ValueError("Config fields do not match the reviewed forward_ab schema")
    if config["preset"] != "forward_ab" or config["reviewed_backend"] is not None:
        raise ValueError("No reviewed A/B training backend is registered")
    if config["scientific_training_budget_seconds"] != 7200:
        raise ValueError("Scientific pilot budget differs from the approved task")
    return config


def build_report(config: dict, source_commit: str) -> tuple[dict, dict]:
    gate_report = run_required_gates(source_commit=source_commit)
    gates_pass = (gate_report.get("status") == "PASS"
                  and all(g.get("status") == "PASS" and isinstance(g.get("evidence"), dict)
                          and g["evidence"] for g in gate_report.get("gates", []))
                  and {g.get("id") for g in gate_report.get("gates", [])} == set(REQUIRED_GATES))
    backend_ready = REVIEWED_TRAINING_BACKEND is not None
    reasons = []
    if not gates_pass:
        reasons.append("Required measurement-aware scientific gates lack runtime PASS evidence.")
    if not backend_ready:
        reasons.append("BLOCKED_MISSING_IMPLEMENTATION: no explicitly reviewed executable A/B backend exists.")
    status = "BLOCKED_MISSING_IMPLEMENTATION" if not (gates_pass and backend_ready) else "READY"
    gate_report["a_b_authorized"] = bool(gates_pass and backend_ready)
    gate_report["required_gate_ids"] = list(REQUIRED_GATES)
    gate_report["status"] = "PASS" if gates_pass else "BLOCKED_MISSING_EVIDENCE"
    gate_report["block_reasons"] = reasons
    metrics = {
        "schema_version": 1,
        "status": status,
        "training_started": False,
        "scientific_performance_claim": False,
        "metrics": {},
        "config_sha256": None,
        "source_commit": source_commit,
    }
    return gate_report, metrics


def write_outputs(config_path: Path, output_dir: Path, source_commit: str) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    config = read_config(config_path)
    config_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
    gate_report, metrics = build_report(config, source_commit)
    metrics["config_sha256"] = config_hash
    metrics_path = output_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    gate_report["config_sha256"] = config_hash
    (output_dir / "gate_report.json").write_text(
        json.dumps(gate_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    run_manifest = {
        "schema_version": 1,
        "status": metrics["status"],
        "preset": "forward_ab",
        "experiment_id": config["experiment_id"],
        "source_commit": source_commit,
        "config": "pxrd_autolab/configs/forward_ab_pilot.json",
        "config_sha256": config_hash,
        "entrypoint": "pxrd_autolab/run.py",
        "entrypoint_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "training_started": False,
        "scientific_certification": False,
    }
    (output_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    next_steps = [
        "Implement and execute independent BaTiO3/Pymatgen full-spectrum parity tests.",
        "Implement a differentiable measurement-aware expected profile and autograd/finite-difference tests.",
        "Measure local q–eta identifiability and a deployable non-oracle nuisance path.",
        "Produce runtime evidence for split and leakage checks from the approved source tree.",
        "Add and review a real A/B backend only after every required gate passes.",
    ]
    report = [
        "# Measurement-aware PXRD pilot preflight",
        "",
        f"Status: **{metrics['status']}**",
        "",
        "No training was started. This checkout has no validated measurement-aware forward closure or reviewed A/B backend.",
        "The old clean-reference loss prototypes are not used. No V9 result or frozen scientific artifact was changed.",
        "",
        "## Gate status",
        "",
    ]
    report.extend(f"- `{g['id']}`: **{g['status']}**" for g in gate_report["gates"])
    report.extend(["", "## Required next steps", ""])
    report.extend(f"- {step}" for step in next_steps)
    report.extend([
        "", "## Scope", "",
        "The source-controlled config describes one exploratory, single-CIF BaTiO3 pilot. Even after future gates pass, it will not establish unseen-structure generalization or real-experiment refinement.",
        "The approved scientific training budget is 7,200 seconds. The bridge itself has no wall-clock kill timeout; the budget is an experiment-policy limit for a future reviewed backend.",
    ])
    (output_dir / "TECHNICAL_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return 0 if metrics["status"] == "READY" else 3


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--source-commit", default="unknown")
    args = parser.parse_args(argv)
    try:
        return write_outputs(args.config.resolve(), args.output_dir.resolve(), args.source_commit)
    except Exception as exc:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "gate_report.json").write_text(json.dumps({
            "schema_version": 1, "status": "BLOCKED_INVALID_CONFIG",
            "summary": str(exc)[:500], "gates": [],
        }, indent=2) + "\n", encoding="utf-8")
        (output_dir / "metrics.json").write_text(json.dumps({
            "schema_version": 1, "status": "BLOCKED_INVALID_CONFIG", "metrics": {},
        }, indent=2) + "\n", encoding="utf-8")
        (output_dir / "TECHNICAL_REPORT.md").write_text(
            "# Measurement-aware PXRD pilot preflight\n\n"
            "Status: **BLOCKED_INVALID_CONFIG**\n\nNo training was started.\n", encoding="utf-8")
        print("Preflight blocked:", str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
