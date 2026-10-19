# 2026-10-19 exploratory NEW undergraduate research directions (not selected)

> **STATUS: BRAINSTORMING / EVIDENCE-TO-COLLECT; not an approved title, not a research result, not a user commitment to change the current thesis.** The researcher explicitly asked, "如果要开展一个全新的研究呢", after seeing both the 2026-10-19 Garnet real-profile pilots fail to establish useful physics/DA superiority. The completed seven-crystal-system study and old negative inversion attempts are preserved unchanged.

## Design constraints expressed by the researcher
- Must be a genuinely separable research question, not hiding unsuccessful lattice inversion behind a software platform.
- Prefer AI for materials characterization and applied physics; no wet lab requirement for the researcher.
- Scientific method improvement over credible physical/classical/reference baselines is more important than Qwen, visual UI or generic automation.
- Existing XRD data pipelines and experience are reusable *tools*, not a justification for reusing frozen test results as new evidence.

## Candidate 1 — real Raman instrument transfer and K-shot adaptation
- **New question:** when Raman excitation wavelength/instrument/resolution/background changes, can small-label, physics-aware calibration plus compact learning improve **mineral identification** relative to a strong classical peak/cosine/correlation library matcher, source-only CNN, ordinary fine-tuning, and non-neural instrument calibration?
- Official RRUFF has Raman raw spectra from multiple laser/instrument setups (such as 514/532/780–785 nm), but paired instrument labels and enough independent specimen-per-class-per-domain records **have not been audited**. Wavenumber coordinates vs excitation wavelength need careful physical handling.
- Scientific novelty **not claimed**: prior Raman domain adaptation, RRUFF mineral CNNs and instrument transfer already exist. A specific protocol or physics-based hypothesis must be sharpened after prior-art review. Avoid a cosmetic CNN architecture change.
- Gate: audit number of real scans / distinct sample IDs / mineral species split by trusted instrument/excitation and resolution metadata; verify train/test independence and enough labels before model training.

## Candidate 2 — complementary Raman + PXRD under measurement uncertainty
- **New question:** for the *same mineral specimen* with measured Raman and powder XRD, when does combining crystal-diffraction and vibrational evidence substantially improve **mineral identification**, including when one measurement is low quality or absent?
- Establish baseline A: XRD-only credible reference/pattern matching; B: Raman-only credible spectral library matching; C: simple probability/score late fusion; D: small uncertainty-aware quality-conditioned fusion. Evaluate accuracy / Macro-F1, selective error or Top-K, missing modality and acquisition conditions.
- **First and binding data gate:** intersect exact/base RRUFF sample IDs of Raman raw and **experimental** XY_RAW powder profiles; verify that a matched base ID really represents the same specimen; count classes with enough independent specimens, measurement quality and excitation metadata; grouped splits by true specimen/locality/related scans. Do not assume 1-to-1 correspondences from mineral name only. If no viable paired cohort, NO-GO for this idea.
- Literature already addresses Raman multimodal studies and experimental Raman/PXRD structure retrieval (2026 RealBind), so *pairing alone* is not novel. Investigate a specific limitation, such as quality-dependent selective use and missing-modality stress, before any novelty claim.

## Candidate 3 — candidate-library PXRD structure retrieval with experimental transfer
- **New question:** can a learned experimental-domain representation retrieve the correct *known* crystal structure from a challenging candidate library faster or more accurately than strong simulated-spectrum correlation/peak search-match (with equal candidate library and the same non-oracle chemistry)?
- This differs from low-dimensional known-phase parameter refinement and seven-crystal-system classification. However, multiple strong recent systems (XQueryer, XCCP and 2026 PXRD-Bench/X2SBench/RealBind) are close prior art; RealBind reports strong model-free retrieval, so **do not assume learned retrieval wins**.
- Gate: independently verify access, rights, exact pattern-to-structure pairs and leak-safe candidate library / splits before training. No whole-structure generation thesis on an undergraduate schedule.

## Short feasibility order

1. Spend up to 2–4 days on read-only **data viability and literature overlap**, not model development: RRUFF Raman XRD pairing audit; Raman excitation/instrument domain audit; optionally recent benchmark access/reproduction. Log exact counts and independent group distribution.
2. Decide **one** primary topic after both scientific feasibility and supervisor's independent new-project requirements are confirmed.
3. Predeclare strong physical/reference baseline and independent held-out real evaluation; build a small deterministic baseline before ML; run a small paired pilot and only then commit 8–12 weeks.
4. Preserve previous completed work as separate work and do not reframe 2026-10-19 speculative questions as completed novel findings.

## Evidence and precedent links (verify publication versions)
- RRUFF downloads: https://www.rruff.net/about/download-data/
- RRUFF instruments: https://www.rruff.net/about/equipment/
- Raman prior art: https://pubs.acs.org/doi/10.1021/acsearthspacechem.5c00136 and https://pubs.acs.org/doi/10.1021/acs.analchem.4c01581
- RealBind preprint (2026-09): https://doi.org/10.26434/chemrxiv.15009668/v1
- X2SBench (2026-09): https://arxiv.org/abs/2609.29751
- PXRD-Bench (2026-10): https://arxiv.org/abs/2610.16480
