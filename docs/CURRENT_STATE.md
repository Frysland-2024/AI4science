# AI4science 当前状态

> **权威性说明：** 本文件记录当前科学状态与当前执行口径。历史版本、旧聊天和 `PROJECT_HISTORY.md` 用于解释“为什么改变”，不得覆盖这里的当前结论；AI/Agent 工作规则见 [`../AGENTS.md`](../AGENTS.md) 与 [`RESEARCH_WORKFLOW.md`](RESEARCH_WORKFLOW.md)。

**状态日期：** 2026-10-18

**阶段：** PXRD 分类主线的模拟、RRUFF-301 few-shot 与 CNRS-318 zero-shot 均已完成，当前做论文封装；独立预精修候选已完成一个有限的 Forward Reconstruction Loss 工程 pilot，材料家族专属研究仍待确认。

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

### 2026-10-18：Forward Reconstruction Loss 独立 pilot（PRELIMINARY）

用户授权开展的小范围 A/B 工程试验已在独立 `xrd_forward_loss/` 模块完成。使用原训练折中的单个四方 HfCd 结构，预测 `du,dv` 两个归一化晶格坐标；参数样本按 358/77/77 分为训练/验证/测试，验证集选择 `lambda=1.0`，三组匹配 seed。物理梯度和有限差分 Gate 通过。A 的平均两参数 MAE 为 `0.01495 ± 0.00327`，B 为 `0.01509 ± 0.00120`；B 的干净变换谱 RMSE 从 `0.009008 ± 0.001868` 降为 `0.008497 ± 0.000602`，但平均参数 MAE 略差。

该结果只验证一个已知结构下的模拟参数反演工程链路。它不是铁电陶瓷、实验域、未见结构、精修初值效用或泛化证据。首次训练因回归头饱和退化，失败输出已保留。结果与限制见 [pilot report](../xrd_forward_loss/FORWARD_LOSS_PILOT_REPORT.md)，文献对照和下一步见 [12 周计划](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)。

主分类研究、V9 JS 结果、冻结 split 和 Stage-1 解耦 NO-GO 均未修改；新 pilot 不能用来改写其结论。

### 2026-10-18：铁电陶瓷预精修辅助的新版 12 周候选规划（PROPOSED / NOT_STARTED）

在 2026-10-08 连续参数＋可微重构 Loss 候选思路基础上，进一步收敛了面向真实应用的下一阶段方案：**一个待定铁电陶瓷家族、模拟谱主训练、Top-K 单相结构候选及经模拟域检验的概率校准、逐候选参数初值与不确定性、物理正向核验、精修前指导**。学长少量真实谱主要用于外部案例，不作为主训练集。重构 Loss 降为可选消融，不作为项目启动的必需步骤。

**两相共存不被排除**：12 周主任务暂以候选单相为核心，但必须用物理合理的合成混相作单相假设失配压力测试，允许 `REVIEW_REQUIRED` 拒判；进一步两相模型提示仅为可选，质量分数定量另立后续课题。**单相 Softmax 的 70% R / 30% C 是互斥候选解释概率，不是两相含量。** ECE 是模拟域可靠性评估，不保证真实域概率准确。

本规划**不是已实施工作、已批准开题或对旧 xrd_inversion/JS 主线的改写**。详情与每双周里程碑见 [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)。旧 [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md) 原文保留作为 10 月 8 日历史提案。

### 2026-10-18：PXRD AutoLab 自动化执行方案（PROPOSED / NOT IMPLEMENTED）

为支持 10 月 18 日前置科研冲刺及双周真实汇报策略，新增 [**PXRD AutoLab：自动科研执行与可审计证据流水线**](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md) 作为**科研工程规划**，不改变已冻结 V9 或新的 Forward Loss 科学任务的证据状态。

自动化范围是已人工审阅协议下的模拟数据、物理/梯度/拆分 Gate、受控 A/B、指标图表、不可变实验 manifest、报告草稿与人工最终审核。**当前只有规划，没有新代码、后台执行器或自动科研结果。** P0 先从配置和 provenance 机制、CPU smoke、失败停止及报告器着手；需真实接入工作站后才能谈无人值守 GPU。不得自动改协议、测试集或无限寻找正结果。

## 9. 2026-10-13 独立母结构数量效率实验（PROPOSED，尚未运行）

从早期暂缓的 sample-efficiency 设想中恢复 **10% / 25% / 50% / 100% 的 Train 母结构预算曲线**，检验在相同独立结构数、相同双视图曝光和优化预算下，利用同源关系的 Dynamic JS 是否比 Dynamic ERM 更充分使用晶体结构数据。

- 本实验是现有 `shared parent identity → relationship supervision` 主张的**独立补充机制/效率验证**，不是新模型、不是 RRUFF few-shot 标签效率，也不替代冻结的主实验。
- 采用原 Train 9,842 母结构的晶系分层嵌套子集；ResNet-18-GN、`lambda_js=60` 不变；配对 seed 和模拟协议固定，训练曝光量/优化步数必须统一。
- 已识别工程风险：目前公共 `runner.py` 的 epoch 末尾可能有不完整 batch，而且每 epoch 进行验证与保存，不适合直接充当完全公平的预算比较入口。CODEX LUNA 应先完成独立固定步数入口、数据审计、单元测试与 smoke，才能执行大规模 run。
- 当前模拟 Test 已在正式论文中使用过；本次应标明为 **post-main supplementary follow-up**，不能声称是全新未打开的 confirmatory Test。
- 状态 **PROPOSED / READY FOR CODEX IMPLEMENTATION / NOT_RUN**；完整任务与结果交付标准见 [PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md](PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md)。原主实验的报告、划分、权重和历史结果均不得修改。

## 10. V9 扰动复用于 Forward Loss 的新工程 Pilot（PRELIMINARY）

在 PR #11 head 上独立开发了 V9 测量扰动适配器与一项新的 HfCd 工程 Pilot；没有改写 PR #11 的原始 noisy-input Forward Loss 结果。新 B 明确使用模拟器生成的 clean reference，属于 **simulator-supervised clean-reference forward loss**，不能称作真实实验谱上的无监督重建。

- 128 个同一训练折四方 HfCd 母结构的参数样本，按 90/19/19 划分；A/B 共用样本、网络、配对 seeds 和优化预算，比较简单 Poisson+线性背景输入及 V9 扰动输入。
- V9 Poisson–Gaussian 噪声、平滑背景、面积稳定峰展宽、全谱 2θ 零点偏移均已接入并通过算子检查。March–Dollase 保持关闭。零点和峰宽只扰动输入，不改晶格参数标签。
- V9 与 Torch clean renderer 的 max-abs 差 `1.04e-7`； Forward Loss 梯度有限差分检查通过，晶格 Jacobian 条件数 `3.36`。
- 三 seed 结果是混合证据：simple 输入下 B 平均 normalized-q MAE `0.05208`，A `0.05913`；V9 输入下 B `0.06842`，A `0.07293`。但 V9 下 B 的 clean-spectrum RMSE 略高（`0.04365` vs `0.04299`），晶格 `a` MAE 也略高，不能据此宣称全面改善。
- 所有结果来自单一已知 HfCd 结构的模拟参数泛化；没有 CIF 文件，结构来自冻结的本地 standardized-structure JSON。未验证铁电陶瓷、实验谱、未见结构或精修初值效用。

配置、逐样本扰动和 seed、原始谱阵列、Gate、A/B JSON、重算校验、图表和报告见 [`xrd_forward_loss/reports/v9_perturbation_phase2_pilot_20261018/`](../xrd_forward_loss/reports/v9_perturbation_phase2_pilot_20261018/)；接口说明见 [`V9_PERTURBATION_ADAPTER.md`](../xrd_forward_loss/V9_PERTURBATION_ADAPTER.md)。该工作保存在由 PR #11 head 分出的独立 stacked PR；PR 仍需人工审核，未自动合并。

## 11. Issue #19：测量一致的 Forward 闭环（PRELIMINARY ENGINEERING PILOT COMPLETE）

用户指出旧 reconstruction 目标与扰动 observed profile 不一致后，独立工作分支完成公开 BaTiO₃ CIF 上的 P0–P2 物理/梯度/未知 nuisance Gate，并在通过后按授权完成 P3 A/B。Torch/V9 全谱 parity、有限差分梯度、q+eta 局部可辨识、non-oracle profile recovery、噪声期望和 23 项测试均通过。P1 v1 的自由背景形状失败已保留；v2 按冻结的 V9 variation=0 固定形状，不降低 Gate 阈值。

512 个同一 CIF 的参数样本、3 paired seeds 和两类合成测量条件下，simple q MAE 为 A `0.013533`、B `0.013676`；V9 为 A `0.032235`、B `0.030554`。B 只在 V9 的两维 q MAE 略低，simple 略高；V9 nuisance head 对 zero-shift 的误差较大。结论是闭环工程可行、效果尚未确立；不得概括为更好的参数反演方法，也不构成真实谱或未见结构证据。

本次累计 smoke、失败尝试保守计时、正式训练和 λ 选择 `1386.05/7200 s`，在 RTX 4060 完成。失败运行、命令 exit codes、逐 seed 指标、数据/配置 SHA、原始 checkpoint SHA 台账和训练记录均已留档。本地清理重复模型副本与 optimizer 状态后，保留 12 个最终 FP32 最佳权重推理快照（约 596 MiB），释放约 8.34 GiB；精简快照不能续训。详情见 [Issue #19 报告](MEASUREMENT_AWARE_FORWARD_CLOSURE_REPORT_20261018.md) 和 [技术报告](../xrd_forward_loss/measurement_closure/TECHNICAL_REPORT.md)。本次不改 frozen JS 分类、旧 PR 结果、Stage-1 factorization NO-GO 或 12 周研究规划；新增工作以独立 Draft PR 交审。

## 12. Issue #31 / PR #26 公平诊断与新 A/B/C 试验（2026-10-19）

12 个 PR #26 精简推理 checkpoint 已重新核验 SHA、架构加载、GPU 推理与 q-MAE 重算。A/B 在已打开的旧 test 子集上使用同一 nuisance 中性初值、物理边界、目标函数、优化器与预算进行事后公平诊断。仅用 validation 的梯度分析发现 V9 q/reconstruction 梯度存在冲突，且 q 误差与 zero-shift 误差高度相关；新实验前仅预注册了一项改动：仅在 reconstruction 分支 detach q。

新的合成 512-q、三 seed、simple/V9 A/B/C 训练在预算内完成。simple 条件的三 seed 中 C 的 direct q-MAE 均低于 A；V9 条件 C 结果按 seed 混合，B 与 C 的均值均低于 A，而 C 均值略高于 B。等预算 joint q+eta fitting 后三种训练方法的 q 误差与谱残差几乎一致。结果仅属于一个公开 BaTiO₃ CIF 的合成条件插值，不构成真实 XRD、未见成分泛化或 Rietveld 证据。完整记录见 [`overnight_pr26_20261019/`](../overnight_pr26_20261019/)。

实验与证据已完成；分支 `codex/issue31-pr26-fair-diagnostic` 已推送，提交为 `23f344b`。GitHub Issue #31 状态评论和 Draft PR 创建因 GitHub CLI 凭证无效（HTTP 401）未完成；未尝试合并。冻结 PR #26 与 V9 证据未修改。


## 13. 2026-10-19 DONUT-PXRD bounded follow-up (EXPLORATORY COMPLETE)

The preregistered four-stage DONUT-PXRD follow-up completed on one public BaTiO3 P4mm CIF. It adapts DONUT's dual-branch unsupervised training mechanism to 1D PXRD; it is not the project's new primary method or a reproduction of the original 2D SXDM figures. The frozen forward parity, gradient, local-identifiability, source-fidelity and resume checkpoint audits passed.

Across the three stages, DONUT parameter recovery remained weak (exp3c normalized q mean MAE `0.2894` over 77 held-out parent identities per seed). In the fair exp4 comparison on those same 77 noisy exp3c observations, A/B/C direct q MAE averaged `0.0345/0.0348/0.0367` across seeds, while DONUT D averaged `0.2894`; bounded optimizer E achieved best-of-three q MAE `0.000359` on this synthetic condition, with 71/77 solver-success flags. A/B/C and optimizer refinements remain single-material results, not real-spectrum or unseen-material evidence.

The complete reports and raw arrays are under [`donut_pxrd/reports/`](../donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md) and [`donut_pxrd/results/study_v1/`](../donut_pxrd/results/study_v1/). The experiment does not change the supervised PXRD classification framing, frozen V9 results, PR #26 evidence, or the earlier Stage-1 factorization NO-GO. Delivery is through a stacked draft PR targeting `codex/issue31-pr26-fair-diagnostic`; no merge is authorized or attempted.

## 14. 2026-10-19 Independent phase-router bachelor prototype (ENGINEERING MVP)

This is a separate applied-characterization prototype, not a change to the primary supervised crystal-system classification project or to the DONUT follow-up. The application evaluates three source-attributed fixed CIF hypotheses (BaTiO3 P4mm, MgO rocksalt, CeO2 fluorite), refines candidate lattice parameters and bounded profile nuisance terms, and returns fit alternatives. At first implementation no compatible checkpoint or PyTorch was present in this worktree, so the adapter reported it unavailable. The follow-up below records the separately verified read-only checkpoint found in the source repository.

The current implementation passes a deterministic synthetic self-consistency suite for all three CIFs. It does not establish real-spectrum accuracy, universal phase or composition identification, confidence calibration, or Rietveld equivalence. Its renderer uses the zero-angle neutral-atom form-factor approximation and a Gaussian peak profile. See [`../reports/DEMO_VALIDATION.md`](../reports/DEMO_VALIDATION.md), [`../reports/MVP_IMPLEMENTATION_STATUS.json`](../reports/MVP_IMPLEMENTATION_STATUS.json), and the decision record in [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md). This engineering work does not alter frozen classifier artifacts, scientific splits/configurations, or DONUT evidence.

### 2026-10-19 RRUFF local adapter follow-up (PARTIAL ENGINEERING DEMO)

The branch now includes an opt-in read-only adapter for RRUFF-371 adaptation-pool samples R050045 Fluorite (CaF2) and R060745 Rutile (TiO2). It checks split membership and manifest spectrum hashes, uses recorded wavelength #1 for the measured profile (1.541838 Å, matching the frozen simulator's CuKa), and keeps wavelength #2 (1.540562 Å) as the separate refinement reference wavelength. Same-sample refined cells are excluded from routing. The bundled library has no CaF2 or rutile candidate, so both runs are explicitly `real_demo_requires_better_forward`; real-spectrum phase validation remains NOT DONE. Updated fits rank MgO first for both samples, but observed/model overlays show mismatch and one fit hits its evaluation cap. No CaF2/rutile CIF was fabricated after independent COD download attempts failed in the restricted host.

The frozen ResNet18-GN Dynamic-JS checkpoint was found in the main repository read-only, verified by SHA and strict config/state loading, and inferred on both adaptation examples. It predicted triclinic as the highest class for both (manifest labels cubic/tetragonal), so its optional prior is off by default and remains weak. Audit, limitations and test status are in [`../reports/RRUFF_REAL_DEMO_AUDIT.md`](../reports/RRUFF_REAL_DEMO_AUDIT.md) and [`../reports/MVP_IMPLEMENTATION_STATUS.json`](../reports/MVP_IMPLEMENTATION_STATUS.json). Local overlays are ignored and stay out of Git; no frozen split, source data, or other worktree was changed.

### 2026-10-19 Garnet AutoLab staged feasibility follow-up (LIMITED_GO; no training)

An independent reparse reviewed the 44 shortlisted RRUFF Garnet IDs: 44 raw powder profiles and complete same-ID refined cells were found, with 43 descriptions lacking an explicit mixture/contamination caveat. Five IDs overlap prior/frozen benchmark roles, leaving 39 IDs outside those roles. Twelve new Grossular IDs were predeclared for development. No same-specimen AMCSD CIF match was established; selected ideal/reference CIFs omit at least one measured substitution element for 38/44 records. RRUFF refined cells remain posthoc reference estimates, and `XY_RAW` does not provide verified wavelength metadata.

Building on the PR #37 phase-router MVP, a separately hash-pinned COD Grossular CIF and a single-free-parameter cubic-a fit were added. The synthetic recovery gate passed, and all 12 new development profiles met the predeclared peak-position and RMSE-improvement gate. A five-start L-BFGS-B baseline improved profile RMSE on 12/12 profiles and the absolute error against the posthoc RRUFF cell estimate on 6/12. Mean fitted-vs-reference absolute difference was 0.01985 Å. This supports a limited physics-fit pilot, not a validated real-domain adaptation claim. A small ResNet/K-shot protocol is proposed, but no training was run because the 12 profiles are development data and cannot also serve as independent adaptation/validation/test samples.

The staged artifacts are in [`../reports/GARNET_PXRD_AUTOLAB_STAGE_REPORT.md`](../reports/GARNET_PXRD_AUTOLAB_STAGE_REPORT.md), [`../reports/garnet_rruff_44/`](../reports/garnet_rruff_44/), and `pxrd_router_mvp/projects/grossular/`. They are being delivered on a new Draft PR based on PR #37; no merge was performed. A separate related Draft PR #40 remains independent and reports a stricter multiparameter stability failure; its measurements are not combined with this one-a study. This branch did not edit PR #37, the primary supervised crystal-system classification results, frozen data/splits/checkpoints, or the separate pilot worktree. At final inspection, that pilot worktree was clean at commit `2397b9f`.
