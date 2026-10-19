# User-approved DONUT-PXRD **serial workflow runner** implementation task

**2026-10-19. Scope:** `Frysland-2024/AI4science` isolated worktree `E:\AI4science_donut_serial` on branch `codex/donut-pxrd-serial-pipeline-20261019`. This is a software integration task, **NOT authorization to launch new full training**. Do not edit main, source branch, or any other worktree. Do not merge any PR.

## WHY / race safety

A different unattended Codex is CURRENTLY RUNNING the four-phase DONUT study in `E:\AI4science_donut_pxrd` under `AI4science-DONUT-PXRD-Resume1`, using GPU and writing untracked `donut_pxrd/` files. **Do not edit any file in that active worktree, interrupt it, kill its processes, or consume its GPU for more training.** You may READ its scripts/results as an interface specification. You must implement entirely in the isolated worktree `E:\AI4science_donut_serial` and use a subprocess-based CPU-only mock end-to-end smoke test to show that the runner works. If active experiment eventually finishes and commits, we can integrate later safely; do not cherry-pick or merge into the active worktree while it is busy.

## Exact deliverable

1. Review `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/DONUT_PXRD_FOUR_STAGE_EXECUTION_20261019.md`, prior issue31 evidence, official DONUT training workflow. Inspect (read-only) existing untracked active scripts:
   - `E:\AI4science_donut_pxrd\donut_pxrd\scripts\run_donut_stages.py` flags `--experiment 1|2|3|all`, `--texture-only`;
   - `E:\AI4science_donut_pxrd\donut_pxrd\scripts\run_experiment4.py` uses current experimental input and A/B/C + L-BFGS-B;
   - `E:\AI4science_donut_pxrd\donut_pxrd\scripts\audit_resume.py`, and its five directories `exp1,exp2,exp3a,exp3b,exp3c` and texture OOD;
   - `E:\AI4science_donut_pxrd\donut_pxrd\configs\study_v1.json`, pre-reg hashes.
   These are **read-only interface references**, not to be copied as completed evidence into this branch.
2. Implement `donut_pxrd/pipeline.py` (or `donut_pxrd/scripts/serial_pipeline.py`) as a minimal maintainable **Python stdlib** stage controller with CLI:
   - `--config <path>`, `--repo-root <path>` (explicitly selected), `--mode inspect|smoke|run|resume`, `--output-dir <path>`, `--help`.
   - One declarative JSON config `donut_pxrd/configs/serial_pipeline_v1.json` contains **ordered DAG / sequential** stages: (preflight/source/physics/data), exp1, exp2, exp3a, exp3b, exp3c, texture OOD, exp4, report. A stage is identified by stable ID, script/arguments, input path checks, required output files, *verifier* hooks, timeout, and precedence. Stage commands must be semantically grounded in the inspected real scripts, not hallucinated.
   - Artifacts passed by **file paths** and sha256 manifest; config and upstream input changes invalidate dependent completion; no shell interpolation; subprocess with argument vector, stdout+stderr logged, exit code and duration; atomic state-write; immutable run IDs and log paths; file lock to prohibit duplicate concurrent pipeline; per-stage COMPLETE|FAILED|BLOCKED|NOT_RUN, no bogus COMPLETED on presence of files alone.
   - `inspect` is *strictly read-only* and should make a truthful report of existing experiment outputs on active worktree; show missing required files, do not mutate or run. The existing source worktree may be mid-execution; do not infer failures from partial files.
   - `smoke` should run safe, tiny CPU-only mock subprocess stages and intentionally failing stage, validate order, stop-on-fail, reproducible state and resume skips valid-complete stages. It must **not** run stage real training.
   - `run` must refuse to overwrite existing `run_donut_stages.py` training folders (uses `exist_ok=False`), prevent retransplant of a stage if already scientifically completed and verified, handle recovery after crash. By default require `--execute` explicit confirmation for any real training and provide `--dry-run` preview. The study config's 3 seeds, 512 parents, 30 epoch limit and fixed train/test are immutable for current study. Do not automatically adjust metric thresholds or select hyperparameters on test.
   - `resume` re-verifies existing results/hashes from raw arrays, verified checkpoints, all 3 seeds; skip truly complete stages; do not simply skip when output dir exists. Missing/invalid existing partially generated stages must be marked BLOCKED for manual cleanup/repair, not blindly overwritten. If exp4 needs work, respect concurrent GPU process lock guard.
   - stage reporting must distinguish actual scientific outcome vs command-exit success; there is no report that all 4 experiments are complete until all actual output checks are satisfied; tests have to catch fake output / checkpoint hash.
3. Add `donut_pxrd/tests/test_serial_pipeline.py` with tempfile/unittest or pytest, no GPU. Tests cover stage ordering, validation failure, no test leakage policy, immutable config SHA, interruption/resume skip, stale artifact detection, concurrent lock, path traversal rejection, stage status atomicity and deterministic dry-run. Keep tests fast.
4. Add `donut_pxrd/README_PIPELINE.md` as user-friendly one-page manual with exact commands, outputs and distinctions `inspect` (read-only), `smoke` (CPU mock), `run` (full real GPU user-authorized but only AFTER prior worker ends), `resume`, source upstream links. Explain every stage uses the **same immutable data split**; negative model performance doesn't mean software failure. `run` must require explicit `--execute` and should not be called by this task.
5. Perform CPU-only tests and successful full mock smoke of at least 3 stages and an intentional simulated failure + resume. Then perform `inspect` against `E:\AI4science_donut_pxrd` **read only** with separate log in THIS worktree; summarize actual partial data plainly, no implicit training.
6. Run `git diff --check`, verify clean after commit, push ONLY own branch to GitHub. Create Draft PR base `codex/donut-pxrd-four-stage-20261019` if GitHub authentication succeeds; if CLI returns 401, record it and leave branch pushed. **Do not merge**.
7. Put `donut_pxrd/pipeline_status/BUILD_REPORT.md` with tested commands, actual exit codes, mock tests, real-worktree inspect result and limitations; if any blocker, record accurately. Do not claim 4 science experiments completed.

## Important distinction

The scientific four-stage worker is already active; this new branch builds engineering orchestration, not new science. The final user answer must distinguish **pipeline implementation tests** from actual DONUT training/exp4 completion.
