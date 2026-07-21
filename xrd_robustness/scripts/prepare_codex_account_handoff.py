#!/usr/bin/env python3
"""Build a machine-readable, no-training handoff snapshot for another Codex account."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
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


DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "codex_account_handoff_manifest.json"
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
PLAN_PATH = PROJECT_ROOT / "reports" / "v9_method_transfer_tuning_plan.json"
PREFLIGHT_PATH = PROJECT_ROOT / "reports" / "v9_method_transfer_preflight.json"
STREAM_AUDIT_PATH = PROJECT_ROOT / "reports" / "v9_training_stream_preflight_audit.json"
MIGRATION_PATH = PROJECT_ROOT / "reports" / "v9_desktop_migration_manifest.json"
MIGRATION_VERIFICATION_PATH = (
    PROJECT_ROOT / "reports" / "v9_desktop_migration_verification.json"
)
FINAL_LOCK_PATH = PROJECT_ROOT / "reports" / "v9_method_transfer_final_lock_audit.json"
HARDWARE_PATH = PROJECT_ROOT / "configs" / "hardware.v9.desktop.9600x_4070tis.json"

ARTIFACT_ROLES = {
    "CODEX_HANDOFF.md": "authoritative cross-account entry point",
    "docs/CODEX_ACCOUNT_HANDOFF.docx": "portable human-readable handoff manual",
    "README.md": "project overview and handoff pointer",
    "docs/V9_METHOD_TRANSFER_ENGINEERING.md": "research and method-transfer engineering contract",
    "docs/V9_DESKTOP_MIGRATION_HANDOFF.md": "desktop migration procedure",
    "docs/V9_DESKTOP_HARDWARE_CONFIGURATION.md": "target hardware and acceleration contract",
    "configs/algorithm.v9.method_transfer.json": "authoritative experiment contract",
    "configs/hardware.v9.desktop.9600x_4070tis.json": "target desktop hardware profile",
    "configs/simulation.v9.method_transfer.frozen.json": "frozen physical simulation profiles",
    "configs/evaluation.v9.method_transfer.json": "development and final evaluation locks",
    "configs/data.v9.method_transfer.family_split.json": "family-aware split contract",
    "data/formal_14060/manifests/split_manifest.v9t.family_v1.csv": "authoritative train validation test split",
    "data/formal_14060/manifests/v9_method_transfer_validation.csv": "unified development validation panel",
    "reports/v9_method_transfer_preflight.json": "latest source-machine scientific preflight",
    "reports/v9_training_stream_preflight_audit.json": "stream fairness and bounded-memory proof",
    "reports/v9_method_transfer_tuning_plan.json": "seven-run plan; all runs must remain unstarted",
    "reports/v9_method_transfer_final_lock_audit.json": "simulated-test and real-test lock proof",
    "scripts/desktop_first_boot_v9.ps1": "no-training target-desktop acceptance orchestrator",
    "scripts/run_v9_method_transfer.py": "planning and explicitly authorized execution launcher",
    "scripts/train_v7.py": "shared training entry point",
    "scripts/prepare_codex_account_handoff.py": "handoff snapshot builder",
    "scripts/verify_codex_account_handoff.py": "cross-account handoff verifier",
    "scripts/build_codex_handoff_docx.py": "portable DOCX handoff renderer",
    "scripts/audit_codex_handoff_docx.py": "dependency-free DOCX structure auditor",
    "scripts/audit_codex_handoff_unit_tests.py": "standard-library full unit-test auditor",
    "reports/codex_account_handoff_docx_audit.json": "DOCX structural QA and visual-render limitation",
    "reports/codex_account_handoff_unittest.json": "full source-unit-test evidence",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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


def _output_state(contract: dict[str, Any]) -> dict[str, Any]:
    output_root = PROJECT_ROOT / str(contract["development_tuning"]["output_root"])
    registry_path = output_root / "run_registry.json"
    registry = _load(registry_path)
    registry_runs = registry.get("runs", []) if isinstance(registry, dict) else registry
    checkpoints = [
        path
        for suffix in ("*.pt", "*.pth", "*.ckpt")
        for path in output_root.rglob(suffix)
    ]
    results = list(output_root.rglob("results.json"))
    run_directories = [path for path in output_root.iterdir() if path.is_dir()]
    return {
        "root": output_root.relative_to(PROJECT_ROOT).as_posix(),
        "registry_present": registry_path.is_file(),
        "registry_run_count": len(registry_runs),
        "checkpoint_count": len(checkpoints),
        "result_count": len(results),
        "run_directory_count": len(run_directories),
        "resume_allowed": False,
        "required_start_step": 0,
    }


def _artifact_ledger() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative, role in ARTIFACT_ROLES.items():
        path = PROJECT_ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        rows.append(
            {
                "path": relative,
                "role": role,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    if missing:
        raise FileNotFoundError("missing handoff artifacts: " + ", ".join(missing))
    return rows


def build_handoff() -> dict[str, Any]:
    contract = load_contract(CONTRACT_PATH)
    plan = _load(PLAN_PATH)
    expected_plan = build_tuning_plan(contract, PROJECT_ROOT)
    preflight = _load(PREFLIGHT_PATH)
    stream = _load(STREAM_AUDIT_PATH)
    migration = _load(MIGRATION_PATH)
    migration_verification = _load(MIGRATION_VERIFICATION_PATH)
    final_lock = _load(FINAL_LOCK_PATH)
    hardware = _load(HARDWARE_PATH)
    output_state = _output_state(contract)
    process_probe_supported, training_processes = _training_processes()

    expected_signature = [
        (run["run_id"], run["output_dir"], run["argv"])
        for run in expected_plan["runs"]
    ]
    observed_signature = [
        (run.get("run_id"), run.get("output_dir"), run.get("argv"))
        for run in plan.get("runs", [])
    ]
    gates = {
        "authoritative_markdown_present": (PROJECT_ROOT / "CODEX_HANDOFF.md").is_file(),
        "portable_docx_present": (
            PROJECT_ROOT / "docs" / "CODEX_ACCOUNT_HANDOFF.docx"
        ).is_file(),
        "source_migration_manifest_ready_for_copy": migration.get("status")
        == "ready_for_copy",
        "source_migration_verification_passed": migration_verification.get("status")
        == "pass",
        "scientific_preflight_passed": preflight.get("status") == "passed",
        "stream_audit_passed": stream.get("status") == "pass",
        "seven_run_plan_count": int(plan.get("run_count", 0)) == 7,
        "seven_run_plan_is_current": (
            plan.get("contract_hash") == canonical_hash(contract)
            and observed_signature == expected_signature
        ),
        "all_seven_runs_planned_not_started": all(
            run.get("status") == "planned_not_started" for run in plan.get("runs", [])
        ),
        "run_registry_empty": output_state["registry_run_count"] == 0,
        "checkpoint_count_zero": output_state["checkpoint_count"] == 0,
        "result_count_zero": output_state["result_count"] == 0,
        "run_directory_count_zero": output_state["run_directory_count"] == 0,
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
        "desktop_revalidation_required": hardware.get("desktop_measurement_gate", {})
        .get("current_selection", {})
        .get("desktop_revalidation_required")
        is True,
    }
    run_rows = []
    for run in plan.get("runs", []):
        argv = list(run.get("argv", []))
        lambda_name = None
        lambda_value = None
        for flag, name in (("--lambda-js", "lambda_js"), ("--lambda-res", "lambda_res")):
            if flag in argv:
                index = argv.index(flag)
                lambda_name = name
                lambda_value = float(argv[index + 1])
        run_rows.append(
            {
                "run_id": run.get("run_id"),
                "method_id": run.get("method_id"),
                "status": run.get("status"),
                "lambda_name": lambda_name,
                "lambda_value": lambda_value,
                "output_dir": run.get("output_dir"),
            }
        )

    status = "handoff_ready_for_copy" if all(gates.values()) else "blocked"
    return {
        "schema_version": "codex-account-handoff-v1",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_machine": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": sys.executable,
        },
        "authoritative_entrypoint": "CODEX_HANDOFF.md",
        "portable_manual": "docs/CODEX_ACCOUNT_HANDOFF.docx",
        "policy": {
            "source_laptop": "engineering tests and no-training audits only",
            "target_desktop_first_boot": "environment and no-training acceptance only",
            "development_tuning_authorized_now": False,
            "formal_training_authorized_now": False,
            "simulated_test_authorized_now": False,
            "real_test_authorized_now": False,
            "cold_restart_from_optimizer_step_zero": True,
            "copy_or_resume_laptop_checkpoints": False,
        },
        "research": {
            "program": "V9-T",
            "short_name": "Algorithm Transfer for PXRD Robustness",
            "primary_model": "PAMPT-B3",
            "class_count": 7,
            "split_counts": preflight.get("split_counts"),
            "unique_material_ids": preflight.get("unique_material_ids"),
            "core_modes": ["dynamic_erm", "dynamic_js", "dynamic_residual"],
            "reference_modes": ["near-clean ERM", "offline ERM"],
            "structured_dynamic_status": contract.get("narrative_policy", {}).get(
                "structured_perturbation_status"
            ),
        },
        "training_stream": {
            "epochs": stream.get("training_epochs"),
            "steps_per_epoch": stream.get("steps_per_epoch"),
            "optimizer_steps": stream.get("target_optimizer_steps"),
            "batch_size": stream.get("sampler_contract", {}).get("batch_size"),
            "structure_exposures": stream.get("exposure_distribution", {}).get(
                "total_structure_exposures"
            ),
            "spectrum_exposures": stream.get("methods", {})
            .get("dynamic_erm", {})
            .get("spectrum_exposures"),
            "legacy_eager_rows": stream.get("legacy_eager_dynamic_parameter_rows"),
            "maximum_live_dynamic_rows": stream.get("maximum_live_dynamic_parameter_rows"),
            "sampler_hash": stream.get("methods", {})
            .get("dynamic_erm", {})
            .get("sampler_hash"),
            "pair_schedule_hash": stream.get("methods", {})
            .get("dynamic_erm", {})
            .get("pair_schedule_hash"),
            "dynamic_parameter_pair_hash": stream.get("methods", {})
            .get("dynamic_erm", {})
            .get("parameter_pair_hash"),
        },
        "target_desktop": hardware.get("target"),
        "registered_acceleration": hardware.get("applied"),
        "output_state": output_state,
        "tuning_runs": run_rows,
        "gates": gates,
        "failed_gates": [name for name, passed in gates.items() if not passed],
        "active_training_processes": training_processes,
        "artifact_ledger": _artifact_ledger(),
        "next_account_stop_rule": (
            "After desktop_first_boot_v9.ps1 reports ready_for_explicit_tuning_authorization, "
            "stop and obtain a new explicit user authorization before tune-run."
        ),
    }


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    try:
        output.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise SystemExit("handoff manifest must stay inside project root") from error
    handoff = build_handoff()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(handoff, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": handoff["status"],
                "failed_gates": handoff["failed_gates"],
                "artifacts": len(handoff["artifact_ledger"]),
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0 if handoff["status"] == "handoff_ready_for_copy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
