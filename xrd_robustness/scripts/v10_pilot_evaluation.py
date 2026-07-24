"""Independent Train-only probing and decision logic for the V10 Pilot."""
from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import torch
from torch.nn import functional as F

from audit_v9_learned_state_scale import CRYSTAL_SYSTEMS, _autocast
from v10_p0_gate_panel import FAMILIES, _extract_features, _family_regressions
from v10_p0_gate_stats import _classification_probe
from v10_pilot_config import SELECTED_STRENGTH_FAMILIES
from xrd_robustness.models import PAMPT


def classification_metrics(
    model: PAMPT,
    panel: Mapping[str, Any],
    device: torch.device,
    *,
    amp_enabled: bool,
    batch_size: int = 64,
) -> dict[str, float]:
    model.eval()
    first = np.asarray(panel["first"], dtype=np.float32)
    second = np.asarray(panel["second"], dtype=np.float32)
    targets = np.asarray(panel["crystal_labels"], dtype=np.int64)
    ce_sum = 0.0
    correct = 0
    examples = 0
    with torch.no_grad():
        for start in range(0, len(first), batch_size):
            stop = start + batch_size
            x1 = torch.from_numpy(np.ascontiguousarray(first[start:stop])).to(device)
            x2 = torch.from_numpy(np.ascontiguousarray(second[start:stop])).to(device)
            target = torch.from_numpy(targets[start:stop]).to(device)
            with _autocast(device, amp_enabled):
                logits1 = model(x1)["logits"]
                logits2 = model(x2)["logits"]
                ce = 0.5 * (
                    F.cross_entropy(logits1, target, reduction="sum")
                    + F.cross_entropy(logits2, target, reduction="sum")
                )
            count = len(target)
            ce_sum += float(ce.detach().float())
            correct += int((logits1.argmax(-1) == target).sum())
            correct += int((logits2.argmax(-1) == target).sum())
            examples += count
    return {
        "classification_ce": ce_sum / examples,
        "classification_accuracy_across_two_views": correct / (2 * examples),
        "paired_examples": examples,
    }


def evaluate_branch(
    model: PAMPT,
    calibration_panel: Mapping[str, Any],
    audit_panel: Mapping[str, Any],
    device: torch.device,
    *,
    amp_enabled: bool,
    permutations: int,
    seed: int,
) -> dict[str, Any]:
    calibration_features = _extract_features(
        model, calibration_panel, device, amp_enabled=amp_enabled
    )
    audit_features = _extract_features(
        model, audit_panel, device, amp_enabled=amp_enabled
    )
    family_probe = _classification_probe(
        calibration_features["signed_residual"],
        calibration_panel["family_labels"],
        audit_features["signed_residual"],
        audit_panel["family_labels"],
        classes=len(FAMILIES),
        permutations=permutations,
        seed=seed,
        train_groups=calibration_panel["sample_groups"],
        test_groups=audit_panel["sample_groups"],
        group_constant_labels=False,
    )
    signed_crystal_probe = _classification_probe(
        calibration_features["signed_residual"],
        calibration_panel["crystal_labels"],
        audit_features["signed_residual"],
        audit_panel["crystal_labels"],
        classes=len(CRYSTAL_SYSTEMS),
        permutations=permutations,
        seed=seed + 1000,
        train_groups=calibration_panel["sample_groups"],
        test_groups=audit_panel["sample_groups"],
        group_constant_labels=True,
    )
    symmetric_crystal_probe = _classification_probe(
        calibration_features["symmetric_residual"],
        calibration_panel["crystal_labels"],
        audit_features["symmetric_residual"],
        audit_panel["crystal_labels"],
        classes=len(CRYSTAL_SYSTEMS),
        permutations=permutations,
        seed=seed + 1500,
        train_groups=calibration_panel["sample_groups"],
        test_groups=audit_panel["sample_groups"],
        group_constant_labels=True,
    )
    strength = _family_regressions(
        calibration_features["signed_residual"],
        audit_features["signed_residual"],
        calibration_panel["family_labels"],
        audit_panel["family_labels"],
        calibration_panel["strength"],
        audit_panel["strength"],
        permutations=permutations,
        seed=seed + 2000,
    )
    selected_pass_count = sum(
        strength[family]["status"] == "signal_demonstrated"
        for family in SELECTED_STRENGTH_FAMILIES
    )
    return {
        "controlled_panel_classification": classification_metrics(
            model, audit_panel, device, amp_enabled=amp_enabled
        ),
        "signed_residual_measurement_family_probe": family_probe,
        "signed_residual_crystal_leakage_probe": signed_crystal_probe,
        "symmetric_residual_crystal_leakage_probe": symmetric_crystal_probe,
        "signed_residual_strength_regression": strength,
        "selected_strength_families": list(SELECTED_STRENGTH_FAMILIES),
        "selected_strength_targets_passing": int(selected_pass_count),
    }


def pilot_decision(final: Mapping[str, Any]) -> dict[str, Any]:
    erm = final["erm"]
    v9 = final["v9_residual"]
    v10 = final["v10_supervised"]
    measurement_retained = bool(
        v10["signed_residual_measurement_family_probe"]["status"]
        == "signal_demonstrated"
        and v10["selected_strength_targets_passing"] >= 2
    )
    leakage_reduced = bool(
        v10["signed_residual_crystal_leakage_probe"]["accuracy"]
        < v9["symmetric_residual_crystal_leakage_probe"]["accuracy"]
    )
    erm_ce = erm["controlled_panel_classification"]["classification_ce"]
    v10_ce = v10["controlled_panel_classification"]["classification_ce"]
    classification_cost_acceptable = bool(v10_ce - erm_ce <= 0.10)
    status = "PASS"
    rationale = (
        "V10 retained independently decodable measurement information, reduced "
        "crystal-system leakage relative to the matched V9 residual branch, and "
        "kept the controlled-panel classification cost within the Pilot boundary."
    )
    if not measurement_retained:
        status = "HOLD"
        rationale = (
            "V10 did not retain enough independently decodable measurement "
            "information under the fixed Train-only Pilot protocol."
        )
    elif not leakage_reduced or not classification_cost_acceptable:
        status = "PARTIAL"
        rationale = (
            "V10 retained measurement information, but leakage reduction or the "
            "classification-cost boundary was not demonstrated."
        )
    return {
        "pilot_status": status,
        "measurement_information_retained": measurement_retained,
        "crystal_leakage_reduced_vs_v9": leakage_reduced,
        "classification_cost_acceptable_vs_erm": classification_cost_acceptable,
        "classification_ce_delta_v10_minus_erm": float(v10_ce - erm_ce),
        "crystal_leakage_accuracy_delta_v10_minus_v9": float(
            v10["signed_residual_crystal_leakage_probe"]["accuracy"]
            - v9["symmetric_residual_crystal_leakage_probe"]["accuracy"]
        ),
        "automatic_formal_v10_authorization": False,
        "requires_human_review": True,
        "rationale": rationale,
    }
