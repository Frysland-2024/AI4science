"""Read-only preflight for the locked ResNet Dynamic-versus-JS four-run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = PROJECT_ROOT / "configs" / "v9_resnet_js_four_run.preregistered.json"
DEFAULT_PLAN = PROJECT_ROOT / "reports" / "v9_resnet_js_four_run_plan.json"
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "v9_resnet_js_four_run_preflight.json"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_audit(contract_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _load_json(contract_path)
    checks: dict[str, bool] = {}

    runs = contract["runs"]
    checks["exact_four_run_matrix"] = [
        (row["method"], float(row["lambda_js"])) for row in runs
    ] == [
        ("ordinary_dynamic_augmentation", 0.0),
        ("js_consistency_transfer", 3.0),
        ("js_consistency_transfer", 30.0),
        ("js_consistency_transfer", 60.0),
    ]
    checks["residual_absent"] = all("residual" not in json.dumps(row).lower() for row in runs)
    execution = contract["execution"]
    checks["four_run_locked"] = not bool(execution["four_run_enabled"])
    checks["downstream_locked"] = not any(
        bool(execution[key])
        for key in ("ten_run_enabled", "simulated_test_enabled", "real_xrd_enabled")
    )
    checks["human_authorization_required"] = bool(
        execution["explicit_human_authorization_required"]
    )

    historical = _load_json(PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json")
    checks["historical_seven_run_fail_closed"] = not any(
        (
            historical["method_parameter_governance"]["development_tuning_execution_allowed"],
            historical["development_tuning"]["execution_enabled"],
            historical["execution_policy"]["development_tuning_execution_enabled"],
        )
    )

    hash_results: dict[str, Any] = {}
    for name, registration in contract["registered_inputs"].items():
        path = PROJECT_ROOT / registration["path"]
        actual = file_hash(path) if path.is_file() else None
        matched = actual == registration["sha256"]
        hash_results[name] = {
            "path": registration["path"],
            "expected_sha256": registration["sha256"],
            "actual_sha256": actual,
            "matched": matched,
        }
    checks["all_registered_hashes_match"] = all(
        item["matched"] for item in hash_results.values()
    )

    split_path = PROJECT_ROOT / contract["registered_inputs"]["split_manifest"]["path"]
    records = _load_json(split_path)["records"]
    ids_by_split = {
        role: {row["parent_structure_id"] for row in records if row["split"] == role}
        for role in ("train", "validation", "test")
    }
    counts = Counter(row["split"] for row in records)
    checks["split_counts_match_frozen_contract"] = dict(counts) == {
        "train": 9842,
        "validation": 2109,
        "test": 2109,
    }
    checks["parent_ids_unique_and_split_disjoint"] = (
        len({row["parent_structure_id"] for row in records}) == len(records)
        and not (ids_by_split["train"] & ids_by_split["validation"])
        and not (ids_by_split["train"] & ids_by_split["test"])
        and not (ids_by_split["validation"] & ids_by_split["test"])
    )

    validation_path = (
        PROJECT_ROOT / contract["registered_inputs"]["validation_manifest"]["path"]
    )
    with validation_path.open("r", encoding="utf-8", newline="") as handle:
        validation_rows = list(csv.DictReader(handle))
    validation_ids = {row["parent_structure_id"] for row in validation_rows}
    checks["validation_manifest_exactly_matches_validation_split"] = (
        len(validation_rows) == 2109
        and len(validation_ids) == 2109
        and validation_ids == ids_by_split["validation"]
        and all(row["source_split"] == "validation" for row in validation_rows)
    )

    output_root = PROJECT_ROOT / contract["output_root"]
    checks["no_four_run_output_root_exists"] = not output_root.exists()
    checks["no_forbidden_pre_authorization_validation_use"] = not bool(
        contract["data_boundaries"][
            "validation_spectra_or_metrics_allowed_before_authorization"
        ]
    )
    checks["test_and_real_forbidden"] = (
        not contract["data_boundaries"]["simulated_test_allowed"]
        and not contract["data_boundaries"]["real_xrd_allowed"]
    )

    status = "pass" if all(checks.values()) else "fail"
    try:
        contract_display_path = str(contract_path.relative_to(PROJECT_ROOT)).replace(
            "\\", "/"
        )
    except ValueError:
        contract_display_path = str(contract_path)
    plan = {
        "schema_version": "v9-resnet-js-four-run-plan-v1",
        "status": "planned_not_started_locked",
        "contract_path": contract_display_path,
        "contract_sha256": file_hash(contract_path),
        "runs": [
            {
                **row,
                "training_seed": contract["seeds"]["training"],
                "evaluation_seed": contract["seeds"]["evaluation"],
                "state": "planned_not_started",
            }
            for row in runs
        ],
        "execution_authorized": False,
        "four_run_started": False,
    }
    report = {
        "schema_version": "v9-resnet-js-four-run-preflight-v1",
        "status": status,
        "checks": checks,
        "registered_input_hashes": hash_results,
        "split_counts": dict(counts),
        "validation_manifest_metadata_inspected": True,
        "validation_spectra_or_metrics_used": False,
        "simulated_test_used": False,
        "real_xrd_used": False,
        "model_or_checkpoint_loaded": False,
        "gpu_training_started": False,
        "four_run_started": False,
        "ready_for_explicit_four_run_authorization": status == "pass",
        "ready_to_execute_without_authorization": False,
    }
    return plan, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    plan, report = run_audit(args.contract.resolve())
    args.plan.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
