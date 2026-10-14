# AI4science 当前状态

> **权威性说明：** 本文件记录当前科学状态与当前执行口径。历史版本、旧聊天和 `PROJECT_HISTORY.md` 用于解释“为什么改变”，不得覆盖这里的当前结论；AI/Agent 工作规则见 [`../AGENTS.md`](../AGENTS.md) 与 [`RESEARCH_WORKFLOW.md`](RESEARCH_WORKFLOW.md)。

**状态日期：** 2026-10-14

**阶段：** 模拟主实验、RRUFF-301 few-shot、CNRS-318 zero-shot 与母结构预算补充实验均已完成；当前在做论文图表、方法 framing 与成果封装

## 1. 当前科学设计

当前已经完成的项目首先是一个**监督学习方法研究**：在线 PXRD 模拟器不仅能生成带晶系标签的谱图，还知道哪些谱图来自同一个母体结构。项目要回答的是：能不能把这种 parent provenance 转化为额外的 measurement-equivalence / relationship supervision，使相同晶体结构数据库提供比普通类别标签更多的监督信息，并由此提高七晶系分类、分布外泛化、真实域迁移和少标签适配表现。

最终确定的设计：

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
- 完成 CUIFA 台式机迁移后的母结构预算补充实验（40/40 模型、20/20 配对运行），并完成结果、运行时间与迁移环境归档；
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

两个实验真实域互补，主任务不同：

- **RRUFF-301**：平衡、人工整理的实验真实域（balanced curated experimental domain），主任务是 K=1/2/5 few-shot adaptation。composition audit 已完成并结案：adaptation/test 无相同 RRUFF ID、无相同 spectrum SHA、无 Pearson ≥ 0.95 的跨 split 近重复谱；共享 mineral identity 被保留，因为该 benchmark 不是 unseen-mineral task。
- **CNRS-318**：自然不平衡、跨数据库的独立实验真实域（naturally imbalanced independent experimental domain），已正式定级为第二实验域，主分析是 frozen-model zero-shot external evaluation，保留自然类别分布 `21 / 87 / 77 / 41 / 33 / 12 / 47`。

两个真实域均已有结果，但不合并成一个分数：

- CNRS-318 的权威审计与父样本 manifest 已进入 git（见 [`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) 和 [`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv)）；
- 评测已按冻结协议执行完毕；pre-run 协议文件保持原样，完成状态与纠错记录见结果报告和 run record（[`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md)）；
- 人工标签质量复核**不计划执行**：标签由 deposited structure 稳定重建、未做人工物相核验，这一限制将如实注明；
- 真实数据不参与模型、checkpoint、seed 或 `lambda_js` 选择；
- CNRS-318 的五个 seed 均 favor JS，平均配对 ΔMacro-F1 为 `+0.018713`；pooled Macro-F1、balanced accuracy、accuracy、ECE、NLL 与 Brier 共同改善。修正后的 class-stratified paired-parent 95% CI 为 `[−0.009339, +0.046107]`，说明自然类别不平衡和低支持类别带来较大的统计不确定性；该区间作为严格审计如实保留，但不单独否决上述多 seed、多指标一致的科学结果；
- CNRS 的绝对 sim-to-real 表现仍弱、校准仍差；overall accuracy `0.200→0.210` 低于多数类基线 `0.274`，不能包装成已解决的真实域分类。

## 6. 当前卡点

现在主要是把已有数字和方法思想转化为清楚、可复述的成果：

- **最高优先级：**把 `shared parent identity → measurement equivalence → relationship supervision` 做成论文/PPT 的统一方法叙事；
- 制作核心方法图，明确对照 `simulator = data generator` 与 `simulator = data generator + relationship supervisor`；
- 生成五种扰动图、同源双视图方法图和配对结果图；
- 完成仿照“组会1”视觉语言的阶段汇报；
- 完成方法、结果和讨论正文；
- 确保公开结果、图表和讲稿中的数字完全一致。

这里的 framing 工作**不是新实验，也不是算法扩张**。不要重新把项目包装成“JS consistency 用于 XRD”；应把 JS 放在 measurement-equivalence relationship supervision 的下游实现位置。

## 7. 当前项目下一步

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

## 8. 独立数值反演与下一阶段毕业研究候选（FUTURE）

当前完成并正在封装的科学主线仍是 **PXRD 七晶系分类中的 same-parent relationship supervision（JS-only）**。不为了新课题而修改其冻结协议、已完成结果或论文 framing。

**既有数值反演分支：** `xrd_inversion/` 已有正向模型与数值可恢复性基础设施（见 [README](../xrd_inversion/README.md) 和 [Week-1 报告](../xrd_inversion/reports/WEEK1_FORMAL_REPORT.md)）。早先以结构/测量参数解耦为核心的 Stage-1 方案，在预注册机制 Gate 中获 **NO-GO**，已于 2026-09-07 封存（见 [归档](archive/XRD_FACTORIZATION_STAGE1_ARCHIVED_20260907.md)）；数值基础设施的存在**不等于**该算法假设通过或获得重新开跑许可。

**2026-10-08 新增研究意向：** 如果硕士申请时本科毕业论文尚未正式开始，拟把毕业研究安排在 AI 辅助材料表征领域。候选课题为：从 PXRD 输入谱预测限定材料体系的结构/测量参数，再通过前向物理模型重构理论谱，以重构差异作为**可能的辅助训练约束**；比较常规参数监督与物理辅助方法，研究参数预测准确性、数据利用效率、训练成本及其在真实实验谱上的适用边界。

- 这是 **FUTURE / CANDIDATE**，不是正式毕业论文题目、已经启动的实验或既定成功的方法。
- “预测参数 → 重构理论谱”已有相关研究，不能直接当作原创算法；谱图相似不必然意味着真实参数正确。
- 初期优先限定单相、已知候选结构、有限连续参数（如四方晶格参数、零点偏移与峰宽），先核验参数可辨识性和正向模型；是否加入参数解耦、传统精修或其他模态，由独立验证结果决定。
- 本次计划**不复活**旧解耦 Stage-1 NO-GO，也不影响当前 JS-only 论文或 frozen tests。

正式规划与申请用文字见 **[FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md)**；未来如实际开题发生变化，须单独记录新决策与证据。

## 9. 2026-10-14 独立母结构数量效率实验（COMPLETED，post-main supplementary analysis）

从早期暂缓的 sample-efficiency 设想中恢复 **10% / 25% / 50% / 100% 的 Train 母结构预算曲线**。CUIFA 台式机迁移后，按冻结协议完成 40 个模型（4 档预算 × 5 seeds × ERM/JS）和 20 个配对运行；每个模型均完成 49,280 步。结果报告、逐 seed 指标、配对差值、图表和运行审计见 [`../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md`](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md) 与 [`../xrd_robustness/reports/parent_budget_efficiency/`](../xrd_robustness/reports/parent_budget_efficiency/)。

| Train 母结构预算 | Dynamic ERM Test Macro-F1 | Dynamic JS Test Macro-F1 | 配对差值 JS−ERM | 正向 seeds |
|---:|---:|---:|---:|---:|
| 984（10%） | 0.43156 ± 0.00438 | 0.48763 ± 0.00393 | +0.05607 | 5/5 |
| 2,460（25%） | 0.51925 ± 0.00357 | 0.57098 ± 0.00803 | +0.05173 | 5/5 |
| 4,921（50%） | 0.59349 ± 0.00413 | 0.63611 ± 0.00589 | +0.04261 | 5/5 |
| 9,842（100%） | 0.64589 ± 0.00648 | 0.69985 ± 0.00496 | +0.05396 | 5/5 |

`±` 为五 seed 的 sample SD。四档预算下 JS 的同预算性能均高于 ERM，但实测曲线不支持更低预算 JS 达到更高预算 ERM 的均值；因此**没有证据支持可量化的母结构节省**。该结论限于实测预算，不外推比例。模拟 Test 已被主研究使用，本结果明确属于 post-main supplementary analysis，不是首次打开的独立盲测。

- 本实验是现有 `shared parent identity → relationship supervision` 主张的**独立补充机制/效率验证**，不是新模型、不是 RRUFF few-shot 标签效率，也不替代冻结的主实验。
- 采用原 Train 9,842 母结构的晶系分层嵌套子集；ResNet-18-GN、`lambda_js=60` 不变；配对 seed 和模拟协议固定，训练曝光量/优化步数必须统一。
- 为避开公共 epoch runner 的 partial batch 和逐 epoch 验证行为，已使用独立固定步数配对入口与确定性嵌套母结构子集；公平性检查和 matched-view smoke 通过，协议与实现见本节链接的计划、配置及结果报告。
- 运行使用 RTX 4070 Ti SUPER 16 GB，自动选择 12 workers / 12 prefetch、BF16、TF32、fused AdamW、pin memory 与 non-blocking H2D；20 个完成配对运行累计 12.24 小时，端到端矩阵墙钟时间 12.86 小时。采样所得约 5.29 GPU busy-equivalent hours 是整卡遥测，可能包含其他进程，不能视为实验独占 GPU 时间。
- 正式矩阵前，源端一次预启动在首个验证检查点前发现评估 batch size 与 V9 协议不一致（128 对 256），未产生检查点或分数；冻结配置改为 256 后才运行矩阵。CUIFA 转移完整性预检曾拦截意外的 Python `__pycache__` 文件；重新通过完整性验证后才开始科研训练。这两项预检均不计入 40 个模型。
- 迁移时一组 10% 配对运行在 step 43,120 遇到 Windows dashboard 文件替换 PermissionError；修正监控原子替换后，该配对从 step 0 重跑并完成。失败尝试留在本地审计，不计入 40 个完成模型。
- CUIFA 基准为 24.93 paired optimizer steps/s，来源机器 RTX 4060 Laptop 基准为 11.79 steps/s，约 2.12×；两边 GPU 和 worker 设置不同，该比值不代表仅软件优化的因果效果。
- 状态 **COMPLETED**；完整冻结设计见 [PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md](PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md)，结果与审计见上述报告和归档文件。原主实验报告、划分、权重和历史结果未修改。
