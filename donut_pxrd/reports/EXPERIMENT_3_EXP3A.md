# Experiment 3a

**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**

Progressive disturbance 1: broadened FWHM, inferred with nominal 0.12° width.

All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.296465 ± 0.0253 |
| du MAE | 0.300426 ± 0.0202 |
| dv MAE | 0.292504 ± 0.0311 |
| Lattice a MAE (Å) | 0.0127876 ± 0.00128 |
| Lattice c MAE (Å) | 0.0134165 ± 0.000222 |
| Zero-shift MAE (deg) | 0.0292866 ± 0.000298 |
| Expected-profile RMSE | 0.102059 ± 0.00388 |
| Best epoch | 29, 30, 30 |
| Recorded GPU training time (s) | 16.8726 ± 0.247 |

Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.

Raw records: `../results/study_v1/exp3a/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.
