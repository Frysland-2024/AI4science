# PXRD 鲁棒性项目：80/20 双人贡献切分方案

**日期：** 2026-09-01  
**性质：** 已完成 PXRD robustness / measurement-equivalence supervision 项目的内部协作切分方案。  
**适用范围：** `xrd_robustness/` 当前已经冻结并完成的 Dynamic ERM / Dynamic JS 主线、模拟 OOD、RRUFF-301 few-shot、CNRS-318 zero-shot。  
**目的：** 在不重新打开主实验、不重写 scientific claim 的前提下，把约 20% 的工作切成一个边界清晰、可以独立讲述的真实域迁移模块；约 80% 的方法学主线保持集中。

> 本文件是项目管理与申请叙事的内部边界说明，不自动等同于正式 authorship / CRediT 声明。最终作者贡献必须按实际完成的工作如实记录。

---

## 1. 总体切分

```text
主负责人（约 75–80%）
Provenance-Aware Measurement-Equivalence Supervision
        ↓
回答：在线模拟器保留的 parent provenance
能否从“数据生成信息”转化为“关系监督”，
从而提升对物理测量扰动的鲁棒性？

协作者（约 20–25%）
Experimental Few-Shot Adaptation & Label Efficiency
        ↓
回答：在完全相同的少量真实标签预算下，
哪一种模拟预训练表示更容易适配实验 PXRD？
```

一句话边界：

> **主负责人负责“怎样从 simulator provenance 学到更稳健的表示”；协作者负责“这种表示到了真实实验域以后，能不能更省标签地适配”。**

这个切法不是把同一个算法硬拆成两半，而是把研究链条自然拆成：

```text
方法提出与模拟域验证
        ↓
真实域低标签迁移验证
```

---

## 2. 主负责人：Provenance-Aware Consistency 主线（约 75–80%）

### 2.1 核心科学问题

已有 PXRD-ML 工作已经成熟使用随机物理扰动和 on-the-fly generation 来扩大合成数据覆盖。当前项目进一步利用 simulator-retained parent identity：

```text
同一 parent crystal structure s
      ├── measurement state m1 -> x1
      └── measurement state m2 -> x2
```

`x1` 与 `x2` 不只是“同晶系样本”，而是同一个 latent physical object 的不同 measurement realizations。

主负责人的核心贡献是：

```text
shared parent identity
        ↓
measurement equivalence
        ↓
relationship supervision
        ↓
Dynamic JS consistency
```

即：

> **simulator = data generator + relationship supervisor**

而不是仅仅把 JS divergence 搬到 XRD。

### 2.2 主负责人拥有的研究内容

主负责人负责并保留以下核心工作：

1. **研究问题定义与 novelty framing**
   - 从随机物理扰动 / on-the-fly generation 文献谱系出发；
   - 定义 `parent provenance -> measurement equivalence -> relationship supervision`；
   - 解释为什么 JS 是对称、弱约束的输出一致性实现。

2. **模拟数据与物理扰动体系**
   - `formal_14060` 母结构数据集；
   - 9842 / 2109 / 2109 parent-level split；
   - 五类物理扰动及其冻结范围；
   - online paired-view generation；
   - train / validation / test 的 parent isolation。

3. **公共 backbone 与方法比较**
   - ResNet-18-GN 公共 backbone；
   - Dynamic ERM matched baseline；
   - Dynamic JS；
   - `lambda_js=60` 的冻结选择路径；
   - 保证 ERM / JS data exposure、forward 次数、训练预算与评测协议一致。

4. **模拟 Validation / Final Test 主证据**
   - 5 matched seeds；
   - simulated single-factor OOD；
   - ID / in-range / OOD performance；
   - profile-wise 结果；
   - 主方法的最终模拟域结论。

5. **广域第二真实域与方法可靠性**
   - CNRS-318 frozen-model zero-shot external evaluation；
   - calibration / ECE / NLL / Brier 等 reliability evidence；
   - 真实域局限性与不能过度包装的边界。

6. **最终论文的核心 Methods / Introduction / Discussion**
   - 方法图；
   - `data generator -> relationship supervisor` 叙事；
   - 主方法因果对照；
   - 结果的总整合。

### 2.3 当前主线的关键已完成结果

当前冻结结果中：

- simulated Test single-factor OOD Macro-F1：`0.65074 -> 0.70534`，配对提升约 `+0.05460`，5/5 matched seeds 为正；
- simulated Test Accuracy：`0.65078 -> 0.70524`；
- CNRS-318 zero-shot seed-level Macro-F1：约 `0.18837 -> 0.20708`，5/5 seeds favor JS；
- CNRS pooled ECE：约 `0.68257 -> 0.61242`。

这些属于主方法的整体证据，不应被拆成协作者独立的算法贡献。

---

## 3. 协作者：RRUFF-301 Few-Shot Adaptation & Label Efficiency（约 20–25%）

### 3.1 独立故事线

协作者模块不重新提出 JS，不修改模拟器，不重新选 `lambda_js`，也不负责主模型训练。

其完整科学问题为：

> **当两个模型都只在模拟 PXRD 上预训练以后，在完全相同的少量真实标签预算下，哪一种预训练表示更容易适配实验测量域？**

因此该模块可以独立表述为：

> **Experimental label-efficient adaptation of simulation-pretrained PXRD representations.**

或者中文：

> **模拟预训练 PXRD 表示在实验域中的少样本适配与标签效率研究。**

它回答的是 transfer / adaptation 问题，而不是 consistency 方法本身的原创问题。

### 3.2 协作者的输入必须冻结

主负责人交付：

```text
5 × Dynamic ERM pretrained checkpoints
5 × Dynamic JS pretrained checkpoints

RRUFF-301 frozen split / manifest
RRUFF-70 adaptation pool
RRUFF-231 locked test

canonical preprocessing
crystal-system label mapping
统一 CE fine-tuning protocol
```

核心原则：

> **协作者不能根据 RRUFF 结果重新选择模拟 checkpoint、seed、lambda_js、backbone 或扰动配置。**

RRUFF 是下游评测 / 适配模块，不得反向改写主方法。

### 3.3 协作者的主实验

冻结真实标签预算：

```text
K = 1 / 2 / 5 shot per crystal system
```

比较：

```text
Dynamic ERM pretrained model
        ↓ 相同 CE adaptation
RRUFF K-shot

Dynamic JS pretrained model
        ↓ 相同 CE adaptation
RRUFF K-shot
```

两种初始化必须使用：

- 完全相同的 RRUFF support IDs；
- 完全相同的 adaptation budget；
- 完全相同的 optimizer / early stopping / train steps；
- 完全相同的 locked test；
- 不在真实域微调阶段继续加入 JS loss。

这样差异主要归因于：

> **模拟预训练阶段学到的表示是否更适合低标签真实域适配。**

### 3.4 协作者负责的结果与分析

协作者拥有以下完整子模块：

1. **RRUFF-301 数据角色与 split 审计**
   - adaptation/test RRUFF ID overlap；
   - exact spectrum SHA overlap；
   - near-duplicate Pearson audit；
   - 解释为什么 shared mineral identity 在当前 in-domain few-shot task 下允许保留。

2. **K-shot adaptation runner / protocol**
   - K=1/2/5；
   - matched real support；
   - ERM / JS 统一 CE adaptation；
   - 重复 support / model seed 的组合执行。

3. **label-efficiency learning curve**
   - Macro-F1；
   - Accuracy；
   - mean ± SD；
   - paired direction consistency；
   - K 增加时 JS–ERM gap 是否保持或扩大。

4. **per-class 与 failure analysis（克制版）**
   - 哪些 crystal systems 最受益；
   - 少标签时的主要 confusion；
   - 不扩展成新的大规模方法研究。

5. **RRUFF 子模块图表与报告**
   - K-shot learning curve；
   - ERM vs JS paired delta 图；
   - RRUFF 数据切分示意图；
   - 一页独立实验域结论。

### 3.5 当前已经存在的结果

当前 RRUFF-301 locked-test 结果为：

| Label budget | ERM Macro-F1 | JS Macro-F1 | Δ |
|---|---:|---:|---:|
| K=1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | `+0.0433` |
| K=2 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | `+0.0460` |
| K=5 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | `+0.0545` |

Accuracy 的对应提升约为：

```text
K=1: +0.0384
K=2: +0.0488
K=5: +0.0568
```

因此这个模块已经具有独立完整的实证故事：

> **相同的真实标签预算下，JS-pretrained representation consistently 比 ERM-pretrained representation 更容易适配 RRUFF experimental domain，并且优势在 K=1/2/5 三档预算中持续存在。**

---

## 4. 为什么这个模块适合 20%，但不会抢走主创新

### 4.1 它有独立问题

协作者不是“帮忙跑真实数据”，而是在回答：

> **simulation-pretrained representations 的 experimental label efficiency。**

这本身属于 transfer learning / low-label adaptation 的完整问题。

### 4.2 它依赖主模型，但不等于没有独立故事

依赖主预训练模型是正常的研究链条关系：

```text
主方法：如何学 representation
        ↓
协作模块：representation 是否更 transferable / label-efficient
```

就像：

```text
pretraining paper
        ↓
downstream transfer benchmark
```

下游模块仍可以具有独立实验设计、评价指标和结论。

### 4.3 它不会夺走主 novelty

以下内容明确不属于协作者主张：

- `measurement-equivalence supervision` 的原始问题定义；
- simulator provenance 的 novelty framing；
- Dynamic JS objective 的设计与 λ 选择；
- formal_14060 模拟训练体系；
- 5-seed simulated OOD 主实验；
- CNRS-318 second-domain zero-shot 主结论；
- 整篇论文的核心算法与方法学定位。

协作者可以说：

> “I studied the label-efficient experimental adaptation of two frozen simulation-pretrained representations.”

但不能说：

> “I proposed the provenance-aware JS consistency method.”

除非实际贡献事实另有变化。

---

## 5. 最干净的代码 / 文件边界

当前项目已经完成，所以优先采用**结果与适配模块边界**，不要重新拆主训练代码。

建议协作者主要维护：

```text
xrd_robustness/scripts/
  # RRUFF few-shot adaptation / aggregation 相关脚本

xrd_robustness/reports/
  RRUFF301_COMPOSITION_AUDIT.md
  RRUFF301_COMPOSITION_AUDIT.json
  rruff301_fewshot_results.json
  # RRUFF-specific figures / summaries
```

主负责人继续维护：

```text
xrd_robustness/src/xrd_robustness/
  simulator.py
  online_views.py
  models/
  training/objectives.py
  training/runner.py

xrd_robustness/configs/
  simulation / model / JS frozen configs

xrd_robustness/reports/
  validation_results.json
  simulated_test_results.json
  CNRS_318_RESULTS.md
  CALIBRATION_ANALYSIS.md
```

公共接口原则：

> **协作者消费 frozen checkpoints / prediction artifacts / manifests；不进入主训练管线重新设计方法。**

---

## 6. 如果现在才开始让协作者接手，怎么交接

由于主实验已经完成，这个模块非常适合“主负责人先做完主线，再让协作者按冻结计划完成/复核下游模块”。

建议交接包：

```text
A. 科学说明
   docs/PXRD_ROBUSTNESS_TEAM_DIVISION_80_20.md
   docs/CURRENT_STATE.md
   docs/PXRD_EVIDENCE_CLOSURE.md

B. 固定数据
   RRUFF-301 manifests
   adaptation support IDs
   locked-test IDs

C. 固定模型
   5 ERM checkpoints
   5 JS checkpoints
   model / preprocessing config

D. 固定协议
   K=1/2/5
   CE-only adaptation
   matched support
   frozen evaluation metrics

E. 协作者输出
   RRUFF few-shot result table
   learning curve
   paired delta plot
   composition audit summary
   independent module write-up
```

协作者首先应复现已有汇总；如果结果一致，再进行图表、逐类分析和模块写作。不得为了“做出新东西”擅自新增 K、重新切 split 或反向调主模型。

---

## 7. 双方各自可以怎样讲项目

### 主负责人申请 / 面试版

> I noticed that an online scientific simulator provides more than synthetic samples: it retains provenance indicating which measurements originate from the same underlying crystal. I converted this parent identity into measurement-equivalence supervision and tested whether explicit consistency improves PXRD robustness under matched data exposure. I led the simulator design, matched ERM–JS comparison, multi-seed OOD experiments, and cross-domain evaluation.

核心身份：

> **scientific ML / structured supervision / robust representation learning**

### 协作者申请 / 面试版

> I investigated whether robustness learned from physics-based simulation improves label-efficient adaptation to experimental PXRD. Using frozen ERM- and consistency-pretrained representations, I designed and evaluated matched K-shot adaptation on a curated RRUFF experimental benchmark, including split auditing, repeated low-label evaluation, and learning-curve analysis.

核心身份：

> **transfer learning / few-shot scientific data / experimental-domain adaptation**

两条叙事相连，但不重复。

---

## 8. 最终论文结构中的归属

建议按科学内容理解：

```text
Introduction / Related Work
  主负责人：主导

Simulator + physical perturbation
  主负责人：主导

Measurement-equivalence supervision / JS objective
  主负责人：主导

Matched simulated Validation/Test
  主负责人：主导

RRUFF-301 few-shot adaptation
  协作者：主导该小节

CNRS-318 zero-shot + calibration
  主负责人：主导

Discussion / overall framing
  主负责人：主导，协作者提供 RRUFF transfer interpretation
```

这会自然形成约 80/20 的论文工作结构，而不是人工按页面数量分配。

---

## 9. 当前内部贡献比例定位

仅用于项目规划：

```text
约 75–80%
  problem definition
  literature / novelty framing
  simulator + physical perturbation design
  parent-level dataset governance
  ResNet public backbone
  Dynamic ERM / Dynamic JS
  lambda selection
  5-seed validation / simulated final test
  CNRS zero-shot + calibration
  manuscript mainline integration

约 20–25%
  RRUFF-301 experimental adaptation module
  real-domain split / composition audit
  K=1/2/5 matched few-shot protocol
  adaptation execution / aggregation
  label-efficiency learning curve
  RRUFF-specific figures and subsection writing
```

最终 authorship / CRediT 不能机械地照搬该比例，应以实际贡献为准。

---

## 10. 明确不建议的切法

### 不切 simulator 给协作者

原因：

```text
online simulator
  -> parent provenance
  -> measurement equivalence
  -> relationship supervision
```

是当前主 novelty 的逻辑地基。若把 simulator/provenance 设计整体切出去，会削弱主负责人的完整方法叙事。

### 不把 CNRS 单独当 20% 主模块

CNRS 是有价值的 independent zero-shot second-domain evidence，但它更像主方法的外部 stress test，独立故事完整度低于 RRUFF few-shot adaptation。

### 不重新开新算法 / 新 loss 给协作者

当前主实验已经结案。为了凑 20% 再增加：

- KL / MSE consistency；
- Residual；
- 新 backbone；
- 新 target domain；
- 新 simulator；

都会破坏项目收敛状态，并且让贡献比例失控。

---

## 11. 最终一句话

最推荐的 8:2 切分是：

```text
80%：
从 simulator provenance 中定义 measurement equivalence，
并用 consistency supervision 学习更稳健的 PXRD representation。

20%：
把冻结的模拟预训练 representation 带入 RRUFF 实验域，
研究低真实标签预算下的 adaptation / label efficiency。
```

也就是：

> **主负责人解决“怎么学得更稳”；协作者解决“学稳以后，真实实验域能不能更省标签地用起来”。**
