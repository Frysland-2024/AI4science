# AI4science Current State

**Canonical status date:** 2026-07-22

**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> This file records the current state only. Historical changes and abandoned directions must remain in `PROJECT_JOURNEY.md` and the archived design documents.

## 1. Current research identity

The active project is **V9-T: Algorithm Transfer for PXRD Robustness**.

The project is used as a bridge from materials-centered ML toward ML-centered scientific research. The current question is not merely whether more simulated spectra improve crystal-system classification, but whether different learning principles produce more robust representations under controlled simulation-to-experiment distribution shift.

The current paper scope is **problem-driven algorithm transfer and rigorous PXRD-specific validation**. It does not claim a new general-purpose ML theory.

## 2. Current scientific question

Under strictly matched:

- mother crystal structures;
- physical perturbation distribution;
- paired training views;
- backbone architecture;
- optimizer and training budget;
- validation and OOD evaluation panels;

compare whether the following learning principles differ in generalization to unseen measurement conditions and real PXRD:

1. augmentation-only supervised learning;
2. cross-view prediction consistency;
3. residual class decorrelation.

The core controlled comparison is:

```text
The same dynamic view pair
├── Dynamic/Paired ERM: classification only
├── JS Consistency: classification + prediction consistency
└── Residual Decorrelation: classification + residual class decorrelation
```

## 3. Frozen data contract

Total unique Materials Project structures: **14,060**.

| Split | Structures | Role |
|---|---:|---|
| Train | 9,842 | Training and dynamic view generation |
| Validation | 2,109 | Hyperparameter selection, early stopping, checkpoint selection, development OOD evaluation |
| Test | 2,109 | Locked final simulated evaluation |

Rules:

- Splitting is performed at the unique structure/family level.
- All clean, frozen, weak, strong, and dynamic views inherit the split of their mother structure.
- Validation and Test structures must never enter a training view generator.
- All five methods share the same mother-structure split.

Train crystal-system counts:

| Crystal system | Count |
|---|---:|
| cubic | 1,409 |
| hexagonal | 1,406 |
| monoclinic | 1,409 |
| orthorhombic | 1,411 |
| tetragonal | 1,406 |
| triclinic | 1,400 |
| trigonal | 1,401 |
| **Total** | **9,842** |

Each structure has a cached ideal-reflection representation including peak positions, integrated intensities, hkl, multiplicity, reciprocal vectors, and reflection-to-peak mapping.

## 4. Frozen training perturbation family

Except for Clean ERM, methods use the same frozen training distribution:

- zero shift: Uniform `[-0.2°, 0.2°]`, activation probability `0.5`;
- FWHM: Uniform `[0.08°, 0.20°]`, activation probability `1.0`;
- background ratio: Uniform `[0, 0.02]`, activation probability `0.5`;
- background shape: smooth third-order polynomial;
- Poisson count scale: Log-uniform `[2500, 40000]`;
- electronic noise standard deviation: Uniform `[0, 2]` counts;
- March–Dollase parameter: Uniform `[0.8, 1.0]`, activation probability `0.7`.

These activation probabilities describe training coverage, not empirical frequencies in a real instrument population.

## 5. Active method set

### 5.1 Clean ERM

One frozen level-0 view per mother structure. It is a high-count, minimally perturbed reference and is not a perfectly noiseless mathematical ideal because the current level-0 rendering still uses a Poisson count model at scale 40,000.

### 5.2 Frozen Four-View ERM

Four fixed perturbation parameter/seed combinations per mother structure. The full rendered arrays are not persisted; spectra are deterministically re-rendered from reflection caches and frozen parameters.

### 5.3 Dynamic/Paired ERM

Two independently sampled dynamic views per structure and training step. The view seed is determined by:

```text
run_seed, epoch, global_step, material_id, view_id
```

Loss: mean classification loss across the two views.

### 5.4 JS Consistency

Uses exactly the same dynamic paired views as Dynamic ERM. The only change is the addition of a Jensen–Shannon prediction-consistency term.

Frozen tuning candidates:

```text
lambda_JS ∈ {0.1, 0.3, 1.0}
```

### 5.5 Residual Class Decorrelation

Uses exactly the same dynamic paired views. It permits reasonable view differences but suppresses crystal-system information in the normalized feature residual.

Frozen tuning candidates:

```text
lambda_res ∈ {0.01, 0.1, 1.0}
```

Current configuration also includes a one-layer residual head, 2-epoch warmup, and 3-epoch ramp.

Simulator perturbation labels are not used in V9-T.

## 6. Current experiment state

- Lambda tuning: **0/7 runs completed**.
- Seven tuning runs: planned, not started.
- The method-parameter candidate ranges are frozen after the one-time Train-only Gate, but both tuning execution switches remain false because the 7-run has not received separate execution authorization.
- Active training process: none.
- Active checkpoint selected for formal comparison: none.
- Formal multi-seed 15-run stage: not started.
- Locked simulated Test evaluation: not authorized and not started.
- Final real-spectrum evaluation: not authorized and not started.
- Previous laptop training products are not authoritative and must not be resumed.
- Formal desktop training must start from optimizer step 0 after engineering gates pass and the user gives explicit authorization.

## 7. Current engineering status

The earlier **dynamic manifest growth problem has been fixed**.

Dynamic training no longer materializes or persists an epoch-scale or run-scale manifest. Parameter rows are generated only for the consumed batch, or for a bounded prefetch window. The current audit reports:

- `dynamic_rows_are_batch_bounded = true`;
- `dynamic_rows_are_prefetch_bounded = true`;
- maximum parameter rows per batch: `32`;
- maximum live parameter rows with the registered prefetch window: `256`;
- the legacy eager design would have produced `606,267,200` rows and is no longer used;
- Dynamic ERM, JS, and Residual share the same sampler, pair schedule, and dynamic parameter-pair hashes;
- the same dynamic coordinate replays the same parameters;
- Train/Validation/Test exclusion gates pass.

Therefore, dynamic manifest growth is **not a current blocker**.

The checkpoint-resume verification gap is now closed. A bounded real-cache CUDA audit interrupts after epoch 0, reloads a self-contained checkpoint, and compares the continuation against an uninterrupted three-epoch reference. All 12 checks pass, including future material IDs, accepted parameter pairs, next-step loss, global step, stream hashes/snapshot, and final model-parameter SHA256. The checkpoint also stores the stream audit and sampler-contract hash directly; RNG restore explicitly normalizes CPU/CUDA state tensors after `map_location`.

The method-parameter semantic audit is now complete: all 22 checks pass. It proves zero-weight reduction to Dynamic/Paired ERM, JS symmetry/non-negativity/batch-mean reduction, residual entropy direction, finite normalization, head/backbone gradient flow, and the exact 2-epoch warmup plus 3-epoch ramp. The production V9 residual is an absolute normalized feature difference and is therefore swap-invariant; the separately retained signed residual is swap-antisymmetric. These semantics are tested independently and must not be conflated.

The schema-v3 128-step scale audit remains preserved, but it is now classified only as **initialization/chance-state evidence**. Its late classification accuracy was 11.96% (chance 14.29%) and the residual probe remained at uniform CE, so its inverse-gradient values (`2.874e5` JS and `2.556e4` Residual) are invalid for grid revision.

The authorized learned-state audit remains the evidence that the backbone and detached residual probe reached an interpretable state. The user then approved the single permitted pre-Validation grid revision: JS `[0.3, 3.0, 30.0]` and Residual `[0.2, 2.0, 20.0]`. The decisive Train-only Gate is `reports/v9_candidate_grid_gate.json` (SHA-256 `E59EE2A56906757C82238CB47D520B1D74D690455EA907540AFFF59EA2E8A947`). It rebuilt a classification-only Dynamic/Paired ERM PAMPT-B3 from the same fixed seed and epoch 0 for five epochs on all 9,842 Train structures, wrote no checkpoint, trained the detached one-layer residual probe for 50 epochs at `lr=1e-3` on a disjoint Train-calibration subset, and directly evaluated the weighted auxiliary and combined backbone gradients for all six candidates on the separate Train scale subset. Median weighted auxiliary/classification ratios were JS `0.02283`, `0.22842`, `2.28533` and Residual `0.02581`, `0.25854`, `2.58715`, exactly spanning weak, material non-dominant, and dominant. All finite, gradient-presence, combined-direction, identity, and runaway checks passed. No Validation metric, simulated Test, or real XRD was used. The candidate range is now frozen and the one revision is consumed, but both tuning execution switches remain false and the 7-run remains 0/7 pending separate explicit user authorization.

## 8. Engineering gate status before tuning

| Gate | Current status |
|---|---|
| Dynamic parameter rows remain batch/prefetch bounded | **PASS** |
| Same dynamic coordinate replays identical parameters | **PASS** |
| Dynamic ERM, JS, and Residual receive the same paired-view schedule | **PASS** |
| View 1 and View 2 remain separately sampled for one mother structure | **Implemented; unit-level evidence present** |
| Checkpoint resume restores model, optimizers, modules, Torch CPU/CUDA RNG, epoch and stream audit | **Implemented** |
| Resumed future view sequence matches uninterrupted execution end-to-end | **PASS: real reflection-cache CUDA audit, 12/12 checks** |
| Validation and Test IDs are excluded from dynamic training | **PASS** |
| Optimizer-step and pattern-forward budgets match across methods | **PASS** |
| Method formula, reduction, zero-weight fallback, direction and gradient flow | **PASS: 22/22 semantic checks** |
| Classification learning signal exists before JS scale interpretation | **PASS at learned-state epochs 3 and 5** |
| Residual probe predicts class on an exclusive Train-audit subset | **PASS at epochs 3 and 5; epoch-5 accuracy 32.57%, Macro-F1 28.92%** |
| Learned-state auxiliary-gradient ratios are eligible for interpretation | **PASS; used only for the single human-approved pre-Validation revision** |
| Registered λ grids span weak, material non-dominant, and dominant gradient influence | **PASS: direct Train-only autograd Gate for JS `[0.3,3,30]` and Residual `[0.2,2,20]`** |
| Candidate range is frozen before Validation | **PASS; one permitted revision consumed** |
| Validation tuning execution authorized | **NO: both execution switches remain false; 7-run remains 0/7** |
| Current reports match the frozen configuration and source hashes | **PASS in the recorded preflight; rerun after any code change** |

A failed mandatory gate blocks training authorization.

## 9. Immediate next actions

1. Complete the desktop migration hash rehearsal and rerun the full unit suite/V9 preflight on the final source tree.
2. On the target desktop, run bootstrap plus first-boot engineering acceptance; the frozen candidate range does not itself authorize tuning.
3. Wait for explicit user authorization before enabling or starting the seven-run Validation-only lambda tuning from optimizer step 0.
4. Keep the 15-run comparison, simulated Test, and real test under their separate locks.

## 10. Current paper structure

### Primary question

**Robust learning-strategy transfer for simulated-to-experimental PXRD generalization.**

### Pre-registered secondary question

**Unique-structure sample efficiency**, initially using a restrained set of structure budgets such as 25%, 50%, and 100%, only after the main pilot is stable.

The sample-efficiency horizontal axis must be the number of unique mother structures, not the number of dynamically rendered spectra.

## 11. Archived or conditional directions

These directions are scientifically valid but are outside the current V9-T tuning matrix:

### A. Structured dynamic measurement simulation

Archived unless evidence shows that the dominant bottleneck is the mismatch between independent perturbation sampling and realistic joint measurement states.

### B. Simulator-supervised measurement residual

Archived unless ordinary Residual Decorrelation shows a meaningful signal but the semantics of the residual remain insufficiently identified.

### C. Few-shot or semi-supervised Sim2Real adaptation

Reserved as a possible later project. It would study simulated pretraining plus small labeled and/or large unlabeled real PXRD data, rather than being used as an ad hoc rescue experiment for V9-T.

## 12. Decision rule for future pivots

- If JS or Residual wins consistently at full data: retain algorithm transfer as primary and sample efficiency as secondary.
- If methods tie at full data but JS/Residual wins at lower unique-structure budgets: elevate sample efficiency while retaining the controlled algorithm comparison.
- If all learning objectives fail while simulated OOD is acceptable and real performance remains poor: investigate the measurement simulation distribution rather than adding more losses.
- If Residual has a positive trend but unclear semantics: consider simulator-supervised residual modeling as a new method version.
- If no stable signal appears across the predefined analyses: stop expanding the XRD method matrix, preserve the negative result and infrastructure, and move the next project toward a more explicitly ML-centered task.

## 13. Evidence priority

When documents disagree, use this order:

1. frozen machine-readable configurations;
2. current source code and hashes;
3. matching audit reports and experiment registry;
4. this `CURRENT_STATE.md`;
5. explanatory design documents;
6. archived plans and historical conversations.

A conflict between higher-priority evidence sources must stop training and trigger a new audit.

## 14. Repository synchronization policy

The repository root is `E:/AI4science`, the active branch is `main`, and the normal
publication target is `origin/main`. Root `AGENTS.md` now requires an automatic GitHub
synchronization workflow after actual code, configuration, or project-documentation
changes: verify the root worktree, run relevant tests or audits, update handoff/state
records when project state changes, stage only explicit task files, inspect the staged
diff and scan for secrets/prohibited artifacts, commit with an accurate English
message, require a clean worktree, and push with `git push origin main`.

This is a repository-governance change only. It does not change the V9-T scientific
design, the 0/7 tuning state, any experiment result, or any training/test authorization.
An explicit user instruction not to commit or not to push overrides automatic
publication for that task.

## 15. Local GTIIT external-data inventory

On 2026-07-22, an external GTIIT laboratory archive was moved from the desktop,
validated, and organized under `E:/AI4science/04_external_lab_data/GTIIT`. The
entire top-level directory is Git-ignored because it contains raw experimental
data, PDFs, images, external scripts, and privacy-sensitive laboratory forms.

Current local evidence:

- the source archive SHA-256 is
  `959B26A57519BF0CEAC77581EBF2653FD52AD4B6FCCFFCFDA8FDC6433D1508B6`;
- all 561 extracted files match their seven nested ZIP entries by size and CRC;
- the XRD portion contains 543 files, including 237 RAW and 228 TXT files;
- 224/228 XRD TXT files parse as monotonic two-column spectra, and 218 RAW/TXT
  pairs share a directory and filename stem;
- one remote XRD folder was explicitly missing from the source export;
- 40 of 41 readable non-temporary Word documents were flagged for contact,
  address, invoicing, or account-like information and must remain local.

This inventory creates a candidate real-instrument data pool only. It is not a
frozen label manifest, training source, Validation set, or authorized real test.
Before any future use, it requires de-identification, sample-level label evidence,
batch isolation, provenance documentation, and the relevant explicit authorization.
The V9-T scientific design, current blocker, 0/7 tuning state, and test locks are
unchanged.

## 16. Laptop-stage V9-T closure package (2026-07-22)

### Completed engineering evidence

- `reports/v9_resume_determinism_audit.json`: PASS, 12/12 end-to-end resume checks on CUDA using the real reflection cache and frozen Train renderer.
- `reports/v9_method_semantics_audit.json`: PASS, 22/22 formula/direction/reduction/gradient-flow/schedule checks.
- `reports/v9_loss_gradient_scale_audit.json`: numerical PASS on formal PAMPT-B3 over 128 Train-only optimizer steps, with a blocked registered-candidate range Gate; no λ selection.
- `configs/v9_method_parameter_governance.json`: hashed source table, fixed secondary parameters, one-revision policy, and fail-closed tuning Gate.
- `reports/v9_real_test_preprocessing_readiness.json`: locked-ready preprocessing contract; no model or real spectrum loaded.
- Formal runs now export hashed per-spectrum `prediction_rows.jsonl` with `family_id`, probabilities, and profile/run identity.

### Frozen statistical design

- The independent resampling unit is the mother-structure/family cluster.
- Resampling is paired within each registered seed, then contrasts are averaged across all registered seeds.
- Bootstrapping only the three seed summaries is removed from the formal comparison path.
- Direct `Residual - JS` evidence is mandatory for superiority language.
- Synthetic tests cover consistent gains, mixed seed direction, near-ties, and OOD gains accompanied by ID loss.

### Prepared non-result assets

- mechanism diagnostics for paired JS/flip rate, residual probe inputs, norm, variance, effective rank, class separation, and collapse risk;
- disabled real-test manifest/hash/preprocessing/overlap audit interfaces;
- manuscript skeleton, result/figure templates, and reviewer-attack checklist;
- migration/first-boot workflow remains training-free;
- the refreshed desktop payload count, bytes, and stream SHA-256 are authoritative only in `reports/v9_desktop_migration_manifest.json`, avoiding a self-referential stale copy here;
- source-side migration verification passed with every manifest file checked, 0 missing files, 0 size mismatches, and 0 hash mismatches; exact counts are authoritative in `reports/v9_desktop_migration_verification.json`;
- the copy-script `-WhatIf` rehearsal copied nothing, and the first-boot `-PlanOnly` rehearsal contained 0 formal-training commands.

### Unchanged experiment status and blockers

- λ tuning remains **0/7**; formal development comparison remains **0/15**.
- Simulated Test and real test remain unused and locked.
- No laptop checkpoint is authoritative.
- The method-parameter range Gate is complete. The remaining blockers are explicit user authorization for the seven-run and target-desktop first-boot acceptance.
- The source-side migration package is ready for copy, but this is not target-machine acceptance; the desktop must still run its own environment, hardware, transfer, evaluation, acceleration, and final-readiness probes.

## 17. Local WICSCI2025 external-material inventory

On 2026-07-22, `C:/Users/81504/Desktop/1.zip` was validated, moved, and
organized under `E:/AI4science/04_external_lab_data/WICSCI2025`. The directory
is covered by the repository's external-data ignore rule and is not a tracked
training dependency.

Current local evidence:

- archive SHA-256: `1B22A831D648D18790A46D3430753CB6AE767B7F87EF15CFEEC959CE199FD813`;
- 337 extracted files totaling 670,143,742 bytes, with a 337-row per-file
  SHA-256 inventory;
- full ZIP payload read passed, with no unsafe paths, symbolic links, or common
  secret patterns detected;
- four organized projects: molecular-vibration/IR/Raman processing (DXL),
  Quantum ESPRESSO XAS/Xspectra examples (HBY), the MIT-licensed NMRNet code
  and demo data (XFJ), and an NN-NMR tutorial with an external model weight
  (YQ).

These materials are useful as isolated spectroscopy and AI4S references,
especially for learned NMR representations and physics-to-spectrum workflows.
They are not PXRD labels, V9-T Train/Validation/Test inputs, or authorization to
load the external model weight. The V9-T experiment states and test locks are
unchanged.

## 18. Cross-project priority: XRD primary, Raman secondary

The active research priority remains XRD V9-T. The local Raman mapping material
under `04_external_lab_data/GTIIT/06_raman_mapping` is a promising seed for a
future spatial-spectral project, but it is not currently a second ML study of
comparable maturity.

Verified Raman evidence:

- two sample files, `sample_1_undoped_20240823.txt` and
  `sample_2_doped_20240823.txt`;
- each file contains a 26 x 26 spatial grid and 829 Raman-shift bins;
- the apparent 1,352 pixel spectra therefore come from only two independent
  specimen files whose names record the same date (`20240823`);
- the available MATLAB prototype reads the text cube, selects/integrates a
  Raman-shift interval, plots spectra, and renders a spatial surface; it does
  not implement an ML hypothesis, sample-level split, baseline comparison, or
  external validation.

Consequently, pixels from one specimen must not be randomly divided into Train
and Test and described as independent samples. The current files support
descriptive visualization and exploratory PCA/NMF-style analysis only. A future
Raman ML project requires multiple independent specimens and batches, stronger
label/provenance evidence, sample-level held-out evaluation, and a frozen
scientific task. Its preferred long-term niche is spatial-spectral
self-supervision, segmentation/unmixing, or anomaly detection after those data
conditions are met.

This decision does not add Raman to V9-T, alter the XRD method matrix, authorize
Raman model development, or change the XRD 0/7 and 0/15 experiment states.

## 19. Method-parameter literature provenance correction

The Hu et al. SD3Net paper was re-audited against the local primary PDF and the
publisher record. Its Equations 16-17 define
`L_cls = lambda_1 L_sd + lambda_2 L_sim` and
`L_total = L_cls + lambda_3 L_decorr`. Table 5 fixes `lambda_3=1` for Pavia,
HyRANK, and WHU while jointly varying `lambda_1/lambda_2`; Figure 12 separately
reports a regularization parameter `lambda` with an optimum near `1e-4` but does
not explicitly reconcile that symbol with the Table 5 `lambda_3` value.

Current scientific interpretation:

- the paper supports residual entropy/decorrelation as a method precedent;
- it supports reasoning in terms of relative loss contributions, sensitivity,
  and module ablation;
- neither `1` nor `1e-4` is numerical authority for V9-T `lambda_res`;
- copying `1e-4` into the PXRD grid is explicitly prohibited by the governance
  contract;
- at the time of this literature correction, the candidate grids remained
  unchanged and unfrozen; this historical state is superseded by Section 21
  and the current frozen-grid summary above.

This provenance correction changed no implementation formula, run count,
training authorization, Validation access, or Test lock. At that historical
checkpoint, tuning was 0/7, the formal comparison was 0/15, and the registered
candidate-range Gate was blocked; the later Train-only Gate resolved only the
candidate-range blocker, not the execution authorization.

## 20. Method-weight gradient compensation diagnosis

The V9-T Train-only scale audit was upgraded to schema v3 and rerun on CUDA.
It now records the requested raw losses, unweighted encoder/backbone gradients,
prediction JS distance, normalized feature-residual norm, and residual-head
entropy over non-overlapping early/middle/late thirds of the 128-step audit
trajectory. It also records pre-update residual-probe accuracy/loss/entropy so
probe learning is not confused with successful decorrelation.

Completed evidence:

- 128 deterministic, non-repeated paired Train batches from 14 balanced
  structures; no Validation, simulated Test, real spectrum, candidate-specific
  run, or formal training run was used;
- JS and Residual reductions are each one batch mean after summing the class
  dimension; no repeated class mean was found;
- encoder/backbone gradient norms now explicitly exclude PAMPT's supervised
  task head; full-model and task-head norms remain available in the trace;
- late classification accuracy is 11.96% with `L_cls=1.9499`, versus seven-class
  chance 14.29% and uniform cross-entropy `ln(7)=1.94591`;
- late paired-view top-1 agreement is 99.34% while prediction JS is
  approximately `2.97e-7`, showing that high agreement occurred before the
  classifier learned the task;
- late residual-probe pre-update accuracy is 14.62%, cross-entropy is 1.94613,
  and head entropy remains approximately maximal, so residual class-prediction
  competence is not demonstrated.

Scientific status:

- inverse-gradient values (approximately `2.874e5` for JS and `2.556e4` for
  Residual) are diagnostic compensation factors from an insufficiently learned
  trajectory, not theoretical weights or grid proposals;
- both registered grids remained unchanged and unfrozen at this historical
  diagnostic stage; the later human revision and direct Gate supersede this state;
- the previous wording that a range recalibration was already required is
  superseded: first require a Train-only classification learning milestone and,
  for Residual, a competent class probe before interpreting auxiliary-gradient
  scale;
- at this historical diagnostic stage, the candidate-range Gate and the new
  gradient-compensation interpretation Gate were blocked; tuning was 0/7 and
  formal development was 0/15;
- simulated Test and real test remain unused and locked.

The next action recorded at that checkpoint was to design and explicitly
authorize a longer Train-only, milestone-triggered diagnostic. That action was
subsequently completed in Section 21 and followed by the one-time revision and
direct six-candidate Gate summarized in the current-state sections above.

## 21. Learned-state Train-only scale audit

The longer milestone audit requested above is complete. It trained exactly one
classification-only Dynamic/Paired ERM PAMPT-B3 trajectory for five epochs on
all 9,842 Train structures, using batch size 16 and AdamW with learning rate and
weight decay `1e-4`. It wrote no checkpoint and did not read Validation,
simulated Test, or real XRD. The actual device was an RTX 4060 Laptop GPU; this
is diagnostic evidence only and makes no target-desktop performance claim.

At preregistered epochs 1, 3, and 5, detached residuals were split across three
mutually exclusive balanced Train subsets: 700 for probe calibration, 700 for
probe audit, and 700 for gradient-scale measurement. A one-layer residual probe
was fit for 50 epochs with fixed AdamW `lr=1e-3`, `weight_decay=0`; this stronger
diagnostic fit is intentionally separate from the backbone optimizer so an
underfit probe cannot create a false negative.

Results:

- epoch 1 remains chance state: backbone learning and probe gates both fail;
- epoch 3 passes both gates; probe audit accuracy is 22.43%, Macro-F1 16.55%;
- epoch 5 passes both gates; backbone Train CE is 1.62189 with 31.02% two-view
  accuracy, while the disjoint residual-probe audit gives 32.57% accuracy,
  28.92% Macro-F1, and CE 1.85059;
- epoch-5 median raw JS is 0.01862; paired top-1 disagreement is 35.42%;
- epoch-5 median unweighted JS/classification backbone-gradient ratio is
  0.05898 and Residual/classification is 0.09738.

The scientific interpretation is narrow but decisive: after the backbone learns,
JS has non-zero signal and the current symmetric normalized residual contains
class-predictive information. The huge inverse ratios from the 128-step report
are still invalid. This learned-state report itself did **not** select a lambda,
propose or apply a new grid, freeze the range, enable tuning, or start the 7-run.
Its historical human-review blocker was subsequently resolved by the explicit
revision and direct six-candidate Gate summarized above. Tuning remains 0/7,
formal development remains 0/15, and both test stages remain locked.
