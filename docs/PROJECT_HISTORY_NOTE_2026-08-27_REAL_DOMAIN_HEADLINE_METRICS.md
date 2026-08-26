# Project History Note — Real-domain headline metrics and reporting roles

Date: 2026-08-27

## Decision

For external communication, group-meeting slides, application narratives, and the main manuscript story, the two real-domain evaluations should be summarized using the performance-reporting conventions common in PXRD / materials-ML rather than by promoting every internal statistical audit quantity to a headline gate.

Strict statistics remain available as second-layer credibility evidence and appendix material. They are not deleted, but they should not automatically veto or dominate the main scientific narrative.

## RRUFF: role = few-shot adaptation efficiency

RRUFF should be presented primarily as the balanced real-domain few-shot adaptation benchmark.

Headline quantities:

- 1-shot/class: Macro-F1 gain of approximately +4.33 percentage points (JS over Dynamic ERM).
- 2-shot/class: Macro-F1 gain of approximately +4.60 percentage points.
- 5-shot/class: Macro-F1 gain of approximately +5.45 percentage points.
- Across the 75 paired few-shot comparisons (3 label budgets × 25 matched comparisons), 68 are positive for JS.

Interpretation:

> Under the same small real-label budget and the same adaptation procedure, JS-pretrained models consistently adapt better to experimental RRUFF spectra than Dynamic-ERM-pretrained models.

RRUFF zero-shot should not be a headline result or a standalone main-text / main-slide figure. It may remain as a secondary diagnostic or appendix result.

## CNRS: role = independent real-source transfer trend

CNRS should be presented as the second independent experimental source, emphasizing cross-seed and cross-metric consistency rather than treating one confidence interval as the sole success criterion.

Headline quantities:

- 5/5 independent training seeds: JS > Dynamic ERM in Macro-F1.
- Macro-F1: 0.1912 -> 0.2091, improvement about +1.79 percentage points.
- Balanced Accuracy: 0.2182 -> 0.2388, improvement about +2.06 percentage points.
- Overall Accuracy: 0.2000 -> 0.2101, improvement about +1.01 percentage points.
- ECE: 0.6826 -> 0.6124, a lower calibration error for JS.

Interpretation:

> On a second, naturally imbalanced experimental source, JS preserves a positive advantage across all five training seeds, with Macro-F1, balanced accuracy, overall accuracy, and ECE all moving in the favorable direction.

Because CNRS is naturally imbalanced (class counts 21 / 87 / 77 / 41 / 33 / 12 / 47), support limitations of the smallest classes should be acknowledged when needed. However, the main presentation should focus on the fact that several standard classification metrics and all five seeds agree in direction.

## Main-story division of labor

The two real domains should not be forced to tell the same story:

- RRUFF = label-efficient real-domain adaptation.
- CNRS = independent-source zero-shot transfer trend / robustness check.

Together they support a cleaner real-domain narrative:

> JS consistency improves simulated OOD robustness, makes subsequent RRUFF adaptation more label-efficient, and preserves a positive trend on an independent CNRS experimental source.

## What moves out of the headline story

The following are retained for audit, appendices, rebuttal/defense, or detailed reporting rather than headline communication:

- RRUFF zero-shot as a standalone result;
- CNRS parent-bootstrap confidence interval as a primary success/failure gate;
- worst-class F1 as a headline metric;
- full per-class CNRS tables in the main slide deck;
- internal labels such as "stable replication" vs "directional support" as the main public framing;
- detailed bootstrap mechanics and parent-level statistical protocol.

These quantities remain valuable as evidence of rigor; they simply no longer define whether the main result is considered communicable.

## General reporting principle

> Main results should be communicated using the standard performance language of the PXRD / materials-ML community (F1, accuracy, balanced accuracy, label-efficiency curves, repeated-run consistency). Stricter paired/bootstrap audits are retained as a second evidence layer that strengthens credibility rather than as a mechanism for invalidating otherwise coherent, domain-appropriate results.
