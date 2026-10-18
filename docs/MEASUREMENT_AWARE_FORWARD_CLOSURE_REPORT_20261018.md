# Measurement-aware forward closure: BaTiO3 bounded pilot

**Status:** COMPLETED ENGINEERING PILOT; no evidence for real PXRD or new-structure generalization. This is a synthetic single-CIF interpolation experiment.

## Previous objective and corrected target

The existing clean Torch forward is `F_clean(q, eta_ref)`. `compose_full_q` appends normalized zero shift `0` and width coordinate `-1`, which map to `delta=0 deg` and `FWHM=0.08 deg` in the frozen Week-1 configuration. PR #11's `paired_losses` uses `L_param + lambda * MSE(F_clean(q_pred, eta_ref), x_observed)`, although `x_observed` can include zero shift, broadening, background and readout noise. PR #17's `clean_reference_paired_losses` instead uses the simulator's `x_clean` target. That is numerically consistent simulator-provided privileged supervision, but it is not a likelihood for a measurement with unknown nuisance. Neither target implies that the crystallographic clean forward itself was wrong.

This pilot adds `mu(q, eta)`: the same differentiable Bragg model with global zero shift, Gaussian FWHM, smooth nonnegative linear background and relative scale. Poisson-Gaussian readout is applied only when constructing observed inputs; reconstruction targets are deterministic expected profiles, never individual noise draws. Units and bounds are recorded in `measurement_closure/audit.py` and the run manifest.

## P0/P1 gates

Public COD 9014273 CIF parses as five-site BaTiO3, P4mm (#99), `a=b=3.986 Å`, `c=4.026 Å`; Cu K-alpha wavelength is 1.54184 Å on 10–80 degrees 2theta at 0.02-degree spacing. Four q probes were compared against the independent V9 Pymatgen peak-table clean renderer. Full-grid RMSE was `2.76e-9` to `4.34e-9`; max absolute error was `7.81e-8` to `1.44e-7`. Pymatgen peak coverage was 100% in a seven-bin neighborhood for all probes. This supports clean renderer parity over the tested single-CIF domain; it does not validate every nuisance operator against V9.

At an informative displaced q, autograd and centered finite differences gave q gradients `[0.00255430, -0.000229717]` and `[0.00255430, -0.000229717]`; maximum symmetric relative error was `8.65e-7`. At the nominal q/eta point the seven-column joint profile Jacobian (2 q + 5 eta) had full rank and condition number 17.44. A bounded noiseless profile fit estimated q and eta without reading their truth during optimization: after 7 evaluations q max error was `2.1e-12` and profile RMSE `3.1e-13`. This is an exact-model identifiability diagnostic; finite noise, wider nuisance ranges, background misspecification and other structures can worsen it. Three CUDA tests passed, including separate q/eta perturbation, finite differences and repeated-noise mean vs realization.

The deliberate mismatch was also measured. For one deterministic expected profile at q `[0.18,-0.22]` with diagnostic-only nuisance `[zero=0.05 deg, FWHM=0.12 deg, background endpoints=0.01/0.015, scale=1]`, fixed clean forward at the true q had gradient `[0.02343,0.003773]`; q-only fitting moved the best point by `[-0.10546,-0.09991]` and still left RMSE `0.03131`. Measurement-aware expected forward at q truth had zero residual and zero gradient, as constructed. This is an exact-model noiseless illustration of the target mismatch, not a statistical bias estimate under noisy/V9 data. Full numbers are in `audit_run_v3/p0_p1_audit.json`.

## Bounded A/B run

The run used 512 Sobol parameter samples from the same BaTiO3 CIF, a fixed 70/15/15 split, paired seeds `20261021–20261023`, and 24-epoch maximum per run. Conditions were simple readout and a **V9-style Torch synthetic condition**: global zero shift, Gaussian broadening, smooth linear background and Poisson-Gaussian readout. It is not the complete V9 NumPy peak-table perturbation pipeline; the second condition is not labeled as full V9 in the artifacts. Parameter ranges are small synthetic stress ranges, not instrument calibration. There were 12 runs total. A and B share the ResNet-18-GN feature backbone, input arrays, splits, optimizer, batch size and update budget. B adds five eta outputs and receives synthetic eta labels plus a deterministic expected-profile auxiliary loss (both weights fixed at 0.1); this is additional supervision and a larger output head. B predicts eta from the input at inference and never consumes `eta_true` at test time.

| Condition | A q-MAE mean ± SD | B q-MAE mean ± SD | Paired B−A by seed | A mean a/c MAE (Å) | B mean a/c MAE (Å) |
|---|---:|---:|---|---:|---:|
| Simple | 0.01959 ± 0.00347 | 0.01616 ± 0.00178 | -0.00933, -0.00104, +0.00008 | 0.000589 / 0.000980 | 0.000563 / 0.000743 |
| V9-style | 0.03773 ± 0.00722 | 0.04084 ± 0.00276 | -0.00707, +0.00924, +0.00715 | 0.001664 / 0.002302 | 0.001786 / 0.002501 |

Thus the simple-condition B mean is lower, with 2/3 paired seeds improving; in the more perturbed condition B is worse on average, with only 1/3 paired seeds improving. Do not claim a general A/B gain. B's expected-profile RMSE by seed was 0.01436, 0.01560, 0.01701 (simple) and 0.02482, 0.03178, 0.02721 (V9-style). A profile residual was not logged in this bounded run; clean-profile residuals are therefore not compared. Training time averaged 22.6 s (A) / 30.5 s (B) for simple and 21.6 s / 28.4 s for V9-style. Peak PyTorch allocated memory was 0.58–0.68 GB per run; system GPU utilization was observed near 98% during the run, with no OOM.

All per-seed metrics and histories are in `xrd_forward_loss/measurement_closure/ab_run/results.json`; caps and config digests are in `manifest.json`. The gate record is in `audit_run_v3/p0_p1_audit.json`. The run is exploratory: one CIF, parameter realizations rather than independent structures, synthetic noise/nuisance, and the same forward family for generation and inversion. The B auxiliary supervision is not available for arbitrary real patterns without a compatible expected-profile target; deployable eta inference here is demonstrated only under this synthetic model.

## Reproduction and checks

From the repository root in the installed `xrd_test` environment:

```powershell
$env:PYTHONPATH='xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src;xrd_forward_loss'
python -c "from pathlib import Path; from measurement_closure.audit import run_audit; run_audit(Path.cwd(), Path('xrd_forward_loss/measurement_closure/new_audit_output'))"
python -m pytest xrd_forward_loss/measurement_closure/test_gates.py -q
python -m measurement_closure.run_ab --output xrd_forward_loss/measurement_closure/ab_reproduction_new
```

The recorded test command completed with **3 passed**. The A/B output directory is immutable by the runner (`exist_ok=False`).
