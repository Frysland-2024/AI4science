from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from xrd_inversion.factorial_dataset import FactorialTensorBundle
from xrd_inversion.factorization_pilot import (
    _write_prediction_dump,
    evaluate_tiny_overfit_gate,
)
from xrd_inversion.factorization_training import TrainingRun, save_training_checkpoint
from xrd_inversion.models import TwoHeadFactorizationModel


def _training_run(*, final_parameter: float, final_pair: float) -> TrainingRun:
    model = TwoHeadFactorizationModel(
        input_channels=3,
        base_channels=2,
        latent_dim=4,
        pooled_length=2,
        output_bound=1.0,
    )
    return TrainingRun(
        model=model,
        seed=7,
        lambda_pair=1.0,
        steps=10,
        initial_state_sha256="a" * 64,
        batch_schedule_sha256="b" * 64,
        channel_mean=np.zeros(3, dtype=np.float32),
        channel_std=np.ones(3, dtype=np.float32),
        initial_losses={
            "total": 1.1,
            "parameter": 1.0,
            "structure_invariance": 0.05,
            "measurement_invariance": 0.05,
            "pair": 0.1,
            "lambda_pair": 1.0,
        },
        final_losses={
            "total": final_parameter + final_pair,
            "parameter": final_parameter,
            "structure_invariance": final_pair / 2.0,
            "measurement_invariance": final_pair / 2.0,
            "pair": final_pair,
            "lambda_pair": 1.0,
        },
        history=[],
        optimizer_state_dict={"state": {}, "param_groups": []},
    )


def test_tiny_gate_requires_overfit_pair_descent_and_matching() -> None:
    baseline = _training_run(final_parameter=1e-3, final_pair=2e-3)
    factorized = _training_run(final_parameter=1e-3, final_pair=1e-4)
    config = {
        "parameter_mse_max": 0.0025,
        "paired_invariance_mse_max": 0.0005,
        "loss_reduction_fraction_min": 0.95,
    }
    assert evaluate_tiny_overfit_gate(baseline, factorized, config)["status"] == "PASS"
    factorized.batch_schedule_sha256 = "c" * 64
    result = evaluate_tiny_overfit_gate(baseline, factorized, config)
    assert result["status"] == "FAIL"
    assert result["checks"]["matched_batch_schedule"] is False


def test_checkpoint_and_prediction_dump_freeze_handoff_fields(tmp_path: Path) -> None:
    run = _training_run(final_parameter=1e-3, final_pair=1e-4)
    config = {
        "model": {
            "input_channels": 3,
            "base_channels": 2,
            "latent_dim": 4,
            "pooled_length": 2,
            "output_bound": 1.0,
        },
        "training": {"checkpoint_policy": "fixed_final_step_no_metric_selection"},
    }
    provenance = {
        "interface_version": "factorization-interface-v1",
        "interface_sha256": "1" * 64,
        "config_sha256": "2" * 64,
        "manifest_sha256": "3" * 64,
        "source_sha256": {"models.py": "4" * 64},
        "dataset_source_sha256": {"records": "5" * 64},
        "corner_order": ["x11", "x12", "x21", "x22"],
        "structure_parameter_order": ["q_u", "q_v"],
        "measurement_parameter_order": ["q_delta", "q_w"],
        "reference_q": [0.0, 0.0, 0.0, -1.0],
        "profile_transform": "log1p_100_normalized",
        "profile_view": "gpu_forward_compatibility_false",
        "scope": "Train-only",
    }
    checkpoint = tmp_path / "checkpoint.pt"
    save_training_checkpoint(
        checkpoint,
        run,
        config,
        manifest_sha256="3" * 64,
        condition="factorized",
        provenance=provenance,
    )
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    assert payload["model_kind"] == "two_head_shared_encoder"
    assert "optimizer_state_dict" in payload
    assert payload["structure_parameter_order"] == ["q_u", "q_v"]

    observed = np.linspace(0.0, 1.0, 20, dtype=np.float32).reshape(1, 2, 2, 5)
    reference = np.zeros_like(observed)
    inputs = np.stack((observed, reference, observed - reference), axis=3)
    theta_s = np.asarray([[[[0.1, 0.2], [0.1, 0.2]], [[0.3, 0.4], [0.3, 0.4]]]])
    theta_m = np.asarray([[[[0.5, 0.6], [0.7, 0.8]], [[0.5, 0.6], [0.7, 0.8]]]])
    bundle = FactorialTensorBundle(
        inputs=inputs,
        theta_s=theta_s.astype(np.float64),
        theta_m=theta_m.astype(np.float64),
        parent_id=np.asarray(["p1"]),
        parent_a=np.asarray([4.0]),
        parent_c=np.asarray([6.0]),
        block_id=np.asarray([12]),
        subset=np.asarray(["sanity_eval"]),
        manifest_sha256="3" * 64,
    )
    dump = tmp_path / "predictions.npz"
    physical = np.zeros((1, 2, 2, 4), dtype=np.float64)
    _write_prediction_dump(
        dump,
        bundle=bundle,
        indices=np.asarray([0]),
        pred_s=theta_s,
        pred_m=theta_m,
        predicted_physical=physical,
        true_physical=physical,
        metadata=provenance,
    )
    with np.load(dump, allow_pickle=False) as archive:
        assert archive["theta_s"].shape == (1, 2, 2)
        assert archive["theta_m"].shape == (1, 2, 2)
        assert archive["true_s"].shape == (1, 2, 2)
        assert archive["true_m"].shape == (1, 2, 2)
        assert archive["theta_s"].dtype == np.float64
        assert archive["theta_m"].dtype == np.float64
        assert archive["true_s"].dtype == np.float64
        assert archive["true_m"].dtype == np.float64
        assert archive["x11_pred_s"].shape == (1, 2)
        assert archive["x22_pred_m"].shape == (1, 2)
        assert str(archive["parent_id"][0]) == "p1"
