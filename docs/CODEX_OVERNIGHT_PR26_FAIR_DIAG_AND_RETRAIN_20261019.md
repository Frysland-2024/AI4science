# Codex overnight research task — PR #26 fair diagnosis → root cause → one new paired training round

**Date:** 2026-10-19 (Asia/Shanghai). **Status:** USER-AUTHORIZED / not yet executed by creation of this file.
**User's explicit instruction:** work independently tonight; tomorrow provide results, including failures. Full autonomy for bounded project work, **NOT permission to edit frozen V9, fabricate results, delete evidence, leak unpublished samples, or auto-merge**.

## 0. First read and scope

Read `AGENTS.md`, `docs/CURRENT_STATE.md`, `docs/PROJECT_HISTORY.md`, then PR #26's `xrd_forward_loss/measurement_closure/TECHNICAL_REPORT.md`, `formal/ab_results.json`, `formal/validation_lambda_selection.json`, `formal/split_indices.json`, `run_issue19_p3.py`, and `src/pxrd_forward_loss/measurement_closure.py`. Also inspect PR #21's `measurement_closure/run_ab.py` as a historical *different protocol*, not as comparable replication. PR #26 head: `e261faadbc2fba88b2f2289e7900d237a733345a`; base PR #17; do not merge any old PR.

Work **only on a new isolated branch/worktree** derived from the above PR #26 exact head, e.g. `codex/issue31-pr26-fair-diagnostic`, in a **new distinct output directory** `xrd_forward_loss/measurement_closure/results/overnight_pr26_20261019/`. Never modify/delete the original PR #26 formal results, original 12 compact inference checkpoints, logs, PR #21, V9 frozen results, other Codex worktrees or local `main`. Keep local weights private/untracked. Missing dependencies/checkpoints should produce `BLOCKED` with evidence, not invented metrics.

This document controls only *this specific finite experiment*. **Never automatically run indefinitely**, never use hyperparameter/test cherry-picking. Do not interpret one-CIF simulated conditional parameter interpolation as a real XRD or Rietveld success.

## 1. P0: Independent audit of existing PR #26

- Verify 12 compact PR #26 checkpoints by existence, SHA or manifest, architecture fit, loader and inference on GPU; check original `formal_data.npz` + `split_indices.json` hashes and matching seed/parameterization. Recompute at least q-MAE per seed to match `formal/ab_results.json` within floating point tolerance.
- Confirm P0/P1 physics gates, code/data provenance, no oracle eta, q/eta parameter physical ranges, transformation/normalization and target matching. Identify what changed from PR #21 (supervised synthetic eta labels, five nuisance outputs, deterministic clean target versus PR #26's three predicted nuisance dimensions and observed expectation).
- Record all actual confounding variables: B vs A head count (+771), validation-selected lambda, unequal cost in previously reported profile RMSE; B cannot be called superior by profile RMSE of A with extra fit.
- Run pytest/physical gates in installed project virtualenv, do not lower any thresholds.

## 2. P1: FAIR EVALUATION WITHOUT NEW TRAINING (mandatory before any retraining)

Same PR #26 12 frozen networks, same held-out test samples and nuisance-free physical q extraction; eval over simple and V9, three paired seeds.

For each A and B produce **three distinct and explicitly labeled metric tracks**, identical rules and constraints for A and B:

1. **Direct one-pass q inference**: q-MAE, a/c Å MAE, per-seed runtime (no refinement).
2. **Fixed q, bounded eta-only profile fit**: initialize eta *from the same neutral value* for A and B, and use *the same optimizer, nuisance search bounds, tolerance, stopping budget, profile objective, preprocessing and initializations*. For B optionally report the head-predicted eta as a *separate* faster inference path, never silently favor B. Compare observed transformed-profile RMSE and nuisance error (eta_true only post-hoc scoring). q stays frozen.
3. **Matched q+eta local refinement**: initialize q from each model's prediction and eta from the same neutral prior; use identical bounded optimization (no q_true/eta_true), max iterations and gradient/step budget; report final q/a/c MAE, final RMSE, solver success, iteration/time to reach predeclared objective tolerance and failure/outlier rates. Include **physics-only prior/neutral start** comparison if finite-budget possible; don't call this real Rietveld.

Use full 77 tests/condition/seed where feasible; if computationally heavy, **freeze the exact same deterministic subset of >=24 indices per condition for A/B/3 seeds before inspection**, report scope and runtime. Fail closed if test arrays, prediction files and checkpoint scoring disagree. Use original already-open PR #26 test only as **post-hoc diagnostic**—not an unseen validation set for choosing new loss/architecture.

Save paired per-sample CSV/JSON, summary with uncertainty across three seeds, worst 5 q/eta cases (public synthetic data only), numerical gate status, time and compute fairness audit. Crucial: separate eta-head *capacity*, *gradient interference*, *nuisance identifiability*, *physics mismatch* and *data preprocessing* as candidate mechanisms. Diagnostic evidence is not proof of causal mechanism.

## 3. P2: CAUSE HYPOTHESES & PRE-REGISTERED NEW EXPERIMENT

Before new training starts, write `PRETRAIN_CAUSE_AUDIT.md` and a machine-readable frozen config/hash to the new output directory. At minimum evaluate with held-out **validation only** (not PR #26 test):
- q and eta predictions correlation, q vs nuisance compensation, especially zero-shift;
- `grad_q(L_param)` versus `grad_q(L_recon)`: norm, cosine and instability across a *validation* mini-batch; note shared-trunk gradient effects and head dimension;
- observed vs clean profile target, normalization, nuisance map saturation, lambda scaling;
- matched model head/compute fairness.

Select **one** justified small change based on the diagnostic evidence. Preferred candidate when gradients conflict: controlled stop-gradient/separate nuisance optimization that prevents nuisance-profile reconstruction from dominating the q-head/shared features (e.g. detached q only in profile auxiliary path or a documented staged/frozen head), **without using oracle eta at test**. Alternative of new nuisance parameterization or validated weight is permitted only with documented reason and predeclared validation selection. Do not invent many competing methods and select the best based on old test.

## 4. P3: Gate PASS → immediately execute ONE bounded new paired training experiment, no extra user approval

**Training is authorized after P0–P2 required checks pass and protocol is frozen.**

- Material one public BaTiO3 P4mm CIF COD 9014273; no external real spectrum, no general structure inference.
- **Fresh independent synthetic q+noise dataset** with fresh explicit Sobol/perturbation seeds, split strictly by parameter draw before adding repeated noise. Save `q_true`, clean expected profile, observed profile, nuisance generation metadata, original record identity, split indices and SHA hashes. Fresh test is frozen and only evaluated **once** after candidate and lambda selected using validation. Mention this is still same structure, not new compositions.
- Fixed conditions simple and V9 four perturbations (zero-shift, width, background and Poisson-Gaussian noise; March–Dollase off); preserve physical profile parity and gradient gates.
- Paired **A (supervised q-only)**, **B (PR #26 reconstruction protocol)**, **C (one pre-registered P2 change)**, using same backbone, paired seeds, splits and budget as far as architecture differences allow. Max **512 parent q draws**, **3 paired seeds**, **24 epochs per method/condition/seed**, per-method best epoch selected on validation q-MAE only; reduce to 2 conditions + A/B/C × 2 paired seeds if runtime pressure but **do not reduce below 2 paired seeds if claiming even exploratory comparative value**. Clearly mark any unequal head size/labels/training optimization and include wall time.
- B lambda and optional C regularization selected only among at most **two pre-registered candidates** by validation, test evaluated once; no old PR #26 test-based model/weight tuning. Training + selection max **2 hours of measured GPU runtime** for this new round; stop and label PARTIAL if exceeds, preserve complete logs. No silent runaway.
- Preserve negative/mixed results: q parameter MAE ±SD and *paired* differences by seed and condition, a/c MAE, zero-shift/width/background errors, observed-profile RMSE with equal evaluation compute paths, direct vs refined q, success, p95 runtime. Do not generalize to real data, new CIFs, or refined crystal phases.

If P2 diagnoses irreparable violated physical gates, model checkpoint provenance mismatch or unavailable computing → **do not run** and report `BLOCKED` with exact reasons. If diagnostic proves baseline q error is already at a numerical floor, discuss scientific STOP/NO-GO rather than tuning endlessly.

## 5. Finishing / communication / handoff (MANDATORY)

- Create `xrd_forward_loss/measurement_closure/overnight_pr26/TECHNICAL_REPORT.md`, with: what completed, raw numeric paired table, fair-inference cost table, root-cause evidence vs hypothesis, post-hoc vs new held-out separation, physics gate results, failed attempts/recovery, caveats, next single experiment if needed. Machine-readable `summary.json`, `gate_report.json`, `execution_log.json`, `split_manifest.json`, and plots if verified.
- Ensure independent `pytest`, `git diff --check`, test/metric round trip, no large binary checkpoint in Git; record final SHA/hash and local best checkpoint paths.
- **Commit/push only this isolated branch** and create a **Draft PR** based on `codex/issue19-measurement-closure`, not main; do not merge old PRs or this one.
- Status notifications: GitHub Issue corresponding to this task must be commented at **STARTED, P0_VERIFIED, P1_DIAG_COMPLETED, TRAINING_STARTED, TRAINING_COMPLETED / BLOCKED / FAILED, PR_CREATED** with brief evidence and links when connectivity allows; no secrets/public raw unpublished data. Keep a local append-only execution status/log so errors are visible even if GitHub fails.
- Do not claim success before the final tests and PR exist. Note if user PC sleeps/offline, local task pauses; do not make unsupported promises of guaranteed morning completion. Stop gracefully on preflight failure.

**Output priority**: Fair diagnostic and root cause proof (must finish and publish) > controlled paired retraining > extra visualization. The user expects *actual executed work*, not only a prompt.
