# Source-only deeper validation: two mild-impurity RRUFF cases (2026-11-04)

**Outcome:** Propose the RRUFF-1032 main cohort, by adding Dickite R090054-1 and Polylithionite R060215-1 to the existing RRUFF-1030 *candidate* cohort. **Not yet final Test frozen.** No model inference or metric used to make this source-only pre-inference decision. The other 13 declared mixtures remain outside the primary benchmark; the four short-2theta cases remain independently categorized.

## Source-level verification

Each original RRUFF XY_RAW sample and matching primary DIF was reloaded and its SHA256 checked against the prior manifest. All **6 quartz** and **13 corundum** reference DIF datasets use wavelength **1.541838 angstrom**, also used in the corresponding main DIF files. This verifies *calculated references*, not independent wavelength metadata in experimental RAW.

A main-phase-only strong peak is identifiable:
- Dickite: 12.41 degrees (main DIF exactly 12.41); closest quartz reference reflection across six DIF archives is 8.43 degrees distant.
- Polylithionite: 17.98 degrees (main DIF 17.95); closest corundum reference reflection across 13 files is 7.51 degrees distant.

### Dickite + quartz R090054-1 — high confidence

For each of six quartz references, three percentile-baseline/smoothing choices (windows 201/301/401, Gaussian sigma 1.5/2.5/3.5 bins), and four peak-position tolerances (0.10, 0.16, 0.22, 0.30 degrees), the strongest TOTAL measured signal near *any* quartz DIF reference reflection, divided by the independently observed Dickite 12.41-degree main peak, lies in **7.60%–7.66%**. Unlike the earlier 7.6% diagnostic-only result, this accounts conservatively for all listed impurity reflections, including those that may overlap main-phase peaks.

With the assumption of nonnegative incoherent powder intensities and correct source-reference alignment, the observed total signal upper-bounds the quartz contribution. Evidence tier: **high-confidence adapted Lee acceptance** (source upper-bound test). The formal original Lee quantitative peak ratio is not directly decomposed.

### Polylithionite + corundum R060215-1 — conditional acceptance

The strongest-corundum-reference peak at 35.17 degrees overlaps the calculated strong Polylithionite peak at 35.15 degrees. The TOTAL observed mixed peak / independent 17.98-degree Polylithionite strong peak is **9.51%–11.09%**, sometimes >10%; attributing this total to corundum would wrongly count main-phase signal.

Use independently observed corundum diagnostic markers (25.59, 43.38, 52.58, 66.56 degrees) to bound the corundum template's contribution at 35.17, using each source DIF reference's relative intensities. Across **13 corundum references x 3 baseline/smoothing settings = 39 cases**, the estimated strongest corundum contribution / independently observed main 17.98-degree peak is **7.08%–9.33%**. Worst case: inferred corundum 46.46 a.u. / main 497.80 a.u. = 9.33%.

**This is model/reference-template conditional, NOT an assumption-free measurement of separate phase heights**. Strong texture, a changed relative reflection-intensity distribution, overlapping peaks, or reference mismatch could move the actual Lee ratio over 10%. This sample may be included for a pragmatic real-domain benchmark with an explicit weak-impurity/conditional-estimate flag, but should never be reported as strict certification of the Lee threshold. Evidence tier: **medium confidence conditional**.

## Versioned private artifacts

All under E:/AI4science/_local/rruff_benchmark_prospective_20261104/:

- RRUFF_TWO_LEE_UPPER_BOUND_GRID_20261104.json — all six quartz references x three baselines x four tolerance checks (plus all corundum refs).
- RRUFF_R060215_CORUNDUM_OVERLAP_TEMPLATE_SENSITIVITY_20261104.json — 39 reference/template settings with worst 9.33%.
- RRUFF_TWO_LEE_WAVELENGTH_SOURCE_AUDIT_20261104.json — reference wavelengths, RAW/DIF SHA matches, main-only peak independence.
- lee2_full_ref_upper_bounds.py, lee2_corundum_overlap_anchor.py, lee2_wave_source_audit.py — reproducible local source-only scripts.
- **RRUFF_1032_PRIMARY_PROPOSED_LEE_ADAPTED_NOT_FROZEN.csv** — proposed primary 1032 unique parent IDs; SHA256 **341c16f973767254eabf6b12540269ccfb14dc67d319b76fefbe16163790759e**.
- RRUFF_1032_OWNER_PROPOSED_COHORT_AUDIT.json — class distribution and evidence tiers.

Resulting prospective primary seven-system distribution: cubic 120; hexagonal 82; tetragonal 46; orthorhombic 217; triclinic 97; monoclinic 340; trigonal 130. Historical RRUFF-1030/15/19 source manifests stay immutable.

## Scientific and reporting boundaries

Lee et al. (Advanced Intelligent Systems 2023, DOI 10.1002/aisy.202300140) originally used a >10% maximum impurity/main diffraction peak criterion for 52 *self-measured commercial powder samples*, **not** Lee's own RRUFF Ex_dataset_2. Application to our RRUFF samples is explicitly **adapted**.

The final project RRUFF cohort cannot yet be called FROZEN: source provenance, wavelength interpretation, RRUFF symmetry labels, and fixed resampling are still under audit. The two proposed inclusions must never be reversed based on future model predictions or scores. The new 1032 is not guaranteed identical to Bin Cao's RRUFF-1003 cohort. Historical RRUFF-70/301/350/371 were retired as current benchmarks by the project owner, but past evidence remains preserved.
