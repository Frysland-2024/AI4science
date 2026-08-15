# Robust Physics-Guided Lattice-Parameter Inversion from PXRD

**Status:** `SEALED_FUTURE_MODULE`
**Design date:** 2026-08-15
**Execution profile:** prospective four-week prototype
**Active V9 affected:** no
**Relationship to earlier draft:** conceptual successor to the 2026-08-13 joint sample–instrument inversion draft; the earlier file is preserved as project-history evidence rather than overwritten.

## 1. Scientific correction and design decision

The primary scientific target of the one-month inverse project is **not** instrument-error recovery. The project should ask a cleaner materials question:

> Given a known phase / nominal structural template, can lattice parameters be recovered accurately from PXRD patterns, and can that recovery remain reliable under realistic measurement perturbations?

The core inverse target is therefore the lattice geometry itself. For a first tetragonal prototype,

\[
y\;\longrightarrow\;(\hat a,\hat c).
\]

Noise, background, peak broadening, intensity variation and small axis/peak-position shifts are treated primarily as **measurement nuisances used for robustness stress tests**, not as scientific prediction targets.

This deliberately replaces the earlier preferred minimum target `(epsilon_iso, global_zero_shift)` with the more standard and interpretable crystallographic target `(a,c)`. The older proposal is retained because it records an important intermediate stage in the project reasoning.

## 2. Why this is continuous with the existing XRD project

The broader project has progressively changed how physical knowledge is used by machine learning:

1. **Physics-informed data generation:** use crystallographic simulation and physically motivated perturbations to construct training observations.
2. **Physics-informed relational supervision:** JS Consistency uses the known fact that multiple perturbed patterns can share one parent crystal and should retain compatible predictions.
3. **Physics-constrained inverse inference:** predicted lattice parameters must be compatible with the diffraction geometry that links `(a,c)` to `d_hkl`, Bragg angles and the expected diffraction pattern.

The common research question is:

> **How can scientific facts that are already known a priori be converted into useful machine-learning supervision, rather than using only ordinary class or parameter labels?**

This makes the inversion module a natural continuation of the current project rather than an unrelated application switch.

## 3. Minimum physical model

For a known tetragonal prototype with fixed fractional coordinates, reflection identities and wavelength,

\[
\frac{1}{d_{hkl}^2}=\frac{h^2+k^2}{a^2}+\frac{l^2}{c^2},
\]

followed by Bragg's law,

\[
2d_{hkl}\sin\theta_{hkl}=\lambda.
\]

Thus the forward chain is

\[
(a,c)\rightarrow d_{hkl}\rightarrow 2\theta_{hkl}\rightarrow \mu(2\theta),
\]

and the inverse-learning task is

\[
y(2\theta)\rightarrow(\hat a,\hat c).
\]

The one-month prototype assumes that phase identity / nominal template is known. It does **not** attempt full ab-initio structure solution, atomic-coordinate recovery, occupancy refinement, phase-fraction refinement, microstrain separation, crystallite-size inference or complete Rietveld refinement.

## 4. Core hypotheses

### H1 — quantitative inversion is learnable
A 1D ResNet can regress `(a,c)` from simulated PXRD of one known tetragonal prototype with substantially lower error than constant/median baselines and with agreement to a conventional physics-based fitting reference.

### H2 — measurement robustness matters for inversion
A model trained only on ideal/clean patterns will degrade under realistic perturbations, while perturbation-aware training should reduce lattice-parameter error under these shifts.

### H3 — explicit physical supervision may improve robustness / data efficiency
Adding a forward-physics consistency term to ordinary parameter regression may improve lattice-parameter recovery under perturbation or reduced-label settings without materially degrading clean-domain recovery.

H3 is a hypothesis, not an assumed positive result.

## 5. Learning objectives

### Baseline: supervised lattice regression

\[
(\hat a,\hat c)=G_\theta(y),
\]

with

\[
L_{\rm param}=\operatorname{Huber}(\hat a,a)+\operatorname{Huber}(\hat c,c)
\]

after target standardization.

### Physics-guided variant

The prediction is passed through a differentiable crystallographic forward model:

\[
(\hat a,\hat c)\rightarrow \hat\mu(2\theta).
\]

The working objective is

\[
L=L_{\rm param}+\lambda L_{\rm phys}.
\]

`L_phys` must be defined so that it rewards physically correct diffraction geometry rather than blindly matching nuisance-corrupted intensity point-by-point. Candidate implementations, in increasing complexity, are:

1. **peak-position / d-spacing consistency** on registered reflections;
2. **canonical-pattern consistency** against the nuisance-free expected pattern available in synthetic training;
3. **nuisance-aware forward consistency** in which known synthetic augmentation state is used only inside the renderer, while nuisance variables remain non-targets;
4. later, a nuisance-invariant discrepancy suitable for unlabeled or experimental observations.

Ordinary raw-spectrum MSE against a heavily perturbed observation is **not** automatically valid, because correct lattice parameters can coexist with background, broadening or axis-shift mismatch.

## 6. Four-week roadmap

### Week 1 — establish the inverse problem before ML novelty

- freeze one tetragonal prototype and physically reasonable `(a,c)` box;
- generate PXRD while preserving exact lattice labels;
- verify the `(a,c) -> d_hkl -> 2theta` implementation against `pymatgen` or another trusted reference;
- implement conventional least-squares / peak-position fitting for `(a,c)`;
- perform simple identifiability / collision checks over the chosen parameter range;
- produce plots showing how independent changes in `a` and `c` move different reflection families.

**Gate:** if `(a,c)` cannot be reliably recovered from clean/high-SNR synthetic patterns by the physics baseline, do not proceed by merely increasing neural-network capacity.

### Week 2 — supervised neural inversion

- reuse the existing 1D ResNet encoder where practical;
- replace the classification head with a two-output regression head;
- train on clean / mild-noise patterns;
- report `MAE_a`, `MAE_c`, relative error, bias and error surfaces across the `(a,c)` parameter box;
- compare with constant/median predictor and conventional fitting.

**Minimum month-end fallback result:** a technically correct PXRD-to-lattice-parameter regression prototype.

### Week 3 — robust quantitative inversion

Introduce measurement variation while keeping the scientific target fixed at `(a,c)`:

- count/read noise;
- peak broadening / profile change;
- background change;
- intensity / preferred-orientation-like modulation where defensible;
- small peak-axis / zero-position shift as a stress test, not a prediction target.

Compare clean-trained and perturbation-trained inversion under matched clean and perturbed evaluations.

**Primary question:** does measurement-aware training preserve quantitative lattice recovery under nuisance shifts?

### Week 4 — physics-guided supervision

Compare the same backbone under exactly two principal objectives:

1. supervised parameter regression;
2. supervised regression + forward-physics consistency.

If feasible, include one frozen reduced-label stratum to test whether physical supervision becomes more useful when direct parameter labels are limited.

Evaluate on:

- clean ID;
- registered perturbation ID;
- stronger-noise / broader-profile OOD;
- parameter-range OOD;
- at least one renderer/operator mismatch (e.g. Gaussian training peaks vs pseudo-Voigt or angle-dependent-width evaluation).

Write a short technical report that distinguishes parameter-recovery gains from mere spectral-fit gains.

## 7. Minimal experiment matrix

| Training / objective | Clean evaluation | Perturbed evaluation | OOD / renderer mismatch |
|---|---:|---:|---:|
| clean supervised ResNet | required | required | required |
| perturbation-aware supervised ResNet | required | required | required |
| perturbation-aware + physics consistency | required | required | required |

Primary metrics: `MAE_a`, `MAE_c`, normalized/relative error and bias. Spectral residual is secondary and must never substitute for parameter-recovery accuracy.

## 8. Scope boundaries for the one-month version

Explicitly out of scope unless the core finishes early:

- predicting instrument zero shift as a scientific target;
- FWHM / crystallite size / microstrain decomposition;
- background coefficients as outputs;
- occupancy or atomic-coordinate refinement;
- phase fraction / multiphase quantification;
- full Rietveld refinement;
- new Transformer/diffusion architecture research;
- Bayesian uncertainty or MCMC;
- general all-crystal-system indexing.

The point of the prototype is to learn the inverse-problem paradigm cleanly, not to reproduce an entire crystallography software stack.

## 9. Working novelty position

The literature already establishes that neural networks can predict lattice/unit-cell parameters directly from powder diffraction. Therefore **"CNN predicts lattice constants from PXRD" is not a novelty claim**.

The present working novelty hypothesis is the combination of:

- known-template quantitative PXRD lattice-parameter inversion;
- explicit study of robustness under measurement perturbations;
- a forward crystallographic relation used as an additional learning constraint/supervision signal;
- a controlled comparison against the same backbone without that physical supervision.

This position is provisional and requires a fuller literature review before any novelty claim is made.

## 10. Literature reconnaissance — 2026-08-15

### Direct precedents: PXRD -> lattice/unit-cell parameters

1. **Chitturi et al., 2021, Journal of Applied Crystallography** — *Automated prediction of lattice parameters from X-ray powder diffraction patterns*. 1D CNNs predict lattice parameters by crystal system and explicitly study realistic experimental non-idealities. DOI: `10.1107/S1600576721010840`.
   - Directly relevant to the supervised-regression baseline and robustness question.

2. **Vamvakeros et al., 2021, npj Computational Materials** — *A deep convolutional neural network for real-time full profile analysis of big powder diffraction data* (PQ-Net). Predicts quantitative diffraction parameters including lattice parameters and crystallite size, with simulated and experimental validation. DOI: `10.1038/s41524-021-00542-4`.
   - Establishes fast quantitative regression from powder diffraction and comparison to full-profile/Rietveld analysis.

3. **Gómez-Peralta, 2023, J. Phys. Chem. A** — *Convolutional Neural Networks to Assist the Assessment of Lattice Parameters from X-ray Powder Diffraction*. CNN-based lattice-parameter estimation from simulated patterns, including experimental checks. DOI: `10.1021/acs.jpca.3c03860`.
   - Another direct baseline precedent; confirms that simple direct lattice prediction is already established.

4. **Shu et al., 2025, Journal of Chemical Information and Modeling** — *Machine Learning Tackles the Challenge of Powder X-ray Diffraction Indexing for All Crystal Systems*. AIdex jointly predicts symmetry/extinction group and unit-cell parameters and tests robustness to zero shift/noise. DOI: `10.1021/acs.jcim.5c01506`.
   - Important recent reference for robust unit-cell inference, though the task is broader indexing rather than known-template lattice regression.

5. **Mun, Nam & Choi, 2026, Journal of Applied Crystallography** — *Automation of Rietveld refinement through machine learning*. CNNs predict structural/profile parameters from simulated PXRD and are validated on experimental CeO2, Tb2BaCoO5 and PbSO4. DOI: `10.1107/S1600576726001494`.
   - Shows the field is moving toward automated quantitative refinement; useful for positioning the one-month project as deliberately narrower than full Rietveld automation.

6. **Hofgard et al., 2026, arXiv:2607.21829** — *Learning Lattice Parameters from Powder X-Ray Diffraction Data Using Invariants*. Introduces an invariant reciprocal-lattice target and reports substantially better lattice prediction than direct cell-parameter regression on MP-20, with RRUFF evaluation.
   - Very recent and highly relevant to representation/target-design questions; should be followed closely before implementation.

### Methodological bridge: physics-forward supervision in diffraction

7. **Luo et al., 2025, npj Computational Materials** — *DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis*. A physics-aware autoencoder predicts lattice strain and tilt, sends those latent physical parameters through a differentiable X-ray forward-scattering model, and trains against measured diffraction without requiring ordinary labels. DOI: `10.1038/s41524-025-01860-7`.
   - This is the clearest methodological analogue found so far for the proposed idea: physical quantities are inferred from diffraction and constrained through a differentiable forward model. The modality is scanning nanodiffraction rather than 1D powder XRD.

8. **Hybrid physics-machine learning models for quantitative electron diffraction refinements**, Nature Communications (2026). Integrates differentiable diffraction simulation with trainable neural components for quantitative 3D electron-diffraction refinement. DOI: `10.1038/s41467-026-71673-9`.
   - Adjacent modality but strong evidence that differentiable diffraction physics + ML is an active quantitative-refinement paradigm.

### Existing project-lineage reference

9. **Oviedo et al., 2019, npj Computational Materials** — *Fast and interpretable classification of small X-ray diffraction datasets using data augmentation and deep neural networks*. Uses physics-informed augmentation for XRD classification. DOI: `10.1038/s41524-019-0196-x`.
   - Useful as an earlier example of using known measurement/physics structure at the data-generation level, contrasting with the proposed move toward physics as direct inverse-learning supervision.

## 11. Application narrative

A concise future application story is:

> The project began by using physical simulation to generate realistic training observations, then used known same-origin relationships between simulated measurements as relational supervision, and finally extended this principle to quantitative inverse learning, where predicted physical parameters must remain consistent with the forward diffraction law. The broader theme is converting known scientific structure into machine-learning supervision.

Conceptually:

\[
\text{physics-informed data}
\rightarrow
\text{physics-informed relational supervision}
\rightarrow
\text{physics-constrained quantitative inference}.
\]

This progression is more important than any one architecture choice and provides a bridge from PXRD robustness toward broader scientific inverse problems and measurement science.
