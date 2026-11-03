# V11 simulator readiness check — 2026-11-03

## Decision

**V11 is usable for controlled simulation pilots and structure-to-spectrum smoke runs. It is not yet qualified for generating the full 154,975-record training corpus or starting formal large-scale training.** The latest simulator implementation in this checkout is `v11_tch_pseudo_voigt`, introduced by commit `f18c27b`.

## Evidence run

- Re-ran `xrd_robustness/scripts/accept_simulator_v11.py` in an isolated temporary Python environment with Pymatgen 2026.5.4. The seven-CIF acceptance completed successfully: one actual CIF per crystal system, labels preserved, outputs finite, paired views from the same parent and label, views distinct, deterministic replay exact, and the legacy V9 renderer unchanged.
- The physical checks passed for increasing Caglioti angular broadening, stronger microstrain broadening, and stronger Scherrer broadening at smaller crystallite size. The area-normalized peak test retained its integrated area. The test used the 10–80° grid at 0.02° spacing (3,501 points).
- The acceptance timing over seven cached PeakTables averaged 0.00690 s per two-view pair for V11 and 0.00262 s for V9 (V11/V9 = 2.63). This is renderer-only timing, not structure parsing, peak-table precomputation, disk I/O, or a full training epoch.
- Separately sampled the first training-shard record for each of the seven crystal systems from the current 154,975-ID structure library. Reconstructed each structure, made its ideal PeakTable, and rendered a V11 pair. All seven matched their stored crystal-system labels when checked with Pymatgen at `symprec=0.1`; each produced finite 3,501-point outputs, exact replay, same-parent metadata, and distinct views. This is a seven-record smoke sample, not a random or full-corpus audit.
- Two CIF parser warnings noted small fractional-coordinate adjustments to ideal values. They did not cause label mismatches in this sample; batch processing should retain parser warnings and failure counts.

## What this establishes

V11 can currently turn structures from the new library into usable simulated spectra on a small smoke sample. The previous wording that spectra still need to be generated remains correct for the library itself: the committed 154,975-record pool is structure-only, and no full spectrum corpus has been generated.

The current training runner consumes a JSONL manifest pointing to precomputed `.npz` PeakTables and accepts only `train` and `validation` rows. The new library stores its structure under `structure`; the existing PeakTable precompute script expects `standardized_structure`. A schema adapter, scalable PeakTable precomputation, integrity/skip audit, and a runner manifest are still needed before full-corpus training. No model training was started in this check.

The targeted pytest file was not run in this environment because the default interpreter did not have pytest (and the full training stack was not installed there). The executable acceptance script and the seven-record real-library smoke both completed in the isolated environment; this record does not claim a full test-suite pass.

## Decision record

- **Date:** 2026-11-03
- **Question / previous assumption:** Whether the current V11 simulator can be used with the newly split structure library.
- **New evidence:** Official seven-CIF acceptance rerun passed; seven structures sampled from the new train shard also rendered successfully with matching labels.
- **Decision:** Mark V11 as the latest bounded-ready simulator for controlled generation and pilot work. Keep full-scale generation and formal training conditional on the data adapter, corpus-scale integrity/runtime measurements, independent RRUFF evaluation readiness, and a declared compute budget.
- **What changes now:** Small controlled experiments may select V11 explicitly and cite these acceptance artifacts.
- **What does NOT change:** V9 historical results/default behavior, frozen datasets/splits/checkpoints, and the fact that the 154,975-record library contains structures rather than spectra.
- **Status:** V11 BOUNDED ACCEPTANCE PASS / FULL-CORPUS GENERATION NOT YET VALIDATED.
- **Relevant implementation:** [V11 simulator](../xrd_robustness/src/xrd_robustness/simulator_v11.py), [V11 config](../xrd_robustness/configs/simulation.v11_tch_pseudo_voigt.json), [acceptance script](../xrd_robustness/scripts/accept_simulator_v11.py).
- **Machine-readable evidence:** [official acceptance rerun](../xrd_robustness/reports/simulator_v11/acceptance_rerun_20261103.json) and [154,975-library sample](../xrd_robustness/reports/simulator_v11/merged_154975_sample_20261103.json).
