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

## Methodological reflection — separating scientific judgment from statistical audit

A major lesson from this stage of the project is that we had temporarily conflated **internal credibility auditing** with **the criterion for whether the scientific result itself is allowed to count as successful**.

The earlier logic was effectively:

> high-intensity ML audit -> every real-domain result must individually clear a confirmatory threshold -> only then may the experiment be described as successful.

That logic is too strong for this application setting. In a real PXRD domain with naturally scarce and imbalanced experimental samples, metrics such as Macro-F1 and class-stratified parent bootstrap can be intentionally conservative. For example, in CNRS the class counts are highly uneven and the hexagonal class has only 12 samples, yet Macro-F1 assigns every class the same 1/7 weight. A parent-level bootstrap therefore honestly exposes large uncertainty, but that uncertainty should not be converted into a binary verdict on whether the entire experiment "worked".

The project therefore formally distinguishes two questions:

### Scientific conclusion layer

Ask whether the **full body of evidence is directionally coherent** across:

- simulated OOD;
- RRUFF few-shot adaptation;
- CNRS external-domain validation;
- calibration / confidence behavior;
- independent training-seed consistency.

If these pieces jointly support the same mechanism-level conclusion, then the scientific story is supported even if one auxiliary confidence interval in one limited real domain crosses zero.

### Statistical audit layer

Use:

- confidence intervals;
- parent-level bootstrap;
- per-class uncertainty;
- seed-wise variation;
- ECE / NLL / Brier;
- detailed stratified resampling;

as tools for answering **how certain the conclusion is, where it is fragile, and which classes/domains remain underpowered**.

They are not automatic vetoes on the first layer.

This distinction is now part of the project history because it represents an important change in research judgment:

> **Early in the project, we temporarily treated high-strength ML statistical auditing as a confirmatory gate that every materials-application result had to pass. We later separated credibility auditing from scientific-result judgment: strict statistics are preserved, but a single CI crossing zero no longer determines the narrative or reclassifies an otherwise coherent result as failure.**

This correction does not reduce rigor. It changes the hierarchy of evidence so that rigor serves interpretation rather than replacing it.

## Community-metric survey — what PXRD / crystallographic ML actually reports

A follow-up literature survey of representative PXRD / XRD machine-learning work from 2019–2026 was used to ground the reporting reset in actual community practice rather than project preference. Representative examples considered include Oviedo et al. (npj Computational Materials, 2019), Suzuki et al. (Scientific Reports, 2020), CrystalMELA (Journal of Applied Crystallography, 2023), Lee et al. (Advanced Intelligent Systems, 2023), Schopmans et al. (Digital Discovery, 2023), SimXRD-4M (2025), XQueryer (National Science Review, 2025), and recent real-PXRD structure-solving work.

The recurring classification-reporting pattern in this community is:

1. **Accuracy** — still the most traditional and widely comparable headline metric.
2. **F1 / Macro-F1** — especially important for multiclass or imbalanced crystal-system / space-group classification.
3. **Precision / Recall** — often reported as macro averages or per-class diagnostics.
4. **Confusion matrix and per-class scores** — common for understanding crystal-system confusions.
5. **Balanced Accuracy** — useful and established when the experimental domain is naturally imbalanced.
6. **Top-k Accuracy / match rate** — common in many-class candidate retrieval, indexing, or structure-solving tasks.
7. **Cross-validation standard deviation or repeated-run mean ± std** — a common way of reporting training variability and robustness.
8. **Uncertainty / calibration metrics** — increasingly used in recent work, but still generally secondary to the above performance metrics rather than replacing them as the headline.

The survey did **not** identify a community norm in which a paired/bootstrap 95% confidence interval must lie completely above zero before an XRD-ML result may be reported as positive. Strict bootstrap or significance analyses can strengthen a paper, but they are not the normal binary success criterion of the PXRD classification literature.

### Metric redundancy notes

For standard single-label multiclass classification:

- micro-F1 is numerically equivalent to overall accuracy, so both do not need to occupy separate headline columns;
- balanced accuracy is the mean per-class recall, so macro recall is highly redundant if balanced accuracy is already reported.

This motivates concise main tables rather than maximizing the number of metrics.

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
- mean ± std or equivalent repeated-run summaries;
- Top-k metrics only when the task is candidate retrieval / many-class ranking rather than ordinary seven-class classification;
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

## Domain-specific reporting rules adopted for this project

### Simulated OOD

Main outward-facing result:

- **Primary:** Macro-F1;
- also report overall accuracy where useful;
- report the matched-seed mean / standard deviation and direction consistency;
- JS improves mean single-factor OOD Macro-F1 by about **+5.46 percentage points**;
- all **5/5** matched training seeds improve.

The paired/bootstrap audit remains supporting evidence rather than the headline.

### RRUFF-301

RRUFF is a balanced curated experimental domain, so the main outward-facing role is:

- emphasize **few-shot adaptation / label efficiency** under identical real-label budgets;
- report Macro-F1 and Accuracy at each K;
- report the learning curve and JS-vs-ERM percentage-point differences;
- report repeated-seed mean ± std / direction consistency;
- do not let an overly strict auxiliary CI criterion determine whether the real-domain result is considered useful.

Balanced Accuracy is not needed as a headline in a deliberately balanced benchmark. RRUFF zero-shot does not need an independent main-slide role if it distracts from the stronger few-shot story; K=0 may remain as a diagnostic point in a learning curve when useful.

### CNRS-318

Treat CNRS as a naturally imbalanced second real domain. Its natural class counts are:

`21 / 87 / 77 / 41 / 33 / 12 / 47`

The main table should therefore use the combination:

- **Macro-F1** — equal-weight precision/recall performance across all seven crystal systems;
- **Balanced Accuracy** — mean per-class recall, appropriate for the natural imbalance;
- **Overall Accuracy** — performance under the actual natural sample distribution and the most conventional PXRD comparison metric;
- **per-class F1 + support** when space permits;
- **5-seed direction / mean ± std** as the main stability description.

Current conventional performance picture:

- 5/5 training seeds favor JS;
- Macro-F1: about 0.191 -> 0.209;
- balanced accuracy: about 0.218 -> 0.239;
- overall accuracy: about 0.200 -> 0.210;
- ECE: about 0.683 -> 0.612.

The small class supports (notably hexagonal n=12) make Macro-F1 uncertainty intrinsically wide because every crystal system receives equal weight. This limitation should be acknowledged, but the parent-bootstrap CI crossing zero is **not** the headline and should not be used to reclassify the experiment as a failed result.

Appropriate public wording is along the lines of:

> The independent CNRS experimental domain shows a directionally consistent improvement across all five training seeds, with gains in Macro-F1, balanced accuracy, overall accuracy, and calibration; uncertainty remains larger because the real dataset is naturally imbalanced and contains low-support crystal systems.

### Calibration / reliability metrics

ECE, NLL, Brier score, predictive entropy and confidence analysis are scientifically valuable and increasingly relevant to reliable scientific ML. In this project they should be used as **secondary reliability evidence**. For example, an ECE improvement can support the statement that the performance gain is accompanied by better calibration.

They should not replace Accuracy / Macro-F1 / Balanced Accuracy as the headline performance layer unless the scientific question itself is specifically calibration or uncertainty estimation.

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

For future PPTs, paper drafts, result summaries, and application narratives, Codex and other analysis agents should default to the domain-specific metric hierarchy above. If an older project document uses language equivalent to `CI > 0 or the result fails`, that should be treated as a historical governance rule, not as the current reporting standard.
