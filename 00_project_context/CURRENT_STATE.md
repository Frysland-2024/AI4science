# AI4science Current State

**Canonical status date:** 2026-08-01  
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> This file records only the current authoritative state. Historical reasoning
> remains in `PROJECT_JOURNEY.md`, dated reports, and Git history.

## Latest authoritative state

The active V9 backbone and optimization contract remain frozen as
ML4pXRDs-style ResNet-18-GN with identity preprocessing, AdamW, constant
learning rate, the parent-structure 70/15/15 split, and the registered online
PXRD simulator. Dynamic ERM is the strong baseline. Residual-v1 remains rejected
and archived after its preregistered stability Gate failed.

The active scientific comparison was frozen as Dynamic ERM versus JS
Consistency with `lambda_js = 60`. The preregistered five-seed paired
Validation replication has completed: five matched training seeds, two methods
per seed, ten runs total. No seed was excluded post hoc and lambda was not
retuned.

The confirmatory one-shot simulated-Test protocol is now also frozen in:

`xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json`

Human-readable contract:

`xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md`

Its status is `preregistered_locked_not_authorized`. The user's instruction to
freeze the contract did not authorize Test inference. Simulated Test therefore
remains unused and execution-disabled.

## 2026-08-01 five-seed paired replication completed

All ten registered Validation-only runs completed. The authoritative
machine-readable report is:

`xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`

The human-readable result record is:

`xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`

Aggregate results:

| Metric | Dynamic ERM, mean ± sample SD | JS lambda=60, mean ± sample SD | Delta |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 ± 0.006272 | 0.734648 ± 0.008533 | +0.027757 |
| In-range Macro-F1 | 0.705112 ± 0.010905 | 0.733103 ± 0.008101 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | +0.046569 |
| Worst-class F1 | 0.574014 ± 0.017829 | 0.593611 ± 0.033188 | +0.019597 |

The preregistered primary paired effect is:

- mean OOD delta: `+0.046569`;
- sample SD of paired OOD deltas: `0.009711`;
- paired-bootstrap 95% interval: `[0.038145, 0.052834]`;
- positive OOD delta in all five matched seed pairs.

The paired in-range effect is:

- mean in-range delta: `+0.027991`;
- sample SD: `0.017987`;
- paired-bootstrap 95% interval: `[0.014028, 0.041954]`;
- positive in-range delta in all five matched seed pairs.

The preregistered in-range guardrail passed. The result therefore supports JS
Consistency with `lambda_js = 60` as the selected V9 method under the frozen
Validation protocol.

## Frozen simulated-Test contract

The one-shot Test contract freezes the following choices before any Test
inference:

- all five Dynamic ERM / JS training-seed pairs are retained;
- all ten Validation-selected checkpoints are evaluated independently;
- each checkpoint is fixed by its registered best epoch and global step;
- checkpoint averaging, ensembling, substitution, retraining, seed exclusion,
  lambda retuning, and Test-guided selection are forbidden;
- Test contains 2,109 held-out parent structures;
- deterministic evaluation seeds are `20260721`, `20260722`, and `20260723`;
- the primary endpoint is the five-pair delta in mean single-factor OOD
  Macro-F1, after averaging the six profiles and three measurement-panel seeds
  within each checkpoint;
- evaluation-panel seeds are not treated as additional model replicates;
- the primary interval is a paired bootstrap over the five matched training-seed
  pairs;
- no observed Test outcome permits a changed method or a second modified Test
  attempt.

The older evaluation configuration contains an early placeholder referring to
three checkpoint hashes. That historical file remains unchanged. The new Test
contract explicitly supersedes that placeholder and requires the ten
Validation-selected checkpoints from the completed five-pair design.

## Diagnostic limitation

Worst-class F1 improved on average and in four of five Validation seed pairs,
but seed `20260714` showed a paired worst-class change of `-0.061139`. This is
an important secondary diagnostic. It does not reverse the preregistered primary
OOD conclusion, but the affected class and condition must be identified before
publication or any claim of uniform per-class improvement.

The simulated-Test contract requires this anomaly to be reported descriptively,
but forbids using it to change the selected checkpoint, method, or lambda.

## Scientific decision

The V9 method-selection question is closed:

- selected method: JS Consistency;
- selected weight: `lambda_js = 60`;
- comparison baseline: Dynamic ERM;
- no further lambda search is permitted;
- no post-hoc seed selection is permitted;
- Validation may not be reused to reopen method choice;
- the Test protocol is confirmatory and cannot change the selected method.

The completed evidence supports the statement that JS Consistency produced a
repeatable positive paired effect on mean single-factor Validation-OOD
Macro-F1 while also improving mean in-range Macro-F1 across the five registered
training seeds. It does not yet support a simulated-Test or real-XRD claim.

## Boundary status

The following boundaries remain authoritative:

- simulated Test used: **no**;
- simulated-Test contract frozen: **yes**;
- simulated-Test execution authorized: **no**;
- real XRD used: **no**;
- real-domain adaptation used: **no**;
- lambda retuned after replication: **no**;
- seed excluded post hoc: **no**;
- V10 opened: **no**.

The ten-run result is development/Validation evidence only. It is not a
simulated-Test result, a sim-to-real result, or a final external-validity claim.

## Current blocker

The scientific Test design is no longer the blocker: the one-shot protocol is
frozen. The remaining blockers before execution are:

1. implement or review the contract-conforming read-only preflight and serial
   evaluation runner;
2. locate all ten local Validation-selected checkpoint binaries;
3. record checkpoint SHA-256 values and verify epoch/global-step matches;
4. generate and freeze the three deterministic Test manifest hashes before
   inference;
5. verify that simulated Test has not previously been accessed and that the
   output root is empty;
6. obtain a separate explicit user authorization to execute the frozen contract.

Missing checkpoints may not be silently regenerated or replaced under the
current contract.

## Next actions

1. Implement and review the read-only preflight and Test evaluation runner
   against the frozen machine-readable contract, without running inference.
2. Run documentation/configuration validation and inspect the planned manifest,
   checkpoint, provenance, and output paths.
3. Obtain a separate explicit execution authorization.
4. Only after all preflight gates pass, perform the one-shot simulated-Test
   evaluation and stop for audit.
5. Freeze the Test report and diagnose the seed-20260714 worst-class result as a
   secondary analysis.
6. Only after the simulated-Test report is frozen, design the real-XRD external
   validation stage.

## Authoritative records

- `xrd_robustness/configs/v9_resnet_js_ten_run.preregistered.json`
- `xrd_robustness/configs/v9_resnet_js_ten_run.authorization.json`
- `xrd_robustness/scripts/run_v9_resnet_js_ten_run.sh`
- `xrd_robustness/scripts/summarize_v9_resnet_js_ten_run.py`
- `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`
- `xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`
- `xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md`
- Validation result commit `868b079c1b410e6afe877330b7defc4262d82969`
- Test-contract commits begin at `1a2d180baf10e47a4b8732b14549522cfdaf48d2`

Older execution details remain available in Git history and dated reports. They
must not override this current-state record when they conflict with the status
above.
