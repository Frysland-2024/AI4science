# 00 — Current Authoritative Project State

**Updated:** 2026-06-27  
**Primary project:** SimXRD / XRD measurement reliability benchmark  
**Long-term research line:** reliable scientific ML for imperfect measurement data, uncertainty, robustness, and inverse problems.

## One-sentence project definition

> Transfer consistency-based robust learning from computer vision and medical AI into physically motivated XRD measurement perturbations, construct a diffraction-specific reliability benchmark, and test/improve prediction stability under label-preserving perturbations.

## Core scientific question

For the same crystal structure measured under plausible variations in the measurement process, the material label is unchanged. Does a classifier preserve its prediction and calibrated confidence?

\[
x' = T_{\mathrm{phys}}(x), \qquad y(x') = y(x), \qquad f(x') \approx f(x).
\]

The central object is **measurement reliability**, not merely clean-set accuracy.

## Current technical scope

- **Input:** one-dimensional powder XRD intensity pattern on a common diffraction grid.
- **Task:** initially crystal system / symmetry classification, subject to the exact SimXRD label taxonomy verified from the dataset.
- **Primary data setting:** controlled simulated patterns from SimXRD-style data.
- **External validation:** real XRD is a required value-add component, but the precise source, label standard, and protocol remain unresolved.
- **Core approach:** clean baseline + physically grounded perturbation stress test + consistency regularization.
- **Principal perturbations:** peak/zero shift, peak broadening, noise, background; texture/preferred orientation is a separately controlled perturbation family.
- **Main outputs:** clean accuracy, perturbed accuracy, FlipRate, pairwise consistency, calibration/OOD diagnostics, sample-level churn, and real-XRD external checks.

## Canonical model objective

The preferred MVP formulation is:

\[
\mathcal{L} = \mathcal{L}_{\mathrm{task}} + \lambda\,D\big(p_\theta(x),p_\theta(T_{\mathrm{phys}}(x))\big),
\]

where `L_task` is supervised classification loss and `D` is a probability/logit consistency distance. The exact form of `D`, confidence filtering, and the value/schedule of `λ` are implementation choices that must be tuned only with a validation protocol.

## Project story for experimentalist-facing communication

> A single sample can be measured more than once under slightly different instrument/sample conditions. The phase/symmetry label should stay the same; a trustworthy classifier should not flip unpredictably because the peaks shift slightly, broaden, or ride on a different background.

Use this framing before terms such as OOD, invariance, or causal representation learning.

## Active decisions

- **Consistency regularization** is the default research method.
- **IRM is not the MVP mainline.** It may be a later comparison or conceptual reference.
- **Physical perturbations must be evidence-backed.** Numerical severity boundaries are not yet fixed.
- **Real-XRD validation is a required closing-loop goal**, not a decorative appendix.
- The project is a deliberately bounded **12-week MVP**, not a full XRD platform.
- The central contribution is the **benchmark + stress test + controlled ablations + scientific argument**, not the novelty of a single neural architecture.

## Non-goals for the MVP

- Do not build a broad "AI XRD system".
- Do not claim causal discovery from this benchmark alone.
- Do not make artificial protocol-label shortcuts the central benchmark mechanism.
- Do not replace physical or crystallographic judgment with generic augmentation heuristics.
- Do not collapse simulation and real-data conclusions into one unsupported claim.

## Current implementation status

The research specification and storytelling are developed. No repository-level implementation milestone, dataset schema, data license verification, or numerical perturbation boundary has been independently verified in this context pack. Treat all such items as pending until observed in the repository/data and recorded in a run manifest.

## Relationship to legacy FerroAI work

The older FerroAI audit supplied the intellectual motivation: model outputs that look plausible are not automatically reliable scientific knowledge. The active project moves from auditing a composition–temperature phase classifier to designing and testing robustness for experimental diffraction measurements. See `legacy/` for details.
