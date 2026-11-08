# RRUFF mixture screening: Lee 2023 source-peak audit, 2026-11-04

**Owner rule:** apply Lee et al. (2023) 10% impurity-to-main XRD **maximum peak intensity** threshold to 15 previously identified mixed/contaminated RRUFF examples, using original experimental RAW spectra and published/locally available DIF references. This is an explicitly **adapted** rule: Lee applied it to their own 52 commercial powders (Ex_dataset_1), not to the RRUFF dataset (Ex_dataset_2, noise screening).

Source: https://doi.org/10.1002/aisy.202300140

**Research result: 7 source-supported high-ratio samples; 2 tentative low-ratio samples; 6 Unknown.** No model inference, HPO, or Test scoring used. Main RRUFF-1030 and four short-window challenge cases unchanged.

## How the source-only screening was performed

- Used the existing RRUFF XY_RAW.zip original experimental patterns and matching DIF.zip main-phase reflections, plus named second-phase DIF references. DIF is calculated/structure-based reference, **not** a second observed experiment.
- Calculated baseline-reduced measured peak heights and matched observed diagnostic 2theta peaks to reference reflection positions, checking whether main-phase reference peaks overlap. Three background/smoothing conditions: rolling 10th percentile (201, 301, 401 points) and Gaussian sigma (1.5, 2.5, 3.5 bins) on the 0.01 degree grid.
- For clear impurity-only markers, the conservative statistic is **measured impurity-marker peak height / strongest peak in the ENTIRE experimental spectrum**. Because the strongest main-phase reflection cannot exceed the whole-spectrum maximum, a clearly attributed marker >10% supports rejecting the specimen under Lee. This is a **conservative lower-bound proxy**, NOT the exact fully separated Lee impurity/main ratio.
- For candidate ratios below 10%, other impurity peaks may be hidden under main peaks: NOT a certified Lee pass. All identified markers had diagnostic SNR >5, verified from high-frequency noise. Two nearby observed peaks at 26.48 and 26.73 degrees for Bikitaite/quartz were explicitly confirmed as distinct.

## Seven strongly supported Lee-reject cases

| RRUFF variant | Main / impurity | Diagnostic measured 2theta | Conservative impurity/total maximum | Sensitivity range |
| --- | --- | --- | ---: | ---: |
| R040063-1 | Actinolite / talc | 9.51 degrees | 100% | 100% |
| R040067-1 | Amblygonite / wavellite | 10.55 degrees, also 10.23 | 28.7% | 28.0–29.4% |
| R060032-1 | Bikitaite / quartz | 26.73 degrees, separated from primary 26.48 | 100% | 100% |
| R060667-1 | Cervantite / quartz, plus romeite | 26.66 degrees | 51.8% | 48.2–60.1% |
| R060881-1 | Gartrellite / quartz | 20.88 degrees | 26.7% | 26.4–26.7% |
| R070168-1 | Borax / tincalconite | 20.30 degrees | 24.0% | 21.9–26.1% |
| R070725-1 | Julgoldite-(Fe2+) / quartz | 26.65 degrees | 100% | 100% |

**Important:** Values of 100% mean a particular impurity-marker peak is the highest entire observed peak. They do **not** mean 100 mass% impurity or that the measured phase ratio equals exactly 1.0.

## Two tentative low-ratio candidates (NOT verified Lee passes)

| RRUFF variant | Main / impurity | Diagnostic measured ratio to entire profile maximum | Remaining issue |
| --- | --- | --- | --- |
| R060215-1 | Polylithionite / trace corundum | 7.0%, sensitivity 6.3–8.0% | Corundum 35.17 degree peak overlaps a main reflection, so peak-height maximum of the separated impurity phase remains uncertain |
| R090054-1 | Dickite / quartz | 7.6%, sensitivity 7.60–7.66% | Quartz strongest diagnostic 26.66 degree reference corresponds to measured 26.69; check complete peak identity before a verified pass |

## Six Unknowns

| RRUFF variant | Main | Reason |
| --- | --- | --- |
| R040049-1 | Rutile | Hematite diagnostic peaks not reliably resolved; other hematite reference peaks overlap Rutile |
| R040064-1 | Actinolite | Chlorite polymorph/reference not specified |
| R050471-1 | Natrojarosite | Secondary phase not identified |
| R060125-1 | Schorlomite | Second andradite garnet shares major reflection positions, requiring physical separation/refinement |
| R060473-1 | Kutnohorite | Other carbonate phase not identified |
| R070680-1 | Rossmanite | Strong quartz peak at ~26.66 degrees overlaps primary at 26.60; weaker unique marker cannot bound impurity maximum |

## Versioning and next decision

No RRUFF model predictions were used in the entire screening. This is a source-only pre-inference audit, NOT a certified multiphase Rietveld refinement and NOT a completed Lee pass/fail decision for the remaining eight cases. Historical RRUFF 70/301/350/371 remain retired for future formal results. The primary 1030 unchanged, with all 15 and four truncated-window samples retained as separate prespecified cases; do not silently add provisional Lee-passes before independent phase confirmation and a versioned owner-approved cohort revision.

Inspect locally: E:/AI4science/_local/rruff_benchmark_prospective_20261104/

- RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_RESULTS.csv; SHA256 621453ac1ea334b352f97b991d90c18dd85d1c06f42aeb88b34d71cf6611b3e6
- RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_SUMMARY.json
- RRUFF_15_LEE_DIAGNOSTIC_SNR_AUDIT.json
- LEE15_SOURCE_PEAK_DIAGNOSTIC_FIGURES/ (15 RAW/DIF overlaid figures)
- lee15_attribution_audit.py, lee15_snr_audit.py, render_lee15_diagnostics.py (repeatable local source-only audit)

Scientific limitation: source profile provenance/wavelength and reference peak attribution must be independently checked for borderline/overlapping mixtures; do not treat any below-threshold global-normalized marker as certified Lee passing.
