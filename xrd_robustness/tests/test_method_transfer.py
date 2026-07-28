import copy
import json
from pathlib import Path
import unittest

from xrd_robustness.method_transfer import load_contract, sha256_file, validate_contract


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
GOVERNANCE_PATH = PROJECT_ROOT / "configs" / "v9_method_parameter_governance.json"


class MethodTransferResNetResetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = load_contract(CONTRACT_PATH)
        cls.governance = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))

    def test_resnet_candidate_and_all_execution_switches_are_locked(self) -> None:
        self.assertEqual(
            self.contract["model"]["variant"], "ml4pxrd_resnet18_gn_candidate"
        )
        self.assertFalse(self.contract["development_tuning"]["execution_enabled"])
        policy = self.contract["execution_policy"]
        self.assertFalse(policy["tuning_plan_generation_enabled"])
        self.assertFalse(policy["development_tuning_execution_enabled"])
        self.assertFalse(policy["experiment_execution_enabled"])
        self.assertFalse(policy["simulated_test_enabled"])
        self.assertFalse(policy["real_test_enabled"])

    def test_governance_is_hash_bound_and_invalidated_for_resnet(self) -> None:
        self.assertEqual(
            sha256_file(GOVERNANCE_PATH),
            self.contract["method_parameter_governance"]["sha256"],
        )
        self.assertFalse(self.governance["candidate_range_frozen_for_validation"])
        self.assertFalse(
            self.governance["candidate_grid_gate_evidence"][
                "valid_for_current_backbone"
            ]
        )
        self.assertFalse(
            self.governance["tuning_gate"][
                "development_tuning_execution_allowed"
            ]
        )

    def test_enabling_tuning_before_the_new_scale_gate_fails_closed(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["development_tuning"]["execution_enabled"] = True
        contract["execution_policy"]["development_tuning_execution_enabled"] = True
        contract["method_parameter_governance"][
            "development_tuning_execution_allowed"
        ] = True
        with self.assertRaisesRegex(ValueError, "candidate range is frozen"):
            validate_contract(contract)

    def test_parent_structure_split_and_final_test_locks_remain_active(self) -> None:
        self.assertEqual(
            self.contract["data"]["expected_split_counts"],
            {"train": 9842, "validation": 2109, "test": 2109},
        )
        self.assertTrue(self.contract["data"]["simulated_test_locked"])
        self.assertTrue(self.contract["data"]["real_test_locked"])


if __name__ == "__main__":
    unittest.main()
