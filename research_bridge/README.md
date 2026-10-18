# Research Task Bridge · Read-only + approved coding (2026-10-18)

**Status:** GitHub Issues → locally authenticated Codex CLI → GitHub review has completed a real read-only test (#15). The coding lane is new and must still pass a separately approved live test; no GPU experiments are enabled.

## Two separate, explicitly authorized lanes

**Read-only review**: Repo owner writes an Issue starting with `[Bridge] `, labels `bridge-ready` and `bridge-readonly-approved`. The local task worker fetches the latest GitHub main, exports that exact revision to a disposable directory, calls `codex exec --sandbox read-only`, and puts the review as an Issue comment. No API key is required; Codex plan allowances apply.

**Code development (PR only)**: Repo owner writes an Issue starting `[Bridge Code] `, in **exact JSON**:

```json
{
  "task": "Create a short Markdown example explaining the approved bridge workflow. Do not edit experiments.",
  "allowed_paths": ["docs/bridge_proposals/example.md"],
  "test_profile": "syntax"
}
```

After inspecting the task, add `bridge-ready` and `bridge-code-approved`. This grants one bounded development run on an **isolated temporary clone** using Codex CLI workspace-write sandbox. A machine-enforced scope check blocks changes outside the exact approved paths. If it passes, the worker pushes `bridge/issue-N` and opens a **DRAFT PR**. No auto-merge. Code generation must not access local ignored data, GPU training or frozen V9 tests.

Allowed coding areas currently: `research_bridge/tests/`, `pxrd_autolab/`, `xrd_pre_refinement/`, `xrd_inversion/`, `docs/bridge_proposals/`. Protected: `xrd_robustness/`, `.github/`, `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/PROJECT_HISTORY.md`, the two bridge execution scripts. Requests outside approved areas are ignored/blocked. Other modifications are rejected after generation. An issue can opt into `test_profile: syntax` (Python AST syntax check only, no code execution) or `none`. This is **not** approval to execute arbitrary shell commands.

## Latest-main synchronization bug fixed

Previously `worker.revision()` refused to run when the local checkout HEAD was behind GitHub main. Now it does **`git fetch --no-tags origin main`** and exports an immutable snapshot of `FETCH_HEAD`. The user's checkout remains unmodified: no `git pull`, no branch switch, no reset, no `git clean`. The untracked local `xrd_pre_refinement/` folder remains untouched.

This solves *research task source freshness*, **not automatic self-updating of the worker Python files**. Updating the bridge's own code after a merged PR still requires a deliberate fast-forward pull after checking local changes.

## Setup / verification (Windows PowerShell)

```powershell
cd E:\AI4science
git status --short
git pull --ff-only
codex login status
gh auth status
python -m unittest discover -s research_bridge/tests -v
python -m research_bridge.worker --doctor
python -m research_bridge.worker --setup-labels
python -m research_bridge.worker --once --dry-run
```

After approving an Issue, the task scheduler can run `python -m research_bridge.worker --once` on a cadence. Repetition will never automatically reprocess an Issue that already has a local journal record or the `bridge-review`/`bridge-failed` label.

Use `research_bridge/register_windows_task.ps1` to register 30-minute checks *after* one supervised successful run. The timer does nothing if no approved task is pending; Codex is NOT invoked on idle checks. A shutdown pauses this local automation; a scheduled task cannot run while the computer is off.

Logs/status:
- Read/Code tasks are reported back to the originating Issue.
- `E:\AI4science\.git\research_bridge\issue-N.json` contains local attempts.
- `bridge-running`, `bridge-review`, `bridge-failed` indicate state.
- **Do not clear journals or retry after a crash without inspecting the Issue and local records.**

## Important limits

- This is an experimental agent workflow; local read-only and workspace-write sandbox security on Windows must be verified against your installed Codex version.
- Codex may execute tools inside its sandbox. Only the preapproved coding area and post-run checks are implemented; do not grant coding approval for untrusted content.
- GitHub repo/Issues are **public**. Never place tokens, passwords, unpublished raw experimental data or private sample metadata in tasks.
- Worker's CI unit tests and Python syntax checks do not prove produced scientific code is correct.
- No automatic GPU jobs, scientific A/B experiments, publishing claims, PR merges or changes to frozen protocols. Those require a separately designed and approved execution protocol with compute budget, preflight and experiment logs.
- ChatGPT's separately configured hourly GitHub watch is a status monitor; it is not a two-agent continuous deliberation service.

## Explicitly approved GPU execution and training-speed optimization

The third lane accepts owner-created GitHub Issues titled **[Bridge GPU] ...** carrying **both** `bridge-ready` and `bridge-gpu-approved`. The Issue body must be exactly:

```json
{
  "preset": "forward_ab",
  "approved_sha": "40-character-main-commit-sha",
  "config": "pxrd_autolab/configs/forward_ab_pilot.yaml",
  "config_sha256": "64-character-SHA256-of-config",
  "run_id": "unique_run_001",
  "max_minutes": 45
}
```

The GPU task dispatches **only** a hard-coded reviewed preset:
- `forward_ab` uses `pxrd_autolab/run.py`
- `forward_speed_benchmark` uses `pxrd_autolab/benchmark_gpu.py`

**These preset scripts are not yet in main**, so any GPU Issue remains blocked until a separately reviewed coding PR implements the runner and configuration. This distinction is intentional: user-level permission is granted, but no scientifically justified formal experiment has yet been selected.

Pre-run checks require current GitHub `main` to match `approved_sha`, an exact config SHA256, a permitted path, a fresh run ID, and a bounded `max_minutes` between 1 and 120. Results stay local in `.git/research_bridge/gpu_runs/<run_id>/`, with a manifest that explicitly says `metrics_verified=false`. Reports are not proof of scientific efficacy. A nonzero exit stops with failure, and the bridge never retries or changes hyperparameters automatically. Script/arguments cannot be supplied by an Issue.

**Permitted speed optimization:** Codex can implement faster data loading, batching, caching, mixed precision *only with explicit validation of numerical and scientific equivalence*, and benchmark throughput, memory and wall-clock speed. It may propose a draft PR in the approved coding lane. It must not secretly change optimizer, seed, effective batch size, data split, perturbation distribution, number of update steps, checkpoint selection, frozen tests or science claims. The baseline and optimized implementation must be compared under the same protocol.

**Training warning:** Timeout currently bounds the launched parent process; child worker processes and GPU memory consumption are not yet enforced by a hardware-level quota. Windows shutdown, sleep, battery rules and task-scheduler execution limits may interrupt training. Do not approve a long or costly task until the runner has reliable checkpointing, child-process shutdown and hardware preflight. A process exiting successfully does not replace physics/evidence review.

No approval tag is automatically placed on new issues, and the bridge does not auto-merge draft PRs.
