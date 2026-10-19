"""Integrity checks for the exploratory Issue #19 nuisance diagnostic."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
DIAGNOSTIC_DIR = ROOT / "xrd_forward_loss/measurement_closure/nuisance_diagnostic"
sys.path.insert(0, str(DIAGNOSTIC_DIR))
sys.path.insert(0, str(ROOT / "xrd_forward_loss/scripts"))

import run_issue19_nuisance_diagnostic as diagnostic  # noqa: E402
import run_issue19_p3 as p3  # noqa: E402


def test_frozen_split_lambda_roster_and_all_checkpoint_hashes():
    config, arrays, split, selection, old_results = diagnostic.load_sources()
    indices = diagnostic.validate_frozen_inputs(config, arrays, split, selection, old_results)
    assert len(indices) == 77
    assert tuple(config["training"]["seeds"]) == diagnostic.SEEDS
    assert selection["simple"]["selected_lambda"] == 0.1
    assert selection["v9"]["selected_lambda"] == 1.0
    hashes = diagnostic.verify_checkpoint_hashes()
    assert len(hashes) == 12
    assert all(len(row["sha256"]) == 64 and row["inference_only"] for row in hashes)


def test_all_retained_model_states_load_frozen_for_inference():
    assert torch.cuda.is_available()
    _, arrays, _, _, _ = diagnostic.load_sources()
    device = torch.device("cuda")
    for row in diagnostic.verify_checkpoint_hashes():
        model = diagnostic.load_and_freeze_model(
            row,
            int(arrays[f"{row['condition']}_observed"].shape[1]),
            device,
        )
        assert not model.training
        assert all(not parameter.requires_grad for parameter in model.parameters())
        del model
        torch.cuda.empty_cache()


def test_shared_fit_has_same_canonical_knobs_and_no_truth_inputs():
    signature = inspect.signature(diagnostic.profile_fit_eta_shared)
    parameters = set(signature.parameters)
    assert not ({"q_true", "eta_true", "eta_native", "method"} & parameters)
    assert diagnostic.SOLVER_KNOBS["n_starts_per_profile"] == 1
    assert diagnostic.SOLVER_KNOBS["start_scaled_z"] == [0.0, 0.0, 0.0]
    assert diagnostic.SOLVER_KNOBS["method"] == "L-BFGS-B"
    assert diagnostic.SOLVER_KNOBS["scaled_bounds_per_coordinate"] == [-0.999, 0.999]
    assert diagnostic.SOLVER_KNOBS["options"] == {
        "maxiter": 80,
        "ftol": 1e-10,
        "gtol": 1e-7,
        "maxls": 25,
    }
    old_source = inspect.getsource(p3.profile_fit_eta)
    for expected in ('method="L-BFGS-B"', 'np.asarray([0.0, 0.0, 0.0]', 'bounds=[(-0.999, 0.999)] * 3'):
        assert expected in old_source
    assert '"maxiter": maxiter' in old_source
    assert '"ftol": 1e-10' in old_source and '"gtol": 1e-7' in old_source and '"maxls": 25' in old_source


def test_prediction_and_shared_solver_do_not_receive_truth_labels():
    predict_source = inspect.getsource(diagnostic.predict_profiles)
    fit_source = inspect.getsource(diagnostic.profile_fit_eta_shared)
    evaluate_source = inspect.getsource(diagnostic.evaluate_frozen_model)
    assert "q_true" not in predict_source and "eta_true" not in predict_source
    assert "q_true" not in fit_source and "eta_true" not in fit_source
    assert "eta_native" not in fit_source
    prediction_position = evaluate_source.index("predict_profiles(model, observed, device)")
    q_scoring_position = evaluate_source.index('q_true = arrays["q"]')
    eta_scoring_position = evaluate_source.index('eta_true = arrays[f"{condition}_eta_true"]')
    assert prediction_position < q_scoring_position < eta_scoring_position


def test_all_residuals_use_the_single_frozen_profile_preprocessing():
    source = (ROOT / "xrd_forward_loss/src/pxrd_forward_loss/measurement_closure.py").read_text(encoding="utf-8")
    assert "expected_raw = expected_raw / torch.clamp_min(" in source
    assert "torch.log1p(100.0 * expected_raw) / math.log(101.0)" in source
    fit_source = inspect.getsource(diagnostic.profile_fit_eta_shared)
    assert "expected_profile(forward, q_tensor, eta, background_shape_mode=background_mode)" in fit_source
    assert "F.mse_loss(expected.to(dtype=torch.float32), target)" in fit_source
    assert "render_profiles(" in inspect.getsource(diagnostic.evaluate_frozen_model)


def test_recorded_a_b_fits_share_identical_solver_configuration():
    results = diagnostic.read_json(diagnostic.RESULT_DIR / "metrics.json")
    hashes = {row["shared_fit"]["solver_knobs_sha256"] for row in results["per_seed"]}
    assert len(results["per_seed"]) == 12
    assert hashes == {results["shared_solver_sha256"]}
    assert all(row["shared_fit"]["n_profiles"] == 77 for row in results["per_seed"])


def test_shared_solver_repeatability_with_two_fixed_q_inputs(monkeypatch: pytest.MonkeyPatch):
    if not torch.cuda.is_available():
        pytest.skip("the authoritative Issue #19 forward renderer requires CUDA")

    def toy_expected_profile(_forward, q, eta, *, background_shape_mode):
        del q, background_shape_mode
        value = eta[:, 0:1] + 0.2 * eta[:, 1:2] + 0.01 * eta[:, 2:3]
        return value.expand(-1, 4)

    monkeypatch.setattr(diagnostic, "expected_profile", toy_expected_profile)
    device = torch.device("cuda")
    target = np.full((4,), 0.012, dtype=np.float32)
    for q_value in (np.asarray([0.1, -0.2]), np.asarray([-0.3, 0.4])):
        first = diagnostic.profile_fit_eta_shared(
            object(), q_value, target, background_mode="simple_linear_counts", device=device
        )
        second = diagnostic.profile_fit_eta_shared(
            object(), q_value, target, background_mode="simple_linear_counts", device=device
        )
        np.testing.assert_array_equal(first["scaled_z"], second["scaled_z"])
        assert first["profile_mse"] == second["profile_mse"]
        assert first["nfev"] == second["nfev"]
        assert first["nit"] == second["nit"]


def test_diagnostic_has_no_training_or_model_selection_path():
    tree = ast.parse(DIAGNOSTIC_DIR.joinpath("run_issue19_nuisance_diagnostic.py").read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert "backward" not in names
    source = DIAGNOSTIC_DIR.joinpath("run_issue19_nuisance_diagnostic.py").read_text(encoding="utf-8")
    assert '"optimizer_state" in checkpoint' in source  # rejection guard for old full checkpoints
    assert "test_used_for_selection" in source
    assert "no_retraining_or_model_selection" in source
    assert "torch.no_grad()" in source
