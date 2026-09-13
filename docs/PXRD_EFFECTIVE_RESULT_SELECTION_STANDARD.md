# PXRD 有效结果选取标准

**状态：当前有效 / canonical**  
**生效日期：2026-09-13**  
**适用范围：** `Frysland-2024/AI4science` 中 PXRD 七晶系鲁棒分类主线，以及后续基于同一任务体系的结果汇报、导师汇报、论文 Results、PPT 和申请材料。  
**目的：** 明确项目会输出很多数字，但**不是所有数字都是“科研结果”**，更不是所有数字都应参与项目好坏的评级。本标准按照 PXRD / XRD machine-learning 论文常见评价方式，区分：真正影响科学判断的结果、支持性结果、Methods 参数和过度 AI 工程化的审计信息。

---

## 0. 一句话原则

> **评价 PXRD 机器学习工作，首先看模型在 XRD 任务上“分得准不准、跨扰动/实验域是否仍然分得准、哪些晶系分错了、真实谱上是否有实际收益”；而不是先看 loss、梯度、哈希、checkpoint、ECE、bootstrap 或训练工程细节。**

本项目的结果排序遵循：

```text
XRD classification performance
    > per-class / perturbation / experimental-domain behavior
    > probability reliability / mechanism evidence
    > strict statistical audit
    > training engineering / provenance
```

这不是降低严谨性。低层信息仍永久保留，只是**不能把工程审计当作项目主成绩**。

---

# 1. 文献对齐依据

本标准主要对齐以下类型的 PXRD / XRD ML 工作，而不是对齐通用大模型 benchmark：

### Oviedo et al., npj Computational Materials 2019

其分类结果核心报告：

- Accuracy；
- Micro-F1 / Macro-F1；
- 五折交叉验证的均值与标准差；
- simulated-only、sim→experimental、sim+experimental 三种任务条件；
- 随 augmentation 数量、2θ step size 变化的性能；
- CAM 和代表性误分类谱用于解释错误原因。

对本项目的直接启示：**Accuracy / Macro-F1、真实谱性能、误分类解释和物理条件下的性能变化属于真正结果。**

### Lee et al., Advanced Intelligent Systems 2023

七晶系（CS）主指标采用 **top-1 Accuracy**；101/230 类 EG/SG 才讨论 top-k。论文核心比较：

- compound-based hold-out test Accuracy；
- standard / perturbed synthetic data 上的 Accuracy；
- experimental powder / RRUFF 上的 Accuracy；
- confusion matrix 和具体 misclassification analysis；
- 数据划分是否避免同一 compound 的不同扰动跨 train/test。

对本项目的直接启示：**七晶系任务不需要为了“AI 味”增加 top-k；top-1 分类性能、真实实验性能、confusion / class behavior 才是主结果。**

### Schopmans et al., Digital Discovery 2023

主要以：

- unseen-structure-type test Accuracy；
- synthetic-crystal training vs ICSD training 的 Accuracy；
- experimental RRUFF 初步测试；
- 数据集 / split 设计

来判断模型能否提取结构信息。

对本项目的直接启示：**泛化任务中的绝对分类性能和合理的数据划分优先于复杂统计包装。**

---

# 2. 四层“有效结果”分类

## Tier A — 主科学结果：真正影响项目评级

这一级结果决定“模型是否更好”“方法是否成立”“真实 XRD 上是否有价值”。论文摘要、Results 主表、导师汇报第一页优先放这里。

### A1. Accuracy / Top-1 Accuracy

**有效等级：核心。**

适用：

- 七晶系这种标准 single-label multiclass 分类；
- simulated Test；
- RRUFF；
- CNRS。

原因：XRD ML 文献最常见、最直观，Lee / Schopmans 等工作直接以 Accuracy 作为核心结果。

注意：七晶系不需要常规报告 Top-3 / Top-5。只有上百类空间群或候选检索问题时，top-k 才具有明确任务意义。

### A2. Macro-F1

**有效等级：核心。**

本项目建议与 Accuracy 并列主指标，尤其用于：

- 七晶系均衡任务中检查所有类别是否共同改善；
- RRUFF few-shot；
- CNRS 自然不平衡域；
- OOD 评估。

Macro-F1 的意义不是“更 AI”，而是避免总体 Accuracy 掩盖低支持或难分类晶系。

### A3. Balanced Accuracy

**有效等级：核心，但仅在天然不平衡域。**

主要用于 CNRS-318。

模拟 Test 和 RRUFF-301 本身接近平衡，不需要为了表格更长而强行把 Balanced Accuracy 放 headline。

### A4. 绝对性能 + percentage-point improvement

**有效等级：核心。**

必须同时报告：

- ERM 的绝对值；
- JS 的绝对值；
- JS−ERM 的百分点变化。

不能只写“提升 5.46 pp”而不写 `0.6507 → 0.7053`。

### A5. 实验真实域性能

**有效等级：最高。**

对本项目：

- RRUFF-301 的 K-shot Macro-F1 / Accuracy learning curve；
- CNRS-318 zero-shot Macro-F1 / Balanced Accuracy / Accuracy。

原因：XRD ML 的最终意义是实验谱是否可用。真实域性能通常比模拟 Validation 上复杂的内部诊断更具有材料学解释力。

### A6. Per-class F1 / recall / support + confusion matrix

**有效等级：核心诊断结果。**

这是 XRD 分类里真正具有物理解释价值的结果之一，回答：

- triclinic / monoclinic / orthorhombic 等哪些晶系最难；
- tetragonal↔trigonal 等错误是否系统出现；
- 方法改善是否只来自某一类；
- 是否存在低对称性不可分、峰重叠或实验域偏差。

对于 CNRS，必须同时带 support，因为 `n=12` 的 hexagonal 与 `n=87` 的 monoclinic 不能按相同证据强度解释。

### A7. Profile-wise XRD perturbation performance

**有效等级：核心。**

对每种物理扰动分别报告 F1 / Accuracy：

- peak shift；
- broadening；
- preferred orientation；
- background；
- noise；
- combined perturbations（作为补充）。

原因：这些 profile 对应 XRD 的物理测量变化。它们回答“方法到底对哪种 XRD 扰动有效”，比单纯报告一个平均 OOD 分数更具科学解释力。

### A8. Few-shot learning curve / label efficiency

**有效等级：核心。**

RRUFF 主结果应直接报告 K=1/2/5 下 Macro-F1 / Accuracy，而不是只报告某一个 K。

研究问题是：相同真实标签预算下，哪种预训练表示更容易适配实验域。

---

## Tier B — 支持性科学结果：有价值，但不能替代主成绩

### B1. mean ± SD / 多 seed 稳定性

**有效，但属于主结果的可信度增强。**

应与 Accuracy / Macro-F1 一起出现，例如：

`0.6507 ± 0.0072 → 0.7053 ± 0.0098`

“5/5 seeds favor JS”可以作为增强证据，但**不能单独替代绝对性能**。

### B2. Worst-class F1

**有效，但为辅助结果。**

适合说明是否存在某一晶系被严重牺牲；不是典型 XRD 论文 headline 指标。

### B3. Representative failure analysis

**高度推荐。**

包括：

- 典型误分类谱；
- ground truth vs predicted class；
- 峰重叠、弱峰、缺峰、texture、背景等可能原因；
- 若有解释性工具，可显示模型关注的峰区。

这类分析在 Oviedo、Lee 等 XRD ML 工作中是真正的科学内容，而不是 AI 装饰。

### B4. JS paired-view consistency / flip rate / confidence variation

**机制证据。**

若研究问题是“same-parent relationship supervision 为什么有效”，这些指标可帮助闭环：

`consistency constraint → predictions become more stable → OOD performance improves`

但它们不能代替 Accuracy / F1。

### B5. ECE / NLL / Brier / predictive entropy / confidence

**可靠性增强证据，不是 PXRD 社区 headline。**

可以说明 JS 的性能改善是否伴随更合理的概率质量。

当前项目允许写：

> performance improvement is accompanied by improved calibration / probability quality.

不能把项目主要贡献改写成“ECE 从多少降到多少”。

---

## Tier C — 严格统计审计：保留，但不主导科研评级

包括：

- parent-level paired bootstrap；
- class-stratified bootstrap；
- 95% CI；
- paired-seed difference distribution；
- uncertainty decomposition；
- p-value（如果未来使用）。

这些结果回答“我们对效应估计有多确定”，不是回答“XRD 模型分得准不准”。

因此：

> `CI crosses zero` = 在该 resampling model 下不确定性较大。

它**不自动等于**：

- 实验失败；
- 方法无效；
- 不能报告正向结果；
- 5/5 seed、Accuracy、Macro-F1、Balanced Accuracy 等全部作废。

严格统计必须如实保留，但应放在详细 Results / limitation / appendix，不应该把整项 XRD 工作包装成统计显著性考试。

---

## Tier D — Methods / Reproducibility：重要，但不是“结果”

以下信息必须记录，因为它们决定复现和实验解释，但**不参与项目性能评级**：

- 2θ 范围、step size、wavelength；
- 数据来源和 split；
- parent identity；
- peak-shift / FWHM / background / noise / March–Dollase 范围；
- 模型架构；
- parameter count；
- optimizer / learning rate / weight decay；
- `lambda_JS`；
- batch size；
- training epochs；
- early stopping；
- preprocessing / normalization；
- frozen checkpoint 选择规则。

这些属于 **Methods 参数**，不是“模型表现结果”。

特殊例外：若论文明确研究“采集分辨率”“模型大小”“计算效率”，相应 step size / parameter count / runtime 才升级为科学结果。Oviedo 的 2θ coarsening 就属于这种情况，因为它直接研究 acquisition-speed vs accuracy trade-off；本项目固定 `0.02°` 时，它只是方法参数。

---

# 3. “过于 AI 工程”的输出：不应影响科研评级

以下数字可以留在日志、audit、仓库，但默认**不进入导师汇报主结果表、Abstract 或论文 headline**：

| 输出 | 默认角色 | 为什么不是有效主结果 |
|---|---|---|
| Train loss / CE loss | 工程诊断 | 只说明优化过程，不代表 XRD 分类质量 |
| Validation loss | 工程诊断 | 不如任务指标直观；仅用于训练控制 |
| JS loss 数值本身 | 机制/工程 | loss scale 不可跨配置直接解释 |
| gradient norm / gradient ratio | 调参审计 | 用于判断 λ 是否有梯度作用，不是材料学性能 |
| best epoch / stop epoch | 复现参数 | 不表示方法科学价值 |
| step count / samples seen | 工程复现 | 除非研究 sample efficiency，否则不评级 |
| learning rate / weight decay | Methods | 训练设置，不是结果 |
| fused AdamW / AMP / bfloat16 / float32 fallback | 工程 | 与 XRD 科学结论无直接关系 |
| GPU 型号 / GPU 数量 /显存 | 工程 | 除非论文声称计算效率优势 |
| checkpoint SHA / file SHA256 | provenance | 数据卫生，不是科学贡献 |
| manifest hash / Git commit hash | provenance | 复现追踪，不是模型性能 |
| exact seed IDs | reproducibility | 需要记录，但 seed 数字本身不是结果 |
| raw parameter count | Methods | 除非明确比较模型简洁性/效率 |
| train accuracy | learnability diagnostic | 可用于排障，但不能作为最终性能证明 |
| calibration-only improvement | supporting | 不能替代真实分类性能 |
| bootstrap CI 单独一项 | audit | 不能脱离绝对效果量、seed 和任务指标单独判刑 |

这些内容的共同特点是：

> **它们主要告诉我们“实验有没有正确执行”，而不是“模型是否更会分析 XRD”。**

---

# 4. 本项目最终“有效结果”优先级

当以后问“当前项目结果到底好不好”，严格按下面顺序看。

## 第一优先级：模拟 Test 的 XRD 分类性能

必须看：

1. mean single-factor OOD Macro-F1；
2. mean single-factor OOD Accuracy；
3. in-range Macro-F1 / Accuracy；
4. profile-wise F1 / Accuracy；
5. per-class F1 / confusion matrix。

当前 headline：

- OOD Macro-F1 `0.65074 → 0.70534`，`+5.46 pp`；
- OOD Accuracy `0.65078 → 0.70524`，`+5.45 pp`；
- 5/5 matched training seeds 为正。

## 第二优先级：RRUFF-301 few-shot 实验谱

必须看：

- K=1/2/5 Macro-F1；
- K=1/2/5 Accuracy；
- learning curve / label efficiency；
- per-class behavior（如果用于详细分析）。

这是项目当前最强的真实域应用证据。

## 第三优先级：CNRS-318 独立来源 zero-shot

必须看：

- Macro-F1；
- Balanced Accuracy；
- Accuracy；
- per-class F1 + support；
- confusion / 典型错误。

ECE/NLL/Brier 放在第二层说明 probability quality；bootstrap CI 放严格审计层。

## 第四优先级：机制和概率可靠性

包括：

- paired-view consistency；
- ECE/NLL/Brier；
- confidence / entropy；
- mechanism-specific diagnostics。

它们解释“为什么可能更稳健”，不能替代前三层。

---

# 5. 论文 / PPT 的结果表应该长什么样

## 模拟 Test 主表

推荐只放：

| Method | In-range Accuracy | In-range Macro-F1 | OOD Accuracy | OOD Macro-F1 |
|---|---:|---:|---:|---:|
| Dynamic ERM |  |  |  |  |
| JS consistency |  |  |  |  |

旁边再给一张 profile-wise 图和 confusion matrix。

`worst-class F1`、CI、ECE、NLL、Brier 不要全部挤进主表。

## RRUFF 主表 / 主图

K=1/2/5：

- Accuracy；
- Macro-F1；
- mean ± SD；
- JS−ERM pp improvement。

最适合用 learning curve 图展示。

## CNRS 主表

| Method | Accuracy | Balanced Accuracy | Macro-F1 |
|---|---:|---:|---:|
| ERM |  |  |  |
| JS |  |  |  |

另表给 per-class F1 + support。

ECE/NLL/Brier 放“可靠性补充结果”。

---

# 6. 哪些当前常见输出以后不再写进“主结果”

从本标准生效起，下列内容除非特别回答对应研究问题，否则不得被包装成 headline scientific result：

- gradient-scale Gate；
- λ=3/30/60 的梯度比；
- early-stopping 具体轮数；
- 616 steps/epoch、9856 parent draws；
- fused AdamW；
- bfloat16 fallback；
- hash / manifest / provenance 完整度；
- checkpoint 选择 tie-break 的细节；
- 单独的 ECE/NLL/Brier improvement；
- 单独的 bootstrap CI；
- 单独的 prediction entropy / confidence；
- 单独的 train accuracy。

它们仍然可以存在于 Methods、appendix、audit 和内部记录中。

---

# 7. 有效结果的最低完整性要求

一个数字只有满足以下条件，才可以进入“有效科学结果”主表：

1. 对应明确的 XRD 任务条件（simulated ID/OOD、RRUFF few-shot、CNRS zero-shot）；
2. 有明确 test / locked evaluation 数据，而不是 train-only；
3. 使用社区可解释指标（Accuracy / Macro-F1 / Balanced Accuracy / per-class F1）；
4. 能说明样本单位和 support；
5. 比较方法之间的数据暴露和任务条件可比；
6. 对 repeated runs 报 mean ± SD 或至少说明 run 数；
7. 不用内部工程指标代替真实分类性能。

---

# 8. 当前项目的一句话评价标准

以后评价这个项目，只问四件事：

> **(1) 在冻结 simulated Test 上，七晶系 Accuracy / Macro-F1 是否稳定提高？**  
> **(2) 在峰移、展宽、织构、背景、噪声等实际 XRD 扰动上，改善发生在哪里？**  
> **(3) 在 RRUFF / CNRS 实验谱上，Accuracy / F1 / label efficiency 是否改善？**  
> **(4) 哪些晶系仍然容易混淆，错误是否有 XRD 物理解释？**

如果这四件事成立，项目结果就成立。

训练 loss、梯度比、CI、ECE、哈希、GPU、checkpoint 只是用来回答：

> **“我们对这个结论有多放心、实验是否可复现、机制是否合理？”**

它们不是这个项目“成绩是多少”的答案。

---

# 9. 与现有项目文档的关系

- 本文件：**决定哪些输出算“有效结果”，哪些不参与主评级。**
- `docs/PXRD_RESULT_REPORTING_STANDARD.md`：规定这些结果怎样分层汇报。
- `xrd_robustness/reports/RESULTS.md`：当前冻结结果事实来源。
- `docs/PXRD_PERTURBATION_EVIDENCE.md`：五类扰动的物理与文献依据。
- `docs/XRD_技术细节备忘录_彻底重写版.md`：Methods / 物理复现技术备忘录。

若未来内部 audit 文档与本文件在“什么是 headline scientific result”上冲突，以本文件与 `PXRD_RESULT_REPORTING_STANDARD.md` 为当前对外汇报标准；原始实验输出与不利结果不得因此删除或修改。

---

# 10. 最终原则

> **XRD-ML 的有效结果不是“模型产生了多少数字”，而是这些数字是否回答 XRD 分类问题。**

有效结果优先回答：

- 分得准不准；
- 实验谱能不能用；
- 物理扰动下是否稳健；
- 哪些晶系容易错；
- 少量真实标签是否能改善部署。

过度 AI 工程化的信息主要回答：

- 怎么训的；
- 有没有收敛；
- 怎么追踪文件；
- 梯度是不是活着；
- 统计审计有多严格。

两者都需要，但**只有前一类决定这个 PXRD 项目的科学评级。**
