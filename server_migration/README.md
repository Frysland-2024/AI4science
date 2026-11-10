# AI4science 2026-11-03 — Linux GPU migration + bounded one-command V11 Optuna

> **ACTIVE 2026-11-10 — R-FIRST V11 HPO; LAPTOP GRADIENT WORK CLOSED; AWAIT CUIFA STAGE 0/HPO.** The authoritative Train gradient scale is the FIRST [108,478-parent whole-Train audit](gradient_gate_v11_train_108478.json), with A0 r=0.0681726422271 (6,780 batches, fingerprint pinned). Rather than copying V9's numeric lambda=60, transfer the historical Validation-winning **R=1.754115** as a reference: lambda=R/r≈25.73 on V11 A0. Main HPO SEARCH FOCUS is **R=lambda*r_A0** (nominal target 0.05..2, actual after lambda minimum R≈0.20452..2), corresponding to **lambda 3..29.33728156**. R=2 is a design limit, NOT a universal safety threshold. The [second 704-parent Train-only combined-gradient report](gradient_gate_v11_v9style_train_108478.json) is immutable **supplementary safety evidence**, not the primary lambda-range selector. The cuifa runner reconstructs its portable gradient_gate.json from BOTH SHA-pinned JSONs (no laptop GPU run or repeated 108,478-parent sweep). Four A0–A3 architecture comparisons use a COMMON reference lambda≈25.73, then multivariate TPE jointly searches lambda log-float / middle stride {2,4} / kernel {5,9} on frozen 23,245-parent six-profile Validation; default **8 trials**, not 12. Using the same A0 reference R does NOT imply equal actual R across different architectures. Tests, data, physics, batch16/micro16 and fixed optimizer remain unchanged; cuifa Stage0, formal HPO, independent-seed confirmation, final training, synthetic Test and RRUFF remain NOT_RUN. Stage0 budget approval is still required. Prior discussions of copying V9 lambda [0.3,60] or hard-cutting at R=2 are historical; neither is the current HPO protocol.

> **2026-11-10 measured laptop Batch default (ACTIVE):** Effective `--batch-size 16` plus `--microbatch-size 16` (no accumulation) is already the unchanged `one_click_v11.py` default. Under RTX 4060 Laptop/8GiB and 12-worker/4-queue/64-cache prefetch, this ran 256 Train-only optimizer steps (4,096 independent-parent exposures) at ~162.10 parents/s with PyTorch allocated peak 0.419GiB. All four A0–A3 architectures passed short 16:16 CUDA steps. Short hardware-ceiling tests passed physical batch 384, but 448+ terminated before acceptance and 384 was NOT verified for sustained training. **Do not automatically raise effective batch**, because both the historical whole-Train gradient audit and the new V9-style safety gate are bound to effective batch16; raising it is a new science/optimizer choice, not a pure VRAM tweak. Cuifa 4070 Ti SUPER Stage0 and HPO remain NOT_RUN. Source: [CURRENT_STATE.md](../docs/CURRENT_STATE.md), [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). The historical `.10` descriptions below predate the completed `.11` gradient run; use current-state evidence for execution.

> **HISTORICAL FIRST R GATE — R-based design restored above (this exact original report is still authoritative evidence). V11 TRAIN-ONLY GRADIENT GATE COMPLETED ON LAPTOP (2026-11-10; HPO NOT_RUN).** The current, independently verified, Git-published [whole-Train gradient evidence](gradient_gate_v11_train_108478.json) is the required input for cuifa's automatic Optuna HPO. Source/Train fingerprints are frozen; the 20,480-stratified-parent, 20-epoch A0 ERM **warmup** is distinct from the complete **108,478-Train-parent, 6,780-batch gradient scan**. Unweighted trunk JS/CE gradient-norm median **0.0681726422** and alignment cosine median **-0.0204393** yield a frozen **lambda_js ∈ [3.0, 29.337281564301204]** design prior: weak [3,4.4005922], medium [4.4005922,14.6686408], strong [14.6686408,29.3372816]. This is a *gradient-effect calibration*, **not** Validation-selected optimum. At lambda=60 the chosen bound is exceeded, but no conclusion about real-domain relative performance follows. Final evidence SHA256: `7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020` (Git commit `8d7c7a6`).

> **HISTORICAL .10 cuifa HPO integration (superseded):** pull the same source commit/manifest, run target-machine Stage 0, then the existing authorized V11 `--mode run` automatically reads the Git-tracked evidence, verifies the portable scientific fingerprint, imports it as immutable `gradient_gate.json` and runs fully automatic multivariate Optuna on **lambda_js ∈ [3,29.3372815643]**, **middle_stride ∈ {2,4}**, **kernel_size ∈ {5,9}**. **No Train gradient warmup/sweep is repeated on cuifa.** HPO trials still require ≥50 complete 108,478-parent epochs. This entry supersedes older `.10` statements below claiming the laptop gradient scan was NOT_RUN; cuifa HPO, confirmation, final, Test and RRUFF remain NOT_RUN. Previous local failed attempts (overstrict CE plateau; confusing 1,280 warmup versus 6,780 gradient steps) are recorded and fixed in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).
> **HISTORICAL V11 .10 — Fully automatic, TRAIN-gradient-guided 3D Optuna TPE (2026-11-10; CODE/TEST PASS, GPU HPO NOT_RUN).** The previous .9 fixed six-trial design is superseded. Fixed: AdamW LR=2e-4, cosine-to-5%-floor over the same 100-parent-epoch horizon, WD=1e-4; ResNet-18-GN blocks/channels/head; effective batch=16. Exactly THREE freely optimized scientific parameters: JS lambda (log-float, constrained by a TRAIN gradient-derived window within the absolute safety bounds [3,120]), middle stage stride (categorical 2/4, outer transitions 4/4), and residual kernel (categorical 5/9). These form the A0–A3 2x2 peak-preservation hypotheses inspired by SimXRD-4M; Bin Cao did NOT directly establish our optimum ResNet stride/kernel combination.

> **HISTORICAL .10 norm-ratio-only gradient gate (superseded):** Train-only A0 Dynamic ERM learns with at least FIVE and at most TEN complete shuffled 108,478-parent epochs. Require learned-state sampled Train accuracy >=0.30 and CE <=1.85, or stop HPO. On that learned model, visit ALL 108,478 unique Train parents exactly once and measure FP32 full-backbone gradients for unweighted CE and paired-view JS, preserving batchwise ratios plus whole-Train aggregate gradient norms. The median ratio defines a weak-to-strong relative gradient-influence search window (weighted JS/CE 0.05–2.0), clipped to lambda [3,120]; reject windows narrower than 2x. Historical lambda60 is only an anchor if inside the independently derived range. The training-only gate is hashed, versioned and required at confirmation/final/handoff; it is not a Validation score and does not touch held-out Test/RRUFF.

> **HISTORICAL .10 Optuna design (superseded candidate range/trial count):** enqueue the four A0–A3 matched-lambda architecture controls first, to report effects of stride, kernel and their interaction at equal exposure. Then multivariate TPE freely proposes the remaining THREE-parameter combinations within the frozen gradient/architecture bounds. Default EIGHT candidates; allowed 6–12. No predetermined lambda30/90 second stage. Every HPO candidate trains at least FIFTY full parent epochs (339,000 steps at batch16), with full six-profile Validation every TEN and ranking based on checkpoints from epoch50 onward. Confirmation uses 2 independent seeds and final uses 3 seeds, each with a 100-epoch maximum and min50/patience3 checks/min_delta0.002. All three stages share the 100-epoch cosine horizon so 50-epoch trials do not decay LR to floor prematurely. Earlier .8 5/10/10 budgets and .9 six fixed combinations are historical. No model, simulator or TEST/RRUFF performances are claimed by this code change; full gradient Gate/HPO on GPU is NOT_RUN.

> **CPU engineering:** user-selected cross-platform default 12 prefetch workers / 4 batches / 64 cached PeakTables / native threads1 (Windows, direct Python and Linux), with explicit overrides. This profile was measured only on the Windows Ryzen 9 7945HX; cuifa/cloud CPU throughput and RAM must still pass Stage 0 before heavy HPO. Effective batch16 remains fixed as scientific optimizer choice; microbatch/accumulation are engineering knobs. Existing 3.64GiB frozen Validation arrays from .7/.8/.9 may be reused under v11-gradient-gated-optuna-20261110.10 only after identity and file-SHA audits. Isolated code checkout: 45 server_migration tests + 2 subtests PASS; the full 108,478-parent CUDA gradient sweep has NOT been executed.
> **CURRENT EXECUTION STATUS (2026-11-09): LOCAL PREFLIGHT PASS; GPU GATE TRANSFERRED.** The `.3` source snapshot passed local package verification, `start_server.sh --plan`, merged-shard/parent-isolation and cache readiness, current manifest reconstruction, one-batch CPU ResNet/CE+JS smoke, `--records-path` adapter smoke, and deterministic prefetch parity. Follow-up CPU and local CUDA interrupted-vs-uninterrupted synthetic training regressions also pass through the trainer's shared checkpoint save/restore helpers; the CUDA regression used this laptop's RTX 4060 with PyTorch `2.13.0+cu126`. The source payload contract is now `v11-prefetch-validation-20261109.5`; the already verified `.3` kit does not contain these follow-up changes and must be regenerated before transfer. These small laptop CPU/CUDA checks do **not** establish target Linux CUDA readiness. Target Linux GPU smoke, throughput/resource measurement, full Validation GPU access, and real trainer/prefetch checkpoint-resume/RNG acceptance remain **BLOCKED / NOT_RUN and assigned as Stage 0 of [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55)**. HPO remains separately gated by GPU/budget approval. **Do not execute the `--run` / HPO / final-training launch commands below.** See [`docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md`](../docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md).

> **Historical implementation reference below:** commands and local receipts describe the 2026-11-03 migration proposal, not current execution approval. Target-GPU readiness is tracked in Issue #55 Stage 0; do not launch without its current receipt and separate authorization. Issue #61 records the local package/CPU preflight only.

2026-11-03 HISTORICAL LOCAL STATE: 154,975 MP-ID structures split 108,483 train / 23,246 Validation / 23,246 Test, with complete ideal PeakTables. ResNet-18-GN A0_R1 won the previous V10/14,060 single-seed architecture study, but it is NOT a V11/154,975 checkpoint.

## Private files
- source_snapshot.zip: V11 source/config/tests + ResNet code + new one_click_v11.py.
- structure_shards.zip: all 154,975 source parent structures and provenance.
- peak_cache_bundle.zip: all 154,975 precomputed ideal PeakTables plus 131,729 train/validation runner records.
- a0_reference_checkpoint.zip: historical V10 single-seed A0_R1 checkpoint and run evidence. REFERENCE ONLY, not a ready V11 model.
- `source_snapshot.zip` includes a versioned member manifest with SHA256 for every source file. `start_server.sh` rejects missing, stale, altered, or incomplete snapshots and verifies an extracted staging tree before copying it into `~/research/AI4science`.
- bundle_manifest.json / SHA256SUMS.txt: archive and launcher SHA256s. Transfer `start_server.sh`, `verify_source_snapshot.py`, and `payload_contract.py` beside the four ZIPs and SHA256SUMS.txt.
- `create_migration_bundles.py` resolves project files from its own Git worktree and restricts the bundle destination to that worktree; it does not source code from the main checkout or a separately staged project tree.

Keep private source data/checkpoints OFF public GitHub. Obey Materials Project and XQueryer terms.

## On rented Linux GPU server
Choose a GPU-enabled Linux image with Python 3.11 and CUDA-compatible PyTorch. Transfer all four ZIPs, SHA256SUMS.txt, start_server.sh, verify_source_snapshot.py, and payload_contract.py together by private SCP/SFTP. From the transfer directory run:

    bash start_server.sh --plan

This unpacks archives into ~/research/AI4science, checks ZIP SHA256, original 154,975 structure IDs/parent isolation, PeakTable manifests/sizes, and prints the frozen HPO design. It DOES NOT run training.

When the above passes and GPU budget is approved, run exactly one command:

    bash start_server.sh --run

This rechecks data, installs scientific requirements into the selected Python environment, runs CPU one-batch V11/ResNet-A0/JS smoke, then automatically searches using Optuna TPE:
- Fixed architecture: original ResNet-18-GN A0, 13,008,839 parameters (not an unproven CNN11 replacement).
- Dynamic same-parent JS. V11 TCH pseudo-Voigt online rendering from pretrained ideal-reflection PeakTables.
- Formal training pool: all 108,478 unique TRAIN parent groups (108,483 MP IDs; five aliases deduplicated). Full HPO Validation: all 23,245 independent parent groups (23,246 MP IDs, one alias deduplicated), six OOD profiles. No 896-parent sampling for formal model selection. Frozen seed 20260721. Locked Test/RRUFF inaccessible.
- Executable `.8` CLI defaults (NOT_RUN): six HPO trials x five parent epochs (33,900 steps per trial at effective batch16), two confirmations x ten epochs (67,800 steps per seed), and three final seeds x ten epochs. Complete six-profile Validation every parent epoch. The later **performance-first v2 active research plan** (NOT YET IMPLEMENTED) instead proposes matched JS/ERM 50-epoch convergence pilots and 12 HPO candidates per method. Neither plan is a finished experiment; see Issue #55.
- Parameters: LR 5e-5 to 3e-4, JS lambda 15 to 120, AdamW weight decay 1e-6 to 1e-3, cosine-vs-constant schedule. First Optuna trial is the old A0_R1 recipe, reevaluated on the NEW data and V11, not treated as a prior score.
- Deterministic full-Validation paired spectra are generated ONCE per profile, cached as immutable memory-mapped .npy arrays (~3.64 GiB total for 6 profiles x 2 views x 23,245 x 3,501 float32 samples), SHA256-indexed and reused across every candidate/seed. Half-written profiles are rebuilt; mismatching completed profiles fail closed. SQLite study, frozen trial contract, checksummed checkpoint, validation history, final JSON and safe resume.
- max_gpu_hours default 12 is a soft stop before new trials, NOT a hard spending cap or a background shutdown.

Output: ~/research/AI4science/server_runs/v11_a0_js_optuna/

## Scientific / implementation boundaries
The local package test verified ZIP integrity, 154,975 source records/parent isolation, and V11 two-view ResNet A0 one-batch forward+backprop on CPU. Full 155k PeakTable cache file count, hashes and manifest were separately audited on the laptop. FULL OPTUNA EXPERIMENT HAS NOT RUN ON A RENTED LINUX GPU.

The existing generic xrd_robustness.training.runner does not implement the full architecture-conditioned cosine HPO. New server_migration/one_click_v11.py implements a separate bounded A0 trainer with validation and checkpoint recovery. It must pass Linux CUDA + memory + throughput smoke before formal unattended operation can be considered production proven.

Do NOT claim the old V10 validation 0.7318 has been achieved under V11/new data. Do NOT use the frozen Test or real RRUFF to tune. Final RRUFF paper-aligned protocol remains a later stage; full unique-parent Validation is now mandatory for HPO selection; independent seeds on the same Validation still do not constitute external real-domain evidence.

Recommend inspecting 32+ GiB RAM, 16+ GiB GPU memory, and at least 20 GiB spare disk (including ~3.64 GiB for frozen Validation panels) as initial planning targets; actual machine sizing and cloud runtimes have not been measured. Original Windows E-drive scripts are in source_snapshot under reference_windows_resnet_joint and are NOT used by this workflow.

Changing HPO budget/search parameters after starting a study triggers an immutable-contract error. Use a separately named new study rather than silently overwriting old trials.

**Scope verified (2026-11-03):** The actual 131,729-record train/validation manifest was checked row-by-row: train 108,478 unique parents, Validation 23,245 unique parents, all 7 systems, alias exclusions 5/1, no overlap. Four automated regression tests pass; direct V11 simulated-vs-cached scores matched exactly on a seven-parent six-profile smoke fixture. This does NOT mean full validation GPU scoring or Linux cloud HPO has run.


## Unified prefetch and GPU training path (draft update, PR #67)

The same deterministic pipeline is now selected for **all V11 GPU stages**, not
only Validation:

- TRAIN: a bounded set of 4 `spawn` CPU workers (defaults: `--prefetch-workers 4
  --prefetch-batches 3 --native-threads 1 --worker-peak-cache 512`) lazily
  load ideal-peak NPZ into per-worker LRU caches and render same-parent dynamic
  pairs concurrently with the GPU forward/backward pass. SHA256 material-ID
  worker sharding and native thread policy are reused from the earlier
  `training_prefetch.py`.
- GPU: pinned CPU input buffers, asynchronous H2D transfers, BF16 forward
  when supported, stable FP32 CE + JS arithmetic, finite-gradient assertion,
  and periodic last/best checkpoints.
- VALIDATION: the same V11 prefetch workers render all **23,245 parent-disjoint
  groups** over six fixed OOD profiles exactly once. The paired float32 spectra
  are SHA-indexed and memory-mapped for repeated batched GPU evaluation.
  FP32 inference is the default for consistent HPO ranking. Optional
  `--validation-bf16` requires separate parity verification.
- RESUME: CPU can schedule ahead, but the checkpoint saves the RNG state
  *after the last completed optimizer step*, never the later prefetched RNG
  state; resumed experiments can reproduce parent selection.
- OPTUNA: `bash start_server.sh --run` uses this shared loop for six trial
  configurations plus two-seed confirmation.
- FINAL: after a completed HPO study, a separate explicit
  `bash start_server.sh --final` runs three predetermined independent seeds
  (default 49,280 optimizer steps each) with the **same optimized pipeline**.
  It saves `final_training_summary.json` but does not evaluate RRUFF/Test.
  The final stage is NOT automatically started before confirmation.
- Do **not** transfer or run an older four-ZIP kit unchanged. Regenerate the
  private snapshot from the reviewed worktree so its versioned manifest and
  all member hashes match the current `payload_contract.py`; update
  `SHA256SUMS.txt` with the launcher and verifier files too.

**Validation level:** integration code and regression tests are committed
to GitHub, but the authorized laptop is offline. The new pipeline has NOT yet
been executed through the full GPU parity/throughput/resume tests or the rented
Linux server. Do not claim it is a fully tested production runner.


### Optional portable precomputed full Validation panels (2026-11-03)

On the local RTX 4060 laptop, all 23,245 independent Validation parents under
all six V11 OOD profiles were rendered and SHA-indexed successfully. A separate
GPU FP32 engineering scoring pass evaluated all six profiles with UNTRAINED
model weights; these are NOT scientific model performance results. The data
contains 3,906,277,296 bytes in 12 paired-view .npy arrays.

The package_validation_panels.py script can generate optional integrity-checked
validation_panel_bundle.zip. If this fifth ZIP is present and SHA256SUMS.txt
includes its checksum, start_server.sh --run automatically extracts it into
~/research/AI4science/server_runs/v11_a0_js_optuna/validation_panels_v11 once.
The HPO runner rechecks exact renderer/source/parent identity and every array
SHA before reuse. Without the optional ZIP, the original four-ZIP one-click
workflow still works and regenerates frozen Validation panels on the server.
Never treat the simulated Validation data as held-out Test or RRUFF evidence.

This optional cache remains private; do not upload it to public GitHub.


## Native Windows HPO → Linux final training (2026-11-09)

The **same** V11 simulator, ResNet-A0, same-parent JS loss, frozen 108,478
training parents and 23,245 Validation parents are used on both platforms.
This is an *execution split*, not a new research protocol or a second model.

**cuifa Windows desktop candidate:** RTX 4070 Ti SUPER 16 GiB VRAM,
32 GiB RAM. CPU/SSD not yet measured. CUDA PyTorch, Optuna and the Python
package must be installed in a suitable Windows Python 3.11 environment.
The complete private `xrd_robustness/data/merged_154975_v11` source/cache,
frozen manifest and matching source snapshot must be present, and remain
outside public GitHub. Do not restart old 9,842-parent Optuna.

**2026-11-09 V11 scaled parent-epoch training budget (source contract `.8`, NOT_RUN):** To avoid selecting hyperparameters after only one parent pass, the **new CLI defaults** for the active `epoch_shuffle` mode are **5 full TRAIN-parent epochs per HPO trial**, **10 per confirmation seed**, and **10 per final seed**; full six-profile Validation is checked every parent epoch by default. At effective parent batch **16**, one epoch is `ceil(108478/16)=6,780` optimizer steps, therefore HPO **33,900 steps/trial** (6 trials), confirmation **67,800 steps/seed** (2 seeds), and final **67,800 steps/seed** (3 seeds). At other effective batches, each stage recomputes steps from `ceil(108478/batch)`. A parent draws *two* independently disturbed XRD views for the same-parent CE+JS objective; a parent epoch is **not** the same unit as a SimXRD spectral epoch. Existing `--hpo-steps`, `--confirm-steps`, `--final-steps` and `--eval-every` explicit CLI overrides remain available, but experiments must freeze and report their actual choices. This change scales the planned optimizer updates from **215,640** to **542,400** across the full default 6+2+3 run sequence (about **2.52×**, excluding Validation and simulator overhead), not a measured duration or a claim of equal compute with SimXRD-4M. No target-GPU HPO has started or been authorized. The default 12-hour `max_gpu_hours` is a **soft stop between trials/seeds**, not a hard mid-trial cap; obtain representative cuifa Stage-0 measurements and explicit budget authorization first. An existing `.7` private source kit is stale; regenerate/hash-verify the `.8` payload, and do not resume an already-created study with a mismatching experiment contract. See [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

**SimXRD-4M hardware reference (literature; checked 2026-11-09, not a V11 measurement):** Bin Cao et al., *SimXRD-4M* (ICLR 2025), §4.2 p.7, explicitly report PyTorch training on **GeForce RTX 3090 (24 GB VRAM)**, **not RTX 3070**; their shared settings were batch size **128**, learning rate **2.5e-4**, up to **50 epochs**, and early-stopping patience **3**. The paper does **not** establish how many 3090 cards were used or any V11 runtime/compatibility result. The cuifa **4070 Ti SUPER (16 GB)** has less VRAM and the V11 same-parent paired-view workload/batch meaning differs, so do **not** transfer the paper's batch size, throughput, or feasibility assumptions; use the Stage-0 measured batch/microbatch, peak VRAM, CPU-prefetch/RAM, full Validation and resume gates in Issue #55. Primary source: [ICLR 2025 official PDF, §4.2](https://proceedings.iclr.cc/paper_files/paper/2025/file/b04843d76c9f090beca55f335c4ea6bf-Paper-Conference.pdf).

From the repository root, using native PowerShell (no WSL/Ubuntu required):

```powershell
powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode plan
powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode smoke
# Only after explicit owner approval and complete Stage-0 hardware / resource /
# full-Validation / resume acceptance; plan/smoke do not authorize formal HPO:
powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode hpo
# Once all 6 trials + 2 independent confirmation seeds really complete:
powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode export
```

`smoke` checks CUDA two-view forward/backprop and two-worker rendering parity,
but is **only a bounded smoke**, not a completed Stage 0. With 16/32 GiB,
measure GPU peak memory, Windows RAM/commit, SSD free space, full six-profile
Validation accessibility, GPU/CPU throughput and interrupted resume *before*
authorizing HPO. If batch or prefetch settings change, keep the contract and
optimization exposure fixed across trial comparisons and record the change.

The native launcher defaults to two prefetch workers, two queued batches and
256 cached PeakTables per worker on the candidate 16/32 GiB desktop. Non-default
runner options may be forwarded via `-RunnerArgs` and must then be repeated
for final training.

Export creates private `_local/v11_hpo_handoff.zip`: verified Optuna database,
trial JSON evidence, selected and confirmation checkpoints and their hashes,
original experiment contract, and a compact Validation index. It intentionally
excludes frozen Test / RRUFF and the large simulated Validation `.npy` arrays.

For **cloud Linux final training**, rebuild the full private source kit using
the current source snapshot contract (not the old `.5` kit), transfer the
HPO ZIP into the same kit directory, and add its SHA256 to
`SHA256SUMS.txt` as `<64-hex-sha>  hpo_handoff.zip`.
Run `bash start_server.sh --plan` first (handoff ZIP may already be present),
then **only with separate final-training authorization** run:

```bash
bash start_server.sh --final
```

The final launcher imports the hash-verified handoff, regenerates full
Validation panels if they were not separately supplied, checks every paired
panel SHA against the frozen HPO identity, then revalidates Optuna trial scores,
the selected checkpoint, both confirmation checkpoints and the full
contract before starting three final seeds. If cross-OS rendering is not
bitwise identical, the correct response is **BLOCKED**, not to weaken hashes:
transfer the existing separately SHA-verified `validation_panel_bundle.zip`
as an optional kit asset, with its own line in `SHA256SUMS.txt`.

As of V11 payload contract `.8`, Windows HPO and Linux final may vary
only CPU prefetch workers, queued batches, worker-cache size, native threads
and the local GPU-hours soft stop. All differences are audited. The scientific
effective/micro batch, sampling mode, training budgets, source, simulator,
model, validation and selected hyperparameters remain frozen. Worker-count
rendering parity is tested. Test/RRUFF scoring remains separate.


### V11 parent coverage and batch profiling (.8 current; .7 historical tests)

- Default `epoch_shuffle` makes every complete train epoch cover each of the
  **108,478** independent parents once, including a possibly short last batch.
  Restarting at any optimizer step deterministically recovers the permutation.
  `random_batch` is retained only as an explicit alternative; it does not
  guarantee coverage across steps.
- Default effective `--batch-size 16` processes 16 parents / 32 XRD views
  per optimizer step. The **currently implemented .8 CLI default (NOT_RUN; superseded by the separate v2 research plan)** is
  **33,900 steps** (5 parent epochs); confirmation and final are both
  **67,800 steps** (10 epochs) per seed. Validation runs every **6,780 steps**.
  These planned defaults rescale with batch size using `ceil(108478 / batch)`.
  Legacy .7 one/two-epoch figures describe historical engineering tests only.
- `--microbatch-size 8 --batch-size 16` performs two backward passes with
  parent-count-weighted CE + JS and only one clip/optimizer step; it reduces
  activation memory without changing effective parent batch or exposure.
  Microbatch size is still recorded in the frozen experiment contract.
- Stage 0 can run a bounded Train-only, non-HPO batch check:
  `powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1
  -Mode benchmark -Python path\to\python.exe`.
  For an 8GB laptop, direct command example:
  `python server_migration/benchmark_windows_v11.py
  --cases 4:4,8:8,16:8 --warmup 1 --steps 2`.
  Output gives parent/s, measured-step latency, CUDA allocated/reserved
  memory and disk free. Tiny smokes do not certify cuifa's 4070 Ti SUPER.


### Unified CPU prefetch default — Windows, Linux and future cloud

Owner decision (2026-11-09): **12 prefetch workers / 4 queued batches /
64 cached PeakTables per worker / native_threads=1** is the universal
engineering starting point. This applies to the native Windows launcher,
`python server_migration/one_click_v11.py` directly, and the Linux
`bash start_server.sh --plan|--run|--final` launcher on rented cloud
servers. There is no automatic worker downgrade based on CPU model/RAM;
explicit `--prefetch-workers`, `--prefetch-batches`,
`--worker-peak-cache`, `--native-threads` overrides remain available.
The Linux prefetch smoke also follows an explicitly overridden worker
count instead of hardcoding four. HPO/final study contracts record the
actual choices, and resumed jobs must remain scientifically consistent.

The **12/4/64/1 performance numbers come only from the Ryzen 9 7945HX
Windows laptop**. Linux/cloud throughput and memory stability are not
yet demonstrated; measure the target machine in Stage 0 before
authorizing full-duration training. Rebuild the private source snapshot
and associated SHA256SUMS after this default change. Neither an
untested cloud deployment nor a `--plan` is a completed GPU training run.

### CPU prefetch tuning — local Ryzen 9 7945HX (2026-11-09)

Only **engineering resource settings** changed. TCH pseudo-Voigt rendering,
the fixed 108,478-parent Train pool, deterministic epoch shuffle, two views,
ResNet-A0, CE+JS and the frozen six-profile Validation are unchanged.

On the user's **Ryzen 9 7945HX (16 cores/32 threads), Windows, 32 GiB RAM,
RTX 4060 Laptop**, Train-only CPU paired-render sweeps with identical
SHA256 outputs measured 2/2: **52.83**, 4/2: **84.82**, 6/3: **116.54**,
8/4: **140.15** parents/s (48 batches; 64-item caches); additional
80-batch sweeps yielded 8/4: **144.60**, 10/4: **165.50**,
12/4: **181.49** parents/s. Short measurements are not HPO estimates.

More importantly, actual **CPU+GPU paired ResNet-A0/JS optimizer** comparisons
at effective/microbatch=16, native_threads=1 and deterministic
`epoch_shuffle` yielded 4/2/128: **82.43** parents/s (128 measured steps);
8/4/64: **136.64**, 10/4/64: **149.14**, 12/4/64:
**168.08** parents/s (160 measured steps). GPU step compute was about
0.036–0.048 seconds; most overhead was waiting for the CPU renderer.
12 workers' minimum sampled available RAM was **10.25 GiB** in the 160-step GPU benchmark. A later 12-worker 512-step + complete six-profile Validation acceptance **PASS** took 129.88s for training+scoring (earlier 4-worker full-Validation acceptance: ~183.17s, not load-matched); the lowest available RAM was only **5.80 GiB**, with GPU temperature at most 58°C and total VRAM usage at most 2,594MiB. The launcher warns when startup free RAM is below 14 GiB; close heavy background apps before HPO.
Paired-view hashes matched exactly across every CPU comparison; no Test or
RRUFF data were used. Rates can vary with thermals, background load and
the parent mix; full multi-hour durability is not established by these sweeps.

`start_windows.ps1 -CpuProfile auto` now selects the **conservative
12-worker / 4 queued batches / 64 cached PeakTables per worker /
native_threads=1** profile on **all Windows hosts**, including cuifa's desktop, without CPU-model,
core-count or installed-RAM branches. `-CpuProfile conservative` explicitly
forces this laptop-validated setting; `-CpuProfile ryzen7945hx` and
`-CpuProfile performance12` remain equivalent aliases. There is no
automatic low-memory worker fallback; current free RAM is still checked
and warned about at launch.

For cuifa's stronger but as-yet unmeasured CPU, the **optional,
experimental** `-CpuProfile aggressive16` enables **16 workers /
4 queued batches / cache 32 / native_threads=1**. It is not assumed faster
or approved for formal HPO until cuifa-host CPU+GPU benchmark, complete
six-profile Validation and restart/memory checks. On 16 workers the
HPO launcher refuses startup with <18 GiB free RAM; the conservative
12-worker profile warns below 14 GiB free RAM. Any
individual `-RunnerArgs` resource flags take precedence without resetting
the other flags. These exact settings are frozen on HPO start/resume; Linux
final may override only already-authorized runtime CPU-resource settings.

To profile a *different* Windows host without GPU training or Optuna:
```powershell
& .\.venvs\xrd_test\Scripts\python.exe server_migration/benchmark_windows_v11.py --cpu-only --worker-cases 4:2,8:4,12:4,16:4 --steps 80 --batch 16 --cache 32 --output _local/v11_cpu_host_profile.json
powershell -ExecutionPolicy Bypass -File server_migration/start_windows.ps1 -Mode plan -Python .\.venvs\xrd_test\Scripts\python.exe
```
The real `plan` confirms the resolved profile and effective experiment
contract; neither command authorizes or starts HPO. If moving to cuifa,
run this CPU-only benchmark **on cuifa itself**, then compare 12 vs
16 workers under GPU load and select a fixed resource profile before
starting her HPO study. The user reports that cuifa's CPU is faster than
the local Ryzen 9 7945HX, but a faster CPU alone does not guarantee
16-worker superiority with the same 32GiB RAM. Recreate the private source snapshot after changing
the launcher or benchmark script; old kit hashes cannot be reused.
