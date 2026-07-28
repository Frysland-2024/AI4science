# XRD Robustness V9-T — Current Handoff

**Status date:** 2026-07-28  
**Current backbone candidate:** ML4pXRDs ResNet-18-GN  
**Execution state:** all method tuning and final evaluation locked

## Read this first

The repository has completed a **PAMPT-to-ResNet foundation reset**. Historical PAMPT and V10 artifacts are preserved under `../archive/`, but they are not active execution inputs.

## Current evidence

- ResNet Clean: Train accuracy `1.0`, level0 Macro-F1 `0.652168`, mean single-factor OOD Macro-F1 `0.403163`.
- PAMPT Clean: `0.638494`, `0.532749`, `0.289676`.
- Active split: 9,842 / 2,109 / 2,109 parent structures, seed `20260726`, zero parent/material leakage.
- Formal V9 comparison: `0/15`.
- Validation lambda tuning: `0/7`, disabled.
- Simulated Test, real XRD, real adaptation, and V10: locked.

## What remains valid

The data split, simulation physics, evaluation panels, Test isolation, sampler/provenance principles, and the core Dynamic/JS/Residual research question remain valid.

## What must not be reused

- PAMPT learned-state gradient ratios;
- PAMPT JS/Residual candidate-grid qualification;
- PAMPT lambda selections or checkpoints;
- V10 learned-state conclusions;
- superseded tuning launch commands.

## Next engineering action

Generalize and freeze the ResNet wrapper so the same ResNet-18-GN construction can run `clean_erm`, `dynamic_erm`, `dynamic_js`, and `dynamic_residual` without monkey-patching ambiguity. Then run exactly one matched Dynamic ERM diagnostic.

## Next scientific gate

After the ResNet Dynamic diagnostic:

- freeze the shared backbone if Clean/Dynamic behavior is stable and interpretable;
- rerun a minimal Train-only JS/Residual scale audit on the learned ResNet state;
- keep Validation, simulated Test, and real XRD untouched until the new gate is frozen.

## Active files

- `configs/algorithm.v9.method_transfer.json`
- `configs/v9_method_parameter_governance.json`
- `docs/GATE3_ML4PXRD_RESNET_REPLICATION_PROTOCOL.md`
- `docs/GATE3_ML4PXRD_SOURCE_TO_PORT_MAP.md`
- `reports/gate3_pampt_vs_resnet.json`
- `reports/v9_method_transfer_split_audit.json`
- `reports/v9_method_transfer_preflight.json`

Historical project reasoning remains in `../00_project_context/PROJECT_JOURNEY.md`.
