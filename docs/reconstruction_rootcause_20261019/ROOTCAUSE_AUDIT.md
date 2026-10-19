# Reconstruction root-cause audit — 2026-10-19

## Scope and decision

This audit explains the mixed A/B/C results for the synthetic, single-CIF BaTiO3 measurement-aware reconstruction task, corrects specific bookkeeping and comparison errors, and preregisters one new intervention. One bounded fresh round was run only after the source/physics, reproducibility, runtime, and GPU-concurrency checks passed. The comparison remains a synthetic interpolation study for COD 9014273; it does not validate real PXRD, unseen materials, or Rietveld refinement.

## What was already known

- Issue 19's fixed-background physical gate passed: Torch/V9 profile parity, finite-difference gradients, local q+eta identifiability, non-oracle recovery, and expected-noise checks met their frozen thresholds. The unrestricted background-shape variant was non-identifiable and was correctly excluded; the fixed configured shape was retained without lowering thresholds.
- Issue 31's original A/B/C round used 512 parent-q draws split 358/77/77, three paired model seeds, and a 24-epoch cap. C detached q only on the reconstruction branch. Its result was mixed on V9, so repeating q-detach was not a useful new causal test.
- The old PR26 test was opened. Neither its post-hoc profile fits nor its method metrics were used for the new intervention, training, validation selection, or thresholds.

## New source and evidence checks

1. Re-read the current branch's raw JSON, arrays, run histories, manifests, and source scripts. The fresh Issue 31 NPZ matches SHA-256 `d43a364e75b2acd46e1b9c5351ffc5b0a9356d750ed9e1a8a449b7776168993d`; its recorded array hashes and 358/77/77 split are internally consistent. `eta_true` is a separate diagnostic array and was excluded from the prior A/B/C inputs and losses. The current working-tree CRLF form of the frozen source config hashes to `a558304235509b2d00c95e3423e084e5a08af9b1d3ad6e312c0032318df40bd3`; CRLF normalization reproduces the committed LF blob and prior frozen hash `b17a9db0eed38557f4b06a092f8d4a35437619025f78532119e3a923ddf2251f`. This is line-ending conversion only.
2. Corrected the validation-gradient denominator from the raw 6 batches per seed (5 per seed, 3 seeds) to 15 per condition. V9 q-output gradients opposed q supervision in 6/15 batches, with cosine range `-0.3073..0.7111` and mean `0.1140`; shared-trunk gradients opposed in 4/15, range `-0.5064..0.9251`, mean `0.4447`. Simple had 0/15 negative q gradients (range `0.4503..0.8377`, mean `0.7024`) and 0/15 negative trunk gradients (range `0.5732..0.9056`, mean `0.7393`). Earlier reporting used 6/30 and 0/45; those denominators were wrong. No historical file was rewritten.
3. On the old validation split only, B's V9 zero-shift MAE was `0.02276`, `0.02768`, and `0.03156` degrees for the three seeds. The validation correlation between du error and zero-shift error was `0.904`, `0.853`, and `0.949`. This is a strong association in this simulator, not proof that shift error causes the q error. Simple-condition nuisance MAEs were much smaller (shift `0.00133–0.00277` degrees).
4. The old PR26 residual comparison used unequal optimization compute. A's per-profile nuisance fit and B's predicted nuisance were not a fair inference-cost comparison. The post-hoc equal-budget refit on the already-open old test made q MAE nearly identical (simple `0.000286` vs `0.000296`; V9 `0.000430` vs `0.000429`) and is descriptive only.
5. The DONUT `~0.2918` versus `~0.00035` comparison also mixed tasks and initialization. `~0.2918` was texture-OOD, while `~0.00035` came from joint q+eta fitting initialized by supervised B predictions on ordinary noisy profiles. Direct DONUT noisy q-MAE was about `0.2280 ± 0.2825`; neutral-start physics-only fit was about `0.0506`; supervised-start joint fit was about `0.00034`. These values do not establish failure of upstream DONUT. See read-only branch audit `codex/donut-pxrd-experiment-20261019@31fc7f7`.
6. Run histories contain train q/reconstruction losses and validation q-MAE, but not validation reconstruction loss, epochwise nuisance-head saturation, or epochwise gradient diagnostics. The evidence therefore supports a measured nuisance-prediction gap and intermittent V9 gradient conflict; it does not support a logit-saturation claim. Three seeds are too few to distinguish these effects from optimization variance.
7. The compact PR26 checkpoint manifest is present but binary `.pt` weights are absent from this worktree. Hashes and predictions could not be independently reloaded here. New training does not depend on those weights; it uses the current tracked simulator/model source and a separately generated dataset.

## New root-cause hypothesis

For the V9 condition, the leading actionable bottleneck is the unsupervised zero-shift output: its validation error is comparatively large and tracks lattice-du error closely. A secondary contributor is intermittent conflict between q-parameter and expected-profile gradients. The data do not establish which contribution is causal. The preregistered D intervention adds only simulator-provided zero-shift supervision while retaining the B reconstruction path and its direct gradient into q. The label is additional information, so D is not an equal-information comparison with A or B.

## Physical and runtime gates

The Issue 19 fixed-background physical gate is reused unchanged and passed; the free-background non-identifiability failure remains explicitly excluded. The old-test data remain excluded from all choices. The isolated runtime was verified at `C:\Users\Lenovo\.codex\venvs\issue19-measurement-closure\Scripts\python.exe`, PyTorch `2.13.0+cu126`, CUDA available, one NVIDIA GeForce RTX 4060 Laptop GPU. Four extant Python processes had no Torch/CUDA modules loaded. `nvidia-smi` showed approximately 2% utilization; its permission-limited process entries resolved to Windows shell/UI, browser, chat, QQ/WeChat, or LegionZone processes. No active Python/CUDA training process was found, and none was disturbed.

## Evidence classification

All reported numerical evidence above is from simulator-generated data and the repository's historical validation or opened-test records. The new round's data generation seeds, model seeds, selection rules, thresholds, and code hash are frozen in `PREREGISTRATION.md`, `frozen_train_config.json`, and `FROZEN_SHA256SUMS.txt` before the new run. The fresh test is opened once only after all validation choices are frozen.
