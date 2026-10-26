# AI4science 当前状态

> **权威性说明：** 本文件记录当前科学状态与当前执行口径。历史版本、旧聊天和 `PROJECT_HISTORY.md` 用于解释“为什么改变”，不得覆盖这里的当前结论；AI/Agent 工作规则见 [`../AGENTS.md`](../AGENTS.md) 与 [`RESEARCH_WORKFLOW.md`](RESEARCH_WORKFLOW.md)。

**状态日期：** 2026-10-26

**阶段：** PXRD 七晶系分类研究的既有实验均已冻结；当前毕设工作是基于既有证据完成写作与答辩准备，不启动新实验。参数反演结果（含 PR #46）已封存为历史探索。

## 2026-10-26: current undergraduate-thesis scope (DECISION)

**唯一当前毕设主线：** PXRD 七晶系分类中的同母结构关系监督研究。研究问题是：利用在线模拟器已知的同一母结构身份，将不同测量视图之间的关系作为额外监督，能否在匹配设置下改善分类？核心对照是 ResNet-18-GN 上的 Dynamic JS Consistency 与 Dynamic ERM。

**当前阶段：** 对已完成并冻结的分类证据进行整理、报告和答辩准备；本次决策不包含新实验，也不包含扩容任务。

| Evidence | Current thesis role | Qualification |
| --- | --- | --- |
| Simulated OOD, five matched seeds | Core result; Dynamic JS Macro-F1 gain **+5.46 percentage points** over Dynamic ERM. | Frozen study and split; report as a bounded result, not universal superiority. |
| RRUFF-301 K=1/2/5 and CNRS-318 | Supporting completed evidence, separate from the core comparison. | RRUFF is few-shot, not zero-shot; CNRS absolute accuracy is low and the corrected paired-parent interval crosses zero. |
| Parent-budget study | Supplementary post-main result. | The simulated Test had already been used; no quantitative structure-saving claim is supported. |
| PR #46 parameter-inversion benchmark | **Archived / exploratory only; excluded from evidence for the classification method.** | See the archival disposition below. |

### PR #46: partial parameter-inversion benchmark archived on 2026-10-26

PR #46 completed primary synthetic scoring for 42 models and 8,085 per-parent records, but its overall status was **PARTIAL**. The q-accuracy gate passed **0/42**; the per-DOF cell-MAE constraint passed **41/42**; convergence was no worse in 42/42 and the amortized runtime gate passed 41/42. These are descriptive results from a bounded synthetic setup, not proof that parameter inversion is accurate, robust, or superior.

The held-out parent set had already been evaluated in PR #43, so this was not independent confirmation. New-architecture stress was **BLOCKED_NOT_RUN**; real RRUFF validation was **BLOCKED / NOT RUN**. It was not an exact reproduction of XQueryer, SimXRD-4M, CPICANN, or PyWPEM. The benchmark and all associated parameter-inversion, Forward Loss, DONUT-inspired, and automatic-refinement routes are now **ARCHIVED / INACTIVE**.

**Claim disposition:** withdraw any claim that PR #46 established method superiority, validated real-data inversion, or reproduced those literature methods. Downgrade the completed matrix, cell-MAE/convergence/runtime passes, and 8,085 rows to exploratory engineering evidence with the limitations above. Do not use them as the thesis's scientific result.

### Deferred work

The 2026-10-23 scale-up plan and Issue #49 (new RRUFF zero-shot evaluation, calibration, larger-parent training, simulator upgrade, training retuning, and architecture comparison) are **DEFERRED** as of this decision. They are not current thesis tasks or acceptance gates. No new data acquisition or experiment is being initiated.

Related: [frozen classification results](../xrd_robustness/reports/RESULTS.md), [current supervisor brief](START_HERE_FOR_SUPERVISORS.md), [historical PR #46](https://github.com/Frysland-2024/AI4science/pull/46), [project history](PROJECT_HISTORY.md), [deferred scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).

### 2026-10-23: CNRS downgraded to optional second real domain

**User decision:** CNRS is an **optional second real-domain showcase**; it is not required for any of the three headline metrics or the next-stage RRUFF competition. The primary measured-data result remains RRUFF.

**Presentation policy:** Do not allocate main benchmark leaderboard space or new training budget to CNRS by default. It may appear as a separate supplementary external-domain robustness/generalization case if its independently defined dataset quality, task relevance and full evaluation make that informative. **Do not select reports/models/checkpoints or decide whether to disclose completed experiments solely on whether the scores look good.** In any paper or report making broad cross-domain claims, cite the completed CNRS evaluation with its low absolute Accuracy/Macro-F1 and uncertainty, even if detailed plots are in supplementary materials. Existing fixed CNRS-318 results stay public and immutable (JS zero-shot pooled Accuracy 0.2000 → 0.2101; Macro-F1 0.1912 → 0.2091; ECE 0.6826 → 0.6124). Current results show a modest paired relative gain, not high absolute accuracy.

**Status:** historical presentation decision for the completed CNRS evidence, not a current experiment. Under the 2026-10-26 thesis scope, report the existing CNRS result only with its low absolute score and uncertainty; do not start a new CNRS or RRUFF evaluation.

### 2026-10-23 scale-up proposal: simulator and training retuning (DEFERRED 2026-10-26)

**Historical proposal:** At the time, the proposed prerequisites were a more complete reference-guided online dynamic PXRD simulator and re-selection of training settings after data/simulator changes. This proposal is retained for chronology only; it is not part of current thesis execution.

**Historical sequence:** audit sources and simulator coverage → versioned physics changes → physical/label checks → paired old/new pilot → expanded-parent pilot and validation-only tuning → matched ERM/JS scale-up → RRUFF, ECE and parent-budget evaluation. None of these steps is authorized by the current 2026-10-26 scope.

**Sources/status:** [deferred plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md), [existing perturbation evidence](PXRD_PERTURBATION_EVIDENCE.md), [Issue #49, deferred](https://github.com/Frysland-2024/AI4science/issues/49). **DEFERRED / NOT IMPLEMENTED.**

### Deferred technical options (not current thesis tasks)

以下均是 2026-10-23 的扩展提案，已于 2026-10-26 推迟；不是当前研究 TODO 或毕设验收门槛。若未来要恢复，需另行确定时间、问题和资源，不能从历史计划直接启动。

- 增加独立训练母结构，并审计各晶系覆盖、去重与拆分。
- 设计带版本的新在线动态 PXRD 模拟器。
- 在数据和模拟器改变后重新选择训练设置。
- 条件性比较其他分类架构。

详情见[历史扩容计划](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md)。当前没有实现、下载或训练这些提案。

## 1. 已完成的科学方法与冻结实验设计

当前已经完成的项目首先是一个**监督学习方法研究**：在线 PXRD 模拟器不仅能生成带晶系标签的谱图，还知道哪些谱图来自同一个母体结构。项目要回答的是：能不能把这种 parent provenance 转化为额外的 measurement-equivalence / relationship supervision，使相同晶体结构数据库提供比普通类别标签更多的监督信息，并由此提高七晶系分类、分布外泛化、真实域迁移和少标签适配表现。

冻结历史研究的实验设计：

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency，一致性权重 `lambda_js=60`；
- 预处理：不做额外处理；
- 优化器：AdamW；
- 学习率：恒定；
- 划分：训练 9,842 / 验证 2,109 / 测试 2,109；
- 划分方式：按母体结构严格分开，训练/验证/测试不共享同一母体。

当前方法贡献的统一表述是（一级 framing 见 [`PXRD_SUPERVISION_FRAMING.md`](PXRD_SUPERVISION_FRAMING.md)）：

> **shared parent identity → measurement equivalence → relationship supervision**

传统 online PXRD simulator 主要承担 `data generator` 的角色；本项目进一步利用 simulator-retained parent identity，使其同时成为 **data generator + relationship supervisor**。JS consistency 是这一 measurement-equivalence supervision 的具体实现，而不是项目声称发明的新算法。

### 当前标签口径

- **项目本体：** supervised learning / PXRD crystal-system classification；
- **方法核心：** structured / relational supervision from simulator provenance；
- **具体实现：** JS consistency regularization；
- **实验设置/结果：** simulated OOD generalization、CNRS zero-shot cross-domain evaluation、RRUFF few-shot adaptation / label efficiency、probability calibration；
- **大领域背景：** AI4Science / AI for Characterization。

`robust learning`、`representation learning`、`domain adaptation`、`computer vision`、`physics-informed ML` 均不再作为整个项目的一级标签；其中只有 RRUFF K-shot 子实验可准确称为 target-domain adaptation。

## 2. 已经做完的事

- 在验证集上跑完了五组配对实验；
- 在选好的模型上完成了模拟测试集评估；
- 固定了模型、数据、扰动、优化器和训练量；
- 把公开的结果和论文的说法统一了；
- 精简了公开文件，只留下训练、评估和核对结果需要的部分；
- 明确当前结果不再通过新增 loss、重新调参或重开训练改变；
- 完成 RRUFF-301 的 K=1/2/5 locked-test few-shot 评测并回溯核验结果；当前直接按 Macro-F1、Accuracy、mean ± SD、paired consistency 与 learning curve 报告；
- 完成 CNRS-318 的 10-checkpoint zero-shot 外部域评测、原始输入复建和结果完整性审计；
- 完成模拟 Test 与 CNRS 的概率可靠性审计；
- 完成跨平台换行规范化哈希校验与全量回归测试（`117 passed`）；
- 完成五类扰动物理/文献依据的当前主线汇总，确认该问题不是新的科研 TODO；
- 完成 RRUFF-301 adaptation/test 的只读 composition audit：301 个 RRUFF ID 全部唯一，ID overlap = 0，spectrum-SHA overlap = 0，16,170 个跨 split 谱图对中 maximum Pearson = `0.947785`，没有 Pearson ≥ 0.95 的近重复谱。

### 2.1 本轮三个问题的最终状态

权威结案文档：[`PXRD_EVIDENCE_CLOSURE.md`](PXRD_EVIDENCE_CLOSURE.md)。

| 问题 | 状态 | 当前处理 |
|---|---|---|
| 五类扰动的物理/文献依据 | **CLOSED** | 已有系统 evidence；后续只在 Methods / PPT / 答辩中调用，不重新调查 |
| RRUFF-301 composition / near-duplicate 检查 | **CLOSED** | 无相同 RRUFF ID、无相同谱、无 Pearson ≥ 0.95 的跨 split 近重复谱；不修改 frozen split |
| 新颖性 framing | **ACTIVE WRITING** | 当前最高优先级；打磨 `simulator = data generator + relationship supervisor`，不是补实验或加算法 |

除非未来 scientific claim 明显改变，否则前两个问题不再重新开启。

## 3. 结果与当前评价口径

主科学判断采用 PXRD / Materials ML 社区常用的 performance-reporting 范式，并按三层证据组织：Macro-F1、balanced accuracy、accuracy、mean ± std、多 seed 一致性、few-shot learning curve、label efficiency 和 per-class F1 是主 performance layer；ECE/NLL/Brier 等是 reliability 增强证据；paired/class-stratified parent bootstrap、95% CI 与不确定性分解是 strict statistical audit。单个 CI 跨 0 不再自动把整体一致的结果判成失败。当前权威规范见 [`PXRD_RESULT_REPORTING_STANDARD.md`](PXRD_RESULT_REPORTING_STANDARD.md)，方法论转变的历史缘由已归并进 [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md)。

这项修正只改变证据层级，不改变实验或原始结果：不得删除不利统计结果、隐藏跨零 CI、看结果后换指标、修改 frozen test 数据、重选 checkpoint/seed、反复重跑到满意，或改写历史 raw outputs。

| 指标 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | Δ `+0.046569`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | Δ `+0.054600`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | Δ `+0.054454`；5/5 为正 |
| RRUFF-301 · K=1 few-shot locked-test Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | Δ `+0.0433`；21/25 为正 |
| RRUFF-301 · K=1 few-shot locked-test Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | Δ `+0.0384`；20/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | Δ `+0.0460`；23/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | Δ `+0.0488`；23/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | Δ `+0.0545`；24/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | Δ `+0.0568`；23/25 为正 |
| CNRS-318 · zero-shot seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | mean paired Δ `+0.01871 ± 0.00675`；5/5 为正 |
| CNRS-318 · zero-shot pooled Macro-F1（描述性） | 0.19118 | 0.20912 | `+0.01794` |
| CNRS-318 · zero-shot Balanced Accuracy | 0.21823 | 0.23878 | `+0.02055` |
| CNRS-318 · zero-shot Accuracy | 0.20000 | 0.21006 | `+0.01006` |
| CNRS-318 · zero-shot ECE ↓ | 0.68257 | 0.61242 | `−0.07015`（更低为好） |

表中 `±` 均为对应重复运行的 sample standard deviation；完整 mean±SD、paired consistency 与结果说明见 [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)。

结果与证据文件：

- [`PXRD_EVIDENCE_CLOSURE.md`](PXRD_EVIDENCE_CLOSURE.md)
- [`PXRD_PERTURBATION_EVIDENCE.md`](PXRD_PERTURBATION_EVIDENCE.md)
- [`../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`](../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md)
- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/reports/validation_results.json`](../xrd_robustness/reports/validation_results.json)
- [`../xrd_robustness/reports/simulated_test_results.json`](../xrd_robustness/reports/simulated_test_results.json)
- [`../xrd_robustness/reports/rruff301_fewshot_results.json`](../xrd_robustness/reports/rruff301_fewshot_results.json)
- [`../xrd_robustness/reports/CNRS_318_RESULTS.md`](../xrd_robustness/reports/CNRS_318_RESULTS.md)
- [`../xrd_robustness/reports/CALIBRATION_ANALYSIS.md`](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md)

## 4. 当前实现

主要实现：

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/src/xrd_robustness/training/runner.py`](../xrd_robustness/src/xrd_robustness/training/runner.py)
- [`../xrd_robustness/scripts/audit_rruff301_composition.py`](../xrd_robustness/scripts/audit_rruff301_composition.py)

结果已经确定，不会再改。公开仓库里只留当前实现、运行配置、结果和使用文档；安装项目后通过 `xrd-train` 调用可复用训练入口，分数看已有模型的评估结果文件。

这里说的“结果已经确定”包括模拟部分和两个角色不同的实验域。CNRS 的结果是
**zero-shot 外部域压力测试**，不是使用 CNRS 标签做域适配；冻结配置保持原样，执行完成状态由
结果报告和 run record 另行记录。

## 5. 实验进度

方法对比、验证集和模拟测试集的评估都做完了，模拟部分的结果已经确定、不会再改。

既有真实域结果的当前定位：

- **RRUFF-301**：平衡、人工整理的实验域。已完成 K=1/2/5 few-shot 历史评测和 split composition audit；共享 mineral identity 被保留，因为该任务并非 unseen-mineral benchmark。下一阶段新增的主要外部评测将是明确协议的 RRUFF zero-shot 结果及可比基准。
- **CNRS-318**：自然不平衡的独立实验域（类别数 `21 / 87 / 77 / 41 / 33 / 12 / 47`），已完成 frozen-model zero-shot 评测。自 2026-10-23 起仅作为 **Optional Secondary Experimental Domain**，不是必须完成的核心评价轴。

既有两个真实域结果均保留，但不合并成一个分数：

- CNRS-318 的权威审计与父样本 manifest 已进入 git（见 [`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) 和 [`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv)）；
- 评测已按冻结协议执行完毕；pre-run 协议文件保持原样，完成状态与纠错记录见结果报告和 run record（[`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md)）；
- 人工标签质量复核**不计划执行**：标签由 deposited structure 稳定重建、未做人工物相核验，这一限制将如实注明；
- 真实数据不参与模型、checkpoint、seed 或 `lambda_js` 选择；
- CNRS-318 的五个 seed 均 favor JS，平均配对 ΔMacro-F1 为 `+0.018713`；pooled Macro-F1、balanced accuracy、accuracy、ECE、NLL 与 Brier 共同改善。修正后的 class-stratified paired-parent 95% CI 为 `[−0.009339, +0.046107]`，说明自然类别不平衡和低支持类别带来较大的统计不确定性；该区间作为严格审计如实保留，但不单独否决上述多 seed、多指标一致的科学结果；
- CNRS 的绝对 sim-to-real 表现仍弱、校准仍差；overall accuracy `0.200→0.210` 低于多数类基线 `0.274`，不能包装成已解决的真实域分类。

## 6. 历史汇报与论文封装待办（2026-10-20 快照；不定义当前科学任务）

以下清单记录 2026-10-20 的论文/展示整理计划，状态可能已变；它们不是新一轮科学实验优先级。当前毕设范围以本文件开头的 2026-10-26 决策为准，扩容计划已延期。

当这些文字或图表需要更新时，仍须以冻结结果为准：

- **最高优先级：**把 `shared parent identity → measurement equivalence → relationship supervision` 做成论文/PPT 的统一方法叙事；
- 制作核心方法图，明确对照 `simulator = data generator` 与 `simulator = data generator + relationship supervisor`；
- 生成五种扰动图、同源双视图方法图和配对结果图；
- 完成仿照“组会1”视觉语言的阶段汇报；
- 完成方法、结果和讨论正文；
- 确保公开结果、图表和讲稿中的数字完全一致。

这里的 framing 工作**不是新实验，也不是算法扩张**。不要重新把项目包装成“JS consistency 用于 XRD”；应把 JS 放在 measurement-equivalence relationship supervision 的下游实现位置。

## 7. 历史展示与论文整理提案（2026-10-20 快照；当前范围以 2026-10-26 决策为准）

1. 首先打磨并固定方法新颖性 framing：`simulator from data generator to relationship supervisor`。
2. 把该 framing 做成 PPT / manuscript 的核心方法图，视觉重点放在 `shared parent identity → measurement equivalence → supervision`，而不是把 JS 画成最大创新模块。
3. 从 `reports/validation_results.json`、`reports/simulated_test_results.json` 和真实域结果文件生成论文与 PPT 图表。
4. 完成 Introduction、Methods、Results 和 Discussion，使标题、摘要、方法图和公开项目叙事使用同一套 measurement-equivalence 语言。
5. 将技术报告、方法图和一页项目摘要整理为可公开复用的成果材料。
6. 把 RRUFF-301 few-shot 与 CNRS-318 zero-shot 分表写入正文并补齐结果图；不重开模型选择、不修改 frozen split、不事后删改真实域样本。

复现当前工程检查的命令：

```powershell
cd xrd_robustness
python -m pytest -q
```

## 8. Archived / Inactive：独立数值反演与旧毕业研究候选

**状态（2026-10-23）：本节所列参数反演、晶格参数预测、Forward Loss 与自动精修均为 Archived / Inactive。** 唯一主动科学任务是本文件前述 PXRD 七晶系分类。此处保留早期计划及其边界，不能作为执行清单或恢复研究路线的依据。

**既有数值反演分支：** `xrd_inversion/` 已有正向模型与数值可恢复性基础设施（见 [README](../xrd_inversion/README.md) 和 [Week-1 报告](../xrd_inversion/reports/WEEK1_FORMAL_REPORT.md)）。早先以结构/测量参数解耦为核心的 Stage-1 方案，在预注册机制 Gate 中获 **NO-GO**，已于 2026-09-07 封存（见 [归档](archive/XRD_FACTORIZATION_STAGE1_ARCHIVED_20260907.md)）；数值基础设施的存在**不等于**该算法假设通过或获得重新开跑许可。

**历史提案（2026-10-08；2026-10-23 已归档）：** 如果硕士申请时本科毕业论文尚未正式开始，拟把毕业研究安排在 AI 辅助材料表征领域。候选课题为：从 PXRD 输入谱预测限定材料体系的结构/测量参数，再通过前向物理模型重构理论谱，以重构差异作为**可能的辅助训练约束**；比较常规参数监督与物理辅助方法，研究参数预测准确性、数据利用效率、训练成本及其在真实实验谱上的适用边界。

- 这是当时的 **FUTURE / CANDIDATE** 提案；目前状态为 **ARCHIVED / INACTIVE**，不是正式毕业论文题目、已启动实验或既定成功方法。
- “预测参数 → 重构理论谱”已有相关研究，不能直接当作原创算法；谱图相似不必然意味着真实参数正确。
- 初期优先限定单相、已知候选结构、有限连续参数（如四方晶格参数、零点偏移与峰宽），先核验参数可辨识性和正向模型；是否加入参数解耦、传统精修或其他模态，由独立验证结果决定。
- 本次计划**不复活**旧解耦 Stage-1 NO-GO，也不影响当前 JS-only 论文或 frozen tests。

原提案见 [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md)，仅供历史追溯；若将来改变科学方向，必须先记录新的明确决策。

### 2026-10-18：铁电陶瓷预精修 12 周提案（ARCHIVED / INACTIVE；原提案未启动）

以下为 2026-10-18 的历史研究提案，2026-10-23 起已归档、不再属于当前下一阶段：在当时的连续参数＋可微重构 Loss 候选思路基础上，曾考虑一个面向真实应用的方案：**一个待定铁电陶瓷家族、模拟谱主训练、Top-K 单相结构候选及经模拟域检验的概率校准、逐候选参数初值与不确定性、物理正向核验、精修前指导**。学长少量真实谱主要用于外部案例，不作为主训练集。重构 Loss 降为可选消融，不作为项目启动的必需步骤。

**两相共存不被排除**：12 周主任务暂以候选单相为核心，但必须用物理合理的合成混相作单相假设失配压力测试，允许 `REVIEW_REQUIRED` 拒判；进一步两相模型提示仅为可选，质量分数定量另立后续课题。**单相 Softmax 的 70% R / 30% C 是互斥候选解释概率，不是两相含量。** ECE 是模拟域可靠性评估，不保证真实域概率准确。

本规划**不是已实施工作、已批准开题或对旧 xrd_inversion/JS 主线的改写**。详情与每双周里程碑见 [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)。旧 [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md) 原文保留作为 10 月 8 日历史提案。

### 2026-10-18：PXRD AutoLab 工程支持提案（科学首个用例已归档）

[PXRD AutoLab 工程方案](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md) 保留为工程自动化设计记录。其历史首个参数反演/Forward Loss 用例已归档；AutoLab 工程代码本身不是第二个科学研究任务，也不授予训练权限。

该方案当时规划了人工审阅协议下的 Gate、A/B、报告与人工审核；**它不是当前主动科学路线，也没有代表自动实验或新结果**。任何工程维护仍须服从 2026-10-23 唯一科研任务及本仓库的安全规则。

## 9. 2026-10-13 独立母结构效率实验提案（历史快照；已于 10-14 完成）

本段保留 2026-10-13 提案原貌，后来由下方 2026-10-14 完成记录取代。实验比较 **10% / 25% / 50% / 100% 的 Train 母结构预算曲线**，检验相同独立结构数、双视图曝光和优化预算下 Dynamic JS 与 Dynamic ERM。

- 本实验是现有 `shared parent identity → relationship supervision` 主张的**独立补充机制/效率验证**，不是新模型、不是 RRUFF few-shot 标签效率，也不替代冻结的主实验。
- 采用原 Train 9,842 母结构的晶系分层嵌套子集；ResNet-18-GN、`lambda_js=60` 不变；配对 seed 和模拟协议固定，训练曝光量/优化步数必须统一。
- 已识别工程风险：目前公共 `runner.py` 的 epoch 末尾可能有不完整 batch，而且每 epoch 进行验证与保存，不适合直接充当完全公平的预算比较入口。CODEX LUNA 应先完成独立固定步数入口、数据审计、单元测试与 smoke，才能执行大规模 run。
- 当前模拟 Test 已在正式论文中使用过；本次应标明为 **post-main supplementary follow-up**，不能声称是全新未打开的 confirmatory Test。
- 提案当时的状态为 **PROPOSED / READY FOR CODEX IMPLEMENTATION / NOT_RUN**；该状态随后被下方完成记录取代。原主实验的报告、划分、权重和历史结果均未修改。


## 10. 2026-10-14 已完成的母结构预算补充实验（post-main）

The formerly proposed parent-budget experiment is complete: 4 budgets (984/2460/4921/9842) × 5 seeds × 2 methods = 40 scored models, 20 pairs. At each budget Dynamic JS outperformed matched Dynamic ERM on the simulated Test by +0.05607 / +0.05173 / +0.04261 / +0.05396 Macro-F1 respectively, with 5/5 paired seeds positive at every budget. The already-used Test makes this explicitly post-main supplementary evidence. No measured budget crossing supports a quantitative crystal-structure saving claim. Full frozen protocol, raw aggregates, audit limitations and figures: [PARENT_BUDGET_EFFICIENCY.md](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).

Research-role clarification (reported by project lead): Across the project, **Frysland-2024 has been the principal designer and planner of the scientific approach**, responsible for overall research direction, experimental design and changes in project strategy. This includes the main same-parent JS study, simulated OOD validation, the RRUFF and CNRS real-domain experiments, and the parent-budget/Data Efficiency design. **Cuifa01 participated primarily in executing these plans**, giving auxiliary ideas and feedback, helping collect/organize data, and contributing software implementation, GPU experiments, desktop transfer and other operational work. Supporting ideas and execution should not be presented as joint overall project design or leadership. This clarifies roles without changing original Git authorship, executed data, or independently determining formal manuscript authorship.
