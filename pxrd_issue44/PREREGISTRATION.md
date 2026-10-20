# Issue #44 protocol: known-candidate PXRD parameter inversion

**Frozen:** 2026-10-20, before this extension regenerates or scores any test observation. The machine-readable authority is `frozen_config.json`; this document and all code/data source hashes are sealed in the run manifest before full architecture training begins.

## Claim boundary and source fidelity

This is a bounded **architecture-transfer/adaptation** study for known-candidate lattice-parameter regression and physical refinement. It is not a source-faithful replication of XQueryer, SimXRD-4M, or PyWPEM: XQueryer and SimXRD-4M primarily classify structure/system/space group, while PyWPEM performs Bragg-constrained whole-pattern refinement. The available papers do not provide this exact known-CIF q-regression benchmark. `literature_matrix.md` records task, source, implementation commit snapshot, results, and limits.

## Immutable relationship to PR #43

PR43 MLP results and code are immutable. This extension uses only the seven materials supported in PR43 and references its already opened parent split (358/77/77) and 77 same-generator test parents per material. Those tests are **not new or independent**. The fixed CNN and Transformer configurations and paired seeds are recorded here before this extension regenerates the deterministic observations. All checkpoint selection is validation-only. The prior MLP N+A per-sample results are read-only historical comparators. The old MLP is not retrained; missing MLP-only checkpoints/predictions are not reconstructed.

The PR43 independent-renderer stress set is likewise already opened for its MLP comparison. The same fixed 16 new parents/material, independently rendered profiles, are reused for this extension and are explicitly exploratory. No performance result from either previously opened set is presented as confirmatory.

## Material support and physical gate

Materials: BaTiO3, MgO, CeO2, rutile, ZnO, silicon, and grossular. This is seven materials across cubic, tetragonal, and hexagonal systems; trigonal calcite and corundum remain unsupported and excluded. Before training, verify the exact CIF hashes and rerun the existing deterministic forward/parity/recoverability/site gates for each included CIF. A failed or unavailable gate stops that material; no gate relaxation or material substitution is allowed. New physical fits use the same frozen `PowderModel.fit` implementation, bounds, neutral nuisance start, optimizer tolerances, and stopping ceilings as PR43.

The simulator fixes fractional coordinates/occupancies to the candidate CIF, uses Cu wavelength 1.5406 Å, and models a single-phase kinematic Gaussian profile. It omits texture, instrumental doublet, multiphase overlap, and full Rietveld refinement. q is dimensionless and normalized by 0.02 relative lattice change. Report q MAE and each lattice DOF error in Å separately.

## Data, training, and comparison

Reuse the exact PR43 parent generator/split: 512 independent q parents, fixed 358 train / 77 validation / 77 previously opened test, and existing paired seeds. The nuisance and noise recipe is unchanged. Preprocessing is train-only. The two fixed architectures and three seeds are in `frozen_config.json`. Both train on the same 358 parents for 24 epochs, batch 32, Adam 0.001, q-MSE, gradient clip 5; choose lowest validation q-MAE (earliest epoch on tie). There is no model/seed search on test. Training uses the RTX 4060 Laptop GPU only if available, not occupied by another confirmed compute job, and at least 1 GiB VRAM is free. Inference is CPU, one profile at a time.

Before the full matrix, a fixed operational smoke uses BaTiO3, MgO, and ZnO; both architectures; seed 2026102020; 64 train parents, 32 validation parents, and three epochs. It creates no test observation and is excluded from any performance conclusion. Its GPU time counts against the same cumulative training and wall budgets.

Compare neural-only direct q, neural initialization plus the identical physics refinement, and physics-only P0/P3/P5. P0 uses one neutral start; P3 uses q starts [0, -0.5, +0.5]; P5 adds [-0.85, +0.85]. Every start uses the identical L-BFGS-B solver and limits, with all attempts, actual nfev, wall time, convergence, and boundaries retained. P3/P5 select by observed profile RMSE. Report the historical PR43 MLP and recomputed P0/P3/P5 on identical previously opened parents, with no cherry-picked wall-clock baseline. Runtime includes all starts and failed attempts; training is shown both separately and amortized over the fixed evaluation set.

The fixed ResNet1D and patch Transformer are architecture-inspired adaptations, not the original SimXRD/XQueryer source model. Their patching, residual blocks, parameter count, training updates, GPU time, inference time, checkpoints and code hashes are retained. No exact FLOP equality is claimed; practical fairness is paired parent data, labels, augmentations, optimizer/update budget, device, and physical-refinement budget.

## Stress, real data, budgets, and stop rules

Run the already opened PR43 independent-pymatgen stress profiles (16/material, Gaussian/Lorentzian mixture, quadratic background) only after all primary architecture checkpoints and selection records are hashed. Stress cannot rescue, replace, or select a primary conclusion. Real RRUFF remains blocked by the separate frozen gate: instrument wavelength and candidate identity are not verified, same-sample refined cells cannot select templates, the previous Grossular baseline is physically unstable, and classification locked-test data are not development data.

Use one serial manager lock and enforce <=8 hours wall, <=4 hours cumulative CUDA training, and <=10 GB output. Persist epoch checkpoints, optimizer state, JSONL curves/events, fit attempts, and test rows incrementally. Stop at the first budget, gate, hash, disk, GPU, or unknown-active-process violation; preserve failures and mark unfinished cells NOT_RUN. Do not interrupt another user process. No automatic retry after a test-open marker. No raw RRUFF spectra, private metadata, checkpoints, generated profile arrays, or secrets are committed.

## Interpretation and delivery

Report every material, architecture, seed, and q/cell DOF; preserve mixed and adverse cases. A neural accuracy increment requires every paired seed to improve P3 q-MAE by at least 5%, no per-DOF cell MAE worsening over 5%, and convergence no worse; P5 must be shown. A runtime increment requires actual measured end-to-end training/inference/refinement time and the same error/convergence constraints. These are descriptive predeclared gates, not significance tests. If they fail, say so. Synthetic results do not establish experimental accuracy, structure identification, causality, or generalization to unseen materials.

Repository output is this isolated branch only. Draft PR only; never merge automatically. If authentication prevents publication, preserve a tracked terminal report and state that publication is blocked.
