# Related Work and PXRD Workflow Audit

**Scope:** method and implementation review for the isolated forward-reconstruction-loss pilot. This is a workflow adaptation, not a reproduction of any one published model.

## PQ-Net (Dong et al., 2021): primary regression workflow

PQ-Net shows a practical path from a simulator-backed PXRD library to rapid continuous parameter prediction. Its published task assumes known candidate phases and sample composition, and predicts scale factors, lattice parameters, and crystallite size from full profiles. The paper compares simulated predictions with experimental XRD-CT data and uses Rietveld results as a reference for a subset of measurements. It presents the network as a fast predictor and refinement initializer, not as a replacement for Rietveld refinement or an unknown-phase discovery system.

The transferable workflow is:

1. define a limited candidate structure/phase set and physical parameter ranges;
2. generate profiles with a named physical simulator and save parameter labels;
3. normalize continuous targets using known training-range bounds;
4. train a 1D CNN with a regression loss and fixed validation/test protocol;
5. compare parameter error and runtime with conventional profile refinement or its outputs;
6. treat simulated and experimental evaluations as different evidence domains.

The paper reports a convolutional pattern encoder and phase-specific branches, Adam at `0.0005`, target rescaling to `[0, 100]`, and MAE. For the five-phase experiments, it reports 100,000 simulated training profiles and a 10% validation subset. The experimental comparison uses an ensemble of 10 models. Those details inform this pilot's target scaling, learning-rate scale, regression framing, and separation of simulation from experimental evidence; the present pilot uses the repository's ResNet-18-GN, two lattice coordinates, one known structure, and a matched three-seed comparison instead of reconstructing the full PQ-Net architecture or five-phase workflow.

**Availability audit:** the 2021 article says code is available from the authors on reasonable request; the original Zenodo record exposes the paper's data (CC BY 4.0) but not the original training code or weights. Therefore this work does not claim to run or reproduce official PQ-Net code. A later 2025 Zenodo record provides a larger XRD library and weights, but it is not the original 2021 implementation. The article's TOPAS/MATLAB data-generation path is also not fully reproducible from the public package alone.

Sources: [npj Computational Materials article](https://www.nature.com/articles/s41524-021-00542-4), [supplementary information](https://static-content.springer.com/esm/art%3A10.1038%2Fs41524-021-00542-4/MediaObjects/41524_2021_542_MOESM1_ESM.pdf), [original Zenodo dataset](https://zenodo.org/records/4664597), and [later 2025 data/weights record](https://zenodo.org/records/16531261).

## DRNets (Chen et al., 2021): reconstruction plus constraints

DRNets addresses unsupervised phase-diagram decomposition, not supervised continuous refinement-parameter regression. Its networks reconstruct the measured map from component patterns and combine reconstruction with constraint reasoning; the paper also describes entropy relaxations and constraint-aware optimization. The applicable idea here is to let a differentiable forward reconstruction term send gradients through a learned prediction. The pilot does not transfer DRNets' phase decomposition, mixture model, constraint solver, or objective wholesale.

The public [DRNets repository](https://github.com/gomes-lab/DRNets-Nature-Machine-Intelligence) is MIT-licensed. Its historical environment uses PyTorch 0.4.1 and TensorFlow 1.8, so it is a methodological reference rather than a directly reused dependency. The paper and [CaltechAUTHORS record](https://authors.library.caltech.edu/records/98z81-3ev19) provide supplementary material/source-data links. Data terms are recorded separately from the repository's code license; the code license must not be assumed to license all linked datasets.

Sources: [Nature Machine Intelligence article](https://www.nature.com/articles/s42256-021-00384-1), [author PDF](https://dichen9412.github.io/papers/DRNets_NMI.pdf), and [repository](https://github.com/gomes-lab/DRNets-Nature-Machine-Intelligence).

## CrystalShift (Chang et al., 2025): physics-only reference

CrystalShift is a physics-only candidate-phase and lattice-refinement workflow. Given candidate CIFs, it searches single-/multi-phase hypotheses, performs symmetry-constrained lattice optimization, forward-simulates patterns, and compares hypotheses probabilistically. It is a useful precedent and potential physics-only baseline. It is not a neural-regression workflow and its fixed candidate structures, symmetry assumptions, and nuisance treatment are not a drop-in model for ferroelectric distortions or all instrument effects.

The public [CrystalShift.jl repository](https://github.com/MingChiangChang/CrystalShift.jl) is MIT-licensed and is a Julia implementation. The paper's [CaltechAUTHORS record and supplemental/source-data record](https://authors.library.caltech.edu/records/y73e9-s4578) links its associated material data; the repository license alone does not establish the license for those data. This pilot neither ports CrystalShift nor compares against it. A later physics-only comparison must pin a specific release/data snapshot and matching physical support.

Source: [npj Computational Materials article](https://www.nature.com/articles/s41524-025-01627-0), [repository](https://github.com/MingChiangChang/CrystalShift.jl), [repository license](https://github.com/MingChiangChang/CrystalShift.jl/blob/main/LICENSE), and [supplemental record](https://authors.library.caltech.edu/records/y73e9-s4578).

## Reuse boundary

| Element | Status in this project |
|---|---|
| Simulator-driven profile/parameter pairs, continuous regression, target-range scaling, validation selection, parameter MAE | Workflow adapted from PQ-Net; not a reproduction |
| Differentiable profile reconstruction sends gradients through predicted lattice coordinates | Borrowed methodological pattern; related to DRNets but adapted to supervised known-structure regression |
| ResNet-18-GN from `xrd_robustness` with a two-coordinate continuous head | Existing repository implementation reused |
| `CachedTetragonalGPUForward` structure factors, Bragg positions, Gaussian peaks, transform | Existing repository implementation reused; pilot restricts it to one known tetragonal parent and two lattice coordinates |
| Poisson-count measurement noise plus a small linear background; one-parent randomized q split; validation-selected lambda; matched seed pilot | Independent pilot design choices; explicitly scoped to method engineering |
| Full PQ-Net architecture/data protocol, DRNets phase decomposition, CrystalShift model evidence/refinement | Not reproduced |

The pilot's training target and reconstruction target both originate from the same ideal forward renderer, with a separately generated measurement perturbation applied to the observed profile. This tests whether the extra loss changes parameter estimation under this controlled mismatch. It does not establish simulator-independent or experimental-domain performance. No novel-algorithm claim is made for the reconstruction loss itself.
