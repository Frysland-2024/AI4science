# Research Supervisor MVP — task observability, recovery, evidence review (2026-10-18)

**Status: ENGINEERING PROPOSAL / NOT IMPLEMENTED.** This does not modify scientific claims, rerun frozen V9, authorize new GPU budgets, or supersede AGENTS.md and docs/CURRENT_STATE.md.

## Starting facts, verified 2026-10-18
- Research Bridge already supports GitHub Issue dispatch, approved read-only/code/GPU lanes, local journaling and GPU heartbeats.
- `research_bridge/gpu_tasks.py` writes a local `heartbeat.json` at ~30-second intervals and writes stdout/stderr to local disk, can stop using `STOP`, and attempts to publish bounded public result artifacts via draft PR.
- A normal Codex CLI task launched directly via Desktop Commander (e.g. the Issue #19 nuisance follow-up in `E:\AI4science_nuisance_diag`) is NOT automatically enrolled in Research Bridge; do not pretend this is a bridge-managed job.
- GitHub Issue comments/labels currently convey coarse transitions rather than reliable cross-session progress.
- ChatGPT has a separately configured hourly GitHub conditional watch; it can inspect new commits and bridge-review reports when available, but cannot receive a real-time push directly into an ordinary conversation.
- Formal scientific acceptance requires inspecting primary run artifacts and respecting split/seed/gate/negative-result rules. A process exiting with code 0 only proves technical completion.

## 1. Shared state machine and identity
Define one canonical run_id/job_id and issue number, origin, host ID, and optional PR number for all task origins:
`QUEUED -> CLAIMED -> RUNNING -> UPLOADING -> REVIEW_PENDING -> REVIEWED`.
Terminal/exception states: `BLOCKED`, `FAILED`, `STOPPED`, `STALE_UNCERTAIN`.
All events record `schema_version`, `task_mode`, `owner`, `run_id`, `issue_number`, `attempt`, `host`, `source_sha`, `config_sha256` (if applicable), `started_at`, `updated_at_utc`, `stage`, `status`, and permitted `artifacts` (relative paths + checksums). Process identity must include both pid AND start timestamp to avoid PID-reuse false matches.
Atomic state writes under the shared Git common dir `.git/research_bridge/`, with immutable append-only event log for diagnosis. Never overwrite old run_id artifacts.

## 2. Health monitor (independent of task runner)
Implement `research_bridge/supervisor.py --once --dry-run` and `--once`, invoked by a separate lightweight Windows Scheduled Task every 10 minutes. It never calls Codex or runs GPU on idle checks and must not edit source branches.
- Detect missing heartbeat beyond configurable 10 minutes by checking local time, machine sleep/wake gaps, pid+start time, Windows process tree, logs, exit code, and local journal together.
- If evidence is ambiguous: `STALE_UNCERTAIN` with a single alert, not `FAILED` and never a blind process kill/restart.
- Post to the originating Issue only on state transitions, a confirmed failure, or low-frequency progress milestones (e.g. max once per 30 minutes); avoid writing a Git commit or public Issue comment every 30 seconds.
- Preserve stdout/stderr locally. Public telemetry is sanitized and bounded; never send credentials, absolute local paths, raw spectra, checkpoints or sensitive sample data to this public repo.
- If offline, queue the outbound status event locally and flush after connectivity returns, with stable event_id dedupe.
- Support an explicit registration command for externally launched Codex executions so that *only registered* Desktop Commander / Codex worktrees are claimed as supervised; no retrospective assumption of monitoring.

## 3. Failure classification and recovery
Classify `AUTH_NETWORK`, `MISSING_DEPENDENCY`, `CUDA_OOM`, `TIMEOUT`, `INTERRUPTED_SHUTDOWN`, `SCIENTIFIC_GATE_FAIL`, `VALIDATION_FAIL`, and `UNKNOWN` from grounded logs and process evidence, retaining original failure.
- No automatic retries by default. A low-risk idempotent retrieval/notification failure may retry at most 2 times with bounded exponential backoff and event deduplication.
- A GPU or Codex task restart requires an explicit same-run resume contract (checkpoint integrity/hash, model/optimizer/RNG/training-step state, frozen source/config/seed/split, consistent run budget). If missing, mark `NEEDS_REVIEW`, never restart from scratch or change the science to obtain a positive result.
- Resume uses `attempt+1` under the same logical run, original records immutable. Stop files and user cancellations override any retry logic.
- A failed physical/numerical gate is terminal `BLOCKED` for that approved protocol. Do not 'fix' by lowering a threshold.
- Never auto-merge PRs or modify the approved experiment's test or selection rules.

## 4. Evidence bundle + scientific review trigger
Implement `research_bridge/evidence.py` (or reuse existing GPU allowlist publication) to create a small schema-validated bundle (manifest, run status, gate results, metrics, test summary, provenance, checkpoint hash ledger, source SHA, links to raw *local* evidence only). Use explicit statuses: `NOT_RUN / RUNNING / BLOCKED / FAILED / COMPLETED_UNREVIEWED / SCIENTIFICALLY_REVIEWED`.
- On completion, GitHub Issue becomes `bridge-review` and links to a Draft PR (or sanitized report), with metric field names and units preserved, no inference from log snippets.
- For A/B: inspect paired seeds, held fixed variables, validation-only model/hyperparameter selection, both favorable and unfavorable results, baseline raw JSON, and gate details before claims.
- Review must say: executed scope, supported metrics (source paths + checksums), evidence limitations, whether scientific gates passed, and proposed next steps; 'model got better' cannot be inferred from exit code.
- Reuse the existing hourly ChatGPT GitHub watch for asynchronous review (up to about one-hour latency). Truly event-driven immediate AI review requires an external API/agent service and its own costs. Do not falsely imply this specific ChatGPT session auto-wakes.
- Never start a new experiment simply because the review says a follow-up could be helpful.

## 5. Deliverables and acceptance tests
Code delivery proposed: `research_bridge/supervisor.py`, `research_bridge/events.py`, `research_bridge/evidence.py`, updated `worker.py`/GPU runner integration, `research_bridge/register_supervisor_task.ps1`, unit tests, docs, dry-run logs.

Acceptance:
1. Existing bridge tests still pass; existing Issue #15/#23 journals and run outputs remain untouched.
2. Unit tests simulate stale heartbeat with alive process, exited process, sleep/wake, PID reuse, GitHub outage, duplicate webhook/poll, reboot, and missing report.
3. A dry run does not execute Codex or GPU and makes no GitHub writes.
4. New code and GPU test jobs generate exactly one visible `RUNNING`, one completion status, and bounded progress notices; idempotent re-checks do not spam.
5. Unexpected shutdown preserves old output and results in `STALE_UNCERTAIN` or `NEEDS_REVIEW`, never silent re-training.
6. External Codex executions are only tracked after explicit registration and cannot be confused with another worktree.
7. Completed technical run is still `COMPLETED_UNREVIEWED` until validated from machine-readable scientific evidence.
8. Independent reviewer verifies no GPU is started or old V9 is modified as a side effect of the supervisor.
9. Changes are built and tested on a separate branch, with Draft PR, CI and human review before installation. Do not hot-swap the worker while jobs are active.

## Rollout order
P0: inventory/migrate none; implement read-only supervisor + dry run in a separate branch.
P1: add events + Issue status transitions + offline delivery dedupe, test on disposable mock task.
P2: add classified recovery with safe/no-restart default, simulate interruptions.
P3: introduce evidence schema and route new `bridge-review` to hourly ChatGPT scientific review; verify on a fake synthetic smoke, not frozen scientific tests.
P4: optionally register fresh Codex CLI jobs via explicit launch wrapper and issue-specific labels; do not retroactively claim ownership of Issue #19's already active process.

No task authorization is granted by this document. Engineering work may be assigned separately; a new Issue must be explicitly approved.
