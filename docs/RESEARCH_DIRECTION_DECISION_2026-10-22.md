# Research Direction Decision — 2026-10-22

> **Current-scope addendum (2026-10-26):** The undergraduate thesis is limited to writing up and defending the completed PXRD seven-crystal-system classification study: same-parent measurement-equivalence supervision versus matched Dynamic ERM. No new experiments are in current scope. Parameter inversion, including PR #46, is Archived / Inactive; its partial synthetic results are exploratory and do not establish method superiority or real-domain validity. The 2026-10-23 scale-up axes are deferred. See [current state](CURRENT_STATE.md), [history](PROJECT_HISTORY.md), and [README](../README.md).

> **Historical scope addendum (2026-10-23; superseded 2026-10-26):** The project lead formally confirmed that the only active scientific task is machine-learning-based PXRD seven-crystal-system classification. The next stage has exactly three evaluation axes: RRUFF real-domain zero-shot Accuracy/Macro-F1; confidence calibration (ECE primary, NLL/Brier/reliability diagrams supporting); and simulated-data efficiency by independent training-parent count under matched Dynamic ERM/Dynamic JS budgets. CNRS remains optional secondary evidence. Quantitative parameter prediction/inversion, lattice-parameter recovery, Forward Reconstruction Loss, DONUT-related work, and automated refinement are Archived / Inactive. See [current state](CURRENT_STATE.md), [history](PROJECT_HISTORY.md), and the [scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).


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
3. Archive inversion as historical evidence and preserve its code, results and chronology; no inversion task or next-stage plan is active.
4. Keep README-facing scientific claims based on auditable evidence. Do not introduce unsupported quantification claims.

## Evidence already recorded (not newly tested here)
- Simulated single-factor OOD Macro-F1: Dynamic ERM 0.65074; Dynamic JS 0.70534; paired +0.05460 (5/5 seeds favorable).
- RRUFF-301 K=5 few-shot locked-test Macro-F1: 0.3555 vs 0.4099; paired +0.0545.
- CNRS-318 zero-shot Macro-F1: 0.18837 vs 0.20708; small absolute values remain a limitation.

See: docs/CURRENT_STATE.md; docs/PROJECT_HISTORY.md; xrd_robustness/reports/RESULTS.md.

## Chronology / future application narrative
This decision represents **scoping after empirical exploration**, not a retroactive erasure of inversion: the team explored whether classification could lead to quantitative inversion; physics-based fitting and data requirements made that expansion much harder to validate with available evidence; the lead chose to return to the already demonstrated scientific problem and deepen its mechanistic and real-domain evaluation.

This note records the original 2026-10-22 direction decision. The 2026-10-26 addendum above records the current thesis scope and supersedes the historical 2026-10-23 addendum and any earlier inversion or scale-up task instructions. This file does not report a technical scheduler state; historical commands or authorizations below must not be treated as permission to execute an inversion task.
