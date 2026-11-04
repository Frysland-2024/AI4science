# RRUFF-1034 source audit → RRUFF-Cu-1011 prelocked primary, 2026-11-04

**Audit completion state:** Original RRUFF source and V11 input ENGINEERING CHECK COMPLETED and independently rerun with identical file SHA. **Primary source/engineering cohort PRELOCKED at 1011; no trained model inference on RRUFF or Test, no scientific performance measured.** The project owner proposed RRUFF-1032 and asked to fully audit 1032/possibly 1034. This audit discovered physically meaningful differences that require splitting the prospective 1034 rather than treating all 1034 as identical Cu-laboratory powder XRD profiles.

## Main result: every original candidate accounted for

| Source-derived subgroup | Count | Planned evaluation treatment |
| --- | ---: | --- |
| **Cu-compatible source, dense RAW, complete 10–80° interval** | **1011** | **Recommended PRIMARY prelocked seven-crystal-system real-domain evaluation set**, 3501 V11 input points and matching SHA manifest. Cu radiation inferred from DIF and peak-position agreement when RAW does not explicitly state radiation. |
| Explicit **Mo radiation** in original RAW measurement description | **19** | **Separate Mo-domain conditional diagnostic**. Do not combine Mo spectra at native angles with V11 Cu training; optional Bragg-angle-converted diagnostic arrays are NOT physically equivalent to actual Cu-measured intensity curves. |
| Cu-compatible RAW with **incomplete upper angular range** | **3** | Separate partial-window OOD measurement challenges (Tremolite R150094-1 to 70°, Hydromagnesite R220007-1 to ~60°, Triploidite R240016-1 to ~60°). Do not invent unmeasured intensity from 60–80°. |
| **Sparse, irregular, 232-point XY_RAW** | **1** | Harmotome R070016-1 — quarantine as unsuitable for interpolation into a continuous 3501-point laboratory spectrum. Raw profile label alone does not make an irregular peak listing into a dense continuous measurement. |
| **Total** | **1034** | Every source accounted for; no sample removal based on predictions. |

**Important:** In the 19 explicit Mo RAW records, **11 have a matching DIF calculated reference that instead states Cu Kα 1.541838 Å**; only eight have Mo-reference DIF. Comparing Mo RAW angle positions to Cu DIF angles without a physical conversion is invalid. RRUFF original RAW describes “using Mo radiation”; do not infer actual experimental radiation from its paired DIF alone.

## Provenance and seven-crystal-system labels

- Local official RRUFF snapshot: XY_RAW.zip and DIF.zip. Each of the original **1034** candidate RAW and DIF source members was read and its SHA256 checked against the earlier frozen source inventory; exact sample-variant and base RRUFF IDs checked. **0 source-file SHA mismatch, 0 identifier mismatch, 0 direct seven-system space-group vs retained label conflict.**
- All 1034 have named RRUFF mineral, owner/source metadata, original status and a matching DIF diffraction reference. The 33 source status phrases that say “identification made only by X-ray diffraction” must not be misread as missing mineral confirmation. Source-only labels are reference-based and do not mean our project independently solved 1034 structures.
- **136 of the 1034** (including **134 of the Cu-1011**) use noncanonical DIF space-group spellings. Their seven-system **families** and the independent RAW crystal-system statements agree; retain symbol-family evidence flags instead of excluding on a pymatgen parsing limitation. A full independently standardized space-group-setting verification is a remaining evidence limitation.
- Trigonal DIF space groups often occur with RAW cell axes described as hexagonal. **130 records** in the broad 1034 (129 in primary 1011) are labeled TRIGONAL from the space group; hexagonal axes DO NOT justify relabeling them as the hexagonal crystal system.
- Primary CU-1011 classes: **triclinic 97, monoclinic 334, orthorhombic 211, tetragonal 45, trigonal 129, hexagonal 76, cubic 119**. All seven are represented.
- The two previously proposed minor-impurity inclusions, **R040049-1 Rutile + hematite** and **R040064-1 Actinolite + chlorite**, fall in this Cu-1011 group. They remain explicitly quality-flagged as NOT rigorously proven to pass the adapted Lee 10% maximum impurity/main peak rule. The earlier Dickite/quartz and Polylithionite/corundum source-audited inclusions are also preserved.

## End-to-end source parser and preprocessing audit

An initial pass uncovered apparent inconsistencies in 21 native source axes, 22 incomplete V11 windows, and eight Mo-wavelength DIF references. **These first-pass counts were provisional and have been corrected by inspecting the original source bytes.** Notably, ignoring scientific-notation intensities in some files falsely shortened the recorded measurement width (e.g. Hessite R060226-9, 5.55° first observed point was missed), and source line “-2009, 10” before the proper native data in Vladimirivanovite R130034-1 must not be treated as a physical -2009° measurement. We fixed the parser, not the source archive.

Versioned physical preprocessing for the main 1011:

1. Extract original numeric diffraction block only AFTER the RAW ##FILETYPE line and BEFORE ##END; accept decimal and exponent/engineering-scientific numeric notation.
2. Retain untouched source RAW/DIF ZIP bytes and per-member SHA. Repair **19** records with isolated x-coordinate typing/truncated-prefix errors deterministically from adjacent native sample spacings and log every original and reconstructed angle; average intensities at one duplicate native 2theta coordinate. A stray impossible negative-angle source value is excluded only from the derived array, with source file preserved. Do not sort/force an entire irregular sparse spectrum into a dense one.
3. Keep only source-consistent dense Cu-compatible RAWs that cover the entire measured **10°–80°** interval without any invented values. V11 model grid is **10°–80°, step 0.02°, 3501 points**; interpolate linearly on this axis within the observed measured interval.
4. Clip negative intensities to zero, **do NOT remove experimental background**, and **max-normalize AFTER interpolation onto the final model input grid** (not before; interpolating can lower the highest native-grid peak). No experiment-specific feature engineering or Test-derived tuning.
5. Verify **1011/1011** rows have finite, nonnegative 3501-point spectra, exactly normalized maximum of 1, FULL observed-bin masks, unique variant and base IDs, and source-matched seven-system labels in the exact trained-model index order: triclinic, monoclinic, orthorhombic, tetragonal, trigonal, hexagonal, cubic.
6. Re-execute source-to-array generation and its independent contract check. The Cu-1011 compressed input and source manifest regenerate with **unchanged SHA256**; see hashes below.

**Cannot infer independently the Cu Kα wavelength for every remaining RAW:** most RAW metadata provide no explicit instrument-wavelength header. Its source-matched DIF often states Cu Kα 1.541838 Å, and main reflection positions are consistent in representative cases, but that is an evidence-tier assumption, not a complete independent spectrometer certificate. Some low agreement examples (strong texture/poor signal/structure mismatch) remain flagged, not automatically discarded. This should be stated in any publication.

## Exact private artifacts and immutable checksums

Local evidence directory: E:\AI4science\_local\rruff_benchmark_prospective_20261104

**Prelocked PRIMARY candidate:**
- RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_20261104.csv — 1011 rows, each with source RAW/DIF file names/hashes, RRUFF ID, seven-class label and model label index, source/processing assumptions; **SHA256 75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37**.
- RRUFF_1011_CU_FULL_10_80_DENSE_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz — float32 shape (1011, 3501), observed mask all TRUE, correct label order; **SHA256 19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179**.
- RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_CONTRACT_20261104.json — complete preprocessing, labels, source proof and QA digest receipt.

**Complete 1034 source cross-check:**
- RRUFF_1034_CORRECTED_SOURCE_PHYSICS_AUDIT_20261104.csv — full 1034 row-by-row source wavelengths/quality/partition flags.
- RRUFF_1034_CORRECTED_SOURCE_AUDIT_20261104.json — immutable group counts, main and subgroup NPZ hashes.
- RRUFF_1034_RAW_THETA_TYPO_RECONSTRUCTION_20261104.json — local audit of every altered derived angular coordinate.
- RRUFF_19_MO_RADIATION_SEPARATE_PROTOCOL_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz — theoretical Bragg-equivalent Cu angle mapping diagnostic ONLY, not authentic Cu-measured intensity.
- RRUFF_3_CU_PARTIAL_10_80_DENSE_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz — partial angular data + explicit observation masks.
- RRUFF_1_QUARANTINE_SPARSE_IRREGULAR_XY_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz — no fabricated continuous spectrum.
- audit_rruff1034_source_physics_v2.py and finalize_rruff1011_source_prelock_contract.py — local, replayable source-only implementation. No original ZIP modified and no new root E:\AI4science directory created.

## What is actually frozen, and what is not

- The **source audit and the 1011 proposed Cu-primary input cohort have a cryptographic PRELOCK**: the input images/arrays/IDs and the preprocessing transform are fixed before any new model evaluation; all historical RRUFF-70/301/350/371 benchmark tracks remain formally retired. All earlier 910/1049/1045/1030/1032/1034 candidates and their experiment records remain available as historical evidence.
- **Do not** conflate a source/engineering prelock with external scientific validation of every source label or instrument wavelength: original RAW Cu wavelength inferred for many samples; **134** noncanonical B-tier space-group strings in primary 1011 remain canonical-setting-review flags. These do not invalidate the seven-family labels already checked, but qualify evidence strength.
- Held-out RRUFF **MODEL RESULTS are still fully sealed**. No official HPO, no RRUFF accuracy/F1/ECE, no locked simulation Test were accessed or executed. The exact checkpoint and HPO/model-selection policy must be frozen BEFORE scoring the 1011 primary and any separate Mo/partial-window diagnostic pools.
- **The old requested “RRUFF-1034 homogeneous Cu benchmark” is not technically defensible from this source snapshot**; the 23 non-main patterns need differentiated protocols. Bin Cao's 1003 RRUFF uses a different 2024 vintage and different sample IDs; **1011 is not an author-identical test set**, despite similar size.

## Research-development history for future application narrative

The owner prioritized an experimental real-domain benchmark with literature-comparable sample count and minimal arbitrary exclusions: retired 70/301/350/371 → reviewed entire official RRUFF ZIP → 910 too strict due to SG software aliases → 1049 candidates → applied Bin Cao observable cutoffs → 1045 → remove obvious mixtures to 1030 → recover two weakly contaminated to 1032 → investigated remaining 13 carefully → considered two more weakly contaminated to 1034 → **physical source audit distinguished 1011 directly model-compatible Cu full-window patterns from 19 Mo, 3 Cu-short-window, and 1 sparse entry**. Crucial lesson: scientific dataset cleaning must distinguish *arbitrary library parser exclusions* (to correct) from *measurement physics/input compatibility constraints* (to preserve). All decisions occurred BEFORE model results, with real measured spectra and uncertainty traceable to source.
