# Experiment 2

**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**

Adds unknown zero shift to q; fixed width/background; three-dimensional local identifiability passed.

All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.331311 ± 0.0101 |
| du MAE | 0.370032 ± 0.00714 |
| dv MAE | 0.292589 ± 0.0146 |
| Lattice a MAE (Å) | 0.0155174 ± 0.00032 |
| Lattice c MAE (Å) | 0.0151092 ± 0.000619 |
| Zero-shift MAE (deg) | 0.0298132 ± 0.000754 |
| Expected-profile RMSE | 0.109659 ± 0.00128 |
| Best epoch | 30, 28, 30 |
| Recorded GPU training time (s) | 16.8722 ± 0.591 |

Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.

Raw records: `../results/study_v1/exp2/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.
