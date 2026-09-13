# PXRD 七晶系鲁棒分类：技术细节备忘录（社区范式精简版）

**用途：** 导师汇报、论文 Methods/Results 对照、XRD 物理追问。  
**日期：** 2026-09-13  
**范围：** 仅记录已完成并冻结的七晶系鲁棒分类主线；后续参数反演/因子解耦属于另一研究模块。

## 0. 社区范式：哪些参数写进报告，写在哪里

本报告按代表性 XRD/PXRD 机器学习论文的组织方式处理参数：**XRD 测量/模拟条件写在 Experimental / Data preparation / Methods；模型训练参数用一张紧凑 Methods 表交代；真正的 Results 只放 Accuracy、F1、逐类/扰动表现和真实谱结果。**

| 参数类型 | 在 XRD-ML 论文中的典型角色 | 本报告处理 |
|---|---|---|
| 2θ 范围、步长、波长 | XRD 表征/实验或模拟条件，属于 Methods/Experimental | **保留并突出** |
| 数据来源、筛选、train/test split | 数据与评测协议，直接影响科学有效性 | **保留并突出** |
| 峰移、展宽、texture、背景、噪声范围 | synthetic-data generation / physics-informed augmentation | **保留并突出** |
| 归一化、重采样、实验谱预处理 | 数据预处理 Methods | **保留** |
| backbone 与主要结构 | model Methods；通常用示意图或一小段说明 | **简写** |
| optimizer、learning rate、batch size、epochs | training Methods；常见于 Methods 或 Supplementary | **一张紧凑表** |
| λ_JS | 本文方法本身的超参数 | **Methods 中保留；只说明最终值与验证集选择** |
| early stopping/checkpoint 规则 | training detail | **只保留一句，不展开内部阈值** |

Lee 等人的 Experimental Section 会明确写 2θ 范围、步长、数据筛选和 perturbation 生成方式；复杂超参数搜索则放 Supporting Information。Oviedo 将仪器条件、预处理和 physics-informed augmentation 放在 Methods，同时只有当 2θ step size 被专门研究为“采集速度–准确率权衡”时，它才升级为 Results。Schopmans 把 wavelength、模拟方式、split 与 online-training setup 放在 Methods/ESI；batch size 与 epoch 数在其工作中之所以被强调，是因为“持续生成多少唯一衍射谱”本身属于研究方法的一部分。

因此，本报告不再把训练工程细节当“结果”。

---

# 1. 研究问题与主结果

研究问题：在完全相同的母结构、在线扰动分布、ResNet backbone 和双视图数据暴露下，显式利用“同一母结构的两次测量属于同一个物理对象”这一关系，是否能比普通 Dynamic ERM 获得更好的 PXRD 扰动鲁棒性？

`same parent → measurement-equivalent views → CE + JS prediction consistency`

| 评测域 | Dynamic ERM | JS consistency | 变化 |
|---|---:|---:|---:|
| 模拟 Test · 单因素 OOD Accuracy | 0.6508 ± 0.0078 | 0.7052 ± 0.0086 | +5.45 pp |
| 模拟 Test · 单因素 OOD Macro-F1 | 0.6507 ± 0.0072 | 0.7053 ± 0.0098 | +5.46 pp |
| RRUFF-301 · 1-shot Macro-F1 / Accuracy | 0.2847 / 0.2990 | 0.3280 / 0.3375 | +4.33 / +3.84 pp |
| RRUFF-301 · 2-shot Macro-F1 / Accuracy | 0.3026 / 0.3120 | 0.3486 / 0.3609 | +4.60 / +4.88 pp |
| RRUFF-301 · 5-shot Macro-F1 / Accuracy | 0.3555 / 0.3581 | 0.4099 / 0.4149 | +5.45 / +5.68 pp |
| CNRS-318 · Macro-F1 | 0.1912 | 0.2091 | +1.79 pp |
| CNRS-318 · Balanced Accuracy | 0.2182 | 0.2388 | +2.06 pp |
| CNRS-318 · Accuracy | 0.2000 | 0.2101 | +1.01 pp |

**主结论：** JS 在冻结模拟 Test 上同时提高 top-1 Accuracy 与 Macro-F1；在 RRUFF-301 上提高少样本适配性能；在独立 CNRS-318 实验来源上，Macro-F1、Balanced Accuracy 与 Accuracy 也同向提高。CNRS 的绝对 Accuracy 仍仅约 0.21，因此结果支持“相对鲁棒性改善”，不支持“广义 Sim-to-Real 已解决”。

---

# 2. 数据与 XRD 表征（Methods）

- 任务：七晶系 single-label classification。
- 类别顺序：triclinic / monoclinic / orthorhombic / tetragonal / trigonal / hexagonal / cubic。
- 输入角度：2θ = 10°–80°。
- 步长：0.02°，共 3,501 点。
- 主模拟器：`pymatgen.analysis.diffraction.xrd.XRDCalculator(wavelength="CuKa")`。
- 强度进入网络前做 max normalization。

数据来自 14,060 个 Materials Project 晶体结构。当前冻结 split 以 `structure_fingerprint` 为 parent identity，按晶系分层：

| Split | Parent structures |
|---|---:|
| Train | 9,842 |
| Validation | 2,109 |
| Test | 2,109 |

同一 parent 的不同扰动谱不会跨 split。该 split 解决的是**精确母结构泄漏**，不是 chemical-family/prototype-disjoint benchmark。

---

# 3. PXRD forward model 与物理扰动（Methods）

主链：

`crystal structure → ideal reflection table → preferred orientation (optional) → global 2θ shift → Gaussian broadening → smooth background → count/readout noise → max normalization`

## 3.1 理想反射与峰形

`XRDCalculator` 产生理想峰位与相对强度，同时保留 hkl、multiplicity 和 reciprocal-vector 信息。随后用 Gaussian profile 渲染：

`σ = FWHM / [2√(2 ln2)]`

`I(2θ) = Σ (A_i/σ) exp[-0.5((2θ−2θ_i)/σ)^2]`

最小 FWHM 为 0.08°，对应 0.02° 网格上约 4 个 sampling bins/FWHM。这里使用的是统一标量 FWHM 代理，不等同于完整 Caglioti/Scherrer 仪器峰形模型。

## 3.2 五类冻结扰动

| 扰动 | Train / in-range | Single-factor OOD | 物理角色 |
|---|---|---|---|
| 全谱峰位偏移 | Δ2θ ~ U(-0.2, 0.2)°, p=0.5 | [-0.5,-0.2]° / [0.2,0.5]° | 零点、样品高度或标定型角度偏移 |
| 峰展宽 | FWHM ~ U(0.08,0.20)° | U(0.20,0.35)° | 有效峰宽变化 |
| 择优取向 | March–Dollase r ~ U(0.8,1.0), p=0.7 | r ~ U(0.5,0.8) | 晶面族相对强度系统变化 |
| 背景 | 三阶 polynomial，ratio 0–0.02 | GP，ratio 0.02–0.05 | 平滑非负实验背景 |
| 计数/读出噪声 | C~LogU(2500,40000)，σe=0–2 counts | C~LogU(100,2500)，σe=0–5 counts | Poisson counting + electronic readout |

March–Dollase：

`P(α;r) = [r²cos²α + (1/r)(1−cos²α)]^(-3/2)`

这些范围定义的是**文献锚定、物理合理的冻结扰动空间**，不是某一台仪器的经验误差分布；`apply_probability` 也是数据生成设置，不是现实发生频率。

---

# 4. 模型与训练（Methods，按社区习惯简写）

模型采用 ML4pXRDs 风格的一维 ResNet-18（PyTorch port），使用 GroupNorm。网络读取 3,501 点一维 PXRD，经过一维卷积和残差块提取特征，最后输出七晶系概率。

| Training item | Frozen setting |
|---|---|
| Backbone | 1D ResNet-18-GN |
| Optimizer | AdamW |
| Learning rate | 1×10⁻⁴ |
| Weight decay | 1×10⁻⁴ |
| Batch construction | 16 parents × 2 online views = 32 patterns/update |
| Maximum training | 100 epochs |
| Validation frequency | every 10 epochs |
| Early stopping | used after a minimum training period |
| Preprocessing after rendering | identity; max normalization already applied by simulator |

这些参数的角色与 XRD-ML 论文中的 training setup 相同：**为了让别人知道模型怎么训练，而不是作为科学结果本身。** 不再报告 fused AdamW、AMP/bfloat16、batch 尾部补齐、stop epoch、step count 等运行工程细节。

---

# 5. JS consistency 方法（Methods）

对同一母结构在线生成两个独立测量视图：

`x1 = g(s,m1),  x2 = g(s,m2)`

Dynamic ERM 和 JS 都对两张谱进行相同的晶系交叉熵监督：

`L_cls = 0.5[CE(f(x1),y) + CE(f(x2),y)]`

JS 额外使用同母结构关系：

`JS(p1,p2)=0.5 KL(p1||m)+0.5 KL(p2||m),  m=0.5(p1+p2)`

`L = L_cls + 60 × JS(p1,p2)`

正式 `λ_JS=60` 仅由 Validation 选择；冻结 Test、RRUFF、CNRS 不参与选参。

---

# 6. Frozen simulated Test（正式模拟结果）

| 指标 | Dynamic ERM | JS consistency | 改善 |
|---|---:|---:|---:|
| In-range Macro-F1 | 0.6953 | 0.7349 | +3.96 pp |
| Mean single-factor OOD Accuracy | 0.6508 ± 0.0078 | 0.7052 ± 0.0086 | +5.45 pp |
| Mean single-factor OOD Macro-F1 | 0.6507 ± 0.0072 | 0.7053 ± 0.0098 | +5.46 pp |

五个 matched training seeds 的主 OOD Accuracy 与 Macro-F1 均为 JS 更高。

按照 XRD 分类论文的读法，这里最重要的是：**在未参与选参的冻结模拟 Test 上，面对更强峰移、展宽、texture、背景和噪声扰动，JS 的 top-1 classification performance 稳定高于 matched Dynamic ERM。**

后续若做 failure analysis，应优先从 frozen predictions 重建：

- 7×7 confusion matrix；
- 各晶系 F1/recall；
- 各物理 perturbation profile 的 Accuracy/F1；
- 代表性错分谱。

这些都属于真正 XRD-ML 解释性结果，而不是增加更多 AI 指标。

---

# 7. RRUFF-301：few-shot 实验域

RRUFF-301 是平衡、人工整理的实验矿物域：七晶系各 43 条；其中 10/class 构成 adaptation pool，33/class 为 locked test。K=1/2/5 分别使用每类 1、2、5 条真实谱进行少样本适配。

主结果按 XRD-ML 社区习惯直接报告 Accuracy + Macro-F1：

| K | ERM Macro-F1 | JS Macro-F1 | ERM Accuracy | JS Accuracy |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 |
| 2 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 |
| 5 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 |

**解释：** 相同真实标签预算下，JS 预训练模型在 K=1/2/5 都获得更高实验谱分类性能；随着真实标签增加，两种方法都改善，而 JS 的优势持续存在。因此 RRUFF 最适合表述为 **label efficiency / few-shot adaptation**，而不是广义 unseen-mineral 泛化。

---

# 8. CNRS-318：独立来源 zero-shot

CNRS-318 含 318 个独立 structural parents，七晶系 support 为：

`21 / 87 / 77 / 41 / 33 / 12 / 47`

它不参与 adaptation、λ 选择或 checkpoint 选择。原始谱按 Bragg relation 统一至 `λ_target=1.5406 Å`，再插值到 10–80° / 0.02° 网格并 max-normalize。

由于类别天然不平衡，主表使用 Macro-F1、Balanced Accuracy 和 Accuracy：

| 指标 | Dynamic ERM | JS consistency | 变化 |
|---|---:|---:|---:|
| Macro-F1 | 0.1912 | 0.2091 | +1.79 pp |
| Balanced Accuracy | 0.2182 | 0.2388 | +2.06 pp |
| Accuracy | 0.2000 | 0.2101 | +1.01 pp |

### Per-class F1

| 晶系 | n | ERM F1 | JS F1 | ΔF1 |
|---|---:|---:|---:|---:|
| triclinic | 21 | 0.1474 | 0.1767 | +0.0292 |
| monoclinic | 87 | 0.2928 | 0.2801 | -0.0128 |
| orthorhombic | 77 | 0.1123 | 0.1811 | +0.0688 |
| tetragonal | 41 | 0.2984 | 0.2362 | -0.0623 |
| trigonal | 33 | 0.0968 | 0.1015 | +0.0047 |
| hexagonal | 12 | 0.1667 | 0.2500 | +0.0833 |
| cubic | 47 | 0.2238 | 0.2383 | +0.0145 |

**解释：** JS 在总体三项分类指标上改善，并提高 5/7 个晶系的 pooled F1；monoclinic 与 tetragonal 下降。hexagonal 只有 12 个 parent，因此不能把该类较大的 F1 涨幅当作强结论。更重要的是，绝对 Accuracy 仍约 0.21，说明第二真实来源上的 sim-to-real gap 仍然很大。

---

# 9. 正式报告只保留的支持性结果（Tier B）

正式汇报允许保留的支持性信息仅包括：

- mean ± SD；
- matched-seed 方向一致性（如 5/5）；
- per-class F1 / support；
- confusion matrix；
- representative failure cases；
- 必要时一句话说明 probability quality 与分类改善同向。

其余内部审计与运行记录不进入正式报告，保留在本地结果文件和项目记录中。

---

# 10. 报告边界

可以说：

- 在冻结模拟 Test 上，JS 提高 OOD Accuracy 与 Macro-F1；
- RRUFF-301 支持更好的 few-shot label efficiency；
- CNRS-318 提供第二独立实验来源上的正向总体分类证据；
- same-parent provenance 被用作 measurement-equivalence supervision。

不能说：

- JS、consistency 或 online PXRD simulation 是本项目首创；
- 当前扰动分布精确对应某一台真实仪器；
- family/prototype leakage 已被完全排除；
- 所有晶系都得到一致改善；
- 广义 Sim-to-Real 已经解决。

---

# 外部参考

1. Lee BD et al. *Advanced Intelligent Systems* 2023, 5, 2300140. DOI: 10.1002/aisy.202300140.
2. Oviedo F et al. *npj Computational Materials* 2019, 5, 60. DOI: 10.1038/s41524-019-0196-x.
3. Schopmans H, Reiser P, Friederich P. *Digital Discovery* 2023, 2, 1414–1424. DOI: 10.1039/d3dd00071k.

### 波长边界

- 主分类模拟器：`XRDCalculator(wavelength="CuKa")`。
- CNRS 统一化：`λ_target=1.5406 Å`。
- 后续 inversion 模块中的 `1.54184 Å` 属于另一研究模块，不能回填到本分类实验。
