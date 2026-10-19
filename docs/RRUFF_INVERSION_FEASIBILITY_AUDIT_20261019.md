# RRUFF lattice inversion and Sim-to-Real feasibility audit

**Audit date:** 2026-10-19
**Status:** DATA AUDIT COMPLETE; no neural-network training or GPU experiment was run.
**Scope:** official RRUFF powder archives and AMCSD CIF references available in the local `RRUFF/` ignored data directory; finite mineral-family registry declared by the audit script. This is not a claim of complete coverage of all minerals or all RRUFF releases.

## Decision

The data support a **small, exploratory, known-structure PXRD inversion pilot**, with the **Rutile structure type** as the best first choice. It has 11 valid experimental-powder profiles with complete, exact-RRUFF-ID cell estimates; 9 have high-compatibility AMCSD CIF candidates. After excluding the one profile whose metadata says it is a Rutile/Hematite mixture, 10 labeled sample IDs remain. All 11 are tetragonal `P4_2/mnm`, matching the symmetry scope of the current inversion forward model. This is enough to investigate a tightly bounded sample-level pilot, but not enough for a strong, broad Sim-to-Real generalization claim.

**Domain adaptation is possible as a small supervised few-shot pilot, not established as a reliable method.** The 10 clean Rutile-structure-type samples can in principle be separated by exact sample ID into adaptation, validation, and test groups, but the held-out test would be small and would not establish transfer to unseen mineral species. No independent split has yet been frozen. The RAW profiles do not state wavelength; exact-ID refinement outputs list wavelength conditions, but those still need to be checked against acquisition records before fitting. No separate, large unlabeled real Rutile pool was identified.

The audit therefore recommends proceeding only to a **data/forward-model compatibility and identifiability gate**. Do not start a multi-family model or claim validated real-domain adaptation from these counts alone. Garnet has the richest coherent labeled set (44 profiles), but it is cubic and is outside the current tetragonal forward-model contract; it would require a separately validated cubic forward model. The AMCSD CIFs are structural templates, never verified same-specimen ground truth.

## Sources and audit method

The official RRUFF download and ZIP help pages describe the downloadable diffraction and structure resources: [RRUFF download data](https://www.rruff.net/about/download-data/) and [RRUFF ZIP download help](https://www.rruff.net/help/zip-download/). The audit read these archives directly without extracting or modifying them:

| Archive | Official URL | Members | SHA-256 | Acquisition record |
|---|---|---:|---|---|
| `XY_RAW.zip` | [powder archive](https://www.rruff.net/zipped_data_files/powder/XY_RAW.zip) | 3,019 | `948a133482bb3c99da80194cc2848933aee668129beb209150f7f850cd4b0587` | Pre-existing local ZIP; original download date not independently verified |
| `XY_Processed.zip` | [powder archive](https://www.rruff.net/zipped_data_files/powder/XY_Processed.zip) | 1,484 | `c0b079535ab3e6077212b7a8f6ced28129cbe538fc03b1479061430f219ff9cb` | Pre-existing local ZIP; original download date not independently verified |
| `DIF.zip` | [powder archive](https://www.rruff.net/zipped_data_files/powder/DIF.zip) | 3,013 | `3b540db61664cacdd22268ffbac6ab586ca6bce389b7399cc3e9baaeb6607b03` | Pre-existing local ZIP; original download date not independently verified |
| `Refinement_Data.zip` | [powder archive](https://www.rruff.net/zipped_data_files/powder/Refinement_Data.zip) | 1,175 | `7e075457ebac5ad8c5841e699857e7666e6feae1f8e8dd00945dc6818d60d5f6` | Pre-existing local ZIP; original download date not independently verified |
| `Refinement_Output_Data.zip` | [powder archive](https://www.rruff.net/zipped_data_files/powder/Refinement_Output_Data.zip) | 1,176 | `a51e4f7399051889a3d699dadb99c2139476d3d17ea47baf85e3ebf3df4f5c12` | Pre-existing local ZIP; original download date not independently verified |
| `cif.zip` (AMCSD) | [AMCSD CIF archive](https://www.rruff.net/AMS/zipped_files/cif.zip) | 21,720 | `f84e8aa19042182dd1c01c25f4d4aa171356bf709c5b888fac706295999687bc` | Downloaded from the official URL on 2026-10-19 |

Hashes are of the local archive bytes at audit time. The five pre-existing archives' mtimes do not prove when or from where they were originally downloaded. Only `cif.zip` was newly retrieved in this audit. Raw ZIPs remain in the ignored local data directory and are not part of this change.

The reproducible parser reads archive members in place, preserves exact RRUFF IDs including suffixes, fingerprints numeric XY traces, parses refinement cell values and their parenthetical estimated standard deviations, reads peak-index data, extracts AMCSD CIF structure metadata, and records per-source member hashes. The finite alias registry is listed in the JSON; unlisted mineral names remain unclassified. The current inversion contract was checked against [`xrd_inversion/README.md`](../xrd_inversion/README.md) and `xrd_inversion/src/xrd_inversion/gpu_forward.py`: the current differentiable forward path models conventional tetragonal cells and consumes a fixed `Structure`, so it is not immediately suitable for cubic or hexagonal families.

## Screening counts

These are archive-member, exact-ID, and eligible-sample counts at different stages; they should not be conflated.

| Stage | Count | Interpretation |
|---|---:|---|
| `XY_RAW.zip` members | 3,019 | Every member in the official raw-profile archive present locally |
| Members with parseable RRUFF `R...` sample IDs | 3,002 | 17 members had non-R IDs or malformed ID strings; preserved with hashes in JSON, excluded from the RRUFF-R sample manifest |
| Unique exact RRUFF IDs in the union of indexed powder archives | 3,256 | Broader archive union; includes IDs with no `XY_RAW` member |
| Unique exact RRUFF IDs with a raw profile | 3,002 | Keeps sub-number suffixes; does not mean profile is experimental powder |
| Numerically valid raw profiles | 2,976 | At least two finite, increasing 2θ/intensity pairs with nonconstant intensity |
| Valid profiles classified as experimental-powder candidates | 1,272 | Metadata says powder and does not explicitly say calculated; 35 have a mixture/contamination caveat |
| Same candidate profiles without a mixture/contamination caveat | 1,237 | Metadata-screened subset; not a manual phase-purity validation |
| Raw-profile IDs intersecting an exact-ID refinement-output member | 1,161 | Member exists; not necessarily a valid powder profile or complete label |
| Valid experimental-powder profiles with all six exact-ID RRUFF cell parameters | 1,133 | RRUFF refinement estimates, with reported ESD where available |
| Same, without mixture/contamination caveat | 1,102 | Metadata-cleaner labeled subset |
| Same with high AMCSD template compatibility | 853 | Compatibility is not proof that CIF and measured specimen are identical |
| Same with high compatibility and no mixture/contamination caveat | 831 | More conservative template-linked subset |

The 1,695 profiles explicitly described as calculated are not experimental measurements; 5 are classified as non-powder/single-crystal, and 4 are unresolved. The valid-powder count is therefore not 2,976. The 37 powder descriptions that say their cell parameters are from single-crystal data were flagged; 5 overlap with a complete exact-ID refinement output. These are not silently treated as powder-refined ground truth. In the Apatite family, two labeled Mimetite samples have this wording.

## What the labels and CIF matches mean

The manifest keeps three distinct evidence types:

1. **RRUFF exact-ID refined cell:** six cell parameters parsed from that exact sample ID's `Refinement_Output_Data` entry, plus any available ESD, refinement output hash, wavelength fields and source. These are reference estimates with uncertainty, not error-free physical truth. In some metadata the cell source is explicitly single-crystal-derived.
2. **AMCSD CIF:** a deposited structure and lattice used as a possible simulation template. A compatible cell/system/chemistry can support structural-template compatibility; it does not prove the CIF came from the same physical specimen.
3. **DIF/peak-index data:** supports phase/reflection and possible AMCSD database-code cross-reference. It does not turn an AMCSD entry into an exact-specimen CIF.

High CIF compatibility requires matching crystal system, a small cell/angle metric difference, compatible cation-element sets, and either exact normalized mineral-name evidence or an exact DIF-to-AMCSD database-code link. Name alone never makes a high-confidence match. Every `amcsd_is_same_specimen_confirmed` field is false. The audit found 3,087 exact-name sample-ID candidates, but these are candidates for further checking, not 3,087 verified sample/CIF pairs.

`XY_RAW` gives numeric 2θ/intensity but no explicit wavelength field. The exact-ID refinement output often provides a wavelength triplet; for the Rutile family this is consistently `1.541838|1.540562|1.54439 Å`. The audit records it as a same-ID refinement-output value, not as an independently verified instrument setting embedded in the raw scan. All Rutile candidate scans have 8,500–8,501 points over 5–90°, but radiation and instrument geometry still need external confirmation.

## Family feasibility

`GO` means only “reasonable to run a bounded pilot”; `LIMITED_GO` means the data may support exploration after major scope or forward-model limitations are handled; `NO_GO` means the current family evidence is too small or heterogeneous for a family-level DA study. These are evidence-based qualitative decisions, not automatic sample-count cutoffs.

| Family | Valid powder + complete exact-ID cell | High-compatible CIF | Structure / target | Decision |
|---|---:|---:|---|---|
| **Rutile structure type** | **11** (10 without mixture caveat) | **9** | 11 tetragonal `P4_2/mnm`; 3 species; 2 independent parameters `a,c`; `a=4.404–4.7385 Å`, `c=2.87–3.1869 Å` | **GO — bounded pilot only** |
| **Garnet** | **44** (43 without mixture caveat) | **44** | 44 cubic; 7 species; one independent `a=11.4941–12.1221 Å` | **LIMITED_GO** — strongest family coverage, but current forward model is tetragonal-only |
| **Apatite** | **29** | **28** | 28 hexagonal, 1 monoclinic; 6 species; use `a,c` only for a narrowed hexagonal subset | **LIMITED_GO** — two labeled Mimetite descriptions say cell values are from single-crystal data; requires hexagonal forward path |
| Amphibole | 36 | 30 | 16 species; 35 monoclinic, 1 orthorhombic | LIMITED_GO — heterogeneous systems |
| Pyroxene | 31 | 30 | 8 species; mostly monoclinic with orthorhombic/triclinic cases | LIMITED_GO — needs a narrowed structural subset |
| Feldspar | 21 | 20 | 5 species; triclinic and monoclinic | LIMITED_GO |
| Carbonate group | 40 | 16 | 11 species; mixed crystal systems | LIMITED_GO — many labels, weaker CIF compatibility |
| Zeolite | 21 | 16 | 10 species; varied systems | LIMITED_GO |
| Spinel | 13 (14 powder candidates) | 13 | 13 cubic labels; 5 species; one `a` | LIMITED_GO — smaller and requires cubic forward support |
| Olivine | 9 | 9 | 2 species; orthorhombic | LIMITED_GO — small |
| Zircon structure type | 6 | 4 | 2 species; tetragonal | LIMITED_GO — too few for a useful independent DA test |
| Quartz group | 4 | 4 | several structure types | NO_GO for family-level DA |

### A–E assessment for the three strongest candidates

| Question | Rutile structure type | Garnet | Apatite |
|---|---|---|---|
| **A. Simulation-only training?** | Yes in principle: compatible tetragonal CIF templates and exact-ID cell ranges exist. The simulation-to-real gap is untested. | Yes in principle, but a cubic forward implementation and verification are required first. | Yes in principle for a symmetry-specific subset, but a hexagonal forward implementation is required. |
| **B. Supervised few-shot real adaptation?** | Technically possible with 10 metadata-clean labeled sample IDs; too small for strong conclusions. RRUFF cells remain uncertain reference estimates. | 43 metadata-clean labels provide better sample-level scope, but only after cubic forward support and CIF/instrument verification. | Labels exist, but two Mimetite records have single-crystal-cell wording; narrow to the 28 hexagonal samples and audit label source before using. |
| **C. Unlabeled adaptation/calibration?** | No separate unlabeled real Rutile cohort was identified. A deliberately label-masked subset could test a protocol, but does not add independent data. | Same limitation: no distinct unlabeled cohort identified by this audit; masked use is possible only under a frozen split. | Same limitation. Do not use test labels to calibrate the simulator. |
| **D. Independent real test?** | A base-ID-level split is possible in principle (11 IDs, 10 after the mixture caveat), but a test of a few samples has low precision and does not test unseen-species transfer. No split is frozen. | A more plausible sample-level holdout exists among 44 labels, but the present code cannot run this cubic task. | Sample-level holdout is possible, but parameter-source caveats and mixed symmetry reduce effective scope. |
| **E. AI initialization vs conventional refinement?** | Feasible to compare on held-out IDs after scan wavelength, CIF convention and forward model are verified; report reference-cell error with ESD, residual, convergence/failure and time. Not yet measured. | Feasible only after cubic simulator/optimizer validation. | Feasible only after a hexagonal model and a provenance-clean label subset are established. |

The machine-readable family table records A–E fields for all 12 registered families. All say no independent DA/test split is already established; a split must be frozen before training or validation.

## Duplication, leakage, and failure risks

- The global audit found **20 sample IDs in 10 pairs** with identical numeric XY traces across IDs, plus **6 IDs in 3 same-base sub-number groups** that may represent related samples. Split by exact base ID and numeric trace SHA, never by random spectrum row. The Rutile, Garnet, and Apatite labeled candidate subsets have no detected identical-trace pair or related sub-number group in this audit.
- Thirty-five powder candidates carry mixture/contamination wording. One of 11 Rutile-structure labeled profiles, `R040049-1 Rutile`, is described as an 87% Rutile / 13% Hematite mixture. Exclude it from the primary single-phase benchmark or reserve it as a separate mismatch case.
- Thirty-seven otherwise valid experimental-powder descriptions state that cell parameters came from single-crystal data; five have complete exact-ID refinement entries. A raw profile plus a cell file is not sufficient evidence that those labels were refined from that profile.
- The exact-ID output wavelength is not embedded in `XY_RAW`. A mismatch in wavelength/geometry, peak shape, intensity normalization, texture or specimen composition can dominate apparent lattice error and optimizer success.
- Matching by name or nearby lattice constants can select a plausible prototype, but not prove same specimen. Keep the template confidence and provenance attached to every evaluation.
- Cell parameters are not uniquely determined by a low profile residual in every setting. Use RRUFF ESD as an uncertainty annotation and report residual and parameter error separately. Never repeatedly tune on the same small labeled set and then call it independent validation.
- Family mapping is intentionally finite. The 2,846 unclassified IDs are not a statement that they lack useful materials families.

## Recommended first minimum experiment

**Material:** Rutile structure type (`P4_2/mnm`), including Rutile, Cassiterite and Pyrolusite. Begin with `R050031-1` as a Rutile/TiO₂ data/forward smoke case: 8,501 points from 5–90°, measured composition recorded as TiO₂, exact-ID RRUFF cell `a=4.5945(1) Å`, `c=2.9594(1) Å`, and high-compatibility template candidate `Rutile__0009161.cif`. The CIF is a reference template, not confirmed to be that exact specimen.

**Before training:** verify the actual radiation/wavelength and sample/profile provenance; compare the CIF-based forward profile to the observed scan; confirm the target parameters are identifiable over the measured range; freeze exact-ID groups and an untouched real test split. If these checks fail, stop or narrow the task rather than tuning evaluation criteria after seeing results.

**If that gate passes:**

- **Input:** XY_RAW 2θ/intensity plus a documented candidate Rutile CIF and verified instrument assumptions.
- **Output:** tetragonal lattice parameters `a,c` and the reconstructed profile.
- **Comparison:** simulation-only parameter regressor; the same regressor after a predeclared few-shot adaptation set; then give each prediction to the same bounded L-BFGS-B physical refinement. Compare against L-BFGS-B initialized from the matched AMCSD template cell under identical bounds, profile model, stopping rules and time budget.
- **Report:** MAE/error relative to the exact-ID RRUFF estimates with their ESDs shown, profile residual, convergence and failure rate, inference/refinement time, and grouped split identities. Keep simulation training realizations separate from independent material samples; split adaptation/validation/test before fitting.
- **Scope:** 10 metadata-clean labeled Rutile-structure samples (4 Cassiterite, 4 Rutile, 2 Pyrolusite); avoid claiming unseen-species performance. Use the one known mixed-profile sample only as a separately labeled stress case.

This is a plan for the next gate, not an experiment run in this audit. It makes an undergraduate thesis route plausible if framed as one-family, known-candidate, small-sample feasibility research. It does **not** currently support a multi-family router or a claim that real-domain adaptation has succeeded.

## Deliverables and reproduction

- [`sample_manifest.csv`](../xrd_inversion/audits/rruff_domain_adaptation/sample_manifest.csv) — one row per exact RRUFF ID in the archive union, with source/member hashes, XY validity/range, raw/refinement fields, ESD, CIF evidence/confidence, duplicates, and ineligibility codes.
- [`family_summary.csv`](../xrd_inversion/audits/rruff_domain_adaptation/family_summary.csv) — family coverage, parameter ranges, A–E assessment, and qualitative decision.
- [`audit_summary.json`](../xrd_inversion/audits/rruff_domain_adaptation/audit_summary.json) — screening counts, archive hashes/provenance, source URLs, alias registry, criteria and limitations.
- [`audit_rruff_domain_adaptation.py`](../xrd_inversion/scripts/audit_rruff_domain_adaptation.py) — repeatable read-only archive parser; optional `--download-missing` downloads absent official ZIPs without overwriting existing ones.
- [`test_rruff_domain_adaptation_audit.py`](../xrd_inversion/tests/test_rruff_domain_adaptation_audit.py) — parser tests.

With the official ZIPs in `RRUFF/`, reproduce from the repository root:

```powershell
xrd_inversion/.venv/Scripts/python.exe xrd_inversion/scripts/audit_rruff_domain_adaptation.py
```

If a required archive is absent, use `--download-missing`; the script does not overwrite existing ZIPs. To record the manually downloaded CIF archive as acquired during this audit, the audited command was:

```powershell
xrd_inversion/.venv/Scripts/python.exe xrd_inversion/scripts/audit_rruff_domain_adaptation.py --downloaded-during-audit cif.zip
```

Parser tests: `python -m unittest tests.test_rruff_domain_adaptation_audit -v` from `xrd_inversion/` (6 tests passed). The historical RRUFF-301/371 manifests, split and model results were not changed. No neural network, GPU run, or result recalculation was performed.
