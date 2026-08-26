# Study Results

## Experiment

The experiment compares Dynamic ERM with JS Consistency
(`lambda = 60`) using the same ResNet-18-GN architecture and five matched
seeds. The simulated PXRD dataset contains 14,060 parent
structures split into 9,842 Train, 2,109 Validation, and 2,109 simulated Test
structures.

## Validation

| Metric | Dynamic ERM | JS Consistency | Paired improvement |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
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
| Mean single-factor OOD Macro-F1 | 0.650737 | 0.705336 | +0.054600 |
| Worst-class F1 | 0.511064 | 0.558558 | +0.047495 |

All four aggregate paired improvements were positive in all five matched
pairs. The primary single-factor OOD improvement had sample SD
`0.007271` and a paired-bootstrap 95% interval of
`[0.048944, 0.060255]`.

## Secondary probabilistic reliability result

A completed post-hoc audit of the frozen models shows that the robustness gain
is accompanied by broadly improved probability quality rather than merely a
change in hard-label accuracy.

Across **180 matched simulated-Test evaluation conditions** (five training
seeds × three evaluation seeds × twelve profiles):

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

The full interpretation, claim boundaries, and evidence mapping are recorded
in [`CALIBRATION_ANALYSIS.md`](CALIBRATION_ANALYSIS.md) and
[`CALIBRATION_EVIDENCE_PACKAGE.md`](CALIBRATION_EVIDENCE_PACKAGE.md).

Exact calibration/reliability outputs are under
`../outputs/calibration_analysis/`, with `summary.json` as the canonical
machine-readable aggregate.

Exact aggregate classification values are available in
`validation_results.json` and `simulated_test_results.json`. The experiment
definition is `../configs/experiment.public.json`.
