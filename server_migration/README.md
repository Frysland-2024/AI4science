# AI4science 2026-11-03 — Linux GPU migration + bounded one-command V11 Optuna

CURRENT STATE: 154,975 MP-ID structures split 108,483 train / 23,246 Validation / 23,246 Test, with complete ideal PeakTables. ResNet-18-GN A0_R1 won the previous V10/14,060 single-seed architecture study, but it is NOT a V11/154,975 checkpoint.

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
- 6 trials x 6,160 optimizer steps each, 16 parents/batch, with FULL Validation after 6,160 steps; two new-seed confirmations x 12,320 steps with 2 full Validation checkpoints each. Reduced validation frequency intentionally limits GPU cost when using all 23,245 parents.
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
