from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from xrd_robustness.evaluation.rruff301_replay import (
    EVIDENCE_ROLE,
    KNOWN_INVALID_V1_SPLIT_SHA256,
    ReplayContractError,
    audit_existing_artifacts,
    build_retrospective_episode_plan,
    build_run_replay_refusal,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = PROJECT_ROOT / "configs" / "rruff301_retrospective_replay.v1.json"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_rruff301_retrospective_replay.py"


class Rruff301RetrospectiveReplayTest(unittest.TestCase):
    def test_contract_binds_known_provenance_and_is_not_authorized(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(contract["status"], "RETROSPECTIVE_REPLAY_NOT_AUTHORIZED")
        self.assertEqual(contract["evidence_role"], EVIDENCE_ROLE)
        self.assertFalse(contract["historical_execution_claim"])
        self.assertFalse(contract["authorization"]["execution_enabled"])
        self.assertEqual(
            contract["dataset"]["canonical_split"]["sha256"],
            "9FEDCB1ABDF3F84349DFC8479D233FBD953E6552D7478DAC3680737E460BBE35",
        )
        self.assertEqual(
            contract["dataset"]["master_manifest"]["sha256"],
            "EBF6B35ABAF78C716498D327CDD02EF3FFC3E53662AFC56A5CB009A10B96B142",
        )
        self.assertEqual(
            contract["preprocessing"]["contract_sha256"],
            "90DCBDC89F641A876DA2E8A927499A3E7225934AE38E820D70AD26640113C9CC",
        )
        self.assertIn(
            KNOWN_INVALID_V1_SPLIT_SHA256,
            {item["sha256"] for item in contract["dataset"]["forbidden_inputs"]},
        )
        self.assertEqual(len(contract["checkpoints"]["items"]), 10)
        self.assertEqual(
            len({item["sha256"] for item in contract["checkpoints"]["items"]}),
            10,
        )

    def test_run_replay_refuses_before_model_or_spectrum_access(self) -> None:
        payload = build_run_replay_refusal(
            CONTRACT_PATH,
            project_root=PROJECT_ROOT,
            authorization_path="untrusted-authorization.json",
        )
        self.assertEqual(payload["status"], "refused_execution_not_authorized")
        self.assertFalse(payload["authorization_validated"])
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["spectra_loaded"])
        self.assertFalse(payload["training_started"])
        self.assertFalse(payload["inference_started"])

    def test_cli_run_replay_writes_only_a_refusal(self) -> None:
        spec = importlib.util.spec_from_file_location("rruff301_replay_cli", SCRIPT_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "refusal.json"
            exit_code = module.main(
                [
                    "run-replay",
                    "--contract",
                    str(CONTRACT_PATH),
                    "--project-root",
                    str(PROJECT_ROOT),
                    "--authorization",
                    "untrusted.json",
                    "--output",
                    str(output),
                ]
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "refused_execution_not_authorized")
        self.assertFalse(payload["model_loaded"])
        self.assertFalse(payload["spectra_loaded"])

    def test_cli_check_only_does_not_write_refusal_report(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "rruff301_replay_cli_check_only",
            SCRIPT_PATH,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist.json"
            exit_code = module.main(
                [
                    "run-replay",
                    "--contract",
                    str(CONTRACT_PATH),
                    "--project-root",
                    str(PROJECT_ROOT),
                    "--output",
                    str(output),
                    "--check-only",
                ]
            )
            self.assertFalse(output.exists())
        self.assertEqual(exit_code, 2)

    @unittest.skipUnless(
        (PROJECT_ROOT / "data/real_xrd/rruff371/splits/rruff301_adaptation_test_split.csv").is_file(),
        "local ignored RRUFF-301 manifests are unavailable",
    )
    def test_plan_is_deterministic_nested_and_fixed_test(self) -> None:
        first = build_retrospective_episode_plan(CONTRACT_PATH, project_root=PROJECT_ROOT)
        second = build_retrospective_episode_plan(CONTRACT_PATH, project_root=PROJECT_ROOT)
        self.assertEqual(first, second)
        self.assertEqual(first["evidence_role"], EVIDENCE_ROLE)
        self.assertFalse(first["historical_plan_claim"])
        self.assertEqual(first["episode_count"], 15)
        self.assertEqual(first["support_assignment_count"], 280)
        self.assertEqual(first["locked_test_count"], 231)
        self.assertEqual(
            len({episode["locked_test_set_sha256"] for episode in first["episodes"]}),
            1,
        )
        supports = {
            (episode["K"], episode["episode_seed"]): {
                row["rruff_id"] for row in episode["support"]
            }
            for episode in first["episodes"]
        }
        for seed in (42, 123, 456, 789, 1024):
            self.assertLess(supports[(1, seed)], supports[(2, seed)])
            self.assertLess(supports[(2, seed)], supports[(5, seed)])
        self.assertEqual(
            [row["rruff_id"] for row in first["episodes"][0]["support"]],
            [
                "R050160",
                "R050136",
                "R050200",
                "R050208",
                "R050484",
                "R060359",
                "R060033",
            ],
        )

    @unittest.skipUnless(
        (PROJECT_ROOT / "data/real_xrd/rruff371/results/rruff301_predictions.json").is_file(),
        "local ignored RRUFF-301 result artifacts are unavailable",
    )
    def test_existing_artifact_audit_is_internal_only(self) -> None:
        report = audit_existing_artifacts(
            CONTRACT_PATH,
            project_root=PROJECT_ROOT,
            require_local_artifacts=True,
            verify_checkpoints=False,
        )
        self.assertEqual(
            report["status"],
            "existing_artifacts_verified_at_declared_levels_provenance_incomplete",
            report["errors"],
        )
        self.assertEqual(
            report["internal_artifact_consistency"],
            "pass_with_per_artifact_verification_levels",
        )
        self.assertFalse(report["confirmatory_claim_supported"])
        self.assertEqual(report["original_execution_reproducibility"], "incomplete")
        verification = report["result_artifact_audit"]["artifact_verification"]
        self.assertEqual(
            verification["fewshot_runs"]["level"],
            "metrics_recomputed_from_prediction_rows",
        )
        self.assertFalse(
            verification["fixed200"]["metrics_recomputed_from_predictions"]
        )
        self.assertFalse(
            verification["zero_shot"]["accuracy_recomputed_from_predictions"]
        )

    def test_audit_missing_local_artifacts_fails_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_dir = root / "configs"
            config_dir.mkdir()
            contract = config_dir / "contract.json"
            contract.write_bytes(CONTRACT_PATH.read_bytes())

            report = audit_existing_artifacts(contract, project_root=root)

        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["missing_required_local_files"])
        self.assertIn("required local artifacts are missing", report["errors"][-1])

    def test_prediction_metric_tamper_is_rejected_without_local_dataset(self) -> None:
        locked_test = []
        prediction_rows = []
        for class_index, crystal_system in enumerate(
            ("triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic")
        ):
            for item_index in range(33):
                sample_id = f"sample-{class_index}-{item_index}"
                locked_test.append(
                    {"rruff_id": sample_id, "crystal_system": crystal_system}
                )
                prediction_rows.append(
                    {
                        "K": 1,
                        "episode_seed": 42,
                        "train_seed": "seed-a",
                        "method": "method-a",
                        "sample_id": sample_id,
                        "true_class": crystal_system,
                        "true_idx": class_index,
                        "pred_class": crystal_system,
                        "pred_idx": class_index,
                        "correct": 1,
                    }
                )

        fewshot = {
            "results": [
                {
                    "K": 1,
                    "episode_seed": 42,
                    "train_seed": "seed-a",
                    "method": "method-a",
                    "accuracy": 1.0,
                    "macro_f1": 0.5,
                    "per_class_f1": {
                        crystal_system: 1.0
                        for crystal_system in (
                            "triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic"
                        )
                    },
                }
            ]
        }
        fixed = {
            "results": [
                {
                    "K": K,
                    "episode_seed": 42,
                    "train_seed": "seed-a",
                    "method": "method-a",
                    "accuracy": 1.0,
                    "macro_f1": 1.0,
                    "optimizer_steps": 200,
                }
                for K in (1, 5)
            ]
        }
        zero = {
            "results": [
                {
                    "seed": "seed-a",
                    "method": "method-a",
                    "accuracy": 1.0,
                    "macro_f1": 1.0,
                    "per_class_f1": {
                        crystal_system: 1.0
                        for crystal_system in (
                            "triclinic", "monoclinic", "orthorhombic", "tetragonal", "trigonal", "hexagonal", "cubic"
                        )
                    },
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payloads = {
                "fewshot_runs": fewshot,
                "predictions": {"predictions": prediction_rows},
                "fixed200": fixed,
                "zero_shot": zero,
            }
            paths = {}
            for name, payload in payloads.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                paths[name] = path

            with (
                mock.patch(
                    "xrd_robustness.evaluation.rruff301_replay.K_VALUES", (1,)
                ),
                mock.patch(
                    "xrd_robustness.evaluation.rruff301_replay.EPISODE_SEEDS", (42,)
                ),
                mock.patch(
                    "xrd_robustness.evaluation.rruff301_replay.TRAIN_SEEDS", ("seed-a",)
                ),
                mock.patch(
                    "xrd_robustness.evaluation.rruff301_replay.METHODS", ("method-a",)
                ),
                self.assertRaisesRegex(ReplayContractError, "macro_f1 mismatch"),
            ):
                from xrd_robustness.evaluation import rruff301_replay

                rruff301_replay._audit_result_payloads(paths, locked_test)

    def test_configured_invalid_v1_cannot_become_canonical(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract["dataset"]["canonical_split"]["sha256"] = KNOWN_INVALID_V1_SPLIT_SHA256
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            config_dir = temporary_root / "configs"
            config_dir.mkdir()
            mutated = config_dir / "contract.json"
            mutated.write_text(json.dumps(contract), encoding="utf-8")
            with self.assertRaisesRegex(ReplayContractError, "known-invalid v1"):
                build_retrospective_episode_plan(mutated, project_root=temporary_root)


if __name__ == "__main__":
    unittest.main()
