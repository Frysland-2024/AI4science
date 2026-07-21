#!/usr/bin/env python3
"""Run the registered desktop prefetch candidate matrix without training."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--batches", type=int, default=16)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument(
        "--evidence-root",
        default=str(PROJECT_ROOT / "reports" / "desktop_acceptance" / "prefetch_matrix"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "desktop_acceptance" / "prefetch_matrix.json"),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    args = parse_args()
    if args.batches <= 10 or args.repeats < 2:
        raise SystemExit("--batches must exceed 10 and --repeats must be at least 2")
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    gate = profile["desktop_measurement_gate"]
    workers = [int(value) for value in gate["prefetch_worker_candidates"]]
    windows = [int(value) for value in gate["prefetch_batch_candidates"]]
    evidence_root = Path(args.evidence_root).resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)
    audit_script = PROJECT_ROOT / "scripts" / "audit_v9_dynamic_prefetch.py"
    rows: list[dict[str, Any]] = []
    for worker_count in workers:
        for prefetch_batches in windows:
            for repeat in range(args.repeats):
                evidence = evidence_root / (
                    f"workers_{worker_count}_window_{prefetch_batches}_repeat_{repeat + 1}.json"
                )
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-s",
                        str(audit_script),
                        "--contract",
                        str(contract_path),
                        "--batches",
                        str(args.batches),
                        "--workers",
                        str(worker_count),
                        "--prefetch-batches",
                        str(prefetch_batches),
                        "--output",
                        str(evidence),
                    ],
                    cwd=PROJECT_ROOT,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                payload = (
                    json.loads(evidence.read_text(encoding="utf-8"))
                    if evidence.is_file()
                    else {}
                )
                rows.append(
                    {
                        "worker_processes": worker_count,
                        "prefetch_batches": prefetch_batches,
                        "repeat": repeat + 1,
                        "status": payload.get("status", "missing"),
                        "exit_code": completed.returncode,
                        "prefetch_batches_per_second": payload.get("performance", {}).get(
                            "prefetch_batches_per_second"
                        ),
                        "speedup": payload.get("performance", {}).get("speedup"),
                        "parameter_pair_hash": payload.get("equivalence", {}).get(
                            "prefetch_parameter_pair_hash"
                        ),
                        "evidence": evidence.relative_to(PROJECT_ROOT).as_posix(),
                        "stderr_tail": completed.stderr[-1000:],
                    }
                )
    grouped: dict[str, dict[str, Any]] = {}
    for worker_count in workers:
        for prefetch_batches in windows:
            matching = [
                row
                for row in rows
                if row["worker_processes"] == worker_count
                and row["prefetch_batches"] == prefetch_batches
            ]
            rates = [
                float(row["prefetch_batches_per_second"])
                for row in matching
                if row["prefetch_batches_per_second"] is not None
            ]
            key = f"{worker_count}x{prefetch_batches}"
            grouped[key] = {
                "all_equivalence_gates_passed": len(matching) == args.repeats
                and all(row["status"] == "passed" and row["exit_code"] == 0 for row in matching),
                "median_prefetch_batches_per_second": statistics.median(rates)
                if len(rates) == args.repeats
                else None,
                "repeat_rates": rates,
            }
    passing = {
        key: value
        for key, value in grouped.items()
        if value["all_equivalence_gates_passed"]
        and value["median_prefetch_batches_per_second"] is not None
    }
    fastest = max(
        passing,
        key=lambda key: passing[key]["median_prefetch_batches_per_second"],
        default=None,
    )
    default_key = (
        f"{gate['current_selection']['worker_processes']}x"
        f"{gate['current_selection']['prefetch_batches']}"
    )
    default_rate = grouped.get(default_key, {}).get("median_prefetch_batches_per_second")
    fastest_rate = passing.get(fastest, {}).get("median_prefetch_batches_per_second")
    improvement = (
        float(fastest_rate) / float(default_rate) - 1.0
        if fastest_rate is not None and default_rate
        else None
    )
    recommendation = (
        fastest
        if fastest is not None
        and fastest != default_key
        and improvement is not None
        and improvement >= 0.10
        else default_key
    )
    status = "pass" if grouped and all(
        value["all_equivalence_gates_passed"] for value in grouped.values()
    ) else "fail"
    report = {
        "schema_version": "v9-desktop-prefetch-matrix-v1",
        "status": status,
        "purpose": "repeatable real-data prefetch engineering audit; no model training",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": {"path": contract_path.relative_to(PROJECT_ROOT).as_posix(), "sha256": _sha256(contract_path)},
        "implementation_sha256": _sha256(Path(__file__).resolve()),
        "configuration": {
            "workers": workers,
            "prefetch_batches": windows,
            "audited_batches_per_repeat": args.batches,
            "repeats": args.repeats,
            "no_optimizer_step": True,
            "no_checkpoint": True,
        },
        "results": grouped,
        "evidence": rows,
        "selection": {
            "registered_default": default_key,
            "fastest_passing": fastest,
            "fastest_vs_default_fraction": improvement,
            "recommended": recommendation,
            "automatic_contract_change": False,
            "minimum_improvement_to_recommend_change": 0.10,
        },
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "recommended": recommendation, "output": str(output)}))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
