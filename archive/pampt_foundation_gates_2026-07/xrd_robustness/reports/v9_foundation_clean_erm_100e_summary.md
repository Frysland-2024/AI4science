# Clean early-stopping diagnostic summary

- Gate: **fail_validation_plateau**
- Stopped early: **True**
- Best epoch / step: **70 / 43120**
- Stop epoch: **100**
- Stop reason: **no primary improvement greater than 0.002 for 3 validation checks**
- Selected best level0 Macro-F1: **0.5327**
- Selected best in-range Macro-F1: **0.0937**
- Selected best mean single-factor OOD Macro-F1: **0.2897**
- Train accuracy/loss at stop: **0.6385 / 0.9154**
- Train still improving at stop: **False**

## Selected best level0 per-class metrics

| Crystal system | F1 | Recall |
|---|---:|---:|
| triclinic | 0.6618 | 0.6100 |
| monoclinic | 0.5223 | 0.6192 |
| orthorhombic | 0.4397 | 0.4455 |
| tetragonal | 0.3916 | 0.3422 |
| trigonal | 0.4499 | 0.4867 |
| hexagonal | 0.4856 | 0.4485 |
| cubic | 0.7781 | 0.7781 |

## Interpretation

- `pass`: selected best level0 Macro-F1 >= 0.80
- `partial`: 0.65 <= selected best level0 Macro-F1 < 0.80
- `fail_validation_plateau`: selected best level0 Macro-F1 < 0.65 and the registered early-stopping rule fired
- `inconclusive_max_budget`: selected best level0 Macro-F1 < 0.65, maximum budget was reached, and Train was still improving

Development-only evidence; simulated Test and real XRD remain locked.