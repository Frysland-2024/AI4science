import unittest

import torch
from torch import nn

from xrd_robustness.online_views import TrainingMode
from xrd_robustness.training import dynamic_erm, dynamic_js
from xrd_robustness.training import TrainingStepConfig, run_training_step


class TrainingObjectiveTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(7)
        self.model = nn.Sequential(nn.Linear(8, 7))
        self.x1 = torch.rand(4, 8)
        self.x2 = torch.rand(4, 8)
        self.target = torch.tensor([0, 1, 2, 3])

    def test_dynamic_modes_share_classification_term_for_same_pair(self):
        erm = dynamic_erm(self.model, self.x1, self.x2, self.target)
        consistent = dynamic_js(
            self.model,
            self.x1,
            self.x2,
            self.target,
            lambda_js=0.5,
        )
        torch.testing.assert_close(erm["logits_first"], consistent["logits_first"])
        torch.testing.assert_close(erm["logits_second"], consistent["logits_second"])
        torch.testing.assert_close(erm["classification"], consistent["classification"])
        torch.testing.assert_close(
            consistent["total"],
            erm["total"] + 0.5 * consistent["consistency"],
        )

    def test_dynamic_js_zero_weight_matches_dynamic_erm(self):
        erm = dynamic_erm(self.model, self.x1, self.x2, self.target)
        js = dynamic_js(self.model, self.x1, self.x2, self.target, lambda_js=0.0)
        torch.testing.assert_close(erm["classification"], js["classification"])
        torch.testing.assert_close(erm["total"], js["total"])

    def test_dispatch_supports_dynamic_js(self):
        result = run_training_step(
            TrainingStepConfig(mode=TrainingMode.DYNAMIC_JS, lambda_js=0.5),
            self.model,
            x1=self.x1,
            x2=self.x2,
            target=self.target,
        )
        self.assertIn("logits_second", result)
        self.assertGreaterEqual(float(result["consistency"].detach()), 0.0)


if __name__ == "__main__":
    unittest.main()
