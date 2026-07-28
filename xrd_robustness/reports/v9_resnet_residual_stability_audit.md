# V9 ResNet Residual stability audit

Train-only fixed-probe follow-up, completed 2026-07-28.

| Milestone | Signal-demonstrated seeds | Required | Result |
|---|---:|---:|---|
| Epoch 3 | 2/3 | Informational | mixed |
| Epoch 5 | 1/3 | 2/3 | failed |
| Epoch 10 | 2/3 | 2/3 | passed |

The preregistered decision requires at least 2/3 signal-demonstrated seeds at
both epochs 5 and 10. Overall status: `stable_signal_not_demonstrated`.

No Validation, simulated Test, real XRD, checkpoint selection, candidate
training, or 7-run execution occurred. Residual lambda candidate reopening is
not authorized. The machine-readable per-seed, per-class-F1, confusion-matrix,
residual-norm, and gradient-scale evidence is
`v9_resnet_residual_stability_audit.json`.
