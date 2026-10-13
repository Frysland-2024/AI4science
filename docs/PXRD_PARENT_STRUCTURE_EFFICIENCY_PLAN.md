# Parent-Structure Sample Efficiency — supplementary experiment plan

**Recorded:** 2026-10-13  
**Status:** PROPOSED / READY FOR CODEX IMPLEMENTATION; NO NEW EXPERIMENTAL RESULT  
**Owner of next execution:** CODEX LUNA (user-directed execution)  
**Scope:** an independent **supplementary** investigation, not a reopening of frozen V9 main results or the archived factorization branch.

## 1. Recovered historical design and scientific rationale

Prior research planning proposed a **parent-structure efficiency curve** with four nested Train budgets: `10% / 25% / 50% / 100%`. The unit of scarcity is **unique parent crystal structure**, **not** the number of on-the-fly synthetic views. The aim is to test whether using same-parent provenance as relationship supervision extracts more training value from the **same finite structure database**.

- Baseline: matched two-view **Dynamic ERM**.
- Method: **Dynamic JS**, fixed `lambda_js = 60`.
- Backbone: **ResNet-18-GN**.
- Fixed source data: existing 14,060 structures with 9,842 Train / 2,109 Validation / 2,109 simulated Test, split at parent level.
- Key comparison: at the **same independent parent budget**, **same two views**, **same optimizer-step / generated-view budget**, is the JS model better?
- Distinguish from RRUFF-301 K-shot experiments: RRUFF studies **real-label adaptation efficiency**; this experiment studies **simulated independent-parent efficiency**.

This is a follow-up test of the existing **supervision-efficiency hypothesis**, **not** a new algorithm or proof in advance of data savings.

## 2. Experiment matrix (precommit before training)

| Train budget | Planned unique parents | Dynamic ERM | Dynamic JS (`lambda=60`) |
|---|---:|---|---|
| 10% | 984 | run | run |
| 25% | 2,460 | run | run |
| 50% | 4,921 | run | run |
| 100% | 9,842 | run | run |

Use the original formal training seeds `20260711..20260715` in matched pairs. Desired complete matrix = **4 budgets × 2 objectives × 5 seeds = 40 new runs**, if affordable. A resource-gated first installment can run the first seed across all 8 cells and then progressively add fixed remaining seeds **without selecting cells based on favorable results**. Preserve any negative results.

Parent subsets must be fixed once, **stratified by the seven crystal-system labels**, **nested within each other**, and selected without inspecting Validation/Test performance. Use one separately specified, deterministic parent-subset selection seed (suggested: `20261013`, not a training seed). Within each class, sort parent IDs using a stable SHA-256 rank keyed by this selection seed and construct nested prefixes; document exact rounding and per-class counts. Confirm material IDs and parent fingerprints do not create accidental duplicate physical parents.

Exact totals should be `984 / 2460 / 4921 / 9842`, with 100% identical to existing Train parents. Do **not** regenerate train/val/test split. Keep all 2,109 Validation and all 2,109 Test parents unchanged across budgets.

## 3. Fairness and frozen scientific choices

- Freeze the scientific ingredients against `xrd_robustness/configs/experiment.public.json`, `data.method_transfer.structure_split.json`, and `simulation.method_transfer.frozen.json`: architecture, input normalization, five physical perturbation operators, train profile, `lambda_js=60`, optimizer family, batch size, LR policy, seed identities, simulation grid, and evaluation definition.
- **Before runs**, CODEX must determine from local original provenance/selected checkpoints/run records the actual final training budget (global steps, batch size, LR, scheduler/checkpoint rule). The public runner's `--epochs=100 --learning-rate=1e-4 --batch-size=16` are defaults, **not proof they match the actual historical five-seed runs**. If provenance is missing, document it and freeze a new common supplementary budget; do not falsely describe a new 100% run as reproducing V9.
- Primary fairness condition: fixed **optimizer steps**, **complete batches of equal size**, **two generated views per parent occurrence**, and the same total parent-occurrences / views across budget cells. Epoch counts naturally differ as subset sizes differ. With 10% parents, repeat parents over more cycles; that is the intended parent-scarcity condition.
- Within each (budget, seed), ERM and JS MUST see **identical ordered parent IDs** and the **identical two simulated views at every step**. Record and test deterministic sample/view hashes (at least smoke and representative replay checks).
- No change in CE/JS definitions, `lambda_js`, backbone, input processing, original split, or frozen main-run configs; no extra loss, residual branch, new augmentation or domain adaptation.
- If original 100% matched runs cannot be proven identical on all relevant training/evaluation contracts, **rerun the 100% ERM–JS controls under the same supplementary protocol**. Historical `0.65074→0.70534` remains a cited context result, not a plug-in anchor for a mismatched learning curve.

## 4. Required CODEX implementation checks

**Existing public runner:** `xrd_robustness/src/xrd_robustness/training/runner.py`

- Uses a record JSONL `--records` containing `material_id`, `split`, `peak_table_path`, label or crystal system. It permits train/validation, not test. The raw 14,060 structure dataset / cached NPZ peak tables / training checkpoints are **not publicly committed**.
- Has `--max-steps`, but its `train_epoch()` reshuffles each epoch, includes a **possibly short final batch**, and validates/saves at **every epoch**. Different parent budgets therefore produce different number of partial batches and different checkpoint/validation density unless managed. For 10% repeated parent cycling, naive very-high-`--epochs` wastes considerable time on validation.
- Implement a minimally invasive **separate supplementary fixed-step runner** or optional new CLI mode reusing model, **the restored multiprocessing prefetch acceleration**, data rendering, objectives, AMP/fused optimizer settings where hardware-compatible, and checkpoint code. Do not break/change default `xrd-train` behavior used by the published contract.
- Implement full-size batch accounting (no short steps), a deterministic cyclic/shuffled parent sampler, **global-step-based validation/checkpoint intervals**, and exact expected step & exposure counters. If desired use a scheduled last evaluation at the same global step across budgets. Checkpoint choice must follow one predeclared Validation rule identical for ERM/JS and all budgets.
- Safely build per-budget *derived* JSONL manifests using original Train records + full original Validation records; correctly resolve relative peak-table paths when writing new manifest locations. Do not copy large NPZ files or redefine the official dataset.
- Store immutable manifests and hashed resolved configs separately from source/frozen main files; never overwrite existing reports, main checkpoints or `xrd_robustness/configs/experiment.public.json`.
- Add tests: nested/stratified/duplicate-free subsets; frozen Validation/Test identities; fair ERM/JS batch and view matching; stable subset hashes/replay; equal actual global steps, full batch size, parent occurrence and generated-view counts; no contamination of formal files; resume/failed-run integrity if resumption is implemented.
- The existing `--max-steps` by itself is **not** proof that equal views were seen: require verified actual counters and prohibit partial-batch differences.

## 4A. Critical performance correction — restore historical fast V9 training path

The original 2026-07-28 optimization and 2026-07-29 ten-run launcher are available in Git history. **Do not estimate or implement the new study as 40 runs of the stripped-down public `training/runner.py` without first recovering the accelerated execution path.** CODEX LUNA should inspect the historical Git revision and current restored prefetch code first.

**Evidence from Git history:**

- Commit `e553286332` (2026-07-28): trained online views were accelerated by caching **structure-invariant** HKL ordering, preferred-orientation candidate/index maps and clean quality-reference spectra, while never caching dynamic spectra, random draws or sampled measurement conditions. The audited 16-worker × 16-prefetch, 64-batch benchmark improved from **24.5265 → 31.3120 batches/s (+27.67%)**, and sequential from **3.6794 → 5.4267 batches/s (+47.49%)**; exact output arrays and view identities remained unchanged (max difference 0).
- The old registered hardware profile, `configs/hardware.v9.laptop.7945hx_4060.json` at historical commit `c1ae176963`, specified **BF16 autocast/AMP, fused AdamW, TF32, cuDNN benchmark, pinned memory, non-blocking CPU→GPU transfer, explicit CPU thread caps, serial model runs**, and disabled `torch.compile` because the probe found no working Triton setup. Hardware benchmark machine: Ryzen 9 7945HX + RTX 4060 Laptop GPU.
- The historical Linux ten-run launcher `scripts/run_v9_resnet_js_ten_run.sh` (commit `c1ae176963`) used the optimized `train_cnn_contract_diagnostic.py` with `--dynamic-prefetch-workers`, `--dynamic-prefetch-batches`, the above GPU flags, and **8 worker / 8 prefetched batch defaults** unless overridden in that runtime's environment. Therefore the 16/16 benchmark must **not** be mislabeled as proof of ten-run runtime worker count.
- The ten-run V9 validation summary recorded **ten completed ERM–JS runs** with 100-epoch / 61,600-step **ceiling** and several early-stopped runs. The public summary does **not** contain the full wall-time; the project owner recalls **about eight hours** for the prior training effort. Treat this as a useful **user-reported runtime anchor**, not independently verified timing telemetry.
- On 2026-09-13 the current repository restored the deterministic optimized online-rendering machinery as `src/xrd_robustness/training_prefetch.py`; `scripts/run_pairing_ablation.py` demonstrates its integration, persistent workers, worker-local lazy reflection cache and in-order reassembly. That script's **same-class ablation loss is not the new experiment's loss**; reuse only its execution plumbing.

**CODEX action:** Review historical launcher, hardware configuration, archived optimization report and current `training_prefetch.py` / `run_pairing_ablation.py`. Adapt/reuse fast prefetch + GPU settings for the supplementary fixed-step experiment, retaining original **Dynamic ERM and same-parent Dynamic JS objectives**, exact view stream, full-batch equal exposure, and matched global-step budget. Do not copy the same-class pairing ablation as a scientific comparator.

**Runtime planning:** Before any GPU run, compute expected duration from the **actual measured end-to-end time per step** plus regular Validation, loading and save overhead on the target machine. As a sanity check only, if prior **ten-run training took ~8 hours on genuinely comparable hardware and protocol**, a four-times-larger **40-run** grid has order-of-magnitude **~32 GPU-hours**, potentially less if compatible 100% controls can be rigorously reused or the design/protocol legitimately changes. This is a *conditional proportional estimate*, not a new benchmark and not a reason to silently reduce scientific training steps. Report fresh numbers rather than repeating generic 0.2–1.0 s/step guesses.

## 5. Staged execution for CODEX

### Gate A — read-only preflight
1. Read `AGENTS.md`, `docs/CURRENT_STATE.md`, this plan, `docs/PXRD_SUPERVISION_FRAMING.md`, `xrd_robustness/reports/RESULTS.md` and the three configs above; inspect the relevant trainer and evaluator.
2. Confirm local data/peak caches/manifests and the original V9 run provenance. If only a fresh Git clone is available, clearly report `BLOCKED_DATA` and do **not** pretend any training ran.
3. Freeze the new supplementary protocol **before seeing new experimental scores**, including training steps, validation cadence, score selection, evaluation seeds, subset-seed, exact output paths and hardware/cost cap.

### Gate B — implementation and smoke
1. Implement deterministic nested subsets, new fixed-step runner/launcher and new analysis output, under distinct `xrd_robustness/scripts/` + `xrd_robustness/tests/` paths.
2. Run targeted unit tests and pre-existing non-data-bound tests.
3. With a tiny synthetic fixture, run both objectives for equal 2–5 optimizer steps; prove batch IDs + rendered views are identical and no incomplete batches/exposure mismatch. This fixture is **not scientific evidence**.
4. Produce a concise preflight report with statuses `PASS`, `BLOCKED_DATA`, or `BLOCKED_PROVENANCE`.

### Gate C — fixed scientific matrix
1. When data, GPU and a reasonable existing-compute budget are available, run the **precommitted 8 method–budget cells for training seed 20260711** under matched sampling.
2. Complete seeds `20260712..20260715` for all cells if resources allow. If interrupted, clearly report the partial fixed matrix, not a selected favorable subset. Do not purchase GPU/cloud resources without user authorization.
3. Keep logs/checkpoints/full per-example predictions outside tracked source; record code SHA, configuration SHA, manifest SHA, seed, GPU, optimizer steps, generated views, validation selection policy, and wall-time.
4. **Primary analysis:** frozen simulated **single-factor OOD Macro-F1**, averaged across the six named OOD profiles using the same evaluation convention for all new runs; **secondary:** in-range Macro-F1, level0, accuracy, per-class F1, six profile metrics.
5. Use **Validation-only** to diagnose implementation/checkpoint behavior; once run selection rules and schedule are fixed, evaluate all cells uniformly on the **unchanged simulated Test**. The old Test has **already been used in the main study**; this is therefore a **clearly labeled supplementary/post-main follow-up analysis**, not a newly untouched confirmatory holdout.
6. Keep RRUFF-301 and CNRS-318 **out of the main parent-budget experiment**. Optional CNRS zero-shot extension should be a separately scoped, later, fixed-protocol replication, not required to finish the curve.

## 6. Figures, metrics and interpretation

Primary display:

1. **Learning curve:** x = unique Train parents (984, 2460, 4921, 9842), y = frozen simulated single-factor OOD Macro-F1, ERM vs JS, point = mean over training seeds, uncertainty shown transparently.
2. **Matched Δ by budget:** `F1_JS(N) − F1_ERM(N)` with paired-seed results.
3. **Optional data-efficiency equivalence:** estimate `N_JS(F*)` and `N_ERM(F*)` **only if the target \(F*\) is bracketed by measured budget points**. Do not extrapolate or claim numerical savings by reading off an unbracketed or non-monotonic curve.
4. Optional normalized area under the measured learning curve (AULC), marked as supporting summary, not replacement for data points.

Possible conclusions:
- JS beats ERM at matched `N`: stronger performance **at the same parent budget**.
- JS reaches an ERM target with fewer measured/interpolated parents: evidence for **parent-structure data efficiency**.
- JS only shifts the whole curve upward without any reliably measurable equivalent-budget reduction: performance gain across budgets, **not** proven data savings.
- Advantage shrinks, flips, or is unstable at low budget: preserve it and discuss limits of provenance-based supervision.

Avoid `database speed`, `training converges faster`, `requires fewer labels`, or `can halve the database` unless the **appropriate** directly measured evidence exists. In particular, RRUFF label efficiency and simulated parent-budget efficiency are distinct.

## 7. Deliverables

- `xrd_robustness/configs/parent_budget_efficiency.v1.json` — **new** proposal-frozen supplementary config, no changes to original frozen configs.
- `xrd_robustness/manifests/parent_budget_efficiency/` — immutable parent lists / SHA-256 summaries (no licensed/raw spectra).
- `xrd_robustness/scripts/` — subset generator, fixed-step launcher, evaluator/aggregator/plotter.
- `xrd_robustness/tests/` — deterministic, fairness, integrity and smoke tests.
- `xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md` — preflight, actual run grid, constraints, accurate comparison/limitations and figures; at first create `NOT_RUN` report rather than placeholders disguised as results.
- Figures/CSV/JSON summaries under a **new clearly scoped location**; large checkpoints and arrays remain untracked.

**Definition of done:** implementation and smoke tests first; scientific completion requires all planned cells or an explicit incomplete report, matching exposure verification, unaltered frozen assets, auditable figures/metrics, and an interpretation that distinguishes performance gain from measured structure savings.

## 8. Historical/evidence provenance

- Original scope and nested 10/25/50/100% budget, same-step/same-view design, and possible learning-curve left-shift were discussed in the project conversation (July 2026 idea; reconsidered September 2026). This document records that plan in the current public repository; it is **not a claim that these runs were already executed**.
- Current framing: [PXRD_SUPERVISION_FRAMING.md](PXRD_SUPERVISION_FRAMING.md).
- Current main results: [../xrd_robustness/reports/RESULTS.md](../xrd_robustness/reports/RESULTS.md).
- Code and training-contract starting points: `../xrd_robustness/src/xrd_robustness/training/runner.py`, `../xrd_robustness/configs/experiment.public.json`.
