#!/usr/bin/env python3
"""Combine target-desktop engineering gates without authorizing or starting training."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import (  # noqa: E402
    audit_contract_assets,
    build_tuning_plan,
    canonical_hash,
    load_contract,
)


DEFAULT_ACCEPTANCE_ROOT = PROJECT_ROOT / "outputs" / "desktop_acceptance"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument("--acceptance-root", default=str(DEFAULT_ACCEPTANCE_ROOT))
    parser.add_argument(
        "--output", default=str(DEFAULT_ACCEPTANCE_ROOT / "desktop_readiness.json")
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


def _training_processes() -> tuple[bool, list[dict[str, Any]]]:
    if os.name != "nt":
        return False, []
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -match '^python(w)?\\.exe$' -and "
        "$_.CommandLine -match 'train_v7.py|run_v9_method_transfer.py.+(tune-run|run)' } | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        return False, []
    payload = completed.stdout.strip()
    if not payload:
        return True, []
    decoded = json.loads(payload)
    rows = decoded if isinstance(decoded, list) else [decoded]
    return True, rows


def _prefetch_passed(report: dict[str, Any]) -> bool:
    equivalence = report.get("equivalence", {})
    return bool(
        report.get("status") == "passed"
        and equivalence.get("exact_material_order")
        and equivalence.get("exact_accepted_manifest_rows")
        and equivalence.get("exact_parameters")
        and equivalence.get("exact_spectrum_arrays")
        and equivalence.get("quality_gate_counts_match")
        and equivalence.get("sequential_parameter_pair_hash")
        == equivalence.get("prefetch_parameter_pair_hash")
    )


def build_readiness(
    *,
    contract: dict[str, Any],
    contract_path: Path,
    asset_audit: dict[str, Any],
    expected_plan: dict[str, Any],
    plan: dict[str, Any],
    reports: dict[str, dict[str, Any]],
    process_probe_supported: bool,
    training_processes: list[dict[str, Any]],
    registry_present: bool,
    registry_runs: list[dict[str, Any]],
    checkpoint_count: int,
    result_count: int,
) -> dict[str, Any]:
    contract_sha256 = _sha256(contract_path)
    expected_signature = [
        (run["run_id"], run["output_dir"], run["argv"])
        for run in expected_plan["runs"]
    ]
    observed_signature = [
        (run.get("run_id"), run.get("output_dir"), run.get("argv"))
        for run in plan.get("runs", [])
    ]
    hardware = reports["hardware"]
    acceleration = reports["acceleration"]
    preflight = reports["preflight"]
    checks = {
        "environment_bootstrap_pass": reports["environment"].get("status") == "pass",
        "frozen_runtime_and_pip_check_pass": all(
            reports["environment"].get("checks", {}).get(name) is True
            for name in (
                "python_version",
                "torch_version",
                "cuda_runtime",
                "cuda_available",
                "gpu_name",
                "gpu_memory",
                "bf16_supported",
                "pip_check",
                "msvc_toolchain_discoverable",
            )
        ),
        "contract_assets_current": (
            preflight.get("status") == "passed"
            and preflight.get("hashes") == asset_audit.get("hashes")
        ),
        "runtime_ready_for_development_tuning": preflight.get("runtime", {}).get(
            "ready_for_development_tuning"
        )
        is True,
        "target_hardware_detected": hardware.get("status")
        == "target_detected_ready_for_no_training_benchmarks",
        "hardware_contract_hash_current": str(
            hardware.get("contract", {}).get("sha256", "")
        ).upper()
        == contract_sha256,
        "prefetch_8x8_exact": _prefetch_passed(reports["prefetch_8x8"]),
        "prefetch_4x8_exact": _prefetch_passed(reports["prefetch_4x8"]),
        "full_prefetch_candidate_matrix_pass": reports["prefetch_matrix"].get(
            "status"
        )
        == "pass",
        "evaluation_batch_candidate_gate_pass": reports["evaluation_batch"].get(
            "status"
        )
        == "pass",
        "pinned_non_blocking_h2d_pass": reports["cuda_transfer"].get("status")
        == "pass",
        "acceleration_gate_pass": acceleration.get("status") == "pass",
        "acceleration_contract_hash_current": str(
            acceleration.get("contract", {}).get("sha256", "")
        ).upper()
        == contract_sha256,
        "tuning_plan_contract_hash_current": plan.get("contract_hash")
        == canonical_hash(contract),
        "tuning_plan_commands_current": observed_signature == expected_signature,
        "all_seven_runs_planned_not_started": (
            int(plan.get("run_count", 0)) == 7
            and all(
                run.get("status") == "planned_not_started"
                for run in plan.get("runs", [])
            )
        ),
        "training_process_probe_succeeded": process_probe_supported,
        "no_active_training_processes": not training_processes,
        "run_registry_present": registry_present,
        "run_registry_empty": registry_present and not registry_runs,
        "checkpoint_count_zero": checkpoint_count == 0,
        "result_count_zero": result_count == 0,
    }
    return {
        "schema_version": "v9-desktop-readiness-v1",
        "status": "ready_for_explicit_tuning_authorization"
        if all(checks.values())
        else "blocked",
        "purpose": (
            "target-desktop engineering readiness only; this artifact does not authorize "
            "or start the seven-run tuning study"
        ),
        "contract": {
            "path": contract_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": contract_sha256,
            "canonical_hash": canonical_hash(contract),
        },
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "execution_state": {
            "explicit_tuning_authorization_recorded": False,
            "training_started": False,
            "active_training_processes": training_processes,
            "registry_run_count": len(registry_runs),
            "checkpoint_count": checkpoint_count,
            "result_count": result_count,
        },
        "evidence_statuses": {
            name: report.get("status") for name, report in reports.items()
        },
        "next_action": (
            "request explicit user authorization before tune-run"
            if all(checks.values())
            else "repair failed engineering gates and rerun desktop acceptance"
        ),
    }


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()
    acceptance_root = Path(args.acceptance_root).resolve()
    contract = load_contract(contract_path)
    asset_audit = audit_contract_assets(contract, PROJECT_ROOT)
    expected_plan = build_tuning_plan(contract, PROJECT_ROOT)
    plan_path = PROJECT_ROOT / "reports" / "v9_method_transfer_tuning_plan.json"
    plan = _load(plan_path)
    report_paths = {
        "environment": acceptance_root / "environment.json",
        "preflight": acceptance_root / "preflight.json",
        "hardware": acceptance_root / "hardware_config.json",
        "prefetch_8x8": acceptance_root / "prefetch_8x8.json",
        "prefetch_4x8": acceptance_root / "prefetch_4x8.json",
        "prefetch_matrix": acceptance_root / "prefetch_matrix.json",
        "cuda_transfer": acceptance_root / "cuda_transfer.json",
        "evaluation_batch": acceptance_root / "evaluation_batch.json",
        "acceleration": acceptance_root / "acceleration.json",
    }
    reports = {name: _load(path) for name, path in report_paths.items()}
    output_root = PROJECT_ROOT / str(contract["development_tuning"]["output_root"])
    registry_path = output_root / "run_registry.json"
    registry_present = registry_path.is_file()
    registry = _load(registry_path)
    registry_runs = registry.get("runs", []) if isinstance(registry, dict) else registry
    checkpoint_count = sum(
        1
        for suffix in ("*.pt", "*.pth", "*.ckpt")
        for _ in output_root.rglob(suffix)
    )
    result_count = sum(1 for _ in output_root.rglob("results.json"))
    process_probe_supported, training_processes = _training_processes()
    readiness = build_readiness(
        contract=contract,
        contract_path=contract_path,
        asset_audit=asset_audit,
        expected_plan=expected_plan,
        plan=plan,
        reports=reports,
        process_probe_supported=process_probe_supported,
        training_processes=training_processes,
        registry_present=registry_present,
        registry_runs=registry_runs,
        checkpoint_count=checkpoint_count,
        result_count=result_count,
    )
    readiness["evidence_paths"] = {
        name: path.relative_to(PROJECT_ROOT).as_posix()
        if path.is_relative_to(PROJECT_ROOT)
        else str(path)
        for name, path in report_paths.items()
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(readiness, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": readiness["status"],
                "failed_checks": readiness["failed_checks"],
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if readiness["status"] == "ready_for_explicit_tuning_authorization" else 1


if __name__ == "__main__":
    raise SystemExit(main())
