# PXRD SimXRD / CNN11 Pilot — 2026-11-03

## Decision record

**Date:** 2026-11-03  
**Question / previous assumption:** The 2026-10-23 scale-up plan called for a versioned, label-preserving simulator pilot on the existing CIF split before any 100k expansion; CNN11 was a conditional architecture comparison. The user's current request authorizes this bounded three-configuration follow-up and explicitly separates it from the thesis evidence frozen on 2026-10-26.

**New evidence and reasoning:** Source inspection of SimXRD/Pysimxrd found a physically parameterized Voigt peak renderer, grain-size-dependent broadening, and convolution with detector geometry / slit effects. The public Salgado et al. repository implements a no-pooling 1D CNN and dense predictor; the paper describes the no-pooling variant as retaining the convolutional CNN while removing pooling. These are selective references, not evidence that their complete simulator or data pipeline is transplanted.

**Decision:** Run a small, fixed-budget, post-main pilot on the existing 14,060-structure parent-disjoint CIF dataset. Compare (1) frozen V9 Gaussian + historical ResNet-18-GN checkpoints, (2) V10 pseudo-Voigt/Caglioti + ResNet-18-GN, and (3) V10 + a SimXRD / Salgado no-pooling CNN11-style model. All use the existing CE + dynamic same-parent JS objective where training occurs. No CIF expansion, broad hyperparameter sweep, or additional architecture search follows this comparison.

This explicit three-configuration request uses ResNet-18-GN as the fixed reference and does not execute the broader ResNet architecture/optimizer retuning step recorded in the earlier 2026-11-03 project sequence. That retuning/search is outside this bounded pilot; the pilot stops after this comparison.

**What changes now:** Add V10 as an opt-in renderer and a new CNN11-style model; keep the legacy Gaussian renderer and ResNet-18-GN available. New run artifacts are written under the dated pilot outputs and reports. The existing RRUFF-70 evaluation was run once after all available checkpoint hashes were frozen, using the user's explicit 2026-11-03 authorization for one-time reporting of Accuracy and Macro-F1. Test and RRUFF scores are excluded from checkpoint/model selection.

**What does NOT change:** The 2026-10-26 frozen thesis evidence, its configurations, selected checkpoints, splits, and reported results remain untouched. Existing V9 simulator behavior is the default for old call sites. The original Test split is already-used evidence and this work is labeled post-main supplementary evaluation. The historical RRUFF execution lock is not edited; its evaluation-disabled flag remains as provenance, with the current user authorization recorded in the separate pilot freeze manifest.

**Status:** COMPLETE WITH PARTIAL CNN11 TRAINING FAILURE; smoke, ResNet V10 training, checkpoint freeze, Test evaluation, and one-time RRUFF-70 evaluation completed. CNN11 training stopped after non-finite loss; its sole finite pre-failure checkpoint is reported descriptively and is not an equal-budget comparison.

**Relevant files / commits:** `docs/PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md`; `xrd_robustness/configs/simulation.simxrd_v10_pilot.20261103.json`; `xrd_robustness/configs/simxrd_cnn11_pilot.20261103.json`; `xrd_robustness/src/xrd_robustness/simulator_v10.py`; `xrd_robustness/src/xrd_robustness/models/simxrd_cnn11.py`; `xrd_robustness/scripts/run_simxrd_architecture_pilot.py`; final evidence in `xrd_robustness/reports/simxrd_architecture_pilot_20261103/`.

## Frozen protocol

- Data and split: existing `formal_14060`, with 9,842 Train / 2,109 Validation / 2,109 Test parent structures. No additional CIF records.
- New-model budget: 49,280 optimizer steps, 16 parent structures per step, AdamW at `1e-4`, weight decay `1e-4`, dynamic JS `lambda=60`; 3 fixed training seeds: `20260711`, `20260712`, `20260713`.
- Validation-only selection: mean single-factor OOD Macro-F1 on the six frozen Validation profiles; tie-break by in-range Macro-F1, then earlier step. No Test or RRUFF metrics enter selection.
- Simulated Test: post-main supplementary evaluation on the existing Test parents, across 3 fixed simulation seeds, six OOD profiles, and both V9 and V10 renderers.
- RRUFF: the existing balanced RRUFF-70 manifest and 10–80° / 0.02° / linear interpolation / zero-fill / max-normalization preprocessing. One-time Accuracy and Macro-F1 evaluation after checkpoint freeze, explicitly authorized by the current user request. No RRUFF spectra are included in public artifacts.
- Cost: report measured training time, optimizer throughput, peak allocated CUDA memory, and parameter count on the local RTX 4060 Laptop GPU. Historical training wall time is not inferred from a different machine.

## Model and simulator scope

V10 changes only peak rendering: area-normalized pseudo-Voigt profiles, with angle-dependent Caglioti-form width terms. Peak positions and reflection intensities remain supplied by the existing peak tables; the same-parent pair sampler, preferred orientation, zero-shift, background, and noise stages are retained. Coefficients are generic pilot values and are not calibrated to a particular diffractometer. The width perturbation does not change the stored crystal-system label.

The CNN11-style implementation uses three no-pooling Conv1D layers (80 channels; kernels 100/50/25; strides 5/5/2), ReLU and dropout, followed by dense widths 2300/1150 and seven output logits. It is trained with the same CE + JS routine as ResNet-18-GN. This is a PyTorch reimplementation of the published architecture pattern, not a claim of identical preprocessing, initialization, or training protocol.

## Source references

- SimXRD/Pysimxrd peak rendering: [`WPEMsim.py`](https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/utils/WPEMsim.py) and [`funs.py`](https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/utils/funs.py).
- Salgado et al. (2023), *Automated classification of big X-ray diffraction data using deep learning models*, [npj Computational Materials](https://www.nature.com/articles/s41524-023-01164-8), with the authors' [XRDs code](https://github.com/AGI-init/XRDs).

## Completion record

## Results and interpretation

The full machine-readable record is [results.json](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/results.json); the pre-Test freeze is [model_selection_freeze.json](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/model_selection_freeze.json). The historical V9 ResNet row reuses its three frozen checkpoints. ResNet+V10 completed all three new 49,280-step runs. CNN11+V10 produced one finite checkpoint selected at step 18,480. Its CE, JS, and total loss were first logged as NaN at step 20,000; subsequent logged losses remained NaN, and validation OOD Macro-F1 collapsed to 0.0356 at step 24,640. Training was stopped after the 26,000-step log. The remaining CNN11 seeds were not run; this failure is preserved in [cnn11_v10_training_failure.json](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/cnn11_v10_training_failure.json).

### Simulated OOD Test

Values are the mean of each training-seed checkpoint's mean over 3 fixed evaluation seeds × 6 single-factor OOD profiles, shown as mean ± sample SD across training seeds. Both V9 and V10 renderers were evaluated on the same existing Test parents. The directly matched generator settings are V9-trained/V9-evaluated for the historical baseline and V10-trained/V10-evaluated for the two new models.

| Configuration | Training seeds | V9 Test renderer | V10 Test renderer |
|---|---:|---:|---:|
| Historical ResNet-18-GN + V9 Gaussian | 3 frozen | 0.7060 ± 0.0115 | 0.6905 ± 0.0107 |
| ResNet-18-GN + V10 pseudo-Voigt/Caglioti | 3 complete | 0.7084 ± 0.0038 | 0.7059 ± 0.0007 |
| CNN11-style + V10 | 1 pre-failure checkpoint | 0.6930 (n=1) | 0.6844 (n=1) |

In the matched generator settings, the V10 ResNet point estimate is effectively unchanged from the V9 baseline (0.7059 vs 0.7060). On V9-rendered Test panels, the V10-trained ResNet is also similar (0.7084 ± 0.0038, see the full JSON aggregation). This pilot does not establish a simulated OOD gain from the new line profile. The CNN11 single-checkpoint scores are exploratory only: its training run was incomplete and has no seed replication.

### RRUFF-70

The panel contains 70 measured spectra, balanced at 10 per crystal system. It was evaluated once after the checkpoint freeze; it was not used for model selection or tuning.

| Configuration | Training seeds | Accuracy | Macro-F1 |
|---|---:|---:|---:|
| Historical ResNet-18-GN + V9 Gaussian | 3 frozen | 0.2095 ± 0.0360 | 0.1621 ± 0.0366 |
| ResNet-18-GN + V10 pseudo-Voigt/Caglioti | 3 complete | 0.2524 ± 0.0218 | 0.2067 ± 0.0155 |
| CNN11-style + V10 | 1 pre-failure checkpoint | 0.1571 (n=1) | 0.1032 (n=1) |

The V10 ResNet has descriptive point-estimate increases of 4.3 percentage points in Accuracy and 4.5 points in Macro-F1 versus the reused V9 checkpoints. With three seeds and this small panel, these are not significance or generalization claims. The unreplicated CNN11 checkpoint is lower and was trained for an incomplete, numerically unstable run.

### Training cost and smoke

On the NVIDIA RTX 4060 Laptop GPU, each V10 ResNet seed completed 49,280 steps in 1,390–1,394 seconds (mean 1,392 seconds; about 35.4 steps/s); the maximum recorded allocated CUDA memory was 4.75 GB. ResNet has 13,008,839 parameters. The CNN11 run reached the 26,000-step log in 556 seconds (about 46.7 logged steps/s) before stopping, with 12,712,747 parameters; a full-budget runtime and training peak memory are unavailable. Smoke-only CNN11 allocated 0.291 GB. Historical V9 wall time was not measured on this machine and is not compared.

Smoke checks passed for finite nonnegative views, preserved peak center, integrated line-area conservation, angle-dependent width, deterministic and distinct same-parent paired views across all seven labels, CE+JS gradients, and device memory/throughput. At 20° the measured V10 FWHM was 0.08067°; at 80° it was 0.08707°. This validates implementation consistency and a physically plausible trend, not calibration to a real instrument.

### Boundaries

The 2026-10-26 thesis evidence and historical V9 configurations, checkpoints, splits, and reports are unchanged. This Test split was already used in the thesis, so these metrics are post-main supplementary evidence. No 100k CIF expansion, broad tuning, or architecture search followed. The bounded pilot uses ResNet-18-GN as a fixed reference and does not include the broader ResNet retuning step described in the earlier 2026-11-03 project sequence. See the preserved [raw training logs](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/logs/), [validation histories](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/validation/), and [smoke record](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/smoke.json).
