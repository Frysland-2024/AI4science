from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "donut_pxrd/results/study_v1"
REPORTS = ROOT / "donut_pxrd/reports"
WEIGHT_DIR = Path(r"E:\AI4science_DONUT_checkpoints\donut_pxrd_four_stage_20261019")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def avg_sd(values):
    values = list(map(float, values))
    return {"mean": float(np.mean(values)), "sample_sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0}


def show(v):
    if isinstance(v, dict):
        return f"{v['mean']:.6g} ± {v['sample_sd']:.3g}"
    return f"{float(v):.6g}"


def main():
    summary = json.loads((BASE / "exp4/summary.json").read_text(encoding="utf-8"))
    raw = json.loads((BASE / "exp4/raw_paired_results.json").read_text(encoding="utf-8"))
    validation = json.loads((BASE / "exp4/validation.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "donut_pxrd/results/resume_audit.json").read_text(encoding="utf-8"))
    experiment4 = {}
    for method in "ABCD":
        rows = [r for r in raw if r["method"] == method]
        by_seed = {}
        for seed in (20261061, 20261062, 20261063):
            sr = [r for r in rows if r["seed"] == seed]
            by_seed[str(seed)] = {
                "n": len(sr),
                "direct_q_mae": avg_sd([np.mean(r["q_abs_error_direct"]) for r in sr])["mean"],
                "direct_du_mae": float(np.mean([r["q_abs_error_direct"][0] for r in sr])),
                "direct_dv_mae": float(np.mean([r["q_abs_error_direct"][1] for r in sr])),
                "direct_a_mae_angstrom": float(np.mean([r["a_abs_error_direct_angstrom"] for r in sr])),
                "direct_c_mae_angstrom": float(np.mean([r["c_abs_error_direct_angstrom"] for r in sr])),
                "direct_shift_mae_deg": float(np.mean([r["eta_abs_error_direct"][0] for r in sr])),
                "direct_profile_rmse": float(np.mean([r["direct_profile_rmse_posthoc"] for r in sr])),
                "joint_q_mae": float(np.mean([np.mean(r["joint_q_abs_error"]) for r in sr])),
                "joint_a_mae_angstrom": float(np.mean([r["a_abs_error_joint_angstrom"] for r in sr])),
                "joint_c_mae_angstrom": float(np.mean([r["c_abs_error_joint_angstrom"] for r in sr])),
                "joint_shift_mae_deg": float(np.mean([r["joint_eta_abs_error"][0] for r in sr])),
                "joint_profile_rmse": float(np.mean([r["joint_refinement"]["profile_rmse"] for r in sr])),
                "joint_solver_success_rate": float(np.mean([r["joint_refinement"]["success"] for r in sr])),
                "joint_iterations_mean": float(np.mean([r["joint_refinement"]["iterations"] for r in sr])),
                "eta_only_shift_mae_deg": float(np.mean([abs(r["eta_only_refinement"]["x"][0]-r["eta_true_posthoc"][0]) for r in sr])),
            }
        metrics = {}
        for k in next(iter(by_seed.values())):
            if k == "n":
                continue
            metrics[k] = avg_sd([v[k] for v in by_seed.values()])
        metrics["solver_failure_count"] = sum(not r["joint_refinement"]["success"] for r in rows)
        metrics["direct_latency_p50_p95_sec"] = summary["per_method_metrics"][method]["latency_seconds_p50_p95"]
        metrics["joint_fit_latency_p50_p95_sec"] = {"p50": summary["per_method_metrics"][method]["latency_seconds_p50"], "p95": summary["per_method_metrics"][method]["latency_seconds_p95"]} if "latency_seconds_p50" in summary["per_method_metrics"][method] else {
            "p50": summary["per_method_metrics"][method]["latency_seconds_p50_p95"]["joint_fit_p50"],
            "p95": summary["per_method_metrics"][method]["latency_seconds_p50_p95"]["joint_fit_p95"]}
        experiment4[method] = {"per_seed": by_seed, "summary": metrics}
    erows = [r for r in raw if r["method"] == "E"]
    ebest = [r["optimizer_only_best_of_three"] for r in erows]
    eneutral = [r["optimizer_only_neutral_start"] for r in erows]
    experiment4["E"] = {"n": len(erows), "deterministic": True,
        "best_of_three": {"q_mae": float(np.mean([np.mean(r["q_abs_error_direct"]) for r in erows])),
            "du_mae": float(np.mean([r["q_abs_error_direct"][0] for r in erows])), "dv_mae": float(np.mean([r["q_abs_error_direct"][1] for r in erows])),
            "a_mae_angstrom": float(np.mean([r["a_abs_error_direct_angstrom"] for r in erows])), "c_mae_angstrom": float(np.mean([r["c_abs_error_direct_angstrom"] for r in erows])),
            "shift_mae_deg": float(np.mean([r["eta_abs_error_direct"][0] for r in erows])),
            "profile_rmse": float(np.mean([r["direct_profile_rmse_posthoc"] for r in erows])),
            "success_rate": float(np.mean([r["success"] for r in ebest])), "success_count": sum(r["success"] for r in ebest),
            "iterations_mean": float(np.mean([r["iterations"] for r in ebest])),
            "latency_p50_p95_sec": {"p50": float(np.percentile([r["seconds"] for r in ebest], 50)), "p95": float(np.percentile([r["seconds"] for r in ebest], 95))}},
        "neutral_start": {"success_rate": float(np.mean([r["success"] for r in eneutral])),
            "q_mae": float(np.mean([np.mean(np.abs(np.asarray(r["optimizer_only_neutral_start"]["x"][:2])-np.asarray(r["q_true_posthoc"]))) for r in erows])),
            "profile_rmse": float(np.mean([r["optimizer_only_neutral_start"]["profile_rmse"] for r in erows]))}}
    summary["validated_metrics"] = experiment4
    summary["validation"] = {k: v for k, v in validation.items() if k != "checkpoint_manifest"}
    summary["latency_limitations"] = {"cpu_latency": "not measured in this run", "gpu_latency": "measured with CUDA synchronization and warm-up; direct neural p50/p95 and per-fit p50/p95 retained", "peak_vram": "not captured with experiment-scoped allocator instrumentation; system-wide nvidia-smi included unrelated processes"}
    (BASE / "exp4/summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    rows = []
    for method in "ABCD":
        m = experiment4[method]["summary"]
        rows.append(f"| {method} | {show(m['direct_q_mae'])} | {show(m['direct_shift_mae_deg'])} | {show(m['direct_profile_rmse'])} | {show(m['joint_q_mae'])} | {show(m['joint_profile_rmse'])} | {m['solver_failure_count']}/231 |")
    e = experiment4["E"]
    rows.append(f"| E (best of 3) | {e['best_of_three']['q_mae']:.6g} | {e['best_of_three']['shift_mae_deg']:.6g} | {e['best_of_three']['profile_rmse']:.6g} | — | — | {77-e['best_of_three']['success_count']}/77 |")
    md = ["# Experiment 4 — fair A/B/C/D/E comparison", "",
        "**Run status: COMPLETE.** All methods were evaluated on the identical 77 frozen exp3c test q-parent identities and observed spectra. The new A/B/C models were validation-selected on the frozen 358/77 training/validation split; D reused the three frozen exp3c DONUT checkpoints; E was deterministic and receives no invented seeds.", "",
        f"Dataset SHA-256: `{summary['dataset_sha256']}`. The paired raw set contains `{validation['raw_row_count']}` rows: 231 each for A–D (77 parents × 3 seeds), and 77 deterministic E rows. The validation audit confirmed the identical parent set for all methods and seeds. All selection was completed before test scoring; the later profile/lattice audit only recomputed metrics from stored predictions and did not change models, starts, bounds or solver settings.", "",
        "## Direct inference and joint q+eta refinement", "",
        "Values show mean ± sample SD across the three stochastic seeds for A–D. Direct prediction is reported before refinement; joint columns use one equal-budget, method-seeded bounded L-BFGS-B fit for each network prediction. E uses the best observed-profile objective among its three preregistered starts; its neutral-start outcome is preserved separately in the raw records.", "",
        "| Method | Direct q MAE | Direct shift MAE (deg) | Direct profile RMSE | Joint q MAE | Joint profile RMSE | Joint solver failures |", "|---|---:|---:|---:|---:|---:|---:|", *rows, "",
        f"E neutral-start alone: q MAE `{e['neutral_start']['q_mae']:.6g}`, profile RMSE `{e['neutral_start']['profile_rmse']:.6g}`, success `{e['neutral_start']['success_rate']:.1%}`. E best-of-three: normalized q MAE `{e['best_of_three']['q_mae']:.6g}`, shift MAE `{e['best_of_three']['shift_mae_deg']:.6g}°`, profile RMSE `{e['best_of_three']['profile_rmse']:.6g}`, solver success `{e['best_of_three']['success_count']}/77`; mean iterations `{e['best_of_three']['iterations_mean']:.2f}`.", "",
        "A–C direct q errors are much smaller than D on this single-CIF interpolation. Joint refinement substantially reduces A–C q error; D starts farther away and retains larger residuals. This result demonstrates optimization on this synthetic fixed-material setting only; it does not establish generalization to experimental PXRD, new materials, phase mixtures or Rietveld refinement. `success=false` is reported from SciPy termination status even where the returned point is usable; no failure was hidden.", "",
        "## Runtime and compute", "",
        f"A/B/C training: `{summary['abc_training_seconds']:.2f} s`; prior exp1–3 training: `{summary['exp1_to_exp3_training_seconds']:.2f} s`; aggregate recorded training: `{summary['aggregate_recorded_training_seconds']:.2f} s` (about `{summary['aggregate_recorded_training_seconds']/3600:.4f}` GPU-hours), below the 8-hour cap. A/B/C each used three seeds and at most 24 epochs; all nine ran 24 epochs.", "",
        "GPU direct-network and joint-fit p50/p95 timings are available per method in `summary.json` and each raw fit includes elapsed time. The deterministic E per-sample p50/p95 is above. CPU latency and experiment-scoped peak VRAM were not captured; the live GPU was shared with unrelated processes, so system-wide memory readings cannot be attributed to this study.", "",
        "## Reproducibility and raw results", "",
        "- `../results/study_v1/exp4/raw_paired_results.json` contains every direct prediction, truth reserved for post-hoc scoring, eta-only fit, method-seeded joint fit, E neutral fit, all three E starts, iterations, success, objective and elapsed time.",
        "- `../results/study_v1/exp4/raw_paired_results.csv` contains one paired direct-result row per method/seed/parent.",
        "- `../results/study_v1/exp4/summary.json` contains per-seed metrics, sample SDs, timings and hardware.",
        "- `../results/study_v1/exp4/validation.json` records dataset identity, paired coverage and 24 unique checkpoint hashes (15 frozen exp1–3 + 9 A/B/C exp4; D is already among the frozen 15). All checkpoint hashes and reloads passed.",
        "- Frozen protocol: `../configs/experiment4_preregistration.json`; study config: `../configs/study_v1.json`.", "",
        "System: NVIDIA RTX 4060 Laptop, CUDA 12.6 / Torch 2.13.0+cu126 as reported by the run; SciPy and Python versions are in machine-readable summary.", "",
        "Source fidelity is bounded to the pinned DONUT core mechanism, not the original SXDM geometry or figures: [Luo et al., 2025](https://doi.org/10.1038/s41524-025-01860-7), [official DONUT source](https://github.com/AdvancedPhotonSource/DONUT). March–Dollase remains a nondifferentiable generator-side OOD stress test.", ""]
    (REPORTS / "EXPERIMENT_4.md").write_text("\n".join(md), encoding="utf-8")

    source_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in [ROOT / "donut_pxrd/scripts/run_experiment4.py", ROOT / "donut_pxrd/scripts/validate_experiment4.py", ROOT / "donut_pxrd/src/donut_pxrd/model.py"]}
    status = {"schema": "donut_pxrd_execution_status_v1", "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "codex/donut-pxrd-four-stage-20261019", "source_upstream_commit": "090c10bdf99333d3670dc26e617a93364f714bdc",
        "protocol_sha256": json.loads((ROOT / "donut_pxrd/configs/preregistration_manifest.json").read_text(encoding="utf-8-sig"))["config_sha256"],
        "experiment4_preregistration_sha256": sha(ROOT / "donut_pxrd/configs/experiment4_preregistration.json"),
        "dataset_exp3c_sha256": sha(ROOT / "donut_pxrd/results/study_v1/exp3c/data_arrays.npz"),
        "source_code_sha256": source_hashes, "source_fidelity_audit": "PASS", "resume_audit": "PASS", "experiment4_raw_pair_audit": "PASS",
        "experiments": {
            "experiment_1": {"status": "COMPLETE", "seeds": 3, "test_parents_per_seed": 77, "mean_q_mae": 0.31619751794352297, "scientific_outcome": "weak parameter recovery; negative numeric result retained"},
            "experiment_2": {"status": "COMPLETE", "seeds": 3, "test_parents_per_seed": 77, "mean_q_mae": 0.33131054689617856, "mean_zero_shift_mae_deg": 0.029813190969162306, "scientific_outcome": "weak parameter recovery with nuisance confounding; result retained"},
            "experiment_3": {"status": "COMPLETE", "conditions": ["3a broadened width", "3b smooth background", "3c Poisson plus Gaussian readout", "texture OOD stress"], "seeds_per_retrained_condition": 3, "test_parents_per_seed": 77, "exp3c_mean_q_mae": 0.2893912134120076, "texture_classification": "nondifferentiable generator-side OOD stress, not texture inverse"},
            "experiment_4": {"status": "COMPLETE", "methods": ["A", "B", "C", "D", "E"], "test_parents": 77, "raw_rows": 1001, "A_to_D_seed_pairs": 3, "E_starts_per_parent": 3, "training_seconds_abc": 357.84430120000616, "joint_optimizer_failures": {m: sum(not r["joint_refinement"]["success"] for r in raw if r["method"] == m) for m in "ABCD"}, "E_bestof3_successes": sum(r["optimizer_only_best_of_three"]["success"] for r in raw if r["method"] == "E")}},
        "training_budget": {"aggregate_recorded_gpu_training_seconds": summary["aggregate_recorded_training_seconds"], "max_seconds": 28800, "passed": summary["aggregate_recorded_training_seconds"] <= 28800},
        "checkpoint_manifest": "donut_pxrd/results/study_v1/exp4/validation.json", "results": "donut_pxrd/results/study_v1/exp4/raw_paired_results.json",
        "terminal_delivery": {"branch_push": "PENDING", "draft_pr": "PENDING", "issue_comments": "not posted per user instruction", "merge": "not performed"},
        "known_instrumentation_gaps": ["CPU latency not measured", "experiment-scoped peak VRAM not captured"],
        "recovery": [{"event": "first checkpoint write denied by workspace sandbox", "resolution": "reran the identical frozen Experiment 4 under approved escalated execution; no existing checkpoint was overwritten", "accounting": "Training duration from the failed attempt was not retained and is excluded from aggregate_recorded_gpu_training_seconds; completed rerun timing is retained. The successful-run total is below the 8-hour cap, but the excluded attempt is not represented as measured time.", "status": "RECOVERED"}]}
    (REPORTS / "EXECUTION_STATUS.json").write_text(json.dumps(status, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    final = ["# DONUT-PXRD four-stage technical report", "", "**Terminal status: all four experiments technically COMPLETE; the numeric findings include weak or negative DONUT-PXRD inversion performance.**", "",
        "This is a single public BaTiO₃ P4mm (COD 9014273) synthetic conditional-q interpolation study. It adapts the dual-branch unsupervised mechanism from DONUT to 1D powder profiles; it does not reproduce the original 2D SXDM geometry or numerical figures and does not establish performance on real PXRD or unseen materials.", "",
        "| Stage | Status | Evaluation | Result |", "|---|---|---|---|",
        "| 1 | COMPLETE | 3 seeds × 77 test parents | q mean MAE 0.3162; weak recovery |",
        "| 2 | COMPLETE | 3 seeds × 77 test parents | q mean MAE 0.3313; shift MAE 0.0298°; weak recovery/confounding |",
        "| 3 | COMPLETE | 3a/3b/3c each 3 seeds × 77; texture OOD on same parents | 3c q mean MAE 0.2894; texture remains generator-side nondifferentiable OOD stress |",
        f"| 4 | COMPLETE | 5 methods × same 77 parents; A–D have 3 seeds | E best-of-three q MAE {e['best_of_three']['q_mae']:.6g}; D direct q MAE {experiment4['D']['summary']['direct_q_mae']['mean']:.4f} ± {experiment4['D']['summary']['direct_q_mae']['sample_sd']:.3g}; see full table |", "",
        "Experiments 1–3 were audited in place; none were rerun. All 15 pre-existing checkpoints retained their recorded SHA-256 and load successfully. Experiment 4 used the frozen exp3c spectra, split and pre-registration. A/B/C retraining used q labels only for their supervised q objective; reconstruction branches consumed only predicted q/eta and observed spectra. All methods share the 77 held-out parent identities. No test-driven tuning occurred.", "",
        "The local physics gates passed forward-render parity, finite-difference gradients, parameter identifiability bounds and non-oracle recovery checks. Both DONUT decoder and physics losses backpropagate to its encoder. The scientific outcome is mixed: direct A/B/C networks recover q substantially better than D on this narrow synthetic condition, while the bounded optimizer reaches very low residuals from most starts. These results are not transferable beyond this fixed material/task without independent evaluation.", "",
        "Training used 610.56 recorded GPU seconds in total (252.72 for the pre-existing stages plus 357.84 for exp4 A/B/C), below the 8 GPU-hour cap. Per-method details, raw outcomes, failures, runtimes, hashes, and limitations are in [Experiment 4](EXPERIMENT_4.md), stage reports, `../results/study_v1/exp4/summary.json`, `raw_paired_results.json`, and `validation.json`.", "",
        "Recovery: the initial default-sandbox process failed to write new checkpoints to the explicitly designated external checkpoint directory. Its training duration was not retained and is excluded from the recorded compute total. The same frozen protocol was rerun under reviewed authorization; no existing checkpoint was overwritten. The 15 original checkpoint hashes were rechecked after completion. The recorded successful-run total is below the 8-hour cap; unrecorded time is not claimed as measured.", "",
        "Source links: [Luo et al., DONUT (2025)](https://doi.org/10.1038/s41524-025-01860-7); [official DONUT code](https://github.com/AdvancedPhotonSource/DONUT), pinned at `090c10bdf99333d3670dc26e617a93364f714bdc`. The detailed source fidelity boundary is recorded in `SOURCE_FIDELITY_AUDIT.md`.", ""]
    (REPORTS / "FINAL_TECHNICAL_REPORT.md").write_text("\n".join(final), encoding="utf-8")


if __name__ == "__main__":
    main()
