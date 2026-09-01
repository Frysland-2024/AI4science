# PXRD 方法新颖性：文献谱系与正式 framing

**记录日期：** 2026-09-01  
**状态：** 当前分类项目的正式写作口径；用于 Introduction、Related Work、PPT、答辩与申请材料。  
**边界：** 本文档固定“如何定位已有范式与本项目增量”，不宣称已经完成穷尽式 first/novelty search。

## 1. 最终核心判断

当前最稳妥的历史叙事不是：

> “Schopmans 提出了动态生成，我们在此基础上做 JS。”

也不是：

> “本项目发明了随机物理扰动或训练时动态生成。”

而是：

> **随机采样物理合理扰动、生成多样化 PXRD 训练谱，本身已经是一条较成熟的 PXRD-ML 范式；其中部分工作进一步采用训练时 on-the-fly 在线生成。Schopmans et al. (2023) 是其中与本项目非常接近的代表性实现。当前项目的增量不是发明随机扰动，而是进一步利用生成过程中天然已知的“同一母结构”关系。**

这意味着本项目应被描述为对既有 augmentation / synthetic-generation 范式的**继承与精进**，而不是对前人路线的否定。

---

## 2. 现有范式应该怎么概括

### 推荐主标题

> **现有范式：随机采样物理扰动，生成多样化训练谱**

### 推荐副标题

> 已有工作通过峰移、展宽、噪声、择优取向、背景等物理合理随机变化，使计算谱覆盖更多实验条件并提高模型对真实测量变化的鲁棒性。

### 推荐流程图

```text
              晶体结构
                  ↓
        随机采样物理 / 测量扰动
                  ↓
          生成不同的训练谱
                  ↓
              模型训练
```

这个表述刻意把两件事区分开：

1. **stochastic / physics-informed augmentation**：随机采样物理合理扰动，生成更多不同训练谱；
2. **on-the-fly generation**：在训练期间持续重新生成，而不是只使用预先固定的数据池。

并非所有使用随机扰动的工作都属于严格意义的 training-step on-the-fly generation，因此不要把整个历史范式写成“前人都在训练时动态生成”。

---

## 3. 代表性文献谱系

当前写作至少可以依赖以下几篇代表性工作来说明这条路线已经形成清楚的历史谱系：

### Oviedo et al., npj Computational Materials, 2019

使用 physics-informed data augmentation 处理薄膜 XRD，小数据条件下通过随机峰强变化、消峰、2θ 平移等方式扩充训练分布。

**在本项目叙事中的角色：** 很早的直接先例，支持“随机采样物理合理的 XRD 变化来生成训练样本”并非本项目首创。

### Szymanski et al., Chemistry of Materials, 2021

通过 physics-informed perturbations 模拟实验制样与测量中的变化，并考虑固溶体、择优取向等效应。

**在本项目叙事中的角色：** 支持“测量与样品条件变化应进入模拟训练分布”的成熟性。

### Lee et al., Advanced Intelligent Systems, 2023

大规模构造包含 peak shift、broadening、texture、background/noise 等扰动的合成 PXRD，并在其文献回顾中系统梳理此前的 peak-parameter randomization、texture/strain augmentation、experiment-derived perturbation、physics-informed augmentation 等路线。

**在本项目叙事中的角色：** 最适合证明这不是 Schopmans 单篇论文孤立提出的做法，而是一条已经被多篇工作发展的 perturbation / augmentation 路线。

### Schopmans et al., Digital Discovery, 2023

将 synthetic crystal generation 和 PXRD simulation 嵌入训练过程，形成 continuous / on-the-fly generation；训练时持续产生新的 synthetic crystals 与 diffractograms，而不是依赖固定训练集。

**在本项目叙事中的角色：** 与当前 online generation 形式最接近的直接方法学前驱。

推荐在 PPT 底部写：

> **Representative precedents: Oviedo et al. (2019); Szymanski et al. (2021); Lee et al. (2023); Schopmans et al. (2023).**

并单独给 Schopmans 加小注：

> *Schopmans et al. further adopted continuous on-the-fly generation during training.*

### 其他 supporting literature

本轮文献讨论还整理了 Chitturi et al. (2021)、CPICANN (2024)、end-to-end structure determination (2024)、以及后续 experiment-informed augmentation 工作等候选 supporting precedents。它们可以用于扩充 Related Work，但在正式论文写出“first / no prior work”之前，应逐篇核验原文与训练实现，不把当前讨论直接等同于穷尽式 novelty search。

---

## 4. 本项目真正的增量

已有 augmentation / online-generation 工作主要把 simulator 当成：

> **data generator**

即：

```text
crystal structure
      ↓
physical perturbation / simulator
      ↓
more diverse labeled PXRD patterns
      ↓
training
```

但当 simulator 从同一个母结构 `s` 生成两个不同测量 realization：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

它天然还知道一条普通单样本标签之外的信息：

> **x1 与 x2 来自同一个 underlying / parent crystal structure。**

二者并不只是“碰巧属于同一个晶系”，而是同一个 latent physical object 在不同测量条件下的观测。

因此 simulator 同时提供：

1. **label supervision**：每个 view 的晶系标签；
2. **provenance / relational supervision**：哪些 views 来源于同一个 parent structure。

Dynamic ERM 主要使用第一层：

```text
x1 -> y
x2 -> y
```

本项目进一步使用第二层：

```text
             同一母结构 s
              ↙       ↘
       扰动计算谱 A   扰动计算谱 B
             ↓         ↓
           p_A         p_B
              ↘       ↙
          JS consistency
              ↓
       两次判断保持一致
```

因此真正的角色升级是：

```text
simulator = data generator
                 ↓
simulator = data generator + relationship supervisor
```

推荐概括为：

> **from data generation to provenance-aware relational supervision**

或：

> **from scalable synthetic data generation to simulator-provided measurement-equivalence supervision**

---

## 5. P2 / P3 的正式 PPT framing

### P2 — 前人已经做什么

标题：

> **现有范式：随机采样物理扰动，生成多样化训练谱**

正文只需要表达：

- 真实实验 PXRD 会受到峰移、展宽、择优取向、背景、噪声等影响；
- 代表性工作已经通过随机物理扰动扩展合成训练分布；
- 部分工作进一步采用 on-the-fly 生成，持续扩大训练数据支持集。

不要把 P2 写成“Schopmans 的方法”单篇论文介绍，也不要把离线 augmentation 描述成落后或错误路线。

### P3 — 本项目多用了什么信息

标题：

> **我的改进：不仅生成不同的谱，还利用“它们来自同一结构”这一关系**

核心视觉：

```text
same parent structure
      ↙        ↘
   view A     view B
      ↓        ↓
    pred A    pred B
       ↘      ↙
      consistency
```

底部一句：

> **前人主要利用“更多样的训练谱”；本工作进一步利用生成过程天然提供的“同一母结构关系”。**

---

## 6. Introduction / Related Work 推荐句式

### 中文

> **已有工作主要利用随机物理扰动增加训练谱的多样性；我们进一步利用生成过程天然已知的同源结构关系，将其转化为学习约束。**

更完整版本：

> 物理扰动增强已经成为提高合成 PXRD 训练数据多样性与实验适用性的重要路线，训练时在线生成又进一步解除固定合成数据集的规模限制。在此基础上，我们注意到模拟器不仅生成带标签样本，还保留每个观测对应的母结构来源。因而，同一母结构在不同测量条件下生成的谱可以被视为同一个潜在物理对象的 measurement-equivalent views。我们将这一 provenance 转化为一致性监督，并在严格匹配的数据暴露和训练条件下检验这种关系监督是否能进一步提高鲁棒性。

### English

> **Prior work mainly uses stochastic physical perturbations to increase the diversity of synthetic diffraction data; we additionally exploit the provenance of generated views—knowing that they originate from the same underlying crystal structure—as a learning constraint.**

更完整版本：

> Physics-informed perturbation has become a common strategy for increasing the diversity and experimental realism of synthetic PXRD training data, while on-the-fly generation further removes the limitation of a fixed synthetic dataset. Building on this paradigm, we exploit an additional form of information retained by the simulator: the provenance that multiple perturbed observations originate from the same parent crystal structure. We treat these observations as measurement-equivalent views and use their shared provenance as relational supervision during training.

---

## 7. 不应该怎么说

以下说法默认禁止用于正式稿件和汇报：

- “我们首次提出随机扰动 XRD 训练数据。”
- “现有 XRD 方法都是固定离线数据集。”
- “Schopmans 就是整个前人范式。”
- “我们发明了 on-the-fly PXRD generation。”
- “我们发明了 JS consistency。”
- “前人忽略了同源关系”——除非完成专门的 novelty search 后有足够证据；当前更稳妥的说法是“existing generation formulations create an additional opportunity to exploit parent-structure provenance”。

更成熟的语气应该是：

> **前人已经把物理扰动与在线生成做成了可靠的数据构建范式；本项目继续追问生成过程还能提供什么监督信息。**

---

## 8. 当前 novelty 边界

当前已经有充分依据支持以下定位：

> **本项目的增量不是 stochastic augmentation 本身，而是把 simulator-retained parent identity / provenance 显式转化为 measurement-equivalence consistency supervision。**

但目前仍不应该无条件写：

> “This is the first PXRD work to use same-parent consistency.”

正式 first/novelty claim 之前，应单独检索并核验至少以下关键词族：

```text
PXRD / XRD
+ same-parent / same-structure / paired-view / multi-view
+ consistency / invariant / Siamese / contrastive
+ simulator provenance / synthetic pairs
```

只有在这一专项 novelty search 完成后，才决定是否使用 “first” 或 “to our knowledge”。

---

## 9. 与项目发展史的关系

这一 framing 是项目方法认知的一次重要收敛：

```text
早期：怎样把模拟谱做得更真实、更多？
      ↓
动态生成：训练过程中持续暴露更多物理扰动视图
      ↓
进一步认识：生成器不仅知道 label，还知道 parent identity
      ↓
当前主线：把 parent provenance 转化为 relationship supervision
```

因此，以后申请文案描述 XRD 项目的发展过程时，应突出：

> **研究重点从“扩大数据覆盖”推进到了“理解并利用模拟器生成过程中蕴含的监督结构”。**

这比“把一个 JS loss 搬到 XRD”更准确地反映项目的思想演化。
