# 材料模拟（Materials Simulation）与材料信息（Materials Informatics）的区分

**状态：** 当前研究方向判断规则  
**用途：** 用于理解研究方向、筛选导师/课题组、判断一个“AI+材料”项目究竟偏向传统计算材料还是数据驱动材料研究。  
**说明：** 这是一套工作性分类，不是要求所有课题只能落入一个学科标签。现实中存在大量混合方向。

---

## 1. 最重要的区分

判断一个课题属于“材料模拟”还是“材料信息”，**不要只看它有没有使用机器学习，也不要只看标题里有没有 AI**。

真正需要看的是：

> **研究的核心计算范式是什么？AI / 数据方法是主方法，还是只是传统物理模拟流程中的辅助工具？**

可以简化成：

```text
材料模拟：
物理模型 / governing equations
        ↓
数值求解
        ↓
材料行为 / 性质

材料信息：
材料数据 / 表征数据 / 模拟数据
        ↓
统计学习 / 机器学习 / AI
        ↓
预测、分类、反演、发现、决策
```

---

## 2. 材料模拟是什么

这里的“材料模拟”主要指以**物理模型和数值求解器**为核心的计算材料研究。

典型方法包括：

- DFT / first-principles calculation；
- Molecular Dynamics (MD)；
- Monte Carlo；
- phase-field；
- finite-element / continuum simulation；
- electronic-structure calculation；
- thermodynamic / kinetic simulation；
- multiphysics simulation。

其典型逻辑是：

```text
已知物理规律 / 能量模型 / 控制方程
                ↓
构建计算模型
                ↓
数值求解材料体系
                ↓
得到能量、结构、输运、相变、力学等结果
```

这类方向的核心能力通常是：

- 物理建模；
- 数值方法；
- HPC；
- 计算材料理论；
- 对特定尺度的材料行为进行 forward simulation。

### 即使加入 AI，也不一定变成材料信息

例如：

- 用神经网络加速 DFT；
- 用 ML surrogate 替代昂贵的相场计算；
- 用神经网络势函数跑更大的 MD；
- 用 ML 预测 DFT 计算的能量，以减少计算次数。

这些工作当然属于 AI4Science，但如果科研问题仍然主要是：

> **如何更快、更大规模、更精确地完成原本的材料模拟？**

那么它的主线仍然更接近 **materials simulation / computational materials**。

---

## 3. 材料信息是什么

“材料信息”更接近 **Materials Informatics / data-driven materials science**。

它的核心对象不是“把控制方程求出来”，而是：

> **怎样从已有材料数据中提取规律、建立预测关系、完成识别/反演/发现/决策。**

数据可以来自：

- 实验；
- 材料表征；
- 数据库；
- 文献；
- 高通量计算；
- 物理模拟器；
- 多种数据源的组合。

典型任务包括：

- property prediction；
- classification；
- representation learning；
- materials discovery / screening；
- inverse design；
- spectroscopy / diffraction / microscopy analysis；
- defect detection；
- process–structure–property learning；
- uncertainty / active learning；
- multimodal materials data analysis。

其典型逻辑更像：

```text
材料数据
   ↓
特征 / representation
   ↓
ML / DL / statistical model
   ↓
预测 / 分类 / 反演 / 发现
   ↓
材料问题解释或决策
```

这里 AI / 数据建模本身通常就是研究方法的核心组成部分。

---

## 4. 模拟数据不等于“材料模拟”

这是一个很容易混淆的点。

> **使用模拟器生成数据，不意味着研究本身就是材料模拟。**

例如当前 PXRD 项目：

```text
晶体结构
   ↓
PXRD forward simulator
   ↓
大量带 provenance 的模拟谱
   ↓
机器学习分类 / relationship supervision
   ↓
真实域与 OOD 评价
```

这里确实存在物理模拟器，但研究问题不是：

> 怎样把 PXRD forward simulation 做得更精确？

而是：

> 怎样利用模拟器产生的数据及其 provenance，为机器学习提供更有效的监督信息？

因此其主要范式属于：

> **materials informatics / AI for characterization / scientific machine learning on measurement data**

而不是传统意义上的 materials simulation。

模拟器在这里是：

> **data-generation / supervision infrastructure**

而不是最终研究对象。

---

## 5. 一个非常实用的判断问题

面对一个导师、实验室或论文时，可以问：

> **如果把机器学习模块拿掉，这个组的主要科研问题还基本成立吗？**

### 情况 A

去掉 ML 后，核心仍然是：

- 算电子结构；
- 跑 MD；
- 做相场；
- 求 PDE；
- 研究第一性原理性质。

那么通常说明：

> **materials simulation 是主线，AI 是工具。**

### 情况 B

去掉 ML 后，核心任务本身就失去了主要方法，例如：

- 从 XRD 自动识别结构；
- 从 microscopy 自动检测缺陷；
- 从 spectroscopy 反演材料参数；
- 从实验数据库学习结构–性能关系；
- 多模态材料数据预测；
- 数据驱动 inverse design。

那么通常说明：

> **materials informatics / AI for materials 是主线。**

---

## 6. 混合区：不能只靠标签判断

有一些方向天然位于两者之间。

### ML interatomic potentials

例如 MACE、NequIP、DeepMD。

它们使用 ML，但主要目标通常是构建高精度势能面，从而进行更大尺度原子模拟。

因此更接近：

> **AI-enhanced atomistic simulation**

而不是典型的数据分析型 Materials Informatics。

### 高通量 DFT + ML

如果工作重点是：

```text
大量 DFT → 数据库 → ML property prediction / screening
```

它可能真正跨入 Materials Informatics。

但如果是：

```text
ML → 减少 DFT 计算成本 → 继续做第一性原理研究
```

则仍明显偏 computational materials。

### AI-driven inverse design

如果核心是从目标性质反推结构/组成，通常明显偏 Materials Informatics。

但若整个 inverse design 的主体仍依赖大规模物理求解与优化，则属于交叉区，需要看实际工作内容。

---

## 7. 对研究方向筛选的实际含义

对于当前希望发展的路线，不能使用：

> “这个导师做材料 + AI，所以就匹配”

这种过宽标准。

应该进一步判断：

### 优先匹配

- AI for materials characterization；
- XRD / spectroscopy / microscopy + ML；
- scientific measurement + machine learning；
- inverse problems；
- data-driven metrology；
- defect / structure recognition；
- multimodal characterization；
- experimental-data-driven materials informatics；
- simulation-to-experiment learning；
- scientific computer vision / signal learning（有明确材料或物理对象）。

### 需要具体判断

- materials discovery；
- high-throughput materials screening；
- graph neural networks for materials；
- generative materials design；
- ML-assisted computational materials；
- digital twin / surrogate modeling。

这些方向既可能偏 Materials Informatics，也可能实际上是 computational materials。

### 明显偏离当前主线

如果一个课题组的主要产出长期集中在：

- pure DFT；
- electronic structure；
- traditional MD；
- phase-field；
- continuum / FEM；
- thermodynamic simulation；

即使偶尔有 ML 论文，也不能仅凭“用了 AI”把它判断为材料信息方向。

---

## 8. 与“计算材料”的关系

“计算材料（computational materials science）”是更大的概念，Materials Simulation 通常属于其中。

Materials Informatics 也可以和计算材料发生重叠，但不能简单画等号：

```text
Computational Materials Science
├── physics-based simulation
│   ├── DFT
│   ├── MD
│   ├── phase-field
│   └── continuum simulation
│
└── data-driven / informatics methods
    ├── ML property prediction
    ├── materials databases
    ├── inverse design
    └── AI-assisted discovery
```

因此判断个人研究路线时，应看**实际范式**，而不是只看院系名称中是否写着“计算材料”。

---

## 9. 当前路线的定位

当前 PXRD 工作更合理的位置是：

```text
AI4Science
└── AI for Characterization / Materials Informatics
    └── PXRD measurement learning
        ├── supervised classification
        ├── simulator provenance
        ├── relationship supervision
        ├── OOD / sim-to-real evaluation
        └── few-shot experimental adaptation
```

它和 materials simulation 有联系，因为使用了物理 forward simulator。

但它的核心不是：

> **模拟一个材料体系本身。**

而是：

> **利用材料测量与模拟产生的信息，让机器学习模型更有效地理解表征数据。**

---

## 10. 最终判断口诀

以后判断一个所谓 “AI + Materials” 方向，可以依次问：

1. **研究对象是什么？** 材料物理过程，还是材料数据 / 测量？
2. **核心方法是什么？** 求解物理模型，还是学习数据关系？
3. **AI 在哪里？** 是辅助传统模拟，还是承担主要推断任务？
4. **最终输出是什么？** 一次材料模拟结果，还是预测 / 分类 / 反演 / 筛选模型？
5. **如果去掉 AI，这个组的主线是否基本不变？**

一句话总结：

> **不要用“有没有 AI”区分材料模拟和材料信息，要用“科研问题的主要推理引擎是什么”来区分。**


## 11. 方向进一步明确：XRD 是起点，不是终点（2026-10-05）

当前长期目标不是把研究身份锁定在 XRD / PXRD 本身，也不是简单从 XRD 平移到 XPS/XAS。

更准确的目标是：

> **以 XRD/PXRD 为第一个训练场，逐步进入更大的 scientific measurement / AI for Characterization / data-driven metrology 世界。**

理想扩展路径包括：

```text
XRD / PXRD
→ spectroscopy
→ electron microscopy / STEM / CL
→ X-ray CT / tomography
→ multimodal characterization
→ inverse / reconstruction / uncertainty / active measurement
```

因此未来判断课题和导师时，不应只问：

> “和现在的 XRD 项目像不像？”

还必须问：

> **“这个环境能否让已有的 measurement-learning 能力迁移到更多计测模态与更一般的逆问题？”**

### 新的优先级含义

- **谱学连续性**是优点，但不是最高目标；
- **跨模态 measurement science 能力**更重要；
- 优先学习可迁移的方法：inverse problems、reconstruction、signal/image learning、uncertainty、measurement correction、active measurement、multimodal fusion；
- XRD 是申请叙事中的起点和方法证明，不应成为未来研究边界。

一句话：

> **不是“做 XRD 的人”，而是“从 XRD 出发做 AI for Measurement / Characterization 的人”。**
