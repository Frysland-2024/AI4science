# Preregistration — fresh A/B/D round

**Freeze date:** 2026-10-19. This document and the adjacent `frozen_train_config.json` and `train_fresh_abd.py` were saved and hashed before the new training began.

## Question and intervention

Does explicit simulator supervision of the V9 zero-shift output reduce the held-out lattice-parameter error that co-varies with zero-shift error in the old validation data? Compare A (q supervision), B (q plus expected-profile reconstruction), and D (B plus normalized zero-shift supervision). D retains the direct reconstruction-to-q gradient. The D arm uses extra simulator information and is not an equal-information comparison.

## Frozen data, models, and compute

- Generate 512 new Sobol parent-q draws for the same public BaTiO3 P4mm CIF, with q in `[-0.8,0.8]`. Split parent draws before nuisance/noise generation into 358/77/77 train/validation/test. Use the fresh seeds and conditions in `frozen_train_config.json`; old PR26/Issue31 test records do not enter this round.
- Use paired model seeds `20261201`, `20261202`, `20261203`. A, B, and D use the same `MeasurementAwareRegressor`, including its three-coordinate nuisance head. A trains q MSE only; B trains q MSE plus `lambda * MSE(expected_observed_profile, observed_profile)`; D adds `MSE(predicted_zero_shift/0.06, simulator_zero_shift/0.06)` at fixed weight 1.0. The expected profile is formed from predicted q and eta and the configured measurement process. No clean privileged target or nuisance oracle is used at inference.
- Train at most 24 epochs per candidate using Adam, batch 16, learning rate `5e-4`, zero weight decay, gradient clipping at 5.0. Candidate lambdas are `{0.1,1.0}` for B and D, separately by condition. This is 30 candidates total and one two-hour total training-plus-validation-selection budget.
- Select best epoch by validation mean absolute normalized q error. For B and D, select lambda independently per condition by the mean of the three paired seed best-epoch validation q-MAEs; ties choose the smaller lambda. No test metric or test-derived fit enters selection.

## Test and decision rules

After every candidate completes and selection is saved, open the new test split once. Primary metrics are direct q-MAE and lattice `a/c` MAE. V9 supports the intervention only if D lowers mean q-MAE by at least 5% versus B, improves q-MAE in at least two of three paired seeds, and neither mean `a` nor `c` MAE is more than 5% worse. The mechanism check requires at least 20% lower D zero-shift RMSE than B. The simple-condition guardrail requires D mean q, `a`, and `c` errors each to be no more than 5% worse than B. If zero-shift error improves but the V9 q criterion does not, the proposed nuisance-to-q explanation is not supported.

Secondary results include coordinate-wise q errors, direct predicted-eta profile RMSE, and a q-fixed eta-only profile fit on the full test set using identical neutral initialization, bounds, objective, and 60-iteration maximum for A/B/D. Report every seed, mean, sample standard deviation, solver success, iterations, runtime, failures, and outliers. Three seeds are exploratory and do not support a significance claim.

## Stop rules and claim boundary

Stop without test evaluation if source/config/data hashes or split integrity fail, the physics/identifiability gate regresses, loss/gradients become non-finite, data leak into selection, or the full candidate set does not finish within 7200 measured training-plus-validation seconds. Keep partial artifacts and label the round `PARTIAL` or `BLOCKED`; do not retry, extend epochs, or add a new intervention. Any completed result remains a one-CIF synthetic interpolation result, not real PXRD, unseen-structure generalization, or Rietveld evidence.

## Frozen artifact hashes

See `FROZEN_SHA256SUMS.txt`. That manifest was created before training and records the exact frozen config, this protocol, the runner, and the root-cause audit used to select D.
