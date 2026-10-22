import torch

from pxrd_forward_loss.model import ParameterRegressor


def test_regression_head_initialization_avoids_immediate_tanh_saturation() -> None:
    torch.manual_seed(20261018)
    model = ParameterRegressor(input_length=3501, bound=0.8)
    head = model.backbone.head

    assert float(head.weight.detach().std()) < 0.0012
    assert torch.count_nonzero(head.bias.detach()).item() == 0

    with torch.no_grad():
        prediction = model(torch.randn(2, 1, 3501))
    assert torch.isfinite(prediction).all()
    assert torch.all(prediction.abs() < 0.5 * model.bound)
