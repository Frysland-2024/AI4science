#!/usr/bin/env python3
"""Verify the cross-account handoff snapshot without starting training."""

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
    build_tuning_plan,
    canonical_hash,
    load_contract,
)


DEFAULT_MANIFEST = PROJECT_ROOT / "reports" / "codex_account_handoff_manifest.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "codex_account_handoff_verification.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _training_processes() -> tuple[bool, list[dict[str, Any]]]:
    if os.name != "nt":
        return False, []
    command = r"""
$items = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and (
        $_.CommandLine -match 'train_v[0-9]+\.py' -or
        $_.CommandLine -match 'run_v9_method_transfer\.py.+tune-run' -or
        $_.CommandLine -match 'run_v9_method_transfer\.py.+\srun(\s|$)'
    )
}
$items | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress
"""
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
    parsed = json.loads(payload)
    return True, parsed if isinstance(parsed, list) else [parsed]


def verify(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    size_mismatches: list[dict[str, Any]] = []
    hash_mismatches: list[dict[str, str]] = []
    for row in manifest.get("artifact_ledger", []):
        relative = str(row["path"])
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        observed_size = path.stat().st_size
        if observed_size != int(row["size_bytes"]):
            size_mismatches.append(
                {
                    "path": relative,
                    "expected": int(row["size_bytes"]),
                    "observed": observed_size,
                }
            )
            continue
        observed_hash = _sha256(path)
        if observed_hash != str(row["sha256"]).upper():
            hash_mismatches.append(
                {
                    "path": relative,
                    "expected": str(row["sha256"]).upper(),
                    "observed": observed_hash,
                }
            )

    contract_path = root / "configs" / "algorithm.v9.method_transfer.json"
    contract = load_contract(contract_path)
    plan = _load(root / "reports" / "v9_method_transfer_tuning_plan.json")
    expected_plan = build_tuning_plan(contract, root)
    expected_signature = [
        (run["run_id"], run["output_dir"], run["argv"])
        for run in expected_plan["runs"]
    ]
    observed_signature = [
        (run.get("run_id"), run.get("output_dir"), run.get("argv"))
        for run in plan.get("runs", [])
    ]
    migration = _load(root / "reports" / "v9_desktop_migration_manifest.json")
    final_lock = _load(root / "reports" / "v9_method_transfer_final_lock_audit.json")
    output_root = root / str(contract["development_tuning"]["output_root"])
    registry_path = output_root / "run_registry.json"
    registry = _load(registry_path) if registry_path.is_file() else {"runs": None}
    registry_runs = registry.get("runs") if isinstance(registry, dict) else registry
    checkpoints = [
        path
        for suffix in ("*.pt", "*.pth", "*.ckpt")
        for path in output_root.rglob(suffix)
    ]
    results = list(output_root.rglob("results.json"))
    run_directories = [path for path in output_root.iterdir() if path.is_dir()]
    process_probe_supported, training_processes = _training_processes()

    checks = {
        "manifest_declares_ready": manifest.get("status") == "handoff_ready_for_copy",
        "artifact_ledger_not_empty": bool(manifest.get("artifact_ledger")),
        "no_missing_handoff_artifacts": not missing,
        "no_handoff_size_mismatches": not size_mismatches,
        "no_handoff_hash_mismatches": not hash_mismatches,
        "migration_manifest_ready_for_copy": migration.get("status") == "ready_for_copy",
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
        "run_registry_present_and_empty": registry_path.is_file()
        and registry_runs == [],
        "checkpoint_count_zero": not checkpoints,
        "result_count_zero": not results,
        "run_directory_count_zero": not run_directories,
        "training_process_probe_succeeded": process_probe_supported,
        "no_active_training_processes": not training_processes,
        "simulated_test_locked": final_lock.get("simulated_test_locked") is True,
        "real_test_locked": final_lock.get("real_test_locked") is True,
        "formal_experiment_is_development_only": contract.get("experiment", {}).get(
            "development_only"
        )
        is True,
        "formal_plan_requires_frozen_tuning_selection": contract.get(
            "development_tuning", {}
        )
        .get("selection", {})
        .get("selection_artifact_required_before_formal_plan")
        is True,
        "handoff_does_not_authorize_tuning": manifest.get("policy", {}).get(
            "development_tuning_authorized_now"
        )
        is False,
    }
    return {
        "schema_version": "codex-account-handoff-verification-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "purpose": "cross-account and migration integrity verification; no training",
        "verified_root": str(root),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "missing": missing,
        "size_mismatches": size_mismatches,
        "hash_mismatches": hash_mismatches,
        "active_training_processes": training_processes,
        "execution_state": {
            "planned_runs": int(plan.get("run_count", 0)),
            "registry_runs": len(registry_runs or []),
            "checkpoints": len(checkpoints),
            "results": len(results),
            "run_directories": len(run_directories),
            "training_authorized": False,
        },
        "next_action": (
            "continue with no-training desktop acceptance and then stop for explicit authorization"
            if all(checks.values())
            else "stop; repair the listed handoff failures before any further action"
        ),
    }


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve()
    manifest = _load(manifest_path)
    report = verify(root, manifest)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "failed_checks": report["failed_checks"],
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
