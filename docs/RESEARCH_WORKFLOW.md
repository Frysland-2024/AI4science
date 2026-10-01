# AI4science Research Workflow

**Effective date:** 2026-10-02  
**Purpose:** Keep literature review, experimentation, result interpretation, and project history reproducible instead of relying on conversational memory.

This document expands the operating rules in [`../AGENTS.md`](../AGENTS.md).

## 1. Four canonical entry points

### A. "Where is the project now?"

Read, in order:

1. latest relevant commits;
2. `CURRENT_STATE.md`;
3. the relevant result / evidence-closure document;
4. older history only if needed.

Separate completed, active, archived, and future/optional work.

### B. "Why did we do/change this?"

Read:

1. `CURRENT_STATE.md` for today's interpretation;
2. `PROJECT_HISTORY.md` for the research evolution;
3. relevant commits around the transition.

Do not flatten the history into a tidy post-hoc story. Preserve uncertainty, failed attempts, and changed assumptions.

### C. "Has anyone done this before?"

```text
Current repository claim
        ↓
Define the exact novelty question
        ↓
Search peer-reviewed literature
        ↓
Read primary papers
        ↓
Check code / supplement / dataset when material
        ↓
Compare claim-by-claim with this repository
        ↓
Classify: established / close precedent / partial overlap / unsupported / unknown
```

For the current PXRD study, distinguish:

- online simulation;
- physical perturbation augmentation;
- consistency regularization;
- same-parent / provenance relations;
- measurement-equivalence supervision;
- real-domain evaluation.

### D. "What do the results say?"

```text
Machine-readable result
        ↓
Check run / seed / split identity
        ↓
Recompute or aggregate if needed
        ↓
Compare against the frozen baseline
        ↓
Report community-standard performance
        ↓
Add reliability / strict audit as supporting layers
        ↓
Write only supported claims
```

Do not quote an exact metric from memory when a result artifact exists.

## 2. PXRD evidence set

For a general project question, start from:

- `CURRENT_STATE.md`
- `PXRD_SUPERVISION_FRAMING.md`
- `PXRD_EVIDENCE_CLOSURE.md`
- `../xrd_robustness/reports/RESULTS.md`

Add:

- `PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md` for implementation/fairness/history questions;
- `PXRD_RESULT_REPORTING_STANDARD.md` for metric/statistics questions;
- `PXRD_NOVELTY_LITERATURE_LINEAGE.md` for novelty/related-work questions;
- `PROJECT_HISTORY.md` and Git history for research-evolution questions.

## 3. Literature-review protocol

For each important precedent, record:

- citation / DOI;
- exact task;
- data source and split;
- simulated vs experimental data;
- model and objective;
- what physical information is used;
- whether parent provenance or paired views are used;
- evaluation domain;
- what overlaps with this project;
- what does not overlap;
- confidence level.

A title or abstract alone is insufficient for a strong novelty claim.

## 4. Experiment protocol

Before a scientific experiment:

1. state the question in one sentence;
2. identify the intended changing factor;
3. freeze data, split, backbone, optimizer, budget, seeds, and metrics as appropriate;
4. record whether the run is exploratory, validation, confirmatory, diagnostic, or final;
5. define stopping/selection rules before opening final results when feasible;
6. store machine-readable outputs;
7. retain failed or negative runs when scientifically relevant;
8. update current state/history only after interpreting the evidence.

If a question is already marked CLOSED, do not reopen it merely because another analysis could be run.

## 5. Result-reporting protocol

Use the project reporting hierarchy in `PXRD_RESULT_REPORTING_STANDARD.md`.

At minimum distinguish:

1. **community-standard performance** — Macro-F1, balanced accuracy, accuracy, learning curves, per-class results as appropriate;
2. **supporting evidence** — multi-seed consistency, failure analysis, ECE/NLL/Brier, mechanism diagnostics;
3. **strict audit / reproducibility** — paired/bootstrap uncertainty, leakage checks, manifests, hashes, run records.

Strict audit strengthens or limits interpretation; it does not silently replace the community's normal performance-reporting language.

## 6. Repository write-back protocol

Update `CURRENT_STATE.md` when:

- the active method changes;
- a major result is finalized;
- an evidence question changes status;
- the current next step changes materially;
- the official project framing changes.

Update `PROJECT_HISTORY.md` when:

- a plausible route is rejected or archived;
- a new idea changes the research question;
- a methodological correction changes how earlier evidence is interpreted;
- a major project transition should remain visible to future readers.

Lower-level engineering history can remain in Git commits.

## 7. Public artifact workflow

For a README, manuscript, technical report, figure, or presentation:

```text
CURRENT_STATE + RESULTS
        ↓
select supported claims
        ↓
choose the simplest evidence for each claim
        ↓
draft the narrative/figure
        ↓
fact-check against repository evidence
```

Do not let the communication layer create a stronger claim than the evidence layer.

## 8. Definition of "done"

A research task is complete at the relevant level when:

- **question answered:** an evidence-backed answer exists;
- **analysis done:** a reproducible artifact/result exists;
- **decision done:** current state/history is updated if material;
- **engineering done:** implementation is validated;
- **communication done:** the artifact is fact-checked against current repository state.

A material scientific result that exists only in a chat is not a durable project decision.
