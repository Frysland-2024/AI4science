# 2026-10-18 文献纠偏：为何 Forward Model 仍是 AI 辅助 PXRD 预精修的核心

> **Current status (2026-10-23): ARCHIVED / INACTIVE.** This document is retained as a historical proposal or task record. It is superseded by the sole active PXRD seven-crystal-system classification direction and the three evaluation axes in [CURRENT_STATE](CURRENT_STATE.md) and [the scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md). Do not execute or reactivate this route based on its earlier wording.
>
> The literature review below supports a historical proposal only; it is not an active project direction.

**原始状态（2026-10-18）：LITERATURE-GROUNDED DESIGN REVIEW / FUTURE CANDIDATE；无新实验。当前状态（2026-10-23）：ARCHIVED / INACTIVE。**
**背景：** 现有 [12 周计划](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md) 强调“模拟训练→Top-K 候选相＋晶格参数初值＋校准＋Forward 核验”，但如果 Forward 只作为离线数据发生器，研究将退化成普通晶相分类。此处基于查到的原始文献明确方法先例、科学问题和可能的对照，不代表新功能已实现，亦不立即授权大规模训练。

## 1. 直接先例（原文网页/DOI，逐项核对）

| 研究 | 已发表做了什么 | 对本项目的启示 / 不能直接声称的新颖性 |
|---|---|---|
| Chang et al. (2025), **CrystalShift**, *npj Computational Materials* 11, 148. [DOI](https://doi.org/10.1038/s41524-025-01627-0), [code](https://github.com/MingChiangChang/CrystalShift.jl) | 对候选相及**相组合**执行对称性约束的晶格参数优化，比较正向拟合，通过 Bayesian model comparison 形成概率输出；无需训练神经网络。报道 synthetic 和 experimental 结果、概率校准/噪声敏感性。 | **首要强基线**；“相组合概率＋晶格参数优化＋物理比谱”不能直接当成原创想法。与全套 Rietveld 仍有适用范围差异。 |
| Dong et al. (2021), **PQ-Net**, *npj Computational Materials* 7, 74. [DOI](https://doi.org/10.1038/s41524-021-00542-4) | CNN 对多相粉末衍射预测 scale factors、lattice parameters、crystallite size，在大规模实验衍射数据上与 full-profile Rietveld 结果比较并讨论 uncertainty。 | AI 连续参数预测/全谱分析已有重要先例；可借鉴参数任务、预测速度与对照范式。 |
| Lee et al. (2020), *Nature Communications* 11, 86. [DOI](https://doi.org/10.1038/s41467-019-13749-3) | 在 Sr–Li–Al–O 限定成分空间，用 170 种参考化合物合成约 178 万混相粉末谱训练 CNN，报告混相识别与粗粒度 fraction classification 的真实样品结果。 | “限定材料家族/成分空间＋模拟库＋混相 CNN”已有非常直接先例；注意三档 fraction 分类不等于高精度 Rietveld 定量。 |
| Ito et al. (2026), **PhaseDifformer**, *npj Computational Materials* 12, 238. [DOI](https://doi.org/10.1038/s41524-026-02087-w) | 生成式模型将一条混相 PXRD 分解成组分单相谱，测试模拟和实验样品。 | 若扩展多相分解有参照，但**分解谱不等于物相证明或完整精修参数反演**。 |
| Oviedo et al. (2019), *npj Computational Materials* 5, 60. [DOI](https://doi.org/10.1038/s41524-019-0196-x) | 结构数据库模拟与物理知识增强支持小样本 XRD 分类；含受控模拟与真实谱的实验设计。 | 数据生成/增强与模拟—真实数据角色可借鉴，但不直接实现物相参数精修。 |
| **DONUT** (2025), *npj Computational Materials*. [文章](https://www.nature.com/articles/s41524-025-01860-7) | 针对扫描纳米 XRD，网络预测应变/倾斜并经**可微 forward 散射**回传谱图残差进行学习。 | 可微 Forward reconstruction loss 的方法论先例，但**不是常规 PXRD**，物理模型不可直接移植；该方向不是单凭 Loss 即有新颖性。 |

## 2. Forward Model 应该有的三个角色

1. **训练数据发生器（必要）**：已知参考 CIF/结构状态/测量条件 \(\to\) 模拟 XRD 与可信参数标签。必须检查结构因子、相消条件、晶胞约束、谱图轴、强度和 nuisance 模型的正确性；不能只用峰位模拟就宣称支持可靠相含量。
2. **推理期物理模型比较/局部反演（建议核心）**：对每个家族内单相或少量双相候选 \(H_k\) 由 AI 提出参数初值 \(\hat\theta_k\)，经 \(F(H_k,\theta_k, m)\) 重构谱，并允许受限局部优化；评价拟合残差与复杂度，输出 Top-K 候选/参数/失败出口。尤其不能把双相拟合降损自动当作共存证据，应处罚新增自由参数或用模型证据比较。
3. **可选训练期重构损失（独立消融）**：比较纯监督参数回归 \(L_{param}\) 与 \(L_{param}+\lambda D(F(H,\hat\theta),x)\)，按相同结构数/训练预算评估是否改善参数 MAE、初值质量、收敛域和真实域 case；需要可微性、数值梯度、可辨识性核验。此选项不因为“前人已做过”而无意义，也不因“有 forward”就自动带来改进。

**所以不是只能在推理期 *或* 训练期使用。** 建议首阶段先确保（1）和（2）是可靠、可复现的闭环；（3）是否加入取决于前置数值与时间条件。

## 3. 至少对照的三类系统

| 方法 | 推理方式 | 需要报告的差异 |
|---|---|---|
| **Physics only / CrystalShift 类基线** | 结构库＋前向物理候选优化＋概率模型比较，无 NN | 参数/候选正确性、计算时间、噪声和峰重叠的可靠性 |
| **NN only** | 模拟训练网络直接输出候选相/组合、每候选条件参数及模拟域校准 | 速度、参数 MAE、Top-K、ECE/NLL/Brier、sim-to-real 退化 |
| **NN initialization + Forward checking/refinement** | NN 提案／初值，Forward 检查并可局部精修，输出更谨慎的候选报告 | 相同物理拟合预算下的收敛、时间、误认率、拒判率、参数误差、拟合残差及不确定性 |

若第三种并不优于第一种，不能只因加入 AI 就宣称科学增益；负结果须保留。“加 Forward reconstruction training loss”可作为第四种追加条件，而**不是本阶段完成前提**。

## 4. 混相及置信度边界

- 单相 `P(R | single-phase set,x)` 与双相 `P(H_{R+C}|x)` 是不同结构模型假设的概率；二者都**不是**真实质量分数。
- 混相生成可在结构物理假设允许时写为 \(I(q)=s_R F_R(q,\theta_R)+s_C F_C(q,\theta_C)+B(q)\)。衍射权重与真实重量百分比不能直接等同；应考虑结构因子、质量、参考强度、织构等。
- 类别 softmax 在训练外/未知家族/混相可能极度自信；优先使用模型残差、OOD/review 标志和单相/混相竞争假设，概率校准先在严格模拟验证分布进行；少量真实谱不得声称真实域 ECE 得到稳定验证。
- **难点不是“能够拟合两相一定优于一相”**，而是低含量、峰重叠、仪器失配、拟合自由度下，什么证据足以支持更复杂的模型。

## 5. 具体的 W0 / Work 纠偏建议

- Work 的 W0 先审计 `xrd_inversion` 既有 forward 是否支持各相的结构因子/全谱强度模型、复用程度、数值正确性及现有冻结证据；新增任务不可覆盖已有研究。
- **最小可运行 Demo 不能仅止于输出分类 Top-K**：至少对 *两个有可靠 CIF 的单相候选* 用同一测量条件重构谱、估计有限晶格初值/局部数值改良、画叠加/残差，再输出可信的“拟合是否充分/需复核”；训练模型可没有，但 **Forward 的物理比较必须真实运行**。
- 如需要对接 CrystalShift 开源实现，先核实依赖、许可、可运行性、物理假设，**不要承诺马上移植全套 Julia 系统**；第一版可以先复现实验中的最小物理-only baseline。
- 在研究材料家族未由合作学长确定前，临时 BaTiO3 为 **engineering smoke**，正式模拟泛化与真实样品适用性不得从该例推断。

## 6. 项目历史及科研 claim

2026-10-08 的连续参数＋可微重构初始研究方案 → 2026-10-18 转向概率化相候选与精修前初值 → 同日文献对照发现 **CrystalShift 已完成相组合概率、对称性约束参数优化与 Forward 物理模型比较** → 修正为 **模拟学习能否高效、可靠地为已知物理反演提供候选与好的初值；比较 physics-only / NN-only / hybrid，且分别考察 train-time reconstruction loss 是否有效**。

**不改写过去：** V9 的 JS-only same-parent 研究已经完成并冻结；2×2 解耦 Stage-1 NO-GO 仍封存；现有 `xrd_inversion/` 仅具有已知四方单相 forward 数值基础，未实证多相量化。该文档是 **literature audit + prospective design choice**，不是新论文已经发表/系统完成或专用实验已经跑通的声明。
