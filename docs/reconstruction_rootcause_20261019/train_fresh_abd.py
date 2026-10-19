from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import math
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CONF_PATH = OUT / "frozen_train_config.json"
DATA_DIR = OUT / "fresh_data"
CKDIR = OUT / "checkpoints"
LOG_PATH = OUT / "training_events.jsonl"
CONF = json.loads(CONF_PATH.read_text(encoding="utf-8"))
sys.path[:0] = [
    str(ROOT / "xrd_inversion/src"),
    str(ROOT / "xrd_robustness/src"),
    str(ROOT / "xrd_forward_loss/src"),
]
spec = importlib.util.spec_from_file_location(
    "rootcause_issue19_driver", ROOT / "xrd_forward_loss/scripts/run_issue19_p3.py"
)
driver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = driver
spec.loader.exec_module(driver)
from pxrd_forward_loss.model import MeasurementAwareRegressor

METHODS = ("A", "B", "D")
CONDITIONS = ("simple", "v9")
SEEDS = CONF["selection"]["model_seeds"]
LAMBDAS = CONF["selection"]["lambda_candidates_for_B_and_D"]
LIMIT = float(CONF["training"]["hard_budget_seconds_training_plus_validation_selection"])
torch.set_num_threads(int(CONF["training"]["torch_num_threads"]))
torch.backends.cudnn.deterministic = bool(CONF["training"]["cudnn_deterministic"])
torch.backends.cudnn.benchmark = bool(CONF["training"]["cudnn_benchmark"])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log_event(event: str, **details: object) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {"time_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, **details},
                ensure_ascii=False,
            )
            + "\n"
        )


def load_config_and_forward():
    source_path = ROOT / CONF["source_config"]
    source_bytes = source_path.read_bytes()
    normalized_source_hash = hashlib.sha256(source_bytes.replace(b"\r\n", b"\n")).hexdigest()
    assert normalized_source_hash == CONF["source_config_normalized_lf_sha256"], normalized_source_hash
    config = json.loads(source_path.read_text(encoding="utf-8"))
    cif_path = ROOT / config["source"]["cif"]
    normalized_cif_hash = hashlib.sha256(cif_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert normalized_cif_hash == CONF["source_cif_sha256"], normalized_cif_hash
    config = copy.deepcopy(config)
    data_cfg = config["data"]
    for key in ("sobol_seed", "split_seed", "nuisance_seed"):
        data_cfg[key] = CONF["fresh_data"][key]
    forward, forward_cfg, structure = driver.make_forward(config)
    return config, forward, forward_cfg, structure


def generate_fresh_data(config: dict, forward) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict]:
    fresh = CONF["fresh_data"]
    arrays, metadata = driver.build_data(
        config=config,
        forward=forward,
        count=int(fresh["parent_q_draws"]),
        sobol_seed=int(fresh["sobol_seed"]),
        split_seed=int(fresh["split_seed"]),
        nuisance_seed=int(fresh["nuisance_seed"]),
        noise_seed=int(fresh["noise_seed"]),
    )
    splits = {key: arrays[f"{key}_indices"] for key in ("train", "validation", "test")}
    universe = np.arange(int(fresh["parent_q_draws"]))
    joined = np.concatenate([splits[key] for key in ("train", "validation", "test")])
    assert len(np.unique(joined)) == len(joined) == len(universe)
    assert np.array_equal(np.sort(joined), universe)
    assert {key: int(len(val)) for key, val in splits.items()} == fresh["expected_split_counts"]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data_path = DATA_DIR / "fresh_batio3_paired.npz"
    np.savez_compressed(data_path, **arrays)
    manifest = {
        "schema": "reconstruction_rootcause_fresh_data_v1",
        "config_sha256": sha256_file(CONF_PATH),
        "runner_sha256": sha256_file(Path(__file__)),
        "source_config_normalized_lf_sha256": CONF["source_config_normalized_lf_sha256"],
        "cif_sha256": CONF["source_cif_sha256"],
        "npz_sha256": sha256_file(data_path),
        "npz_bytes": data_path.stat().st_size,
        "array_sha256": metadata["array_sha256"],
        "split_counts": {key: int(len(val)) for key, val in splits.items()},
        "split_index_sha256": {key: driver.sha256_array(val) for key, val in splits.items()},
        "split_disjoint_and_cover_all_parent_draws": True,
        "split_before_nuisance_and_noise": True,
        "test_used_for_training_or_selection": False,
        "metadata": metadata,
    }
    write_json(DATA_DIR / "split_manifest.json", manifest)
    log_event("FRESH_DATA_FROZEN", npz_sha256=manifest["npz_sha256"], counts=manifest["split_counts"])
    train_global = splits["train"]
    validation_global = splits["validation"]
    train_validation_global = np.concatenate([train_global, validation_global])
    train_count = len(train_global)
    train_validation_arrays = {
        "q": arrays["q"][train_validation_global].astype(np.float32),
        "simple_observed": arrays["simple_observed"][train_validation_global],
        "v9_observed": arrays["v9_observed"][train_validation_global],
        "simple_eta_train_shift": arrays["simple_eta_true"][train_global, 0].astype(np.float32),
        "v9_eta_train_shift": arrays["v9_eta_true"][train_global, 0].astype(np.float32),
    }
    train_validation_splits = {
        "train": np.arange(train_count, dtype=np.int64),
        "validation": np.arange(train_count, len(train_validation_global), dtype=np.int64),
    }
    # Drop all raw arrays, including test profiles and labels, from the training scope.
    del arrays
    return train_validation_arrays, train_validation_splits, manifest


def load_train_validation_from_prepared_data() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict]:
    """Load only train/validation inputs and labels from the frozen NPZ."""
    manifest = json.loads((DATA_DIR / "split_manifest.json").read_text(encoding="utf-8"))
    assert manifest["config_sha256"] == sha256_file(CONF_PATH)
    assert manifest["runner_sha256"] == sha256_file(Path(__file__))
    assert manifest["npz_sha256"] == sha256_file(DATA_DIR / "fresh_batio3_paired.npz")
    with np.load(DATA_DIR / "fresh_batio3_paired.npz", allow_pickle=False) as archive:
        train_global = np.asarray(archive["train_indices"], dtype=np.int64)
        validation_global = np.asarray(archive["validation_indices"], dtype=np.int64)
        train_validation_global = np.concatenate([train_global, validation_global])
        train_count = len(train_global)
        arrays = {
            "q": np.asarray(archive["q"][train_validation_global], dtype=np.float32),
            "simple_observed": np.asarray(archive["simple_observed"][train_validation_global]),
            "v9_observed": np.asarray(archive["v9_observed"][train_validation_global]),
            "simple_eta_train_shift": np.asarray(archive["simple_eta_true"][train_global, 0], dtype=np.float32),
            "v9_eta_train_shift": np.asarray(archive["v9_eta_true"][train_global, 0], dtype=np.float32),
        }
    expected_counts = CONF["fresh_data"]["expected_split_counts"]
    assert {"train": train_count, "validation": len(validation_global)} == {
        "train": expected_counts["train"],
        "validation": expected_counts["validation"],
    }
    splits = {
        "train": np.arange(train_count, dtype=np.int64),
        "validation": np.arange(train_count, len(train_validation_global), dtype=np.int64),
    }
    return arrays, splits, manifest


def runtime_smoke(arrays: dict[str, np.ndarray], data_manifest: dict, device_name: str) -> int:
    x = torch.as_tensor(arrays["simple_observed"][:1], device="cuda", dtype=torch.float32)
    smoke_model = MeasurementAwareRegressor(input_length=x.shape[-1]).cuda()
    with torch.no_grad():
        smoke_q, smoke_eta = smoke_model(x)
    actual_params = sum(parameter.numel() for parameter in smoke_model.parameters())
    assert actual_params == int(CONF["models"]["parameter_count_expected"])
    assert tuple(smoke_q.shape) == (1, 2) and tuple(smoke_eta.shape) == (1, 3)
    del smoke_model, x
    torch.cuda.empty_cache()
    write_json(
        OUT / "runtime_manifest.json",
        {
            "python": sys.version,
            "python_executable": sys.executable,
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": device_name,
            "parameter_count": actual_params,
            "data_npz_sha256": data_manifest["npz_sha256"],
            "preregistration_sha256": sha256_file(OUT / "PREREGISTRATION.md"),
            "frozen_config_sha256": sha256_file(CONF_PATH),
            "runner_sha256": sha256_file(Path(__file__)),
            "selection_smoke": "passed; test values not loaded",
        },
    )
    return actual_params


def val_q_mae(model, x: torch.Tensor, q: torch.Tensor, indices: np.ndarray) -> float:
    ids = torch.as_tensor(indices, device=x.device, dtype=torch.long)
    model.eval()
    with torch.no_grad():
        pred_q, _ = model(x.index_select(0, ids))
        value = torch.mean(torch.abs(pred_q - q.index_select(0, ids)))
    return float(value.detach().cpu())


def train_one(
    method: str,
    condition: str,
    seed: int,
    lam: float,
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    forward,
    base_config: dict,
    used_seconds: list[float],
) -> dict:
    train_cfg = base_config["training"]
    seed = int(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)
    device = torch.device("cuda")
    x = torch.as_tensor(arrays[f"{condition}_observed"], device=device, dtype=torch.float32)
    q = torch.as_tensor(arrays["q"], device=device, dtype=torch.float32)
    # The eta truth tensor is accessed only for D and only at its training indices.
    eta_train_shift = None
    if method == "D":
        eta_train_shift = torch.as_tensor(arrays[f"{condition}_eta_train_shift"], device=device, dtype=torch.float32)
    model = MeasurementAwareRegressor(input_length=x.shape[1]).to(device)
    parameter_count = sum(parameter.numel() for parameter in model.parameters())
    expected_count = int(CONF["models"]["parameter_count_expected"])
    if parameter_count != expected_count:
        raise RuntimeError(f"frozen parameter count changed: {parameter_count} != {expected_count}")
    optimizer = torch.optim.Adam(
        model.parameters(), lr=float(train_cfg["learning_rate"]), weight_decay=float(train_cfg["weight_decay"])
    )
    generator = torch.Generator(device=device)
    generator.manual_seed(seed + 1900)
    train_ids = torch.as_tensor(splits["train"], device=device, dtype=torch.long)
    max_epochs = int(CONF["training"]["max_epochs_per_candidate_condition_seed"])
    batch_size = int(CONF["training"]["batch_size"])
    best = math.inf
    best_epoch = 0
    best_state = None
    history = []
    torch.cuda.synchronize()
    started = time.perf_counter()
    budget_hit = False

    for epoch in range(1, max_epochs + 1):
        if used_seconds[0] + (time.perf_counter() - started) >= LIMIT - 5.0:
            budget_hit = True
            break
        model.train()
        order = train_ids[
            torch.randperm(len(train_ids), generator=generator, device=device)
        ]
        sums = np.zeros(4, dtype=np.float64)
        batches = 0
        for start in range(0, len(order), batch_size):
            torch.cuda.synchronize()
            if used_seconds[0] + (time.perf_counter() - started) >= LIMIT - 5.0:
                budget_hit = True
                break
            ids = order[start : start + batch_size]
            xb = x.index_select(0, ids)
            yq = q.index_select(0, ids)
            optimizer.zero_grad(set_to_none=True)
            pred_q, pred_eta = model(xb)
            loss_q = F.mse_loss(pred_q, yq)
            loss_recon = loss_q.new_zeros(())
            loss_shift = loss_q.new_zeros(())
            if method in ("B", "D"):
                expected = driver.expected_profile(
                    forward,
                    pred_q.to(torch.float64),
                    pred_eta.to(torch.float64),
                    background_shape_mode=driver.CONDITIONS[condition],
                ).to(xb.dtype)
                loss_recon = F.mse_loss(expected, xb)
            if method == "A":
                loss = loss_q
            elif method == "B":
                loss = loss_q + float(lam) * loss_recon
            else:
                true_shift = eta_train_shift.index_select(0, ids) / 0.06
                pred_shift = pred_eta[:, 0] / 0.06
                loss_shift = F.mse_loss(pred_shift, true_shift)
                loss = loss_q + float(lam) * loss_recon + loss_shift
            if not torch.isfinite(loss):
                raise FloatingPointError(f"non-finite total loss: {method}/{condition}/{seed}/{epoch}")
            loss.backward()
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            if not grads or any(not torch.isfinite(grad).all() for grad in grads):
                raise FloatingPointError(f"non-finite gradient: {method}/{condition}/{seed}/{epoch}")
            torch.nn.utils.clip_grad_norm_(model.parameters(), float(train_cfg["gradient_clip_norm"]))
            optimizer.step()
            sums += [float(loss.detach()), float(loss_q.detach()), float(loss_recon.detach()), float(loss_shift.detach())]
            batches += 1
        if budget_hit:
            break
        torch.cuda.synchronize()
        if used_seconds[0] + (time.perf_counter() - started) >= LIMIT - 5.0:
            budget_hit = True
            break
        validation = val_q_mae(model, x, q, splits["validation"])
        torch.cuda.synchronize()
        epoch_row = {
            "epoch": epoch,
            "validation_q_mae": validation,
            "train_total_loss": float(sums[0] / max(batches, 1)),
            "train_q_mse": float(sums[1] / max(batches, 1)),
            "train_reconstruction_mse": float(sums[2] / max(batches, 1)),
            "train_zero_shift_mse_normalized": float(sums[3] / max(batches, 1)),
            "elapsed_seconds": time.perf_counter() - started,
        }
        history.append(epoch_row)
        if validation < best:
            best = validation
            best_epoch = epoch
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
        if used_seconds[0] + (time.perf_counter() - started) >= LIMIT:
            budget_hit = True
            break

    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    used_seconds[0] += elapsed
    record = {
        "method": method,
        "condition": condition,
        "seed": seed,
        "lambda": float(lam),
        "status": "COMPLETE" if len(history) == max_epochs and used_seconds[0] < LIMIT else "PARTIAL_BUDGET",
        "epochs_completed": len(history),
        "planned_epochs": max_epochs,
        "best_epoch": best_epoch,
        "best_validation_q_mae": best if math.isfinite(best) else None,
        "training_plus_validation_seconds": elapsed,
        "cumulative_training_plus_validation_seconds": used_seconds[0],
        "parameter_count": parameter_count,
        "history": history,
    }
    if best_state is not None:
        CKDIR.mkdir(parents=True, exist_ok=True)
        checkpoint_path = CKDIR / f"{condition}_{method}_lambda{lam:g}_seed{seed}.pt"
        torch.save(
            {
                "best_model_state": best_state,
                "method": method,
                "condition": condition,
                "seed": seed,
                "lambda": float(lam),
                "best_epoch": best_epoch,
                "best_validation_q_mae": best,
                "parameter_count": parameter_count,
            },
            checkpoint_path,
        )
        record["checkpoint"] = str(checkpoint_path.relative_to(OUT))
        record["checkpoint_sha256"] = sha256_file(checkpoint_path)
    log_event("TRAIN_RUN_FINISHED", **{key: value for key, value in record.items() if key != "history"})
    del model, x, q
    torch.cuda.empty_cache()
    return record


def load_best(path: Path, input_length: int):
    checkpoint = torch.load(path, map_location="cuda", weights_only=False)
    model = MeasurementAwareRegressor(input_length=input_length).cuda()
    model.load_state_dict(checkpoint["best_model_state"])
    model.eval()
    return model


def fit_eta(forward, condition: str, q0: np.ndarray, observed: np.ndarray) -> dict:
    mode = driver.CONDITIONS[condition]
    target = torch.as_tensor(observed[None], device="cuda", dtype=torch.float32)
    qfixed = torch.as_tensor(q0[None], device="cuda", dtype=torch.float64)
    bounds = [(-0.06, 0.06), (0.08, 0.13), (0.0, 0.01)]
    neutral = np.asarray([0.0, 0.105, 0.005], dtype=np.float64)

    def objective(values: np.ndarray):
        eta = torch.as_tensor(values[None], device="cuda", dtype=torch.float64).requires_grad_(True)
        expected = driver.expected_profile(forward, qfixed, eta, background_shape_mode=mode).float()
        loss = F.mse_loss(expected, target)
        gradient = torch.autograd.grad(loss, eta)[0]
        return float(loss.detach()), gradient.detach().cpu().numpy()[0]

    started = time.perf_counter()
    result = scipy.optimize.minimize(
        objective,
        neutral,
        method="L-BFGS-B",
        jac=True,
        bounds=bounds,
        options={"maxiter": 60, "ftol": 1e-9, "gtol": 1e-7, "maxls": 20},
    )
    return {
        "eta": result.x.tolist(),
        "success": bool(result.success),
        "iterations": int(result.nit),
        "seconds": time.perf_counter() - started,
        "rmse": math.sqrt(max(0.0, float(result.fun))),
        "at_bound": bool(
            np.any(np.isclose(result.x, [bound[0] for bound in bounds], atol=1e-5))
            or np.any(np.isclose(result.x, [bound[1] for bound in bounds], atol=1e-5))
        ),
    }


def select_validation_only(records: list[dict]) -> dict:
    selection = {}
    selected = {}
    for condition in CONDITIONS:
        selection[condition] = {}
        selected[condition] = {"A": 0.0}
        for method in ("B", "D"):
            score_by_lambda = {
                str(lam): float(
                    np.mean(
                        [
                            row["best_validation_q_mae"]
                            for row in records
                            if row["condition"] == condition
                            and row["method"] == method
                            and float(row["lambda"]) == float(lam)
                        ]
                    )
                )
                for lam in LAMBDAS
            }
            chosen = min(LAMBDAS, key=lambda lam: (score_by_lambda[str(lam)], float(lam)))
            selected[condition][method] = float(chosen)
            selection[condition][method] = {
                "mean_best_validation_q_mae_by_lambda": score_by_lambda,
                "selected_lambda": float(chosen),
                "test_used": False,
            }
    return {
        "status": "FROZEN_BEFORE_TEST",
        "rule": CONF["selection"]["lambda_rule"],
        "best_epoch_rule": CONF["selection"]["best_epoch_rule"],
        "selection": selection,
        "selected_lambda": selected,
        "training_records_sha256": sha256_file(OUT / "training_runs.json"),
        "fresh_data_sha256": sha256_file(DATA_DIR / "fresh_batio3_paired.npz"),
    }


def load_test_arrays_after_selection() -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Open test values only after the validation selection artifact is written."""
    with np.load(DATA_DIR / "fresh_batio3_paired.npz", allow_pickle=False) as archive:
        global_test = np.asarray(archive["test_indices"], dtype=np.int64)
        arrays = {
            "q": np.asarray(archive["q"][global_test], dtype=np.float64),
            "simple_observed": np.asarray(archive["simple_observed"][global_test]),
            "v9_observed": np.asarray(archive["v9_observed"][global_test]),
            "simple_eta_true": np.asarray(archive["simple_eta_true"][global_test], dtype=np.float64),
            "v9_eta_true": np.asarray(archive["v9_eta_true"][global_test], dtype=np.float64),
            "test_global_indices": global_test,
        }
    return arrays, {"test": np.arange(len(global_test), dtype=np.int64)}


def evaluate_test_once(
    arrays: dict[str, np.ndarray],
    splits: dict[str, np.ndarray],
    forward,
    forward_cfg,
    structure,
    selected: dict,
    records: list[dict],
) -> tuple[list[dict], dict]:
    test_ids = np.asarray(splits["test"], dtype=np.int64)
    test_global_indices = arrays["test_global_indices"]
    true_q = arrays["q"]
    per_sample = []
    test_started = time.perf_counter()
    for condition in CONDITIONS:
        obs_all = arrays[f"{condition}_observed"]
        eta_true_all = arrays[f"{condition}_eta_true"]
        for method in METHODS:
            for seed in SEEDS:
                lam = float(selected[condition][method])
                checkpoint = CKDIR / f"{condition}_{method}_lambda{lam:g}_seed{int(seed)}.pt"
                model = load_best(checkpoint, int(obs_all.shape[-1]))
                q_pred_t, eta_pred_t = [], []
                with torch.no_grad():
                    for start in range(0, len(obs_all), 16):
                        xb = torch.as_tensor(obs_all[start : start + 16], device="cuda", dtype=torch.float32)
                        q_batch, eta_batch = model(xb)
                        q_pred_t.append(q_batch.cpu().numpy().astype(np.float64))
                        eta_pred_t.append(eta_batch.cpu().numpy().astype(np.float64))
                q_pred = np.concatenate(q_pred_t)
                eta_pred = np.concatenate(eta_pred_t)
                for local_i, global_i in enumerate(test_global_indices):
                    observed = obs_all[local_i]
                    qp = q_pred[local_i]
                    ep = eta_pred[local_i]
                    q_tensor = torch.as_tensor(qp[None], device="cuda", dtype=torch.float64)
                    eta_tensor = torch.as_tensor(ep[None], device="cuda", dtype=torch.float64)
                    target = torch.as_tensor(observed[None], device="cuda", dtype=torch.float32)
                    with torch.no_grad():
                        direct_profile = driver.expected_profile(
                            forward,
                            q_tensor,
                            eta_tensor,
                            background_shape_mode=driver.CONDITIONS[condition],
                        ).float()
                        direct_rmse = float(torch.sqrt(torch.mean((direct_profile - target) ** 2)).cpu())
                    fit = fit_eta(forward, condition, qp, observed)
                    a_true, c_true = driver.q_to_lattice(true_q[local_i], structure, forward_cfg)
                    a_pred, c_pred = driver.q_to_lattice(qp, structure, forward_cfg)
                    row = {
                        "condition": condition,
                        "method": method,
                        "seed": int(seed),
                        "lambda": lam,
                        "global_index": int(global_i),
                        "q_true": true_q[local_i].tolist(),
                        "q_pred": qp.tolist(),
                        "q_abs_error": np.abs(qp - true_q[local_i]).tolist(),
                        "a_abs_error_angstrom": float(abs(a_pred - a_true)),
                        "c_abs_error_angstrom": float(abs(c_pred - c_true)),
                        "eta_true_posthoc": eta_true_all[local_i].tolist(),
                        "eta_pred": ep.tolist(),
                        "zero_shift_abs_error_deg": float(abs(ep[0] - eta_true_all[local_i, 0])),
                        "direct_predicted_eta_profile_rmse": direct_rmse,
                        "q_fixed_eta_fit": fit,
                    }
                    per_sample.append(row)
                del model
                torch.cuda.empty_cache()

    summary: dict = {condition: {} for condition in CONDITIONS}
    for condition in CONDITIONS:
        for method in METHODS:
            summary[condition][method] = {}
            for seed in SEEDS:
                rows = [
                    row for row in per_sample
                    if row["condition"] == condition and row["method"] == method and row["seed"] == int(seed)
                ]
                q_abs = np.asarray([row["q_abs_error"] for row in rows], dtype=np.float64)
                summary[condition][method][str(seed)] = {
                    "n_test": len(rows),
                    "du_mae": float(q_abs[:, 0].mean()),
                    "dv_mae": float(q_abs[:, 1].mean()),
                    "q_mae": float(q_abs.mean()),
                    "a_mae_angstrom": float(np.mean([row["a_abs_error_angstrom"] for row in rows])),
                    "c_mae_angstrom": float(np.mean([row["c_abs_error_angstrom"] for row in rows])),
                    "zero_shift_rmse_deg": float(np.sqrt(np.mean([row["zero_shift_abs_error_deg"] ** 2 for row in rows]))),
                    "direct_predicted_eta_profile_rmse": float(np.mean([row["direct_predicted_eta_profile_rmse"] for row in rows])),
                    "q_fixed_eta_fit_profile_rmse": float(np.mean([row["q_fixed_eta_fit"]["rmse"] for row in rows])),
                    "q_fixed_eta_fit_success_rate": float(np.mean([row["q_fixed_eta_fit"]["success"] for row in rows])),
                    "q_fixed_eta_fit_mean_iterations": float(np.mean([row["q_fixed_eta_fit"]["iterations"] for row in rows])),
                    "q_fixed_eta_fit_runtime_p95_seconds": float(np.percentile([row["q_fixed_eta_fit"]["seconds"] for row in rows], 95)),
                    "q_fixed_eta_fit_at_bound_count": int(sum(row["q_fixed_eta_fit"]["at_bound"] for row in rows)),
                }
    paired = {}
    criteria = {}
    for condition in CONDITIONS:
        paired[condition] = {}
        for metric in ("q_mae", "a_mae_angstrom", "c_mae_angstrom", "zero_shift_rmse_deg"):
            deltas = {
                str(seed): summary[condition]["D"][str(seed)][metric] - summary[condition]["B"][str(seed)][metric]
                for seed in SEEDS
            }
            paired[condition][metric + "_D_minus_B"] = {
                "by_seed": deltas,
                "mean": float(np.mean(list(deltas.values()))),
                "sample_sd": float(np.std(list(deltas.values()), ddof=1)),
            }
        mean_metrics = {
            method: {
                metric: float(np.mean([summary[condition][method][str(seed)][metric] for seed in SEEDS]))
                for metric in ("q_mae", "a_mae_angstrom", "c_mae_angstrom", "zero_shift_rmse_deg")
            }
            for method in ("B", "D")
        }
        q_seed_better = sum(
            summary[condition]["D"][str(seed)]["q_mae"] < summary[condition]["B"][str(seed)]["q_mae"]
            for seed in SEEDS
        )
        criteria[condition] = {
            "mean_metrics_B_D": mean_metrics,
            "q_seed_improvements_D_over_B": int(q_seed_better),
            "q_relative_reduction_D_vs_B": float(
                (mean_metrics["B"]["q_mae"] - mean_metrics["D"]["q_mae"]) / mean_metrics["B"]["q_mae"]
            ),
        }
    v9 = criteria["v9"]
    b = v9["mean_metrics_B_D"]["B"]
    d = v9["mean_metrics_B_D"]["D"]
    v9_support = (
        v9["q_relative_reduction_D_vs_B"] >= 0.05
        and v9["q_seed_improvements_D_over_B"] >= 2
        and d["a_mae_angstrom"] <= 1.05 * b["a_mae_angstrom"]
        and d["c_mae_angstrom"] <= 1.05 * b["c_mae_angstrom"]
    )
    shift_support = d["zero_shift_rmse_deg"] <= 0.80 * b["zero_shift_rmse_deg"]
    simple_guardrail = all(
        criteria["simple"]["mean_metrics_B_D"]["D"][metric]
        <= 1.05 * criteria["simple"]["mean_metrics_B_D"]["B"][metric]
        for metric in ("q_mae", "a_mae_angstrom", "c_mae_angstrom")
    )
    decision = "SUPPORTS_PREREGISTERED_HYPOTHESIS" if v9_support and shift_support and simple_guardrail else "HYPOTHESIS_NOT_SUPPORTED"
    result = {
        "status": "COMPLETED",
        "claim_scope": CONF["claim_limit"],
        "test_evaluated_once_after_selection": True,
        "selected_lambda": selected,
        "seed_summary": summary,
        "paired_D_minus_B": paired,
        "criteria": criteria,
        "decision": {
            "classification": decision,
            "v9_primary_q_and_ac_criterion_passed": bool(v9_support),
            "v9_zero_shift_mechanism_check_passed": bool(shift_support),
            "simple_condition_guardrail_passed": bool(simple_guardrail),
        },
        "training_plus_validation_seconds": float(sum(row["training_plus_validation_seconds"] for row in records)),
        "test_evaluation_seconds": float(time.perf_counter() - test_started),
        "model_seed_count": len(SEEDS),
        "test_size_per_seed": int(len(test_ids)),
    }
    return per_sample, result


def write_test_csv(path: Path, rows: list[dict]) -> None:
    columns = [
        "condition", "method", "seed", "lambda", "global_index", "du_abs_error", "dv_abs_error",
        "a_abs_error_angstrom", "c_abs_error_angstrom", "zero_shift_abs_error_deg",
        "direct_predicted_eta_profile_rmse", "q_fixed_eta_fit_rmse", "q_fixed_eta_fit_success",
        "q_fixed_eta_fit_iterations", "q_fixed_eta_fit_seconds", "q_fixed_eta_fit_at_bound",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "condition": row["condition"],
                    "method": row["method"],
                    "seed": row["seed"],
                    "lambda": row["lambda"],
                    "global_index": row["global_index"],
                    "du_abs_error": row["q_abs_error"][0],
                    "dv_abs_error": row["q_abs_error"][1],
                    "a_abs_error_angstrom": row["a_abs_error_angstrom"],
                    "c_abs_error_angstrom": row["c_abs_error_angstrom"],
                    "zero_shift_abs_error_deg": row["zero_shift_abs_error_deg"],
                    "direct_predicted_eta_profile_rmse": row["direct_predicted_eta_profile_rmse"],
                    "q_fixed_eta_fit_rmse": row["q_fixed_eta_fit"]["rmse"],
                    "q_fixed_eta_fit_success": row["q_fixed_eta_fit"]["success"],
                    "q_fixed_eta_fit_iterations": row["q_fixed_eta_fit"]["iterations"],
                    "q_fixed_eta_fit_seconds": row["q_fixed_eta_fit"]["seconds"],
                    "q_fixed_eta_fit_at_bound": row["q_fixed_eta_fit"]["at_bound"],
                }
            )


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA runtime gate failed after preregistration")
    device_name = torch.cuda.get_device_name(0)
    if "RTX 4060" not in device_name:
        raise RuntimeError(f"unexpected frozen GPU: {device_name}")
    config, forward, forward_cfg, structure = load_config_and_forward()
    if "--prepare-only" in sys.argv[1:]:
        arrays, _, data_manifest = generate_fresh_data(config, forward)
    elif (DATA_DIR / "fresh_batio3_paired.npz").is_file() and (DATA_DIR / "split_manifest.json").is_file():
        arrays, _, data_manifest = load_train_validation_from_prepared_data()
    else:
        arrays, _, data_manifest = generate_fresh_data(config, forward)
    actual_params = runtime_smoke(arrays, data_manifest, device_name)
    if "--prepare-only" in sys.argv[1:]:
        print(json.dumps({"status": "PREPARED_NO_TRAINING", "npz_sha256": data_manifest["npz_sha256"], "parameter_count": actual_params}, indent=2))
        return
    if (OUT / "training_runs.json").exists():
        raise RuntimeError("training_runs.json already exists; this runner never starts a second round or resumes implicitly")
    with np.load(DATA_DIR / "fresh_batio3_paired.npz", allow_pickle=False) as archive:
        train_global = np.asarray(archive["train_indices"], dtype=np.int64)
        validation_global = np.asarray(archive["validation_indices"], dtype=np.int64)
        train_count = len(train_global)
        splits = {
            "train": np.arange(train_count, dtype=np.int64),
            "validation": np.arange(train_count, train_count + len(validation_global), dtype=np.int64),
        }
    records: list[dict] = []
    used = [0.0]
    budget_hit = False
    expected_runs = 30
    write_json(OUT / "training_runs.json", {"status": "IN_PROGRESS", "planned_runs": expected_runs, "runs": records})
    try:
        for condition in CONDITIONS:
            for seed in SEEDS:
                for method, lambdas in (("A", [0.0]), ("B", LAMBDAS), ("D", LAMBDAS)):
                    for lam in lambdas:
                        if used[0] >= LIMIT - 5.0:
                            budget_hit = True
                            break
                        record = train_one(
                            method, condition, int(seed), float(lam), arrays, splits, forward, config, used
                        )
                        records.append(record)
                        status = "IN_PROGRESS"
                        if record["status"] != "COMPLETE":
                            budget_hit = True
                            status = "PARTIAL_BUDGET"
                        write_json(
                            OUT / "training_runs.json",
                            {
                                "status": status,
                                "planned_runs": expected_runs,
                                "completed_candidate_count": len(records),
                                "cumulative_training_plus_validation_seconds": used[0],
                                "hard_budget_seconds": LIMIT,
                                "runs": records,
                            },
                        )
                        if budget_hit:
                            break
                    if budget_hit:
                        break
                if budget_hit:
                    break
            if budget_hit:
                break
    except Exception as exc:
        write_json(
            OUT / "training_runs.json",
            {
                "status": "FAILED",
                "planned_runs": expected_runs,
                "completed_candidate_count": len(records),
                "cumulative_training_plus_validation_seconds": used[0],
                "runs": records,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            },
        )
        log_event("TRAINING_FAILED", error=repr(exc), traceback=traceback.format_exc())
        raise

    complete = len(records) == expected_runs and all(row["status"] == "COMPLETE" for row in records)
    run_status = "CANDIDATES_COMPLETED" if complete else "PARTIAL_BUDGET"
    write_json(
        OUT / "training_runs.json",
        {
            "status": run_status,
            "planned_runs": expected_runs,
            "completed_candidate_count": len(records),
            "cumulative_training_plus_validation_seconds": used[0],
            "hard_budget_seconds": LIMIT,
            "runs": records,
        },
    )
    if not complete:
        write_json(
            OUT / "final_summary.json",
            {
                "status": "PARTIAL",
                "reason": "The full preregistered A/B/D candidate set did not complete within the frozen budget.",
                "test_evaluated": False,
                "completed_candidate_count": len(records),
                "planned_candidate_count": expected_runs,
                "training_plus_validation_seconds": used[0],
                "hard_budget_seconds": LIMIT,
            },
        )
        log_event("ROUND_PARTIAL_NO_TEST", completed=len(records), seconds=used[0])
        return

    selection = select_validation_only(records)
    write_json(OUT / "training_selection.json", selection)
    # Only now, after all candidate models and validation choices are frozen, open test arrays.
    del arrays, splits
    torch.cuda.empty_cache()
    arrays, splits = load_test_arrays_after_selection()
    per_sample, result = evaluate_test_once(
        arrays, splits, forward, forward_cfg, structure, selection["selected_lambda"], records
    )
    result["selection_sha256"] = sha256_file(OUT / "training_selection.json")
    result["fresh_data_sha256"] = data_manifest["npz_sha256"]
    write_json(OUT / "fresh_test_per_sample.json", per_sample)
    write_test_csv(OUT / "fresh_test_per_sample.csv", per_sample)
    write_json(OUT / "fresh_results_per_seed.json", result)
    seed_rows = []
    for condition in CONDITIONS:
        for method in METHODS:
            for seed in SEEDS:
                row = result["seed_summary"][condition][method][str(seed)]
                seed_rows.append({"condition": condition, "method": method, "seed": seed, "lambda": selection["selected_lambda"][condition][method], **row})
    with (OUT / "fresh_results_per_seed.csv").open("w", encoding="utf-8", newline="") as stream:
        columns = list(seed_rows[0].keys())
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(seed_rows)
    write_json(
        OUT / "final_summary.json",
        {
            "status": "COMPLETED",
            "decision": result["decision"],
            "data": {"n_parent_draws": 512, "split_counts": data_manifest["split_counts"], "sha256": data_manifest["npz_sha256"]},
            "model_seeds": SEEDS,
            "candidate_count": len(records),
            "training_plus_validation_seconds": used[0],
            "hard_budget_seconds": LIMIT,
            "test_evaluated_once": True,
            "selected_lambda": selection["selected_lambda"],
            "seed_summary": result["seed_summary"],
            "paired_D_minus_B": result["paired_D_minus_B"],
            "criteria": result["criteria"],
            "claim_limit": CONF["claim_limit"],
        },
    )
    checkpoint_rows = []
    for path in sorted(CKDIR.glob("*.pt")):
        checkpoint_rows.append({"path": str(path.relative_to(OUT)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_json(OUT / "checkpoint_manifest.json", {"tracked_in_git": False, "count": len(checkpoint_rows), "checkpoints": checkpoint_rows})
    log_event("ROUND_COMPLETED", seconds=used[0], test_evaluated_once=True, decision=result["decision"]["classification"])
    print(json.dumps({"status": "COMPLETED", "training_plus_validation_seconds": used[0], "decision": result["decision"]}, indent=2))


if __name__ == "__main__":
    main()
