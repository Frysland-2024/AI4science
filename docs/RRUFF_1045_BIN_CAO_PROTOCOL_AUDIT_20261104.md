# RRUFF replacement and Bin Cao screening audit — 2026-11-04

## Current owner decision

RRUFF-70, RRUFF-301, RRUFF-350 and RRUFF-371 are **all retired** as future formal real-domain benchmarks for the V11 project. Their past raw files, reports, results, failures and research history remain preserved; do not erase or rewrite historical evidence. No previous sample set should be used for current headline scoring, model selection or Optuna HPO.

This supersedes previously stated intent to use only the preliminary RRUFF-910 set. The new goal is a larger independently curated REAL RRUFF evaluation cohort, frozen before final model scoring; no RRUFF model inference or Test access has been authorized.

## Why 910 was unnecessarily strict

The local RRUFF archives have 3,019 XY_RAW and 3,013 DIF members. The initial 910 candidates required direct parsing of a DIF space-group symbol by the installed pymatgen version. This software restriction was not a scientific data-quality requirement.

139 other records have same-variant RAW-DIF pairs and valid numerical spectra, but alternate/nonstandard SG spellings (e.g. P2_1/n, P2_1/a, Fm3m, Pa3, Cmca). Their symmetry-system families agree with the RAW non-hexagonal labels. Recovering these gives 1,049 *candidate* records, with 1,049 different base RRUFF IDs and seven-system coverage. These 139 are still provisional, pending an independent crystallographic setting/notation review.

## Bin Cao published-method eligibility audit

Bin Cao 2026 HKUST thesis, section 4.2.4: author downloaded the March 2024 RRUFF dataset, paired XY_RAW and DIF by RRUFF ID (2,088 matched entries), and filtered incomplete samples, including insufficient 2theta coverage (example <30 degrees) or missing lattice constants; 1,003 valid remained. Author source: https://www.researchgate.net/publication/405807468_Physics-Constrained_Learning_of_Crystal_Structures_and_Properties_from_Powder_Diffraction . Published XQueryer: https://doi.org/10.1093/nsr/nwaf421 .

We checked the original bytes of all 1,049 local candidate RAW and DIF files individually:

| Observable criterion | Pass |
| --- | ---: |
| Exact RAW-DIF RRUFF variant-ID pairing | 1049 / 1049 |
| Finite, physically positive lattice a,b,c and valid alpha,beta,gamma in DIF | 1049 / 1049 |
| RAW lattice a,b,c present | 1049 / 1049 |
| Numerical RAW spectrum present | 1049 / 1049 |
| RAW sample description not explicitly marked calculated/simulated | 1049 / 1049 |
| RAW and DIF byte SHA matches initial archive provenance | 1049 / 1049 |
| Recorded raw 2theta width >=30 degrees | **1045 / 1049** |

The four failing records, with 2theta coverage, are R060491-9 (29.64 degrees), R070519-9 (29.92 degrees), R100193-9 (24.02 degrees), R110126-9 (27.22 degrees).

**Outcome: 1,045 records pass the publicly reconstructible screening fields, NOT all 1,049.** We operationalized 30 degrees from the author's example; the original precise author sample IDs and any unreported screening rules have NOT been reconstructed. Our local archive is different from his 2024 snapshot, so 1045 versus 1003 is NOT an identical-cohort benchmark.

The 1045 provisional seven-system distribution is cubic 121, hexagonal 82, tetragonal 47, orthorhombic 218, monoclinic 344, trigonal 133, triclinic 100. Quality flags still require review: **137 of 1045** are SG-alias recovered labels, and **15 of 1045** have possible mixed-phase sample descriptions. “Not explicitly marked calculated” is NOT affirmative independent proof of measurement provenance.

## Private, inspectable evidence

All located under E:/AI4science/_local/rruff_benchmark_prospective_20261104/ (do not publish source archives):

- RRUFF_EXPANDED_1049_PROSPECTIVE_NOT_FROZEN.csv, SHA256 af46b914eacf95c541834bfa21f406f85d0fce29c7c5c3081149639ad31a819d.
- RRUFF_1049_CAO_EXPLICIT_FIELDS_AUDIT.csv + RRUFF_1049_BIN_CAO_CRITERIA_AUDIT.json, per-row criteria and reasons.
- RRUFF_1045_CAO_EXPLICIT_FIELDS_PASS_NOT_FROZEN.csv, SHA256 8dfeb7c5fad4f77613167c81a9002e20c638dbf5a01b6ffee710b4277a182c43.

**Status:** 1045 is the recommended eligible candidate cohort after *published explicit* checks, NOT frozen final Test. Review SG aliases, mixture warnings, wavelength/2theta transformations, experimental provenance, and deduplication; freeze exact source manifest, role flags and preprocessing before final model evaluation. Do not use results for model tuning. Preserve old 70/301/350/371 exclusively as historical records.

## Research-method evolution

The trajectory: earlier limited RRUFF 70/301/350/371 experiments → owner retired all four → broad RAW+DIF discovery produced 910 conservative candidates → removing software-only SG parsing exclusion yielded 1049 → applying Bin Cao publicly reconstructible quality fields resulted in **1045**. Main lesson: library parser strictness is not equivalent to scientific validity, while reproducing an author's sample count is not the same as reproducing their exact dataset.
