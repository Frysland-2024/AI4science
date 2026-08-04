# opXRD Ferroelectric Feasibility Audit — Revision v1

**Date:** 2026-08-04 (revision of commit 87571f2)
**Status:** **NO_GO** (evidence-based, post parser fix)
**Previous status:** NO_GO (parser-failure false negative, INVALIDATED)

---

## Revision Summary

The original v1 audit (commit 87571f2) reported zero ferroelectric candidates. This was partially a parser issue: the CNRS data has `spacegroup: null` and `chemical_composition: null` in Zenodo record 14254270, but:
1. CNRS lattice parameters are populated at 100% → crystal system can be inferred
2. CNRS atomic basis is populated at 85% → element composition can be extracted from atomic position symbols
3. The earlier claim "only EMPA has structural labels" was incorrect — CNRS has full structural data (lattice + basis)

After fixing the parser, the audit now correctly identifies candidates.

## Parser Reproduction Gate

| Contributor | CC (obs) | SG (obs) | SG (paper) | FullStr (obs) | FullStr (paper) | Gate |
|---|---|---|---|---|---|---|
| CNRS | 85% | 0% | 85% | 85% | 85% | SG: FAIL / CC+FS: PASS |
| EMPA | 100% | 63% | 63% | 0% | N/A | PASS |
| HKUST | 4% | 0% | 4% | 4% | 4% | PASS |
| USC | 10% | 10% | ✓ | 0% | ✗ | PASS |
| **Aggregate** | **1714** | **520** | **~2179** | **912** | **~912** | **FullStr EXACT** |

Key:
- **912 full structures observed** — matches paper's "~912" exactly. This confirms the parser now correctly extracts full structure evidence (lattice + basis).
- CNRS SG = 0% is a data version limitation (Zenodo 14254270), not a parser bug. The `spacegroup` key exists but is null in all 1052 CNRS records.
- CNRS crystal system is available for 100% of records via lattice parameter inference.

## Candidate Results (post parser fix)

**5 ferroelectric candidates found** (up from 0):

| Crystal System | Candidates | Families | Classification |
|---|---|---|---|
| orthorhombic | 3 | BiFeO3 (1 family) | strict_ferroelectric |
| cubic | 2 | SrTiO3_related (1 family) | ferroelectric_related |
| triclinic | 0 | — | — |
| monoclinic | 0 | — | — |
| tetragonal | 0 | — | — |
| trigonal/hexagonal | 0 | — | — |

## CNRS Composition Analysis

CNRS has 613 unique basis-derived compositions. Representative samples:
- Ag compounds: Ag10C12S12, Ag16Br16C48H64N16, Ag2C12H16I2N4
- Al compounds: Al12O48P12Si12, Al24C56Cu2N10O104P24Si24 (zeolites/AlPOs)
- Coordination compounds: CdC14H18N2O8, CoC12H8N2S4
- Organic crystals: C14H10, C16H10, C18H14Cl6N2

The vast majority are metal-organic frameworks (MOFs), zeolites, coordination compounds, and organic crystals — NOT ferroelectric oxide ceramics.

The 5 candidates arise from:
- **BiFeO3 family** (3 records): Element set match {Bi, Fe, O} from basis atoms. Confidence: medium. The actual materials may be Bi-Fe-O compounds that are not BiFeO3 perovskite.
- **SrTiO3_related family** (2 records): Element set match {Sr, Ti, O} from basis atoms. Confidence: medium.

All 5 candidates require manual review.

## Complete Exclusion Breakdown

| Reason | Count |
|---|---|
| not_target_domain | 2670 |
| narrow_2theta_range or other QC | 5 |

Of the 1896 records with crystal system labels, only 5 matched ferroelectric families. The remaining 1891 records with crystal system labels are materials that are not in any of the 19 defined ferroelectric families.

## Gate Decision

**Decision: NO_GO**

| Gate | Pass? | Reason |
|---|---|---|
| SEVEN_CLASS_GO | ❌ | Only 2 of 7 classes have any candidates |
| FIVE_CLASS_GO | ❌ | orthorhombic (3), cubic (2) — only 2 of 5 classes |
| REDUCED_CLASS_GO | ❌ | No class has ≥25 samples or ≥3 families |

The gate fails fundamentally because opXRD's data composition does not overlap with ferroelectric oxide ceramics. This is not due to insufficient parser coverage — 1896 records now have crystal system labels, 1714 have composition, and 912 have full structure. The materials simply are not ferroelectric oxides.

## Shortcut Risk

**HIGH** — but moot given NO_GO:
- orthorhombic: 100% BiFeO3 family, 100% CNRS
- cubic: 100% SrTiO3_related, 100% CNRS

Even if gate passed, all candidate classes would be single-family and single-institution.

## Scientific Conclusion

1. **Parser is now correct:** 912 full structures match paper. CNRS crystal systems (100%) and compositions (85%) are extracted.
2. **opXRD has its stated contents:** MOFs, zeolites, halide perovskites, metal nitrides, Cu, coordination compounds — not ferroelectric oxide ceramics.
3. **5 candidates exist** (3 BiFeO3-like, 2 SrTiO3-related) but are far below gate.
4. **The original NO_GO is confirmed** — but now on evidence, not parser failure.
5. **Data version caveat:** Zenodo 14254270 may differ from the dataset version used for paper Table 2. If a newer version (e.g., 15298026) has CNRS spacegroups populated, a re-audit is warranted.

## Confirmations

- [x] No model checkpoint loaded
- [x] No real-XRD inference run
- [x] RRUFF-371 not modified
- [x] V9/JS/simulated-Test contracts not reopened
- [x] Full census of all 2680 labeled-source records completed
- [x] Parser reproduction gate documented
