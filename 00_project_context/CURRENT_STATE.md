# AI4science Current State

**Canonical status date:** 2026-07-28  
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> This file contains current executable truth only. Historical reasoning remains in `PROJECT_JOURNEY.md`; superseded code, reports, and contracts are preserved under `archive/`.

## 1. Active scientific state

The active project is **V9-T: Algorithm Transfer for PXRD Robustness**.

Foundation Gate 3 showed that PAMPT-B3 was a major backbone bottleneck. Under the matched Clean diagnostic:

| Backbone | Train accuracy | level0 Macro-F1 | mean single-factor OOD Macro-F1 |
|---|---:|---:|---:|
| PAMPT-B3 | 0.638494 | 0.532749 | 0.289676 |
| ML4pXRDs ResNet-18-GN | 1.000000 | 0.652168 | 0.403163 |

This is development-only evidence. ResNet-18-GN is the current **candidate shared backbone**, not yet a frozen formal contract.

## 2. Frozen backbone-independent contracts

- Parent-structure split: Train 9,842 / Validation 2,109 / Test 2,109.
- Split seed: `20260726`.
- Zero parent/material leakage; all seven crystal systems appear in every split.
- Frozen XRD simulation ranges and evaluation panels remain active.
- Simulated Test and real XRD remain locked.
- Core comparison remains Dynamic/Paired ERM vs JS Consistency vs Residual Class Decorrelation.

## 3. Invalidated by the backbone change

The following PAMPT-dependent evidence is historical only:

- Train-only learned-state and gradient-scale gates;
- JS grid `[0.3, 3, 30]` and Residual grid `[0.2, 2, 20]` as active ResNet ranges;
- PAMPT Validation tuning plans, selections, checkpoints, and convergence reports;
- V10 P0 / Pilot / Pilot v2 learned-state conclusions.

These materials were moved to `archive/`; their content was preserved.

## 4. Execution locks

```text
ResNet shared training contract = pending freeze
matched ResNet Dynamic ERM diagnostic = not completed
ResNet JS/Residual Train-only scale gate = not completed
Validation tuning = 0/7 and disabled
formal simulation comparison = 0/15 and disabled
simulated Test = locked
real XRD / real adaptation = locked
V10 = archived and locked
```

No PAMPT launcher, PAMPT lambda, or archived checkpoint may be reused as current ResNet evidence.

## 5. Immediate sequence

1. Complete the bounded Clean configuration diagnostic and stop further Clean search.
2. Freeze one ResNet-18-GN preprocessing/optimizer/schedule contract.
3. Run exactly one matched ResNet Dynamic ERM diagnostic.
4. If the shared backbone remains scientifically usable, rerun the minimal Train-only JS/Residual scale gate.
5. Only then create a new ResNet seven-run Validation plan.

Authoritative active contracts:

- `xrd_robustness/configs/algorithm.v9.method_transfer.json`
- `xrd_robustness/configs/v9_method_parameter_governance.json`
- `xrd_robustness/docs/GATE3_ML4PXRD_RESNET_REPLICATION_PROTOCOL.md`
- `xrd_robustness/docs/GATE3_ML4PXRD_SOURCE_TO_PORT_MAP.md`
- `xrd_robustness/reports/gate3_pampt_vs_resnet.json`
