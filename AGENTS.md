# AGENTS.md — Research Agent Operating Rules

## Current research direction (2026-11-09)

**Active:** PXRD seven-crystal-system classification with same-parent Dynamic JS consistency. Simulator integration PR #58 is merged. The 154,975-record structure library is collected but not yet fully integrated into V11 training. **First complete [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61) (schema/PeakTable/integrity/readiness); only then consider [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) (bounded GPU tuning on 108,478 training parents).** GPU rental/training requires explicit authorization.

**Do not:** recollect the existing structure library, restart owner-cancelled legacy 9,842-parent Optuna, optimize against held-out synthetic test or real RRUFF, reopen archived parameter inversion/DONUT/AutoLab tasks, or treat planning as executed experiments.

**Historical:** the October 26 write-up-only freeze and the November 3 simulator-first phase are superseded as execution instructions. Preserve their evidence and rationale in Git history, not as current commands.

## Minimal operating protocol

1. Read `docs/CURRENT_STATE.md`, current issues #61/#55, relevant code, and machine-readable evidence; check for newer conflicting execution decisions.
2. Execute only the specifically authorized, smallest necessary change. Protect frozen results, dataset splits, checkpoints and local worktrees.
3. Verify tests/logs before claiming completion. Distinguish code merged, data collected, data ready, model trained and benchmark validated.
4. Update `docs/CURRENT_STATE.md` only for **material** scientific or execution changes. Add a concise decision entry to `docs/PROJECT_HISTORY.md` only for genuine direction changes, not routine brainstorming.
5. Keep public README focused on present method, verified results and reproducibility. Preserve detailed historical evidence in reports, archived documents and Git history.

## Historical full agent policy

The following is retained for provenance and technical safeguards. **Any superseded historical execution instruction is non-operative.** The current section above and newly authorized work take precedence.

---

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

## 2026-11-03 ACTIVE THESIS RESTART — replaces 2026-10-26 execution freeze

**The project lead explicitly restarted the undergraduate thesis.** This newer decision supersedes the 2026-10-26 *no new research* execution instruction below, which remains historical evidence only. Active project: PXRD seven-system classification, retained same-parent Dynamic JS consistency, improving absolute RRUFF experimental classification performance. **Phase 1 deliverable is a runnable versioned new simulator integrated and tested in `xrd_robustness/`, not a literature-only report** (implementation task [Issue #53](https://github.com/Frysland-2024/AI4science/issues/53)). Inspect/reuse SimXRD/Pysimxrd, GSAS-II, ML4pXRDs and selected equivalents; do not copy broken or label-changing operators. Retain old simulator, frozen configs, datasets and old outputs. **Only after simulator implementation passes tests, compare architectures** (ResNet-18-GN+JS vs CNN11+JS). No architecture training as part of Phase 1. The separate `research_bridge` code lane still has an old protected-path allowlist and cannot autonomously modify `xrd_robustness/`; do not misrepresent a GitHub Issue as executed code. For current truth read [CURRENT_STATE](docs/CURRENT_STATE.md) and [simulator candidates](docs/PXRD_SIMULATOR_CANDIDATES_2026-11-03.md).

---

## Historic thesis scope — decision dated 2026-10-26 (superseded for execution on 2026-11-03)

The sole current undergraduate thesis line is to write up and defend the completed PXRD seven-crystal-system classification study. Its scientific question is whether simulator-known same-parent measurement equivalence, used as relationship supervision, improves classification over matched Dynamic ERM. The controlled ResNet-18-GN Dynamic JS vs Dynamic ERM study is complete and frozen; **no new experiments are in current thesis scope**.

Report the frozen evidence with its limits: simulated OOD Macro-F1 gain +5.46 percentage points across five matched seeds; RRUFF-301 K=1/2/5 as few-shot evidence; CNRS-318 with its low absolute accuracy and uncertainty; and the parent-budget result as post-main supplementary evidence that does not support a numeric structure-saving claim.

PR #46 is a **partial, archived synthetic parameter-inversion exploration**, not evidence for the classification method. It scored 42 models and 8,085 records; the q-accuracy gate passed 0/42 and the per-DOF cell-MAE constraint passed 41/42. Its PR43 held-out parents had already been evaluated; new-architecture stress and real RRUFF validation were not run. Do not claim inversion superiority, real-domain validity, independent confirmation, or exact reproduction of XQueryer, SimXRD-4M, CPICANN, or PyWPEM.

Parameter inversion, lattice recovery, Forward Loss, DONUT-related workflows, automatic refinement, and the ferroelectric pre-refinement proposal remain **Archived / Inactive**. The 2026-10-23 classification scale-up plan and Issue #49 are **DEFERRED**, not current tasks or thesis acceptance gates. PR #46 is closed unmerged; Issue #44 is closed as not planned. A historical plan, issue, code directory, or earlier authorization does not reactivate work. Reopen a direction only after a new explicit decision is recorded in [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) and [docs/PROJECT_HISTORY.md](docs/PROJECT_HISTORY.md).

## 5. Current PXRD framing guardrail

The current hierarchy is:

- **Project and thesis:** supervised learning / PXRD seven-crystal-system classification; thesis work is closure and reporting of the frozen study.
- **Research question:** whether simulator-retained same-parent identity can provide additional relationship supervision beyond class labels.
- **Method core:** structured / relational supervision from simulator provenance.
- **Concrete realization:** JS consistency regularization.
- **Completed evidence:** simulated OOD, RRUFF few-shot adaptation, CNRS zero-shot, and the supplementary parent-budget study, each described with its task-specific limits.
- **Archived / inactive:** quantitative parameter inversion, Forward Loss, DONUT-related work, and automatic refinement.
- **Deferred:** RRUFF zero-shot scale-up, new calibration evaluation, parent-data expansion, simulator upgrade, training retuning, and architecture comparison. These are not active tracks.

Do not casually relabel the whole project as robustness research, representation learning, domain adaptation, computer vision, or physics-informed ML. See `docs/PXRD_SUPERVISION_FRAMING.md`.

## 6. Experiment-integrity rules

- Do not reopen a CLOSED evidence question without a changed scientific claim or new contradictory evidence.
- Do not alter frozen test data, selected checkpoints, seeds, metrics, or hyperparameters after seeing final results.
- Do not add a new loss/model/experiment merely to make the story look stronger.
- Preserve negative, uncertain, and cross-zero statistical results.
- Distinguish headline performance, supporting reliability evidence, and strict statistical audit according to `docs/PXRD_RESULT_REPORTING_STANDARD.md`.
- A local engineering change is not automatically a scientific change.

## 7. Repository write-back rule

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

## 8. Decision-record format

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

## 9. Default working loop

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
