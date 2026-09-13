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

这些参数的角色与 XRD-ML 论文中的 training setup 相同：**为了让别人知道模型怎么训练，而不是作为科学结果本身。**

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

## 6.1 各物理扰动下的分类性能

下面把六个 single-factor OOD 条件拆开。每个数字先在同一 training seed 内平均 3 个固定 evaluation seeds，再对 5 个 training seeds 报 mean ± SD；因此六行的平均值与上面的 mean single-factor OOD 总结果严格一致。

| 物理扰动 | ERM Macro-F1 | JS Macro-F1 | ΔF1 | ERM Accuracy | JS Accuracy | ΔAcc |
|---|---:|---:|---:|---:|---:|---:|
| Peak shift − | 0.6926 ± 0.0034 | 0.7290 ± 0.0142 | +3.64 pp | 0.6938 ± 0.0022 | 0.7294 ± 0.0135 | +3.56 pp |
| Peak shift + | 0.6871 ± 0.0058 | 0.7307 ± 0.0083 | +4.36 pp | 0.6891 ± 0.0057 | 0.7313 ± 0.0071 | +4.22 pp |
| Broadening | 0.5517 ± 0.0633 | 0.6357 ± 0.0268 | **+8.40 pp** | 0.5441 ± 0.0636 | 0.6330 ± 0.0255 | **+8.89 pp** |
| Noise | 0.6712 ± 0.0044 | 0.7033 ± 0.0109 | +3.22 pp | 0.6714 ± 0.0037 | 0.7020 ± 0.0100 | +3.07 pp |
| Background | 0.6827 ± 0.0038 | 0.7332 ± 0.0115 | +5.05 pp | 0.6825 ± 0.0052 | 0.7339 ± 0.0111 | +5.13 pp |
| Preferred orientation / texture | 0.6191 ± 0.0211 | 0.7000 ± 0.0120 | **+8.09 pp** | 0.6238 ± 0.0179 | 0.7018 ± 0.0106 | **+7.80 pp** |

六种 single-factor OOD 中，五个 training seeds 的平均 Macro-F1 差值均为正。**Broadening 和 texture 是 ERM 绝对性能下降最明显、同时也是 JS 增益最大的两类扰动；background 次之，而 noise 和单纯全谱 shift 的增益较小但仍为正。**

这让“+5.46 pp”不再只是一个平均 OOD 数字，而有了明确的 XRD 物理含义：当前方法的优势主要集中在**峰宽变化和相对峰强系统变化**这两类更强地改变峰形/峰强关系的测量条件上。这个现象支持“同母结构约束帮助模型减少对测量状态的依赖”这一解释，但不能单独证明具体机制。

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

## 7.1 晶系级行为：早期 monoclinic 负迁移未在 RRUFF-301 复制

早期较小的 RRUFF-70 探索曾出现 monoclinic 负迁移，但 RRUFF-301 v2 的确认性结果为：

| K | ERM monoclinic F1 | JS monoclinic F1 | ΔF1 |
|---:|---:|---:|---:|
| 1 | 0.2374 | 0.2735 | +3.60 pp |
| 2 | 0.2335 | 0.3016 | +6.81 pp |
| 5 | 0.2294 | 0.2985 | +6.91 pp |

因此，monoclinic 的早期负迁移更适合解释为小样本探索阶段的不稳定类级信号，而不是稳定的方法边界。

## 7.2 Fix / break：JS 改正了更多实验谱，但收益并非所有晶系一致

对每个 K 的 25 组 paired adaptation 结果逐样本比较，可以统计“ERM 错、JS 对”的 fix 与“ERM 对、JS 错”的 break：

| K | 被 JS 净改善的 test samples | 被 JS 净损伤的 test samples | JS-only correct episodes | ERM-only correct episodes | Fix/Break ratio |
|---:|---:|---:|---:|---:|---:|
| 1 | 112 | 78 | 934 | 712 | 1.31 |
| 2 | 110 | 66 | 936 | 654 | 1.43 |
| 5 | 103 | 70 | 902 | 574 | 1.57 |

K=5 时，各晶系跨 25 组 paired runs 的**净正确次数变化**为：triclinic +68、monoclinic +74、orthorhombic +116、tetragonal +30、trigonal −14、hexagonal +81、cubic −27。也就是说，整体性能提升并不是“七个晶系全部等比例变好”：orthorhombic、hexagonal、monoclinic 等类受益明显，而 trigonal 和 cubic 在这一诊断下仍存在局部退化。

## 7.3 代表性成功/失败样本

现有预测分析已经能定位最值得画进论文的真实谱案例。以 K=5、25 组 paired runs 为例：

- **明显被 JS 修正：** `R090034`（orthorhombic，24 次 JS-only correct / 0 break）、`R070562`（triclinic，22 / 0）、`R050008`（orthorhombic，19 / 0）、`R050027`（hexagonal，19 / 0）。
- **明显被 JS 损伤：** `R050657`（triclinic，0 fix / 20 break）、`R040027`（cubic，0 / 18）、`R050609`（cubic，2 / 16）。

这些 ID 已足以作为后续“代表性实验谱”图的优先候选。**但当前 Git 仓库没有追踪这些原始 RRUFF XRD trace，因此本报告只记录可复核的分类行为，不根据样本 ID 臆测具体峰缺失、背景、texture 或杂相原因。**若要做成熟论文式 spectrum-level failure analysis，应从本地 RRUFF 原始资产调出上述谱线，再逐条解释其峰形与混淆来源。

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

**解释：** JS 在总体三项分类指标上改善，并提高 5/7 个晶系的 pooled F1；其中 orthorhombic 增益较明确。monoclinic 与 tetragonal 下降，尤其 tetragonal 从 0.2984 降至 0.2362；已有 confusion 分析显示，JS 下有更多 tetragonal 谱被路由到 trigonal。hexagonal 虽从 0.1667 升至 0.2500，但只有 12 个 parent，因此不能把该类较大的 F1 涨幅当作强结论。

更重要的是，绝对 Accuracy 仍约 0.21，说明第二真实来源上的 sim-to-real gap 仍然很大。CNRS 的价值不是证明“真实域已经解决”，而是说明：在一个更困难、自然不平衡的独立实验来源上，整体分类指标仍保持同向改善，同时暴露出明确的晶系级失败模式。

---

# 9. 跨域 Discussion：当前结果真正说明了什么

把模拟 Test、RRUFF-301 和 CNRS-318 放在一起看，可以得到三个更接近成熟 XRD-ML 论文的结论：

1. **改善具有明确的扰动物理结构。** 模拟域中 broadening 与 texture 是 ERM 最困难、也是 JS 增益最大的条件；单纯 peak shift 与 noise 的提升较小。这说明方法优势不是均匀撒在所有 profile 上，而主要出现在会明显改变峰宽或相对峰强关系的条件。
2. **真实域收益具有标签效率和晶系异质性。** RRUFF 的 K-shot learning curve 持续 favor JS，而且 fix/break ratio 从 1.31 增至 1.57；但 trigonal/cubic 等类仍可出现局部退化。成熟的结论应同时展示平均提升和哪些晶系受益/受损。
3. **独立来源上仍有明显 sim-to-real gap。** CNRS 的整体三项分类指标改善，但绝对 Accuracy 约 0.21，tetragonal 还出现明显下降。因此当前证据支持“更稳健”，不支持“真实域已经解决”。

这三点把文章从“一个平均 OOD 分数更高”推进到：**在哪些 XRD 测量变化、哪些晶系和哪些真实谱上更好，以及哪里仍然失败。**

## 9.1 目前仍缺的唯一关键归因对照

仓库中**没有找到** `same-parent JS` 与 `same-class but different-parent JS` 的直接消融。因此当前可以严格支持的是：

> matched Dynamic ERM < same-parent JS consistency。

但还不能进一步声称：

> same-parent identity 本身已经被证明优于任何一般性的 same-class consistency pairing。

如果未来需要把“simulator-retained parent identity”作为论文最强的方法学归因，最值得新增的实验仍然是：

`Dynamic ERM vs same-class random-pair JS vs same-parent JS`

这属于一个新的方法消融，不应伪装成当前已有结果。

---

# 10. 成熟论文的最终图表结构

基于当前已找到的冻结结果，最终论文/汇报不需要再增加更多 AI 指标，而应优先形成下面五类 XRD 图表：

1. **Method / XRD forward figure**：同一 parent → 两个物理扰动 view → ERM vs JS；同时展示 shift、broadening、texture、background、noise 的谱形变化。
2. **Profile-wise robustness figure**：六个 single-factor OOD 的 Accuracy / Macro-F1，突出 broadening 与 texture 的最大增益。
3. **RRUFF few-shot learning curve**：K=1/2/5 的 Accuracy 与 Macro-F1；辅以 K=5 fix/break 或 per-class 行为。
4. **Representative experimental spectra**：优先调出 `R090034` / `R070562` 等 JS-improved 谱与 `R050657` / `R040027` 等 JS-damaged 谱，展示真实峰形并解释为什么发生错分。
5. **CNRS per-class/confusion figure**：七晶系 F1 change + support，并突出 tetragonal→trigonal 的失败模式。

前 1–3 和第 5 类图所需数值证据已经存在；第 4 类图还需要读取 Git 未追踪的本地原始 RRUFF spectrum trace，不能由当前 tracked summary 凭空生成。

---

# 11. 正式报告只保留的支持性结果（Tier B）

正式汇报允许保留的支持性信息仅包括：

- mean ± SD；
- matched-seed 方向一致性（如 5/5）；
- per-class F1 / support；
- confusion matrix；
- representative failure cases；
- 必要时一句话说明 probability quality 与分类改善同向。

其余内部审计与运行记录不进入正式报告，保留在本地结果文件和项目记录中。

---

# 12. 报告边界

可以说：

- 在冻结模拟 Test 上，JS 提高 OOD Accuracy 与 Macro-F1；
- 六类单因素扰动的 seed-averaged Macro-F1 均为正向，其中 broadening / texture 增益最大；
- RRUFF-301 支持更好的 few-shot label efficiency，并且现有 fix/break 分析显示 JS 总体修正的实验谱多于损伤的实验谱；
- CNRS-318 提供第二独立实验来源上的正向总体分类证据，同时暴露 tetragonal 等类的退化；
- same-parent provenance 被用作 measurement-equivalence supervision。

不能说：

- JS、consistency 或 online PXRD simulation 是本项目首创；
- 当前扰动分布精确对应某一台真实仪器；
- family/prototype leakage 已被完全排除；
- 所有晶系都得到一致改善；
- same-parent pairing 已被证明优于 same-class random pairing；
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
