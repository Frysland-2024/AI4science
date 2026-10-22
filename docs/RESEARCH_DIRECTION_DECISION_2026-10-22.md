# Research Direction Decision — 2026-10-22

## Decision (user-stated)
On 2026-10-22 the project lead explicitly decided to **stop pursuing quantitative PXRD parameter prediction/inversion as the active research direction and continue crystal-system prediction**.

This is a research-priority decision, not a claim that parameter inversion is scientifically impossible. Previous inversion experiments, failures, forward-model assets, DONUT-related studies and traditional-refinement comparisons remain historical research artifacts and should not be deleted or represented as successful real-domain inversion.

## Why this decision is reasonable
- The seven-crystal-system classification study already has a completed, controlled ERM-vs-JS protocol, matched-seed simulated evaluations, RRUFF-301 few-shot adaptation and CNRS-318 zero-shot diagnostics.
- In contrast, quantitative parameter prediction went through multiple formulation changes (supervised inversion, physics-based reconstruction loss, measurement/structure separation, DONUT-style self-supervision and refinement-assisted workflows) without a correspondingly mature, stable end-to-end real-data evidence chain.
- The project should prioritize research coherence and a defensible undergraduate thesis rather than expanding the task scope.

## Active scientific question
Can online PXRD simulator provenance (multiple measurement realizations from the *same parent structure*) provide useful relationship supervision beyond class labels for seven-crystal-system classification?

Keep the existing terminology: **shared parent identity → measurement equivalence → relationship supervision**, implemented through JS consistency. This is not a claim of inventing JS.

## Recommended immediate scope
1. Treat crystal-system classification as the only active scientific task; preserve all frozen splits, benchmarks and negative findings.
2. Finish existing evidence packaging: performance, structure-coupled perturbations, parent-budget/data efficiency and real-domain label efficiency, without changing previously frozen outcomes.
3. Archive inversion as an exploratory branch and potential future topic; do not delete code, results or chronology.
4. Keep README-facing scientific claims based on auditable evidence. Do not introduce unsupported quantification claims.

## Evidence already recorded (not newly tested here)
- Simulated single-factor OOD Macro-F1: Dynamic ERM 0.65074; Dynamic JS 0.70534; paired +0.05460 (5/5 seeds favorable).
- RRUFF-301 K=5 few-shot locked-test Macro-F1: 0.3555 vs 0.4099; paired +0.0545.
- CNRS-318 zero-shot Macro-F1: 0.18837 vs 0.20708; small absolute values remain a limitation.

See: docs/CURRENT_STATE.md; docs/PROJECT_HISTORY.md; xrd_robustness/reports/RESULTS.md.

## Chronology / future application narrative
This decision represents **scoping after empirical exploration**, not a retroactive erasure of inversion: the team explored whether classification could lead to quantitative inversion; physics-based fitting and data requirements made that expansion much harder to validate with available evidence; the lead chose to return to the already demonstrated scientific problem and deepen its mechanistic and real-domain evaluation.

This note records direction only. It does **not** claim that any previously scheduled inversion job has been technically cancelled, nor that its branch was removed.
