# DONUT-PXRD final technical report

**Overall status:** COMPLETE
**Branch:** `codex/donut-pxrd-experiment-20261019`
**Frozen study config SHA-256:** `cfd0936999d298d860eb8c01eddfc8aaa5bd6172c53a9a95d8aaffc4e9050597`
**Source:** DONUT paper DOI `10.1038/s41524-025-01860-7`; official code commit `090c10bdf99333d3670dc26e617a93364f714bdc`
**Data:** one COD 9014273 BaTiO3 P4mm CIF; train/validation/test `{'train': 358, 'validation': 77, 'test': 77}`
**Measured neural training time:** 2671.169 seconds

| Experiment | Status | Main numerical outcome |
|---|---|---|
| 1 | COMPLETE | fixed: q-MAE=0.344228 |
| 2 | COMPLETE | q_and_shift: q-MAE=0.398342 |
| 3 | COMPLETE | experiment_3_width: q-MAE=0.457009; experiment_3_background: q-MAE=0.139752; experiment_3_noise: q-MAE=0.228037; experiment_3_texture: q-MAE=0.291768 |
| 4 | COMPLETE | A q-MAE=0.0336069; B q-MAE=0.0335781; C q-MAE=0.0342816; DONUT q-MAE=0.228037 |

## Frozen protocol and detailed results

The 512 parent parameter draws were split before nuisance/noise generation into train/validation/test = 358/77/77. The three fixed model seeds were 20261061, 20261062, and 20261063. The test-index SHA-256 is `12c5fd101e7b5f6aa0003626b7754028bf5fd0dc112b8a2c808a634ea945911f`. Checkpoint and A/B/C lambda choices used validation only; test values were used for post-selection scoring. Each condition's trained model scores 77 test parents per seed (231 rows total).

| Condition | q-MAE mean ± seed SD | Failure rate | Inference p50 |
|---|---:|---:|---:|
| Exp. 1: fixed instrument | 0.344228 ± 0.260143 | 0% | 2.67 ms |
| Exp. 2: lattice + zero shift | 0.398342 ± 0.297712 | 0% | 2.92 ms |
| Exp. 3: peak width | 0.457009 ± 0.058123 | 0% | 3.25 ms |
| Exp. 3: width + background | 0.139752 ± 0.136350 | 0% | 3.62 ms |
| Exp. 3: width + background + noise | 0.228037 ± 0.282538 | 0% | 10.07 ms |
| Exp. 3: texture OOD stress | 0.291768 ± 0.231867 | 0% | 12.64 ms |

Experiment 2 local identifiability used a 3501×3 Jacobian: rank 3, condition number 26.663, and absolute cosine 0.924875 between the `du` and zero-shift columns. This indicates substantial local parameter coupling. On 77 test parents, freeing zero shift in L-BFGS-B changed q-MAE from 0.130324 to 0.102435, zero-shift MAE from 0.029816° to 0.012609°, and profile RMSE from 0.036674 to 0.019542; both fits had 100% solver success.

### Experiment 4: direct model inference

The same noisy held-out profiles were scored for all four methods. B and C selected `lambda=0.1` from validation; A uses `lambda=0`. q-MAE is the mean over the 231 sample-seed rows, with SD across seed-level means.

| Method | q-MAE mean ± seed SD | p50 / p95 inference | Failure rate |
|---|---:|---:|---:|
| A | 0.033607 ± 0.003682 | 6.62 / 12.08 ms | 0% |
| B | 0.033578 ± 0.004823 | 29.50 / 47.31 ms | 0% |
| C | 0.034282 ± 0.002875 | 22.34 / 36.17 ms | 0% |
| DONUT | 0.228037 ± 0.282538 | 10.07 / 14.92 ms | 0% |

### Experiment 4: equal-budget joint q + instrument refinement

Each method's direct prediction initialized the same bounded L-BFGS-B objective and iteration budget; failure rate was 0% for all methods. Values are over 231 sample-seed fits.

| Initialization | q-MAE | Profile RMSE | p50 / p95 per fit | Failure rate |
|---|---:|---:|---:|---:|
| A | 0.000343 | 0.005662 | 0.231 / 0.779 s | 0% |
| B | 0.000350 | 0.005663 | 0.667 / 0.888 s | 0% |
| C | 0.000341 | 0.005662 | 0.602 / 0.913 s | 0% |
| DONUT | 0.080026 | 0.015463 | 0.565 / 1.133 s | 0% |

Neutral-start L-BFGS-B on 77 test parents had q-MAE `0.050608`, profile RMSE `0.015760`, p50/p95 runtime `0.385/0.546 s`, mean 26.57 iterations, and 0% failures. A/B/C baseline candidate training consumed `1031.916 s` GPU time; DONUT training across experiments 1–3 consumed `1639.252 s`; total measured neural training was `2671.169 s`. The local run retained 30 checkpoint files (DONUT stages and all A/B/C candidate runs); their paths and SHA-256 values are recorded in the training records and execution status. Model weights and generated arrays are local-only under `E:\AI4science_DONUT_checkpoints\run_20261019_01` and are not included in Git.

The execution log records repaired setup/evaluation failures, including the stale decoder optimizer reference and texture test-order indexing error. Neither repair changed frozen metrics, splits, or thresholds. The preflight regression gate passed 50 tests; each post-experiment gate passed 3 tests. CUDA's native linear 1D upsample backward has no deterministic implementation, so deterministic mode was warn-only; fixed seeds do not imply bitwise-identical reruns.

## Interpretation boundary

DONUT-PXRD adapts the original 2D nanobeam SXDM dual-branch training principle to one-dimensional synthetic powder patterns. Values are conditional to one known single-phase tetragonal CIF and the frozen synthetic generator. They do not establish performance on real measurements, unknown structures, multiple phases, or general PXRD inversion.

See each `EXPERIMENT_n.md`, raw per-sample CSV, full JSON histories, `EXECUTION_STATUS.json`, source fidelity audit, and external local-only checkpoint/data manifests for exact evidence.
