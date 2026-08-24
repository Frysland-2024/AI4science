# 项目历史档案（Project History）

> 本文档是 AI4science / XRD 项目完整历史历程的汇总档案，由散落在多个来源的历史记录整合而成。
>
> **汇总时间：** 2026-08-23
> **性质：** 历史档案，非当前执行合同。文中保留的版本号（V6/V7/V8/V9.2/V9-T）、负结果、失败机制和决策反复，都是历史原貌，只为完整记录"项目如何一步步走到今天"，不代表当前公开叙事或当前可运行范围。
> **当前状态以** `CURRENT_STATE.md` 与 `xrd_robustness/reports/RESULTS.md` 为准。

---

## 内容来源

本文档按"来源"分区整理，各分区保持原文完整，不删改、不美化：

| 分区 | 来源文件 | 内容 |
|---|---|---|
| 第一部分 | `PROJECT_JOURNEY.md` | 项目心路历程（最完整时间线：FerroAI → V6/V7/V8/V9.2/V9-T → 2026-08-23） |
| 第二部分 | `.workbuddy/memory/*.md` | 每日工作日志（2026-08-04 至 2026-08-23） |
| 第三部分 | `AI4Science_Project_Handoff_for_Admissions_AI_2026-08-07.md` | 关键结果与里程碑（JS 参数选择、RRUFF-301、zero-shot、错误审计等） |
| 第四部分 | `.workbuddy/memory/MEMORY.md` | 项目长期记忆（核心定位、关键决策、署名分工） |
| 第五部分 | Git 历史恢复（`PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md` + `DECISION_LOG_20260813.md`） | 心路历程续篇（RRUFF-301 v1 bug→v2、Evidence Freeze、论文冻结）+ 决策日志 |

---

# 第一部分：项目心路历程（PROJECT_JOURNEY.md 全文）
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

## 2026-08-13：把 XRD 反演收缩为已知模板条件下的低维样品—仪器联合问题

新的设想希望把当前“测量扰动感知的稳健分类”延伸到 forward-model-constrained
parameter inversion，并以此连接半导体光学量测及更长期的 CT/MRI 反演研究。方向
本身与已有的未来研究身份一致，但原始首版同时反演 `a`、`c`、zero shift、FWHM
和两个背景系数，混合了样品结构、仪器与信号处理参数。参数维数只有六并不意味
前向映射单射：晶格变化和零偏都会移动峰，峰宽会混合多种未建模机制，背景系数
又依赖强度归一化和基函数。当前模拟器也只在 `pymatgen` 生成冻结 peak table 后
施加测量扰动，并没有可微的 `a,c -> peak positions` 链路。

因此决定保留 2026-08-01 的 measurement-nuisance inversion 模块，并另建 sibling
module，而不是覆盖旧设计或把 V9-T 反向包装成 inverse solver。新的最小目标为：

\[
z=(\varepsilon_{\mathrm{iso}},\delta),
\]

其中已知 nominal prototype、固定分数坐标和反射强度；
`epsilon_iso` 表示样品晶格的各向同性尺度变化，`delta` 表示仪器全局 2-theta
零偏。前者的峰移随角度近似按 `-2 tan(theta)` 变化，后者为常量偏移，所以多条
跨宽角域的独立反射提供了原则上的区分信息，但这一点必须由实际 Jacobian/Fisher
谱、参数碰撞搜索和多起点经典物理拟合证明，不能由神经网络拟合分数代替。

版本阶梯冻结为：先做 `epsilon_iso + delta`；Gate 通过后才考虑
`epsilon_a + epsilon_c + delta`；再后才加入仅代表 renderer 的 effective width；
背景最后进入固定、尺度可解释的 basis。任何一级不可辨识都回退到更低维目标，
不得通过增加网络容量掩盖。一个月的正式学习比较固定为同一 ResNet 的两个
objective：监督回归，以及监督回归加正号的 measurement discrepancy；100% 和一个
预注册低标签比例只是两种 label-budget strata，不扩展成新的模型族。Bragg-law
least squares 与同前向模型的 multi-start nonlinear fit 只承担 Gate 0 和物理参照，
并加入不同峰形、角度相关展宽或不同背景族的 operator-mismatch panel，避免只在
同一 renderer 上制造 inverse-crime 式成功。

四周顺序被固定为：第一周完成单 prototype renderer、数值梯度验证和可辨识性
Gate；第二周只完成 supervised baseline；第三周在完全相同模型上加入
forward-consistency，并只用 Validation 选择小 lambda 网格；第四周冻结选择后评估
新模块自己的 clean/noise/parameter-shift/operator-mismatch panels，并形成 2–4 页
技术报告。三条结果路径都允许保留：参数误差改善是正向 inversion 结果；只有谱
残差改善只能称 forward fit 更稳；不可辨识或 naive consistency 无效则形成负结果。
这份排期仍是 prospective design，不等于数据生成、训练或评估授权。

本次只完成 sealed scientific contract，没有授权实现、数据生成、训练、推理、
simulated Test 或 real XRD 访问。新项目也不使用“V10”名称，因为该名称已属于
仓库中冻结归档的 measurement-supervised residual 机制。它与 CT/MRI 和 optical
scatterometry 共享的是“把已知采集算子显式用于逆推断”的方法论，不意味着物理
模型、损失函数、可辨识性或难度相同。

## 2026-08-23：压缩工作树，保留结论与可恢复历史

本次仓库整理是工程和证据治理决策，不改变已经冻结的科学结果。工作树中过时的
单次脚本、重复报告、退役配置和与退役分支绑定的测试不再继续作为“活跃代码”
保存；PAMPT、Residual、V10、opXRD、RRUFF-70 等分支的关键门控结论被合并到
`xrd_robustness/reports/EVIDENCE_INDEX.md`，科学决策仍由本历程文件保留。整理前的
完整跟踪文件可从 Git commit
`f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217` 精确读取，因此从当前工作树删除不等于
抹除历史，也不允许重写或美化原有负结果。

证据状态同时作如下校正：RRUFF-301 已有产物能够在声明的核验层级上通过内部一致
性检查，150 个 few-shot 指标可由 34,650 条 prediction rows 重算，固定的 231-ID
test membership 也可核验；但原始执行的 runner、support IDs、预执行授权、日志和
完整 code/runtime binding 缺失。因此它继续只作为 retrospective validation，不能
称为 prospective confirmatory evidence。补做正式 provenance 不是当前论文与证据
整理的 blocker，而是已知限制和内部治理事项；只有未来出现必须提出 confirmatory
真实域结论的新科学问题时，才另行审查一次 prospective execution，不能用补文档
倒推不存在的历史治理链。

未来研究方向也需要区分“历史阶梯”和“当前目标”。2026-08-13 的
`(epsilon_iso, zero_shift)` 低维联合反演仍保留为辨识性收缩过程中的历史设计；
2026-08-15 封存的已知模板四方晶系 `(a, c)` robust lattice-parameter inversion
模块取代它，成为当前 future-module target。该取代只改变未来模块的科学设计优先
级，不授权实现、数据生成、训练、推理、simulated Test 或 real-XRD 访问。

整理后的边界明确为：科学设计由冻结 V9-T 与 sealed future modules 表述；工程实现
只保留当前可维护入口和核心库；完成证据由机器可读摘要、哈希审计和合并证据索引
承载；假设与未决风险包括 RRUFF 历史 provenance 不完整、真实铁电实验室 XRD 尚未
建立外部有效性、JS 增益并非对所有类别和扰动都一致。仓库体积或文件数量的下降
不构成新的科学证据。

## 2026-08-23：公开发布范围收束为 V9-T 模拟证据主线

本次公开发布采用“当前论文最小充分叙事”原则：公开仓库只呈现 V9-T 的研究问题、
冻结方法、simulated Validation、simulated Test、可复用实现和论文写作状态。内部
研究历程、候选路线筛选、执行治理细节以及未进入当前论文的未来方向不再作为公开
入口，也不作为读者理解当前结果的前置条件。

这一决定只改变公开信息架构，不改变已完成实验、冻结数值或方法选择。本文件继续
在本地保留完整研究历程，但从 Git 跟踪范围移出，并由仓库根 `.gitignore` 精确排除。
后续若再次调整公开范围，必须先在本地历程中追加理由，不得借公开版精简改写既有
研究过程。


---

# 第二部分：每日工作日志（.workbuddy/memory/）


<!-- 来源: .workbuddy/memory/2026-08-04.md -->
# 2026-08-04 Work Log

## opXRD Ferroelectric Ceramic PXRD Feasibility Audit v1.1 (Revised)

### Result: NO_GO (confirmed on evidence after parser fix)

### v1.0 (87571f2) — INVALIDATED by user
- Parser bug: failed to extract CNRS basis elements and lattice→crystal system
- Falsely claimed "only EMPA has structural labels"
- Reported 0 candidates (false negative from parser failure)

### v1.1 (2ede4f6, cd6c084) — Revised
- Fixed parser: lattice→crystal system (100% CNRS), basis→elements (85% CNRS)
- Parser reproduction gate: FullStr=912 matches paper exactly; EMPA SG=63% matches paper
- Full census of all 2680 labeled-source records (CNRS+EMPA+HKUST+USC)
- Result: 5 candidates (3 BiFeO3, 2 SrTiO3_related) — NO_GO confirmed on evidence
- 1896 records with crystal system, 613 unique CNRS compositions (MOFs/zeolites/coordination)
- CNRS SG=0% documented as Zenodo 14254270 data version limitation

### Constraints Respected
- No model checkpoint loaded
- No real-XRD inference run
- RRUFF-371 not modified
- JS/V9/simulated-Test contracts not reopened

### Git
- Commits: 87571f2 (v1.0) → 2ede4f6 (revision) → cd6c084 (summary update)
- Branch: main, synced with origin/main ✅
- Fix: switched from schannel to OpenSSL backend (`git config http.sslBackend openssl`)


<!-- 来源: .workbuddy/memory/2026-08-06.md -->
## 2026-08-06 / 2026-08-07 (跨午夜会话)

### 关键审计发现: RRUFF-301 v1 split bug
- RRUFF CELL PARAMETERS 把 trigonal 全标成 "hexagonal"
- v1 split 导致 hexagonal=86, trigonal=0, test=241 (not 231)
- v2 fix: DIF space_group + pymatgen.SpaceGroup 区分 hexagonal/trigonal
- 正确 split: 301=70 adapt + 231 test, 43/class × 7
- 实验重跑中 (run_rruff301_confirmatory.py v2)

### 谭启组 Obsidian 知识库数据接入
- 从 SharePoint 下载 OneDrive_2026-08-06.zip (1.1 GB)
- 解压到 `04_external_lab_data/GTIIT/09_piezoelectric_ceramics_obsidian/`
- 606 个原始条目，450 个文件成功提取（156 个 SEM .tif 因中文文件名编码问题未提取，不影响 XRD）

### XRD 数据收获
- **反铁电 PZT 项目** (`projects/2025 anti-ferroelectric/`):
  - 20250910_XRD: PZT937 (3 scans) + PZT973 (3 scans) = 6 raw
  - 20260312_XRD: PZT93/95/97 变温 26-260°C (7 steps each) + room temp = 24 raw
  - 20260317_XRD: PZT93/95/97 各 4 次重复扫描 = 12 raw
  - 20260415_XRD: PZT937/973 不同烧结条件 = 8 raw
- **Sm-doped 压电** (`projects/2025 Sm-doped piezoceramics/`):
  - 20250910_XRD: ZTS05/1/2/3 = 4 raw
- **合计 55 raw + 55 txt + 45 rasx，全部验证可访问**

### 其他项目数据
- H011 (China-made raw materials): dielectric VT, SEM, EDS
- EBSD for piezoceramics: SEM image, h5oina data
- 介电数据分析: example_PNN50PZ18PT32 数据
- 谐振频率高介电常数项目
- 汕大广以3D打印压电项目

### 对相态任务的影响
PZT 反铁电项目是当前最有价值的资产：PZT93/95/97 表示不同 Zr/Ti 比
(93%PZ, 95%PZ, 97%PZ)。高温 XRD 可观察相转变。但这些都是 PZT 体系，
缺少其他钙钛矿家族 (BCZT, BNBT, BNT, KNN) 的数据。

### Delta Tan AM2026 论文获取
- 下载 Advanced Materials 2026 (Sun et al.): BNBT-3 system, Wrec=25.1 J/cm³
- 谭启共同通讯，论文有公开 Source Data
- 下载 Nature Comms 2025 KNN Source Data (XRD patterns, Rietveld data)
- 关键认知：谭启组已在做 ML+压电陶瓷，用户项目可定位为"互补"方向

### RRUFF Pipeline Test 构建与结果
- 从 RRUFF 源归档（3000样本池）独立抽取 35 样本（5/class × 7）
- 与 RRUFF-371 完全无重叠，专用管道测试
- 预处理合同：10-80°, 0.02°步长, 3501点, linear interp, max norm
- 预处理管道对齐审计通过（模拟 ↔ RRUFF 完全一致）
- 波长审计：34/35 为 CuKa，波长不是问题

**Pipeline Smoke Test 结果（5 seed JS vs ERM）：**
- JS zero-shot acc: 0.2343 vs ERM 0.1886 vs random 0.1429
- JS > ERM 在真实域上依然成立（+4.6pp）
- Per-class 差异巨大：triclinic 0.64, cubic 0.00, hexagonal 0.04
- 失败模式：高对称性(峰少)→模型坍缩到低对称性(峰多)
- 管道完全通畅（triclinic 0.64 证明模型在读真实谱）
- **关键结论**：zero-shot 不够，few-shot 是必需的下一步
- 所有结果仅为诊断，不报论文数字

### Personal.zip 归档整理
- 从 Downloads 解压 Personal.zip 到 `04_external_lab_data/Personal_archive/`
- 983 文件中 982 成功提取（1 个路径过长失败），总计 2.3GB
- Python 脚本修复中文文件名编码（cp437→gbk），乱码已解决
- **XRD 重点**：Yifan's Work of Piezoceramics/XRD/（65 raw + 49 rasx + 41 jip + 4 PDF）
  - 样品系列：S053、S009C、NN、H017/H021
  - 日期批次：20230814 至 20231226，含 depolarized 变体和 Ti 掺杂
  - 与 Phase 2 谭启组钙钛矿功能陶瓷直接相关
- 其他成员：Sunny Song (ALD)、Yixin Yang (TEM/FIB)、Fuming Zhang (学术文档)、Tong Wu (Raman) 等
- 压缩包路径较长时不删除，保留原文件


<!-- 来源: .workbuddy/memory/2026-08-07.md -->
# 2026-08-07

## Calibration Analysis — ECE, NLL, Brier, Confidence Distribution
- 基于现有 predictions（无需重新训练），对 V9 关键实验计算校准指标
- 覆盖 8 个实验：4-run tuning (ERM/JS λ=3/30/60)、method transfer (ERM/JS λ=3/30)、foundation_30e
- 核心发现：
  - JS 一致性大幅改善校准：ERM ECE=0.274 → JS λ=30 ECE=0.181，下降 34%
  - λ=30 校准最好但 λ=60 准确率最高（66.0%），存在 tradeoff
  - ERM 严重过度自信：错误预测置信度仍高达 0.84
  - JS 改善了正确/错误置信度的分离
- 输出：`outputs/calibration_report.html`（交互式报告）+ `outputs/calibration_metrics.json`（完整数据）
- 已 commit + push 到 GitHub (a1966ba)
- 脚本：`tmp/calibration_analysis.py`（被 gitignore 排除）

## V9-T 60×90cm 学术海报样张
- 用户上传胡浩天海报（INFORMS-style 学术海报）询问能否复刻 → 用 Matplotlib GridSpec + fig.add_axes 完成
- 海报版式：标题横幅 / 研究背景 / 创新贡献 / V9-T 框架 / A-B-C 方法模块 / Validation+Test 柱图+汇总表 / 结论 / 致谢-交付-联系
- 内容全部使用 V9-T 项目实际数据：JS Consistency λ=60、5-seed Val OOD +0.0466、Test OOD +0.0546、Phase 2 Tan Lab 真实域规划
- 输出文件：
  - `outputs/poster_v9t_60x90cm.pdf`（矢量，打印用）
  - `outputs/poster_v9t_60x90cm.png`（低分辨率预览）
  - `outputs/poster_v9t_60x90cm_v2.png`（最终版本，550 KB）
  - `outputs/poster_v9t_preview.png`（1500×2250 优化版）
- 脚本：`tmp/poster/generate_poster.py`
- 经验教训：matplotlib `add_axes([x, y, w, h])` 期望 0-1 比例，必须除以 W/H 转换 cm；之前用 `W/2 - 1.0/W` 实际是 cm 单位导致结论区宽度爆掉 30×。已修复。

### XRD.zip 归档整理 (GTIIT)
- 解压到 `04_external_lab_data/GTIIT/11_xrd_archive/`
- 504 文件全部提取，24 MB，47 个项目批次（2020.8–2021.9）
- 编码修复：`Ú½ÿµ©®` → `高温XRD`
- 文件类型：223 raw, 221 TXT/txt, 41 doc, 4 rasx, 4 ras, 4 asc
- 主要项目类型：高温 XRD (PP膜ALD)、MXenes、ALD涂层、Co-MOF、PZT陶瓷、AlN/BN粉末
- **与 Phase 2 相关**：Shiyi PZT (4 raw) + varistor PZT 数据可直接纳入钙钛矿相态分析

### OneDrive_2026-08-07.zip 归档
- 5 文件，182 KB，并入 `11_xrd_archive/XRD/XRD_50 and 200 cycle TiO2/`
- TiO2 ALD on AC electrode (50/200 cycle)，含测试条件 .doc

### OneDrive_1_2026-08-07.zip 归档
- 6 文件，273 KB，并入 `11_xrd_archive/XRD/`
- 华丰 CuOx mask XRD（最内层/最外层外表面），2021.1.5，含 .raw/.rasx/.txt

### GTIIT 目录重构
- 从 12 个编号目录重构为按数据类型分类：`XRD/` `Raman/` `metadata/`
- XRD/library: 合并原 01+11（515 文件，49 项目）
- XRD/perovskite: 合并原 02+03+04（34 文件，PLZT + 多孔 PP）
- XRD/han_group: 原 05
- XRD/obsidian_vault: 原 09（707 文件，1.6GB）
- Raman: 原 06
- metadata: 合并原 07+08+10（AI agent + 综述 + KNN 论文数据）
- 旧编号目录移至 `_old/`，创建 README.md 文档

### 04_external_lab_data 大一统
- 确认 DECLMSE、WICSCI2025、Personal_archive 全部来自 GTIIT
- 统一归入 GTIIT 下，按数据类型分类：simulation, microscopy, dielectric, literature, personal_docs, former_members
- 04_external_lab_data 精简为单一 GTIIT/（12 GB, ~5900 文件）


<!-- 来源: .workbuddy/memory/2026-08-08.md -->
# 2026-08-08 工作日志

## 撰写 Research Interest 申请文案

基于项目完整背景（CURRENT_STATE.md、PROJECT_JOURNEY.md、CODEX_HANDOFF.md、
FUTURE_RESEARCH_DIRECTIONS.md），为用户撰写了 5 条关键 research interest 文案，
中英双语，保存至 `00_project_context/RESEARCH_INTERESTS.md`。

五条 RI 覆盖：
1. 测量稳健 XRD 表征学习（Phase 1 已完成证据）
2. 模拟到真实少样本相态识别迁移（Phase 2 设计已冻结，执行未开始）
3. 模拟器 nuisance parameters 弱监督表征解耦（未来方向，V10 负结果为直接动机）
4. 以独立科学实体重新定义样本效率（未来方向）
5. 预注册可复现科学 ML 方法论（贯穿项目的立场）

每条 RI 均标注了证据状态（已完成/设计中/未来方向），避免在申请文书中
做出未经证实的声明。


<!-- 来源: .workbuddy/memory/2026-08-13.md -->
# 2026-08-13 工作日志

## 数据归档：GTIIT 新增 Raman 数据
- 用户提供 `C:/Users/Lenovo/Downloads/Raman.zip`（2.4MB，38 文件），要求存档。
- 原始 zip → `04_external_lab_data/GTIIT/_source_archives/Raman_20260813.zip`
- 解压至 `04_external_lab_data/GTIIT/Raman/` 下，新增 7 个样品文件夹（已去除多余的 `Raman/` 层）：
  - `Raman_CC and ZnCC_zilong_cmjc_2021.8.7`（CaCO3 方解石 + Zn 掺杂，txt）
  - `Raman_ZnCC_zilong_cmjc_2021.8.22`、`Raman_c-ZNCC_zilong_cmjc_2021.12.22`
  - `Raman_Dayakar 6 biomass-AC_cmjc_2021.1.20`（生物质活性炭，PRN）
  - `Raman-3/4/5 AC powder samples-cmjc-fuming-2021`（活性炭粉末）
- 这批是**单点 Raman 谱**（两列 shift/intensity txt/PRN），非 mapping 立方体；与 Tong Wu mapping、MATLAB 项目是不同数据。

## Raman 迁移可行性评估结论
- 主线 backbone：`ML4PXRDResNet1D`，输入 3501 点(XRD 2θ 10-80°)，`encode()` 输出 256 维表征；checkpoint 在 `outputs/v9_resnet_js_simulated_test_checkpoints/checkpoints/`。
- 预处理参考 `evaluation/real_xrd.py` 的 `load_real_xrd`（np.interp 到固定网格 + max 归一化）。
- 硬障碍：Raman 数据**无相态标签**（原项目为 PCA/N-FINDR 无监督）；XRD→Raman 是真正跨模态，预期负迁移；数据量薄（676点×2 mapping + 若干单点谱）。
- 可行方案 A：用主线 backbone 提表征 + 无监督相分离，对比原始光谱 PCA 基线（无需标签）。
- 用户尚未拍板方案（A/B/C 三选）。

## 重大结论：用户职业定位澄清（今日核心）
- 用户坦承想**转行**：本科材料，"烧炉子（合成）没前途"，要从材料合成端转向计算/量测/数据端。
- 明确**不指望发论文**，主线 XRD 项目是转行申请的核心筹码（非学术发表）。
- 决定：先读**海外研究型硕士**（research master）；开学大四，申请季=2026年9-12月（时间紧）；雅思7.5。
- 地区：以色列理工本部 / 加拿大优先；以读书为主，移民为次要长期目标。
- **最终确定领域**：逆问题 / 计算成像 + 机器学习（"打波进去→反解结构/缺陷"内核），不绑定具体波段（光/X光/声/磁/电子束都是实例）。具体落点（半导体量测/工业超声/CT-MRI）尚未最终拍板。
- 主线 XRD 项目 = "逆问题+ML" 的一个实例，是身份定位的硬敲门砖。
- 已同步写用户级长期记忆 `~/.workbuddy/MEMORY.md`（跨项目：转行方向、升学计划、沟通偏好）。

## 申请规划结论（下午补充）
- 申请策略定稿：主力=需套磁研究型硕士（加拿大MASc/澳洲MPhil/日本修士SGU/以色列MSc），保底=欧陆MSc（不套磁），新加坡作直博/就业备选，香港已排除，美国跳过（thesis MS 自费且边缘）。
- 领域方向定稿：主攻计算成像/逆问题，入口=计算显微（材料友好、XRD同源），出口=半导体量测；TCAD备胎（拟做"TCAD+ML代理模型"迷你项目补砖），DFT最后退路。
- 方向树：科学仪器/计算显微 是"横穿各行业的技术平台"，非并列分支。

## 欧陆保底 MSc 调研（已完成）
- 产出：`outputs/europe_msc_backup_list_20260813.md`（清单含课程匹配标注）。
- 核心结论：材料本科最稳保底=比利时 Ghent/VUB Photonics（明确收 Materials Science）+ 挪威 UiT；瑞典 Lund/KTH 可申但需凑物理ECTS（光学/傅里叶/C++ 是潜在缺口）；荷兰 TU Delft/TUe 要求 Physics 本科可能被卡 + 非欧盟学费贵；EPFL 竞争激烈。
- 待补查：米兰理工、TU Wien、Aalto、DTU。

## 战略判断：是否扩大证据链（用户提问，傍晚）
- 读了 CURRENT_STATE / PROJECT_JOURNEY / CODEX_HANDOFF / README，给出分层结论。
- 结论：旧链（模拟 OOD + RRUFF 矿物域）不需要扩，守住 freeze 纪律；真正缺口是"真实功能陶瓷域 + 逆问题方向"的 confirmatory 证据。
- 证据强度 vs 叙事价值错配：最强证据（模拟 OOD）叙事价值中等；叙事价值最高的两块（谭启组 Phase 2、反演 module）都是空的。
- 建议优先级：①推进谭启组 Phase 2 few-shot pilot（第一步是数据审计而非训练）②兜底用反演 module 的 sealed contract 本身作为"研究设计"写进申请。
- 待用户拍板：先做"谭启组数据可行性审计清单"还是"反演 contract 转 CV/SOP 研究设计文字"。


<!-- 来源: .workbuddy/memory/2026-08-15.md -->
# 2026-08-15

## 转行难度咨询 + 时间线纠偏
- 用户问"从材料跑路难度大吗"，给出判断：中低难度，非从零跑路而是从材料实验端切到计算/量测端，数学物理超配 + XRD 项目天然对口。
- **时间线纠偏（重要）**：申请季 = 2026 年 9–12 月，现在 8 月中，窗口仅 1–4 个月（上一轮口误说成"一年"）。用户已明确指出。
- **用户澄清**：GTIIT 无信号处理/光学/C++/算法等课程，补短板不能靠选课，只能自学 + 项目实战。
- **策略校准**：补短板放研究型硕士阶段；申请季前只补到"能独立讲清/改得动 XRD 项目核心代码"的够用最小集，够套磁/面试/文书即可。系统性补（C++/信号处理/光学/算法）留给硕士两年。

## 审阅"一月速成"定量反演方案
- 位置：远程 main 新提交 f36be82 + 0a04fa2，新增 `future_modules/PXRD_ROBUST_LATTICE_PARAMETER_INVERSION.md`（SEALED_FUTURE_MODULE，2026-08-15 设计）；本地仍停 86bba59，未 pull。
- 内容：四周原型，已知 tetragonal 模板下从 PXRD 反演晶格参数 (a,c)；扰动仅作鲁棒性压力测试；前向晶体学关系作额外监督（H3，明确"是假设非预设正结果"）。
- 关键定位：作者自认"CNN 预测晶格参数非 novelty"，novelty = 已知模板 + 扰动鲁棒性 + 前向物理监督 + 受控消融的组合；文献侦察 8 条（Chitturi 2021 / PQ-Net / AIdex / Hofgard 2026 等）。
- 我的评价：作为申请资产 + 补逆问题短板的载体质量很高；作为论文会被 Hofgard 2026（invariant target）卡 novelty。H3 亮点与实现难度成正比（第 3 档 nuisance-aware forward consistency 才是亮点）。放弃零偏移换来了问题干净，但零偏移恰是半导体 OCD 命门，宜作 Phase 2 单独捡回。
- 已执行 `git pull --ff-only`，本地 fast-forward 到 f36be82，与 origin/main 一致。
- 署名澄清：用户有一共一合作者，共一贡献"物理监督 H3 设计"，用户负责执行（git 提交者基本都是用户）。判断：git 提交者≠学术贡献，不影响共一正当性；证据应落在方案文档+Author Contributions。

## XRD 反演论文资源下载（用户 manifest 驱动）
- 位置：`01_literature/source_acquisitions/2026-08-15_xrd_inversion_resources/`（含 00_resource_manifest.md 源清单 + 01_download_status.md 结果清单 + papers/ + code/）。
- 已获取：7 篇论文主 PDF + SI 全部到齐（ACS 两篇 Gómez-Peralta2023 / AIdex2025 由用户手动下载后归档，含主 PDF + SI）；代码库 DeepLPnet + RAPID 已克隆 + DONUT-main（用户手动 Download ZIP 后解压，含全部模型权重约 1.1GB）。
- 剩余缺口：仅 ①PQ-Net 无公开代码（作者可索取）；②Hofgard 无公开代码（仅有 arXiv 源包）。资源归档基本完成。


<!-- 来源: .workbuddy/memory/2026-08-16.md -->
# 2026-08-16 工作日志

## 项目讲解指南生成
- 基于 CURRENT_STATE.md / PROJECT_JOURNEY.md / README.md 最新冻结证据，
  生成完整"会讲你的 XRD 项目"讲解指南
- 输出文件：`outputs/如何讲清楚你的XRD项目_讲解指南.md`
- 内容结构：三个层级讲法（30秒/3分钟/10分钟）、关键数字表、claim边界、
  7个预期问答、不同听众侧重点、一句话定义、练习清单
- 同时渲染两张可视化：项目叙事地图（五段式脊柱）、ERM vs JS 方法对比图
- 核心叙事线：问题(测量不稳)→洞察(模拟器保留provenance)→方法(JS一致性)→
  证据(模拟+5.46%/RRUFF+4.3-5.5%)→意义(量测问题ML化,桥接逆问题)


<!-- 来源: .workbuddy/memory/2026-08-23.md -->
# 2026-08-23 项目工作日志

## Codex 整理后接手做四个语义 commit（与用户决策点）
- 现状：Codex 在 `512b05f` "Consolidate XRD repository evidence and tooling" push 之后，
  working tree 仍有 110 项 dirty（+1139/-52132 行），是 Codex 第二轮整理成果（截图里
  "已编辑 68 个文件"）的开头但未 commit 完成。Codex 报告还提到"宿主安全策略拦截"
  `ten_run_output/` 3.2GB 删除，但实际已经清完。
- 用户决策：
  - 4 个语义 commit 分别 push（推荐）
  - `xrd_robustness/data/` 674MB + `xrd_robustness/outputs/` 5.8GB 全部保留（已 gitignore）

## 完成 commit
- `797b3aa` Add V9 public experiment entry points —— `scripts/train.py` (17 行 CLI) +
  `src/xrd_robustness/training/runner.py` (421 行 trainer) + `tests/training/test_train_cli.py`
  + `configs/experiment.v9.public.json` + `reports/RESULTS.md` + `validation_results.json` +
  `simulated_test_results.json`。7 files, +854/-0。
- `71e572e` Remove V7 and superseded training/evaluation modules —— 删 `train_v7.py`、
  `method_transfer.py`、`real_xrd.py`、`real_adaptation.py`、`residual_probe.py`、
  `rruff301_replay.py`、`v8_independent.py`、`training_prefetch.py`、`training_stream.py`、
  `perturbation_targets.py` + 7 个 models 子模块 + `online_views.py` 简化（删除
  OFFLINE_ERM/FIXED_VIEW_ERM/DYNAMIC_RESIDUAL/PERTURBATION_SUPERVISED_RESIDUAL 等
  TrainingMode 别名 + 私有 _softmax）+ 对应 10 个测试。31 files, -10524。
- `4ef0356` Consolidate configs, scripts and provenance reports —— 删旧 V9
  algorithm/evaluation/provenance configs、旧 reports/provenance 中 V7/早期 V9 证据
  （最大 v9_loss_gradient_scale_audit.json 8534 行被清）、`v9_resnet_js_ten_run_archive_20260802/`
  整目录、修改 `data.v9.method_transfer.structure_split.json` 等仍用的配置、修改所有 src
  模块简化 internal API。56 files, +954/-39365。
- `20467d4` Tighten project documentation around the V9-T surface —— 把所有 docs 收敛到
  "frozen V9-T → 论文阶段"叙事，删 `LITERATURE_LOCAL_RESOURCE_INDEX.md` 与
  `future_modules/` 5 个 .md；`PROJECT_JOURNEY.md` 用 `git rm --cached` 解除跟踪但
  保留 working tree 副本（1067 行 + Codex 加的 12 行 "公开发布范围收束" 附录），
  `.gitignore` 加规则 `00_project_context/PROJECT_JOURNEY.md`。16 files, +188/-3298。

## 验证
- 每次 commit 后 `python -m pytest -q`：84 passed in 4-15s（本次最简体积下 4s）。包含
  `test_train_cli.py`（动态 ERM / Dynamic JS 选项验证）。
- Secret 扫描每次 commit 后跑（`api[_-]?key|password|bearer|aws_*|private[_-]?key`），
  命中均为良性的 `MPRester(args.api_key)` 调用（key 从 `os.environ` 取，无硬编码）。
- 本地 HEAD = origin/main = `20467d4`，工作树干净。

## CODE 提交账户（用户机器上 Codex 用的也是这个）
- `Frysland-2024 <160820048+Frysland-2024@users.noreply.github.com>`，复用相同 identity
  让 commit 形如同一作者。
- 用户曾说诚实实讲 "codex 没有额度"，不代表学术贡献需归 codex——codex 只是执行工具，
  git commit 作者被设为该 GitHub 账号是 project 本地工作流的延续。

## 下一步（按 `CURRENT_STATE.md` 7.）
- 用 `reports/validation_results.json` + `reports/simulated_test_results.json` 生成论文图表
- 完成 Methods / Results / Discussion
- 跑完整测试确认入口一致

## 第二轮清理：丢掉 Codex 残留 + V9-T 替换 + audit 措辞清理（commit `1bb639c`）
- 18:49 用户追加两项要求：① "v9" 这种 AI 风味表述删掉，② "负结果/失败机制/审计证据" 移除出在线发布的 git 仓库
- 看到 `git stash list` 有 Codex 没干完的 stash (`stash@{0}: local ten-run summary placement before sync`)
  - 内容是 4 文件 +22/-10：把 `reports/v9_resnet_js_ten_run_summary.json`（Commit C 已删）重新引入，并加 audit 措辞
  - 与用户新要求"删 audit"对冲 → 直接 `git stash drop`
- 用户三个决策（推荐项均勾）：
  - V9 替换命名：本研究 / this study
  - audit 处理：保留事实陈述（simulated Test、split 数量、exact-parent-disjoint 等），删 "do not infer"、"boundary"、"limitation"、"may not be inferred"、"audit"、"failure mechanism"、"negative result" 等措辞
  - Codex stash：丢掉
- 8 个公开 tracked 文档做了替换 + 扫除：
  - `README.md`、`AGENTS.md` (各 1-2 处)
  - `xrd_robustness/README.md`、`xrd_robustness/CODEX_HANDOFF.md`、`xrd_robustness/reports/RESULTS.md`
  - `00_project_context/README.md`、`00_project_context/CURRENT_STATE.md` (4 处)、
    `00_project_context/APPLICATION_RESEARCH_NARRATIVE.md`
- 替换规则：`V9-T` → `本研究`/`this study`；`V9 public` → `Study Results`/`public experiment`；
  `experiment.v9.public.json` / `build_v9_structure_split.py` 等代码文件名保留不动（内部 contract）
- 84 passed；secret 扫描干净
- 8 files, +13/-13 → commit `1bb639c`，已 push

## 后续
- 用户对话方向更可能是申请材料（CV/RP/SOP），不再纠缠仓库
- 若有人再问起"V9-T"——可以明确说公开仓库里已经没有该标签，commit log 里仍可追溯
- PROJECT_JOURNEY.md 仍在 working tree（gitignore 屏蔽），里面仍含 V9-T 提及——这是 Codex 在 8-23 那次 stash 之前的工作；属于本地保留、不影响公开仓库

## 第三轮清理：公开文档全部改成人话（commit `dd25c28`）
- 21:15 用户要求"全部扫视一遍然后修改措辞，删去过于工程报告/ai 味道的"——直接改，不是列清单
- 扫了 9 个公开 tracked markdown（AGENTS.md 是 agent 操作手册，受众是 agent，保留原样）
- 中文文档（README、xrd_robustness/README、CODEX_HANDOFF、00_project_context/*）替换：
  - "冻结" → "已定型/最终"；"面板" → "数据集"；"matched seed pairs" → "配对种子实验"
  - "backbone" → "骨干网络"；"identity preprocessing" → "不做额外预处理"；"constant learning rate" → "恒定学习率"
  - "exact-parent-disjoint split identity" → "按母体结构严格隔离"
  - "入口/机器可读/人类可读/代码地图/数据合同" 等 → 人话；英文标题 → 中文标题
- 英文文档（MANUSCRIPT、RESULTS、NARRATIVE）替换：
  - "frozen simulated Test" → "simulated Test"；"five matched training-seed pairs" → "five matched seeds"
  - "the public experiment / the formal dataset" → "the experiment / the dataset"
  - "panels" → "Validation and Test sets"
- **保留不动**（学术标准术语，非 AI 味）：Dynamic ERM、JS Consistency、ResNet-18-GN、Macro-F1、OOD、
  lambda_js=60、AdamW、英文论文里的 "matched comparison/matched design"、全部结果数字
- 84 passed；secret 扫描干净；8 files +109/-109 → commit `dd25c28`，已 push
- 判断标准沉淀：中文语境删"冻结/面板/入口/骨干"，英文论文语境保留 "matched"/"backbone"（学术规范用语，不是 AI 味）

## 第四轮清理：中文文档去"中英混杂短语"（commit `33e2927`）
- 21:25 用户要求"尽量不要出现各种所谓中英混杂的短语"
- 扫了 5 个中文文档，把能翻的英文短语都翻成中文，只保留无法翻译的专有名词
- 改掉的中英混杂：
  - 标题英文 → 中文："AI4science Current State"→"AI4science 当前状态"；"Project Context"→"项目上下文"；
    "XRD Robustness"→"XRD 鲁棒性"（README + handoff 两处）；"Status date"→"状态日期"
  - "完成 Methods、Results 和 Discussion"→"完成方法、结果和讨论章节"（2 处）
  - "ResNet Dynamic ERM/JS 训练脚本"→"训练脚本（Dynamic ERM 与 JS 一致性）"（2 处）
- **保留的专有名词**（无法翻译）：PXRD、ResNet-18-GN、Dynamic ERM、Dynamic JS Consistency、AdamW、
  lambda_js、Macro-F1、文件路径/代码标识符
- 4 files +9/-9 → commit `33e2927`，已 push；84 passed

## 沉淀的判断标准（后续直接套用，无需再问）
- 用户对文档措辞的三条偏好（按时间顺序）：①删 AI 味/工程报告味 ②删"V9"等版本号标签 ③删中英混杂短语
- 中文文档：能翻的英文短语全翻中文；只保留方法名/模型名/优化器名/缩写/文件路径
- 英文文档（论文/申请叙事）：保留 "matched"/"backbone" 等学术规范用语，只删 "frozen"/"training-seed pairs" 等 AI 味词
- 改完统一跑 `python -m pytest -q`（84 passed）+ secret 扫描 + push，走 AGENTS.md 流程

## 第五轮清理：删 CODEX_HANDOFF + 中文去"codex 味"（commit `cc56de4`）
- 21:29 用户要求"中文也不要有太多 codex 味，尽量自然有人味"
- 21:32 用户追加："CODEX HANDOFF 不需要了，因为现在不需要交接了"
- 删除 `xrd_robustness/CODEX_HANDOFF.md`（交接不再需要），并清掉所有引用：
  - README.md 导航表删行；xrd_robustness/README.md 文档列表删行
  - AGENTS.md 两处：read 列表 + "update CODEX_HANDOFF on change" 规则
  - `tests/core/test_project_state_contract.py` 的 `test_public_document_links_resolve` 移除对 CODEX_HANDOFF 链接的期望（删了文件后这个测试会 fail，必须同步改）
- 中文去 codex 味（改成自然有人味的表述）：
  - "本研究" → "这个项目"；"已定型" → "已确定"；"正向提升" → "都有提升"
  - "当前阻塞" → "当前卡点"；"实验状态" → "实验进度"；"已完成工作" → "已经做完的事"
  - "保持公开文档中的方法与数值一致" → "让公开文档里的方法和数字保持一致"
  - "核心对比采用...比较...两种方法" → "在 ResNet-18-GN 上对比了...两种方法"
  - 涉及 README.md、xrd_robustness/README.md、00_project_context/README.md、CURRENT_STATE.md
- 7 files +30/-103 → commit `cc56de4`，已 push；84 passed
- 注意：删文件会触发 contract 测试，必须同步更新 test_project_state_contract.py

## 重要沉淀：删文档必须同步更新 contract 测试
- `tests/core/test_project_state_contract.py` 里 `test_public_document_links_resolve` 断言公开文档的交叉链接完整性
- 以后删任何公开 md 文件，先 grep 引用（README/AGENTS/其他 md），再同步改这个 contract 测试，否则 pytest 会 fail

## 第六轮清理：继续收中文 codex 味（commit `940b626`）
- 21:36 用户重复强调"中文不要 codex 味，尽量自然有人味"——上一轮没清干净，继续收
- 又改掉的报告腔：
  - "当前完成项、实验状态、工作重点与下一步" → "项目现状、进度和下一步"
  - "项目申请与交流叙事" → "申请和面试用的项目介绍"（"叙事"是 codex 高频词，中文语境尽量不用）
  - "同一母体结构的配对在线视图" → "同一母体结构的两份配对谱图"
  - "训练预算" → "训练量"；"分数以...为准" → "分数看..."
  - "运行完整测试，确认公开接口、数据约定与核心实现一致" → "跑一遍完整测试，确认接口、数据和实现都对得上"
  - "按母体结构严格隔离" → "按母体结构严格分开"
- 3 files +7/-7 → commit `940b626`，已 push；84 passed

## 用户对中文文档的核心偏好（总结，直接套用）
- 忌 codex/AI 味的词：**叙事、聚焦、收束、为准、保持一致、数据约定、核心实现、框架(作动词)、入口、当前重点、完成项、训练预算、固定(过度)、统一(过度)、精简(过度)、冻结、定型、正向提升、隔离**
- 宜：**这个项目、已经确定、都有提升、卡点、进度、做完的事、看...、跑一遍测试、分开**
- 用"人话"标准：读起来像一个人口头/书面自然描述，而不是 agent 进度报告

## 第七轮：仓库精简（commit `721a0e4`）
- 21:46 用户要求"让 git 仓库更精简一些"
- 盘点：tracked 76 个文件（src 29 / tests 21 / 根 11 / scripts 7 / configs 4 / reports 3 / CI 1）
- 删了 2 个冗余文件：
  - `.gitattributes`——两行 eol=crlf 规则引用的文件（v9_resnet_candidate_grid_gate.json、
    v9_resnet_js_simulated_test_summary.json）早在 Commit C 已删，是死引用，整个文件无有效内容
  - `AGENTS.md`——106 行 agent 操作规范（commit/sync 政策），对外（招生官）无价值，且暴露
    "AI 在维护仓库"痕迹；.gitignore 已覆盖 artifact 排除需求，删了无安全影响
- 保留所有代码/测试/配置/CI（都是功能性）；两个 gitignore 作用域不同（根=全仓大目录，子=子项目），不重复
- tracked 76→74，84 passed → commit `721a0e4`，已 push
- 注意：AGENTS.md 删除后，"删文档要同步改 contract 测试""不 commit 数据集"等规则需靠 memory 记，.gitignore 已兜底 artifact 排除


---

# 第三部分：关键结果与里程碑（Handoff 文档节选）

> 来源：`AI4Science_Project_Handoff_for_Admissions_AI_2026-08-07.md`
> 提取自第 2 节（发展主线）、第 4 节（方法演化与关键失败）、第 6 节（关键结果）。

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


---

# 第四部分：项目长期记忆（MEMORY.md）

# AI4science 项目长期记忆

## 项目核心定位
- 研究模拟预训练产生的 XRD 测量稳健表示能否低成本迁移到真实实验室任务
- Phase 1：通用模拟七晶系预训练（JS Consistency，已完成）
- Phase 2：谭启组钙钛矿功能陶瓷少样本相态识别（新方向）

## 关键决策
- V9 方法选择已关闭：JS lambda=60，backbone ResNet-18-GN
- 真实域：GTIIT/Tan Lab perovskite functional-ceramic XRD domain
- 下游任务：few-shot phase-state recognition（single-phase / multiphase）
- RRUFF-371 为外部矿物域评估资产，不与谭启组任务混淆

## 用户定位与目标（2026-08-13 澄清）
- 用户不指望发论文；主线项目用于申请材料
- 2026-08-13 决定：先读研究型硕士（research master）作为转行过渡，不直接读博；硕士阶段核心任务=补短板(数学/编程)+确认方向+攒项目；主线 XRD 项目是申请核心筹码
- 核心动机：本科材料，认为实验合成（"烧炉子"）天花板有限，想从材料合成端转向计算/量测/数据端
- 目标申请方向：半导体光学量测 / CT-MRI 反演（inverse problems）
- 领域定位（用户自述确定）：逆问题/计算成像 + 机器学习——"打波进去→反解结构/缺陷"内核，不绑定具体波段；光(XRD/CT/半导体散射测量)、声(超声)、磁(MRI)、电子束(电镜)都是实例
- 三个工业承接领域（用户总结）：①半导体量测(KLA/ASML/Nikon/Lasertec，天花板最高、光学最近) ②医学成像(CT/MRI/超声重建，算法最深度化、学术位置多) ③工业无损检测(超声/CT/热成像NDT，最工程化、对接加拿大/澳洲能源矿业)
- 潜在第四承接面：航天/遥感（NASA/ESA、SAR 合成孔径雷达、天文干涉成像）——同为逆问题+ML 重镇，偏政府/学术，暂非中短期工业目标
- 具体落点待定（半导体量测 / 工业超声 / CT-MRI 三选一），取决于"天花板 vs 稳妥落地"；用户以读书为主，移民次要
- 关键定位：主线 XRD 稳健表征 = "量测问题的机器学习化"，正是转行的桥，而非材料学边角料
- 主线 XRD 稳健表征（测量不变性 + Sim2Real + 少样本）是核心资产，命中量测/反演行业痛点
- Raman mapping（GTIIT/Tong Wu，MATLAB+PCA/N-FINDR 相态识别）是实验室他人项目，方法无创新；用户考虑是否复现写入简历——建议定位为"主线方法跨模态迁移验证"，而非"复现"

## 共一与署名分工（2026-08-15 澄清）
- 参数反演模块（PXRD_ROBUST_LATTICE_PARAMETER_INVERSION，一月原型）有一个**共一合作者**。
- 分工：共一贡献"前向物理监督（H3）"的科学设计（核心方法想法）；用户负责执行/工程实现，git 仓库提交者基本都是用户本人。
- 结论口径：git 提交者≠学术贡献；共一正当性取决于智力贡献（提出核心方法是最高级别贡献），不受"git 里没有合作者 commit"影响。证据应落在方案文档 + 论文 Author Contributions 声明，而非 git 记录。
- 待办建议：在方案文档/论文里明确留痕"物理监督设计由合作者提出"；申请材料如实讲分工。


---

# 第五部分：项目心路历程续篇 + 决策日志（从 Git 历史恢复）

> 以下两份文档在 2026-08-23 的仓库整理中被移出工作树，现从 Git 历史（commit `f36be82`）恢复原文，因为它们记录了 PROJECT_JOURNEY.md 未完整覆盖的 2026-08-07 至 08-08 关键历史。


<!-- 来源: git 历史 f36be82 -> 00_project_context/PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md -->
# PROJECT_JOURNEY Continuation — 2026-08-07 to 2026-08-08

> This continuation preserves the late-stage transition from exploratory real-domain evidence to confirmatory evidence and then to manuscript preparation. It is intended to be merged into / read alongside `PROJECT_JOURNEY.md` without deleting the earlier historical record.

## 21. RRUFF-70 从“看起来有效”降级为 exploratory evidence

模拟 Validation 与 frozen simulated Test 已经分别证明 JS 在受控模拟域内有重复性收益后，项目真正缺的是实验域证据。早期 RRUFF-70 few-shot pilot 给出了一个令人兴奋的现象：在 K=1/2/5 真实谱适配中，JS-pretrained 模型整体上比 Dynamic-ERM-pretrained 模型更容易用少量标签适配。

最容易的做法是直接把 RRUFF-70 当成论文的真实域结果。但项目没有这么做。原因是：RRUFF-70 样本量小，而且这些结果已经参与了后续假设形成。如果再把同一批数据包装成“最终确认”，探索与确认就会混在一起。

因此项目主动把 RRUFF-70 定义为：

> **exploratory / hypothesis-generating evidence**

它的作用变成：

1. 证明真实谱 few-shot 管线可运行；
2. 暴露可能的类依赖效应；
3. 产生“JS 是否提高真实域标签效率”的可检验假设；
4. 为更大的独立确认实验提供设计依据。

这一决定是项目实验治理的重要转折：目标从“找到一个支持方法的真实谱结果”变成“建立探索—确认分离的证据结构”。

## 22. RRUFF-301：从 exploratory hypothesis 到 preregistered confirmatory design

项目随后使用 RRUFF-371 资产中的 301-sample extension 构建 confirmatory experiment，并在模型访问前冻结：

- 301 条实验 PXRD，七晶系各 43 条；
- 10/class adaptation pool，共 70 条；
- 33/class locked test，共 231 条；
- K = 1 / 2 / 5；
- 五个 pretraining seeds；
- 五个 episode seeds；
- paired ERM-pretrained vs JS-pretrained comparison；
- primary metric = paired ΔMacro-F1；
- adaptation 使用相同 support、相同优化器、相同可训练 projection/head；
- 不允许增量查看结果后修改 K、episode、split 或 primary endpoint。

因此真实域问题被正式写成：

> **在相同少量真实标签预算下，JS 预训练学到的表示是否比 Dynamic ERM 预训练表示更容易适配实验 RRUFF PXRD？**

这一步让当前项目第一次真正形成了：

`simulation hypothesis → exploratory real evidence → independent confirmatory real-domain test`

的完整结构。

## 23. RRUFF-301 v1 label bug：一个“好结果”不能比数据身份更重要

RRUFF-301 第一次确认实验执行后，审计发现标签构建存在严重问题：RRUFF 的 CELL PARAMETERS 元数据使用晶格约定时，会把 trigonal/rhombohedral 情况表示在 hexagonal setting 下。原 v1 parser 因此把 trigonal 错并入 hexagonal，最终出现 hexagonal 数量异常、trigonal 缺失的问题。

这个 bug 的危险之处在于：训练和评估代码本身可以正常运行，也可以输出一套看似完整的结果。如果只关注模型分数，很容易把“软件成功执行”误当成“科学实验有效”。

项目最终没有尝试修补部分结果或只改几条标签，而是：

1. 明确将 v1 **invalidated for confirmatory use**；
2. 保留完整 `rruff301_v1_audit_trail_20260807.md`；
3. 改用 DIF `space_group` 证据；
4. 用 `pymatgen.SpaceGroup` 做晶系映射；
5. 重新验证 70 adaptation + 231 test、33/class、zero overlap；
6. 从修正后的冻结 split 完整重跑所有 150 个 adaptation runs。

这一事件后来成为项目申请叙事中最重要的方法论节点之一：

> **科研的目标不是保住一个好看的结果，而是确保结果的身份、标签和评估协议值得相信。**

## 24. RRUFF-301 v2：确认性真实域证据成立

2026-08-07，修复后的 RRUFF-301 v2 完整结束。

Primary Macro-F1 结果：

| K | ERM | JS | paired mean Δ | positive pairs |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | +0.0433 | 21/25 |
| 2 | 0.3026 | 0.3486 | +0.0460 | 23/25 |
| 5 | 0.3555 | 0.4099 | +0.0545 | 24/25 |

合计：

> **68/75 paired comparisons 为正。**

同时，K=1 与 K=5 的 fixed-200-step sensitivity check 保持同方向，说明主要差异不是 support-loss early stopping 的偶然产物。

这个结果改变了项目的证据等级。此前可以说：

> “JS 在模拟 OOD 上稳定优于 ERM，并在一个小型真实域 pilot 中表现出潜力。”

现在可以更严格地说：

> **“JS 在受控模拟域形成重复性 robustness gain，并在独立、预注册、纠错后完整重跑的 RRUFF-301 确认实验中表现出更高的 few-shot adaptation efficiency。”**

但项目仍然保留克制：

- zero-shot 绝对性能并不高；
- 不同晶系收益不均匀；
- RRUFF 是矿物实验域，不代表全部 PXRD；
- 不能把 JS 描述成新算法；
- 不能声称 semantic/measurement 已经显式 disentangle。

## 25. RRUFF-70 的 monoclinic negative transfer 没有复制：探索结果可以被推翻

RRUFF-70 pilot 曾出现 monoclinic 在 K=5 下明显负迁移，这一现象一度被认为可能代表 JS 的一个方法边界。

RRUFF-301 v2 对这一现象进行了明确的 confirmatory check。结果是：monoclinic 在 K=1/2/5 的平均 Δ 均为正，早期负迁移没有复制。

因此项目没有把旧结果继续包装成“机制发现”，而是把它重新解释为：

> RRUFF-70 small-sample exploratory artifact / unstable class-level signal.

这进一步强化了项目形成的证据观：

> **探索性结果负责提出问题；确认性结果有权否定探索阶段的故事。**

## 26. 从“平均涨点”进入 representation / calibration analysis

RRUFF-301 v2 后，项目没有立即再开新模型，而是分析已有预测：

- JS fix 了哪些 ERM 错误；
- JS 又 break 了哪些 ERM 正确样本；
- confidence 如何变化；
- 哪些类之间存在 asymmetric confusion；
- per-class gain 是否与 K 一致。

随后又补充：

- ECE；
- NLL；
- Brier；
- confidence distributions。

这一步的意义不是新增一个“calibration 创新点”，而是让项目从：

> 哪个模型分数更高？

继续推进到：

> **这个学习原则在哪些样本、哪些类、哪些置信度状态下改变了模型行为？**

项目因此进一步靠近 AI4Science 中的 representation / reliability 研究，而不是单纯材料分类 benchmark。

## 27. 2026-08-08：Evidence Freeze — 正式停止“默认继续训练”

截至这一节点，当前 JS 主线已经拥有：

1. matched Dynamic ERM baseline；
2. Train-only lambda legality / scale governance；
3. five-seed paired Validation replication；
4. frozen simulated Test confirmation；
5. exploratory RRUFF-70；
6. independent RRUFF-301 confirmatory v2；
7. per-class / fix-break / confidence diagnostics；
8. calibration supplementary evidence；
9. v1 label-bug audit trail。

继续默认开新训练已经不再是最有价值的动作。

项目因此切换为：

> **experiment-building → evidence freeze → manuscript building**

新的规则是：

> 除非论文写作或外部 review 暴露出一个明确的 reviewer-critical evidence gap，而且现有 frozen artifacts 无法回答，否则不新增训练。

这不是“项目做不动了”，而是第一次主动承认：

> **一个研究项目的完成标准不是永远还能多跑一个实验，而是现有证据是否已经足够回答冻结的问题。**

## 28. 当前论文四张主图被正式冻结

当前正文不再无限扩展模块，核心图表固定为：

1. **Method / simulator provenance**：同一 parent structure 的两种 physical views，ERM 只用标签，JS 进一步利用 measurement-equivalence；
2. **Simulated Validation + Test paired effects**：证明受控模拟域的 repeatability 与 confirmation；
3. **RRUFF-301 K=1/2/5 paired few-shot**：当前最强真实域确认性证据；
4. **Per-class + fix/break/confidence diagnostic**：明确平均收益存在 heterogeneity。

Calibration 默认进入 Supplementary。

这一步进一步收缩论文叙事：

> **不是“我们做了很多模块”，而是“一个同源监督假设，在模拟域和实验域分别得到受控证据，并且我们知道它不是处处都有效”。**

## 29. 当前申请叙事：从材料增强到“科学生成机制 → ML supervision”

回顾整个项目，最重要的变化已经不是某一次 +0.05 Macro-F1，而是研究问题的层级变化：

最开始：

> 怎样让模拟 XRD 更像真实谱？

然后：

> 怎样让模型对物理扰动更鲁棒？

再然后：

> Residual 是否能把测量差异与晶体语义分开？

最终：

> **模拟器知道哪些数据是同一个物理对象的不同观测；这种关系本身能否成为监督？**

这正是当前项目作为申请“桥梁”的核心：材料知识提供了对数据生成过程、合法扰动和独立样本单位的理解；机器学习部分则逐渐转向 structured supervision、OOD robustness、representation learning、few-shot transfer 和实验治理。

因此项目目前最适合被概括为：

> **从一个 PXRD Sim2Real 工程问题出发，通过多次失败和协议修正，把科学测量中的同源关系重构成一个可验证的机器学习监督问题。**

## 30. Residual 路线的后验理解：measurement–semantic non-separability

在 Residual-v1 / V10 被归档后，项目进一步形成了一个更成熟的后验解释，但目前只作为 future-research hypothesis，而不是当前论文结论。

对 PXRD 而言，measurement perturbation 往往直接作用在结构判别所依赖的峰上。比如小峰移满足近似：

`x(theta - delta) - x(theta) ≈ -delta * x'(theta)`

因此 residual 最大的位置恰好由原始结构峰决定；展宽 residual 也取决于原始峰位置与形状；择优取向更直接改变结构特定的 hkl 相对强度。

所以：

`residual = f(measurement condition, crystal structure)`

可能比：

`residual = measurement-only nuisance`

更符合真实生成机制。

这意味着要求 residual 完全不含晶系信息可能是一个过强的归纳假设。V10 中“测量可解码性增强时晶系泄漏也同步增强”的现象与这一解释相容，但不能单独证明它。

这个反思也解释了为什么 JS 最终成为更稳妥的主线：它不要求显式拆开 measurement 与 semantic，只要求同一 parent structure 的合法测量轨道上预测保持稳定。换言之，JS 使用了比显式 disentanglement 更弱、更容易被当前证据支持的假设。

## 当前阶段一句话

> **当前项目已经不再默认追求新模型，而是冻结“simulator provenance → measurement-equivalence supervision → simulated robustness → experimental few-shot adaptation”的证据链，并把项目转入论文与申请叙事阶段。**

<!-- 来源: git 历史 f36be82 -> 00_project_context/DECISION_LOG_20260813.md -->
# Project Decision Log — 2026-08-13

## RRUFF-301 rerun priority

The reason rerunning RRUFF-301 is **not important** is **not** that the project is temporarily not pursuing publication.

After discussion with the advisor, the working judgment is that, in the context of materials-science research and materials-journal evaluation, formal evidence-governance machinery such as file hashes, execution-provenance chains, pre-execution authorization records, and similarly strict reproducibility bookkeeping is not a central scientific contribution or a core evidentiary requirement. These should be retained as **internal engineering hygiene**, but they should not be treated as a research contribution or as a scientific shortcoming that must be repaired by rerunning the experiment.

The project should instead prioritize whether:

1. the scientific conclusion itself is valid;
2. the experimental design is sensible and interpretable;
3. the observed effect is stable rather than a fragile one-off result;
4. the overall scientific story is coherent and complete.

Under that priority system, the existing RRUFF-301 result is already useful because it provides a stable real-domain few-shot signal across K=1/2/5 and across matched comparisons. Repeating the same experiment merely to upgrade hashes, execution lineage, or formal provenance would have low scientific value and should not be treated as a project priority.

A new real-domain experiment should only be run if it answers a genuinely new scientific question, tests robustness in a materially different setting, or otherwise strengthens the scientific conclusion itself—not merely to repair formal provenance bookkeeping.

