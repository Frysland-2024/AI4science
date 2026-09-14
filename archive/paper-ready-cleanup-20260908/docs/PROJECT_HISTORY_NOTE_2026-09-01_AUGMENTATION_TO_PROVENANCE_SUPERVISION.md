# 项目发展节点：从随机物理扰动生成，到 provenance-aware relational supervision

**日期：** 2026-09-01  
**状态：** 正式记录；用于后续申请文案、PPT、Introduction 与项目发展史回顾。  
**关联主线：** PXRD robustness / Dynamic ERM vs Dynamic JS。

## 1. 这次认知收敛是什么

此前项目叙事曾经容易把 Schopmans et al. (2023) 单独当作“动态生成训练谱”的代表，并由此描述当前项目是在其基础上增加 JS consistency。

经过重新梳理文献谱系后，现正式修正为：

> **随机采样物理合理的扰动、生成多样化 XRD 训练谱，本身已经是一条较成熟的 PXRD-ML 路线；其中部分工作进一步采用训练时 on-the-fly 在线生成。Schopmans 是其中一个与当前实现特别接近的代表，而不是整个历史范式的唯一来源。**

因此，本项目不能把 novelty 写成：

- 发明随机 XRD augmentation；
- 发明物理扰动训练；
- 发明 on-the-fly PXRD generation；
- 或单纯“第一次把 JS 用到 XRD”。

## 2. 文献谱系带来的正式修正

代表性工作包括：

- Oviedo et al. (2019)：physics-informed XRD augmentation；
- Szymanski et al. (2021)：physics-informed perturbations；
- Lee et al. (2023)：大规模 peak shift / broadening / texture / background / noise augmentation，并在 Related Work 中系统梳理此前扰动路线；
- Schopmans et al. (2023)：continuous / on-the-fly generation，在训练期间持续生成 synthetic crystals 与 diffractograms。

这使得当前项目的 P2 历史背景应统一为：

> **现有范式：随机采样物理扰动，生成多样化训练谱。**

其中 Schopmans 单独作为：

> **进一步采用 on-the-fly continuous generation 的直接前驱。**

## 3. 真正发现的下一步机会

当 simulator 从同一个母结构 `s` 生成：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

普通 augmentation 视角主要看到：

> 又获得了两条带相同标签的训练谱。

但项目进一步意识到，模拟器实际上还知道：

> **x1 与 x2 来自同一个 parent crystal structure。**

所以 simulator 提供的并不只是：

```text
data + label
```

还包括：

```text
relationship / provenance
```

也就是：

> **哪些不同测量 realization 属于同一个 latent physical object。**

## 4. 从 Dynamic ERM 到 Dynamic JS 的重新理解

Dynamic ERM 已经可以看到完全相同的双视图数据：

```text
x1 -> y
x2 -> y
```

但它只显式使用 shared label。

Dynamic JS 额外把：

```text
parent(x1) = parent(x2)
```

转化为：

```text
measurement-equivalent views
        ↓
prediction consistency supervision
```

因此，当前项目真正研究的问题不再是：

> “多生成一些随机 XRD 有没有用？”

而是：

> **在已经采用成熟 stochastic / online generation 的前提下，模拟器保留的同源结构关系能否作为额外监督，提高模型对测量扰动的稳健性？**

## 5. 正式 novelty framing

中文主句：

> **已有工作主要利用随机物理扰动增加训练谱的多样性；我们进一步利用生成过程天然已知的同源结构关系，将其转化为学习约束。**

英文主句：

> **Prior work mainly uses stochastic physical perturbations to increase the diversity of synthetic diffraction data; we additionally exploit the provenance of generated views—knowing that they originate from the same underlying crystal structure—as a learning constraint.**

项目角色升级：

```text
simulator = data generator
        ↓
simulator = data generator + relationship supervisor
```

推荐标题式表达：

> **From data generation to provenance-aware relational supervision**

或者：

> **From scalable online PXRD generation to measurement-equivalence supervision**

## 6. 对前人的语气原则

以后不要把论文写成“挑战主流”或“前人方法不足所以我们替代它”。

正式语气应是：

> **继承并精进。**

即：

1. Oviedo、Szymanski、Lee 等工作已经证明 physics-informed stochastic perturbation 有价值；
2. Schopmans 进一步证明 continuous on-the-fly generation 可以持续扩大合成数据支持；
3. 当前项目站在这一成熟范式上继续追问：**生成过程本身还能提供什么监督结构？**

更成熟的英文写法：

> Previous on-the-fly generation established the value of continuously expanding synthetic training support. This formulation also creates an additional opportunity: because the simulator retains parent-structure provenance, multiple generated patterns can be treated not only as labeled examples, but as physically related observations of the same latent structure.

## 7. 对申请叙事的意义

这个节点对未来申请非常重要，因为它体现了项目思路从“材料数据工程”向“机器学习问题定义”的变化：

```text
阶段 1：怎样模拟更多、更真实的 XRD 扰动？
阶段 2：怎样训练时持续重采样、扩大 perturbation coverage？
阶段 3：为什么同一结构的不同观测只被当成独立样本？
阶段 4：模拟器能否从 data generator 进一步成为 relationship supervisor？
```

所以以后申请材料中，不应把项目简单包装为：

> “我给 XRD 加了一个 JS consistency loss。”

更准确的是：

> **我从既有物理增广与在线生成范式出发，进一步识别出模拟器天然保留的 parent provenance 是一种未被单样本监督充分利用的信息结构，并把这种同源关系转化为 measurement-equivalence consistency supervision。**

这个变化正体现了项目由：

> “怎样构造更多数据”

推进到：

> “怎样从科学生成机制中发现并利用额外监督结构”。

## 8. 当前边界

这份历史记录固定的是**方法定位与思想演化**，不是穷尽式 novelty 结论。

当前可以稳妥说：

> **本项目的增量不在随机物理扰动本身，而在显式利用 simulator-retained parent provenance 作为关系监督。**

在正式论文写：

> “first PXRD work to use same-parent consistency”

之前，仍需单独进行 same-parent / same-structure / paired-view / consistency / Siamese / contrastive / invariant + XRD/PXRD 的专项 novelty search。

## 9. 后续默认执行规则

后续所有：

- 组会 PPT；
- manuscript Introduction / Related Work；
- 研究计划；
- 套磁材料；
- SOP / Personal Statement；
- 项目发展心路历程；

默认采用本节点所记录的 framing：

> **成熟的随机物理扰动/在线生成范式 -> 发现 simulator provenance -> provenance-aware relationship supervision。**

除非后续专项 novelty search 给出新的证据，否则不再退回“Schopmans = 整个现有范式”或“我们的创新是随机扰动 / 动态生成”这两种过度简化表述。
