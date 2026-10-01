# AGENTS.md — AI4science Research Agent Contract

**Effective date:** 2026-10-02  
**Scope:** AI assistants, coding agents, research agents, and collaborators working in this repository.

This file defines how an agent should obtain project truth, change the codebase, and preserve scientific provenance. It is an operating contract, not a scientific-results document.

## 1. Source-of-truth hierarchy

When sources disagree, use the following order unless a new scientific decision explicitly supersedes it:

1. Frozen configs, machine-readable results, run records, manifests, and code relevant to the claim.
2. `docs/CURRENT_STATE.md` for the current project state and scientific framing.
3. Current evidence / reporting / framing documents, especially:
   - `docs/PXRD_SUPERVISION_FRAMING.md`
   - `docs/PXRD_EVIDENCE_CLOSURE.md`
   - `docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`
   - `docs/PXRD_RESULT_REPORTING_STANDARD.md`
4. `xrd_robustness/reports/RESULTS.md` and linked machine-readable result artifacts.
5. Package and repository READMEs.
6. `docs/PROJECT_HISTORY.md` and Git history for why the project changed.
7. Conversational summaries or recollection.

Historical documents explain evolution; they do not override current state.

## 2. Mandatory first step for project questions

For questions about progress, current method, results, next steps, project identity, or historical decisions:

1. inspect the latest relevant commits;
2. read `docs/CURRENT_STATE.md`;
3. read only the evidence files needed for the question;
4. for historical questions, consult `docs/PROJECT_HISTORY.md` and relevant commits;
5. do not answer from conversational memory alone.

A recent commit does not automatically change the scientific state; inspect what changed.

## 3. Evidence-routing rules

### Project state / implementation / provenance
Start from the repository and tracked evidence.

### Local-only assets
If the question depends on local checkpoints, ignored datasets, running jobs, or machine-specific outputs, inspect an authorized local environment. Do not infer local state from Git alone.

### Literature novelty / related work
First define the exact repository claim, then search primary literature. When important, inspect the paper, supplement, code, and dataset rather than relying on titles or snippets.

Separate:
- what a source explicitly claims;
- what its implementation/data demonstrate;
- and what is an interpretation.

### Experimental results
Read the underlying CSV/JSON/result record before quoting exact numbers. Recompute or aggregate when needed; do not reconstruct exact values from memory.

### Mathematical checks
Use exact symbolic or numerical verification when precision materially affects the conclusion.

### Public communication
Ground figures, reports, manuscripts, and summaries in repository evidence. Presentation convenience must not alter scientific claims.

## 4. Current PXRD framing guardrail

The current hierarchy is:

- **Project:** supervised learning / PXRD crystal-system classification.
- **Method core:** structured / relational supervision from simulator provenance.
- **Concrete realization:** JS consistency regularization.
- **Evaluation/result settings:** simulated OOD, CNRS zero-shot, RRUFF few-shot adaptation / label efficiency, calibration.
- **Broad context:** AI4Science / AI for Characterization.

Do not casually relabel the whole project as robustness research, representation learning, domain adaptation, computer vision, or physics-informed ML. See `docs/PXRD_SUPERVISION_FRAMING.md`.

## 5. Experiment-integrity rules

- Do not reopen a CLOSED evidence question without a changed scientific claim or new contradictory evidence.
- Do not alter frozen test data, selected checkpoints, seeds, metrics, or hyperparameters after seeing final results.
- Do not add a new loss/model/experiment merely to make the story look stronger.
- Preserve negative, uncertain, and cross-zero statistical results.
- Distinguish headline performance, supporting reliability evidence, and strict statistical audit according to `docs/PXRD_RESULT_REPORTING_STANDARD.md`.
- A local engineering change is not automatically a scientific change.

## 6. Repository write-back rule

Important scientific discussion must not remain only in chat.

Update the repository when a discussion changes:

- project identity or scientific framing;
- active vs archived method;
- experiment protocol, frozen configuration, or evaluation role;
- interpretation of a major result;
- evidence status;
- next-step research direction;
- the public explanation of how the project evolved.

Write-back destinations:

- **Current truth:** `docs/CURRENT_STATE.md`
- **Major research evolution:** `docs/PROJECT_HISTORY.md`
- **Result change:** relevant report + machine-readable artifact + `CURRENT_STATE.md`
- **Framing change:** relevant framing/evidence document + `CURRENT_STATE.md`
- **Workflow change:** this file and/or `docs/RESEARCH_WORKFLOW.md`

Minor tutoring, brainstorming, and wording alternatives do not require repository write-back.

## 7. Decision-record format

For a material project decision, preserve:

```text
Date
Question / previous assumption
New evidence or reasoning
Decision
What changes now
What does NOT change
Status: ACTIVE / ARCHIVED / CLOSED / FUTURE
Relevant files / commits
```

The purpose is to preserve the real research path, including false starts and corrections, for scientific and retrospective writing.

## 8. Default working loop

```text
Read current state
      ↓
Inspect relevant evidence
      ↓
Research / analyze / execute
      ↓
Separate fact from inference
      ↓
Make the smallest justified change
      ↓
Validate
      ↓
Write material decisions/results back to the repository
```

The goal is a reproducible chain from question → evidence → decision → repository record.
