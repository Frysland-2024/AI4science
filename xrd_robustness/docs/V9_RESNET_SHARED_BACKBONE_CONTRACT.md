# V9 ResNet shared-backbone contract

## Frozen public backbone

Dynamic ERM, JS Consistency, and Residual Class Decorrelation must share:

- ML4pXRDs ResNet-18 with GroupNorm;
- identity intensity preprocessing;
- AdamW, learning rate `1e-4`, weight decay `1e-4`;
- constant learning rate;
- batch size 16;
- the active parent-structure split and frozen simulator;
- maximum 100 epochs / 61,600 optimizer steps;
- Validation every 6,160 steps;
- minimum 50 epochs, patience 3, `min_delta=0.002`, primary profile `level0`.

Dynamic/Paired ERM is the strong public baseline. JS and Residual may differ
only by their registered auxiliary objective and the lambda selected under the
same ResNet contract.

## Lambda Gate reset

PAMPT-B3 lambda evidence is historical archive evidence only. Its selected
`lambda_JS=3` and `lambda_res=2` cannot be inherited by ResNet.

The minimal ResNet Gate uses Train only. It first demonstrates a learned
classification state and a competent detached residual probe, then measures
the actual JS and Residual losses and backbone gradients. The PAMPT grids
`[0.3, 3, 30]` and `[0.2, 2, 20]` are initially scale probes only. They become
ResNet candidates only if direct ResNet autograd measurements cover weak,
material non-dominant, and dominant influence under the frozen bands.

Validation, simulated Test, real XRD, candidate training, and checkpoint
selection are forbidden during this Gate. The 7-run remains disabled until
the Train-only report freezes a ResNet-specific candidate range.

## 2026-07-28 Train-only Gate result

The classification learned-state Gate passed, but the epoch-5 detached
residual probe competence Gate did not. Direct candidate-specific autograd
measurements found:

| Method | Probe grid | Observed median influence bands |
|---|---|---|
| JS | `[0.3, 3, 30]` | negligible / weak / material non-dominant |
| Residual | `[0.2, 2, 20]` | negligible / negligible / weak |

Therefore neither PAMPT-derived grid covers weak, material non-dominant, and
dominant influence on ResNet. No ResNet candidate range is frozen, no larger
Residual values are inferred from an incompetent probe state, and the 7-run
remains disabled.
