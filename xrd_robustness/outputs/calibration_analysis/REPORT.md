# Calibration audit — frozen Dynamic ERM vs JS

This is a **post-hoc secondary analysis**. No model was trained, tuned, or selected by this script.

## Simulated Test

Matched evaluation conditions: **180**.
Calibration interpretation: **support_with_heterogeneity**.

| Metric | Dynamic ERM | JS Consistency | Mean paired Δ (JS−ERM) | Better-direction pairs |
|---|---:|---:|---:|---:|
| macro_f1 | 0.618282 | 0.671078 | +0.052796 | 176/180 |
| accuracy | 0.618242 | 0.672075 | +0.053833 | 179/180 |
| ece | 0.289934 | 0.204461 | -0.085473 | 180/180 |
| nll | 2.667772 | 1.632070 | -1.035702 | 176/180 |
| brier | 0.648412 | 0.518434 | -0.129978 | 180/180 |
| mean_confidence | 0.907905 | 0.876093 | -0.031811 | 151/180 |
| mean_entropy | 0.235102 | 0.319464 | +0.084363 | 152/180 |

The ECE values are recomputed from saved/re-generated per-sample probabilities. Where frozen raw ECE was available, 0 conditions were cross-checked; maximum absolute discrepancy = 0.

Reliability figure: `simulated_single_factor_ood_reliability.png`.

## CNRS-318 zero-shot

Per-seed matched pairs: **5**. CNRS labels were not used to fit or tune anything in this audit.

| Metric | Dynamic ERM pooled | JS pooled | Δ (JS−ERM) |
|---|---:|---:|---:|
| macro_f1 | 0.191176 | 0.209119 | +0.017943 |
| accuracy | 0.200000 | 0.210063 | +0.010063 |
| ece | 0.682570 | 0.612420 | -0.070150 |
| nll | 8.319988 | 6.118566 | -2.201422 |
| brier | 1.433841 | 1.315606 | -0.118235 |
| mean_confidence | 0.882570 | 0.822483 | -0.060087 |
| mean_entropy | 0.289702 | 0.441971 | +0.152269 |

Reliability figure: `cnrs318_reliability.png`.

## Reading rule

The calibration claim should be strengthened only if ECE, NLL, and Brier improve together while classification performance is not sacrificed. Lower ECE alone can reflect confidence shrinkage and is not sufficient to establish a general calibration mechanism.

The repeated simulated conditions and CNRS seed predictions are paired/repeated evaluations, not statistically independent experiments.
