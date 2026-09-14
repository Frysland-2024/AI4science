# AI4Science 项目与留学申请背景交接文档

**用途：** 给另一个 AI / 留学申请顾问快速理解申请人的科研轨迹、当前项目证据、真实能力边界与适合的研究生方向。  
**版本日期：** 2026-08-07（Asia/Singapore）  
**项目仓库：** `Frysland-2024/AI4science`  
**当前导师：** 谭启  

---

## 0. 给接手 AI 的使用说明

请把下面信息分成四种状态理解，不要混淆：

- **[CONFIRMED] 已确认：** 已有正式或确认性实验支持，可以用于申请材料中的事实性叙述。
- **[PILOT] 探索性：** 有初步证据，但不能写成最终科研结论。
- **[ARCHIVED] 已封存：** 曾经认真探索，但由于机制/性能/研究聚焦原因退出当前主线；它们对“研究成长经历”有价值。
- **[PROPOSED] 未来方向：** 尚未正式完成，只能用于说明未来兴趣，不能包装成已有成果。

如果需要判断申请方向、导师匹配或项目强弱，请优先读取 GitHub 仓库最新状态；本文件是截至 2026-08-07 的人工整合快照。

---

# 1. 申请人科研定位：一句话版本

申请人并不希望把自己长期定位为“做材料实验的人，顺便用 AI”，而希望逐步成为：

> **从科学数据生成机制出发，研究 Sim-to-Real、分布偏移、结构化监督、鲁棒表示、少样本适配与科学测量数据学习的 AI4Science / Scientific ML 研究者。**

材料科学和 XRD 是当前最重要的领域锚点，但不是希望终身被锁定的边界。

长期理想身份更接近：

> **研究机器学习如何从受噪声、畸变和分布变化影响的科学测量数据中恢复可靠结构信息。**

因此在研究生申请中，最匹配的关键词包括：

- AI for Science / Scientific Machine Learning
- AI for Materials，但最好是方法型而非单纯性质预测
- AI for Characterization / Scientific Imaging / Scientific Signal Processing
- Sim-to-Real / Domain Shift / Domain Generalization
- Robust Learning / Representation Learning
- Few-shot / Transfer Learning / Data-efficient Learning
- Physics-informed / Simulator-informed Learning
- Computational Imaging / Spectroscopy / Diffraction / Microscopy

申请人对传统湿实验兴趣较低，更倾向计算、算法、科学信号与应用物理交叉方向。

---

# 2. 从 FerroAI 到当前 XRD 项目的发展主线

## 2.1 FerroAI 阶段：从“AI 能否预测材料性质”开始

最早的研究兴趣仍属于比较典型的材料机器学习范式：

> **材料结构/成分 -> 数据库或计算标签 -> 机器学习 -> 性质预测。**

这一阶段最重要的作用不是最终方法本身，而是让申请人完成了从传统材料课程走向 ML/DL 的第一次进入。

后来申请人逐渐对一种典型材料 ML 叙事产生不满足：

> DFT/实验太慢 -> 收集更多数据 -> 换一个神经网络 -> MAE 更低 -> 用于高通量筛选。

申请人开始区分两种研究范式：

1. **Materials Science enabled by ML：** ML 是更快的代理模型/筛选器；
2. **Machine Learning motivated by a scientific problem：** 科学问题暴露一个学习机制、泛化或表示问题，ML 方法本身成为研究对象。

这一步是后续 XRD 项目重构的思想起点。

---

## 2.2 XRD 初期：从“更真实的模拟”出发

XRD 项目最初面对的是一个非常现实的问题：

> 模拟 PXRD 训练出的模型，在真实实验谱上会因为峰移、峰展宽、背景、噪声、择优取向、仪器差异等因素发生严重 Sim-to-Real 域偏移。

早期思路与领域主流一致：

- 尽量模拟真实扰动；
- 扩大扰动参数范围；
- 生成更多模拟谱；
- 尽量覆盖实验域。

这一路线本身合理，但申请人逐渐意识到：

> **更多数据、更多扰动、更多覆盖，不等于模型一定学到了“稳定表示”。**

于是研究问题从“怎样造更多脏谱”转向：

> **在完全相同的数据暴露条件下，不同训练目标是否会产生不同的 OOD / Sim-to-Real 泛化能力？**

这是项目第一次真正从材料工程问题转成 ML 问题。

---

# 3. 项目核心抽象：模拟器不仅提供数据，还提供关系

当前项目最重要的概念重构是：

设一个实验/模拟谱为：

`x = g(s, m)`

其中：

- `s` = 晶体结构/结构语义；
- `m` = 测量条件与样品/仪器扰动；
- `x` = 最终观测 PXRD；
- 分类标签 `y = h(s)` 主要依赖结构，而不应依赖测量条件。

对同一个母结构 `s`，模拟器可以产生：

- `x1 = g(s, m1)`
- `x2 = g(s, m2)`

普通 Dynamic ERM 只使用“它们标签相同”这一层信息；申请人进一步意识到模拟器还提供一条更强的监督：

> **x1 与 x2 不是碰巧属于同一类，而是同一个物理对象在不同测量条件下的两个观测。**

因此项目当前最漂亮的研究叙事不是“我们用了 JS loss”，而是：

> **前人已经把在线模拟器发展为高效的数据生成器；本项目进一步把模拟器视为“物理同源关系的监督提供者”。**

当前主线尝试将这种 measurement-equivalence / parent-structure provenance 转化为显式的一致性监督。

---

# 4. 方法演化与关键失败：这是申请叙事的重要部分

## 4.1 Dynamic ERM

**研究假设：** 如果模型持续看到足够丰富的物理扰动，它会自然学到鲁棒性。

Dynamic ERM 是整个项目最重要的公共基线，不是“落后方法”。它代表：

> **只使用数据暴露，不显式约束同源视图关系。**

---

## 4.2 JS Consistency：当前唯一主方法 [CONFIRMED]

对于同一母结构动态生成的两个物理视图：

- 两者共享分类标签；
- 同时最小化预测分布之间的 Jensen-Shannon divergence。

项目的真正假设是：

> **Dynamic ERM 只通过共享标签间接鼓励扰动不变性；JS consistency 显式要求同一结构的不同测量视图保持预测稳定，使决策函数沿物理扰动轨道更加平滑。**

需要特别注意：

- JS consistency 不是申请人发明的新基础算法；
- 当前创新属于“问题驱动的方法迁移与领域适配”；
- 不能声称“首次提出一致性正则化”；
- 更稳妥的表述是：利用物理配对的动态 PXRD 视图，将 simulator provenance 转化为一致性监督。

当前 V9 已收敛为 **JS-only 主线**。

---

## 4.3 Residual Decorrelation [ARCHIVED]

受高光谱 single-source domain generalization 工作启发，项目曾探索：

> 不要求不同测量视图完全相同，而是显式建模其特征残差，并尽量让残差不携带晶系类别信息。

该思路的研究价值很高，因为它直接触及：

> **结构语义与测量因素是否可以显式解耦。**

但实验中出现了明显问题：

- residual 中确实存在类别泄漏；
- 早期对抗式去相关不稳定；
- 后续 V10 虽然增强了“测量信息可预测性”，却没有稳定去掉晶系泄漏，甚至出现更强纠缠。

因此 Residual 没有被硬救成论文主方法，而是正式封存。

**对申请最重要的意义：** 申请人能够接受“一个看起来更高级的想法不成立”，并根据机制证据主动缩小论文主线，而不是不断调参直到得到想要的结果。

---

## 4.4 PAMPT / Peak-aware Transformer [ARCHIVED]

项目曾设计较复杂的 peak-aware 1D Transformer/PAMPT，希望结合：

- 多尺度局部峰形；
- overlap patch；
- 全局 attention；
- 导数/峰先验。

但关键诊断表明：

- PAMPT Clean Train accuracy 只有约 0.638；
- 同类任务换成 1D ResNet 后，Train accuracy 可到 1.0；
- Dynamic 训练在 ResNet 上也显著恢复。

所以 PAMPT 的问题首先是 **learnability / optimization bottleneck**，而不只是泛化问题。

项目没有继续为了“架构创新感”强行保留 Transformer，而选择成熟 ResNet 作为稳定公共底座。

这产生了一个非常有潜力、但目前封存的未来问题：

> **Backbone–Augmentation Compatibility：为什么面向峰特征设计的复杂模型在动态物理扰动下反而难学，而局部卷积归纳偏置更稳定？**

该问题未来可推广到 Raman、光谱、ECG、传感器时序等一维科学信号。

---

# 5. 当前正式技术主线（V9）

截至 2026-08-07，建议另一个 AI 将项目理解为：

1. **数据源：** Materials Project 晶体结构；
2. **任务：** 七晶系分类；
3. **划分：** 结构级严格 split，避免同一母结构及其扰动版本跨 Train/Validation/Test；
4. **模拟：** 从结构/反射信息动态生成物理扰动 PXRD；
5. **公共 backbone：** 成熟 1D ResNet（替代 PAMPT）；
6. **基线：** Dynamic ERM，两条动态同源视图、相同计算和数据暴露；
7. **主方法：** Dynamic JS Consistency；
8. **冻结超参数：** JS `lambda = 60`；
9. **模拟评估：** in-range + 多种单因素 OOD + 组合 OOD；
10. **真实域：** RRUFF mineral PXRD zero-shot + few-shot adaptation；
11. **统计设计：** pretraining seed 与 few-shot episode seed 成对比较；
12. **研究治理：** Validation/Test 隔离、参数冻结、预注册、错误审计、固定步数敏感性检查。

---

# 6. 当前最重要的结果

## 6.1 JS 参数选择阶段 [CONFIRMED]

在受控 Validation 比较中：

- Dynamic ERM OOD Macro-F1 约 `0.6665`；
- JS `lambda=60` 约 `0.6997`；
- 增益约 `+0.0333`；
- in-range 也从约 `0.7140` 提升至 `0.7298`。

这说明强一致性并非简单牺牲 ID 换 OOD，而是在该受控实验中同时改善了 ID 与 OOD。

同时，`lambda=3` 与 `lambda=30` 的提升远弱于 `lambda=60`，提示可能存在正则强度阈值效应；但“阈值机制”仍只是解释假设，不应写成已证明理论。

---

## 6.2 RRUFF-301 确认性 Few-shot 实验 [CONFIRMED]

这是目前对留学申请最有说服力的实验证据之一。

### 数据与协议

- 301 条 RRUFF 实验矿物 PXRD；
- 7 个晶系，每类 43 条；
- 10/class adaptation pool，共 70；
- 33/class locked test，共 231；
- zero overlap；
- 比较 Dynamic ERM vs JS `lambda=60`；
- 5 个 pretraining seeds × 5 个 episode seeds；
- `K = 1, 2, 5` few-shot；
- frozen convolutional backbone，只训练 projection + classification head；
- primary metric = paired `Delta Macro-F1 (JS - ERM)`。

### 确认性结果

| K-shot / class | ERM Macro-F1 | JS Macro-F1 | Mean paired Delta | Positive pairs |
|---|---:|---:|---:|---:|
| K=1 | 0.2847 | 0.3280 | **+0.0433** | **21/25** |
| K=2 | 0.3026 | 0.3486 | **+0.0460** | **23/25** |
| K=5 | 0.3555 | 0.4099 | **+0.0545** | **24/25** |

总计：

> **68 / 75 个 paired comparisons 为正。**

这支持的最稳妥结论是：

> **在相同真实标签预算下，JS 预训练得到的表示比 Dynamic ERM 更容易通过少量真实实验 PXRD 适配。**

也就是说，项目的真实域贡献已经不再只是：

> “JS zero-shot 好一点。”

而更接近：

> **“显式利用模拟器同源关系，可以提高真实域 adaptation efficiency / label efficiency。”**

这比追求一个绝对高 zero-shot 准确率更适合当前数据规模和项目定位。

---

## 6.3 Zero-shot 真实域结果：有趋势，但不是最强结论 [CONFIRMED / SECONDARY]

RRUFF-301 locked test 上，5 个 pretraining seeds 平均：

- Dynamic ERM Macro-F1 约 `0.2086 ± 0.0444`；
- JS Macro-F1 约 `0.2207 ± 0.0343`。

差距较小且不同 seed 方向并不完全一致，因此：

> **不要把项目包装成“广域 zero-shot 真实 XRD 已经解决”。**

更合理的解释是：

- 中等规模模拟预训练并不足以覆盖全部真实矿物域；
- few-shot adaptation 才是当前更稳定、更有意义的主现实结论。

---

## 6.4 RRUFF 数据错误审计：一次重要的方法论经历 [CONFIRMED]

RRUFF-301 confirmatory v1 曾出现 trigonal / hexagonal 划分错误：

- RRUFF `CELL PARAMETERS` 会把 trigonal 标成 “hexagonal”；
- v1 因此出现 hexagonal=86、trigonal=0；
- 后续使用 DIF `space_group` + `pymatgen.SpaceGroup` 重建标签；
- v2 最终恢复为 43/class；
- split 重新验证为 70 adaptation + 231 locked test，零重叠。

这个错误被完整记录为 audit trail，而不是隐去。

对申请而言，这件事可以体现：

> **申请人逐渐建立了“科学数据不是普通数组，必须理解标签的物理/数据库语义”的意识。**

---

## 6.5 Monoclinic 负迁移：从“发现”到“推翻” [CONFIRMED]

RRUFF-70 小样本 pilot 曾提示：JS 在 monoclinic 上可能造成明显负迁移。

RRUFF-301 的确认性实验却显示：

- K=1: monoclinic Delta F1 = `+0.0360`
- K=2: `+0.0681`
- K=5: `+0.0691`

因此：

> **RRUFF-70 中 monoclinic negative transfer 没有复现，应视为小样本 artifact，而不是方法边界。**

这是一段很好的科研叙事：

> pilot 发现异常 -> preregister confirmatory test -> 更大样本推翻原先解释。

---

## 6.6 Calibration analysis [CONFIRMED, 但不是主贡献]

2026-08-07 已新增 calibration analysis（ECE / NLL / Brier / confidence distributions）。

在汇总 V9 evaluation panel 上：

- ERM overall ECE 约 `0.274`；
- JS60 overall ECE 约 `0.204`。

这说明 JS60 在当前 pooled evaluation 中校准误差更低，但：

- 模型整体仍明显 overconfident；
- 各 OOD profile 的 calibration 并不均匀；
- calibration 暂时更适合作为机制/可信度补充分析，而不是论文主 claim。

---

# 7. 当前项目真正已经证明了什么

最稳妥的最终研究结论可以表述为：

> **在由模拟器生成、结构语义保持不变而测量条件变化的 PXRD 分类任务中，单纯扩大动态物理数据暴露并没有完全利用模拟器提供的结构关系。通过对同一母结构的不同物理观测加入显式预测一致性约束，可以学习更适合低标签真实域适配的表示。该优势在 RRUFF-301 的预注册确认性 few-shot 实验中跨多个 pretraining seeds、episode seeds 与 K-shot 预算稳定出现。**

将 XRD 抽掉后，这个结论仍有可迁移性：

> **当科学模拟器不仅能生成样本和标签，还知道多个观测来自同一个潜在物理对象时，这种 provenance / equivalence relation 本身可以成为额外监督，并改善 domain transfer 与 label efficiency。**

这正是项目从“材料 + AI”走向“AI + scientific data”的核心桥梁。

---

# 8. 项目没有证明什么：申请时必须保持边界

另一个 AI 在帮助写 SOP / PS / Research Statement 时，请避免以下夸大：

## 不能声称

- 申请人发明了 consistency regularization；
- JS consistency 是新的通用 ML 算法；
- 已经解决所有 PXRD Sim-to-Real 问题；
- 广域 RRUFF zero-shot 已达到很高应用性能；
- Residual disentanglement 已成功；
- PAMPT / Transformer 架构优于 CNN；
- 已证明 JS 的理论阈值机制；
- 已证明 residual 就等价于真实测量因素；
- 已经完成谭启组真实陶瓷 phase-state benchmark；
- 已经是“纯机器学习算法研究者”。

## 可以声称

- 将材料表征问题重构为受控的 ML 泛化问题；
- 从 simulator provenance 中识别可利用的结构化监督；
- 建立了公平的 ERM–JS comparison；
- 用严格 split、冻结超参数、预注册和 paired multi-seed evaluation 评估方法；
- 确认 JS 预训练在真实 RRUFF few-shot adaptation 中具有稳定 label-efficiency 优势；
- 能够发现并纠正数据标签 bug；
- 能够根据证据封存失败方法，而不是围绕目标结果反向调参；
- 已经形成从材料问题中提炼 ML 研究问题的能力。

---

# 9. 这个项目最能证明的科研能力

## 9.1 问题重构能力

从：

> 怎样把模拟 XRD 做得更真实？

转成：

> 同样的数据，怎样训练才更会泛化？模拟器是否提供了未被 ERM 利用的关系监督？

这是项目最大的思维跃迁。

---

## 9.2 对科学数据语义的敏感度

项目反复遇到：

- 母结构层级数据泄漏；
- 多个扰动视图不是独立样本；
- RRUFF crystal-system 字段语义错误；
- 模拟 OOD 与真实 Sim-to-Real 不是同一个结论；
- few-shot 的独立单位应是物理样本/母结构，而不是重复扫描。

这些经历表明申请人的优势不只是“会处理数据”，而是逐渐学会：

> **数据究竟代表什么。**

---

## 9.3 实验治理意识

项目已经形成：

- 参数候选冻结；
- Validation / Test 隔离；
- 预注册；
- paired seed design；
- fairness control；
- locked test；
- audit trail；
- fixed-step sensitivity check；
- 不根据 final test 反向改方法。

这对于 AI4Science 尤其重要，因为科学数据常常样本少、来源异质且极易泄漏。

---

## 9.4 能从失败中收敛研究问题

项目不是直线成功：

- PAMPT 没学会 -> 换 ResNet，重新建立可靠底座；
- Residual 机制不成立 -> 封存；
- 弱 JS 效果小 -> 经冻结网格发现强 JS 候选；
- RRUFF-70 monoclinic 负迁移 -> 大样本确认实验推翻；
- RRUFF split bug -> 修复、重跑、保留 audit trail。

这段过程非常适合用于申请里的“research maturity”叙事。

---

# 10. 申请时最合适的科研身份

## 最推荐的主定位

> **AI4Science / Scientific ML，重点关注科学测量数据中的 domain shift、simulator-informed supervision、robust representation 与 few-shot transfer。**

## 第二层定位

> **AI for Characterization / AI + XRD / diffraction / spectroscopy / microscopy / scientific imaging。**

## 可以继续保留的材料身份

> **AI4Materials methods / materials informatics with a methodological focus。**

但需要避开那种只有：

> structure/composition -> property -> 换模型提精度

的纯工具型材料 ML 路线。

---

# 11. 最适合的导师画像

另一个 AI 在帮忙筛导师时，应优先找：

## A. ML / Scientific ML 主导师

研究关键词：

- robust ML
- representation learning
- domain adaptation/generalization
- transfer/few-shot learning
- scientific machine learning
- simulator-based learning
- uncertainty / trustworthy AI
- multimodal or scientific data

并且愿意把材料、物理、医学、遥感或工业测量作为验证场景。

## B. AI + 表征 / 科学测量

例如：

- XRD / electron diffraction
- TEM / STEM / 4D-STEM
- Raman / spectroscopy
- computational imaging
- inverse problems
- signal reconstruction
- instrument calibration
- autonomous characterization

理想组织结构是：

> **ML/信号处理主导师 + 材料/物理表征合作方。**

## C. Applied Physics + ML

如果研究问题围绕：

- 科学信号；
- 物理生成机制；
- inverse problem；
- imaging；
- dynamical systems；
- ML for measurement；

也非常匹配。

---

# 12. 相对不匹配的方向

除非导师本人有强方法线，否则不建议把申请重点放在：

- 传统湿实验材料合成；
- 以制备、烧结、配方优化为主的实验室；
- 单纯 DFT surrogate / property prediction；
- 只追求材料筛选吞吐量的 ML；
- 需要大量湿实验但 AI 只是辅助分析的组；
- 纯理论 ML 且要求申请人已经具备很强学习理论/优化推导背景的组（可冲刺，但不是当前最自然的主池）。

---

# 13. 当前研究生路线（供另一个 AI 继续评估）

截至当前对话，申请人主要考虑：

1. **美国直博**：高上限冲刺；
2. **加拿大 direct-entry PhD**：少量高冲刺；
3. **加拿大 MASc**：非常重要的研究型硕士主池；
4. **Technion MSc**：研究型、材料/物理/ML 交叉特色池；
5. **日本传统硕士**：东大/京大/大阪/东北/Science Tokyo/NAIST 等按导师匹配分层；
6. **日本本科直博例外**：OIST、SOKENDAI 五年一贯制博士可单独作为直博池研究。

上述路线的具体招生政策、导师是否招生、奖学金和 2027 Fall 时间线，请接手 AI 重新联网核验，不要把本文件当作招生政策事实来源。

---

# 14. 当前未来研究方向：只能作为兴趣，不是既有成果

## 14.1 Tan Lab / GTIIT 钙钛矿功能陶瓷真实域 [PROPOSED]

公共数据库对铁电/功能陶瓷相态识别数据不足，opXRD 审计最终为 NO_GO。

项目曾据此提出一个更自然的未来真实域：

> GTIIT / Tan Lab 钙钛矿功能陶瓷 XRD，做 few-shot phase-state / phase-coexistence recognition。

候选任务包括：

- single phase；
- polymorphic coexistence；
- secondary phase；

或数据不足时先做 single-phase vs multiphase。

但该阶段必须先满足独立物理样品数量、标签可靠性与材料家族泄漏控制，因此目前不能写成已完成结果。

---

## 14.2 Peak-token / physics-aware Transformer [PROPOSED / ARCHIVED IDEA]

申请人长期对一个问题感兴趣：

> 科学信号是否应当先被转成“物理 token”，再交给 Transformer，而不是把连续强度点直接当 token？

例如：

`XRD -> peak extraction -> peak tokens (2theta, intensity, FWHM, d-spacing...) -> Transformer -> crystal representation`

这个想法来自对传统 XRD 人工分析流程的观察：人类也往往先把连续信号转换成峰、d-spacing、晶格关系等物理对象。

目前不应继续扩展进本科主论文，但非常适合作为未来硕士研究兴趣。

---

## 14.3 Backbone–Augmentation Compatibility [PROPOSED]

PAMPT vs ResNet 的失败/成功差异暴露一个更一般的 ML 问题：

> 不同模型的归纳偏置是否与物理增广的几何结构相容？

这一问题可能从 PXRD 迁移到 Raman、光谱、ECG 和其他一维科学信号。

---

# 15. 申请材料里最值得讲的“成长故事”

最推荐的叙事不是：

> “我做了一个 XRD 分类器，准确率提高了。”

而是：

> **我最初从典型材料机器学习的性质预测与高通量思路进入 AI。进入 XRD 后，我先沿用‘模拟得更真实、生成更多扰动’的传统思路解决 Sim-to-Real，但逐渐发现数据覆盖并不等价于稳定表示。于是我开始把同一母结构的不同测量视图看作具有物理同源关系的观测，并将研究问题重构为：模拟器是否不仅能生成训练样本，还能提供结构化监督？我用严格控制的数据暴露比较 Dynamic ERM 与 consistency learning，经历了 PAMPT 学习失败、Residual 解耦失败、真实数据标签 bug 和 pilot 结论被确认性实验推翻等过程，最终在 RRUFF-301 的预注册 few-shot 实验中观察到 JS 预训练在 68/75 个配对比较中带来正增益。这个过程让我确认，自己真正想研究的不是某一种材料，而是 AI 如何利用科学数据的生成机制，在分布偏移和少量真实标签下学习可靠表示。**

这段故事比“本科生原创了一个新算法”更可信，也更适合研究型硕士/博士申请。

---

# 16. 对申请强度的现实解释

## 这个项目已经足够证明

- 能独立推进一个完整 AI4Science 项目；
- 能从领域问题抽象出 ML 问题；
- 有比较成熟的实验设计和数据治理意识；
- 具有 Sim-to-Real / OOD / few-shot / representation learning 的实际经验；
- 适合申请偏 ML 的交叉研究型硕士；
- 可以作为直博申请中的核心 research story，尤其当有较强推荐信、论文/预印本/代码成果配合时。

## 这个项目还不足以单独证明

- 已达到纯 ML 顶会方法研究者水平；
- 已有扎实学习理论或优化理论原创能力；
- 已有大规模系统/分布式训练能力；
- 已经能与顶级 CS 本科生在所有通用 ML 方向正面竞争。

因此，申请策略最好不是完全抛弃材料背景，而是利用它建立一个稀缺接口：

> **材料/物理生成机制 + ML 方法问题。**

---

# 17. 给接手 AI 的建议任务

如果你是下一个帮申请人做留学规划的 AI，建议按以下顺序继续：

1. **把申请人定位成 AI4Science / scientific data ML，而不是传统材料学生。**
2. 以 GitHub 最新仓库为 source of truth，必要时检查 `CURRENT_STATE / PROJECT_JOURNEY / reports`。
3. 按国家分别搜索真正匹配的导师，而不是只按学校排名：
   - 美国 PhD；
   - 加拿大 MASc / direct-entry PhD；
   - Technion MSc；
   - 日本 MSc；
   - OIST / SOKENDAI 直博。
4. 导师筛选时优先判断：
   - 研究问题是否以 ML 为主体；
   - 是否处理 scientific data / measurement / simulation；
   - 是否允许跨材料到更广 AI4Science；
   - 是否需要大量湿实验；
   - 是否有学生做 OOD / transfer / representation / uncertainty / scientific imaging。
5. 把项目的失败、收敛与确认性实验当作优势，不要把它们删除成一条“从第一天就知道答案”的假直线。
6. SOP 中不要把创新写成“发明 JS”，而要写成“从 simulator provenance 中识别结构化监督，并严谨验证其 transfer value”。
7. 如果评估直博竞争力，应单独结合：GPA、课程、推荐信、论文状态、英语、研究经历深度和导师匹配；不能只看这个项目的模型分数。

---

# 18. 关键证据锚点（截至 2026-08-07）

## GitHub

Repository: `Frysland-2024/AI4science`

关键近期 commits：

- `24d8c8511bdea9df8b52cdf779b04420bebffafc`  
  RRUFF-301 confirmatory v2 + representation analysis + v1 audit trail；68/75 positive pairs，K=1/2/5 Macro-F1 Delta 约 +0.043 / +0.046 / +0.055。

- `a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`  
  calibration analysis：ECE / NLL / Brier / confidence distributions。

- `385cbbc9e1897e73f0828ca589e279edcf17bf75`  
  RRUFF-70 exploratory few-shot evidence archive + RRUFF-301 preregistration。

- `2cb656c0a1dd32ac4aa7aabfeb1ca1c747242c35`  
  RRUFF pipeline smoke test + Tan Lab domain redefinition；更新 project journey。

- `2ede4f62a52d7905bef323b35c8a5086186e4b30`  
  opXRD ferroelectric feasibility audit parser 修复后仍确认 NO_GO。

## 项目发展相关内部记录

- `材料机器学习的惯性.txt`
- `这个对话的思路很完整，看这个就好了。我是语音输入的.txt`
- `ResNet实验进展.txt`
- `XRD精修与AI协作.txt`
- `AI4Materials 评价分析.txt`
- `分支 · AI4science 项目汇总.txt`

这些文件最适合用于恢复“为什么项目会从 FerroAI 走到现在”的思路历史。

---

# 19. 最后给另一个 AI 的一句话

请不要只问：

> “这个学生会不会 XRD？”

更应该问：

> **“这个学生是否已经开始学会从一个科学测量问题中识别可迁移的机器学习问题，并用可信实验验证它？”**

截至 2026-08-07，答案已经从“有这个倾向”发展到：

> **是的，而且 RRUFF-301 的确认性 few-shot 结果已经给了这条研究身份转换一组相当具体的证据。**
