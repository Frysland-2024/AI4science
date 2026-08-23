from __future__ import annotations

import unittest

from xrd_robustness.evaluation.statistics import (
    build_paired_statistics_report,
    hierarchical_paired_bootstrap,
    interpret_single_contrast,
    validate_prediction_rows,
)


class PairedStatisticsTests(unittest.TestCase):
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
        # C: the two public methods are practically tied at the available precision.
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

    def test_public_report_contains_only_js_minus_erm(self) -> None:
        rows = []
        for seed in (1, 2):
            for parent in range(20):
                label = parent % 2
                for method in ("erm", "js"):
                    rows.append(
                        {
                            "seed": seed,
                            "method_id": method,
                            "profile": "ood",
                            "material_id": f"m{parent}",
                            "parent_structure_id": f"p{parent}",
                            "label": label,
                            "prediction": label,
                        }
                    )
        report = build_paired_statistics_report(
            rows,
            erm_method_id="erm",
            js_method_id="js",
            profiles=["ood"],
            replicates=100,
            random_seed=3,
        )
        self.assertEqual(set(report["paired_comparisons"]), {"js_minus_erm"})


if __name__ == "__main__":
    unittest.main()
