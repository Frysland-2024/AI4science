#!/usr/bin/env python3
"""Create a non-destructive correction sidecar for the V9 class-F1 diagnostic.

The frozen evaluator stored ``per_class_f1`` correctly, but its named
``per_crystal_system_f1`` diagnostic was computed on one-class subsets.  This
auditor maps the already-correct full-panel class vector to canonical names. It
never rewrites the frozen raw result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from xrd_robustness.structure_data import CRYSTAL_SYSTEMS


DEFAULT_SOURCE = ROOT / "outputs/v9_resnet_js_simulated_test_v1/raw_results.json"
DEFAULT_OUTPUT = ROOT / "reports/v9_resnet_js_simulated_test_class_metric_correction.json"
DEFAULT_RUN_STATE = ROOT / "outputs/v9_resnet_js_simulated_test_v1/run_state.json"
DEFAULT_PER_RUN_ROOT = ROOT / "outputs/v9_resnet_js_simulated_test_v1"
CORRECTED_RUNNER = ROOT / "scripts/run_v9_resnet_js_simulated_test.py"


class MetricAuditError(ValueError):
    """Raised when the frozen result cannot support a safe correction."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _same_named_values(left: Any, right: dict[str, float]) -> bool:
    if not isinstance(left, dict) or set(left) != set(right):
        return False
    try:
        return all(
            np.isclose(float(left[name]), value, rtol=0.0, atol=1e-12)
            for name, value in right.items()
        )
    except (TypeError, ValueError):
        return False


def _f1_from_confusion_matrix(value: Any) -> list[float]:
    matrix = np.asarray(value, dtype=np.int64)
    expected_shape = (len(CRYSTAL_SYSTEMS), len(CRYSTAL_SYSTEMS))
    if matrix.shape != expected_shape or np.any(matrix < 0):
        raise MetricAuditError(
            f"confusion_matrix must have shape {expected_shape} and non-negative counts"
        )
    output = []
    for index in range(len(CRYSTAL_SYSTEMS)):
        tp = float(matrix[index, index])
        fn = float(matrix[index].sum() - matrix[index, index])
        fp = float(matrix[:, index].sum() - matrix[index, index])
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        output.append(
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
    return output


def _validate_frozen_run_hashes(
    runs: dict[str, Any],
    *,
    run_state_path: Path,
    per_run_root: Path,
) -> dict[str, Any]:
    state = json.loads(run_state_path.read_text(encoding="utf-8"))
    expected_hashes = state.get("completed_run_sha256")
    completed_runs = state.get("completed_runs")
    if (
        state.get("status") != "completed"
        or not isinstance(expected_hashes, dict)
        or not isinstance(completed_runs, list)
        or set(completed_runs) != set(runs)
        or set(expected_hashes) != set(runs)
    ):
        raise MetricAuditError("run_state does not bind exactly the raw-result runs")

    verified: dict[str, str] = {}
    for run_id in sorted(runs):
        path = per_run_root / f"{run_id}.json"
        actual_hash = sha256(path)
        if actual_hash != str(expected_hashes[run_id]).upper():
            raise MetricAuditError(f"frozen per-run hash mismatch: {run_id}")
        per_run_payload = json.loads(path.read_text(encoding="utf-8"))
        if per_run_payload != runs[run_id]:
            raise MetricAuditError(f"raw result differs from frozen per-run JSON: {run_id}")
        verified[run_id] = actual_hash
    return {
        "run_state_path": _display_path(run_state_path),
        "run_state_sha256": sha256(run_state_path),
        "completed_run_count": len(verified),
        "per_run_sha256": verified,
        "historical_runner_source_sha256": state.get("bindings", {}).get(
            "runner_source_sha256"
        ),
    }


def build_correction_report(
    source: str | Path,
    *,
    run_state: str | Path | None = None,
    per_run_root: str | Path | None = None,
) -> dict[str, Any]:
    source_path = Path(source).resolve()
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    runs = payload.get("runs")
    if not isinstance(runs, dict) or not runs:
        raise MetricAuditError("raw result must contain a non-empty runs mapping")

    corrections: list[dict[str, Any]] = []
    record_count = 0
    mismatch_count = 0
    for run_id, run in sorted(runs.items()):
        panels = run.get("profiles_by_evaluation_seed")
        if not isinstance(panels, dict) or not panels:
            raise MetricAuditError(f"{run_id} has no profiles_by_evaluation_seed")
        for evaluation_seed, profiles in sorted(panels.items()):
            if not isinstance(profiles, dict) or not profiles:
                raise MetricAuditError(
                    f"{run_id}/{evaluation_seed} has no profile metrics"
                )
            for profile, metrics in sorted(profiles.items()):
                record_count += 1
                per_class = metrics.get("per_class_f1")
                if not isinstance(per_class, list) or len(per_class) != len(
                    CRYSTAL_SYSTEMS
                ):
                    raise MetricAuditError(
                        f"{run_id}/{evaluation_seed}/{profile} has an invalid per_class_f1"
                    )
                values = [float(value) for value in per_class]
                recomputed = _f1_from_confusion_matrix(metrics.get("confusion_matrix"))
                if not np.allclose(values, recomputed, rtol=0.0, atol=1e-12):
                    raise MetricAuditError(
                        f"{run_id}/{evaluation_seed}/{profile} per_class_f1 is "
                        "inconsistent with its confusion_matrix"
                    )
                expected_macro = float(np.mean(values))
                expected_worst = float(min(values))
                if not np.isclose(
                    float(metrics.get("macro_f1", np.nan)),
                    expected_macro,
                    rtol=0.0,
                    atol=1e-12,
                ):
                    raise MetricAuditError(
                        f"{run_id}/{evaluation_seed}/{profile} macro_f1 is inconsistent"
                    )
                if not np.isclose(
                    float(metrics.get("worst_class_f1", np.nan)),
                    expected_worst,
                    rtol=0.0,
                    atol=1e-12,
                ):
                    raise MetricAuditError(
                        f"{run_id}/{evaluation_seed}/{profile} worst_class_f1 is inconsistent"
                    )

                corrected = {
                    name: value
                    for name, value in zip(CRYSTAL_SYSTEMS, values, strict=True)
                }
                legacy = metrics.get("per_crystal_system_f1")
                if not _same_named_values(legacy, corrected):
                    mismatch_count += 1
                    corrections.append(
                        {
                            "run_id": run_id,
                            "evaluation_seed": str(evaluation_seed),
                            "profile": profile,
                            "legacy_per_crystal_system_f1": legacy,
                            "corrected_per_crystal_system_f1": corrected,
                        }
                    )

    provenance: dict[str, Any] = {
        "frozen_run_artifact_hashes_verified": False,
        "corrected_runner_path": _display_path(CORRECTED_RUNNER),
        "corrected_runner_source_sha256": sha256(CORRECTED_RUNNER),
    }
    if run_state is not None or per_run_root is not None:
        if run_state is None or per_run_root is None:
            raise MetricAuditError(
                "run_state and per_run_root must either both be supplied or both be omitted"
            )
        provenance.update(
            _validate_frozen_run_hashes(
                runs,
                run_state_path=Path(run_state).resolve(),
                per_run_root=Path(per_run_root).resolve(),
            )
        )
        provenance["frozen_run_artifact_hashes_verified"] = True

    return {
        "schema_version": "v9-simulated-test-class-metric-correction-v1",
        "status": (
            "pass_with_legacy_diagnostic_corrections"
            if mismatch_count
            else "pass_no_legacy_mismatch"
        ),
        "source_path": _display_path(source_path),
        "source_sha256": sha256(source_path),
        "source_schema_version": payload.get("schema_version"),
        "canonical_class_order": list(CRYSTAL_SYSTEMS),
        "profile_metric_record_count": record_count,
        "legacy_named_f1_mismatch_count": mismatch_count,
        "correction_rule": (
            "map the full-panel per_class_f1 vector to canonical crystal-system names"
        ),
        "primary_metrics_affected": False,
        "validated_unchanged_fields": ["macro_f1", "per_class_f1", "worst_class_f1"],
        "frozen_source_modified": False,
        "provenance": provenance,
        "corrections": corrections,
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--run-state", default=str(DEFAULT_RUN_STATE))
    parser.add_argument("--per-run-root", default=str(DEFAULT_PER_RUN_ROOT))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    try:
        report = build_correction_report(
            args.source,
            run_state=args.run_state,
            per_run_root=args.per_run_root,
        )
    except (OSError, json.JSONDecodeError, MetricAuditError) as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
        return 1

    if not args.check_only:
        write_json_atomic(Path(args.output).resolve(), report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "profile_metric_record_count": report["profile_metric_record_count"],
                "legacy_named_f1_mismatch_count": report[
                    "legacy_named_f1_mismatch_count"
                ],
                "output": None if args.check_only else str(Path(args.output).resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
