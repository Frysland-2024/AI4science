# Experiment 4 — fair A/B/C/D/E comparison

**Run status: COMPLETE.** All methods were evaluated on the identical 77 frozen exp3c test q-parent identities and observed spectra. The new A/B/C models were validation-selected on the frozen 358/77 training/validation split; D reused the three frozen exp3c DONUT checkpoints; E was deterministic and receives no invented seeds.

Dataset SHA-256: `52c34aaaf7a448ce76c98d617c2bf1f10855653210f95b12a23e721f527a8703`. The paired raw set contains `1001` rows: 231 each for A–D (77 parents × 3 seeds), and 77 deterministic E rows. The validation audit confirmed the identical parent set for all methods and seeds. All selection was completed before test scoring; the later profile/lattice audit only recomputed metrics from stored predictions and did not change models, starts, bounds or solver settings.

## Direct inference and joint q+eta refinement

Values show mean ± sample SD across the three stochastic seeds for A–D. Direct prediction is reported before refinement; joint columns use one equal-budget, method-seeded bounded L-BFGS-B fit for each network prediction. E uses the best observed-profile objective among its three preregistered starts; its neutral-start outcome is preserved separately in the raw records.

| Method | Direct q MAE | Direct shift MAE (deg) | Direct profile RMSE | Joint q MAE | Joint profile RMSE | Joint solver failures |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.034483 ± 0.0033 | 0.0314869 ± 0 | 0.0415578 ± 0.000863 | 0.000358746 ± 4.06e-07 | 0.00636879 ± 8.38e-11 | 12/231 |
| B | 0.0348295 ± 0.00143 | 0.0291726 ± 0.00152 | 0.0247876 ± 0.00324 | 0.000358488 ± 8.73e-07 | 0.00636879 ± 1.22e-10 | 8/231 |
| C | 0.0366986 ± 0.00137 | 0.0243897 ± 0.00599 | 0.0326302 ± 0.00476 | 0.000358623 ± 7.51e-07 | 0.00636879 ± 1.22e-10 | 19/231 |
| D | 0.289391 ± 0.0375 | 0.0310111 ± 0.000701 | 0.100171 ± 0.0089 | 0.0298001 ± 0.00542 | 0.0136025 ± 0.000932 | 8/231 |
| E (best of 3) | 0.000358565 | 0.000182194 | 0.00636879 | — | — | 6/77 |

E neutral-start alone: q MAE `0.0424607`, profile RMSE `0.014951`, success `96.1%`. E best-of-three: normalized q MAE `0.000358565`, shift MAE `0.000182194°`, profile RMSE `0.00636879`, solver success `71/77`; mean iterations `27.62`.

A–C direct q errors are much smaller than D on this single-CIF interpolation. Joint refinement substantially reduces A–C q error; D starts farther away and retains larger residuals. This result demonstrates optimization on this synthetic fixed-material setting only; it does not establish generalization to experimental PXRD, new materials, phase mixtures or Rietveld refinement. `success=false` is reported from SciPy termination status even where the returned point is usable; no failure was hidden.

## Runtime and compute

A/B/C training: `357.84 s`; prior exp1–3 training: `252.72 s`; aggregate recorded training: `610.56 s` (about `0.1696` GPU-hours), below the 8-hour cap. A/B/C each used three seeds and at most 24 epochs; all nine ran 24 epochs.

GPU direct-network and joint-fit p50/p95 timings are available per method in `summary.json` and each raw fit includes elapsed time. The deterministic E per-sample p50/p95 is above. CPU latency and experiment-scoped peak VRAM were not captured; the live GPU was shared with unrelated processes, so system-wide memory readings cannot be attributed to this study.

## Reproducibility and raw results

- `../results/study_v1/exp4/raw_paired_results.json` contains every direct prediction, truth reserved for post-hoc scoring, eta-only fit, method-seeded joint fit, E neutral fit, all three E starts, iterations, success, objective and elapsed time.
- `../results/study_v1/exp4/raw_paired_results.csv` contains one paired direct-result row per method/seed/parent.
- `../results/study_v1/exp4/summary.json` contains per-seed metrics, sample SDs, timings and hardware.
- `../results/study_v1/exp4/validation.json` records dataset identity, paired coverage and 24 unique checkpoint hashes (15 frozen exp1–3 + 9 A/B/C exp4; D is already among the frozen 15). All checkpoint hashes and reloads passed.
- Frozen protocol: `../configs/experiment4_preregistration.json`; study config: `../configs/study_v1.json`.

System: NVIDIA RTX 4060 Laptop, CUDA 12.6 / Torch 2.13.0+cu126 as reported by the run; SciPy and Python versions are in machine-readable summary.

Source fidelity is bounded to the pinned DONUT core mechanism, not the original SXDM geometry or figures: [Luo et al., 2025](https://doi.org/10.1038/s41524-025-01860-7), [official DONUT source](https://github.com/AdvancedPhotonSource/DONUT). March–Dollase remains a nondifferentiable generator-side OOD stress test.
