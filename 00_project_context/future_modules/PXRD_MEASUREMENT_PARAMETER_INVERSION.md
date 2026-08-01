# PXRD Measurement Parameter Inversion and Calibration

**Status:** `SEALED_FUTURE_MODULE`  
**Design date:** 2026-08-01  
**Active V9 affected:** no  
**Training authorized:** no  
**Simulated Test / real XRD access authorized:** no

> This document registers a future research module. It must not modify, reopen,
> or reinterpret the frozen V9 Dynamic ERM versus JS Consistency experiment.
> V9 remains a measurement-aware robust-classification study. This module asks a
> different question: whether measurement nuisance parameters can be inferred,
> calibrated, and assigned reliable uncertainty from perturbed PXRD patterns.

## 1. Research identity

### Working title

**PXRD Measurement Parameter Inversion and Calibration**

### Precise positioning

The first version is **measurement-parameter inference**, not complete crystal
structure inversion. It belongs to inverse-problem and measurement-science
research, but deliberately avoids claiming recovery of atomic coordinates,
space group, or a unique complete structure from one-dimensional powder data.

### Core research question

> Can measurement nuisance parameters be reliably inferred from perturbed PXRD
> patterns, under which observation conditions are they identifiable, and can
> explicit calibration improve downstream crystal-system classification?

### Relationship to V9

V9 and this module are complementary:

- **V9:** learn predictions that remain stable across label-preserving
  measurement variations;
- **this module:** explicitly infer, explain, and potentially correct those
  measurement variations.

The comparison eventually becomes:

1. invariance through dynamic augmentation;
2. invariance through JS consistency;
3. explicit nuisance inference and calibration.

This comparison is future work and is not part of the frozen V9 evidence chain.

## 2. Forward and inverse formulation

Let

\[
y = \mathcal{M}(s, \eta) + \varepsilon,
\]

where:

- \(s\) is the parent crystal structure and clean diffraction information;
- \(\eta\) contains measurement nuisance parameters;
- \(\mathcal{M}\) is the registered PXRD rendering and perturbation process;
- \(\varepsilon\) is stochastic observation noise;
- \(y\) is the observed perturbed pattern.

The first inverse task is

\[
\hat{\eta}=g_\theta(y),
\]

not

\[
\hat{s}=g_\theta(y)
\]

for complete structure recovery.

## 3. Version-1 target variables

Only parameters already produced and recorded by the simulator may become
supervision targets. The candidate target vector is

\[
\eta=(\delta, w, b, n),
\]

with:

| Target | Meaning | Initial task type |
|---|---|---|
| `zero_shift` \(\delta\) | global 2-theta zero offset | bounded regression |
| `broadening` \(w\) | registered effective peak-broadening parameter | bounded regression |
| `background_strength` \(b\) | registered background amplitude/scale | bounded regression |
| `count_noise_level` \(n\) | registered count scale or noise-strength proxy | log-scale regression |

Preferred orientation and structured background shape are excluded from the
minimal first version unless their simulator metadata have a stable,
unambiguous scalar or low-dimensional parameterization.

### Target-governance rule

A target is eligible only when all of the following hold:

1. the simulator writes it to a machine-readable manifest;
2. units and transformation are fixed;
3. train, Validation-ID, Validation-OOD, and future Test ranges are separated;
4. the target does not depend on hidden post-processing;
5. a one-parameter sweep passes forward-rendering sanity checks.

## 4. Scientific hypotheses

### H1 — heterogeneous identifiability

Different nuisance parameters will not be equally recoverable. Global zero
shift is expected to be more identifiable than parameters that alter peak shape
or noise statistics in partially confounded ways.

### H2 — degradation under information loss

Parameter error and predictive uncertainty should increase as information is
lost through lower SNR, fewer visible peaks, stronger peak overlap, stronger
background, or out-of-range perturbations.

### H3 — conditional confounding

Broadening, count noise, background, and intrinsic peak-density differences may
be partially confounded. Good average MAE does not prove physical
identifiability.

### H4 — calibration may help only selectively

Explicit correction may improve downstream classification for parameters with
stable inverse estimates, while uncertain or non-identifiable corrections may
harm classification or hallucinate detail.

### H5 — uncertainty must track failure

A trustworthy model should produce wider intervals or higher posterior variance
when the inverse task is ambiguous or OOD.

## 5. Experimental stages

### Stage 0 — metadata and forward-model audit

No neural training is allowed until this stage passes.

Deliverables:

- exact simulator target names, units, ranges, and transforms;
- parameter correlation matrix from generated metadata;
- single-parameter and paired-parameter sweeps;
- visual and numerical rendering sanity checks;
- collision search for distinct parameter settings producing near-identical
  patterns;
- frozen parent-structure split reuse without moving any structure across
  Train, Validation, or future Test.

**Gate 0 PASS:** all targets are traceable and rendering behavior is monotonic or
otherwise physically interpretable over the registered range.

### Stage 1 — single-parameter inversion

Train one model per target before joint multi-task learning.

Required baselines:

1. constant mean/median predictor;
2. hand-crafted signal-statistic baseline where meaningful;
3. 1D ResNet regression baseline using the frozen public backbone family;
4. optional lightweight peak-table baseline after a deterministic peak
   extractor is frozen.

Primary metrics:

- MAE and normalized MAE;
- RMSE;
- Spearman correlation;
- error by target bin;
- error by crystal system;
- error by peak count / overlap / SNR strata.

**Gate 1 PASS:** the learned model must outperform the constant baseline across
multiple registered seeds and must not obtain its result from structure leakage
or a single crystal-system subgroup.

### Stage 2 — joint nuisance inference

Use a shared encoder with target-specific heads:

\[
z=E(y), \qquad \hat{\eta}_k=h_k(z).
\]

Candidate objective:

\[
L_{\mathrm{inv}}=\sum_k \alpha_k L_k,
\]

where target transforms and loss scales are audited before choosing
\(\alpha_k\). No weight may be copied from an unrelated paper as a final value.

Compare:

- independent single-target models;
- shared encoder with independent heads;
- shared encoder with uncertainty-aware heads.

The goal is to determine whether multi-task learning exploits common measurement
features or creates negative transfer between confounded targets.

### Stage 3 — identifiability map

Construct a controlled evaluation grid over:

- SNR / count scale;
- visible-peak count;
- peak-overlap score;
- zero-shift magnitude;
- broadening magnitude;
- background magnitude;
- in-range versus OOD parameter ranges;
- single versus combined perturbations.

Required outputs:

1. parameter-wise error surfaces;
2. pairwise confusion/coupling analysis;
3. local sensitivity of the forward model;
4. examples of non-identifiable or weakly identifiable cases;
5. an `identifiability_status` label: `IDENTIFIABLE`, `WEAK`, `CONFOUNDED`, or
   `UNKNOWN` for each condition stratum.

This stage is the scientific center of the module. A high-capacity regressor
alone is insufficient.

### Stage 4 — uncertainty quantification

Minimum candidate methods:

- heteroscedastic Gaussian regression;
- deep ensemble or seed ensemble;
- conformal prediction on a locked calibration subset.

Required metrics:

- interval coverage probability;
- mean interval width;
- coverage-width trade-off;
- calibration error by condition stratum;
- OOD uncertainty increase;
- selective-risk curve when abstaining on uncertain cases.

A model is not considered trustworthy merely because its mean MAE is low.

### Stage 5 — explicit calibration and downstream classification

Only parameters passing Stage 3 and Stage 4 may be used for correction.

Compare under identical parent structures and evaluation panels:

1. raw Dynamic ERM classification;
2. V9 JS Consistency classification;
3. nuisance estimator plus deterministic correction plus classifier;
4. nuisance estimate provided as auxiliary context without modifying the
   spectrum;
5. uncertainty-gated calibration that abstains when inversion is unreliable.

Primary question:

> Is explicit estimation and calibration more effective than learning
> invariance, and under what nuisance and uncertainty regimes?

Calibration must obey a forward-consistency check. A corrected spectrum may not
be evaluated only by visual smoothness.

## 6. Data splitting and leakage control

- Reuse the frozen parent-structure split.
- All perturbation views of one parent remain in the same split.
- Parameter combinations may be resampled online, but the parent structure may
  never cross split boundaries.
- Validation-OOD parameter ranges must be frozen before model selection.
- Simulated Test remains locked until a one-shot contract is approved.
- Real XRD remains external validation and cannot be used to redefine simulator
  targets or retune the inverse model.

### Strong anti-shortcut audit

Because simulator parameter distributions can accidentally correlate with
crystal-system labels, Stage 0 must verify that nuisance sampling is label
independent unless an explicit physical conditional model has been registered.
A nuisance model that predicts parameters through class shortcuts fails the
module even when aggregate regression error is low.

## 7. Architecture policy

### Minimal default

Use the frozen ResNet family first. The purpose is to test the inverse problem,
not to win through a new backbone.

Suggested structure:

```text
perturbed PXRD
    -> ResNet encoder
    -> shared latent representation
    -> zero-shift head
    -> broadening head
    -> background head
    -> count/noise head
    -> optional uncertainty parameters
```

### Excluded from version 1

- diffusion restoration;
- complete crystal-structure generation;
- atomic-coordinate prediction;
- unrestricted denoising autoencoders;
- new Transformer/PAMPT backbone research;
- real-spectrum fine-tuning before simulated identifiability is established.

These exclusions prevent the module from becoming an untestable mixture of
inverse modeling, generation, classification, and architecture design.

## 8. Calibration operator policy

A parameter estimate is not itself a calibrated spectrum. Each correction must
be explicitly defined:

- zero shift: coordinate-axis inverse transform;
- background: subtract only a parameterized estimated background with
  non-negativity and smoothness constraints;
- broadening: no naive sharpening; use a registered deconvolution or
  forward-consistent latent comparison;
- count/noise: do not invent missing peak information.

Broadening correction is therefore not part of the minimal MVP unless a stable
physical inverse operator and uncertainty rule are available.

## 9. Minimum viable study

The smallest scientifically defensible implementation is:

1. audit and export simulator metadata;
2. select `zero_shift` and one background scalar;
3. train single-target ResNet regressors;
4. create an SNR/peak-count/OOD identifiability map;
5. add calibrated intervals;
6. test zero-shift correction on the frozen Validation panels;
7. compare raw ERM, JS, and uncertainty-gated zero-shift calibration.

This MVP deliberately postpones joint recovery of all nuisance parameters.

## 10. Success and failure criteria

### Successful module

The project succeeds if it produces a reproducible map of what can and cannot be
inferred, with calibrated uncertainty, even if some nuisance parameters are
shown to be non-identifiable.

### Scientifically valuable negative result

The module remains valuable if it shows that:

- a target is recoverable only in restricted SNR or peak-density regimes;
- two parameters are systematically confounded;
- explicit correction harms classification when uncertainty is ignored;
- invariance learning is safer than inversion for specific nuisances.

### Failure condition

The module fails if it reports only aggregate regression MAE, does not audit
parameter-label shortcuts, or treats a generated clean-looking spectrum as
proof of correct physical inversion.

## 11. Required repository artifacts before activation

Activation must create and freeze:

```text
xrd_robustness/configs/inversion_target_registry.yaml
xrd_robustness/configs/inversion_validation_profiles.yaml
xrd_robustness/configs/inversion_model_search_space.yaml
xrd_robustness/reports/inversion_stage0_forward_audit.md
xrd_robustness/scripts/export_inversion_metadata.py
xrd_robustness/scripts/train_inversion_baseline.py
xrd_robustness/scripts/evaluate_identifiability.py
```

No file above should be implemented merely because this design document exists.
Implementation requires a later explicit activation decision after V9
simulated-Test and external-validation boundaries are settled.

## 12. Application and research narrative

This module extends the project trajectory from robust prediction to trustworthy
scientific measurement inference:

```text
How is a scientific observation formed?
    -> Which latent measurement factors are recoverable?
    -> Under what conditions are they identifiable?
    -> How uncertain is the inverse estimate?
    -> Does explicit calibration improve scientific decisions?
```

The transferable research identity is:

> Reliable inference from imperfect scientific measurements through
> physics-based forward modeling, inverse problems, uncertainty quantification,
> and machine learning.

This identity can extend beyond PXRD to Raman, electron diffraction, 4D-STEM,
medical imaging, remote sensing spectra, and industrial sensing, while preserving
PXRD as the controlled first testbed.
