# RRUFF-Cu1011 — final source-selection freeze and AlphaDiffract 2026 comparison

Date: 2026-11-04. **Decision: source membership and preprocessing for the RRUFF-Cu1011 primary holdout are FROZEN BEFORE model inference or RRUFF scoring.** This does not freeze a future trained checkpoint. No sample can be selected or removed later based on prediction correctness.

## What the original AlphaDiffract 2026 paper actually did

Primary source: Nina Andrejevic et al., *AlphaDiffract: Automated Crystallographic Analysis of Powder X-ray Diffraction Data*, arXiv:2603.23367 (2026-03-24), Methods §5.1 and Tables 1 and 4. https://arxiv.org/pdf/2603.23367

The published RRUFF curation numbers are:
- 1,362 **background-corrected** RRUFF powder diffraction profiles, plus 2,901 DIF files.
- 2,572 DIF with essential cell/SG/wavelength information; 1,880 successfully parsed into pymatgen lattices; 1,867 checked for crystallographic symmetry and cell volume.
- 837 had a corresponding experimental PXRD file; 745 passed DIF-versus-PXRD **crystal-system AND unit-cell parameter** cross-validation.
- 734 remained after conversion of angular positions to the model's 20 keV radiation wavelength and exclusion of missing data in the converted measurement window.
- **734 is the paper's RRUFF crystal-system and SG classification count**, and only 240 with full atom positions entered the regression subset.
- **59 of its 734 classification sources (8.0%) are calculated powder patterns from single-crystal data**, intentionally included by the authors.
- The paper uses RRUFF curator-provided background-corrected profiles (not our uncorrected XY_RAW), then Bragg wavelength conversion to **20 keV, 5–20° with 8,192 model bins**, whereas our V11 trained grid is Cu Kα effective 1.54184 Å, **10–80°, 0.02° with 3,501 model bins**.
- The paper's quoted RRUFF crystal-system **81.74 ± 0.78%** is from a **ten-model ensemble**, trained using ICSD+Materials Project. The publicly released Materials-Project-only single model is a different result. Do NOT directly compare the reported 81.74% against a different-identity 1011-source model accuracy as if both share identical Test cases.

This original-paper evidence SUPPORTS RRUFF as a legitimate out-of-domain classification test, confirms the need for matching source cell/space group provenance and preventing missing angle coverage, and confirms that noncanonical SG settings are a real RRUFF issue. It does NOT require us to reproduce their particular 734 sample IDs, background-corrected source files, 20-keV instrument setting, inclusion of simulated profiles or complete-structure regression filters: our research target is seven crystal systems on true RAW source spectra.

## Why our source selection is specifically 1011 (not 734, 1003, 1032, or 1034)

The owner-selected, score-blind data-cleaning history is preserved:
retired RRUFF-70/301/350/371 → 910 (over-strict software-alias exclusions) → 1049 (recover 139 valid symmetry aliases) → 1045 initial observation width screen → 1030 excluding all 15 explicitly declared mixtures → 1032 adding two source-evaluated minor-impurity cases → 1034 adding two more with explicit unresolved 10%-impurity flags → **1011 Cu-compatible complete-V11-measurement source benchmark**.

The actual 1034-original-source physical audit discovered that a homogeneous Cu Kα test cannot honestly include:
- **19** experimental RAW sources **explicitly using Mo radiation**, of which **11** misleadingly have a Cu-wavelength *calculated* DIF companion: not physically Cu measurements and cannot be directly stacked on the Cu native angular grid.
- **3** otherwise Cu-compatible profiles that end at ~60°/70° rather than measuring all 10–80° (do not fill unmeasured 60–80° with fake values).
- **1** Harmotome 232-point irregular peak list rather than a dense continuous powder measurement.

**1034 = 1011 main + 19 Mo separately identified + 3 Cu partial-window challenges + 1 sparse quarantined.** All are retained in the audit, none excluded after seeing model scores.

Each of the 1011 retained has original RRUFF ID, original XY_RAW member, paired main DIF, same specimen variant, source sample ownership, SHA-verified files and a seven-system label consistent with the reference space-group family. Every retained RAW has full continuous measured 10–80° interval and valid V11 3,501-bin interpolation. The preprocessing fixes isolated numeric-source errors **without changing original ZIP bytes**; 19 isolated theta typos repaired in derived arrays, one duplicate coordinate averaged, scientific-notation counts parsed, one nonphysical negative-angle line removed from a derived array. Negatives clipped, no background subtraction, max normalized AFTER interpolation; all 1011 arrays are finite, nonnegative, 1011×3501, have maximum 1 and complete observed-bin masks. Separate 23 records are not silently padded or discarded.

Primary seven-class counts: triclinic 97, monoclinic 334, orthorhombic 211, tetragonal 45, trigonal 129, hexagonal 76, cubic 119. Preserve RRUFF raw hexagonal-axes notes for trigonal SGs. Four owner-selected weakly mixed examples retained with quality flags, including Rutile/Hematite R040049-1 and Actinolite/Chlorite R040064-1 whose *strict* Lee >10% impurity peak status was NOT proven. Do not claim 1011 certified absolutely single-phase.

## Reporting cohorts

Headline zero-shot seven-system top-1 Accuracy uses the complete frozen **RRUFF-Cu1011 (n=1011)**. Primary Macro-F1 and ECE use those same IDs. Report separate diagnostics or sensitivity analyses under their own cohort names and denominators.

The earlier **19-case qualitative list** (15 declared mixed/contaminated plus four short-range candidates) belongs to the superseded [RRUFF-1030 protocol](RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md). The 19 explicit-Mo records in the later 1034-source audit are a distinct group. The old case list is preserved separately. If reused for case studies, reconcile its IDs against Cu1011 and use the same frozen checkpoint with a prespecified input protocol. A frozen primary ID is counted once in Cu1011, and no diagnostic result is pooled with primary metrics. RRUFF-70/301/350/371 remain historical evidence.

## Gates before formal model scoring

Formal scores remain sealed. Complete and preserve evidence for all four gates before any RRUFF inference:

1. **Measurement provenance and wavelength sign-off.** For every frozen ID, record the source evidence for experimental RAW provenance and Cu compatibility, distinguishing explicit metadata from inference based on the paired DIF and peak positions. Resolve or explicitly accept every remaining evidence tier. An explicit Mo RAW record cannot be treated as Cu because its paired DIF is calculated at Cu wavelength.
2. **Label and exception sign-off.** Verify the ordered seven-system labels and checkpoint class-index mapping. Review all 134 noncanonical SG flags, 34 RAW–DIF cell discrepancies, and retained mixture flags; record each unresolved limitation and the owner disposition. Keep cell discrepancies as transparent quality flags rather than using future scores to remove cases.
3. **Frozen input reproduction.** Rebuild the ordered 1011 × 3501 array from the source audit and verify the manifest and input SHA-256 values, full measured 10–80° masks, logged source-axis repairs, interpolation without padding, negative clipping, retained background and post-grid max normalization. Run the actual frozen-input preflight and retain its passing receipt; prior synthetic-fixture tests do not sign off the private benchmark bundle.
4. **Model and evaluation-contract lock.** Finish HPO/model selection using synthetic validation only; record the selected checkpoint SHA-256 and selection evidence. Freeze preprocessing/evaluation code and the scoring contract before inference: zero-shot means no labeled RRUFF training, adaptation or selection; run the primary checkpoint once on all 1011 IDs; calculate top-1 Accuracy and Macro-F1 with the repository's seven-class `classification_metrics`, and ECE from softmax probabilities with 15 equal-width bins. Record the evaluation commit, metric definitions and checkpoint hash in the scoring receipt. No diagnostic cohort enters these primary metrics.

Formal scoring is authorized only after all four gates have auditable closure records. Do not inspect or generate formal model scores before that point.

### CPU input preflight (no checkpoint required)

Run from the repository root with NumPy installed:

```bash
PYTHONPATH=xrd_robustness/src python -m xrd_robustness.evaluation.rruff_cu1011 \
  --manifest /path/to/RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_20261104.csv \
  --inputs /path/to/RRUFF_1011_CU_FULL_10_80_DENSE_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz
```

The loader checks the two frozen SHA-256 values, row order, class counts and model class indices, all 3501 observed-bin flags per spectrum, and finite nonnegative float32 inputs with unit row maxima. Its pass receipt covers input integrity. The raw-source audit separately establishes how the coverage flags and resampling were produced. The eventual scoring entry point should call `load_frozen_inputs` directly.

The loader was exercised with synthetic fixtures. The frozen private CSV/NPZ and per-record source evidence were unavailable in the execution environment, so this run cannot sign off the actual input bundle or the wavelength and label exceptions.

## Additional AlphaDiffract-inspired cell cross-validation performed across ALL 1011

Following AlphaDiffract Methods 5.1, we cross-checked each original experimental RAW cell header against its source-matched DIF reference's six lattice parameters, preserving individual failure details:
- **758**: a/b/c relative differences each ≤0.1%, and α/β/γ absolute differences each ≤0.1°.
- **219** more: a/b/c relative differences each ≤1%, and α/β/γ differences each ≤1°.
- **34**: larger source RAW–DIF cell parameter differences, flagged. Some may represent different conventional cell settings or different experimental vs reference refinements; this is NOT independently resolved or evidence that their seven-system family labels are wrong.

This is our source-header versus reference-cell numerical cross-check, NOT an exact replication of AlphaDiffract's Niggli reduction, atom-coordinate symmetry validation, or full lattice-refinement matching. Our 1011 are a *crystal-system classification* holdout, not a clean enough dataset to advertise all 1011 as strict lattice-parameter regression ground truths. The 34 carry explicit quality tier and remain in the primary set rather than being conditionally selected by model accuracy. If desired, the 977 cases without major cell mismatch may be reported as a **predeclared secondary sensitivity analysis**, never substituted for the 1011 main accuracy.

All 34 cell discrepancy IDs: R040137-1, R040166-1, R040185-1, R050051-1, R050078-1, R050082-1, R050144-1, R050279-1, R050289-1, R050360-1, R050485-1, R050514-1, R050515-1, R050527-1, R050548-1, R050614-1, R060015-1, R060021-1, R060034-1, R060044-1, R060052-1, R060114-1, R060168-1, R060400-1, R060402-1, R060406-1, R060483-1, R060593-1, R060683-1, R060912-1, R060913-1, R060920-1, R061009-1, R060215-1.

The 134 nonstandard SG spellings in the 1011 were source-family-matched and flagged B evidence; none gave a direct crystal-system contradiction in the project audit. Original experimental RAW Cu wavelength is often not explicitly listed: Cu compatibility is inferred from matched DIF and diffraction peak locations, not a separate instrument certificate.

## Comparison to our chosen paper competitors

- **Bin Cao / XQueryer**: 1003-source RRUFF test set; similar task and scale, **different specimen IDs and source snapshot** from our 1011. No claim of identical-test leaderboard.
- **Lee (2023)**: 10% impurity strongest-peak ratio came from its 52 commercial-powder Ex_dataset_1, NOT Lee's RRUFF Ex_dataset_2 (which used a separate low-angle noise selection). Our inclusion of borderline samples was an **adaptation** with uncertainty markers.
- **Salgado / NPCNN**: 908 RRUFF sample real-domain classification background; again not an identical test set.
- **AlphaDiffract (2026)**: 734 post-curation RRUFF classification sources (including 59 calculated), after more stringent symmetry/lattice field filtering and an entirely different 20-keV input protocol. Their 81.74% is a contextual external benchmark only.

Cross-paper context is valid; strict comparative accuracy requires reevaluating relevant methods on the exact same 1011 with the same real-domain/no-fine-tuning restrictions and model-adapted spectral grids.

## Immutable decision and evidence files (private source, GitHub public protocol)

The source snapshot and source-only benchmark membership are FROZEN; the future checkpoint, model selection and RRUFF metric evaluation are NOT done.

Private E:/AI4science/_local/rruff_benchmark_prospective_20261104/:
- RRUFF_1011_CUKA_MAIN_SOURCE_PRELOCK_20261104.csv — exact ordered 1011 IDs/labels/source: SHA256 **75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37**.
- RRUFF_1011_CU_FULL_10_80_DENSE_V11_SOURCE_PREPROC_NOT_FROZEN_20261104.npz — exact 1011×3501 source-array bytes: SHA256 **19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179** (filename historically says NOT_FROZEN but now made source-frozen by the separate owner record; original file remains untouched).
- RRUFF_CU1011_PRIMARY_SELECTION_FREEZE_20261104.json — freeze metadata and SHA256 **d258e3f85506e91867e2d9aebd73b77e2f777636bc6a8b722ebe28bf52129455**.
- RRUFF_1011_ALPHA_DIF_RRUFF_CELL_CROSSCHECK_20261104.csv and JSON — all 1011 six-cell source comparisons.
- RRUFF_1011_ALPHA_DIF_CROSSCHECK_WITH_QUALITY_FLAGS_20261104.csv — explicit quality flags, SHA256 **e74e0fbfb1544c1e561880ea6682e48fdcb337d07114c0e174d9c0973b3e4243**.
- check_cu1011_alpha_cell.py and freeze_cu1011_after_alphadiffract_comparison.py — reproducible source-only audit.

Research-history reason for the change: initial cleaning was too strict for valid alternate crystallographic notation, whereas new physical inspection was necessarily strict for actual Mo vs Cu radiation and missing measured angular domain. We corrected implementation errors rather than discarding sources, then excluded only genuinely non-compatible measurement conditions from the main cohort. The benchmark membership was finalized BEFORE any model performance feedback.

**Formal manuscript-safe description:** We constructed a held-out real-domain seven-crystal-system benchmark from 1011 source-traceable RRUFF original powder-diffraction patterns compatible with the training simulator's Cu Kα 10–80° measurement window. We preserved all source IDs, variant provenance and lattice label evidence. All inputs are measured over the full model window, deterministically resampled and max normalized. Twenty-three of 1034 prospective candidates were assigned to separate radiation, truncated angular-coverage and sparse-format groups rather than mixed into the Cu-domain benchmark. This source cohort was frozen before any model evaluation. Noncanonical SG notation and RAW–DIF cell-parameter differences are retained as explicit quality caveats; published RRUFF results from other papers are contextual comparisons unless identical-sample testing is performed.
