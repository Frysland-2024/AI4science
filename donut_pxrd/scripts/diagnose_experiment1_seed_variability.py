"""Summarize DONUT experiment 1 seed variability from frozen training logs only.

This diagnostic deliberately does not load predictions, test metrics, model
weights, or training data. It records missing local checkpoint files as a
limitation and never changes the frozen experiment artifacts.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import statistics
from pathlib import Path
from typing import Any

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = ROOT / "donut_pxrd/results/experiment_1/experiment_1_fixed_training_histories.json"
STATUS_PATH = ROOT / "donut_pxrd/reports/EXECUTION_STATUS.json"
CONFIG_PATH = ROOT / "donut_pxrd/configs/study_v1.json"
OUTPUT_PATH = ROOT / "donut_pxrd/results/experiment_1/seed_variability_diagnostic.json"
LOCAL_RUN_ROOT = ROOT / "_local/checkpoints/donut/run_20261019_01"
DATA_PATH = LOCAL_RUN_ROOT / "datasets/study_v1.npz"
DATA_MANIFEST_PATH = LOCAL_RUN_ROOT / "datasets/data_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_forward_driver() -> Any:
    path = ROOT / "xrd_forward_loss/scripts/run_issue19_p3.py"
    spec = importlib.util.spec_from_file_location("donut_seed_diagnostic_forward_driver", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load existing PXRD forward driver: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _rmse_by_row(prediction: np.ndarray, target: np.ndarray) -> dict[str, float]:
    values = np.sqrt(np.mean(np.square(prediction - target), axis=1))
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p95": float(np.percentile(values, 95)),
    }


def validation_inference(
    *, seed: str, run: dict[str, Any], q_true: np.ndarray, observed: np.ndarray,
    forward: Any, driver: Any, structure: Any, forward_cfg: dict[str, Any],
) -> dict[str, Any]:
    from donut_pxrd.model import DONUTEncoderDecoder, physical_profile

    checkpoint = LOCAL_RUN_ROOT / "checkpoints/experiment_1_fixed" / f"donut_seed{seed}.pt"
    if not checkpoint.is_file():
        raise FileNotFoundError(f"Missing relocated checkpoint: {checkpoint}")
    checkpoint_hash = sha256(checkpoint)
    if checkpoint_hash != run.get("checkpoint_sha256"):
        raise RuntimeError(f"Checkpoint SHA-256 mismatch for seed {seed}")

    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if saved.get("phase") != "experiment_1_fixed" or int(saved.get("seed", -1)) != int(seed):
        raise RuntimeError(f"Checkpoint identity mismatch for seed {seed}")
    if int(saved.get("best_epoch", -1)) != int(run["best_epoch"]):
        raise RuntimeError(f"Checkpoint epoch mismatch for seed {seed}")

    model = DONUTEncoderDecoder(
        input_length=int(saved["input_length"]),
        latent_dim=int(saved["latent_dim"]),
        dropout=0.0,
    ).cuda()
    model.load_state_dict(saved["state_dict"], strict=True)
    model.eval()

    reconstruction_rows: list[np.ndarray] = []
    physics_rows: list[np.ndarray] = []
    prediction_rows: list[np.ndarray] = []
    raw_latent_rows: list[np.ndarray] = []
    constrained_rows: list[np.ndarray] = []
    batch_decoder_losses: list[float] = []
    batch_physics_losses: list[float] = []
    with torch.inference_mode():
        for start in range(0, len(observed), 16):
            xb = torch.as_tensor(observed[start : start + 16], device="cuda", dtype=torch.float32)
            recon, raw, constrained = model(xb)
            physics, q_pred, _ = physical_profile(
                forward, constrained, phase="experiment_1_fixed"
            )
            batch_decoder_losses.append(float(torch.nn.functional.smooth_l1_loss(recon, xb).item()))
            batch_physics_losses.append(float(torch.nn.functional.smooth_l1_loss(physics, xb).item()))
            reconstruction_rows.append(recon.cpu().numpy())
            physics_rows.append(physics.cpu().numpy())
            prediction_rows.append(q_pred.cpu().numpy())
            raw_latent_rows.append(raw.cpu().numpy())
            constrained_rows.append(constrained.cpu().numpy())

    reconstruction = np.concatenate(reconstruction_rows)
    physics_profile = np.concatenate(physics_rows)
    q_pred = np.concatenate(prediction_rows).astype(np.float64)
    raw_latent = np.concatenate(raw_latent_rows).astype(np.float64)
    constrained = np.concatenate(constrained_rows).astype(np.float64)
    errors = q_pred - q_true
    a_true, c_true = driver.q_to_lattice(q_true, structure, forward_cfg)
    a_pred, c_pred = driver.q_to_lattice(q_pred, structure, forward_cfg)
    unit_latent = constrained / 1.7159
    correlations: dict[str, float | None] = {}
    for dimension, name in enumerate(("du", "dv")):
        if np.std(q_pred[:, dimension]) == 0 or np.std(q_true[:, dimension]) == 0:
            correlations[name] = None
        else:
            correlations[name] = float(np.corrcoef(q_pred[:, dimension], q_true[:, dimension])[0, 1])

    return {
        "checkpoint": {
            "path": str(checkpoint),
            "sha256": checkpoint_hash,
            "sha256_matches_execution_record": True,
            "best_epoch_matches_execution_record": True,
        },
        "n_validation": int(len(q_true)),
        "q_prediction": {
            "du_mae": float(np.mean(np.abs(errors[:, 0]))),
            "dv_mae": float(np.mean(np.abs(errors[:, 1]))),
            "normalized_q_mae": float(np.mean(np.abs(errors))),
            "du_bias": float(np.mean(errors[:, 0])),
            "dv_bias": float(np.mean(errors[:, 1])),
            "du_prediction_mean": float(np.mean(q_pred[:, 0])),
            "du_prediction_std": float(np.std(q_pred[:, 0], ddof=1)),
            "du_prediction_min": float(np.min(q_pred[:, 0])),
            "du_prediction_max": float(np.max(q_pred[:, 0])),
            "dv_prediction_mean": float(np.mean(q_pred[:, 1])),
            "dv_prediction_std": float(np.std(q_pred[:, 1], ddof=1)),
            "dv_prediction_min": float(np.min(q_pred[:, 1])),
            "dv_prediction_max": float(np.max(q_pred[:, 1])),
            "du_true_std": float(np.std(q_true[:, 0], ddof=1)),
            "du_pred_std": float(np.std(q_pred[:, 0], ddof=1)),
            "dv_true_std": float(np.std(q_true[:, 1], ddof=1)),
            "dv_pred_std": float(np.std(q_pred[:, 1], ddof=1)),
            "pearson_by_coordinate": correlations,
        },
        "lattice_prediction": {
            "a_mae_angstrom": float(np.mean(np.abs(a_pred - a_true))),
            "c_mae_angstrom": float(np.mean(np.abs(c_pred - c_true))),
        },
        "profile_rmse": {
            "decoder": _rmse_by_row(reconstruction, observed),
            "physics": _rmse_by_row(physics_profile, observed),
        },
        "validation_losses_recomputed_with_original_batching": {
            "decoder": float(np.mean(batch_decoder_losses)),
            "physics_unweighted": float(np.mean(batch_physics_losses)),
            "composite_decoder_plus_5_physics": float(
                np.mean(batch_decoder_losses) + 5.0 * np.mean(batch_physics_losses)
            ),
            "absolute_difference_from_logged_validation_total": abs(
                np.mean(batch_decoder_losses)
                + 5.0 * np.mean(batch_physics_losses)
                - float(run["best_validation_dual_loss"])
            ),
        },
        "latent_diagnostics": {
            "raw_mean_by_coordinate": np.mean(raw_latent, axis=0).tolist(),
            "raw_std_by_coordinate": np.std(raw_latent, axis=0, ddof=1).tolist(),
            "normalized_constrained_mean_by_coordinate": np.mean(unit_latent, axis=0).tolist(),
            "normalized_constrained_std_by_coordinate": np.std(unit_latent, axis=0, ddof=1).tolist(),
            "fraction_abs_normalized_constrained_at_least_0_95_by_coordinate": np.mean(
                np.abs(unit_latent) >= 0.95, axis=0
            ).tolist(),
        },
    }


def summarize_seed(rows: list[dict[str, Any]], run: dict[str, Any]) -> dict[str, Any]:
    best_epoch = int(run["best_epoch"])
    selected = rows[best_epoch - 1]
    totals = [float(row["validation_total_loss"]) for row in rows]
    train_totals = [float(row["train_total_loss"]) for row in rows]
    decoder = float(selected["validation_decoder_loss"])
    physics = float(selected["validation_physics_loss"])
    weighted_physics = 5.0 * physics
    weighted_total = decoder + weighted_physics
    checkpoint_path = Path(run["checkpoint_path_local_only"])

    return {
        "epochs_completed": len(rows),
        "best_epoch": best_epoch,
        "best_validation_dual_loss_recorded": float(run["best_validation_dual_loss"]),
        "selected_epoch_losses": {
            "train_total": float(selected["train_total_loss"]),
            "validation_total": float(selected["validation_total_loss"]),
            "validation_decoder": decoder,
            "validation_physics_unweighted": physics,
            "validation_physics_weighted_x5": weighted_physics,
            "validation_decoder_share_of_composite": decoder / weighted_total,
            "validation_physics_share_of_composite": weighted_physics / weighted_total,
        },
        "validation_total_loss_over_epochs": {
            "minimum": min(totals),
            "median": statistics.median(totals),
            "maximum": max(totals),
        },
        "training_total_loss_over_epochs": {
            "minimum": min(train_totals),
            "minimum_epoch": 1 + train_totals.index(min(train_totals)),
            "final": train_totals[-1],
        },
        "final_validation_total_loss": totals[-1],
        "final_to_selected_validation_loss_ratio": totals[-1] / float(selected["validation_total_loss"]),
        "checkpoint": {
            "declared_path": str(checkpoint_path),
            "exists_at_diagnostic_time": checkpoint_path.is_file(),
            "sha256_from_execution_record": run.get("checkpoint_sha256"),
        },
    }


def main() -> None:
    histories = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    condition = status["experiments"]["experiment_1"]["conditions"]["experiment_1_fixed"]
    runs = {str(run["seed"]): run for run in condition["seed_runs"]}
    configured_seeds = [str(seed) for seed in config["donut_method"]["model_seeds"]]
    if set(histories) != set(configured_seeds) or set(runs) != set(configured_seeds):
        raise RuntimeError("Experiment 1 history, execution records, and frozen seeds do not match")

    # Validate the relocated local-only dataset and load only the frozen
    # validation indices/profiles/labels. The test indices and test rows are
    # never selected or passed to a model in this diagnostic.
    data_manifest = json.loads(DATA_MANIFEST_PATH.read_text(encoding="utf-8"))
    if sha256(DATA_PATH) != data_manifest["dataset_npz_sha256"]:
        raise RuntimeError("Frozen local dataset SHA-256 mismatch")
    if data_manifest["dataset_npz_sha256"] != status.get("dataset_npz_sha256"):
        raise RuntimeError("Frozen dataset hash differs from the execution record")
    with np.load(DATA_PATH, allow_pickle=False) as archive:
        validation_indices = archive["validation_indices"].astype(np.int64)
        q_validation = archive["q"][validation_indices].astype(np.float64)
        observed_validation = archive["experiment_1_fixed_observed"][validation_indices].astype(np.float32)
    if len(validation_indices) != 77 or len(q_validation) != len(observed_validation):
        raise RuntimeError("Unexpected validation split size or alignment")

    # Reuse the repository's existing differentiable PXRD forward model.
    source_paths = [
        ROOT / "donut_pxrd/src",
        ROOT / "xrd_inversion/src",
        ROOT / "xrd_robustness/src",
        ROOT / "xrd_forward_loss/src",
    ]
    sys.path[:0] = [str(path) for path in source_paths]

    torch.set_num_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True, warn_only=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; validation inference cannot reproduce the frozen path")
    forward_driver = load_forward_driver()
    base_forward_cfg = json.loads((ROOT / config["sources"]["base_forward_config"]).read_text(encoding="utf-8"))
    forward, forward_cfg, structure = forward_driver.make_forward(base_forward_cfg)
    torch.use_deterministic_algorithms(True, warn_only=True)
    per_seed = {
        seed: summarize_seed(histories[seed], runs[seed])
        for seed in configured_seeds
    }
    for seed in configured_seeds:
        per_seed[seed]["checkpoint"] = {
            "declared_path": runs[seed]["checkpoint_path_local_only"],
            "located_path": str(
                LOCAL_RUN_ROOT / "checkpoints/experiment_1_fixed" / f"donut_seed{seed}.pt"
            ),
            "sha256_matches_execution_record": False,
        }
        per_seed[seed]["validation_inference"] = validation_inference(
            seed=seed,
            run=runs[seed],
            q_true=q_validation,
            observed=observed_validation,
            forward=forward,
            driver=forward_driver,
            structure=structure,
            forward_cfg=forward_cfg,
        )
        per_seed[seed]["checkpoint"]["sha256_matches_execution_record"] = True
    reference_seed = min(
        configured_seeds,
        key=lambda seed: per_seed[seed]["selected_epoch_losses"]["validation_total"],
    )
    reference_loss = per_seed[reference_seed]["selected_epoch_losses"]["validation_total"]
    for seed, result in per_seed.items():
        result["selected_validation_loss_ratio_to_best_seed"] = (
            result["selected_epoch_losses"]["validation_total"] / reference_loss
        )

    output = {
        "schema": "donut_pxrd_experiment1_seed_variability_diagnostic_v1",
        "scope": "post-hoc descriptive audit of frozen train/validation histories and validation-only inference",
        "test_indices_or_rows_selected_or_passed_to_model": False,
        "test_metrics_used_for_selection_or_recomputed": False,
        "validation_predictions_recomputed_from_frozen_weights": True,
        "frozen_weights_loaded_without_training": True,
        "frozen_seed_order": [int(seed) for seed in configured_seeds],
        "best_validation_reference_seed": int(reference_seed),
        "loss_definition": "validation_decoder_loss + 5 * validation_physics_loss",
        "source_files": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (HISTORY_PATH, STATUS_PATH, CONFIG_PATH, DATA_PATH, DATA_MANIFEST_PATH)
        },
        "by_seed": per_seed,
        "interpretation_limit": (
            "This is descriptive evidence from three seeds on one CIF. It does not isolate "
            "random initialization from the documented CUDA nondeterministic backward op, "
            "and it does not establish a causal mechanism or unseen-material performance."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")
    print(json.dumps({seed: {
        "best_epoch": value["best_epoch"],
        "best_validation_total": value["selected_epoch_losses"]["validation_total"],
        "validation_loss_ratio_to_best": value["selected_validation_loss_ratio_to_best_seed"],
        "validation_q_mae": value["validation_inference"]["q_prediction"]["normalized_q_mae"],
        "validation_dv_mean_std": [
            value["validation_inference"]["q_prediction"]["dv_prediction_mean"],
            value["validation_inference"]["q_prediction"]["dv_prediction_std"],
        ],
        "validation_physics_profile_rmse": value["validation_inference"]["profile_rmse"]["physics"]["mean"],
        "checkpoint_sha_verified": value["validation_inference"]["checkpoint"]["sha256_matches_execution_record"],
    } for seed, value in per_seed.items()}, indent=2))


if __name__ == "__main__":
    main()
