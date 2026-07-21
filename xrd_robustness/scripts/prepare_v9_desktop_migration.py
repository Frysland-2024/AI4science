#!/usr/bin/env python3
"""Prepare a hash-verified V9 desktop migration payload without training."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import (  # noqa: E402
    audit_contract_assets,
    build_tuning_plan,
    canonical_hash,
    load_contract,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_desktop_migration_manifest.json"
DEFAULT_FILE_MANIFEST = PROJECT_ROOT / "reports" / "v9_desktop_migration_files.csv"
DEFAULT_ENVIRONMENT = PROJECT_ROOT / "reports" / "v9_laptop_environment_reference.txt"
DEFAULT_VERIFICATION = PROJECT_ROOT / "reports" / "v9_desktop_migration_verification.json"

COPY_ROOTS = (
    "data/formal_14060",
    "configs",
    "src",
    "scripts",
    "tests",
    "docs",
    "reports",
    "tools",
    "outputs/v9_method_transfer_tuning",
    "CODEX_HANDOFF.md",
    "README.md",
    "pyproject.toml",
)
EXCLUDED_DIRECTORY_NAMES = {"__pycache__", ".pytest_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--file-manifest", default=str(DEFAULT_FILE_MANIFEST))
    parser.add_argument("--environment-output", default=str(DEFAULT_ENVIRONMENT))
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _write_environment_reference(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [
        "# Laptop environment reference only.",
        "# Recreate a CUDA-enabled environment on the desktop and verify it there.",
        f"# python_executable={sys.executable}",
        f"# python_version={sys.version.split()[0]}",
        f"# platform={platform.platform()}",
        "",
    ]
    if completed.returncode == 0:
        lines.extend(completed.stdout.strip().splitlines())
    else:
        lines.append(f"# pip_freeze_failed={completed.stderr.strip()}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "path": _relative(path),
        "sha256": _sha256(path),
        "pip_freeze_status": "passed" if completed.returncode == 0 else "failed",
    }


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


def _is_excluded(path: Path, control_paths: set[str]) -> bool:
    relative = _relative(path)
    if relative in control_paths:
        return True
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in path.parts):
        return True
    return path.suffix.lower() in EXCLUDED_SUFFIXES


def _payload_files(control_paths: set[str]) -> Iterable[Path]:
    observed: dict[str, Path] = {}
    for relative_root in COPY_ROOTS:
        root = PROJECT_ROOT / relative_root
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else root.rglob("*")
        for path in candidates:
            if path.is_file() and not _is_excluded(path, control_paths):
                observed[_relative(path)] = path
    for relative in sorted(observed):
        yield observed[relative]


def _manifest_stream_hash(rows: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(
            f"{row['path']}\0{row['size_bytes']}\0{row['sha256']}\n".encode("utf-8")
        )
    return digest.hexdigest().upper()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output).resolve()
    file_manifest_path = Path(args.file_manifest).resolve()
    environment_path = Path(args.environment_output).resolve()
    for path in (output_path, file_manifest_path, environment_path):
        try:
            path.relative_to(PROJECT_ROOT)
        except ValueError as error:
            raise SystemExit(f"migration control file must stay inside project root: {path}") from error

    environment = _write_environment_reference(environment_path)
    control_paths = {
        _relative(output_path),
        _relative(file_manifest_path),
        _relative(DEFAULT_VERIFICATION),
        "reports/codex_account_handoff_verification.json",
    }
    rows: list[dict[str, Any]] = []
    group_summary: dict[str, dict[str, int]] = {}
    for path in _payload_files(control_paths):
        relative = _relative(path)
        size = path.stat().st_size
        group = relative.split("/", 1)[0]
        rows.append({"path": relative, "size_bytes": size, "sha256": _sha256(path)})
        summary = group_summary.setdefault(group, {"file_count": 0, "size_bytes": 0})
        summary["file_count"] += 1
        summary["size_bytes"] += size

    file_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with file_manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "size_bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    process_probe_supported, training_processes = _training_processes()
    contract_path = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
    contract = load_contract(contract_path)
    hardware_profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    hardware_profile = json.loads(hardware_profile_path.read_text(encoding="utf-8"))
    measurement_paths = {
        name: PROJECT_ROOT / str(relative)
        for name, relative in hardware_profile["desktop_measurement_gate"][
            "implementation"
        ].items()
    }
    plan_path = PROJECT_ROOT / "reports" / "v9_method_transfer_tuning_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    preflight_path = PROJECT_ROOT / "reports" / "v9_method_transfer_preflight.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    hardware_audit_path = (
        PROJECT_ROOT / "reports" / "v9_desktop_hardware_config_audit.json"
    )
    hardware_audit = json.loads(hardware_audit_path.read_text(encoding="utf-8"))
    current_asset_audit = audit_contract_assets(contract, PROJECT_ROOT)
    expected_plan = build_tuning_plan(contract, PROJECT_ROOT)
    expected_plan_signature = [
        (run["run_id"], run["output_dir"], run["argv"])
        for run in expected_plan["runs"]
    ]
    observed_plan_signature = [
        (run.get("run_id"), run.get("output_dir"), run.get("argv"))
        for run in plan.get("runs", [])
    ]
    active_root = PROJECT_ROOT / str(contract["development_tuning"]["output_root"])
    registry_path = active_root / "run_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry_runs = registry.get("runs", []) if isinstance(registry, dict) else registry
    checkpoints = [
        path
        for suffix in ("*.pt", "*.pth", "*.ckpt")
        for path in active_root.rglob(suffix)
    ]
    results = list(active_root.rglob("results.json"))
    run_directories = [path for path in active_root.iterdir() if path.is_dir()]
    expected_implementation_hashes = {
        "trainer": _sha256(PROJECT_ROOT / "scripts" / "train_v7.py"),
        "launcher": _sha256(
            PROJECT_ROOT / "scripts" / "run_v9_method_transfer.py"
        ),
        "method_transfer": _sha256(
            PROJECT_ROOT / "src" / "xrd_robustness" / "method_transfer.py"
        ),
        "audit_script": _sha256(
            PROJECT_ROOT / "scripts" / "audit_v9_desktop_hardware_config.py"
        ),
        **{name: _sha256(path) for name, path in measurement_paths.items()},
    }
    observed_implementation_hashes = hardware_audit.get("implementation_hashes", {})

    gates = {
        "training_process_probe_succeeded": process_probe_supported,
        "no_active_training_processes": not training_processes,
        "active_run_registry_is_empty": len(registry_runs) == 0,
        "active_checkpoint_count_is_zero": len(checkpoints) == 0,
        "active_result_count_is_zero": len(results) == 0,
        "active_run_directory_count_is_zero": len(run_directories) == 0,
        "seven_run_plan_is_planning_only": (
            int(plan.get("run_count", 0)) == 7
            and all(run.get("status") == "planned_not_started" for run in plan.get("runs", []))
        ),
        "tuning_plan_contract_hash_is_current": (
            plan.get("contract_hash") == canonical_hash(contract)
        ),
        "tuning_plan_commands_are_current": (
            observed_plan_signature == expected_plan_signature
        ),
        "preflight_status_passed": preflight.get("status") == "passed",
        "preflight_asset_hashes_are_current": (
            preflight.get("hashes") == current_asset_audit.get("hashes")
        ),
        "desktop_hardware_audit_is_current": (
            str(hardware_audit.get("contract", {}).get("sha256", "")).upper()
            == _sha256(contract_path).upper()
            and str(hardware_audit.get("hardware_profile", {}).get("sha256", "")).upper()
            == _sha256(
                PROJECT_ROOT / str(contract["hardware_profile"]["path"])
            ).upper()
            and hardware_audit.get("status") != "failed"
            and all(hardware_audit.get("engineering_checks", {}).values())
            and all(hardware_audit.get("launcher_checks", {}).values())
            and all(
                str(observed_implementation_hashes.get(name, "")).upper()
                == expected.upper()
                for name, expected in expected_implementation_hashes.items()
            )
        ),
        "payload_contains_formal_14060": any(
            row["path"].startswith("data/formal_14060/") for row in rows
        ),
    }
    status = "ready_for_copy" if all(gates.values()) else "blocked"
    report = {
        "schema_version": "v9-desktop-migration-manifest-v1",
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python_executable": sys.executable,
            "logical_cpu_count": os.cpu_count(),
        },
        "policy": {
            "source_laptop": "engineering tests and read-only audits are allowed",
            "prohibited_on_source_laptop": [
                "tune-run",
                "seven-run lambda tuning",
                "fifteen-run formal experiment",
                "any training that creates a checkpoint",
            ],
            "process_migration_mode": "cold restart from optimizer step zero on desktop; no live process or checkpoint migration",
            "desktop_training_requires_separate_future_authorization": True,
        },
        "copy_roots": list(COPY_ROOTS),
        "explicit_exclusions": [
            "all other outputs outside outputs/v9_method_transfer_tuning",
            ".venv/.conda environments; recreate on desktop",
            "__pycache__, .pytest_cache, *.pyc, *.pyo, *.tmp",
        ],
        "control_files_not_self_listed": sorted(control_paths),
        "file_manifest": {
            "path": _relative(file_manifest_path),
            "sha256": _sha256(file_manifest_path),
            "row_count": len(rows),
            "payload_size_bytes": sum(int(row["size_bytes"]) for row in rows),
            "payload_stream_sha256": _manifest_stream_hash(rows),
            "group_summary": group_summary,
        },
        "environment_reference": environment,
        "critical_hashes": {
            "contract": _sha256(contract_path),
            "tuning_plan": _sha256(plan_path),
            "trainer": _sha256(PROJECT_ROOT / "scripts" / "train_v7.py"),
            "launcher": _sha256(
                PROJECT_ROOT / "scripts" / "run_v9_method_transfer.py"
            ),
            "prefetch_module": _sha256(
                PROJECT_ROOT / "src" / "xrd_robustness" / "training_prefetch.py"
            ),
            "desktop_hardware_profile": _sha256(
                PROJECT_ROOT / str(contract["hardware_profile"]["path"])
            ),
            "desktop_hardware_audit_script": _sha256(
                PROJECT_ROOT / "scripts" / "audit_v9_desktop_hardware_config.py"
            ),
            "desktop_hardware_audit_report": _sha256(
                PROJECT_ROOT / "reports" / "v9_desktop_hardware_config_audit.json"
            ),
            "desktop_measurement_implementations": {
                name: _sha256(path) for name, path in measurement_paths.items()
            },
        },
        "process_state": {
            "probe_supported": process_probe_supported,
            "active_training_process_count": len(training_processes),
            "active_training_processes": training_processes,
            "registry_run_count": len(registry_runs),
            "checkpoint_count": len(checkpoints),
            "result_count": len(results),
            "run_directory_count": len(run_directories),
            "planned_run_count": int(plan.get("run_count", 0)),
        },
        "gates": gates,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "files": len(rows),
                "bytes": report["file_manifest"]["payload_size_bytes"],
                "payload_stream_sha256": report["file_manifest"]["payload_stream_sha256"],
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "ready_for_copy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
