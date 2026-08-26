# CNRS-318 zero-shot evaluation — results

**Date:** 2026-08-27

**Domain:** CNRS-318 (naturally imbalanced independent experimental domain, 318 structural parents).
**Primary analysis:** zero-shot external evaluation of the frozen models (no CNRS label used for adaptation).

## Headline

JS shows a **consistent direction but not a statistically robust effect** on CNRS-318:
all five seeds favor JS, but the 95% class-stratified paired interval crosses zero.

| Quantity | Value |
| --- | --- |
| Mean paired Δ = Macro-F1(JS) − Macro-F1(ERM) | **+0.0187** |
| Positive seeds | **5 / 5** |
| Class-stratified paired 95% CI | **[−0.0149, +0.0521]** |
| Frozen interpretation | **directional support** (not stable replication) |

## Per-seed paired Macro-F1

| seed | Dynamic ERM | JS | Δ |
| --- | ---: | ---: | ---: |
| 20260711 | 0.2067 | 0.2212 | +0.0145 |
| 20260712 | 0.1469 | 0.1756 | +0.0286 |
| 20260713 | 0.1842 | 0.1971 | +0.0129 |
| 20260714 | 0.2149 | 0.2295 | +0.0147 |
| 20260715 | 0.1892 | 0.2120 | +0.0228 |

## Aggregate metrics (five seeds pooled)

| Metric | Dynamic ERM | JS |
| --- | ---: | ---: |
| Macro-F1 | 0.1912 | 0.2091 |
| Balanced accuracy | 0.2182 | 0.2388 |
| Overall accuracy | 0.2000 | 0.2101 |
| ECE | 0.6826 | 0.6124 |
| Worst-class F1 | 0.0968 | 0.1015 |

## Per-class F1 (five seeds pooled; support = parents)

| Crystal system | n | ERM F1 | JS F1 |
| --- | ---: | ---: | ---: |
| triclinic | 21 | 0.1474 | 0.1767 |
| monoclinic | 87 | 0.2928 | 0.2801 |
| orthorhombic | 77 | 0.1123 | 0.1811 |
| tetragonal | 41 | 0.2984 | 0.2362 |
| trigonal | 33 | 0.0968 | 0.1015 |
| hexagonal | 12 | 0.1667 | 0.2500 |
| cubic | 47 | 0.2238 | 0.2383 |

## Honest interpretation and caveats

- **Direction is consistent (5/5) but the effect size is small and the interval crosses
  zero.** Per the frozen interpretation table this is "directional support on CNRS", not
  "stable replication". This is not a negative result and does not demote CNRS-318.
- **Absolute performance is low** (Macro-F1 ≈ 0.19–0.21, accuracy ≈ 0.20 vs. 0.143 random
  for seven classes). This is expected for a zero-shot simulated→experimental transfer; it
  is a large domain gap, not a defect of the protocol.
- **ECE is high** (0.68 ERM / 0.61 JS): the models are over-confident out of domain, a
  typical zero-shot signature.
- **Tetragonal is the one class where ERM looks better** (0.298 vs. 0.236); JS misroutes
  many tetragonal patterns to trigonal (adjacent diffraction families). Worth a note, not a
  per-class strong claim.
- **Hexagonal (n=12) remains underpowered**; its F1 swing (0.167→0.250) is noisy and must
  not be read as a strong per-class conclusion.

## Reproducibility

- Inputs: `outputs/cnrs318_zero_shot/cnrs318_inputs.npz` (318 × 3501, float32), SHA-256
  `980965E95E8A4CFC9020CB1C64976E0B4E95735A7DEFD990407863161C45D7C6`.
- Predictions: `outputs/cnrs318_zero_shot/predictions.ndjson` (3180 rows), SHA-256
  `DE9AE0A3A7C60D84AD8F4DD1083A00811A5A387BD68F3DE49DAF60B81B09A160`.
- Eval manifest: `manifests/cnrs318_eval_manifest.csv`, SHA-256
  `373DDD5FDC9FE5BB879D242C58CDB4969D50FA69AB009383AA6C96416A6A2A98`.
- Bootstrap: class-stratified paired parent, 10,000 replicates, seed 20260827.
