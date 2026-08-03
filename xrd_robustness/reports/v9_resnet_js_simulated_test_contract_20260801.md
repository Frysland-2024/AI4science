# V9 ResNet–JS One-Shot Simulated-Test Contract

**Frozen:** 2026-08-01 19:46 +08:00  
**Status:** `PREREGISTERED_LOCKED_NOT_AUTHORIZED`  
**Execution authorized:** no  
**Simulated Test accessed:** no  
**Real XRD accessed:** no

## 1. Purpose

This document freezes the confirmatory simulated-Test protocol for the already
selected V9 comparison:

- baseline: Dynamic ERM;
- selected method: JS Consistency;
- fixed `lambda_js = 60`;
- backbone: ResNet-18-GN;
- five matched training-seed pairs;
- ten Validation-selected checkpoints.

The user's instruction `冻结` authorizes the creation and locking of this
contract only. It does **not** authorize Test inference.

## 2. Scientific question

> On the completely held-out parent-structure Test split, does the already
> selected JS method retain a positive paired robustness effect over Dynamic ERM
> under the frozen PXRD measurement profiles, without an unacceptable in-range
> performance loss?

The method-selection question is already closed. Test results cannot be used to
retune `lambda_js`, replace checkpoints, exclude seeds, reopen Residual, or
select another method.

## 3. Checkpoint rule

Each of the ten runs must use exactly the best checkpoint selected during the
registered Validation replication.

| Pair | ERM checkpoint | JS checkpoint |
|---|---|---|
| seed 20260711 | epoch 80, step 49280 | epoch 40, step 24640 |
| seed 20260712 | epoch 90, step 55440 | epoch 80, step 49280 |
| seed 20260713 | epoch 100, step 61600 | epoch 80, step 49280 |
| seed 20260714 | epoch 90, step 55440 | epoch 30, step 18480 |
| seed 20260715 | epoch 80, step 49280 | epoch 60, step 36960 |

Before inference, a read-only preflight must locate all checkpoint binaries and
record their SHA-256 values. If any checkpoint is absent or does not match its
registered epoch/global step, execution must stop. Retraining, substitution,
checkpoint averaging, ensembling, and Test-guided checkpoint choice are
forbidden.

The older evaluation configuration contains an early placeholder referring to
three checkpoint hashes. It is retained unchanged as historical evidence. This
contract supersedes that placeholder for Test execution and requires all ten
checkpoints from the completed five-pair design.

## 4. Frozen Test panel

- split: parent-structure `test`;
- number of independent parent structures: 2,109;
- overlap with Train or Validation: forbidden;
- evaluation seeds: `20260721`, `20260722`, `20260723`;
- one deterministic view per structure, profile, and evaluation seed.

Profiles:

- level-0: `level0`;
- in-range: `in_range`;
- single-factor OOD: negative shift, positive shift, broadening, noise,
  background, texture;
- unseen combinations: shift+broadening, background+noise, texture+shift;
- stress: `ood_all`.

All three Test manifests must be generated and hashed before model inference.
Evaluation seeds are repeated deterministic measurement panels, not independent
training replicates.

## 5. Primary endpoint

For each checkpoint:

1. compute Macro-F1 for each of six single-factor OOD profiles under each of
   three evaluation seeds;
2. average the 18 panel values;
3. compute JS minus ERM within each matched training-seed pair;
4. average the five paired differences.

Primary endpoint:

`paired_delta_mean_single_factor_ood_macro_f1`

Primary uncertainty report:

- five individual paired deltas;
- mean paired delta;
- sample standard deviation;
- 20,000-resample paired bootstrap percentile 95% interval, with bootstrap seed
  `20260801`.

The bootstrap unit is the matched training-seed pair. Profiles, evaluation
seeds, and individual generated spectra must not be treated as additional model
replicates.

## 6. Secondary and diagnostic endpoints

Secondary paired endpoints:

- in-range Macro-F1;
- level-0 Macro-F1;
- worst-class F1.

Every panel must additionally report:

- accuracy;
- balanced accuracy;
- Macro-F1;
- per-class recall and F1;
- confusion matrix;
- worst-class F1;
- expected calibration error.

Required diagnostics include per-profile results, per-crystal-system F1,
unseen-combination performance, `ood_all`, and identification of the class and
condition underlying the seed-20260714 Validation worst-class anomaly. The
anomaly analysis is descriptive only and cannot modify the selected method.

## 7. Interpretation rule

**Supportive:** paired mean OOD delta is positive, the paired-bootstrap lower
bound is above zero, and paired mean in-range delta is at least `-0.01`.

**Directionally supportive:** paired mean OOD delta is positive but its interval
includes zero, while the in-range guardrail passes.

**Not supported on Test:** paired mean OOD delta is non-positive or paired mean
in-range delta is below `-0.01`.

No outcome changes the frozen method or permits a second Test attempt with
modified settings. The observed Test result must be reported as-is.

## 8. Preflight gates

Execution remains prohibited until a separate authorization exists and all
following gates pass:

1. all ten checkpoint binaries exist and are hashed;
2. checkpoint epochs and global steps match the frozen table;
3. evaluation source-tree and resolved-config hashes are recorded;
4. Test contains exactly 2,109 parent structures;
5. Train/Validation/Test intersections are empty;
6. all three Test manifests are generated and hashed before inference;
7. the output directory is absent or empty;
8. prior simulated-Test access is ruled out;
9. real XRD remains locked;
10. a separate authorization file matches the machine-readable contract.

## 9. Outputs

Planned local output root:

`outputs/v9_resnet_js_simulated_test_v1`

Planned committed records:

- `reports/v9_resnet_js_simulated_test_preflight.json`;
- `reports/v9_resnet_js_simulated_test_summary.json`;
- `reports/v9_resnet_js_simulated_test_results_20260801.md`;
- `reports/v9_resnet_js_simulated_test_audit.json`.

Checkpoint files, predictions, generated spectra, caches, and other large
runtime artifacts remain outside Git.

## 10. Current boundary

The contract is frozen, but execution is still disabled. The next scientific
authorization must explicitly state that the frozen simulated-Test contract may
be executed. Until then, no Test command is permitted.
