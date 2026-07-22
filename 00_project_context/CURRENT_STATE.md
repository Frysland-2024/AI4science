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

The remaining verification gap is narrower: the code implements epoch-boundary checkpoint resume and deterministic future schedule reconstruction, but the repository does not yet contain a dedicated end-to-end resume integration test that interrupts a real training run, reloads the checkpoint, and proves that the subsequent batch IDs and dynamic view-pair hashes match an uninterrupted reference run.

## 8. Engineering gate status before tuning

| Gate | Current status |
|---|---|
| Dynamic parameter rows remain batch/prefetch bounded | **PASS** |
| Same dynamic coordinate replays identical parameters | **PASS** |
| Dynamic ERM, JS, and Residual receive the same paired-view schedule | **PASS** |
| View 1 and View 2 remain separately sampled for one mother structure | **Implemented; unit-level evidence present** |
| Checkpoint resume restores model, optimizers, modules, Torch CPU/CUDA RNG, epoch and stream audit | **Implemented** |
| Resumed future view sequence matches uninterrupted execution end-to-end | **PARTIAL: logic and audit-snapshot test exist; dedicated integration evidence still missing** |
| Validation and Test IDs are excluded from dynamic training | **PASS** |
| Optimizer-step and pattern-forward budgets match across methods | **PASS** |
| Current reports match the frozen configuration and source hashes | **PASS in the recorded preflight; rerun after any code change** |

A failed mandatory gate blocks training authorization.

## 9. Immediate next actions

1. Add a bounded **checkpoint-resume determinism integration test** at an epoch boundary.
2. Compare uninterrupted versus resumed execution for:
   - next batch material IDs;
   - dynamic parameter-pair hashes;
   - training-stream audit snapshot;
   - checkpoint global step and epoch;
   - optionally the next-step loss/model state under deterministic CUDA settings.
3. Save the result as a machine-readable `v9_resume_determinism_audit.json`.
4. Rerun the full unit suite and V9 training-stream preflight after the test is added.
5. Run a bounded engineering pilot only after the resume gate passes.
6. Begin the seven-run lambda tuning only after explicit user authorization.

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
