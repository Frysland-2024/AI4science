"""Integration coverage for the versioned pilot renderer and validation mode."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.simulator_v10 import DEFAULT_LINE_PROFILE
from xrd_robustness.training_prefetch import DynamicBatchPrefetcher
from xrd_robustness.physics import PhysicsParameterSampler
from xrd_robustness.view_manifest import build_parameter_batch


def _fixed(value: float) -> dict[str, float | str]:
    return {
        "distribution": "fixed",
        "min_value": value,
        "max_value": value,
        "apply_probability": 1.0,
    }


def _profile() -> dict[str, object]:
    return {
        "severity_level": 0,
        "background_type": "flat",
        "delta_2theta_deg": _fixed(0.0),
        "fwhm_deg": _fixed(0.15),
        "background_to_peak_ratio": _fixed(0.0),
        "noise_std_ratio": _fixed(0.0),
    }


def _sim_config() -> dict[str, object]:
    return {
        "run_seed": 37,
        "profiles": {
            "train": _profile(),
            "validation": _profile(),
        },
    }


def _write_peak_table(data_root: Path) -> None:
    peak_path = (
        data_root
        / "mp_processed"
        / "peak_tables_v7_reflection"
        / "mp-pilot-test.npz"
    )
    peak_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        peak_path,
        positions=np.asarray([23.2, 41.7, 67.4], dtype=np.float64),
        intensities=np.asarray([1.0, 0.65, 0.30], dtype=np.float64),
    )


def _load_pilot_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_simxrd_architecture_pilot.py"
    )
    spec = importlib.util.spec_from_file_location(
        "run_simxrd_architecture_pilot_for_tests", script_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _render_training_batch(data_root: Path, version: str) -> np.ndarray:
    config = _sim_config()
    sampler = PhysicsParameterSampler.from_mapping({**config, "run_seed": 91})
    material_ids = ["mp-pilot-test"]
    rows = build_parameter_batch(
        material_ids,
        sampler,
        profile="train",
        epoch=0,
        global_step=0,
        split="train",
    )
    prefetcher = DynamicBatchPrefetcher(
        worker_count=1,
        worker_native_threads=1,
        prefetch_batches=1,
        start_method="spawn",
        data_root=data_root,
        peak_cache_name="peak_tables_v7_reflection",
        sampler_config={**config, "run_seed": 91},
        quality_gate=False,
        quality_gate_config={},
        simulation_config_hash="integration-test-config",
        profile="train",
        simulator_version=version,
        line_profile_config=DEFAULT_LINE_PROFILE,
    )
    try:
        prefetcher.submit(0, material_ids, rows)
        return prefetcher.get(0).first[0].copy()
    finally:
        prefetcher.close()


def test_selected_v10_changes_training_prefetch_views(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    _write_peak_table(data_root)

    v9 = _render_training_batch(data_root, "v9_gaussian")
    v10 = _render_training_batch(data_root, "v10_pseudo_voigt_caglioti")

    assert v9.shape == v10.shape == (3501,)
    assert float(np.max(np.abs(v9 - v10))) > 1e-4


def test_selected_v10_changes_validation_panel_views(tmp_path: Path) -> None:
    pilot = _load_pilot_module()
    data_root = tmp_path / "data"
    _write_peak_table(data_root)
    manifest = data_root / "manifests" / "split_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")
    config_path = tmp_path / "simulation.json"
    config_path.write_text(json.dumps(_sim_config()), encoding="utf-8")
    split_rows = [
        {
            "material_id": "mp-pilot-test",
            "crystal_system": CRYSTAL_SYSTEMS[0],
            "split": "validation",
        }
    ]

    def render(version: str) -> np.ndarray:
        line_profile = DEFAULT_LINE_PROFILE if version == "v10_pseudo_voigt_caglioti" else {}
        arrays, _, _, _ = pilot._build_panels(
            data_root=data_root,
            output_root=tmp_path / "panels",
            split_rows=split_rows,
            split="validation",
            simulator_version=version,
            sim_config=_sim_config(),
            sim_config_path=config_path,
            line_profile=line_profile,
            seed=53,
            profiles=("validation",),
        )
        return np.array(arrays["validation"][0], copy=True)

    v9 = render("v9_gaussian")
    v10 = render("v10_pseudo_voigt_caglioti")

    assert v9.shape == v10.shape == (3501,)
    assert float(np.max(np.abs(v9 - v10))) > 1e-4


class _TinyClassifier(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.dropout = torch.nn.Dropout(p=0.5)
        self.projection = torch.nn.Linear(3501, 7)

    def forward(self, spectra: torch.Tensor) -> dict[str, torch.Tensor]:
        return {"logits": self.projection(self.dropout(spectra))}


def test_validation_restores_the_incoming_training_mode() -> None:
    pilot = _load_pilot_module()
    model = _TinyClassifier()
    spectra = np.zeros((2, 3501), dtype=np.float32)
    labels = np.asarray([0, 1], dtype=np.int64)

    model.train()
    pilot._evaluate_one_panel(
        model, spectra, labels, device=torch.device("cpu"), batch_size=1
    )
    assert model.training
    assert model.dropout.training

    model.eval()
    pilot._evaluate_one_panel(
        model, spectra, labels, device=torch.device("cpu"), batch_size=1
    )
    assert not model.training
    assert not model.dropout.training
