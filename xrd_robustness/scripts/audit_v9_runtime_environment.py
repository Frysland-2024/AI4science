#!/usr/bin/env python3
"""Audit the frozen desktop runtime in the current process without training."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import load_contract  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--contract",
        default=str(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"),
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "reports" / "desktop_acceptance" / "environment.json"),
    )
    return parser.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def main() -> int:
    args = parse_args()
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile: dict[str, Any] = json.loads(profile_path.read_text(encoding="utf-8"))
    runtime = contract["runtime"]
    target = profile["target"]
    cuda_available = bool(torch.cuda.is_available())
    gpu_name = torch.cuda.get_device_name(0) if cuda_available else None
    gpu_memory_mb = (
        int(torch.cuda.get_device_properties(0).total_memory / (1024**2))
        if cuda_available
        else 0
    )
    system_memory_gb = _system_memory_gb()
    pip_check = subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    checks = {
        "python_version": sys.version.split()[0] == runtime["python_version"],
        "torch_version": str(torch.__version__) == runtime["torch_version"],
        "cuda_runtime": str(torch.version.cuda) == runtime["cuda_runtime"],
        "cuda_available": cuda_available,
        "gpu_name": gpu_name == runtime["gpu_name"],
        "gpu_memory": gpu_memory_mb >= int(runtime["minimum_gpu_memory_mb"]),
        "bf16_supported": bool(cuda_available and torch.cuda.is_bf16_supported()),
        "system_memory": system_memory_gb >= float(target["minimum_system_memory_gb"]),
        "logical_threads": os.cpu_count() == int(target["logical_threads"]),
        "pip_check": pip_check.returncode == 0,
        "msvc_toolchain_discoverable": shutil.which("cl.exe") is not None,
    }
    report = {
        "schema_version": "v9-desktop-runtime-environment-audit-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "purpose": "fresh target runtime and dependency audit; no training",
        "contract": {
            "path": contract_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(contract_path),
        },
        "hardware_profile": {
            "path": profile_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256": _sha256(profile_path),
        },
        "implementation_sha256": _sha256(Path(__file__).resolve()),
        "observed": {
            "python_executable": sys.executable,
            "python": sys.version.split()[0],
            "torch": str(torch.__version__),
            "cuda": str(torch.version.cuda),
            "cuda_available": cuda_available,
            "gpu_name": gpu_name,
            "gpu_memory_mb": gpu_memory_mb,
            "bf16_supported": bool(cuda_available and torch.cuda.is_bf16_supported()),
            "system_memory_gb": system_memory_gb,
            "logical_threads": os.cpu_count(),
            "platform": platform.platform(),
            "pip_check_stdout": pip_check.stdout.strip(),
            "pip_check_stderr": pip_check.stderr.strip(),
        },
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
    }
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "output": str(output)}))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
