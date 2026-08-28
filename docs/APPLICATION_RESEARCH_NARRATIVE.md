# Application Research Narrative

**Updated:** 2026-08-28

## Research story

My project studies robust machine learning for powder X-ray diffraction (PXRD). Simulated spectra provide controlled access to realistic measurement variation, including peak shifts, broadening, preferred orientation, background and noise. The central idea is that a simulator provides useful relationships in addition to labeled samples: multiple perturbed spectra generated from one parent structure are measurements of the same latent physical object.

I converted this relationship into measurement-equivalence supervision. For each parent structure, the training system generates two online views and applies Jensen-Shannon prediction consistency while preserving the same structures, perturbation distribution, backbone, optimization and data exposure as a Dynamic ERM baseline.

The final comparison uses a ResNet-18-GN backbone for seven-crystal-system classification. Across five matched seeds, JS consistency improved simulated Validation mean single-factor OOD Macro-F1 by `+0.046569`. Evaluation of the already selected checkpoints on the simulated Test produced a `+0.054600` mean paired improvement. All five paired effects were positive on both the Validation and Test sets.

The same scientific conclusion is supported by two experimental domains with complementary roles. On RRUFF-301, JS-pretrained models improved locked-test Macro-F1 by `+0.0433`, `+0.0460` and `+0.0545` at K=1/2/5 labels per class, showing better label efficiency. On the independent, naturally imbalanced CNRS-318 source, all 5/5 frozen zero-shot seed comparisons favored JS (mean paired `+0.0187`); pooled Macro-F1, balanced accuracy, accuracy, ECE, NLL and Brier score also improved. CNRS remains a difficult sim-to-real setting with low absolute accuracy and larger uncertainty in low-support classes, so I present it as supporting independent-source evidence rather than claiming that real-domain classification is solved.

This work strengthened my interest in robust and data-efficient learning for scientific measurements. It also taught me how to convert information already available in a scientific data-generation process into a focused machine-learning hypothesis, a matched comparison and a reproducible result.

## Application version

My research focuses on robust machine learning for scientific measurements. In powder X-ray diffraction, simulated training patterns can vary with peak position, broadening, preferred orientation, background and noise. I recognized that an online simulator provides more than labeled spectra: it knows which perturbed views originate from the same parent crystal. I used this relationship as measurement-equivalence supervision by adding Jensen-Shannon prediction consistency to a matched Dynamic ERM design. The comparison kept the crystal structures, perturbation distribution, ResNet-18-GN backbone, optimization and two-view data exposure fixed. Across five matched seeds, consistency improved simulated Validation OOD Macro-F1 by `+0.046569`, and the already selected checkpoints achieved `+0.054600` on the simulated Test. JS also improved the full K=1/2/5 RRUFF few-shot learning curve and favored all 5/5 seeds on a second CNRS experimental source, with classification and probability-quality metrics moving together. The project demonstrates how scientific data-generation relationships can become structured supervision for robust and label-efficient classification while retaining honest limits on the remaining sim-to-real gap.

## Interview version

I worked on making simulated PXRD classifiers robust to realistic measurement variation. The key insight was that the simulator knows when two spectra are different measurements of the same parent crystal. I turned that relationship into a consistency objective and compared it with matched dynamic training. Five-seed simulated OOD evaluation showed a `+5.46` percentage-point Test gain; the same model family adapted more efficiently across the RRUFF few-shot learning curve and improved all five seed comparisons on an independent CNRS source. That cross-domain evidence made the project a concrete example of using scientific structure as supervision rather than treating simulation only as a source of more samples.

## Recommended claim language

- “I reframed simulator-retained parent identity as measurement-equivalence supervision.”
- “I compared Dynamic ERM and JS consistency under matched structures, perturbations, optimization and data exposure.”
- “Five matched seeds showed a `+0.046569` Validation gain and a `+0.054600` simulated Test gain.”
- “Under identical real-label budgets, JS improved Macro-F1 across the K=1/2/5 RRUFF few-shot learning curve.”
- “On CNRS-318, all 5/5 seeds and multiple classification and calibration metrics favored JS; uncertainty remains larger because the domain is naturally imbalanced.”
- “The evidence supports improved robustness and label efficiency, not a claim that zero-shot sim-to-real classification is solved.”
