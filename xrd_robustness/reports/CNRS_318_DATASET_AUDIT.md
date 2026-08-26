# CNRS-318 dataset audit (git-trackable authoritative summary)

**Date:** 2026-08-27

**Domain role:** formal second experimental domain — PASS.

> **CNRS-318 = naturally imbalanced independent experimental domain.**

This file is the git-trackable, lightweight record of the authoritative CNRS
audit. The raw spectra and large intermediate files stay under the git-ignored
`data/` tree; only the decision-relevant evidence is committed here.

## Provenance

| Item | Value |
| --- | --- |
| Source | opXRD v11 CNRS path (Zenodo `14254270`, CNRS subfolder) |
| opXRD v11 archive SHA-256 | `38B62BCDDF976DEBB3E41D2597D3F14AC6C1F1C8A33565A84A98EF38BA3B6044` |
| Authoritative v2 manifest (local, git-ignored) | `xrd_robustness/data/real_xrd/opxrd_cnrs7cs/cnrs_7cs_audit_manifest.csv` |
| v2 manifest SHA-256 | `FAF089375C10C18D0A4AB3568E85FA78EAA56DE45F507FAACD39672AD88BE424` |
| Committed lightweight manifest | [`../manifests/cnrs_318_parent_manifest_v2.csv`](../manifests/cnrs_318_parent_manifest_v2.csv) |

## Audit funnel

| Step | Count | Note |
| --- | ---: | --- |
| Raw CNRS JSON files | 1,052 | all parseable; 1,044 valid equal-length finite arrays |
| Parseable atomic structures | 891 | labels are NOT recovered from lattice metrics |
| Stable multi-tolerance crystal-system labels | 886 | same crystal system at `symprec = 0.001/0.01/0.05/0.1` |
| Cu Kα Bragg-mapped coverage 10–80° | 487 | strict endpoints, no 0.01° tolerance |
| Spectrum-unique broad-material candidates | 476 | 11 scans in 5 label-conflicting duplicate-spectrum groups excluded |
| Structural parents within CNRS | 323 | `StructureMatcher` clustering within (reduced formula × stable system) |
| Final independent parents after `formal_14060` exclusion | **318** | 5 parent components with fuzzy `formal_14060` matches excluded as whole groups |

## Seven-class counts (final 318)

| triclinic | monoclinic | orthorhombic | tetragonal | trigonal | hexagonal | cubic | total |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21 | 87 | 77 | 41 | 33 | 12 | 47 | 318 |

## Label source

The seven-class labels are **structure-derived crystal-system labels**: they are
reconstructed from the COD deposited atomic basis (not from the pattern file,
which carries zero deposited space-group labels), and are accepted only when the
crystal system is identical across all audited `symprec` values. They are not
"pseudo-labels" produced by a model. They were **not** independently verified by
manual spectrum-level phase analysis.

## Role relative to RRUFF-301

| Domain | Naming | Role |
| --- | --- | --- |
| RRUFF-301 | balanced curated experimental domain | class-balanced, tidy labels and quality control; stable quantitative comparison |
| CNRS-318 | naturally imbalanced independent experimental domain | more heterogeneous provenance, chemistry and measurement conditions; tests external generalization across databases and measurement sources |

The two domains are **complementary**, not required to be equal in size,
class-balance or statistical strength. See the project history note for why the
earlier "≥20 parents per class" gate was retracted.

## Scope limitation (must be reported with the conclusion)

CNRS-318 is **not class-balanced**; hexagonal has only 12 structural parents, so
hexagonal-specific conclusions remain **underpowered**. This is information
about the data, not a defect: wide bootstrap intervals are reported as-is, and
no downsampling to 84 or upsampling/duplication of hexagonal is performed.

Labels are **derived from the deposited crystal structures through stable symmetry
reconstruction and were not independently verified by manual spectrum-level phase
analysis**. A small amount of metadata, extra-phase, or spectrum-structure mismatch
is therefore possible and must be acknowledged in the Discussion; it does not prevent
CNRS-318 from being a formal second experimental domain.

## Related records

- Evaluation protocol: [`CNRS_318_EVALUATION_PROTOCOL.md`](CNRS_318_EVALUATION_PROTOCOL.md)
- Parent manifest: [`../manifests/cnrs_318_parent_manifest_v2.csv`](../manifests/cnrs_318_parent_manifest_v2.csv)
- Project history node: [`../../docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md`](../../docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md)
