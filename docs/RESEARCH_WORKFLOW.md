# AI4science Research Workflow

**Effective date:** 2026-10-02  
**Purpose:** Turn the repository plus connected research tools into a repeatable workflow instead of relying on conversational memory.

This document expands the operating rules in [`../AGENTS.md`](../AGENTS.md). Scientific truth remains in the relevant configs, artifacts, current-state documents, and result files.

## 1. Four canonical entry points

### A. "Where is the project now?"
Read, in order:

1. latest Git commits;
2. `CURRENT_STATE.md`;
3. relevant result / closure document;
4. only then older history if needed.

Output should clearly separate:
- completed;
- active;
- archived;
- future/optional.

### B. "Why did we do/change this?"
Read:

1. `CURRENT_STATE.md` to learn today's answer;
2. `PROJECT_HISTORY.md` to reconstruct the evolution;
3. dated history notes / commits around the transition.

Do not flatten the history into a tidy post-hoc story. Preserve uncertainty, failed attempts, and changed assumptions.

### C. "Has anyone done this before?"
Workflow:

```text
Current repository claim
        ↓
Define the exact novelty question
        ↓
Peer-reviewed academic search
        ↓
Read primary papers
        ↓
Check code / supplement / dataset when material
        ↓
Compare claim-by-claim with this repository
        ↓
Classify: established / close precedent / partial overlap / unsupported / unknown
```

Never search for a vague label alone when the actual claim is more precise. For the current PXRD work, distinguish:
- online simulation,
- physical perturbation augmentation,
- consistency regularization,
- same-parent / provenance relations,
- measurement-equivalence supervision,
- real-domain evaluation.

### D. "What do the results say?"
Workflow:

```text
Machine-readable raw result
        ↓
Check run/seed/split identity
        ↓
Recompute or aggregate
        ↓
Compare against the frozen baseline
        ↓
Report community-standard performance
        ↓
Add reliability / strict audit as secondary layers
        ↓
Write only supported claims
```

Do not quote a metric from chat memory when a result file exists.

## 2. Tool map

| Need | Preferred capability | Rule |
|---|---|---|
| committed project facts | GitHub | first stop for project questions |
| local machine / terminal / running job | Remote Desktop Commander | use only on authorized machine |
| peer-reviewed evidence | Consensus / SciSpace / Sider Scholar | primary literature first |
| web/code/supplement/dataset discovery | Exa / Parallel Search / web | use after claim is defined |
| model/dataset ecosystem | Hugging Face | inspect concrete resources |
| exact math/symbolic checks | Wolfram | use where precision matters |
| result aggregation and audit | Data Analytics | start from raw CSV/JSON |
| collaborative docs | Google Drive | repository remains scientific source of truth |
| presentation generation | Gamma / Canva | content must be repository-grounded |
| outreach / meetings | Gmail / Calendar | use verified project facts |

## 3. PXRD evidence workflow

For the current PXRD project, use this minimum reading set unless the question is narrower:

- `CURRENT_STATE.md`
- `PXRD_SUPERVISION_FRAMING.md`
- `PXRD_EVIDENCE_CLOSURE.md`
- `../xrd_robustness/reports/RESULTS.md`

Add:
- `PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md` for implementation/history questions;
- `PXRD_RESULT_REPORTING_STANDARD.md` for metric/statistics questions;
- `PXRD_NOVELTY_LITERATURE_LINEAGE.md` for novelty/related-work questions;
- `PROJECT_HISTORY.md` for research-evolution questions.

## 4. Literature-review protocol

For each important precedent, record at least:

- citation / DOI;
- exact task;
- data source and split;
- simulated vs experimental data;
- model and objective;
- what physical information is used;
- whether parent provenance or paired views are used;
- evaluation domain;
- what overlaps with our work;
- what does not overlap;
- confidence level.

A paper title or abstract alone is insufficient for a strong novelty claim.

## 5. Experiment protocol

Before running a scientific experiment:

1. State the question in one sentence.
2. Identify the only factor intended to change.
3. Freeze data, split, backbone, optimizer, budget, seeds, and metrics as appropriate.
4. Record whether the run is exploratory, validation, confirmatory, diagnostic, or final.
5. Define the stopping/selection rule before opening final results when feasible.
6. Store machine-readable outputs.
7. Keep failed/negative runs when scientifically relevant.
8. Update state/history only after interpreting the evidence.

If a question is already marked CLOSED, do not reopen it merely because another analysis could be run.

## 6. Result-reporting protocol

Use three layers:

1. **Performance layer:** Macro-F1, balanced accuracy, accuracy, mean ± SD, multi-seed consistency, learning curves, per-class results as appropriate.
2. **Reliability layer:** ECE, NLL, Brier or related probability-quality evidence.
3. **Strict audit:** paired/bootstrap intervals, class-stratified uncertainty, leakage/composition checks.

The strict audit strengthens or limits interpretation; it does not silently replace the community's normal performance-reporting language.

## 7. Repository write-back protocol

### Update `CURRENT_STATE.md` when
- the active method changes;
- a major result is finalized;
- an evidence question changes status;
- the current next step changes materially;
- the official project framing changes.

### Update `PROJECT_HISTORY.md` when
- a previously plausible route is rejected or archived;
- a new idea changes the research question;
- a methodological correction changes how prior work is interpreted;
- a major project transition should be preserved for admissions / retrospective writing.

### Create a dated history note when
the event is complex enough that future readers should be able to understand it without reconstructing a long chat or many commits.

## 8. Communication / artifact workflow

### PPT or advisor report
```text
CURRENT_STATE + RESULTS
        ↓
select 1–3 supported claims
        ↓
choose the simplest evidence for each claim
        ↓
build narrative
        ↓
Gamma / Canva / slides tooling
        ↓
final fact check against repository
```

### Admissions narrative
Use `PROJECT_HISTORY.md` for evolution and `CURRENT_STATE.md` for today's interpretation. Do not rewrite failed branches as if the final answer had been obvious from the beginning.

### Email / outreach
Verify names, dates, project claims, and requested attachments before drafting/sending.

## 9. Minimal answer discipline

The user prefers concise answers. Use the full workflow internally, but expose only:
- the answer;
- the decisive evidence;
- the immediate consequence.

Long process narration is unnecessary unless requested.

## 10. Definition of "done"

A research task is done when the relevant level is complete:

- **question answered:** evidence-backed answer exists;
- **analysis done:** reproducible artifact/result exists;
- **decision done:** current state/history updated if material;
- **engineering done:** implementation validated;
- **communication done:** artifact is fact-checked against current repository state.

A useful result that remains only inside a chat is **not** a durable project decision.
