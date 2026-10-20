"""Bounded sequential Issue 44 benchmark; PR43 sources/results are read-only."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from pxrd_cross_material_autolab.experiment import splits
from pxrd_cross_material_autolab.manager import atomic, sha
from pxrd_cross_material_autolab.physics import ETA_NEUTRAL, PowderModel, gate
from pxrd_issue44.models import build

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
PRIMARY = ROOT / "pxrd_cross_material_autolab" / "runs" / "pilot_20261019"
STRESS_SOURCE = ROOT / "pxrd_cross_material_autolab" / "stress" / "run.py"

# On Windows WDDM, nvidia-smi reports ordinary desktop graphics contexts as
# C+G with no memory value. Treat only known desktop processes as graphics;
# unknown GPU-backed processes block training until manually inspected.
GRAPHICS_ONLY_IMAGES = {
    "applicationframehost.exe", "chatgpt.exe", "chrome.exe", "cloudmusic.exe", "codex-computer-use-swift.exe",
    "copilotapp.exe", "crossdeviceresume.exe", "dwm.exe", "explorer.exe", "legionzone.exe",
    "lockapp.exe", "msedgewebview2.exe", "nvidia overlay.exe", "phoneexperiencehost.exe",
    "qq.exe", "qqex.exe", "searchhost.exe", "shellexperiencehost.exe", "shellhost.exe",
    "snippingtool.exe", "startmenuexperiencehost.exe", "steamwebhelper.exe", "systemsettings.exe",
    "textinputhost.exe", "windowsterminal.exe", "weixin.exe", "wechatappex.exe", "workbuddy.exe",
}
COMPUTE_IMAGES = {
    "python.exe", "pythonw.exe", "jupyter.exe", "jupyter-lab.exe", "jupyter-notebook.exe",
    "ipykernel.exe", "matlab.exe", "matlabwindow.exe", "r.exe", "rterm.exe", "rscript.exe",
    "julia.exe", "blender.exe", "octave-gui.exe", "ollama.exe", "llama-server.exe",
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def hash_inputs():
    cfg = read_json(HERE / "frozen_config.json")
    oldcfg = read_json(ROOT / "pxrd_cross_material_autolab" / "config.json")
    paths = [HERE / "frozen_config.json", HERE / "PREREGISTRATION.md", HERE / "literature_matrix.md",
             HERE / "REAL_RRUFF_GATE.json", HERE / "models.py", HERE / "benchmark.py",
             HERE / "test_models.py", HERE / "test_benchmark.py",
             ROOT / "pxrd_cross_material_autolab" / "physics.py",
             ROOT / "pxrd_cross_material_autolab" / "experiment.py",
             ROOT / "pxrd_cross_material_autolab" / "manager.py",
             ROOT / "pxrd_cross_material_autolab" / "config.json",
             ROOT / "pxrd_cross_material_autolab" / "stress" / "run.py",
             ROOT / "pxrd_cross_material_autolab" / "stress" / "config.json",
             ROOT / "pxrd_cross_material_autolab" / "PREREGISTRATION.md",
             ROOT / "pxrd_cross_material_autolab" / "runs" / "pilot_20261019" / "manifest.json",
             ROOT / "pxrd_cross_material_autolab" / "runs" / "pilot_20261019" / "config.json",
             ROOT / "pxrd_cross_material_autolab" / "reports" / "final_verify.json"]
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    for mid in cfg["materials"]:
        material = next(m for m in oldcfg["materials"] if m["id"] == mid)
        cif = ROOT / material["cif_path"]
        if sha(cif) != material["cif_sha256"]:
            raise RuntimeError(f"CIF hash mismatch: {mid}")
        hashes[str(cif.relative_to(ROOT))] = sha(cif)
        for p in (PRIMARY / "materials" / mid).glob("attempt_*"):
            if (p / "test_opened.json").is_file() and (p / "per_sample.jsonl").is_file():
                hashes[str((p / "training_selection.json").relative_to(ROOT))] = sha(p / "training_selection.json")
                hashes[str((p / "test_opened.json").relative_to(ROOT))] = sha(p / "test_opened.json")
                hashes[str((p / "per_sample.jsonl").relative_to(ROOT))] = sha(p / "per_sample.jsonl")
        sp = ROOT / "pxrd_cross_material_autolab" / "stress" / "results_20261019" / mid / "per_sample.jsonl"
        if sp.is_file():
            hashes[str(sp.relative_to(ROOT))] = sha(sp)
    return hashes


def verify_pr43():
    cfg = read_json(HERE / "frozen_config.json")
    summary = read_json(ROOT / "pxrd_cross_material_autolab" / "reports" / "final_verify.json")
    if summary.get("status") != "PASS":
        raise RuntimeError("PR43 final_verify status is not PASS")
    frozen = read_json(PRIMARY / "manifest.json")
    code_hashes = frozen.get("identity", {}).get("source_sha256", {})
    source_paths = {"__main__.py": ROOT / "pxrd_cross_material_autolab" / "__main__.py",
                    "experiment.py": ROOT / "pxrd_cross_material_autolab" / "experiment.py",
                    "manager.py": ROOT / "pxrd_cross_material_autolab" / "manager.py",
                    "physics.py": ROOT / "pxrd_cross_material_autolab" / "physics.py",
                    "test_experiment.py": ROOT / "pxrd_cross_material_autolab" / "test_experiment.py",
                    "test_physics.py": ROOT / "pxrd_cross_material_autolab" / "test_physics.py"}
    for name, path in source_paths.items():
        expected = next((v for k, v in code_hashes.items() if k.replace("\\", "/").endswith("/" + name)), None)
        if expected is None or sha(path) != expected:
            raise RuntimeError(f"PR43 frozen source hash differs or is absent: {name}")
    material_cfg = read_json(ROOT / "pxrd_cross_material_autolab" / "config.json")
    found = {}
    for mid in cfg["materials"]:
        d = PRIMARY / "materials" / mid
        status = read_json(d / "status.json")
        if status.get("status") != "PASS":
            raise RuntimeError(f"PR43 material is not PASS: {mid}")
        attempts = [p for p in d.glob("attempt_*") if (p / "test_opened.json").is_file()]
        if len(attempts) != 1:
            raise RuntimeError(f"PR43 opened attempt count != 1: {mid}")
        rows = [json.loads(s) for s in (attempts[0] / "per_sample.jsonl").read_text(encoding="utf-8").splitlines()]
        required = [(m, seed) for m in ("P0", "P3", "N+A") for seed in ([0] if m != "N+A" else cfg["training"]["seeds"])]
        index = {(r["method"], int(r["seed"])): [] for r in rows}
        for r in rows:
            if (r["method"], int(r["seed"])) in index:
                index[(r["method"], int(r["seed"]))].append(r)
        if any(len(index[k]) != cfg["primary"]["test"] for k in required):
            raise RuntimeError(f"PR43 paired samples incomplete: {mid}")
        split_path = attempts[0] / "split_manifest.json"
        old_split = read_json(split_path)
        expected = splits({"data": {"parents": 512, "train": 358, "validation": 77, "test": 77, "split_seed": 2026101902}})
        for key, arr in expected.items():
            if old_split["indices"][key] != arr.tolist():
                raise RuntimeError(f"PR43 {key} parent split differs: {mid}")
        offset = int(hashlib.sha256(mid.encode()).hexdigest()[:8], 16)
        # Use the actual physical DOF count (cubic 1, tetragonal/hexagonal 2).
        ndof = 1 if next(m for m in material_cfg["materials"] if m["id"] == mid)["crystal_system"] == "cubic" else 2
        q = np.random.default_rng(2026101901 + offset).uniform(-0.8, 0.8, (512, ndof))
        qhash = hashlib.sha256(q.tobytes()).hexdigest()
        if old_split.get("q_parent_sha256") != qhash:
            raise RuntimeError(f"PR43 frozen parent q hash differs: {mid}")
        for r in rows:
            if r["method"] in ("P0", "P3", "N+A") and not np.array_equal(np.asarray(r["q_true_posthoc"]), q[int(r["parent"])]):
                raise RuntimeError(f"PR43 per-sample truth does not match frozen parent generator: {mid}/{r['parent']}")
        found[mid] = {"attempt": str(attempts[0].relative_to(ROOT)), "rows": len(rows), "split": old_split,
                      "rows_data": rows, "cif": next(m for m in material_cfg["materials"] if m["id"] == mid)}
    return found


def material_model(material):
    return PowderModel(str(ROOT / material["cif_path"]), grid_size=1024)


def draw_q_eta(material_id, model, base, count, indices=None):
    offset = int(hashlib.sha256(material_id.encode()).hexdigest()[:8], 16)
    q_all = np.random.default_rng(base["parent_seed"] + offset).uniform(-0.8, 0.8, (base["parents"], model.ndim))
    rng = np.random.default_rng(base["nuisance_seed"] + offset)
    eta_all = np.column_stack([rng.uniform(-0.10, 0.10, base["parents"]),
        rng.uniform(0.24, 0.42, base["parents"]), rng.uniform(0.8, 1.2, base["parents"]),
        rng.uniform(0.02, 0.06, base["parents"]), rng.uniform(-0.015, 0.015, base["parents"])])
    if indices is None:
        indices = np.arange(count)
    return q_all[indices], eta_all[indices], base["noise_seed"] + offset


def primary_observation(model, q, eta, seed, parent):
    mu = model.profile(q, eta)
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(parent)]))
    return (rng.poisson(np.maximum(mu, 0) * 15000) / 15000 + rng.normal(0, 0.002, len(mu))).astype(np.float32)


def stress_observation(model, q, eta, seed, parent, config):
    from pymatgen.analysis.diffraction.xrd import XRDCalculator
    pat = XRDCalculator(wavelength=model.wavelength).get_pattern(model.structure_at(q), scaled=False,
             two_theta_range=(10, 95))
    z, width, scale, bg, slope = eta
    delta = (model.grid[None, :] - pat.x[:, None] - z) / width
    frac = config["lorentz_fraction"]
    peaks = (1 - frac) * np.exp(-4 * np.log(2) * delta ** 2) + frac / (1 + 4 * delta ** 2)
    xnorm = (model.grid - model.grid.mean()) / np.ptp(model.grid)
    mu = scale * (pat.y[:, None] * peaks).sum(0) / model.reference_max + bg + slope * xnorm + config["quadratic_background"] * xnorm ** 2
    rng = np.random.default_rng(np.random.SeedSequence([seed, int(parent)]))
    return (rng.poisson(np.maximum(mu, 0) * 15000) / 15000 + rng.normal(0, 0.002, len(mu))).astype(np.float32)


def seed_stream(seed):
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def atomic_torch_save(path: Path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    os.replace(tmp, path)


def fit_attempt(model, y, start, config):
    t0 = time.perf_counter()
    try:
        result = model.fit(y, np.asarray(start, dtype=float), maxiter=config["physics"]["maxiter_per_start"],
                           maxfun=config["physics"]["maxfun_per_start"])
        result["seconds"] = max(float(result.get("seconds", 0.0)), time.perf_counter() - t0)
        return result
    except Exception as exc:
        return {"q": np.asarray(start).tolist(), "eta": ETA_NEUTRAL.tolist(), "rmse": 1.0e9,
                "nfev": 0, "nit": 0, "success": False, "message": repr(exc),
                "seconds": time.perf_counter() - t0,
                "boundary_hit": False, "failed": True}


def metric_row(model, mid, method, seed, parent, truth, qhat, y, attempts, elapsed, inference=0.0):
    successful = [x for x in attempts if x.get("success")]
    best = min(successful or attempts, key=lambda x: x["rmse"])
    qfit = np.asarray(qhat if method.endswith("-direct") else best["q"], dtype=float)
    lattice_fit = model.lattice(qfit)
    lattice_true = model.lattice(truth)
    return {"material": mid, "method": method, "seed": int(seed), "parent": int(parent),
            "q_true_posthoc": np.asarray(truth).tolist(), "q_fit": qfit.tolist(),
            "lattice_true_angstrom": lattice_true.tolist(), "lattice_fit_angstrom": lattice_fit.tolist(),
            "lattice_abs_error_angstrom": np.abs(lattice_fit - lattice_true).tolist(),
            "rmse": float(best["rmse"]), "success": bool(best["success"]),
            "boundary_hit": bool(best["boundary_hit"]), "seconds": float(elapsed + inference),
            "inference_seconds": float(inference), "nfev": int(sum(x["nfev"] for x in attempts)),
            "iterations": int(sum(x["nit"] for x in attempts)), "attempts": attempts,
            "multistart_disagreement": float(np.max(np.ptp(np.asarray([x["q"] for x in attempts]), axis=0))) if len(attempts) > 1 else 0.0,
            "q_hat_direct": np.asarray(qhat).tolist() if method.endswith("-direct") else None,
            "fit_failure_messages": [x.get("message") for x in attempts if not x.get("success")]}


def append_jsonl(path: Path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, allow_nan=False) + "\n")


def gpu_compute_processes():
    """Return GPU processes that could be compute jobs, filtering WDDM GUI noise."""
    proc = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory",
                           "--format=csv,noheader,nounits"], capture_output=True, text=True,
                          timeout=10, check=True)
    rows = []
    for row in csv.reader(io.StringIO(proc.stdout)):
        if len(row) < 1 or not row[0].strip().isdigit():
            continue
        pid = int(row[0].strip())
        if pid == os.getpid():
            continue
        name = Path(row[1].strip()).name.casefold() if len(row) > 1 else ""
        rows.append((pid, name))
    if not rows:
        return []
    powershell_script = ("$ids=@([Console]::In.ReadToEnd() -split '[,\\s]+' | Where-Object { $_ -match '^\\d+$' } "
                         "| ForEach-Object { [int]$_ }); Get-Process -Id $ids -ErrorAction Stop "
                         "| Select-Object Id,ProcessName | ConvertTo-Json -Compress")
    resolved = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", powershell_script],
                              input=",".join(str(pid) for pid, _ in rows), capture_output=True, text=True,
                              timeout=15, check=True)
    process_rows = json.loads(resolved.stdout)
    if isinstance(process_rows, dict):
        process_rows = [process_rows]
    names = {int(row["Id"]): f"{row['ProcessName']}.exe".casefold() for row in process_rows}
    blockers = []
    for pid, reported_name in rows:
        image = names.get(pid, reported_name)
        if not image or image in COMPUTE_IMAGES or image not in GRAPHICS_ONLY_IMAGES:
            blockers.append(image or f"pid:{pid}:unresolved")
    return sorted(set(blockers))


def summarize_issue44(rows):
    summary = []
    groups = sorted(set((r["material"], r["method"], int(r["seed"])) for r in rows))
    for material, method, seed in groups:
        group = [r for r in rows if r["material"] == material and r["method"] == method
                 and int(r["seed"]) == seed]
        ok = [r for r in group if r["success"] and r["q_fit"] is not None]
        qerr = [np.abs(np.asarray(r["q_fit"]) - np.asarray(r["q_true_posthoc"])) for r in ok]
        cellerr = [np.asarray(r["lattice_abs_error_angstrom"]) for r in ok]
        seconds = [float(r["seconds"]) for r in group]
        rmse = [float(r["rmse"]) for r in ok]
        ndim = len(group[0]["q_true_posthoc"])
        summary.append({"material": material, "method": method, "seed": seed,
            "n_total": len(group), "n_success": len(ok), "n_failed": len(group) - len(ok),
            "q_mae": float(np.mean(qerr)) if qerr else None,
            "q_mae_per_dof": np.mean(qerr, axis=0).tolist() if qerr else [None] * ndim,
            "lattice_mae_angstrom": np.mean(cellerr, axis=0).tolist() if cellerr else [None] * ndim,
            "profile_rmse_successful_only": float(np.mean(rmse)) if rmse else None,
            "convergence_rate": len(ok) / len(group),
            "boundary_rate": float(np.mean([r["boundary_hit"] for r in group])),
            "mean_seconds_end_to_end": float(np.mean(seconds)), "median_seconds": float(np.median(seconds)),
            "p95_seconds": float(np.percentile(seconds, 95)),
            "mean_nfev": float(np.mean([r["nfev"] for r in group])),
            "multistart_disagreement_mean": float(np.mean([r.get("multistart_disagreement", 0) for r in group]))})
    return summary


def _summary_entry(rows, material, method, seed=0):
    return next(r for r in rows if r["material"] == material and r["method"] == method and int(r["seed"]) == int(seed))


def _bootstrap_delta(values, rng, resamples=2000):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
        return {"n_parents": int(len(values)), "mean_delta": None, "ci95_low": None, "ci95_high": None}
    draws = rng.integers(0, len(values), size=(resamples, len(values)))
    means = values[draws].mean(axis=1)
    return {"n_parents": int(len(values)), "mean_delta": float(values.mean()),
            "ci95_low": float(np.percentile(means, 2.5)), "ci95_high": float(np.percentile(means, 97.5))}


def paired_parent_bootstrap(rows, material, architecture, seed, resamples=2000):
    """Descriptive paired-parent uncertainty for refined neural minus P3 errors."""
    method = f"{architecture}+A"
    keyed = {}
    for row in rows:
        if row["material"] == material and row["method"] in ("P3", method) and int(row["seed"]) == (0 if row["method"] == "P3" else int(seed)):
            keyed.setdefault(row["method"], {})[int(row["parent"])] = row
    common = sorted(set(keyed.get("P3", {})) & set(keyed.get(method, {})))
    common = [p for p in common if keyed["P3"][p]["success"] and keyed[method][p]["success"]]
    digest = hashlib.sha256(f"issue44-bootstrap-v1/{material}/{architecture}/{seed}".encode()).digest()
    rng = np.random.default_rng(int.from_bytes(digest[:8], "big"))
    if not common:
        return {"material": material, "architecture": architecture, "seed": int(seed), "comparison": f"{method} minus P3",
                "q_mae": _bootstrap_delta([], rng, resamples), "cell_mae_angstrom_per_dof": []}
    model_rows = [keyed[method][p] for p in common]
    base_rows = [keyed["P3"][p] for p in common]
    q_delta = [np.abs(np.asarray(m["q_fit"]) - np.asarray(m["q_true_posthoc"])).mean()
               - np.abs(np.asarray(b["q_fit"]) - np.asarray(b["q_true_posthoc"])).mean()
               for m, b in zip(model_rows, base_rows)]
    ndof = len(model_rows[0]["lattice_abs_error_angstrom"])
    cell_delta = []
    for dof in range(ndof):
        values = [float(m["lattice_abs_error_angstrom"][dof]) - float(b["lattice_abs_error_angstrom"][dof])
                  for m, b in zip(model_rows, base_rows)]
        cell_delta.append(_bootstrap_delta(values, rng, resamples))
    return {"material": material, "architecture": architecture, "seed": int(seed),
            "comparison": f"{method} minus P3", "q_mae": _bootstrap_delta(q_delta, rng, resamples),
            "cell_mae_angstrom_per_dof": cell_delta,
            "interpretation": "descriptive paired-parent bootstrap interval; not a significance test"}


def build_report(run, config):
    primary = read_json(run / "primary" / "metrics.json")
    mlp_primary = read_json(run / "primary" / "mlp_pr43_primary_reference.json")
    stress = read_json(run / "stress" / "metrics.json")
    stress_status = read_json(run / "stress" / "status.json")
    primary_raw = [json.loads(line) for mid in config["materials"]
                   for line in (run / "primary" / mid / "per_sample.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()]
    optimizer_attempts = [attempt for row in primary_raw for attempt in row.get("attempts", [])]
    record_audit = {
        "rows": len(primary_raw),
        "rows_by_method": dict(sorted(Counter(row["method"] for row in primary_raw).items())),
        "failed_rows": sum(not bool(row.get("success")) for row in primary_raw),
        "rows_with_boundary_hit": sum(bool(row.get("boundary_hit")) for row in primary_raw),
        "optimizer_attempts": len(optimizer_attempts),
        "failed_optimizer_attempts": sum(not bool(attempt.get("success")) for attempt in optimizer_attempts),
        "boundary_hit_optimizer_attempts": sum(bool(attempt.get("boundary_hit")) for attempt in optimizer_attempts),
    }
    comparison = {"scope": "previously opened exploratory PR43 same-generator and independent-renderer extensions",
                  "materials": {}, "criteria": {}}
    report = ["# Issue #44 bounded multi-architecture PXRD inversion benchmark", "",
        "**Interpretation:** architecture-transfer extension on synthetic known-candidate profiles. The 77-parent primary split and 16-parent independent-renderer stress set were already opened in PR43 for MLP; this is exploratory and not independent confirmation. MLP results are read-only PR43 references.", "",
        "Real RRUFF: **BLOCKED** by `REAL_RRUFF_GATE.json`. This report does not claim experimental cell accuracy, structure identification, or unseen-material generalization.", "",
        "## Primary results by material and model", "",
        "q MAE averages normalized q DOFs; the per-DOF q and cell errors remain in the machine table. Cell errors are Å. End-to-end time includes all optimizer starts and neural inference; training is also shown separately and amortized across the fixed 77 samples.", "",
        "| Material | Method | Seed | q MAE | q MAE/DOF | Cell MAE/DOF (Å) | Conv. | Mean sec/sample | Training sec | Train amortized sec/sample | nfev |", "|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|"]
    criteria_rows = []
    for mid in config["materials"]:
        entries = [r for r in primary if r["material"] == mid]
        comparison["materials"][mid] = {"primary": entries,
            "mlp_pr43_n_plus_a": [r for r in mlp_primary if r["material"] == mid],
            "stress": [r for r in stress if r["material"] == mid]}
        for method, seed in [("P0", 0), ("P3", 0), ("P5", 0)]:
            r = _summary_entry(entries, mid, method, seed)
            report.append(f"| {mid} | {method} | 0 | {r['q_mae']:.6g} | {r['q_mae_per_dof']} | {r['lattice_mae_angstrom']} | {r['convergence_rate']:.3f} | {r['mean_seconds_end_to_end']:.6g} | 0 | 0 | {r['mean_nfev']:.2f} |")
        for arch in config["architectures"]:
            for seed in config["training"]["seeds"]:
                selection = read_json(run / "models" / mid / arch / f"selection_{seed}.json")
                for method in (f"{arch}-direct", f"{arch}+A"):
                    r = _summary_entry(entries, mid, method, seed)
                    amort = selection["training_seconds"] / config["primary"]["test"]
                    report.append(f"| {mid} | {method} | {seed} | {r['q_mae']:.6g} | {r['q_mae_per_dof']} | {r['lattice_mae_angstrom']} | {r['convergence_rate']:.3f} | {r['mean_seconds_end_to_end']:.6g} | {selection['training_seconds']:.4g} | {amort:.6g} | {r['mean_nfev']:.2f} |")
                p3 = _summary_entry(entries, mid, "P3")
                p5 = _summary_entry(entries, mid, "P5")
                r = _summary_entry(entries, mid, f"{arch}+A", seed)
                q_pass = r["q_mae"] is not None and r["q_mae"] <= 0.95 * p3["q_mae"]
                cell_pass = all(a <= 1.05 * b for a, b in zip(r["lattice_mae_angstrom"], p3["lattice_mae_angstrom"]))
                conv_pass = r["convergence_rate"] >= p3["convergence_rate"]
                total_amort = r["mean_seconds_end_to_end"] + selection["training_seconds"] / config["primary"]["test"]
                runtime_pass = total_amort < p3["mean_seconds_end_to_end"] and cell_pass and conv_pass and r["q_mae"] <= 1.05 * p3["q_mae"]
                criteria_rows.append({"material": mid, "architecture": arch, "seed": seed,
                    "q_accuracy_vs_p3_pass": q_pass, "cell_mae_vs_p3_pass": cell_pass,
                    "convergence_vs_p3_pass": conv_pass, "end_to_end_amortized_runtime_vs_p3_pass": runtime_pass,
                    "q_mae": r["q_mae"], "p3_q_mae": p3["q_mae"], "p5_q_mae": p5["q_mae"],
                    "amortized_total_seconds_per_sample": total_amort, "p3_seconds_per_sample": p3["mean_seconds_end_to_end"]})
        for r in [x for x in mlp_primary if x["material"] == mid]:
            report.append(f"| {mid} | MLP_PR43_N+A | {r['seed']} | {r['q_mae']:.6g} | {r['q_mae_per_dof']} | {r['lattice_mae_angstrom']} | {r['convergence_rate']:.3f} | {r['mean_seconds_end_to_end']:.6g} | historical PR43 | n/a | {r['mean_nfev']:.2f} |")
    accuracy_all = bool(criteria_rows) and all(r["q_accuracy_vs_p3_pass"] and r["cell_mae_vs_p3_pass"] and r["convergence_vs_p3_pass"] for r in criteria_rows)
    runtime_all = bool(criteria_rows) and all(r["end_to_end_amortized_runtime_vs_p3_pass"] for r in criteria_rows)
    comparison["criteria"] = {"per_material_architecture_seed": criteria_rows,
        "all_42_architecture_seed_material_cells_pass_accuracy_vs_p3": accuracy_all,
        "all_42_architecture_seed_material_cells_pass_amortized_runtime_vs_p3": runtime_all,
        "pass_counts": {
            "q_accuracy_vs_p3": sum(bool(r["q_accuracy_vs_p3_pass"]) for r in criteria_rows),
            "cell_mae_vs_p3": sum(bool(r["cell_mae_vs_p3_pass"]) for r in criteria_rows),
            "convergence_vs_p3": sum(bool(r["convergence_vs_p3_pass"]) for r in criteria_rows),
            "amortized_runtime_vs_p3": sum(bool(r["end_to_end_amortized_runtime_vs_p3_pass"]) for r in criteria_rows),
            "denominator": len(criteria_rows),
        },
        "overall_readout": "consistent neural accuracy increment across frozen matrix" if accuracy_all else "no consistent neural accuracy increment across the frozen matrix; retain per-material mixed results"}
    comparison["compute"] = read_json(run / "budget.json")
    comparison["primary_record_audit"] = record_audit
    comparison["training_models"] = read_json(run / "training_complete.json")["models"]
    comparison["paired_parent_bootstrap_vs_p3"] = [
        paired_parent_bootstrap(primary_raw, mid, arch, seed)
        for mid in config["materials"] for arch in config["architectures"]
        for seed in config["training"]["seeds"]]
    comparison["pr43_historical_mlp_training_cuda_seconds_all_materials"] = 20.414
    comparison["stress_status"] = stress_status
    comparison["stress_note"] = ("Same already-opened PR43 independent-renderer parents; exploratory only. Full per-material/per-seed metrics stored in stress/metrics.json."
                                  if stress_status.get("status") == "COMPLETE" else
                                  "Stress was not run in this continuation; see stress/status.json. Historical PR43 stress remains unchanged and is not a new-architecture comparison.")
    recovery_path = run / "post_primary_recovery.json"
    failure_path = run / "failure.json"
    recovery = read_json(recovery_path) if recovery_path.is_file() else {}
    prior_failure = read_json(failure_path) if failure_path.is_file() else {}
    environment_path = run / "stress" / "environment_gate.json"
    environment_gate = read_json(environment_path) if environment_path.is_file() else {}
    process_observation = environment_gate.get("process_observation", {})
    comparison["run_status"] = "PARTIAL" if stress_status.get("status") != "COMPLETE" else "PARTIAL"
    comparison["manager_recovery"] = {
        "primary_rows_verified": recovery.get("primary_rows_verified", len(primary_raw)),
        "primary_scoring_rerun": False,
        "training_models_verified": recovery.get("primary_audit", {}).get("training_models", len(read_json(run / "training_complete.json")["models"])),
        "initial_failure_preserved": bool(prior_failure),
        "initial_failure": prior_failure.get("error"),
        "recovery_method": "material-scoped aggregation from persisted per-sample JSONL; model training, selection, and primary scoring were not repeated",
    }
    comparison["runtime_measurement_caveat"] = {
        "status": "POTENTIAL_CPU_CONTENTION_CANNOT_BE_EXCLUDED" if process_observation else "NO_ADDITIONAL_PROCESS_OBSERVATION_RECORDED",
        "process_observation": process_observation,
        "interpretation": "The unidentified Python process was observed during the stress gate and its recorded start time predates this run; its activity during primary scoring is unknown, so CPU wall-time comparisons are descriptive and may be confounded. It was not interrupted.",
    }
    atomic(run / "comparison.json", comparison)
    report.extend(["", "## Predeclared interpretation", "",
        f"q-accuracy gate versus P3: **{comparison['criteria']['pass_counts']['q_accuracy_vs_p3']}/{len(criteria_rows)}** cells pass the required 5% reduction.",
        f"Per-DOF cell-MAE constraint: **{comparison['criteria']['pass_counts']['cell_mae_vs_p3']}/{len(criteria_rows)}** cells pass; convergence is no worse in **{comparison['criteria']['pass_counts']['convergence_vs_p3']}/{len(criteria_rows)}**.",
        f"Amortized end-to-end runtime gate versus P3: **{comparison['criteria']['pass_counts']['amortized_runtime_vs_p3']}/{len(criteria_rows)}** cells pass (ResNet {sum(r['end_to_end_amortized_runtime_vs_p3_pass'] for r in criteria_rows if r['architecture'] == 'resnet1d')}/21; Transformer {sum(r['end_to_end_amortized_runtime_vs_p3_pass'] for r in criteria_rows if r['architecture'] == 'transformer')}/21).",
        "The full-matrix accuracy and runtime gates are not met. Neural initialization did not show a consistent accuracy gain over P3; per-material results and P0/P3/P5 remain visible in the machine tables.",
        "P5 is listed for each material and all individual attempts are retained in `primary/<material>/per_sample.jsonl`. The historical MLP training duration is reported as the PR43 total; new architecture training is listed by run and epoch in the machine evidence.", "",
        "## Independent-renderer stress", ""])
    if stress_status.get("status") == "COMPLETE":
        report.append("Each material has 16 previously opened PR43 stress parents with 0.7 Gaussian + 0.3 Lorentzian peaks and unmodelled quadratic background. The full per-material/per-seed P0/P3/P5, direct ResNet/Transformer, refined ResNet/Transformer, and historical MLP metrics are in `stress/metrics.json` and `stress/<material>/mlp_pr43_reference.json`. This stress set is not independent confirmation.")
    else:
        report.append(f"**{stress_status.get('status', 'NOT_RECORDED')}:** {stress_status.get('reason', 'No new stress rows were scored.')}")
        report.append("No new independent-renderer profiles were generated or scored in this branch. The historical PR43 stress baseline is unchanged and is not a comparison against the new architectures.")
    report.extend(["",
        "## Provenance and retained evidence", "",
        "`manifest.json` freezes the source/config/CIF/PR43 evidence hashes before new training. `training_complete.json` records all 42 selected models, checkpoint hashes, epochs and measured training time; `models/**/learning_curves.jsonl` records each epoch. `budget.json` records cumulative GPU training time. Per-sample optimizer attempts include starts, nfev, convergence, bounds, errors and timing. See `literature_matrix.md` and `source_audit_addendum_20261020.md` for task fidelity and license provenance. Raw arrays and checkpoints remain ignored locally.", "",
        "No statistical significance is claimed. The synthetic gates do not clear the independent real-RRUFF physics gate.", ""])
    recovery_text = (
        "## Execution status and recovery\n\n"
        "Overall status: **PARTIAL**. The predeclared synthetic primary matrix is complete for seven materials, two architectures, three seeds, and 77 already-opened PR43 test parents per material (42 trained models; 8,085 per-parent/method/seed rows for P0/P3/P5 and the new neural methods). Historical MLP metrics are separate, read-only PR43 summaries. These reused parents make the result exploratory, not independent confirmation.\n\n"
        "The first manager attempt completed training and primary scoring, then stopped while aggregating vectors from materials with different numbers of lattice DOFs. The original `failure.json` is retained. Recovery changed material grouping in the reporting code, verified all saved primary rows and all 42 selection/checkpoint hashes, and regenerated summaries from the saved JSONL. `primary_scoring_rerun` is false; no new profiles were generated and no fit or model selection was repeated.\n\n"
        f"The saved primary records contain {record_audit['optimizer_attempts']:,} optimizer attempts ({record_audit['failed_optimizer_attempts']} failed attempts; {record_audit['boundary_hit_optimizer_attempts']} bound-hit attempts), {record_audit['failed_rows']} failed rows, and {record_audit['rows_with_boundary_hit']} rows with any bound hit. Measured CUDA training was {float(read_json(run / 'budget.json').get('gpu_training_seconds', 0)):.3f} seconds; the recorded run elapsed {float(recovery.get('elapsed_seconds_after', recovery.get('budget_elapsed_seconds_before_stress', 0))):.1f} seconds before report finalization. Stress remains **BLOCKED_NOT_RUN** and real RRUFF remains **BLOCKED**.\n\n"
    )
    if process_observation:
        recovery_text += (
            f"At the stress gate, unidentified Python PID {process_observation.get('pid')} was observed using "
            f"{process_observation.get('cpu_seconds_delta')} CPU seconds during a {process_observation.get('sample_wall_seconds')}-second sample; command-line inspection was denied. Its recorded start ({process_observation.get('started_at')}) predates the run, but activity during primary scoring is unknown. The CPU wall-time comparisons may therefore be confounded and are descriptive only. No process was interrupted.\n\n"
        )
    report.extend([recovery_text.rstrip(), "",
        "Paired-parent bootstrap intervals for refined neural minus P3 q and per-DOF cell errors are descriptive only; they are not significance tests."])
    report.append("")
    (run / "FINAL_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return comparison


def budget_check(run, started, gpu_seconds):
    cfg = read_json(HERE / "frozen_config.json")["compute_limits"]
    if time.time() - started >= cfg["wall_seconds"]:
        raise RuntimeError("PARTIAL: 8-hour wall budget reached")
    if gpu_seconds >= cfg["cuda_training_seconds"]:
        raise RuntimeError("PARTIAL: 4-hour CUDA training budget reached")
    size = sum(p.stat().st_size for p in run.rglob("*") if p.is_file())
    if size >= cfg["disk_bytes"]:
        raise RuntimeError("PARTIAL: 10 GB Issue44 output budget reached")


def train_one(run, mid, arch, seed, model, train_x, train_y, val_x, val_y, config, started, gpu_seconds,
              model_prefix="models"):
    out = run / model_prefix / mid / arch
    private = out / "private"
    private.mkdir(parents=True, exist_ok=True)
    selection_file = out / f"selection_{seed}.json"
    if selection_file.is_file():
        return read_json(selection_file), gpu_seconds
    device = torch.device("cuda")
    seed_stream(seed)
    net = build(arch, model.ndim, len(model.grid)).to(device)
    opt = torch.optim.Adam(net.parameters(), lr=config["training"]["learning_rate"])
    x = torch.as_tensor(train_x, dtype=torch.float32, device=device)
    y = torch.as_tensor(train_y, dtype=torch.float32, device=device)
    vx = torch.as_tensor(val_x, dtype=torch.float32, device=device)
    vy = torch.as_tensor(val_y, dtype=torch.float32, device=device)
    checkpoint = private / f"resume_{seed}.pt"
    curves = out / "learning_curves.jsonl"
    best = float("inf"); best_epoch = 0; best_state = None; first_epoch = 0; history = []
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location=device, weights_only=False)
        if saved["arch"] != arch or saved["seed"] != seed:
            raise RuntimeError(f"checkpoint identity mismatch: {checkpoint}")
        net.load_state_dict(saved["net"]); opt.load_state_dict(saved["optimizer"])
        best = saved["best_val"]; best_epoch = saved["best_epoch"]; best_state = saved["best_state"]
        first_epoch = saved["epoch"]; history = saved["history"]
        torch.set_rng_state(saved["torch_rng"])
        if torch.cuda.is_available() and saved.get("cuda_rng") is not None:
            torch.cuda.set_rng_state(saved["cuda_rng"], device=device)
    torch.set_num_threads(1)
    for epoch in range(first_epoch, config["training"]["epochs"]):
        budget_check(run, started, gpu_seconds)
        net.train(); order = torch.randperm(len(x), device=device); train_losses = []
        if device.type == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for ids in order.split(config["training"]["batch_size"]):
            opt.zero_grad(set_to_none=True)
            loss = torch.mean((net(x[ids]) - y[ids]) ** 2)
            if not torch.isfinite(loss):
                raise RuntimeError(f"nonfinite training loss {mid}/{arch}/{seed}/{epoch + 1}")
            loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), config["training"]["gradient_clip_norm"])
            opt.step(); train_losses.append((float(loss.detach()), len(ids)))
        net.eval()
        with torch.no_grad():
            val_mae = float(torch.mean(torch.abs(net(vx) - vy)))
        if device.type == "cuda":
            torch.cuda.synchronize()
        if not np.isfinite(val_mae):
            raise RuntimeError(f"nonfinite validation q-MAE {mid}/{arch}/{seed}/{epoch + 1}")
        if val_mae < best:
            best = val_mae; best_epoch = epoch + 1
            best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
        duration = time.perf_counter() - t0
        gpu_seconds += duration
        row = {"material": mid, "architecture": arch, "seed": seed, "epoch": epoch + 1,
               "train_mse": sum(a * n for a, n in train_losses) / len(x), "validation_q_mae": val_mae,
               "best_validation_q_mae": best, "best_epoch": best_epoch, "epoch_seconds": duration,
               "cumulative_cuda_training_seconds": gpu_seconds}
        history.append(row)
        payload = {"arch": arch, "seed": seed, "epoch": epoch + 1, "net": net.state_dict(),
                   "optimizer": opt.state_dict(), "best_val": best, "best_epoch": best_epoch,
                   "best_state": best_state, "history": history, "torch_rng": torch.get_rng_state(),
                   "cuda_rng": torch.cuda.get_rng_state(device) if torch.cuda.is_available() else None}
        atomic_torch_save(checkpoint, payload)
        append_jsonl(curves, row)
        atomic(run / "budget.json", {"started": started, "gpu_training_seconds": gpu_seconds,
                                      "updated": time.time(), "last_model": f"{mid}/{arch}/{seed}/{epoch + 1}"})
        budget_check(run, started, gpu_seconds)
    net.load_state_dict(best_state); net.eval()
    final = private / f"best_{seed}.pt"
    atomic_torch_save(final, {"arch": arch, "seed": seed, "state": best_state})
    record = {"material": mid, "architecture": arch, "seed": seed, "best_epoch": best_epoch,
              "best_validation_q_mae": best, "training_epochs": config["training"]["epochs"],
              "training_examples_per_epoch": len(train_x), "optimizer_steps": int(np.ceil(len(train_x) / config["training"]["batch_size"]) * config["training"]["epochs"]),
              "parameter_count": sum(p.numel() for p in build(arch, model.ndim, len(model.grid)).parameters()),
              "checkpoint_sha256": sha(final), "training_device": str(device),
              "training_seconds": float(sum(x["epoch_seconds"] for x in history))}
    atomic(selection_file, record)
    checkpoint.unlink(missing_ok=True)
    return record, gpu_seconds


def tracked_train_one(*args, **kwargs):
    run, mid, arch, seed = args[:4]
    prefix = kwargs.get("model_prefix", "models")
    append_jsonl(run / "events.jsonl", {"event": "model_start", "time": time.time(), "material": mid,
        "architecture": arch, "seed": int(seed), "model_prefix": prefix})
    try:
        record, gpu_seconds = train_one(*args, **kwargs)
    except Exception as exc:
        append_jsonl(run / "events.jsonl", {"event": "model_failed", "time": time.time(),
            "material": mid, "architecture": arch, "seed": int(seed), "error": repr(exc)})
        raise
    append_jsonl(run / "events.jsonl", {"event": "model_complete", "time": time.time(),
        "material": mid, "architecture": arch, "seed": int(seed),
        "best_epoch": record["best_epoch"], "training_seconds": record["training_seconds"],
        "checkpoint_sha256": record["checkpoint_sha256"], "cumulative_cuda_training_seconds": gpu_seconds})
    return record, gpu_seconds


def load_network(run, mid, arch, seed, ndim, length):
    path = run / "models" / mid / arch / "private" / f"best_{seed}.pt"
    saved = torch.load(path, map_location="cpu", weights_only=True)
    net = build(arch, ndim, length); net.load_state_dict(saved["state"]); net.eval()
    return net


def evaluate_primary(run, prior, config, materials):
    marker = run / "test_opened.json"
    if marker.exists():
        raise RuntimeError("test-open marker already exists; no automatic test retry")
    selections = []
    for mid in config["materials"]:
        for arch in config["architectures"]:
            for seed in config["training"]["seeds"]:
                p = run / "models" / mid / arch / f"selection_{seed}.json"
                if not p.is_file():
                    raise RuntimeError(f"missing completed architecture before test opening: {p}")
                selections.append({"path": str(p.relative_to(ROOT)), "sha256": sha(p)})
    atomic(marker, {"time": time.time(), "protocol_sha256": sha(HERE / "PREREGISTRATION.md"),
                    "config_sha256": sha(HERE / "frozen_config.json"), "selection_files": selections,
                    "status": "OPENED_ONCE", "relationship": "same already-opened PR43 test parents; exploratory only"})
    append_jsonl(run / "events.jsonl", {"event": "test_opened", "time": time.time(),
        "selection_count": len(selections), "role": "previously opened PR43 parents; exploratory only"})
    attempt = run / "primary"
    attempt.mkdir(exist_ok=True)
    allrows = []
    old_rows = []
    split_cfg = {"data": {"parents": 512, "train": 358, "validation": 77, "test": 77, "split_seed": 2026101902}}
    sp = splits(split_cfg)
    for mid in config["materials"]:
        m = materials[mid]; model = material_model(m)
        q, eta, noise_seed = draw_q_eta(mid, model, {**config["primary"], "parents": 512}, 512)
        test_ids = sp["test"]
        ytest = [primary_observation(model, q[i], eta[i], noise_seed, i) for i in test_ids]
        # Keep regenerated observations and labels local-only; publish only derived compact rows.
        priv = attempt / mid / "private"; priv.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(priv / "test.npz", observed=np.asarray(ytest, dtype=np.float32),
                            q=q[test_ids], eta=eta[test_ids], parents=test_ids)
        rows = []
        out = attempt / mid
        for local, (parent, yobs) in enumerate(zip(test_ids, ytest)):
            truth = q[parent]; budget_check(run, read_json(run / "manifest.json")["started"], read_json(run / "budget.json")["gpu_training_seconds"])
            for method, starts in (("P0", [np.zeros(model.ndim)]),
                                   ("P3", [np.zeros(model.ndim), np.full(model.ndim, -0.5), np.full(model.ndim, 0.5)]),
                                   ("P5", [np.zeros(model.ndim), np.full(model.ndim, -0.5), np.full(model.ndim, 0.5), np.full(model.ndim, -0.85), np.full(model.ndim, 0.85)])):
                t0 = time.perf_counter(); fits = [fit_attempt(model, yobs, s, config) for s in starts]
                row = metric_row(model, mid, method, 0, parent, truth, min(fits, key=lambda x: x["rmse"])["q"], yobs,
                                 fits, time.perf_counter() - t0)
                rows.append(row); allrows.append(row); append_jsonl(out / "per_sample.jsonl", row)
            for arch in config["architectures"]:
                norm = np.load(run / "models" / mid / arch / "private" / "normalization.npz")
                for seed in config["training"]["seeds"]:
                    net = load_network(run, mid, arch, seed, model.ndim, len(model.grid))
                    x = torch.as_tensor(((yobs - norm["mean"]) / norm["std"])[None], dtype=torch.float32)
                    t0 = time.perf_counter()
                    with torch.no_grad():
                        guess = net(x).numpy()[0]
                    inference = time.perf_counter() - t0
                    eta_fit = ETA_NEUTRAL
                    direct_rmse = float(np.sqrt(np.mean((model.profile(guess, eta_fit) - yobs) ** 2)))
                    direct_fit = {"q": guess.tolist(), "eta": eta_fit.tolist(), "rmse": direct_rmse, "nfev": 0,
                                  "nit": 0, "success": bool(np.all(np.isfinite(guess))), "message": "direct neural q; no optimizer",
                                  "seconds": inference, "boundary_hit": bool(np.any(np.abs(guess) >= 1.0 - 1e-5))}
                    method = f"{arch}-direct"; row = metric_row(model, mid, method, seed, parent, truth, guess, yobs,
                                        [direct_fit], 0.0, inference=inference)
                    rows.append(row); allrows.append(row); append_jsonl(out / "per_sample.jsonl", row)
                    t0 = time.perf_counter(); fit = fit_attempt(model, yobs, guess, config)
                    method = f"{arch}+A"; row = metric_row(model, mid, method, seed, parent, truth, guess, yobs,
                                        [fit], time.perf_counter() - t0, inference=inference)
                    rows.append(row); allrows.append(row); append_jsonl(out / "per_sample.jsonl", row)
            if local % 10 == 0:
                append_jsonl(attempt / "events.jsonl", {"event": "primary_parent_complete", "material": mid,
                              "completed": local + 1, "total": len(test_ids), "parent": int(parent), "time": time.time()})
        metrics = summarize_issue44(rows)
        atomic(out / "metrics.json", metrics)
        old = prior[mid]["rows_data"]
        old_rows.extend([r for r in old if r["method"] == "N+A"])
    atomic(attempt / "metrics.json", summarize_issue44(allrows))
    atomic(attempt / "mlp_pr43_primary_reference.json", summarize_issue44(old_rows))
    (attempt / "test_reuse_notice.md").write_text("This is the PR43 already-opened same-generator test split, regenerated deterministically after the Issue44 architecture protocol was frozen. Results are exploratory extensions, not independent confirmation. Historical MLP N+A rows are read from PR43 unchanged; MLP-only checkpoints/predictions were unavailable and are not reconstructed.\n", encoding="utf-8")
    return allrows


def evaluate_stress(run, prior, config, materials):
    from pxrd_cross_material_autolab.stress.run import draw_parameters, render
    stress_config = read_json(ROOT / "pxrd_cross_material_autolab" / "stress" / "config.json")
    outroot = run / "stress"; outroot.mkdir(exist_ok=True)
    summaries = []
    for mid in config["materials"]:
        model = material_model(materials[mid]); q, eta, noise_seed = draw_parameters(mid, stress_config, model.ndim)
        out = outroot / mid; out.mkdir(exist_ok=True); rows = []
        for parent in range(len(q)):
            mu = render(model, q[parent], eta[parent], stress_config["lorentz_fraction"], stress_config["quadratic_background"])
            rng = np.random.default_rng(np.random.SeedSequence([noise_seed, parent]))
            y = (rng.poisson(np.maximum(mu, 0) * 15000) / 15000 + rng.normal(0, 0.002, len(mu))).astype(np.float32)
            for method, starts in (("P0", [np.zeros(model.ndim)]),
                                   ("P3", [np.zeros(model.ndim), np.full(model.ndim, -.5), np.full(model.ndim, .5)]),
                                   ("P5", [np.zeros(model.ndim), np.full(model.ndim, -.5), np.full(model.ndim, .5), np.full(model.ndim, -.85), np.full(model.ndim, .85)])):
                t0 = time.perf_counter(); fits = [fit_attempt(model, y, s, config) for s in starts]
                row = metric_row(model, mid, method, 0, parent, q[parent], min(fits, key=lambda x: x["rmse"])["q"], y,
                                 fits, time.perf_counter() - t0)
                rows.append(row); append_jsonl(out / "per_sample.jsonl", row)
            for arch in config["architectures"]:
                norm = np.load(run / "models" / mid / arch / "private" / "normalization.npz")
                for seed in config["training"]["seeds"]:
                    net = load_network(run, mid, arch, seed, model.ndim, len(model.grid))
                    x = torch.as_tensor(((y - norm["mean"]) / norm["std"])[None], dtype=torch.float32)
                    t0 = time.perf_counter()
                    with torch.no_grad(): guess = net(x).numpy()[0]
                    inf = time.perf_counter() - t0
                    direct_fit = {"q": guess.tolist(), "eta": ETA_NEUTRAL.tolist(), "rmse": float(np.sqrt(np.mean((model.profile(guess) - y) ** 2))),
                                  "nfev": 0, "nit": 0, "success": True, "message": "direct neural q; no optimizer", "seconds": inf,
                                  "boundary_hit": bool(np.any(np.abs(guess) >= 1.0 - 1e-5))}
                    row = metric_row(model, mid, f"{arch}-direct", seed, parent, q[parent], guess, y, [direct_fit], 0.0, inference=inf)
                    rows.append(row); append_jsonl(out / "per_sample.jsonl", row)
                    t0 = time.perf_counter(); fit = fit_attempt(model, y, guess, config)
                    row = metric_row(model, mid, f"{arch}+A", seed, parent, q[parent], guess, y, [fit], time.perf_counter() - t0, inference=inf)
                    rows.append(row); append_jsonl(out / "per_sample.jsonl", row)
        met = summarize_issue44(rows); atomic(out / "metrics.json", met); summaries.extend(met)
        oldpath = ROOT / "pxrd_cross_material_autolab" / "stress" / "results_20261019" / mid / "per_sample.jsonl"
        old = [json.loads(s) for s in oldpath.read_text(encoding="utf-8").splitlines() if json.loads(s)["method"] == "N+A"]
        if len(old) != len(q) * len(config["training"]["seeds"]):
            raise RuntimeError(f"PR43 stress MLP reference incomplete: {mid}")
        for r in old:
            if not np.array_equal(np.asarray(r["q_true_posthoc"]), q[int(r["parent"])]):
                raise RuntimeError(f"PR43 stress parent differs from frozen generator: {mid}/{r['parent']}")
        atomic(out / "mlp_pr43_reference.json", summarize_issue44(old))
    atomic(outroot / "metrics.json", summaries)
    (outroot / "reuse_notice.md").write_text("Same independently rendered PR43 mismatch stress parents already opened for historical MLP. No new independent confirmation; MLP results are unchanged read-only references.\n", encoding="utf-8")
    return summaries


def acquire_lock(run, resume):
    lock = run / "manager.lock"
    if lock.exists():
        old = read_json(lock)
        alive = False
        try:
            os.kill(int(old["pid"]), 0); alive = True
        except ProcessLookupError:
            pass
        except (PermissionError, ValueError, KeyError):
            alive = True
        if alive:
            raise RuntimeError(f"another Issue44 manager appears active (pid={old.get('pid')}); no concurrent run")
        if not resume:
            raise RuntimeError("stale manager lock exists; use explicit --resume for a pre-test resumable run")
        if (run / "test_opened.json").exists():
            raise RuntimeError("test-open marker exists; automatic resume/retry forbidden")
        lock.rename(run / f"manager.lock.stale.{int(time.time())}.json")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(json.dumps({"pid": os.getpid(), "host": socket.gethostname(), "started": time.time()}))


def require_completed_smoke(run, current_hashes, allow_source_patch=False):
    config = read_json(HERE / "frozen_config.json")
    smoke_path = run / "smoke" / "SMOKE.json"
    manifest_path = run / "manifest.json"
    if not smoke_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("BLOCKED: preregistered operational smoke must pass before full training")
    if (run / "test_opened.json").exists():
        raise RuntimeError("BLOCKED: test-open marker exists; full training cannot resume")
    smoke = read_json(smoke_path)
    manifest = read_json(manifest_path)
    expected = {(m, a, int(config["smoke"]["seed"])) for m in config["smoke"]["materials"]
                for a in config["smoke"]["architectures"]}
    observed = {(r["material"], r["architecture"], int(r["seed"])) for r in smoke.get("records", [])}
    if smoke.get("status") != "PASS" or smoke.get("test_observations_generated") != 0 or smoke.get("test_opened") is not False:
        raise RuntimeError("BLOCKED: operational smoke record is incomplete or opened test data")
    if smoke.get("model_runs") != len(expected) or observed != expected:
        raise RuntimeError("BLOCKED: operational smoke does not cover the frozen material/architecture matrix")
    if manifest.get("stage") not in {"SMOKE_COMPLETE_BEFORE_TEST", "FULL_MATRIX_STARTED_AFTER_SMOKE"}:
        raise RuntimeError("BLOCKED: smoke manifest is not at a pre-test stage")
    if manifest.get("hashes") != current_hashes and not allow_source_patch:
        raise RuntimeError("BLOCKED: smoke manifest stage or frozen source hashes do not match")
    return smoke


def _top_level_function_hashes(path=HERE / "benchmark.py"):
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    return {node.name: hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
            for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def verify_posttraining_manager_patch(run, manifest, current_hashes):
    """Allow a manager-only continuation fix only after every model is frozen and before test-open."""
    frozen = manifest["hashes"]
    changed = {key for key in set(frozen) | set(current_hashes) if frozen.get(key) != current_hashes.get(key)}
    if not changed:
        return False
    benchmark_key = next((k for k in frozen if k.replace(chr(92), "/") == "pxrd_issue44/benchmark.py"), None)
    if changed != {benchmark_key} or benchmark_key is None:
        raise RuntimeError("BLOCKED: source hash drift is broader than the recorded manager-only repair")
    if (run / "test_opened.json").exists() or manifest.get("stage") != "FULL_MATRIX_STARTED_AFTER_SMOKE":
        raise RuntimeError("BLOCKED: manager-only repair is allowed only after full training and before test-open")
    before_path = run / "pre_repair_code_fingerprint.json"
    repair_path = run / "posttraining_manager_continuation.json"
    if not before_path.is_file() or not repair_path.is_file():
        raise RuntimeError("BLOCKED: source-fingerprint evidence for manager-only continuation is missing")
    before = read_json(before_path)
    repair = read_json(repair_path)
    old_sha, new_sha = frozen[benchmark_key], current_hashes[benchmark_key]
    if before.get("original_benchmark_sha256") != old_sha or repair.get("source_sha256_before") != old_sha:
        raise RuntimeError("BLOCKED: prior benchmark hash does not match the frozen manifest")
    if repair.get("source_sha256_after") != new_sha or sha(HERE / "benchmark.py") != new_sha:
        raise RuntimeError("BLOCKED: post-training benchmark hash does not match continuation evidence")
    before_functions = before.get("top_level_function_sha256", {})
    after_functions = _top_level_function_hashes()
    common = set(before_functions) & set(after_functions)
    modified = {name for name in common if before_functions[name] != after_functions[name]}
    added = set(after_functions) - set(before_functions)
    removed = set(before_functions) - set(after_functions)
    if modified != {"run", "require_completed_smoke"} or added != {"_top_level_function_hashes", "verify_posttraining_manager_patch"} or removed:
        raise RuntimeError("BLOCKED: the post-training source change affects functions outside the audited manager continuation")
    if repair.get("function_hashes_after") != after_functions or repair.get("changed_functions") != sorted(modified):
        raise RuntimeError("BLOCKED: continuation function-hash evidence is incomplete")

    config = read_json(HERE / "frozen_config.json")
    expected = {(m, a, int(seed)) for m in config["materials"] for a in config["architectures"]
                for seed in config["training"]["seeds"]}
    frozen_selections = before.get("selections", [])
    observed = {(r["material"], r["architecture"], int(r["seed"])) for r in frozen_selections}
    if before.get("selection_count") != len(expected) or observed != expected or before.get("selection_checkpoint_audit_errors"):
        raise RuntimeError("BLOCKED: prior evidence does not verify a complete 42-model matrix")
    frozen_checkpoint_hashes = {(r["material"], r["architecture"], int(r["seed"])): r["checkpoint_sha256"]
                                for r in frozen_selections}
    for material, architecture, seed in expected:
        selection_path = run / "models" / material / architecture / f"selection_{seed}.json"
        selection = read_json(selection_path)
        checkpoint = selection_path.parent / "private" / f"best_{seed}.pt"
        if (selection.get("material"), selection.get("architecture"), int(selection.get("seed", -1))) != (material, architecture, seed):
            raise RuntimeError(f"BLOCKED: completed selection identity mismatch: {material}/{architecture}/{seed}")
        if selection.get("checkpoint_sha256") != frozen_checkpoint_hashes[(material, architecture, seed)]:
            raise RuntimeError(f"BLOCKED: completed selection changed after the pre-repair fingerprint: {material}/{architecture}/{seed}")
        if not checkpoint.is_file() or sha(checkpoint) != selection.get("checkpoint_sha256"):
            raise RuntimeError(f"BLOCKED: completed checkpoint hash mismatch: {material}/{architecture}/{seed}")
    return True


def preflight(output, dry_run=False):
    config = read_json(HERE / "frozen_config.json")
    prior = verify_pr43()
    gates = {}
    sources = read_json(ROOT / "pxrd_cross_material_autolab" / "config.json")
    for mid in config["materials"]:
        m = next(x for x in sources["materials"] if x["id"] == mid)
        result = gate(PowderModel(str(ROOT / m["cif_path"]), grid_size=1024))
        gates[mid] = result
        if result["status"] != "PASS" or result.get("halt_simulator"):
            raise RuntimeError(f"physics gate failed/blocked for {mid}: {result['status']}")
    process_check = {"status": "NOT_CHECKED_DRY_RUN"}
    if not dry_run:
        if not torch.cuda.is_available():
            raise RuntimeError("BLOCKED: CUDA unavailable")
        if torch.cuda.get_device_name(0) != "NVIDIA GeForce RTX 4060 Laptop GPU":
            raise RuntimeError(f"BLOCKED: unexpected CUDA device {torch.cuda.get_device_name(0)}")
        free, total = torch.cuda.mem_get_info()
        if free < 1024 ** 3:
            raise RuntimeError(f"BLOCKED: only {free / 1024**2:.0f} MiB free VRAM")
        try:
            compute_rows = gpu_compute_processes()
        except Exception as exc:
            raise RuntimeError(f"BLOCKED: could not verify active GPU compute processes: {exc!r}")
        if compute_rows:
            raise RuntimeError(f"BLOCKED: confirmed or unrecognized GPU compute processes are present: {compute_rows}")
        process_check = {"status": "PASS", "confirmed_or_unknown_compute_processes": 0,
                         "policy": "WDDM graphics processes are filtered by executable; unknown GPU processes block training"}
    output.mkdir(parents=True, exist_ok=True)
    snapshot = {"time": time.time(), "branch": os.popen("git branch --show-current").read().strip(),
                "head": os.popen("git rev-parse HEAD").read().strip(), "protocol_sha256": sha(HERE / "PREREGISTRATION.md"),
                "config_sha256": sha(HERE / "frozen_config.json"), "source_hashes": hash_inputs(),
                "pr43_status": "PASS", "pr43_materials": {m: {"rows": len(x["rows_data"]), "attempt": x["attempt"]} for m, x in prior.items()},
                "physics_gates": gates, "cuda": ({"available": torch.cuda.is_available(), "device": torch.cuda.get_device_name(0),
                  "free_bytes": int(torch.cuda.mem_get_info()[0]), "total_bytes": int(torch.cuda.mem_get_info()[1])} if torch.cuda.is_available() else {"available": False}),
                "gpu_process_check": process_check,
                "stage": "DRY_RUN" if dry_run else "PREFLIGHT_PASS"}
    atomic(output / "preflight.json", snapshot)
    return config, prior, sources, snapshot


def run(output, resume=False, smoke=False):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    acquire_lock(output, resume)
    started = time.time()
    try:
        append_jsonl(output / "events.jsonl", {"event": "manager_start", "time": started,
            "pid": os.getpid(), "host": socket.gethostname(), "mode": "smoke" if smoke else "full"})
        config, prior, source_config, snap = preflight(output, dry_run=False)
        append_jsonl(output / "events.jsonl", {"event": "preflight_pass", "time": time.time(),
            "physics_gate_status": {m: v["status"] for m, v in snap["physics_gates"].items()},
            "pr43_status": snap["pr43_status"], "cuda_device": snap["cuda"].get("device"),
            "free_vram_bytes": snap["cuda"].get("free_bytes"), "gpu_process_check": snap["gpu_process_check"]})
        if (output / "manifest.json").exists() and not resume:
            raise RuntimeError("existing manifest detected; explicit --resume is required before test-open")
        if (output / "test_opened.json").exists():
            raise RuntimeError("test-open marker already exists; no automatic retry")
        if (output / "budget.json").exists():
            started = float(read_json(output / "budget.json")["started"])
        materials = {mid: next(m for m in source_config["materials"] if m["id"] == mid) for mid in config["materials"]}
        if smoke:
            if not (output / "manifest.json").exists():
                atomic(output / "manifest.json", {"started": started, "branch": snap["branch"], "head": snap["head"],
                    "config": config, "hashes": snap["source_hashes"], "protocol_sha256": snap["protocol_sha256"],
                    "config_sha256": snap["config_sha256"], "pr43_test_relationship": config["primary"]["test_role"],
                    "stage": "GPU_SMOKE_ONLY_FROZEN_BEFORE_TEST"})
            if not (output / "budget.json").exists():
                atomic(output / "budget.json", {"started": started, "gpu_training_seconds": 0.0, "updated": started})
            elif read_json(output / "manifest.json")["hashes"] != snap["source_hashes"]:
                raise RuntimeError("source hash changed since frozen smoke manifest")
            smoke_cfg = json.loads(json.dumps(config))
            smoke_cfg["training"]["epochs"] = config["smoke"]["epochs"]
            smoke_cfg["training"]["seeds"] = [config["smoke"]["seed"]]
            sp = splits({"data": {"parents": 512, "train": 358, "validation": 77, "test": 77, "split_seed": 2026101902}})
            gpu_seconds = float(read_json(output / "budget.json")["gpu_training_seconds"])
            smoke_records = []
            for mid in config["smoke"]["materials"]:
                model = material_model(materials[mid])
                q, eta, noise_seed = draw_q_eta(mid, model, {**config["primary"], "parents": 512}, 512)
                tr_ids = sp["train"][:config["smoke"]["train_parents"]]
                va_ids = sp["validation"][:config["smoke"]["validation_parents"]]
                tr_raw = np.asarray([primary_observation(model, q[i], eta[i], noise_seed, i) for i in tr_ids], dtype=np.float32)
                va_raw = np.asarray([primary_observation(model, q[i], eta[i], noise_seed, i) for i in va_ids], dtype=np.float32)
                mean = tr_raw.mean(0); std = np.maximum(tr_raw.std(0), .02)
                for arch in config["smoke"]["architectures"]:
                    norm = output / "smoke" / "models" / mid / arch / "private" / "normalization.npz"
                    norm.parent.mkdir(parents=True, exist_ok=True); np.savez_compressed(norm, mean=mean, std=std)
                    record, gpu_seconds = tracked_train_one(output, mid, arch, config["smoke"]["seed"], model,
                        (tr_raw - mean) / std, q[tr_ids].astype(np.float32), (va_raw - mean) / std,
                        q[va_ids].astype(np.float32), smoke_cfg, started, gpu_seconds, model_prefix="smoke/models")
                    smoke_records.append(record)
            atomic(output / "smoke" / "SMOKE.json", {"status": "PASS", "time": time.time(),
                "records": smoke_records, "model_runs": len(smoke_records), "test_observations_generated": 0,
                "test_opened": False, "performance_claim": "none", "cumulative_cuda_training_seconds": gpu_seconds})
            manifest = read_json(output / "manifest.json")
            manifest["stage"] = "SMOKE_COMPLETE_BEFORE_TEST"
            atomic(output / "manifest.json", manifest)
            atomic(output / "status.json", {"status": "SMOKE_PASS_FULL_MATRIX_NOT_STARTED", "stage": "smoke_complete_pre_test",
                "time": time.time(), "test_opened": False, "smoke_models": len(smoke_records), "gpu_training_seconds": gpu_seconds})
            append_jsonl(output / "events.jsonl", {"event": "smoke_complete", "time": time.time(),
                "models": len(smoke_records), "test_opened": False, "gpu_training_seconds": gpu_seconds})
            return
        previous_manifest = read_json(output / "manifest.json") if (output / "manifest.json").exists() else None
        patch_verified = (verify_posttraining_manager_patch(output, previous_manifest, snap["source_hashes"])
                          if previous_manifest is not None else False)
        smoke_result = require_completed_smoke(output, snap["source_hashes"], allow_source_patch=patch_verified)
        append_jsonl(output / "events.jsonl", {"event": "full_matrix_start", "time": time.time(),
            "smoke_model_runs": smoke_result["model_runs"], "test_opened": False})
        if not (output / "manifest.json").exists():
            atomic(output / "manifest.json", {"started": started, "branch": snap["branch"], "head": snap["head"],
                    "config": config, "hashes": snap["source_hashes"], "protocol_sha256": snap["protocol_sha256"],
                    "config_sha256": snap["config_sha256"], "pr43_test_relationship": config["primary"]["test_role"],
                    "stress_relationship": config["stress"]["role"], "device": snap["cuda"], "stage": "FROZEN_BEFORE_NEW_TRAINING"})
        else:
            old_manifest = previous_manifest
            if old_manifest["hashes"] != snap["source_hashes"] and not patch_verified:
                raise RuntimeError("source hash changed since original pre-test manifest; resume refused")
            if patch_verified:
                repair_path = output / "posttraining_manager_continuation.json"
                old_manifest["posttraining_manager_continuation_sha256"] = sha(repair_path)
                old_manifest["posttraining_manager_continuation"] = {
                    "source_sha256_before": next(v for k, v in old_manifest["hashes"].items()
                        if k.replace(chr(92), "/") == "pxrd_issue44/benchmark.py"),
                    "source_sha256_after": snap["source_hashes"][next(k for k in snap["source_hashes"]
                        if k.replace(chr(92), "/") == "pxrd_issue44/benchmark.py")],
                    "functions_changed": ["require_completed_smoke", "run"],
                    "training_checkpoints_reverified": 42,
                    "test_opened_before_continuation": False}
                append_jsonl(output / "events.jsonl", {"event": "posttraining_manager_patch_verified",
                    "time": time.time(), "training_selections_reverified": 42, "test_opened": False,
                    "changed_functions": ["require_completed_smoke", "run"]})
            old_manifest["stage"] = "FULL_MATRIX_STARTED_AFTER_SMOKE" if (output / "smoke" / "SMOKE.json").exists() else "FULL_MATRIX_STARTED"
            atomic(output / "manifest.json", old_manifest)
        if not (output / "budget.json").exists():
            atomic(output / "budget.json", {"started": started, "gpu_training_seconds": 0.0, "updated": started})
        all_selection = []
        gpu_seconds = float(read_json(output / "budget.json")["gpu_training_seconds"])
        sp = splits({"data": {"parents": 512, "train": 358, "validation": 77, "test": 77, "split_seed": 2026101902}})
        d = config["primary"]
        for mid in config["materials"]:
            budget_check(output, started, gpu_seconds)
            m = materials[mid]; model = material_model(m)
            q, eta, noise_seed = draw_q_eta(mid, model, {**d, "parents": 512}, 512)
            tr_ids, va_ids = sp["train"], sp["validation"]
            tr_raw = np.asarray([primary_observation(model, q[i], eta[i], noise_seed, i) for i in tr_ids], dtype=np.float32)
            va_raw = np.asarray([primary_observation(model, q[i], eta[i], noise_seed, i) for i in va_ids], dtype=np.float32)
            norm_root = output / "models" / mid
            for arch in config["architectures"]:
                normfile = norm_root / arch / "private" / "normalization.npz"
                normfile.parent.mkdir(parents=True, exist_ok=True)
                if normfile.exists():
                    z = np.load(normfile); mean, std = z["mean"], z["std"]
                else:
                    mean = tr_raw.mean(0); std = np.maximum(tr_raw.std(0), 0.02)
                    np.savez_compressed(normfile, mean=mean, std=std)
                tx, vx = (tr_raw - mean) / std, (va_raw - mean) / std
                ty, vy = q[tr_ids].astype(np.float32), q[va_ids].astype(np.float32)
                for seed in config["training"]["seeds"]:
                    budget_check(output, started, gpu_seconds)
                    record, gpu_seconds = tracked_train_one(output, mid, arch, seed, model, tx, ty, vx, vy, config, started, gpu_seconds)
                    all_selection.append(record)
        atomic(output / "training_complete.json", {"time": time.time(), "models": all_selection,
                    "model_run_count": len(all_selection), "cuda_training_seconds": gpu_seconds,
                    "selection_sha256": {str((output / "models" / r["material"] / r["architecture"] / f"selection_{r['seed']}.json").relative_to(ROOT)):
                        sha(output / "models" / r["material"] / r["architecture"] / f"selection_{r['seed']}.json") for r in all_selection}})
        primary_rows = evaluate_primary(output, prior, config, materials)
        stress_rows = evaluate_stress(output, prior, config, materials)
        build_report(output, config)
        append_jsonl(output / "events.jsonl", {"event": "synthetic_matrix_complete", "time": time.time(),
            "models": len(all_selection), "primary_rows": len(primary_rows), "stress_summary_rows": len(stress_rows),
            "real_rruff": "BLOCKED"})
        atomic(output / "status.json", {"status": "PARTIAL", "synthetic_status": "COMPLETE",
                  "stage": "SYNTHETIC_PRIMARY_AND_STRESS_COMPLETE_REAL_RRUFF_BLOCKED",
                  "finished": time.time(), "elapsed_seconds": time.time() - started, "model_runs": len(all_selection),
                  "primary_rows_including_baselines_and_neural": len(primary_rows), "stress_summary_rows": len(stress_rows),
                  "materials": config["materials"], "real_rruff": "BLOCKED", "publication": "PENDING",
                  "report": "FINAL_REPORT.md", "comparison": "comparison.json"})
    except Exception as exc:
        status = {"status": "BLOCKED" if "BLOCKED:" in str(exc) else ("PARTIAL" if "PARTIAL:" in str(exc) else "FAILED"),
                  "stage": "stopped", "time": time.time(), "error": repr(exc), "traceback": traceback.format_exc()}
        append_jsonl(output / "events.jsonl", {"event": "manager_stopped", "time": time.time(),
            "status": status["status"], "error": repr(exc)})
        atomic(output / "failure.json", status)
        atomic(output / "status.json", status)
        raise
    finally:
        (output / "manager.lock").unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--smoke-only", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()
    if args.preflight_only:
        config, prior, sources, snap = preflight(args.output, dry_run=True)
        print(json.dumps({"status": "DRY_RUN_PASS", "materials": list(prior), "gates": {m: v["status"] for m, v in snap["physics_gates"].items()}, "cuda": snap["cuda"]}, indent=2))
    else:
        run(args.output, resume=args.resume, smoke=args.smoke_only)


if __name__ == "__main__":
    main()
