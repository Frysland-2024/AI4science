# PXRD AutoLab — Garnet Real-Spectrum Pilot

**Date:** 2026-10-19 · **Status:** `PHYSICS_MODEL_NOT_READY` · **Code base:** Draft PR #37, continued on an isolated stacked branch.

**Scope:** Three local-only experimental Grossular powder spectra; known phase, one cubic lattice parameter, no neural network training.

## Decision

The structure-based forward model explains most strong peak positions and returns lattice constants within 0.09–0.11% of the later-read RRUFF refinements. It does not yet pass the physical readiness gate: for all three spectra, five physically bounded starting points converge to materially different lattice minima, and the residuals retain strong intensity mismatch. Preserve this as a real-spectrum physics diagnostic and stop here. Do not begin simulated training or Few-shot Domain Adaptation from this pilot.

## Candidate audit and development samples

The local audit's 44 strong Garnet rows are a screening count, not 44 independent training examples. The audit itself establishes no independent adaptation test. Removing the mixed-phase R060125 and the four frozen-test IDs R040159, R060452, R061041, and R060446 leaves 39 development candidates before grouping by mineral chemistry, locality/source, and exact spectrum. The selected samples below have distinct base IDs and localities; they are Grossular records only. No XY_RAW, DIF, or refinement member for any frozen-test sample was opened.

| RRUFF sample | Measured chemistry (RRUFF record) | Locality | Input profile |
|---|---|---|---|
| R040066-1 | (Ca2.90 Fe2+0.08 Mn0.02)(Al1.87 Fe3+0.13)(Si1.00O4)3 | Redding, Connecticut, USA | Experimental powder; 8,500 points; 5–89.99° |
| R050036-1 | (Ca2.95 Mg0.05)(Al1.70 Fe3+0.30)(Si1.00O4)3; trace P | Wah Wah Mountains, Utah, USA | Experimental powder; 8,501 points; 5–90° |
| R060382-1 | (Ca2.95 Mg0.03 Mn0.02)Al2.00((Si0.99 Ti0.01)O4)3; trace Fe | Lalatema near Kilimanjaro, Tanzania | Experimental powder; 8,501 points; 5–90° |

Each local XY_RAW member matched the audit-manifest SHA-256. The app reads only its increasing numeric two-column trace; it ignores all header metadata, including the same-sample cell values. Each exact-ID profile and refinement member remains in the official local RRUFF archives. The wavelength used was RRUFF wavelength #1, 1.541838 Å; the profile headers do not contain wavelength. The source refinement files also list #2=1.540562 Å and #3=1.544390 Å, but those are read only after all selected fits have completed.

## Independent structure and physical model

The template is [COD Grossular record 9001871](https://www.crystallography.net/cod/9001871.html), source AMCSD, credited to Geiger and Armbruster, *American Mineralogist* 82 (1997), 740–747. It reports the ideal endmember Ca3Al2Si3O12, space group Ia-3d (No. 230), and a=11.619 Å at 293 K. The local file is `pxrd_router_mvp/candidates/Grossular_COD_9001871.cif`, SHA-256 `EBDD9ABB0BB717A8154EE25B00E26E4AA69F9261EAAFA56B02FE77E30E3AFFD6`. Its cell comes from this independent published structure, not from a target RRUFF specimen or a metric-ranked CIF list. The target formulas remain distinct in the material profiles; the ideal endmember template is not asserted to match their substitutions exactly.

The Garnet path uses `pymatgen.analysis.diffraction.xrd.XRDCalculator` to calculate structure-factor powder reflections from the CIF. Cubic d-spacings are updated with the trial `a`; Lorentz-polarization is recalculated for the shifted line positions. The fitted profile uses a single RRUFF wavelength, Gaussian line width, zero shift, scale, and linear background. Atomic form-factor values are held at the independent CIF reference geometry during the one-parameter lattice search. This bounded profile model is not a full Rietveld refinement and does not model the Kα doublet, texture, absorption, or sample-specific microstructure.

Before reading any target refinement file, the pilot fixed: a ±5% search interval around the COD cell; five starts at −4%, −2%, 0%, +2%, and +4%; a fixed-CIF-cell baseline with nuisance parameters refit; and a readiness gate requiring solver convergence, a multistart spread ≤0.02 Å, an interior minimum, normalized profile RMSE ≤0.05, posthoc lattice error ≤1%, and at least 80% of strong measured peaks matched within 0.20°. Strong peaks use normalized prominence ≥0.05. The same-sample refined `a` is opened only after the optimization phase and is never passed into the fit or candidate/template selection.

## Real-spectrum results

| Sample | COD `a0` (Å) | Fixed-`a0` RMSE | Predicted `a` (Å) | Posthoc RRUFF `a` (Å) | Δa (Å / %) | Fit RMSE | Strong peaks | Start spread (Å) | Solver | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| R040066-1 | 11.6190 | 0.034457 | 11.876720 | 11.866500 | +0.010220 / +0.0861% | 0.017725 | 18/19 | 0.545876 | `ftol`, status 2, 15 evaluations | `PHYSICS_MODEL_NOT_READY` |
| R050036-1 | 11.6190 | 0.030739 | 11.897951 | 11.885100 | +0.012851 / +0.1081% | 0.012285 | 15/15 | 0.846165 | `ftol`, status 2, 25 evaluations | `PHYSICS_MODEL_NOT_READY` |
| R060382-1 | 11.6190 | 0.030415 | 11.864413 | 11.852600 | +0.011813 / +0.0997% | 0.016637 | 20/21 | 0.674013 | `ftol`, status 2, 53 evaluations | `PHYSICS_MODEL_NOT_READY` |

For R040066-1, the fixed independent COD cell with nuisance refitting gives normalized RMSE 0.034457. The best multi-start fit lowers it to 0.017725. Its parameters are zero shift +0.064306°, FWHM 0.129752°, scale 0.723915, and affine background 0.016252 − 0.004185·xnorm. The RRUFF posthoc reference is 11.866500 Å; the absolute error is +0.010220 Å. The RRUFF output's own reported fit RMSE is `7.186536e-05` in its source units; it is not comparable to the pilot's normalized profile RMSE, and no `a` standard error was available in the parsed record.

The R040066-1 start results were: 11.15424→11.94217 Å (weighted RMSE 0.081888), 11.38662→11.42464 Å (0.081860), 11.61900→11.97052 Å (0.081888), 11.85138→11.87672 Å (0.041414), and 12.08376→11.77586 Å (0.081888). Only the +2% start reached the distinctly lower-residual basin. Its largest absolute normalized residual is 0.7257 at a strong line; 99% of absolute residuals are ≤0.0617. All three records show this same optimizer instability: each best solution meets the posthoc error and peak-coverage checks, but none meets the predeclared multistart agreement requirement. Do not read the low lattice error as proof of a reliable physical inverse.

The actual measured/profile/residual plots, full local CSVs, every solver attempt, CIF/member hashes, and JSON evaluation records are stored locally under the ignored `reports/_local_garnet_pilot/` directory. The tracked report contains summary evidence only; no raw RRUFF profile, refinement text, or generated full-resolution trace is included in Git.

## Gate and next work

**Successful:** the exact Grossular subgroup/CIF pairing gives the expected Ia-3d reflection positions; the best local solutions improve over the fixed-CIF baseline and agree closely with independently held posthoc `a` values. The initialization parameter is independent: COD `a0=11.619 Å` was used, while the RRUFF refined `a` was first read after the complete fitting phase.

**Failed:** the five-start optimizer is not robust to reasonable starting points; several starts remain near CIF-like fits with substantially worse residuals, while one basin dominates. Strong relative-intensity residuals remain despite high peak-position coverage. The model therefore does not yet provide a stable, physically adequate full-profile explanation. `PHYSICS_MODEL_NOT_READY` is the stopping status.

**Training readiness:** not ready for simulated training or Few-shot Domain Adaptation. Before generating training data, first identify why starts collapse into distinct basins using a frozen standard and a predeclared cell-only diagnostic; then validate intensity and instrument terms on independently sourced Grossular CIFs and held-out localities without consulting their refinement cells during model selection. Preserve the current three samples as development examples and reserve a separate grouped-by-locality test set.

Recommended order after the physics gate passes:

1. **Simulated training:** freeze composition-specific CIFs, ranges, measurement perturbations, and locality/CIF-grouped splits. Establish the deterministic physical multi-start baseline first; compare a learned initializer only on the untouched grouped test set.
2. **Few-shot adaptation:** define support/query roles by independent sample and locality, report 1/3/5-shot learning curves and uncertainty, and keep all locked classification test records excluded. Adapt only after the simulator-to-real mismatch has a measured error budget.
3. **AI initial-guess assistance:** let a model propose candidate-specific `a` and nuisance starts, then always run the same physical optimizer. Retain the optimizer-only baseline, reject out-of-range or high-residual suggestions, and show a review state when candidate chemistry or profile fit is ambiguous.

The existing BaTiO3/MgO/CeO2 routes, frozen seven-system classifier, their splits, checkpoints, and research conclusions are unchanged.
