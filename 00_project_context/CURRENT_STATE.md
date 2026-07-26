# AI4science Current State

**Canonical status date:** 2026-07-26
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> Current-state record only. Historical reasoning remains in `PROJECT_JOURNEY.md` and dated decision files.

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
| Validation | 2,109 | lambda, early stopping, checkpoint and development comparison |
| Test | 2,109 | locked simulated Test |

All methods share the same mother-structure/family split. Dynamic ERM, JS and Residual also share the same sampler, pair schedule and accepted perturbation parameter-pair stream under matched seeds.

Frozen candidate grids:

```text
lambda_JS  ∈ {0.3, 3.0, 30.0}
lambda_res ∈ {0.2, 2.0, 20.0}
```

Train-only semantics, learned-state and candidate-grid gates have passed. On 2026-07-26 the user explicitly authorized exactly the seven registered Validation-only tuning runs on the measured laptop; this authorization does not extend to the 15-run formal comparison or either locked test.

## 4. Simulation execution state

```text
lambda tuning = 4/7 completed; run 5 second recovery pending
formal simulation comparison = 0/15
simulated Test = locked, not started
active authoritative checkpoints = 1 verified recovery checkpoint
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
