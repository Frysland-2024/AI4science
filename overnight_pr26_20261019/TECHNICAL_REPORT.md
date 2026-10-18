# Issue #31 / PR #26 fair diagnosis and fresh A/B/C retraining

**Status:** P0–P3 research work completed; branch `codex/issue31-pr26-fair-diagnostic` pushed at commit `23f344b`. GitHub Issue comments and Draft PR creation are blocked by invalid GitHub credentials (HTTP 401); no merge was attempted. **Date:** 2026-10-19 (Asia/Shanghai).

## Result

All 12 retained PR #26 compact inference checkpoints passed SHA-256 verification, model loading, CUDA inference, and direct q-metric round-trip. The old PR #26 A/B test was then re-evaluated as a post-hoc diagnostic under identical rules. Validation evidence showed condition-specific q/reconstruction gradient conflict and strong V9 q-error/zero-shift-error coupling, so one change was preregistered before training: C detaches q only inside the reconstruction branch.

The authorized fresh synthetic BaTiO₃ round completed all 30 A/B/C candidate runs (512 parent draws maximum, three paired fresh seeds, 24 epochs each). Total measured GPU training time was **681.06 s of 7200 s**. Lambda selection used the new validation set only. The fresh test was evaluated once, after choices were frozen. The result is mixed: C improved direct q-MAE over A in simple for all three seeds, but V9 C was mixed by seed and slightly worse on mean direct q-MAE than B. After equal local q+eta refinement, A/B/C converged to nearly indistinguishable q error and profile RMSE. This does not establish that the training loss improves physical recovery.

The work covers one public BaTiO₃ P4mm CIF and synthetic conditional interpolation only. It provides no real-XRD validation, unseen-composition generalization, or Rietveld claim.

## P0: frozen PR #26 evidence audit

All 12 compact snapshots matched the manifest hashes. Their declared A/B architecture and seed/condition metadata loaded successfully; each ran on CUDA. Direct q predictions matched the frozen result records within `2e-6`; all 12 recomputed two-coordinate q-MAE values matched the frozen values within `2e-9`. The saved 77-sample test split and its NPZ index arrays agree. Data, config, CIF, split, and checkpoint hashes are in `p0_audit.json` and `original_pr26_metrics.json`.

The original three-seed means ± sample SD were:

| Condition | Method | Direct mean q-MAE | a MAE (Å) | c MAE (Å) | Original profile RMSE path |
|---|---:|---:|---:|---:|---|
| simple | A | 0.013533 ± 0.000849 | 0.000498 | 0.000699 | per-sample eta profile fit |
| simple | B | 0.013676 ± 0.001923 | 0.000525 | 0.000679 | predicted eta head |
| V9 | A | 0.032235 ± 0.001255 | 0.001571 | 0.001879 | per-sample eta profile fit |
| V9 | B | 0.030554 ± 0.002580 | 0.001452 | 0.001778 | predicted eta head |

That original observed-profile residual comparison used unequal test compute. The B head adds 771 output parameters and has no eta-label supervision. Validation-selected lambda was 0.1 for simple and 1.0 for V9. The complete original per-seed machine record is copied, unchanged in meaning, to `original_pr26_metrics.json`.

The retained checkpoints are inference-only best weights, not resumable optimizer checkpoints. Their originals, formal data, configs, V9 results, and PR #26 files were not modified.

## P1: fair post-hoc test diagnostic

All comparisons use a subset of 24 of the old 77 test indices, selected with seed `2026101901` and frozen in `p1_subset_manifest.json` before optimization. The exact same subset was used for A/B, all three seeds, and both conditions.

Three tracks are distinct in the raw files: direct model q prediction; fixed predicted q with bounded eta-only fitting initialized at the same neutral eta `(0, 0.105, 0.005)`; and bounded joint q+eta local optimization initialized at each model's predicted q and the same neutral eta. A physics-only `q=(0,0)` plus neutral eta start is also recorded per sample. All fit paths use L-BFGS-B, float64 forward evaluation, transformed observed-profile MSE, identical q/eta bounds and a 50-iteration budget. No fit reads q or eta truth; truth is used only after fitting to score errors.

| Condition | Method | Direct q-MAE | Eta-only RMSE | Eta-only scaled eta-MAE | Joint q-MAE | Joint RMSE | Solver success eta/joint |
|---|---:|---:|---:|---:|---:|---:|---:|
| simple | A | 0.012951 | 0.008581 | 0.042660 | 0.000286 | 0.005693 | 100% / 100% |
| simple | B | 0.012435 | 0.008379 | 0.041869 | 0.000296 | 0.005693 | 100% / 100% |
| V9 | A | 0.028681 | 0.012732 | 0.125392 | 0.000430 | 0.006177 | 100% / 100% |
| V9 | B | 0.027873 | 0.012045 | 0.113726 | 0.000429 | 0.006177 | 100% / 100% |

These are descriptive means over 24 test items × three seeds. After joint fitting, A and B q-MAE and residual differences are negligible at this optimization scale. The original A/B direct q inference latency over the full 77-profile batch was about 0.01–0.02 s per seed on the local GPU; timings are individually reported in `p1_direct_inference_cost.json`. Mean fit runtimes, per-seed uncertainty, every paired sample, convergence, iteration counts and worst synthetic cases are also retained in the P1 files.

## P2: validation-only cause audit and preregistration

The old validation fold only was used to inspect model predictions and loss gradients. Across five validation batches per seed, q-gradient cosines were negative in **6/30 V9 batches** and zero in all 45 simple batches; V9 seed 20261047 had negative mean q-gradient cosine. V9 `du` error versus predicted zero-shift error correlation was **0.904, 0.853 and 0.949** across seeds. These are diagnostic associations, not causal proof. Architecture, physical parameter ranges, observed-versus-clean target, max-normalization/log transform, eta mapping, nuisance-head capacity, and q/nuisance errors are audited in `validation_cause_audit.json` and `PRETRAIN_CAUSE_AUDIT.md`.

Before any new training, `frozen_retrain_config.json` was written and hashed in `pretrain_manifest.json`. C implements exactly one change: detach predicted q in the expected-profile loss path, while retaining direct q supervision and eta-path gradients. The physical-gate report already passed without threshold changes; `pytest xrd_forward_loss/tests` passed 23/23.

## P3: fresh paired A/B/C run

Fresh data use the same public CIF, new Sobol q draws, new split seed, new nuisance/noise seeds, and three new paired training seeds. Splitting happened before nuisance and noise generation. There are 358/77/77 train/validation/test q parents. The saved NPZ hash and per-array hashes are in `fresh_data/split_manifest.json`. No real data or second structure were used.

All 30 planned runs completed. A used the q-only loss; B used q supervision plus expected-profile loss; C used the preregistered detached-q profile branch. B/C lambda candidates `{0.1,1.0}` were selected on validation only. Selected values were simple B=`1.0`, C=`0.1`; V9 B=`0.1`, C=`0.1`. A/B/C share the same ResNet-18-GN stem and optimizer/training budgets; B/C each have 771 more output parameters than A. Per-run validation best epoch, parameter count, loss history and elapsed training time are in `training_runs.json`.

| Condition | Method | Direct q-MAE (mean ± seed SD) | Direct a/c MAE (Å) | Equal eta-fit RMSE | Joint-refined q-MAE | Joint RMSE |
|---|---:|---:|---:|---:|---:|---:|
| simple | A | 0.018986 ± 0.001674 | 0.000750 / 0.000849 | 0.010610 | 0.000279 | 0.005700 |
| simple | B | 0.019093 ± 0.003220 | 0.000674 / 0.000763 | 0.010680 | 0.000267 | 0.005700 |
| simple | C | 0.014692 ± 0.001822 | 0.000543 / 0.000614 | 0.009104 | 0.000275 | 0.005700 |
| V9 | A | 0.043128 ± 0.004390 | 0.001993 / 0.002534 | 0.017109 | 0.000486 | 0.006265 |
| V9 | B | 0.037117 ± 0.001958 | 0.001802 / 0.002134 | 0.015319 | 0.000419 | 0.006231 |
| V9 | C | 0.037760 ± 0.005314 | 0.001861 / 0.002147 | 0.015514 | 0.000394 | 0.006231 |

Paired direct q-MAE differences `(method − A)` were simple B `+0.000107` (mixed, 1/3 seeds worse), simple C `−0.004295` (all 3 seeds lower), V9 B `−0.006011` (2/3 lower), and V9 C `−0.005367` (2/3 lower). V9 C versus B was `+0.000644` on mean q-MAE and mixed across seeds. These are exploratory three-seed results on one CIF; no population-level inference is warranted. Joint refinement brings all methods close to a q error floor in this synthetic single-template problem, so it provides little separation between training methods.

Eta-only evaluation uses the same bounded fit for each selected A/B/C model; B/C predicted eta head errors are separate diagnostics, not substituted into this equal-cost path. Eta-only success was 97.4–100% across method/condition/seed groups; joint q+eta success was 100%. The full 1,386 sample-method-seed-condition rows include direct and refined q/a/c, observed-profile RMSE, solver outcome, iterations, runtime, boundaries, and eta truth only for post-hoc scoring in `fresh_test_per_sample.json`/`.csv`. Aggregate paired seed deltas are in `fresh_training_aggregate.json`.

## Failures, recovery, and external delivery

The first diagnostic-driver attempts stopped before recording P1 fits due to two local array-shape mistakes (eta-only input length and SciPy bounds); both were corrected before the successful run. Those failures are retained in the execution record, and no partial result was used. No gate threshold was weakened. The fresh train/test run itself had no failed candidate, exceeded no budget, and all candidates reached 24 epochs.

`gh issue view 31`, an authorized P0 milestone comment attempt, and Draft PR creation returned HTTP 401 because the configured GitHub CLI token is invalid. The isolated branch push succeeded, but the requested Issue #31 milestone comments and Draft PR could not be completed from this environment. Local evidence and all attempted/blocked delivery statuses are recorded in `execution_log.jsonl`, `execution_log.json`, and `gate_report.json`. No raw real or unpublished data are included; no model weight blobs are committed; no merge was performed.

## Reproducibility

Start with `summary.json`, `gate_report.json`, and `reproducibility_manifest.json`. Re-run `audit_and_diagnostic.py` for P0/P1, `cause_audit.py` for validation evidence, then `run_fresh_training.py` only as a complete new planned run (it creates fresh outputs and uses the frozen protocol). Local best checkpoints are private/untracked under `local_checkpoints/`; their SHA-256 ledger is `local_checkpoint_manifest.json`. The frozen task source and PR #26 records remain unmodified.
