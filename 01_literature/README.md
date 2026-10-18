# AI4science literature workspace

Generated: 2026-07-14

## Main entry points

- `literature_zones/`: topic-based reading view, with copied PDFs grouped for use.
- `xrd_perturbation_core/`: core XRD perturbation paper-code package, source audit, and XRDMatch source note.
- `literature_audit/`: reading coverage, SHA256 deduplication, deletion log, paper-code map, and the archived 2026-06-28 reading synthesis.
- `00_project_context/` is also reconciled as a literature source; its unique reference PDFs are copied into `literature_zones/07`-`09` with SHA256 provenance.

The former `core_xrd_crystal_ai/` and `related_methods_and_tem/` folders were empty or contained only legacy manifests. Their useful manifest was merged into `xrd_perturbation_core/index/`; no source code was removed.

The former root-level `1111.zip` and `Oviedo_2019_Fast_and_interpretable_XRD_classification.pdf`
were reconciliation inputs only. Their contents were verified against the canonical zone
copies and the redundant root files were removed. The verification record is
`literature_audit/LOCAL_PACKAGE_RECONCILIATION_20260714.md`.

## Compression status

Valid packages have corresponding extracted directories. XQueryer is now kept as a source-only extracted copy under `../02_code_repositories/xrd_perturbation_core/extracted_verified/`; its large data files were removed after extraction. Original ZIP files were deleted after the extracted copies were checked.

Start from:

- `literature_zones/README.md`
- `literature_zones/zone_manifest.csv`
- `xrd_perturbation_core/paper_code_index.csv`
- `literature_audit/READING_SYNTHESIS_2026-06-28.md`

## 2026-07-23 acquisition

The opXRD and SIMPOD papers, source archives, and opXRD experimental dataset were
classified and verified on 2026-07-26:

- acquisition and archive proof:
  `source_acquisitions/2026-07-23_opxrd_simpod/README.md`;
- opXRD experimental patterns:
  `data_resources/opxrd_zenodo_14254270/`;
- curated paper copies:
  `literature_zones/01_core_xrd_perturbation_phase_identification/` and
  `literature_zones/02_xrd_ai_crystal_structure_benchmarks/`;
- extracted reference source:
  `../02_code_repositories/xrd_perturbation_core/extracted_verified/`.

These local resources are not active V9 training, tuning, or test inputs.
