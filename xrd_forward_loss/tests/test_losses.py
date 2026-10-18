import torch
from torch import nn

from pxrd_forward_loss.losses import paired_losses
from pxrd_forward_loss.model import compose_full_q


class ToyForward:
    def transformed(self, q):
        return q[:, :2].square()


def test_supervised_and_reconstruction_losses_backpropagate():
    predicted = torch.tensor([[0.2, -0.3]], requires_grad=True)
    target = torch.tensor([[0.1, -0.2]])
    observed = torch.tensor([[0.01, 0.04]])
    losses = paired_losses(
        predicted,
        target,
        observed,
        forward_model=ToyForward(),
        reconstruction_weight=0.5,
    )
    losses["total"].backward()
    assert torch.isfinite(losses["total"])
    assert predicted.grad is not None
    assert torch.isfinite(predicted.grad).all()
    assert losses["parameter"].item() > 0
    assert losses["reconstruction"].item() > 0


def test_supervised_only_does_not_require_forward_model():
    predicted = torch.tensor([[0.2, -0.3]], requires_grad=True)
    target = torch.tensor([[0.1, -0.2]])
    observed = torch.zeros((1, 2))
    result = paired_losses(predicted, target, observed)
    result["total"].backward()
    assert result["reconstruction"].item() == 0.0
    assert predicted.grad is not None


def test_compose_full_q_pins_nuisance_parameters():
    lattice = torch.tensor([[0.2, -0.3], [0.0, 0.1]])
    full = compose_full_q(lattice)
    assert tuple(full.shape) == (2, 4)
    assert torch.equal(full[:, :2], lattice)
    assert torch.equal(full[:, 2], torch.zeros(2))
    assert torch.equal(full[:, 3], -torch.ones(2))
