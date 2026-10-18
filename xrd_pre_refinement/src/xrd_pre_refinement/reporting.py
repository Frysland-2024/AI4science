"""Serialize uncalibrated pilot output with explicit scientific boundaries."""

from __future__ import annotations

from typing import Any


def build_report(
    *,
    sample_id: str,
    route: dict[str, Any],
    ranked_candidates: list[dict[str, Any]],
    observed_profile: list[float],
    two_theta_deg: list[float],
    model_id: str,
    mixture_stress_case: bool = False,
) -> dict[str, Any]:
    review_reasons = []
    if route["review_required"]:
        review_reasons.append(route["status"])
    review_reasons.append("CALIBRATION_NOT_FITTED")
    has_limited_fit = any("limited_forward_fit" in row for row in ranked_candidates)
    if has_limited_fit:
        review_reasons.append("LIMITED_PARAMETER_FIT_NOT_VALIDATED")
        review_reasons.append("PARAMETER_INTERVALS_NOT_ESTIMATED")
    if mixture_stress_case:
        review_reasons.append("SYNTHETIC_MIXTURE_STRESS_CASE")
    return {
        "schema_version": "xrd-pre-refinement-report-v1",
        "sample_id": sample_id,
        "family_route": route,
        "model": {
            "model_id": model_id,
            "model_status": (
                "ENGINEERING_BASELINE_WITH_LIMITED_FIT_DEMO"
                if has_limited_fit
                else "ENGINEERING_BASELINE_ONLY"
            ),
            "calibration_status": "NOT_FITTED",
            "parameter_fit_status": (
                "LIMITED_FORWARD_FIT_DEMO"
                if has_limited_fit
                else "NOT_RUN"
            ),
            "score_interpretation": "uncalibrated_template_distance; not a probability",
        },
        "single_phase_hypotheses": ranked_candidates,
        "coexistence_hypothesis": {
            "included": mixture_stress_case,
            "model_probability": None,
            "status": "SIMULATED_STRESS_CASE_ONLY" if mixture_stress_case else "NOT_EVALUATED",
            "simulated_intensity_weights": None,
            "weight_basis": None,
        },
        "phase_fraction": {
            "status": "NOT_ESTIMATED",
            "value": None,
            "basis": None,
            "warning": "Candidate ranking scores and synthetic intensity weights are not phase mass fractions.",
        },
        "single_phase_adequacy": "NOT_ESTABLISHED",
        "review": {
            "status": "REVIEW_REQUIRED",
            "required": True,
            "reasons": sorted(set(review_reasons)),
        },
        "observation": {
            "two_theta_deg": two_theta_deg,
            "intensity": observed_profile,
        },
        "refinement_suggestions": [
            {
                "candidate_id": row["candidate_id"],
                "reference_cif": row["reference_cif"],
                "cif_source": row["cif_source"],
                "parameter_initialization": row["conditional_parameters"],
                "limited_forward_fit": row.get("limited_forward_fit"),
                "status": "HUMAN_REVIEW_BEFORE_REFINEMENT",
            }
            for row in ranked_candidates
        ],
    }
