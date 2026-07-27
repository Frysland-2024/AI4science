# Gate 3: PAMPT versus ML4pXRDs ResNet-18-GN

- Verdict: **pampt_major_bottleneck**
- Next action: **Freeze the CNN backbone for the next method comparison; only then reopen Dynamic training under a matched backbone contract.**

| Metric | PAMPT-B3 | ResNet-18-GN | Delta |
|---|---:|---:|---:|
| level0 Macro-F1 | 0.5327 | 0.6522 | 0.1194 |
| Train accuracy at stop | 0.6385 | 1.0000 | 0.3615 |
| in-range Macro-F1 | 0.0937 | 0.1827 | — |
| mean single-factor OOD Macro-F1 | 0.2897 | 0.4032 | — |

- ResNet best epoch: **100**
- ResNet stop epoch: **maximum budget**
- ResNet parameter count: **13008839**

## ResNet level0 per-class metrics

| Crystal system | F1 | Recall |
|---|---:|---:|
| triclinic | 0.6831 | 0.6933 |
| monoclinic | 0.4950 | 0.4934 |
| orthorhombic | 0.5355 | 0.5347 |
| tetragonal | 0.6561 | 0.6213 |
| trigonal | 0.6186 | 0.6433 |
| hexagonal | 0.6879 | 0.6811 |
| cubic | 0.8889 | 0.9007 |

Development-only matched-backbone evidence. Simulated Test, real XRD, the formal seven-run queue, and V10 remain locked.
