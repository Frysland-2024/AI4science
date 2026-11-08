"""Integration coverage for the versioned pilot renderer and validation mode."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from xrd_robustness.structure_data import CRYSTAL_SYSTEMS
from xrd_robustness.online_views import OnlineViewFactory
from xrd_robustness.simulation_interfaces import PeakTable
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



class _StaticPeakCache:
    def __init__(self, peaks: PeakTable) -> None:
        self.peaks = peaks

    def get_or_compute(self, material_id: str, source: object, grid: object) -> PeakTable:
        return self.peaks


def _versioned_factory(pilot, peaks: PeakTable, version: str, *, use_peak_cache: bool):
    config = _sim_config()
    sampler = PhysicsParameterSampler.from_mapping({**config, "run_seed": 73})
    peak_table_simulator = pilot._make_peak_table_simulator(version, DEFAULT_LINE_PROFILE)
    kwargs = {} if peak_table_simulator is None else {"peak_table_simulator": peak_table_simulator}
    return OnlineViewFactory(
        sampler,
        peak_cache=_StaticPeakCache(peaks) if use_peak_cache else None,
        **kwargs,
    )


def test_v10_is_used_for_peak_and_cached_structure_views() -> None:
    pilot = _load_pilot_module()
    peaks = PeakTable(
        positions=np.asarray([23.2, 41.7, 67.4], dtype=np.float64),
        intensities=np.asarray([1.0, 0.65, 0.30], dtype=np.float64),
    )

    for use_peak_cache in (False, True):
        v9_factory = _versioned_factory(
            pilot, peaks, "v9_gaussian", use_peak_cache=use_peak_cache
        )
        v10_factory = _versioned_factory(
            pilot, peaks, "v10_pseudo_voigt_caglioti", use_peak_cache=use_peak_cache
        )
        if use_peak_cache:
            view_v9 = v9_factory.make_pair(
                object(),
                material_id="mp-pilot-test",
                split="validation",
                epoch=0,
                global_step=0,
                profile="validation",
            ).first
            view_v10 = v10_factory.make_pair(
                object(),
                material_id="mp-pilot-test",
                split="validation",
                epoch=0,
                global_step=0,
                profile="validation",
            ).first
        else:
            view_v9 = v9_factory.make_pair_from_peaks(
                peaks,
                material_id="mp-pilot-test",
                split="validation",
                epoch=0,
                global_step=0,
                profile="validation",
            ).first
            view_v10 = v10_factory.make_pair_from_peaks(
                peaks,
                material_id="mp-pilot-test",
                split="validation",
                epoch=0,
                global_step=0,
                profile="validation",
            ).first
        assert float(np.max(np.abs(view_v9.xrd - view_v10.xrd))) > 1e-4


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


def test_nonfinite_losses_and_gradients_are_detected_before_optimizer_update() -> None:
    pilot = _load_pilot_module()
    model = torch.nn.Linear(2, 7, bias=False)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0)
    initial = model.weight.detach().clone()
    first = torch.ones((2, 2))
    second = torch.zeros((2, 2))
    target = torch.tensor([0, 1], dtype=torch.long)

    def training_result():
        return pilot.run_training_step(
            pilot.TrainingStepConfig(pilot.TrainingMode.DYNAMIC_JS, lambda_js=60.0),
            model,
            x1=first,
            x2=second,
            target=target,
        )

    result = training_result()
    assert result["logits_first"].shape == result["logits_second"].shape == (2, 7)
    bad_loss = dict(result)
    bad_loss["total"] = result["total"] * torch.tensor(float("nan"))
    assert pilot._optimizer_step_if_finite(bad_loss, model, optimizer) == "nonfinite_loss"
    assert torch.equal(model.weight.detach(), initial)

    bad_logits = dict(result)
    bad_logits["logits_first"] = result["logits_first"].clone()
    bad_logits["logits_first"][0, 0] = float("inf")
    assert pilot._optimizer_step_if_finite(bad_logits, model, optimizer) == "nonfinite_logits"
    assert torch.equal(model.weight.detach(), initial)

    hook = model.weight.register_hook(
        lambda gradient: torch.full_like(gradient, float("inf"))
    )
    assert pilot._optimizer_step_if_finite(training_result(), model, optimizer) == "nonfinite_gradient"
    assert torch.equal(model.weight.detach(), initial)

    hook.remove()
    optimizer.zero_grad(set_to_none=True)
    assert pilot._optimizer_step_if_finite(training_result(), model, optimizer) is None
    assert not torch.equal(model.weight.detach(), initial)


def test_smoke_integrator_falls_back_to_numpy_1x_trapz(monkeypatch) -> None:
    pilot = _load_pilot_module()
    fallback = getattr(np, "trapezoid", None)
    if fallback is None:
        fallback = lambda y, x: np.sum((y[:-1] + y[1:]) * np.diff(x) * 0.5)
    monkeypatch.setattr(np, "trapz", fallback, raising=False)
    monkeypatch.delattr(np, "trapezoid", raising=False)

    assert pilot._trapezoid(np.asarray([0.0, 1.0, 2.0]), np.asarray([0.0, 1.0, 2.0])) == 2.0


def test_smoke_integrator_falls_back_when_numpy_has_no_trapezoid_aliases(monkeypatch) -> None:
    pilot = _load_pilot_module()
    monkeypatch.delattr(np, "trapezoid", raising=False)
    monkeypatch.delattr(np, "trapz", raising=False)

    assert pilot._trapezoid(np.asarray([0.0, 1.0, 2.0]), np.asarray([0.0, 1.0, 2.0])) == 2.0


def test_smoke_steady_state_timer_measures_steps_after_two_step_warmup(monkeypatch) -> None:
    pilot = _load_pilot_module()
    timestamps = iter((100.0, 104.0))
    monkeypatch.setattr(pilot.time, "monotonic", lambda: next(timestamps))
    synchronization_points: list[str] = []
    monkeypatch.setattr(
        pilot.torch.cuda,
        "synchronize",
        lambda device: synchronization_points.append(str(device)),
    )

    timer = pilot._SmokeSteadyStateTimer(
        torch.device("cuda:0"), total_steps=10, warmup_steps=2
    )
    timer.step_completed(1)
    assert synchronization_points == []
    timer.step_completed(2)
    assert synchronization_points == ["cuda:0"]
    for completed_steps in range(3, 10):
        timer.step_completed(completed_steps)
    assert synchronization_points == ["cuda:0"]
    timer.step_completed(10)
    assert synchronization_points == ["cuda:0", "cuda:0"]

    assert timer.summary() == {
        "steady_state_measured_steps": 8,
        "steady_state_elapsed_seconds": 4.0,
        "steady_steps_per_second_excluding_first_two_steps": 2.0,
    }


def test_freeze_rejects_training_results_with_mismatched_config_hashes() -> None:
    pilot = _load_pilot_module()
    result = {
        "simulator_config_sha256": "A" * 64,
        "protocol_config_sha256": "B" * 64,
    }
    pilot._verify_training_result_config_hashes(
        result,
        config_id="resnet18gn_v10",
        expected_simulator_config_sha256="A" * 64,
        expected_protocol_config_sha256="B" * 64,
    )

    for field in ("simulator_config_sha256", "protocol_config_sha256"):
        mismatched = dict(result)
        mismatched[field] = "C" * 64
        try:
            pilot._verify_training_result_config_hashes(
                mismatched,
                config_id="resnet18gn_v10",
                expected_simulator_config_sha256="A" * 64,
                expected_protocol_config_sha256="B" * 64,
            )
        except ValueError as error:
            assert field in str(error)
        else:
            raise AssertionError(f"freeze accepted mismatched {field}")


def test_evaluation_rejects_changed_frozen_simulator_or_preprocessing_hashes(
    tmp_path: Path, monkeypatch
) -> None:
    pilot = _load_pilot_module()
    v9_path = tmp_path / "v9.json"
    v10_path = tmp_path / "v10.json"
    preprocessing_path = tmp_path / "preprocessing.json"
    for path in (v9_path, v10_path, preprocessing_path):
        path.write_text("frozen", encoding="utf-8")
    monkeypatch.setattr(pilot, "V9_SIM_PATH", v9_path)
    monkeypatch.setattr(pilot, "V10_SIM_PATH", v10_path)
    rruff_root = tmp_path / "rruff"
    (rruff_root / "contracts").mkdir(parents=True)
    preprocessing_path.rename(rruff_root / "contracts" / "preprocessing_contract.json")
    preprocessing_path = rruff_root / "contracts" / "preprocessing_contract.json"

    freeze = {
        "v9_simulation_config_sha256": pilot._sha256(v9_path),
        "v10_simulation_config_sha256": pilot._sha256(v10_path),
        "rruff_preprocessing_contract_sha256": pilot._sha256(preprocessing_path),
    }
    pilot._verify_frozen_evaluation_hashes(freeze, rruff_root)

    for key, changed_path in (
        ("v9_simulation_config_sha256", v9_path),
        ("v10_simulation_config_sha256", v10_path),
        ("rruff_preprocessing_contract_sha256", preprocessing_path),
    ):
        changed_path.write_text("changed", encoding="utf-8")
        try:
            pilot._verify_frozen_evaluation_hashes(freeze, rruff_root)
        except ValueError as error:
            assert key in str(error)
        else:
            raise AssertionError(f"changed frozen hash was accepted: {key}")
        changed_path.write_text("frozen", encoding="utf-8")
