import unittest

import torch

from xrd_robustness.models import PAMPT, PAMPTConfig, PatchTransformerConfig, XRDPatchTransformer


class PatchTransformerTests(unittest.TestCase):
    def test_patch_shape_for_3501_points(self):
        config = PatchTransformerConfig(
            input_length=3501,
            patch_size=16,
            embed_dim=32,
            depth=1,
            num_heads=4,
            dropout=0.0,
        )
        model = XRDPatchTransformer(config)
        tokens = model.patch_embedding(torch.zeros(2, 3501))
        self.assertEqual(tokens.shape, (2, 219, 32))
        self.assertEqual(model.patch_count, 219)

    def test_forward_and_backward(self):
        config = PatchTransformerConfig(
            input_length=3501,
            patch_size=32,
            embed_dim=32,
            depth=1,
            num_heads=4,
            dropout=0.0,
        )
        model = XRDPatchTransformer(config)
        output = model(torch.rand(2, 3501))
        self.assertEqual(output["logits"].shape, (2, 7))
        output["logits"].sum().backward()
        self.assertTrue(any(parameter.grad is not None for parameter in model.parameters()))

    def test_cls_pooling(self):
        config = PatchTransformerConfig(
            input_length=65,
            patch_size=16,
            embed_dim=32,
            depth=1,
            num_heads=4,
            dropout=0.0,
            pooling="cls",
        )
        model = XRDPatchTransformer(config)
        self.assertEqual(model(torch.rand(3, 65))["logits"].shape, (3, 7))

    def test_pampt_b3_contract_and_token_alignment(self):
        config = PAMPTConfig(
            variant="b3",
            input_length=65,
            patch_size=16,
            patch_stride=8,
            embed_dim=32,
            depth=4,
            num_heads=4,
            branch_channels=8,
            fusion_dim=16,
            dropout=0.0,
        )
        model = PAMPT(config)
        output = model(torch.rand(2, 65))
        self.assertEqual(output["logits"].shape, (2, 7))
        self.assertEqual(output["pooled_embedding"].shape, (2, 32))
        self.assertEqual(output["main_tokens"].shape, output["prior_tokens"].shape)

    def test_pampt_variants_forward(self):
        for variant in ("b0", "b1", "b2", "b3"):
            config = PAMPTConfig(
                variant=variant,
                input_length=65,
                embed_dim=32,
                depth=4 if variant == "b3" else 1,
                num_heads=4,
                branch_channels=8,
                fusion_dim=16,
                dropout=0.0,
            )
            output = PAMPT(config)(torch.rand(2, 65))
            self.assertEqual(output["logits"].shape, (2, 7))


if __name__ == "__main__":
    unittest.main()
