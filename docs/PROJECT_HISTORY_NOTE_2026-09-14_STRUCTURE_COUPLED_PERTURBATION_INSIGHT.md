# 项目发展记录：same-parent consistency 对结构耦合扰动的额外价值

**日期：** 2026-09-14  
**性质：** same-class 机制挑战带来的额外科学收获；不改变 ERM–JS 主结果。

## 背景

项目主问题早已由 matched Dynamic ERM vs Dynamic JS 回答：在完全相同的数据暴露、扰动、backbone、optimizer、训练预算与 paired seeds 下，加入“同一母结构的两条 measurement views 应保持预测一致”的 JS 关系监督，能够提高 PXRD 晶系分类的模拟 OOD 鲁棒性，并在 RRUFF / CNRS 真实域中留下支持性证据。

随后为了追问更强的问题——parent identity 是否比 generic same-class consistency 更特殊——新增了 `same-class different-parent JS` 探索性对照。100-epoch replay 显示：same-class consistency 经过充分训练后可以在总体 mean OOD 上逼近 same-parent，因此不能把 parent identity 解释为 consistency 收益的唯一来源。

## 最大意外收获

这次挑战真正带来的价值，不是证明“same-parent 一定比 same-class 更强”，而是暴露出一个更物理化的现象：

> **same-parent consistency 的额外收益具有明显的扰动类型选择性；它在与具体晶体衍射结构强耦合的扰动上尤其突出，而在弱结构耦合扰动上优势很小。**

单 seed exploratory 结果中，same-parent 相对 same-class 的 profile-wise Macro-F1 差值约为：

- peak shift negative：约 `-0.39 pp`；
- peak shift positive：约 `-0.52 pp`；
- noise：约 `-0.70 pp`；
- background：约 `+0.70 pp`；
- broadening：约 `+5.19 pp`；
- preferred orientation / texture：约 `+3.34 pp`。

这意味着六个 OOD profile 全部简单平均会把 broadening / texture 上更明显的 parent-specific effect 稀释掉。

## 物理解释

### 弱结构耦合扰动

- **2theta shift**：主要是整条衍射轴施加统一零点偏移；扰动参数本身不需要知道母结构是谁。
- **background**：主要在测量轴上加入平滑基线；虽然幅值相对 clean peak 定义，但其形状不是由具体 hkl 关系决定。
- **noise**：正式模拟采用 Poisson / Poisson-Gaussian，因此噪声强度会依赖 signal，但其物理来源主要属于观测统计而不是具体 reciprocal-lattice relation。

### 强结构耦合扰动

- **broadening**：FWHM 本身可以独立抽样，但峰展宽后哪些峰发生重叠、肩峰是否消失、局部峰群如何合并，取决于母结构原始峰位置和间距。
- **preferred orientation / texture**：March-Dollase 扰动直接通过具体结构的 hkl family 与 reciprocal-vector 几何改变相对峰强，因此天然是 parent-specific 的。

因此，same-parent relation supervision 在这两类扰动中包含的信息量更高：它告诉模型“这些外观差异虽然显著，但仍来自同一个结构”。

## 与原正式 ERM–JS 结果的呼应

这一机制线索并不是 same-class 探索后才凭空出现。原五 seed simulated Test / Validation 的 profile-wise ERM→JS 提升本来就显示：broadening 与 texture 是收益最大的两类扰动。

因此可以形成两层结论：

1. **主结论：** same-parent consistency 相比 matched ERM 能整体提升 PXRD OOD 鲁棒性；
2. **机制线索：** 这种提升在与具体晶体结构强耦合的 broadening / texture 上尤其明显。

## 申请叙事价值

这次 same-class 挑战没有推翻原方法，反而迫使项目从“consistency 能不能涨点”进一步走向：

> **什么类型的 measurement nuisance 最值得用物理同源关系去约束？**

这使项目从一般的正则化方法比较，进一步转向 scientific measurement / AI4Characterization 的问题意识：关系监督的价值取决于 measurement nuisance 与 latent material structure 的耦合方式。

这是本轮机制挑战最大的研究收获。

## 边界

当前 broadening / texture 的 parent-specific advantage 来自单 seed post-hoc mechanism exploration，因此只能作为机制线索和 Discussion 方向，不能单独升级为最终确认性结论。原 matched five-seed ERM–JS 主结果仍是正式结果主线。
