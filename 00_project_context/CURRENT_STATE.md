# AI4science Current State

**Canonical status date:** 2026-07-24  
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

Train-only semantics, learned-state and candidate-grid gates have passed. This does not authorize training.

## 4. Simulation execution state

```text
lambda tuning = 0/7
formal simulation comparison = 0/15
simulated Test = locked, not started
active authoritative checkpoints = 0
active training processes = 0
```

Formal desktop runs must start from optimizer step 0 after target-machine acceptance and explicit authorization.

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

The full repository test suite has not been run through the GitHub connector; it must be rerun in the local worktree.

## 10. Remaining blockers

- copy the frozen manifests into the project Git-ignored path;
- run strict `--require-local-data` preflight in `E:/AI4science`;
- implement approved simulation-checkpoint loading;
- implement head-only adaptation training and adaptation-validation selection;
- bind adapted checkpoint and result hashes;
- finish target-desktop acceptance;
- obtain separate authorizations for 7-run, adaptation train/validation and final real test.

Current locks:

```text
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

## 11. GTIIT status

GTIIT is not part of RRUFF adaptation train, validation or final-test aggregate metrics. It remains a supplementary local-instrument case study requiring de-identification, label evidence, batch/duplicate isolation, provenance and separate authorization.

## 12. Immediate next commands

After copying the two frozen manifests into
`E:/AI4science/xrd_robustness/data/real_xrd/rruff70/manifests/`:

```powershell
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py --require-local-data
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

No real-data training or final-test inference is currently authorized.
