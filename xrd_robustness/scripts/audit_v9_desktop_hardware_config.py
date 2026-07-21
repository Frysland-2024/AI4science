#!/usr/bin/env python3
"""Audit the V9 desktop performance profile without starting training."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import (  # noqa: E402
    audit_contract_assets,
    build_tuning_plan,
    load_contract,
)


DEFAULT_CONTRACT = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports" / "v9_desktop_hardware_config_audit.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _cpu_name() -> str:
    if os.name == "nt":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return completed.stdout.strip()
    return platform.processor() or "unknown"


def _system_memory_gb() -> float:
    if os.name == "nt":
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem -Property TotalPhysicalMemory).TotalPhysicalMemory",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode == 0 and completed.stdout.strip().isdigit():
            return int(completed.stdout.strip()) / (1024**3)
    return 0.0


def _flag_value(argv: list[str], flag: str) -> str | None:
    if flag not in argv:
        return None
    index = argv.index(flag)
    return argv[index + 1] if index + 1 < len(argv) else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    asset_audit = audit_contract_assets(contract, PROJECT_ROOT)
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile: dict[str, Any] = json.loads(profile_path.read_text(encoding="utf-8"))
    plan = build_tuning_plan(contract, PROJECT_ROOT)
    applied = profile["applied"]
    target = profile["target"]
    representative_argv = list(plan["runs"][0]["argv"])

    required_boolean_flags = {
        "pin_memory": "--pin-memory",
        "non_blocking_h2d": "--non-blocking-h2d",
        "allow_tf32": "--allow-tf32",
        "cudnn_benchmark": "--cudnn-benchmark",
        "cudnn_deterministic": "--cudnn-deterministic",
        "fused_adamw": "--fused-adamw",
        "bf16_amp": "--amp",
        "amp_float32_fallback": "--amp-fallback-to-float32",
        "torch_compile": "--torch-compile",
        "compile_eager_fallback": "--torch-compile-fallback-to-eager",
    }
    expected_values = {
        "batch_size": ("--batch-size", profile["scientific_invariants"]["training_batch_size"]),
        "evaluation_batch_size": (
            "--evaluation-batch-size",
            applied["evaluation_batch_size"],
        ),
        "prefetch_workers": (
            "--dynamic-prefetch-workers",
            applied["dynamic_prefetch"]["worker_processes"],
        ),
        "prefetch_batches": (
            "--dynamic-prefetch-batches",
            applied["dynamic_prefetch"]["prefetch_batches"],
        ),
        "main_intraop_threads": (
            "--main-process-intraop-threads",
            applied["main_process"]["intraop_threads"],
        ),
        "main_interop_threads": (
            "--main-process-interop-threads",
            applied["main_process"]["interop_threads"],
        ),
        "float32_matmul_precision": (
            "--float32-matmul-precision",
            applied["cuda_math"]["float32_matmul_precision"],
        ),
        "amp_dtype": ("--amp-dtype", applied["automatic_mixed_precision"]["dtype"]),
        "compile_backend": (
            "--torch-compile-backend",
            applied["torch_compile"]["backend"],
        ),
        "compile_mode": ("--torch-compile-mode", applied["torch_compile"]["mode"]),
    }
    launcher_checks = {
        name: flag in representative_argv
        for name, flag in required_boolean_flags.items()
    }
    launcher_checks.update(
        {
            name: str(_flag_value(representative_argv, flag)) == str(expected)
            for name, (flag, expected) in expected_values.items()
        }
    )

    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    gpu_memory_mb = (
        int(torch.cuda.get_device_properties(0).total_memory / (1024**2))
        if torch.cuda.is_available()
        else 0
    )
    cpu_name = _cpu_name()
    system_memory_gb = _system_memory_gb()
    target_match = {
        "cpu_name": "9600X" in cpu_name.upper(),
        "logical_threads": os.cpu_count() == int(target["logical_threads"]),
        "system_memory": system_memory_gb
        >= float(target["minimum_system_memory_gb"]),
        "gpu_name": gpu_name == target["gpu"],
        "gpu_memory": gpu_memory_mb >= int(contract["runtime"]["minimum_gpu_memory_mb"]),
        "bf16_supported": bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
    }
    source = (PROJECT_ROOT / "scripts" / "train_v7.py").read_text(encoding="utf-8")
    launcher_source = (PROJECT_ROOT / "scripts" / "run_v9_method_transfer.py").read_text(
        encoding="utf-8"
    )
    measurement_implementation = profile["desktop_measurement_gate"]["implementation"]
    measurement_paths = {
        name: PROJECT_ROOT / str(relative)
        for name, relative in measurement_implementation.items()
    }
    engineering_checks = {
        "asset_audit_passed": asset_audit["status"] == "passed",
        "seven_run_plan_only": plan["run_count"] == 7,
        "all_tuning_runs_dynamic": all(
            run["mode"] in {"dynamic_erm", "dynamic_js", "dynamic_residual"}
            for run in plan["runs"]
        ),
        "all_launcher_settings_bound": all(launcher_checks.values()),
        "epoch_only_scalar_logging": "epoch_aggregate_only" in source,
        "all_method_prefetch_is_registered": applied["dynamic_prefetch"].get(
            "applies_to_modes"
        )
        == [
            "clean_erm",
            "offline_erm",
            "dynamic_erm",
            "dynamic_js",
            "dynamic_residual",
        ],
        "fixed_prefetch_is_implemented": "FixedBatchPrefetcher" in source,
        "main_training_peak_loading_is_disabled_with_prefetch": (
            "if args.dynamic_prefetch_workers == 0:" in source
        ),
        "bf16_amp_is_implemented": "with torch.autocast(" in source,
        "torch_compile_is_implemented": "def _initialize_torch_compile(" in source,
        "two_run_scheduler_is_registered": (
            applied.get("run_concurrency") == 2
            and applied.get("parallel_run_scheduler", {}).get("strategy")
            == "bounded-pairs-v1"
        ),
        "two_run_scheduler_is_implemented": "ThreadPoolExecutor" in launcher_source,
        "parallel_worker_budget_is_eight": (
            int(applied["parallel_run_scheduler"]["concurrent_run_prefetch_workers"])
            * int(applied["run_concurrency"])
            == int(applied["dynamic_prefetch"]["worker_processes"])
        ),
        "measurement_implementations_exist": all(
            path.is_file() for path in measurement_paths.values()
        ),
        "actual_compile_graph_gate_is_required": (
            "torch_compile_graph_executed"
            in profile["desktop_measurement_gate"]["required_checks"]
        ),
        "formal_training_still_disabled": (
            contract["execution_policy"]["experiment_execution_enabled"] is False
        ),
    }
    if not all(engineering_checks.values()):
        status = "failed"
    elif all(target_match.values()):
        status = "target_detected_ready_for_no_training_benchmarks"
    else:
        status = "configuration_passed_target_measurement_pending"
    report = {
        "schema_version": "v9-desktop-hardware-config-audit-v1",
        "status": status,
        "purpose": "configuration and launcher audit only; no training",
        "contract": {
            "path": contract_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(contract_path),
        },
        "hardware_profile": {
            "path": profile_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(profile_path),
            "expected_sha256": contract["hardware_profile"]["sha256"],
        },
        "implementation_hashes": {
            "trainer": _sha256(PROJECT_ROOT / "scripts" / "train_v7.py"),
            "launcher": _sha256(PROJECT_ROOT / "scripts" / "run_v9_method_transfer.py"),
            "method_transfer": _sha256(
                PROJECT_ROOT / "src" / "xrd_robustness" / "method_transfer.py"
            ),
            "audit_script": _sha256(Path(__file__).resolve()),
            **{
                name: _sha256(path)
                for name, path in measurement_paths.items()
                if path.is_file()
            },
        },
        "observed_machine": {
            "cpu_name": cpu_name,
            "logical_threads": os.cpu_count(),
            "system_memory_gb": system_memory_gb,
            "gpu_name": gpu_name,
            "gpu_memory_mb": gpu_memory_mb,
            "python": sys.version.split()[0],
            "torch": str(torch.__version__),
            "torch_cuda": str(torch.version.cuda),
        },
        "target_match": target_match,
        "engineering_checks": engineering_checks,
        "launcher_checks": launcher_checks,
        "applied_configuration": applied,
        "deferred_until_target_gate": profile["deliberately_disabled_until_target_gate"],
        "tuning_plan": {
            "run_count": plan["run_count"],
            "modes": [run["mode"] for run in plan["runs"]],
            "training_started": False,
        },
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "output": str(output)}, ensure_ascii=False))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
