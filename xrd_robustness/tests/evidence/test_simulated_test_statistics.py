from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

import numpy as np
import pytest

from xrd_robustness.evaluation.statistics import (
    build_paired_statistics_report,
    class_stratified_paired_bootstrap,
    hierarchical_paired_bootstrap,
    interpret_single_contrast,
    validate_prediction_rows,
)


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_simulated_test.py"
SPEC = importlib.util.spec_from_file_location("public_simulated_test_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _gate() -> dict:
    return {
        "experiment_sha256": "experiment",
        "data_config_sha256": "data",
        "source_records_sha256": "records",
        "simulation_sha256": "simulation",
        "split_sha256": "split",
        "peak_cache_manifest_sha256": "peaks",
        "runner_source_sha256": "runner",
        "renderer_source_sha256": {"renderer.py": "renderer"},
        "profiles": ["level0", "in_range", "ood"],
        "evaluation_seeds": [1, 2, 3],
        "checkpoints": [],
    }


class PairedStatisticsTests(unittest.TestCase):
    def test_class_stratified_bootstrap_uses_one_shared_parent_draw(self) -> None:
        rows = []
        for seed in (11, 23):
            for parent in range(20):
                label = parent % 2
                prediction = label if parent % 5 else 1 - label
                for method in ("baseline", "focus"):
                    rows.append(
                        {
                            "seed": seed,
                            "method_id": method,
                            "parent_structure_id": f"p{parent}",
                            "label": label,
                            "prediction": prediction,
                        }
                    )

        result = class_stratified_paired_bootstrap(
            rows,
            focus_method_id="focus",
            comparator_method_id="baseline",
            num_classes=2,
            replicates=300,
            random_seed=7,
        )

        self.assertEqual(result["class_stratified_bootstrap_95_ci"], [0.0, 0.0])
        self.assertTrue(result["parent_resampling_shared_across_methods_and_seeds"])

    def test_class_stratified_bootstrap_shares_parent_draw_across_seeds(self) -> None:
        rows = []
        for seed in (11, 23):
            for parent in range(20):
                label = parent % 2
                degraded = 1 - label if parent % 5 == 0 else label
                predictions = (
                    {"baseline": degraded, "focus": label}
                    if seed == 11
                    else {"baseline": label, "focus": degraded}
                )
                for method, prediction in predictions.items():
                    rows.append(
                        {
                            "seed": seed,
                            "method_id": method,
                            "parent_structure_id": f"p{parent}",
                            "label": label,
                            "prediction": prediction,
                        }
                    )

        result = class_stratified_paired_bootstrap(
            rows,
            focus_method_id="focus",
            comparator_method_id="baseline",
            num_classes=2,
            replicates=300,
            random_seed=7,
        )

        self.assertEqual(result["class_stratified_bootstrap_95_ci"], [0.0, 0.0])

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


def test_public_contract_resolves_ten_resnet_runs_and_profiles() -> None:
    contract, simulation_path, simulation = RUNNER.load_public_contract()
    data_path, data = RUNNER.load_data_contract(contract, verify_files=False)
    assert len(RUNNER.run_specs(contract)) == 10
    assert len(contract["evaluation_seeds"]) == 3
    assert {row["method"] for row in RUNNER.run_specs(contract)} == {
        "dynamic_erm",
        "dynamic_js",
    }
    assert RUNNER.flatten_profiles(contract)
    assert simulation_path.name == "simulation.method_transfer.frozen.json"
    assert set(RUNNER.flatten_profiles(contract)).issubset(simulation["profiles"])
    assert data_path.name == "data.method_transfer.structure_split.json"
    assert data["schema_version"] == "parent-structure-data-split-v1"


def test_runtime_bindings_cover_checkpoints_and_view_manifest() -> None:
    value = _gate()
    value["checkpoints"] = [{"run_id": "run-a", "sha256": "checkpoint-a"}]
    assert RUNNER.cache_bindings(value)["checkpoint_sha256"] == {
        "run-a": "checkpoint-a"
    }
    assert "src/xrd_robustness/view_manifest.py" in RUNNER.renderer_source_hashes()


def test_cache_entry_requires_matching_hash_shape_and_float32(tmp_path: Path) -> None:
    path = tmp_path / "panel.npy"
    np.save(path, np.zeros((3, 5), dtype=np.float32), allow_pickle=False)
    entry = {
        "path": "panel.npy",
        "sha256": RUNNER.sha256(path),
        "shape": [3, 5],
        "dtype": "float32",
    }
    assert RUNNER.valid_cache_entry(entry, tmp_path)
    assert not RUNNER.valid_cache_entry({**entry, "sha256": "wrong"}, tmp_path)
    assert not RUNNER.valid_cache_entry({**entry, "shape": [5, 3]}, tmp_path)


def test_run_state_is_atomic_resumable_and_batch_locked(tmp_path: Path) -> None:
    first = RUNNER.initialize_or_resume_run(
        _gate(), 128, output_root=tmp_path, device="cpu"
    )
    second = RUNNER.initialize_or_resume_run(
        _gate(), 128, output_root=tmp_path, device="cpu"
    )
    assert first == second
    assert first["status"] == "in_progress"
    assert first["completed_run_sha256"] == {}
    assert (tmp_path / "run_state.json").is_file()
    assert not (tmp_path / "run_state.json.tmp").exists()
    with pytest.raises(RuntimeError, match="batch size differs"):
        RUNNER.initialize_or_resume_run(
            _gate(), 256, output_root=tmp_path, device="cpu"
        )


def test_named_crystal_system_f1_uses_full_confusion_matrix() -> None:
    labels = np.repeat(np.arange(7), 2)
    predictions = labels.copy()
    predictions[0] = 1
    metrics = RUNNER.classification_metrics(labels, predictions, num_classes=7)
    named = RUNNER.add_named_crystal_system_f1(metrics)
    assert named["per_crystal_system_f1"] == {
        system: pytest.approx(metrics["per_class_f1"][index])
        for index, system in enumerate(RUNNER.CRYSTAL_SYSTEMS)
    }


def test_runner_uses_public_contract_and_configurable_runtime_output(
    tmp_path: Path,
) -> None:
    assert RUNNER.EXPERIMENT_PATH.name == "experiment.public.json"
    assert RUNNER.EXPERIMENT_PATH.is_file()
    args = RUNNER.build_parser().parse_args(
        ["preflight", "--output-root", str(tmp_path)]
    )
    assert args.experiment_config == RUNNER.EXPERIMENT_PATH
    assert args.output_root == tmp_path


if __name__ == "__main__":
    unittest.main()
