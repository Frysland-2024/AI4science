# Experiment 3 — progressive disturbances and orientation stress

**Run status: COMPLETE.** q+shift remains the inference task. The trained sequence adds broadened width (3a), smooth V9 background (3b), then Poisson plus Gaussian readout noise (3c), with texture evaluated separately as a frozen-checkpoint OOD stress.

| Condition | Change | Mean q MAE ± seed SD | Shift MAE (deg) ± seed SD | Expected-profile RMSE ± seed SD |
|---|---|---:|---:|---:|
| exp3a | Broadened FWHM | 0.296465 ± 0.0253 | 0.0292866 ± 0.000298 | 0.102059 ± 0.00388 |
| exp3b | V9 polynomial background | 0.290721 ± 0.0206 | 0.0293466 ± 0.00131 | 0.103564 ± 0.00534 |
| exp3c | Poisson + Gaussian readout | 0.289391 ± 0.0375 | 0.0310111 ± 0.000701 | 0.106534 ± 0.00801 |

Texture is **not** part of the differentiable forward model. The hkl-aware March–Dollase condition is zero-shot, generator-side OOD stress only; see [texture report](EXPERIMENT_3_TEXTURE_OOD.md).

All conditions use the same frozen q-parent split and 77 test parents per seed. Metrics are posthoc test summaries from saved runs; no test-driven retraining or tuning was performed.

Detailed stage records: [3a](EXPERIMENT_3_EXP3A.md), [3b](EXPERIMENT_3_EXP3B.md), [3c](EXPERIMENT_3_EXP3C.md).
