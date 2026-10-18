# V9 perturbation adapter for the Forward Loss pilot

## Scope

This adapter applies the existing `xrd_robustness` peak-table measurement simulator to the one-parent HfCd continuous-lattice pilot. The differentiable Torch forward model remains the clean-spectrum generator and the autograd path. V9's NumPy renderer is used only to generate observed training inputs; no V9 operation is inserted between `theta_pred` and the differentiable forward model.

This is a simulator-supervised clean-reference objective. The clean target is available because this is synthetic data; it is not an unsupervised reconstruction objective for experimental spectra.

## Reused modules

- `xrd_robustness.physics.PhysicsParameterSampler` and `PhysicsParameters` for deterministic nuisance sampling and parameter provenance.
- `xrd_robustness.simulator.ideal_peak_table` for reflection-aware Pymatgen peak tables and `simulate_from_peak_table` for measurement rendering.
- `xrd_robustness.measurement_models.generate_background_profile` for smooth nonnegative backgrounds.
- `xrd_robustness.measurement_models.apply_noise_model` for Poisson counts plus count-domain Gaussian readout.
- `xrd_inversion.gpu_forward.CachedTetragonalGPUForward` for the clean, differentiable spectrum and its transformed-profile gradient.

March–Dollase remains disabled. The adapter retains hkl/reflection metadata in the V9 peak table, but the current pilot does not sample preferred orientation. Random per-peak scaling is not used.

## Data schema and ordering

`pilot_samples.npz` is indexed by `sample_index` and contains:

- `q`: two normalized lattice coordinates (`du`, `dv`), the immutable `theta_true` source.
- `clean_profile_raw` and `clean_profile`: clean raw max-normalized relative intensity and the transformed profile used by B's forward term.
- `observed_profile_simple_raw` / `observed_profile_simple`: the prior pilot's Poisson-plus-linear-background input and its transformed form.
- `observed_profile_v9_raw` / `observed_profile_v9`: the V9-perturbed raw normalized profile and transformed NN input.
- `train_indices`, `validation_indices`, and `test_indices`: frozen sample-level split indices.

The one-to-one `sample_records.jsonl` row has `sample_id`, `sample_index`, split, normalized `theta_true`, physical lattice truth in Å, structure record source/fingerprint, simulator contracts, config SHA-256, profile array SHA-256 values, and per-view nuisance types, strengths, and random seeds. The source data contain `standardized_structure` JSON rather than a CIF, so `cif_source` is explicitly null. The JSONL preserves Sobol `theta_true` at float64; the NPZ q labels are stored as float32 for the existing training interface. The maximum rounding in this run is recorded in run metadata and is about `3e-8` normalized q.

For a measured profile the order is:

1. Generate the clean relative-intensity profile and normalize it to a unit maximum.
2. Add the nonnegative smooth background on the relative-intensity scale.
3. Convert expected intensity to relative detector counts, draw Poisson counts, add count-domain Gaussian readout, and convert back to the same relative-count scale.
4. Clip negative readout values, max-normalize exactly once, then apply `log1p(100*x)/log(101)`.

The count scale is an engineering simulation parameter, not an absolute detector calibration. No normalization occurs between background addition and count sampling.

## Staged nuisance profile

`phase1_noise_background` activates only polynomial smooth background and Poisson–Gaussian noise. `phase2_add_broadening_and_zero_shift` adds area-stable Gaussian peak broadening and a single global 2θ offset. The second phase is refused unless a completed phase-1 smoke manifest is supplied. The three-seed pilot is refused unless a completed phase-2 smoke manifest is supplied.

The profile ranges in `configs/v9_disturbance_clean_reference_pilot.json` are small engineering stress ranges informed by the V9 implementation. They are not copied as instrument calibration ranges. Lattice labels are sampled once and are shared across simple and V9 observations; background, noise, width and zero offset only change observed profiles.

## Running

Use the repository's configured Python environment and expose the three source packages through `PYTHONPATH`. For example, from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = "xrd_forward_loss/src;xrd_inversion/src;xrd_robustness/src"
python xrd_forward_loss/scripts/run_v9_perturbation_pilot.py `
  --phase phase1_noise_background --smoke-only `
  --source-root E:\AI4science `
  --output xrd_forward_loss/reports/v9_perturbation_phase1_smoke_20261018_01
```

After reviewing the phase-1 manifest and report, use the completed manifest for the phase-2 smoke:

```powershell
python xrd_forward_loss/scripts/run_v9_perturbation_pilot.py `
  --phase phase2_add_broadening_and_zero_shift --smoke-only `
  --phase1-evidence xrd_forward_loss/reports/v9_perturbation_phase1_smoke_20261018_01/run_manifest.json `
  --source-root E:\AI4science `
  --output xrd_forward_loss/reports/v9_perturbation_phase2_smoke_20261018_01
```

The final three-seed run takes both `--phase1-evidence` and `--smoke-evidence` (the phase-2 smoke manifest). Each run requires a new output directory and writes config, manifest, run log, arrays, provenance, gates, results, plots and Markdown report.

The delivered full-run command was:

```powershell
python xrd_forward_loss/scripts/run_v9_perturbation_pilot.py `
  --phase phase2_add_broadening_and_zero_shift `
  --phase1-evidence xrd_forward_loss/reports/v9_perturbation_phase1_smoke_20261018_retry2/run_manifest.json `
  --smoke-evidence xrd_forward_loss/reports/v9_perturbation_phase2_smoke_20261018/run_manifest.json `
  --source-root E:\AI4science `
  --output xrd_forward_loss/reports/v9_perturbation_phase2_pilot_20261018
```

The final run invokes `scripts/validate_v9_pilot_results.py <run-dir>` to recompute parameter, lattice and spectrum errors from the saved predictions and arrays; its `results_validation.json` contains the input hashes and comparison tolerances. Review-facing metrics are in `results_summary.json`; full per-sample predictions and reconstruction profiles remain losslessly available in `results_full.json.gz`. If a training run completed and only plot serialization failed, `scripts/recover_v9_pilot_artifacts.py <run-dir>` regenerates plots/report from the saved full JSON or gzip archive. It does not rerun training or edit saved results/history; it snapshots the original failed manifest and records hashes of the result content and its archive.

## Interpretation boundary

The pilot checks implementation integrity and a matched engineering A/B comparison on one known simulated tetragonal HfCd parent. It cannot establish ferroelectric-ceramic performance, real-spectrum recovery, unseen-structure generalization, or refinement-initialization utility. Those require actual target-family structures and phase hypotheses, calibrated instrument and background/noise models, validated orientation/peak-width assumptions, independent material-level splits, and external reference measurements/refinements.
