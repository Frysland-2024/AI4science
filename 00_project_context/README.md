# XRD Robustness Project Context

This directory separates **current execution truth** from **historical research evolution**.

## Current truth

Read in this order:

1. `CURRENT_STATE.md`
2. `../xrd_robustness/CODEX_HANDOFF.md`
3. `../xrd_robustness/configs/algorithm.v9.method_transfer.json`
4. `../xrd_robustness/configs/v9_method_parameter_governance.json`

The active split is a deterministic parent-structure-level 70/15/15 split stratified by crystal system: Train 9,842 / Validation 2,109 / Test 2,109.

The current candidate shared backbone is ML4pXRDs ResNet-18-GN. Its Clean diagnostic is complete, but its common Dynamic/JS/Residual training contract is not yet frozen. Validation tuning, formal runs, simulated Test, real XRD, real adaptation, and V10 are locked.

## Historical reasoning

`PROJECT_JOURNEY.md` is the permanent narrative record from FerroAI through the successive XRD versions, including negative evidence, abandoned branches, and the PAMPT-to-ResNet transition. It must not be treated as an executable contract.

Older V6/V7/V8/V9.2 documents remain useful for explaining why the project changed. Superseded executable artifacts and full state snapshots are preserved under `../archive/`.

## Archive policy

- Historical material is moved, not destroyed.
- Archive files are non-executable evidence unless explicitly restored under a new reviewed contract.
- PAMPT learned-state gates and V10 pilots are not evidence for the ResNet backbone.
- Git history is not rewritten.
