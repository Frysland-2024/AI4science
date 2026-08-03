from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_v9_resnet_js_simulated_test.py"
)
SPEC = importlib.util.spec_from_file_location("simulated_test_runner", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def gate() -> dict:
    return {
        "contract_sha256": "contract",
        "simulation_sha256": "simulation",
        "split_sha256": "split",
        "peak_cache_manifest_sha256": "peaks",
        "source_sha256": "source",
        "renderer_source_sha256": {"renderer.py": "renderer"},
        "manifests": [
            {"path": "manifest-a.csv", "sha256": "manifest-a"},
            {"path": "manifest-b.csv", "sha256": "manifest-b"},
        ],
    }


def test_cache_entry_requires_matching_hash_shape_and_float32(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    path = tmp_path / "panel.npy"
    np.save(path, np.zeros((3, 5), dtype=np.float32), allow_pickle=False)
    entry = {
        "path": "panel.npy",
        "sha256": runner.sha256(path),
        "shape": [3, 5],
        "dtype": "float32",
    }
    assert runner.valid_cache_entry(entry)
    assert not runner.valid_cache_entry({**entry, "sha256": "wrong"})
    assert not runner.valid_cache_entry({**entry, "shape": [5, 3]})


def test_run_state_is_atomic_resumable_and_batch_locked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "output"
    output.mkdir()
    (output / "runner.stdout.log").write_text("", encoding="utf-8")
    monkeypatch.setattr(runner, "OUTPUT_ROOT", output)
    monkeypatch.setattr(runner, "RUN_STATE_PATH", output / "run_state.json")

    first = runner.initialize_or_resume_run(gate(), 128)
    second = runner.initialize_or_resume_run(gate(), 128)
    assert first == second
    assert first["status"] == "in_progress"
    assert first["completed_run_sha256"] == {}
    assert (output / "run_state.json").is_file()
    assert not (output / "run_state.json.tmp").exists()

    with pytest.raises(RuntimeError, match="batch size differs"):
        runner.initialize_or_resume_run(gate(), 256)


def test_cache_bindings_are_ordered_by_manifest_path() -> None:
    value = runner.cache_bindings(gate())
    assert value["runner_source_sha256"] == "source"
    assert value["renderer_source_sha256"] == {"renderer.py": "renderer"}
    assert value["manifests"] == {
        "manifest-a.csv": "manifest-a",
        "manifest-b.csv": "manifest-b",
    }
