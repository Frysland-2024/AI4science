# 01 — Long-Term Research Direction and Selection Criteria

## Long-term intellectual line

The user is building toward **reliable AI / scientific ML for imperfect scientific and engineering measurements**, with recurring interests in:

- uncertainty and calibration;
- distribution shift / out-of-distribution behavior;
- inverse problems and measurement data;
- probabilistic and generative modeling;
- causal/invariant reasoning where assumptions can be defended;
- scientific applications in materials, chemistry, physics, and characterization.

XRD is the current **testbed**, not a permanent narrowing of the research identity.

## Preferred research profile

Future graduate research should preferentially resemble a “Max Welling–type” profile:

- strong AI theory and methods, not merely a material-property prediction pipeline;
- probability, Bayesian inference, generative models, stochastic/free-energy views, geometric or symmetry-aware learning;
- use in material/chemical/physical science, measurement science, or inverse problems;
- willingness to confront uncertainty, reliability, and scientific validity.

## What the codebase should reinforce

Codex should implement infrastructure that remains transferable beyond this dataset:

- reproducible perturbation operators;
- paired-view data handling;
- reliability metrics;
- uncertainty/calibration analysis;
- split/provenance safeguards;
- modular experimental reports.

Avoid over-specializing the architecture to one superficial benchmark artifact when the same capability could support future spectroscopy, microscopy, or electrochemical data.

## Research-quality standard

A scientifically useful result requires all of the following:

1. a valid and explicit question;
2. a benchmark that represents a real measurement mechanism;
3. an evaluation that distinguishes clean performance from stability/reliability;
4. an ablation that tests whether improvement comes from consistency rather than generic augmentation;
5. a cautious sim-to-real statement with appropriate external validation.
