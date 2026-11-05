# ResNet A0 / A1 / A2 × R0 / R1: architecture-conditioned full-budget comparison

Experiment is **V10-only** (all six cells same simulator, parent-disjoint 14,060-parent corpus, identical Validation panels, same seed 20260711).
All new cells trained for **49,280 optimizer steps** with Validation every 6,160 steps; A0_R0 reuses its verified completed historical V10 training.

**R0** = AdamW LR=1e-4, constant. **R1** = AdamW LR=2e-4, cosine decay to 5% floor over the entire 49,280-step horizon.
All cells retain paired CE + same-parent JS λ=60, weight decay 1e-4, batch16 parents; there was no RRUFF or Test tuning.
R1 is a *bundled* learning-rate-plus-scheduler recipe, not a factorial test separating those two mechanisms.

| Cell | Stage strides | Kernel | Initial LR | Schedule | Parameters | Best Val OOD F1 | Best step | Val OOD F1 @49,280 | Training seconds |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| A0_R0 | 4/4/4 | 9 | 1e-04 | none | 13,008,839 | 0.70899 | 30,800 | 0.70733 | 1393 |
| A0_R1 | 4/4/4 | 9 | 2e-04 | cosine_5pct_floor | 13,008,839 | 0.73183 | 43,120 | 0.73140 | 3091 |
| A1_R0 | 4/2/4 | 9 | 1e-04 | none | 14,843,847 | 0.70805 | 43,120 | 0.69662 | 3233 |
| A1_R1 | 4/2/4 | 9 | 2e-04 | cosine_5pct_floor | 14,843,847 | 0.72192 | 49,280 | 0.72192 | 3294 |
| A2_R0 | 4/2/4 | 5 | 1e-04 | none | 9,961,415 | 0.69515 | 36,960 | 0.69092 | 3975 |
| A2_R1 | 4/2/4 | 5 | 2e-04 | cosine_5pct_floor | 9,961,415 | 0.70994 | 43,120 | 0.70848 | 2761 |

## Provisional result (single seed)

- Highest Validation OOD Macro-F1: **A0_R1**, score **0.73183**.
- Difference versus historical A0_R0 best Validation checkpoint: **+0.02284**.
- All results are single-seed and descriptive; a strong architecture claim requires replicate seeds for the chosen pair.
- Architecture and learning-rate/scheduler are compared jointly, not sequentially screening off an architecture at 12,320 steps.
- The 49,280-step ceiling does not prove mathematical convergence. Compare full learning curves and select predeclared best Validation checkpoint.
- A2 vs A1 changes residual kernel and model size, while A0 vs A1 changes stage stride and flatten-head size. Report compute cost too.
- Simulator V11/PR #59 is **NOT** part of these comparisons; no cross-simulator score comparison is used.

## Evidence and provenance

- All reported scores derive from machine-readable per-trial full-run result JSON and eight fixed Validation evaluations.
- Model checkpoint SHA256 recorded in summary; no trained weights or large validation matrices uploaded.
- Original historical V10 files and previous A1/A2 12,320-step pilot remain unchanged.
- This is an experiment snapshot that references local XRD package modules, not yet a production merge of trainer implementation.
