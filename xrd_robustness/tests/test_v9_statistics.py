from __future__ import annotations

import unittest

from xrd_robustness.evaluation.statistics import (
    hierarchical_paired_bootstrap,
    infer_paper_outcome,
    interpret_single_contrast,
    validate_prediction_rows,
)


class V9StatisticsTests(unittest.TestCase):
    def test_parent_structure_bootstrap_detects_paired_improvement(self) -> None:
        rows = []
        for seed in (17, 29, 43):
            for parent in range(60):
                label = parent % 2
                for profile in ("ood_a", "ood_b"):
                    for method, errors in (("baseline", 5), ("focus", 15)):
                        prediction = 1 - label if parent % errors == 0 else label
                        rows.append(
                            {
                                "seed": seed,
                                "method_id": method,
                                "profile": profile,
                                "material_id": f"m{parent}",
                                "parent_structure_id": f"p{parent}",
                                "label": label,
                                "prediction": prediction,
                            }
                        )
        result = hierarchical_paired_bootstrap(
            rows,
            focus_method_id="focus",
            comparator_method_id="baseline",
            profiles=["ood_a", "ood_b"],
            replicates=300,
            random_seed=7,
        )
        self.assertEqual(result["independent_unit"], "parent_structure")
        self.assertTrue(result["seed_resampling_forbidden"])
        self.assertGreater(result["hierarchical_bootstrap_95_ci"][0], 0.0)

    def test_four_preregistered_outcome_scenarios(self) -> None:
        def contrast(mean: float, low: float, high: float) -> dict[str, object]:
            return {"mean_delta": mean, "hierarchical_bootstrap_95_ci": [low, high]}

        scenarios = {
            "A_residual_stably_beats_dynamic_and_js": (
                contrast(0.08, 0.03, 0.12), contrast(0.03, 0.01, 0.06), contrast(0.05, 0.02, 0.09)
            ),
            "B_both_effective_no_clear_difference": (
                contrast(0.05, 0.02, 0.08), contrast(0.04, 0.01, 0.07), contrast(0.01, -0.02, 0.04)
            ),
            "C_js_effective_residual_no_extra_gain": (
                contrast(0.01, -0.02, 0.04), contrast(0.06, 0.03, 0.09), contrast(-0.05, -0.08, -0.02)
            ),
            "D_neither_effective_or_inconclusive": (
                contrast(0.01, -0.02, 0.04), contrast(0.00, -0.03, 0.03), contrast(0.01, -0.02, 0.04)
            ),
        }
        for expected, (res_dynamic, js_dynamic, res_js) in scenarios.items():
            with self.subTest(expected=expected):
                self.assertEqual(
                    infer_paper_outcome(
                        residual_minus_dynamic=res_dynamic,
                        js_minus_dynamic=js_dynamic,
                        residual_minus_js=res_js,
                    ),
                    expected,
                )

    def test_restrained_conclusions_for_requested_synthetic_cases(self) -> None:
        def contrast(mean: float, low: float, high: float, seeds: list[float]) -> dict[str, object]:
            return {
                "mean_delta": mean,
                "hierarchical_bootstrap_95_ci": [low, high],
                "paired_seed_deltas": {str(index): value for index, value in enumerate(seeds)},
            }

        # A: JS is consistently above ERM.
        self.assertEqual(
            interpret_single_contrast(contrast(0.05, 0.02, 0.08, [0.04, 0.05, 0.06])),
            "stable_positive_across_registered_seeds",
        )
        # B: the average is positive but one registered seed is negative.
        self.assertEqual(
            interpret_single_contrast(contrast(0.02, -0.01, 0.05, [0.04, -0.01, 0.03])),
            "average_positive_but_mixed_seed_direction",
        )
        # C: Residual and JS are practically tied at the available precision.
        self.assertEqual(
            interpret_single_contrast(contrast(0.001, -0.01, 0.012, [0.002, -0.001, 0.002])),
            "no_clear_difference",
        )
        # D: OOD gain with a material ID decline must be reported as a tradeoff.
        self.assertEqual(
            interpret_single_contrast(
                contrast(0.05, 0.02, 0.08, [0.04, 0.05, 0.06]), mean_id_delta=-0.08
            ),
            "ood_gain_with_material_id_tradeoff",
        )

    def test_duplicate_prediction_identity_is_rejected(self) -> None:
        row = {
            "seed": 1,
            "method_id": "m",
            "profile": "p",
            "material_id": "id",
            "parent_structure_id": "p",
            "label": 0,
            "prediction": 0,
        }
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_prediction_rows([row, row])


if __name__ == "__main__":
    unittest.main()
