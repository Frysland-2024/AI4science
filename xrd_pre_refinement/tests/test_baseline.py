import numpy as np
import pytest

from xrd_pre_refinement.baseline import rank_single_phase_templates
from xrd_pre_refinement.reporting import build_report


def _candidates():
    return [
        {
            "candidate_id": "A",
            "phase_id": "A single phase",
            "composition": "ABO3",
            "space_group": {"symbol": "P1", "number": 1},
            "cif_path": "A.cif",
            "cif_source": {"citation": "fixture", "url": "fixture", "sha256": "fixture"},
            "parameterization": {"reference_values": {"a_angstrom": 4.0}},
        },
        {
            "candidate_id": "B",
            "phase_id": "B single phase",
            "composition": "ABO3",
            "space_group": {"symbol": "P1", "number": 1},
            "cif_path": "B.cif",
            "cif_source": {"citation": "fixture", "url": "fixture", "sha256": "fixture"},
            "parameterization": {"reference_values": {"a_angstrom": 4.1}},
        },
    ]


def test_template_ranking_is_explicitly_not_probability():
    result = rank_single_phase_templates(
        [1.0, 0.0, 0.0],
        {"A": [1.0, 0.0, 0.0], "B": [0.0, 1.0, 0.0]},
        _candidates(),
        top_k=2,
    )
    assert [row["candidate_id"] for row in result] == ["A", "B"]
    assert all(row["single_phase_probability"] is None for row in result)
    assert all(row["probability_status"] == "NOT_CALIBRATED" for row in result)
    assert result[0]["conditional_parameters"]["interval"] is None


def test_profile_shape_and_top_k_are_validated():
    with pytest.raises(ValueError, match="different 2theta grid length"):
        rank_single_phase_templates([1.0, 0.0, 0.0], {"A": [1.0, 0.0]}, _candidates())
    with pytest.raises(ValueError, match="at least one"):
        rank_single_phase_templates([1.0, 0.0], {}, _candidates())


def test_single_phase_probability_coexistence_probability_and_phase_fraction_are_separate():
    ranked = rank_single_phase_templates(
        np.array([1.0, 0.0, 0.0]),
        {"A": [1.0, 0.0, 0.0]},
        _candidates(),
        top_k=1,
    )
    report = build_report(
        sample_id="fixture",
        route={"status": "ROUTED", "family_id": "fixture", "composition_status": "MATCH", "review_required": False, "message": "fixture"},
        ranked_candidates=ranked,
        observed_profile=[1.0, 0.0, 0.0],
        two_theta_deg=[10.0, 11.0, 12.0],
        model_id="fixture",
        mixture_stress_case=True,
    )
    assert report["single_phase_hypotheses"][0]["single_phase_probability"] is None
    assert report["coexistence_hypothesis"]["model_probability"] is None
    assert report["phase_fraction"]["value"] is None
    assert report["review"]["required"] is True
    assert report["review"]["status"] == "REVIEW_REQUIRED"
