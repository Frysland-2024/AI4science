# 项目心路历程

> **时效说明（2026-08-11）：**本文记录项目为什么改变，而不是当前执行合同。文中的 V8/V9.2、9,800/2,130/2,130 等表述是日期化历史状态，已由 V9-T 及 exact-parent-disjoint 9,842/2,109/2,109 划分取代；该划分不保证 formula/family/prototype disjoint。当前状态、可运行范围和授权边界必须以 `E:/AI4science/xrd_robustness/CODEX_HANDOFF.md`、冻结配置与当前审计报告为准；旧方案保留只是为了说明研究问题如何逐步收敛。

## 0. 从 FerroAI 到 XRD：领域选择与研究方法形成

FerroAI 最重要的遗产不是某个模型，而是完整科研流水线意识：文献与数据整理、特征构建、模型训练、指标检验、误差分析和材料学解释必须组成可复现证据链。这段经验也解释了为什么后续 XRD 项目始终强调 manifest、hash、对照公平性和失败分析。

选择 XRD 之前，项目比较过 XRD、TEM 和 Raman。最终选择粉末 XRD，是因为它同时具备公开晶体结构来源、大规模可控模拟、相对清晰的七晶系标签、物理可解释的峰位与峰形，以及可拆分的样品和测量扰动。项目不是先选择一个模型再寻找应用，而是在寻找“可控干预、稳定标签和可复现实验”的问题时，让 XRD 任务与不变性思想同步收敛。

项目借鉴因果研究中的干预、不变性和去除伪相关思想，但不把当前工作夸大为完整因果推断：这里没有识别因果效应或使用 do-calculus。更准确的定位是，主动改变标签保持的测量因素，检验模型是否依赖稳定结构信息而不是模拟器或仪器捷径。

这条发展线也构成申请叙事的核心：研究价值不在于堆叠 Transformer、JS 或对抗损失，而在于持续修正问题定义、评价指标和实验公平性，并让算法服务于科学测量可靠性。其方法论可迁移到医学影像等同样受到设备、协议、噪声和域偏移影响的任务。

## 1. 最初的问题：模型能分类，不等于模型可靠

项目最初关注的不是继续提高干净模拟 XRD 上的准确率，而是一个更基础的问题：同一晶体结构在合理的测量变化下，晶系标签没有改变，模型的判断是否仍然稳定？

因此，早期主线是把峰移、展宽、背景和噪声作为标签保持的物理扰动，比较普通训练、数据增强和一致性正则化。这个阶段建立了项目的基本立场：研究对象是 XRD 测量域偏移下的鲁棒分类，而不是在静态数据集上追求一个更高的数字。

## 2. V6：从一般增强走向物理约束的鲁棒训练

V6 将 PAMPT 作为峰形感知骨干，并逐步形成 Offline ERM、Dynamic ERM、Dynamic JS 和 Dynamic Residual 等训练方式。扰动参数开始要求具有文献、开源代码或物理公式依据，数据按母晶体结构划分，避免同一结构的不同谱图跨越训练集和测试集。

V6 的价值是把数据、模拟器、模型、训练和 OOD 评估真正接成了可运行管线。但它仍主要回答“不同鲁棒训练方式谁表现更好”。

## 3. V7 的第一次扩张：补齐择优取向，并加入样本效率

项目随后认识到，峰移、展宽、背景和噪声没有覆盖峰间相对强度的系统变化，因此加入 reflection-level 的 March–Dollase 择优取向，形成位置、峰形、相对强度、基线和随机误差五类扰动。

当时的 V7 又增加了结构样本效率问题：分别使用 25%、50% 和 100% 的训练结构，研究不同方法需要多少独立晶体结构。这一设计本身合理，也完成了子集清单、批量计划和统计接口，但它引入了另一条完整研究轴，与鲁棒域泛化并不是同一个问题。

## 4. 方法反思：V7 更像完整框架，还不是最集中的方法命题

讨论中一度使用了过高标准，要求 V7 像顶级通用机器学习工作一样严格证明每一种传统方法为何失败。后来重新校准：本项目的现实目标是达到胡浩天论文那样的问题清楚、方法对应、实验可信，而不是从零发明所有机器学习组件。

真正需要解决的关键问题不是“V7 不够复杂”，而是：模拟器明明知道每张谱被施加了什么扰动，原方案却在生成谱图后丢弃了这些信息。残差被要求不能预测晶系，但没有被要求准确描述峰移、展宽等测量变化，因此残差可能真正编码扰动，也可能只是噪声或发生坍缩。原 V7 无法区分这些情况。

## 5. 方法学边界修正：真实仪器负责验收，不负责定义研究问题

项目同时纠正了对真实仪器校准的默认理解。当前模拟参数优先来自同行评议文献、论文使用的开源代码和物理公式约束；单台本地仪器的数据不作为扰动范围、数据基础设施或训练启动的前置条件。

真实 XRD 的位置被明确为后期 external validation 和 simulation-to-experiment generalization。项目追求的是文献锚定、物理合理、设备无关、可复现的鲁棒性研究，而不是某台仪器的专用误差模型。

## 6. 一次重要分岔：扰动参数监督候选

在寻找更明确的机器学习命题时，项目曾提出：对同一晶体的两张扰动谱计算有符号特征残差，用模拟器已知的参数差 `Δz` 监督残差，同时减少其中的晶系信息。这个候选把“模拟器知道发生了什么扰动”转化为弱监督信号，具有独立研究价值。

进一步讨论后，项目认识到它解决的是“怎样利用扰动标签学习表征”，并没有首先解决“原有五扰动为何仍是无结构独立随机化”。五类扰动还包含连续、离散和结构化参数，统一的 `Δz` 目标会显著增加方法和实验负担。因此，该方案不再作为 V8 主线，保留为未来的弱监督表征解耦方向。

这次分岔留下的重要认识是：一个有价值的机器学习机会，不一定就是当前项目最优先的科学矛盾。项目需要先解决模拟域怎样形成，再研究怎样利用模拟器元数据。

## 7. 当前 V8：物理条件驱动的五扰动结构化动态模拟

V8 当前真正要解决的问题是：原有动态增强通过算子级独立 `apply_probability` 决定峰移、展宽、择优取向、背景和噪声是否出现，缺少样品、仪器和采集条件的语义，也没有显式表达同一物理机制内部的一致变化及测量生成顺序。

V8 因此先采样抽象的虚拟实验状态：

```text
c = (sample state, instrument state, acquisition state)
z ~ P(z | c)
```

- 样品状态描述晶粒尺度、微应变和取向程度等样品因素；
- 仪器状态描述设备无关的零点与分辨率贡献，不绑定具体仪器型号；
- 采集状态描述背景、计数水平和观测噪声。

结构化不意味着强行让五类扰动全部相关。它要求的是：同一物理原因内部使用统一参数，扰动具有明确条件归属，背景和计数噪声遵循合理生成顺序，峰位、峰宽和晶面族强度的变化保持物理一致。所有状态变量、耦合关系和范围仍必须由文献、论文使用的开源代码或物理公式支持。

在结构化模拟基础上，V8 保留测量残差类别去相关：允许参考谱与扰动谱的特征存在差异，但减少这些差异中的晶系信息。这样形成两段问题链：先构造更合理的测量域，再避免模型把测量差异错误地用于晶系判断。

## 8. V8 三组主实验

V8 的正文主比较最终收缩为三组：

| 组别 | 方法 | 回答的问题 |
|---|---|---|
| 1 | Independent Dynamic ERM | 原算子级独立动态增强的基础表现 |
| 2 | Structured Dynamic ERM | 结构化模拟本身是否有价值 |
| 3 | Structured Dynamic + Residual Decorrelation | 在结构化模拟基础上减少残差类别耦合是否进一步改善泛化 |

Clean ERM 和离线增强可以作为基础结果或附录，不扩大正文主线。模拟器仍完整保存状态、扰动参数、随机种子和生成顺序，用于覆盖审计、分层评估和失败分析，但不作为 V8 主训练目标。

2026-07-15，`Structured Dynamic + JS` 从正文主实验删除。原因是 V8 的必要证据链只需分别检验结构化模拟和残差类别去相关的增量价值；继续保留 JS 会重新引入“严格一致性是否过度对齐”的额外比较命题。项目不再以“残差优于 JS”为正式主张，JS 只保留为未来可选附录基线。

同日，项目审计并删除了旧候选配置中“同时最多两个强扰动”的全局拒绝规则。该规则没有直接文献、开源实现或物理公式依据，而且会把本应独立的基线悄悄变成受人工联合约束的分布。Independent 基线改为采用 XRDMatch 所代表的操作符级独立在线随机化范式，但只借用其采样思想，不照搬峰删除、逐点缩放或半监督训练目标；五种物理算子及参数来源仍由本项目定义。

## 9. 主线收缩：正式删除样本效率研究轴

2026-07-15，项目决定从现行方案中删除数据利用效率/样本效率比较。原因不是它没有价值，而是它回答“减少训练结构后谁学得更快”，而 V8 当前需要回答的是“物理结构化动态模拟与残差类别去相关能否提高未知测量条件下的泛化”。同时保留两个问题会显著增加训练比例、随机抽样、计算预算匹配和学习曲线统计工作，分散论文中心。

现行实验固定使用同一套 9,800 个训练结构和相同训练预算。多随机种子、均值和标准差继续保留，因为它们用于结果可靠性，而不是样本效率研究。相关的 25%/50%/100% 子集、36 组 dry-run 计划、聚合和绘图接口已经退出活动代码与实验计划。

## 10. 当前状态与克制边界

截至 2026-07-15，V8 已经完成主问题重定向，但物理条件驱动的五扰动联合生成器尚未完成正式实现或科学验证。此前的扰动监督 smoke test 只证明那条未来支线的软件链路可以运行，不构成当前 V8 的实验结果。

项目当前不需要达到“顶级通用 ML 原创理论”的标准。只要做到问题明确、结构化模拟有依据、方法与问题对应、结构划分无泄漏、三组比较公平，并在 OOD、残差类别 probe 和后期真实谱验证上形成一致证据，就已经达到本项目期望的论文层级。

## 当前一句话定义

> 将峰移、展宽、择优取向、背景和噪声从算子级独立随机开关，重构为由样品—仪器—采集条件驱动、文献锚定且设备无关的结构化动态测量模拟，并通过测量残差类别去相关提升未知测量条件下的晶系分类泛化。

## 11. 后续研究储备：当前不进入 V8 主线

下面两个方向均有独立研究价值，但回答的问题不同于当前 V8。它们被正式记录为未来工作，不作为当前数据生成、方法实现、训练启动或论文完成的前置条件。

### 方向 A：扰动参数监督的弱监督表征解耦

结构化模拟器会自然记录每张谱的样品、仪器和采集状态，以及峰移、展宽、择优取向、背景和噪声参数。未来可以不只把这些参数用于数据审计，还将其作为近乎零成本的弱监督信号：

```text
x1 = T(x0, z1)
x2 = T(x0, z2)
r  = f(x2) - f(x1)
r  -> Δz
r  -/-> crystal system
```

这一方向研究的是：模拟器已知的 nuisance parameters 能否监督模型把晶系语义与测量变化分开。它与当前 V8 的区别是：V8 首先研究怎样生成物理结构合理的扰动域；该支线进一步研究怎样利用生成过程中保存的扰动标签学习表征。

暂不进入 V8 的原因：

- 五类扰动同时包含连续变量、离散机制和结构化参数，难以用一个统一的 `Δz` 回归目标表达；
- 需要额外解决参数归一化、多任务损失权重、不可辨识性和相似谱图变化等问题；
- 它会新增扰动预测、表征分解和 OOD 分类之间关系的完整实验轴；
- 应先确认结构化模拟器本身合理，再研究模型能否理解其参数。

未来启动条件：

1. V8 结构化五扰动生成器已经通过物理与质量门禁；
2. 每类扰动参数具有稳定、可比较且可重放的表示；
3. V8 主实验已经完成，时间与算力允许增加新的学习目标；
4. 正式加入 AugSelf 式参数差预测和胡浩天式类别去相关等必要对照。

当前处理原则：完整保存 `z`、虚拟实验状态、随机种子和生成顺序，但不使用它们训练 V8 主模型。已有扰动监督代码保留为软件原型，不作为当前方法贡献或科学结果。

### 方向 B：独立晶体结构的样本利用效率

这一方向研究的是：在只使用部分独立晶体结构进行训练时，不同鲁棒学习方法达到相同性能需要多少结构数据。研究单位必须是 unique crystal structures，而不是在线生成的扰动谱数量。

它可以回答：

- 结构化动态模拟是否能让每个母结构提供更有效的训练信息；
- V8 在 10%、25%、50% 和 100% 结构预算下是否保持优势；
- 动态视图带来的收益来自更好的数据利用，还是更多优化步数和骨干前向；
- 不同晶系在小结构预算下是否具有不同的数据需求。

暂不进入 V8 的原因：

- 它与未知测量条件泛化是另一项科学问题；
- 需要多种结构比例、重复子集抽样、多随机种子和完整学习曲线；
- 必须同时匹配独立结构数、视图暴露、优化步数和计算预算；
- 会显著扩大实验规模并分散当前论文中心。

未来启动条件：

1. V8 完整方法已经在固定 9,800 结构协议下获得可信结果；
2. 有独立人力和算力承担嵌套子集、重复实验与统计分析；
3. 预先冻结结构预算、子集抽样、训练预算和统计协议；
4. 重新建立与届时方法版本一致的子集清单和运行矩阵，不直接恢复已经删除的旧 V7 计划。

当前处理原则：V8 固定使用相同的完整训练结构和训练预算。多随机种子仍用于结果可靠性，但不解释为样本效率研究。

### 两条支线与当前主线的关系

```text
当前 V8：物理条件驱动的结构化五扰动模拟
          + 测量残差类别去相关
                         │
          ┌──────────────┴──────────────┐
          ↓                             ↓
未来方向 A                        未来方向 B
利用扰动参数监督表征             研究独立结构样本利用效率
```

两条支线都建立在 V8 基础之上，但都不是 V8 成立的必要条件。除非项目后续明确重新批准，否则不得用它们扩大当前主实验或推迟 V8 训练与验证。

用户确认的日期快照见 `XRD_future_research_branches_2026-07-15.md`；面向研究生申请的完整研究问题、潜在贡献和可执行路线另见 `FUTURE_RESEARCH_DIRECTIONS.md`。

## 12. Independent Dynamic ERM 从概念基线变成可执行基线

2026-07-15，项目先完成 V8 第一组正文方法 `Independent Dynamic ERM`。它采用 XRDMatch 所代表的操作符级独立在线采样范式，但不复现 XRDMatch 的弱／强半监督训练，也不照搬峰删除、逐点缩放或其具体概率。基线继续使用本项目的峰移、展宽、March–Dollase 择优取向、背景和噪声五个物理算子。

这组方法的受控定义是：五个算子使用当前相同的单变量边缘范围与分布，分别独立抽样；不先生成样品、仪器或采集共享状态；不设置“最多若干强扰动”的跨算子限制；同一母结构每个训练步生成两个独立在线视图，训练损失只是两个视图晶系分类交叉熵的平均。它不包含 JS、残差去相关或扰动参数监督。

实现已经通过五算子真实渲染与一次前向／反向传播 software smoke，并保存算法契约、参数来源哈希、视图种子和激活记录。这里的“完成”仅指软件基线已经可以审计和运行；继承的边缘范围仍是 candidate，尚未启动科学 Pilot 或正式训练，也没有产生支持 V8 优于基线的实验结论。

## 13. 2026-07-16：V9.2 双轨计划与当前有效结论

V8 的结构化动态扰动提出了重要问题，但其状态变量、依赖关系、范围和联合分布尚无足够证据冻结。V9.2 因此将它封存为未来方向，不让它继续阻塞当前工作，并把近期研究改为共享基础设施上的双轨计划：

- 路线 A 利用模拟器已知生成变量监督测量残差，检验条件可学习性、样本利用和 OOD 收益；
- 路线 B 在相同数据与计算预算下比较 Paired ERM、JS 一致性和残差类别去相关，作为可执行保底路线；
- 最终主线由预先冻结的 Gate、development-OOD 和后期锁定真实谱证据决定，而不是由预设叙事决定。

截至当前，本地已经具备 14,060 结构池、反射缓存、五扰动算子、PAMPT、成对视图及部分 JS/残差组件，但这些属于可复用的 V7/V8 地基。V9.2 专用 schema、pair generator、统一 trainer、固定面板、Pilot、Gate 和分支报告尚未完成。

当前有效执行原则是：先统一 V9.2 与现有冻结 split，收缩主指标和真实谱使用边界，再完成 Stage 0；在这些门禁通过前，不把计划文档表述为已经实现，也不启动 Pilot 或正式训练。

## 2026-07-22：从参数溯源推进到程序性合法性

笔记本阶段的收口把项目的审计标准从模拟器参数扩展到了整个实验程序。早期版本主要追问物理扰动参数是否有文献、代码或物理依据；V9-T 进一步要求算法参数、随机执行、统计不确定性和外部测试边界都能独立复现与质询。

### Resume 成为实验身份的一部分

仅能序列化模型和优化器，不再视为 checkpoint 支持已经完成。新的真实缓存 CUDA 审计在 epoch 0 后中断，再与从未中断的三 epoch 参考运行比较；必须严格一致的对象包括后续母结构顺序、接受的动态参数对、pair schedule/stream hash、下一步 loss、global step、最终 stream snapshot 和最终模型 SHA256。该审计发现并修复了一个真实设备问题：`map_location=cuda` 会同时移动 CPU RNG tensor，因此恢复逻辑现在显式把 CPU/CUDA RNG 状态归一到正确设备。最终 12/12 检查通过。

决定：未来正式 checkpoint 必须自包含 training-stream audit 与 sampler-contract hash。没有继续运行证据时，不能只凭“理论上可恢复”宣称可复现。

### 损失权重与性能调参被严格分离

注册的 JS/Residual 权重在 Train-only 数据上各进行了 8 个有界优化步骤的数值合法性审计。审计覆盖零权重严格退化到 Dynamic ERM、JS 非负与交换对称、Residual 交换不变、2-epoch warmup/3-epoch ramp、head/backbone 梯度传播、非有限数、梯度/特征/Residual 尺度、坍塌风险、显存和时间；没有使用 Validation、simulated Test、real XRD，也没有选择 λ。

审计表明候选值数值稳定，但在这段早期训练中，两种方法最大的加权辅助损失都低于分类损失的 1%。这不能证明候选范围科学上不合适，因为辅助项尺度可能随训练演化；但它也没有证明范围已经覆盖“弱到强”。

决定：不得静默放大或替换候选集合。范围充分性必须在调参授权前作为独立的科学治理问题记录；数值工程证据与 Validation 性能选择继续分离。

### 不确定性单位从 seed 转向母结构家族

旧比较程序只对三个 seed 汇总值做 bootstrap，这一路径已经移除。正式 run 现在导出带哈希的逐谱记录，包含 seed、method、profile、material ID、family ID、label、prediction 和 probabilities。注册分析在每个 seed 内对成对的母结构/family cluster 重采样，再跨全部注册 seed 汇总，并直接计算 `Residual - JS`。

决定：母结构/family 是基本独立统计单位。seed 仍作为完整重复逐一报告，但不再被当作仅有的三个 bootstrap 样本。结论代码用稳定提升、seed 方向混合、近似持平以及 OOD 提升伴随 ID 下降四类合成情形做了测试。

### 机制表述与 real-test 边界在结果前冻结

机制接口现在覆盖 paired JS、prediction flip、correct-and-consistent、Residual probe 输入、norm、variance、effective rank、class separation 和坍塌检查。允许的表述是 Residual 中的类别可预测信息是否改变；没有额外识别证据时，不把 Residual 等同于物理测量因子。

real-XRD 路径增加了只读预处理审计：冻结 10–80°、0.02°、线性插值、零填充、max normalization，以及 SHA256、来源、标签证据、相纯度和重叠控制。manifest 尚未冻结时，审计既不加载模型，也不加载真实谱。

决定：real XRD 仍是唯一方法冻结后的一次性外部测试，不能定义模拟参数、选择 λ、决定 JS/Residual，或用来挽救负面的开发结果。

### 当前边界

本阶段产生的是工程和方法学证据，不是科学性能结果。调参仍为 0/7，正式比较仍为 0/15，两个测试阶段继续锁定。下一步机器动作是台式机 first-boot 验收；下一项科学决定是正式授权调参前明确审查候选尺度是否充分。

## 2026-07-22：方法参数合法性从“数值不报错”升级为可执行 Gate

此前的轻量审计证明 JS 与 Residual 在旧候选值下可以运行，且没有明显非有限值或坍塌；但它只在小模型上为每个候选运行 8 step，主要记录加权辅助损失相对分类损失的比例。该证据不足以回答导师或审稿人真正会问的问题：当前三点是否在正式 backbone、当前损失定义与数据尺度下覆盖了有意义的弱—中—强作用区间。

本轮把方法参数合法性拆成三层并写成机器合同：

1. 方法原理和公式解释为什么需要 `lambda_js` 与 `lambda_res`；
2. 数据无关语义审计验证零权重退化、公式方向、reduction、交换语义、数值稳定性、梯度流和调度；
3. Train-only 尺度审计检查注册网格对正式 PAMPT-B3 backbone 梯度的实际相对影响，Validation 只在网格冻结后负责选择最终值。

语义审计 22/22 通过。一个重要澄清是：当前 V9-T 生产 residual 定义为两个 L2-normalized feature 的绝对差，因此交换视图应当不变；只有为后续研究保留的 signed measurement residual 才在交换后反号。项目没有为了满足口头测试描述而改写冻结方法，而是把二者分别测试并写入治理文档。

尺度审计改用正式 PAMPT-B3、CUDA、七类各 2 个 Train 结构、128 个 classification-only optimizer steps，并把前 64 step 排除为 burn-in。Residual probe 使用 detached features 更新，不改变 backbone 轨迹。结果全部有限、可重放且没有接触 Validation、simulated Test、real XRD，也没有候选专属训练或 λ 选择。

然而，现有六个候选全部落在预注册的 `R < 0.01` 几乎不起作用区间。最大候选的中位 backbone 梯度比分别只有 JS `7.489e-5` 与 Residual `7.610e-4`。审计反推的中位梯度平衡中心约为 `9.745e4` 和 `2.950e4`；这个结果说明旧网格的内部循环引用不能继续被当作范围依据，同时也提醒短轨迹反推值可能非常敏感，不能机械写入正式配置。

决定：

- 当前 `{0.1,0.3,1.0}` 和 `{0.01,0.1,1.0}` 暂时保留为“待修订注册候选”，不是已通过的可执行网格；
- 7-run 的两个 execution switches 改为 `false`，计划仍可生成用于审计，但不能执行；
- residual head depth=1、warm-up=2、ramp=3 明确作为最小固定设计，不根据结果反复搜索；
- 候选网格最多允许在接触 Validation 前整体修订一次，依据只能来自 Train-only 数值证据；
- 在采用数万量级建议前，必须先审查 128-step 轨迹与 influence bands 是否足以代表正式训练；
- 修订后必须重新运行语义/尺度审计，更新配置、治理合同、文档和哈希，再冻结范围；
- simulated Test 与 real test 继续完全锁定。

这一决定把“选择程序合法”与“搜索空间产生程序合法”分开。当前状态不是调参失败，而是参数范围 Gate 诚实地阻止了尚无充分依据的 7-run。

## 2026-07-22：Raman 是第二项目的数据种子，不替代 XRD 主线

项目重新比较了当前 XRD V9-T 与本地 Raman mapping 原型。比较的目的不是判断哪一种数据模态“看起来更高级”，而是判断哪一个项目已经具备可证伪问题、独立样本、可信划分、受控对照和验证协议。

Raman 数据表面上是两个 26 x 26 x 829 的空间—光谱立方体，共有 1,352 条像素谱；但文件核验表明，它们只来自 `undoped` 与 `doped` 两个独立样品文件，且文件名均记录日期 `20240823`。相邻像素共享制样、仪器、日期、背景和空间环境，不能被当作 1,352 个独立实验单位。若随机把像素分进 Train/Test，模型可以利用样品或批次指纹而得到虚高结果。

现有 MATLAB 原型也验证了成熟度差异：它实现的是文本读取、Raman shift 选择、区间强度积分、光谱绘图和空间曲面显示，尚未提出 ML failure mode、方法对照、样品级划分或外部验证。此时直接加入 3D CNN、Transformer 或分类器，只会增加模型复杂度，不会自动补足科学证据。

相比之下，XRD 已经把母结构、family split、扰动分布、配对视图、backbone、训练预算、development OOD、Test 锁和方法间公平性写成可审计合同。它仍然没有正式结果，不能提前宣称论文成立；但它已经是一项等待实验结果的完整研究设计。因此决定保持：

1. XRD V9-T 是当前唯一主研究，优先完成台式机验收、λ 治理决定、7-run 和后续独立授权阶段；
2. Raman 不进入当前 XRD 代码、数据合同或实验矩阵；
3. 当前 Raman 只用于描述性检查和可选的 PCA/NMF 探索，不进行像素级随机 Train/Test；
4. Raman 只有在补充多个独立样品、多个批次或日期、可靠标签/相区证据和样品级外部验证后，才升级为 ML 项目；
5. 升级后的首选问题是少标签空间—光谱自监督、解混/分割或异常检测，而不是用复杂模型区分现有两个样品。

这条路线让两个项目形成互补：XRD 证明可控模拟、鲁棒泛化和学习原则比较；未来 Raman 则检验同一研究兴趣能否迁移到真实空间—光谱信号、有限独立样本和局部异质性。它是第二座桥，但不是现在需要更换的主线。

## 2026-07-22：纠正胡皓天论文参数引用，切断 `1e-4` 到 V9-T 的错误迁移

重新逐页核对 Haotian Hu 等人的 SD3Net 原文后，确认此前把 Fig. 12 的 `1e-4` 直接称为“残差损失权重”会混淆论文中的两套记号。式 (16)–(17) 明确把分类项写为 `lambda_1 L_sd + lambda_2 L_sim`，把去相关项写为 `lambda_3 L_decorr`；Table 5 在 Pavia、HyRANK、WHU 上都使用 `lambda_3=1`，并联合调整 `lambda_1/lambda_2`。同一论文的 Fig. 12 又分析一个记作 `lambda`、约在 `1e-4` 最优的 regularization parameter，但正文没有明确说明它与 `lambda_3=1` 如何对应。

决定：

- 胡皓天论文只作为 residual entropy/decorrelation 机制、相对损失权重、联合敏感性和模块消融的外部方法学先例；
- 不把 `1e-4` 解释为论文已经清楚定义的 `lambda_3`，也不把 `1` 或 `1e-4` 迁移为 PXRD 的 `lambda_res`；
- V9-T 的分类损失系数继续固定为 1，Dynamic/Paired ERM 继续充当 `lambda=0` 消融锚点；
- 当前 7-run 数量、候选网格和执行开关均不因本次文献更正而改变；
- 候选范围的唯一一次修订仍只能依据 V9-T 自身 Train-only 数值尺度证据，并在接触 Validation 前完成；
- 最终权重仍只由预注册的 Simulation Validation 规则选择，simulated Test 与 real test 保持锁定。

这次更正把“外部论文证明方法值得研究”与“外部论文给出本项目可用数值”彻底分开，防止以后通过内部文档循环引用或跨任务抄值制造虚假的参数合法性。

## 2026-07-22：把巨大梯度倒数重新定性为诊断报警，而不是权重提案

上一版 128-step 尺度审计把辅助梯度与分类梯度的倒数报告为“梯度平衡中心”。虽然文档已经警告不能自动采用，但“候选范围需要整体修订”的状态仍然走得太快：如果分类器和 residual probe 在测量时都尚未学会任务，那么辅助目标接近零梯度首先说明测量时点不具备解释条件，而不是说明正确权重必然要放大几万倍。

本轮没有修改任何候选值，而是扩展并重跑同一 Train-only 诊断。新版使用 128 个不重复配对 batch，把正式 PAMPT 监督分类头从 encoder/backbone 梯度范数中分离，并在早、中、晚三段同时记录原始分类/JS/Residual loss、三项未加权梯度、prediction JS、归一化 feature residual norm、residual-head entropy、分类准确率、视图预测一致率，以及 residual probe 每次更新前后的 loss/accuracy/entropy。

结果显示，late 段分类准确率只有 11.96%，分类损失 1.9499，与七分类均匀基线 `ln(7)=1.94591` 一致；但两个视图的 top-1 已有 99.34% 一致，JS 仅约 `2.97e-7`。因此 JS 小并不是已经证明模型具有强扰动不变性，而是两个尚未学会类别的输出本来就几乎相同。Residual probe 的 late pre-update 准确率为 14.62%，交叉熵 1.94613，熵几乎最大，同样没有证明它能从 residual 读取类别信息；此时把均匀输出称为“去相关成功”会产生假象。

决定：

- `1/R` 统一称为轨迹特定的梯度补偿倍数，不称为理论权重、尺度中心或候选网格提案；
- 当前两组三点网格保持原样，不执行此前设想的一次性整体平移；
- 在解释 JS 权重前，Train-only 主分类器必须先达到明确的非随机学习里程碑；
- 在解释 Residual 混淆前，pre-update residual probe 必须先证明具有非平凡类别预测能力；warm-up 期间 head 虽然一直执行 Step A，但“代码有更新”不等于“probe 已学会”；
- 下一轮尺度审计应按学习里程碑取样，而不是把固定 128 step 的第三段称作正式训练后期；
- Validation、simulated Test 和 real test 继续不参与诊断，两项 tuning execution switches 保持关闭。

这次修正没有否定 JS 或 Residual 方法，也没有证明现网格合理。它只是把因果顺序恢复为：先证明主任务与探针已进入可解释状态，再讨论辅助梯度尺度，最后才可能在 Validation 前做唯一一次范围治理决定。

## 2026-07-22：用已学习状态把“辅助目标没信号”与“初始化没信号”分开

项目随后执行了明确授权的 learned-state Train-only audit。它不是正式性能实验，也不使用任何候选 λ：唯一的 PAMPT-B3 主干以 Dynamic/Paired ERM 在完整 9,842 个 Train 结构上训练五个 epoch，并在预先固定的 epoch 1、3、5 观察学习状态。全程没有读取 Validation、simulated Test 或 real XRD，没有保存 checkpoint，也没有启动 7-run。

为避免“probe 自己没学会”继续伪装成“residual 没有类别信息”，Residual 证据被拆成三个互斥的七类平衡 Train 子集：700 个结构只用于训练 detached residual probe，另 700 个只用于 probe 审计，再用第三组 700 个测量 loss 与 backbone 梯度。实现试跑还暴露了一个重要审计细节：把主干的 `1e-4` 学习率机械复制给 probe 会造成欠拟合假阴性。最终冻结的诊断协议仍使用一层 residual head，但给 detached probe 使用仓库既有 post-hoc probe 的 `1e-3` 数量级、固定 50 epochs；这不会改变 backbone，只提高“是否存在可读取类别信号”这个检测的灵敏度。

结果形成了清晰的时间对照：epoch 1 时主干和 probe Gate 都失败；epoch 3 和 epoch 5 时两者都通过。主机意外重启后，由于 checkpoint 只存在内存，审计按同一固定 seed 从 epoch 0 完整重跑，没有声称断点恢复；本次重跑报告成为权威结果。epoch 5 的主干 Train CE 为 1.62189、两视图准确率 31.02%；互斥 Train-audit residual probe 达到 32.57% accuracy、28.92% Macro-F1、CE 1.85059，明显优于 14.29% chance。与此同时，raw JS 中位数升至 0.01862、两视图 top-1 disagreement 为 35.42%，说明短审计里的近零 JS 主要是随机状态现象，而不是已经学到完美不变性。epoch-5 未加权辅助/分类 backbone 梯度比中位数为 JS 0.05898、Residual 0.09738。

决定：

- 128-step 报告继续保存，但只作为 initialization/chance-state evidence；其中几万到几十万的倒数不允许进入参数治理；
- learned-state 报告证明 JS 与 Residual 在主干学习后都有可测信号，也证明当前 residual 确实含有可被 probe 读取的晶系信息；
- 这些结果只把参数讨论推进到“可人工审查”，不等于现网格合理，更不等于已选出最终权重；
- 原 JS `[0.1,0.3,1.0]` 与 Residual `[0.01,0.1,1.0]` 继续原样保留为待审候选，`candidate_range_frozen_for_validation` 保持 `false`，两个 tuning execution switches 保持关闭；
- 不自动生成或应用新网格，不启动 Validation tuning/7-run；是否进行唯一一次整体对数平移必须由人工结合 learned-state 比率另行决定并记录。

这一步把参数尺度审计从“观察一个数”升级为“先证明测量状态、再证明 probe 能力、最后解释梯度”。它排除了初始化假象，但刻意没有越过人工作出的科学治理决定。

## 2026-07-22：完成唯一一次 pre-Validation 网格修订并冻结候选范围

在 learned-state 证据通过人工审查后，用户明确选择第二组 decade grids：JS `[0.3,3,30]`、Residual `[0.2,2,20]`。决定依据不是 Validation 性能，而是四项预先声明的治理逻辑：Dynamic/Paired ERM 已提供 `lambda=0` 锚点；每组严格十倍间隔；两种方法在 learned-state 下的预期影响尽量接近；三个点分别瞄准 weak、material non-dominant 和 dominant。机器合同同步固定 negligible `<0.01`、weak `[0.01,0.1)`、material non-dominant `[0.1,1)`、dominant `>=1`。

因为上一次 learned-state checkpoint 只存在内存，本次没有声称恢复，而是用相同固定 seed 从 epoch 0 再训练一个五 epoch、完整 9,842 Train 结构的 classification-only Dynamic/Paired ERM PAMPT-B3。三个 700 结构的 probe calibration、probe audit、scale audit Train 子集继续严格互斥；detached residual probe 固定一层、`lr=1e-3`、50 epochs。随后对六个候选分别调用 autograd 测量加权辅助目标与 `L_cls + lambda L_aux` 总目标，避免只把 `lambda=1` 的比率线性外推。

最终权威报告 `reports/v9_candidate_grid_gate.json` 通过。主干 learned-state 和 residual-probe competence 再次成立；实测中位辅助/分类 backbone 梯度比分别为 JS `0.02283/0.22842/2.28533`、Residual `0.02581/0.25854/2.58715`，两组均严格落入 weak/material/dominant。所有 loss 与梯度有限，分类梯度和加权辅助梯度非零，中位合并梯度仍是分类下降方向，未触发单 batch 50 倍失控保护。全程未使用 Validation 指标、simulated Test 或 real XRD，未保存 checkpoint，也未启动候选训练或 7-run。

审计实现本身在冻结前经历两项透明修正。第一次把独立 BF16 autograd 遍历的梯度和恒等式误用 `1e-4` float32 风格容差；六候选只有该检查失败，实际差异为 0.84%–2.36%，因此按 BF16 数值路径改为 5%。第二次给 dominant 候选额外加入 p90 combined/classification `<=10`，JS=30 在一次重跑中为 10.13，虽然 loss/梯度均有限、最大比率 16.07、中位方向仍正确；该上限与 `R>=1` 的开放 dominant 定义冲突且并非用户批准阈值，因此删除 p90 硬判定，但保留 50 倍单 batch 失控保护。两次修正都没有改网格、数据、影响带或读取任何性能验证结果；脚本哈希改变后均从 epoch 0 重跑，最终报告与当前脚本哈希一致。

决定：

- 唯一一次候选范围修订已消耗，`completed_range_revisions=1`；
- JS `[0.3,3,30]` 与 Residual `[0.2,2,20]` 现以 `candidate_range_frozen_for_validation=true` 冻结，不得再根据后续结果扩展；
- 这只完成搜索空间合法性，不代表任何 λ 已被选为最终值；
- 两个 tuning execution switches 继续为 `false`，7-run 保持 `0/7`；
- Validation-only tuning 仍须用户单独明确授权，simulated Test 与 real XRD 继续锁定。

这一节点闭合了“方法原理—learned-state 数值尺度—人工预注册范围—直接 Train-only Gate”的前半条证据链，同时保留后半条“独立 Validation 选择—多 seed 敏感性—锁定 Test”的授权边界。

## 2026-07-25：V10 的负结果形成架构级结论，并冻结归档

V10 最初试图利用模拟器已知的测量标签，让 residual 保留测量信息、同时去除晶系信息。Train-only 的 P0 前提 Gate 首先证明 residual 并非纯噪声：测量家族、若干测量强度和晶系信息都可被独立 probe 解码，因此“测量语义表征”是一个值得检验的科学问题，但这一结果本身不构成正式训练授权。

Pilot v1 因三条分支都接近七分类随机水平而返回 `HOLD`，无法区分机制失败和主干尚未学会。Pilot v2 因而先在完整冻结 Train split 上预训练主干，并要求 learned-state Gate 通过后才比较匹配的 ERM、V9 residual 和 V10 supervised residual。该 Gate 通过，V10 也保留了测量家族、背景、展宽和噪声强度信息；但辅助监督启用后，独立 detached probe 读出的晶系泄漏反而高于匹配 V9 residual。

这形成了一个不对称但可操作的结论：正向测量监督可以增强 residual 的测量可解码性，却不会自动带来测量信息与晶体语义的解耦；在当前无条件 decoder 下，它更像增加 residual 的总信息量。内部 adversarial probe 接近随机而独立 probe 仍可解码晶系，也说明当前对抗头可以被规避，不能作为泄漏已消失的证据。

因此项目决定：

- 冻结并归档当前 V10，不继续追加 epoch、搜索标量权重或修改架构直到结果“通过”；
- V9-T 仍是唯一主线，V10 不进入 7-run、15-run 或真实域协议；
- 若 V9 validation 完成后重启 V10，优先研究带 stop-gradient 晶体语义上下文的条件测量 decoder，并继续保留独立 residual crystal probe；
- 重启必须重新预注册 Train-only 协议、匹配 ERM/V9 对照，并获得新的明确科学决策授权。

这一负结果把问题从“权重是否合适”推进为“无条件测量预测目标为何诱导 residual 重编码晶体语义”，同时避免用反复调参抹去可复现的失败证据。
## 2026-07-26：把 7-run 执行目标从待验收台式机改为当前实测笔记本

用户明确要求立即在笔记本上执行 V9-T 的七条 Validation-only 调参 run，并进一步要求最大化利用笔记本设备和条件。这是对旧“仅在目标台式机训练”位置决策的明确覆盖，但授权范围严格限定为预注册的 7-run；15-run 正式比较、simulated Test、real XRD、真实适配和 V10 均未随之开放。

迁移没有直接复用台式机的 4070 Ti SUPER 双 run 配置。当前 LENOVO 82WM 实测为 Ryzen 9 7945HX（16C/32T）、RTX 4060 Laptop GPU（8188 MiB）、32 GB RAM，处于交流供电和性能模式。Python 3.11.9、Torch 2.5.1+cu124、CUDA 12.4、BF16 和依赖完整性均通过。旧的 8-worker/8-batch 预取与 evaluation batch 256 等价性证据继续适用。

为确定“最大化利用”而不是凭显存容量猜测并发，执行了不含 optimizer step、checkpoint 或数据访问的有界前向/反向探针。两个并发负载完成且峰值显存安全，但聚合吞吐只有串行的 0.8377；新合同因此冻结为单 run 串行，每个 run 独占全部八个预取 worker。新鲜单负载 BF16 审计峰值约 1821.5 MiB，远低于 90% 显存门槛。

同一探针也发现当前 Windows 环境没有可工作的 Triton，`torch.compile` 实际产生零个 compiled graph，并回退到 eager。继续请求编译只会为每个进程增加失败编译时间和警告，不会带来计算加速。因此笔记本硬件合同显式关闭 `torch.compile`，同时保留 BF16、TF32、fused AdamW、pinned memory、non-blocking H2D 和八进程预取。这个决定只改变工程执行效率，不改变模型、损失、候选网格、seed、训练步数、结构暴露或 Validation 选择规则。

正式首轮启动后的稳态采样进一步显示，8-worker/8-batch 动态谱图预取时 CPU 平均负载约 82%，GPU 虽可瞬时达到 99%，却会周期性掉到 0–4%，说明瓶颈是 CPU 谱图生成与预取供给，而不是显存。随后执行 128-batch 严格等价扫描：8/8、12/12、16/16、20/20、24/24 分别达到约 13.56、17.67、32.57、23.15、29.08 batch/s；超过物理核心数后吞吐反而下降。最终冻结 16-worker/16-batch，并用新鲜权威审计复验为约 32.4 batch/s。该审计的 manifest、材料顺序、扰动参数、谱图数组、参数哈希和质量门计数全部完全一致，因此这是纯工程供给优化，不改变任何科学随机性或训练合同。

启动前状态仍为 0/7。所有 run 必须由注册计划和 run registry 从 optimizer step 0 启动；任一 run 失败后停止，不得自动进入后续正式或测试阶段。
## 2026-07-26：首次笔记本启动因 Git provenance 缺口停止并从零重启

注册启动器通过空闲门后，首条 Dynamic ERM tuning run 已创建冻结 manifest 并进入 GPU 负载，但 `git_commit.txt` 写成了 `unavailable: workspace has no git repository`。这不是 GitHub 状态真的缺失，而是旧训练器从未执行 Git 发现，直接硬编码 unavailable；项目的真实 Git 根在 `xrd_robustness` 的父目录 `E:\AI4science`。

该缺口不改变模型、数据或参数合同，但会让七条正式结果缺少可核验的提交来源，因此不能以“训练已经开始”为理由继续累积不完整证据。队列被主动停止，部分 checkpoint 与 run 文件整体移动到 `outputs/v9_method_transfer_tuning/aborted_provenance_probe_20260726_1147`，不恢复、不计入 7-run。训练器改为从项目路径执行 `git rev-parse HEAD`，并新增父仓库解析回归测试。修复同步 GitHub 后，首条 run 仍从 optimizer step 0 重新开始。

## 2026-07-26：七条 Validation 调参选择冻结在两个中间候选值

本次明确授权的笔记本阶段完成了全部七条预注册、完整预算的
Validation-only runs。每条 run 均在共同 seed、sampler、pair schedule、
accepted parameter-pair stream 和暴露预算下达到 30,650 optimizer steps。
最终审计还实际触发了 fail-closed 恢复路径：审计器与生产器的统计身份
不一致，以及满步恢复会把 prediction rows 重写为空，这两个工程问题均
在不改变模型、候选网格、seed、优化预算、数据暴露或 split 边界的前提
下修复。受影响的 Residual lambda=0.2 Validation 预测从未变化的已验证
checkpoint 确定性重放，并且只有在指标与原始完成 history 精确一致后
才被接受。

预注册选择规则只使用冻结的统一 Validation 子集，先要求通过 in-range
guardrail，再按 mean single-factor OOD Macro-F1 对合格值排序。JS 只有
3.0 合格：相对 baseline 的 OOD 增益为 0.0498666，in-range Macro-F1
变化为 +0.0180273。Residual 的 2.0 与 20.0 均合格，但 2.0 的 OOD
增益为 0.0194593，高于 20.0 的 0.00538575。因此正式冻结值为
`lambda_JS=3.0` 与 `lambda_res=2.0`。

这一结论只关闭参数选择证据，不证明多 seed 稳定性，也不构成正式方法
性能结论；它不授权 15-run 正式比较、simulated Test、real XRD、真实
适配或 V10。

## 2026-07-26：把 50 epoch 重新界定为固定预算，而不是已证明收敛

七条调参 run 完成得快，促使项目重新检查“50 epoch 是否充分”。只读审计发现，现有产物不能执行原本设想的 best-epoch 检查：训练合同把
`validation_interval_steps` 设为完整预算 `30650`，所以每条
`history.json` 虽有 50 条训练记录，却只有 epoch 50 一次 Validation；
训练器又只覆盖保存 `last.ckpt`，没有逐 epoch checkpoint。因此
best epoch、epoch 50 与 best 的差距、末 10–15 epoch 的 Validation ID/OOD
斜率，以及是否已经过拟合，都无法从现有七条结果恢复。

进一步核对证明这不是“Validation 实际执行但日志漏存”。公平性合同明确写着
`same_checkpoint_rule=last_fixed_budget_checkpoint`，训练器也只有到完整
30,650-step interval 才进入 evaluation；七个 canonical run 中不存在隐藏的
TensorBoard/event、metrics CSV、历史 Validation 记录或旧 epoch checkpoint。
最终 `last.ckpt` 保存了 optimizer 与 RNG 状态，因此未来在经过确定性恢复核验
并获得单独授权后可以继续向前训练，却不能回到 epoch 30/40 补出历史曲线。

这次审计同时发现了执行合同与语义描述的矛盾：操作字段明确实现 fixed-budget
endpoint selection，但 `evaluation.validation_role` 仍宣称包含 early stopping
和 checkpoint selection。七条 run 遵循的是前者，因此结果没有失效；后者则是
当前证据不支持的陈述，必须在冻结正式 15-run 协议前选择并统一，不能同时保留
两种说法。

训练侧证据反而说明优化过程仍在移动。按每个 epoch 覆盖区间的
`global_step` 中点对最后 10 条 history 做普通最小二乘回归，七条 run 的
classification objective 斜率均为
负且拟合度都高于 0.90；入选的 JS 3.0 为每 616 step `-0.01438355`，
Residual 2.0 为 `-0.00700665`。排除只有 466 step 的最后一个不完整 epoch
后结论不变。七条 run 的学习率也始终保持 `1e-4`，没有调度器提供“末端已
充分退火”的证据。动态谱图每轮变化，所以训练目标继续下降并不能推出
Validation 必然继续提高，也不能排除过拟合；它只能否定“已经由现有证据
证明收敛”的说法。

据此作出范围限定：

- `lambda_JS=3.0` 与 `lambda_res=2.0` 仍是公平、统一的 30,650-step
  固定计算预算下的合法选择；
- 不再把这次选择表述为“50 epoch 已充分收敛”，也不把它外推为更长预算下
  必然保持相同排名；
- 不因训练便宜而直接把正式 15-run 改成 75 或 100 epoch。若正式预算改变，
  必须先在新的统一 horizon 上重新验证完整七候选网格；只延长已选方法不能
  证明 lambda 排名仍稳定；
- 可以先把 ERM、JS 3.0、Residual 2.0 的延长作为是否值得完整重调的诊断，
  但这种 finalist-only probe 不能重新冻结 lambda，也不能加入已经消耗完一次
  pre-Validation 修订机会之外的新候选值；
- 新增学习率调度器属于另一项优化合同变化，也必须重新调参，不能作为无害的
  工程修补；
- 当前 15-run 仍为 `0/15` 且未授权；在 fixed-budget endpoint 与 early
  stopping 两种协议中作出明确选择并修正合同语义前，不得启动。Test 与真实域
  边界保持锁定。

权威只读审计为 `xrd_robustness/reports/v9_tuning_convergence_audit.json`。

## 2026-07-26：统一改为 100 epoch 上限加预注册 early stopping，并完整重跑候选网格

50-epoch 审计证明旧七条 run 只有终点 Validation，因而既不能证明已经
收敛，也不能证明继续训练一定有效。用户据此明确选择不只补跑当前赢家，
而是在保持候选网格、seed、模型、动态谱图暴露边界和 Validation-only
边界不变的条件下，从 optimizer step 0 完整重跑七个候选。这样避免把旧
30,650-step 赢家直接外推到一个不同的优化制度。

新制度预注册为：最多 100 epochs / 61,600 optimizer steps；每 5 epochs /
3,080 steps 做一次 Validation；至少训练 50 epochs；监控 single-factor
Validation-OOD Macro-F1 的均值；`mode=max`、`min_delta=0.001`、patience
为 4 次 Validation。保存 `best.ckpt` 和 `last.ckpt`；主指标在
`min_delta` 内时先比较 Validation-ID Macro-F1，再选择更早 epoch。没有
引入 learning-rate scheduler。

这一改变也修正了公平性表述：各方法共享同一最大预算和同一停止规则，
但允许 early stopping 产生不同的实际步数；因此审计共同训练前缀的
sampler、pair 与 parameter hashes，而不再要求每条 run 的最终完整流哈希
或实际步数相等。旧 50-epoch 选择仍作为历史固定终点证据保留，但不再是
新制度下的最终 lambda 结论。15-run 正式实验、simulated Test、real XRD、
真实适配和 V10 仍未获授权。

## 2026-07-26：在首条未完成 run 阶段把 Validation 间隔改为 10 epochs

初始 100-epoch 合同按每 5 epochs Validation、patience 4 启动后，首条
Dynamic ERM 在 epoch 14 / optimizer step 8,624 时仍未形成任何可计数的
最终结果。实测确认训练主体很快，而包含 11 个面板、23,199 条预测的
Validation 是新增时间的主要来源。用户因此在结果产生前明确将间隔改为
每 10 epochs / 6,160 steps，并把 patience 改为 2。

两套参数都表示连续 20 epochs 没有超过 `min_delta=0.001` 的主指标改善，
因此停止等待窗口不变；变化只减少预定 Validation 次数。旧进程被停止，
其两次 Validation、`best.ckpt`、`last.ckpt`、history 和日志完整隔离到
`outputs/superseded_v9_tuning_5epoch_patience4_20260726_1859`，不得恢复或
计入新七条。候选网格、seed、模型、最大 61,600 步、最少 50 epochs、
监控指标、tie-break、硬件调度及所有数据边界均不变。新七条必须从
optimizer step 0 在独立输出根重启。

## 2026-07-26：删除被取代的未完成运行产物

在新的 10-epoch Validation / patience-2 队列已从 optimizer step 0
健康启动后，用户明确授权删除此前隔离的 5-epoch Validation /
patience-4 未完成运行。该目录包含首条 run 截止 epoch 14 / step 8,624
的 history、日志和 checkpoint，共 27 个文件、87,011,670 bytes。由于
本机安全策略拒绝永久递归删除，目录被送入 Windows Recycle Bin，
原路径 `outputs/superseded_v9_tuning_5epoch_patience4_20260726_1859`
已不存在，仍可由用户在清空回收站前恢复。

这一清理不改变科学合同或当前七条队列：旧运行仍不得恢复到实验队列、
不得计数，也不得用于 checkpoint 选择；候选网格、seed、数据边界、
61,600-step 上限、Validation 间隔和 early-stopping 规则均保持不变。

## 2026-07-26：从匿名 Wyckoff family-disjoint 改为 parent-structure 随机分层划分

在 chemistry-anonymous Wyckoff-family-disjoint 划分下，Validation-ID 与
Validation-OOD 均处于极低水平。项目据此决定不再把 family 隔离作为默认
实验设置，改用 parent structure（CIF / material）作为唯一不可拆分单位。
新的划分使用固定种子 `20260726`，仅按七晶系分层，并随机分配为 Train
70%、Validation 15%、Test 15%。同一 parent structure 生成的 clean、
weak、strong、ID 和 OOD 谱图全部继承同一 split；`family_id` 可以保留作
分析字段，但不得参与任何划分决策。

这不是对旧结果的后处理修补，而是实验总体设计的根本变化。因此，旧
family-disjoint split 下的七条固定预算结果、选择结论以及当前 100-epoch
重调中已经完成的第一条结果全部作废，不得用于模型选择、checkpoint
恢复、Test 访问或论文结论；剩余六条旧 split 实验取消。新 split 的
Validation-only tuning 重置为 `0/7`，从实验 1 和 optimizer step 0 开始。

工程实现生成新的 `split_manifest.json`，记录 `material_id`、
`parent_structure_id`、`crystal_system` 和 `split`，并把层级 bootstrap
的独立单位同步改为 parent structure。Validation-ID 仍表示未见过的
parent structure 加 ID 扰动，Validation-OOD 仍表示同一批未见过 parent
structure 加 OOD 扰动；除 split 及其直接统计依赖外，训练方法、扰动
设计和 Test 锁保持不变。

用户已授权从实验 1 重新训练。权威 `xrd_tools` Python 3.11.9 运行时
恢复可用后，新 Train split 上的 candidate-grid Gate 从 epoch 0 重建
五个 epoch 并通过：分类学习信号、互斥 Train 子集 residual probe、
六个候选的直接梯度测量及无 Validation/Test 泄漏检查均通过。当前证据
状态是 manifest、split 审计和当前 split Gate 已完成，训练结果 `0/7`；
实验 1 在本次源码和合同变更提交、推送后从 optimizer step 0 启动。

## 2026-07-27：split pilot 判定——旧 family split 偏难但不是主要瓶颈

实验 1 被用户为修理内存中断后，用户预注册了一个两步 pilot 判定框架，
用最小代价回答"性能低是不是旧 family split 造成的"：第一步只读审计
新划分本身；第二步在隔离目录跑单条 30-epoch Dynamic ERM，判据为
Validation-ID Macro-F1 若升到 0.6+ 则旧 split 过难是主因，若仍在 0.4
左右则问题不在 split，应转查 backbone、数据质量或任务难度。

数据集 pilot 全部通过：数量精确 9,842/2,109/2,109，七晶系分层最大
偏差 0.000379，14,060 个 parent structure 零跨 split 泄漏，各 split
七类齐全，且被中断 run 的 11 个视图 manifest 全部只含 Validation
material ID。新划分的工程实现被排除为嫌疑。

算法 pilot 跑满 18,480 步预算，三次 Validation 轨迹为 ID
0.3714 → 0.4240 → 0.4212，mean single-factor OOD 0.2967 → 0.3419 →
0.3557，gap 收窄至 0.065。与旧 family split 同方法同 seed 的对照
（epoch 70 最佳 ID 0.3875 / OOD 0.3300）相比，新划分用三分之一预算即
超过旧划分历史最好成绩，但 ID 在 epoch 20-30 间平台化于 0.42 附近，
远未达到 0.6+。

科学结论：旧 family-disjoint split 确实附加了约 0.04-0.05 的难度，
但它不是 ID 性能停留在 0.4 量级的主要原因；gap 小且持续收窄说明泛化
机制正常，瓶颈是拟合能力或任务/数据本身。下一步的研究方向依次为
backbone 容量与特征表达、模拟数据质量、任务内在难度。该 pilot 为
development-only 证据，不得用于模型选择或 checkpoint 复用；正式 7-run
重启继续等待电脑修复（预计 2026 年 8 月）与新的显式授权。

## 2026-07-27 Foundation Gate 3: backbone diagnosis changes the next comparison

After the parent-structure split pilot ruled out split difficulty as the
dominant explanation, the project tested backbone capacity under a matched
Clean diagnostic. ML4pXRDs ResNet-18-GN improved level-0 Macro-F1 from
PAMPT-B3's `0.532749` to `0.652168`, mean single-factor OOD Macro-F1 from
`0.289676` to `0.403163`, and Train accuracy from `0.638494` to `1.0`.

This evidence changes the next research direction: PAMPT-B3 is treated as a
major foundation bottleneck, so the CNN backbone contract must be frozen
before reopening matched Dynamic/JS/Residual comparisons. It does not prove a
final model choice and does not authorize the formal seven-run queue,
simulated Test, real XRD, real adaptation, or V10.

## 2026-07-28 ResNet Clean contract selection

Three preregistered single-factor Clean diagnostics tested sqrt preprocessing,
Adam, and 5-epoch warm-up plus cosine. None improved the primary level0
Macro-F1 over the original identity + AdamW + constant-LR ResNet baseline,
and none reached the fixed `+0.02` threshold. The search therefore stops
without a fourth configuration and restores the simplest original best.

This evidence changes the diagnosis: PAMPT-B3 was a major learnability
bottleneck, but replacing it did not remove the severe parent-structure
train-to-validation gap. ResNet can fit Train essentially perfectly while
Clean Validation remains near `0.65`.

The subsequent single matched Dynamic ERM diagnostic answered the controlled
question positively. Dynamic training improved level0 from `0.6522` to
`0.7197`, in-range from `0.1827` to `0.7179`, mean single-factor OOD from
`0.4032` to `0.6563`, and worst-class F1 from `0.4950` to `0.5810`. The old
Dynamic collapse was therefore primarily a backbone interaction, not evidence
that the frozen perturbation stream is intrinsically destructive. This opens
review of a shared ResNet method-comparison contract, but does not itself
authorize JS, Residual, the formal seven-run, Test, or real XRD.

## 2026-07-28 ResNet lambda Gate reset

Changing the public backbone invalidates PAMPT-derived auxiliary-loss scale
evidence. Backbone-independent semantic and engineering Gates remain valid,
but learned-state, auxiliary-loss scale, backbone-gradient influence, and
lambda tuning must be repeated on ResNet.

The shared ResNet contract is frozen before method comparison. A Train-only
Gate then directly tested the PAMPT grids as scale probes. JS
`[0.3,3,30]` produced negligible/weak/material influence; Residual
`[0.2,2,20]` produced negligible/negligible/weak influence. Neither spans the
required weak/material/dominant bands. The independent residual probe also
failed its preregistered epoch-5 competence criterion, so extrapolating a much
larger Residual grid would not be scientifically justified.

The Gate therefore fails closed. PAMPT lambda results stay archived, the
ResNet candidate range remains unfrozen, and the seven-run remains at 0/7.

## 2026-07-28 ResNet Residual stability Gate closes the probe-repair option

The initial epoch-5 probe failure could have been a transient optimization
effect, so the same fixed one-layer detached probe and thresholds were
preregistered across three Train-only seeds at epochs 3, 5, and 10. The
signal-demonstrated counts were `2/3`, `1/3`, and `2/3`. Because the protocol
required at least `2/3` at both epochs 5 and 10, the result is
`stable_signal_not_demonstrated`.

The outcome is informative: the residual feature norm rose with training, but
probe competence was seed- and milestone-dependent. It is therefore not
scientifically defensible to repair the situation by changing only a threshold
or extrapolating to larger Residual lambdas. Residual candidate reopening and
the 7-run remain closed; a future attempt must be a separately approved,
Train-only preregistered redesign of the residual representation/objective.

## 2026-07-28 V9 narrows to Dynamic ERM versus JS Consistency

The Residual-v1 failure is treated as a valid preregistered negative result,
not as a reason to weaken its Gate. The active paper question is narrowed to
whether explicit JS prediction consistency improves OOD and later Sim-to-Real
generalization over the matched Dynamic ERM baseline.

One JS-only Train-scale revision was preregistered as `[3,30,60]`. Values `3`
and `30` reuse direct ResNet autograd traces; `60` is an exact scalar
reconstruction from the same `lambda=30` trace, with per-batch combined
gradient direction and magnitude guards recomputed. The median ratios
`0.087859/0.877058/1.754115` cover weak/material/dominant and all guards pass.

This freezes only the JS candidate grid. It does not authorize or start the
proposed four-run tuning. Residual-v1 stays archived, Residual-v2 remains a
future separately preregistered research module, and Test/real-XRD locks are
unchanged.

## 2026-07-28 Four-run Validation contract is preregistered without execution

The narrowed research question is operationalized as exactly one matched
Dynamic ERM baseline and three JS candidates at `[3,30,60]`. To avoid
post-result flexibility, the shared 100-epoch/61,600-step budget, validation
cadence, early-stopping rule, seeds, OOD-primary selection metric, in-range
guardrail, and tie-breaks were frozen before any candidate training.

A read-only preflight verified registered file hashes, exact parent-level split
isolation, exact Validation-manifest membership, absence of the output root,
and continued Test/real-data locks. It inspected only manifest metadata, not
Validation spectra or metrics, and loaded no model or checkpoint. The obsolete
PAMPT seven-run switches were fail-closed to prevent accidental execution.
Consequently the contract is auditable and launch-ready only after a separate
human decision; scientific execution remains `0/4 locked`.

## 2026-07-28 Online generation is optimized before restarting the four-run

After authorizing execution, the user stopped the first Dynamic run at epoch 9,
before any Validation check, to remove the online-rendering bottleneck. That
partial run is preserved but excluded from all tuning and selection.

Profiling showed repeated preferred-orientation HKL normalization/ranking and
repeated rendering of the noise-free, background-free quality reference.
Both are structure invariants, so workers now cache them while continuing to
sample and render every perturbed spectrum independently. The matched
64-batch, 2,048-view Gate improved 16-worker prefetch throughput by `27.67%`
and sequential throughput by `47.49%`. Accepted manifest rows, material order,
physics parameters, spectrum arrays and hashes, and quality-Gate counts are
exactly unchanged; maximum absolute spectrum difference is zero.

Because this is a verified engineering acceleration rather than a scientific
factor change, the frozen model, optimizer, simulator parameters, random
streams, budget, early stopping, metrics, and selection rule remain unchanged.
The only valid next execution is a complete four-run restart from step zero.

## 2026-08-03 Ten-run recovery: artifact completion is not a metric result

The cloud-executed paired ten-run was recovered after the local system repair
as a Git-ignored archive. A full manifest audit recomputed all 12 supplied
SHA-256 entries successfully. The archive contains exactly ten best
checkpoints, covering the five frozen seeds and both paired methods, and the
embedded metadata confirms every expected epoch and optimizer step.

This is sufficient to establish that the checkpoint artifact set was exported
intact. It is not sufficient to state a five-seed performance comparison:
the recovered local export does not include an aggregate summary or individual
metric histories. The research record therefore separates the engineering fact
of completed, integrity-verified checkpoints from the unresolved scientific
task of recovering and auditing the frozen-evaluation summaries. No Test or
method-selection claim is opened by this recovery alone.

## 2026-08-03 Correction after authoritative repository synchronization

The recovered local archive by itself remains insufficient to establish aggregate
metrics. Synchronization with the authoritative project repository recovered the
version-controlled ten-run summary and result record, which resolve that
archive-only limitation: all five preregistered paired seeds favor JS
`lambda=60` on the Validation OOD primary metric. This does not open the
simulated Test or real-XRD locks; both remain frozen and unused. The archive is
therefore retained as integrity and checkpoint-recovery evidence, not as the
sole source of scientific metrics.

## 2026-08-03 Simulated-Test infrastructure abort and identical retry amendment

The first authorized local simulated-Test launch exposed an engineering flaw:
the evaluator serially regenerated all 75,924 deterministic panel spectra for
each of ten checkpoints and synchronized GPU output after every small batch.
The GPU therefore waited on redundant CPU work. The user stopped the launch
before any checkpoint result or aggregate metric was written. No Test outcome
was available for inspection, but the partial Test access is recorded rather
than relabeled as unused.

Optimization decisions were made exclusively on 256 Train structures and
synthetic ResNet inputs. Serial rendering was fastest at roughly 500 spectra/s;
4, 8, and 16 threads were slower while remaining bit-exact. Batch 128 was the
fastest GPU candidate at roughly 5.9k spectra/s, and an eight-second sustained
forward sample held 98-100% utilization. Direct and cached-input probabilities
were exactly identical on a 128-spectrum Train prefix.

The retry amendment changes engineering only. Each frozen spectrum is rendered
once into a SHA-256-verified local cache and reused across the unchanged ten
checkpoints. Atomic run state binds source, manifests, simulator, split,
peak-cache manifest, and batch size so an interruption can resume the same
attempt but cannot silently become a modified attempt. Checkpoints, scientific
profiles, evaluation seeds, metrics, primary endpoint, and method-selection
closure remain unchanged. The identical retry is authorized but has not begun;
real XRD remains locked.

## 2026-08-03 Frozen simulated-Test confirmation

The authorized identical retry completed all ten Validation-selected
checkpoints against the unchanged 2,109-parent simulated-Test split, six
single-factor OOD profiles, and three deterministic evaluation-panel seeds.
The engineering amendment behaved as intended: 75,924 unique frozen spectra
were rendered once into a hashed local cache and reused serially across all ten
models. A sustained inference sample averaged 94.25% GPU utilization; the
CPU-bound cache phase remained scientifically and operationally separate.

All five preregistered JS-minus-Dynamic-ERM paired OOD Macro-F1 deltas are
positive. Their mean is `+0.054600`, sample SD is `0.007271`, and the frozen
paired-bootstrap 95% interval is `[+0.048944, +0.060255]`. All five in-range
deltas are also positive. This confirms the simulated-domain robustness claim
without changing the selected method, lambda, checkpoints, seeds, profiles, or
endpoint.

The preregistered seed-20260714 secondary diagnostic remains informative. Its
aggregate Test worst-class delta is slightly positive (`+0.005531`), so the
Validation decline did not reproduce at the aggregate level; however,
monoclinic remains the worst-class bottleneck and negative/positive shift plus
texture retain profile-level declines. The result therefore supports aggregate
robustness improvement, not uniform improvement for every class and condition.
The Test report is now frozen, repeat Test access and Test-guided retuning are
closed, and real XRD remains unused pending a separately designed and authorized
external-validation stage.

## 2026-08-03 — RRUFF-350 expansion collection frozen

The user requested expansion of the measured RRUFF evidence pool to 350. The
scientific decision is to preserve the existing RRUFF-70 byte-for-byte and label
it as `legacy_rruff70`, while adding 280 model-blind samples labelled
`rruff350_extension`, yielding 50 samples per crystal system. The 350-sample
asset is not represented as a fresh independent final test and does not change
the frozen 21/14/35 roles of RRUFF-70.

Official archive scarcity makes unique mineral names impossible at 50 samples
per class. Selection therefore uses unique RRUFF sample IDs, normally caps a
mineral at three samples per crystal system, and records the single required
hexagonal relaxation to four Vanadinite samples. Although the staged policy
allowed a Pearson ceiling up to 0.995 if required, the largest actual
correlation at inclusion among the 280 new samples was 0.957184. One frozen
sample, R230005 Edwindavisite, was absent from the current official archive and
was retained only after its local frozen spectrum and DIF hashes matched the
RRUFF-70 manifest. No model outputs or real-XRD inference were used.

## 2026-08-03 — RRUFF-371 expansion and real-domain role revision

Before any model accessed RRUFF spectra, the user authorized enlarging the
external evaluation cohort beyond 300 while retaining exact class balance. The
new version is `rruff-real-pxrd-371-v2`: 70 legacy development samples plus 301
model-blind extension samples, with 53 total and 43 extension samples in each of
the seven crystal systems. The previous `rruff-real-pxrd-350-v1` was not
overwritten. An independent manifest audit confirms that all 350 parent IDs and
their canonical-spectrum, RAW, and DIF hashes are unchanged; the 21 additions
are exactly three per crystal system.

The scientific role also changed prospectively. The legacy RRUFF-70 is now
reserved for real-domain interface development and few-shot adaptation, while
the 301-sample extension is reserved for external evaluation. This makes the
old 21/14/35 contract historical; it remains execution-disabled and is not to
be silently edited or reused as the current protocol.

Two samples per class in the old adaptation-validation set are too unstable for
learning-rate and early-stopping selection: one changed classification alters a
class recall by 50 percentage points. The recommended replacement is therefore
five support and five validation samples per class (35/35), enabling nested
0/1/2/3/5-shot learning curves and reducing per-class validation granularity to
20 percentage points. This allocation is a design recommendation, not yet a
frozen v2 role manifest or authorization to train.

The model-blind overlap audit found that 34 of the 301 extension samples share
23 normalized mineral names with the legacy 70. The primary 301-sample endpoint
therefore measures experimental measurement-domain transfer, not guaranteed
generalization to unseen minerals. Any unseen-mineral claim must use a
separately prespecified mineral-group-disjoint sensitivity cohort. No model,
checkpoint, prediction, or real-XRD inference was used for these decisions.

## 19. 2026-08-04 opXRD 铁电可行性审计：NO_GO

项目曾探索是否可以从统一实验 PXRD 数据库 opXRD（92,552 条谱）建立
"铁电及相关功能氧化物/陶瓷材料域的晶系分类真实谱数据集"，实现"广域模拟
七晶系预训练 → 少量目标域真实谱 few-shot adaptation"的路径。

经过完整模型盲审计后，结论为 **NO_GO**：

opXRD 的数据组成与铁电陶瓷域完全不匹配：
- 唯一有结构标签的贡献者 EMPA（770 条）研究卤化物钙钛矿和金属氮化物，
  而非铁电氧化物陶瓷；
- 最大两个贡献者 LBNL（70,012 条）和 INT（19,796 条）的相信息字段为空，
  无化学组成、无空间群标签；
- 在 5,770 条采样文件中，零条记录匹配 19 个铁电材料家族规则。

这个结果不是筛选阈值过于严格导致的——而是 oppXRD 的数据采集对象与铁电
陶瓷晶体学分类任务之间不存在可行的交集。即使降低标准，也不应宣称 opXRD
中存在可用的铁电陶瓷数据集。

科学决策：放弃 opXRD 路径，按原设计继续推进 RRUFF-371 真实域适配路线。
opXRD 保留为未来更广泛的 PXRD ML 研究资源，但其贡献者数据和材料类型
不适用于铁电陶瓷域任务。

审计遵守了所有模型盲约束：未加载 checkpoint、未执行真实谱推理、未修改
RRUFF-371、未重新打开 V9/JS/simulated-Test 合约。所有新代码（5 个脚本、
4 个测试文件、2 个配置文件、2 个报告）均已测试通过并提交。

## 20. 2026-08-06 — 目标域从"公共数据库铁电七晶系"重构为"谭启组钙钛矿功能陶瓷相态识别"

opXRD NO_GO 的深层教训不是"这个数据库不行，换一个就行"，而是：任何
公共 XRD 数据库都不是为功能陶瓷相态分类而采集的。强行从公共数据库中寻找
铁电陶瓷数据，本质上是试图把别人的数据塞进自己的科学问题——这条路
即使偶然有几条记录命中，也无法提供有统计意义的训练和评估。

因此项目做出根本性方向修正：

### 真实域不应再从公共数据库中硬找

最自然的特定真实域，应直接从谭启组的材料体系和历史实验数据中定义：

> **GTIIT / Tan Lab 钙钛矿功能陶瓷真实 XRD 域**

### 下游任务不应再强行保持"七晶系分类"

谭启组的材料主要是钙钛矿及相关功能陶瓷，结构集中在立方、四方、菱方、
正交及其共存状态，不可能自然覆盖全部七晶系。强行凑七类会造成严重类别
不平衡和"材料家族 = 标签"的泄漏。

正确的问题是谭启组论文反复研究的核心：

> **掺杂与加工如何引起相结构演化、相共存和第二相形成，并进一步影响
> 储能/压电性能。**

对应的分类方案：

| 类别 | 含义 | 组内实例 |
|---|---|---|
| Single phase | 单一主导钙钛矿相，无明显第二相 | 低掺杂、相纯陶瓷 |
| Polymorphic coexistence | 多种钙钛矿对称性共存，如 R–T、T–PC、R–T–C | PSNZT、BNBT |
| Secondary phase | 钙钛矿主相与非钙钛矿第二相共存 | BCZT–SBT 中钨青铜相 |

这不是临时发明的分类。BCZT–SBT 工作本身就建立了"单相/多相"的机器
学习标签，并在实验 XRD 中观察到低掺杂时为四方钙钛矿相、从 x=0.05
开始出现钨青铜第二相。BNBT 工作又明确涉及 R–T–C 多相共存。

如果三分类数据不够，第一版先简化为 single-phase vs multiphase。

### 两阶段架构

- **阶段一（已冻结）：** 通用模拟预训练。继续保留 Dynamic ERM、Dynamic JS、
  七晶系模拟任务、模拟 OOD 和 RRUFF 外部测试。这一阶段学习通用 XRD 表示，
  已经完成且 V9 方法选择关闭。
- **阶段二（新增）：** 谭启组下游任务。去掉七晶系分类头，换成相态识别头。
  比较 Scratch / ERM-pretrained / JS-pretrained 三种初始化，使用相同
  K=1,2,5,10 真实样本预算。

核心科学命题从"七晶系分类"变为：

> **JS 学到的测量稳健表示，是否能以更少的谭启组真实 XRD，完成对功能
> 陶瓷相结构状态的适配。**

### 与当前 JS 项目的衔接

当前项目完全不用推倒。阶段一已完成的工作——ResNet-18-GN backbone、
JS lambda=60、simulated Test 证据、RRUFF-371 外部评估资产——全部保留。
阶段二是在此基础上新增一条研究轴，而不是替换旧轴。

### 数据可行性硬门槛

在启动正式训练前，先做一次组内数据审计：
- 每类至少 20 条独立物理样品，最好 30 条以上；
- 每个标签不能只对应一个材料家族；
- 必须是 `.raw/.txt/.xy` 原始数值文件，不能只截论文图片；
- 标签来自 Rietveld、相分析或明确实验记录；
- 按配方—批次—样品分组划分，重复扫描不得跨集合。

现有 PLZT–PNN 约 10-20 条独立原始谱，足够做数据管线和 Few-shot pilot，
但不足以单独成为最终 benchmark。真正的机会在于谭启组已发表或参与的
多个相关体系：PLZT–PNN、PSNZT–ZnO、BCZT–SBT、BCZT–BNZN、BNBT，以及
其他 BNT、KNN、BaTiO3 基储能陶瓷。

### 不变边界

以下不受本次决策影响：
- V9 方法选择已关闭；
- JS lambda=60 已冻结；
- simulated Test 已完成并冻结；
- RRUFF-371 仍是外部矿物域评估资产；
- real XRD 和 real-domain adaptation 仍锁定。

### 新增工作

- 谭启组相态分类体系定义；
- 组内数据审计管线；
- Few-shot adaptation 协议（support/query 划分、K-shot episodes）；
- ERM-pretrained vs JS-pretrained vs Scratch 比较设计。

## 2026-08-11：从代码与原始产物反校正文档叙事

本次不采用项目说明文字作为结论，而是逐项检查了模型输出、目标函数、模拟器、
split manifest、confusion matrix、逐条预测和哈希绑定。由此做出三项需要保留
在研究历程中的校正。

第一，当前已完成任务是七晶系分类鲁棒性，而不是物理参数反演。模拟器中的
位移、展宽、背景、噪声和择优取向是生成观测视图的 nuisance variables；模型
没有输出晶格常数、相分数、应变或其他反演量。因此申请叙事可以强调
"现实测量—物理模拟—稳健学习—Sim2Real 评估"，但不能把本项目包装成已经完成
的 inverse solver。

第二，发现 simulated-Test runner 的一个诊断字段实现错误：它先按真实晶系筛成
单类子集，再计算七类 Macro-F1，导致命名后的 `per_crystal_system_f1` 被压低并
丢失来自其他真实类的 false positives。决定只修未来 runner，并从完整 confusion
matrix 独立生成纠错 sidecar；不改 10 个哈希冻结的 per-run JSON，也不重跑 Test。
360/360 个 profile 的旧命名字段需要纠正，但正确 `per_class_f1`、主 Macro-F1、
worst-class、配对差值和 bootstrap 均不受影响。

第三，证据范围必须降到实际可审计的层级。正式 split 的 exact parent fingerprint
跨集合为 0，但有 47 个 exact formula 跨集合、涉及 585 条记录，12 个 formula
同时出现在 train/validation/test；因此撤回 "family-aware/family-disjoint" 的当前
表述，保留 exact-parent-disjoint 结论。RRUFF-301 的 150 个 few-shot 指标可由
34,650 条 prediction rows 重算，固定 231-ID test membership 也可核验，但原 runner、
support IDs、预执行授权、执行日志及 code/runtime binding 缺失。旧结果改归类为
retrospective validation，不能继续称为 confirmatory evidence。

工程上新增了 fail-closed retrospective contract、逐 artifact 验证等级和确定性
episode plan。计划是新的复现计划，不冒充历史计划；`run-replay` 即使收到任意
authorization path 也必须在加载模型或谱图之前拒绝。若论文必须提出 confirmatory
真实域结论，唯一合规路径是未来另行审查并授权一次 prospective execution；不能
通过补文档或重命名旧产物来恢复不存在的历史 provenance。
