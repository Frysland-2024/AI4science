from __future__ import annotations

import math
from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from v10_pilot_v2_evaluation import (  # noqa: E402
    learned_state_gate,
    pilot_v2_decision,
    premise_recheck,
)


def _branch(
    *,
    family_signal: bool = True,
    strength_count: int = 2,
    signed_leakage: float = 0.20,
    signed_status: str = "signal_demonstrated",
    symmetric_leakage: float = 0.20,
    symmetric_status: str = "signal_demonstrated",
    ce: float = 1.0,
) -> dict:
    return {
        "signed_residual_measurement_family_probe": {
            "status": "signal_demonstrated" if family_signal else "not_demonstrated"
        },
        "selected_strength_targets_passing": strength_count,
        "signed_residual_crystal_leakage_probe": {
            "accuracy": signed_leakage,
            "status": signed_status,
        },
        "symmetric_residual_crystal_leakage_probe": {
            "accuracy": symmetric_leakage,
            "status": symmetric_status,
        },
        "controlled_panel_classification": {"classification_ce": ce},
    }


class V10PilotV2Tests(unittest.TestCase):
    def test_learned_state_gate_passes_only_above_accuracy_and_below_ce(self) -> None:
        metrics = {
            "classification_accuracy_across_two_views": 0.40,
            "classification_ce": 1.20,
        }
        result = learned_state_gate(metrics, audit_sampling_units=70)
        self.assertEqual(result["status"], "PASS")
        self.assertLess(result["uniform_cross_entropy"], math.log(8.0))

        random_metrics = {
            "classification_accuracy_across_two_views": 1.0 / 7.0,
            "classification_ce": math.log(7.0),
        }
        result = learned_state_gate(random_metrics, audit_sampling_units=70)
        self.assertEqual(result["status"], "INELIGIBLE_LEARNED_STATE")

    def test_premise_recheck_requires_family_two_strengths_and_leakage(self) -> None:
        self.assertEqual(premise_recheck(_branch())["status"], "PASS")
        self.assertEqual(
            premise_recheck(_branch(strength_count=1))["status"],
            "HOLD_PREMISE_RECHECK",
        )
        self.assertEqual(
            premise_recheck(
                _branch(
                    signed_status="not_demonstrated",
                    symmetric_status="not_demonstrated",
                )
            )["status"],
            "HOLD_PREMISE_RECHECK",
        )

    def test_v2_compares_signed_with_signed_and_symmetric_with_symmetric(self) -> None:
        final = {
            "erm": _branch(ce=1.00),
            "v9_residual": _branch(
                signed_leakage=0.30,
                symmetric_leakage=0.25,
                ce=1.02,
            ),
            "v10_supervised": _branch(
                signed_leakage=0.20,
                symmetric_leakage=0.24,
                ce=1.05,
            ),
        }
        result = pilot_v2_decision(final)
        self.assertEqual(result["pilot_status"], "PASS")
        self.assertTrue(result["signed_crystal_leakage_reduced_vs_v9_signed"])
        self.assertTrue(
            result["symmetric_crystal_leakage_not_worse_vs_v9_symmetric"]
        )

    def test_v2_holds_when_measurement_strength_is_not_retained(self) -> None:
        final = {
            "erm": _branch(ce=1.00),
            "v9_residual": _branch(signed_leakage=0.30, ce=1.02),
            "v10_supervised": _branch(
                strength_count=1,
                signed_leakage=0.20,
                ce=1.05,
            ),
        }
        result = pilot_v2_decision(final)
        self.assertEqual(result["pilot_status"], "HOLD")
        self.assertFalse(result["automatic_formal_v10_authorization"])


if __name__ == "__main__":
    unittest.main()
