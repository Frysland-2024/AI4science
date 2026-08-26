# Project history note — from ECE anomaly to probabilistic reliability evidence

**Date:** 2026-08-27

## Why this note exists

This note records an important change in the XRD project's scientific interpretation. The calibration/reliability result was not part of the original model-selection plan. It emerged only after the main robustness experiments and the CNRS zero-shot evaluation had already been completed and frozen.

This development is worth preserving because it shows how the research question evolved by re-reading existing evidence rather than by repeatedly changing the model until a desired result appeared.

## Starting point: CNRS exposed a confidence problem

The CNRS-318 zero-shot experiment produced only a modest classification improvement for JS, but it also revealed that both ERM and JS were extremely over-confident on the experimental domain.

At that point, the immediate temptation could have been to add CNRS-specific adaptation or few-shot tuning in order to make the real-domain classification result larger.

Instead, the project paused on a different observation: the frozen simulated-Test evaluation had already computed ECE, and the local result showed an unusually consistent pattern in which JS had lower ECE than ERM across every matched evaluation condition.

This changed the question from:

> “How can the CNRS classification number be made larger?”

into:

> “Does same-parent consistency change the reliability of the predictive probability distribution itself?”

## First interpretation: promising but insufficient

The first ECE readout was striking:

- 180 matched simulated evaluation conditions;
- mean paired ΔECE around `−0.0855`;
- JS lower ECE in `180/180` conditions;
- CNRS pooled ECE also lower for JS.

However, ECE alone could not support a strong conclusion. A model can obtain lower ECE simply by becoming less confident without becoming a better probabilistic predictor.

The project therefore deliberately did **not** immediately claim that JS was a calibration method or an implicit calibration regularizer.

The minimum follow-up was defined before interpreting the result more strongly:

- compute NLL;
- compute multiclass Brier score;
- inspect mean confidence and entropy;
- generate reliability diagrams;
- verify that classification performance was not sacrificed.

No retraining was required or allowed for this audit.

## Follow-up audit

A dedicated resumable audit runner was added. For simulated Test it reused the frozen checkpoints and frozen evaluation panel/cache and performed forward inference only to recover per-sample probability vectors. For CNRS it reused the already stored zero-shot predictions.

The completed audit showed:

### Simulated Test

- ECE improved in `180/180` matched conditions;
- multiclass Brier improved in `180/180`;
- NLL improved in `176/180`;
- Macro-F1 improved in `176/180`;
- accuracy improved in `179/180`;
- average confidence decreased while predictive entropy increased.

Mean changes were:

- Macro-F1: `+0.0528`;
- accuracy: `+0.0538`;
- ECE: `−0.0855`;
- NLL: `−1.0357`;
- Brier: `−0.1300`.

### CNRS-318

Across all five matched training seeds:

- Macro-F1 improved in `5/5`;
- ECE improved in `5/5`;
- NLL improved in `5/5`;
- Brier improved in `5/5`.

CNRS remained badly miscalibrated in absolute terms, so the result did not erase the Sim-to-Real problem. It instead showed that the same relative probability-quality improvement survives in a much harder external experimental domain.

## Change in scientific conclusion

Before the proper-score audit, the strongest defensible wording was:

> Measurement-view consistency is associated with lower calibration error.

After the audit, the result-level conclusion was upgraded to:

> **Consistency regularization improves both robustness and probabilistic reliability under the evaluated PXRD measurement shifts.**

The mechanism remains intentionally weaker:

> Same-parent consistency may smooth the model's probability response along legal measurement-variation directions and reduce view-specific over-confidence.

This is treated as a plausible explanation, not a proven causal mechanism.

## Why this matters for the project story

This episode marks another shift in the project's identity.

The project began from the relatively conventional question of whether physically structured simulation and a transferred consistency objective could improve crystal-system classification accuracy. The reliability analysis pushed the work toward a broader scientific-measurement question:

> **When a model is exposed to physically plausible measurement variation, does it only remain accurate, or does it also know when its predictions should be trusted?**

That question is closer to the long-term direction of reliable AI for physical measurement and inverse problems than a pure benchmark-accuracy story.

It also provides a useful example of research judgment for future application materials:

1. a real-domain experiment exposed an unexpected weakness (severe over-confidence);
2. an existing frozen output suggested a secondary phenomenon;
3. the first attractive explanation was treated skeptically;
4. alternative explanations such as generic confidence shrinkage were explicitly tested;
5. proper scoring rules supported a stronger result while preserving the method's limitations;
6. the project question became more mature without retraining or post-hoc model selection.

## What should not be rewritten in hindsight

The history should preserve that calibration was **not** an original design target and was **not** used to choose `lambda_js` or checkpoints.

It should also preserve that the project initially considered the ECE observation insufficient and explicitly required NLL/Brier follow-up before strengthening the claim.

That uncertainty and subsequent verification are part of the actual project-development path, not details to be erased from the final story.
