from __future__ import annotations

import math

import numpy as np
import pytest
import torch

from xrd_inversion.factorization_losses import (
    factorization_loss,
    paired_invariance_losses,
    parameter_mse_loss,
    parameter_supervision_loss,
)
from xrd_inversion.factorization_metrics import (
    compute_factorization_metrics,
    decide_factorization_gate,
    physical_parameter_mae,
    summarize_seed_metrics,
    validate_factorial_targets,
)


def _factorial_targets() -> tuple[np.ndarray, np.ndarray]:
    structure_states = np.asarray(
        [
            [[-0.5, 0.2], [0.7, -0.4]],
            [[0.1, -0.7], [-0.4, 0.8]],
            [[-0.8, -0.3], [0.2, 0.5]],
        ],
        dtype=np.float64,
    )
    measurement_states = np.asarray(
        [
            [[-0.6, 0.1], [0.5, 0.7]],
            [[0.3, -0.8], [-0.7, 0.4]],
            [[-0.2, -0.5], [0.6, 0.2]],
        ],
        dtype=np.float64,
    )
    true_s = np.repeat(structure_states[:, :, None, :], 2, axis=2)
    true_m = np.repeat(measurement_states[:, None, :, :], 2, axis=1)
    return true_s, true_m


def test_parameter_supervision_is_mse_over_all_four_coordinates() -> None:
    target_s = torch.zeros(1, 2, 2, 2)
    target_m = torch.zeros_like(target_s)
    pred_s = torch.ones_like(target_s)
    pred_m = torch.full_like(target_m, 3.0)

    expected = torch.tensor(5.0)  # mean of eight 1^2 and eight 3^2 entries
    torch.testing.assert_close(
        parameter_supervision_loss(pred_s, pred_m, target_s, target_m), expected
    )
    torch.testing.assert_close(
        parameter_mse_loss(pred_s, pred_m, target_s, target_m), expected
    )


def test_non_symmetric_pair_fixture_locks_structure_and_measurement_axes() -> None:
    pred_s = torch.tensor(
        [[[[0.0, 0.0], [1.0, 2.0]], [[10.0, 20.0], [13.0, 24.0]]]]
    )
    pred_m = torch.tensor(
        [[[[0.0, 0.0], [5.0, 6.0]], [[7.0, 8.0], [14.0, 16.0]]]]
    )

    paired = paired_invariance_losses(pred_s, pred_m)
    # Structure invariance uses x12-x11=[1,2], x22-x21=[3,4].
    torch.testing.assert_close(paired.structure, torch.tensor(7.5))
    # Measurement invariance uses x21-x11=[7,8], x22-x12=[9,10].
    torch.testing.assert_close(paired.measurement, torch.tensor(73.5))
    torch.testing.assert_close(paired.total, torch.tensor(81.0))
    unpacked_structure, unpacked_measurement = paired
    torch.testing.assert_close(unpacked_structure, paired.structure)
    torch.testing.assert_close(unpacked_measurement, paired.measurement)


def test_factorization_loss_has_finite_gradients_and_only_lambda_changes_total() -> None:
    torch.manual_seed(7)
    pred_s = torch.randn(2, 2, 2, 2, requires_grad=True)
    pred_m = torch.randn(2, 2, 2, 2, requires_grad=True)
    target_s = torch.randn(2, 2, 2, 2)
    target_m = torch.randn(2, 2, 2, 2)

    baseline = factorization_loss(
        pred_s, pred_m, target_s, target_m, lambda_pair=0.0
    )
    factorized = factorization_loss(
        pred_s, pred_m, target_s, target_m, lambda_pair=1.0
    )
    torch.testing.assert_close(baseline.total, baseline.parameter)
    torch.testing.assert_close(
        factorized.total, factorized.parameter + factorized.pair
    )
    torch.testing.assert_close(baseline.parameter, factorized.parameter)
    torch.testing.assert_close(
        baseline.structure_invariance, factorized.structure_invariance
    )
    torch.testing.assert_close(
        baseline.measurement_invariance, factorized.measurement_invariance
    )

    factorized.total.backward()
    assert pred_s.grad is not None and torch.isfinite(pred_s.grad).all()
    assert pred_m.grad is not None and torch.isfinite(pred_m.grad).all()
    assert float(pred_s.grad.norm()) > 0.0
    assert float(pred_m.grad.norm()) > 0.0


def test_losses_reject_a_flattened_or_nonfinite_block() -> None:
    valid = torch.zeros(1, 2, 2, 2)
    with pytest.raises(ValueError, match=r"\[B,2,2,2\]"):
        parameter_mse_loss(
            valid.reshape(1, 4, 2), valid, valid, valid
        )
    invalid = valid.clone()
    invalid[0, 0, 0, 0] = torch.nan
    with pytest.raises(ValueError, match="NaN or Inf"):
        paired_invariance_losses(invalid, valid)


def test_oracle_metrics_are_zero_leakage_identity_response_and_zero_error() -> None:
    true_s, true_m = _factorial_targets()
    report = compute_factorization_metrics(true_s, true_m, true_s, true_m)

    assert report["leakage"]["measurement_to_structure"] == 0.0
    assert report["leakage"]["structure_to_measurement"] == 0.0
    for factor in ("structure", "measurement"):
        response = report["own_factor_response"][factor]
        assert response["mean_l2_error"] == 0.0
        assert response["through_origin_slope"] == pytest.approx(1.0)
        assert response["pearson_correlation"] == pytest.approx(1.0)
    np.testing.assert_allclose(
        report["response_matrix"]["normalized_by_true_own_factor_response"],
        np.eye(2),
        atol=1e-12,
    )


def test_affine_cross_talk_fixture_populates_only_response_off_diagonals() -> None:
    true_s, true_m = _factorial_targets()
    alpha = 0.25  # measurement -> structure
    beta = 0.40  # structure -> measurement
    pred_s = true_s + alpha * true_m
    pred_m = true_m + beta * true_s

    report = compute_factorization_metrics(pred_s, pred_m, true_s, true_m)
    true_s_delta = true_s[:, 1] - true_s[:, 0]
    true_m_delta = true_m[:, :, 1] - true_m[:, :, 0]
    expected_s_from_m = alpha * np.mean(np.linalg.norm(true_m_delta.reshape(-1, 2), axis=-1))
    expected_m_from_s = beta * np.mean(np.linalg.norm(true_s_delta.reshape(-1, 2), axis=-1))
    assert report["leakage"]["measurement_to_structure"] == pytest.approx(
        expected_s_from_m
    )
    assert report["leakage"]["structure_to_measurement"] == pytest.approx(
        expected_m_from_s
    )
    assert report["own_factor_response"]["structure"]["mean_l2_error"] == pytest.approx(0.0)
    assert report["own_factor_response"]["measurement"]["mean_l2_error"] == pytest.approx(0.0)
    np.testing.assert_allclose(
        report["response_matrix"]["normalized_by_true_own_factor_response"],
        [[1.0, beta], [alpha, 1.0]],
        atol=1e-12,
    )


def test_collapsed_predictions_cannot_fake_own_factor_response() -> None:
    true_s, true_m = _factorial_targets()
    collapsed_s = np.zeros_like(true_s)
    collapsed_m = np.zeros_like(true_m)
    report = compute_factorization_metrics(
        collapsed_s, collapsed_m, true_s, true_m
    )

    assert report["leakage"]["measurement_to_structure"] == 0.0
    assert report["leakage"]["structure_to_measurement"] == 0.0
    np.testing.assert_allclose(
        report["response_matrix"]["normalized_by_true_own_factor_response"],
        np.zeros((2, 2)),
    )
    for factor in ("structure", "measurement"):
        response = report["own_factor_response"][factor]
        assert response["mean_l2_error"] == pytest.approx(
            response["true_mean_l2_response"]
        )
        assert response["through_origin_slope"] == pytest.approx(0.0)
        assert response["pearson_correlation"] is None


def test_signed_response_statistics_detect_reversed_direction() -> None:
    true_s, true_m = _factorial_targets()
    report = compute_factorization_metrics(-true_s, -true_m, true_s, true_m)

    for factor in ("structure", "measurement"):
        response = report["own_factor_response"][factor]
        assert response["through_origin_slope"] == pytest.approx(-1.0)
        assert response["pearson_correlation"] == pytest.approx(-1.0)
        assert response["mean_l2_error"] == pytest.approx(
            2.0 * response["true_mean_l2_response"]
        )
    # Magnitude-only matrix stays diagonal, demonstrating why signed metrics
    # are a mandatory companion to the response matrix.
    np.testing.assert_allclose(
        report["response_matrix"]["normalized_by_true_own_factor_response"],
        np.eye(2),
    )


def test_target_validation_catches_wrong_axis_and_equal_states() -> None:
    true_s, true_m = _factorial_targets()
    wrong_s = true_s.copy()
    wrong_s[0, 0, 1, 0] += 0.1
    with pytest.raises(ValueError, match="measurement axis"):
        validate_factorial_targets(wrong_s, true_m)

    equal_m = true_m.copy()
    equal_m[0, :, 1] = equal_m[0, :, 0]
    with pytest.raises(ValueError, match="indistinguishable measurement"):
        validate_factorial_targets(true_s, equal_m)


def test_physical_mae_uses_frozen_parameter_order_and_units() -> None:
    target = np.asarray(
        [
            [4.0, 6.0, -0.10, 0.08],
            [5.0, 7.0, 0.15, 0.20],
        ]
    )
    offset = np.asarray([0.10, -0.20, 0.03, 0.04])
    predicted = target + offset
    result = physical_parameter_mae(predicted, target)
    assert result == pytest.approx(
        {
            "a_angstrom": 0.10,
            "c_angstrom": 0.20,
            "delta_2theta_deg": 0.03,
            "fwhm_deg": 0.04,
        }
    )


def _seed_report(
    *,
    leakage_s_from_m: float,
    leakage_m_from_s: float,
    response_error: float,
    mae: float,
) -> dict[str, object]:
    return {
        "leakage": {
            "measurement_to_structure": leakage_s_from_m,
            "structure_to_measurement": leakage_m_from_s,
        },
        "own_factor_response": {
            "structure": {"mean_l2_error": response_error},
            "measurement": {"mean_l2_error": response_error},
        },
        "parameter_mae": {
            "a_angstrom": mae,
            "c_angstrom": mae,
            "delta_2theta_deg": mae,
            "fwhm_deg": mae,
        },
    }


def _matched_reports(
    leakage_factors: tuple[float, float],
    *,
    response_factor: float = 1.04,
    mae_factor: float = 1.04,
) -> tuple[dict[int, dict[str, object]], dict[int, dict[str, object]]]:
    baseline: dict[int, dict[str, object]] = {}
    factorized: dict[int, dict[str, object]] = {}
    for index, seed in enumerate((101, 202, 303)):
        scale = 1.0 + index * 0.1
        baseline[seed] = _seed_report(
            leakage_s_from_m=scale,
            leakage_m_from_s=1.2 * scale,
            response_error=0.5 * scale,
            mae=0.1 * scale,
        )
        factorized[seed] = _seed_report(
            leakage_s_from_m=leakage_factors[0] * scale,
            leakage_m_from_s=leakage_factors[1] * 1.2 * scale,
            response_error=response_factor * 0.5 * scale,
            mae=mae_factor * 0.1 * scale,
        )
    return baseline, factorized


def test_seed_summary_and_preregistered_go_decision_are_matched() -> None:
    baseline, factorized = _matched_reports((0.75, 0.70))
    summary = summarize_seed_metrics(baseline, factorized)
    assert summary["seeds"] == ["101", "202", "303"]
    comparison = summary["comparison"]
    assert comparison["leakage_measurement_to_structure"][
        "relative_reduction_of_means"
    ] == pytest.approx(0.25)
    assert comparison["leakage_structure_to_measurement"][
        "improved_seed_fraction"
    ] == 1.0
    assert math.isfinite(
        summary["baseline"]["mae_a_angstrom"]["sample_std"]
    )

    gate = decide_factorization_gate(summary)
    assert gate["decision"] == "GO"
    assert gate["failed_checks"] == []
    assert gate["continuation_allowed"] is True


@pytest.mark.parametrize(
    ("leakage_factors", "expected"),
    [
        ((0.75, 0.95), "PARTIAL"),
        ((0.95, 0.95), "NO-GO"),
    ],
)
def test_preregistered_partial_and_no_go_decisions(
    leakage_factors: tuple[float, float], expected: str
) -> None:
    baseline, factorized = _matched_reports(leakage_factors)
    assert decide_factorization_gate(baseline, factorized)["decision"] == expected


def test_seed_summary_rejects_unmatched_seeds() -> None:
    baseline, factorized = _matched_reports((0.75, 0.70))
    factorized.pop(303)
    with pytest.raises(ValueError, match="identical seed sets"):
        summarize_seed_metrics(baseline, factorized)
