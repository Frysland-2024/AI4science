# Sealed Future Research Modules

This directory records research directions that are scientifically designed but
are not part of the active execution contract.

A module in this directory must not automatically:

- reopen a completed method-selection decision;
- alter frozen V9 configurations or selected checkpoints;
- access simulated Test or real XRD;
- trigger implementation or training;
- be cited as an experimental result.

## Registered modules

| Module | Status | Relationship to active V9 |
|---|---|---|
| [PXRD Measurement Parameter Inversion and Calibration](PXRD_MEASUREMENT_PARAMETER_INVERSION.md) | `SEALED_FUTURE_MODULE` | Complementary future project: explicitly infer and calibrate measurement nuisance parameters, while V9 learns measurement-robust classification through JS Consistency |
| [Scientific Signal Tokenization and Backbone–Augmentation Compatibility](SCIENTIFIC_SIGNAL_TOKENIZATION_AND_BACKBONE_COMPATIBILITY.md) | `SEALED_FUTURE_MODULE` | Explains why the earlier peak-aware Transformer/PAMPT underperformed the frozen ResNet backbone and studies whether scientific-signal tokenization, hybrid CNN-attention representations, and perturbation-compatible inductive bias can improve it without reopening V9 |

## Activation rule

Activation requires a separate dated decision that defines scope, data access,
pre-registration, leakage controls, success criteria, and compute budget. Until
then, module documents preserve research reasoning and application narrative
only.
