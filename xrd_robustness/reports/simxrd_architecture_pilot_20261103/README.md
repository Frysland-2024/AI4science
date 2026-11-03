# SimXRD / CNN11 pilot — 2026-11-03

## Summary

This post-main pilot used the existing 14,060-CIF, parent-disjoint split. It compared frozen V9 Gaussian + historical ResNet-18-GN checkpoints, V10 pseudo-Voigt/Caglioti + ResNet-18-GN, and V10 + a published no-pooling CNN11-style model. The 2026-10-26 thesis evidence and historical results remain unchanged. No 100k CIF expansion, broad tuning, or additional architecture search was run.

| Training configuration | Seeds evaluated | Simulated OOD Macro-F1, V9 Test renderer | Simulated OOD Macro-F1, V10 Test renderer | RRUFF-70 Accuracy | RRUFF-70 Macro-F1 |
|---|---:|---:|---:|---:|---:|
| Historical ResNet-18-GN + V9 | 3 frozen | 0.7060 ± 0.0115 | 0.6905 ± 0.0107 | 0.2095 ± 0.0360 | 0.1621 ± 0.0366 |
| ResNet-18-GN + V10 | 3 complete | 0.7084 ± 0.0038 | 0.7059 ± 0.0007 | 0.2524 ± 0.0218 | 0.2067 ± 0.0155 |
| CNN11-style + V10 | 1 finite pre-failure checkpoint | 0.6930 (n=1) | 0.6844 (n=1) | 0.1571 (n=1) | 0.1032 (n=1) |

Macro-F1 values for the replicated rows are mean ± sample SD across 3 training seeds. Each seed's simulated score averages 3 fixed evaluation seeds × 6 OOD profiles. For the unreplicated CNN11 checkpoint, no SD is reported. RRUFF-70 contains 70 measured patterns, balanced at 10 per crystal system, and was evaluated once after checkpoint hashes were frozen; it was not used for selection or tuning.

The matched simulator settings show effectively unchanged simulated OOD performance for the V10 ResNet (V9-trained/V9-evaluated 0.7060; V10-trained/V10-evaluated 0.7059). On RRUFF-70, the V10 ResNet point estimates are higher than the reused V9 checkpoints by 4.3 percentage points Accuracy and 4.5 points Macro-F1, but the panel and seed count are small, so these are descriptive results. CNN11 training was numerically unstable: its logged CE, JS, and total loss were NaN at step 20,000; validation OOD Macro-F1 collapsed to 0.0356 at 24,640. Its finite checkpoint from step 18,480 was retained, frozen, and evaluated as a single-seed exploratory candidate. The other two CNN11 seeds were not run; no equal-budget architecture claim is supported.

## Training cost

The V10 ResNet completed 49,280 steps per seed in 1,390–1,394 seconds (mean 1,392 seconds; about 35.4 steps/s), with 13,008,839 parameters. Maximum recorded CUDA allocation was 4.75 GB on an NVIDIA RTX 4060 Laptop GPU. CNN11 has 12,712,747 parameters; its interrupted run reached the 26,000-step log in 556 seconds (about 46.7 logged steps/s). Full-budget CNN11 time and training peak memory are unavailable; smoke-only allocated memory was 0.291 GB. Historical V9 runtime was not measured on this machine.

## Protocol and evidence

- The new renderer changes only peak profile response, using area-normalized pseudo-Voigt lines and generic, uncalibrated Caglioti-form angle-dependent width. Peak positions, reflection intensities, label mapping, same-parent paired views, JS objective, and other perturbation stages remain shared. V10 is a selective adaptation inspired by SimXRD/Pysimxrd, not an exact reproduction of its instrument pipeline.
- CNN11 adapts the published no-pooling 1D CNN architecture pattern to the current 3,501-bin input, seven logits, and CE + dynamic JS objective; it is not the paper's identical training pipeline.
- Smoke passed line area/center/width checks, paired-view checks for all seven crystal systems, CE+JS gradient checks, and device throughput/memory checks. Smoke supports implementation consistency and a plausible line-width trend, not instrument calibration.
- Test parents have already been used in the thesis; all simulated Test results here are post-main supplementary evidence. Model selection used six Validation OOD profiles and an in-range tie-break only.
- The RRUFF source files and model checkpoints are not included in this report.

## Artifacts

- [`results.json`](results.json): full per-seed, per-profile simulated Test and RRUFF metrics, confusion matrices, protocol hashes, and training-completeness status.
- [`model_selection_freeze.json`](model_selection_freeze.json): checkpoint, protocol, data, and RRUFF manifest hashes captured before evaluation.
- [`smoke.json`](smoke.json) and [`smoke.log.jsonl`](smoke.log.jsonl): physical and runtime smoke evidence.
- [`cnn11_v10_training_failure.json`](cnn11_v10_training_failure.json): failure record and finite checkpoint details.
- [`logs/`](logs/): raw JSONL training logs; [`validation/`](validation/): validation histories; [`runs/`](runs/): per-seed result records.
- `resnet18gn_v10_training_results.json` and `cnn11_v10_training_results.json`: new-model run records.
- `preflight_failures.jsonl`: two initial configuration/version-string smoke preflight errors, preserved with their corrections.

See [`docs/PXRD_SIMXRD_CNN11_PILOT_20261103.md`](../../../docs/PXRD_SIMXRD_CNN11_PILOT_20261103.md) for the decision record, sources, and detailed interpretation.
