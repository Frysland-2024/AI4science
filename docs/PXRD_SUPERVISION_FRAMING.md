# PXRD 项目当前一级定位：监督学习与同源关系监督

**状态：当前有效**  
**日期：2026-09-29**  
**作用：** 统一 README、论文、技术报告与后续公开说明中的项目定位。

## 1. 一句话定位

> **本项目是 PXRD 七晶系监督学习方法研究：利用在线模拟器保留的母结构 provenance，把同一晶体结构在不同测量条件下生成的谱视为 measurement-equivalent views，并将这种同源关系转化为额外监督。**

项目的核心问题不是“给谱加扰动以后性能掉多少”，而是：

> **同一个晶体数据库和同一个模拟器，除了提供类别标签与更多合成样本，还能否提供样本之间的物理关系，并把这些关系用于训练一个更好的分类器？**

## 2. 方法层级

### 一级任务：监督分类

基础任务始终是 (x\rightarrow y)：(x) 是 PXRD 谱，(y) 是七晶系标签。Dynamic ERM 使用普通类别监督。

### 额外监督：same-parent relationship supervision

对于同一母结构 (s)，在线模拟器可生成 (x_1=g(s,m_1)) 与 (x_2=g(s,m_2))。两条谱不仅具有同一晶系标签，更重要的是它们来自**完全相同的母结构**。

因此模拟器提供两层信息：

1. 类别标签；
2. 母结构同源关系。

本项目使用 JS prediction consistency，把第二层信息显式加入监督目标。

### 方法贡献

> **把 simulator 从 data generator 扩展为 data generator + relationship supervisor。**

这意味着项目重点不是“生成更多谱”，而是**从已有科学数据生成过程中提取更多监督信息**。

## 3. “提高数据库利用效率”应该怎样表述

推荐：supervision efficiency、data utilization efficiency、extracting additional supervision from simulator provenance、provenance-aware relational supervision、measurement-equivalence supervision。

不推荐把它简单写成 “database efficiency”，因为项目没有优化数据库读取、存储或查询速度。

最准确的中文是：

> **提高已有晶体结构数据库的监督信息利用效率。**

也就是从“一个结构只提供类别标签”，扩展为“一个结构同时提供类别标签与多个同源测量视图之间的关系监督”。

## 4. 结果如何描述

1. **模拟域分类与 OOD 泛化提高**：冻结 Test 中 Macro-F1 / Accuracy 提升；
2. **真实域标签效率提高**：RRUFF-301 的 K=1/2/5 few-shot learning curve 整体更高；
3. **独立真实来源的 zero-shot 相对表现提高**：CNRS-318 五个 matched seeds 同方向；
4. **概率质量改善**：ECE / NLL / Brier 与分类指标同向；
5. **结构耦合扰动收益尤其明显**：broadening / texture 的增益较大。

这些是**方法产生的实验结果与泛化证据**，不是项目的一级学科标签。

## 5. 当前推荐标题

英文：**Measurement-Equivalence Supervision from Simulator Provenance for PXRD Classification**

中文：**利用模拟器母结构同源关系监督的 PXRD 七晶系分类**

## 6. 当前推荐研究叙事

晶体结构数据库 → 在线物理模拟 → 保留 parent provenance → 构造 same-parent measurement-equivalent views → 关系监督 → 更充分利用同一数据库 → 更好的分类、跨域泛化与少标签适配。

> **前人已经把在线模拟器发展为高效的数据生成器；本项目进一步利用模拟器已知的母结构来源，把它发展成关系监督的提供者。**

## 7. 术语规则

当前项目介绍、论文摘要、技术报告、README 和对外口述优先使用：supervised learning、structured / relational supervision、simulator provenance、parent identity、measurement equivalence、consistency regularization、data / supervision efficiency、OOD generalization、sim-to-real transfer、few-shot adaptation / label efficiency。

不要再把整个项目的一级定位写成某种“扰动抵抗能力研究”。

## 8. 项目标签分层：以后必须按层级使用

### 8.1 一级标签：项目“是什么”

只保留两个：

- **Supervised Learning / 监督学习**
- **PXRD Crystal-System Classification / PXRD 七晶系分类**

这是项目本体。任何对外介绍都应先从这里开始。

### 8.2 二级标签：方法“做了什么改变”

推荐：

- **Structured Supervision / 结构化监督**
- **Relational Supervision / 关系监督**
- **Simulator-Provenance Supervision / 模拟器来源关系监督**
- **Measurement-Equivalence Supervision / 测量等价关系监督**
- **Consistency Regularization / 一致性正则化**

其中前四项描述的是方法思想，JS consistency 描述具体实现。不要反过来把“JS”本身写成项目一级身份。

### 8.3 三级标签：项目“在哪些设置下被验证”

这些可以使用，但只能作为实验设置或结果维度：

- **OOD generalization**：模拟未见扰动条件下的泛化；
- **Sim-to-Real transfer**：模拟训练到真实实验谱的迁移场景；
- **few-shot adaptation / label efficiency**：仅对应 RRUFF K=1/2/5 真实域适配子实验；
- **zero-shot cross-domain evaluation**：对应 CNRS-318；
- **probabilistic calibration / reliability**：对应 ECE / NLL / Brier 分析。

它们回答的是“方法在哪些条件下有效”，不是“项目属于什么学习范式”。

### 8.4 四级标签：更大的应用与学科背景

可以用于更广泛的研究方向介绍，但不能替代方法定义：

- **AI4Science / Scientific ML**
- **AI for Characterization / AI + 表征**
- **Materials Informatics / AI4Materials**（宽泛背景）

推荐顺序是：

> **AI4Science / AI for Characterization → supervised learning → PXRD classification → relational supervision → JS consistency → OOD / Sim-to-Real / few-shot results**

### 8.5 不再作为当前项目一级标签的词

以下词不是“完全错误”，但不能再用来定义整个项目：

- **robust learning / robustness research**：最多描述扰动条件下的结果性质；
- **representation learning**：可以讨论 learned representation 的分析结果，但当前方法没有显式以 representation-learning objective 为核心；
- **domain adaptation**：只适用于使用目标域标签的 RRUFF few-shot 子实验，不适用于整个主线，更不适用于 CNRS zero-shot；
- **domain generalization**：可以描述特定未见域评测，但不是项目一级身份；
- **physics-informed ML**：容易让人理解为显式物理方程/约束进入优化；当前主线更准确的是 **physics-guided data generation + provenance-aware supervision**；
- **computer vision / CV**：当前输入是 1D PXRD 科学信号，使用 ResNet 不会自动把项目变成 CV；
- **semi-supervised / self-supervised / contrastive learning**：当前主线不属于这些范式。

### 8.6 判断新标签能否使用的规则

以后任何新标签先问四个问题：

1. **它描述的是训练监督来源，还是只描述某个评测？**
2. **它是否对应当前 loss / data / task 的真实改变？**
3. **如果把某个结果表删掉，这个标签是否仍然成立？**
4. **它是不是因为“用了某种模型/指标”才被贴上的？**

只有真正描述任务或训练机制的词，才能升级为项目一级/二级标签。

---

## 9. 代码目录说明

当前代码仍位于 `xrd_robustness/`。这是历史技术目录名，继续保留以避免破坏 Python import、CLI、冻结配置、结果路径、旧 commit/report 链接与复现实验记录。

**目录名不再决定学术 framing。**
