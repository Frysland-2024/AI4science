# 2026-11-04 · RRUFF remaining 13 declared mixtures: extended source-only audit

**Purpose.** After proposing RRUFF-1032 (1030 non-declared mixtures + two source-rechecked mild impurities), the owner asked for a complete recheck of the **remaining 13** originally declared multi-phase RRUFF records, before any real-domain model scoring.

**Outcome:** **7 source-supported impurity-marker >10% rejections, 2 probable significant mixtures not strictly proven by the adapted Lee ratio, 4 still Unknown, 0 newly verified Lee-passing entries.** The **proposed RRUFF-1032 candidate list remains unchanged**. All 13 remain outside the primary cohort. No trained-model predictions or held-out Test metrics were accessed.

## Screening definition and source caveat

Lee et al., Advanced Intelligent Systems (2023), DOI https://doi.org/10.1002/aisy.202300140, discard when **the maximum impurity-phase diffraction peak height exceeds 10% of the maximum main-phase peak height**. The authors applied this to their **52 self-measured commercial powders (Ex_dataset_1)**, **not** their RRUFF Ex_dataset_2 (which used a different low-angle background/noise filter). Our use on RRUFF is an explicit *adaptation*, not a reproduction of Lee's own RRUFF screening.

- We re-read original measured RRUFF XY_RAW and calculated main-phase and impurity-phase DIF references. For named secondary species, inspected available reference variants instead of selecting only one convenient reference; e.g. quartz 6 variants, andradite 13, hematite 5, wavellite 2, talc 2, tincalconite 1.
- Quantified phase-marker peak positions and empirical heights after 10th-percentile background subtraction and Gaussian smoothing, varied baseline windows **201/301/401** and smoothing sigma **1.5/2.5/3.5**. Checked whether main-phase reference peaks overlap. Considered native instrument 2theta and source phase descriptions.
- A source-supported secondary-only marker over 10% of the **whole observed spectrum maximum** is a conservative rejection signal because the main-phase maximum cannot exceed the whole observed maximum. This reasoning relies on accurate attribution of that peak to a non-overlapped impurity.
- If only a weak independent secondary marker is detected, **this does not certify Lee acceptance**: a stronger secondary peak can overlap a main peak. The source-derived peak intensities are neither phase mass fractions nor exact decomposed phase intensities.
- For unresolved phases, tested separate mineral-family DIF references and *exploratory* nonnegative two-phase peak-template fits (three Gaussian FWHM values, three common peak shifts, two relative DIF intensity exponents). Such approximate templates are **not Rietveld**; strong texture, extinction, secondary chemistry, coincidence and source shift can invalidate them. Automatic fitting was used as a consistency test, not a final Lee criterion.

## Seven samples with strong source-supported exclusion evidence

The ratios are **independently attributed impurity diagnostic measured peak / maximum whole-pattern measured peak**; these are conservative screening statistics, not the formal deconvolved Lee ratio.

| RRUFF variant | Source-identified impurity | Diagnostic peak / whole maximum | Source evidence |
| --- | --- | ---: | --- |
| R040063-1 | Talc (also chlorite reported) | 100% at ~9.51° | Source estimates 45% talc by sample composition; 9.51° observed strong talc marker |
| R040067-1 | Wavellite | 28.0–29.4% at ~10.55° | Multiple wavellite lines agree; 2 available wavellite DIF variants |
| R060032-1 | Quartz | 100% at ~26.73° | Resolved from neighbouring Bikitaite ~26.48° source peak, supporting quartz lines |
| R060667-1 | Quartz (also Romeite) | 48.2–60.1% at ~26.66° | Multiple impurity families named; additional quartz marker near ~20.88° |
| R060881-1 | Quartz | 26.4–26.7% at ~20.88° | Distinct independent line used, because quartz 26.66° overlaps main reflections |
| R070168-1 | Tincalconite | 21.9–26.1% at ~20.30° | Distinct matching 20.30°/25.90° reference lines |
| R070725-1 | Quartz | 100% at ~26.65° | Independently observable line and additional quartz markers |

**Do not** interpret a ratio of 100% as “100% impurity by mass”.

## Two probable significant mixtures — not strict Lee-certified rejections

| RRUFF variant | Evidence | Why still not certified |
| --- | --- | --- |
| **R060473-1 Kutnohorite** | Original diffraction has distinct strong main peak near 30.10° and a secondary peak near **30.79°**, the latter around **37.1–47.3% of whole-pattern maximum** under the tested baselines. Several dolomite/ankerite family reference variants support a nearby ~30.8° independent reflection; nonnegative template fits consistently prefer material in that family. | RAW source describes “a second carbonate phase” but gives **no exact mineral identity**. Dolomite/ankerite are chemically plausible reference hypotheses, not confirmed source phase labels; therefore the 30.79° peak's chemical attribution is conditional. |
| **R070680-1 Rossmanite** | RAW/source says quartz. Observed line ~26.64° is around 36% of global maximum but **overlaps Rossmanite main ~26.60°**. Independent quartz ~20.88° marker is only ~4.2–8.3% global. A quartz-template explanation of the strong overlapped peak is possible and two-phase NNLS finds >10% conditional contributions in a subset of improving fits. | Shared ~26.6° line cannot be uniquely separated by simple peak matching. The template-fit global quality was weak and depends heavily on quartz relative intensity and preferred orientation. Therefore do not report the raw mixed peak or model-predicted proportion as a measured Lee ratio. |

## Four Unknowns — different underlying reasons

| RRUFF variant | Evidence inspected | Reason no reliable pass/fail |
| --- | --- | --- |
| **R040049-1 Rutile + hematite** | Five hematite reference variants; independently observable hematite-like peaks only around **1.8–2.3%** of whole-pattern maximum. Source composition says **13% hematite by sample fraction**. Two-template fits sometimes suggest a small secondary contribution. | Stronger hematite ~54.15° reference overlaps rutile ~54.35°, preventing an assumption-free upper bound. The stated 13% composition is **not** Lee's diffraction intensity ratio. Cannot declare Lee pass from the weak independent lines alone. |
| **R040064-1 Actinolite + chlorite** | Source estimates ~4% chlorite by composition. Exploratory chlorite-family DIF (clinochlore, cookeite, amesite) matches measured ~6.28°/12.54°/18.82°/25.18° lines. The ~12.54° candidate marker ranges **7.1–10.6%** across processing and reference choices. | Exact chlorite polymorph was not reported and the apparent peak is borderline and sensitive to preprocessing. A family resemblance does not establish phase attribution; also 4 wt% is not 4% peak intensity. |
| **R050471-1 Natrojarosite** | Original raw specimen says only “includes another phase”; main Natrojarosite reference and extra observed peaks inspected. | Secondary phase **not identified** and no attributable reference spectrum. No defensible Lee ratio, regardless of extra peaks. |
| **R060125-1 Schorlomite + andradite** | Thirteen andradite reference variants; two garnet phases explicitly named in RAW. Both share many strong peak positions. Two-component NNLS intensity allocations vary dramatically, including near-collinear/unstable fits. | No independent per-phase maximum can be determined without substantial structural constraints/refinement. Both garnets may be cubic, but that does not satisfy a single-phase purity threshold. |

## Decision, limitations and reproducibility

**No newly certified sample should be added to RRUFF-1032 on these data.** Keep the seven source-supported, two probable and four Unknown **outside** the planned primary Test. This is not the assertion that all 13 physically violate the 10% Lee cutoff. Cases could be re-assigned only by a separately registered, source-only protocol amendment **before** any model results are used, with detailed evidence.

The original source archive's RAW wavelength metadata is not always explicit, and full two-phase quantitative Rietveld/Pawley refinement is not available for unnamed phases; thus this audit is the most comprehensive source-only cross-reference check under the currently available evidence, **not** a complete experimental phase-separation determination.

**Private reproducible evidence, not uploaded to GitHub:**
- E:/AI4science/_local/rruff_benchmark_prospective_20261104/RRUFF_13_LEE_20261104_SOURCE_SCREENING_RECHECK.csv (13 rows), SHA256 **59fec0bc1dc34d0b8e8c6795bdc7e2fbb129239e9a8904c29a883e799aabda30**.
- RRUFF_13_LEE_20261104_DIAGNOSTIC_PNG/ (13 original experimental RAW vs calculated main/secondary reference figures).
- RRUFF_REMAINING13_FULL_REFERENCE_DIAGNOSTIC_AUDIT_20261104.json (source-reference-variant details, 3 preprocessing settings).
- RRUFF_SIX_UNKNOWN_13_ADDITIONAL_SOURCE_BOUNDS_20261104.json (six hard cases, phase-intensity upper/proxy calculations).
- RRUFF_SIX_UNKNOWN_NNLS_TEMPLATE_SENSITIVITY_20261104.json (full parameter sweep, exploratory only).
- RRUFF_13_LEE_20261104_SOURCE_RECHECK_SUMMARY.json and scripts audit13_all_references.py, rruff_six_unknown_deep_bounds.py, rruff6_template_nnls_stress.py, rruff13_final_source_report.py.

**Project history:** User's evaluation-data decisions remain 70/301/350/371 retired → RRUFF-910 over-strict → 1049 recovered → 1045 published-method filtered → 1030 no-explicit-mixture → **proposed 1032** after two mild-impurity checks → remaining **13 re-examined, no defensible further inclusions**. No RRUFF model inference or headline scores have yet been performed.
