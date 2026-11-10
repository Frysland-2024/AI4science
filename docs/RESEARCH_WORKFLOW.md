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

## 9. Healthy Vibe Research — human handoff (2026-11-10)

**Goal:** Eliminate the project owner as a real-time relay among ChatGPT, Codex, GitHub, and GPU. Separate the *scientific decision* from the *approved execution*. This policy does not authorize tasks currently blocked.

### Ownership and permissions

- **Owner (L3):** research hypothesis, protocol/dataset/split changes, Test/RRUFF release, publication claims, extra GPU rental or compute budget, and permission to enter the next major stage. Always require explicit approval.
- **GPT (planning/review):** consult AGENTS.md, CURRENT_STATE and actual evidence; prepare bounded tasks with acceptance/stop conditions. Conversational plans do not authorize GPU runs.
- **Codex/execution runner (L1/L2):** perform only approved maintenance and SHA-frozen steps within the resource budget. Existing HPO proposal/recovery rules apply; retries must be bounded, logged and must not silently change scientific contracts.
- **Reporting:** put routine updates in existing Issue #55 and canonical evidence; do not create new Issues, PRs, branches or narrative Markdown just to record progress. Follow AGENTS.md risk-based change delivery.
- **Retired path:** research_bridge is not an active job manager. Do not reinstall its worker/supervisor or scheduled tasks.

### Status handoff

| Owner-facing state | Meaning | Action |
| --- | --- | --- |
| COMPLETED | Scope-specific outputs exist, not necessarily scientifically certified | Review once, then close or approve next stage |
| RUNNING | A live V11 runner lock is confirmed on that same machine | No routine intervention |
| BLOCKED | Malformed/inconsistent evidence or an explicit gate failure | Investigate; no automatic science changes |
| NEEDS_DECISION | Awaiting approval or execution cannot be confirmed | Decide at the next review window unless safety/cost risk is urgent |

Read-only local commands:

~~~powershell
cd E:\AI4science
python server_migration/research_status.py
python server_migration/research_status.py --json
~~~

The script reads only local server_runs/v11_a0_js_optuna metadata and probes an *existing* process lock. It never touches Test/RRUFF, launches or resumes GPU work, or assumes that a file's existence means a live process. It does not monitor another computer. A local metadata-complete status is not a substitute for hash-verifying checkpoints and scientific acceptance via the V11 runner's strict validators.

### Review cadence — no notification flood

- Recommended owner review windows: **10:00 and 20:30** in the owner's chosen local timezone. Between those windows, capture ideas without altering a running approved protocol.
- One brief digest: completed/running/blocked/needs approval, one next decision, evidence URL, and observable budget status. Suppress unchanged messages wherever the scheduling system supports it.
- No automatic phase expansion: complete HPO and independent confirmation, then stop for separate final-training approval. Complete final training, then stop before held-out synthetic Test and real RRUFF.
- Distinguish *the project is unfinished* from *today's research decisions are complete*. Outside review windows, an authorized runner may continue without owner attention.

### V11 transition (dated, not a live heartbeat)

As of 2026-11-10, laptop Train-only gradient evidence is closed. Cuifa Stage 0/HPO, final training and Test/RRUFF have not run and are not newly authorized by this workflow. See CURRENT_STATE.md and Issue #55 for current authority; cross-check live host logs before reporting execution.

### Controlled local task dispatch (Codex review / bounded V11 preflight)

Source: server_migration/controlled_dispatch.py; tests:
server_migration/tests/test_controlled_dispatch.py. This is a limited
execution helper, NOT a new scientific protocol or an old-Bridge revival.

- Allowlisted lanes: codex_review (read-only ephemeral Codex CLI),
  v11_plan, v11_smoke (fixed Windows launcher commands). HPO, final,
  Test/RRUFF, arbitrary shell, Codex write/PR, and GPU rental are blocked.
- Private tasks, approvals and journals live inside the existing Git common
  directory: controlled_dispatch_v1/tasks, approvals, runs.
  Do NOT commit prompts, logs or local data.
- Every task requires exact source SHA, hostname, explicit local approval
  binding the entire task JSON SHA256, and a clean working tree. Failed,
  stale or inconsistent jobs do not auto-retry; a new task ID and renewed
  approval are needed. A single-instance lock and bounded subprocess
  timeouts prevent duplicate launch. Uncertainty is not reported as live.
- Current laptop may have uncommitted work; NEVER reset/pull over it
  merely to satisfy a dispatch preflight. No work is queued by default.
- Separate human approval for cuifa Stage 0, full HPO, final training and
  opening held-out Test/RRUFF still applies (Issue #55).

Read-only inspection:

~~~powershell
cd E:\AI4science
python server_migration/controlled_dispatch.py --status
python server_migration/controlled_dispatch.py --dry-run
~~~

A *private* task under .git/controlled_dispatch_v1/tasks/review_001.json
uses this schema, with values filled from the approved actual machine:

~~~json
{
  "version": 1,
  "task_id": "review_001",
  "lane": "codex_review",
  "source_sha": "REPLACE_WITH_40_LOWERCASE_GIT_SHA",
  "expected_hostname": "REPLACE_WITH_COMPUTERNAME",
  "prompt": "Review V11 code and AGENTS.md for reproducible bugs. Do not modify files."
}
~~~

Once reviewed, the owner explicitly authorizes this task:

~~~powershell
python server_migration/controlled_dispatch.py --approve review_001
python server_migration/controlled_dispatch.py --dry-run
~~~

A local Windows Scheduled Task named AI4science-Controlled-Dispatch may
check the approved queue every 30 minutes using --once and IgnoreNew.
An empty or unapproved queue launches NOTHING. It works only while the
authorized machine is available; it cannot remotely check cuifa or report
private logs through GitHub. The 10:00/20:30 ChatGPT summaries are
independent read-only checks and must never claim access to a disconnected
host. Disable the named task before uninstalling it. No public Issues/PRs
should be created for normal dispatcher polls.

### Controlled dispatcher deployment (2026-11-10)

**Active on the owner laptop:** Windows scheduled task **AI4science-Controlled-Dispatch**
runs every 30 minutes. Its private source and one-shot task records are under
.git/controlled_dispatch_v1/. It supports only explicitly approved, pinned
read-only Codex review and bounded V11 plan/smoke preflight; it cannot
launch HPO/final or create a PR. Read its status on the same laptop:

~~~powershell
python E:\AI4science\.git\controlled_dispatch_v1\controlled_dispatch.py --root E:\AI4science --status
~~~

**No duplicate scheduler:** an experimental second Windows task,
**AI4science-Controlled-Dispatcher**, was briefly installed and has been
**disabled** so only one active laptop task consumes approvals.
Neither task reinstates the retired research_bridge or October PhaseRouter.

**Deferred cuifa GPU lane:** source-controlled
server_migration/controlled_dispatcher.py and its tests offer a bounded
one-shot HPO dispatch route, but this is **not installed on cuifa**.
Future activation requires actual target-machine Stage0 proof, including
CUDA, sufficient resources, full six-profile frozen Validation,
cache integrity and checkpoint/restart checks; hash-pinned private
artifacts; matching source SHA; and separate budget approval. Its
max-gpu-hours budget is a **soft stop between HPO trials**, not a hard
wall-time or cloud-spending guarantee. No real cuifa Stage0 or HPO
can be inferred from this implementation.

**Human-facing review cadence:** use the two existing ChatGPT morning/evening
summaries, preferably with read-only local state if the authorized machine
is online; otherwise explicitly say local state is unknown. Never push
idle heartbeats, open routine PRs/Issues or auto-expand scientific scope.

