from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.optimize
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
BASE = ROOT / "xrd_forward_loss/measurement_closure/results/p3_issue19_20261018"
FORMAL = BASE / "formal"
sys.path[:0] = [str(ROOT / "xrd_inversion/src"), str(ROOT / "xrd_robustness/src"), str(ROOT / "xrd_forward_loss/src")]
spec = importlib.util.spec_from_file_location("issue19_driver", ROOT / "xrd_forward_loss/scripts/run_issue19_p3.py")
driver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = driver
spec.loader.exec_module(driver)

SEEDS = (20261045, 20261046, 20261047)
DEVICE = "cuda"
torch.set_num_threads(1)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def jwrite(name: str, obj: object) -> None:
    (OUT / name).write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    start = time.perf_counter()
    manifest = json.loads((BASE / "checkpoint_manifest.json").read_text(encoding="utf-8"))
    retained = manifest["post_run_local_optimization"]["retained_checkpoints"]
    ckdir = FORMAL / "checkpoints/inference_only_best"
    data = dict(np.load(FORMAL / "formal_data.npz"))
    original = json.loads((FORMAL / "ab_results.json").read_text(encoding="utf-8"))
    split = json.loads((FORMAL / "split_indices.json").read_text(encoding="utf-8"))
    config_manifest = json.loads((FORMAL / "config_manifest.json").read_text(encoding="utf-8"))
    config = config_manifest["full_config"]
    pred_arrays = dict(np.load(FORMAL / "test_profile_predictions.npz"))
    cif = ROOT / config["source"]["cif"]
    frozen_data_hash = sha(FORMAL / "formal_data.npz")
    frozen_split_hash = sha(FORMAL / "split_indices.json")
    assert frozen_data_hash == config_manifest["data_sha256"]
    data_manifest = json.loads((FORMAL / "data_manifest.json").read_text(encoding="utf-8"))
    for split_name in ("train", "validation", "test"):
        assert np.array_equal(data[f"{split_name}_indices"], np.asarray(split[split_name], dtype=np.int64))
        assert driver.sha256_array(data[f"{split_name}_indices"]) == data_manifest["array_sha256"][f"{split_name}_indices"]
    test_idx = np.asarray(split["test"], dtype=int)
    assert len(test_idx) == 77
    forward, forward_cfg, structure = driver.make_forward(config)

    checkpoint_rows = []
    predictions = {}
    for row in retained:
        path = ckdir / Path(row["path"]).name
        assert path.is_file(), f"missing {path}"
        actual_hash = sha(path)
        assert actual_hash == row["sha256"], f"checkpoint hash mismatch: {path.name}"
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        assert ckpt["format"] == row["format"]
        assert ckpt["method"] == row["method"] and int(ckpt["seed"]) == row["seed"]
        model = driver.load_best_model(path, row["method"], data[f"{row['condition']}_observed"].shape[-1])
        q, eta = driver._predict(model, data[f"{row['condition']}_observed"][test_idx])
        key = f"{row['condition']}_{row['method']}_{row['seed']}"
        result_row = original["per_seed"][row["condition"]][row["method"]][str(row["seed"])]
        q_saved = np.asarray(result_row["prediction_q"], dtype=np.float64)
        q_maxdiff = float(np.max(np.abs(q - q_saved)))
        assert q_maxdiff < 2e-6, f"checkpoint prediction mismatch {key}: {q_maxdiff}"
        predictions[key] = {"q": q, "eta": eta}
        checkpoint_rows.append({"path": str(path.relative_to(ROOT)), "sha256": actual_hash, "bytes": path.stat().st_size,
                                "method": row["method"], "condition": row["condition"], "seed": row["seed"],
                                "architecture_loaded": True, "q_prediction_max_abs_difference_from_frozen_record": q_maxdiff,
                                "eta_present": eta is not None})
        del model
        torch.cuda.empty_cache()

    recomputed = []
    for condition in ("simple", "v9"):
        for seed in SEEDS:
            for method in ("A", "B"):
                key = f"{condition}_{method}_{seed}"
                q = predictions[key]["q"]
                truth = data["q"][test_idx]
                q_mae = np.abs(q - truth).mean(axis=0)
                a_true, c_true = driver.q_to_lattice(truth, structure, forward_cfg)
                a_pred, c_pred = driver.q_to_lattice(q, structure, forward_cfg)
                rec = original["per_seed"][condition][method][str(seed)]
                diff = float(q_mae.mean() - rec["parameter_mae_normalized_q"]["mean_two_coordinate"])
                assert abs(diff) < 2e-9, f"frozen q metric differs {key}: {diff}"
                recomputed.append({"condition": condition, "seed": seed, "method": method,
                                   "test_n": len(test_idx), "du_mae": float(q_mae[0]), "dv_mae": float(q_mae[1]),
                                   "mean_q_mae": float(q_mae.mean()), "a_mae_angstrom": float(np.abs(a_pred-a_true).mean()),
                                   "c_mae_angstrom": float(np.abs(c_pred-c_true).mean()),
                                   "frozen_q_mae_difference": diff})

    # Freeze a deterministic 24-index test subset before running any optimization.
    rng = np.random.default_rng(2026101901)
    local_positions = np.sort(rng.choice(len(test_idx), size=24, replace=False))
    selected_global = test_idx[local_positions]
    jwrite("p1_subset_manifest.json", {"status": "FROZEN_BEFORE_DIAGNOSTIC_OPTIMIZATION", "seed": 2026101901,
             "selection_rule": "uniform sample without replacement from original held-out test indices; sorted local positions",
             "local_positions": local_positions.tolist(), "global_indices": selected_global.tolist(),
             "same_subset_for_all_methods_seeds_conditions": True})
    scipy.optimize.minimize  # record the explicit optimizer protocol below
    modes = {"simple": "simple_linear_counts", "v9": "v9_polynomial"}
    neutral_eta = np.asarray([0.0, 0.105, 0.005], dtype=np.float64)
    eta_bounds = [(-0.06, 0.06), (0.08, 0.13), (0.0, 0.01)]
    q_bounds = [(-0.8, 0.8), (-0.8, 0.8)]
    bounds = q_bounds + eta_bounds
    target_tol = 1e-6  # transformed-profile MSE objective; declared before optimization
    maxiter = 50

    def optimize_one(condition: str, obs: np.ndarray, initial: np.ndarray, q_fixed: np.ndarray | None) -> dict:
        target = torch.as_tensor(obs[None, :], device=DEVICE, dtype=torch.float32)
        q0 = np.asarray(initial[:2] if q_fixed is None else q_fixed, dtype=np.float64)
        x0 = np.asarray(initial, dtype=np.float64)
        bds = bounds if q_fixed is None else eta_bounds

        def fun(x):
            z = torch.as_tensor(x, device=DEVICE, dtype=torch.float64).reshape(1, -1).requires_grad_(True)
            if q_fixed is None:
                q = z[:, :2]
                eta = z[:, 2:]
            else:
                q = torch.as_tensor(q0[None, :], device=DEVICE, dtype=torch.float64)
                eta = z
            y = driver.expected_profile(forward, q, eta, background_shape_mode=modes[condition]).float()
            loss = F.mse_loss(y, target)
            grad = torch.autograd.grad(loss, z)[0]
            return float(loss.detach().cpu()), grad.detach().cpu().numpy().reshape(-1)

        t0 = time.perf_counter()
        res = scipy.optimize.minimize(fun, x0, method="L-BFGS-B", jac=True, bounds=bds,
             options={"maxiter": maxiter, "ftol": 1e-9, "gtol": 1e-7, "maxls": 20})
        elapsed = time.perf_counter() - t0
        if q_fixed is None:
            qf, etaf = res.x[:2], res.x[2:]
        else:
            qf, etaf = q0, res.x
        predicted = driver.expected_profile(forward,
            torch.as_tensor(qf[None, :], device=DEVICE, dtype=torch.float64),
            torch.as_tensor(etaf[None, :], device=DEVICE, dtype=torch.float64),
            background_shape_mode=modes[condition]).detach().cpu().numpy()[0]
        rmse = float(np.sqrt(np.mean((predicted - obs) ** 2)))
        qtrue = data["q"][int(np.where(np.arange(len(data["q"])) == -1)[0][0])] if False else None
        return {"q": qf.tolist(), "eta": etaf.tolist(), "objective_mse": float(res.fun), "rmse": rmse,
                "success": bool(res.success), "iterations": int(res.nit), "function_evaluations": int(res.nfev),
                "elapsed_seconds": elapsed, "reached_predeclared_objective_tolerance": bool(res.fun <= target_tol),
                "at_bound": bool(np.any(np.isclose(res.x, [b[0] for b in bds], atol=1e-5)) or np.any(np.isclose(res.x, [b[1] for b in bds], atol=1e-5)))}

    p1_rows = []
    for condition in ("simple", "v9"):
        for seed in SEEDS:
            for local_i, global_i in zip(local_positions, selected_global, strict=True):
                observed = data[f"{condition}_observed"][global_i]
                truth_q = data["q"][global_i]
                truth_eta = data[f"{condition}_eta_true"][global_i]
                neutral = np.r_[neutral_eta]
                prior = optimize_one(condition, observed, np.r_[np.zeros(2), neutral], None)
                for method in ("A", "B"):
                    key = f"{condition}_{method}_{seed}"
                    pred = predictions[key]
                    qhat = pred["q"][local_i]
                    # Direct one pass plus same neutral initial nuisance.
                    eta_only = optimize_one(condition, observed, neutral, qhat)
                    joint = optimize_one(condition, observed, np.r_[qhat, neutral], None)
                    direct_q = qhat
                    q_mae_direct = np.abs(direct_q - truth_q)
                    q_mae_refined = np.abs(np.asarray(joint["q"]) - truth_q)
                    eta_scaled_err = np.abs(driver.eta_to_scaled(np.asarray(eta_only["eta"])) - driver.eta_to_scaled(truth_eta))
                    j_eta_scaled_err = np.abs(driver.eta_to_scaled(np.asarray(joint["eta"])) - driver.eta_to_scaled(truth_eta))
                    row = {"condition": condition, "seed": seed, "method": method, "global_index": int(global_i),
                           "direct_q": direct_q.tolist(), "direct_du_abs_error": float(q_mae_direct[0]), "direct_dv_abs_error": float(q_mae_direct[1]),
                           "fixed_q_eta_only": eta_only, "eta_only_scaled_nuisance_mae": float(eta_scaled_err.mean()),
                           "joint_q_eta_refinement": joint, "joint_du_abs_error": float(q_mae_refined[0]), "joint_dv_abs_error": float(q_mae_refined[1]),
                           "joint_scaled_nuisance_mae": float(j_eta_scaled_err.mean()), "physics_only_neutral_start": prior}
                    p1_rows.append(row)
    # Per-sample machine record and paired CSV.
    jwrite("p1_per_sample.json", p1_rows)
    with (OUT / "p1_per_sample.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["condition", "seed", "method", "global_index", "direct_du_abs_error", "direct_dv_abs_error",
             "eta_only_rmse", "eta_only_eta_mae", "eta_only_success", "eta_only_iterations", "eta_only_seconds",
             "joint_rmse", "joint_du_abs_error", "joint_dv_abs_error", "joint_eta_mae", "joint_success", "joint_iterations", "joint_seconds",
             "prior_rmse", "prior_success", "prior_iterations", "prior_seconds"])
        w.writeheader()
        for x in p1_rows:
            w.writerow({"condition": x["condition"], "seed": x["seed"], "method": x["method"], "global_index": x["global_index"],
              "direct_du_abs_error": x["direct_du_abs_error"], "direct_dv_abs_error": x["direct_dv_abs_error"],
              "eta_only_rmse": x["fixed_q_eta_only"]["rmse"], "eta_only_eta_mae": x["eta_only_scaled_nuisance_mae"],
              "eta_only_success": x["fixed_q_eta_only"]["success"], "eta_only_iterations": x["fixed_q_eta_only"]["iterations"], "eta_only_seconds": x["fixed_q_eta_only"]["elapsed_seconds"],
              "joint_rmse": x["joint_q_eta_refinement"]["rmse"], "joint_du_abs_error": x["joint_du_abs_error"], "joint_dv_abs_error": x["joint_dv_abs_error"],
              "joint_eta_mae": x["joint_scaled_nuisance_mae"], "joint_success": x["joint_q_eta_refinement"]["success"], "joint_iterations": x["joint_q_eta_refinement"]["iterations"], "joint_seconds": x["joint_q_eta_refinement"]["elapsed_seconds"],
              "prior_rmse": x["physics_only_neutral_start"]["rmse"], "prior_success": x["physics_only_neutral_start"]["success"],
              "prior_iterations": x["physics_only_neutral_start"]["iterations"], "prior_seconds": x["physics_only_neutral_start"]["elapsed_seconds"]})

    summaries = {}
    for cond in ("simple", "v9"):
        summaries[cond] = {}
        for method in ("A", "B"):
            rows = [r for r in p1_rows if r["condition"] == cond and r["method"] == method]
            summaries[cond][method] = {
                "n": len(rows),
                "direct_q_mae_mean": float(np.mean([np.mean([r["direct_du_abs_error"], r["direct_dv_abs_error"]]) for r in rows])),
                "eta_only_profile_rmse_mean": float(np.mean([r["fixed_q_eta_only"]["rmse"] for r in rows])),
                "eta_only_nuisance_scaled_mae_mean": float(np.mean([r["eta_only_scaled_nuisance_mae"] for r in rows])),
                "eta_only_success_rate": float(np.mean([r["fixed_q_eta_only"]["success"] for r in rows])),
                "eta_only_seconds_mean": float(np.mean([r["fixed_q_eta_only"]["elapsed_seconds"] for r in rows])),
                "joint_q_mae_mean": float(np.mean([np.mean([r["joint_du_abs_error"], r["joint_dv_abs_error"]]) for r in rows])),
                "joint_profile_rmse_mean": float(np.mean([r["joint_q_eta_refinement"]["rmse"] for r in rows])),
                "joint_nuisance_scaled_mae_mean": float(np.mean([r["joint_scaled_nuisance_mae"] for r in rows])),
                "joint_success_rate": float(np.mean([r["joint_q_eta_refinement"]["success"] for r in rows])),
                "joint_seconds_mean": float(np.mean([r["joint_q_eta_refinement"]["elapsed_seconds"] for r in rows])),
            }
    total = time.perf_counter() - start
    jwrite("p0_audit.json", {"checkpoint_manifest_count": len(retained), "checkpoint_audit": checkpoint_rows,
             "all_checkpoint_hash_architecture_inference_checks_passed": len(checkpoint_rows) == 12,
             "formal_data_sha256": frozen_data_hash, "split_indices_sha256": frozen_split_hash,
             "split_indices_crosschecked_against_formal_data_arrays": True,
             "cif_sha256": sha(cif), "config_sha256": sha(ROOT / config_manifest["path"]),
             "test_count": len(test_idx), "recomputed_metrics": recomputed,
             "original_p3_test_used_for_training_selection": original["test_used_for_selection"] is True,
             "fair_original_test_is_post_hoc_diagnostic_only": True})
    jwrite("p1_summary.json", {"status": "COMPLETED", "subset_manifest": "p1_subset_manifest.json", "summary": summaries,
             "optimizer": "SciPy L-BFGS-B with torch autograd, float64 forward, transformed-profile MSE",
             "eta_neutral_initialization": neutral_eta.tolist(), "eta_bounds": eta_bounds, "q_bounds": q_bounds,
             "max_iterations": maxiter, "predeclared_objective_mse_tolerance": target_tol,
             "all_methods_same_initial_eta_optimizer_bounds_objective_budget": True,
             "total_elapsed_seconds_including_p0_and_p1": total})
    (OUT / "p0_checkpoint_and_metric_audit.csv").write_text("condition,seed,method,test_n,du_mae,dv_mae,mean_q_mae,a_mae_angstrom,c_mae_angstrom\n" + "".join(
        f"{r['condition']},{r['seed']},{r['method']},{r['test_n']},{r['du_mae']:.12g},{r['dv_mae']:.12g},{r['mean_q_mae']:.12g},{r['a_mae_angstrom']:.12g},{r['c_mae_angstrom']:.12g}\n" for r in recomputed), encoding="utf-8")
    print(json.dumps({"p0_checkpoints": len(checkpoint_rows), "p0_recomputed_rows": len(recomputed), "p1_rows": len(p1_rows), "elapsed_seconds": total}, indent=2))


if __name__ == "__main__":
    main()
