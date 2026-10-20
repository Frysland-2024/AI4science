"""Small architecture/gradient checks; never load or open held-out samples."""
import json
from pathlib import Path

import torch

from pxrd_issue44.models import build


def test_architecture_shapes_gradients_and_fixed_parameterization():
    for architecture in ("resnet1d", "transformer"):
        torch.manual_seed(901)
        net = build(architecture, ndim=2, input_length=1024)
        sample = torch.randn(3, 1024)
        output = net(sample)
        assert output.shape == (3, 2)
        assert torch.isfinite(output).all()
        output.square().mean().backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in net.parameters() if p.requires_grad)
        assert int(sum(p.numel() for p in net.parameters())) > 0


def test_protocol_json_and_experiment_has_no_runtime_architecture_search():
    here = Path(__file__).parent
    config = json.loads((here / "frozen_config.json").read_text(encoding="utf-8"))
    assert config["primary"]["test"] == 77
    assert config["training"]["seeds"] == [2026101911, 2026101912, 2026101913]
    assert set(config["architectures"]) == {"resnet1d", "transformer"}
    assert config["physics"]["P5_starts"] == [0.0, -0.5, 0.5, -0.85, 0.85]
    assert config["real_rruff"]["status"] == "BLOCKED"
