# AI4science 2026-11-03 — Linux GPU migration + bounded one-command V11 Optuna

CURRENT STATE: 154,975 MP-ID structures split 108,483 train / 23,246 Validation / 23,246 Test, with complete ideal PeakTables. ResNet-18-GN A0_R1 won the previous V10/14,060 single-seed architecture study, but it is NOT a V11/154,975 checkpoint.

## Private files
- source_snapshot.zip: V11 source/config/tests + ResNet code + new one_click_v11.py.
- structure_shards.zip: all 154,975 source parent structures and provenance.
- peak_cache_bundle.zip: all 154,975 precomputed ideal PeakTables plus 131,729 train/validation runner records.
- a0_reference_checkpoint.zip: historical V10 single-seed A0_R1 checkpoint and run evidence. REFERENCE ONLY, not a ready V11 model.
- bundle_manifest.json / SHA256SUMS.txt: archive SHA256s. start_server.sh: one-command entrypoint.

Keep private source data/checkpoints OFF public GitHub. Obey Materials Project and XQueryer terms.

## On rented Linux GPU server
Choose a GPU-enabled Linux image with Python 3.11 and CUDA-compatible PyTorch. Transfer all four ZIPs, SHA256SUMS.txt and start_server.sh together by private SCP/SFTP. From the transfer directory run:

    bash start_server.sh --plan

This unpacks archives into ~/research/AI4science, checks ZIP SHA256, original 154,975 structure IDs/parent isolation, PeakTable manifests/sizes, and prints the frozen HPO design. It DOES NOT run training.

When the above passes and GPU budget is approved, run exactly one command:

    bash start_server.sh --run

This rechecks data, installs scientific requirements into the selected Python environment, runs CPU one-batch V11/ResNet-A0/JS smoke, then automatically searches using Optuna TPE:
- Fixed architecture: original ResNet-18-GN A0, 13,008,839 parameters (not an unproven CNN11 replacement).
- Dynamic same-parent JS. V11 TCH pseudo-Voigt online rendering from pretrained ideal-reflection PeakTables.
- Formal training pool: all 108,478 unique TRAIN parent groups (108,483 MP IDs; five aliases deduplicated). Full HPO Validation: all 23,245 independent parent groups (23,246 MP IDs, one alias deduplicated), six OOD profiles. No 896-parent sampling for formal model selection. Frozen seed 20260721. Locked Test/RRUFF inaccessible.
- 6 trials x 6,780 optimizer steps each, 16 parents/batch, with FULL Validation after 6,780 steps; two new-seed confirmations x 12,320 steps with 2 full Validation checkpoints each. The HPO budget covers all 108,478 unique training parents at least once. Parent sampling shuffles each full cycle without replacement and carries the sampler cursor through checkpoints. Reduced validation frequency intentionally limits GPU cost when using all 23,245 parents.
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
