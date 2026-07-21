# ChatGPT「科研」项目记忆导出

导出日期：2026-05-15  
项目名称：科研  
主要方向：FerroAI / ferroelectric phase diagram prediction / AI for materials / 模型审计与数据幻觉

> 说明：这份文件不是平台后台的完整原始聊天记录导出，而是根据当前项目上下文中可见的“项目记忆、重要对话摘要、上传文件、研究决策、阶段性结论”整理出的工作档案。它适合保存到本地，例如：`C:\Users\81504\FerroAI\chatgpt_project_memory.md`。

---

## 0. 当前最重要的一句话

你的研究已经从“复现 FerroAI”转向了一个更清楚、更有价值的方向：

> **以 FerroAI 为案例，研究材料 AI 在相图预测中的可靠性、失效模式、数据幻觉与模型表征问题。**

其中，FerroAI 不只是一个工具，而是一个非常适合做 AI for Science 审计的对象：它能稳定输出“像相图”的结果，但这些结果未必已经构成可靠的材料知识。

---

## 1. 用户身份与当前阶段

- 用户身份：学生。
- 当前阶段：主要在考虑硕士申请与科研方向积累。
- 当前核心诉求：
  - 找到一个既能和导师/学长项目衔接，又能形成自己长期能力的研究方向。
  - 不只是“帮学长搬砖”，而是争取能够学习到核心能力的分工。
  - 通过 FerroAI 项目建立以后做 AI for Materials / AI for Science 审计 / 图像与材料数据智能分析的基础。

---

## 2. 总体研究方向演化

### 2.1 早期问题

最开始关注的是：

- FerroAI 能不能复现？
- 为什么 BaTiO3、PZT、PbTiO3 等体系的预测结果与预期不一致？
- 复现失败到底是不是用户自己的操作问题？
- 官方 release 文件、论文描述、GUI 演示之间是否存在调用协议差异？

### 2.2 中期转向

后来逐渐从“复现是否成功”转向：

- 公开 release artifact 是否和论文中描述的模型完全一致？
- 模型输入协议、scaler、PCA/embedding、keras/h5 文件结构是否有隐藏差异？
- 公开模型是否存在可以系统追踪的预测偏差？
- 这些偏差能否用模型内部表征或决策层解释？

### 2.3 当前主线

当前主线已经比较明确：

> **FerroAI 是一个材料 AI 数据幻觉的案例。它可以输出看起来合理的相图，但这些输出是否代表可靠材料知识，需要被审计。**

更深一层：

> **数据幻觉不只是标签错误或数据集不干净，而是材料知识的表示形式与材料知识成立条件之间存在错位。**

也就是说，模型学到的是：

```text
composition + temperature -> phase label
```

但真实材料相图成立依赖的是：

```text
结构稳定性 / 自由能景观 / 相变机制 / 实验条件 / 文献证据 / 测量方法
```

这两者之间的错位，正是 FerroAI 容易产生“像知识但未必是知识”的根本原因。

---

## 3. 对 FerroAI 论文/模型的核心理解

### 3.1 论文声称的模型任务

FerroAI 论文的核心任务是用 AI 预测铁电材料的 composition-temperature phase diagram。

论文中模型大致流程：

1. 用 NLP 从大量文献中提取相变信息。
2. 构建 phase transformation dataset。
3. 通过数据增强转换成 augmented crystal dataset。
4. 用化学组成向量 + 温度作为输入。
5. 输出晶体对称性类别。
6. 拼接不同温度/成分点的分类结果，形成相图。

### 3.2 FerroAI 数据来源与规模

当前文件与论文中反复出现的关键信息：

- 文本挖掘约 41,597 篇研究文章。
- 编译出 2,838 个 phase transformations。
- 涉及约 846 个铁电材料体系。
- 数据主要来自 Elsevier 文献。
- 论文中宣称模型可预测多种铁电体系相图，并指导发现新材料。

### 3.3 模型结构

论文描述中的模型结构：

- 六层深度神经网络。
- 输入：chemical vector + temperature。
- 输出：crystal symmetry。
- hidden layers：Dense 512 ReLU，多层。
- output：Softmax。
- 输出类别包含 cubic, tetragonal, orthorhombic, monoclinic, rhombohedral, triclinic, hexagonal 等。

### 3.4 关键疑点

你已经敏锐发现并反复讨论过的疑点：

1. 论文说 chemical vector 是 118 维元素向量，但公开 release 的调用协议似乎并不完全透明。
2. 公开模型文件表面上是 `.keras`，但实际可能具有 h5 结构特征。
3. 官方 GUI / 本地调用生成软件 可能使用了额外封装流程，和单独下载模型直接调用不完全等价。
4. release artifact、论文叙述、GUI 输出之间可能存在“版本鸿沟”或“调用协议鸿沟”。
5. 因此，复现不一致不应简单归因于用户操作错误。

---

## 4. 已经形成的核心判断

### 4.1 审计公开 release model 是有意义的

即使无法保证你调用方式和作者完全一致，直接审计公开 release model 仍然有意义。

理由：

- 公开 release model 本身就是其他研究者可获得、可使用的工件。
- 如果公开模型的行为与论文叙述或 GUI 展示不一致，这本身就是 AI for Science 可复现性问题。
- 研究对象可以从“论文中的理想 FerroAI”转变为“公开 artifact 版本 FerroAI”。
- 这不是攻击作者，而是研究公开科学工件的可靠性边界。

适合使用的表述：

> This work audits the publicly released FerroAI artifact rather than making claims about the inaccessible internal training version.

中文理解：

> 我们审计的是公开发布的 FerroAI 工件，而不是断言作者内部训练版本一定有同样问题。

### 4.2 复现失败未必是用户自己的问题

已经检查/讨论过的点包括：

- 官方 tscaler / cscaler 的使用。
- 模型文件本体结构。
- keras/h5 兼容性。
- hash 或文件等价性检查。
- double-softmax 的调用错误。
- dense_softmax 输出模式。
- raw logits 与 softmax 概率的区别。

当前判断：

> 一部分问题确实可能来自调用方式，但很多偏差不能简单解释为“用户不会用模型”。更合理的说法是：公开 artifact 存在不透明调用协议和行为边界，需要系统审计。

---

## 5. 目前已经做过/讨论过的技术检查

### 5.1 环境与文件检查

你已经围绕以下问题做过很多检查：

- Anaconda 环境配置。
- Spyder 中运行脚本。
- 官方模型文件是否可正常读取。
- `.keras` 文件本质是否为 h5。
- WSL 下检查模型结构。
- hash 检验文件等价性。
- scaler 文件是否使用正确。
- 输出文件为何没有生成图像/表格。
- Conda 启动命令。
- 如何保证每次打开 Anaconda 仍在同一个环境。

### 5.2 double-softmax 问题

之前一个关键坑是 double-softmax。

修正后：

- 文件中明确写成 `output_mode: dense_softmax`。
- 所谓 logits 恢复成真正 raw logits 的形状。
- 例如 PbTiO3 在高温时 cubic logit 很高，softmax 后 cubic 概率接近 1。
- 在 300 K 附近 tetragonal 概率占优，说明模型并非普遍无法输出 tetragonal。

意义：

> PbTiO3 成为一个重要对照，说明公开模型不是简单地“压不出 tetragonal”，而是某些体系存在特定偏差。

### 5.3 BaTiO3 问题

BaTiO3 是当前反复关注的核心案例之一。

重点问题：

- BaTiO3 经典相序包含 C-T-O-R 等转变。
- FerroAI 对 BaTiO3 可能出现 T/O 缺失或被 cubic 吞掉的情况。
- 论文中作者也提到过 small fraction of tetragonal and orthorhombic structures are recognized as cubic or other symmetries，并将其可能归因于 marginal differences in lattice parameters。

你的关键追问：

> 为什么这种识别错误会被归结到 lattice parameter 的差距上？

这说明你已经从结果对错进入到“作者解释是否成立”的层面。

### 5.4 PbTiO3 问题

PbTiO3 的意义是：

- 它证明模型可以输出 tetragonal。
- 它可以作为“非普遍性错误”的对照组。
- 如果 BaTiO3 出现 T/O 缺失，而 PbTiO3 正常，这说明问题更可能来自体系表征、训练分布、相邻相边界或决策层偏置，而不是简单输出层坏掉。

### 5.5 PZT / PMN-PT 等 Pb 系材料

此前讨论过：

- PZT、PbTiO3、PMN-PT 可能在 embedding 或 PCA 特征空间中聚集。
- 这可能导致它们共享某些异常预测偏见。
- 需要通过潜在特征空间聚类来验证。

---

## 6. 当前建议的分析框架

### 6.1 不只是 Top-1，而是概率景观

不要只看每个温度点的 top-1 phase label。

更好的方法：

- 画出全温区 7 个相类别的概率曲线。
- 看相变点附近不同类别概率如何竞争。
- 判断某个相是完全没被模型识别，还是概率曾经抬头但被 cubic/rhombohedral 压制。

这被称为：

```text
Probability Landscape
```

用途：

- 解释 T/O 缺失是“完全无信号”还是“信号被决策边界压掉”。
- 从分类结果深入到模型不确定性。
- 比单点 Top-1 更像真正的模型审计。

### 6.2 潜在特征空间聚类

另一个建议动作是：

```text
Embedding Clustering / Latent Space Clustering
```

做法：

- 利用模型中间层或 PCA vector。
- 把不同体系在 0K 或关键温度下的特征点投影到 2D。
- 使用 PCA / t-SNE / UMAP 观察聚类。

预期意义：

- 观察 BaTiO3、PbTiO3、PZT、PMN-PT 等是否聚在一起。
- 判断模型是否根据元素组成而非真实相变机制形成分类偏置。
- 为“表征侧归因”提供证据。

### 6.3 表征侧归因 vs 决策侧归因

你已经问过这两个概念。

简化解释：

#### 表征侧归因

关注模型在中间层如何“理解”材料。

问题是：

- BaTiO3 在模型内部被放到了哪里？
- 它和哪些材料被认为相似？
- 模型是否把本该不同的体系压缩到相近区域？

#### 决策侧归因

关注模型最后如何做分类决定。

问题是：

- T 相概率有没有出现？
- O 相概率有没有出现？
- 为什么最后 top-1 变成 cubic？
- 相变点附近是不是几个类别概率接近？

### 6.4 数据幻觉框架

你后来提出的方向是：

> 以 XRD / SEM 作为载体，研究 AI 能否在真实杂乱数据中整理出简洁有效的结论。

这个方向和 FerroAI 的区别在于：

- FerroAI 是从 composition + temperature 直接预测 phase label。
- 你的未来方向更可能是从真实实验数据中提取结构化信息。
- 重点不是让 AI 直接“生成答案”，而是让 AI 帮助整理证据、降低噪声、形成可审计结论。

这可以自然延伸为：

> AI-assisted evidence extraction and reliability auditing for materials characterization data.

---

## 7. 当前导师给出的任务目标

你已经和导师谈过方向调整。

导师当前给出的目标大致是：

> 排查 FerroAI 模型中哪些材料体系是有问题的。

具体要求/方向：

- 不是只盯一个 BaTiO3。
- 需要排查大约 30–50 个材料体系。
- 通过网络和文献搜集证明模型是否有问题。
- 文献数量可能需要 100–200 篇。
- 在此基础上，找出一两个典型问题体系，继续做深入分析或优化。
- 时间线最好在 8 月前完成。

这说明你的项目已经不是“随便试模型”，而是具有比较明确的 audit pipeline 方向。

---

## 8. 你当前最该争取的项目分工

你之前问过：如果参与学长工作，为了学到核心技能，最该争取什么分工？

建议的核心分工不是简单跑图，而是：

### 8.1 争取“证据链构建”分工

包括：

- 找文献。
- 提取真实相序。
- 记录实验测量方法。
- 判断 phase labels 是否可靠。
- 把文献信息整理成结构化 truth table。

这是项目的根基。因为 FerroAI 审计不是只看模型输出，而是看模型输出和可靠证据之间的关系。

### 8.2 争取“模型行为诊断”分工

包括：

- 跑不同材料体系的预测。
- 画 probability landscape。
- 看 top-1 相序、概率变化、边界位置。
- 对比真实相序与模型相序。
- 记录 failure mode。

### 8.3 争取“失效归因”分工

包括：

- 判断错误是训练数据缺失、相标签压缩、边界不确定、结构相似性、元素表征不足，还是调用协议问题。
- 进一步做 embedding / latent space 分析。
- 对典型体系写成小案例。

### 8.4 不建议只做的分工

相对不建议只做：

- 机械下载文献。
- 单纯复制运行脚本。
- 只做漂亮相图。
- 只整理结果而不参与判断标准。

因为这些工作不够核心，难以形成你以后可迁移的能力。

---

## 9. 推荐形成的能力结构

如果你想通过这个项目为以后积累经验，最该学会的不是某一个软件，而是下面几类能力。

### 9.1 材料证据判断能力

你要学会判断：

- 什么样的文献相图可信？
- DSC、XRD、介电温谱、Raman、SEM 等证据各自能说明什么？
- phase boundary 是直接测量、拟合、推断还是经验标注？
- 相序中哪些点是硬证据，哪些只是作者解释？

### 9.2 数据结构化能力

你要学会把论文内容变成机器可读数据：

```json
{
  "system": "BaTiO3",
  "composition": "...",
  "temperature_range": "...",
  "phase_sequence": "C-T-O-R",
  "evidence_type": "DSC/XRD/dielectric",
  "source": "paper DOI",
  "confidence": "high/medium/low"
}
```

这会成为你以后做材料 AI 的关键能力。

### 9.3 模型审计能力

你要学会问：

- 模型在哪些体系对？
- 哪些体系错？
- 错误有没有模式？
- 错误是否集中在某些相、某些元素、某些温区、某些材料家族？
- 这个模型是真的学到物理，还是学到文献分布？

### 9.4 AI for Materials 的问题意识

你的长期优势可以是：

> 不只是会用 AI，而是知道 AI 输出在材料科学中什么时候不可信，以及如何建立证据链去审计它。

---

## 10. 关于 LAMMPS / 传统模拟 / AI 方向的判断

你问过是否有必要了解 LAMMPS。

当前建议：

- 你可以了解 LAMMPS 是什么，但暂时不必深挖。
- 如果你的主线是 FerroAI 审计、材料数据幻觉、XRD/SEM 图像整理，那么 LAMMPS 不是最优先。
- 传统模拟更关注从势能、结构、相互作用出发推导性质。
- 你当前 AI 方向更关注数据之间的关系、证据结构和模型可靠性。

可以这样理解两者区别：

```text
传统模拟：从物理机制出发，计算材料行为。
AI 审计/数据方向：从数据表达出发，判断模型是否把数据关系误当成材料规律。
```

这不是说 AI 方向比模拟浅，而是二者的核心问题不同。

---

## 11. 关于“AI 幻觉”的会议总结思路

你听到 Chenbo Zhang 报告中的 “AI hallucination” 后，形成了一个重要思路。

核心总结是：

- 只靠数据集训练寻找规律的 AI 必然会面临幻觉风险。
- 提高数据集干净程度是一项有效方法，也是工作者追求。
- 但更深的问题是：AI 到底有没有通过某种方式学到物理意义？
- 如果 AI 学的是 interaction / energy landscape 等机制性对象，离物理更近。
- 如果 AI 学的是 composition + temperature -> phase label，则更容易产生“像知识”的输出。

你后来希望写入文段的重点是：

> 相比于某些直接学习物理相互作用或能量景观的 AI 模型，FerroAI 更接近一种从成分和温度到相标签的统计映射。因此，它的预测结果虽然可能具有经验有效性，但更需要通过实验文献和模型审计来确认其物理可靠性。

---

## 12. 你对未来方向的表述

你提出过一个很重要的未来方向：

> 以 XRD / SEM 作为载体，研究 AI 能否帮助我们在真实杂乱数据中整理出简洁有效的结论。

我对这个方向的判断是：

- 这个方向比“单纯调用一个模型预测相图”更有长期价值。
- 它和你现在做 FerroAI 审计是连续的。
- FerroAI 让你看到 AI 生成材料知识的风险。
- XRD/SEM 数据整理则可以让你进一步研究 AI 如何从真实证据中提取知识。
- 二者共同指向：AI for Materials 的可靠性、证据链和知识生成。

可以作为未来研究方向的表达：

> My broader interest is to develop and audit AI methods that extract reliable materials knowledge from noisy experimental data, using characterization data such as XRD and SEM as evidence carriers.

---

## 13. 当前工作流建议

### 13.1 总体 pipeline

建议你当前项目按以下步骤推进：

1. 固定公开 FerroAI artifact 的调用方式。
2. 建立材料体系清单，目标 30–50 个。
3. 对每个材料体系生成模型预测相序/概率曲线。
4. 对每个体系搜集文献证据。
5. 将文献相序整理成 reviewed truth。
6. 比较 model prediction vs reviewed truth。
7. 标记 failure type。
8. 选择 1–2 个典型 failure system 深入归因。
9. 写成 audit case study。

### 13.2 建议的数据表字段

```text
ID
material_family
formula/system
composition_range
temperature_range
predicted_sequence
predicted_boundaries
probability_landscape_available
literature_sequence
literature_boundaries
experimental_method
reference_DOI
evidence_confidence
match_status
failure_type
notes
```

### 13.3 failure type 可暂定

```text
Correct / Mostly correct / Boundary shift / Missing phase / Extra phase / Wrong sequence / Over-smoothed phase boundary / Cubic swallowing low-symmetry phase / Uncertain due to literature ambiguity
```

---

## 14. 已讨论过的“failure map”问题

你曾经质疑：为什么一定要搞 failure map？

更准确的理解是：

- failure map 本身不是目的。
- 它只是把零散错误变成可分析模式的一种工具。
- 如果只是为了画一张图而画 failure map，意义不大。
- 但如果它能帮助回答“模型在哪些材料家族/相类别/温区失效”，它就有价值。

你后来更倾向于：

> 与其泛泛做 failure mode，不如回到模型内部，对 BaTiO3 的 T/O 缺失做表征侧和决策侧归因。

这个判断是合理的。

更有价值的题目可能是：

> A model-behavior audit of FerroAI: from missing phases to representation-level diagnosis.

---

## 15. 已上传/项目相关文件清单

当前项目上下文中可见的文件包括：

### FerroAI 相关

- `s41524-025-01778-0.pdf`  
  npj Computational Materials 版本 FerroAI 论文。

- `ferro AI.pdf`  
  FerroAI 论文相关 PDF。

- `FerroAI_A_Deep_Learning_Model_for_Predicting_Phase-1.pdf`  
  arXiv 版本 FerroAI 论文。

- `README.md`  
  Hugging Face 模型卡/说明文件，说明 model、tscaler、cscaler、GUI 等。

- `FerroAI_model.keras`  
  公开模型文件。

- `FerroAI_cscaler.pkl`  
  chemical formula scaler。

- `FerroAI_tscaler.pkl`  
  temperature scaler。

- `LICENSE`  
  许可证文件。

- `gitattributes`  
  Git/LFS 相关文件。

### 压电/铁电背景资料

- `Li et al. - 2020 - Piezoelectricity—An important property for ferroel.pdf`
- `压电陶瓷简单介绍_20230914_v3.pdf`
- `Advanced Ceramics in Piezo Applications压电陶瓷原理及应用_CeramTec赛琅泰克.pdf`

### 培训/学习资料

- `机器学习与材料模拟的培训.md`

内容包括：

- 第一性原理计算介绍。
- DFT、HF、MD、VASP、ASE、Pymatgen、GPAW。
- Linux / Python / Anaconda。
- 机器学习基础。
- 随机森林、交叉验证、F1、特征重要性。
- CGCNN、Matbench、DeePMD、CHGNet。
- 对材料模拟 + 机器学习结合路线的思考。

### 图片

- `IMG_7999.jpeg`
- `ec325624-2012-4072-87ef-68721b4dde5d.png`

---

## 16. FerroAI README / 模型卡中的关键信息

README 中说明：

- 模型名称：FerroAI。
- 论文：npj Computational Materials, 2025, 11, 282。
- model：主模型文件。
- tscaler：temperature scaler。
- cscaler：chemical formula scaler。
- 开发者：Chenbo Zhang, Xian Chen。
- 提供 FerroAI-GUI。
- GUI 宣称可以快速生成超细相图，帮助定位 MPB。
- 使用时需要承认研究用途并正确引用。

这支持了你之前关于“公开模型文件 + scaler + GUI 之间可能存在封装差异”的关注。

---

## 17. 材料模拟培训笔记中对你方向有帮助的内容

你培训笔记中的关键思想：

1. 机器学习材料研究通常需要大量结构化数据。
2. 材料模拟可以比实验更快地产出大量数据，因此常被用来训练模型。
3. 如果实验数据作为训练来源，关键问题是：
   - 任务是分类还是回归？
   - X 是什么？Y 是什么？
   - 数据是否规范？
   - 数据是否真的与目标性质相关？
4. 如果要做实验 + AI：
   - 要么让实验产生大量有意义数据。
   - 要么用模拟 + AI 得出规律，再用实验验证。
   - 要么实验发现现象后，用模拟解释微观机制。
5. 你特别关心：能否用已有预训练模型生成 PNN-PZ-PT 等体系的相图，以及预测偏离化学计量数或焦绿石相风险。

这些笔记和 FerroAI 方向的关系：

> 它帮助你意识到，AI 模型是否有价值，不取决于它能不能输出图，而取决于训练数据、目标变量和材料问题之间是否真的对齐。

---

## 18. 项目中的重要表达储备

### 18.1 中文表达

- 模型审计
- 公开工件审计
- 复现性鸿沟
- 调用协议不透明
- 数据幻觉
- 材料知识的表示形式
- 材料知识的成立条件
- 表征侧归因
- 决策侧归因
- 概率景观
- 潜在特征空间
- 相标签压缩
- 文献证据链
- 真实相序 / reviewed truth
- 失效模式
- 缺相 / 吞相
- cubic 吞掉 tetragonal/orthorhombic

### 18.2 英文表达

- model audit
- artifact audit
- publicly released artifact
- reproducibility gap
- invocation protocol
- phase label prediction
- data hallucination
- evidence-aware audit pipeline
- representation-side attribution
- decision-side attribution
- probability landscape
- latent feature space
- embedding clustering
- reviewed truth
- missing phase
- phase swallowing
- tetragonal/orthorhombic phases being recognized as cubic
- composition-temperature phase diagram
- phase sequence object
- morphotropic phase boundary, MPB

### 18.3 你在会议上可用的问题表达

> I am doing some audit work on the publicly released FerroAI model.

> In my reproduction, BaTiO3 seems to show missing tetragonal or orthorhombic regions. Could this be related to the limitation mentioned in the paper, where tetragonal and orthorhombic structures may be recognized as cubic?

> Why is this misclassification attributed to marginal differences in lattice parameters?

---

## 19. 当前应避免的坑

### 19.1 不要把问题说成“作者错了”

更稳妥说法：

> 公开模型工件在某些材料体系上的行为与文献相序或论文叙述存在不一致，需要进一步审计。

### 19.2 不要只凭一个体系下结论

BaTiO3 很重要，但不能只靠 BaTiO3 得出大结论。

需要：

- PbTiO3 做正对照。
- PZT / PMN-PT / KNN / BZT-BCT 等做横向比较。
- 30–50 个体系形成系统图景。

### 19.3 不要只做 top-1

Top-1 容易误导。

要看：

- probability landscape。
- 相变点附近类别竞争。
- low-symmetry phase 的概率是否曾经出现。

### 19.4 不要陷入纯工程修 bug

工程修 bug 是必要的，但你的研究价值不在“终于跑通代码”。

真正价值在：

> 公开 AI 模型如何在材料知识生成中产生可信或不可信的结果。

---

## 20. 下一阶段最具体的任务清单

### 20.1 本周/近期

1. 固定当前可复现的 FerroAI 调用脚本版本。
2. 确认 scaler、输出模式、softmax 处理全部无误。
3. 对 BaTiO3、PbTiO3、PZT 画 probability landscape。
4. 整理这三个体系的文献相序作为小型 truth table。
5. 写一个 1–2 页内部报告，说明：
   - 调用协议；
   - 已排除的问题；
   - 当前观察到的模型行为；
   - 下一步扩展到 30–50 体系的计划。

### 20.2 中期

1. 建立 30–50 个材料体系清单。
2. 每个体系至少对应 2–4 篇文献证据。
3. 建立 reviewed truth JSON/CSV。
4. 自动生成 prediction vs truth 对照表。
5. 分类 failure mode。

### 20.3 深入方向

从横向排查中选择 1–2 个典型体系：

- BaTiO3：T/O 缺失，适合做 missing phase / cubic swallowing 分析。
- PbTiO3：可作为模型能识别 tetragonal 的对照。
- PZT：MPB 与 Pb 系材料聚类分析。
- KNN 或 BZT-BCT：可作为 lead-free 对照体系。

---

## 21. 你当前研究的潜在题目

### 21.1 中文题目

- FerroAI 公开模型的相图预测可靠性审计
- 铁电材料相图预测模型中的数据幻觉与失效模式分析
- 面向材料 AI 的证据感知模型审计：以 FerroAI 为例
- 从缺相现象到表征归因：FerroAI 在铁电相图预测中的可靠性边界

### 21.2 英文题目

- Reliability Audit of the Publicly Released FerroAI Model for Ferroelectric Phase Diagram Prediction
- Data Hallucination in AI-Predicted Ferroelectric Phase Diagrams: A Case Study of FerroAI
- Evidence-Aware Auditing of AI for Materials: From Missing Phases to Representation-Level Diagnosis
- Model Behavior Analysis of FerroAI: Probability Landscapes, Missing Phases, and Latent Representations

---

## 22. 最重要的个人判断

你现在的方向是成立的，而且比单纯复现 FerroAI 更有价值。

原因是：

1. 你抓到的是 AI for Science 的核心问题：模型输出是否真的等于科学知识。
2. 你不是停留在“模型错了”，而是在问“为什么错、错在哪里、能否归因”。
3. 你已经有导师给出的明确任务：排查问题体系。
4. 你正在形成一套可迁移能力：文献证据链 + 模型审计 + 失效归因。
5. 这条路可以自然延伸到 XRD/SEM 等真实实验数据的 AI 辅助分析。

一句话总结：

> 你现在不是在做一个小模型的小 bug，而是在学习如何判断 AI 生成的材料知识是否可靠。这是一个很值得继续推进的方向。

---

## 23. 文件保存建议

建议将本文件保存为：

```text
C:\Users\81504\FerroAI\chatgpt_project_memory.md
```

也可以继续拆成：

```text
project_memory.md
research_direction.md
ferroai_audit_plan.md
literature_truth_table_template.md
```

---

## 24. 后续使用方式

以后开启新对话时，可以直接上传或粘贴本文件，然后说：

> 这是我 FerroAI 项目的项目记忆，请基于这个继续帮我推进。

这样可以减少上下文丢失，也能避免重复解释已经完成的工作。

