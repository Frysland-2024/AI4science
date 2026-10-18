# Research Task Bridge

The bridge uses GitHub Issues as a small, auditable hand-off queue between ChatGPT and a local Codex CLI worker. It does not add a service, database, OpenAI API call, or second experiment runner. AutoLab remains the planned research execution pipeline; this module only transports bounded tasks and records their execution feedback.

## Install on Windows

Requirements: Python 3.10+, Git, GitHub CLI (`gh`), and the Codex CLI signed in with the user's existing Codex account. The Python bridge uses only the standard library.

From a clone of this repository:

```powershell
gh auth login
python -m research_task_bridge --repo Frysland-2024/AI4science doctor
python -m research_task_bridge --repo Frysland-2024/AI4science init-labels
```

Run `init-labels` once before using the Issue form: GitHub does not create labels just because they are listed in a form template.

The worker needs GitHub Issues read/write access to list tasks, claim them, update labels, and post feedback. `init-labels` additionally needs permission to create repository labels. ChatGPT needs an authorized GitHub connection with Issues write access to create tasks. No token is put in task files or logs; authentication stays in `gh` and the local Codex CLI.

## Create and run a task

ChatGPT can create an Issue using **New issue → Research task for local Codex**. The form starts the task in `rtb:ready`; the local worker discovers it on its next poll. The CLI can create the same issue:

```powershell
python -m research_task_bridge --repo Frysland-2024/AI4science create `
  --title "Review AutoLab implementation boundary" `
  --action codex_read_only `
  --scope docs `
  --request "Summarize the AutoLab proposal and state which parts are implemented. Do not run code."
```

Run one poll or keep a user-session worker watching:

```powershell
python -m research_task_bridge --repo Frysland-2024/AI4science once
python -m research_task_bridge --repo Frysland-2024/AI4science watch --interval 30
```

`watch` claims at most one task at a time and continues while that process is running. To start it at Windows sign-in, create a Task Scheduler entry that launches the `watch` command as the same user who is signed in to both `gh` and Codex. V1 intentionally does not install a background service or configure Task Scheduler automatically.

## Example task

```text
Action: codex_read_only
Context scope: docs
Request: Summarize the proposed AutoLab execution boundary and distinguish documented plans from implemented code. Cite repository paths. Do not run tests or experiments.
```

`bridge_cpu_smoke` runs only `unittest` in `research_task_bridge/tests`; the Issue text cannot select a command. `requires_user_approval` and requests that mention GPU/formal training, test-set use, scientific protocol edits, or research-direction changes are held without execution. The Codex task runs from a temporary snapshot that excludes tests, data, result reports, manifests, run outputs, and ignored files; the CLI uses `--sandbox read-only` and clears `CUDA_VISIBLE_DEVICES`.

## Status, retries, and recovery

Issue labels record `rtb:ready → rtb:claimed → rtb:running → rtb:review`; failures are commented with the failure reason and retried at most twice. Successful feedback includes a bounded summary, local log path, current Git commit, dirty/clean state, attempt count, and runtime, then moves to `rtb:review` for ChatGPT/researcher review. Duplicate active/review tasks with the same normalized request are marked `rtb:duplicate`; set a new dedupe key only for an intentional rerun. A stale `claimed`/`running` task is recovered after 30 minutes; safe actions are idempotent and a retry remains bounded.

The local OS lock prevents two workers on the same machine from claiming simultaneously. V1 supports one configured worker per repository; multi-host atomic leases are a future extension. Local logs live under `%LOCALAPPDATA%\ResearchTaskBridge\AI4science\` and are ignored by Git.

## Implemented vs future

Implemented: GitHub Issue form/CLI creation, polling, local claim lock, bounded read-only Codex execution, fixed CPU self-check, risk hold, deduplication, retry/recovery, issue status tracking, feedback comments, and CI unit tests.

Future: OpenAI API integration, automatic ChatGPT analysis, multi-host leases, arbitrary command execution, AutoLab experiment scheduling, GPU jobs, approval workflows for formal experiments, and unattended scientific decisions. The task bridge does not change or claim results for any scientific project.
