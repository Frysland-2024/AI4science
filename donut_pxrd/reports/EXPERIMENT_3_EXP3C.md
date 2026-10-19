# Experiment 3c

**Run status: COMPLETE (three saved seeds); scientific outcome: weak parameter recovery.**

Progressive disturbance 3: Poisson plus Gaussian readout noise; texture remains off.

All metrics below are the recorded one-time frozen 77-parent test results. Mean ± sample SD is across the three seeds; no checkpoint was retrained or selected from test results.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.289391 ± 0.0375 |
| du MAE | 0.293083 ± 0.0428 |
| dv MAE | 0.2857 ± 0.0505 |
| Lattice a MAE (Å) | 0.0127977 ± 0.00175 |
| Lattice c MAE (Å) | 0.0127406 ± 0.00104 |
| Zero-shift MAE (deg) | 0.0310111 ± 0.000701 |
| Expected-profile RMSE | 0.106534 ± 0.00801 |
| Best epoch | 29, 26, 30 |
| Recorded GPU training time (s) | 16.8973 ± 0.0834 |

Poor parameter accuracy is retained as a negative outcome; low reconstruction loss is not treated as evidence of correct inversion. The run is technically complete and does not pass an accuracy claim.

Raw records: `../results/study_v1/exp3c/test_per_seed.json`, `training_curves.json`, `test_per_sample.csv`, and `data_manifest.json`.
