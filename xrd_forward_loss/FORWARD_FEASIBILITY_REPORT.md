# Forward Model Feasibility Report

**Status:** numerical gate passed for a narrow two-parameter pilot. This does not validate other crystal systems, mixtures, phases, or instrument parameters.

## Existing forward capability

`xrd_inversion/src/xrd_inversion/gpu_forward.py` implements `CachedTetragonalGPUForward`: fixed parent-structure constants, tetragonal reciprocal geometry, atomic scattering factors and structure factors, Bragg peak locations, Gaussian broadening, normalization, and the `log1p_100` profile transform. It is CUDA-only float64 and disables TF32/deterministic shortcuts. The older Week-1 work records CPU-reference parity and gradient/Jacobian checks; its formal report also documents recoverability limits. In particular, the existing nuisance-condition local-capture diagnostic was 181/288 (62.8%), so that infrastructure must not be represented as universal parameter recovery.

The new gate used the original training-fold tetragonal parent `mp-1007758` (HfCd, space group 129, 4 sites; `a=3.047264 Å`, `c=9.162464 Å`). The experimental parameters are the normalized lattice coordinates `du,dv`; zero shift is fixed at 0 and FWHM at the existing model's 0.08° minimum. The scan is Cu Kα, 10–80° 2θ, 0.02° step. The chosen parent is a method-engineering example, not a ferroelectric material result.

## New numerical checks

At anchor `q=[0.11,-0.13,0,-1]`, the transformed-profile Jacobian columns for `du,dv` are nonzero and full rank. Its singular values are `[39.4990, 11.7564]`, condition number `3.3598`. Central finite differences over three steps gave best relative L2 errors `5.85e-6` for `du` and `1.15e-6` for `dv`. The end-to-end reconstruction MSE gradient to a predicted two-coordinate tensor was finite; in the final pilot gate JSON, scalar-loss autograd versus central finite difference had relative errors `3.25e-7` and `1.38e-6` for `du,dv`. The earlier degenerate-initialization gate had different errors and is retained separately with that failed run.

The actual A/B smoke path also passed: each method completed one training epoch on a 64-pattern subset, with finite total loss and validation MAE. This confirms that the NN output can enter the forward graph and return gradients to the NN.

Machine-readable detail is in `reports/pilot_20261018/forward_gate.json` and `smoke.json` after the full pilot run.

## Data and scientific boundary

The single fixed CIF comes from the original `train` fold only. The 512 distinct Sobol `du,dv` draws are split 70/15/15 into train/validation/test, with deterministic split and measurement seeds. As this is a known-structure conditional inversion task, the same fixed structure necessarily appears in all three parameter partitions; there is no cross-structure test and no claimed unseen-prototype generalization. The 2026 frozen train/validation/test assignments and structures were not modified, and no records from the original validation/test folds were read for training, model selection, or evaluation.

Each input profile adds independent Poisson count noise at a 40,000-count scale and a 100–200 count linear background before max normalization. The reconstruction target is the perturbed transformed input; the forward renderer itself has no background or noise model in this pilot. This is deliberate model mismatch, but it is a narrow, synthetic perturbation—not a real instrument model.

## Gate conclusion and limitations

**Pass:** the existing differentiable forward is adequate for a small supervised-versus-supervised-plus-reconstruction experiment on `du,dv` for this parent and parameter range.

**Not established:** zero-shift or FWHM recovery; cross-parameter compensation; other structures/material families; BaTiO3/PZT/KNN physics; preferred orientation or texture; mixtures/phase fractions; independent-renderer performance; experimental accuracy; usefulness as a Rietveld starting point. The frozen independent-renderer holdout was not opened. A proper multi-parent/family follow-up must build structure/prototype-grouped splits using only allowed source records before any model selection.
