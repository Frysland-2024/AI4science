# Identifiability-Aware Joint Sample–Instrument Inversion from PXRD

**Status:** `SEALED_FUTURE_MODULE`
**Design date:** 2026-08-13
**Execution profile:** prospective four-week prototype; not authorized
**Active V9 affected:** no
**Training authorized:** no
**Existing frozen V9 simulated Test / real XRD access authorized:** no

> This document registers a future project contract. It does not implement an
> inverse solver, authorize training, reopen the frozen V9 comparison, or turn
> completed V9 classification evidence into physical-parameter-recovery evidence.

## 1. Decision

The proposed first version must **not** jointly regress

\[
(a,c,\delta,\mathrm{FWHM},b_0,b_1).
\]

That target is compact in dimension but not automatically identifiable. Lattice
changes and zero offset both move peaks; effective width can mix instrumental,
size, strain, and overlap effects; background coefficients depend on intensity
normalization and basis choice. The current simulator also has no differentiable
`a,c -> peak positions` path and does not expose `b0,b1` as registered targets.

The minimum defensible project is instead a **known-template, low-dimensional
joint inverse problem**:

\[
z=(\varepsilon_{\mathrm{iso}},\delta),
\]

where \(\varepsilon_{\mathrm{iso}}\) is an isotropic lattice-scale change of a
known nominal crystal prototype and \(\delta\) is a global 2-theta zero offset.
This contains one sample quantity and one instrument quantity while remaining
small enough for an explicit identifiability audit before machine learning.

## 2. Relationship to existing work

This module is a sibling of, not a replacement for,
[`PXRD_MEASUREMENT_PARAMETER_INVERSION.md`](PXRD_MEASUREMENT_PARAMETER_INVERSION.md).

| Project | Question | Status |
|---|---|---|
| Frozen V9-T | Can seven-class predictions remain stable under simulated measurement variation? | Completed robust-classification evidence |
| Measurement-parameter inversion | Which measurement nuisance parameters can be inferred and calibrated? | Sealed future module |
| This module | Can a sample parameter and an instrument nuisance be recovered jointly under a known nominal PXRD template? | Sealed future module |

The repository already uses **V10** for an archived measurement-supervised
residual mechanism. This project must therefore not be named or presented as
V10.

## 3. Conditional forward problem

The forward model must include the known template explicitly:

\[
y \sim p\!\left(y\mid \mu(s_0,z)\right),
\]

where \(s_0\) contains the nominal structure, indexed reflections, fixed
reflection amplitudes, wavelength, and registered angular grid. The target alone
is not sufficient to generate a spectrum without this conditioning information.

For the first tetragonal prototype,

\[
a=a_0\exp(\varepsilon_{\mathrm{iso}}),\qquad
c=c_0\exp(\varepsilon_{\mathrm{iso}}),
\]

\[
\frac{1}{d_{hkl}^2}=\frac{h^2+k^2}{a^2}+\frac{l^2}{c^2},\qquad
2\theta_{hkl}=2\arcsin\!\left(\frac{\lambda}{2d_{hkl}}\right)+\delta.
\]

At small strain, the lattice contribution to the angular displacement is
approximately proportional to \(-2\tan(\theta)\varepsilon_{\mathrm{iso}}\),
whereas \(\delta\) is constant across angle. Multiple separated reflections over
a sufficiently broad angular range can therefore distinguish the two effects in
principle; the project must demonstrate that distinction for its actual grid and
noise levels rather than assume it.

## 4. Version ladder

Each stage requires a new dated activation decision and a passed identifiability
gate. A failed stage returns to the last defensible lower-dimensional target.

### MVP-0 — isotropic sample change plus zero offset

- one known tetragonal prototype;
- fixed fractional coordinates, reflection set, amplitudes, wavelength, effective
  width, and background;
- inverse target \((\varepsilon_{\mathrm{iso}},\delta)\);
- no atomic-coordinate, phase-fraction, texture, or full-structure recovery.

This is the two-parameter four-week core. Results may also be reported as
\(a=a_0\exp(\varepsilon_{\mathrm{iso}})\) and
\(c=c_0\exp(\varepsilon_{\mathrm{iso}})\), but those two reported lattice
constants still represent one constrained sample degree of freedom.

### MVP-1 — anisotropic lattice change

After MVP-0 passes, consider

\[
z=(\varepsilon_a,\varepsilon_c,\delta),\qquad
a=a_0\exp(\varepsilon_a),\quad c=c_0\exp(\varepsilon_c).
\]

Only patterns with sufficient independent \(hkl\) sensitivities, angular span,
and non-overlapping reflections are eligible.

This three-parameter target is the first stretch goal for the four-week profile.

### MVP-2 — effective renderer width

Add `log_width` only after the earlier targets remain identifiable. The value is
the constant Gaussian or registered profile width of the simplified renderer. It
must not be interpreted as crystallite size, microstrain, or a uniquely physical
instrument FWHM.

Use `log_width` so positivity is structural. This is the fourth and final
four-week stretch target, not a promised Week-2 output.

### MVP-3 — registered background basis

Add background last, using a fixed basis on a normalized coordinate and
non-negative, scale-aware coefficients. Max-normalized spectra cannot support a
claim of absolute background or count-scale recovery. Random GP background is
excluded from the first joint inverse target.

Background inversion is outside the four-week prototype.

Joint six-parameter regression is eligible only if all preceding stages pass. It
is not the default undergraduate MVP.

## 5. Gate 0 — identifiability before neural training

No inverse network may be trained before Gate 0 is reviewed and passed.

### Local sensitivity

For standardized parameters, compute

\[
J=\frac{\partial \mu}{\partial z},\qquad
\mathcal I=J^\top\Sigma^{-1}J,
\]

where \(\Sigma\) is the registered observation-noise covariance or diagonal
variance model. Report:

- Jacobian rank and singular spectrum;
- condition number;
- pairwise sensitivity cosine;
- parameter-wise and paired profile-loss surfaces;
- dependence on SNR, visible-peak count, overlap, and angular range.

### Global collision search

Search the full registered parameter box for pairs whose parameter difference
exceeds the scientific tolerance but whose spectral distance lies inside the
95% envelope produced by repeated observations at the same parameters. Such
regions are `CONFOUNDED`; point estimates there cannot support a recovery claim.

### Physics-only recovery

Run multi-start nonlinear least-squares or maximum-likelihood fitting from the
same forward model on noiseless and noisy cases. If the correct parameters cannot
be recovered reliably by this baseline, adding network capacity is not a remedy.

Candidate quantitative gates for later preregistration are:

- at least 95% of the high-SNR design stratum has full-rank standardized
  Jacobians with condition number at most \(10^3\);
- collision rate at the registered scientific tolerances is at most 1%;
- multi-start fitting reaches normalized error at most 0.01 for every primary
  target in at least 95% of noiseless cases.

These are design candidates, not authorized thresholds. Activation must freeze
the units, parameter box, tolerances, strata, and gates before any result exists.

## 6. Differentiable expected-signal renderer

The first renderer should be a small vectorized PyTorch module with:

1. frozen \(hkl\) indices and reflection amplitudes from \(s_0\);
2. differentiable lattice-to-\(d\)-spacing and Bragg-angle calculations;
3. a global zero-offset transform;
4. an area-stable Gaussian peak kernel;
5. a fixed, explicitly registered background for MVP-0;
6. stochastic observation noise sampled only after the expected signal is built.

Measurement consistency must compare the observation with the expected signal or
its registered likelihood. It must not resample fresh noise inside every
consistency evaluation.

### Renderer verification

- compare peak centers against `pymatgen` on a frozen parameter grid;
- require center discrepancies no larger than half of one 0.02-degree bin;
- compare autograd derivatives with central finite differences, with a candidate
  relative-error tolerance of \(10^{-3}\);
- record wavelength, angular grid, peak normalization, reflection/amplitude
  provenance, boundary treatment, and precision;
- test gradients near the edges of the parameter box.

The existing `xrd_robustness` simulator remains a higher-level non-differentiable
reference and mismatch generator. Its current background parameterization is not
silently redefined as `b0,b1`.

## 7. Models and objective

The inverse map is

\[
\hat z=G_\theta(y,s_0).
\]

The conditional input may be implicit only while every sample uses the same
frozen template. Later multi-template work must expose or encode \(s_0\).

A candidate objective is

\[
L_{\mathrm{sup}}=L_{\mathrm{param}}(\hat z,z),
\]

for the baseline, and

\[
L_{\mathrm{physics}}=L_{\mathrm{sup}}
 +\lambda D\!\left(\mu(s_0,\hat z),y\right),
\qquad \lambda\geq 0,
\]

- `L_param`: Huber loss or Gaussian negative log-likelihood after each target is
  standardized with preregistered scales;
- `D`: a non-negative noise-aware deviance or variance-weighted robust spectral
  discrepancy between \(y\) and \(\mu(s_0,\hat z)\);
- `lambda=0`: the paired supervised baseline;
- `lambda>0`: the only learned-method change in the physics-guided comparison.

Because \(D\) is a discrepancy that is minimized, its sign is positive. A minus
sign would be valid only if the term were explicitly defined as a similarity or
reward to maximize.

Ordinary pointwise spectrum MSE is not the default because background and the
largest peaks can dominate it, while small peak misalignment can create unstable
gradients. A small lambda grid may be selected on Validation only. Learned
uncertainty, JS, PINNs, Transformers, diffusion models, and architectural searches
are outside the four-week profile.

Supervised parameter regression is already an inverse problem. Adding
measurement consistency is a physics-guided regularizer; it does not by itself
prove identifiability or correctness. A lower spectral residual with unchanged or
worse parameter error is not a successful inversion result.

## 8. Required comparisons

There are exactly two learned objectives, using the same ResNet encoder,
regression head, initialization policy, optimizer budget, and labeled IDs:

| Learned objective | Parameter labels | Unlabeled spectra |
|---|---:|---:|
| Supervised inverse ResNet, `lambda=0` | registered labeled subset | no parameter loss |
| Physics-guided inverse ResNet, `lambda>0` | same registered labeled subset | measurement discrepancy only, with known \(s_0\) |

Run these objectives in two label-budget strata:

1. 100% parameter labels;
2. one low-label budget frozen before execution, with 10% recommended and 20%
   permitted only if selected prospectively instead.

Synthetic parameter labels exist by construction. The low-label study therefore
means that labels are deliberately masked in a controlled ablation; it is not
evidence that simulated labels are costly to obtain. The mask must be hashed and
identical for the paired objectives. Optimizer steps, labeled exposures,
unlabeled exposures, and forward-model evaluations must be reported so the added
physics signal is explicit.

A constant/median predictor is a required regression sanity check. Bragg-law
least squares and same-renderer multi-start fitting belong to Gate 0 and provide
physics reference values; they are not extra learned methods or an expanded model
search.

## 9. Data, leakage, and evaluation

### Initial data contract

- create isolated `train`, `validation`, and locked `evaluation` manifests for
  this new module;
- do not access the existing frozen V9 simulated Test or any real XRD;
- keep all observations derived from one nominal parent in one split when the
  project expands beyond a single prototype;
- keep exact parameter tuples and observation seeds disjoint across the new
  module's manifests;
- store parameter labels in a machine-readable manifest with fixed units and
  transforms;
- keep label budgets, seeds, parameter ranges, and model-selection metrics fixed
  across paired comparisons.

### OOD panels

The four-week minimum includes:

- ID clean and registered-noise panels;
- one stronger count/SNR/read-noise shift;
- one parameter-range shift;
- one forward-operator mismatch panel.

Peak masking, angular truncation, combined nuisances, and held-out prototypes are
post-prototype extensions unless the minimum matrix finishes early.

The mismatch panel is mandatory. A suitable sequence is:

```text
training renderer:
  constant-width Gaussian + fixed linear background

evaluation generator:
  pseudo-Voigt or angle-dependent width
  + different background family
  + optional wavelength/doublet or axis mismatch
```

Training and testing only with the identical renderer and prior is a synthetic
inverse crime. Such a result can establish code correctness but not operator
robustness, Sim2Real behavior, or real-measurement reliability.

### Metrics

- target-wise MAE, normalized MAE, RMSE, and bias;
- joint error and error surfaces by parameter stratum;
- spectral likelihood or registered reconstruction residual;
- failure and boundary-clipping rates;
- paired ID/OOD differences across at least three preregistered seeds, with five
  as the preferred stretch;
- inference time separately from accuracy.

Seed-to-seed intervals or paired bootstrap intervals describe experimental
variability; they are not learned uncertainty quantification.

If a neural method is only faster than classical fitting, the supported claim is
amortized speedup, not more correct physical recovery.

## 10. Primary hypothesis and decision rule

### Research question

> Under a known nominal PXRD template, does a differentiable forward-model
> consistency term improve low-label parameter recovery under preregistered
> synthetic parameter and operator shifts without materially degrading ID
> recovery?

This is a hypothesis, not a result.

### Positive inversion PASS

Across the matched seeds, the physics-guided method should improve the primary
low-label OOD normalized parameter error, with paired variability reported,
while no ID target degrades beyond a preregistered relative margin. A mature
paper-level claim would require more seeds and a separately frozen statistical
decision rule; the four-week prototype must not overstate that evidence level.

### Partial or negative conclusions

- if only spectral discrepancy improves, the supported conclusion is better
  forward fit, not more accurate parameter inversion;
- if naive consistency does not improve parameter error, report the negative
  method result rather than retuning until positive;
- if Gate 0 identifies collisions or rank deficiency, reduce the target from four
  to three to the two-parameter core;
- if the two-parameter core is still non-identifiable, do not train an inverse
  network; deliver the identifiability/collision analysis as the scientific
  result;
- a careful negative result about non-uniqueness or ill-posedness is valid for an
  application narrative but is not a positive inversion-performance claim.

### Invalid-result conditions

- the target is changed after evaluation results are observed;
- clipping at target bounds creates an artificial low error;
- the model exploits template, filename, RNG, or manifest shortcuts;
- apparent robustness disappears under the renderer-mismatch panel;
- the report treats a spectral-fit improvement as parameter-recovery improvement.

A careful non-identifiability map is a scientifically useful result. It is better
than forcing a positive neural-network result.

## 11. Prospective four-week prototype profile

This schedule is designed for a complete, application-usable prototype, not a
mature standalone inverse-problem paper. It remains prospective until a dated
activation decision fills every unresolved registry field.

| Week | Work | Gate / deliverable |
|---|---|---|
| 1 | Freeze one known tetragonal prototype, wavelength, angular grid, parameter box, and tolerances; implement the expected-signal renderer; verify it against `pymatgen` and finite differences; run Jacobian/Fisher, collision, and multi-start audits | Renderer is numerically correct and the selected target passes Gate 0; otherwise downscope before training |
| 2 | Wrap the existing ResNet encoder with a new regression head; train only the supervised objective; run constant and physics-fit sanity references | Target-wise normalized error clearly beats the constant predictor, while the physics fit recovers noiseless/high-SNR cases |
| 3 | Add the positive-sign forward discrepancy; search only the preregistered small lambda grid on Validation; run 100% and the one frozen low-label budget | Finite gradients and stable training; ID parameter error stays within the preregistered non-inferiority margin |
| 4 | Freeze lambda; evaluate the new module's locked ID, noise, parameter-shift, and one renderer-mismatch panel; aggregate matched seeds; write a 2–4 page report | Reproducible positive, partial, or negative conclusion with claim boundaries and figures |

### Month-end completion contract

The prototype is complete when it has:

1. a tested differentiable renderer and provenance-bound configuration;
2. a recorded Gate-0 outcome and target-dimension decision made before training;
3. the same ResNet compared under exactly two learned objectives and two label
   budgets, if Gate 0 permits training;
4. locked ID/OOD/operator-mismatch results with at least three matched seeds;
5. parameter-error and spectral-residual figures;
6. a 2–4 page technical report that distinguishes completed evidence from future
   CT/MRI or optical-metrology goals.

The planning estimate that such a scoped prototype is likely achievable within a
month is not repository evidence or a publication guarantee.

### Implementation isolation

If activated, use a new namespace rather than editing the V9 trainer or head:

```text
xrd_robustness/src/xrd_robustness/inversion_prototype/
xrd_robustness/configs/inversion_prototype/
xrd_robustness/scripts/inversion_prototype/
xrd_robustness/tests/inversion_prototype/
outputs/inversion_prototype/        # local only; never commit
```

The ResNet encoder design, grid types, nominal `pymatgen` peak calculation,
seeding/provenance patterns, and NumPy renderer as a mismatch reference may be
reused. Add a separate regression wrapper and initialize it independently; do not
load V9 checkpoints or modify the V9 classification head, runner, configs, or
reports. The existing NumPy renderer cannot substitute for the new differentiable
lattice-to-peak path.

This is research and code-module isolation. It does not by itself authorize a Git
branch, implementation, data generation, or execution.

## 12. Inverse-crime blacklist

The project must not:

- use the same renderer and parameter prior as the only train/test setting;
- place observations from one parent structure across splits;
- use true nuisance values during evaluation preprocessing;
- hide access to true test `hkl` or amplitudes while calling the task blind
  inversion;
- infer absolute background or count scale after normalization has removed it;
- interpret synthetic effective width as a unique physical broadening mechanism;
- expose RNG seeds, filenames, or manifest ordering to the model;
- select loss weights, parameter ranges, or stopping rules on Test;
- report spectrum reconstruction without parameter accuracy;
- describe synthetic corruption shift as real-domain or clinical evidence.

## 13. Research narrative boundary

A defensible summary is:

> This future project formulates low-dimensional PXRD parameter estimation under
> a known crystal template as a nonlinear inverse problem. It will test whether
> adding a differentiable forward-model consistency constraint to parameter
> supervision improves recovery under controlled label scarcity and synthetic
> operator mismatch. The design shares the abstract principle of explicitly
> using an acquisition operator with model-based MRI and CT reconstruction, and
> with optical scatterometry inversion, without claiming identical physics,
> losses, identifiability, or difficulty.

The longer trajectory is:

```text
completed measurement-aware PXRD classification
    -> sealed low-dimensional sample–instrument inversion
    -> future optical scatterometry inverse metrology
    -> possible later computational-imaging research
```

CT and MRI are methodological destinations, not experiments or completed
capabilities in this repository.

## 14. Literature anchors and evidence level

- Chitturi et al. demonstrated CNN estimates of PXRD lattice parameters; the work
  supports feasibility of coarse low-dimensional regression, not metrology-grade
  joint identifiability: <https://doi.org/10.1107/S1600576721010840>.
- Dong et al. estimated several quantitative PXRD parameters and compared with
  full-profile analysis; it is a useful parameter-regression precedent, not a
  validation of this forward-consistency contract:
  <https://doi.org/10.1038/s41524-021-00542-4>.
- DONUT embeds a differentiable X-ray nanodiffraction forward model and uses
  measurement reconstruction to infer strain/orientation without labels. It is
  the closest methodological precedent found, but it is scanning nanodiffraction,
  not one-dimensional powder XRD:
  <https://doi.org/10.1038/s41524-025-01860-7>.
- Learned Primal-Dual is a representative CT method that embeds the projection
  operator and its adjoint in an unrolled learned reconstruction:
  <https://doi.org/10.1109/TMI.2018.2799231>.
- Variational networks are a representative MRI example combining acquisition
  physics, data consistency, and learned regularization:
  <https://doi.org/10.1002/mrm.26977>.
- Neural inversion of diffraction-grating geometry has a long optical
  scatterometry history; this supports the bridge in method language, not a claim
  of identical forward physics: <https://doi.org/10.1364/JOSAA.19.000024>.

These references are feasibility anchors, not a complete review. Activation
requires a fresh literature search and a dated related-work audit.

## 15. Activation and ownership

Activation requires an explicit dated decision specifying:

- the exact nominal prototype and provenance;
- the new module's isolated train/validation/locked-evaluation data-generation
  scope;
- target ranges, units, scientific tolerances, and Gate 0 thresholds;
- renderer implementation and mismatch generator;
- label budgets, seeds, baselines, success/failure criteria, and compute budget;
- ownership of renderer, identifiability audit, training, evaluation, and review;
- whether any future real standard or calibration sample may be accessed.

Until then:

- no code, config, data, or report is required by this document;
- no training or inference command is authorized;
- V9, V10, the existing frozen V9 simulated Test, RRUFF evidence, and manuscript
  claims remain unchanged;
- the existing measurement-nuisance module remains separately sealed.
