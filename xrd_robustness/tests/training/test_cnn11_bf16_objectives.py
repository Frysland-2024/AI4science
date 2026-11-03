"""Regression checks for numerically stable Dynamic JS under BF16 autocast."""
import unittest

import torch
from torch import nn

from xrd_robustness.training.objectives import dynamic_erm, dynamic_js, js_divergence


class TestBF16ObjectiveNumerics(unittest.TestCase):
    def test_js_extreme_bf16_logits_stays_finite_and_has_finite_gradients(self):
        first = torch.tensor([[500.0, 0.0, -500.0], [0.0, 500.0, -500.0]],
                             dtype=torch.bfloat16, requires_grad=True)
        second = torch.tensor([[0.0, 500.0, -500.0], [500.0, 0.0, -500.0]],
                              dtype=torch.bfloat16, requires_grad=True)
        score = js_divergence(first, second)
        self.assertEqual(score.dtype, torch.float32)
        self.assertTrue(bool(torch.isfinite(score)))
        self.assertGreaterEqual(float(score.detach()), -1e-6)
        score.backward()
        for grad in (first.grad, second.grad):
            self.assertIsNotNone(grad)
            self.assertTrue(bool(torch.isfinite(grad).all()))

    def test_autocast_bf16_erm_js_have_matching_fp32_ce(self):
        torch.manual_seed(17)
        model = nn.Sequential(nn.Linear(8, 32), nn.ReLU(), nn.Linear(32, 7))
        inputs = torch.randn(16, 8)
        other = inputs + 0.07 * torch.randn_like(inputs)
        targets = torch.arange(16) % 7
        with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
            erm = dynamic_erm(model, inputs, other, targets)
            js = dynamic_js(model, inputs, other, targets, lambda_js=60.)
        self.assertEqual(erm["logits_first"].dtype, torch.bfloat16)
        self.assertEqual(erm["classification"].dtype, torch.float32)
        self.assertEqual(js["consistency"].dtype, torch.float32)
        torch.testing.assert_close(erm["classification"], js["classification"])
        self.assertTrue(bool(torch.isfinite(js["total"])))
        js["total"].backward()
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters()
                            if p.grad is not None))

    def test_fp32_behavior_matches_reference(self):
        torch.manual_seed(19)
        a = torch.randn(4, 7, requires_grad=True)
        b = torch.randn(4, 7, requires_grad=True)
        result = js_divergence(a, b)
        ref_a = a.log_softmax(-1)
        ref_b = b.log_softmax(-1)
        mean = (0.5 * (ref_a.exp() + ref_b.exp())).clamp_min(1e-12).log()
        expected = 0.5 * (
            torch.nn.functional.kl_div(mean, ref_a.exp(), reduction="batchmean")
            + torch.nn.functional.kl_div(mean, ref_b.exp(), reduction="batchmean")
        )
        torch.testing.assert_close(result, expected)


if __name__ == "__main__":
    unittest.main()
