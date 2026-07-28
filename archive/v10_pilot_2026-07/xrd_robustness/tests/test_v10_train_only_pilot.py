from __future__ import annotations

from pathlib import Path
import sys
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from v10_pilot_evaluation import pilot_decision  # noqa: E402
from v10_pilot_targets import measurement_delta_rows  # noqa: E402
from xrd_robustness.physics import PhysicsParameters  # noqa: E402


def _params(
    *,
    fwhm: float,
    background: float,
    count_scale: float,
    electronic: float,
) -> PhysicsParameters:
    return PhysicsParameters(
        delta_2theta_deg=0.0,
        fwhm_deg=fwhm,
        background_to_peak_ratio=background,
        noise_std_ratio=0.0,
        background_type="flat",
        severity_level=0,
        noise_model="poisson_gaussian",
        poisson_count_scale=count_scale,
        electronic_noise_std_counts=electronic,
    )


def _branch(
    *,
    family_signal: bool,
    strength_count: int,
    signed_leakage: float,
    symmetric_leakage: float,
    ce: float,
) -> dict:
    return {
        "signed_residual_measurement_family_probe": {
            "status": "signal_demonstrated" if family_signal else "not_demonstrated"
        },
        "selected_strength_targets_passing": strength_count,
        "signed_residual_crystal_leakage_probe": {"accuracy": signed_leakage},
        "symmetric_residual_crystal_leakage_probe": {
            "accuracy": symmetric_leakage
        },
        "controlled_panel_classification": {"classification_ce": ce},
    }


class V10TrainOnlyPilotTests(unittest.TestCase):
    def test_measurement_delta_uses_second_minus_first(self) -> None:
        first = _params(
            fwhm=0.08,
            background=0.0,
            count_scale=40000.0,
            electronic=0.0,
        )
        second = _params(
            fwhm=0.20,
            background=0.02,
            count_scale=2500.0,
            electronic=2.0,
        )
        delta = measurement_delta_rows([first], [second])
        self.assertEqual(delta.shape, (1, 4))
        for value in delta[0]:
            self.assertAlmostEqual(float(value), 1.0, places=6)

    def test_measurement_delta_reverses_sign_when_views_swap(self) -> None:
        first = _params(
            fwhm=0.10,
            background=0.005,
            count_scale=20000.0,
            electronic=0.5,
        )
        second = _params(
            fwhm=0.15,
            background=0.015,
            count_scale=5000.0,
            electronic=1.5,
        )
        forward = measurement_delta_rows([first], [second])
        reverse = measurement_delta_rows([second], [first])
        self.assertTrue(((forward + reverse) ** 2 < 1e-12).all())

    def test_pilot_pass_requires_measurement_leakage_and_cost_gates(self) -> None:
        final = {
            "erm": _branch(
                family_signal=True,
                strength_count=3,
                signed_leakage=0.30,
                symmetric_leakage=0.30,
                ce=1.00,
            ),
            "v9_residual": _branch(
                family_signal=True,
                strength_count=3,
                signed_leakage=0.27,
                symmetric_leakage=0.26,
                ce=1.02,
            ),
            "v10_supervised": _branch(
                family_signal=True,
                strength_count=2,
                signed_leakage=0.20,
                symmetric_leakage=0.22,
                ce=1.05,
            ),
        }
        decision = pilot_decision(final)
        self.assertEqual(decision["pilot_status"], "PASS")
        self.assertFalse(decision["automatic_formal_v10_authorization"])

    def test_pilot_holds_when_measurement_information_is_not_retained(self) -> None:
        final = {
            "erm": _branch(
                family_signal=True,
                strength_count=3,
                signed_leakage=0.30,
                symmetric_leakage=0.30,
                ce=1.00,
            ),
            "v9_residual": _branch(
                family_signal=True,
                strength_count=3,
                signed_leakage=0.27,
                symmetric_leakage=0.26,
                ce=1.02,
            ),
            "v10_supervised": _branch(
                family_signal=False,
                strength_count=1,
                signed_leakage=0.20,
                symmetric_leakage=0.22,
                ce=1.05,
            ),
        }
        decision = pilot_decision(final)
        self.assertEqual(decision["pilot_status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
