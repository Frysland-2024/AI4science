# Garnet PXRD AutoLab: staged feasibility and baseline report

**Date:** 2026-10-19
**Status:** Stage 1 and Stage 2 completed; Stage 3 baseline comparison completed; no neural network training was run.
**Branch:** `codex/garnet-pxrd-autolab-next-20261019`, based on PR #37 head `3506a82`.
**Scope:** Independent audit of 44 shortlisted RRUFF Garnet records, followed by an a-only physical fitting pilot on 12 new Grossular development records. The work does not alter the primary crystal-system classification results or any frozen split/checkpoint.

## Decision summary

| Stage | Verdict | What the evidence supports |
|---|---|---|
| 1. Independent Garnet row audit | **LIMITED_GO** | The 44 records can support a small development pilot. A usable same-specimen CIF/reference structure was not established, and the RRUFF refined cells remain estimates rather than error-free truth. |
| 2. Grossular physical loop | **LIMITED_GO** | The pinned cubic template explains the major peak positions in the 12 predeclared non-frozen profiles and reduces full-profile RMSE in all 12. The residual intensity mismatch and lattice-reference offsets limit the claim to an engineering pilot. |
| 3. Baseline and adaptation protocol | **LIMITED_GO** | Five-start L-BFGS-B improves profile RMSE on all 12 and improves posthoc reference error on 6/12. A small ResNet/K-shot protocol is specified below, but the current 12 profiles are already development data and do not provide an independent adaptation/validation/test design. Do not train yet. |

**Overall recommendation:** Continue with targeted data/metadata collection and physical-model diagnostics. Do not start a ResNet fine-tune or claim validated sim-to-real adaptation from this dataset. The completed real-spectrum result is a useful feasibility signal, not an independently validated performance estimate.

## Stage 1 — Independent review of the 44 RRUFF candidates

The new auditor reparsed exact-ID members directly from the local official RRUFF archives; it did not trust the earlier row-level fields. It retains RRUFF subnumbers in IDs, hashes source archives and members, and writes only derived metadata. Source XY arrays and ZIP archives are not included in this branch.

### Counts and sample integrity

- **44/44** exact candidate IDs had one raw XY member and a numeric profile parsed as powder data. All 44 had a complete six-parameter cell in the same-ID `Refinement_Output_Data` entry, and all 44 had reported e.s.d. for `a`, `b`, and `c`. All entries are cubic; the three 90-degree angles are symmetry-fixed and have no independent e.s.d.
- **43/44** descriptions have no explicit mixture/contamination caveat. `R060125-1` is still a powder profile, but its description identifies a two-garnet mixture and it is excluded from the clean single-phase development list.
- **1/44** (`R060382-1`) lacks an exact-ID DIF auxiliary member. It still has the raw spectrum and refined-cell output; the missing DIF is recorded as an auxiliary-data issue, not as a missing raw profile or cell.
- The recorded lattice `a` range is **11.4941–12.1221 Å**. Profiles contain 8,500 or 8,501 points and cover approximately 5–90° 2θ.
- No exact numeric profile trace was duplicated among these 44 or against the scanned XY_RAW archive members. No related subnumber group was found within this 44-row set. This check does not prove that every distinct RRUFF ID is a physically independent specimen.
- Five IDs overlap prior benchmark roles by base ID and were excluded from new development: `R040159-1` (locked test), `R060446-1` (legacy RRUFF-70), `R060452-1` (locked test), `R060453-1` (adaptation pool), and `R061041-1` (locked test). That leaves **39** IDs not present in those prior roles. The predeclared new Grossular development set contains **12** exact IDs; none was read from a locked-test group.

### Chemistry and CIF compatibility

All 44 rows have a name/system/ideal-formula compatible AMCSD reference candidate. The auditor does **not** call any of them a same-specimen CIF match: **0/44** have evidence establishing specimen identity. Only **6/44** selected reference CIF formulas contain every element listed in the measured chemistry. The other 38 report substitutions or additional measured elements absent from the selected ideal/reference CIF: 5 rows miss one element, 8 miss two, 14 miss three, 8 miss four, and 3 miss five. Thus these CIFs are structural analogues/templates, not exact chemistry-resolved structures for the measured specimens.

The selected AMCSD candidate match is evidence-weighted by mineral name, ideal chemistry, cubic symmetry/cell, and the refinement record; it is not a deterministic one-to-one identity claim. The full row-level candidate counts, selected-record provenance, formulas, cell deltas, missing measured elements, and match fields are in the CSV manifest.

### Wavelength and parameter-reference limits

`XY_RAW` does not state an explicit wavelength, although its header contains cell parameters. Those header cells were explicitly excluded from every fit. The same-ID refinement artifacts list wavelengths `1.541838`, `1.540562`, and `1.544390 Å`; the indexed refinement rows use wavelength #2. Stage 2 fixed **1.540562 Å** as a documented proxy, not as verified instrument metadata for the raw trace. The same-ID refined `a` value and e.s.d. were read only after fitting for context. They are reference estimates and may carry systematic/model error beyond their reported statistical e.s.d.

### Parser corrections

The independent parser now treats detailed descriptions beginning with “Powder” as powder profiles while preserving mixture/contamination caveats, parses true element symbols from CIF labels such as `CaX`, and preserves the exact RRUFF subnumber. These changes are covered by parser tests. They do not change any frozen audit or benchmark files.

During the final summary-schema rerun, one Windows-shell invocation did not propagate the optional split argument and correctly reported `FROZEN_BOUNDARY_NOT_CHECKED`. That output was not accepted as the final audit: the command was rerun with explicit `--name=value` arguments, and the final JSON confirms `complete_by_base_id` plus hashes for both frozen inputs. The 12-profile physical runner independently requires both files and rejects any sample present in either boundary.

**Stage 1 deliverables:** `pxrd_router_mvp/garnet_audit.py`, `pxrd_router_mvp/tests/test_garnet_audit.py`, `reports/garnet_rruff_44/garnet44_independent_review.csv`, and `reports/garnet_rruff_44/garnet44_independent_review.json`.

## Stage 2 — Pinned Grossular template and single-a physical fit

### Structure and model

The local project uses COD **9001868**, a 293 K cubic `Ia-3d` Grossular reference with formula `Ca3Al2Si3O12` and initial `a=11.847 Å`. Its standalone CIF SHA-256 is `d6b3d78a1d487de504d4d47db9cbd1a2dc28e51e99c9c43a0565c8e1325cbb1e`. The source is [COD 9001868](https://www.crystallography.net/cod/9001868.html); COD states its database contents are public domain/CC0 and requests attribution to the source publication ([COD terms](https://www.crystallography.net/cod/)). This reference is independent of the 12 RRUFF specimens.

The fit reuses `pxrd_router_mvp.crystal.render`. Only cubic `a` is a nonlinear structural parameter; `b=c=a` and all angles stay fixed. Wavelength, zero shift, and Gaussian FWHM are fixed at 1.540562 Å, 0°, and 0.14° respectively. Intensity scale and constant background are solved linearly for each trial `a`. The existing BaTiO3/MgO/CeO2 candidate tests and defaults remain in place. No raw XY header cell parameter enters model initialization, bounds, candidate ranking, or fitting.

### Synthetic gate

With seed `20261019`, a synthetic profile generated at `a=11.930000 Å` was recovered as **11.929993 Å** (absolute error `0.000007 Å`; normalized full-profile RMSE `0.001027`). This passed the predeclared synthetic recovery limit of `0.01 Å` before the real development profiles were loaded.

### New real development profiles

The predeclared set is `R040065-1`, `R040066-1`, `R050036-1`, `R050081-1`, `R050312-1`, `R060278-1`, `R060382-1`, `R060442-1`, `R060443-1`, `R060444-1`, `R060499-1`, and `R070551-1`. The runner rejects any ID found in the frozen manifest or locked-test split, reads numeric XY rows only, and keeps the same-ID cell for post-fit reporting only.

The predeclared real-profile gate passed:

- Fit RMSE improved over the fixed CIF initial profile on **12/12** samples (gate: at least 10/12).
- For each sample, at least 80% of the eight strongest predicted peaks were within 0.25° of an observed peak on **12/12** samples (gate: at least 10/12).
- There were **0/12** load failures.
- The fitted `a` values span **11.8314–11.9593 Å**. Their mean absolute difference from the posthoc RRUFF refined `a` estimates is **0.01985 Å** (median `0.01766 Å`; maximum `0.03278 Å`). These differences are substantially larger than the listed statistical e.s.d. values, so they should be interpreted as model/instrument/composition mismatch and reference uncertainty, not as high-accuracy lattice recovery.
- The mean fitted normalized full-profile RMSE is **0.02318**. Peak positions are better explained than the full intensity profile; the model omits K-alpha doublet, preferred orientation, absorption, microstrain, and phase-mixture effects.

This is enough to justify a narrowly scoped physical baseline comparison. It is not enough to claim a general or calibrated real-spectrum solver.

### Concurrent related pilot

A separate Draft [PR #40](https://github.com/Frysland-2024/AI4science/pull/40) was created on the same PR #37 base while this work was in progress. It is preserved and not merged into this branch. PR #40 uses COD 9001871 (`a0=11.619 Å`), three Grossular profiles, wavelength #1, and a broader fit over `a`, zero shift, width, scale, and affine background; its predeclared multistart-spread gate fails (`0.546–0.846 Å`) and its status is `PHYSICS_MODEL_NOT_READY`. This branch instead audits 44 candidates and uses 12 profiles, COD 9001868 (`a0=11.847 Å`), wavelength #2 as a proxy, and only one free structural parameter with the instrument terms fixed. The metrics are not directly comparable. PR #40's instability finding is a reason to keep this branch's interpretation limited and to defer training until the physical model and inputs are reconciled.

**Stage 2 deliverables:** `pxrd_router_mvp/grossular_project.py`, `pxrd_router_mvp/projects/grossular/project.json`, the pinned CIF under `pxrd_router_mvp/projects/grossular/templates/`, `pxrd_router_mvp/tests/test_grossular_project.py`, `tools/run_grossular_pilot.py`, and `reports/garnet_rruff_44/grossular_dev_fit_results.json`.

## Stage 3 — CIF initial vs five-start physical baseline; no training

Because the predeclared Stage 2 gate passed, the same 12 development profiles were compared using (a) fixed CIF initial `a=11.847 Å` and (b) five-start L-BFGS-B refinement within the predeclared ±2.5% `a` bounds. Both use the same renderer, fixed wavelength/shift/width, scale/background treatment, 2θ span, and post-fit reference definition. The RRUFF refined cell was not used during optimization.

| Metric across the 12 development profiles | CIF initial | Five-start L-BFGS-B |
|---|---:|---:|
| Mean full-profile RMSE | 0.02711 | 0.02318 |
| Median full-profile RMSE | 0.02349 | 0.02176 |
| Mean absolute `a` difference vs posthoc RRUFF reference | 0.03622 Å | 0.01985 Å |
| Median absolute `a` difference vs posthoc RRUFF reference | 0.02130 Å | 0.01901 Å |
| RMSE improved vs CIF initial | — | 12/12 |
| Posthoc reference error improved vs CIF initial | — | 6/12 |
| Solver success / failures | — | 12/12 / 0/12 |
| Mean / median CPU runtime per profile | — | 1.86 s / 1.61 s |

The five-start fit improves profile agreement consistently, but changes the lattice reference error in both directions. Its 6/12 parameter-error improvement is not a supervised-accuracy claim because the reference cell is approximate and was excluded from fitting. The machine-readable file contains every sample result, attempt, bound, runtime, and input spectrum hash.

### Proposed small ResNet/K-shot protocol (proposal only)

1. **Before training:** obtain new, independent Grossular-family profiles with verified instrument wavelength/geometry and specimen provenance. The 12 samples above are development data and must not be re-used as untouched validation or test data. Split by exact sample/base identity; keep every scan from one specimen in one partition.
2. **Input/output:** use a fixed, documented 2θ grid and normalized intensity. Predict one scalar cubic `a` (or `Δa` from the pinned CIF); derive `b=c=a`. Train a modest 1D ResNet on simulator-generated profiles from the hash-pinned Grossular CIF and explicit composition/measurement perturbations. Do not introduce a new loss family in this first comparison.
3. **Few-shot arms:** simulated-only initialization, then K-shot adaptation with `K=1,3,5` labeled spectra drawn only from a designated adaptation partition. If the independent pool cannot support separate adaptation, validation, and test identities, report the experiment as exploratory and do not produce a held-out performance claim.
4. **Fixed baselines:** pinned CIF initial `a`; the same five-start L-BFGS-B physical fit; and, after model training is separately authorized, ResNet zero-shot and ResNet-initialized physical refinement. Keep forward model, bounds, stopping budget, wavelength handling, and candidate CIF identical across arms.
5. **Report:** reference `a` error with the RRUFF e.s.d. caveat, full-profile RMSE, peak-position agreement, optimizer success/failure, wall time, and adaptation sample count. Select no checkpoint or hyperparameter using the final test partition. Acquire enough separate samples to make all roles real; the current 12-profile development set cannot by itself support this validation design.

**Stage 3 deliverables:** `tools/run_grossular_baselines.py`, the added synthetic multistart test, and `reports/garnet_rruff_44/grossular_baseline_comparison.json`. No ResNet, GPU job, Qwen agent, or multi-user platform was created or run.

## Reproduction and verification

Use the local official RRUFF ZIP directory as `$ArchiveRoot`; the raw archives stay outside Git. The CSV/JSON record the official source URLs, archive hashes, and byte sizes. The frozen manifest and split are read-only inputs. On this machine, set the paths as follows (adjust only the three local input paths when reproducing elsewhere):

```powershell
$ArchiveRoot = 'E:\AI4science\RRUFF'
$FrozenManifest = 'E:\AI4science\xrd_robustness\data\real_xrd\rruff371\manifests\rruff371_master_manifest.csv'
$FrozenSplit = 'E:\AI4science\xrd_robustness\data\real_xrd\rruff371\splits\rruff301_adaptation_test_split.csv'
py -3 -m pxrd_router_mvp.garnet_audit --archive-root=$ArchiveRoot --output-dir=reports\garnet_rruff_44 --frozen-manifest=$FrozenManifest --frozen-split=$FrozenSplit
py -3 -m tools.run_grossular_pilot --archive-root=$ArchiveRoot --frozen-manifest=$FrozenManifest --frozen-split=$FrozenSplit --output=reports\garnet_rruff_44\grossular_dev_fit_results.json
py -3 -m tools.run_grossular_baselines --stage2-result=reports\garnet_rruff_44\grossular_dev_fit_results.json --archive-root=$ArchiveRoot --frozen-manifest=$FrozenManifest --frozen-split=$FrozenSplit --output=reports\garnet_rruff_44\grossular_baseline_comparison.json
py -3 -m unittest discover -s pxrd_router_mvp\tests -v
```

The recorded test run completed **18 tests successfully**, with **3 optional local-data/checkpoint tests skipped**. The existing BaTiO3/MgO/CeO2 tests passed unchanged. The frozen RRUFF manifests and data remain outside this branch's write set. Review and merge are not performed by this task.
