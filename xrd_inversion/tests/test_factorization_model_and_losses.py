from __future__ import annotations

import math

import pytest
import torch

from xrd_inversion.factorization_losses import (
    paired_invariance_losses,
    parameter_mse_loss,
)
from xrd_inversion.models import (
    DeterministicSegmentMean1d,
    FACTORIAL_BLOCK_AXIS_ORDER,
    INPUT_CHANNEL_ORDER,
    MEASUREMENT_PARAMETER_ORDER,
    STRUCTURE_PARAMETER_ORDER,
    TwoHeadFactorizationModel,
)


def test_deterministic_segment_pool_preserves_all_positions() -> None:
    pool = DeterministicSegmentMean1d(3)
    values = torch.arange(10, dtype=torch.float32).reshape(1, 1, 10)
    output = pool(values)
    expected = torch.tensor([[[1.5, 5.5, 8.5]]])
    torch.testing.assert_close(output, expected)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA is required")
def test_segment_pool_cuda_backward_obeys_deterministic_mode() -> None:
    previous = torch.are_deterministic_algorithms_enabled()
    try:
        torch.use_deterministic_algorithms(True)
        values = torch.randn(2, 3, 17, device="cuda", requires_grad=True)
        DeterministicSegmentMean1d(5).cuda()(values).square().mean().backward()
        assert values.grad is not None
        assert torch.isfinite(values.grad).all()
    finally:
        torch.use_deterministic_algorithms(previous)


def small_model() -> TwoHeadFactorizationModel:
    torch.manual_seed(20260901)
    return TwoHeadFactorizationModel(
        input_channels=3,
        base_channels=4,
        latent_dim=8,
        pooled_length=4,
        output_bound=1.0,
    )


def test_flat_and_block_forward_shapes_bounds_and_corner_order() -> None:
    model = small_model().eval()
    flat = torch.randn(8, 3, 128)
    block = flat.reshape(2, 2, 2, 3, 128)

    with torch.no_grad():
        flat_s, flat_m = model(flat)
        block_s, block_m = model.forward_blocks(block)

    assert flat_s.shape == (8, 2)
    assert flat_m.shape == (8, 2)
    assert block_s.shape == (2, 2, 2, 2)
    assert block_m.shape == (2, 2, 2, 2)
    torch.testing.assert_close(block_s, flat_s.reshape(2, 2, 2, 2))
    torch.testing.assert_close(block_m, flat_m.reshape(2, 2, 2, 2))
    assert torch.isfinite(block_s).all()
    assert torch.isfinite(block_m).all()
    assert torch.all(block_s >= -1.0) and torch.all(block_s <= 1.0)
    assert torch.all(block_m >= -1.0) and torch.all(block_m <= 1.0)


def test_channel_parameter_and_factorial_axis_orders_are_frozen() -> None:
    assert INPUT_CHANNEL_ORDER == ("x_obs", "x_ref", "x_diff")
    assert STRUCTURE_PARAMETER_ORDER == ("q_u", "q_v")
    assert MEASUREMENT_PARAMETER_ORDER == ("q_delta", "q_w")
    assert FACTORIAL_BLOCK_AXIS_ORDER == (
        "batch",
        "structure_state",
        "measurement_state",
        "channel",
        "two_theta",
    )

    model = small_model().eval()
    expected_s = torch.tensor([0.25, -0.50])
    expected_m = torch.tensor([-0.75, 0.50])
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.zero_()
        model.structure_head.bias.copy_(torch.atanh(expected_s))
        model.measurement_head.bias.copy_(torch.atanh(expected_m))
        pred_s, pred_m = model(torch.zeros(3, 3, 128))

    torch.testing.assert_close(pred_s, expected_s.expand(3, -1))
    torch.testing.assert_close(pred_m, expected_m.expand(3, -1))


def test_both_heads_and_shared_encoder_receive_finite_gradients() -> None:
    model = small_model()
    spectra = torch.randn(1, 2, 2, 3, 128, requires_grad=True)
    target_s = torch.tensor(
        [[-0.5, 0.2], [0.1, -0.3], [0.4, 0.6], [-0.2, -0.7]]
    ).reshape(1, 2, 2, 2)
    target_m = torch.tensor(
        [[0.3, -0.4], [-0.6, 0.8], [0.2, 0.1], [0.7, -0.2]]
    ).reshape(1, 2, 2, 2)

    pred_s, pred_m = model.forward_blocks(spectra)
    loss = parameter_mse_loss(pred_s, pred_m, target_s, target_m)
    loss.backward()

    assert loss.ndim == 0 and math.isfinite(float(loss.detach()))
    assert spectra.grad is not None
    assert torch.isfinite(spectra.grad).all()
    assert float(spectra.grad.abs().sum()) > 0.0
    gradients = {
        name: parameter.grad for name, parameter in model.named_parameters()
    }
    assert all(gradient is not None for gradient in gradients.values())
    assert all(torch.isfinite(gradient).all() for gradient in gradients.values())
    assert float(gradients["structure_head.weight"].abs().sum()) > 0.0
    assert float(gradients["measurement_head.weight"].abs().sum()) > 0.0
    assert any(
        float(gradient.abs().sum()) > 0.0
        for name, gradient in gradients.items()
        if name.startswith("encoder.")
    )


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_input_is_rejected(bad_value: float) -> None:
    model = small_model()
    spectra = torch.zeros(2, 3, 128)
    spectra[0, 0, 0] = bad_value
    with pytest.raises(ValueError, match="finite"):
        model(spectra)


def test_invalid_shapes_and_dtypes_are_rejected() -> None:
    model = small_model()
    with pytest.raises(ValueError, match=r"\[N, 3, L\]"):
        model(torch.zeros(2, 3, 8, 8))
    with pytest.raises(ValueError, match="channel"):
        model(torch.zeros(2, 2, 128))
    with pytest.raises(TypeError, match="floating-point"):
        model(torch.zeros(2, 3, 128, dtype=torch.int64))
    with pytest.raises(TypeError, match="does not match"):
        model(torch.zeros(2, 3, 128, dtype=torch.float64))
    with pytest.raises(ValueError, match="exactly two structure"):
        model.forward_blocks(torch.zeros(1, 2, 3, 3, 128))


def test_non_finite_internal_prediction_is_rejected() -> None:
    model = small_model()
    with torch.no_grad():
        model.structure_head.bias[0] = float("nan")
    with pytest.raises(FloatingPointError, match="non-finite q predictions"):
        model(torch.zeros(1, 3, 128))


def test_pair_losses_are_zero_only_for_the_expected_invariances() -> None:
    pred_s = torch.tensor(
        [[[[0.1, 0.2], [0.1, 0.2]], [[-0.4, 0.7], [-0.4, 0.7]]]]
    )
    pred_m = torch.tensor(
        [[[[0.3, -0.8], [-0.2, 0.5]], [[0.3, -0.8], [-0.2, 0.5]]]]
    )

    loss_s, loss_m = paired_invariance_losses(pred_s, pred_m)
    torch.testing.assert_close(loss_s, torch.zeros_like(loss_s))
    torch.testing.assert_close(loss_m, torch.zeros_like(loss_m))

    leaky_s = pred_s.clone()
    leaky_s[:, 0, 1, 0] += 1.0
    changed_s, unchanged_m = paired_invariance_losses(leaky_s, pred_m)
    assert float(changed_s) > 0.0
    torch.testing.assert_close(unchanged_m, torch.zeros_like(unchanged_m))

    leaky_m = pred_m.clone()
    leaky_m[:, 1, 0, 1] += 1.0
    unchanged_s, changed_m = paired_invariance_losses(pred_s, leaky_m)
    torch.testing.assert_close(unchanged_s, torch.zeros_like(unchanged_s))
    assert float(changed_m) > 0.0
