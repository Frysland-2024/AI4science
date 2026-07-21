# 04 — Physical Validity and Label-Preservation Protocol

## Central principle

The scientific bottleneck is not writing the perturbation code. It is defining the region in which a perturbation is both:

1. physically/instrumentally plausible; and
2. label-preserving for the selected classification taxonomy.

AI may help retrieve evidence, derive conversions, and test implementation. It must **not** silently decide the final valid numeric range.

## Minimum legality test for every transform

A proposed perturbation is usable only if the answer to all questions is documented:

1. **Mechanism:** What real instrument/sample effect does it represent?
2. **Forward effect:** Which features of a powder pattern should change, and why?
3. **Label:** Why should the target crystal-system/symmetry label remain unchanged at this magnitude?
4. **Magnitude:** What source, instrument specification, literature measurement, or user decision supports the range?
5. **Implementation:** Does the code match the mechanism rather than a visually similar generic transform?
6. **Auditability:** Can an external reader reconstruct the chosen distribution and reproduce the transformed pattern?

## Perturbation-specific guidance

### 1. Global peak/zero shift

**Interpretation:** A calibration or zero-offset-like effect can shift all diffraction features along the `2θ` axis in a largely coherent manner.

**Physics:** Bragg's law is

\[
2d\sin\theta = n\lambda.
\]

A global instrument offset should not be confused with a true change in lattice spacing. A true strain/temperature-induced lattice change can produce peak-position behavior that needs a separately justified forward model.

**Implementation requirements:**

- operate on the physical `2θ` coordinate, not arbitrary array indices;
- state interpolation, boundary behavior, and intensity conservation policy;
- verify no artificial wrap-around or clipped peak artifacts;
- store the applied shift in units and in the run manifest.

### 2. Peak broadening

**Interpretation:** Finite crystallite size, microstrain, and instrumental resolution can broaden peaks.

**Implementation requirements:**

- use a declared line-shape model or a carefully documented convolution operator;
- specify whether broadening is constant, angle-dependent, or peak-dependent;
- prevent negative intensities and unphysical ringing;
- include plots showing peak-width changes at several `2θ` values.

### 3. Noise

**Interpretation:** Counting statistics and detector/measurement variability.

**Implementation requirements:**

- define intensity scaling prior to Poisson-like noise if used;
- specify any Gaussian/readout component;
- preserve non-negativity through a documented method;
- do not use a noise model that encodes labels or source IDs.

### 4. Background

**Interpretation:** Air scatter, fluorescence, amorphous/support contribution, baseline drift, or other non-Bragg intensity contributions.

**Implementation requirements:**

- construct a smooth physically interpretable baseline family;
- distinguish additive background from multiplicative intensity scaling;
- prevent class-specific template leakage;
- test that background choices do not silently erase the entire pattern.

### 5. Preferred orientation / texture

**Interpretation:** Reflection intensities can be reweighted by orientation distribution without a phase change.

**Status:** Secondary/advanced. Treat separately because it can suppress or amplify diagnostic reflections and has strong identifiability implications.

### 6. Unit-cell variation

**Interpretation:** Lattice deformation/temperature/strain/composition changes may move peaks.

**Status:** Not automatically valid for the main paired consistency loss. It can cross a symmetry boundary or change the label. Only use after structure-aware validation that the symmetry label remains the same.

## Evidence ledger template

Every accepted transform parameter must be recorded in a machine-readable table with at least:

```text
perturbation_id
mechanism
parameter_name
parameter_definition
unit
sampling_distribution
minimum
maximum
severity_tier
source_type (literature / instrument / measured repeat scan / user decision)
source_citation_or_file
label_preservation_argument
implementation_function
status (proposed / verified / rejected)
notes
```

## Recommended severity policy

Use named tiers (`S0`, `S1`, `S2`, `S3`) rather than ungrounded adjectives. The numerical mapping must remain `TBD` until the evidence ledger is complete. Higher severity can be used as a **stress test** even when it is no longer a standard repeat-measurement regime, but it must be labelled clearly and never mixed into the central label-preserving claim.

## Review gate before large-scale training

No full experiment should start until a reviewer can inspect:

- the evidence ledger;
- representative clean/transformed overlays;
- transform unit tests;
- a written label-preservation argument;
- split-leakage checks;
- exact transform configuration files.
