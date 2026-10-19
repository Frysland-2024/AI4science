from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("donut_pxrd/src", "xrd_inversion/src", "xrd_robustness/src", "xrd_forward_loss/src")]
from donut_pxrd.model import DonutPXRD, physical_latent
from pxrd_forward_loss.measurement_closure import expected_profile, map_nuisance_logits
from pxrd_forward_loss.model import MeasurementAwareRegressor, ParameterRegressor
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward

RUN = ROOT / "donut_pxrd/results/study_v1/exp4"
DATA_PATH = ROOT / "donut_pxrd/results/study_v1/exp3c/data_arrays.npz"
WEIGHT_DIR = Path(r"E:\AI4science\_local\checkpoints\donut\donut_pxrd_four_stage_20261019")
SEEDS = (20261061, 20261062, 20261063)
LOG101 = math.log(101.0)
DIRECT_MODELS: dict[tuple[str, int], torch.nn.Module] = {}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean_summary(values: list[float]) -> dict[str, float]:
    return {"mean": float(np.mean(values)), "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0}


def load_driver():
    spec = importlib.util.spec_from_file_location("issue19_driver", ROOT / "xrd_forward_loss/scripts/run_issue19_p3.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def train_abc(arrays: dict[str, np.ndarray], forward, mode: str, cfg: dict) -> list[dict]:
    x = torch.as_tensor(arrays["observed"], device="cuda", dtype=torch.float32)
    q = torch.as_tensor(arrays["q"], device="cuda", dtype=torch.float32)
    tr = cfg["training"]
    all_records = []
    for method in ("A", "B", "C"):
        for seed in SEEDS:
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            np.random.seed(seed)
            model = ParameterRegressor(input_length=x.shape[-1]).cuda() if method == "A" else MeasurementAwareRegressor(input_length=x.shape[-1]).cuda()
            opt = torch.optim.Adam(model.parameters(), lr=tr["learning_rate"], weight_decay=tr["weight_decay"])
            generator = torch.Generator(device="cuda").manual_seed(seed + 1900)
            train_idx = torch.as_tensor(arrays["train_indices"], device="cuda", dtype=torch.long)
            val_idx = torch.as_tensor(arrays["validation_indices"], device="cuda", dtype=torch.long)
            best, best_epoch, best_state, history = float("inf"), 0, None, []
            torch.cuda.synchronize(); started = time.perf_counter()
            for epoch in range(1, tr["epochs_max"] + 1):
                model.train()
                order = train_idx[torch.randperm(len(train_idx), generator=generator, device="cuda")]
                losses = []
                for ids in order.split(tr["batch_size"]):
                    observed = x.index_select(0, ids)
                    target_q = q.index_select(0, ids)
                    output = model(observed)
                    if method == "A":
                        q_pred = output
                        qloss = F.mse_loss(q_pred, target_q)
                        rloss = qloss.new_zeros(())
                        loss = qloss
                    else:
                        q_pred, eta = output
                        profile_q = q_pred.detach() if method == "C" else q_pred
                        rendered = expected_profile(forward, profile_q.double(), eta.double(), background_shape_mode="v9_polynomial").float()
                        qloss = F.mse_loss(q_pred, target_q)
                        rloss = F.mse_loss(rendered, observed)
                        loss = qloss + tr["reconstruction_weight"] * rloss
                    opt.zero_grad(set_to_none=True)
                    loss.backward()
                    opt.step()
                    losses.append([float(loss.detach()), float(qloss.detach()), float(rloss.detach())])
                model.eval()
                with torch.no_grad():
                    vp = []
                    for ids in val_idx.split(tr["batch_size"]):
                        output = model(x.index_select(0, ids))
                        vp.append(output[0] if isinstance(output, tuple) else output)
                    val_mae = float(torch.abs(torch.cat(vp) - q.index_select(0, val_idx)).mean().cpu())
                history.append({"epoch": epoch, "validation_q_mae": val_mae, "train_loss": np.mean(losses, axis=0).tolist()})
                if val_mae < best:
                    best, best_epoch = val_mae, epoch
                    best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            torch.cuda.synchronize(); elapsed = time.perf_counter() - started
            if best_state is None:
                raise RuntimeError(f"No validation checkpoint selected for {method}/{seed}")
            model.load_state_dict(best_state)
            path = WEIGHT_DIR / f"exp4_{method}_seed{seed}.pt"
            if path.exists():
                raise FileExistsError(f"Refusing to overwrite an existing checkpoint: {path}")
            torch.save({"best_model_state": best_state, "method": method, "seed": seed, "best_epoch": best_epoch}, path)
            reloaded = ParameterRegressor(input_length=x.shape[-1]).cuda() if method == "A" else MeasurementAwareRegressor(input_length=x.shape[-1]).cuda()
            reloaded.load_state_dict(torch.load(path, map_location="cuda", weights_only=False)["best_model_state"])
            reloaded.eval()
            row = {"method": method, "seed": seed, "best_epoch": best_epoch, "best_validation_q_mae": best,
                   "training_seconds": elapsed, "checkpoint": str(path), "checkpoint_sha256": sha(path),
                   "checkpoint_bytes": path.stat().st_size, "history": history}
            all_records.append(row)
            del model, reloaded, opt
            torch.cuda.empty_cache()
    return all_records


def direct_prediction(method: str, seed: int, obs: np.ndarray, arrays: dict, abc_records: list[dict], donut_records: list[dict], input_len: int) -> tuple[np.ndarray, np.ndarray, float]:
    model = DIRECT_MODELS.get((method, seed))
    if model is None and method in ("A", "B", "C"):
        rec = next(r for r in abc_records if r["method"] == method and r["seed"] == seed)
        path = WEIGHT_DIR / Path(rec["checkpoint"]).name
        model = ParameterRegressor(input_length=input_len).cuda() if method == "A" else MeasurementAwareRegressor(input_length=input_len).cuda()
        model.load_state_dict(torch.load(path, map_location="cuda", weights_only=False)["best_model_state"])
        model.eval()
    elif model is None and method == "D":
        rec = next(r for r in donut_records if r["seed"] == seed)
        model = DonutPXRD(("du", "dv", "zero_shift"), output_length=input_len).cuda()
        model.load_state_dict(torch.load(WEIGHT_DIR / Path(rec["checkpoint"]).name, map_location="cuda", weights_only=False)["state_dict"])
        model.eval()
    x = torch.as_tensor(obs[None, :], device="cuda", dtype=torch.float32)
    torch.cuda.synchronize(); t0 = time.perf_counter()
    with torch.no_grad():
        if method == "D":
            latent, _ = model(x)
            vals = physical_latent(latent, ("du", "dv", "zero_shift"))
            q = np.array([[float(vals["du"].item()), float(vals["dv"].item())]])
            delta = np.array([float(vals["zero_shift"].item())])
            eta = np.array([[delta[0], 0.12, 0.0065]])
        else:
            out = model(x)
            if method == "A":
                q = out.cpu().numpy().astype(float)
                eta = np.array([[0.0, 0.105, 0.005]])
            else:
                q_t, eta_t = out
                q = q_t.cpu().numpy().astype(float)
                eta = eta_t.cpu().numpy().astype(float)
    torch.cuda.synchronize(); elapsed = time.perf_counter() - t0
    if method == "A":
        q = q
    return q[0], eta[0], elapsed


def make_objective(forward, observed: np.ndarray):
    target = torch.as_tensor(observed[None, :], device="cuda", dtype=torch.float32)
    bounds = [(-0.8, 0.8), (-0.8, 0.8), (-0.06, 0.06), (0.08, 0.13), (0.0, 0.01)]
    def objective(z):
        p = torch.as_tensor(np.asarray(z, dtype=float)[None, :], device="cuda", dtype=torch.float64).requires_grad_(True)
        pred = expected_profile(forward, p[:, :2], p[:, 2:], background_shape_mode="v9_polynomial").float()
        loss = F.mse_loss(pred, target)
        grad = torch.autograd.grad(loss, p)[0]
        return float(loss.detach().cpu()), grad.detach().cpu().numpy()[0].astype(float)
    return objective, bounds


def fit(objective, start, bounds, options):
    torch.cuda.synchronize(); t0 = time.perf_counter()
    result = minimize(objective, np.asarray(start, dtype=float), method="L-BFGS-B", jac=True, bounds=bounds,
                      options={"ftol": options["ftol"], "gtol": options["gtol"], "maxiter": options["maxiter"], "maxfun": options["maxfun"]})
    torch.cuda.synchronize(); elapsed = time.perf_counter() - t0
    return {"x": result.x.tolist(), "success": bool(result.success), "status": int(result.status), "message": str(result.message),
            "iterations": int(result.nit), "function_evaluations": int(result.nfev), "mse": float(result.fun),
            "profile_rmse": math.sqrt(max(float(result.fun), 0)), "seconds": elapsed,
            "at_bound": bool(any(abs(result.x[j] - b[0]) < 1e-5 or abs(result.x[j] - b[1]) < 1e-5 for j, b in enumerate(bounds)))}


def main() -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    reg_path = ROOT / "donut_pxrd/configs/experiment4_preregistration.json"
    cfg = json.loads(reg_path.read_text(encoding="utf-8"))
    assert sha(DATA_PATH) == cfg["dataset_sha256"]
    config = json.loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text(encoding="utf-8"))
    from pymatgen.core import Structure
    structure = Structure.from_file(ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif")
    forward = CachedTetragonalGPUForward(structure, grid_config=config["grid"], parameter_config=config["parameterization"], device="cuda", dtype=torch.float64)
    arrays = dict(np.load(DATA_PATH))
    obs = arrays["observed"]
    split = {k: arrays[k] for k in ("train_indices", "validation_indices", "test_indices")}
    assert [len(split[k]) for k in ("train_indices", "validation_indices", "test_indices")] == [358, 77, 77]
    abc_records = train_abc(arrays, forward, "v9_polynomial", cfg)
    donut_records = json.loads((ROOT / "donut_pxrd/results/study_v1/exp3c/test_per_seed.json").read_text(encoding="utf-8"))
    test_ids = arrays["test_indices"]
    truths = arrays["q"][test_ids]
    eta_truth = np.column_stack((arrays["delta_deg"][test_ids], arrays["fwhm_deg"][test_ids], arrays["background_ratio"][test_ids]))
    methods = ("A", "B", "C", "D", "E")
    seeds = SEEDS
    raw = []
    direct_times = {m: [] for m in methods}
    # Load each selected model once and warm it before measuring direct inference.
    for method in ("A", "B", "C", "D"):
        for seed in seeds:
            if method in ("A", "B", "C"):
                rec = next(r for r in abc_records if r["method"] == method and r["seed"] == seed)
                model = ParameterRegressor(input_length=obs.shape[1]).cuda() if method == "A" else MeasurementAwareRegressor(input_length=obs.shape[1]).cuda()
                model.load_state_dict(torch.load(WEIGHT_DIR / Path(rec["checkpoint"]).name, map_location="cuda", weights_only=False)["best_model_state"])
            else:
                rec = next(r for r in donut_records if r["seed"] == seed)
                model = DonutPXRD(("du", "dv", "zero_shift"), output_length=obs.shape[1]).cuda()
                model.load_state_dict(torch.load(WEIGHT_DIR / Path(rec["checkpoint"]).name, map_location="cuda", weights_only=False)["state_dict"])
            model.eval()
            DIRECT_MODELS[(method, seed)] = model
    for method in ("A", "B", "C", "D"):
        for seed in seeds:
            direct_prediction(method, seed, obs[split["validation_indices"][0]], arrays, abc_records, donut_records, obs.shape[1])
    # Warm up accelerator and simulator outside measured per-sample latency.
    _ = expected_profile(forward, torch.zeros((1, 2), device="cuda", dtype=torch.float64), torch.tensor([[0, .12, .0065]], device="cuda", dtype=torch.float64), background_shape_mode="v9_polynomial")
    torch.cuda.synchronize()
    for local, global_idx in enumerate(test_ids):
        observed = obs[global_idx]
        objective, bounds = make_objective(forward, observed)
        neutral = cfg["refinement"]["neutral_start"]
        classic_starts = [neutral, [-0.4, 0.4, 0.0, 0.105, 0.005], [0.4, -0.4, 0.0, 0.105, 0.005]]
        e_fits = [fit(objective, start, bounds, cfg["refinement"]) for start in classic_starts]
        best_e = min(e_fits, key=lambda r: (r["mse"], r["iterations"]))
        direct_by_seed = {}
        for method in ("A", "B", "C", "D"):
            for seed in seeds:
                qhat, etahat, elapsed = direct_prediction(method, seed, observed, arrays, abc_records, donut_records, obs.shape[1])
                direct_times[method].append(elapsed)
                direct_by_seed[(method, seed)] = (qhat, etahat)
                # Each neural direct output gets the preregistered single method-seeded q+eta refinement.
                start = np.r_[qhat, etahat]
                refined = fit(objective, start, bounds, cfg["refinement"])
                # eta-only fit starts from the shared neutral nuisance, with direct q frozen.
                def eta_objective(e):
                    value, grad = objective(np.r_[qhat, e])
                    return value, grad[2:]
                eta_fit = fit(eta_objective, neutral[2:], bounds[2:], cfg["refinement"])
                qtruth = truths[local]
                row = {"method": method, "seed": seed, "test_local_index": local, "q_parent_index": int(global_idx),
                       "q_true_posthoc": qtruth.tolist(), "eta_true_posthoc": eta_truth[local].tolist(),
                       "q_direct": qhat.tolist(), "eta_direct": etahat.tolist(),
                       "q_abs_error_direct": np.abs(qhat-qtruth).tolist(), "eta_abs_error_direct": np.abs(etahat-eta_truth[local]).tolist(),
                       "joint_refinement": refined, "joint_q_abs_error": np.abs(np.asarray(refined["x"][:2])-qtruth).tolist(),
                       "joint_eta_abs_error": np.abs(np.asarray(refined["x"][2:])-eta_truth[local]).tolist(), "eta_only_refinement": eta_fit}
                raw.append(row)
        raw.append({"method": "E", "seed": None, "test_local_index": local, "q_parent_index": int(global_idx),
                    "q_true_posthoc": truths[local].tolist(), "eta_true_posthoc": eta_truth[local].tolist(),
                    "optimizer_only_neutral_start": e_fits[0], "classic_multistart_fits": e_fits,
                    "optimizer_only_best_of_three": best_e, "q_direct": best_e["x"][:2], "eta_direct": best_e["x"][2:],
                    "q_abs_error_direct": np.abs(np.asarray(best_e["x"][:2])-truths[local]).tolist(),
                    "eta_abs_error_direct": np.abs(np.asarray(best_e["x"][2:])-eta_truth[local]).tolist()})
    torch.cuda.synchronize()
    (RUN / "raw_paired_results.json").write_text(json.dumps(raw, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (RUN / "raw_paired_results.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["method", "seed", "q_parent_index", "true_du", "pred_du", "true_dv", "pred_dv", "true_shift_deg", "true_fwhm_deg", "true_background_ratio"]
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in raw:
            pred = r.get("q_direct", [None, None]); truth = r["q_true_posthoc"]
            w.writerow({"method": r["method"], "seed": r["seed"], "q_parent_index": r["q_parent_index"], "true_du": truth[0], "pred_du": pred[0], "true_dv": truth[1], "pred_dv": pred[1],
                        "true_shift_deg": r["eta_true_posthoc"][0], "true_fwhm_deg": r["eta_true_posthoc"][1], "true_background_ratio": r["eta_true_posthoc"][2]})
    metrics = {}
    for method in methods:
        rows = [r for r in raw if r["method"] == method]
        if method == "E":
            metrics[method] = {"n": len(rows), "q_direct_mae": float(np.mean([np.mean(np.abs(np.asarray(r["q_direct"])-np.asarray(r["q_true_posthoc"]))) for r in rows])),
                               "du_mae": float(np.mean([r["q_abs_error_direct"][0] for r in rows])),
                               "dv_mae": float(np.mean([r["q_abs_error_direct"][1] for r in rows])),
                               "shift_mae_deg": float(np.mean([abs(r["eta_direct"][0]-r["eta_true_posthoc"][0]) for r in rows])),
                               "optimizer_success_rate": float(np.mean([r["optimizer_only_best_of_three"]["success"] for r in rows])),
                               "mean_iterations": float(np.mean([r["optimizer_only_best_of_three"]["iterations"] for r in rows])),
                               "mean_profile_rmse": float(np.mean([r["optimizer_only_best_of_three"]["profile_rmse"] for r in rows]))}
        else:
            metrics[method] = {}
            for seed in seeds:
                sr = [r for r in rows if r["seed"] == seed]
                metrics[method][str(seed)] = {"n": len(sr), "direct_q_mae": float(np.mean([np.mean(r["q_abs_error_direct"]) for r in sr])),
                                              "direct_du_mae": float(np.mean([r["q_abs_error_direct"][0] for r in sr])), "direct_dv_mae": float(np.mean([r["q_abs_error_direct"][1] for r in sr])),
                                              "direct_shift_mae_deg": float(np.mean([r["eta_abs_error_direct"][0] for r in sr])),
                                              "joint_q_mae": float(np.mean([np.mean(r["joint_q_abs_error"]) for r in sr])),
                                              "joint_eta_shift_mae_deg": float(np.mean([r["joint_eta_abs_error"][0] for r in sr])),
                                              "joint_profile_rmse": float(np.mean([r["joint_refinement"]["profile_rmse"] for r in sr])),
                                              "joint_solver_success_rate": float(np.mean([r["joint_refinement"]["success"] for r in sr])),
                                              "joint_solver_iterations_mean": float(np.mean([r["joint_refinement"]["iterations"] for r in sr])),
                                              "eta_only_shift_mae_deg": float(np.mean([abs(r["eta_only_refinement"]["x"][0]-r["eta_true_posthoc"][0]) for r in sr]))}
            flat = [r["joint_refinement"]["seconds"] for r in rows]
            metrics[method]["latency_seconds_p50_p95"] = {"direct_network_p50": float(np.percentile(direct_times[method], 50)), "direct_network_p95": float(np.percentile(direct_times[method], 95)),
                                                            "joint_fit_p50": float(np.percentile(flat, 50)), "joint_fit_p95": float(np.percentile(flat, 95))}
    elapsed_train = sum(r["training_seconds"] for r in abc_records)
    elapsed_hist = json.loads((ROOT / "donut_pxrd/results/resume_audit.json").read_text(encoding="utf-8"))["historical_gpu_training_seconds"]
    summary = {"status": "COMPLETE", "condition": "frozen exp3c noisy no-texture", "dataset_sha256": sha(DATA_PATH), "test_parent_count": len(test_ids),
               "train_validation_counts": {"train": len(split["train_indices"]), "validation": len(split["validation_indices"])}, "methods": methods,
               "seed_count": 3, "abc_training_records": abc_records, "abc_training_seconds": elapsed_train, "exp1_to_exp3_training_seconds": elapsed_hist,
               "aggregate_recorded_training_seconds": elapsed_hist + elapsed_train, "per_method_metrics": metrics,
               "hardware": {"gpu": torch.cuda.get_device_name(0), "torch": torch.__version__, "cuda": torch.version.cuda, "scipy": scipy.__version__, "python": sys.version, "platform": platform.platform()},
               "protocol": "pre-registration frozen; no test tuning; test evaluated once after validation-selected epochs; D uses frozen exp3c checkpoints; E uses 3 bounded classic starts; each A-D seed gets a method-seeded joint fit and eta-only fit",
               "timing_note": "CUDA synchronized; network direct p50/p95 includes model load and one-sample inference; fitting times include all objective evaluations; classic solver timing is retained per sample in raw JSON"}
    (RUN / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "COMPLETE", "training_seconds": elapsed_train, "evaluation_seconds": sum(direct_times["A"]), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
