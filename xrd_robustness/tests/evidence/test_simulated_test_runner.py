from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/run_simulated_test.py"
SPEC = importlib.util.spec_from_file_location("public_simulated_test_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def gate() -> dict:
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


def test_public_contract_resolves_ten_resnet_runs_and_profiles() -> None:
    contract, simulation_path, simulation = runner.load_public_contract()
    data_path, data = runner.load_data_contract(contract, verify_files=False)
    assert len(runner.run_specs(contract)) == 10
    assert len(contract["evaluation_seeds"]) == 3
    assert {row["method"] for row in runner.run_specs(contract)} == {
        "dynamic_erm",
        "dynamic_js",
    }
    assert runner.flatten_profiles(contract)
    assert simulation_path.name == "simulation.method_transfer.frozen.json"
    assert set(runner.flatten_profiles(contract)).issubset(simulation["profiles"])
    assert data_path.name == "data.method_transfer.structure_split.json"
    assert data["schema_version"] == "parent-structure-data-split-v1"


def test_runtime_bindings_cover_checkpoints_and_view_manifest() -> None:
    value = gate()
    value["checkpoints"] = [{"run_id": "run-a", "sha256": "checkpoint-a"}]
    assert runner.cache_bindings(value)["checkpoint_sha256"] == {
        "run-a": "checkpoint-a"
    }
    assert "src/xrd_robustness/view_manifest.py" in runner.renderer_source_hashes()


def test_cache_entry_requires_matching_hash_shape_and_float32(tmp_path: Path) -> None:
    path = tmp_path / "panel.npy"
    np.save(path, np.zeros((3, 5), dtype=np.float32), allow_pickle=False)
    entry = {
        "path": "panel.npy",
        "sha256": runner.sha256(path),
        "shape": [3, 5],
        "dtype": "float32",
    }
    assert runner.valid_cache_entry(entry, tmp_path)
    assert not runner.valid_cache_entry({**entry, "sha256": "wrong"}, tmp_path)
    assert not runner.valid_cache_entry({**entry, "shape": [5, 3]}, tmp_path)


def test_run_state_is_atomic_resumable_and_batch_locked(tmp_path: Path) -> None:
    first = runner.initialize_or_resume_run(
        gate(), 128, output_root=tmp_path, device="cpu"
    )
    second = runner.initialize_or_resume_run(
        gate(), 128, output_root=tmp_path, device="cpu"
    )
    assert first == second
    assert first["status"] == "in_progress"
    assert first["completed_run_sha256"] == {}
    assert (tmp_path / "run_state.json").is_file()
    assert not (tmp_path / "run_state.json.tmp").exists()
    with pytest.raises(RuntimeError, match="batch size differs"):
        runner.initialize_or_resume_run(
            gate(), 256, output_root=tmp_path, device="cpu"
        )


def test_named_crystal_system_f1_uses_full_confusion_matrix() -> None:
    labels = np.repeat(np.arange(7), 2)
    predictions = labels.copy()
    predictions[0] = 1
    metrics = runner.classification_metrics(labels, predictions, num_classes=7)
    named = runner.add_named_crystal_system_f1(metrics)
    assert named["per_crystal_system_f1"] == {
        system: pytest.approx(metrics["per_class_f1"][index])
        for index, system in enumerate(runner.CRYSTAL_SYSTEMS)
    }


def test_runner_uses_public_contract_and_configurable_runtime_output(
    tmp_path: Path,
) -> None:
    assert runner.EXPERIMENT_PATH.name == "experiment.public.json"
    assert runner.EXPERIMENT_PATH.is_file()
    args = runner.build_parser().parse_args(
        ["preflight", "--output-root", str(tmp_path)]
    )
    assert args.experiment_config == runner.EXPERIMENT_PATH
    assert args.output_root == tmp_path
