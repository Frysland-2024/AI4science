from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "donut_pxrd/results/study_v1"
REPORTS = ROOT / "donut_pxrd/reports"


def summary(vals):
    return f"{np.mean(vals):.6g} ± {np.std(vals, ddof=1):.3g}"


def read(exp):
    return json.loads((BASE / exp / "test_per_seed.json").read_text(encoding="utf-8"))


def main():
    stages = [
        ("Experiment 1", "exp1", "Fixed shift, FWHM and simple linear background; Poisson counts; latent q=(du,dv)."),
        ("Experiment 2", "exp2", "Adds unknown zero shift to q; fixed width/background; three-dimensional local identifiability passed."),
        ("Experiment 3a", "exp3a", "Progressive disturbance 1: broadened FWHM, inferred with nominal 0.12° width."),
        ("Experiment 3b", "exp3b", "Progressive disturbance 2: smooth V9 polynomial background, fixed nominal amplitude at inference."),
        ("Experiment 3c", "exp3c", "Progressive disturbance 3: Poisson plus Gaussian readout noise; texture remains off."),
    ]
    for title, exp, condition in stages:
        rows = read(exp)
        assert len(rows) == 3 and all(r["n"] == 77 for r in rows)
        md = [f"# {title}", "", "**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**", "", condition, "",
              "All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.", "",
              "| Metric | Mean ± seed SD |", "|---|---:|",
              f"| Normalized q mean MAE | {summary([r['mean_q_mae'] for r in rows])} |",
              f"| du MAE | {summary([r['du_mae'] for r in rows])} |",
              f"| dv MAE | {summary([r['dv_mae'] for r in rows])} |",
              f"| Lattice a MAE (Å) | {summary([r['a_mae_angstrom'] for r in rows])} |",
              f"| Lattice c MAE (Å) | {summary([r['c_mae_angstrom'] for r in rows])} |",
              f"| Zero-shift MAE (deg) | {summary([r['zero_shift_mae_deg'] for r in rows])} |",
              f"| Expected-profile RMSE | {summary([r['test_profile_rmse'] for r in rows])} |",
              f"| Best epoch | {', '.join(str(r['best_epoch']) for r in rows)} |",
              f"| Recorded GPU training time (s) | {summary([r['training_seconds'] for r in rows])} |", "",
              "Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.", "",
              "Raw records: `../results/study_v1/" + exp + "/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.", ""]
        name = "EXPERIMENT_1.md" if exp == "exp1" else "EXPERIMENT_2.md" if exp == "exp2" else f"EXPERIMENT_3_{exp.upper()}.md"
        (REPORTS / name).write_text("\n".join(md), encoding="utf-8")
    tex = json.loads((BASE / "exp3_texture_ood_metrics.json").read_text(encoding="utf-8"))
    texture_rows = tex["metrics_by_seed"]
    md = ["# Experiment 3 texture OOD stress", "", "**Run status: COMPLETE as a zero-shot, generator-side texture stress test.** March–Dollase texture is nondifferentiable here and is not part of the learned five-parameter inverse model.", "",
          "The frozen texture-free Experiment 3c checkpoints were evaluated on hkl-aware March–Dollase textured spectra for the same held-out parent identities. This is an OOD sensitivity test; it is not retraining and not a differentiable texture inverse.", "",
          "| Metric | Mean ± seed SD |", "|---|---:|",
          f"| Normalized q mean MAE | {summary([r['mean_q_mae'] for r in texture_rows])} |",
          f"| du MAE | {summary([r['du_mae'] for r in texture_rows])} |",
          f"| dv MAE | {summary([r['dv_mae'] for r in texture_rows])} |",
          f"| Zero-shift MAE (deg) | {summary([r['zero_shift_mae_deg'] for r in texture_rows])} |", "",
          "Raw record: `../results/study_v1/exp3_texture_ood_metrics.json`. The result does not establish texture compensation or unknown-texture parameter recovery.", ""]
    (REPORTS / "EXPERIMENT_3_TEXTURE_OOD.md").write_text("\n".join(md), encoding="utf-8")
    ex3 = ["# Experiment 3 — progressive disturbances and orientation stress", "",
           "**Run status: COMPLETE.** q+shift remains the inference task. The trained sequence adds broadened width (3a), smooth V9 background (3b), then Poisson plus Gaussian readout noise (3c), with texture evaluated separately as a frozen-checkpoint OOD stress.", "",
           "| Condition | Change | Mean q MAE ± seed SD | Shift MAE (deg) ± seed SD | Expected-profile RMSE ± seed SD |",
           "|---|---|---:|---:|---:|"]
    for exp, label in [("exp3a", "Broadened FWHM"), ("exp3b", "V9 polynomial background"), ("exp3c", "Poisson + Gaussian readout")]:
        rows = read(exp)
        ex3.append(f"| {exp} | {label} | {summary([r['mean_q_mae'] for r in rows])} | {summary([r['zero_shift_mae_deg'] for r in rows])} | {summary([r['test_profile_rmse'] for r in rows])} |")
    ex3 += ["", "Texture is **not** part of the differentiable forward model. The hkl-aware March–Dollase condition is zero-shot, generator-side OOD stress only; see [texture report](EXPERIMENT_3_TEXTURE_OOD.md).", "",
            "All conditions use the same frozen q-parent split and 77 test parents per seed. Metrics are posthoc test summaries from saved runs; no test-driven retraining or tuning was performed.", "",
            "Detailed stage records: [3a](EXPERIMENT_3_EXP3A.md), [3b](EXPERIMENT_3_EXP3B.md), [3c](EXPERIMENT_3_EXP3C.md).", ""]
    (REPORTS / "EXPERIMENT_3.md").write_text("\n".join(ex3), encoding="utf-8")


if __name__ == "__main__":
    main()
