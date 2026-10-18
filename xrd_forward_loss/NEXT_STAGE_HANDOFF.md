# Next-Stage Handoff: PXRD Forward-Loss Pre-Refinement

## Completed

- Audited the published workflows of PQ-Net, DRNets, and CrystalShift; recorded reusable elements, licenses, data/code availability, and reproduction limits in [`RELATED_WORK_WORKFLOW.md`](RELATED_WORK_WORKFLOW.md).
- Reused the existing tetragonal CUDA float64 forward model and ResNet-18-GN in an isolated module under `xrd_forward_loss/`.
- Passed a two-coordinate lattice Jacobian/autograd/finite-difference gate and completed matched A/B smoke and three-seed preliminary training.
- Recorded the positive, negative, and degenerate engineering results in [`FORWARD_FEASIBILITY_REPORT.md`](FORWARD_FEASIBILITY_REPORT.md) and [`FORWARD_LOSS_PILOT_REPORT.md`](FORWARD_LOSS_PILOT_REPORT.md).

## What remains scientifically open

- The HfCd pilot is only a method-engineering example. It is not evidence for BaTiO3, PZT, KNN, or any experimental sample.
- The reconstruction term reduced spectral RMSE slightly but did not improve the mean two-coordinate parameter MAE in this three-seed pilot.
- Zero shift, peak width, background, texture, mixtures, independent-renderer behavior, and traditional-refinement initialization were not tested.
- The forward loss and ideal training profiles share the same renderer. Measurement perturbation was added independently, but this is not simulator-independent or experimental-domain validation.
- The collaborator's material family, nominal chemistry, phase candidates, instrument setup, and available reference refinements remain to be confirmed.

## First actions after the family is confirmed

1. Obtain the nominal composition, plausible phases, temperature/state, instrument wavelength/range/step, profile format, and any expert-refined reference patterns.
2. Curate and cite valid phase-specific CIFs; inspect occupancies, symmetry, temperature, and cell convention. Do not transfer the HfCd forward assumptions blindly.
3. Implement the needed phase forward equations and match them to an authoritative CPU renderer. Verify peak positions, structure-factor intensities, and profile transforms before ML.
4. Identify a conservative parameter set with full-rank, well-conditioned Jacobians over the allowed range. Add zero shift, width, or background only after separate identifiability and gradient checks.
5. Freeze a parent/prototype-grouped split before simulation or training. Do not mix anonymous near-duplicate prototypes across train/validation/test. Reserve the collaborator's spectra and any independent renderer for one-time external cases.
6. Re-run paired A/B with shared architecture/data/steps and validation-only lambda selection. Add a physics-only candidate fit / local-refinement baseline and compare initialization success under the same optimizer budget.
7. Report parameter MAE, clean/noisy profile error, robustness to measurement mismatch, seed spread, failures, compute, and uncertainty. Treat a lower residual without lower parameter error as a tradeoff, not a win.

## Suggested 12-week sequence

| Weeks | Work | Gate / deliverable |
|---|---|---|
| 1–2 | Confirm family and instrument; curate CIFs; validate forward profiles and parameter identifiability; freeze prototype-aware splits | Gate 1: physical profile and gradient checks pass; parameter set is identifiable |
| 3–4 | Generate versioned simulation library with controlled perturbations; implement baseline A; establish physics-only local fitting | Gate 2: data provenance, split audit, baseline recovery, and fit budget are reproducible |
| 5–6 | Implement B as the sole loss intervention; validation-only lambda selection; matched multi-seed pilot | Gate 3: A/B comparison is finite, fair, and failure-audited |
| 7–8 | Test peak overlap, noise/background/width variation and plausible single-phase mismatch; test local refinement from NN initial values | Gate 4: parameter and residual changes are interpreted together |
| 9–10 | Freeze protocol/checkpoints; compare A, B, and physics-only under equal refinement budgets; do limited mixture/reject review stress tests if physically justified | Gate 5: no post-test tuning; document where assumptions fail |
| 11–12 | Evaluate a small untouched set of experimental cases if available; prepare reproducible report, figures, and next-step recommendation | Final: application-bounded conclusions with negative results and limitations retained |

The forward-loss pilot is a feasibility result only. The family-specific study starts at Week 1 after sample/material information is available; the HfCd pilot does not consume or replace those 12 weeks.
