from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest

from xrd_robustness.evaluation.real_adaptation import (
    audit_real_adaptation_contract,
    build_real_adaptation_plan,
    sha256_file,
)


CLASSES = (
    "cubic",
    "hexagonal",
    "monoclinic",
    "orthorhombic",
    "tetragonal",
    "triclinic",
    "trigonal",
)


class RealAdaptationContractTest(unittest.TestCase):
    def _build_fixture(self, root: Path) -> Path:
        manifest_dir = root / "data" / "real_xrd" / "rruff70" / "manifests"
        config_dir = root / "configs"
        manifest_dir.mkdir(parents=True)
        config_dir.mkdir(parents=True)

        role_path = manifest_dir / "rruff70_real_adaptation_split_v1.csv"
        role_rows = []
        for crystal_system in CLASSES:
            for index in range(10):
                if index < 3:
                    role = "adaptation_train"
                    rank = str(index + 1)
                elif index < 5:
                    role = "adaptation_validation"
                    rank = ""
                else:
                    role = "final_real_test"
                    rank = ""
                role_rows.append(
                    {
                        "sample_id": f"{crystal_system}-{index}",
                        "crystal_system": crystal_system,
                        "real_domain_role": role,
                        "adaptation_train_rank_within_class": rank,
                        "spectrum_sha256": f"{index:064X}",
                    }
                )
        with role_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(role_rows[0]))
            writer.writeheader()
            writer.writerows(role_rows)

        episode_path = manifest_dir / "rruff70_fewshot_episode_manifest_v1.csv"
        episode_defs = {
            ("1shot", "E1"): {1},
            ("1shot", "E2"): {2},
            ("1shot", "E3"): {3},
            ("2shot", "E1"): {1, 2},
            ("2shot", "E2"): {1, 3},
            ("2shot", "E3"): {2, 3},
            ("3shot", "E1"): {1, 2, 3},
        }
        episode_rows = []
        for (budget, episode_id), ranks in episode_defs.items():
            for row in role_rows:
                if row["real_domain_role"] == "adaptation_train":
                    if int(row["adaptation_train_rank_within_class"]) not in ranks:
                        continue
                    role = "support_train"
                elif row["real_domain_role"] == "adaptation_validation":
                    role = "adaptation_validation"
                else:
                    role = "final_real_test"
                episode_rows.append(
                    {
                        "shot_budget": budget,
                        "episode_id": episode_id,
                        "sample_id": row["sample_id"],
                        "crystal_system": row["crystal_system"],
                        "role": role,
                        "spectrum_sha256": row["spectrum_sha256"],
                    }
                )
        with episode_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(episode_rows[0]))
            writer.writeheader()
            writer.writerows(episode_rows)

        contract = {
            "schema_version": "v9-real-domain-adaptation-v1",
            "status": "role_assignment_frozen_execution_disabled",
            "execution_enabled": False,
            "source_dataset": {"sample_count": 70},
            "role_assignment": {
                "split_manifest_path": str(role_path.relative_to(root)),
                "split_manifest_sha256": sha256_file(role_path),
                "counts": {
                    "adaptation_train": 21,
                    "adaptation_validation": 14,
                    "final_real_test": 35,
                },
                "per_crystal_system": {
                    "adaptation_train": 3,
                    "adaptation_validation": 2,
                    "final_real_test": 5,
                },
            },
            "fewshot_episodes": {
                "manifest_path": str(episode_path.relative_to(root)),
                "manifest_sha256": sha256_file(episode_path),
                "budgets": {
                    "0shot": {"episodes": {"E0": []}},
                    "1shot": {"episodes": {"E1": [1], "E2": [2], "E3": [3]}},
                    "2shot": {
                        "episodes": {"E1": [1, 2], "E2": [1, 3], "E3": [2, 3]}
                    },
                    "3shot": {"episodes": {"E1": [1, 2, 3]}},
                },
            },
            "core_methods": ["erm", "js", "residual"],
            "pretraining_seeds": [1, 2, 3],
            "primary_adaptation": {
                "id": "classifier_head_only_ce",
                "encoder_trainable": False,
                "classifier_trainable": True,
                "objective": "cross_entropy_only",
                "js_loss_enabled": False,
                "residual_loss_enabled": False,
                "learning_rate_candidates": [0.0001, 0.0003, 0.001],
                "checkpoint_metric": "adaptation_validation_macro_f1",
            },
            "secondary_adaptation": {
                "id": "full_network_ce",
                "learning_rate_candidates": [0.000001, 0.000003, 0.00001],
                "checkpoint_metric": "adaptation_validation_macro_f1",
            },
            "final_real_test": {"enabled": False, "locked": True, "sample_count": 35},
        }
        contract_path = config_dir / "real_adaptation.v9.method_transfer.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        return contract_path

    def test_complete_fixture_passes_without_model_or_spectrum_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = self._build_fixture(root)
            report = audit_real_adaptation_contract(
                contract_path,
                project_root=root,
                require_local_data=True,
            )
            self.assertEqual(report["status"], "locked_contract_and_manifests_pass")
            self.assertFalse(report["model_loaded"])
            self.assertFalse(report["spectra_loaded"])
            self.assertFalse(report["final_test_used"])

    def test_plan_counts_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = self._build_fixture(root)
            primary = build_real_adaptation_plan(contract_path)
            self.assertEqual(primary["candidate_training_run_count"], 189)
            self.assertEqual(primary["selected_checkpoint_group_count"], 63)
            self.assertEqual(primary["zero_shot_evaluation_count"], 9)
            both = build_real_adaptation_plan(contract_path, include_secondary=True)
            self.assertEqual(both["candidate_training_run_count"], 378)
            self.assertEqual(both["selected_checkpoint_group_count"], 126)

    def test_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_path = self._build_fixture(root)
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["role_assignment"]["split_manifest_sha256"] = "0" * 64
            contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
            report = audit_real_adaptation_contract(
                contract_path,
                project_root=root,
                require_local_data=True,
            )
            self.assertEqual(report["status"], "fail")
            self.assertTrue(any("hash mismatch" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
