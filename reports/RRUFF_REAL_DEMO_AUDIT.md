# Local RRUFF real-spectrum demo audit

**Date:** 2026-10-19

**Result:** PARTIAL / `real_demo_requires_better_forward` for both samples. The opt-in data adapter and local overlays work; the bundled candidate library does not contain either measured composition, so neither run is phase validation.

## Source and safety

- Read-only source root: `E:\AI4science\xrd_robustness\data\real_xrd\rruff371`.
- Accepted IDs: R050045 Fluorite CaF2 and R060745 Rutile TiO2. Both are verified as `adaptation_pool`; the adapter rejects every other ID, including locked-test IDs.
- Input files are RRUFF-371 resampled measured patterns on 10–80 degrees at 0.02-degree spacing. The manifest SHA-256 is checked before parsing.
- The recorded wavelength triplet is #1=1.541838, #2=1.540562 and #3=1.544390 Å. The measured DIF/profile wavelength #1 is used for routing and matches the frozen simulator's CuKa wavelength (1.54184 Å). Wavelength #2 is the separately reported refinement-reference wavelength. It is not used for fitting the observed profile.
- Refinement cells were refined against the same sample patterns. They were excluded from initialization, parameter bounds, scoring, candidate selection and ranking, then used only for the posthoc comparison below.
- `CITATION_AND_RELEASE_POLICY.md` says spectrum and DIF/refinement contents are local research material and redistribution rights are not asserted. No raw RRUFF spectrum, DIF/refinement text, data table, private local metadata or overlay image is tracked in Git. Cite Lafuente et al., *The power of databases: The RRUFF project* (2016), DOI `10.1515/9783110417104-003`.
- The frozen `rruff301_adaptation_test_split.csv` was not changed. No locked-test spectrum, DIF, refinement, or model output was read for this demo.

## Observed results

| RRUFF sample | Held posthoc cell (Å) | Best bundled candidate | Fit RMSE | Solver | Fitted cell (Å) | Posthoc comparison |
|---|---|---|---:|---|---|---|
| R050045 Fluorite CaF2, cubic Fm-3m | a=b=c=5.46445 | MgO rocksalt Fm-3m | 0.055150 | converged | a=4.211059 | a: −22.94% |
| R060745 Rutile TiO2, tetragonal P42/mnm | a=b=4.6134, c=2.9748 | MgO rocksalt Fm-3m | 0.047882 | **failed**: 60-evaluation cap | a=4.208126 (cubic model) | a: −8.78%; fitted cubic `a` versus held tetragonal `c`: +41.46% |

CeO2 fluorite ranked second for both, with RMSE 0.055214 (Fluorite) and 0.048312 (Rutile); BaTiO3 ranked third with RMSE 0.058446 and 0.051093. These uncalibrated metrics are not confidence or accuracy measures. The overlays show peak-position/intensity residuals that the neutral-atom Gaussian forward model does not explain. The modest RMSE values reflect sparse normalized profiles and do not establish an adequate match. CaF2 is not CeO2: a shared fluorite prototype does not establish shared chemistry or phase identity.

The observed/model/residual plots were regenerated with wavelength #1 for visual inspection at `reports/_local_rruff_overlays/R050045_overlay.png` and `reports/_local_rruff_overlays/R060745_overlay.png`; that directory is ignored by Git. The app draws the same diagnostics interactively when the user supplies the local data root.

## Frozen seven-system classifier check

The read-only checkpoint `seed_20260711_js_lambda_60/best.ckpt` has SHA-256 `3ee1beb8831e46a8d701435d5c1adfac49b7fe8959894811c1cb559b2cc6b49`. The model implementation SHA-256 is `2d048344865bbe5667bb235d8d3c851a9d6eea60fc1835f722bf0b10114ce276`; the label-source SHA-256 is `745c020dacf4c4214d1f17edf902012784487240c56d02fd1c43e158c458b655`. Its config and state dict loaded strictly through the project ResNet18-GN source on CPU. Input preprocessing was max normalization only, on the checkpoint's exact 3501-point 10–80-degree axis and frozen simulator CuKa wavelength 1.54184 Å. The highest-probability output was **triclinic** for both measured examples (manifest labels: cubic and tetragonal, respectively). This is an exploratory zero-shot failure on these two samples, not a measured performance estimate. The classifier prior is opt-in and off by default; it never removes candidates.

## Template availability and decision

The existing library contains BaTiO3, MgO and CeO2, but no CaF2 or rutile CIF. COD records identify [CaF2 entry 9009005](https://www.crystallography.net/cod/9009005.html) and [rutile entry 1530150](https://www.crystallography.net/cod/1530150.html); network retrieval of CIF bytes failed in this host. COD records are CC0, with source-author attribution requested; see the [COD license page](https://www.crystallography.net/cod/). No template was fabricated or reconstructed from a same-sample RRUFF cell. CaF2 and CeO2 are chemically distinct despite both having a fluorite structure type. Add independently fetched, hashed COD templates only after provenance and bytes can be verified.

**Decision:** Keep both local RRUFF examples as opt-in ingestion/overlay demos, mark them `real_demo_requires_better_forward`, and leave real-spectrum phase validation **NOT DONE**. Existing BaTiO3, MgO and CeO2 synthetic demos remain unchanged. No frozen classifier, original data, or other worktree was modified.
