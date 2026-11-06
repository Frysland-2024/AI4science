# SimXRD / CNN11 pilot — 2026-11-03

> **Integrity hold (2026-11-03):** V10-labelled training and validation views in the initial pilot used the V9 Gaussian renderer, and CNN11 dropout stayed disabled after its first validation. This PR fixes the integration paths and adds regression tests, but the reported V10 and CNN11 outputs were produced before the fixes. Do not interpret those metrics as a valid V10/CNN11 comparison until the panels and runs are regenerated. No rerun has been performed. The standalone renderer smoke checks did not verify the full generation paths.

## Archive status

This directory preserves the pre-fix attempt for provenance and debugging. Its checkpoints and derived metrics cannot support the V10/CNN11 comparison. The [corrected rerun checklist](../../../docs/PXRD_SIMXRD_CNN11_PILOT_20261103.md#corrected-rerun-checklist--pending-execution) identifies the replacement artifacts and evidence gates.

## Artifacts

- [`results.json`](results.json): full per-seed, per-profile simulated Test and RRUFF metrics, confusion matrices, protocol hashes, and training-completeness status.
- [`model_selection_freeze.json`](model_selection_freeze.json): checkpoint, protocol, data, and RRUFF manifest hashes captured before evaluation.
- [`smoke.json`](smoke.json) and [`smoke.log.jsonl`](smoke.log.jsonl): physical and runtime smoke evidence.
- [`cnn11_v10_training_failure.json`](cnn11_v10_training_failure.json): failure record and finite checkpoint details.
- [`logs/`](logs/): raw JSONL training logs; [`validation/`](validation/): validation histories; [`runs/`](runs/): per-seed result records.
- `resnet18gn_v10_training_results.json` and `cnn11_v10_training_results.json`: new-model run records.
- `preflight_failures.jsonl`: two initial configuration/version-string smoke preflight errors, preserved with their corrections.

