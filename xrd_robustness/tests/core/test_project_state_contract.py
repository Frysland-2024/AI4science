from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def test_frozen_simulated_test_summary_is_bound_to_completed_audit() -> None:
    summary_path = PROJECT_ROOT / "reports/v9_resnet_js_simulated_test_summary.json"
    summary = _load_json("reports/v9_resnet_js_simulated_test_summary.json")
    audit = _load_json("reports/v9_resnet_js_simulated_test_audit.json")

    assert summary["status"] == "completed"
    assert summary["simulated_test_used"] is True
    assert summary["real_xrd_used"] is False
    assert audit["status"] == "completed"
    assert audit["checkpoint_count"] == 10
    assert audit["real_xrd_accessed"] is False
    assert audit["summary_sha256"] == hashlib.sha256(
        summary_path.read_bytes()
    ).hexdigest().upper()


def test_preregistered_test_contract_remains_closed_to_posthoc_changes() -> None:
    contract = _load_json("configs/v9_resnet_js_simulated_test.preregistered.json")

    assert contract["status"] == "preregistered_locked_not_authorized"
    selection = contract["selection_is_closed"]
    assert isinstance(selection, dict)
    for key in (
        "lambda_retuning_allowed",
        "method_reselection_allowed",
        "posthoc_seed_exclusion_allowed",
        "retraining_allowed",
    ):
        assert selection[key] is False

    boundaries = contract["boundaries"]
    assert isinstance(boundaries, dict)
    assert all(value is False for value in boundaries.values())


def test_current_handoff_points_to_live_audits_and_retrospective_boundary() -> None:
    handoff = (PROJECT_ROOT / "CODEX_HANDOFF.md").read_text(encoding="utf-8")

    for required in (
        "v9_resnet_js_simulated_test_summary.json",
        "v9_resnet_js_simulated_test_audit.json",
        "v9_resnet_js_simulated_test_class_metric_correction.json",
        "v9_formal_split_identity_overlap_audit.json",
        "rruff301_existing_artifact_lineage_audit.json",
    ):
        assert required in handoff
    assert "retrospective evidence" in handoff
    assert "not confirmatory evidence" in handoff


def test_removed_legacy_account_handoff_assets_stay_out_of_current_docs() -> None:
    current_docs = (
        PROJECT_ROOT.parent / "README.md",
        PROJECT_ROOT.parent / "00_project_context" / "README.md",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CODEX_HANDOFF.md",
    )
    retired_names = (
        "CODEX_HANDOFF_REAL_ADAPTATION_ADDENDUM.md",
        "CODEX_ACCOUNT_HANDOFF.docx",
        "codex_account_handoff_verification.json",
    )

    combined = "\n".join(path.read_text(encoding="utf-8") for path in current_docs)
    for retired_name in retired_names:
        assert retired_name not in combined
