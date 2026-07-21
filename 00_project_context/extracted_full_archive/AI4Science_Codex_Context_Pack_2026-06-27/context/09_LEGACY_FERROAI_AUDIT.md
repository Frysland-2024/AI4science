# 09 — Legacy FerroAI Audit Context

## Why this history matters

The current XRD reliability benchmark did not appear from nowhere. It grew out of a FerroAI audit question:

> A model can output a visually/plausibly convincing materials phase diagram while still failing to represent reliable materials knowledge.

This became the user’s general scientific-ML instinct: distinguish a model’s **output plausibility** from an auditable evidence chain, physical validity, calibration, and robustness.

## Legacy FerroAI project summary

- FerroAI was studied as a composition + temperature → phase/symmetry classifier for ferroelectric phase diagrams.
- The work shifted from a simple reproduction exercise to auditing a publicly released model artifact.
- Important audit concerns included: opaque invocation protocol, possible mismatch between release artifact/GUI/paper description, scaler/preprocessing ambiguity, model-file format/compatibility issues, and system-specific prediction failures.
- A key technical trap was double-softmax / output-mode interpretation; fixing it showed that the released model could produce tetragonal predictions in some cases (for example PbTiO3), implying that failures such as BaTiO3 could be system-specific rather than a universal output-layer defect.
- Candidate analysis tools included probability landscapes, latent/embedding clustering, reviewed literature truth tables, failure taxonomy, and public-artifact reproducibility framing.

## Legacy lesson carried forward

1. A high score or visually plausible output does not prove scientific reliability.
2. The data-generating/measurement process and the model’s representation both matter.
3. A comparison needs an evidence-backed reference, not intuition.
4. Model behavior needs attribution: data/representation/decision boundary/implementation protocol.
5. A public release artifact is a legitimate object of reproducibility and reliability audit.

## Why it is not the active code target

The active project is **not** to continue FerroAI phase-diagram auditing. It is to build an XRD measurement-robustness benchmark and consistency-learning study. Do not import FerroAI-specific data schemas, class semantics, or modeling assumptions into the SimXRD codebase without explicit request.

## Verbatim legacy memory

The original available memory export is preserved as:

```text
legacy/chatgpt_project_memory_2026-05-15.md
```

It is historical context, not the current source of truth.
