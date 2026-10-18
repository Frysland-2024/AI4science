# Literature zones

Generated: 2026-07-12

This folder is the working, topic-based view of the project literature. Source folders are left intact; files here are curated copies for reading, review writing, and experiment planning.

## Zones

| Zone | Use |
| --- | --- |
| `01_core_xrd_perturbation_phase_identification/` | Core XRD perturbation, phase identification, simulated-vs-real robustness, and directly paired paper-code items. |
| `02_xrd_ai_crystal_structure_benchmarks/` | Broader XRD AI papers, structure refinement, crystal workflow papers, and benchmark/context documents. |
| `03_consistency_ssl_physical_regularization/` | Semi-supervised learning, consistency regularization, physical consistency, and method papers relevant to XRDMatch/PAMPT-style training. |
| `04_tem_spectroscopy_image_ml/` | TEM, spectroscopy, hyperspectral/image ML, and microscopy-adjacent references. |
| `05_project_group_and_misc_materials/` | Group meeting slides and local project materials that are useful but not cleanly paper-like. |
| `06_source_free_domain_generalization/` | TIR and source-free cross-domain limited-data method references; low relevance to V7 and not part of the core XRD chain. |
| `07_small_data_and_sample_efficiency/` | Small-data learning, repeated evaluation, uncertainty, and compute-budget references for V7 protocol design. |
| `08_scientific_ml_and_causal_context/` | Scientific ML software architecture and generative/causal modeling context. |
| `09_materials_and_dielectric_ml_context/` | Dielectric-materials, phase-field, simulation-guided design, and materials-ML context. |
| `90_source_archives_extracted/` | Pointers to extracted source archives and provenance directories. |

## Index files

- `zone_manifest.csv`: file-level manifest with zone, original source path, size, and SHA256.
- `../xrd_perturbation_core/paper_code_index.csv`: detailed paper-code mapping for the core XRD perturbation set.
- `../xrd_perturbation_core/download_audit.md`: download and zip integrity audit for the XRD perturbation package.

## Notes

- Duplicates are intentionally reduced in these zones; original source directories may still contain duplicate copies and source-package provenance.
- XQueryer source code is available under `../../02_code_repositories/xrd_perturbation_core/extracted_verified/XQueryer-main/`; large datasets and generated matching files were removed.
- `OneDrive_1_2026-7-12.zip` was extracted as a source archive because it is mostly workshop/data material, not a clean literature packet.
- `00_project_context/extracted_full_archive/.../references/original/` was reconciled by SHA256. The reconciliation record is in `../literature_audit/CONTEXT_SOURCE_RECONCILIATION.md`.
- PDFs bundled inside source packages were separately classified in `../literature_audit/SOURCE_PACKAGE_REFERENCE_AUDIT.md`; directly relevant XRD papers were copied into zone `02`, while manuals and certificates remain with their source packages.
- The 2026 opXRD paper and supplement are classified in zone `01`; the 2025
  SIMPOD benchmark paper is classified in zone `02`. Their acquisition and
  archive hashes are recorded in
  `../source_acquisitions/2026-07-23_opxrd_simpod/README.md`.
- Five XRD-AI papers from the 2026-10-18 reading list, their available supplements,
  and local code sources are indexed in zone `02`; the acquisition record is at
  `../source_acquisitions/2026-10-18_xrd_paper_code/README.md`.
