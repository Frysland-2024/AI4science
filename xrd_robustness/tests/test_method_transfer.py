import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from xrd_robustness.method_transfer import (
    audit_contract_assets,
    audit_final_evaluation_locks,
    build_run_plan,
    build_tuning_plan,
    evaluate_validation_comparison,
    evaluate_tuning_selection,
    load_contract,
    sha256_file,
    validate_contract,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "configs" / "algorithm.v9.method_transfer.json"
METHOD_PARAMETER_GOVERNANCE_PATH = (
    PROJECT_ROOT / "configs" / "v9_method_parameter_governance.json"
)
HASH_A = hashlib.sha256(b"a").hexdigest().upper()
HASH_B = hashlib.sha256(b"b").hexdigest().upper()
HASH_C = hashlib.sha256(b"c").hexdigest().upper()


def _metrics(value: float) -> dict:
    return {
        "accuracy": value,
        "balanced_accuracy": value,
        "macro_f1": value,
        "per_class_recall": [value] * 7,
        "per_class_f1": [value] * 7,
        "confusion_matrix": [[1 if row == column else 0 for column in range(7)] for row in range(7)],
        "worst_group_f1": value,
        "ece": 0.05,
    }


class MethodTransferContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = load_contract(CONTRACT_PATH)
        cls.method_parameter_governance = json.loads(
            METHOD_PARAMETER_GOVERNANCE_PATH.read_text(encoding="utf-8")
        )

    def test_hu_et_al_parameter_provenance_cannot_authorize_v9_residual_grid(self):
        provenance = self.method_parameter_governance[
            "literature_parameter_provenance"
        ]["hu_et_al_2026_sd3net"]
        self.assertEqual(provenance["doi"], "10.1016/j.knosys.2026.116429")
        self.assertEqual(
            provenance["local_primary_pdf_sha256"],
            "5F30D94A288542EA173F4A774B9CBE2EB27CD0A8B6B6E9667FB62514E816579F",
        )
        self.assertEqual(
            provenance["paper_loss_definition"]["paper_equations"], [16, 17]
        )
        self.assertEqual(provenance["table_5_record"]["lambda_3_fixed_anchor"], 1.0)
        self.assertEqual(
            provenance["table_5_record"]["lambda_1_lambda_2_joint_search_range"],
            [0.1, 1.0],
        )
        self.assertEqual(
            provenance["figure_12_record"]["reported_optimum"], 0.0001
        )
        self.assertFalse(
            provenance["figure_12_record"]["explicit_mapping_to_lambda_3"]
        )
        self.assertIn(
            "copy 1e-4 into V9-T lambda_res",
            provenance["prohibited_evidentiary_use"],
        )
        residual_source = self.method_parameter_governance["parameter_sources"][
            "lambda_res"
        ]
        self.assertFalse(residual_source["external_numerical_authority"])
        self.assertEqual(
            self.method_parameter_governance["tuning_gate"][
                "candidate_range_frozen_for_validation"
            ],
            False,
        )

    def test_current_assets_and_locked_splits_pass_preflight(self):
        audit = audit_contract_assets(self.contract, PROJECT_ROOT)
        self.assertEqual(audit["status"], "passed")
        self.assertEqual(audit["split_counts"], {"train": 9842, "validation": 2109, "test": 2109})
        self.assertEqual(audit["development_validation_count"], 2109)
        self.assertEqual(audit["cross_split_family_count"], 0)
        self.assertEqual(audit["development_tuning_run_count"], 7)
        self.assertEqual(audit["formal_development_run_count"], 15)
        self.assertEqual(audit["core_comparison_run_count"], 9)
        self.assertTrue(audit["simulated_test_locked"])
        self.assertTrue(audit["real_test_locked"])
        self.assertFalse(audit["experiment_execution_enabled"])
        self.assertEqual(
            audit["method_parameter_governance_status"],
            "candidate_range_recalibration_required_before_validation",
        )
        self.assertEqual(audit["method_parameter_candidate_range_gate"], "blocked")
        self.assertFalse(audit["method_parameter_tuning_execution_allowed"])
        self.assertEqual(
            audit["hashes"]["method_parameter_governance"],
            self.contract["method_parameter_governance"]["sha256"],
        )
        self.assertTrue(Path(self.contract["runtime"]["python_executable"]).is_file())
        self.assertEqual(
            audit["hashes"]["hardware_profile"],
            self.contract["hardware_profile"]["sha256"],
        )
        narrative = self.contract["narrative_policy"]
        self.assertEqual(
            narrative["current_program_priority"], "complete_algorithm_transfer_paper_first"
        )
        self.assertEqual(narrative["program_id"], "V9-T")
        self.assertEqual(narrative["paper_scope"], "algorithm_transfer_only")
        self.assertEqual(narrative["deferred_research"], "simulator_label_supervised_residual")
        self.assertEqual(narrative["deferred_program_id"], "V10")
        self.assertEqual(
            narrative["challenged_paradigm"], "augmentation_only_supervised_learning"
        )
        self.assertEqual(
            narrative["registered_method_progression"],
            [
                "augmentation_only_supervised_learning",
                "cross_view_prediction_consistency",
                "difference_aware_residual_class_decorrelation",
            ],
        )
        self.assertEqual(
            narrative["dynamic_perturbation_role"],
            "strong_matched_augmentation_only_baseline_and_paired_view_infrastructure",
        )
        self.assertFalse(narrative["dynamic_perturbation_claimed_as_innovation"])
        self.assertFalse(narrative["structured_perturbation_in_scope"])
        self.assertFalse(narrative["simulator_label_supervision_in_scope"])

    def test_tuning_plan_is_seven_full_budget_validation_only_runs(self):
        plan = build_tuning_plan(self.contract, PROJECT_ROOT)
        self.assertEqual(plan["run_count"], 7)
        self.assertEqual(
            plan["execution_enabled"],
            self.contract["development_tuning"]["execution_enabled"],
        )
        self.assertEqual(
            plan["execution_enabled"],
            self.contract["execution_policy"]["development_tuning_execution_enabled"],
        )
        self.assertFalse(plan["execution_enabled"])
        self.assertEqual(len({run["run_id"] for run in plan["runs"]}), 7)
        for run in plan["runs"]:
            self.assertIn("--development-only", run["argv"])
            self.assertIn("--development-subset-manifest", run["argv"])
            self.assertIn("--evaluation-seed", run["argv"])
            self.assertIn("--dynamic-prefetch-workers", run["argv"])
            self.assertIn("--dynamic-prefetch-batches", run["argv"])
            self.assertIn("--dynamic-prefetch-worker-native-threads", run["argv"])
            self.assertIn("--pin-memory", run["argv"])
            self.assertIn("--non-blocking-h2d", run["argv"])
            self.assertIn("--main-process-intraop-threads", run["argv"])
            self.assertIn("--main-process-interop-threads", run["argv"])
            self.assertIn("--float32-matmul-precision", run["argv"])
            self.assertIn("--allow-tf32", run["argv"])
            self.assertIn("--cudnn-benchmark", run["argv"])
            self.assertIn("--cudnn-deterministic", run["argv"])
            self.assertIn("--fused-adamw", run["argv"])
            self.assertIn("--amp", run["argv"])
            self.assertIn("--amp-dtype", run["argv"])
            self.assertIn("--amp-fallback-to-float32", run["argv"])
            self.assertIn("--torch-compile", run["argv"])
            self.assertIn("--torch-compile-backend", run["argv"])
            self.assertIn("--torch-compile-mode", run["argv"])
            self.assertIn("--torch-compile-fallback-to-eager", run["argv"])
            worker_flag = run["argv"].index("--dynamic-prefetch-workers")
            batch_flag = run["argv"].index("--dynamic-prefetch-batches")
            native_thread_flag = run["argv"].index(
                "--dynamic-prefetch-worker-native-threads"
            )
            self.assertEqual(
                int(run["argv"][worker_flag + 1]),
                self.contract["experiment"]["dynamic_view_prefetch"]["worker_processes"],
            )
            self.assertEqual(
                int(run["argv"][batch_flag + 1]),
                self.contract["experiment"]["dynamic_view_prefetch"]["prefetch_batches"],
            )
            self.assertEqual(
                int(run["argv"][native_thread_flag + 1]),
                self.contract["experiment"]["dynamic_view_prefetch"][
                    "worker_native_threads"
                ],
            )
            self.assertEqual(
                run["argv"][run["argv"].index("--amp-dtype") + 1], "bfloat16"
            )
            self.assertEqual(
                run["argv"][run["argv"].index("--torch-compile-backend") + 1],
                "inductor",
            )
            self.assertEqual(
                run["argv"][run["argv"].index("--torch-compile-mode") + 1],
                "default",
            )
            self.assertNotIn("perturbation_supervised_residual", run["argv"])
            self.assertEqual(
                run["development_subset_manifest_hash"],
                self.contract["data"]["development_validation_manifest_sha256"],
            )
            self.assertTrue(run["simulated_test_locked"])
            self.assertTrue(run["real_test_locked"])

    def test_contract_rejects_dynamic_augmentation_as_the_challenged_paradigm(self):
        contract = copy.deepcopy(self.contract)
        contract["narrative_policy"]["challenged_paradigm"] = "dynamic_augmentation"
        with self.assertRaisesRegex(ValueError, "augmentation-only paradigm"):
            validate_contract(contract)

    def test_contract_rejects_tuning_when_method_parameter_range_is_not_frozen(self):
        contract = copy.deepcopy(self.contract)
        contract["development_tuning"]["execution_enabled"] = True
        contract["execution_policy"]["development_tuning_execution_enabled"] = True
        contract["method_parameter_governance"][
            "development_tuning_execution_allowed"
        ] = True
        with self.assertRaisesRegex(ValueError, "candidate range is frozen"):
            validate_contract(contract)

    def test_contract_rejects_candidate_grid_outside_governance(self):
        contract = copy.deepcopy(self.contract)
        contract["development_tuning"]["candidates"][0]["values"] = [0.3, 1.0, 3.0]
        with self.assertRaisesRegex(ValueError, "unexpected development tuning grids"):
            validate_contract(contract)

    def test_formal_plan_fails_closed_before_tuning_freeze(self):
        with self.assertRaisesRegex(ValueError, "tuning selection has not been frozen"):
            build_run_plan(self.contract, PROJECT_ROOT)

    def test_formal_plan_contains_clean_offline_and_three_core_methods(self):
        with patch(
            "xrd_robustness.method_transfer._frozen_hyperparameters",
            return_value={"lambda_js": 0.3, "lambda_res": 0.1},
        ):
            plan = build_run_plan(self.contract, PROJECT_ROOT)
        self.assertEqual(plan["run_count"], 15)
        self.assertEqual({run["mode"] for run in plan["runs"]}, {
            "clean_erm", "offline_erm", "dynamic_erm", "dynamic_js", "dynamic_residual"
        })
        for run in plan["runs"]:
            self.assertIn("--development-only", run["argv"])
            self.assertEqual(
                run["development_subset_manifest_hash"],
                self.contract["data"]["development_validation_manifest_sha256"],
            )
        clean = next(run for run in plan["runs"] if run["mode"] == "clean_erm")
        offline = next(run for run in plan["runs"] if run["mode"] == "offline_erm")
        js = next(run for run in plan["runs"] if run["mode"] == "dynamic_js")
        residual = next(run for run in plan["runs"] if run["mode"] == "dynamic_residual")
        self.assertIn("--clean-profile", clean["argv"])
        self.assertIn("--offline-views", offline["argv"])
        self.assertIn("--paired-offline-views", offline["argv"])
        self.assertEqual(js["hyperparameters"]["lambda_js"], 0.3)
        self.assertEqual(residual["hyperparameters"]["lambda_res"], 0.1)

    def test_final_test_contracts_remain_locked(self):
        audit = audit_final_evaluation_locks(self.contract, PROJECT_ROOT)
        self.assertEqual(audit["status"], "locked_as_required")
        self.assertTrue(audit["simulated_test_locked"])
        self.assertTrue(audit["real_test_locked"])
        self.assertFalse(audit["simulated_test_used"])
        self.assertFalse(audit["real_test_used"])


class SyntheticResultMixin:
    contract: dict

    def _write_result(
        self,
        output: Path,
        method: dict,
        seed: int,
        run_id: str,
        *,
        subset_hash: str,
        in_range: float,
        ood: float,
        evaluation_manifest_hash: str = HASH_A,
        view_manifest_hash: str = HASH_B,
        training_sampler_hash: str = HASH_A,
        pair_schedule_hash: str = HASH_B,
        parameter_pair_hash: str = HASH_C,
        locked: bool = True,
    ) -> None:
        profiles = self.contract["simulation"]["development_ood_profiles"]
        result = {
            "run_id": run_id,
            "mode": method["mode"],
            "seed": seed,
            "evaluation_seed": self.contract["evaluation"]["development_evaluation_seed"],
            "unique_train_structures": 9842,
            "study_contract_hash": sha256_file(CONTRACT_PATH),
            "evaluation_contract_hash": self.contract["evaluation"]["sha256"],
            "resolved_config_hash": HASH_C,
            "source_tree_hash": HASH_C,
            "training_sampler_contract_hash": HASH_C,
            "training_stream_audit_hash": HASH_C,
            "training_stream_audit": {
                "schema_version": "training-stream-v1",
                "sampler_contract_hash": HASH_C,
                "sampler_hash": training_sampler_hash,
                "pair_schedule_hash": pair_schedule_hash,
                "parameter_pair_hash": parameter_pair_hash,
                "optimizer_steps": 30650,
                "structure_exposures": 490400,
                "spectrum_exposures": 980800,
            },
            "view_manifest_hash": view_manifest_hash,
            "evaluation_manifest_hash": evaluation_manifest_hash,
            "checkpoint_hash": HASH_C,
            "offline_manifest_hash": HASH_C if method["mode"] in {"clean_erm", "offline_erm"} else None,
            "data_manifest_hash": self.contract["data"]["split_manifest_sha256"],
            "development_subset_manifest_hash": subset_hash,
            "simulation_config_hash": self.contract["simulation"]["sha256"],
            "peak_cache_manifest_hash": self.contract["data"]["peak_cache_manifest_sha256"],
            "runtime_provenance": {
                "python_version": self.contract["runtime"]["python_version"],
                "torch_version": self.contract["runtime"]["torch_version"],
                "cuda_runtime": self.contract["runtime"]["cuda_runtime"],
                "gpu_name": self.contract["runtime"]["gpu_name"],
                "device": "cuda:0",
            },
            "evaluation_scope": {
                "development_only": locked,
                "selection_split": "validation" if locked else "test",
                "simulated_test_locked": locked,
                "real_test_locked": True,
            },
            "compute_summary": {
                "optimizer_steps": 30650,
                "training_backbone_forward_views": 61300,
                "training_structure_exposures": 490400,
                "training_view_exposures": 980800,
                "wall_clock_seconds": 100.0,
                "gpu_hours": 0.03,
                "peak_gpu_memory_mb": 1000.0,
            },
            "history": [
                {
                    "epoch": 50,
                    "in_range": _metrics(in_range),
                    "ood": {name: _metrics(ood) for name in profiles},
                }
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        in_range_profile = self.contract["simulation"]["in_range_profile"]
        for profile, value in [(in_range_profile, in_range), *[(name, ood) for name in profiles]]:
            row_accuracy = max(0.05, min(0.95, 0.5 + (float(value) - 0.58) * 5.0))
            correct_count = int(round(row_accuracy * 210))
            for family in range(210):
                label = family % 7
                prediction = label if family < correct_count else (label + 1) % 7
                probabilities = [0.01] * 7
                probabilities[prediction] = 0.94
                rows.append({
                    "seed": seed,
                    "method_id": method["id"],
                    "profile": profile,
                    "material_id": f"mp-{family}",
                    "family_id": f"family-{family}",
                    "label": label,
                    "prediction": prediction,
                    "probabilities": probabilities,
                })
        prediction_path = output.parent / "prediction_rows.jsonl"
        prediction_path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        result["prediction_rows"] = {
            "path": prediction_path.name,
            "sha256": sha256_file(prediction_path),
            "row_count": len(rows),
        }
        output.write_text(json.dumps(result), encoding="utf-8")


class MethodTransferTuningTests(SyntheticResultMixin, unittest.TestCase):
    def setUp(self):
        self.contract = load_contract(CONTRACT_PATH)

    def test_tuning_selects_best_guardrail_eligible_registered_values(self):
        plan = build_tuning_plan(self.contract, PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for run in plan["runs"]:
                method = next(
                    item for item in self.contract["experiment"]["methods"]
                    if item["id"] == run["method_id"]
                )
                if run["role"] == "baseline":
                    ood = 0.60
                elif "lambda_js" in run["hyperparameters"]:
                    ood = {0.1: 0.61, 0.3: 0.625, 1.0: 0.62}[
                        float(run["hyperparameters"]["lambda_js"])
                    ]
                else:
                    ood = {0.01: 0.59, 0.1: 0.605, 1.0: 0.603}[
                        float(run["hyperparameters"]["lambda_res"])
                    ]
                self._write_result(
                    root / run["run_id"] / "results.json",
                    method,
                    int(run["seed"]),
                    str(run["run_id"]),
                    subset_hash=self.contract["data"]["development_validation_manifest_sha256"],
                    in_range=0.80,
                    ood=ood,
                )
            selection = evaluate_tuning_selection(self.contract, root, PROJECT_ROOT)
            self.assertEqual(selection["status"], "selected")
            self.assertEqual(selection["selected_values"], {"lambda_js": 0.3, "lambda_res": 0.1})
            self.assertFalse(selection["simulated_test_used"])
            self.assertFalse(selection["real_test_used"])

    def test_tuning_fails_closed_on_sampler_hash_mismatch(self):
        plan = build_tuning_plan(self.contract, PROJECT_ROOT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for run in plan["runs"]:
                method = next(
                    item for item in self.contract["experiment"]["methods"]
                    if item["id"] == run["method_id"]
                )
                self._write_result(
                    root / run["run_id"] / "results.json",
                    method,
                    int(run["seed"]),
                    str(run["run_id"]),
                    subset_hash=self.contract["data"]["development_validation_manifest_sha256"],
                    in_range=0.80,
                    ood=0.60,
                    training_sampler_hash=(HASH_B if run is plan["runs"][0] else HASH_A),
                )
            with self.assertRaisesRegex(ValueError, "matched sampler"):
                evaluate_tuning_selection(self.contract, root, PROJECT_ROOT)


class MethodTransferUnifiedValidationTests(SyntheticResultMixin, unittest.TestCase):
    def setUp(self):
        self.contract = copy.deepcopy(load_contract(CONTRACT_PATH))
        self.contract["formal_hyperparameters"]["frozen"] = True
        self.contract["formal_hyperparameters"]["values"] = {
            "lambda_js": 0.3,
            "lambda_res": 0.1,
        }

    def _synthetic_results(
        self,
        root: Path,
        *,
        unlock_one: bool = False,
        js_ood: float = 0.621,
        residual_ood: float = 0.605,
    ) -> None:
        for method_index, method in enumerate(self.contract["experiment"]["methods"]):
            for seed_index, seed in enumerate(self.contract["experiment"]["seeds"]):
                if method["mode"] == "dynamic_js":
                    in_range, ood = 0.795, js_ood + seed_index * 0.001
                elif method["mode"] == "dynamic_residual":
                    in_range, ood = 0.81, residual_ood + seed_index * 0.001
                elif method["mode"] == "dynamic_erm":
                    in_range, ood = 0.80, 0.60
                elif method["mode"] == "clean_erm":
                    in_range, ood = 0.78, 0.50
                else:
                    in_range, ood = 0.79, 0.57
                self._write_result(
                    root / method["id"] / f"seed_{seed}" / "results.json",
                    method,
                    int(seed),
                    f"{method['id']}__seed_{seed}",
                    subset_hash=self.contract["data"]["development_validation_manifest_sha256"],
                    in_range=in_range,
                    ood=ood,
                    view_manifest_hash=(HASH_B if method["role"] in {"baseline", "candidate"} else hashlib.sha256(method["id"].encode()).hexdigest().upper()),
                    locked=not (unlock_one and method["mode"] == "dynamic_js" and seed_index == 0),
                )

    def test_validation_comparison_selects_highest_scoring_registered_method(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._synthetic_results(root)
            report = evaluate_validation_comparison(self.contract, root, PROJECT_ROOT)
            self.assertEqual(report["status"], "selected")
            self.assertEqual(report["formal_run_count"], 15)
            self.assertEqual(report["selected_method"], "js_consistency_transfer")
            self.assertFalse(report["pass_fail_decision_used"])
            self.assertIn("clean_erm_reference", report["method_summaries"])
            self.assertIn("offline_physical_augmentation_reference", report["method_summaries"])
            self.assertEqual(
                report["paper_narrative_outcome"],
                "js_effective_residual_no_extra_gain",
            )
            self.assertTrue(
                all(
                    value < 0
                    for value in report["paired_comparisons"]["residual_minus_js"]["paired_seed_deltas"]
                )
            )
            self.assertFalse(report["simulated_test_used"])
            self.assertFalse(report["real_test_used"])

    def test_validation_comparison_reports_direct_paired_residual_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._synthetic_results(root, js_ood=0.615, residual_ood=0.640)
            report = evaluate_validation_comparison(self.contract, root, PROJECT_ROOT)
            self.assertEqual(report["selected_method"], "residual_decorrelation_transfer")
            self.assertEqual(
                report["paper_narrative_outcome"],
                "residual_stably_beats_dynamic_and_js",
            )
            self.assertTrue(
                report["paired_comparisons"]["residual_minus_js"]["all_seed_deltas_positive"]
            )

    def test_validation_comparison_fails_closed_if_test_split_was_unlocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._synthetic_results(root, unlock_one=True)
            with self.assertRaisesRegex(ValueError, "test lock violated"):
                evaluate_validation_comparison(self.contract, root, PROJECT_ROOT)

    def test_validation_comparison_fails_closed_on_pair_schedule_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._synthetic_results(root)
            path = root / "clean_erm_reference" / "seed_20260711" / "results.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            result["training_stream_audit"]["pair_schedule_hash"] = HASH_A
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pair_schedule_hash"):
                evaluate_validation_comparison(self.contract, root, PROJECT_ROOT)

    def test_validation_comparison_fails_closed_on_dynamic_parameter_pair_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._synthetic_results(root)
            path = root / "js_consistency_transfer" / "seed_20260711" / "results.json"
            result = json.loads(path.read_text(encoding="utf-8"))
            result["training_stream_audit"]["parameter_pair_hash"] = HASH_A
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "parameter_pair_hash"):
                evaluate_validation_comparison(self.contract, root, PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
