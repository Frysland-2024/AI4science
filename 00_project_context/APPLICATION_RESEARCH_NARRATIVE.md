# Application Research Narrative

**Updated:** 2026-08-23

## Research story

My project studies robust machine learning for powder X-ray diffraction (PXRD). Simulated spectra provide controlled access to realistic measurement variation, including peak shifts, broadening, preferred orientation, background and noise. The central idea is that a simulator provides useful relationships in addition to labeled samples: multiple perturbed spectra generated from one parent structure are measurements of the same latent physical object.

I converted this relationship into measurement-equivalence supervision. For each parent structure, the training system generates two online views and applies Jensen-Shannon prediction consistency while preserving the same structures, perturbation distribution, backbone, optimization and data exposure as a Dynamic ERM baseline.

The final comparison uses a ResNet-18-GN backbone for seven-crystal-system classification. Across five matched training-seed pairs, JS consistency improved simulated Validation mean single-factor OOD Macro-F1 by `+0.046569`. Evaluation of the already selected checkpoints on the frozen simulated Test produced a `+0.054600` mean paired improvement. All five paired effects were positive on both panels.

This work strengthened my interest in robust and data-efficient learning for scientific measurements. It also taught me how to convert information already available in a scientific data-generation process into a focused machine-learning hypothesis, a matched comparison and a reproducible result.

## Application version

My research focuses on robust machine learning for scientific measurements. In powder X-ray diffraction, simulated training patterns can vary with peak position, broadening, preferred orientation, background and noise. I recognized that an online simulator provides more than labeled spectra: it knows which perturbed views originate from the same parent crystal. I used this relationship as measurement-equivalence supervision by adding Jensen-Shannon prediction consistency to a matched Dynamic ERM design. The comparison kept the crystal structures, perturbation distribution, ResNet-18-GN backbone, optimization and two-view data exposure fixed. Across five matched seeds, consistency improved simulated Validation OOD Macro-F1 by `+0.046569`. The already selected checkpoints then achieved a `+0.054600` mean paired improvement on the frozen simulated Test, with all five paired effects positive. The project demonstrates how scientific data-generation relationships can become structured supervision for robust classification.

## Interview version

I worked on making simulated PXRD classifiers robust to realistic measurement variation. The key insight was that the simulator knows when two spectra are different measurements of the same parent crystal. I turned that relationship into a consistency objective and compared it with matched dynamic training. Five-seed Validation and a frozen simulated Test both showed clear aggregate gains, so the project became a concrete example of using scientific structure as supervision rather than treating simulation only as a source of more samples.

## Recommended claim language

- “I reframed simulator-retained parent identity as measurement-equivalence supervision.”
- “I compared Dynamic ERM and JS consistency under matched structures, perturbations, optimization and data exposure.”
- “Five matched seeds showed a `+0.046569` Validation gain and a `+0.054600` simulated Test gain.”
- “The completed study addresses robust seven-crystal-system PXRD classification in the simulated domain.”
