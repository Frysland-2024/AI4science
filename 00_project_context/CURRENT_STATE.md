# AI4science Current State

**Canonical status date:** 2026-08-03
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> Current-state record only. Historical reasoning remains in `PROJECT_JOURNEY.md` and dated decision files.

## 2026-08-03 V9 ten-run recovery inventory and test-readiness status (authoritative)

The cloud-executed paired ten-run has been recovered locally as a Git-ignored
evidence archive at `xrd_robustness/reports/ten_run_output/`. The recovery
inventory is complete at the artifact-integrity level: the `COMPLETE_EXPORT`
manifest contains 12 files and all 12 SHA-256 values were recomputed locally
and matched on 2026-08-03. This includes the five checkpoint archive parts,
the assembled checkpoint archive, formal-14060 data archive, and recovery
metadata archive.

The assembled `v9_best_checkpoints_20260802.tar` contains exactly ten
`best.ckpt` artifacts: Dynamic ERM and JS lambda=60 for each seed
`20260711` through `20260715`. The embedded checkpoint metadata records the
expected stored epoch and optimizer step for all ten artifacts; every stored
value matches its corresponding expected value. The checkpoint archive's
SHA-256 is `a6f9defb8ba63a541543252006e9b95f0b89fae031f8a597dbacd91856dc1ab0`;
the formal-data and recovery-metadata archives also match their supplied
sidecars.

This establishes recovered completion and artifact integrity, **not** the
scientific result table: the local export has no five-seed aggregate summary
and no per-run metric histories. Do not infer final OOD, in-range, Test, or
method-selection metrics from checkpoint presence alone. The next evidence
action is to recover or regenerate the cloud run summary/history under the
frozen evaluation contract, then audit it against the ten checkpoint hashes.

Test readiness after the C-drive reinstall is restored. Git 2.55.0 and Python
3.11.9 are installed. The preserved `.venvs/xrd_tools` launcher remains
unusable because it references the removed `C:\Users\81504` Python 3.11
installation; it is retained as recovery evidence. A clean ignored environment
`.venvs/xrd_test` now contains the declared `science` and test dependencies
(`numpy`, `pytest`, `mp-api`, `pymatgen`, and CPU `torch`). Source compilation
passes. The historical four-run *pre-execution* test was revised to assert the
correct post-completion behavior: the preflight must refuse an existing output
root while every other lock/check still passes and `four_run_started=false`.
The complete unit suite passed on 2026-08-03 after that revision. The
reproducible command is:

```powershell
cd E:\AI4science\xrd_robustness
$env:PYTHONPATH='src'; E:\AI4science\.venvs\xrd_test\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

## Latest authoritative override: four-run authorized after exact online-generation optimization

The V9 public backbone is frozen as ML4pXRDs ResNet-18-GN with identity
preprocessing, AdamW, constant learning rate, and the frozen split, simulator,
batch size, maximum budget, and early-stopping contract. Dynamic ERM is the
public strong baseline.

The active scientific comparison is now **Dynamic ERM versus JS Consistency**.
Residual-v1 was rejected by its preregistered stability Gate and is archived;
it is not an active method and its lambda range may not be reopened.

The JS-only Train Gate passed. The candidate grid is frozen as `[3,30,60]`,
with median auxiliary-to-classification backbone-gradient ratios
`0.087859/0.877058/1.754115`, covering weak, material non-dominant, and
dominant influence. All combined-gradient direction and runaway guards passed.

The `1 Dynamic ERM + 3 JS` Validation-tuning contract is now preregistered.
It freezes the shared 100-epoch/61,600-step budget, checks every 6,160 steps,
minimum epoch 50, patience 3, `0.002` minimum delta, training/evaluation seeds
`20260710/20260720`, mean single-factor OOD Macro-F1 primary metric, in-range
guardrail, and deterministic tie-breaks. The launch preflight passed all 13
checks: exact matrix, registered hashes, parent-level split isolation,
Validation-manifest membership, absent output root, and Test/real locks.

The user authorized serial four-run execution. The initial Dynamic run was
stopped on request at epoch 9 / step 5,544 before its first Validation check
and is archived as optimization-only evidence, ineligible for selection.
Profiling identified repeated HKL ordering and repeated clean quality-reference
rendering. Caching only those structure invariants improved matched 16x16
prefetch throughput from `24.5265` to `31.3120` batches/s (`+27.67%`) and
sequential rendering from `3.6794` to `5.4267` batches/s (`+47.49%`).

## 2026-07-29 V9 ResNet JS four-run completed; lambda=60 selected (authoritative)

The preregistered Validation-tuning matrix of one Dynamic ERM baseline and three
JS Consistency candidates completed successfully. All four runs used the frozen
ResNet-18-GN public contract and Validation-only selection protocol.

Results:

- Dynamic ERM: mean single-factor OOD Macro-F1 `0.666471`, in-range `0.714013`;
- JS lambda=3: OOD `0.676134`, in-range `0.718417`;
- JS lambda=30: OOD `0.676164`, in-range `0.716428`;
- JS lambda=60: OOD `0.699742`, in-range `0.729806`.

All three JS candidates passed the preregistered in-range guardrail. Under the
frozen selection rule, JS lambda=60 is selected at best epoch 40 / optimizer
step 24,640. Its OOD improvement over Dynamic ERM is `+0.033271`, while its
in-range score also improves by `+0.015793`.

The four-run Validation selection is complete and frozen. Residual-v1 remains
archived. Simulated Test and real XRD were not accessed. The ten-run comparison
is not authorized and must not start automatically.

Authoritative report:
`xrd_robustness/reports/v9_resnet_js_four_run_summary.json`.
The optimization Gate passed exact accepted rows, material order, parameters,
spectrum arrays, array hashes, and quality-Gate counts, with maximum spectrum
difference `0.0`. No perturbed spectrum or random draw is cached. The complete
four-run is authorized to restart from optimizer step zero with the same
scientific contract and optimized execution hashes. It remains incomplete
until all four fresh runs and selection finish. The historical PAMPT 7-run,
ten-run comparison, simulated Test, real XRD, real adaptation, and V10 remain
locked.

Authoritative machine-readable records:

- `xrd_robustness/configs/v9_resnet_method_parameter_governance.json`;
- `xrd_robustness/configs/v9_resnet_js_four_run.preregistered.json`;
- `xrd_robustness/reports/v9_resnet_js_four_run_preflight.json`;
- `xrd_robustness/configs/v9_resnet_js_four_run.authorization.json`;
- `xrd_robustness/reports/v9_online_generation_optimization_audit.json`;
- `xrd_robustness/reports/v9_resnet_js_only_scale_gate.json`;
- `xrd_robustness/reports/v9_resnet_residual_stability_audit.json`.

All lower dated sections preserve intermediate or historical evidence. If any
lower section conflicts with this override, this override and the three
machine-readable records above take precedence.

## 2026-07-28 CNN Clean A/B/C diagnostics completed (authoritative)

The preregistered ResNet-18-GN Clean search is closed after exactly three
single-factor runs. Baseline identity + AdamW + constant LR remains selected
at level0 Macro-F1 `0.652168`. Sqrt preprocessing reached `0.645539`, Adam
reached `0.620014`, and 5-epoch warm-up + cosine reached `0.610826`; none met
the fixed `0.672168` selection threshold.

The matched ResNet Dynamic ERM diagnostic is also complete. Its best checkpoint
(epoch 80, step 49,280) reached level0 `0.719724`, in-range `0.717942`, mean
single-factor OOD `0.656316`, and worst-class F1 `0.580952`. Relative to Clean,
the deltas are `+0.067555`, `+0.535220`, `+0.253153`, and `+0.085936`.
The existing dynamic stream therefore acts as effective regularization on the
mature CNN rather than causing the earlier collapse.

Authoritative reports are `xrd_robustness/reports/cnn_contract_clean_abc_summary.json`
and `xrd_robustness/reports/cnn_contract_dynamic_erm_summary.json`. The CNN
foundation diagnostic Gate passes, but no fourth Clean search, JS, Residual,
curriculum, or clean anchor is open. Formal 7-run remains `0/7`; simulated
Test, real XRD, 15-run, and V10 remain locked. Next review and freeze a shared
method-comparison contract; do not immediately execute it.

## 2026-07-27 Foundation Gate 3 completed (authoritative)

The matched Clean-backbone diagnostic identifies PAMPT-B3 as a major
foundation bottleneck. The audited ML4pXRDs ResNet-18-GN port reached level-0
Macro-F1 `0.652168`, mean single-factor OOD Macro-F1 `0.403163`, and Train
accuracy `1.0` at the fixed 100-epoch / 61,600-step budget. The matched PAMPT
diagnostic reached `0.532749`, `0.289676`, and `0.638494`, respectively.
The level-0 Macro-F1 delta is `+0.119419` in favor of ResNet.

This is development-only evidence. The next scientific action is to freeze the
CNN backbone contract before reopening Dynamic/JS/Residual comparisons.
The formal seven-run queue remains `0/7`; simulated Test, the 15-run formal
comparison, real XRD, real adaptation, and V10 remain locked.
Authoritative report: `xrd_robustness/reports/gate3_pampt_vs_resnet.json`.

## 2026-07-27 split pilots completed (authoritative)

Two user-authorized pilots ran on 2026-07-27 while the registered 7-run queue
stays interrupted at `0/7`.

**Dataset pilot (read-only audit): PASS on all checks.**
`scripts/audit_v9_split_dataset_pilot.py` verified against the authoritative
`split_manifest.json` (SHA-256 `b9d3b72e...`): exact 9,842/2,109/2,109 counts,
maximum crystal-system share deviation 0.000379 (tolerance 0.01), zero
parent-structure or material leakage across 14,060 parents, all seven classes
present in every split, one split per parent, and all 11 persisted view
manifests of the interrupted run contain Validation material IDs only.
Report: `reports/v9_split_dataset_pilot_audit.json`.

**Algorithm pilot (isolated 30-epoch Dynamic ERM): completed, budget filled.**
Launched via `scripts/run_v9_split_pilot_erm.ps1` into the isolated root
`outputs/v9_split_pilot_erm_30e/` (same seed 20260710, contracts, and
hardware profile as registered experiment 1; only epochs=30, max steps
18,480, and no early stopping differ). All 18,480 steps ran;
`data_manifest_hash` confirms the new split; prefetch wait fraction 0.037.
Validation trajectory (ID Macro-F1 / mean single-factor OOD Macro-F1 / gap):
epoch 10 `0.3714 / 0.2967 / 0.075`; epoch 20 `0.4240 / 0.3419 / 0.082`;
epoch 30 `0.4212 / 0.3557 / 0.065`.

**Interpretation under the user's pre-registered criterion (ID 0.6+ means the
old family split was the main problem; ~0.4 means it was not):** ID plateaus
near 0.42 by epoch 20-30, above the old family split's 70-epoch best
(ID 0.3875 / OOD 0.3300) at one third of the budget, so the old split did add
difficulty, but the dominant bottleneck is not the split. Next investigation
targets are backbone capacity, data/simulation quality, and intrinsic task
difficulty. The pilot run is development-only evidence and must not be used
for model selection or checkpoint reuse. Formal 7-run relaunch stays blocked
until the user's computer repair (expected August 2026) and new explicit
authorization.

## 2026-07-27 experiment-1 interruption (authoritative)

The user force-terminated the active new-split tuning run
`ordinary_dynamic_augmentation__tuning_seed_20260710` at about 21:40 on
2026-07-26 in order to repair a computer memory problem. The trainer died
after writing epoch 9 / optimizer step 5,544 to `history.json` and
`last.ckpt`; no Validation evaluation had occurred because the first check is
scheduled at epoch 10. Sixteen orphaned DataLoader workers survived the kill
and were terminated on 2026-07-27 with explicit user authorization; no Python
training process remains and the GPU holds no compute context.

The run directory under
`outputs/v9_method_transfer_tuning_parent_structure_split_v1/` is preserved
intact and the scheduler registry remains `0/7`. The interrupted run is not
countable evidence. Relaunching the queue requires explicit user
authorization plus a decision between a from-step-0 restart and a
deterministic-resume path validated against the checkpoint's global step and
sampler/pair contract hashes. Simulated Test, the 15-run formal comparison,
real XRD, real adaptation, and V10 remain locked.

## 2026-07-26 parent-structure split reset (authoritative)

The chemistry-anonymous Wyckoff-family-disjoint split is retired. The active
dataset contract assigns each parent structure (`CIF` / material) as one
indivisible unit using deterministic random sampling stratified only by the
seven crystal systems: Train 70% (9,842), Validation 15% (2,109), and Test 15%
(2,109), with seed `20260726`.

All clean, weak, strong, ID, and OOD patterns derived from one parent structure
inherit the same split. The regenerated local `split_manifest.json` has SHA-256
`B9D3B72E42EA0FD549DAE34425FF61D2D650D5DD7FE6F337D747CB952CF43293`;
the audit records 14,060 unique parent structures and zero cross-split parent
overlap. `family_id` is not used by the assignment.

Every training result produced under the retired split is invalid for model
selection, checkpoint resume, evaluation, or paper claims. The remaining six
old-split runs are cancelled. New-split tuning is reset to `0/7` and must
restart at experiment 1 from optimizer step zero.

The restart is authorized. The authoritative `xrd_tools` Python 3.11.9 runtime
is available again, and the fresh Train-only candidate-grid Gate passed on the
exact new split without accessing Validation, simulated Test, or real XRD.
The source/configuration change was committed and pushed as
`9eeb972d45574c9b6d49a34d0914879bc8133288`. The registered serial queue was
then launched from the new seven-run plan. Experiment 1,
`ordinary_dynamic_augmentation__tuning_seed_20260710`, is active from optimizer
step zero under the new split and is writing its immutable run contracts and
Validation-only view manifests beneath
`outputs/v9_method_transfer_tuning_parent_structure_split_v1/`. The scheduler
registry remains `0/7` until a run completes; this is an active run, not a
completed result. Simulated Test, formal 15-run training, real XRD, real-domain
adaptation, and V10 remain locked.

## 2026-07-26 queue paused after the first retuning run

The first 10-epoch-Validation / patience-2 tuning run,
`ordinary_dynamic_augmentation__tuning_seed_20260710`, completed and the queue
is now intentionally paused before candidate 2. Early stopping fired at epoch
80 / optimizer step 49,280 after two checks without a primary improvement
greater than `0.001`. The tie-break-selected checkpoint is epoch 70 / step
43,120: mean single-factor Validation-OOD Macro-F1 `0.3300474407481531` and
Validation-ID Macro-F1 `0.3875303685641823`.

The audited `results.json` SHA-256 is
`80C48FF483CA08E4AA567281F1C76F38153E4369DC53889651B4775CD277D7DB`;
the selected `best.ckpt` SHA-256 is
`89D6EFEB6221A3CEA8BFAF73E86A49E2902A82321CAAD8EB7C866CE6FC8ADA73`.
All result values are finite, the run is development/Validation-only, and
simulated Test plus real Test remain locked. Both intentionally suspended
launcher processes were terminated after the result audit; no trainer or
candidate-2 output exists.

The scheduler-owned registry remains `0/7` because the scheduler was suspended
before it could ingest the completed child result. The filesystem has one
audited result and six unstarted candidates. Do not run `tune-select`. When the
user later authorizes continuation, relaunch the registered serial `tune-run`
command; it will detect and register the completed first result before starting
candidate 2.

## 2026-07-26 authoritative 10-epoch Validation override

The user replaced the initial 5-epoch / patience-4 schedule before it produced
any countable tuning result. The superseded queue was stopped at epoch 14 /
optimizer step 8,624 of its first run. It was initially isolated under
`outputs/superseded_v9_tuning_5epoch_patience4_20260726_1859`, then moved to
the Windows Recycle Bin on the user's explicit authorization on 2026-07-26.
The source path is absent; those superseded artifacts are unavailable for
resume and must not be counted.

The active retuning contract keeps the 100-epoch / 61,600-step maximum,
`min_epochs=50`, `min_delta=0.001`, monitor, checkpoint artifacts and
tie-breakers unchanged, but Validation now runs every 10 epochs / 6,160 steps
and patience is 2 Validation checks. The no-improvement window therefore remains
20 epochs while avoiding half of the scheduled Validation passes. All seven
candidates restart from optimizer step 0 in
`outputs/v9_method_transfer_tuning_100e_10epoch_patience2`.

## 2026-07-26 authoritative 100-epoch retuning override

The user has authorized a fresh Validation-only rerun of the complete frozen
seven-candidate V9-T tuning grid under one common early-stopping contract. The
previous 50-epoch, 30,650-step seven-run comparison remains preserved as
historical endpoint evidence; its selected values (`lambda_JS=3.0`,
`lambda_res=2.0`) are not treated as the final selection under the new
optimization contract.

The new contract is frozen as follows:

```text
max_epochs = 100
max_optimizer_steps = 61,600
validation_interval = 5 epochs = 3,080 optimizer steps
min_epochs = 50
monitor = mean single-factor Validation-OOD Macro-F1
mode = max
min_delta = 0.001
patience = 4 validation checks
checkpoint = best + last
tie-break = higher Validation-ID Macro-F1, then earlier epoch
```

All seven candidates restart from optimizer step 0 in
`outputs/v9_method_transfer_tuning_100e_early_stopping`. They share the same
maximum budget, stopping rule, Validation panels, seed, sampler and pair-stream
contract. Because early stopping can produce different realized step counts,
fairness is defined by the common maximum budget and stopping rule plus exact
common-prefix sampler/pair/parameter hashes, not by equal realized compute.
There is no learning-rate scheduler. The measured laptop execution profile
remains strict serial scheduling with 16 DataLoader workers and a 16-batch
prefetch window, eager BF16, TF32, fused AdamW, pinned memory and non-blocking
host-to-device transfer.

At the time this override was written, implementation and preflight evidence
were being finalized and the new registry was `0/7`; no new tuning process had
yet been counted. The 15-run formal comparison, simulated Test, real XRD,
real-domain adaptation and V10 remain unauthorized and locked.

## 1. Research identity

The active project is **V9-T: Algorithm Transfer for PXRD Robustness**.

Its current paper scope is:

> **controlled simulated pretraining, zero-shot experimental robustness, and label-efficient real-domain adaptation for PXRD crystal-system classification.**

The project compares learning principles rather than merely increasing simulated data volume. It is an XRD-specific controlled method-transfer study, not a claim of new general-purpose ML theory.

## 2. Core methods

1. `ordinary_dynamic_augmentation`: Dynamic/Paired ERM;
2. `js_consistency_transfer`: JS Consistency;
3. `residual_decorrelation_transfer`: Residual Class Decorrelation.

Near-clean ERM and frozen offline physical augmentation remain simulation reference baselines.

## 3. Frozen simulation contract

Materials Project structures: **14,060**.

| Split | Count | Role |
|---|---:|---|
| Train | 9,842 | training and dynamic view generation |
| Validation | 2,109 | fixed-budget endpoint lambda and development comparison in the completed tuning; no intermediate early-stopping evidence |
| Test | 2,109 | locked simulated Test |

All methods share the same parent-structure split. Dynamic ERM, JS and Residual also share the same sampler, pair schedule and accepted perturbation parameter-pair stream under matched seeds.

Frozen candidate grids:

```text
lambda_JS  ∈ {0.3, 3.0, 30.0}
lambda_res ∈ {0.2, 2.0, 20.0}
```

Train-only semantics, learned-state and candidate-grid gates have passed. On 2026-07-26 the user explicitly authorized exactly the seven registered Validation-only tuning runs on the measured laptop; this authorization does not extend to the 15-run formal comparison or either locked test.

## 4. Simulation execution state

```text
lambda tuning = 7/7 completed and audited; selected lambda_JS=3.0 and lambda_res=2.0
formal simulation comparison = 0/15
simulated Test = locked, not started
active authoritative checkpoints = 7 completed tuning checkpoints
active training processes = 0
```

The registered tuning target is now the LENOVO 82WM laptop (Ryzen 9 7945HX, RTX 4060 Laptop GPU, 8 GB VRAM). Fresh checks passed for AC power, Python/Torch/CUDA, BF16, dependency integrity, GPU identity and bounded single-run memory. A bounded two-process probe was safe in memory but delivered only 0.838 times serial aggregate throughput, so the performance-maximizing registered scheduler is one run at a time. Live training showed periodic GPU starvation under the initial 8-worker prefetch setting. A strict-equivalence sweep therefore measured 8/8, 12/12, 16/16, 20/20 and 24/24 worker/window settings; 16/16 was fastest and the fresh frozen audit delivered about 32.4 batches/s with exact manifests, parameters, spectra, hashes and quality-gate counts. `torch.compile` is disabled on this target because a fresh probe found no working Triton installation and zero compiled graphs; eager BF16 and fused AdamW remain enabled.

All seven tuning runs must start from optimizer step 0 through the registered launcher. Formal simulation, simulated Test, real XRD and V10 remain separately locked.

The first launcher attempt on 2026-07-26 was deliberately stopped before being counted because the trainer wrote `git_commit.txt` as unavailable even though the authoritative Git root is the parent directory `E:\AI4science`. Its partial checkpoint and run directory were moved intact to `outputs/v9_method_transfer_tuning/aborted_provenance_probe_20260726_1147`; they are not resumable evidence and must not count toward 7/7. The trainer now resolves `git rev-parse HEAD` from the project path, is regression-tested, and the registered queue must restart the first run from optimizer step 0.

Four registered runs have now completed with return code 0. The fifth run,
`residual_decorrelation_transfer__lambda_res_0p2__tuning_seed_20260710`,
completed its frozen 50-epoch, 30,650-step training budget, then failed before
`results.json` while generating the Train-only posthoc residual probe. The
engineering root cause was an invalid manifest split label, `posthoc_train`,
being passed to the perturbation strategy, whose scientific split contract only
permits `train`, `validation`, or `test`. The failed run directory, traceback,
full-step `last.ckpt`, history, manifests, and stream audit were preserved.
The first repair correctly relabeled this Train-only diagnostic as `train`, but
the recovery exposed a second engineering defect: the posthoc manifest persisted
the sampler's first candidate rows without applying the deterministic training
quality-gate retry policy. Replay therefore stopped at `mp-1147626` when its
first candidate failed `window_intensity_below_threshold`. The second failure
evidence is preserved under
`outputs/v9_method_transfer_tuning/failed_posthoc_recovery_evidence_20260726_143311`.
The follow-up repair reuses the same deterministic accepted-row renderer as
training before saving the posthoc manifest. It does not change the model, grid,
seed, optimization budget, completed structure or spectrum exposure, or any
training sampler/pair/parameter hash. The same verified epoch-50 checkpoint may
be resumed only after the follow-up repair is tested, committed, and pushed; the
queue must then finish this same run before starting run 6.

All seven registered runs subsequently completed their frozen 50-epoch,
30,650-step budgets and Validation-only evaluations with return code 0. The
registered queue exited normally and no training process remains. The first
final `tune-select` audit then failed closed on two recovery-path engineering
assumptions. First, tuning prediction rows intentionally use the training mode
(`dynamic_erm`, `dynamic_js`, or `dynamic_residual`) as their statistics identity,
while the auditor incorrectly required the longer contract method ID. Second,
the full-step recovery for Residual lambda=0.2 initialized an empty prediction
sink, skipped the already-complete training loop, and overwrote
`prediction_rows.jsonl` with zero rows. Its checkpoint, history metrics,
Validation manifests, posthoc manifest, and frozen training-stream hashes remain
intact. The audit failure is preserved under
`outputs/v9_method_transfer_tuning/failed_final_tuning_audit_evidence_20260726_1554`.
The engineering repair makes the auditor follow the producer's registered
statistics identity and makes a full-step resume deterministically replay the
completed Validation evaluation, fail unless its metrics exactly match history,
and only then rewrite prediction rows.

After the repair passed 181/181 tests and was committed and pushed, the
Residual lambda=0.2 checkpoint was verified unchanged at
`91e227dd1e7224c9551e065de681036e714b05584549c94544f3522232f20084`.
Its deterministic Validation replay regenerated 23,199 prediction rows and
matched the completed history metrics exactly. The seven-run `tune-select`
audit then passed and selected `lambda_JS=3.0` and `lambda_res=2.0`. All seven
results have 23,199 prediction rows, 30,650 optimizer steps, 490,400 structure
exposures, 980,800 spectrum exposures, matching checkpoint/prediction hashes,
the common sampler/pair/parameter hashes, and locked simulated/real Test
boundaries. The authoritative selection artifact is
`xrd_robustness/reports/v9_method_transfer_tuning_selection.json`. The tuning
queue is stopped. No 15-run formal comparison, simulated Test, real XRD, real
adaptation, or V10 execution is authorized.

### 4.1 Fixed-budget convergence audit

A read-only audit of the seven canonical `history.json` files found that the
50-epoch endpoint is **not convergence-certified**. Although every history has
50 training rows, `validation_interval_steps=30650` means that each run has only
one Validation evaluation, at epoch 50. Each run also retains only the
overwritten `last.ckpt`, so the best Validation epoch, an epoch-50-versus-best
comparison, late Validation ID/OOD slopes, and an overfitting diagnosis are not
recoverable from the completed artifacts.

This is not a hidden-logging issue. The operational contract explicitly sets
`fairness.same_checkpoint_rule=last_fixed_budget_checkpoint`, and the trainer
only enters evaluation when the complete 30,650-step interval is reached. No
TensorBoard/event log, metrics CSV, earlier Validation row, or historical
checkpoint exists in the seven canonical run directories. The final checkpoints
do contain optimizer and RNG state, so a separately authorized future
continuation may be technically possible after deterministic-resume validation,
but they cannot reconstruct earlier epoch models or Validation values.

There is nevertheless a contract-semantic defect that must be resolved before
formal training: `evaluation.validation_role` still says
`hyperparameter_selection_early_stopping_checkpoint_selection_and_development_method_comparison`.
That description conflicts with the executed endpoint-only fixed-budget rule.
The completed selection is valid under the operational rule, but no early
stopping or best-checkpoint claim is supported.

The training-side evidence does not show a late plateau. Ordinary-least-squares
slopes over the last 10 history rows are negative for the classification
objective in all seven runs, with R-squared above 0.90. The selected JS 3.0 run
has the steepest slope, `-0.01438355` per 616 optimizer steps; selected Residual
2.0 is `-0.00700665`. Excluding the partial 466-step final epoch leaves the same
conclusion. All runs still use the initial learning rate `1e-4`; no learning-rate
scheduler is configured.

Therefore the selected values remain valid only as the winners of the frozen,
equal-compute 30,650-step comparison. The evidence neither proves that 50 epochs
is sufficient nor proves that a longer budget would improve Validation. The
formal comparison remains `0/15` and unauthorized. If the formal budget is
changed, the complete candidate grid must be revalidated at the new common
horizon before freezing lambda values; adding a scheduler would be a separate
optimization-contract change requiring fresh tuning. The authoritative audit is
`xrd_robustness/reports/v9_tuning_convergence_audit.json`.

## 5. Real-domain research axis

Before any formal model accessed RRUFF-70, the real-data question was expanded from pure zero-shot evaluation to:

- 0-shot experimental robustness;
- 1/2/3-shot real-domain adaptation efficiency.

Scientific question:

> With identical real support samples, adaptation validation, CE objective and compute, do JS or Residual retain a relative advantage over Dynamic/Paired ERM?

Absolute accuracy may improve for every method; the controlled estimands remain the relative differences against Dynamic ERM.

Decision record:

- `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`

## 6. Frozen RRUFF-70 source and roles

Dataset: `rruff-real-pxrd-70-v1.0-final`, 70 measured mineral powder PXRD profiles, seven crystal systems, 10 per class.

Source manifest SHA-256:

```text
17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5
```

Role assignment occurred before model access using ascending
`SHA256(20260724|crystal_system|sample_id)` within each class:

| Role | Per class | Total |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

Role manifest SHA-256:

```text
32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455
```

Few-shot episode manifest SHA-256:

```text
B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6
```

These manifests and spectra are local Git-ignored data.

## 7. Few-shot design

Each class has frozen adaptation-train ranks 1/2/3:

- 0-shot: no real training data;
- 1-shot: three episodes using rank 1, 2 or 3;
- 2-shot: three episodes using (1,2), (1,3) or (2,3);
- 3-shot: one episode using (1,2,3).

All methods and pretraining seeds use identical episode membership.

Primary adaptation:

- encoder frozen;
- classifier head trainable;
- CE only;
- AdamW;
- LR `[1e-4, 3e-4, 1e-3]`;
- weight decay `1e-4`;
- max 200 epochs;
- patience 30;
- adaptation-validation Macro-F1 selects checkpoint.

Secondary preregistered analysis: full-network CE with LR `[1e-6, 3e-6, 1e-5]`, max 100 epochs and patience 20.

## 8. Implemented real-adaptation engineering

Implemented and committed:

- `configs/real_adaptation.v9.method_transfer.json`;
- `src/xrd_robustness/evaluation/real_adaptation.py`;
- `scripts/audit_v9_real_adaptation_contract.py`;
- `scripts/run_v9_real_adaptation.py` preflight/plan paths;
- `tests/test_v9_real_adaptation_contract.py`;
- updated README, engineering, data, handoff and decision documentation.

The audit is fail-closed and loads neither models nor spectra. It validates CSV hashes, 70 unique samples, 21/14/35 counts, seven-class 3/2/5 balance, train ranks, episode membership and final-test exclusion.

The deterministic planner produces:

- primary: 189 candidate training runs, 63 checkpoint-selection groups, 9 zero-shot evaluations;
- primary + secondary: 378 candidate runs and 126 selection groups.

`run_v9_real_adaptation.py run` currently refuses execution.

## 9. Targeted verification completed

An isolated targeted test run passed 3/3 tests:

- complete role/episode fixture passes without model or spectrum access;
- plan counts are deterministic;
- manifest hash mismatch fails closed.

The actual generated RRUFF split artifacts also passed the same local audit:

- 70 unique samples;
- 21/14/35 role counts;
- every class 3/2/5;
- all seven registered support episodes balanced;
- 14 validation and 35 final-test samples in every episode.

The strict local audit and deterministic plan artifacts are now synchronized:

- `xrd_robustness/reports/v9_real_adaptation_contract_audit.json`
  - status: `locked_contract_and_manifests_pass`;
  - SHA-256: `B598B3E843C429B34F27DF3B2AB5143093ED3FA14298AFD736DEAC3C3611F84E`;
- `xrd_robustness/reports/v9_real_adaptation_plan.json`
  - status: `planned_not_started_execution_disabled`;
  - SHA-256: `C97C02395CE8BA7C44245159F10B0A22A370DEEE9782FBCF3EC17FA38A4FCE4E`.

Neither artifact loads a model or spectrum, performs adaptation, or accesses the
final real test.

The local full repository suite passed **180/180** tests on 2026-07-26.

## 10. Remaining blockers

- implement approved simulation-checkpoint loading;
- implement head-only adaptation training and adaptation-validation selection;
- bind adapted checkpoint and result hashes;
- launch and monitor the authorized seven-run laptop tuning registry;
- after 7/7, stop and audit the registered Validation selection without starting the 15-run formal comparison;
- obtain separate authorizations for adaptation train/validation, the 15-run formal comparison and final tests.

Current locks:

```text
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

## 11. GTIIT status

GTIIT is not part of RRUFF adaptation train, validation or final-test aggregate metrics. It remains a supplementary local-instrument case study requiring de-identification, label evidence, batch/duplicate isolation, provenance and separate authorization.

## 12. Immediate next commands

The two frozen manifests are present in the Git-ignored local data path. The
following commands are safe read-only verification or plan-generation commands:

```powershell
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py --require-local-data
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

No real-data training or final-test inference is currently authorized.

## 13. V10 Train-only diagnostic closure

V10 completed a bounded Train-only evidence chain and is now frozen and
archived:

- the V10-P0 premise gate passed: the learned residual carried independently
  decodable measurement information and crystal-system information;
- Pilot v1 returned `HOLD` because all branches remained near chance;
- Pilot v2 passed its learned-state gate and returned `PARTIAL`;
- measurement-family and multiple measurement-strength signals remained
  decodable, but crystal leakage increased relative to matched V9 residual
  baselines after auxiliary supervision was activated.

The current scientific conclusion is asymmetric: simulator-supervised
measurement representation is feasible, but the unconditional V10 decoder
increased total residual information rather than separating measurement
information from crystal semantics. This is an architecture-level failure mode,
not evidence that more epochs or scalar-weight search would solve the problem.

`xrd_robustness/docs/V10_MODULE_ARCHIVE_AND_FUTURE_DIRECTIONS.md` is the
authoritative archive record. V10 may not be reopened until the frozen V9
validation program is completed and a new explicit scientific decision record
is approved.

## 2026-07-28 ResNet Residual stability Gate (intermediate decision)

The public ResNet-18-GN shared backbone remains frozen as identity preprocessing,
AdamW, and constant learning rate. The Train-only follow-up for the fixed
one-layer detached Residual probe used three preregistered seeds at epochs 3, 5,
and 10. Signal-demonstrated counts were `2/3`, `1/3`, and `2/3`; the rule
required at least `2/3` at both epochs 5 and 10. The result is
`stable_signal_not_demonstrated`.

This is completed diagnostic evidence, not a Validation result: no Validation,
simulated Test, real XRD, checkpoint selection, or 7-run was used. The
Residual path is not eligible for threshold adjustment or larger-lambda
extrapolation. At this intermediate point no candidate range was frozen; the
subsequent JS-only Gate below supersedes that state for JS only. Any further
Residual redesign requires a new explicit scientific decision and Train-only
preregistration.

## 2026-07-28 JS-only scale Gate

The active V9 scientific scope is narrowed to Dynamic ERM versus JS
Consistency. Residual-v1 remains archived as a preregistered negative result.
The single permitted pre-Validation JS range revision `[3,30,60]` passed its
Train-only scale Gate: median auxiliary-to-classification backbone-gradient
ratios were `0.087859`, `0.877058`, and `1.754115`, covering
weak/material-non-dominant/dominant. All finite-value, nonzero-gradient,
combined-direction, and runaway guards passed.

The JS candidate grid is frozen, but execution remains locked. No candidate
training, Validation, simulated Test, real XRD, four-run, or ten-run execution
occurred. The proposed `1 Dynamic + 3 JS` four-run tuning requires a new
explicit authorization.

## 14. Local literature and external resources

The 2026-07-23 opXRD/SIMPOD acquisition was unpacked and classified locally on
2026-07-26:

- opXRD paper and supplement: core XRD perturbation / phase-identification zone;
- SIMPOD paper: XRD AI / crystal-structure benchmark zone;
- opXRD Zenodo archive: 92,552 JSON files and 3,612,139,779 bytes, with extracted
  count and bytes exactly matching the ZIP payload;
- opXRD and SIMPOD source archives: extracted into verified third-party reference
  trees with exact count/byte agreement.

The Git-safe metadata index is
`00_project_context/LITERATURE_LOCAL_RESOURCE_INDEX.md`. PDFs, dataset files,
ZIP archives, and external source trees remain Git-ignored local resources and
have no active V9 role or execution authorization.
