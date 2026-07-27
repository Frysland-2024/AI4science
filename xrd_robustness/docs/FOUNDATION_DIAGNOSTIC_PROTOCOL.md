# V9-T Foundation Diagnostic Protocol

**Status:** development-only diagnostic protocol  
**Branch:** `diagnostics/foundation-gates`  
**Starting point:** commit `b40b92f1361b962f730b96292bc9642706a54f90`

## Purpose

The new parent-structure split pilot established that the old family-disjoint
split was not the dominant reason for the low score. The next task is to isolate
four possible bottlenecks without changing several variables at once:

1. insufficient training/optimization;
2. PAMPT-B3 backbone suitability;
3. rendering, angular resolution, or normalization;
4. excessive difficulty in the joint dynamic perturbation distribution.

This protocol is diagnostic only. It does not authorize the registered 7-run
queue, the formal 15-run comparison, simulated Test, real XRD, real adaptation,
or V10.

## Non-negotiable rule

Each Gate changes only one scientific factor. A later Gate is opened only when
the previous result does not already resolve the question.

## Gate 1 — Can the current pipeline learn minimally perturbed spectra?

### Code

- Launcher: `scripts/run_v9_clean_foundation_pilot.ps1`
- Report generator: `scripts/diagnostics/summarize_training_run.py`

### Frozen factors

The launcher keeps the same parent-structure split, seed, PAMPT-B3 variant,
optimizer defaults, batch size, evaluation seed, validation subset, hardware
profile, maximum optimizer steps, and validation interval as the completed
30-epoch Dynamic ERM split pilot.

### Single changed factor

Training mode changes from `dynamic_erm` to `clean_erm`, using the existing
`level0` profile. `level0` is a minimally perturbed reference profile, not an
absolutely noise-free mathematical delta pattern: it keeps FWHM 0.08 degrees
and high-count Poisson observation.

### Required evaluation panels

- `level0`: direct clean-task learnability;
- `in_range`: matched comparison with Dynamic ERM;
- the six single-factor OOD panels;
- the three combo panels;
- `ood_all`.

### Decision

| Final level0 Validation Macro-F1 | Gate result | Next action |
|---:|---|---|
| `>= 0.80` | PASS | Current rendering and PAMPT can learn the base task; inspect Dynamic training/optimization next. |
| `0.65–0.80` | PARTIAL | Check whether Train loss/accuracy are still improving; extend the same Clean run budget before changing the backbone. |
| `< 0.65`, Train still improving | INCONCLUSIVE UNDERTRAINED | Run a fresh matched 100-epoch Clean diagnostic. |
| `< 0.65`, Train plateaued | FAIL | Open backbone/input diagnostics; do not blame Dynamic perturbation first. |

The report script defines a strong underfitting signal conservatively as final
Train accuracy below 0.60 while recent Train accuracy rises and Train loss
falls. This is a diagnostic flag, not a paper claim.

## Gate 2 — Is the original Dynamic ERM merely undertrained?

Gate 2 code is intentionally not activated until Gate 1 is interpreted.

The planned experiment is a fresh PAMPT-B3 Dynamic ERM diagnostic with the
same learning rate and no scheduler, extended to 100 epochs. No learning-rate,
backbone, rendering, or perturbation change may be introduced in that run.

## Gate 3 — Is PAMPT-B3 the bottleneck?

Gate 3 is opened only if the Clean/Dynamic evidence cannot be explained by
training budget alone. A conventional 1D ResNet/FCN baseline will be added and
compared under the same input, split, pair stream, optimizer-step budget, seed,
and evaluation panels.

## Gate 4 — Is information being lost before the model?

Gate 4 is opened only if both PAMPT and the CNN baseline perform poorly on the
minimally perturbed task. Checks will be implemented in this order:

1. label and peak-table/render alignment;
2. angular-grid step and samples per minimum-FWHM peak;
3. max normalization versus area normalization;
4. simple-model separability and tri/hex/tet overlap.

## Execution command for Gate 1

From PowerShell:

```powershell
cd E:\AI4science\xrd_robustness
git switch diagnostics/foundation-gates
& .\scripts\run_v9_clean_foundation_pilot.ps1
```

The launcher refuses to overwrite an existing diagnostic directory and refuses
to start while another `train_v7.py` process is active.

## Report artifacts

The run directory will contain:

```text
foundation_diagnostic_summary.json
foundation_diagnostic_summary.md
```

The summary is generated from existing `history.json` only. It does not load a
checkpoint or access locked data.
