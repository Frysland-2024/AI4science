# Experiment 3b

**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**

Progressive disturbance 2: smooth V9 polynomial background, fixed nominal amplitude at inference.

All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.290721 ± 0.0206 |
| du MAE | 0.265562 ± 0.0358 |
| dv MAE | 0.315881 ± 0.0232 |
| Lattice a MAE (Å) | 0.011508 ± 0.000968 |
| Lattice c MAE (Å) | 0.0123206 ± 0.00142 |
| Zero-shift MAE (deg) | 0.0293466 ± 0.00131 |
| Expected-profile RMSE | 0.103564 ± 0.00534 |
| Best epoch | 30, 28, 30 |
| Recorded GPU training time (s) | 16.6998 ± 0.115 |

Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.

Raw records: `../results/study_v1/exp3b/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.
