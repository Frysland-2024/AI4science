"""Eligibility gates and final decision logic for V10 Pilot v2."""
from __future__ import annotations

import math
from typing import Any, Mapping

CRYSTAL_CLASSES = 7
UNIFORM_CE = math.log(CRYSTAL_CLASSES)


def learned_state_gate(
    classification: Mapping[str, Any], *, audit_sampling_units: int
) -> dict[str, Any]:
    if audit_sampling_units <= 1:
        raise ValueError("audit_sampling_units must exceed one")
    chance = 1.0 / CRYSTAL_CLASSES
    standard_error = math.sqrt(chance * (1.0 - chance) / audit_sampling_units)
    accuracy_threshold = chance + 2.0 * standard_error
    accuracy = float(classification["classification_accuracy_across_two_views"])
    cross_entropy = float(classification["classification_ce"])
    passed = bool(accuracy > accuracy_threshold and cross_entropy < UNIFORM_CE)
    return {
        "status": "PASS" if passed else "INELIGIBLE_LEARNED_STATE",
        "accuracy": accuracy,
        "cross_entropy": cross_entropy,
        "chance_accuracy": chance,
        "accuracy_threshold": accuracy_threshold,
        "uniform_cross_entropy": UNIFORM_CE,
        "audit_sampling_units": int(audit_sampling_units),
        "requires_accuracy_above_threshold_and_ce_below_uniform": True,
        "not_a_generalization_claim": True,
    }


def premise_recheck(branch: Mapping[str, Any]) -> dict[str, Any]:
    family_signal = bool(
        branch["signed_residual_measurement_family_probe"]["status"]
        == "signal_demonstrated"
    )
    strength_count = int(branch["selected_strength_targets_passing"])
    signed_leakage = bool(
        branch["signed_residual_crystal_leakage_probe"]["status"]
        == "signal_demonstrated"
    )
    symmetric_leakage = bool(
        branch["symmetric_residual_crystal_leakage_probe"]["status"]
        == "signal_demonstrated"
    )
    leakage_signal = signed_leakage or symmetric_leakage
    passed = bool(family_signal and strength_count >= 2 and leakage_signal)
    return {
        "status": "PASS" if passed else "HOLD_PREMISE_RECHECK",
        "measurement_family_signal": family_signal,
        "selected_strength_targets_passing": strength_count,
        "minimum_strength_targets_required": 2,
        "signed_crystal_leakage_signal": signed_leakage,
        "symmetric_crystal_leakage_signal": symmetric_leakage,
        "crystal_leakage_signal": leakage_signal,
    }


def pilot_v2_decision(final: Mapping[str, Any]) -> dict[str, Any]:
    erm = final["erm"]
    v9 = final["v9_residual"]
    v10 = final["v10_supervised"]

    measurement_retained = bool(
        v10["signed_residual_measurement_family_probe"]["status"]
        == "signal_demonstrated"
        and int(v10["selected_strength_targets_passing"]) >= 2
    )
    v10_signed = float(v10["signed_residual_crystal_leakage_probe"]["accuracy"])
    v9_signed = float(v9["signed_residual_crystal_leakage_probe"]["accuracy"])
    v10_symmetric = float(
        v10["symmetric_residual_crystal_leakage_probe"]["accuracy"]
    )
    v9_symmetric = float(
        v9["symmetric_residual_crystal_leakage_probe"]["accuracy"]
    )
    signed_leakage_reduced = v10_signed < v9_signed
    symmetric_leakage_not_worse = v10_symmetric <= v9_symmetric

    erm_ce = float(erm["controlled_panel_classification"]["classification_ce"])
    v10_ce = float(v10["controlled_panel_classification"]["classification_ce"])
    classification_cost_acceptable = v10_ce - erm_ce <= 0.10

    status = "PASS"
    rationale = (
        "V10 retained independently decodable measurement information, reduced "
        "signed-residual crystal leakage relative to matched V9, did not worsen "
        "symmetric-residual leakage, and stayed within the classification-cost bound."
    )
    if not measurement_retained:
        status = "HOLD"
        rationale = (
            "Under a demonstrated learned state, V10 did not retain enough "
            "independently decodable measurement-strength information."
        )
    elif not (
        signed_leakage_reduced
        and symmetric_leakage_not_worse
        and classification_cost_acceptable
    ):
        status = "PARTIAL"
        rationale = (
            "V10 retained measurement information, but leakage reduction or the "
            "classification-cost boundary was not fully demonstrated."
        )

    return {
        "pilot_status": status,
        "measurement_information_retained": measurement_retained,
        "signed_crystal_leakage_reduced_vs_v9_signed": signed_leakage_reduced,
        "symmetric_crystal_leakage_not_worse_vs_v9_symmetric": (
            symmetric_leakage_not_worse
        ),
        "classification_cost_acceptable_vs_erm": classification_cost_acceptable,
        "classification_ce_delta_v10_minus_erm": v10_ce - erm_ce,
        "signed_crystal_leakage_accuracy_delta_v10_minus_v9": (
            v10_signed - v9_signed
        ),
        "symmetric_crystal_leakage_accuracy_delta_v10_minus_v9": (
            v10_symmetric - v9_symmetric
        ),
        "automatic_formal_v10_authorization": False,
        "requires_human_review": True,
        "rationale": rationale,
    }
