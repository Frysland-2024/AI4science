# BaTiO3 public-CIF forward A/B pilot (2026-10-18)

**Status:** EXECUTED SINGLE-SEED EXPLORATORY SIMULATED PILOT. NOT a claimed method benefit, not real PXRD, not the V9 full-perturbation adapter, not unseen-structure generalization. All results below were recorded by the executable script using an RTX 4060 laptop CUDA environment.

- Structure: tetragonal BaTiO3, COD 9014273, P4mm (#99), a0=3.986 Å, c0=4.026 Å, from the historical Shirane et al. (1957) experimental structure file.
- Reference CIF: `xrd_forward_loss/data/public_cif/BaTiO3_COD_9014273_P4mm.cif`, attribution and source in nearby README.
- Physics screening: local 2-D lattice parameter Jacobian condition number 2.966; at the nominal reference 100% of Pymatgen's expected peak positions intersect a visible peak in the GPU profile within an 11-bin window. This is **not** exhaustive full-profile parity, correct broadening or independent renderer validation.
- Data: 512 Sobol lattice parameter samples with 358/77/77 param-draw train/validation/test samples **from the same reference CIF**. Fixed zero offset/FWHM, 40,000-count Poisson signal and 150-count constant background (not V9 full five perturbations).
- Models: A = parameter-only supervision; B = parameter loss + observed-profile reconstruction loss at weight 1.0. Same backbone, seed 20261021, Adam 0.0005, 24 epochs. **Weight 1.0 was inherited from HfCd; no BaTiO3-specific validation-only weight selection was carried out.**
- Small engineering smoke: 128 samples, 4 epochs, A q-MAE 0.2427, B q-MAE 0.2544. These are undertrained sanity checks, **not useful comparative science**.

## 512-sample actual observed run

| Metric | A: supervised | B: + forward-loss |
|---|---:|---:|
| Normalized two-parameter q-MAE | 0.019204 | 0.026612 |
| a MAE (Å) | 0.000520 | 0.000695 |
| c MAE (Å) | 0.000950 | 0.001469 |
| Clean transformed spectrum RMSE | 0.018014 | 0.026132 |
| Model training time (s) | 27.25 | 29.24 |

In this **single seed**, B was worse for both lattice error and spectrum reconstruction. This does not disprove physics-based reconstruction generally: the regularization strength and target are not material-validated, simulator-generated data share the model's forward operator, and the dataset includes only one parameterized structure.

Machine-readable results are in `reports/batio3_cod9014273_pilot_512/results.json`. The first (128-sample) run is retained separately.

## Reproduction

With CUDA, PyTorch and the dependencies installed, from repository root:

```powershell
$env:PYTHONPATH = "xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src"
python xrd_forward_loss/scripts/run_public_batio3_smoke.py --epochs 24 --sobol-power 9 --output xrd_forward_loss/reports/batio3_reproduction_new
```

The script refuses to overwrite an existing output directory.

## Follow-up and stopping conditions

1. Review the P4mm physical model fully against independent CPU/reference calculations, verify selected atomic structure metadata, and test Jacobian conditioning across the expected parameter range.
2. Join the independent active Codex V9 disturbance adapter work only after it passes smoke and is reviewed; **this branch does not contain five-nuisance perturbation integration.**
3. Freeze a new physical-noise protocol. For B, compare clean-reference reconstruction or explicit measurement nuisance modeling; do not silently change the objective in the already-run results.
4. After the material and physical forward gate are credible, run a *bounded* replicated multi-seed A/B with a validation-only lambda policy and an actual local physics-fitting baseline. No tuning on test.
5. Obtain and assess real PXRD only with source, instrument settings, nominal composition and reference refinement details. No claims about the collaborator's samples at this stage.
