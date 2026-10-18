# Research Task Bridge

**Status:** implemented as an engineering hand-off module; no AutoLab experiment runner or automatic scientific analysis is included.

## Purpose and boundary

The bridge uses versioned GitHub Issue forms as its queue. ChatGPT can create an Issue with the repository's **Research task for local Codex** form; a local worker polls the repository and processes one bounded task at a time. The module reuses the responsibility split in [the AutoLab plan](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md): transport and provenance live here, while experiment planning/execution remains a separate future AutoLab component.

The v1 action allowlist is intentionally small:

- `codex_read_only`: invokes the installed Codex CLI with `--sandbox read-only` in a disposable snapshot. The snapshot includes the project instructions, research workflow, AutoLab plan, and optionally tracked source files. It excludes tests, datasets, results/reports, manifests, run outputs, ignored files, and files larger than 500 KB. CUDA is hidden from the child process.
- `bridge_cpu_smoke`: invokes only `python -m unittest discover -s research_task_bridge/tests`; task text cannot supply a command.
- `requires_user_approval`: records a hold and does not execute.

Requests containing GPU/CUDA, formal training, held-out/test-set use, protocol edits, or research-direction changes are held as `rtb:blocked-approval`, even if submitted as read-only. This is conservative keyword screening, not an automatic scientific-risk classifier. Review and rewrite a held task before resubmitting a safe action. No action in v1 can write repository files or run an experiment.

## Lifecycle and recovery

| Issue state | Meaning |
| --- | --- |
| `rtb:ready` | Queued and authorized for one of the bounded v1 actions |
| `rtb:claimed` | A local worker acquired it |
| `rtb:running` | Codex read-only review or bridge CPU self-check is active |
| `rtb:review` | Summary, local log path, commit, status, and runtime were posted; awaiting researcher review |
| `rtb:blocked-approval` | High-risk or unsupported request; no execution occurred |
| `rtb:failed` | Failure reached the two-attempt cap |
| `rtb:duplicate` | Same normalized action/scope/request is already active or awaiting review |

Every attempt has a remote start comment; results and failures have a separate marker and feedback comment. The normalized task fingerprint is fixed across retries; editing a task after an attempt blocks it and requires a new Issue. A stale claimed/running issue with no result is requeued after 30 minutes, up to two attempts. If a process stops after execution but before feedback is posted, a safe read-only or idempotent self-check may be repeated once. The local OS lock prevents concurrent workers on the same host. Run exactly one configured worker per repository; a multi-host atomic lease is not part of v1.

Local logs are written under `%LOCALAPPDATA%\ResearchTaskBridge\AI4science\` and ignored by Git. Logs and task summaries redact common token/private-key formats; do not put private CIFs, sample metadata, credentials, or confidential findings in public Issues. The bridge does not print or store the `gh` or Codex authentication token.

## Setup and operation

See [the module README](../research_task_bridge/README.md) for prerequisites, issue creation, the `doctor` and `init-labels` commands, and the `once`/`watch` worker commands. ChatGPT requires a GitHub connection with Issues write permission. The local worker requires an authenticated `gh` CLI able to read/write Issues and a signed-in Codex CLI. An optional Windows Task Scheduler entry can launch `watch` at user logon; v1 does not create a background service.

## Implemented and future scope

Implemented: issue-form and CLI task creation, low-risk task polling/claiming, local lock, filtered Codex read-only context, fixed CPU self-check, deduplication, bounded retries, stale recovery, issue state tracking, and feedback. Unit tests and GitHub Actions cover the bridge only.

Future: automatic ChatGPT analysis, OpenAI API calls, multi-host leases, arbitrary commands, AutoLab scheduling, GPU jobs, approval-based scientific execution, and unattended research decisions. All scientific conclusions remain subject to human review and the existing evidence workflow.
