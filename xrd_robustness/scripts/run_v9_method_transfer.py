#!/usr/bin/env python3
"""Validate, plan, execute, or compare the V9 XRD method-transfer study."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from xrd_robustness.method_transfer import (
    audit_final_evaluation_locks,
    audit_contract_assets,
    build_run_plan,
    build_tuning_plan,
    evaluate_validation_comparison,
    evaluate_tuning_selection,
    load_contract,
)


DEFAULT_CONTRACT = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
DEFAULT_PREFLIGHT = PROJECT_ROOT / "reports" / "v9_method_transfer_preflight.json"
DEFAULT_TUNING_PLAN = PROJECT_ROOT / "reports" / "v9_method_transfer_tuning_plan.json"
DEFAULT_TUNING_SELECTION = PROJECT_ROOT / "reports" / "v9_method_transfer_tuning_selection.json"
DEFAULT_PLAN = PROJECT_ROOT / "reports" / "v9_method_transfer_run_plan.json"
DEFAULT_COMPARISON = PROJECT_ROOT / "reports" / "v9_method_transfer_validation_comparison.json"
DEFAULT_FINAL_PREFLIGHT = PROJECT_ROOT / "reports" / "v9_method_transfer_final_lock_audit.json"
MAIN_NATIVE_THREAD_ENV_VARS = (
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "BLIS_NUM_THREADS",
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _training_environment(contract: dict[str, Any]) -> dict[str, str]:
    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    main_threads = int(profile["applied"]["main_process"]["intraop_threads"])
    environment = os.environ.copy()
    for name in MAIN_NATIVE_THREAD_ENV_VARS:
        environment[name] = str(main_threads)
    environment["CUDA_MODULE_LOADING"] = "LAZY"
    return environment


def _runtime_audit(contract: dict[str, Any]) -> dict[str, Any]:
    runtime = contract["runtime"]
    python_path = Path(str(runtime["python_executable"]))
    probe = (
        "import json,sys,torch; "
        "print(json.dumps({'python':sys.executable,'python_version':sys.version.split()[0],"
        "'torch_version':str(torch.__version__),'cuda_available':bool(torch.cuda.is_available()),"
        "'cuda_runtime':str(torch.version.cuda),'gpu_name':torch.cuda.get_device_name(0) "
        "if torch.cuda.is_available() else None,'gpu_memory_mb':int("
        "torch.cuda.get_device_properties(0).total_memory/(1024**2)) "
        "if torch.cuda.is_available() else 0}))"
    )
    import_error = None
    try:
        completed = subprocess.run(
            [str(python_path), "-c", probe],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        observed = json.loads(completed.stdout.strip().splitlines()[-1])
    except Exception as error:  # pragma: no cover - exercised only in incomplete runtimes
        observed = {
            "python": str(python_path),
            "python_version": None,
            "torch_version": None,
            "cuda_available": False,
            "cuda_runtime": None,
            "gpu_name": None,
            "gpu_memory_mb": 0,
        }
        import_error = str(error)

    pip_check = subprocess.run(
        [str(python_path), "-m", "pip", "check"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    ) if python_path.is_file() else None
    mismatches = []
    for key in ("python_version", "torch_version", "cuda_runtime", "gpu_name"):
        if observed.get(key) != runtime[key]:
            mismatches.append(
                f"{key} mismatch: expected {runtime[key]!r}, observed {observed.get(key)!r}"
            )
    if not observed.get("cuda_available"):
        mismatches.append("CUDA is unavailable in the frozen runtime")
    if int(observed.get("gpu_memory_mb", 0)) < int(runtime["minimum_gpu_memory_mb"]):
        mismatches.append("GPU memory is below the frozen minimum")
    if pip_check is None or pip_check.returncode != 0:
        mismatches.append("pip check failed in the frozen runtime")

    required_device = str(contract["experiment"]["device"])
    runtime_blockers = []
    if import_error:
        runtime_blockers.append(f"torch import failed: {import_error}")
    runtime_blockers.extend(mismatches)
    tuning_blockers = list(runtime_blockers)
    if not contract["execution_policy"]["development_tuning_execution_enabled"]:
        tuning_blockers.append(
            "Validation-only development tuning is not authorized in the contract"
        )
    formal_blockers = list(runtime_blockers)
    if not contract["execution_policy"]["experiment_execution_enabled"]:
        formal_blockers.append("formal experiment execution is not authorized in the contract")
    scientific_blockers = []
    if contract["simulation"]["scientific_range_status"] != "frozen":
        scientific_blockers.append(
            "scientific perturbation ranges are not frozen"
        )
    return {
        **observed,
        "configured_python": str(python_path),
        "pip_check": "passed" if pip_check is not None and pip_check.returncode == 0 else "failed",
        "runtime_frozen_and_verified": not import_error and not mismatches,
        "required_device": required_device,
        "ready_to_execute": not tuning_blockers,
        "ready_for_development_tuning": not tuning_blockers,
        "ready_for_formal_experiment": not formal_blockers,
        "runtime_blockers": runtime_blockers,
        "execution_blockers": tuning_blockers,
        "formal_execution_blockers": formal_blockers,
        "ready_for_formal_conclusions": not formal_blockers and not scientific_blockers,
        "scientific_blockers": scientific_blockers,
    }


def _replace_flag_value(argv: list[str], flag: str, value: int) -> list[str]:
    effective = list(argv)
    try:
        index = effective.index(flag)
    except ValueError as error:
        raise RuntimeError(f"registered training argv is missing {flag}") from error
    effective[index + 1] = str(value)
    return effective


def _scheduled_argv(
    argv: list[str], scheduler: dict[str, Any], group_size: int
) -> tuple[list[str], int]:
    workers = int(
        scheduler[
            "concurrent_run_prefetch_workers"
            if group_size > 1
            else "serial_tail_prefetch_workers"
        ]
    )
    return _replace_flag_value(argv, "--dynamic-prefetch-workers", workers), workers


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    subparsers = parser.add_subparsers(dest="command", required=True)

    preflight = subparsers.add_parser("preflight", help="validate contract, hashes, and data assets")
    preflight.add_argument("--output", default=str(DEFAULT_PREFLIGHT))

    tuning_plan = subparsers.add_parser(
        "tune-plan", help="write the seven-run Validation-only tuning plan without training"
    )
    tuning_plan.add_argument("--output", default=str(DEFAULT_TUNING_PLAN))

    tuning_run = subparsers.add_parser(
        "tune-run", help="execute the tuning plan only when separately authorized"
    )
    tuning_run.add_argument("--plan", default=str(DEFAULT_TUNING_PLAN))
    tuning_run.add_argument("--confirm-development-tuning", action="store_true")
    tuning_run.add_argument(
        "--max-parallel-runs",
        type=int,
        choices=[1, 2],
        help="override the registered two-run scheduler; one is a safe serial fallback",
    )

    tuning_select = subparsers.add_parser(
        "tune-select", help="select registered lambdas from seven completed tuning artifacts"
    )
    tuning_select.add_argument(
        "--results-root",
        default=str(PROJECT_ROOT / "outputs" / "v9_method_transfer_tuning"),
    )
    tuning_select.add_argument("--output", default=str(DEFAULT_TUNING_SELECTION))

    plan = subparsers.add_parser("plan", help="write the matched fifteen-run plan without training")
    plan.add_argument("--output", default=str(DEFAULT_PLAN))

    run = subparsers.add_parser("run", help="execute a previously generated plan when authorized")
    run.add_argument("--plan", default=str(DEFAULT_PLAN))
    run.add_argument(
        "--confirm-experiment",
        action="store_true",
        help="required in addition to an enabled contract; never inferred from plan generation",
    )
    run.add_argument(
        "--max-parallel-runs",
        type=int,
        choices=[1, 2],
        help="override the registered two-run scheduler; one is a safe serial fallback",
    )

    compare = subparsers.add_parser(
        "compare", help="compare completed methods on unified Validation and freeze one method"
    )
    compare.add_argument(
        "--results-root",
        default=str(PROJECT_ROOT / "outputs" / "v9_method_transfer"),
    )
    compare.add_argument("--output", default=str(DEFAULT_COMPARISON))

    final_preflight = subparsers.add_parser(
        "final-preflight", help="audit simulated- and real-test locks without using either test set"
    )
    final_preflight.add_argument("--output", default=str(DEFAULT_FINAL_PREFLIGHT))
    return parser


def _run_plan(
    contract: dict[str, Any],
    plan_path: Path,
    *,
    confirmed: bool,
    tuning: bool = False,
    max_parallel_runs: int | None = None,
) -> int:
    if tuning:
        enabled = (
            contract["development_tuning"]["execution_enabled"] is True
            and contract["execution_policy"]["development_tuning_execution_enabled"] is True
        )
        confirmation_flag = "--confirm-development-tuning"
        expected_plan = build_tuning_plan(contract, PROJECT_ROOT)
        registry_root = Path(str(contract["development_tuning"]["output_root"]))
        blocked_message = (
            "Validation-only tuning execution is disabled; explicit user authorization and both "
            "contract switches are required"
        )
    else:
        enabled = contract["execution_policy"]["experiment_execution_enabled"] is True
        confirmation_flag = "--confirm-experiment"
        expected_plan = build_run_plan(contract, PROJECT_ROOT)
        registry_root = Path(str(contract["experiment"]["output_root"]))
        blocked_message = (
            "formal experiment execution is disabled by the method-transfer contract; explicit "
            "user authorization is required"
        )
    if not enabled:
        raise SystemExit(blocked_message)
    if not confirmed:
        raise SystemExit(f"{confirmation_flag} is required for training execution")
    runtime_audit = _runtime_audit(contract)
    readiness_key = (
        "ready_for_development_tuning" if tuning else "ready_for_formal_experiment"
    )
    if not runtime_audit[readiness_key]:
        blocker_key = "execution_blockers" if tuning else "formal_execution_blockers"
        blockers = "; ".join(runtime_audit[blocker_key])
        raise SystemExit(f"current machine is not ready for this execution: {blockers}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan.get("contract_hash") != expected_plan["contract_hash"]:
        raise SystemExit("run plan does not match the current method-transfer contract")
    expected_signature = [
        (run["run_id"], run["output_dir"], run["argv"])
        for run in expected_plan["runs"]
    ]
    observed_signature = [
        (run.get("run_id"), run.get("output_dir"), run.get("argv"))
        for run in plan.get("runs", [])
    ]
    if observed_signature != expected_signature:
        raise SystemExit("run plan commands do not match the current registered plan")

    profile_path = PROJECT_ROOT / str(contract["hardware_profile"]["path"])
    hardware_profile = json.loads(profile_path.read_text(encoding="utf-8"))
    applied = hardware_profile["applied"]
    registered_concurrency = int(applied["run_concurrency"])
    concurrency = (
        int(max_parallel_runs)
        if max_parallel_runs is not None
        else registered_concurrency
    )
    if concurrency < 1 or concurrency > registered_concurrency:
        raise SystemExit(
            f"max parallel runs must be between 1 and {registered_concurrency}"
        )
    scheduler = applied["parallel_run_scheduler"]

    registry_path = registry_root
    if not registry_path.is_absolute():
        registry_path = PROJECT_ROOT / registry_path
    registry_path = registry_path / "run_registry.json"
    registry = {"schema_version": "v9.0-method-transfer-run-registry", "runs": []}
    training_python = str(contract["runtime"]["python_executable"])
    pending_runs = []
    for run in plan["runs"]:
        output_dir = PROJECT_ROOT / run["output_dir"]
        results_path = output_dir / "results.json"
        if results_path.is_file():
            registry["runs"].append(
                {
                    **run,
                    "effective_argv": run["argv"],
                    "resource_allocation": {"parallel_group_size": 0},
                    "status": "completed_existing",
                    "returncode": 0,
                }
            )
        else:
            pending_runs.append(run)
    _write_json(registry_path, registry)

    def execute(run: dict[str, Any], group_size: int) -> dict[str, Any]:
        output_dir = PROJECT_ROOT / run["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        effective_argv, workers = _scheduled_argv(
            list(run["argv"]), scheduler, group_size
        )
        completed = subprocess.run(
            [training_python, *effective_argv],
            cwd=PROJECT_ROOT,
            check=False,
            env=_training_environment(contract),
        )
        return {
            **run,
            "effective_argv": effective_argv,
            "resource_allocation": {
                "parallel_group_size": group_size,
                "prefetch_workers": workers,
                "scheduler_strategy": scheduler["strategy"],
            },
            "status": "completed" if completed.returncode == 0 else "failed",
            "returncode": int(completed.returncode),
        }

    for start in range(0, len(pending_runs), concurrency):
        group = pending_runs[start : start + concurrency]
        group_size = len(group)
        if group_size == 1:
            completed_group = [execute(group[0], group_size)]
        else:
            with ThreadPoolExecutor(max_workers=group_size) as executor:
                futures = [executor.submit(execute, run, group_size) for run in group]
                completed_group = [future.result() for future in futures]
        registry["runs"].extend(completed_group)
        _write_json(registry_path, registry)
        failures = [item for item in completed_group if item["returncode"] != 0]
        if failures:
            return int(failures[0]["returncode"])
    return 0


def main() -> int:
    args = _parser().parse_args()
    contract = load_contract(args.contract)
    if args.command == "preflight":
        payload = audit_contract_assets(contract, PROJECT_ROOT)
        payload["runtime"] = _runtime_audit(contract)
        _write_json(Path(args.output), payload)
        print(json.dumps({"status": payload["status"], "output": str(Path(args.output).resolve())}))
        return 0
    if args.command == "tune-plan":
        payload = build_tuning_plan(contract, PROJECT_ROOT)
        payload["runtime"] = _runtime_audit(contract)
        payload["contract_execution_enabled"] = payload["execution_enabled"]
        payload["runtime_execution_ready"] = payload["runtime"][
            "ready_for_development_tuning"
        ]
        _write_json(Path(args.output), payload)
        print(
            json.dumps(
                {
                    "status": "planned_not_started",
                    "plan_kind": payload["plan_kind"],
                    "run_count": payload["run_count"],
                    "contract_execution_enabled": payload["contract_execution_enabled"],
                    "runtime_execution_ready": payload["runtime_execution_ready"],
                    "output": str(Path(args.output).resolve()),
                }
            )
        )
        return 0
    if args.command == "tune-run":
        return _run_plan(
            contract,
            Path(args.plan),
            confirmed=bool(args.confirm_development_tuning),
            tuning=True,
            max_parallel_runs=args.max_parallel_runs,
        )
    if args.command == "tune-select":
        payload = evaluate_tuning_selection(contract, args.results_root, PROJECT_ROOT)
        _write_json(Path(args.output), payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "selected_values": payload["selected_values"],
                    "output": str(Path(args.output).resolve()),
                }
            )
        )
        return 0
    if args.command == "plan":
        try:
            payload = build_run_plan(contract, PROJECT_ROOT)
        except ValueError as error:
            raise SystemExit(str(error)) from error
        payload["runtime"] = _runtime_audit(contract)
        _write_json(Path(args.output), payload)
        print(
            json.dumps(
                {
                    "status": "planned_not_started",
                    "run_count": payload["run_count"],
                    "experiment_execution_enabled": payload["execution_policy"]["experiment_execution_enabled"],
                    "output": str(Path(args.output).resolve()),
                }
            )
        )
        return 0
    if args.command == "run":
        return _run_plan(
            contract,
            Path(args.plan),
            confirmed=bool(args.confirm_experiment),
            tuning=False,
            max_parallel_runs=args.max_parallel_runs,
        )
    if args.command == "compare":
        payload = evaluate_validation_comparison(contract, args.results_root, PROJECT_ROOT)
        _write_json(Path(args.output), payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "selected_method": payload["selected_method"],
                    "output": str(Path(args.output).resolve()),
                }
            )
        )
        return 0
    if args.command == "final-preflight":
        payload = audit_final_evaluation_locks(contract, PROJECT_ROOT)
        _write_json(Path(args.output), payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "simulated_test_locked": payload["simulated_test_locked"],
                    "real_test_locked": payload["real_test_locked"],
                    "output": str(Path(args.output).resolve()),
                }
            )
        )
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
