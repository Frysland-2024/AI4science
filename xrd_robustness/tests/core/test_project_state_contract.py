from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def _load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _source_sha256(path: Path) -> str:
    content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(content).hexdigest().upper()


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
        "rruff301_fewshot_results.json",
        "validation_results.json",
        "CNRS_318_DATASET_AUDIT.md",
        "CNRS_318_EVALUATION_PROTOCOL.md",
        "CNRS_318_RESULTS.md",
        "CALIBRATION_ANALYSIS.md",
        "opxrd_cnrs7cs_independent_parent_audit_20260827.md",
    }


def test_completed_cnrs_result_is_not_described_as_pending() -> None:
    run_record = _load_json(
        PROJECT_ROOT / "manifests/cnrs318_zero_shot_run_record.json"
    )
    assert run_record["status"] == "completed"
    assert run_record["n_parents"] == 318
    assert run_record["n_prediction_rows"] == 3180
    audit_code = run_record["audit_code"]
    assert isinstance(audit_code, dict)
    for path_field, hash_field in (
        ("analysis_entry_point", "analysis_entry_point_sha256"),
        ("statistics_module", "statistics_module_sha256"),
        ("report_artifact_entry_point", "report_artifact_entry_point_sha256"),
        ("future_inference_entry_point", "future_inference_entry_point_sha256"),
    ):
        path = PROJECT_ROOT / str(audit_code[path_field])
        assert path.is_file()
        assert audit_code[hash_field] == _source_sha256(path)
    for path in (
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "docs/CURRENT_STATE.md",
        PROJECT_ROOT / "MANUSCRIPT.md",
    ):
        text = path.read_text(encoding="utf-8")
        assert "CNRS-318" in text
        assert "CNRS-318，推理尚未运行" not in text
        assert "CNRS-318) is planned but not yet run" not in text


def test_frozen_cnrs_protocol_remains_a_pre_run_record() -> None:
    protocol = (
        PROJECT_ROOT / "reports/CNRS_318_EVALUATION_PROTOCOL.md"
    ).read_text(encoding="utf-8")
    assert "**Status:** spec frozen; **inference not yet run**" in protocol
    assert "- [ ] One-time frozen zero-shot inference" in protocol
    assert "executed 2026-08-27" not in protocol


def test_community_reporting_extensions_are_machine_readable() -> None:
    simulated = _load_json(PROJECT_ROOT / "reports/simulated_test_results.json")
    assert simulated["schema_version"] == "v9-public-simulated-test-results-v2"
    extension = simulated["reporting_extension"]
    assert isinstance(extension, dict)
    assert len(str(extension["source_raw_results_sha256"])) == 64
    tracked_cross_check = PROJECT_ROOT / str(extension["tracked_cross_check"])
    assert tracked_cross_check.is_file()
    assert extension["tracked_cross_check_sha256"] == _source_sha256(
        tracked_cross_check
    )
    assert "normalizing CRLF and CR line endings to LF" in str(
        extension["tracked_cross_check_hash_definition"]
    )
    accuracy = simulated["paired_improvements"][
        "mean_single_factor_ood_accuracy"
    ]
    assert accuracy["positive_pairs"] == 5
    assert abs(float(accuracy["mean"]) - 0.054454454454454446) < 1e-12

    rruff = _load_json(PROJECT_ROOT / "reports/rruff301_fewshot_results.json")
    assert rruff["status"] == "completed"
    assert rruff["scope"] == "locked_test_fewshot"
    assert rruff["methods"]["js_consistency"] == {
        "source_method_name": "js_lambda_60",
        "lambda_js": 60,
    }
    assert rruff["macro_f1_positive_pairs_total"] == 68
    assert len(str(rruff["source_record"]["source_local_results_sha256"])) == 64
    assert rruff["source_record"]["verification"]["metrics_recomputed_from_predictions"] == 150
    assert rruff["results_by_k"]["5"]["macro_f1"]["paired_delta"][
        "positive_pairs"
    ] == 24


def test_current_pxrd_reporting_policy_has_three_layers() -> None:
    policy = (
        REPOSITORY_ROOT / "docs/PXRD_RESULT_REPORTING_STANDARD.md"
    ).read_text(encoding="utf-8")
    for heading in (
        "Layer A — community-standard performance",
        "Layer B — reliability",
        "Layer C — strict statistical audit",
    ):
        assert heading in policy
    assert "CI crosses zero" in policy
    assert "experiment failed" in policy
    assert "不得删除或隐藏不利统计结果" in policy


def test_current_reporting_does_not_use_confirmatory_evidence_tiers() -> None:
    documents = (
        REPOSITORY_ROOT / "docs/CURRENT_STATE.md",
        REPOSITORY_ROOT / "docs/PXRD_RESULT_REPORTING_STANDARD.md",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "MANUSCRIPT.md",
        PROJECT_ROOT / "reports/RESULTS.md",
        PROJECT_ROOT / "reports/rruff301_fewshot_results.json",
    )
    banned = (
        "provenance-complete",
        "prospective confirmatory",
        "confirmatory evidence",
        "confirmatory threshold",
    )
    for path in documents:
        text = path.read_text(encoding="utf-8").lower()
        for phrase in banned:
            assert phrase not in text


def test_public_document_links_resolve() -> None:
    expected_links = {
        REPOSITORY_ROOT / "README.md": {
            "docs/CURRENT_STATE.md",
            "docs/GRADUATE_RESEARCH_DIRECTION.md",
            "docs/PROJECT_HISTORY.md",
            "xrd_robustness/README.md",
            "xrd_robustness/MANUSCRIPT.md",
            "xrd_robustness/reports/RESULTS.md",
            "xrd_robustness/reports/validation_results.json",
            "xrd_robustness/reports/simulated_test_results.json",
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
