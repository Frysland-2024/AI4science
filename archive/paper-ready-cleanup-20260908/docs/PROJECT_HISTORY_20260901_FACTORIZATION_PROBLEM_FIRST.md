# 2026-09-01 方法论补充：从“方法迁移”到“物理问题先行”

> **性质：** 项目历史档案 / 申请叙事记录。  
> **关联记录：** `PROJECT_HISTORY_20260901_XRD_INVERSION_NOVELTY_PIVOT.md`

## 核心修正

在把 PXRD 定量反演主线重定位为 `structure–measurement factorized inversion` 后，需要明确记录一个重要的方法论区别：

> **最终使用的 ML 组件本身完全可以是已有的小方法；当前主张的新意不应放在“发明一个新的 disentanglement 网络”，而应放在 XRD 物理问题定义、可控干预和 simulator-known 关系监督。**

这与此前某些“先看到一个 ML 方法，再搬到 XRD 试效果”的探索不同。

旧式方法迁移更接近：

```text
已有 ML 方法
    -> 搬到 XRD
    -> 看指标是否提高
```

当前 factorization 思路的来源顺序是：

```text
XRD 物理生成过程
    -> 观测同时受 sample state 与 measurement state 影响
    -> simulator 可以分别控制 / 干预这两类变量
    -> 因而天然得到 same-structure/different-measurement
       与 same-measurement/different-structure 的关系
    -> 再选择已有 ML 机制去利用这种关系
```

因此，即使最终模型只是：

```text
shared encoder
    -> structure head
    -> measurement head
    + paired consistency / factorization loss
```

也不应把 novelty 写成“提出新的双头网络”或“提出新的 disentanglement architecture”。

更准确的研究命题是：

> **将 known-phase PXRD inversion 重新表述为一个由物理干预监督的 structure–measurement factorization 问题，并利用模拟器天然保留的生成关系，学习区分材料真实状态与测量系统状态。**

## 与此前 residual 分支的区别

这个区别需要特别保留在未来申请叙事中。

此前 residual / decorrelation 分支更接近：先从其他领域看到一个表征去相关思想，再讨论它是否适合 XRD；后来发现 PXRD 中 nuisance 与 structure 具有结构相关耦合，简单要求 residual class-independent 过强，因此被封存。

当前 factorization 分支则反过来：

1. 先从衍射生成物理出发；
2. 明确哪些变量属于结构、哪些属于测量；
3. 利用可控模拟产生物理上确定的关系监督；
4. 最后才选择简单 ML 组件实现。

因此这次的核心不是“又找到一个 ML 小模块”，而是：

> **物理系统暴露出一种以前没有被利用的监督结构，ML 只是负责把这份监督吃进去。**

这也是当前更符合 AI4Science 的方法论表达。

## 当前执行含义

在扩大正式实验之前，不直接假定 paired factorization 有价值。下一步只执行一个有限的 Train-only 机制 Pilot：

`NEXT_FINITE_TASK_XRD_FACTORIZATION_SANITY_PILOT.md`

它专门检验：

> 在四参数真值监督已经存在时，paired physics supervision 是否仍能显著降低 `measurement -> structure` 与 `structure -> measurement` 的 cross-talk。

如果不能，就尽早 NO-GO；如果能，再把该思路升级为正式主线。
