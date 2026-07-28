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

    def test_final_governance_remains_fail_closed(self) -> None:
        path = (
            PROJECT_ROOT
            / "configs"
            / "v9_resnet_method_parameter_governance.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "candidate_range_gate_failed")
        self.assertFalse(payload["candidate_range_frozen_for_validation"])
        self.assertTrue(all(value is False for value in payload["execution"].values()))
        self.assertEqual(
            payload["train_only_gate_result"]["decision"],
            "do_not_freeze_candidates_and_do_not_start_seven_run",
        )


if __name__ == "__main__":
    unittest.main()
