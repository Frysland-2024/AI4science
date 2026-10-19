# Experiment 3 texture OOD stress

**Run status: COMPLETE as a zero-shot, generator-side texture stress test.** March–Dollase texture is nondifferentiable here and is not part of the learned five-parameter inverse model.

The frozen texture-free Experiment 3c checkpoints were evaluated on hkl-aware March–Dollase textured spectra for the same held-out parent identities. This is an OOD sensitivity test; it is not retraining and not a differentiable texture inverse.

| Metric | Mean ± seed SD |
|---|---:|
| Normalized q mean MAE | 0.481598 ± 0.0972 |
| du MAE | 0.583263 ± 0.0976 |
| dv MAE | 0.379933 ± 0.119 |
| Zero-shift MAE (deg) | 0.0336785 ± 0.00321 |

Raw record: `../results/study_v1/exp3_texture_ood_metrics.json`. The result does not establish texture compensation or unknown-texture parameter recovery.
