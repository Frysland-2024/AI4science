from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from analyze_v9_p0_statistical_robustness import (  # noqa: E402
    SINGLE_FACTOR_PROFILES,
    _bootstrap_mean,
    analyze_report,
)
from audit_v9_p0_short_trajectory import _aggregate  # noqa: E402
from audit_v9_p0_short_trajectory_resilient import (  # noqa: E402
    _is_quality_gate_exhaustion,
    _render_balanced_bundle_with_retry,
)


class V9P0FollowupUtilityTest(unittest.TestCase):
    def test_cluster_bootstrap_is_deterministic(self) -> None:
        first = _bootstrap_mean([0.1, 0.2, 0.3], draws=1000, seed=11)
        second = _bootstrap_mean([0.1, 0.2, 0.3], draws=1000, seed=11)
        self.assertEqual(first, second)
        self.assertGreater(first["lower_95"], 0.0)

    def test_statistical_analysis_uses_repeat_as_sampling_unit(self) -> None:
        rows = []
        for repeat in range(4):
            for profile_index, profile in enumerate(SINGLE_FACTOR_PROFILES):
                benefit = 0.01 + repeat * 0.001 + profile_index * 0.0001
                rows.append(
                    {
                        "repeat": repeat,
                        "profile": profile,
                        "benefit_vs_erm": {
                            "js": {"classification_ce": benefit},
                            "residual": {"classification_ce": -benefit},
                        },
                    }
                )
        result = analyze_report({"rows": rows}, draws=1000, seed=5)
        js_ci = result["repeat_clustered_analysis"]["js"][
            "repeat_clustered_bootstrap_95"
        ]
        residual_ci = result["repeat_clustered_analysis"]["residual"][
            "repeat_clustered_bootstrap_95"
        ]
        self.assertEqual(js_ci["sampling_unit_count"], 4)
        self.assertGreater(js_ci["lower_95"], 0.0)
        self.assertLess(residual_ci["upper_95"], 0.0)
        self.assertEqual(
            set(result["leave_one_profile_out"]["js"]),
            set(SINGLE_FACTOR_PROFILES),
        )

    def test_short_trajectory_aggregate_clusters_by_repeat(self) -> None:
        rows = []
        for repeat in range(3):
            for profile in SINGLE_FACTOR_PROFILES:
                branches = {
                    "erm": {
                        "paired_js": 0.2,
                        "fixed_audit_probe_accuracy": 0.3,
                        "fixed_audit_probe_ce": 1.8,
                    },
                    "js": {
                        "paired_js": 0.1,
                        "fixed_audit_probe_accuracy": 0.3,
                        "fixed_audit_probe_ce": 1.8,
                    },
                    "residual": {
                        "paired_js": 0.15,
                        "fixed_audit_probe_accuracy": 0.2,
                        "fixed_audit_probe_ce": 1.9,
                    },
                }
                rows.append(
                    {
                        "repeat": repeat,
                        "step": 1,
                        "profile": profile,
                        "branches": branches,
                        "benefit_vs_erm": {
                            "js": {"classification_ce": 0.01 + repeat * 0.001},
                            "residual": {"classification_ce": 0.005},
                        },
                    }
                )
        result = _aggregate(rows)
        self.assertEqual(
            result["1"]["js"]["repeat_clustered_bootstrap_95"]["repeat_count"],
            3,
        )
        self.assertLess(
            result["1"]["js"]["mean_mechanism_differences_vs_erm"][
                "paired_js_difference_vs_erm"
            ],
            0.0,
        )
        self.assertGreater(
            result["1"]["residual"]["mean_mechanism_differences_vs_erm"][
                "probe_ce_difference_vs_erm"
            ],
            0.0,
        )

    def test_quality_gate_exhaustion_is_detected_narrowly(self) -> None:
        self.assertTrue(
            _is_quality_gate_exhaustion(
                ValueError("quality gate exhausted deterministic resampling after 32 attempts")
            )
        )
        self.assertFalse(_is_quality_gate_exhaustion(ValueError("unrelated render error")))

    @patch("audit_v9_p0_short_trajectory_resilient.p0._render_profile")
    @patch("audit_v9_p0_short_trajectory_resilient.p0._balanced_repeat_batch")
    def test_quality_invalid_whole_batch_is_replaced_deterministically(
        self, balanced_batch, render_profile
    ) -> None:
        balanced_batch.side_effect = [["bad"], ["good"]]
        view = np.zeros((1, 8), dtype=np.float32)
        render_profile.side_effect = [
            ValueError("quality gate exhausted deterministic resampling after 32 attempts"),
            (view, view.copy()),
        ]
        material_ids, rendered, rejections, attempt = _render_balanced_bundle_with_retry(
            pool=["bad", "good"],
            labels={"bad": 0, "good": 0},
            profiles=("train",),
            logical_repeat=3,
            stream_offset=10,
            render_repeat_base=20,
            panel_start=0,
            peaks={},
            sampler=object(),
            factory=object(),
            phase="unit_test",
            max_attempts=2,
        )
        self.assertEqual(material_ids, ["good"])
        self.assertEqual(set(rendered), {"train"})
        self.assertEqual(attempt, 1)
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]["material_ids"], ["bad"])


if __name__ == "__main__":
    unittest.main()
