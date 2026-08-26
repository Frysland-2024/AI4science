# 项目发展历史节点 — CNRS-318 重新定级为正式第二实验域（2026-08-27）

> 这是一个"认知修正"节点，不是一次简单的 PASS 盖章。它记录的是：项目先建立了一个
> 过严的门槛并据此下了 NO-GO，随后认识到那个门槛回答的是错误的问题，于是重新定义了
> 数据集的角色。这段转向本身值得保留为项目历程的一部分。

## 最初目标

为七晶系分类找一个与 RRUFF-301 **同规格**的第二 benchmark：各类别至少 20 个独立父样本、
类别平衡、统计强度与 RRUFF-301 相当。

## 原始判断（旧 NO-GO）

opXRD v11 的 CNRS 路径经严格审计后剩余 318 个独立父样本，七类分布为
`21 / 87 / 77 / 41 / 33 / 12 / 47`；hexagonal 只有 12 条。按"每类至少 20 个父样本"的
旧 Gate，hexagonal 不达标，因此当时判定为 **HOLD / NO-GO**，只能降级为探索性域。

旧判断的完整记录保留在 `xrd_robustness/data/real_xrd/opxrd_cnrs7cs/` 下的审计文档中
（该目录被 `.gitignore` 排除，但结论已整理进 `xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`）。

## 认知修正

两个问题被混在了一起：

1. "能不能作为正式的独立实验真实域"；
2. "能不能成为与 RRUFF-301 完全同规格、平衡、统计强度相同的 benchmark"。

**前者可以，后者没必要。** "每类至少 20 个父样本"是项目内部的一个保守 Gate，并不是该
领域公认的准入标准。hexagonal 只有 12 条，只意味着这一类的 F1/recall 单独看不稳定，
不意味着整个 CNRS 域无效。先例 RealPXRD-Solver 明确把 CNRS(126) 与 RRUFF(269) 并列作为
两个规模不等的实验数据集报告；opXRD 原论文也把带标签实验数据定位为 benchmark 资源。

## 重新定级（两问两答）

| 判断问题 | 结论 |
| --- | --- |
| 能否成为与 RRUFF-301 同样平衡、每类统计强度相近的 benchmark？ | **NO** |
| 能否作为自然类别分布下的正式独立实验域？ | **YES** |

**数据、标签和模型都没有因这次重分类而改变**——改变的只是数据集角色与结论强度的表述。

## 两个实验域的分工

| 实验域 | 命名 | 主任务 |
| --- | --- | --- |
| RRUFF-301 | balanced curated experimental domain | K=1/2/5 few-shot adaptation（主要 Few-shot 实验域） |
| CNRS-318 | naturally imbalanced independent experimental domain | frozen-model zero-shot external evaluation（正式第二实验域，主分析 Zero-shot） |

CNRS 不硬抄 RRUFF 的 few-shot 设计；它回答的是另一个互补问题：在不接触任何 CNRS 标签
的情况下，模拟训练所得的 JS 优势能否迁移到另一个数据库来源的自然实验分布。

## 范围限制（必须随结论一起写明）

CNRS-318 不是类别平衡域；hexagonal 只有 12 个父样本，关于 hexagonal 单独类的结论仍属
**underpowered（统计功效不足）**。宽 bootstrap 区间是数据的信息，如实保留，不人为补齐。

晶系标签由关联的 deposited structure 通过稳定对称重建获得，**未对每条实验谱做人工物相
核验**。因此不能声称 318 条谱都经人工确认、也不能声称每条谱一定理想单相且与 deposited
structure 完全一致；论文讨论中需承认可能存在少量 metadata、附加相或谱—结构对应误差。
这不影响 CNRS-318 作为正式第二实验域。

## 人工复核的取舍（2026-08-27 追加）

最初把质量控制堆得很满，拟做 42 条（12 hex 全查 + 其余六类每类 5）模型盲人工标签复核，
作为推理前置 Gate。随后认识到这超出当前研究问题真正需要的程度：更关键的机器化审计
（deposited structure 解析、多 `symprec` 稳定性、精确谱去重、结构父样本聚类、
`formal_14060` 重叠排除）已经完成。因此**人工复核正式降为不计划执行的可选增强项**。

这带来的唯一硬底线是：

> **318 条全部按冻结 manifest 使用，不能看完模型错误后再人工挑出"不好"的样本删除。**
> 可以分析错例，但不能依据预测结果修改评测集——否则会变成结果驱动的数据清洗。

## 当前执行准备状态

**PENDING**：数据集角色已定为正式第二实验域（Zero-shot 主分析），但正式推理尚未运行。
运行前还需完成：

- 冻结 `cnrs318_eval_manifest.csv` 与 `real.cnrs318.zero_shot.frozen.json`；
- 生成 `cnrs318_inputs.npz`（严格波长映射、3501 点、最大值归一化）；
- 一次性跑 10 个冻结模型（5 ERM + 5 JS），主指标配对差 Δ = MacroF1_JS − MacroF1_ERM；
- class-stratified paired parent bootstrap。

## 关联文件

- 数据集审计（git 可跟踪）：`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`
- 评测协议：`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`
- 父样本 manifest：`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`
- 冻结配置：`xrd_robustness/configs/real.cnrs318.zero_shot.frozen.json`
- 当前状态：`docs/CURRENT_STATE.md`
