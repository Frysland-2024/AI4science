# RRUFF real-domain evaluation: 1030 primary + 19 challenge cases

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
