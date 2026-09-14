# 项目发展记录：重新界定 same-class pairing 消融的角色

**日期：** 2026-09-14  
**性质：** 方法论边界修正；不改变已经冻结的 ERM–JS 主结果。

## 问题来源

在主线结果已经证明 `same-parent JS` 优于 matched Dynamic ERM 之后，为了进一步追问“收益是否特异地来自 parent identity”，新增了 `same-class different-parent JS` 对照。

随后发现，这个问题本身比主项目原始科学问题更强：它要求证明 `same-parent` 不仅优于“不使用关系监督”，还必须优于另一种人为构造的 consistency 关系。

这不是主方法成立所必需的条件。

## 主问题重新确认

项目真正需要回答的是：

> 在相同 parent structures、相同两张在线扰动谱、相同 CE、相同 backbone、相同 optimizer、相同训练预算与配对 seed 下，显式加入“同一母结构的两个 measurement views 应保持预测一致”这一关系监督，是否比不加入 consistency 更好？

这一问题已经由 frozen Dynamic ERM vs Dynamic JS matched experiment 直接回答。

两者唯一方法差异是：

- Dynamic ERM：`0.5 * [CE(p1,y) + CE(p2,y)]`
- Dynamic JS：`0.5 * [CE(p1,y) + CE(p2,y)] + lambda_js * JS(p1,p2)`

因此，ERM–JS 对照本身就是主方法最关键的消融：它检验“加入 same-parent consistency relationship supervision 是否有价值”。

## same-class 消融的正确角色

`same-class different-parent JS` 不是主方法成立的必要 Gate，而是一个更强、更窄的机制诊断：

> parent identity 是否比一般性的 same-class consistency 关系更特殊、更必要？

它只能用于限定更强的机制 claim，不能反过来否定已经成立的主结果。

100-epoch exploratory result 显示：same-class consistency 经过更长训练可以逼近 same-parent 的总体 OOD 表现，因此当前不应声称“只有 same-parent consistency 才有效”或“parent identity 是 consistency 收益的唯一来源”。

但这不改变以下已成立事实：

1. same-parent Dynamic JS 相比 matched Dynamic ERM 提升模拟 OOD 鲁棒性；
2. 两者数据暴露完全匹配，新增项就是 same-parent JS consistency；
3. RRUFF few-shot 与 CNRS support evidence 仍按原边界解释；
4. same-class experiment 属于 post-hoc mechanism exploration，而不是主结果的有效性判据。

## 后续汇报原则

正式 XRD-ML 报告与 PPT：

- 主线仍是 `Dynamic ERM -> same-parent Dynamic JS`；
- 主结果只回答“same-parent consistency 是否比不使用 consistency 更有效”；
- 不把 same-class ablation 作为主方法必须通过的 Gate；
- 若讨论机制，可把 same-class 结果作为探索性补充，用于说明“generic consistency 也能解释部分收益，因此 parent identity 的唯一性尚未建立”。

该修正与项目此前“避免把通用 AI 审计标准变成材料/XRD 项目的额外考试”的原则一致。
