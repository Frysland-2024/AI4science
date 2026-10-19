# Experiment 1 seed variability diagnostic

**Date:** 2026-10-19
**Status:** Validation-only diagnostic complete; the underlying optimization cause is not isolated.
**Study:** Frozen DONUT-PXRD Experiment 1, one COD 9014273 BaTiO₃/P4mm CIF.

## Scope and provenance

This is a post-hoc diagnostic of the three already trained Experiment 1 checkpoints. It does not change the frozen model, loss, split, seeds, metrics, or selection rule, and it runs no training. It recomputes predictions only for the original 77 validation parents. Test indices and test rows were not selected or passed to a model, and no test metric was recomputed or used for selection.

The diagnostic verified all three checkpoint SHA-256 values against `EXECUTION_STATUS.json` and verified the local dataset archive against its data manifest. The run files had moved from the historical `E:\AI4science_DONUT_checkpoints\...` path recorded in the execution log to `E:\AI4science\_local\checkpoints\donut\run_20261019_01\...`. The diagnostic used those verified files. Recomputed validation composite losses match the logged best losses within `1e-9`.

The loss is `validation_decoder_loss + 5 × validation_physics_loss`. The decoder and physics profile RMSE values below are mean per-profile RMSE on the validation split. The normalized-q MAE is the mean absolute error across both normalized lattice coordinates and all validation parents.

## Validation results by seed

| Seed | Best epoch | Train loss at selected epoch | Validation composite loss | Validation q-MAE | Validation `dv` prediction (mean ± SD) | True `dv` SD | `dv` correlation | Lattice `a/c` MAE (Å) | Physics / decoder profile RMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20261061 | 17 | 0.059202 | 0.034609 | 0.512352 | −0.7651 ± 0.0251 | 0.4587 | −0.226 | 0.004663 / 0.030315 | 0.099392 / 0.171647 |
| 20261062 | 8 | 0.069600 | 0.053063 | 0.506082 | −0.7797 ± 0.0207 | 0.4587 | −0.311 | 0.005006 / 0.029054 | 0.097752 / 0.492343 |
| 20261063 | 24 | 0.011976 | 0.009685 | 0.040336 | 0.0604 ± 0.4409 | 0.4587 | 0.989 | 0.001027 / 0.001964 | 0.029722 / 0.118057 |

On seeds 20261061 and 20261062, the `dv` latent is pinned near its lower physical bound: `dv` predictions have only `0.0251` and `0.0207` SD despite a validation target SD of `0.4587`; respectively `75.3%` and `83.1%` of normalized constrained `dv` activations have absolute value at least `0.95`. Seed 20261063 has no such saturated validation activations and tracks both coordinates closely.

The same pattern appears in the composite objective: seeds 20261061 and 20261062 have validation losses `3.57×` and `5.48×` the best-seed loss. Their training losses at the selected checkpoints are also much higher (`4.94×` and `5.81×` seed 20261063), so the histories do not show a simple validation-only overfit signature. The poor `dv` estimates align with the high physics-profile RMSE, while seed 20261062 also has a high decoder-profile RMSE.

## Finding and limits

The failure mode is now localized to **seed-associated saturation/collapse of the `dv` latent**, rather than a general inference crash or non-finite output. In the two poor runs, `du` remains correlated with its target (`r=0.963` and `0.941`), while `dv` collapses to the lower bound and has negative validation correlation. The third run learns both coordinates. This explains the large between-seed accuracy gap in this fixed-instrument experiment.

This does not identify why the two runs enter that state. The runs differ in initialization and shuffled sample order, and the recorded CUDA linear-upsampling backward operation is not bitwise deterministic. Three seeds on one CIF are insufficient to separate those causes or support a broader performance claim. No optimizer or hyperparameter changes were attempted, and the existing test split was not used for diagnosis or tuning.

To investigate causes, first preregister a bounded optimizer/initialization diagnostic using only train and validation data; any confirmatory performance claim would need a new held-out CIF-level test split. The current result remains an exploratory single-CIF finding.

## Reproduction

Run from the repository root with the experiment environment activated:

```powershell
python donut_pxrd/scripts/diagnose_experiment1_seed_variability.py
```

The generated machine-readable metrics are in [`seed_variability_diagnostic.json`](../results/experiment_1/seed_variability_diagnostic.json). The script records hashes of its inputs and performs validation-only inference from the frozen weights.
