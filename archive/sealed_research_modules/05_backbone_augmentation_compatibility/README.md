# 封存研究模块 05：模型归纳偏置与物理增广相容性

**英文工作名：Backbone–Augmentation Compatibility in Scientific One-Dimensional Signals**  
**副标题：为什么面向峰特征设计的复杂模型没有学进去，而简单 ResNet 反而能够从动态增广中受益？**

> **状态：SEALED / FUTURE RESEARCH**  
> **封存日期：2026-07-28**  
> **当前作用：保存研究问题、证据链、机制假设、验证方案和潜在解决方向，不进入当前 V9 正式实验矩阵。**  
> **重要边界：本模块不宣称已经解释 PAMPT 失败的机制，也不宣称 Transformer 不适合 XRD。当前只确认出现了一个值得研究的 backbone–augmentation interaction。**

---

## 0. 为什么要独立封存这个模块

本模块来自当前 XRD 项目一次非常关键的失败诊断。

项目早期选择 PAMPT，不是为了追逐 Transformer 热点，而是因为它看上去具有合理的领域先验：多尺度卷积提取局部峰形，导数信息提示峰边缘，patch token 与 attention 建模远距离峰间关系，希望比普通 CNN 更“懂峰”。

但正式诊断显示：

- PAMPT 在 Clean 条件下连训练集都没有充分拟合；
- 在相同数据、相同任务和相同 100 epoch / 61,600 step 预算下，成熟的 ResNet-18-GN 明显优于 PAMPT；
- 当 backbone 换成 ResNet 后，原先表现不佳的 Dynamic ERM 不仅没有继续崩溃，反而同时提高了最小扰动、训练范围扰动和单因素 OOD 表现；
- 因此，问题已经不能简单解释为“动态扰动太强”“数据管线坏了”或“XRD 分类本身学不会”。

这使项目产生了一个比“再换一个模型”更偏机器学习的问题：

> **为什么加入更多领域先验、更复杂的 peak-aware attention 模型，反而不如具有局部卷积归纳偏置的简单 ResNet？**

这个问题涉及：

- inductive bias；
- tokenization；
- augmentation compatibility；
- optimization dynamics；
- sample efficiency；
- representation continuity；
- domain knowledge 何时帮助、何时伤害学习。

它可以由 XRD 提供高度可控的科学信号试验场，但结论有可能推广到 Raman、IR、质谱、ECG、传感器时序等其他一维科学信号。因此，它是目前五个封存方向中最偏纯机器学习、也最适合作为未来硕士研究起点之一的模块。

---

## 1. 问题是怎样被发现的

### 1.1 最初的默认判断

当 PAMPT Dynamic ERM 表现较低时，最初怀疑的对象主要是：

1. 动态扰动联合分布过难；
2. 训练时间不足、学习率过小或 scheduler 不合适；
3. max normalization、谱图分辨率或弱峰损失；
4. 数据划分过严；
5. 晶系本身存在较强类别重叠。

这些都是合理嫌疑，但当时没有证据确定哪一项是主因。

### 1.2 排障思想的形成

项目随后把混乱的问题拆成多个 Gate：

1. **Clean Gate**：模型在最小扰动谱上到底能不能学会基础晶系任务；
2. **训练预算 Gate**：Dynamic 是否只是没有训练够；
3. **Backbone Gate**：换成熟 CNN 后是否恢复；
4. **输入与渲染 Gate**：只有多个 backbone 都失败时，才检查分辨率、归一化、标签和渲染。

这套顺序的核心原则是：

> **每个实验只回答一个问题，不同时修改 backbone、优化器、预处理和扰动。**

### 1.3 关键转折

Foundation Gate 3 给出了决定性现象：PAMPT 与 ResNet 在同一 Clean 任务上出现明显差距。随后，ResNet Dynamic ERM 又出现大幅恢复。

于是项目的解释发生变化：

> 早期 Dynamic 表现不佳，不再主要指向“动态增广范式有毒”，而更可能指向 backbone 的可学习性、归纳偏置和增广相容性。

---

## 2. 当前证据链

以下全部是 **development-only Validation evidence**。它们支持提出研究问题，但不能直接当成机制结论。

### 2.1 数据划分和泄漏审计已通过

当前 parent-structure split：

- Train：9,842 个独立母结构；
- Validation：2,109；
- Test：2,109；
- 总计：14,060；
- 每个母结构及其全部 clean / weak / strong / ID / OOD 视图只属于一个 split；
- zero parent leakage；
- zero material leakage；
- 七个晶系均在每个 split 中存在；
- 最大类别比例偏差为 0.000379。

这排除了“同一结构不同谱跨集合泄漏”造成的虚高，也说明当前验证差距是真实的跨母结构泛化问题。

### 2.2 PAMPT Clean 没有充分拟合训练集

在固定 100 epoch / 61,600 optimizer steps 下：

| Backbone | Train accuracy | level0 Macro-F1 | Mean single-factor OOD Macro-F1 |
|---|---:|---:|---:|
| PAMPT-B3 | 0.638494 | 0.532749 | 0.289676 |
| ResNet-18-GN | 1.000000 | 0.652168 | 0.403163 |

level0 Macro-F1 差值：

\[
0.652168-0.532749=+0.119419
\]

最关键的不是 Validation 高了约 0.12，而是：

> **PAMPT 连训练集都只学到约 0.64，而 ResNet 可以完整拟合。**

因此 PAMPT 首先表现为 learnability / optimization bottleneck，而不只是普通的过拟合或 OOD 泛化不足。

### 2.3 ResNet Clean 的受控 A/B/C 诊断没有找到更好的简单修复

在 ResNet 上只允许三个预注册、单因素 Clean 诊断：

| 方案 | 唯一变化 | level0 Macro-F1 | 结果 |
|---|---|---:|---|
| Baseline | identity + AdamW + constant LR | 0.652168 | 保留 |
| A | sqrt preprocessing | 0.645539 | 未通过 |
| B | Adam | 0.620014 | 未通过 |
| C | warm-up + cosine | 约 0.6108 | 未通过 |

固定选择阈值为 baseline + 0.02，即 0.672168。三项都没有达到阈值，因此停止第四次 Clean 搜索。

这条证据的意义不是“所有优化问题都已排除”，而是：

- 当前 ResNet baseline 足够稳定；
- 不应继续无限调 backbone；
- 简单的预处理、optimizer 和 scheduler 改动无法解释当前核心现象；
- 后续比较应该冻结公共底座，而不是持续追分。

### 2.4 ResNet Dynamic ERM 明显成功

ResNet Dynamic ERM 最佳 checkpoint：epoch 80 / step 49,280。

| 指标 | ResNet Clean | ResNet Dynamic | Dynamic − Clean |
|---|---:|---:|---:|
| level0 Macro-F1 | 0.652168 | 0.719724 | +0.067555 |
| in-range Macro-F1 | 0.182722 | 0.717942 | +0.535220 |
| mean single-factor OOD | 0.403163 | 0.656316 | +0.253153 |
| worst-class F1 | 0.495017 | 0.580952 | +0.085936 |

Dynamic 的 Train accuracy 约 0.9984，level0 与 in-range 之间只差约 0.00178。

这说明：

1. 当前动态扰动流并不必然导致模型崩溃；
2. 在成熟 CNN 上，它可以成为有效正则化；
3. 它不仅提高扰动鲁棒性，也提高了 clean-like level0 泛化；
4. 早期低性能更可能来自 backbone 与动态训练的交互，而不是动态增广概念本身。

### 2.5 类别层面的剩余困难

ResNet Dynamic 的 per-class F1：

- triclinic：0.7405；
- monoclinic：0.5810；
- orthorhombic：0.6262；
- tetragonal：0.7496；
- trigonal：0.6621；
- hexagonal：0.7587；
- cubic：0.9200。

这说明：

- 高对称 cubic 相对容易；
- monoclinic、orthorhombic 等类别仍存在结构重叠或跨结构泛化困难；
- 输入与任务本身并非毫无难度；
- 但这种难度不能解释 PAMPT 的训练集拟合失败，因为 ResNet 已经能把 Train 学到接近 1.0。

---

## 3. 当前能够说什么，不能说什么

### 3.1 当前可以说

> **PAMPT 是当前 V9 Foundation 的主要 learnability bottleneck；ResNet 与当前动态扰动训练具有更好的相容性。**

> **已经观察到明显的 backbone–augmentation interaction。**

> **更复杂、更“领域感知”的模型并未自动带来更好的学习或鲁棒性。**

### 3.2 当前不能说

- 不能说 Transformer 天然不适合 XRD；
- 不能说 peak-aware 表示一定错误；
- 不能说 PAMPT 只因为数据少而失败；
- 不能说 PAMPT 只因为 optimizer 不合适而失败；
- 不能说 ResNet 已达到任务上限；
- 不能说 Dynamic 与 PAMPT 的精确因果机制已经识别；
- 不能把不同训练预算的结果伪装成完全匹配的正式方法比较；
- 不能把开发集诊断写成最终 Test 或真实谱结论。

---

## 4. 机制假设树

以下全部是待检验假设，不是已证明结论。

### H1：胡浩天提出的“杀鸡用牛刀”假设——数据统计结构可能并不需要 Transformer

与胡浩天交流时，他提出一种很直接的解释：

> **XRD 的数据结构可能相对简单，使用 Transformer 属于“杀鸡用牛刀”。**

这句话需要精确解释，不能理解成“XRD 科学问题简单”。更合理的机器学习表述是：

> 当前七晶系分类任务中的主要可用统计规律，可能主要由局部峰形、相邻峰组合、峰间距和层级局部模式构成；成熟卷积网络已经拥有与这些规律高度匹配的 inductive bias，而全局 attention 的额外自由度没有提供足够边际收益，反而增加了样本复杂度与优化负担。

可能机制：

1. CNN 天然具有局部连接、权重共享和一定平移容忍度；
2. Transformer 需要从数据中重新学习“局部相邻点应该相关”；
3. 当前只有 9,842 个独立训练母结构，可能不足以可靠学习更自由的全局关系；
4. XRD 的长程峰间关系虽然存在，但七晶系分类可能不需要对所有谱区做 dense all-to-all interaction；
5. PAMPT 的额外 attention、guided branch 和 token aggregation 可能增加方差和优化难度，却没有增加当前任务真正需要的信息。

关键边界：

> “杀鸡用牛刀”是假设 **模型复杂度与任务统计复杂度不匹配**，不是否定衍射物理的复杂性。

#### 可证伪预测

- 参数量匹配后，小 CNN 仍优于 Transformer；
- 增加 attention 层不会稳定提高结果；
- 仅使用 CNN stem + 简单分类头就能达到大部分性能；
- 随训练结构数量增加，PAMPT 不一定明显追上；
- ResNet 的性能/计算比持续优于 PAMPT。

若 PAMPT 随数据规模扩大明显追上或反超，则该假设需要改写为“Transformer 更吃数据”，而不是“任务不需要 Transformer”。

---

### H2：XRD 采样点或 patch 不是天然语义 token

语言 token 本身是词或子词，具有相对明确的语义单位；而 XRD 的单个采样点只是连续函数 \(I(2\theta)\) 上的一个数值。

真正更接近物理实体的对象可能是：

- 峰；
- 峰簇；
- 峰位、峰强、FWHM、面积；
- \(d\)-spacing；
- 系统消光关系；
- 一组满足晶格约束的反射事件。

因此：

> 直接把固定长度 patch 当作 token，可能类似于让语言模型把若干字母块当词，而没有先形成稳定语义单元。

可能后果：

- patch 边界切开窄峰；
- 同一峰在轻微峰移后落入不同 patch；
- 多个弱峰在投影后被压缩；
- patch token 的含义随背景、展宽和强度变化而不稳定；
- attention 在不稳定 token 上学习远距离关系，数据效率较低。

#### 可证伪预测

- peak-token Transformer 明显优于 patch-token Transformer；
- CNN stem 先提取局部峰事件，再做 attention，比直接 patching 更稳定；
- 减小 patch size / 改变 stride 会显著改变性能；
- 同一峰跨 patch 边界时，PAMPT embedding 出现异常跳变。

---

### H3：物理上连续的扰动，在 PAMPT 表示空间中可能变得不连续

Dynamic 会连续改变：

- 峰位；
- 峰宽；
- 相对强度；
- 背景；
- 噪声；
- 择优取向。

对 CNN 而言，峰移动几个 bin 后仍位于相邻局部感受野中，局部模式通常平滑变化。

对 patch / peak-aware attention 而言，小扰动可能导致：

- 峰落入另一 patch；
- 峰显著性排序改变；
- 弱峰消失；
- 相邻峰合并；
- 导数峰数量改变；
- token 集合或注意力关系突然变化。

于是：

> **物理输入只发生微小连续变化，但模型内部表示发生离散跳变。**

这会直接解释为什么 Dynamic 对 CNN 是正则化，而对 PAMPT 可能增加优化难度。

#### 可证伪预测

对同一母结构逐渐增加单一扰动强度，若 PAMPT 的 embedding distance、logit distance 或 attention map 出现明显非平滑跳变，而 ResNet 更平滑，则支持该假设。

---

### H4：PAMPT 的峰感知先验可能过强、过早或方向错误

“加入物理先验”并不自动等于更有效。

当前 PAMPT 的先验包括：

- 多尺度局部卷积；
- 一阶/二阶导数指导；
- patch 化；
- guided attention；
- token mean pooling。

可能问题：

1. 导数在理想谱上突出峰边缘，但会放大噪声和背景起伏；
2. 强调显著峰可能忽略弱峰、消光和整体峰间关系；
3. 先做手工峰感知会限制表示空间，导致模型无法自行学习更有效的连续谱特征；
4. 不正确或过强的领域先验，可能比弱先验更有害。

#### 可证伪预测

- 去除导数 guidance 后性能提高；
- 仅保留连续谱 CNN stem 时性能提高；
- 模型对弱峰遮挡比 ResNet 更不稳定；
- 输入中加入噪声后，导数支路激活和梯度异常增大。

---

### H5：Mean pooling 可能稀释稀疏的关键峰信息

XRD 判别信息不是均匀分布在 3501 个点或全部 token 上，而可能集中在少量：

- 关键峰；
- 峰分裂；
- 消光位置；
- 相邻峰簇；
- 特定角度区间。

若最后直接对所有 token 做平均，关键 token 可能被大量平坦背景 token 稀释。

#### 可证伪预测

- mean pooling 改为 CLS token、attention pooling、top-k pooling 或 peak-weighted pooling 后明显改善；
- PAMPT 的关键峰 token 贡献在 pooling 后显著下降；
- 只保留峰附近 token 后，模型反而更容易训练。

---

### H6：复杂分支之间存在优化协调困难

PAMPT 同时包含多尺度卷积、导数 guidance、self-attention、guided attention、patch projection 和分类头。

训练早期可能发生：

- 不同分支梯度尺度不匹配；
- 导数支路主导或噪声化；
- attention 学到近似均匀权重；
- token 聚合形成瓶颈；
- 分类头获得的有效梯度过弱；
- 多模块共同优化比残差卷积路径更难。

PAMPT Train accuracy 约 0.638 是这类假设的重要动机：它首先是训练可学习性问题。

#### 可证伪预测

- 在极小训练集上也无法快速记忆；
- 某些分支 gradient norm 长期接近 0 或显著大于主干；
- attention entropy 长期接近均匀；
- 去掉某一复杂分支后 Train 拟合明显改善；
- layerwise learning rate 或分阶段训练显著改善。

---

### H7：PAMPT 可能更吃独立结构数据，而 Dynamic 视图不能替代语义多样性

Dynamic 可以为同一结构生成近乎无限的测量视图，但母结构仍只有 9,842 个。

必须区分：

- **视图多样性**：同一结构在不同测量条件下的谱；
- **语义多样性**：更多独立晶体结构、结构原型和类内变化。

Transformer/attention 可能需要更多独立结构，才能学习稳定的峰间关系；重复生成同一母结构的扰动谱不会等价增加新的晶体学知识。

#### 可证伪预测

- 在 25% / 50% / 100% 嵌套结构预算下，PAMPT 的学习曲线斜率比 ResNet 更陡；
- 数据增加后 PAMPT 与 ResNet 差距逐渐缩小；
- 用随机生成晶体或更大结构库后 PAMPT 明显恢复；
- 单纯增加每个结构的扰动视图数量无法产生同等恢复。

---

### H8：预处理和离散化可能与 PAMPT 发生特异性交互

项目曾怀疑：

- max normalization 可能压低弱峰；
- 最小 FWHM 与网格步长比例可能不足；
- 导数在低信噪比输入上放大噪声；
- 背景或择优取向造成单峰支配；
- patch 投影进一步损失精细峰位。

ResNet 在相同输入上成功，说明数据管线并未整体失效。但这不能排除：

> 同一预处理对 ResNet 尚可，对依赖导数、patch 和 attention 的 PAMPT 却更有破坏性。

#### 可证伪预测

- sqrt / log1p / area normalization 只对 PAMPT 显著有利；
- 提高角度分辨率后 PAMPT 收益大于 ResNet；
- 去除导数支路后预处理敏感性下降。

---

### H9：类别可分性限制存在，但不是 PAMPT 失败的充分解释

PXRD 是三维结构压缩到一维信号的逆问题，存在峰重叠、信息损失和不同结构产生相似谱的问题。

ResNet per-class 结果显示单斜和正交仍然较弱，说明任务确实具有内在难度。

但类别重叠无法解释：

- 为什么 PAMPT Train 只能到 0.638；
- 为什么 ResNet Train 可到 1.0；
- 为什么 Dynamic 在 ResNet 上能显著提高 Validation。

因此，intrinsic task difficulty 是性能上限因素，不是当前 backbone 差距的唯一主因。

---

## 5. 假设之间的关系

这些假设不是互斥的，最可能是联合机制：

```text
有限的独立结构数量
        +
不自然的 patch tokenization
        +
导数/峰先验对扰动敏感
        +
复杂分支和 pooling 的优化瓶颈
        +
任务本身主要依赖局部层级模式
        ↓
PAMPT 学习困难，Dynamic 进一步放大不稳定

而 ResNet：
局部卷积 + 权重共享 + 残差优化 + 连续全谱输入
        ↓
更容易拟合，并将 Dynamic 视为有效正则化
```

当前最值得优先检验的不是九个假设全部展开，而是先区分三个大类：

1. **任务不需要复杂 Transformer**；
2. **Transformer 思路可以，但 tokenization / pooling 错了**；
3. **模型结构没错，主要是数据规模或优化不足。**

---

## 6. 分阶段验证协议

为了避免再次形成巨大实验矩阵，本模块未来必须采用 Gate 式、可停止的验证流程。

### Gate A：最小可学习性与记忆测试

目的：判断 PAMPT 是否存在基础实现或优化故障。

实验：

- 从 Train 中取 64、256 或 512 条固定样本；
- 关闭 Dynamic，只用 level0；
- 比较 PAMPT、ResNet 和简单 CNN；
- 要求模型在小数据上快速达到接近 100% Train accuracy。

解释：

- PAMPT 不能记忆极小数据：实现、梯度路径、pooling 或优化存在强问题；
- 能记忆小数据但全量 Train 失败：优化规模、数据异质性或 sample complexity 问题；
- 小 CNN 已完全胜任：支持“任务统计结构较简单”。

### Gate B：架构拆解定位

只做最小逐层消融：

1. CNN stem + classifier；
2. CNN stem + patch projection + classifier；
3. CNN stem + attention + classifier；
4. 完整 PAMPT；
5. 完整 PAMPT 去除 derivative guidance；
6. 完整 PAMPT 更换 pooling。

目标：找出性能下降首次发生在哪个组件。

停止规则：一旦定位到主瓶颈，不继续无穷组合。

### Gate C：表示连续性 / 增广相容性

对同一母结构生成连续强度网格：

- 峰移从 0 逐步增加；
- FWHM 逐步增加；
- 背景幅度逐步增加；
- 噪声强度逐步增加；
- 择优取向强度逐步增加。

记录：

- 输入距离；
- 中间 embedding cosine / L2 distance；
- logit distance；
- 预测类别变化点；
- attention map / token attribution 变化；
- class margin。

定义一个简单的扰动响应斜率：

\[
S_m = \frac{\Delta d(h(x),h(T_m(x)))}{\Delta m}
\]

并检查是否出现异常跳变。

核心问题：

> 物理扰动连续增加时，模型表示是否也连续变化？

### Gate D：样本复杂度与“杀鸡用牛刀”检验

使用嵌套的唯一母结构子集：

- 25%；
- 50%；
- 100%。

保持：

- 同一 Validation；
- 同一扰动流；
- 同一训练协议；
- 同一 optimizer-step 定义；
- 同一随机种子集合。

比较：

- ResNet；
- 参数量匹配小 CNN；
- PAMPT；
- compact Transformer；
- 可选 CNN + attention hybrid。

重点不是最高分，而是：

- 学习曲线斜率；
- 达到固定 Macro-F1 所需的母结构数；
- 性能/参数量；
- 性能/GPU 小时；
- 方差和校准。

判定：

- 小 CNN 在全部数据规模上占优：支持“当前任务不需要 Transformer”；
- PAMPT 随数据增加追上：支持“更吃数据”；
- hybrid 追上：支持“tokenization / local stem 是关键”；
- 只改优化就追上：支持“训练动态是主因”。

### Gate E：物理 tokenization

仅在 Gate B/C 支持 tokenization 问题后启动。

比较：

1. fixed patch token；
2. hard peak token；
3. soft / learnable peak token；
4. CNN local feature token；
5. token 中加入 \(2\theta\)、强度、FWHM、面积、\(d\)-spacing 和相对位置；
6. 使用 relative-distance bias 的局部或稀疏 attention。

核心问题：

> Transformer 是否必须先看到“物理事件”，而不是原始采样块？

### Gate F：跨信号泛化

只有 XRD 机制较清楚后，再考虑 Raman、IR、ECG 或传感器信号。

目的是判断结论是否属于：

- PXRD 特例；
- 所有稀疏峰型信号；
- 一般一维科学测量。

---

## 7. 建议记录的诊断指标

除 Macro-F1 外，至少记录：

### 可学习性

- Train accuracy / CE；
- 小样本记忆速度；
- 达到固定 Train accuracy 的 steps；
- early epoch convergence slope。

### 泛化

- level0、in-range、single-factor OOD、combo OOD；
- worst-class F1；
- per-class confusion；
- calibration / ECE；
- 多 seed 均值与方差。

### 增广相容性

- clean-to-perturbed embedding distance；
- 扰动强度—表示距离曲线；
- 类别 margin 变化；
- 预测翻转阈值；
- representation smoothness。

### 优化

- 各模块 gradient norm；
- activation variance；
- attention entropy；
- gradient conflict；
- NaN / saturation / dead branch；
- layerwise update ratio。

### 效率

- 参数量；
- FLOPs；
- GPU 小时；
- 峰值显存；
- 性能/计算；
- 性能/独立母结构数。

### 解释性

- 峰遮挡实验；
- 弱峰遮挡；
- 背景-only / peak-only 对照；
- saliency 与已知峰位置的重合；
- token / channel attribution 稳定性。

---

## 8. 潜在解决方案

这些方案按“最小修复 → 更纯 ML 方法”排序。

### S1：接受简单模型是正确模型

若验证表明当前七晶系任务主要依赖局部层级模式，最合理的结论可能就是：

> **ResNet/FCN 是与任务结构更匹配的模型，复杂 attention 没有必要。**

这不是研究失败。一个严格的 inductive-bias 结果本身就有价值。

### S2：缩小 Transformer，而不是继续堆复杂度

- 减少层数和 heads；
- 限制 attention 范围；
- 使用 local / sparse attention；
- 参数量匹配 CNN；
- 保留长程关系，但避免全局 all-to-all 过度自由。

### S3：CNN stem + compact attention hybrid

让 CNN 先把连续谱转换为稳定局部特征，再由少量 attention 建模远距离关系：

```text
continuous XRD
→ multi-scale CNN stem
→ local peak-like features
→ compact attention
→ classification
```

这可能同时保留：

- CNN 的局部归纳偏置；
- attention 的长程关系建模；
- 更稳定的 Dynamic 相容性。

### S4：用物理事件做 token

构造 peak token：

\[
[2\theta, I, \mathrm{FWHM}, area, d, prominence, relative\ distance]
\]

进一步可研究：

- hard peak detection；
- differentiable soft peak extractor；
- learnable event tokenizer；
- 不确定峰 token；
- 峰缺失与系统消光 token。

### S5：修正 pooling

- CLS token；
- attention pooling；
- peak-weighted pooling；
- top-k token pooling；
- 多尺度分区 pooling；
- 保留绝对角度信息的分层聚合。

### S6：修正训练动力学

仅在优化证据支持后考虑：

- tiny-set sanity check；
- layerwise learning rate；
- warm-up；
- staged branch activation；
- gradient clipping；
- auxiliary branch loss normalization；
- 先 Clean 学习，再逐步开放 Dynamic；
- 少量 clean anchor。

不能把这些作为无证据的全面调参。

### S7：提高数据而不是增加重复视图

若数据规模实验支持：

- 增加独立 CIF / 结构原型；
- 使用更大数据库并严格去重；
- on-the-fly 随机晶体生成；
- self-supervised pretraining；
- simulator-to-simulator 多域预训练；
- 再比较 PAMPT 是否追上。

必须强调：

> 更多 Dynamic 视图不等于更多独立晶体结构。

### S8：更适合弱峰的预处理

- sqrt / log1p intensity；
- area normalization；
- multi-channel 输入：raw + sqrt + derivative；
- 保留未标准化统计量作为额外通道；
- 更高角度分辨率；
- 但必须受控、单因素验证。

### S9：让模型学习关系，而不是默认 patch 关系

可加入：

- 基于 \(2\theta\) 或 \(d\)-spacing 的 relative positional bias；
- 峰间距离图；
- 稀疏图神经网络；
- Bragg / lattice relation aware attention；
- 只在物理候选关系之间建立边。

这比对全部 patch 做无结构 dense attention 更有解释力。

---

## 9. 可能出现的结果及其解释

| 结果 | 最合理解释 |
|---|---|
| 小 CNN / ResNet 始终最好 | 当前任务统计结构主要是局部层级模式；Transformer 确实过度复杂 |
| PAMPT 随独立结构数量增加追上 | 主要是 sample complexity，不是架构逻辑错误 |
| CNN stem + attention 追上 | 原始 tokenization / local feature extraction 是关键 |
| peak-token Transformer 追上 | Transformer 可以，但必须以物理事件为 token |
| 去掉 derivative guidance 后恢复 | 过强领域先验或噪声放大是主因 |
| 更换 pooling 后恢复 | 稀疏关键信息被 mean pooling 稀释 |
| tiny-set 都记不住 | 实现、梯度路径或优化存在基础故障 |
| Clean 能学、Dynamic 崩 | augmentation compatibility / representation discontinuity |
| 多模型都在同类上失败 | intrinsic class overlap / label ambiguity / input information limit |
| 所有复杂方案都无收益 | 最简模型就是正确工程与科学选择，应停止追求结构复杂度 |

---

## 10. 为什么这个模块更偏纯机器学习

当前 V9 主线研究的是：Dynamic ERM、JS consistency 与 residual decorrelation 在 XRD Sim-to-Real 中的比较。

本模块更进一步追问：

> **模型应该以什么归纳偏置读取科学信号？**

它关注的不是某个材料体系，而是：

- 什么是科学信号中的自然 token；
- 局部卷积与全局 attention 的适用边界；
- 领域先验是否稳定；
- 数据规模如何改变架构排序；
- 增广如何与表示发生交互；
- 物理连续变化是否对应表示连续变化；
- 模型复杂度是否与任务统计复杂度匹配。

因此它更接近：

- representation learning；
- architecture inductive bias；
- scientific signal modeling；
- sample-efficient learning；
- robustness and invariance；
- optimization dynamics。

XRD 在这里是受控试验场，而不是研究终点。

---

## 11. 与个人研究路径的关系

这一模块是项目发展史中的重要转折：

1. 最初相信“更懂物理的复杂模型”应该更好；
2. 真实实验表明，PAMPT 连基础训练任务都没有学进去；
3. 没有用更多调参掩盖失败，而是建立 Gate、引入成熟 ResNet 对照；
4. ResNet 成功后，主动承认 backbone 选择错误，并冻结新底座；
5. 将失败进一步抽象为可推广的 ML 问题：领域先验、tokenization、模型复杂度和物理增广之间的相容性。

这段历程适合未来申请中表述为：

> 我最初把注意力放在构造一个看似更符合衍射峰物理的复杂模型上，但受控诊断显示，复杂先验并没有自动转化为可学习性；相反，一个成熟的一维 ResNet 在同一任务上能够充分拟合，并从动态物理增广中获得显著泛化收益。这个负结果促使我从“哪种模型更先进”转向“哪种归纳偏置真正匹配科学信号”，并形成了关于 tokenization、表示连续性、样本复杂度和增广相容性的独立研究问题。

它体现的不是一次模型替换，而是研究方式的变化：

> **从为领域任务套模型，转向用领域失败现象提出机器学习问题。**

---

## 12. 当前封存决定

### 当前 V9 必须做

- 冻结 ResNet-18-GN 共享 backbone；
- 冻结 Dynamic ERM 公共训练合同；
- 重做 ResNet 版最小 λ 合法性 Gate；
- 完成正式 Dynamic / JS / Residual 比较；
- Test、真实谱和 V10 继续锁定直到协议允许。

### 当前 V9 不做

- 不重新修 PAMPT；
- 不启动 peak-token Transformer；
- 不做大规模 architecture sweep；
- 不重新打开 Clean 调参；
- 不把第五模块塞进当前论文；
- 不用当前诊断结果宣称 Transformer 机制结论。

### 未来重新开启条件

满足以下至少一项时，才解封本模块：

1. 当前 V9 正式主线完成；
2. 有稳定算力支持至少一组多 seed 架构对照；
3. 能获得更多独立结构数据；
4. 需要构建硕士阶段更偏 ML 的研究提案；
5. 准备将问题推广到另一种一维科学信号。

---

## 13. 内部证据与参考入口

### 当前项目证据

- `00_project_context/CURRENT_STATE.md`
- `xrd_robustness/reports/gate3_pampt_vs_resnet.json`
- `xrd_robustness/reports/cnn_contract_clean_abc_summary.json`
- `xrd_robustness/reports/cnn_contract_dynamic_erm_summary.json`
- `00_project_context/PROJECT_JOURNEY.md`

### 外部方法背景

- Lee et al., 2023：大规模扰动 PXRD 与 FCN；
- Schopmans et al., 2023：ResNet-like 模型与在线随机晶体/谱生成；
- Oviedo et al., 2019：all-convolutional XRD 分类、物理增广与可解释性；
- ML4pXRDs：成熟 ResNet-like PXRD 管线；
- Hu et al., 2026：结构化模拟与域差异残差去相关；
- KBSS, 2026：知识引导增广、一致性和小样本材料学习。

特别说明：

> “XRD 数据结构可能较简单，Transformer 是杀鸡用牛刀”是与胡浩天交流时提出的研究猜想，不是其论文已经证明的结论。该观点在本模块中被正式记录为 H1，并配套可证伪实验，而不是作为既定事实使用。

---

## 14. 一句话封存结论

> **当前结果证明的不是“Transformer 不如 CNN”，而是：在一个受控 PXRD 晶系分类任务中，复杂 peak-aware attention 模型未能充分学习，而成熟 ResNet 能够拟合并从动态物理增广中显著受益；这一现象提出了关于任务复杂度、科学 tokenization、领域先验、数据规模、优化动力学与增广相容性的独立机器学习研究问题。**
