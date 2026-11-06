# RRUFF real-domain evaluation: 1030 primary + 19 challenge cases

> **Superseded protocol.** The 1030 primary proposal and its 19-case list are historical. The [RRUFF-Cu1011 freeze](RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md) governs formal scoring. The historical 19 are distinct from the 19 explicit-Mo records in the later source audit.

**Owner decision date:** 2026-11-04
**Status:** Evaluation cohort membership selected by source metadata; FINAL TEST FREEZE PENDING label/provenance/wavelength/axis audit. No model predictions have been run.

## Final intended roles

| Track | Count | Selection based on original files | Interpretation |
| --- | ---: | --- | --- |
| **Primary RRUFF-1030** | **1030** | RAW/DIF same variant ID; valid six lattice parameters; numeric RAW spectrum; RAW description not explicitly calculated; RAW 2theta coverage >=30 degrees; no *explicitly described* additional phase | **Single-phase-oriented real-domain seven-crystal-system benchmark** (Accuracy, Macro-F1, ECE, confusion matrix and all seven per-class recall/F1). “No explicit mixture” does not prove fully single-phase. |
| **Challenge A: declared mixtures** | **15** | Otherwise passed the above metadata checks, but RAW diffraction sample description reports a second phase/impurity/contamination | **Qualitative/diagnostic case series** for applicability limits in multi-phase real measurements. No single-phase classifier phase-decomposition claim; distinguish known target crystal system from mixed pattern. |
| **Challenge B: short measured angular range** | **4** | Passed other source/label filters but 2theta coverage less than 30 degrees | **Qualitative/diagnostic case series** for restricted measurement windows / incomplete information. |

Sets are disjoint: **1030 + 15 + 4 = 1049** original metadata-candidate RRUFF variants, all different base RRUFF IDs. Never move cases between groups based on classification performance. Neither challenge group contributes to the primary Macro-F1/ECE denominator; never merge the two challenge mechanisms without stratification.

Historical RRUFF-70/301/350/371 protocols are **retired from future formal evaluation** by owner instruction; historical experimental results and data remain in place for scientific traceability. Early RRUFF-910 and RRUFF-1045 were *candidate milestones* in this protocol's design, not current benchmark definitions.

## 2026-11-04 owner amendment: screen the 15 mixed-pattern cases using Lee (2023)

**Decision rule from Lee et al., *Advanced Intelligent Systems* (2023), DOI 10.1002/aisy.202300140:**

```text
impurity_peak_ratio = max(baseline-corrected, attributed impurity-phase reflection)
                    / max(baseline-corrected, attributed main-phase reflection)
Exclude from relatively-pure evaluation only if ratio > 0.10.
```

The strict **greater-than** threshold, not >= 0.10, is from Lee's discussion of **Ex_dataset_1 (52 self-measured commercial powder specimens)**. Lee's **RRUFF Ex_dataset_2** instead used a different noise/background cutoff (remove top 40% by low-angle 5–8 degree intensity standard deviation). **Do not incorrectly cite Lee as having applied the impurity 10% rule to its RRUFF dataset.** Our use on 15 RRUFF samples is an explicitly **adapted** policy.

Implementation/pre-registered decision before any model predictions:

1. For each of the 15 pre-identified RRUFF variants, identify observed XRD main-phase diagnostic peaks and second-phase diagnostic peaks (from the actual measured RAW profile, using full DIF/reference structures, instrumental wavelength/axis alignment, and background correction). Quantify each phase's observed highest attributable peak height on a consistent intensity scale.
2. **Lee-pass:** verified ratio <=0.10: flag as `minor_impurity_lee_acceptable` and eligible for *source-based review* as a relatively-pure sample. It is **not automatically added to the frozen 1030** without a clearly versioned, pre-inference cohort amendment.
3. **Lee-fail:** verified ratio >0.10: flag as `substantial_secondary_lee_rejected`; keep as a prespecified difficult mixed-phase challenge example, never use for headline single-phase metrics.
4. **Unknown:** if secondary phase is unidentified, no suitable reference exists, or peak overlap prevents unique attribution: keep in separately flagged challenge/uncertain sample pool, do NOT force a pass/fail classification or infer the ratio from a composition weight fraction.
5. The four separately selected limited-2theta challenge cases remain unchanged. Do not use *model prediction outcomes* to choose Lee-pass/fail labels. Report all 15 original case IDs and their triage disposition to avoid hidden post hoc exclusion.

**Updated source-only peak attribution status (2026-11-04):** The 15 original RAW patterns were examined against main- and named secondary-phase DIF reflection positions, with background correction and three smoothing settings. **Seven** have strong attributable impurity markers above 10% of the *entire* observed profile maximum (conservative evidence for Lee rejection). **Two** have diagnostic ratios of about 7.0% and 7.6%, but cannot yet be certified as Lee passes because some secondary reflections may overlap the primary. **Six** remain Unknown because phase identity or peak separation is insufficient. Do not confuse this lower-bound measured-profile statistic with the exact independently deconvolved Lee phase-maximum ratio. No Test/model predictions accessed. Full 15-ID results and QA: [RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md](RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md). Private CSV SHA256: 621453ac1ea334b352f97b991d90c18dd85d1c06f42aeb88b34d71cf6611b3e6. The 1030 main and four short-range samples remain unchanged.

Do NOT substitute 4%, 13%, 14 wt% phase mass fractions for peak-height ratios, since scattering factors, texture, structure factors and overlapping reflections change intensity.

## Exactly what the challenge cases can establish

After the trained model and preprocessing are frozen, run **the same unmodified model once** on all 19 predefined cases. Report each case's sample ID, known target label and any ambiguity, seven-class probabilities, predicted label, confidence, original measured range/phase description, and plotted spectrum. Include **all 19** in the supplementary diagnostic table; if selecting a smaller number for figures, preselect them by material/measurement characteristics, not by favorable predictions.

These cases can illustrate success, failure, uncertainty, misleading confidence and limits of single-crystal-system prediction under mixed phases or truncated 2theta. They **cannot** establish multi-phase phase separation or identify all constituents from a single predicted crystal-system class.

Reference framing: Ito et al. (2026), *Enabling single-observation decomposition of multi-phase X-ray diffraction patterns via generative deep learning*, npj Computational Materials, DOI [10.1038/s41524-026-02087-w](https://doi.org/10.1038/s41524-026-02087-w), separates quantitative synthetic/real mixtures from illustrative experimental mixed-phase examples. Our analogy is *evaluation presentation and problem boundaries only*, **not** equivalent method or task: PhaseDifformer decomposes mixtures, ours is a seven-system single-label classifier. Likewise Liu et al. (2026), *A Unified preprocessing framework for high-throughput diffraction pattern analysis*, DOI [10.1038/s41524-026-01993-3](https://doi.org/10.1038/s41524-026-01993-3) analyzes 4D-STEM preprocessing, a different diffraction modality and task. Do not conflate their metrics or experiments with PXRD classification.

## Local private lists and reproducibility

Local folder: `E:\AI4science\_local\rruff_benchmark_prospective_20261104`

- `RRUFF_1030_PRIMARY_CANDIDATE_NOT_FROZEN.csv`: **1030**, SHA256 `1de8ac7d84c2c0526919a9a8f5924b9d72a8fea0a7cfc8e730007f242c838b99`.
- `RRUFF_19_HARD_CASES_NOT_FROZEN.csv`: **19**, SHA256 `d955b92f20a26f7364efd80633ae1215166a49bec965747a2221bc021f38bed7`.
- `RRUFF_1030_PLUS_19_OWNER_PROTOCOL_DRAFT.json`: role separation, 1030 class distribution, per-case flags, source manifest SHA. No signal arrays uploaded to public Git.
- Earlier 1049/1045 source audit files retained unchanged.

Primary crystal-system counts: cubic 120, hexagonal 82, tetragonal 46, orthorhombic 217, triclinic 97, monoclinic 338, trigonal 130 (sum 1030).

## Freeze gates and post-HPO use

1. Audit original RAW measurement provenance, label quality (including recovered noncanonical space-group aliases), physical radiation/wavelength and 2theta resampling; document any missing values without selecting on model scores.
2. Confirm no parent duplication/label conflict and finalize inclusion, preprocessing and source hashes. If critical source failures arise, record a prospective protocol amendment **before any predictions** rather than quietly changing the 1030 denominator.
3. **Do not inspect RRUFF model results during V11 HPO, architecture selection, or training-seed tuning.** Freeze model checkpoint/hyperparameters first, then evaluate primary 1030 and all 19 challenge cases according to this prespecified split.
4. Report results honestly even if challenge samples fail. XQueryer/Bin Cao 1003 is a different source snapshot/cohort: literature comparison is **not same-exact-test-set ranking** unless author IDs are independently reproduced.

**Research-history significance:** Initial 910 was over-restrictive due to software space-group string compatibility. 139 recovered aliases -> 1049; applying Cao's published 30-degree minimum -> 1045; owner chose 15 explicit mixtures to join the 4 insufficient-window spectra as distinct **challenge demonstrations**, leaving 1030 primary. This is a role assignment based on experimental metadata, not cherry-picking model outcomes.
