# V10-P0 Measurement-Information Gate

## Purpose

This diagnostic answers one narrow question before any V10 training is allowed:

> Does the current PAMPT-B3 feature residual contain simulator-known measurement information, rather than only crystal-system leakage or unstructured noise?

The diagnostic is deliberately separate from V9 performance evaluation. It cannot select V9 hyperparameters, revise the frozen V9 comparison, open Validation/Test/real XRD, save a checkpoint, or automatically authorize V10.

## Why this Gate exists

The current V9 residual objective only asks the residual to become less predictive of crystal system. That is not sufficient to show that the residual represents measurement variation; a residual can become uninformative simply by collapsing into noise.

V10 would add positive simulator supervision so that a signed residual remains predictive of known perturbation differences while becoming less predictive of crystal class. Before building that method, the project needs evidence that measurement information is actually decodable from the present learned representation.

## Frozen diagnostic protocol

1. Read only the frozen Train split from `data/formal_14060`.
2. Rebuild one five-epoch Dynamic/Paired ERM PAMPT-B3 state in memory.
3. Freeze the backbone and write no checkpoint.
4. Use disjoint, seven-crystal-system-balanced calibration and audit structure pools.
5. For every selected structure, render five controlled pairs:
   - level-0 anchor versus peak shift;
   - level-0 anchor versus broadening;
   - level-0 anchor versus background;
   - level-0 anchor versus noise;
   - level-0 anchor versus texture.
6. Fit detached linear ridge probes only on the calibration structures.
7. Evaluate on unseen audit structures.
8. Compare every signal with grouped permutation baselines.

The same structure is rendered under all five families within a subset. This prevents perturbation-family prediction from being explained by structure identity. Calibration and audit structures never overlap.

## Three checks

### 1. Raw identifiability check

A probe predicts perturbation family from a pooled absolute raw-spectrum difference. If this fails, the simulator labels are not reliably identifiable under the chosen panel and V10 is blocked.

### 2. Residual measurement-information check

Two probes predict perturbation family from (a) the symmetric normalized residual used by V9 and (b) the signed normalized residual intended for V10. The Gate decision uses the signed residual. Per-family ridge regressors also predict normalized perturbation strength from that signed residual.

The minimum measurement-information Gate requires:

- raw perturbation family is identifiable;
- residual perturbation family is identifiable;
- at least two of five strength targets have positive out-of-structure R² and exceed their 95th-percentile permutation baselines.

### 3. Crystal-system leakage check

A separate probe asks whether the same symmetric residual still predicts crystal system on unseen structures. This repeats the other half of the V10 premise under the controlled one-factor panel.

## Status meanings

| Status | Meaning |
|---|---|
| `PASS` | Measurement information is decodable and crystal-system leakage is also present. A V10 pilot is scientifically justified, but not automatically authorized. |
| `PARTIAL` | Some premise is present, but strength decoding or crystal leakage is not sufficiently reproduced. Recheck after formal V9 training if Residual remains relevant. |
| `HOLD` | Raw labels are identifiable, but the frozen five-epoch backbone residual does not yet carry enough measurement information. |
| `BLOCK` | The controlled simulator labels are not identifiable even from raw spectrum differences. Do not build V10 on this target definition. |

A failure at the five-epoch learned state is not a permanent falsification of V10. It means only that V10 should not be unlocked now from this diagnostic.

## Run command

From `E:\AI4science\xrd_robustness`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\run_v10_p0_gate.ps1
```

Default output:

```text
reports\v10_p0_measurement_information_gate.json
```

The PowerShell runner hashes and protects all existing V9 P0 reports before execution.

## Interpretation boundary

This Gate is a representation-diagnostic prerequisite, not a performance claim. Passing does not show that simulator-supervised residual training will improve Validation OOD, simulated Test, or real XRD. It only demonstrates that the proposed V10 supervision has a non-degenerate target in the current representation.
