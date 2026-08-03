# AI4science Current State

**Canonical status date:** 2026-08-03
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

## 2026-08-03 RRUFF-350 collection completed

The local measured-PXRD expansion asset is now frozen as
`rruff-real-pxrd-350-v1`: 350 unique RRUFF sample IDs, balanced at 50 samples
for each of the seven crystal systems. It preserves all 70 frozen RRUFF-70
canonical spectrum hashes and adds 280 model-blind samples selected from the
official RRUFF powder archives using measurement, label, DIF, quality, and
spectral-redundancy evidence only.

The archives and spectra remain under the ignored local data root
`xrd_robustness/data/real_xrd/rruff350/`; datasets are not committed. The
reproducible builder is `xrd_robustness/scripts/build_rruff350.py`, and the
tracked audit is `xrd_robustness/reports/rruff350_build_audit.json`.

RRUFF-350 is an expansion/evaluation asset, not a new independent 350-sample
final test: the embedded RRUFF-70 roles remain frozen and explicitly labelled.
No model was loaded and no real-XRD inference was run while constructing it.

The confirmatory one-shot simulated-Test protocol is now also frozen in:

`xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json`

Human-readable contract:

`xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md`

The contract itself remains `preregistered_locked_not_authorized`, preserving
the pre-execution scientific choices. A separate authorization was recorded on
2026-08-02. The first local launch on 2026-08-03 was stopped by the user before
any checkpoint result or summary was written because the runner regenerated
the same deterministic spectra for every checkpoint and starved the GPU.

No Test metric was observed. Test access has nevertheless occurred and is
recorded as an aborted infrastructure attempt. The user's subsequent explicit
instruction `重搞` authorizes one identical retry: checkpoints, manifests,
profiles, seeds, metrics, and selection rules remain unchanged. Only the
execution implementation changes to a hash-verified, render-once panel cache,
atomic run state, and checkpoint-level resume. The retry is authorized but has
not started.

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
training seeds. The frozen simulated Test independently confirmed the direction:
the mean five-pair OOD Macro-F1 delta is `+0.054600`, with all five pair deltas
positive and a paired-bootstrap 95% interval of `[+0.048944, +0.060255]`. This
still does not support a real-XRD or sim-to-real claim.

## Boundary status

The following boundaries remain authoritative:

- simulated Test accessed: **yes**;
- simulated-Test result available: **yes, completed 10/10 checkpoints**;
- identical retry started: **yes, completed**;
- simulated-Test contract frozen: **yes**;
- identical simulated-Test retry authorized: **yes**;
- real XRD used: **no**;
- real-domain adaptation used: **no**;
- lambda retuned after replication: **no**;
- seed excluded post hoc: **no**;
- V10 opened: **no**.

The ten-run result is development/Validation evidence only. It is not a
simulated-Test result, a sim-to-real result, or a final external-validity claim.

## Current blocker

No simulated-Test engineering or execution blocker remains. The authorized
identical retry completed all 10 checkpoints with the frozen three manifests
and 2,109 Test parents. The completed audit verifies one-time spectrum reuse,
serial checkpoint evaluation, the panel-cache index hash, and the final summary
hash. A sustained 12-second inference sample averaged 94.25% GPU utilization
(91-97%), above the requested 88-90% execution target.

The remaining scientific boundary is external validity: real XRD and
real-domain adaptation have not been used. The seed-20260714 Test diagnosis also
shows that aggregate improvement is not uniform across every class/profile;
monoclinic remains the principal worst-class bottleneck.

## Next actions

1. Preserve the frozen simulated-Test report and local hashed raw evidence; do
   not rerun, retune, exclude seeds, or select checkpoints from Test outcomes.
2. Carry the monoclinic shift/texture limitation into publication claims and
   any future error analysis.
3. Design and separately authorize the real-XRD external-validation stage
   without reopening the V9 method or lambda decision.

## Authoritative records

- `xrd_robustness/configs/v9_resnet_js_ten_run.preregistered.json`
- `xrd_robustness/configs/v9_resnet_js_ten_run.authorization.json`
- `xrd_robustness/scripts/run_v9_resnet_js_ten_run.sh`
- `xrd_robustness/scripts/summarize_v9_resnet_js_ten_run.py`
- `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`
- `xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`
- `xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json`
- `xrd_robustness/configs/v9_resnet_js_simulated_test.authorization.json`
- `xrd_robustness/configs/v9_resnet_js_simulated_test.retry_authorization.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_performance_audit_20260803.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_summary.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_audit.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_results_20260803.md`
- Validation result commit `868b079c1b410e6afe877330b7defc4262d82969`
- Test-contract commits begin at `1a2d180baf10e47a4b8732b14549522cfdaf48d2`

Older execution details remain available in Git history and dated reports. They
must not override this current-state record when they conflict with the status
above.
