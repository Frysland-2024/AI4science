# Foundation Gate 3 — ML4pXRDs 1D ResNet replication and matched backbone test

**Status:** preregistered next conditional Gate  
**Scope:** development-only; Validation panels only  
**Upstream dependency:** interpret the completed Clean PAMPT-B3 100e early-stopping run first

## Scientific question

Is the low Clean crystal-system performance primarily caused by the current PAMPT-B3 backbone, or does the limitation persist when a mature 1D CNN family used in prior pXRD work is placed inside the same data and evaluation pipeline?

This Gate uses the public ML4pXRDs implementation as the source architecture reference, especially:

- `training/utils/resnet_keras_1D.py`;
- `training/models.py::build_model_resnet_i`;
- `training/train_classifier.py`.

The source implementation uses a 1D ResNet family, Group Normalization, a 7/2 stem followed by 3/2 max pooling, residual stages, and a dense classification head. The published training script also uses square-root preprocessing and long training schedules, but those factors are not mixed into the first backbone-only comparison.

## Gate ordering

Gate 3 opens when the final Clean PAMPT-B3 result does not establish adequate base-task learnability.

- If Clean `level0` Validation Macro-F1 is at least `0.80`, Gate 3 is unnecessary; investigate Dynamic training instead.
- If Clean `level0` Validation Macro-F1 is below `0.80`, or remains clearly optimization-limited at the maximum budget, run Gate 3 before any further Dynamic 100e expansion.
- The Dynamic 100e run must not be treated as a prerequisite when Clean itself is weak.

## Stage 3A — source audit and faithful port contract

Before training, record a source-to-port mapping for every architectural decision:

1. stem kernel, stride, padding, channel count;
2. residual block type and repeat counts;
3. downsampling locations and projection shortcuts;
4. Group Normalization placement;
5. activation placement;
6. classifier head;
7. initialization policy;
8. parameter count and receptive-field summary.

The PyTorch port must include automated shape and determinism tests. Any deliberate deviation from ML4pXRDs must be labelled explicitly rather than described as an exact reproduction.

## Stage 3B — sanity gates

The full run is blocked until all checks pass:

1. **Forward/backward gate:** finite logits, loss, and gradients on one real rendered batch.
2. **Tiny-set overfit gate:** at least `95%` training accuracy on a frozen 32-structure Clean subset without augmentation.
3. **Identity gate:** deterministic parameter count, model-config hash, and source-port mapping artifact.
4. **Memory gate:** preserve effective batch size 16. Micro-batching with deterministic gradient accumulation is allowed if required; changing the effective batch is not.
5. **Isolation gate:** no simulated Test, real XRD, or Test-derived model selection.

Failure of the tiny-set overfit gate is an implementation or optimization failure and blocks scientific interpretation.

## Stage 3C — matched Clean backbone comparison

Run a Clean 1D ResNet under the same experimental contract as PAMPT-B3:

- same 9,842/2,109/2,109 parent-structure split;
- same Train and Validation structure IDs;
- same `level0` training profile and rendered input grid;
- same normalization used by the PAMPT Clean run;
- same seed `20260710` and evaluation seed `20260720`;
- same effective batch size 16;
- same maximum 61,600 optimizer steps / 100 epochs;
- same Validation interval every 10 epochs;
- same early-stopping rule: minimum 50 epochs, patience 3 checks, `min_delta=0.002`;
- same AdamW learning rate and weight decay as the PAMPT matched run;
- same `level0`, `in_range`, single-factor OOD, combo OOD, and `ood_all` Validation panels.

The primary Gate metric is best-checkpoint `level0` Validation Macro-F1. Train accuracy and loss are diagnostic, not selection metrics.

### Architecture selection

The first operational baseline will be the closest feasible ML4pXRDs residual-family configuration that preserves the source stem, residual blocks, Group Normalization, and classifier-head logic while fitting the available GPU with effective batch 16.

Candidate order is fixed before Validation is read:

1. ResNet-18-GN;
2. ResNet-10-GN if ResNet-18 cannot satisfy the memory gate;
3. ML4pXRDs `custom_10` only if both standard variants fail the memory gate.

The architecture may not be changed based on Validation score. A ResNet-101 source-faithful run is optional and does not block the Gate because its flatten-plus-dense head may exceed the local memory budget.

## Decision table

Let `Delta = ResNet best level0 Macro-F1 - PAMPT best level0 Macro-F1` under the matched Clean contract.

| Result | Interpretation | Next action |
|---|---|---|
| `Delta >= 0.05` and ResNet Train accuracy is at least `0.10` higher | PAMPT is a major bottleneck | adopt the CNN backbone for the next method comparison; rerun Dynamic only after the backbone decision is frozen |
| `0.02 <= Delta < 0.05` | mixed backbone/optimization evidence | run one preregistered confirmation seed or a parameter-matched CNN; do not claim a resolved bottleneck |
| `Delta < 0.02` and both models remain weak | backbone is not the dominant bottleneck | open Gate 4 input/rendering/task-separability diagnostics |
| ResNet learns Train strongly but Validation remains weak | split-level generalization or task ambiguity | inspect class confusion, structure similarity, and label separability before changing rendering |
| ResNet cannot pass the tiny-set overfit gate | implementation/optimization failure | repair the port; no scientific conclusion |

## Optional source-faithful follow-up

Only after the matched backbone comparison is interpreted, an optional sub-study may add ML4pXRDs-specific training choices one factor at a time:

1. square-root intensity preprocessing;
2. Adam rather than AdamW;
3. the source learning-rate schedule;
4. longer exposure budget;
5. source-style class sampling.

These are not part of the backbone-only Gate because combining them would prevent attribution.

## Required outputs

- source-to-port architecture map;
- unit and tiny-set overfit reports;
- model parameter count and config hash;
- complete `history.json`;
- best and last checkpoints;
- per-class level0 confusion matrix, recall, and F1;
- matched PAMPT-versus-ResNet comparison JSON/Markdown;
- explicit Gate verdict and next authorized action.

## Interpretation boundary

This Gate answers whether a mature 1D CNN backbone materially improves the current Clean pipeline. It does not reproduce the published ML4pXRDs headline score, because the original work used different data generation, task labels, preprocessing, training duration, and compute. It also does not authorize simulated Test, real XRD, the formal seven-run queue, or V10.
