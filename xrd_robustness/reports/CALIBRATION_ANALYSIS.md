# Calibration analysis of Dynamic ERM and JS consistency

**Date:** 2026-08-27  
**Status:** post-hoc secondary analysis of frozen predictions; no model retraining, checkpoint selection, or hyperparameter tuning was performed.

## Motivation

The primary study asks whether consistency regularization between two measurement views of the same parent crystal improves robustness to PXRD measurement variation.

Because the classifier outputs a probability distribution rather than only a hard crystal-system label, the frozen evaluation results also allow a secondary question:

> Does measurement-view consistency affect the reliability of predictive confidence?

This analysis was not used to select `lambda_js`, training seeds, checkpoints, or evaluation profiles. It is therefore interpreted as a secondary characterization of the already frozen models rather than an additional model-selection criterion.

## Calibration metric

The existing evaluation pipeline computes the **Expected Calibration Error (ECE)** whenever class probabilities are available.

The current implementation uses 15 equal-width confidence bins. For each sample, confidence is defined as the maximum predicted class probability, and ECE measures the weighted discrepancy between mean confidence and empirical accuracy within each bin.

Lower ECE indicates that predicted confidence is better aligned with observed correctness.

ECE does not measure classification accuracy itself and should therefore be interpreted together with Macro-F1 and other predictive metrics.

## Simulated Test

The frozen simulated-Test evaluation contains:

- 5 matched training seeds;
- 3 fixed evaluation seeds;
- 12 evaluation profiles;
- 2 methods: Dynamic ERM and JS Consistency.

This yields 180 matched ERM-JS calibration comparisons.

The ECE values were already computed during the original simulated-Test evaluation and stored in the local raw evaluation output; no model rerun was required.

| Training seed | Mean ΔECE = ECE(JS) − ECE(ERM) | JS lower ECE |
| --- | ---: | ---: |
| 20260711 | −0.1103 | 36 / 36 |
| 20260712 | −0.0554 | 36 / 36 |
| 20260713 | −0.0594 | 36 / 36 |
| 20260714 | −0.1359 | 36 / 36 |
| 20260715 | −0.0665 | 36 / 36 |
| **Overall** | **−0.0855** | **180 / 180** |

Across all 180 matched evaluations, JS produced a lower ECE than its corresponding Dynamic ERM model.

The observed paired ECE differences ranged approximately from:

\[
-0.254 \leq \Delta \mathrm{ECE} \leq -0.013
\]

with no evaluated profile showing the opposite direction.

This calibration result accompanies the previously frozen robustness result: JS also improves the mean single-factor OOD Macro-F1 on simulated Test by approximately `+0.0546`.

Thus, within the simulated evaluation domain, improved robustness is not accompanied by poorer confidence calibration. Instead, the frozen results show both higher predictive performance and systematically lower calibration error.

## CNRS-318 external experimental domain

The same direction is observed on the independent CNRS-318 zero-shot experimental domain.

| Metric | Dynamic ERM | JS |
| --- | ---: | ---: |
| Macro-F1 | 0.1912 | 0.2091 |
| Balanced accuracy | 0.2182 | 0.2388 |
| Accuracy | 0.2000 | 0.2101 |
| **ECE** | **0.6826** | **0.6124** |

CNRS remains a difficult zero-shot Sim-to-Real setting: absolute classification performance is low and both methods remain strongly over-confident. The calibration improvement therefore does **not** imply that the experimental-domain confidence estimates are already reliable.

Nevertheless, the direction agrees with the much stronger simulated-domain observation:

\[
\mathrm{ECE}_{JS}<\mathrm{ECE}_{ERM}.
\]

The CNRS result should therefore be treated as **cross-domain directional support**, rather than an independent statistical confirmation of calibration improvement.

## Interpretation

The calibration results suggest an additional property of measurement-view consistency regularization.

Dynamic ERM requires each perturbed observation to predict the correct crystal-system label independently. JS Consistency additionally penalizes differences between the complete predictive distributions produced from two measurement views of the same parent structure.

A plausible interpretation is that this constraint discourages highly view-specific, sharply varying predictive distributions. In other words, consistency training may smooth the classifier's probability response along measurement-variation directions.

This interpretation is compatible with two observations:

\[
\text{higher OOD Macro-F1}
\]

and

\[
\text{lower ECE}.
\]

However, the current evidence does **not** by itself prove that JS is an implicit calibration regularizer.

A lower ECE can arise partly from reduced confidence magnitude, and ECE is a bin-dependent summary statistic. Therefore, the strongest current conclusion is:

> **Measurement-view consistency is associated with systematically lower calibration error in the frozen simulated evaluations, while the same direction is observed in the independent CNRS experimental domain.**

It would be premature to claim a general calibration mechanism without additional proper scoring-rule analysis.

## Relation to the main study

Calibration is not treated as a separate methodological contribution.

The primary contribution remains the use of simulator-defined parent provenance to provide measurement-equivalence supervision and improve robustness under distribution shift.

Calibration instead provides a complementary reliability perspective:

> JS does not merely improve the frequency of correct predictions under simulated measurement shift; the resulting probability outputs also appear less over-confident.

This is particularly relevant for scientific measurement analysis, where confidence estimates may eventually be used to identify uncertain spectra, trigger additional measurements, or defer difficult cases for expert review.

## Limitations and minimum follow-up

The present ECE analysis should remain secondary for three reasons.

First, ECE is sensitive to binning and does not constitute a proper scoring rule. Second, the CNRS models remain severely miscalibrated despite the relative improvement. Third, the simulated raw calibration values are currently retained in the local frozen evaluation outputs rather than in the public summarized result files.

Before elevating calibration from a secondary observation to a stronger methodological claim, the existing predictions should be used to compute:

1. negative log-likelihood (NLL);
2. multiclass Brier score;
3. mean predictive confidence;
4. reliability diagrams for matched ERM and JS models.

No retraining is required for these analyses.

If ECE, NLL, and Brier score all improve consistently while Macro-F1 also remains higher, the evidence would support the stronger statement:

> **Consistency regularization improves both robustness and probabilistic reliability under simulated PXRD measurement shift.**

Until then, calibration should be presented as a strong secondary finding rather than a new primary contribution.

## Recommended manuscript wording

> Beyond classification performance, the frozen predictions revealed a consistent calibration difference between the two training objectives. Across all 180 matched simulated-Test evaluations, JS Consistency yielded lower expected calibration error than Dynamic ERM, with a mean paired ΔECE of −0.0855. The same direction was observed on the independent CNRS-318 experimental domain, where pooled ECE decreased from 0.6826 to 0.6124. These results suggest that measurement-view consistency may reduce over-confident predictions in addition to improving OOD robustness. Because ECE alone cannot distinguish genuine calibration improvement from general confidence shrinkage, we treat this result as a secondary reliability observation rather than evidence of a distinct calibration mechanism.
