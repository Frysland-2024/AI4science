# XRD Robustness V9-T

> **2026-07-28 ResNet reset:** PAMPT-B3 was identified as a major foundation bottleneck. The current candidate shared backbone is the audited ML4pXRDs ResNet-18-GN port. All PAMPT-dependent method-weight gates, tuning plans, selections, and V10 learned-state pilots are archived and inactive.

## Research question

Under the same parent structures, physical perturbation views, shared backbone, training budget, and evaluation panels, do:

1. Dynamic/Paired ERM,
2. JS Consistency,
3. Residual Class Decorrelation

differ in their ability to generalize across PXRD measurement shifts?

The project is a controlled XRD-specific method-transfer study, not a claim of a new general-purpose ML theory.

## Current evidence

| Item | State |
|---|---|
| Parent-structure split | Frozen: 9,842 / 2,109 / 2,109 |
| Split leakage audit | PASS |
| ResNet Clean diagnostic | Train 1.0; level0 Macro-F1 0.652168; mean single-factor OOD 0.403163 |
| Shared ResNet method contract | Pending freeze |
| Matched ResNet Dynamic ERM diagnostic | Not completed |
| ResNet JS/Residual scale gate | Not completed |
| Validation tuning | 0/7, disabled |
| Formal comparison | 0/15, disabled |
| simulated Test | Locked |
| real XRD / adaptation | Locked |
| V10 | Archived and locked |

## Active workflow

```text
freeze bounded ResNet Clean contract
  -> one matched ResNet Dynamic ERM diagnostic
  -> minimal Train-only JS/Residual scale gate
  -> new ResNet 7-run Validation tuning
  -> formal multi-seed comparison
  -> locked simulated Test
  -> locked real-XRD evaluation
```

No later stage is automatically authorized by completion of an earlier stage.

## Active entry points

- `CODEX_HANDOFF.md`
- `configs/algorithm.v9.method_transfer.json`
- `configs/v9_method_parameter_governance.json`
- `docs/GATE3_ML4PXRD_RESNET_REPLICATION_PROTOCOL.md`
- `docs/GATE3_ML4PXRD_SOURCE_TO_PORT_MAP.md`
- `reports/gate3_pampt_vs_resnet.json`
- `reports/v9_method_transfer_split_audit.json`
- `reports/v9_method_transfer_preflight.json`

## Safe commands

At this reset point, only read-only checks and unit tests are safe. The old `tune-run` command is not authorized.

```powershell
# Unit tests
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

Any command that trains JS, Residual, runs a seven-run queue, accesses simulated Test, loads real XRD, or executes V10 must fail closed until a new reviewed ResNet contract enables it.

## Archive

Superseded code and reports are retained under `../archive/`:

- `v10_pilot_2026-07/`
- `pampt_v9_p0_2026-07/`
- `pampt_foundation_gates_2026-07/`
- `pampt_v9_tuning_2026-07/`
- `pampt_v9_method_parameter_gates_2026-07/`
- `state_before_resnet_reset_2026-07-28/`

The full scientific development narrative remains in `../00_project_context/PROJECT_JOURNEY.md`.
