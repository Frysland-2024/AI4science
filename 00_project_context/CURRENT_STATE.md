# AI4science Current State

**Status date:** 2026-08-23

**Authority:** current project state for `Frysland-2024/AI4science`

**Phase:** evidence freeze → manuscript and figure construction

## 1. Current scientific design

当前论文问题是：在线 PXRD 模拟器能够为同一 parent structure 生成不同物理扰动视图时，measurement-equivalence consistency 是否能提高七晶系分类器的合成 OOD 鲁棒性。

冻结合同如下：

- task：7-class crystal-system classification；
- backbone：ResNet-18-GN；
- baseline：Dynamic ERM；
- selected method：Dynamic JS Consistency，`lambda_js=60`；
- preprocessing：identity；optimizer：AdamW；schedule：constant LR；
- split：Train 9,842 / Validation 2,109 / Test 2,109；
- split claim：exact-parent-disjoint only。

模型不输出晶格常数、相分数、应变、织构、峰宽或其他物理参数。

## 2. Completed and frozen evidence

| Evidence | Dynamic ERM | Dynamic JS | Paired result |
|---|---:|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | Δ `+0.046569`; 5/5 positive |
| Frozen simulated Test mean single-factor OOD Macro-F1 | 0.65074 | 0.70534 | Δ `+0.054600`; 5/5 positive |
| RRUFF-301 few-shot Macro-F1, K=1/2/5 | — | — | Δ `+0.0433/+0.0460/+0.0545` |

Validation ten-run 与 frozen simulated Test 均已完成并关闭。Test 只支持 aggregate synthetic-OOD robustness improvement；它不证明每个晶系或每个压力条件都改善。

RRUFF-301 是当前最强的真实域补充证据，但只能称为 **retrospective validation**。历史 runner、episode support IDs、独立执行授权、完整日志以及代码/运行时绑定不全，因此不能升级为 confirmatory evidence。该 provenance 缺口是论文 claim limitation，**不是当前 blocker，也不构成重跑理由**。

旧 `per_crystal_system_f1` diagnostic 的实现有误；正确 named class F1 已由 full-panel confusion matrix 复核。主 Macro-F1、worst-class F1 和冻结 summary 不受影响。

权威证据入口：

- [`../xrd_robustness/reports/EVIDENCE_INDEX.md`](../xrd_robustness/reports/EVIDENCE_INDEX.md)
- [`../xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`](../xrd_robustness/reports/v9_resnet_js_ten_run_summary.json)
- [`../xrd_robustness/reports/v9_resnet_js_simulated_test_summary.json`](../xrd_robustness/reports/v9_resnet_js_simulated_test_summary.json)
- [`../xrd_robustness/reports/v9_resnet_js_simulated_test_audit.json`](../xrd_robustness/reports/v9_resnet_js_simulated_test_audit.json)
- [`../xrd_robustness/reports/v9_resnet_js_simulated_test_class_metric_correction.json`](../xrd_robustness/reports/v9_resnet_js_simulated_test_class_metric_correction.json)
- [`../xrd_robustness/reports/v9_formal_split_identity_overlap_audit.json`](../xrd_robustness/reports/v9_formal_split_identity_overlap_audit.json)
- [`../xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json`](../xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json)

## 3. Current engineering state

Active reusable implementation:

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/scripts/train_v7.py`](../xrd_robustness/scripts/train_v7.py) — 文件名沿用旧版本，但仍是 V9-T 共享训练入口
- [`../xrd_robustness/src/xrd_robustness/evaluation/rruff301_replay.py`](../xrd_robustness/src/xrd_robustness/evaluation/rruff301_replay.py)

2026-08-23 仓库整理将一次性 runner、重复配置、重复报告和低价值脚本测试合并或删除。当前布局为：`scripts/` 10 个文件；`configs/` 顶层 10 个、`provenance/` 3 个；`reports/` 顶层 10 个、hash-bound `provenance/` 8 个、Git-safe ten-run archive 3 个；`tests/` 顶层 1 个，并按 `core 6 / simulation 9 / training 9 / evidence 5` 组织。每个作者维护目录均不超过 10 个直接文件。

历史科学结论写入 [`PROJECT_JOURNEY.md`](PROJECT_JOURNEY.md) 和证据索引，原始文件仍可从 Git baseline `f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217` 恢复。保留的 provenance 子目录不是旧报告堆积：其中的文件仍被冻结方法合同逐项路径/哈希校验。

本地忽略的数据集、checkpoint、生成谱图和 raw outputs 是复核资产，不属于本轮删除范围，也不得提交。

## 4. Hard execution lock

在没有新的科学问题、书面授权和全新空输出根目录前：

- 不启动新训练；
- 不重跑 frozen simulated Test；
- 不根据 Test 调参或改变方法选择；
- 不替换冻结 checkpoint；
- 不把历史 RRUFF-301 重新命名为 confirmatory run；
- 不执行 sealed future module。

## 5. Known limitations and current blocker

已知限制：

- exact-parent-disjoint 不等于 formula、chemical-family、prototype 或 symmetry-equivalence disjoint；
- simulated Test 是合成域 aggregate 证据，存在 class/condition heterogeneity；
- RRUFF-301 历史 provenance 不完整，只允许 retrospective claim；
- 当前结论只覆盖七晶系分类，不可外推为参数反演能力。

当前 blocker 是**论文与图表尚未完成并接受 claim-boundary 校核**。RRUFF provenance 只是需要在稿件中透明披露的限制，不是工程或实验 blocker。

## 6. Sealed future direction

[`future_modules/PXRD_ROBUST_LATTICE_PARAMETER_INVERSION.md`](future_modules/PXRD_ROBUST_LATTICE_PARAMETER_INVERSION.md) 登记了 known-template tetragonal `(a,c)` robust lattice-parameter inversion：以 nuisance robustness 和 physics-guided forward consistency 为核心，并设置 identifiability gate 与 conventional-fit baseline。

该模块状态为 **SEALED_FUTURE_MODULE**。它不是 V9-T 的追加目标，尚未获执行授权，也不能与当前七晶系分类 claim 混写。

## 7. Next actions

1. 依据冻结 Validation/Test/RRUFF-301 证据完成论文正文与图表。
2. 在方法与限制部分明确 exact-parent split、class heterogeneity 和 retrospective provenance 边界。
3. 仅在出现新的、可预注册的科学问题时评审新实验；否则保持冻结。

当前精确下一条命令：

```powershell
cd E:\AI4science\xrd_robustness
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q
```

历史研究判断与方向变化必须追加到 [`PROJECT_JOURNEY.md`](PROJECT_JOURNEY.md)，不得通过重写本文件删除历史。
