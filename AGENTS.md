# AGENTS.md — AI4science Agent Working Contract

**Effective date:** 2026-10-02  
**Scope:** All AI assistants, coding agents, research agents, and collaborators working in this repository.

This file defines **how an agent must obtain project truth, choose tools, make changes, and write important decisions back to the repository**. It is an operating contract, not a scientific-results document.

## 1. Source-of-truth hierarchy

When sources disagree, use the following order unless the user explicitly makes a new decision:

1. Current frozen configs, raw/result artifacts, run records, and code relevant to the claim.
2. `docs/CURRENT_STATE.md` for the current project state and current scientific framing.
3. Current closure / reporting / framing documents, especially:
   - `docs/PXRD_SUPERVISION_FRAMING.md`
   - `docs/PXRD_EVIDENCE_CLOSURE.md`
   - `docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`
   - `docs/PXRD_RESULT_REPORTING_STANDARD.md`
4. `xrd_robustness/reports/RESULTS.md` and machine-readable result JSON/CSV files.
5. `README.md` and subsystem READMEs.
6. `docs/PROJECT_HISTORY.md` and dated history notes for **why the project changed**.
7. Chat memory, summaries, or prior conversational recollections.

Historical documents explain evolution; they do not override the current state.

## 2. Mandatory first step for project questions

For any question about AI4science/XRD **progress, current method, results, next step, project identity, or why a decision was made**:

1. Read the latest repository commits.
2. Read `docs/CURRENT_STATE.md`.
3. Read only the additional files needed for the question.
4. If the question is historical, consult `docs/PROJECT_HISTORY.md` and the relevant dated history note.
5. Do not answer from conversational memory alone.

A recent commit does not automatically change the scientific state; inspect what it changed.

## 3. Tool-routing rules

### Project state / implementation / provenance
Use **GitHub** first. Repository evidence is authoritative for committed project facts.

### Local files, running jobs, checkpoints, environments, or terminal work
Use **Remote Desktop Commander** when an authorized machine is connected. Do not infer local state from GitHub.

### Literature novelty / "has anyone done this?" / related work
First establish the current project claim from the repository, then use academic-search sources such as **Consensus / SciSpace / Sider Scholar**, followed by **Exa / Parallel Search / web** when code, supplements, datasets, author pages, or newer materials are needed. Distinguish:
- what the paper actually claims,
- what its code/data show,
- and what is our interpretation.

### Models / datasets / public ML resources
Use **Hugging Face** when relevant.

### Mathematical or symbolic verification
Use **Wolfram** when exact symbolic/numerical verification materially improves confidence.

### Experimental results / CSV / JSON / metrics
Read the underlying result files first, then use the **Data Analytics** workflow for aggregation, paired comparisons, plots, uncertainty, and report-quality analysis. Never reconstruct exact numbers from memory.

### Presentations / visual communication
Ground all scientific content in repository evidence first; then use **Gamma / Canva** for presentation and visual refinement. Visual convenience must not alter scientific claims.

### Applications / outreach
Use repository-backed project facts first; then **Google Drive**, **Gmail**, and **Google Calendar** for documents, correspondence, and scheduling.

## 4. Current PXRD framing guardrail

The current project hierarchy is:

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
- Distinguish performance evidence, reliability evidence, and strict statistical audit according to `docs/PXRD_RESULT_REPORTING_STANDARD.md`.
- A local engineering change is not automatically a scientific change.

## 6. Write-back rule

Important discussion must not remain only in chat.

Update the repository when a discussion changes any of the following:

- project identity or scientific framing;
- active vs archived method;
- experiment protocol, frozen configuration, or evaluation role;
- interpretation of a major result;
- evidence status (OPEN / CLOSED / ACTIVE WRITING);
- next-step research direction;
- application narrative that materially changes how the project evolution is explained.

Write-back destinations:

- **Current truth:** `docs/CURRENT_STATE.md`
- **Why/when the decision changed:** append to `docs/PROJECT_HISTORY.md` or create a dated history note when the event needs a self-contained record.
- **Result change:** update the relevant report + machine-readable artifact + `CURRENT_STATE.md`.
- **Framing change:** update the relevant framing document + `CURRENT_STATE.md`.
- **Workflow change:** update this file and/or `docs/RESEARCH_WORKFLOW.md`.

Minor explanations, tutoring, brainstorming, and wording alternatives do **not** need repository write-back.

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

The purpose is to preserve the real research path, including false starts and corrections, for future scientific writing and admissions narratives.

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
Write material decisions/results back to GitHub
```

The goal is not maximum tool usage. The goal is a reproducible chain from question → evidence → decision → repository record.
