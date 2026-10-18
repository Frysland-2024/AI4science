# Pretraining cause audit and preregistration

**Date:** 2026-10-19. **Status:** completed before fresh training.

## Gate evidence

The 12 retained inference-only checkpoints passed manifest SHA-256 checks, architecture loading, and GPU inference. Recomputed held-out q MAE matched the frozen `ab_results.json` values within `2e-9`; formal data, split arrays, source config, and CIF provenance were cross-checked. The original P1/P2 physics gate report is PASS and all 23 `xrd_forward_loss/tests` tests pass. The compact snapshots are not resumable training checkpoints; they were used only for inference and validation diagnostics.

The old PR #26 test is already-open exploratory data. It was used only for the post-hoc fair inference diagnostic in this report. All new method choices below use the old validation split, and all retraining uses a newly generated independent synthetic q split.

## Fair old-test diagnostic

The diagnostic froze 24 of the 77 original test indices with seed `2026101901`, before any optimization. Both methods, all three seeds and both conditions use exactly these same indices. Direct q predictions are one pass. The bounded profile fits share L-BFGS-B, float64 forward, transformed-profile MSE, q/eta bounds, a neutral nuisance start `(0, 0.105, 0.005)`, 50 maximum iterations, and the same tolerances.

`p1_summary.json` contains method/condition means and costs; `p1_per_sample.csv` and `.json` contain the paired records. The fixed-q nuisance fit begins from the same neutral eta for A and B. The joint fit begins at each model's own q prediction plus that neutral eta. A physics-only `(q=0, neutral eta)` start is included per test item. These test fits are post-hoc diagnostics, not training choices.

The old raw residual comparison had unequal compute: PR26's A path ran a nuisance profile optimization, while B used a predicted nuisance head. The equal-budget matched fit reduces that asymmetry; it still measures local single-CIF profile optimization, not Rietveld refinement. See `p1_summary.json` for actual equal-rule outcomes and runtime.

## Validation-only root-cause evidence

The validation audit used the three retained seeds and five batches per condition/seed. V9 had negative cosine between `grad_q(L_param)` and `grad_q(L_recon)` in 6/30 batches; seed 20261047 had a negative mean q-gradient cosine. Simple had no negative q-gradient cosine across 45 batches. Shared-trunk gradient cosines and reconstruction-to-parameter gradient norm ratios are retained in `validation_cause_audit.json`; the result shows condition-dependent interference rather than a universal conflict.

V9 B validation `du` error and zero-shift error had Pearson correlations `0.904`, `0.853`, and `0.949` for the three seeds. This is an error-coupling diagnostic, not proof that one parameter causally substitutes for the other. Local Jacobian evidence from the frozen physical gate remains below its preregistered condition/correlation limits. Architecture audit: the ResNet-18-GN trunks are shared, B has 771 additional output parameters for three unsupervised nuisance outputs, and both methods receive observed max-normalized `log1p_100` spectra. Reconstruction targets a deterministic expected transformed profile; it does not fit an individual noise realization or use clean-profile labels. `eta_true` is excluded from model inputs, training losses, and validation selection.

## One frozen change

The single C intervention is **detach predicted q inside the reconstruction branch only**. C retains direct q supervision and the differentiable nuisance-head reconstruction path. This tests whether q-directed reconstruction gradients contribute to the V9 q/zero-shift error coupling, given the observed negative q-gradient batches. It is not claimed to fix nuisance identifiability, and no expected gain is assumed.

The complete machine-readable protocol is `frozen_retrain_config.json`; its SHA-256 is recorded in `pretrain_manifest.json` before training starts. It fixes one fresh 512-parent dataset, three paired fresh seeds, two conditions, A/B/C, at most 24 epochs, two validation-only lambda candidates for B/C, one fresh test evaluation after selection, and a 7200-second measured GPU-training ceiling. No real spectrum or additional structure is included.

## Other candidate causes and limits

Nuisance-head capacity alone is not established as the cause: B adds only 771 output parameters and no eta labels. Validation correlation and gradient data support a targeted gradient-routing diagnostic, while training-target mismatch remains a distinct possibility because the deterministic expected spectrum cannot encode a sampled detector-noise realization. Physics mismatch is limited to one known CIF and frozen nuisance parameterization. Preprocessing is shared by A/B/C. The one-CIF interpolation and old-test reuse prevent confirmatory or broad claims.

## Historical protocol distinction

The historical `run_ab.py` at commit `e6b08aa` (PR #21-era protocol) is not comparable replication: it used five nuisance outputs with synthetic nuisance labels, and a deterministic clean expected target; the present PR #26 B uses three nuisance outputs without nuisance labels and an observed-profile expected target with a stochastic observation process. It also differs in split/selection protocol and output-head capacity. The old profile-RMSE comparison further gave A a per-sample fit while B used a head prediction.
