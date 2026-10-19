import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(REPO / "donut_pxrd" / "src"),
    str(REPO / "xrd_inversion" / "src"),
    str(REPO / "xrd_robustness" / "src"),
    str(REPO / "xrd_forward_loss" / "src"),
]

import torch

from donut_pxrd.model import DONUTEncoderDecoder, map_latent_to_physics, modified_tanh


def test_modified_tanh_matches_donut_bottleneck():
    values = torch.tensor([-3.0, 0.0, 3.0])
    expected = 1.7159 * torch.tanh((2.0 / 3.0) * values)
    assert torch.allclose(modified_tanh(values), expected)


def test_latent_maps_to_frozen_physical_ranges_by_phase():
    constrained = torch.tensor([[1.7159, -1.7159, 1.7159, -1.7159, 1.7159]])
    q, eta = map_latent_to_physics(constrained, phase="experiment_3_noise")
    assert torch.allclose(q, torch.tensor([[0.8, -0.8]]), atol=1e-6)
    assert torch.allclose(eta, torch.tensor([[0.06, 0.08, 0.01]]), atol=1e-6)


def test_decoder_is_latent_only_and_backpropagates_to_encoder():
    model = DONUTEncoderDecoder(input_length=256, latent_dim=2, dropout=0.0)
    observed = torch.rand((2, 256))
    reconstructed, raw, constrained = model(observed)
    assert reconstructed.shape == observed.shape
    assert raw.shape == constrained.shape == (2, 2)
    reconstructed.square().mean().backward()
    assert model.encoder_fc.weight.grad is not None
    assert torch.isfinite(model.encoder_fc.weight.grad).all()
