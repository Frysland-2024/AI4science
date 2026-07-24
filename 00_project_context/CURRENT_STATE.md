# AI4science Current State

**Canonical status date:** 2026-07-24  
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> This file records the current state only. Historical and abandoned directions remain in `PROJECT_JOURNEY.md`, archived design documents, and dated decision records.

## 1. Current research identity

The active project is **V9-T: Algorithm Transfer for PXRD Robustness**.

It is a bridge from materials-centered ML toward ML-centered scientific research. The paper asks whether different learning principles—not merely more simulated spectra—produce more robust and more transferable representations under controlled PXRD measurement-domain shift.

The paper scope is now:

> **controlled simulated pretraining, zero-shot experimental robustness, and label-efficient real-domain adaptation for PXRD crystal-system classification.**

It does not claim a new general-purpose ML theory.

## 2. Core method comparison

Under matched mother structures, perturbation views, architecture, optimizer budget and simulation evaluation panels, compare:

1. `ordinary_dynamic_augmentation`: Dynamic/Paired ERM;
2. `js_consistency_transfer`: JS Consistency;
3. `residual_decorrelation_transfer`: Residual Class Decorrelation.

The common paired-view flow is:

```text
same mother structure and same dynamic pair
├── Dynamic/Paired ERM: classification only
├── JS Consistency: classification + prediction consistency
└── Residual Decorrelation: classification + residual class decorrelation
```

Near-clean ERM and frozen offline physical augmentation remain reference baselines. Dynamic augmentation is not claimed as the innovation.

## 3. Frozen simulation data contract

Total unique Materials Project structures: **14,060**.

| Split | Structures | Role |
|---|---:|---|
| Train | 9,842 | training and dynamic view generation |
| Validation | 2,109 | lambda selection, early stopping, checkpoint selection, simulation development comparison |
| Test | 2,109 | locked final simulated evaluation |

Rules:

- split at unique structure/family level;
- all derived views inherit the mother-structure split;
- Validation and Test never enter the training view generator;
- all methods share the same mother structures and matched pair schedule.

Each structure has a complete ideal-reflection cache containing peak position, integrated intensity, hkl, multiplicity, reciprocal vector and reflection-to-peak mapping.

## 4. Frozen simulation perturbation family

The active training distribution contains:

- global zero shift: Uniform `[-0.2°, 0.2°]`, activation probability `0.5`;
- FWHM: Uniform `[0.08°, 0.20°]`, activation probability `1.0`;
- smooth third-order polynomial background, ratio Uniform `[0, 0.02]`, activation probability `0.5`;
- Poisson count scale: Log-uniform `[2500, 40000]`;
- electronic-noise standard deviation: Uniform `[0, 2]` counts;
- March–Dollase parameter: Uniform `[0.8, 1.0]`, activation probability `0.7`.

Activation probabilities describe training coverage, not empirical instrument frequencies.

## 5. Method-parameter governance

The one permitted pre-Validation range revision has been consumed and the candidate ranges are frozen:

```text
lambda_JS  ∈ {0.3, 3.0, 30.0}
lambda_res ∈ {0.2, 2.0, 20.0}
```

The decisive Train-only candidate Gate directly measured weighted auxiliary and combined backbone gradients on a rebuilt learned state. Median weighted auxiliary/classification ratios were:

- JS: `0.02283 / 0.22842 / 2.28533`;
- Residual: `0.02581 / 0.25854 / 2.58715`.

The ranges cover weak, material non-dominant and dominant influence. This does not authorize tuning.

## 6. Simulation experiment state

- lambda tuning: **0/7**;
- seven tuning runs: planned, not started;
- tuning execution switches: false;
- active training process: none;
- active authoritative checkpoint: none;
- formal five-method, three-seed comparison: **0/15**;
- simulated Test: locked, not authorized, not started;
- previous laptop training products: non-authoritative and must not be resumed;
- formal desktop execution must start from optimizer step 0 after engineering acceptance and explicit authorization.

## 7. Completed engineering evidence

The following gates are closed:

- dynamic parameter rows remain batch/prefetch bounded;
- maximum parameter rows per batch: 32;
- maximum live rows under the registered prefetch window: 256;
- Dynamic ERM, JS and Residual share the same sampler, pair schedule and parameter-pair hashes;
- the same dynamic coordinate deterministically replays the same parameters;
- Train/Validation/Test exclusion gates pass;
- checkpoint resume audit passes 12/12 checks on the real reflection cache and CUDA;
- method semantic audit passes 22/22 checks;
- learned-state classification and residual-probe gates pass at epochs 3 and 5;
- candidate-grid legality Gate passes for all six registered lambda values.

The remaining blockers before 7-run execution are target-desktop acceptance and a separate explicit user authorization.

## 8. New real-domain research axis

The old design restricted real spectra to a pure zero-shot final test. Before any formal model accessed RRUFF-70, the user approved a stronger transfer-learning question:

> When Dynamic ERM, JS and Residual receive the same limited labeled real data and the same adaptation protocol, do JS or Residual retain a relative advantage and require fewer real labels?

The paper now reports both:

- **0-shot real robustness**;
- **1/2/3-shot real-domain adaptation efficiency**.

Absolute real-domain accuracy may improve after adaptation. The controlled comparison remains the relative difference between the three simulation-pretrained methods.

Decision record:

- `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`

## 9. Frozen RRUFF-70 source corpus

Dataset identity: `rruff-real-pxrd-70-v1.0-final`.

- 70 measured mineral powder PXRD profiles;
- seven crystal systems;
- 10 samples per crystal system;
- source manifest SHA-256:
  `17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5`;
- no model prediction was used for dataset selection;
- preprocessing: 10–80°, 0.02°, linear interpolation, zero fill, max normalization, no smoothing, no baseline subtraction, no manual peak editing.

The corpus measures simulation-to-experiment measurement-domain transfer. It is not claimed as a strict unseen-structure benchmark or a quantitative phase-purity benchmark.

## 10. Frozen RRUFF real-domain roles

Role assignment occurred before model access using:

```text
SHA256(20260724 | crystal_system | sample_id)
```

| Role | Per class | Total |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

Frozen local manifests:

- `data/real_xrd/rruff70/manifests/rruff70_real_adaptation_split_v1.csv`
  - SHA-256 `32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455`
- `data/real_xrd/rruff70/manifests/rruff70_fewshot_episode_manifest_v1.csv`
  - SHA-256 `B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6`

These files and spectra are local Git-ignored data and must not be committed.

## 11. Few-shot episode design

Within each class, the three adaptation-train samples receive frozen ranks 1/2/3.

- 0-shot: no real training data;
- 1-shot: three episodes using rank 1, rank 2 or rank 3;
- 2-shot: three episodes using (1,2), (1,3) or (2,3);
- 3-shot: one episode using all three ranks.

Every method and every pretraining seed must use the identical episode membership.

## 12. Primary real-adaptation protocol

Primary analysis:

- start from the frozen simulation-pretrained checkpoint for each method and seed;
- freeze encoder;
- update classifier head only;
- cross-entropy only;
- no JS or Residual auxiliary loss on real data;
- AdamW;
- learning-rate candidates `[1e-4, 3e-4, 1e-3]`;
- weight decay `1e-4`;
- maximum 200 epochs;
- patience 30;
- select adaptation checkpoint by 14-sample adaptation-validation Macro-F1;
- tie break by smaller learning rate, then earlier epoch.

A preregistered secondary analysis allows full-network CE fine-tuning with `[1e-6, 3e-6, 1e-5]`, maximum 100 epochs and patience 20.

## 13. Final real-test boundary

The 35 final-real-test samples remain fully locked until:

1. Simulation Validation tuning is complete;
2. formal hyperparameters are frozen for all three core methods;
3. three checkpoint hashes per method are frozen;
4. simulated Test is complete and immutable;
5. real-adaptation code, tests and preflight pass;
6. all adapted checkpoint hashes are frozen;
7. the user provides separate final-real-test authorization.

The final stage must evaluate all preregistered 0/1/2/3-shot method/seed/episode combinations in one immutable run. Results cannot change support samples, learning rate, epoch, checkpoint or dataset membership.

## 14. Real-domain metrics and estimands

At each shot budget, primary effects are:

```text
Delta_JS  = MacroF1(JS)       - MacroF1(Dynamic ERM)
Delta_RES = MacroF1(Residual) - MacroF1(Dynamic ERM)
```

Required reporting includes:

- Accuracy, Balanced Accuracy, Macro-F1;
- per-class Recall/F1 and confusion matrix;
- within-method gain from 0-shot;
- all pretraining seeds and support episodes;
- crystal-system-stratified paired bootstrap 95% intervals;
- the complete label-efficiency curve, not only the best shot.

## 15. GTIIT status

GTIIT does not enter RRUFF adaptation train, adaptation validation or final-test aggregate metrics.

It remains a supplementary local-instrument case study and still requires:

- de-identification;
- sample-level label evidence;
- batch and duplicate isolation;
- provenance manifest;
- separate authorization.

## 16. Current real-domain engineering state

Completed:

- scientific design frozen;
- RRUFF-70 role assignment frozen;
- support episodes frozen;
- GitHub protocol and machine-readable design contract added.

Not completed:

- local manifests copied into the project data path;
- `scripts/audit_v9_real_adaptation_contract.py`;
- `scripts/run_v9_real_adaptation.py`;
- adaptation unit tests;
- adaptation training;
- final real test.

Therefore:

```text
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

## 17. Immediate next actions

1. Complete desktop migration and first-boot engineering acceptance.
2. Run the existing simulation preflight and full unit suite.
3. Obtain explicit authorization before enabling the 7-run.
4. Implement the real-adaptation preflight, runner and tests without loading final-test data.
5. Copy the frozen local RRUFF manifests and verify the registered hashes.
6. Keep simulated Test, adaptation execution and final real test under separate locks.

## 18. Evidence priority

When evidence disagrees, use this order:

1. frozen machine-readable configurations;
2. current source code and hashes;
3. matching audit reports and experiment registry;
4. this `CURRENT_STATE.md`;
5. current design documents and dated decision records;
6. archived plans and historical conversations.

A conflict between higher-priority evidence sources must stop training or test access and trigger a new audit.
