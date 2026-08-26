from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_public_release_keeps_three_positive_result_reports() -> None:
    validation = _load_json(PROJECT_ROOT / "reports/validation_results.json")
    simulated_test = _load_json(PROJECT_ROOT / "reports/simulated_test_results.json")
    results = (PROJECT_ROOT / "reports/RESULTS.md").read_text(encoding="utf-8")
    assert validation["status"] == "completed"
    assert simulated_test["status"] == "completed"
    assert "ResNet-18-GN" in results
    assert "Dynamic ERM" in results
    assert "JS Consistency" in results


def test_public_experiment_declares_exactly_five_paired_runs() -> None:
    contract = _load_json(PROJECT_ROOT / "configs/experiment.public.json")
    assert contract["schema_version"] == "public-experiment-v1"
    assert contract["model"] == {"architecture": "ResNet-18-GN"}
    assert len(contract["runs"]) == 5
    assert len(contract["training_seeds"]) == 5
    assert len(contract["evaluation_seeds"]) == 3
    assert {method["name"] for method in contract["methods"]} == {
        "Dynamic ERM",
        "JS Consistency",
    }


def test_public_report_directory_matches_positive_allowlist() -> None:
    reports = PROJECT_ROOT / "reports"
    assert {
        path.name
        for path in reports.iterdir()
        if path.is_file()
    } == {
        "RESULTS.md",
        "simulated_test_results.json",
        "validation_results.json",
        "CNRS_318_DATASET_AUDIT.md",
        "CNRS_318_EVALUATION_PROTOCOL.md",
        "CNRS_318_RESULTS.md",
        "CALIBRATION_ANALYSIS.md",
        "opxrd_cnrs7cs_independent_parent_audit_20260827.md",
    }


def test_public_document_links_resolve() -> None:
    expected_links = {
        REPOSITORY_ROOT / "README.md": {
            "docs/CURRENT_STATE.md",
            "docs/APPLICATION_RESEARCH_NARRATIVE.md",
            "docs/PROJECT_HISTORY.md",
            "xrd_robustness/README.md",
            "xrd_robustness/MANUSCRIPT.md",
            "xrd_robustness/reports/RESULTS.md",
            "xrd_robustness/reports/validation_results.json",
            "xrd_robustness/reports/simulated_test_results.json",
        },
        REPOSITORY_ROOT / "docs/README.md": {
            "CURRENT_STATE.md",
            "APPLICATION_RESEARCH_NARRATIVE.md",
            "PROJECT_HISTORY.md",
            "../xrd_robustness/MANUSCRIPT.md",
            "../xrd_robustness/reports/RESULTS.md",
        },
        PROJECT_ROOT / "README.md": {
            "../docs/CURRENT_STATE.md",
            "MANUSCRIPT.md",
            "reports/RESULTS.md",
            "reports/validation_results.json",
            "reports/simulated_test_results.json",
        },
        PROJECT_ROOT / "reports/RESULTS.md": {
            "validation_results.json",
            "simulated_test_results.json",
            "../configs/experiment.public.json",
        },
    }
    for document, expected in expected_links.items():
        text = document.read_text(encoding="utf-8")
        for target in expected:
            assert target in text
            assert (document.parent / target).resolve().is_file()
