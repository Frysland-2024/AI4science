# Project history note — XRD reporting-standard reset

**Date:** 2026-08-27

## Decision

For the PXRD robustness project, the main outward-facing results will be reported using the performance-reporting conventions that are normal in PXRD / materials-ML literature. Strict statistical auditing remains available as a second layer of evidence, but it is no longer treated as a pass/fail gate that can override an otherwise coherent scientific result.

The guiding rule is:

> **主结果应按照 PXRD/材料 ML 社区常用的 performance-reporting 范式来讲；严格统计审计作为增强可信度的第二层证据，而不是把结果重新判刑。**

## Why this reset was needed

Earlier project governance gradually adopted standards closer to a confirmatory ML benchmark than to the reporting practice of the target PXRD/materials-ML community. Examples included treating parent-level paired bootstrap confidence intervals, CI>0 requirements, and other stringent audit conditions as if every external-domain result had to pass them before it could be described as a useful positive result.

Those analyses are scientifically useful, but this created a mismatch between:

1. what the field normally reports and understands (accuracy, Macro-F1/F1, precision/recall, mean performance, learning curves, repeated-run consistency, per-class results), and
2. what the project had started requiring internally as a hard success criterion.

This mismatch made valid real-domain results appear unnecessarily weak, especially for naturally limited and imbalanced experimental datasets.

## New two-layer reporting policy

### Layer 1 — main scientific / presentation results

Use conventional, directly interpretable performance evidence:

- Macro-F1 / F1 where appropriate;
- balanced accuracy for naturally imbalanced domains;
- overall accuracy when useful for comparison with prior PXRD literature;
- few-shot learning curves and label-budget comparisons;
- mean improvement in percentage points;
- consistency across independent training seeds;
- per-class performance where scientifically informative;
- ECE / NLL / Brier as secondary reliability metrics when relevant.

The main question is whether the evidence as a whole supports the scientific claim, not whether every auxiliary statistical test independently clears a confirmatory threshold.

### Layer 2 — strict statistical audit

Keep, but demote to secondary evidence / appendix / internal audit:

- class-stratified parent bootstrap;
- paired confidence intervals;
- detailed uncertainty decomposition;
- strict parent-level resampling rules;
- narrow confirmatory wording gates such as requiring a 95% CI to lie completely above zero.

These analyses remain valuable for transparency and for answering methodological questions, but **a CI crossing zero is not by itself a reason to treat the whole real-domain experiment as a failure** when the broader performance evidence is coherent.

## Consequences for current results

### Simulated OOD

Main outward-facing result:

- JS improves mean single-factor OOD Macro-F1 by about **+5.46 percentage points**;
- all **5/5** matched training seeds improve.

The paired/bootstrap audit remains supporting evidence rather than the headline.

### RRUFF

Main outward-facing role:

- emphasize **few-shot adaptation / label efficiency** under identical real-label budgets;
- report the learning curve and JS-vs-ERM performance differences;
- do not let an overly strict auxiliary CI criterion determine whether the real-domain result is considered useful.

RRUFF zero-shot does not need an independent main-slide role if it distracts from the stronger few-shot story; K=0 may remain as a diagnostic point in a learning curve when useful.

### CNRS-318

Treat CNRS as a naturally imbalanced second real domain and report the conventional performance picture:

- 5/5 training seeds favor JS;
- Macro-F1: about 0.191 -> 0.209;
- balanced accuracy: about 0.218 -> 0.239;
- overall accuracy: about 0.200 -> 0.210;
- ECE: about 0.683 -> 0.612.

The small class supports (notably hexagonal n=12) make Macro-F1 uncertainty intrinsically wide because every crystal system receives equal weight. This limitation should be acknowledged, but the parent-bootstrap CI crossing zero is **not** the headline and should not be used to reclassify the experiment as a failed result.

Appropriate public wording is along the lines of:

> The independent CNRS experimental domain shows a directionally consistent improvement across all five training seeds, with gains also observed in balanced accuracy, overall accuracy, and calibration; uncertainty remains larger because the real dataset is naturally imbalanced and contains low-support crystal systems.

## What is explicitly abandoned

The project will no longer use the following logic for outward-facing scientific judgment:

> "If a strict paired/bootstrap 95% CI crosses zero, the result is effectively unsuccessful or should not be presented positively."

Likewise, not every internal audit statistic needs to appear in the main group-meeting PPT or application narrative.

## What is NOT abandoned

This is **not** permission to hide contradictory evidence, change metrics after seeing results to manufacture significance, delete frozen results, or alter evaluation data post hoc.

The original audit outputs remain preserved. The change is about the **role and hierarchy of evidence**:

- community-standard performance reporting = primary communication layer;
- strict statistical audit = secondary credibility layer.

## Rationale for future project decisions

For materials-ML / AI-for-characterization work, evaluation standards should be calibrated to the scientific question, the actual experimental-data regime, and the conventions of the target field. Internal rigor should improve credibility, not impose a stricter success definition than the community itself normally uses and thereby make valid results artificially difficult to communicate.
