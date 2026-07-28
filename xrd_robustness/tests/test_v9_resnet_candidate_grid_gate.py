from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import audit_v9_resnet_candidate_grid_gate as gate


class ResNetCandidateGridGateTests(unittest.TestCase):
    def setUp(self) -> None:
        path = (
            PROJECT_ROOT
            / "configs"
            / "v9_resnet_method_parameter_governance.proposal.json"
        )
        self.proposal = json.loads(path.read_text(encoding="utf-8"))

    def test_registered_probe_contract_is_accepted(self) -> None:
        gate._assert_registered_proposal(self.proposal)

    def test_frozen_range_is_rejected_before_gate(self) -> None:
        payload = copy.deepcopy(self.proposal)
        payload["candidate_range_frozen_for_validation"] = True
        with self.assertRaisesRegex(ValueError, "unfrozen"):
            gate._assert_registered_proposal(payload)

    def test_influence_band_boundaries(self) -> None:
        self.assertEqual(gate._ratio_band(0.0), "negligible")
        self.assertEqual(gate._ratio_band(0.01), "weak")
        self.assertEqual(gate._ratio_band(0.1), "material_non_dominant")
        self.assertEqual(gate._ratio_band(1.0), "dominant")

    def test_final_governance_freezes_only_js_and_keeps_execution_closed(self) -> None:
        path = (
            PROJECT_ROOT
            / "configs"
            / "v9_resnet_method_parameter_governance.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(
            payload["status"],
            "js_candidate_range_frozen_four_run_not_authorized",
        )
        self.assertTrue(payload["candidate_range_frozen_for_validation"])
        self.assertEqual(payload["frozen_js_candidate_grid"], [3.0, 30.0, 60.0])
        self.assertEqual(
            payload["shared_methods"],
            ["ordinary_dynamic_augmentation", "js_consistency_transfer"],
        )
        self.assertTrue(all(value is False for value in payload["execution"].values()))
        self.assertEqual(
            payload["train_only_gate_result"]["decision"],
            "freeze_js_3_30_60_archive_residual_v1_and_do_not_start_four_run",
        )


if __name__ == "__main__":
    unittest.main()
