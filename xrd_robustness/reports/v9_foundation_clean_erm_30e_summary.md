# Foundation diagnostic summary

## Training state

- Final epoch / step: **30 / 18480**
- Final Train accuracy: **0.4990**
- Final Train loss: **1.2503**
- Recent accuracy slope: **0.004424 per epoch**
- Recent loss slope: **-0.010525 per epoch**
- Train still improving: **True**
- Strong underfitting signal: **True**

## Validation trajectory

| Epoch | Train Acc | Train Loss | level0 F1 | in-range F1 | mean single-factor OOD | ID→OOD gap |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.3282 | 1.5936 | 0.2718 | 0.0930 | 0.1796 | -0.0866 |
| 20 | 0.4282 | 1.4010 | 0.4635 | 0.1045 | 0.2604 | -0.1559 |
| 30 | 0.4990 | 1.2503 | 0.4808 | 0.1614 | 0.2827 | -0.1213 |

## Gate result

- Clean level0 Gate: **fail**
- `pass`: level0 Macro-F1 ≥ 0.80
- `partial`: 0.65 ≤ level0 Macro-F1 < 0.80
- `fail`: level0 Macro-F1 < 0.65

## Final level0 per-class metrics

| Crystal system | F1 | Recall |
|---|---:|---:|
| triclinic | 0.5497 | 0.3967 |
| monoclinic | 0.5080 | 0.5795 |
| orthorhombic | 0.4159 | 0.4488 |
| tetragonal | 0.3716 | 0.4086 |
| trigonal | 0.3730 | 0.3500 |
| hexagonal | 0.4505 | 0.4983 |
| cubic | 0.6969 | 0.6358 |

## Final in-range per-class metrics

| Crystal system | F1 | Recall |
|---|---:|---:|
| triclinic | 0.4345 | 0.8233 |
| monoclinic | 0.1981 | 0.3377 |
| orthorhombic | 0.1190 | 0.1221 |
| tetragonal | 0.0856 | 0.0532 |
| trigonal | 0.0846 | 0.0567 |
| hexagonal | 0.0967 | 0.0532 |
| cubic | 0.1118 | 0.0596 |

## Interpretation boundary

This report is descriptive development evidence only. It does not select a checkpoint,
open simulated Test, access real XRD, or authorize the formal 7-run stage.
