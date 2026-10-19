# Experiment 1

**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**

Fixed shift, FWHM and simple linear background; Poisson counts; latent q=(du,dv).

All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.316198 ± 0.0147 |
| du MAE | 0.339134 ± 0.0138 |
| dv MAE | 0.293261 ± 0.0157 |
| Lattice a MAE (Å) | 0.0143112 ± 0.000824 |
| Lattice c MAE (Å) | 0.0148455 ± 0.000637 |
| Zero-shift MAE (deg) | 0 ± 0 |
| Expected-profile RMSE | 0.103683 ± 0.00216 |
| Best epoch | 29, 29, 30 |
| Recorded GPU training time (s) | 16.8968 ± 0.328 |

Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.

Raw records: `../results/study_v1/exp1/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.
