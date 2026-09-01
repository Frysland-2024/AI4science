# Structure–Measurement Factorization Pilot

**Decision: NO-GO**

This is a finite mechanism test on authoritative Train parents only. The four held-out blocks per parent are internal unseen-intervention sanity evaluation, not Validation/Test evidence or a formal generalization result.

## Frozen scope and matched comparison

- Parents: 32 conventional tetragonal Train parents
- Blocks/spectra: 512 / 2048
- Training/internal-eval blocks: 384 / 128
- Seeds: 20260901, 20260902, 20260903
- Interface status: v1 frozen after the successful tiny-overfit Gate.
- Channels: `[x_obs, x_ref, x_obs-x_ref]`; structure order: `[q_u,q_v]`; measurement order: `[q_delta,q_w]`.
- Manifest labels, handoff truth, decoded truth, and metrics are canonical float64; model training casts labels to float32.
- Same data, initialization policy, optimizer, steps, and batch schedule; the only condition difference is `lambda_pair=0` versus `lambda_pair=1`.

## Tiny-overfit engineering Gate

Status: **PASS**. All pairing, finite-value, matched-initialization/schedule, supervised-overfit, and paired-loss checks passed before the formal manifest was generated.

## Three-seed aggregate metrics

| Metric | Baseline mean ± sample SD | Paired mean ± sample SD | Relative reduction | Improved seeds |
|---|---:|---:|---:|---:|
| E_s<-m | 0.133630 ± 0.003060 | 0.120918 ± 0.003808 | 9.51% | 3/3 |
| E_m<-s | 0.114034 ± 0.004590 | 0.109241 ± 0.004249 | 4.20% | 3/3 |
| Structure response error | 0.186325 ± 0.006498 | 0.185481 ± 0.005090 | 0.45% | 2/3 |
| Measurement response error | 0.115425 ± 0.004591 | 0.116655 ± 0.003605 | -1.07% | 1/3 |
| a MAE (Å) | 0.005050 ± 1.788e-04 | 0.005324 ± 1.100e-04 | -5.43% | 0/3 |
| c MAE (Å) | 0.015020 ± 7.455e-04 | 0.013815 ± 8.227e-04 | 8.02% | 3/3 |
| delta MAE (deg 2theta) | 0.016184 ± 0.001122 | 0.016786 ± 7.871e-04 | -3.72% | 0/3 |
| FWHM MAE (deg) | 0.002938 ± 7.194e-04 | 0.002423 ± 2.661e-04 | 17.54% | 2/3 |

`Improved seeds` counts strictly lower paired values. The pre-registered 2/3 direction-consistency requirement applies to leakage improvements; own-response and physical-MAE checks are matched-seed mean degradation safeguards. Per-seed safeguard pass counts are serialized in `gate.seed_consistency_audit`.

## Per-seed leakage and own-factor response

| Seed | Model | E_s<-m | E_m<-s | Structure response error | Measurement response error |
|---:|---|---:|---:|---:|---:|
| 20260901 | baseline | 0.135977 | 0.118459 | 0.193096 | 0.120559 |
| 20260901 | factorized | 0.125250 | 0.114146 | 0.191348 | 0.118529 |
| 20260902 | baseline | 0.134742 | 0.114346 | 0.185741 | 0.111715 |
| 20260902 | factorized | 0.119403 | 0.106891 | 0.182842 | 0.112499 |
| 20260903 | baseline | 0.130169 | 0.109295 | 0.180139 | 0.114002 |
| 20260903 | factorized | 0.118101 | 0.106685 | 0.182252 | 0.118937 |

## Mean 2×2 intervention response matrices

### Baseline

Rows are true interventions `[structure, measurement]`; columns are predicted heads `[structure, measurement]`.

Raw mean L2 response:

| Intervention \ head | Structure | Measurement |
|---|---:|---:|
| Structure | 0.789167 | 0.114034 |
| Measurement | 0.133630 | 0.837476 |

Normalized by the corresponding true own-factor response:

| Intervention \ head | Structure | Measurement |
|---|---:|---:|
| Structure | 0.930440 | 0.134447 |
| Measurement | 0.153248 | 0.960430 |

### Factorized

Rows are true interventions `[structure, measurement]`; columns are predicted heads `[structure, measurement]`.

Raw mean L2 response:

| Intervention \ head | Structure | Measurement |
|---|---:|---:|
| Structure | 0.783333 | 0.109241 |
| Measurement | 0.120918 | 0.825277 |

Normalized by the corresponding true own-factor response:

| Intervention \ head | Structure | Measurement |
|---|---:|---:|
| Structure | 0.923561 | 0.128796 |
| Measurement | 0.138670 | 0.946440 |

## Gate interpretation

Decision: **NO-GO**.

Passed checks: response_error_structure, response_error_measurement, mae_c_angstrom, mae_delta_2theta_deg, mae_fwhm_deg.

Failed checks: leakage_measurement_to_structure, leakage_structure_to_measurement, mae_a_angstrom.

No lambda search, backbone search, forward reconstruction loss, real spectra, refinement, or new rescue loss was used.

## Boundary audit

The formal dataset, training, predictions, metrics, and Gate used Train only and did not read Validation, Test, or independent-renderer outcomes. During implementation QA, one broad read-only search echoed frozen independent-renderer config metadata, and a delegated agent mistakenly ran `pytest -q xrd_inversion/tests`, which executed `test_independent_renderer.py`. Neither event supplied data or metrics to this Pilot; the broad test result is excluded from Stage-1 evidence and produced no formal artefact.

## Provenance

- Interface: `factorization-interface-v1` (`sha256=27a3bd4b99d98dd5e4481d9d52a8fc4a1699ff63887b14a06ccf3f663a21489a`)
- Config SHA-256: `0672be6170da5b835b8c3fd378575384273bdd84cb1645163f4e2467f9ec121d`
- Factorial manifest canonical payload SHA-256 (self-hash field excluded): `fad96ebc45eff6716a9b0faa403a609007cb7a8d0299a00a7527dff676cceba8`
- Eval manifest canonical payload SHA-256 (self-hash field excluded): `8ff04a87a52da91fc8f1398cd442b4b60e030a555e37260f08f334341543e82b`
- Reference q: `[0.0, 0.0, 0.0, -1.0]`
- Profile view/transform: `gpu_forward_compatibility_false` / `log1p_100_normalized`
- Source closure:
  - `xrd_inversion/src/xrd_inversion/gpu_forward.py`: `4e247bd2b6202e62960729fbd9ee1e13c7ac5e157a2b1b116f1f920745d65c91`
  - `xrd_inversion/src/xrd_inversion/week1_pilot.py`: `e8ca8a918c764d06c4c2d618474786b110ee8b3a572c10104d696b045c905400`
  - `xrd_inversion/src/xrd_inversion/factorial_dataset.py`: `94a7a7400fe24c5acfd3e0ecd4124bd9ac183837e5f2ebbe3ff88a6ac6e77022`
  - `xrd_inversion/src/xrd_inversion/parameterization.py`: `c798c10aaf633ec471cc5228528a920bb8a342fcd6c39d0c78698e86674a8e87`
  - `xrd_inversion/src/xrd_inversion/models.py`: `1fbf00f9c0a9fcd92646cf7123f1a76a03092794f9ff967581186e1af0a70efc`
  - `xrd_inversion/src/xrd_inversion/factorization_losses.py`: `28b46710f3f20a67679fa31b52e24bf1ae643101470b19edb87ed2af6f114716`
  - `xrd_inversion/src/xrd_inversion/factorization_metrics.py`: `a90a6d314ae1abdf0fa81a95cb4aba01104a3dcec157cfcb3f5f12034bb4e6fb`
  - `xrd_inversion/src/xrd_inversion/factorization_training.py`: `29d53620101f28bb28d1c4ff0b4946a6032aea1b845e1703e2ca2ab962581f3d`
  - `xrd_inversion/src/xrd_inversion/factorization_pilot.py`: `d0f73d0ffed829fd46226cc02c58ddc1341c8abf03ad6c854448be308c572e38`

## Handoff artefacts

- `factorization_pilot_manifest`: `xrd_inversion/manifests/factorization_pilot_manifest.json` (`sha256=ff0534280b51b24eb754f4f0f2fe4ae42b5b2b565465ca3e5453ca920a9751fe`)
- `factorial_eval_manifest`: `xrd_inversion/manifests/factorial_eval_manifest.json` (`sha256=a4a1dbb0ee8a4977e0dd333e0a611941b38bc38a093327c8c00f42ef60a0d3f4`)
- `tiny_factorial_manifest`: `xrd_inversion/runs/factorization_tiny_overfit/tiny_factorial_manifest_0b23d647a4bfb2bb.json` (`sha256=6c1e4277f21bc24a2222d9e8e0f9f905c051ab40f0455f90547a9f78ee86210a`)
- `tiny_factorial_profiles`: `xrd_inversion/runs/factorization_tiny_overfit/tiny_factorial_profiles_0b23d647a4bfb2bb.npz` (`sha256=3ab04d343258d1577525734234716d576a8b834fbfd4f4cc282c9845e69bf606`)
- `factorization_interface_v1`: `xrd_inversion/contracts/factorization_interface_v1.md` (`sha256=27a3bd4b99d98dd5e4481d9d52a8fc4a1699ff63887b14a06ccf3f663a21489a`)
- `factorization_pilot_figure_data`: `xrd_inversion/reports/factorization_pilot_figure_data.json` (`sha256=e6244363abfd0032e1e6b7f663fffd3bb138d4ad457d9eb93d89b264f37bd24e`)
- `checkpoint_baseline`: `xrd_inversion/checkpoints/factorization_pilot/checkpoint_baseline.pt` (`sha256=9c31f80ef175c8021ec9fb9e9223e1812b913880b3b67cfca0007d2dae008938`)
- `prediction_dump_baseline`: `xrd_inversion/outputs/factorization_pilot/prediction_dump_baseline.npz` (`sha256=d09bb53dcc4a22cfd628be349fdba4f3667178088ae975a944922da5d955b078`)
- `checkpoint_factorized`: `xrd_inversion/checkpoints/factorization_pilot/checkpoint_factorized.pt` (`sha256=083c200ab71c120a16b49066e11f412bbeccab781fa3d5d34e75dada8760857f`)
- `prediction_dump_factorized`: `xrd_inversion/outputs/factorization_pilot/prediction_dump_factorized.npz` (`sha256=def57fa4dbe17c9668a831dd2b36ab9e0a3f12f7f22b5e919d39546c1d38dfb5`)

The canonical handoff checkpoint and prediction dump use the primary fixed seed. All per-seed artefacts remain available in seed-specific subdirectories.

Reporting outputs:

- Results JSON: `xrd_inversion/reports/factorization_pilot_results.json`
- Figure-data JSON: `xrd_inversion/reports/factorization_pilot_figure_data.json`
- This report: `xrd_inversion/reports/FACTORIZATION_PILOT_REPORT.md`
- Per-seed checkpoints: `xrd_inversion/checkpoints/factorization_pilot/seed_<seed>/checkpoint_<condition>.pt`
- Per-seed prediction dumps: `xrd_inversion/outputs/factorization_pilot/seed_<seed>/prediction_dump_<condition>.npz`
- Tiny manifest: `xrd_inversion/runs/factorization_tiny_overfit/tiny_factorial_manifest_0b23d647a4bfb2bb.json` (canonical payload sha256=0b23d647a4bfb2bbeade2d6e3cd4b82ae01714052479f4a8474bedfe2adc1d60; file sha256=6c1e4277f21bc24a2222d9e8e0f9f905c051ab40f0455f90547a9f78ee86210a)
- Tiny profile bundle: `xrd_inversion/runs/factorization_tiny_overfit/tiny_factorial_profiles_0b23d647a4bfb2bb.npz` (file sha256=3ab04d343258d1577525734234716d576a8b834fbfd4f4cc282c9845e69bf606)
