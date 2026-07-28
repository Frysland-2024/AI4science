# CNN Dynamic ERM diagnostic summary

**Scope:** development-only Validation evidence; simulated Test and real XRD were not used.

| Metric | Clean | Dynamic ERM | Delta |
|---|---:|---:|---:|
| level0 Macro-F1 | 0.6522 | 0.7197 | +0.0676 |
| in-range Macro-F1 | 0.1827 | 0.7179 | +0.5352 |
| mean single-factor OOD Macro-F1 | 0.4032 | 0.6563 | +0.2532 |
| worst-class F1 | 0.4950 | 0.5810 | +0.0859 |

Best Dynamic checkpoint: epoch 80, global step 49280.

Verdict: matched Dynamic ERM recovers in-range and OOD performance while also improving level0 and worst-class F1. This passes the CNN foundation diagnostic Gate.

The formal seven-run is still 0/7 and locked. No JS, Residual, curriculum, clean anchor, simulated Test, real XRD, 15-run, or V10 execution occurred.
