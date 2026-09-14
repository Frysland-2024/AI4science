# 基于同母结构测量等价监督的鲁棒 PXRD 七晶系分类

**技术备忘录｜按成熟 Machine Learning XRD 论文范式重写**  
**更新日期：** 2026-09-14  
**研究主线：** 七晶系 PXRD 分类、在线物理扰动、same-parent consistency、真实谱少样本适配

## 摘要

基于模拟粉末 X 射线衍射（PXRD）训练的机器学习模型，在真实测量中会受到峰位偏移、峰展宽、择优取向、背景和计数噪声等测量变化影响。传统在线模拟主要把这些变化作为数据增强来源；本项目进一步利用模拟器保留的 **parent structure identity**，把同一晶体结构在不同测量状态下生成的两条 PXRD 谱定义为 measurement-equivalent views，并在常规晶系交叉熵监督之外加入 Jensen–Shannon（JS）预测一致性约束。

在完全匹配的 parent structures、在线扰动分布、ResNet backbone、优化器和数据暴露下，same-parent JS consistency 在冻结模拟 Test 上将 mean single-factor OOD Macro-F1 从 `0.6507` 提高到 `0.7053`，提升 **5.46 个百分点**；Accuracy 同期提升 **5.45 个百分点**，五个训练种子均保持正向改善。真实实验谱中，RRUFF-301 的 K=1/2/5 few-shot 适配分别获得 **+4.33 / +4.60 / +5.45 pp Macro-F1**，表明一致性预训练提高了真实标签利用效率；独立 CNRS-318 zero-shot 域中，五个训练种子的 Macro-F1 也保持同方向提升。进一步拆分物理扰动后，峰展宽和择优取向分别获得 **+8.40 pp** 与 **+8.09 pp Macro-F1**，是所有单因素 OOD 中增益最明显的两类。机制补充实验进一步显示，same-parent pairing 相对 same-class pairing 的额外收益主要保留在 broadening 和 texture 上。

因此，当前工作形成三个主要科学结论：**总体分类鲁棒性稳定提高；真实实验谱的标签效率提高；对与具体晶体衍射结构强耦合的测量扰动尤其具有优势。**

---

# 1. 研究背景与问题定义

PXRD 机器学习长期面临一个核心问题：训练数据往往来自理想结构计算，而实验谱包含真实测量条件带来的系统变化。Oviedo 等、Lee 等以及后续多项 PXRD-ML 工作已经证明，物理合理的数据增强对于把模型从理想模拟谱推进到实验谱至关重要。峰位变化、峰展宽、择优取向、背景和噪声已经成为该领域最常见的几类模拟测量扰动。

本项目进一步关注模拟过程中的另一类信息：**同一母结构可以在不同测量状态下生成多条不同的 PXRD 谱，而模拟器明确知道这些谱共享同一个 parent structure。**

对母结构 `s` 和两个独立测量状态 `m1,m2`：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

两条谱的峰形、背景、噪声和相对峰强可以明显不同，但它们仍然对应同一个潜在晶体结构。由此定义：

```text
same parent
    ↓
measurement-equivalent views
    ↓
prediction consistency supervision
```

因此，本项目把在线模拟器从“生成更多训练谱”的工具进一步扩展为“提供测量关系监督”的工具。

研究问题可以写成：

> **在相同数据、相同扰动和相同模型条件下，显式利用 same-parent measurement equivalence，是否能够提高 PXRD 晶系分类在模拟扰动和实验域中的鲁棒性？**

---

# 2. 主要结果

## 2.1 结论一：模拟域与真实域的总体分类性能稳定提高

正式对照为 Dynamic ERM 与 same-parent Dynamic JS。两种方法使用相同的 parent structures、相同的两张在线扰动谱、相同 backbone、相同 optimizer 和相同训练预算。Dynamic JS 在分类损失之外加入 same-parent 预测一致性。

冻结 simulated Test 的五种训练种子结果如下：

| 指标 | Dynamic ERM | Same-parent JS | 提升 |
|---|---:|---:|---:|
| In-range Macro-F1 | 0.6953 | 0.7349 | +3.96 pp |
| Mean single-factor OOD Macro-F1 | 0.6507 ± 0.0072 | 0.7053 ± 0.0098 | **+5.46 pp** |
| Mean single-factor OOD Accuracy | 0.6508 ± 0.0078 | 0.7052 ± 0.0086 | **+5.45 pp** |

五个 matched training seeds 在主要 OOD Macro-F1 和 Accuracy 上均为正向改善。这个结果说明 same-parent consistency 带来的收益能够跨训练随机性稳定复现，并同时体现在 Macro-F1 与 top-1 Accuracy 上。

真实实验谱进一步给出两类互补证据。

### RRUFF-301：真实域 few-shot 适配

| Labels / class | Metric | Dynamic ERM | Same-parent JS | 提升 |
|---:|---|---:|---:|---:|
| 1 | Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | **+4.33 pp** |
| 1 | Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | +3.84 pp |
| 2 | Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | **+4.60 pp** |
| 2 | Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | +4.88 pp |
| 5 | Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | **+5.45 pp** |
| 5 | Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | +5.68 pp |

RRUFF-301 使用 `5 pretraining seeds × 5 episode seeds` 的 matched protocol。在每个 K 值上，把五个 episode seeds 先在对应 pretraining seed 内平均后，五个 pretraining seeds 均 favor JS；全部 75 个 Macro-F1 matched comparisons 中有 68 个 favor JS。

### CNRS-318：独立实验来源 zero-shot 评测

CNRS-318 保持模型冻结，直接进行实验域 zero-shot 评测。五个训练种子的 Macro-F1 为：

```text
0.1884 ± 0.0263  →  0.2071 ± 0.0213
mean paired Δ = +1.87 pp
```

五个训练种子全部为正向变化。将五组重复预测 pooled 后：

| Metric | Dynamic ERM | Same-parent JS | 改善 |
|---|---:|---:|---:|
| Macro-F1 | 0.1912 | 0.2091 | +1.79 pp |
| Balanced Accuracy | 0.2182 | 0.2388 | +2.06 pp |
| Accuracy | 0.2000 | 0.2101 | +1.01 pp |

模拟 Test、RRUFF-301 和 CNRS-318 共同构成第一条结论：**same-parent consistency 在模拟扰动和实验谱上都带来稳定的分类性能提升。**

---

## 2.2 结论二：真实实验谱适配具有更高标签效率

RRUFF-301 的核心价值来自完整的 K-shot learning curve。两组模型拥有相同数量的真实标签，在 K=1、K=2 和 K=5 三个预算下，JS-pretrained representation 始终取得更高的 Macro-F1 和 Accuracy。

从实际适配角度看，这意味着模拟阶段学到的 same-parent measurement consistency 能够形成更容易被少量真实标签校准的 representation：

```text
same synthetic pretraining scale
        ↓
more measurement-invariant representation
        ↓
fewer real labels are used more efficiently
```

随着真实标签预算从 K=1 增加到 K=5，Macro-F1 的优势从 `+4.33 pp` 增加到 `+5.45 pp`，说明该收益能够持续存在于少样本适配过程，而非只集中在某一个偶然 K 值。

进一步的 prediction-level 分析也显示，JS-pretrained 模型在 RRUFF locked test 上修正的样本数持续高于被破坏的样本数：

| K | ERM-only correct | JS-only correct | Fix | Break | Fix / Break |
|---:|---:|---:|---:|---:|---:|
| 1 | 112 | 78 | 934 | 712 | 1.31 |
| 2 | 110 | 66 | 936 | 654 | 1.43 |
| 5 | 103 | 70 | 902 | 574 | 1.57 |

在 K=5 下，orthorhombic、hexagonal、monoclinic、triclinic 和 tetragonal 的净正确次数均增加，其中 orthorhombic `+116`、hexagonal `+81`、monoclinic `+74`。这说明真实域提升能够落实到具体样本和具体晶系行为，而不仅是总体平均值变化。

第二条结论因此可以直接表述为：**same-parent consistency 预训练提高了真实 PXRD 的 label efficiency，使有限的实验标签产生更高的下游适配收益。**

---

## 2.3 结论三：对强结构耦合扰动的鲁棒性提升尤其明显

将 simulated Test 的六个 single-factor OOD 条件拆开后，JS consistency 的收益呈现出清晰的物理结构。

| OOD 扰动 | ERM Macro-F1 | JS Macro-F1 | ΔMacro-F1 | ΔAccuracy |
|---|---:|---:|---:|---:|
| Peak shift − | 0.6926 ± 0.0034 | 0.7290 ± 0.0142 | +3.64 pp | +3.56 pp |
| Peak shift + | 0.6871 ± 0.0058 | 0.7307 ± 0.0083 | +4.36 pp | +4.22 pp |
| **Broadening** | 0.5517 ± 0.0633 | 0.6357 ± 0.0268 | **+8.40 pp** | **+8.89 pp** |
| Noise | 0.6712 ± 0.0044 | 0.7033 ± 0.0109 | +3.22 pp | +3.07 pp |
| Background | 0.6827 ± 0.0038 | 0.7332 ± 0.0115 | +5.05 pp | +5.13 pp |
| **Preferred orientation / texture** | 0.6191 ± 0.0211 | 0.7000 ± 0.0120 | **+8.09 pp** | **+7.80 pp** |

其中 broadening 和 texture 是增益最大的两类扰动，同时也是最明显依赖具体晶体衍射结构的两类测量变化。

### Broadening 的结构耦合

统一 FWHM 参数本身可以独立采样，但展宽作用于每一个具体 Bragg peak。展宽之后：

- 哪些峰开始发生重叠；
- 哪些肩峰消失；
- 局部峰群如何合并；
- 峰间距信息被压缩到什么程度；

都由原始 parent structure 的峰位置和峰群布局决定。因此，broadening 对模型造成的困难具有明显的 parent-dependent 特征。

### Texture 的结构耦合

择优取向使用结构条件的 March–Dollase 模型，对具体 `hkl` reflection families 的相对强度进行系统重加权。它直接依赖 reciprocal vectors、晶面族和原始反射强度，因此具有更明确的 parent-specific 结构依赖。

相比之下，全谱 peak shift 更接近统一坐标轴变换，noise 主要改变观测统计，background 主要改变基线形状。因此，same-parent relationship supervision 在 broadening 和 texture 上获得更大的收益具有明确的 XRD 物理解释：

> **当测量扰动与潜在晶体结构耦合得越深，同一个 parent 在不同测量状态下保持预测一致这一关系，就越具有信息量。**

### 机制补充：same-parent 与 same-class pairing

为了进一步观察 parent relation 的作用，项目进行了 Validation-only pairing ablation，将 same-parent JS 与“同晶系、不同 parent”的 same-class JS 进行比较。100-epoch extension 中：

```text
same-parent mean OOD Macro-F1 = 0.7106
same-class  mean OOD Macro-F1 = 0.6979
Δ = +1.27 pp
```

更值得关注的是逐扰动差值：

| 扰动 | same-parent − same-class Macro-F1 |
|---|---:|
| Background | +0.70 pp |
| **Broadening** | **+5.19 pp** |
| Noise | −0.70 pp |
| Shift − | −0.39 pp |
| Shift + | −0.52 pp |
| **Texture** | **+3.34 pp** |

这个补充实验与正式 ERM-vs-JS profile 结果形成一致的物理图景：**same-parent relation 的额外价值主要集中在 broadening 和 texture 这类强结构耦合扰动。**

---

# 3. Discussion

## 3.1 从数据增强到关系监督

传统 PXRD synthetic-data pipeline 的主要作用是扩大训练数据覆盖：

```text
crystal structure
    ↓
simulator
    ↓
perturbed PXRD patterns
    ↓
classification training
```

本项目在同一流程中继续利用 simulator-retained provenance：

```text
crystal structure s
   ↙          ↘
view x1      view x2
   \          /
    same parent
        ↓
measurement equivalence
        ↓
relationship supervision
```

因此，模型不仅看到“更多不同的谱”，还被明确告知“哪些变化属于同一个物理对象允许出现的测量变化”。这种关系信息对于科学测量问题尤其自然，因为许多表征数据都可以表示为：

```text
measurement = latent material state + acquisition-dependent nuisance
```

same-parent consistency 的作用，就是利用已知 latent identity 约束模型对 nuisance 的敏感性。

## 3.2 为什么第三条结论具有 XRD 特异性

本项目最重要的物理观察，是性能增益与 perturbation 的结构耦合程度存在对应关系。

Broadening 改变峰宽并重新组织局部峰重叠；texture 改变具体晶面族的相对强度。这两种变化会重构模型用于识别晶系的峰形和峰强关系，因此同母结构的跨视图一致性提供了高价值监督。

Peak shift、noise 和 background 仍会降低模型性能，也能够从一致性中受益；但它们对具体 parent structure 的依赖程度相对更弱。由此形成一个更一般的 AI-for-characterization 认识：

> **关系监督的价值取决于测量 nuisance 与潜在材料结构之间的耦合程度。**

这个认识使本项目从“用 JS 提高一个分类分数”进一步发展成“利用科学模拟器中的对象身份，学习结构条件下的测量不变性”。

## 3.3 真实域意义

RRUFF 与 CNRS 对应两种不同的实验使用场景：RRUFF-301 关注少量真实标签可用时的 adaptation efficiency；CNRS-318 关注没有目标域标签时的 frozen zero-shot transfer。两类实验结果都与模拟域的主趋势一致，因此 same-parent consistency 的收益能够从 controlled simulation 延伸到真实实验来源。

当前最完整的证据链可以概括为：

```text
simulated OOD robustness
        +
experimental zero-shot improvement
        +
few-shot label efficiency
        +
structure-coupled perturbation advantage
```

---

# 4. Methods

## 4.1 Task and structural dataset

任务为七晶系 single-label classification：

```text
triclinic
monoclinic
orthorhombic
tetragonal
trigonal
hexagonal
cubic
```

结构数据来自 14,060 个 Materials Project parent structures。以 `structure_fingerprint` 定义 parent identity，并在任何在线扰动生成之前完成按晶系分层的 parent-level split：

| Split | Parent structures |
|---|---:|
| Train | 9,842 |
| Validation | 2,109 |
| Test | 2,109 |

该 split 保证同一母结构生成的不同 measurement views 始终位于同一数据划分中。

## 4.2 PXRD representation

理想衍射峰由：

```python
pymatgen.analysis.diffraction.xrd.XRDCalculator(wavelength="CuKa")
```

计算。输入区间与采样为：

- `2θ = 10°–80°`
- step size = `0.02°`
- 3501 points / pattern
- final max normalization

模拟器同时保留 peak positions、relative intensities、`hkl`、multiplicity 和 reciprocal-vector information，用于后续 preferred-orientation 建模。

## 4.3 Peak rendering

离散理想反射通过 Gaussian profile 渲染：

\[
\sigma=\frac{\mathrm{FWHM}}{2\sqrt{2\ln2}}
\]

\[
I(2\theta)=\sum_i\frac{A_i}{\sigma}
\exp\left[-\frac12\left(\frac{2\theta-2\theta_i}{\sigma}\right)^2\right]
\]

峰强以 integrated peak strength 处理，除以 `σ` 使 FWHM 变化时峰面积保持稳定。

## 4.4 Physics-informed online perturbations

正式训练和 OOD 评测使用以下冻结扰动：

| 扰动 | Train / in-range | Single-factor OOD |
|---|---|---|
| Global 2θ shift | `U(-0.2,0.2)°`, p=0.5 | `[-0.5,-0.2]°` / `[0.2,0.5]°` |
| Peak broadening | FWHM `U(0.08,0.20)°` | FWHM `U(0.20,0.35)°` |
| Preferred orientation | March–Dollase `r=0.8–1.0`, p=0.7 | `r=0.5–0.8` |
| Background | 3rd-order polynomial, ratio `0–0.02` | GP background, ratio `0.02–0.05` |
| Noise | Poisson–Gaussian, count scale `2500–40000`, electronic `0–2 counts` | count scale `100–2500`, electronic `0–5 counts` |

Preferred orientation 使用 March–Dollase：

\[
P(\alpha;r)=\left[r^2\cos^2\alpha+\frac1r(1-\cos^2\alpha)\right]^{-3/2}
\]

完整 forward chain 为：

```text
parent crystal structure
→ ideal reflection table
→ preferred orientation
→ global 2θ shift
→ Gaussian broadening
→ smooth background
→ Poisson / readout noise
→ clipping
→ max normalization
```

## 4.5 Model architecture and training

模型采用一维 ResNet-18-GN，输入为 3501 点 PXRD，输出七晶系 softmax probability。

| Training item | Setting |
|---|---|
| Backbone | 1D ResNet-18-GN |
| Optimizer | AdamW |
| Learning rate | `1×10⁻⁴` |
| Weight decay | `1×10⁻⁴` |
| Batch | 16 parents × 2 online views = 32 patterns |
| Maximum epochs | 100 |
| Validation | every 10 epochs |
| Checkpoint selection | Validation performance |
| JS weight | `λ_JS = 60` |

`λ_JS=60` 由 Validation 选择并在正式 simulated Test 与真实域评测前冻结。

## 4.6 Same-parent consistency objective

每个 parent 生成两条独立 measurement views：

\[
x_1=g(s,m_1),\qquad x_2=g(s,m_2)
\]

分类项为：

\[
\mathcal L_{cls}
=\frac12\left[
CE(f(x_1),y)+CE(f(x_2),y)
\right]
\]

令 `p1,p2` 为两条谱的预测概率，

\[
m=\frac12(p_1+p_2)
\]

\[
JS(p_1,p_2)
=\frac12KL(p_1\|m)+\frac12KL(p_2\|m)
\]

最终 same-parent JS objective 为：

\[
\mathcal L
=\mathcal L_{cls}+60\,JS(p_1,p_2)
\]

Dynamic ERM 使用相同的双视图分类项；因此两者的核心差异就是 same-parent prediction consistency。

## 4.7 Experimental-domain evaluation

### RRUFF-301

RRUFF-301 用于 few-shot adaptation 和 label-efficiency evaluation。采用相同 frozen-backbone adaptation procedure，对 ERM-pretrained 与 JS-pretrained representation 使用相同真实标签预算：

- K = 1 / 2 / 5 labels per class
- 5 pretraining seeds
- 5 episode seeds
- paired locked-test comparison
- primary reporting: Macro-F1、Accuracy、learning curve 与 per-class behavior

### CNRS-318

CNRS-318 用于 independent experimental zero-shot evaluation：

- 318 independent structural parents
- natural class distribution：`21 / 87 / 77 / 41 / 33 / 12 / 47`
- frozen model inference
- reporting：Macro-F1、Balanced Accuracy、Accuracy，以及 probability-quality supporting metrics

---

# 5. 当前三大主要结论

## 结论一：总体分类性能稳定提升

Same-parent JS consistency 在冻结模拟 Test 上稳定提升 Macro-F1 和 Accuracy，并在 RRUFF 与 CNRS 两个实验来源中继续表现出同方向的分类性能改善。

## 结论二：真实谱适配的标签效率更高

RRUFF-301 的 K=1/2/5 learning curve 显示，在完全相同的真实标签预算下，JS-pretrained representation 始终取得更高 Macro-F1 和 Accuracy，说明真实标签能够被更有效地利用。

## 结论三：强结构耦合扰动下的鲁棒性优势最明显

Broadening 与 preferred orientation / texture 在正式 simulated Test 中获得最大的性能增益；same-parent vs same-class 的机制补充实验也把额外优势定位到这两类扰动。结果说明，当 measurement nuisance 与具体晶体衍射结构耦合更强时，parent-aware relationship supervision 的价值更高。

---

# 6. 证据来源

当前技术备忘录的数据与方法以以下仓库文件为准：

- `xrd_robustness/reports/RESULTS.md`：正式 simulated Test、RRUFF-301、CNRS-318 结果
- `xrd_robustness/reports/simulated_test_results.json`：五 seed simulated Test 原始汇总
- `xrd_robustness/outputs/pairing_ablation_extend100/summary.json`：same-parent / same-class 机制补充结果
- `xrd_robustness/configs/simulation.method_transfer.frozen.json`：正式冻结的 PXRD 扰动配置
- `docs/PXRD_PERTURBATION_EVIDENCE.md`：五类扰动的物理与文献依据
- `docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`：数据构建、split、训练与 λ_JS 的方法证据
- `docs/PROJECT_HISTORY_NOTE_2026-09-14_XRD_THREE_MAIN_CONCLUSIONS.md`：当前三大主要结论

代表性 XRD-ML 写作参考包括 Oviedo et al. (2019)、Lee et al. (2023) 及项目中已审读的 Schopmans 等工作：以实验/模拟条件和模型设置构成 Methods，以 Accuracy、F1、真实谱迁移、逐扰动与逐类行为构成 Results，并在 Discussion 中解释性能变化背后的 XRD 物理机制。
