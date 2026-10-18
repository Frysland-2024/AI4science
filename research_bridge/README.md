# Research Task Bridge · Phase 2

**Status: code in development branch; 7 offline test cases supplied; Windows end-to-end login/online tests not yet verified.**

A lightweight **ChatGPT → GitHub Issue → Codex CLI signed in with ChatGPT → Issue report → ChatGPT** task transfer system. No OpenAI API key or separate API bill is needed for this supported Codex CLI path; actual Codex usage is subject to your ChatGPT plan allowance and any applicable credits. This is an engineering layer for the proposed [PXRD AutoLab plan](../docs/PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md), not a completed autonomous research project.

## Capabilities and boundaries

- ChatGPT uses the already-connected GitHub connector to create a task Issue.
- Local worker accepts only Issues authored by **Frysland-2024**, starting with **[Bridge]**, with BOTH **bridge-ready** and **bridge-readonly-approved** labels.
- Codex runs non-interactively in **read-only sandbox** on a temporary Git snapshot, not on your normal working directory. Untracked checkpoints, raw experimental records and credentials are intentionally excluded.
- Codex produces a **draft**; worker posts it as an Issue comment with the source commit and marks **bridge-review**.
- Failure is marked **bridge-failed**; local no-retry journal is stored under .git/research_bridge.
- No auto-code-edits, GPU execution, training, test-set changes, auto-merge, or unsupervised scientific decisions. Those will require a separate human-approved workflow.

## Windows first-run (after PR is reviewed/merged)

Install current [GitHub CLI](https://cli.github.com/), [Codex CLI](https://developers.openai.com/codex/cli), Git, and Python 3.11+. On your PC open PowerShell:

~~~powershell
codex login           # Choose Sign in with ChatGPT; NOT API key
gh auth login
cd E:\AI4science
git switch main
git pull --ff-only
python -m unittest discover -s research_bridge/tests -v
python -m research_bridge.worker --doctor
python -m research_bridge.worker --setup-labels
~~~

Run a dry test, which **will not consume Codex model allowance**:

~~~powershell
python -m research_bridge.worker --once --dry-run
~~~

Once you have created an approved GitHub Issue, run a real task:

~~~powershell
python -m research_bridge.worker --once
~~~

To check every five minutes while your computer and process stay online (alternative to Windows Task Scheduler):

~~~powershell
python -m research_bridge.worker --watch --interval-seconds 300
~~~

Or, after successfully running doctor, dry-run, and a supervised real task, opt in to Windows Task Scheduler. It executes one check every five minutes and writes a local log:

~~~powershell
powershell -ExecutionPolicy Bypass -File .\research_bridge\register_windows_task.ps1
~~~

Inspect scheduled execution and the latest local log:

~~~powershell
Get-ScheduledTask -TaskName AI4science-Codex-Bridge
Get-Content .git\research_bridge\scheduled.log -Tail 30
~~~

Remove scheduled execution:

~~~powershell
Unregister-ScheduledTask -TaskName AI4science-Codex-Bridge -Confirm:$false
~~~

## The first task template

Create an Issue as the repo owner:

**Title:** [Bridge] Review the AutoLab design for missing evidence

**Body:** Read docs/PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md and docs/CURRENT_STATE.md and AGENTS.md. List which parts are proposals rather than working software. Report evidence paths, limitations and recommended review questions only. Do not edit files, change protocols or start experiments.

Add both labels **bridge-ready** and **bridge-readonly-approved** only after you approve that exact issue. The worker cannot process anything without them. Do not put credentials or unpublished spectra in the public Issue.

## Troubleshooting and security

- **This phase is not an always-on ChatGPT conversation.** It automates the Codex side; ChatGPT analysis is still invoked by you unless a separate triggered analysis service is installed later.
- The worker fetches the latest remote `main` Git objects and analyzes a commit-specific `git archive` snapshot. It never checks out, overwrites, or resets local files; untracked research work stays untouched. It requires network access for GitHub and Codex. Do not run two workers on different PCs.
- The scheduled runner logs timestamps, success/failure and task status locally under `.git/research_bridge/scheduled.log`; its previous rotated log is `scheduled.previous.log`. Logs are NOT pushed to GitHub.
- Use the *ChatGPT account login* in Codex; the worker deliberately strips OPENAI_API_KEY, CODEX_API_KEY and CODEX_ACCESS_TOKEN so it cannot fall back to separately metered API use.
- Local Windows agent/CLI authentication is **not tested remotely**: Desktop Commander was offline at implementation time.
- After a crash, manually inspect the Issue and journal before clearing labels/journal. No blind automatic retries.
- Issue comments are public. Only request reviews of Git-tracked, publishable information.
- Final scientific assertions and new experiment approvals remain yours, as prescribed by AGENTS.md.
