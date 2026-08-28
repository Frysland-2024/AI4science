# Study Results

## Experiment

The experiment compares Dynamic ERM with JS Consistency
(`lambda = 60`) using the same ResNet-18-GN architecture and five matched
seeds. The simulated PXRD dataset contains 14,060 parent
structures split into 9,842 Train, 2,109 Validation, and 2,109 simulated Test
structures.

## Reporting hierarchy

The evidence is organized in three layers. **Layer A (primary performance)**
follows common PXRD / materials-ML reporting: Macro-F1, balanced accuracy when
imbalance matters, accuracy, mean ± SD, matched-seed consistency, few-shot
learning curves, label efficiency and per-class behavior. **Layer B
(reliability)** adds ECE, NLL, Brier score, entropy and confidence behavior as
supporting evidence; these do not replace F1/accuracy as headline metrics.
**Layer C (strict statistical audit)** retains paired and class-stratified
parent bootstrap intervals and uncertainty decomposition. One interval crossing
zero quantifies uncertainty but is not, by itself, a pass/fail verdict on an
otherwise coherent body of evidence.

## Validation

| Metric | Dynamic ERM | JS Consistency | Paired improvement |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | +0.046569 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

The primary single-factor OOD improvement was positive in all five matched
pairs. Its paired-bootstrap 95% interval was `[0.038145, 0.052834]`. The
in-range improvement was also positive in all five pairs, with a 95% interval
of `[0.014028, 0.041954]`.

## Simulated Test

| Metric | Dynamic ERM | JS Consistency | Paired improvement |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.697280 | 0.737159 | +0.039880 |
| In-range Macro-F1 | 0.695267 | 0.734854 | +0.039587 |
| Mean single-factor OOD Macro-F1 | 0.650737 ± 0.007208 | 0.705336 ± 0.009767 | +0.054600 ± 0.007271 |
| Mean single-factor OOD Accuracy | 0.650782 ± 0.007804 | 0.705237 ± 0.008560 | +0.054454 ± 0.004149 |
| Worst-class F1 | 0.511064 | 0.558558 | +0.047495 |

All four pre-existing F1 summaries were positive in all five matched
pairs; the added single-factor OOD Accuracy summary also improves in all 5/5 pairs. Values after `±`
are sample standard deviations across five training seeds. The primary Macro-F1
improvement had sample SD
`0.007271` and a paired-bootstrap 95% interval of
`[0.048944, 0.060255]`.

## Experimental real-domain results

### RRUFF-301: few-shot adaptation and label efficiency

Under identical real-label budgets and the same locked-test adaptation
procedure, JS-pretrained representations improve Macro-F1 at all three label
budgets:

| Labels/class | Metric | Dynamic ERM (mean ± SD) | JS Consistency (mean ± SD) | Mean paired Δ | Positive pairs |
|---:|---|---:|---:|---:|---:|
| 1 | Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | +0.0433 | 21 / 25 |
| 1 | Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | +0.0384 | 20 / 25 |
| 2 | Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | +0.0460 | 23 / 25 |
| 2 | Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | +0.0488 | 23 / 25 |
| 5 | Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | +0.0545 | 24 / 25 |
| 5 | Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | +0.0568 | 23 / 25 |

Across the full Macro-F1 learning curve, 68 of 75 matched comparisons favor JS; after
averaging the five episode seeds within each pretraining seed, all 5/5 pretraining seeds
favor JS at each of K=1, K=2 and K=5. The
values after `±` are sample standard deviations across 25 paired runs per budget. RRUFF
therefore provides the primary real-domain evidence for more label-efficient
adaptation; its zero-shot point is a diagnostic starting point rather than the
headline. The locked-test aggregates were retrospectively verified against the stored
result file, and the exact values are recorded in
[`rruff301_fewshot_results.json`](rruff301_fewshot_results.json).

### CNRS-318: second independent experimental source

CNRS is a frozen zero-shot evaluation; no CNRS label was used for adaptation,
checkpoint selection or hyperparameter selection. All five training seeds favor
JS in Macro-F1. Across those seeds, Macro-F1 is
`0.188372 ± 0.026336 → 0.207085 ± 0.021336`, with a paired improvement of
`+0.018713 ± 0.006754` (about `+1.87` percentage points). All `±` values here are
sample standard deviations across the five fixed training seeds.

| Pooled metric | Dynamic ERM | JS Consistency | Change (JS−ERM) |
|---|---:|---:|---:|
| Macro-F1 | 0.191176 | 0.209119 | +0.017943 |
| Balanced accuracy | 0.218225 | 0.238777 | +0.020552 |
| Accuracy | 0.200000 | 0.210063 | +0.010063 |
| ECE ↓ | 0.682570 | 0.612420 | −0.070150 |
| NLL ↓ | 8.319988 | 6.118566 | −2.201422 |
| Brier score ↓ | 1.433841 | 1.315606 | −0.118235 |

The classification and reliability metrics therefore move together in the
favorable direction. The strict audit remains visible: the corrected
class-stratified paired-parent 95% interval is
`[−0.009339, +0.046107]`. Its width is consistent with the natural class
imbalance (`21 / 87 / 77 / 41 / 33 / 12 / 47`) and especially the 12-parent
hexagonal class. It indicates substantial uncertainty in the effect estimate;
it does not erase the 5/5 seed consistency or turn the experiment into a failed
replication.

## Secondary probabilistic reliability result

A completed post-hoc audit of the frozen models shows that the robustness gain
is accompanied by broadly improved probability quality rather than merely a
change in hard-label accuracy.

Across **180 matched simulated-Test evaluation conditions** (five training
seeds × three evaluation seeds × twelve profiles):

These are repeated matched conditions from five trained models, not 180 independent
experiments.

| Metric | Dynamic ERM | JS Consistency | Mean paired Δ (JS−ERM) | Better-direction conditions |
|---|---:|---:|---:|---:|
| Macro-F1 | 0.618282 | 0.671078 | +0.052796 | 176 / 180 |
| Accuracy | 0.618242 | 0.672075 | +0.053833 | 179 / 180 |
| ECE ↓ | 0.289934 | 0.204461 | −0.085473 | **180 / 180** |
| NLL ↓ | 2.667772 | 1.632070 | −1.035702 | 176 / 180 |
| Brier ↓ | 0.648412 | 0.518434 | −0.129978 | **180 / 180** |

Mean confidence also decreases (`0.907905 -> 0.876093`) while mean predictive
entropy increases (`0.235102 -> 0.319464`). Because ECE and Brier improve in
all 180 matched conditions, NLL improves in 176/180, and classification
performance increases simultaneously, the result is not well explained by
indiscriminate confidence shrinkage alone.

The independent **CNRS-318 zero-shot** domain shows the same probability-level
direction. Pooled ECE decreases from `0.682570` to `0.612420`, NLL from
`8.319988` to `6.118566`, and Brier from `1.433841` to `1.315606`; Macro-F1
increases from `0.191176` to `0.209119`. Across the five matched training
seeds, Macro-F1, ECE, NLL, and Brier all favor JS in **5/5** seed pairs.

The supported result-level conclusion is therefore:

> **Consistency regularization improves both robustness and probabilistic reliability under the evaluated PXRD measurement shifts.**

This does **not** establish JS as a standalone calibration algorithm or prove a
universal calibration mechanism. CNRS remains strongly over-confident in
absolute terms, so consistency reduces but does not eliminate the broader
Sim-to-Real reliability gap.

The full interpretation and claim boundaries are recorded in
[`CALIBRATION_ANALYSIS.md`](CALIBRATION_ANALYSIS.md).

Exact calibration/reliability outputs are under
`../outputs/calibration_analysis/`, with `summary.json` as the canonical
machine-readable aggregate.

Exact aggregate classification values are available in
`validation_results.json` and `simulated_test_results.json`. The experiment
definition is `../configs/experiment.public.json`.

## Overall scientific judgment

The simulated OOD gains, RRUFF few-shot learning curve, CNRS five-seed and
multi-metric improvements, and probability-quality results jointly support the
conclusion that JS consistency uses shared-parent measurement equivalence to
learn a model that is more robust than matched Dynamic ERM. This conclusion
does not claim that zero-shot sim-to-real classification is solved: CNRS
absolute accuracy remains below the natural-domain majority-class baseline,
calibration remains poor in absolute terms, and low-support classes retain
large uncertainty.
