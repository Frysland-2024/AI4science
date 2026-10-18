# Research Task Bridge · Read-only + approved coding (2026-10-18)

**Status:** GitHub Issues → locally authenticated Codex CLI → GitHub review has completed a real read-only test (#15). The coding lane is new and must still pass a separately approved live test. The GPU bridge lane now supports approved presets and automatic result branches; scientific A/B remains blocked until its real gates and reviewed backend exist.

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

## Approved GPU lane and automatic result publication

The GPU lane accepts owner-created `[Bridge GPU] ...` Issues with **both** `bridge-ready` and `bridge-gpu-approved`. The JSON body has exactly these fields; `max_minutes`, executable paths, commands, and extra fields are rejected:

```json
{
  "preset": "forward_ab",
  "approved_sha": "40-character-main-commit-sha",
  "config": "pxrd_autolab/configs/forward_ab_pilot.json",
  "config_sha256": "64-character-SHA256-of-config",
  "run_id": "unique_run_001"
}
```

Only these source-controlled presets and exact config paths are dispatched:

- `forward_ab` → `pxrd_autolab/run.py` and `configs/forward_ab_pilot.json`
- `forward_speed_benchmark` → `pxrd_autolab/benchmark_gpu.py` and `configs/forward_speed_benchmark.json`

The worker fetches `main`, requires an exact approved commit and config SHA256, snapshots only tracked source from that commit, and starts the fixed script with a local administrator-selected Python (`AI4SCIENCE_GPU_PYTHON`, the documented local venv default, or the bridge interpreter). An Issue cannot choose the interpreter or pass shell arguments. GPU stdout/stderr stream to local files; the worker writes periodic heartbeats. There is no bridge subprocess wall-clock timeout. To cancel a run, create `.git/research_bridge/gpu_runs/<run_id>/STOP`; the worker checks it periodically and terminates the process tree. Task Scheduler also has no fixed execution limit when registered with the current script.

Every completed, blocked, stopped, or failed run attempts to publish a small public bundle to `bridge-results/<run_id>`, based on the approved source commit, then open a **Draft PR** to `main`. The allowlist is `run_manifest.json`, `gate_report.json`, `metrics.json`, `TECHNICAL_REPORT.md`, and optional bounded `test_summary.json`. Symlinks, non-text files, files over 256 KiB, bundles over 768 KiB, and unlisted outputs are rejected. Local logs, checkpoints, raw spectra, sample arrays, private data, absolute local paths, and credential-like strings are not published. Publication errors are written to the local run journal and surfaced on the Issue; the worker does not report publication success when a push fails. Draft PRs are never auto-merged, and publication is not scientific certification.

The current `forward_ab` entrypoint is intentionally **blocked**: this source tree has no validated measurement-aware gate suite or reviewed A/B training backend. It refuses training until approved-source tests establish BaTiO₃/reference provenance, independent full-spectrum parity, expected measurement-profile behavior, autograd/finite-difference agreement, q–eta identifiability, non-oracle nuisance handling, and split/leakage safety. A JSON status flag from an Issue is never accepted as gate evidence. Old clean-reference prototypes are not used. The approved config preserves a 7,200-second scientific pilot budget, separate from the bridge's unlimited software runtime; when the backend is eventually reviewed, it must enforce the experiment budget itself.

`forward_speed_benchmark` performs actual CUDA float32 matrix multiplication and reports device, VRAM, and throughput. It does not train a scientific model. If CUDA or PyTorch is unavailable or free VRAM is below the preset threshold, it publishes a blocked result instead of substituting a CPU number.

No approval label is added automatically. See [Windows setup](WINDOWS_SETUP.md) for the scheduler re-registration step. CPU-only bridge tests: `python -m unittest discover -s research_bridge/tests -v`.
