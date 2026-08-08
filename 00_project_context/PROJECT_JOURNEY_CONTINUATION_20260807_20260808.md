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
