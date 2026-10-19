from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from pymatgen.core import Lattice, Structure

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / p) for p in ("xrd_inversion/src", "xrd_robustness/src", "xrd_forward_loss/src", "donut_pxrd/src")]
from donut_pxrd.model import DonutPXRD, physical_latent
from pxrd_forward_loss.measurement_closure import expected_intensity_profile, expected_profile
from pxrd_forward_loss.measurement_sampling import sample_q_bank, sample_v9_nuisance_bank, split_assignment, split_q_indices
from xrd_inversion.gpu_forward import CachedTetragonalGPUForward


SEEDS = (20261061, 20261062, 20261063)
OUT = ROOT / "donut_pxrd" / "results" / "study_v1"
CKPT = Path(r"E:\AI4science_DONUT_checkpoints\donut_pxrd_four_stage_20261019")
LOG101 = math.log(101.0)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_array(value: np.ndarray) -> str:
    a = np.ascontiguousarray(value)
    return hashlib.sha256(str(a.dtype).encode() + json.dumps(a.shape).encode() + a.tobytes()).hexdigest()


def setup_forward():
    cfg = json.loads((ROOT / "xrd_inversion/configs/week1_formal_gate.json").read_text())
    cif = ROOT / "xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif"
    structure = Structure.from_file(cif)
    forward = CachedTetragonalGPUForward(structure, grid_config=cfg["grid"], parameter_config=cfg["parameterization"], device="cuda", dtype=torch.float64)
    return forward, cfg, structure


def profile_arrays(forward, q, delta, width, bg, mode):
    rows = []
    with torch.no_grad():
        for start in range(0, len(q), 16):
            sl = slice(start, start + 16)
            qt = torch.as_tensor(q[sl], dtype=torch.float64, device="cuda")
            eta = torch.as_tensor(np.column_stack((delta[sl], width[sl], bg[sl])), dtype=torch.float64, device="cuda")
            rows.append(expected_intensity_profile(forward, qt, eta, background_shape_mode=mode).cpu().numpy())
    return np.concatenate(rows)


def stage_truth(name: str, q: np.ndarray, rng: np.random.Generator):
    n = len(q)
    delta = np.zeros(n)
    width = np.full(n, 0.08)
    bg = np.full(n, 200.0 / 30000.0)
    mode = "simple_linear_counts"
    gaussian = False
    if name in ("exp2", "exp3a", "exp3b", "exp3c"):
        delta = rng.uniform(-0.06, 0.06, n)
    if name in ("exp3a", "exp3b", "exp3c"):
        width = rng.uniform(0.11, 0.13, n)
    if name in ("exp3b", "exp3c"):
        mode = "v9_polynomial"
        bg = rng.uniform(0.005, 0.008, n)
    if name == "exp3c":
        gaussian = True
    return delta, width, bg, mode, gaussian


def make_dataset(forward, name: str, cfg: dict):
    data = cfg["data"]
    q = sample_q_bank(data["q_count"], seed=data["sobol_seed"], q_bound=0.8)
    splits = split_q_indices(data["q_count"], seed=data["split_seed"], train_fraction=.70, validation_fraction=.15)
    rng = np.random.default_rng(data["nuisance_seed"] + {"exp1": 0, "exp2": 1, "exp3a": 2, "exp3b": 3, "exp3c": 4}[name])
    delta, width, bg, mode, gaussian = stage_truth(name, q, rng)
    expected_raw = profile_arrays(forward, q, delta, width, bg, mode)
    nrng = np.random.default_rng(data["noise_seed"] + {"exp1": 0, "exp2": 1, "exp3a": 2, "exp3b": 3, "exp3c": 4}[name])
    scale = int(data["count_scale"])
    counts = nrng.poisson(np.clip(expected_raw, 0, None) * scale).astype(np.float64)
    if gaussian:
        sigma = nrng.uniform(.5, 1.5, (len(q), 1))
        counts += nrng.normal(0, sigma, counts.shape)
    intensity = np.clip(counts, 0, None) / scale
    intensity /= np.maximum(intensity.max(axis=1, keepdims=True), 1.0 / scale)
    observed = (np.log1p(100 * intensity) / LOG101).astype(np.float32)
    arrays = {"q": q, "delta_deg": delta, "fwhm_deg": width, "background_ratio": bg, "observed": observed,
              "train_indices": splits["train"], "validation_indices": splits["validation"], "test_indices": splits["test"]}
    manifest = {"condition": name, "split_assignment": split_assignment(splits, len(q)), "split_counts": {k: len(v) for k, v in splits.items()},
                "arrays_sha256": {k: sha_array(v) for k, v in arrays.items()}, "background_shape_mode": mode,
                "nuisance_truth_policy": "generator and posthoc scoring only; excluded from model inputs, DONUT loss and validation selection",
                "observation": {"poisson_count_scale": scale, "gaussian_readout_counts": [0.5, 1.5] if gaussian else [0, 0], "preprocessing": cfg["data"]["input_transform"]}}
    return arrays, manifest


def physics_branch(forward, latent, names, mode, nominal):
    params = physical_latent(latent, names)
    delta = params.get("zero_shift", torch.zeros_like(params["du"]))
    q = torch.stack((params["du"], params["dv"]), dim=1).to(torch.float64)
    width = torch.full_like(delta, float(nominal["width"]))
    bg = torch.full_like(delta, float(nominal["bg"]))
    eta = torch.stack((delta, width, bg), dim=1).to(torch.float64)
    return expected_profile(forward, q, eta, background_shape_mode=mode).to(dtype=latent.dtype)


def metrics_from_prediction(q_pred, shift_pred, arrays, idx, structure, forward_cfg):
    q_true = arrays["q"][idx]
    delta_true = arrays["delta_deg"][idx]
    du, dv = q_pred[:, 0], q_pred[:, 1]
    err = q_pred - q_true
    pc = forward_cfg["parameterization"]
    u0 = (2 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3
    v0 = math.log(structure.lattice.c / structure.lattice.a)
    u = u0 + q_true[:, 0] * pc["du_half_range"]
    v = v0 + q_true[:, 1] * pc["dv_half_range"]
    a_true, c_true = np.exp(u - v / 3), np.exp(u + 2 * v / 3)
    up = u0 + du * pc["du_half_range"]
    vp = v0 + dv * pc["dv_half_range"]
    a_pred, c_pred = np.exp(up - vp / 3), np.exp(up + 2 * vp / 3)
    return {"n": len(idx), "du_mae": float(np.mean(np.abs(err[:, 0]))), "dv_mae": float(np.mean(np.abs(err[:, 1]))),
            "mean_q_mae": float(np.mean(np.abs(err))), "zero_shift_mae_deg": float(np.mean(np.abs(shift_pred - delta_true))),
            "a_mae_angstrom": float(np.mean(np.abs(a_pred - a_true))), "c_mae_angstrom": float(np.mean(np.abs(c_pred - c_true))),
            "q_shift_signed_corr": float(np.corrcoef(err[:, 0], shift_pred - delta_true)[0, 1]) if len(idx) > 2 else float("nan")}


def train_one(forward, cfg, arrays, manifest, exp_name, seed, nominal, mode, latent_names):
    device = torch.device("cuda")
    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    model = DonutPXRD(latent_names, output_length=arrays["observed"].shape[1], dropout=cfg["donut"]["dropout"]).to(device)
    opt = torch.optim.AdamW([
        {"params": model.encoder.parameters(), "lr": cfg["donut"]["encoder_lr"]},
        {"params": model.decoder.parameters(), "lr": cfg["donut"]["decoder_lr"]}], weight_decay=cfg["donut"]["weight_decay"])
    x = torch.as_tensor(arrays["observed"], device=device, dtype=torch.float32)
    train_idx = torch.as_tensor(arrays["train_indices"], device=device)
    val_idx = torch.as_tensor(arrays["validation_indices"], device=device)
    gen = torch.Generator(device=device).manual_seed(seed + 777)
    history, best, best_epoch, best_state = [], float("inf"), 0, None
    started = time.perf_counter()
    for epoch in range(1, cfg["donut"]["epochs_max"] + 1):
        model.train(); sums = np.zeros(3, dtype=np.float64)
        order = train_idx[torch.randperm(len(train_idx), generator=gen, device=device)]
        for ix in order.split(cfg["donut"]["batch_size"]):
            observed = x.index_select(0, ix).unsqueeze(1)
            latent, decoded = model(observed)
            physics = physics_branch(forward, latent, latent_names, mode, nominal)
            decode_loss = F.smooth_l1_loss(decoded[:, 0, :], observed[:, 0, :])
            physics_loss = F.smooth_l1_loss(physics, observed[:, 0, :])
            total = decode_loss + 5.0 * physics_loss
            opt.zero_grad(set_to_none=True); total.backward(); opt.step()
            sums += np.array([total.item(), decode_loss.item(), physics_loss.item()])
        model.eval(); val_sums = np.zeros(3, dtype=np.float64)
        with torch.no_grad():
            for ix in val_idx.split(cfg["donut"]["batch_size"]):
                observed = x.index_select(0, ix).unsqueeze(1)
                latent, decoded = model(observed)
                physics = physics_branch(forward, latent, latent_names, mode, nominal)
                dl = F.smooth_l1_loss(decoded[:, 0, :], observed[:, 0, :])
                pl = F.smooth_l1_loss(physics, observed[:, 0, :])
                val_sums += np.array([(dl + 5 * pl).item(), dl.item(), pl.item()])
        rec = {"epoch": epoch, "train_total": float(sums[0] / math.ceil(len(train_idx) / cfg["donut"]["batch_size"])),
               "train_decoder": float(sums[1] / math.ceil(len(train_idx) / cfg["donut"]["batch_size"])),
               "train_physics": float(sums[2] / math.ceil(len(train_idx) / cfg["donut"]["batch_size"])),
               "validation_total": float(val_sums[0] / math.ceil(len(val_idx) / cfg["donut"]["batch_size"])),
               "validation_decoder": float(val_sums[1] / math.ceil(len(val_idx) / cfg["donut"]["batch_size"])),
               "validation_physics": float(val_sums[2] / math.ceil(len(val_idx) / cfg["donut"]["batch_size"]))}
        history.append(rec)
        if rec["validation_total"] < best:
            best, best_epoch = rec["validation_total"], epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    elapsed = time.perf_counter() - started
    if best_state is None: raise RuntimeError("no validation checkpoint selected")
    model.load_state_dict(best_state)
    ckpt_path = CKPT / f"{exp_name}_seed{seed}.pt"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": best_state, "epoch": best_epoch, "latent_names": latent_names, "seed": seed}, ckpt_path)
    ckpt_sha = sha_file(ckpt_path)
    test_idx = arrays["test_indices"]
    with torch.no_grad():
        pred_rows, shift_rows = [], []
        for start in range(0, len(test_idx), 16):
            ix = test_idx[start:start+16]
            obs = x[torch.as_tensor(ix, device=device)].unsqueeze(1)
            latent, _ = model(obs)
            vals = physical_latent(latent, latent_names)
            pred_rows.append(torch.stack((vals["du"], vals["dv"]), dim=1).cpu().numpy())
            shift_rows.append(vals.get("zero_shift", torch.zeros_like(vals["du"])).cpu().numpy())
    pred_q, pred_shift = np.concatenate(pred_rows), np.concatenate(shift_rows)
    # A scored held-out pass also checks forward-profile reconstruction.
    pred_profile, target_profile = [], []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(test_idx), 16):
            ix = test_idx[start:start+16]
            obs = x[torch.as_tensor(ix, device=device)].unsqueeze(1)
            latent, _ = model(obs)
            pred_profile.append(physics_branch(forward, latent, latent_names, mode, nominal).cpu().numpy())
            target_profile.append(obs[:, 0, :].cpu().numpy())
    prof_rmse = float(np.sqrt(np.mean((np.concatenate(pred_profile) - np.concatenate(target_profile)) ** 2)))
    metric = metrics_from_prediction(pred_q, pred_shift, arrays, test_idx, STRUCTURE, FORWARD_CFG)
    metric.update({"seed": seed, "best_epoch": best_epoch, "training_seconds": elapsed, "checkpoint": str(ckpt_path), "checkpoint_sha256": ckpt_sha,
                   "test_profile_rmse": prof_rmse, "test_indices": test_idx.tolist(), "predicted_q": pred_q.tolist(), "true_q": arrays["q"][test_idx].tolist(),
                   "predicted_zero_shift_deg": pred_shift.tolist(), "true_zero_shift_deg": arrays["delta_deg"][test_idx].tolist()})
    return model, history, metric


def texture_ood(forward, cfg, arrays, base_test, structure, forward_cfg):
    """Generate hkl-aware March-Dollase stress spectra for frozen test q parents."""
    from xrd_robustness.physics import PhysicsParameters
    from xrd_robustness.simulator import SimulationGrid, ideal_peak_table, render_gaussian_peaks
    from xrd_robustness.preferred_orientation import apply_preferred_orientation
    grid_cfg = forward_cfg["grid"]
    grid = SimulationGrid(float(grid_cfg["two_theta_min"]), float(grid_cfg["two_theta_max"]), float(grid_cfg["step"]), float(grid_cfg["wavelength_angstrom"]))
    qidx = arrays["test_indices"]
    rng = np.random.default_rng(cfg["data"]["texture_seed"])
    rows, factors = [], []
    for idx in qidx:
        qv = arrays["q"][idx]
        p = forward.parameter_config
        u0 = (2 * math.log(structure.lattice.a) + math.log(structure.lattice.c)) / 3
        v0 = math.log(structure.lattice.c / structure.lattice.a)
        u = u0 + qv[0] * p["du_half_range"]; v = v0 + qv[1] * p["dv_half_range"]
        a, c = math.exp(u-v/3), math.exp(u+2*v/3)
        varied = Structure(lattice=Lattice.tetragonal(a,c), species=[s.species for s in structure], coords=structure.frac_coords)
        table = ideal_peak_table(varied, grid)
        march = float(rng.choice([0.85, 1.15]))
        params = PhysicsParameters(delta_2theta_deg=float(arrays["delta_deg"][idx]),
                                   fwhm_deg=float(arrays["fwhm_deg"][idx]),
                                   background_to_peak_ratio=float(arrays["background_ratio"][idx]),
                                   noise_std_ratio=0.0, background_type="polynomial", severity_level=1,
                                   preferred_orientation_active=True, march_parameter=march, preferred_hkl=(0,0,1),
                                   background_active=False, broadening_active=False, noise_active=False, zero_shift_active=False)
        modified, _, diag = apply_preferred_orientation(table, params)
        raw = render_gaussian_peaks(table.positions + arrays["delta_deg"][idx], modified, grid.values, float(arrays["fwhm_deg"][idx]), normalize=False)
        t = np.linspace(-1,1,len(raw)); bg_shape = 0.8 + 0.15*t + 0.05*t*t
        bg_shape = 0.10 + 0.90*(bg_shape-bg_shape.min())/(bg_shape.max()-bg_shape.min())
        raw = np.maximum(raw,0) + float(arrays["background_ratio"][idx]) * bg_shape
        noise_rng = np.random.default_rng(int(cfg["data"]["texture_seed"] + idx))
        counts = noise_rng.poisson(np.clip(raw,0,None) * int(cfg["data"]["count_scale"])).astype(float)
        counts += noise_rng.normal(0, 1.0, counts.shape)
        counts = np.clip(counts,0,None) / int(cfg["data"]["count_scale"])
        counts /= max(float(counts.max()), 1.0/int(cfg["data"]["count_scale"]))
        rows.append((np.log1p(100*counts)/LOG101).astype(np.float32)); factors.append({"q_index":int(idx),"march_parameter":march,**diag})
    return np.stack(rows), factors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", choices=("1","2","3","all"), required=True)
    parser.add_argument("--texture-only", action="store_true")
    args = parser.parse_args()
    cfg_path = ROOT / "donut_pxrd/configs/study_v1.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    global STRUCTURE, FORWARD_CFG
    forward, FORWARD_CFG, STRUCTURE = setup_forward()
    OUT.mkdir(parents=True, exist_ok=True); CKPT.mkdir(parents=True, exist_ok=True)
    outputs = []
    plan = [("exp1", ("du","dv"), "simple_linear_counts", {"width":.08,"bg":200/30000}),
            ("exp2", ("du","dv","zero_shift"), "simple_linear_counts", {"width":.08,"bg":200/30000}),
            ("exp3a", ("du","dv","zero_shift"), "simple_linear_counts", {"width":.12,"bg":200/30000}),
            ("exp3b", ("du","dv","zero_shift"), "v9_polynomial", {"width":.12,"bg":.0065}),
            ("exp3c", ("du","dv","zero_shift"), "v9_polynomial", {"width":.12,"bg":.0065})]
    selected = [] if args.texture_only else plan if args.experiment == "all" else [plan[int(args.experiment)-1]] if args.experiment in ("1","2") else plan[2:]
    for exp_name, names, model_mode, nominal in selected:
        arrays, data_manifest = make_dataset(forward, exp_name, cfg)
        run_dir = OUT / exp_name; run_dir.mkdir(parents=True, exist_ok=False)
        np.savez_compressed(run_dir / "data_arrays.npz", **arrays)
        data_manifest["npz_sha256"] = sha_file(run_dir / "data_arrays.npz")
        (run_dir / "data_manifest.json").write_text(json.dumps(data_manifest, indent=2)+"\n", encoding="utf-8")
        seed_metrics, histories = [], {}
        for seed in SEEDS:
            model, history, record = train_one(forward, cfg, arrays, data_manifest, exp_name, seed, nominal, model_mode, names)
            histories[str(seed)] = history; seed_metrics.append(record)
            # Save model output curves separately and reload the external checkpoint before accepting its hash.
            reloaded = DonutPXRD(names, output_length=arrays["observed"].shape[1], dropout=cfg["donut"]["dropout"]).cuda()
            loaded = torch.load(record["checkpoint"], map_location="cuda", weights_only=False)
            reloaded.load_state_dict(loaded["state_dict"])
            reloaded.eval()
        (run_dir / "training_curves.json").write_text(json.dumps(histories, indent=2)+"\n", encoding="utf-8")
        (run_dir / "test_per_seed.json").write_text(json.dumps(seed_metrics, indent=2)+"\n", encoding="utf-8")
        with (run_dir / "test_per_sample.csv").open("w", newline="", encoding="utf-8") as f:
            fields = ["seed","q_parent_index","true_du","pred_du","true_dv","pred_dv","true_shift_deg","pred_shift_deg"]
            writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
            for m in seed_metrics:
                for j,idx in enumerate(m["test_indices"]):
                    writer.writerow({"seed":m["seed"],"q_parent_index":idx,"true_du":m["true_q"][j][0],"pred_du":m["predicted_q"][j][0],"true_dv":m["true_q"][j][1],"pred_dv":m["predicted_q"][j][1],"true_shift_deg":m["true_zero_shift_deg"][j],"pred_shift_deg":m["predicted_zero_shift_deg"][j]})
        outputs.append({"experiment":exp_name,"status":"COMPLETE","run_dir":str(run_dir),"seeds":seed_metrics})
    if args.texture_only or args.experiment in ("3","all"):
        texture_base = json.loads((OUT/"exp3c"/"test_per_seed.json").read_text(encoding="utf-8"))
        arrays = dict(np.load(OUT/"exp3c"/"data_arrays.npz"))
        textured, texture_factors = texture_ood(forward,cfg,arrays,None,STRUCTURE,FORWARD_CFG)
        np.savez_compressed(OUT/"exp3_texture_ood.npz", observed=textured, test_indices=arrays["test_indices"])
        texture_metrics=[]
        for record in texture_base:
            names=("du","dv","zero_shift")
            model=DonutPXRD(names,output_length=textured.shape[1],dropout=cfg["donut"]["dropout"]).cuda()
            state=torch.load(record["checkpoint"],map_location="cuda",weights_only=False); model.load_state_dict(state["state_dict"]); model.eval()
            qhat=[]; shat=[]
            with torch.no_grad():
                for start in range(0,len(textured),16):
                    lat,_=model(torch.as_tensor(textured[start:start+16],device="cuda")[:,None,:]); p=physical_latent(lat,names)
                    qhat.extend(torch.stack((p["du"],p["dv"]),1).cpu().numpy()); shat.extend(p["zero_shift"].cpu().numpy())
            m=metrics_from_prediction(np.asarray(qhat),np.asarray(shat),arrays,arrays["test_indices"],STRUCTURE,FORWARD_CFG)
            m["seed"]=record["seed"]; texture_metrics.append(m)
        (OUT/"exp3_texture_ood_metrics.json").write_text(json.dumps({"status":"COMPLETE","classification":"nondifferentiable hkl-aware generator-side March-Dollase texture OOD stress; q+shift physics branch is texture-free","factors":texture_factors,"metrics_by_seed":texture_metrics},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"COMPLETE","experiments":outputs,"gpu_seconds":sum(m["training_seconds"] for o in outputs for m in o["seeds"])},indent=2))


if __name__ == "__main__":
    main()
