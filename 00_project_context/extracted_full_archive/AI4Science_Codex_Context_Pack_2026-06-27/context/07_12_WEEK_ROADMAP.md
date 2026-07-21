# 07 — 12-Week MVP Roadmap

## Definition of done

A credible mini-benchmark with a reproducible data/model/evaluation pipeline, a physically documented perturbation suite, controlled ablations, and at least one real-XRD external-validation component or a transparent explanation of why it remains incomplete.

## Weeks 1–3 — Data and clean baseline

- Obtain/verify data, labels, and rights.
- Create structure-level splits and an immutable split manifest.
- Implement preprocessing audit and simple 1D-CNN baseline.
- Produce clean IID accuracy, class-wise performance, confusion matrix, and reproducibility checks.
- Deliverable: baseline report and data-card draft.

## Weeks 4–5 — Perturbation sandbox

- Implement shift, broadening, noise, background transforms with unit tests.
- Create an evidence ledger; leave unverified parameters explicitly unverified.
- Render clean/perturbed overlay gallery across severity tiers.
- Verify no split leakage and no transform artifacts.
- Deliverable: perturbation module + visual/physics audit.

## Weeks 6–8 — Stress test and failure map

- Run ERM baseline under each perturbation family and severity.
- Calculate accuracy degradation, FlipRate, probability disagreement, calibration, and churn.
- Identify vulnerable classes/material groups where metadata permits.
- Deliverable: reliability benchmark results and failure taxonomy.

## Weeks 9–10 — Robustness improvement and ablation

- Train augmentation-only and augmentation+consistency conditions with identical perturbation draws, classification supervision, and two-view compute.
- Tune only with validation data.
- Run multi-seed comparison and paired analyses.
- Deliverable: ablation table and statistical comparison.

## Weeks 11–12 — Real-XRD loop and storytelling

- Prepare real-XRD preprocessing and a small external validation protocol.
- Execute external cases or document the data-access blocker transparently.
- Assemble report, figures, limitations, and reproducibility package.
- Deliverable: portfolio-quality benchmark/report/presentation.

## Critical gates

Do not advance merely because code executes. Advance only when these are true:

1. Baseline split is verified at source-structure level.
2. Each core transform passes physical and numerical sanity checks.
3. Central evaluation includes augment-only controls.
4. Results are stable across seeds and data subsets.
5. Claims separate simulated findings from real-XRD findings.
