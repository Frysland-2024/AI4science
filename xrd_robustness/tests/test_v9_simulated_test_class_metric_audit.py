from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "audit_v9_simulated_test_class_metrics.py"
)
SPEC = importlib.util.spec_from_file_location("class_metric_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def write_fixture(path: Path, *, macro_f1: float | None = None) -> bytes:
    confusion = [
        [0, 1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 1],
    ]
    values = audit._f1_from_confusion_matrix(confusion)
    stored_macro = sum(values) / len(values) if macro_f1 is None else macro_f1
    payload = {
        "schema_version": "fixture-v1",
        "runs": {
            "run-a": {
                "profiles_by_evaluation_seed": {
                    "1": {
                        "in_range": {
                            "macro_f1": stored_macro,
                            "per_class_f1": values,
                            "worst_class_f1": min(values),
                            "confusion_matrix": confusion,
                            "per_crystal_system_f1": {
                                name: value / 7.0
                                for name, value in zip(
                                    audit.CRYSTAL_SYSTEMS, values, strict=True
                                )
                            },
                        }
                    }
                }
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path.read_bytes()


def test_builds_sidecar_correction_without_mutating_source(tmp_path: Path) -> None:
    source = tmp_path / "raw.json"
    before = write_fixture(source)

    report = audit.build_correction_report(source)

    assert source.read_bytes() == before
    assert report["status"] == "pass_with_legacy_diagnostic_corrections"
    assert report["profile_metric_record_count"] == 1
    assert report["legacy_named_f1_mismatch_count"] == 1
    assert report["primary_metrics_affected"] is False
    assert report["frozen_source_modified"] is False
    assert report["corrections"][0]["corrected_per_crystal_system_f1"] == {
        name: pytest.approx(value)
        for name, value in zip(
            audit.CRYSTAL_SYSTEMS,
            [0.0, 2.0 / 3.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            strict=True,
        )
    }


def test_rejects_inconsistent_primary_macro_f1(tmp_path: Path) -> None:
    source = tmp_path / "raw.json"
    write_fixture(source, macro_f1=0.5)

    with pytest.raises(audit.MetricAuditError, match="macro_f1 is inconsistent"):
        audit.build_correction_report(source)


def test_reports_no_mismatch_when_named_values_are_already_correct(
    tmp_path: Path,
) -> None:
    source = tmp_path / "raw.json"
    write_fixture(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    metrics = payload["runs"]["run-a"]["profiles_by_evaluation_seed"]["1"][
        "in_range"
    ]
    metrics["per_crystal_system_f1"] = {
        name: value
        for name, value in zip(
            audit.CRYSTAL_SYSTEMS,
            metrics["per_class_f1"],
            strict=True,
        )
    }
    source.write_text(json.dumps(payload), encoding="utf-8")

    report = audit.build_correction_report(source)

    assert report["status"] == "pass_no_legacy_mismatch"
    assert report["legacy_named_f1_mismatch_count"] == 0
    assert report["corrections"] == []
