from __future__ import annotations

import torch

from xrd_robustness.models.ml4pxrd_resnet1d import (
    ML4PXRDResNet1D,
    ML4PXRDResNet1DConfig,
)


def test_resnet18_output_contract() -> None:
    config = ML4PXRDResNet1DConfig(model_id="18", input_length=3501)
    model = ML4PXRDResNet1D(config)
    output = model(torch.zeros(2, 3501))
    assert output["logits"].shape == (2, 7)
    assert output["pooled_embedding"].shape == (2, 256)
    assert output["main_tokens"].shape == (2, 14, 512)
    assert output["prior_tokens"] is None
    assert model.final_length == 14


def test_resnet18_initialization_is_seed_deterministic() -> None:
    config = ML4PXRDResNet1DConfig(model_id="18", input_length=3501)
    torch.manual_seed(20260710)
    first = ML4PXRDResNet1D(config)
    torch.manual_seed(20260710)
    second = ML4PXRDResNet1D(config)
    assert all(
        torch.equal(first.state_dict()[name], second.state_dict()[name])
        for name in first.state_dict()
    )


def test_resnet18_backward_is_finite() -> None:
    model = ML4PXRDResNet1D(ML4PXRDResNet1DConfig())
    x = torch.randn(2, 3501)
    target = torch.tensor([0, 6])
    loss = torch.nn.functional.cross_entropy(model(x)["logits"], target)
    loss.backward()
    assert torch.isfinite(loss)
    assert all(
        parameter.grad is None or torch.isfinite(parameter.grad).all()
        for parameter in model.parameters()
    )
