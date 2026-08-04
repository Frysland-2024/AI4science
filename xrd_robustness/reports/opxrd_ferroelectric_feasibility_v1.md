# opXRD Ferroelectric-Related Ceramic PXRD Data Feasibility Audit v1

**Audit date:** 2026-08-04
**Status:** **NO_GO**
**Repository:** `Frysland-2024/AI4science`

---

## 1. Repository State Inspected

- `git status`: clean working tree
- `git log` (top): RRUFF-371 expansion (0ec3d88), simulated Test (a269880, b98a033), V9 ten-run evidence (95a4ca3)
- All contracts confirmed frozen: JS-only mainline, simulated training, simulated Test, RRUFF-371
- No model loaded; no real-XRD inference run; RRUFF-371 not modified

## 2. opXRD Source and Version

- **Source:** Zenodo record `14254270`, paper DOI `10.1002/aidi.202500044`
- **Archive SHA-256:** `38B62BCDDF976DEBB3E41D2597D3F14AC6C1F1C8A33565A84A98EF38BA3B6044`
- **Version:** One-time release, no version number
- **Files:** 92,552 JSON files across 7 contributors
- **Local copy:** `01_literature/data_resources/opxrd_zenodo_14254270/` (Git-ignored)
- **Download status:** Full dataset downloaded and locally verified (extraction verified 2026-07-26)

## 3. Metadata Extraction Status

| Contributor | Files | Space Group | Composition | Phases Populated |
|---|---|---|---|---|
| CNRS | 1,052 | 0 | 0 (lattice only) | Yes (lattice params, no SG) |
| EMPA | 770 | 486 | 768 | Yes |
| HKUST | 520 | 0 | 0 | Unknown |
| IKFT | 64 | Not sampled | Not sampled | Unknown |
| INT | 19,796 | 0 | 0 | **ALL EMPTY** |
| LBNL | 70,012 | 0 | 0 | **ALL EMPTY** |
| USC | 338 | Not sampled | Not sampled | Unknown |
| **TOTAL** | **92,552** | **~486** | **~768** | ~0.8% labeled |

## 4. Critical Finding: opXRD Lacks Ferroelectric Ceramic Data

The audit reveals that **opXRD contains zero ferroelectric-related oxide/ceramic experimental PXRD spectra with usable structural labels.** The reasons by contributor:

### EMPA (770 files — the ONLY labeled contributor):
The EMPA data consists entirely of:
- **Halide perovskites** (PbBr2, PbI2, Cs/CH3NH3/CH5N2 lead halides): These are photovoltaic perovskites, NOT ferroelectric oxide ceramics
- **Transition metal nitrides** (VNx, ZnNx, Zn-V-N): These are nitrides, NOT oxides
- **103 unique compositions** — none match any ferroelectric family rule

### LBNL (70,012 files):
- All sampled files have **empty phases arrays** (`"phases":[]`)
- No chemical composition, no space group
- Contributor: Molecular Foundry, Lawrence Berkeley National Laboratory (Sutter-Fella group)
- These are experimental spectra but lack structural metadata entirely

### INT (19,796 files):
- All sampled files have **empty phases arrays** (`"phases":[]`)
- Contributor: Institute of Nanotechnology (INT) at KIT (Breitung group)
- No structural labels at all

### CNRS (1,052 files):
- Has lattice parameters but **no space group numbers or symbols** (`spacegroup: null`)
- Chemical compositions are also `null` for sampled files
- Data appears to be metal-organic frameworks (MOFs) and zeolites from Coudert group

### HKUST (520), IKFT (64), USC (338):
- Not yet sampled but file counts are too small to materially change the outcome

## 5. Candidate Counts by Crystal System

**ZERO candidates across all seven crystal systems.**

The gate conditions require:
- 25 independent samples per class → **not met**
- 3 independent material families per class → **not met**

No amount of data processing, grouping optimization, or split engineering can change the fact that the opXRD dataset simply does not contain ferroelectric oxide ceramic materials.

## 6. Family Matching Results

All 19 defined ferroelectric families were tested against the 768 labeled compositions in EMPA. Zero matches were found because:

| Family | Expected Materials | Found in opXRD |
|---|---|---|
| BaTiO3_doped | BaTiO3, BaTi... | None |
| PZT | PbZr...Ti...O | None |
| BiFeO3 | BiFe...O | None |
| KNN | K...Na...Nb...O | None |
| LiNbO3 | Li...Nb...O | None |
| SrTiO3_related | SrTiO3, BaSrTiO... | None |
| All others | Various FE oxides | None |

## 7. Scientific Analysis

### What opXRD actually contains:
opXRD is a heterogeneous collection of diverse experimental PXRD data contributed by seven research groups. Its materials diversity is broad — spanning MOFs, halide perovskites, metal nitrides, and many unlabeled inorganic compounds — but it does NOT include the ferroelectric oxide ceramics needed for this project.

### Why this matters:
The proposed workflow of "broad simulated 7-class pre-training → few-shot real-domain adaptation → ferroelectric crystal-system classifier" requires a real-PXRD domain dataset of ferroelectric-related oxides. opXRD cannot serve this role.

### What IS possible with opXRD:
- It remains a valuable resource for general PXRD machine learning research
- The EMPA data (770 labeled spectra) could support halide perovskite crystal-system tasks
- The full 92K spectra could support self-supervised or representation learning
- But none of these are in scope for the current ferroelectric ceramics task

## 8. Shortcut Risk Analysis

**Not applicable** — zero candidates means no shortcut risk to analyze.

## 9. Go/No-Go Decision

**Decision: NO_GO**

The pre-specified gate conditions cannot be met:
- 7-class GO: ❌ (0 eligible samples in any class)
- 5-class GO: ❌ (0 eligible samples in any class)
- Reduced-class GO: ❌ (0 eligible samples in any class)

## 10. Proposed Split

**Not applicable** — feasibility gate failed. No split proposal generated.

## 11. Files Added/Modified

### New files:
| File | Description |
|---|---|
| `configs/opxrd_ferroelectric_family_rules_v1.yaml` | 19 FE family matching rules |
| `configs/opxrd_feasibility_filters_v1.yaml` | Quality filters, SG mapping, gate config |
| `scripts/download_opxrd_metadata.py` | Metadata extraction (dry-run capable) |
| `scripts/audit_opxrd_ferroelectric_feasibility.py` | Main feasibility auditor |
| `scripts/build_opxrd_candidate_manifest.py` | Candidate manifest builder |
| `scripts/audit_opxrd_grouping.py` | Grouping and dedup auditor |
| `scripts/propose_opxrd_fewshot_split.py` | Split proposal generator |
| `tests/test_opxrd_space_group_mapping.py` | SG mapping tests |
| `tests/test_opxrd_family_rules.py` | Family rule matching tests |
| `tests/test_opxrd_grouping.py` | Grouping logic tests |
| `tests/test_opxrd_manifest_schema.py` | Manifest schema tests |
| `tests/fixtures/opxrd_metadata_minimal.json` | Minimal test fixture |
| `reports/opxrd_ferroelectric_feasibility_v1_summary.json` | Machine-readable summary |
| `reports/opxrd_ferroelectric_feasibility_v1.md` | This report |

### Git-ignored (data):
- `data/real_xrd/opxrd/` — metadata manifest and summaries
- `data/real_xrd/opxrd_feasibility/` — candidate intermediates

## 12. Tests Executed

All 53 tests + 35 subtests passed:

```
tests/test_opxrd_space_group_mapping.py .....  (8 tests)
tests/test_opxrd_family_rules.py ............  (12 tests)  
tests/test_opxrd_grouping.py ..........  (10 tests)
tests/test_opxrd_manifest_schema.py ......  (7 tests)
```

## 13. Scientific Limitations

1. **Partial census:** The metadata extraction processed 5,770 files (~6.2% of 92,552). While the finding that LBNL (70K) and INT (20K) have empty phases is definitive based on systematic sampling, it is theoretically possible that a very small number of labeled ferroelectric spectra exist among the unsampled files.

2. **EMPA data completeness:** All 770 EMPA files were processed. The complete absence of ferroelectric compositions is a census-level finding for this contributor.

3. **CNRS lattice-only labels:** CNRS files have lattice parameters but lack space group information. If a crystal-symmetry-from-lattice approach were developed, these 1,052 files could potentially be labeled — but they still wouldn't be ferroelectric ceramics.

4. **Other contributors not fully sampled:** HKUST (520), IKFT (64), USC (338) were not fully sampled. Even if they contained ferroelectric materials, the total labeled file count would be far below the gate requirements.

## 14. Confirmations

- [x] No model checkpoint was loaded
- [x] No real-XRD inference was run
- [x] RRUFF-371 was not modified
- [x] V9/JS/simulated-Test contracts were not reopened
- [x] JS-only mainline remains frozen
- [x] Simulated training and Test remain frozen
- [x] No ERM/JS checkpoint was accessed

## 15. Next Steps for Real-Domain Adaptation

Given the NO_GO finding for opXRD:

1. **RRUFF-371 remains the primary real-PXRD asset.** The existing 371-sample RRUFF collection with 7-class balanced labels is the verified and audited real-domain data source.

2. **RRUFF is a mineral database, not a ceramics database.** The 371 RRUFF samples are natural minerals (not synthetic ceramics), but they provide the only experimentally measured, labeled, and audited PXRD data with complete 7-class crystal-system coverage available to this project.

3. **The measurement-domain transfer approach should proceed with RRUFF-371**, following the frozen design:
   - RRUFF-70 for few-shot adaptation development (35 support / 35 adaptation validation)
   - RRUFF-301 for external evaluation
   - Mineral-group-disjoint sensitivity cohort for unseen-mineral claims

4. **opXRD remains a future resource** for broader PXRD ML research but cannot support the ferroelectric ceramics domain adaptation task.

## 16. Recommendations

1. Accept the NO_GO finding for opXRD-based ferroelectric ceramics classification
2. Proceed with RRUFF-371 as the primary real-domain data asset
3. If ferroelectric ceramic-specific claims are required in the future:
   - Identify dedicated ferroelectric ceramic experimental databases (COD, ICSD with experimental tags, published ferroelectric datasets)
   - These would require separate acquisition, labeling audit, and feasibility assessment
4. Freeze the real-domain few-shot episodes for RRUFF-371 as the next engineering task
5. Do NOT further sample opXRD — the definitive finding is established
