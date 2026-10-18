# XRD papers and code from the 2026-10-18 reading list

Acquired from the five titles shown in the user's reading-list screenshots. Main articles and publisher supplements are stored in the existing topic zone:

`../../literature_zones/02_xrd_ai_crystal_structure_benchmarks/`

Code and supplementary software are stored under:

`../../../02_code_repositories/related_methods_and_tem/`

## Papers and local source status

| Paper | Article and local file | Supplement / code status |
| --- | --- | --- |
| Chang et al. (2025), “Probabilistic phase labeling and lattice refinement for autonomous materials research” | DOI [10.1038/s41524-025-01627-0](https://doi.org/10.1038/s41524-025-01627-0); `01_CrystalShift_2025.pdf` | `01_CrystalShift_2025_Supplementary.pdf`; official `CrystalShift.jl` and companion `CrystalTree.jl` repositories cloned locally. |
| Dong et al. (2021), “PQ-Net: A deep convolutional neural network for real-time full profile analysis of big powder diffraction data” | DOI [10.1038/s41524-021-00542-4](https://doi.org/10.1038/s41524-021-00542-4); `02_PQNet_2021.pdf` | `02_PQNet_2021_Supplementary.pdf`; the article says code is available from the authors on reasonable request. No public code repository was found, and no author request was sent. |
| Lee et al. (2020), “A deep-learning technique for phase identification in multiphase inorganic compounds using synthetic XRD powder patterns” | DOI [10.1038/s41467-019-13749-3](https://doi.org/10.1038/s41467-019-13749-3); `03_Lee_2020.pdf` | `03_Lee_2020_Supplementary.pdf` and `03_Lee_2020_Supplementary_Additional.pdf`; the two publisher supplementary-software files are retained under `06_Lee2020_supplementary_code/`. They contain JSON-serialized notebook source. |
| Ito et al. (2026), “Enabling single-observation decomposition of multi-phase X-ray diffraction patterns via generative deep learning” (PhaseDifformer) | DOI [10.1038/s41524-026-02087-w](https://doi.org/10.1038/s41524-026-02087-w); `04_PhaseDifformer_2026.pdf` | `04_PhaseDifformer_2026_Supplementary.pdf`; official PhaseDifformer repository cloned locally. |
| “DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis” (2025) | DOI [10.1038/s41524-025-01860-7](https://doi.org/10.1038/s41524-025-01860-7); `05_DONUT_2025.pdf` | Official `main` branch source snapshot at `090c10bdf99333d3670dc26e617a93364f714bdc`; per-file source checksums are listed in `CODE_SHA256SUMS.txt`. |

The main article and supplement PDFs were checked for a `%PDF-` signature. File sizes and SHA-256 values are listed in `SHA256SUMS.txt` and the literature-zone `zone_manifest.csv`. Repository remotes and captured commit IDs are in `CODE_COMMITS.csv`; source and notebook checksums are in `CODE_SHA256SUMS.txt`.

## Source notes

- The CrystalShift article PDF was obtained from an author-hosted Cornell copy; the DOI page is retained as the canonical publication record.
- The PQ-Net article PDF was obtained from UCL Discovery; the publisher page is the canonical publication record.
- The Lee article PDF was obtained from a ResearchHub-hosted copy after the publisher and PMC PDF endpoints returned access-verification pages. Article metadata and supplementary files are linked from the canonical Nature/PMC records.
- The PhaseDifformer publisher PDF endpoint initially returned an access-verification page; the valid article PDF was subsequently retrieved with a browser user agent and verified locally.
- No standalone bulk datasets or model-weight packages outside the requested source repositories were downloaded.
