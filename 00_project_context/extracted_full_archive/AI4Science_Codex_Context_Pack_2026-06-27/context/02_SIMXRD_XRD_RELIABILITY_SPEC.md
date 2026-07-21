# 02 — SimXRD / XRD Reliability Specification

## Research claim under test

A classifier that has learned diffraction-relevant structure should be more stable than ordinary ERM when a pattern is modified by a **label-preserving physical measurement perturbation**.

This is an empirical hypothesis, not a guaranteed theorem.

## Formal data model

For each base structure/sample `i`:

```text
base latent object:       s_i
clean simulated pattern:  x_i = M(s_i; m_0)
physical measurement view:x'_i = T_phys(x_i; ξ_i)
class label:              y_i
```

The training/evaluation pair is valid only when:

```text
y_i remains scientifically valid for x'_i.
```

The transformation `T_phys` acts on an observed diffraction pattern or a well-defined forward-model parameterization. It must never be treated as a generic image augmentation.

## Candidate perturbation families

| Family | Measurement/physical interpretation | MVP role | Primary risk |
|---|---|---:|---|
| Global 2θ/zero shift | instrument calibration / zero-offset-type effect | core | confusing it with phase/lattice change |
| Peak broadening | instrument resolution, crystallite size, microstrain | core | nonphysical line-shape or over-severe overlap |
| Noise | counting/statistical detector variation | core | unrealistic distribution or negative intensity |
| Background | air scatter, fluorescence, amorphous/support contribution, baseline drift | core | synthetic class cue / inappropriate baseline |
| Preferred orientation / texture | reflection-intensity reweighting due to orientation distribution | secondary | can erase diagnostic reflections; needs separate analysis |
| Unit-cell variation | strain/temperature/composition-related lattice response | exploratory only | may cross a phase boundary or change the target label |

## Preferred loss family

Let `pθ(x)` denote the class probability vector and `zθ(x)` the logits.

Possible consistency terms include:

```text
MSE(logits):      ||zθ(x) - zθ(x')||²
KL probability:   KL(pθ(x) || pθ(x'))
JS probability:   JS(pθ(x), pθ(x'))
```

Choose one with a documented justification; do not compare loss functions opportunistically on the held-out test set.

## Required train/evaluation conditions

1. **ERM clean baseline:** supervised clean patterns only.
2. **Augmentation-only:** supervised clean and transformed views, without consistency penalty.
3. **Augmentation + consistency:** the same supervised clean and transformed views as augmentation-only, plus a paired consistency penalty.

There is no no-augmentation `consistency-only` condition: the consistency penalty requires both `x` and `T_phys(x)`. A diagnostic condition that removes transformed-view hard-label CE still uses augmentation and must be named `without transformed-view supervision`, not `consistency-only`.

All conditions must use the same backbone, splits, train budget, early-stop criterion, and comparable tuning budget. Conditions 2 and 3 must use the same perturbation draws, two-view forward passes, and classification-loss scaling so their difference is attributable to the consistency term.

## Dataset split requirements

The split unit must be the underlying structure/material identity, never an individual augmented pattern. All views of the same source structure must remain in one split.

Before use, record:

- source data version and license;
- source identifier / crystal structure identifier;
- exact label mapping;
- class distribution by split;
- generation parameters if available;
- overlap between source IDs across train/validation/test (must be zero).

## Evaluation questions

### Clean correctness

- Does the model classify unperturbed patterns correctly?

### Perturbation stability

- Does its prediction remain stable on paired physical views?
- Does the probability vector change smoothly rather than catastrophically?

### Reliability/calibration

- When a prediction changes or becomes uncertain, is confidence appropriately reduced?

### External relevance

- Do conclusions persist, at least qualitatively, on pre-specified real XRD data or repeated measurements?

## Recommended visual artifacts

- paired clean/perturbed pattern panels with effect labels;
- accuracy vs perturbation severity curves;
- FlipRate vs severity curves;
- confidence/consistency scatter plots;
- class-wise heatmaps by perturbation family;
- per-sample churn examples;
- reliability diagrams for clean and shifted distributions;
- real-XRD case studies with preprocessing provenance.

## Vocabulary discipline

Use "measurement perturbation", "stability", "prediction flip", "paired-view consistency", and "external validation" as default language. Use "causal" or "intervention" only where the corresponding assumptions are explicit and defensible.
