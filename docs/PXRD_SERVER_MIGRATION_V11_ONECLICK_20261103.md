# PXRD V11 + 154,975 parent structures: one-command Linux GPU migration (2026-11-03)

> **Status superseded for execution on 2026-11-09:** do not follow historical launch commands in this note. Issue #61 is BLOCKED pending current-main schema/manifest and package-hash checks; GPU smoke is BLOCKED / NOT_RUN without separate authorization; #55 remains BLOCKED BY #61. See [the minimum preflight audit](ISSUE_61_V11_MINIMUM_PREFLIGHT_AUDIT_20261109.md).


STATUS: LOCAL PACKAGE BUILT / PACKAGE HASHES VERIFIED / LOCAL CPU AND CUDA SMOKES PASS / RENTED LINUX GPU FULL HPO NOT RUN.

## Motivation and model selection
The previous V10 / 14,060-structure A0/A1/A2 x R0/R1 ResNet campaign completed its six cells. A0_R1 was the provisional single-seed Validation OOD Macro-F1 winner at 0.731830. Its architecture is ML4PXRD ResNet-18-GN with original stride 4/4/4 and kernel size 9, 13,008,839 parameters. R1 means LR=2e-4 and cosine LR schedule. This was OLD dataset / V10 renderer evidence, not an achieved V11/154975 score. The old-data V10 Optuna supervisor had been explicitly cancelled by the owner and is not restarted.

The owner requested a single server workflow for model, simulator and hyperparameter selection. This deliverable preserves A0 as the bounded starting architecture, uses the precomputed 154,975 ideal-reflection PeakTables and V11 TCH pseudo-Voigt online simulator, and introduces a new Linux-portable ResNet-A0 / same-parent Dynamic JS / Optuna TPE workflow. It searches LR, JS lambda, AdamW weight decay, and cosine-vs-constant schedule, not another broad architecture sweep. The first trial reevaluates old A0_R1 settings on the new data; old V10 scores are not seeded as new-study measurements.

## What was actually verified
- 154,975 original structure IDs and 154,968 canonical parent groups have a SHA256-verified parent-disjoint 70/15/15 split; 154,975 ideal PeakTables were fully generated and audited (0 skips).
- A new private bundle in E:\AI4science\_local\server_migration_20261103 contains code snapshot, structure split, complete PeakTable cache, historical A0_R1 checkpoint, checksums, and Linux bootstrap scripts. Archive SHA256 all verified; source snapshot CRC passed; 154,986 cache ZIP entries enumerated.
- Extracting the new code package plus a minimal cache fixture successfully ran the exact packaged Python one_click_v11 plan and CPU smoke. Model/simulator/same-parent JS one-batch loss and gradient were finite.
- Direct local CUDA microtrial of two gradient steps plus six OOD profile validation, checkpoint save, checkpoint file SHA256, and completed-result reuse succeeded. That microtrial used only seven validation parents and must NOT be cited as model accuracy.
- The full new simulator-to-131,729 train/validation manifest is ready; row-level parent audit confirmed train 108,478 and Validation 23,245 unique parent IDs, 5/1 duplicate aliases removed. Formal selection rejects missing/extra parents, cross-split leakage, conflicting labels, altered hashes, or missing completed Validation cache. Test remains excluded.

## One-command server contract
After private transfer of source_snapshot.zip, structure_shards.zip, peak_cache_bundle.zip, a0_reference_checkpoint.zip, SHA256SUMS.txt and start_server.sh to the same directory of a CUDA-compatible Linux/Python 3.11 GPU machine:

    bash start_server.sh --plan
    bash start_server.sh --run

Plan verifies source split, parent integrity, archive SHA256, PeakTable manifest and data-path contract. Run installs required scientific dependencies into the selected GPU Python environment, performs one-batch V11/A0/JS smoke, then runs bounded Optuna TPE using a SQLite study, append-only per-trial protocols, last/best checkpoints, source/simulation config SHA256, deterministic Validation, and two extra confirmation seeds. Default budget: 6 trials x 6160 steps, then best recipe x 2 seeds x 12320 steps. Six OOD simulated Validation profiles are used for selection on ALL 23,245 unique frozen parent-disjoint Validation groups (from 23,246 MP-ID rows, one alias excluded), not RRUFF or locked Test. Training samples all 108,478 unique train groups (from 108,483 rows, five aliases excluded). The old 896-parent subsample option was removed for formal HPO. Each profile's two deterministic realizations are pre-rendered exactly once to checksum-indexed memory-mapped .npy panels (~3.64 GiB), then reused across all checkpoints/trials. Each 6,160-step HPO trial receives one full-Validation checkpoint; each 12,320-step confirmation gets two. Resource usage is bounded by trial counts; a configured GPU-hours value is a SOFT cap checked between trials, NOT a rental price shutdown.

## Limitations
- No complete Linux CUDA end-to-end HPO / rented-server runtime / memory measurement yet. Full 23,245-parent Validation scoring has NOT been run on the rented Linux machine; all-class split audit and 7-parent cached/live consistency smoke have passed. Calling this an already completed hyperparameter search would be false.
- New V11 and new 15.5w data results are not directly interchangeable with historical V10/14k numbers; Test and RRUFF cannot be used to pick hyperparameters.
- The A0_R1 checkpoint remains a historical V10 reference. It was NOT used to initialize new V11 HPO weights and does NOT imply training on the new corpus.
- The latest code is a local snapshot from the V11 feature worktree, including necessary unmerged modifications. GitHub main alone is not presently a complete source of the private split/caches.
- Large private structure assets and weights do not belong in the public Git repository. All source terms and provenance must be retained.

This deliverable is an engineering mobility milestone, not a new classification-performance result.

## Correction: owner-requested full Validation before renting the GPU

2026-11-03 follow-up fixed the earlier 896-parent formal HPO defect in the new server launcher. Four pure offline parent-integrity regression tests and full 131,729-row manifest audit passed. A seven-parent/six-profile test verified cache generation, hash reuse and exactly identical live-versus-cached Validation metrics. Model mode now returns to train after Validation. The Linux entrypoint no longer prints COMPLETE if the soft GPU-hours gate returns before Optuna confirmation. Private source ZIP will be reassembled and checked against updated SHA256 before transfer; the original 154,975 PeakTable bundle need not change.
