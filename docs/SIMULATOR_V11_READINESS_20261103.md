# V11 simulator readiness check — 2026-11-03

## Decision

**V11 is usable for controlled simulation pilots and online rendering from the full library's validated PeakTables.** All 154,975 ideal-reflection PeakTables and the runner-compatible train/validation manifest are complete and passed a file-level integrity audit. This does not mean a persistent spectrum corpus or a model-training run exists, and it does not establish full-epoch V11 rendering/training throughput. The latest simulator implementation in this checkout is `v11_tch_pseudo_voigt`, introduced by commit `f18c27b`.

## Evidence run

- Re-ran `xrd_robustness/scripts/accept_simulator_v11.py` in an isolated temporary Python environment with Pymatgen 2026.5.4. The seven-CIF acceptance completed successfully: one actual CIF per crystal system, labels preserved, outputs finite, paired views from the same parent and label, views distinct, deterministic replay exact, and the legacy V9 renderer unchanged.
- The physical checks passed for increasing Caglioti angular broadening, stronger microstrain broadening, and stronger Scherrer broadening at smaller crystallite size. The area-normalized peak test retained its integrated area. The test used the 10–80° grid at 0.02° spacing (3,501 points).
- The acceptance timing over seven cached PeakTables averaged 0.00690 s per two-view pair for V11 and 0.00262 s for V9 (V11/V9 = 2.63). This is renderer-only timing, not structure parsing, peak-table precomputation, disk I/O, or a full training epoch.
- Separately sampled the first training-shard record for each of the seven crystal systems from the current 154,975-ID structure library. Reconstructed each structure, made its ideal PeakTable, and rendered a V11 pair. All seven matched their stored crystal-system labels when checked with Pymatgen at `symprec=0.1`; each produced finite 3,501-point outputs, exact replay, same-parent metadata, and distinct views. This is a seven-record smoke sample, not a random or full-corpus audit.
- Two CIF parser warnings noted small fractional-coordinate adjustments to ideal values. They did not cause label mismatches in this sample; batch processing should retain parser warnings and failure counts.

## What this establishes

V11 can turn structures from the new library into usable simulated spectra on bounded smoke samples and can render online from validated full-library PeakTables. The original source pool remains structure-only; the new local cache holds ideal reflection intermediates, not rendered spectra, and no full spectrum corpus has been generated.

The current training runner consumes a JSONL manifest pointing to precomputed `.npz` PeakTables and accepts only `train` and `validation` rows. The new library stores its structure under `structure`; the precompute script maps that field and `source_structure_fingerprint` directly from the compressed shards. The builder emits the complete train/validation manifest and excludes test. Full-corpus PeakTable precomputation and file-integrity checks are now complete; model training and full-epoch rendered-spectrum throughput were not measured.

The initial acceptance-only environment lacked pytest, so no test was claimed at that point. In the follow-up, the focused simulator and cache tests ran in an isolated environment: **10 passed**. This is a targeted test pass, not a full repository test-suite pass.

## 2026-11-03 implementation follow-up

Added direct `.jsonl`/`.jsonl.gz` schema adaptation to [the PeakTable precompute script](../xrd_robustness/scripts/precompute_peak_tables.py), optional `--external-python` selection for the threaded batch helper, and [a training-manifest builder](../xrd_robustness/scripts/build_merged_library_training_manifest.py). The runner manifest joins complete train and validation caches, checks exact IDs/fingerprints/cache sizes, uses paths relative to the cache root, and excludes the test shard. The subsequent full-library results are recorded below and in the [adapter workflow](STRUCTURE_LIBRARY_154975_TRAINING_ADAPTER.md).

## 2026-11-03 full-library PeakTable precompute follow-up

| Split | Completed | Skipped | Cache bytes | Elapsed seconds |
| --- | ---: | ---: | ---: | ---: |
| Train | 108,483 | 0 | 1,213,929,797 | 1,777.38 |
| Validation | 23,246 | 0 | 260,847,519 | 334.68 |
| Test | 23,246 | 0 | 264,560,366 | 334.52 |
| **Total** | **154,975** | **0** | **1,739,337,682** | **2,446.59** |

The run used six workers, batch size 100, and Pymatgen 2026.5.4 / pymatgen-core 2026.10.31 on the local Windows workstation. It was not run on Tencent Cloud. Cache generation loaded all six required reflection arrays back from every `.npz`; an independent audit then verified exact IDs, fingerprints, sizes, and SHA256 for all **154,975/154,975** files. A real-cache smoke used train `mp-10` and validation `mp-10004`; both produced distinct, same-parent, deterministic V11 view pairs with finite 3,501-point outputs. The manifest has 131,729 rows (train 108,483; validation 23,246) and zero test rows. Focused pytest result: 10 passed.

This establishes the structure → ideal PeakTable cache → runner-manifest → V11 online-render path. It does not generate persistent V11 spectra, start training, or measure a full training epoch. The workflow's full-scale model run still targets the planned Tencent Cloud environment. See the [machine-readable evidence](../xrd_robustness/reports/simulator_v11/merged_154975_precompute_20261103.json).

## Decision record

- **Date:** 2026-11-03
- **Question / previous assumption:** Whether the current V11 simulator can be used with the newly split structure library.
- **New evidence:** Official seven-CIF acceptance rerun passed; seven structures sampled from the new train shard also rendered successfully with matching labels.
- **Decision:** Mark V11 as the latest bounded-ready simulator for controlled generation and pilot work. Keep full-scale generation and formal training conditional on the data adapter, corpus-scale integrity/runtime measurements, independent RRUFF evaluation readiness, and a declared compute budget.
- **What changes now:** Small controlled experiments may select V11 explicitly and cite these acceptance artifacts.
- **What does NOT change:** V9 historical results/default behavior, frozen datasets/splits/checkpoints, and the fact that the 154,975-record library contains structures rather than spectra.
- **Status:** V11 BOUNDED ACCEPTANCE PASS / FULL PEAKTABLE INTEGRATION VALIDATED / SPECTRUM-TRAINING THROUGHPUT NOT MEASURED.
- **Relevant implementation:** [V11 simulator](../xrd_robustness/src/xrd_robustness/simulator_v11.py), [V11 config](../xrd_robustness/configs/simulation.v11_tch_pseudo_voigt.json), [acceptance script](../xrd_robustness/scripts/accept_simulator_v11.py).
- **Machine-readable evidence:** [official acceptance rerun](../xrd_robustness/reports/simulator_v11/acceptance_rerun_20261103.json) and [154,975-library sample](../xrd_robustness/reports/simulator_v11/merged_154975_sample_20261103.json).
