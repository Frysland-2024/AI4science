# PXRD 项目结果评价与汇报规范

**状态：** 当前有效，适用于 `Frysland-2024/AI4science` 的 PXRD 鲁棒分类项目  
**首次生效：** 2026-08-28  
**汇报边界修订：** 2026-09-13

## 1. 总原则

项目的主科学判断回答：

> 模拟 OOD、RRUFF few-shot、CNRS 第二真实域、多 seed、逐类行为和必要的可靠性证据，是否共同支持 JS 比匹配的 Dynamic ERM 更稳健？

本项目从 2026-09-13 起正式采用：

```text
Tier A — XRD community-standard performance：必须汇报
Tier B — supporting scientific evidence：按需要汇报
Tier C — strict statistical audit：本地保存，不做常规汇报
Tier D — engineering / reproducibility：本地保存，不做结果汇报
```

> **常规科研汇报只使用 Tier A + Tier B。**  
> **Tier C + Tier D 留在本地 JSON / CSV / audit / config / log / code 中，用于审计、复现和排障。**

这里的“常规汇报”包括：导师汇报、PPT 结果页、论文 Results 主文、项目总结、申请材料和对外 README headline。

Tier C / D 只有在审稿人、导师或内部核查**明确询问统计审计、复现或工程执行问题**时才调出。

---

## 2. Tier A — community-standard performance（主结果层）

主结果优先使用：

- Macro-F1 / F1；
- Accuracy / top-1 Accuracy；
- 天然类别不平衡时的 Balanced Accuracy；
- percentage-point improvement；
- few-shot learning curve 与 label efficiency；
- per-class precision / recall / F1、support 和 confusion matrix；
- profile-wise XRD perturbation performance；
- 仅在候选检索或大类别任务需要时使用 Top-k Accuracy。

这一级回答的是：

> **模型到底是不是更会分析 XRD。**

### Simulated OOD

- Primary：mean single-factor OOD Macro-F1；
- 同时报告 Accuracy；
- 报告绝对值和百分点提升；
- profile-wise 结果和 confusion / per-class behavior 用于说明改善发生在哪里；
- 当前 headline：`0.65074 → 0.70534`，mean paired Δ `+0.05460`（`+5.46 pp`）。

### RRUFF-301

- 角色：平衡、人工整理真实域上的 few-shot adaptation / label efficiency；
- K=1/2/5 分别报告 Macro-F1、Accuracy 和百分点差；
- 主图：K-shot learning curve；
- zero-shot 只作诊断起点或补充结果，不支配真实域叙事；
- 因数据已平衡，Balanced Accuracy 不必成为 headline。

### CNRS-318

- 角色：天然不平衡的第二独立真实域，冻结模型 zero-shot external evaluation；
- 类别 support：`21 / 87 / 77 / 41 / 33 / 12 / 47`；
- 主表至少报告 Macro-F1、Balanced Accuracy、Accuracy；
- 同时报告 per-class F1 与 support；
- 当前 performance picture：seed-level Macro-F1 `0.188372±0.026336 → 0.207085±0.021336`，mean paired Δ `+0.018713±0.006754`；pooled Macro-F1 `0.191176→0.209119`、Balanced Accuracy `0.218225→0.238777`、Accuracy `0.200000→0.210063`。

---

## 3. Tier B — supporting scientific evidence（支持结果层）

Tier B **属于可汇报结果**，但它必须服务于 Tier A，而不能替代 Tier A。

使用：

- mean ± sample standard deviation；
- matched-seed 方向一致性，例如 5/5；
- worst-class F1；
- representative failure analysis；
- paired-view consistency / flip rate / confidence variation；
- ECE；
- NLL；
- Brier score；
- predictive entropy；
- confidence behavior；
- 必要时的 uncertainty / rejection analysis。

这些指标回答：

> **主性能结果是否稳定？是否伴随更合理的概率行为？机制证据是否与性能方向一致？**

其中：

- mean ± SD 和 5/5 seed 可以和 Tier A 主指标一起出现；
- failure analysis、per-class behavior 非常值得在 XRD 论文/汇报中展示；
- ECE/NLL/Brier 只说明 probability quality，不是 PXRD 分类社区的主成绩；
- JS consistency / flip rate 等只作为机制支持，不能替代 Accuracy / F1。

CNRS 可以表述为：

> performance improvement is accompanied by improved calibration / probability quality.

当前 pooled ECE `0.682570→0.612420`、NLL `8.319988→6.118566`、Brier `1.433841→1.315606`；绝对 ECE 仍高，说明改善并未消除 sim-to-real reliability gap。

---

## 4. Tier C — strict statistical audit（内部审计层）

包括：

- parent-level paired bootstrap；
- class-stratified paired bootstrap；
- 95% confidence interval；
- paired-seed difference distribution；
- per-class uncertainty；
- uncertainty decomposition；
- p-value（若未来使用）。

### 汇报规则

> **Tier C 默认不进入常规科研汇报。**

保存位置：

- 本地/仓库 JSON；
- CSV；
- analysis output；
- audit report。

只有在以下情形调出：

- 审稿人要求统计不确定性；
- 导师专门询问统计证据；
- 内部审计；
- 复核某项结果是否稳定。

`CI crosses zero` 的正确含义仍是：在该 resampling model 下效应估计存在较大不确定性。它不自动等于实验失败、方法无效或 Tier A/B 结果作废。

CNRS 修正后的 class-stratified paired-parent 95% CI `[−0.009339, +0.046107]` 应继续永久保存，但**不放在常规导师汇报主结果页或 Results 主表里**。

---

## 5. Tier D — engineering / reproducibility（工程与复现层）

包括：

- hashes / manifests / run records；
- checkpoint SHA；
- exact seed IDs；
- train/validation loss；
- gradient norm / gradient ratio；
- early-stop epoch；
- step count；
- AMP / bfloat16 / fused optimizer；
- GPU / runtime environment；
- 以及完整 config 中的训练和工程参数。

### 汇报规则

> **Tier D 不作为“结果”汇报，只在本地记录与复现时使用。**

论文 Methods / 技术备忘录仍可以从 Tier D 中提取**最小必要复现参数**，例如：

- 2θ 范围、步长、波长；
- 数据 split；
- 扰动范围；
- backbone；
- optimizer；
- learning rate；
- λ_JS；
- batch size / epochs / preprocessing。

但这些参数不得出现在“项目成绩”或 Results 主表中，也不得因为工程记录更详细就被包装成科研贡献。

---

## 6. 避免数学与 AI 工程冗余

- 标准 single-label multiclass 任务中，micro-F1 等于 Accuracy；无需同时 headline。
- 标准 multiclass Balanced Accuracy 等于 mean per-class recall；已有 Balanced Accuracy 时，macro recall 不必重复。
- 平衡/模拟域简洁主表：Macro-F1、Accuracy；Tier B 可附 mean ± SD。
- 天然不平衡真实域简洁主表：Macro-F1、Balanced Accuracy、Accuracy、per-class F1/support。
- Top-k 只用于候选检索或大类别任务。
- loss、梯度、hash、checkpoint、GPU、exact seed 编号等不得因为“数字很多”进入结果页。

---

## 7. 推荐叙事

项目整体结论应主要由 Tier A / B 构成：

> Simulated OOD 的 Accuracy / Macro-F1 提升、RRUFF few-shot 的 label-efficiency learning curve、CNRS 的 Macro-F1 / balanced accuracy / accuracy 改善，以及 matched-seed、逐类、failure analysis 和概率可靠性等支持证据，共同支持 JS 利用同母结构不同测量视图的关系，学到了比匹配 Dynamic ERM 更稳健的模型。

CNRS 常规推荐写法：

> On the naturally imbalanced CNRS experimental domain, JS improves Macro-F1, balanced accuracy and overall accuracy, with positive Macro-F1 changes across all five matched training seeds. The performance gain is accompanied by improved calibration, although absolute real-domain performance remains limited.

严格 bootstrap CI 留在 Tier C 内部审计，除非被明确要求，不主动放入常规汇报主文。

---

## 8. 严谨性底线

“Tier C / D 默认不汇报”不等于允许删除不利证据。

必须继续遵守：

- 不得删除或篡改不利统计结果；
- 不得看完结果后更换指标制造更好结论；
- 不得修改 frozen test 数据或事后删除 CNRS 样本；
- 不得重选 checkpoint、seed 或 `lambda_js`；
- 不得反复重跑到结果满意为止；
- 不得改写历史 raw outputs 或冻结协议；
- Tier C / D 必须可在本地审计记录中追溯。

区别只是：

> **内部完整保留 ≠ 对外每次都展示。**

---

## 9. 文档优先级

关于“哪些结果需要汇报”，当前优先级为：

1. `docs/PXRD_EFFECTIVE_RESULT_SELECTION_STANDARD.md`；
2. 本文件 `docs/PXRD_RESULT_REPORTING_STANDARD.md`；
3. `xrd_robustness/reports/RESULTS.md` 作为冻结事实来源；
4. Tier C / D 的 protocol、audit、run record、JSON、manifest 作为内部证据库。

若旧文件把 bootstrap、hash、provenance 或其他内部指标放得比 XRD performance 更高，按当前标准重新组织汇报，但不改动历史原始记录。

本规范来自对 2019–2026 年代表性 PXRD / XRD ML 工作所采用指标的整理，包括 Oviedo et al.、Suzuki et al.、CrystalMELA、Lee et al.、Schopmans et al.、SimXRD-4M、XQueryer 与 RealPXRD-Solver。正式论文的 Related Work 与指标选择说明仍应引用对应原始文献。

---

## 10. 最终口径

> **Tier A + Tier B 才是“要汇报的结果”。**  
> **Tier C + Tier D 是“要保存的证据”，默认留在本地机器可读记录和审计文件中。**

以后生成 PPT、导师汇报、项目总结、Results 表和申请材料时，默认只读取 Tier A / B 作为输出候选。