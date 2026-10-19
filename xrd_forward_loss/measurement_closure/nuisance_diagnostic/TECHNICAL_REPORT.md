# Issue #19 nuisance diagnostic — 2026-10-18

## Status

**COMPLETED with one recorded non-converged profile fit.** This is an exploratory post-hoc diagnostic on the previously evaluated Issue #19 test set, not a new blind confirmatory test. A and B q predictions, model weights, split, selected epochs, and validation-selected lambda values were frozen.

## Question and controlled comparison

The prior P3 table compared A's fixed-q, test-time eta profile fit against B's direct nuisance-head eta. That was an unequal inference path. This diagnostic fixes each model's existing q prediction, then gives both A and B the same independent eta profile fit. It separately evaluates B's native eta head and, at the same fixed q_B, the reduction after shared eta fitting.

The 12 retained inference-only FP32 checkpoints were verified against the original manifest by identity, byte count, and SHA-256, then loaded as frozen inference states. No retraining, optimizer-state recovery, data generation, q refit, lambda/epoch reselection, or output reuse from any alternate model occurred. Every runtime q prediction (and B native eta) matched the saved P3 prediction arrays within `2e-6` absolute tolerance.

The solver uses the existing P3 renderer and the same transformed profile loss for both networks: mean squared error between `expected_profile` and observed inputs in the max-normalized `log1p(100*x)/log(101)` domain. At each fixed q it performs one L-BFGS-B fit from scaled eta `[0,0,0]`, with each scaled coordinate bounded to `[-0.999,0.999]`; options are `maxiter=80`, `ftol=1e-10`, `gtol=1e-7`, and `maxls=25`. The physical nuisance coordinates are zero shift in degrees 2θ, FWHM in degrees, and background amplitude relative to the reference clean peak height. Both A and B call the same routine, use no B eta warm start, and use no truth values for fitting or fit-setting selection.

`q_true` and `eta_true` are accessed only after prediction to score q/lattice errors, nuisance mismatch, and descriptive correlations. No oracle fit is included. The solver is a post-hoc test-time optimizer, not B's learned nuisance head. Its additional inference cost affects deployment significance.

## Frozen scope and provenance

- BaTiO₃ P4mm, COD 9014273; one known structure and synthetic measurements only.
- Conditions: `simple` and `v9`.
- Seeds: 20261045, 20261046, 20261047; 77 frozen test q indices per condition and seed.
- Prior selected lambda: simple `0.1`, V9 `1.0`; selected epoch/checkpoint identities are unchanged.
- Source commit: `e261faadbc2fba88b2f2289e7900d237a733345a`.
- Device: NVIDIA GeForce RTX 4060 Laptop GPU, CUDA 12.6, PyTorch 2.13.0+cu126, Python 3.11.9.
- Full diagnostic runtime: `127.68 s`; the observed shared-fit runtime and GPU-event time are recorded per model run. The full pass made 924 shared fits, at batch size 16 for inference and one profile at a time for eta optimization.

Input asset and checkpoint hashes, commands, return codes, environment, selected model hash per run, and artifact hashes are in [`run_manifest.json`](results/20261018/run_manifest.json). Compact metrics are in [`metrics.json`](results/20261018/metrics.json). Per-example fit records are retained locally as an ignored compressed file and are not part of the Git delivery.

## Results

Values below are mean ± sample SD across the three seed-level estimates. q MAE is the mean of absolute error across normalized `du,dv`. Profile RMSE is over all observed transformed profile points. `A/B shared fit` uses the same fixed-q eta solver for each model.

| Condition | Model | q MAE | a MAE (Å) | c MAE (Å) | Shared-fit profile RMSE |
|---|---|---:|---:|---:|---:|
| simple | A | 0.013533 ± 0.000849 | 0.000498 ± 0.000066 | 0.000699 ± 0.000022 | 0.009456 ± 0.000016 |
| simple | B | 0.013676 ± 0.001923 | 0.000525 ± 0.000110 | 0.000679 ± 0.000028 | 0.009415 ± 0.000491 |
| V9 | A | 0.032235 ± 0.001255 | 0.001571 ± 0.000301 | 0.001879 ± 0.000098 | 0.016034 ± 0.000795 |
| V9 | B | 0.030554 ± 0.002580 | 0.001452 ± 0.000187 | 0.001778 ± 0.000136 | 0.015621 ± 0.000655 |

The paired seed-level B−A shared-fit RMSE differences are `−0.0000406 ± 0.0004765` for simple and `−0.0004132 ± 0.0012680` for V9. The individual seed directions are mixed in both conditions (simple: one positive, two negative; V9: one positive, two negative). The mean B residual is slightly lower, but the paired differences are small relative to seed variation and do not establish a stable A/B spectral advantage.

For B's native nuisance head, the observed-profile RMSE is `0.015885 ± 0.001492` (simple) and `0.027332 ± 0.001431` (V9). At the identical fixed q_B, shared eta fitting reduces those residuals by `0.006470 ± 0.001435` and `0.011711 ± 0.001283`, respectively. This isolates a substantial nuisance-head/estimator gap at fixed q. It does not imply that A's weights or q predictions caused the profile difference.

Native B eta errors, in physical units, are:

| Condition | zero-shift bias (°) | zero-shift RMSE (°) | FWHM RMSE (°) | background-amplitude RMSE |
|---|---:|---:|---:|---:|
| simple | −0.000321 ± 0.000302 | 0.003355 ± 0.001845 | 0.002803 ± 0.000184 | 0.000206 ± 0.000029 |
| V9 | +0.005290 ± 0.007080 | 0.032117 ± 0.004448 | 0.006068 ± 0.000124 | 0.000901 ± 0.000005 |

The V9 native-head zero-shift mismatch remains visible. Correlations between per-example q error and eta mismatch are included in the machine results as descriptive statistics only; they are not causal analyses.

## Solver cost and failures

Each model/condition/seed run made 77 independent fits. Average function evaluations and iterations per profile were:

| Condition | Model | nfev/profile | nit/profile | Fit failure rate | Any-boundary hit rate |
|---|---|---:|---:|---:|---:|
| simple | A | 11.60 | 8.59 | 0/231 | 46.75% |
| simple | B | 11.30 | 8.47 | 0/231 | 48.92% |
| V9 | A | 12.70 | 9.00 | 0/231 | 6.49% |
| V9 | B | 13.17 | 8.99 | 1/231 | 3.03% |

The single failed fit is V9/B/seed 20261046, global test index 435. L-BFGS-B returned status 2 (`ABNORMAL:`) after 59 function evaluations and 8 iterations. The returned eta/profile score is retained in the full aggregate; the sample was not removed or retried. Overall, 923 of 924 fits returned success. Per-run CPU wallclock, CUDA-event time, nfev, nit, success, and boundary-hit details are preserved in `metrics.json`; deployment inference and profile-fit cost are listed separately.

## Interpretation and limits

The old headline residual comparison used different evaluation paths and should not be read as a fair B-versus-A spectral comparison. Under a common profile solver, the two models are close on this one-template synthetic test, with seed-variable, small mean differences. B's direct nuisance head still has a notable V9 zero-shift mismatch, and the same-q profile fit closes much of the residual gap. Since q is fixed separately at each model's prediction, the shared-fit residual comparison can still reflect differences in those frozen q predictions; it does not identify a causal effect on the q weights.

These results are limited to one BaTiO₃ template and synthetic measurement conditions. They establish no real-domain performance, unseen-structure generalization, instrument calibration, mixed-phase robustness, or Rietveld refinement result. The diagnostic does not alter the project's primary classification framing or frozen JS classification evidence.

## Validation

- Read-only smoke: 2 examples per condition and method, seed 20261045; all 12 checkpoint hashes and inference-state loads passed, q/native eta matched P3, the shared solver reproduced old A fits, and repeated fits/predictions were deterministic.
- Offline tests: `8 passed` (test command and final return code are in the run manifest).
- Python compilation, 119-character source-line check, and `git diff --check` passed.
