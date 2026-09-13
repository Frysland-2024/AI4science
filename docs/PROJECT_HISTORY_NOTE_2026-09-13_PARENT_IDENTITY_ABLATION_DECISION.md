# 项目发展记录：把“方法有效”继续拆成“为什么有效”

**日期：** 2026-09-13  
**状态：** 已决定执行，结果尚未产生。

## 背景

在重新按 XRD-ML 社区范式整理结果后，当前主结果已经能够支持：same-parent JS consistency 比 matched Dynamic ERM 更稳健；模拟 OOD、RRUFF few-shot 和 CNRS independent-source evidence 的方向总体一致。

新的问题不再是“JS 到底有没有用”，而是更窄的机制归因：

> 收益是否真的来自 simulator 保留的 parent identity / measurement-equivalence relation，还是任意两个同晶系、不同 parent 的样本做 consistency 也能获得类似收益？

此前仓库没有这个直接对照，所以不能把“parent identity 是关键因果来源”写成已经被证明的结论。

## 决策

新增一个只改变 JS pairing identity 的机制消融：

`same-parent JS` vs `same-class different-parent JS`

为了避免重新引入数据暴露差异，两个 arm 使用完全相同的一批 parent、每个 parent 完全相同的两张 online views、完全相同的 CE、模型初始化、optimizer、lambda 和 Validation spectra。

唯一差异：

- same-parent：`view1(A)` 与 `view2(A)` 计算 JS；
- same-class：`view1(A)` 与同晶系另一 parent `B` 的 `view2(B)` 计算 JS。

same-class arm 通过 batch 内 second-view logits 的交换实现，因此不增加输入谱、不增加 forward，也不改变分类监督。

## 为什么先不重新跑 ERM

当前问题是 parent-specific relation 是否比 generic same-class relation 更有效，而不是重新证明 JS 是否优于 ERM。ERM-vs-JS 已经由主实验回答。

因此今晚先做最直接的两臂机制对照，可以把计算量压缩为两次训练；若后续论文真的需要三臂完整图，再加入同批次 ERM。

## 执行层级

第一阶段：单 seed、Validation-only quick pilot，不访问 simulated Test。

- seed `20260711`；
- 两个 pairing arms；
- 最多 60 epochs；
- 看 in-range 与 six-single-OOD mean Macro-F1；
- 输出 profile-wise parent-minus-same-class delta。

若单 seed 显示明显 parent-specific gap，再决定是否扩展到原五个 training seeds。五 seed 完整版本相当于 10 次训练，不在看到 pilot 之前默认投入。

## 结果如何改变项目叙事

如果 same-parent 明显优于 same-class：

> 可以把项目从“在同一母结构的两张谱上做 consistency”进一步推进为“模拟器的 parent provenance 本身提供有价值的关系监督”。

如果两者接近：

> 主结果仍然成立，但机制叙事应收缩为 generic consistency / class-level invariance，而不能强调 parent identity 的独特价值。

如果 same-class 更好：

> 需要主动修正当前对 parent provenance 的机制解释；这不会推翻原 ERM-vs-JS 主结果，但会改变创新点的表述。

因此这项消融无论正负都有信息价值。

## 实现

- 脚本：`xrd_robustness/scripts/run_pairing_ablation.py`
- 执行说明：`xrd_robustness/reports/PAIRING_ABLATION_PROTOCOL_20260913.md`
