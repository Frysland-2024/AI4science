# Fresh A/B/D results — 2026-10-19

## 中文结论

按预注册方案完成 30 个模型候选：simple/V9 两条件、A/B/D 三方法、3 个配对 seed，所有候选均跑满 24 epoch。训练与验证选型用时 `722.78 / 7200 s`。新测试集每个 seed 77 个父结构；所有 λ 和 checkpoint 选择冻结后，测试集只评估一次。

预注册根因假设**未获支持**。D 的零点偏移监督确实把 V9 测试零点偏移 RMSE 从 B 的 `0.02676°` 降到 `0.01255°`（改善 53.1%），但 q-MAE 从 B 的 `0.03238` 升到 `0.04618`，恶化 42.6%；三组配对 seed 的 q-MAE 均更差，a/c MAE 分别恶化 16.0%/19.5%。simple 条件也未通过保护线：D 的 a-MAE 比 B 高 27.5%。因此，历史验证中零点偏移误差与 du 误差的强相关并不足以说明零点偏移标签会改善晶格反演。此项一次性干预不能排除其他测量 nuisance 或优化因素的作用，也不构成真实 XRD 证据。

## Frozen design and execution

- Fresh NPZ: `fresh_data/fresh_batio3_paired.npz`, SHA-256 `3e4f4951fe2cb8d676871f4a38d32dfd48d317a49fbf6be401b2c9ca25c3e25e`; 512 parent q draws split 358/77/77. The old PR26 test was excluded.
- All three methods used the same 13,008,325-parameter `MeasurementAwareRegressor`. A used q supervision only; B used q plus measurement-aware expected-profile loss; D added a fixed-weight normalized zero-shift training-label loss while retaining reconstruction-to-q gradients. D uses extra simulator information.
- Validation selected simple λ: B `0.1`, D `1.0`; V9 λ: B `1.0`, D `1.0`. These values were written to `training_selection.json` before test arrays were loaded.
- All 30 candidate runs completed 24 epochs with no non-finite loss/gradient or budget interruption. Training plus validation selection took `722.78 s`; the single test evaluation, including matched q-fixed eta optimization, took `147.13 s` outside that training budget.
- Test scope: 77 held-out parent draws per seed, both paired conditions, 1,386 per-sample method/condition/seed rows, and 1,386 equal-protocol q-fixed eta fits (L-BFGS-B, same neutral start, bounds, objective, max 60 iterations). Three of the fits reported solver non-success; retain them in the full records.
- The held-out zero-shift measurement is post-hoc diagnostic truth only. It was not used for training D, checkpoint selection, or λ selection. No nuisance oracle was used at inference.

## Primary held-out metrics

Entries are mean ± sample SD over three paired model seeds. q-MAE averages the absolute errors of normalized `du,dv`; `a/c` are in Å. Each seed uses the same fresh 77-parent test split.

| Condition | Method | q-MAE | a-MAE (Å) | c-MAE (Å) | zero-shift RMSE (°) |
|---|---:|---:|---:|---:|---:|
| simple | A | 0.01503 ± 0.00238 | 0.000505 ± 0.000120 | 0.000668 ± 0.000071 | 0.002334 ± 0.001050 |
| simple | B | 0.01805 ± 0.00138 | 0.000471 ± 0.000087 | 0.000893 ± 0.000047 | 0.002779 ± 0.000933 |
| simple | D | 0.01791 ± 0.00073 | 0.000600 ± 0.000084 | 0.000867 ± 0.000108 | 0.001163 ± 0.000839 |
| V9 | A | 0.03531 ± 0.00373 | 0.001457 ± 0.000101 | 0.001996 ± 0.000066 | 0.032456 ± 0.000070 |
| V9 | B | 0.03238 ± 0.00220 | 0.001312 ± 0.000128 | 0.001654 ± 0.000085 | 0.026757 ± 0.004509 |
| V9 | D | 0.04618 ± 0.00150 | 0.001522 ± 0.000123 | 0.001977 ± 0.000148 | 0.012545 ± 0.002435 |

The zero-shift mechanism check passed, but the primary q/a/c rule failed in V9 and the simple guardrail failed. On V9, D's q-MAE was worse than B in all 3 seeds. Do not select D as an improved inverse model from this round.

## Supporting profile results

These use the transformed observed-profile space. Direct profile RMSE uses each model's predicted q and eta. The second profile column uses a common q-fixed nuisance fit for every method after test opening.

| Condition | Method | Direct predicted-eta profile RMSE | Matched q-fixed eta-fit profile RMSE |
|---|---:|---:|---:|
| simple | A | 0.02952 ± 0.00095 | 0.00915 ± 0.00068 |
| simple | B | 0.01431 ± 0.00099 | 0.01035 ± 0.00065 |
| simple | D | 0.01546 ± 0.00106 | 0.01020 ± 0.00015 |
| V9 | A | 0.03913 ± 0.00176 | 0.01404 ± 0.00073 |
| V9 | B | 0.02255 ± 0.00013 | 0.01298 ± 0.00061 |
| V9 | D | 0.02533 ± 0.00249 | 0.01717 ± 0.00043 |

The matched fit succeeded on `1,383/1,386` test profiles. The three reported non-success cases are retained per sample; there was no test-time retuning.

## Task-required joint q+eta refinement and neutral-start physics baseline

The frozen preregistration specified the q-fixed eta-only fits above. The task document also required bounded joint q+eta refinement and a neutral-start physics-only baseline. These were run as an explicitly post-hoc secondary evaluation after the primary test result was frozen. The optimizer used only the observed profile and its permitted initialization; `q_true` and `eta_true` were used only after each fit for scoring. No checkpoint, lambda, or primary decision changed. The exact fixed settings and this timing caveat are recorded in `POSTHOC_REFINEMENT_PROTOCOL.md`.

Each model-start fit used that sample's predicted q and common neutral eta start `[0, 0.105, 0.005]`; the physics-only baseline started from q `[0, 0]` plus the same eta. Both used the same measurement-aware expected-profile MSE, bounds, and L-BFGS-B settings (60 iteration maximum). The model-start column reports mean ± sample SD over three seed-level test means; all 231 fits per condition/method converged successfully. `Bound` counts any optimized q or eta coordinate at its configured bound. The 1,540 supplemental fits took 277.45 s total; each row's runtime, status, iterations, and bound flags are preserved.

| Condition | Method start | Refined q-MAE | Refined a-MAE (Å) | Refined c-MAE (Å) | Observed-profile RMSE | Mean iterations | Mean seed p95 (s) | At bound / 231 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| simple | A | 0.000329 ± 0.000011 | 0.0000122 ± 0.0000005 | 0.0000152 ± 0.0000017 | 0.005639 | 19.77 | 0.218 | 124 |
| simple | B | 0.000311 ± 0.000011 | 0.0000112 ± 0.0000007 | 0.0000144 ± 0.0000013 | 0.005639 | 20.60 | 0.225 | 128 |
| simple | D | 0.000351 ± 0.000016 | 0.0000125 ± 0.0000004 | 0.0000166 ± 0.0000017 | 0.005639 | 20.16 | 0.224 | 122 |
| V9 | A | 0.000439 ± 0.000017 | 0.0000158 ± 0.0000016 | 0.0000202 ± 0.0000001 | 0.006201 | 21.32 | 0.241 | 0 |
| V9 | B | 0.000400 ± 0.000032 | 0.0000143 ± 0.0000009 | 0.0000189 ± 0.0000019 | 0.006194 | 21.37 | 0 |
| V9 | D | 0.000437 ± 0.000045 | 0.0000159 ± 0.0000019 | 0.0000205 ± 0.0000027 | 0.006194 | 21.11 | 0 |

| Neutral physics start | Refined q-MAE | a-MAE (Å) | c-MAE (Å) | Observed-profile RMSE | Solver success | Mean iterations | p95 fit time (s) | At bound / 77 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| simple | 0.09464 | 0.003180 | 0.004749 | 0.022751 | 76/77 | 31.13 | 0.446 | 45 |
| V9 | 0.01664 | 0.000581 | 0.000680 | 0.009451 | 77/77 | 27.21 | 0.326 | 2 |

The neutral-start baseline is much worse than model-start refinement in simple profiles and remains worse in V9, though its V9 q-MAE is lower than the direct neural predictions. All learned starts reach similar near-generator q accuracy after refinement; this shows that the shared forward objective can refine useful starts in this single-template synthetic setting, not that B or D improved direct inference. The 120–128 simple model-start fits at a bound are retained as a warning that nuisance/parameter trade-offs remain active. Full per-sample starts, fitted parameters, failures, iterations, timings, and bounds are in `joint_qeta_refinement_per_sample.json` and `.csv`.

## Interpretation and next decision

The intervention improved D's V9 shift estimate while worsening q, lattice `a/c`, and profile fit. That pattern refutes the preregistered claim that simulator shift supervision alone would relieve the observed q bottleneck. The validation correlations remain real descriptive evidence, but they may reflect coupled estimation or shared optimizer dynamics. Do not repeat this D intervention or add post-hoc variants. Any future work needs a new, independent validation-grounded hypothesis and a fresh preregistration.

All evidence is synthetic and conditional on one public BaTiO3 P4mm CIF, fixed background shape, and these simulator noise ranges. It says nothing about real instrument calibration, unseen structures/compositions, or Rietveld refinement. This is an exploratory 3-seed comparison, not a population-level statistical result.

## Artifacts

- Per-seed and per-sample metrics: `fresh_results_per_seed.csv/json`, `fresh_test_per_sample.csv/json`.
- Required post-hoc joint refinements and neutral-start physics baseline: `joint_qeta_refinement_per_sample.json/csv` and `joint_qeta_refinement_summary.json`; fixed supplemental protocol: `POSTHOC_REFINEMENT_PROTOCOL.md`.
- Full candidate histories and selection: `training_runs.json`, `training_selection.json`.
- Data, source, run, and local checkpoint hashes: `fresh_data/split_manifest.json`, `runtime_manifest.json`, `checkpoint_manifest.json`, and `reproducibility_manifest.json`.
- Figures: `rootcause_validation_diagnostics.png` and `fresh_test_metrics.png`; plotting source: `make_figures.py`.
- All 30 candidate `.pt` files are retained locally under `checkpoints/` and ignored by Git; their byte sizes and SHA-256 values are in `checkpoint_manifest.json`.
- See [`AUDIT.md`](AUDIT.md), [`CAUSE_RANKING.md`](CAUSE_RANKING.md), and the pretraining freeze records for the source audit and immutable protocol.
