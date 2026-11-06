# PXRD SimXRD / CNN11 Pilot — 2026-11-03

> **Integrity hold (2026-11-03):** The initial pilot routed V10-labelled training and validation views through the V9 Gaussian renderer, and the evaluation helper left CNN11 in `eval()` after its first validation. The integration fixes and regression tests are now on this PR, but the recorded V10 ResNet and CNN11 outputs below were produced before those fixes. The archived outputs cannot support a V10 or CNN11 comparison. No rerun has been performed. Standalone renderer smoke checks did not exercise these integration paths.

## Decision record

**Date:** 2026-11-03  
**Question / previous assumption:** The 2026-10-23 scale-up plan called for a versioned, label-preserving simulator pilot on the existing CIF split before any 100k expansion; CNN11 was a conditional architecture comparison. The user's current request authorizes this bounded three-configuration follow-up and explicitly separates it from the thesis evidence frozen on 2026-10-26.

**New evidence and reasoning:** Source inspection of SimXRD/Pysimxrd found a physically parameterized Voigt peak renderer, grain-size-dependent broadening, and convolution with detector geometry / slit effects. The public Salgado et al. repository implements a no-pooling 1D CNN and dense predictor; the paper describes the no-pooling variant as retaining the convolutional CNN while removing pooling. These are selective references, not evidence that their complete simulator or data pipeline is transplanted.

**Decision:** Run a small, fixed-budget, post-main pilot on the existing 14,060-structure parent-disjoint CIF dataset. Compare (1) frozen V9 Gaussian + historical ResNet-18-GN checkpoints, (2) V10 pseudo-Voigt/Caglioti + ResNet-18-GN, and (3) V10 + a SimXRD / Salgado no-pooling CNN11-style model. All use the existing CE + dynamic same-parent JS objective where training occurs. No CIF expansion, broad hyperparameter sweep, or additional architecture search follows this comparison.

This explicit three-configuration request uses ResNet-18-GN as the fixed reference and does not execute the broader ResNet architecture/optimizer retuning step recorded in the earlier 2026-11-03 project sequence. That retuning/search is outside this bounded pilot; the pilot stops after this comparison.

**Original execution:** The initial attempt used the dated pilot output and report directories. RRUFF-70 was evaluated once after the historical checkpoint freeze under the 2026-11-03 authorization.

**What does NOT change:** The 2026-10-26 frozen thesis evidence, its configurations, selected checkpoints, splits, and reported results remain untouched. Existing V9 simulator behavior is the default for old call sites. The original Test split is already-used evidence and this work is labeled post-main supplementary evaluation. The historical RRUFF execution lock is not edited; its evaluation-disabled flag remains as provenance, with the current user authorization recorded in the separate pilot freeze manifest.

**Status (2026-11-06):** Integration fixes and regression coverage are in PR #62. The corrected pilot is pending. Archived outputs document the failed pre-fix attempt.

**Relevant files / commits:** `docs/PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md`; `xrd_robustness/configs/simulation.simxrd_v10_pilot.20261103.json`; `xrd_robustness/configs/simxrd_cnn11_pilot.20261103.json`; `xrd_robustness/src/xrd_robustness/simulator_v10.py`; `xrd_robustness/src/xrd_robustness/models/simxrd_cnn11.py`; `xrd_robustness/scripts/run_simxrd_architecture_pilot.py`; final evidence in `xrd_robustness/reports/simxrd_architecture_pilot_20261103/`.

## Frozen protocol for the original attempt

- Data and split: existing `formal_14060`, with 9,842 Train / 2,109 Validation / 2,109 Test parent structures. No additional CIF records.
- New-model budget: 49,280 optimizer steps, 16 parent structures per step, AdamW at `1e-4`, weight decay `1e-4`, dynamic JS `lambda=60`; 3 fixed training seeds: `20260711`, `20260712`, `20260713`.
- Validation-only selection: mean single-factor OOD Macro-F1 on the six frozen Validation profiles; tie-break by in-range Macro-F1, then earlier step. No Test or RRUFF metrics enter selection.
- Simulated Test: post-main supplementary evaluation on the existing Test parents, across 3 fixed simulation seeds, six OOD profiles, and both V9 and V10 renderers.
- RRUFF: the existing balanced RRUFF-70 manifest and 10–80° / 0.02° / linear interpolation / zero-fill / max-normalization preprocessing. One-time Accuracy and Macro-F1 evaluation after checkpoint freeze, explicitly authorized by the current user request. No RRUFF spectra are included in public artifacts.
- Cost: report measured training time, optimizer throughput, peak allocated CUDA memory, and parameter count on the local RTX 4060 Laptop GPU. Historical training wall time is not inferred from a different machine.

## Model and simulator scope

V10 changes only peak rendering: area-normalized pseudo-Voigt profiles, with angle-dependent Caglioti-form width terms. Peak positions and reflection intensities remain supplied by the existing peak tables; the same-parent pair sampler, preferred orientation, zero-shift, background, and noise stages are retained. Coefficients are generic pilot values and are not calibrated to a particular diffractometer. The width perturbation does not change the stored crystal-system label.

The CNN11-style implementation uses three no-pooling Conv1D layers (80 channels; kernels 100/50/25; strides 5/5/2), ReLU and dropout, followed by dense widths 2300/1150 and seven output logits. It is trained with the same CE + JS routine as ResNet-18-GN. This is a PyTorch reimplementation of the published architecture pattern, not a claim of identical preprocessing, initialization, or training protocol.

## Source references

- SimXRD/Pysimxrd peak rendering: [`WPEMsim.py`](https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/utils/WPEMsim.py) and [`funs.py`](https://github.com/Bin-Cao/SimXRD/blob/main/src/Pysimxrd/utils/funs.py).
- Salgado et al. (2023), *Automated classification of big X-ray diffraction data using deep learning models*, [npj Computational Materials](https://www.nature.com/articles/s41524-023-01164-8), with the authors' [XRDs code](https://github.com/AGI-init/XRDs).

## Corrected rerun checklist — pending execution

The V10 callable is used by training prefetch and the shared Validation/Test panel builder. The panel evaluator restores the incoming model mode in `finally`. The [XRD tests run for 5e5777d](https://github.com/Frysland-2024/AI4science/actions/runs/41984524129) passed, including the non-data-bound integration tests for peak views, cached structures, prefetch, Validation panels, and mode/Dropout restoration. The completed Codex review applies to the pre-fix commit `8f7890b`.

From the repository root with the test dependencies installed and the original dataset available, use a fresh output directory. The runner writes reports under that same directory. Reuse the same directory for each phase of a single attempt.

```bash
set -euo pipefail
git rev-parse HEAD
test -z "$(git status --porcelain --untracked-files=no)"
(cd xrd_robustness && python -m pytest -q tests/simulation/test_simxrd_pilot_integrations.py)

pilot=xrd_robustness/scripts/run_simxrd_architecture_pilot.py
mkdir -p xrd_robustness/outputs
out=$(mktemp -d "$PWD/xrd_robustness/outputs/pr62-rerun.XXXXXX")
args=(--data-root "$PWD/xrd_robustness/data/formal_14060" --output-root "$out" --device cuda)
python "$pilot" --phase smoke "${args[@]}"
git rev-parse HEAD > "$out/reports/source_commit.txt"
python "$pilot" --phase train_resnet "${args[@]}"
python "$pilot" --phase train_cnn11 "${args[@]}"
```

These phases use one local GPU job at a time. The runner checks the frozen split, structure records and reflection-cache manifest hashes. Reuse the renderer-independent ideal reflection cache and the three original V9 ResNet checkpoints. Start both V10 models from scratch for seeds `20260711`–`20260713` at 49,280 steps each, batch 16, AdamW with learning rate and weight decay `1e-4`, same-parent two-view CE + JS with lambda 60, and the frozen runtime policy. Selection uses only Validation seed `20260721`, mean Macro-F1 across six OOD profiles, in-range Macro-F1, and then earlier step.

### Evidence required before merging this PR as a comparison

1. Record the corrected source commit, green CI, fresh smoke, runtime/precision, renderer/config hashes and data hashes. Check that real V10 training and Validation views differ from V9 under fixed inputs. Capture fresh training logs, validation histories, run status and checkpoint hashes for all six runs. If CNN11 has a nonfinite or incomplete run, preserve the failure and actual budget and keep architecture selection open.
2. Check that both V10 models completed the same three seeds and budgets before freezing. The script accepts partial checkpoints for descriptive evaluation, so check the per-seed run records explicitly. Once the repeat RRUFF-70 evaluation is separately authorized, run the following with the same `args`. The original one-time RRUFF-70 authorization was already used, and the runner's `evaluate` phase evaluates both simulated Test and RRUFF. Keep the historical execution lock intact.

   ```bash
   rruff="$PWD/xrd_robustness/data/real_xrd/rruff70"
   python "$pilot" --phase freeze "${args[@]}" --rruff-root "$rruff"
   python "$pilot" --phase evaluate "${args[@]}" --rruff-root "$rruff"
   ```

3. Bind the new freeze and evaluations to the corrected run and verify checkpoint/panel hashes. Build fresh common V9 and V10 Test panels for seeds `20260721`–`20260723` and six OOD profiles on the same Test parents, and evaluate all three configurations on both panel sets. Test is previously used supplementary evidence. Any authorized RRUFF-70 repeat is supplementary reuse of the same panel. Keep Test and RRUFF outside checkpoint selection and tuning. The V10 architecture comparison holds the renderer fixed, while the historical V9 reference provides context.
4. Publish the corrected report, update the PR summary and current state from the new records, and obtain review of the corrected head. Keep Issue #60 and the architecture decision open until valid evidence is available. Scope stays at the frozen 14,060-parent pilot.

### Artifacts to supersede

Publish new smoke records, V10 Validation panels, common Test panels and panel indexes, V10 checkpoints, per-seed run records/logs/validation histories, both `*_training_results.json` summaries, `model_selection_freeze.json` and `results.json`. Record any new failure separately. The [original report directory](../xrd_robustness/reports/simxrd_architecture_pilot_20261103/) is archival. Preserve the original failure record, implementation manifest and preflight logs there. Every V10-trained checkpoint and its derived metrics, including on V9 Test or measured RRUFF, needs fresh evaluation. Historical V9 checkpoint files remain eligible for reuse, but regenerate their scores for the corrected comparison.
