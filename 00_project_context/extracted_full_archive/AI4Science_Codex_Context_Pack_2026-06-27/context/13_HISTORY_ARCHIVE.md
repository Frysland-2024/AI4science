# 13 — Project History Archive (Curated Timeline)

This is a chronology of **available project-level context**, not a verbatim platform transcript.

## 2025-12 — FerroAI entry point

- User joined Daniel Qi Tan’s group context and was assigned/recommended to reproduce FerroAI.
- Initial question: can the published model be reproduced and trusted for ferroelectric phase-diagram prediction?

## 2026-05 — Reliability/audit mindset crystallizes

- FerroAI reproduction difficulties were recognized as potentially more than user error: release artifact, preprocessing, scaler, model format, and GUI/paper consistency could themselves be reproducibility questions.
- The project reframed toward auditing a public scientific ML artifact.
- User identified the difference between a model that outputs "phase-diagram-like" results and a model that yields reliable materials knowledge.
- Proposed audit tools included literature truth tables, probability landscapes, latent representation analysis, and failure-mode taxonomy.

## 2026-05-29 — SimXRD / XRD reliability direction proposed

- The user formulated a summer project around XRD classification reliability, initially considering causal or intervention-aware learning and protocol-induced confounding.
- A key concern emerged: avoid a benchmark that looks engineered after the fact.
- Decision trajectory: use real measurement perturbations with clear physical mechanisms.

## 2026-06-01 — “One layer + three layers” formulation

- Core statement fixed: the same structure under different physical measurement perturbations has the same label, so prediction should remain stable.
- MVP sequence: clean baseline → perturbation stress test → robustness improvement.
- Measurement perturbations: peak shift, broadening, noise, background, and related effects.
- This replaced an over-ambitious shortcut-learning/confounding-only mainline.

## 2026-06-05 to 2026-06-07 — Execution design and method selection

- The user adopted an engineering pipeline as a minimum standard: controllable scientific ML task → full baseline → evaluation/error analysis → own reliability contribution.
- IRM/invariance was considered but deemed higher-risk for a three-month MVP.
- Consistency regularization became the preferred operational method.
- Required ablation logic became explicit: baseline, augmentation-only, consistency-only, augmentation+consistency.

## 2026-06-07 to 2026-06-11 — Benchmark/story refined

- Project language refined to: **Physically Motivated Consistency Regularization for Robust XRD Symmetry Classification**.
- Required metrics expanded beyond accuracy: FlipRate, churn, calibration, OOD behavior, and paired prediction stability.
- Three central research risks identified: valid label-preserving boundary, rigorous ablation, and sim-to-real closure.
- Real XRD validation was upgraded from optional bonus to a core credibility module.
- The project target was formalized as a diffraction-specific reliability benchmark, inspired by mature robustness/consistency work in CV and medical AI but grounded in XRD mechanisms.

## 2026-06-16 — Data and rights concern

- User recognized that data access/licensing and physical perturbation legitimacy must be checked before implementation, not treated as afterthoughts.

## 2026-06-21 onward — Long-term research identity

- The user clarified a preference for theory-strong, probabilistic/generative/scientific-ML research directions, while keeping reliable ML, uncertainty, inverse problems, and measurement data as a durable main line.

## 2026-06-27 — Codex handoff

- This context pack was created so code agents can act from an explicit source of truth rather than relying on scattered conversation history.

## 2026-07-11 — Ablation logic corrected after reading Hu et al.

- The core comparison was corrected to three conditions: clean baseline, augmentation-only, and augmentation + consistency.
- The former `consistency-only` condition was removed from the active protocol because consistency itself requires a transformed paired view.
- Hu et al.'s structured simulation and domain-disparity decorrelation motivated a phase-two residual-decorrelation candidate, not a replacement for the three-condition MVP.
