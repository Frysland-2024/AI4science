# XRD Quantitative Inversion / Physics-Guided Diffraction - Resource Manifest

**Source check date:** 2026-08-15  
**Imported into repository:** 2026-08-27

This document preserves the locally assembled literature, code, data, and supplementary-material manifest used to plan the quantitative inversion project. Availability statements below reflect the 2026-08-15 check and should be re-verified before formal reuse.

## 1. Chitturi et al. (2021) - Automated prediction of lattice parameters from X-ray powder diffraction patterns

DOI: https://doi.org/10.1107/S1600576721010840

- Main PDF (open access): https://journals.iucr.org/j/issues/2021/06/00/vb5020/vb5020.pdf
- Supporting Information PDF: https://journals.iucr.org/j/issues/2021/06/00/vb5020/vb5020sup1.pdf
- Official/author code + trained models + SSRL data: https://github.com/sathya-chitturi/DeepLPnet
- Note: the original paper links an older GitHub URL (`src47/DeepLPnet`), which now resolves to the repository above.

## 2. Dong et al. / Vamvakeros et al. (2021) - PQ-Net

**Title:** A deep convolutional neural network for real-time full profile analysis of big powder diffraction data  
**DOI:** https://doi.org/10.1038/s41524-021-00542-4

- Main PDF (open access): https://www.nature.com/articles/s41524-021-00542-4.pdf
- Publisher article page / Supplementary Information download: https://www.nature.com/articles/s41524-021-00542-4
- SI filename: `41524_2021_542_MOESM1_ESM.pdf`
- Public training/test data: https://doi.org/10.5281/zenodo.4664597
- Code: NOT public in the paper; authors state that code is available upon reasonable request.

## 3. Gómez-Peralta et al. (2023)

**Title:** Convolutional Neural Networks to Assist the Assessment of Lattice Parameters from X-ray Powder Diffraction  
**DOI:** https://doi.org/10.1021/acs.jpca.3c03860

- ACS article / PDF access page: https://pubs.acs.org/doi/10.1021/acs.jpca.3c03860
- Main PDF: publisher-access dependent; ACS marked it Available to Purchase unless institutional access is available.
- Supporting Information: free from the article page above
- SI filename: `jp3c03860_si_001.pdf`
- No official public code repository found in the checked sources/GitHub search as of 2026-08-15.

## 4. Shu et al. (2025) - AIdex

**Title:** Machine Learning Tackles the Challenge of Powder X-ray Diffraction Indexing for All Crystal Systems  
**DOI:** https://doi.org/10.1021/acs.jcim.5c01506

- ACS article / PDF access page: https://pubs.acs.org/doi/10.1021/acs.jcim.5c01506
- Main PDF: publisher-access dependent; ACS marked it Available to Purchase unless institutional access is available.
- Supporting Information: free from the article page above
- SI filename: `ci5c01506_si_001.pdf` (37.37 MB)
- No official public code repository found in the checked sources/GitHub search as of 2026-08-15.

## 5. Mun, Nam & Choi (2026) - RAPID

**Title:** Automation of Rietveld refinement through machine learning  
**DOI:** https://doi.org/10.1107/S1600576726001494

- Main PDF (open access): https://journals.iucr.org/j/issues/2026/02/00/yr5164/yr5164.pdf
- Article page: https://journals.iucr.org/j/issues/2026/02/00/yr5164/index.html
- Code + data + manuals: https://github.com/DataForgeSci/RAPID
- Separate SI: none found on the official article page; extensive Appendices A-J are incorporated into the paper itself.

## 6. Luo et al. (2025) - DONUT

**Title:** DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis  
**DOI:** https://doi.org/10.1038/s41524-025-01860-7

- Main PDF (open access): https://www.nature.com/articles/s41524-025-01860-7.pdf
- Publisher article page / Supplementary Information DOCX download: https://www.nature.com/articles/s41524-025-01860-7
- Code + trained model: https://github.com/AdvancedPhotonSource/DONUT
- Public data: https://doi.org/10.5281/zenodo.17586299
- Note: the official Nature page provides a separate Supplementary Information DOCX; the GitHub repository also contains a supplementary directory.

## 7. Hofgard et al. (2026) - Invariant lattice representation

**Title:** Learning Lattice Parameters from Powder X-Ray Diffraction Data Using Invariants

- arXiv abstract: https://arxiv.org/abs/2607.21829
- arXiv PDF: https://arxiv.org/pdf/2607.21829
- arXiv source package: https://arxiv.org/e-print/2607.21829
- No official public code repository was identified from the arXiv page or GitHub search as of 2026-08-15.
- Supplementary material appears to be integrated into the manuscript/source rather than listed as a separate publisher SI item.

## Priority for the current one-month project

1. **Chitturi 2021** - closest baseline for lattice-parameter regression + measurement non-idealities.
2. **DONUT 2025** - closest methodological precedent for differentiable diffraction forward physics as training supervision.
3. **RAPID 2026** - closest recent endpoint showing known-phase ML parameter refinement and robustness/noise handling.
4. **PQ-Net 2021** - important quantitative diffraction regression / Rietveld-comparison precedent.
5. **AIdex 2025** - important for indexing robustness and unit-cell prediction under peak uncertainty / zero shift.
6. **Hofgard 2026** - important if the project later expands beyond one known tetragonal template to multi-system lattice representations.
7. **Gómez-Peralta 2023** - direct lattice-parameter CNN precedent and experimental validation.

## Use in the formal plan

The formal execution plan is maintained separately:

- [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md)

The plan deliberately narrows the first implementation to a known-phase, single-phase tetragonal task. The broader resources in this manifest are references for staged expansion, not a commitment to reproduce all listed systems in V0.
