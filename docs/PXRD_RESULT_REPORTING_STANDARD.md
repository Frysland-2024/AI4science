# PXRD 项目结果评价与汇报规范

**状态：** 当前有效，适用于 Frysland-2024/AI4science 的 PXRD 鲁棒分类项目
**生效日期：** 2026-08-28

## 1. 总原则

项目的主科学判断回答：

> 模拟 OOD、RRUFF few-shot、CNRS 第二真实域、概率可靠性、多 seed 与逐类行为，是否共同支持 JS 比匹配的 Dynamic ERM 更稳健？

评价采用与 PXRD / crystallographic machine-learning 文献相符的三层结构。严格统计分析全部保留，但任何单个 bootstrap 区间都不得脱离完整证据链，独自充当科研成败 Gate。

## 2. Layer A — community-standard performance（主结果层）

主结果优先使用：

- Macro-F1 / F1；
- Accuracy；
- 天然类别不平衡时的 Balanced Accuracy；
- mean ± sample standard deviation；
- matched-seed 方向一致性；
- percentage-point improvement；
- few-shot learning curve 与 label efficiency；
- per-class precision / recall / F1、support 和 confusion matrix；
- 仅在候选检索或大类别任务需要时使用 Top-k Accuracy。

主问题是多个相互独立的 performance 证据是否一致，而不是让单个统计区间独自决定整项研究的成败。

### Simulated OOD

- Primary：mean single-factor OOD Macro-F1；
- 同时报告 Accuracy、五个 matched training seeds 的 mean ± SD、5/5 方向和百分点提升；
- 当前 headline：`0.65074 → 0.70534`，mean paired Δ `+0.05460`（`+5.46 pp`），5/5 seeds favor JS。

### RRUFF-301

- 角色：平衡、人工整理真实域上的 few-shot adaptation / label efficiency；
- K=1/2/5 分别报告 Macro-F1、Accuracy、mean ± SD、JS−ERM 百分点差和 paired consistency；
- 主图：K-shot learning curve；
- zero-shot 只作诊断起点或补充结果，不支配真实域叙事；
- 因数据已平衡，Balanced Accuracy 不必成为 headline。

### CNRS-318

- 角色：天然不平衡的第二独立真实域，冻结模型 zero-shot external evaluation；
- 类别 support：`21 / 87 / 77 / 41 / 33 / 12 / 47`；
- 主表至少报告 Macro-F1、Balanced Accuracy、Accuracy；同时提供 per-class F1 与 support；
- 当前 performance picture：Macro-F1 在 5/5 seeds 中 favor JS；seed-level mean ± SD 为 `0.188372±0.026336→0.207085±0.021336`，mean paired ΔMacro-F1 `+0.018713±0.006754`（约 `+1.87 pp`）；pooled Macro-F1 `0.191176→0.209119`、Balanced Accuracy `0.218225→0.238777`、Accuracy `0.200000→0.210063`。

## 3. Layer B — reliability（第二层增强证据）

使用：

- ECE；
- NLL；
- Brier score；
- predictive entropy；
- confidence behavior；
- 必要时的 uncertainty / rejection analysis。

这些指标回答性能改善是否伴随更合理的概率行为。它们很有价值，但目前不是 PXRD 分类社区最常见的 headline metrics，不能替代 F1/Accuracy 成为主成绩。

CNRS 可表述为：performance improvement is accompanied by improved calibration。当前 pooled ECE `0.682570→0.612420`、NLL `8.319988→6.118566`、Brier `1.433841→1.315606`；绝对 ECE 仍高，说明改善并未消除 sim-to-real reliability gap。

## 4. Layer C — strict statistical audit（第三层可信度审计）

永久保留：

- parent-level paired bootstrap；
- class-stratified paired bootstrap；
- 95% confidence interval；
- seed-wise paired analysis；
- per-class uncertainty；
- uncertainty decomposition。

这些分析回答：效应有多确定、不确定性来自哪里、哪些类别样本不足、哪些结果最稳定。

`CI crosses zero` 的正确含义是：在特定 resampling model 下，效应估计仍有较大不确定性。它不自动等于 `experiment failed`、`result invalid`、`no replication` 或 `cannot be positively reported`。

CNRS 修正后的 class-stratified paired-parent 95% CI `[−0.009339, +0.046107]` 必须如实保留在详细结果、appendix 或 limitation 中；它不能覆盖 5/5 seed、多个 performance metric 与 reliability metric 的共同方向。

工程上的哈希、manifest、run record 和文件追踪可以继续保留，用于复现和核对，但不属于科研贡献，也不构成判断结果是否成立的额外门槛。

## 5. 避免数学冗余

- 标准 single-label multiclass 任务中，micro-F1 等于 Accuracy；两者无需同时作为 headline。
- 标准 multiclass Balanced Accuracy 等于 mean per-class recall；主表已有 Balanced Accuracy 时，macro recall 可放补充材料。
- 平衡/模拟域的简洁主表：Macro-F1、Accuracy、mean ± SD。
- 天然不平衡真实域的简洁主表：Macro-F1、Balanced Accuracy、Accuracy、per-class F1/support。
- Top-k 只用于候选检索或大类别任务，不因“指标更多”而添加。

## 6. 推荐叙事

项目整体结论：

> Simulated OOD 的明确稳定提升、RRUFF few-shot 的 label-efficiency learning curve、CNRS 的 5/5 seed 与多性能指标改善，以及同方向的概率可靠性证据，共同支持 JS 利用同母结构不同测量视图的关系，学到了比匹配 Dynamic ERM 更稳健的模型。

CNRS 推荐写法：

> On the naturally imbalanced CNRS experimental domain, JS improves Macro-F1, balanced accuracy and overall accuracy, with positive Macro-F1 changes across all five matched training seeds. The performance gain is accompanied by improved calibration. The effect estimate carries larger uncertainty because several crystal systems have limited experimental support; the strict parent-level bootstrap interval overlaps zero.

禁止把最后一句调到 headline，也禁止把 `directional support` / `stable replication` 的历史内部分类当成当前对外标题。

## 7. 严谨性底线

评价层级改变不授权任何结果修改：

- 不得删除或隐藏不利统计结果与跨零 CI；
- 不得看完结果后更换指标制造显著性；
- 不得修改 frozen test 数据或事后删除 CNRS 样本；
- 不得重选 checkpoint、seed 或 `lambda_js`；
- 不得反复重跑到结果满意为止；
- 不得改写历史 raw outputs 或冻结协议。

## 8. 文档优先级

当前输出首先遵循本规范、[`CURRENT_STATE.md`](CURRENT_STATE.md) 与 [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)。冻结协议、run record、详细审计报告和日期化历史节点继续保存原貌，用于核对研究过程与不确定性；其中旧的单一 CI 门槛或内部结果分类只代表历史内部审计阶段，不得未经判断复制到当前 PPT、论文 headline、README、申请材料或项目总结。

日期化的 reporting-reset 历史说明曾采用“两层”粗分：当时的主结果层对应本规范的 Layer A performance + Layer B reliability，当时的严格审计层对应本规范的 Layer C。两者在证据优先级上没有实质冲突；2026-08-28 起以本文件的三层命名为当前权威表述。

本规范来自对 2019–2026 年代表性 PXRD / XRD ML 工作所采用指标的整理，包括 Oviedo et al.、Suzuki et al.、CrystalMELA、Lee et al.、Schopmans et al.、SimXRD-4M、XQueryer 与 RealPXRD-Solver。正式论文的 Related Work 与指标选择说明仍应引用对应原始文献。
