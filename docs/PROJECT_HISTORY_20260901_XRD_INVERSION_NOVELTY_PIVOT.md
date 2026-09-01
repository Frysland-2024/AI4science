# 2026-09-01 PXRD 定量反演：Novelty 重定位记录

> **性质：** 项目历史档案 / 决策记录。用于保留“为什么改变研究主线”的真实原因，供后续申请文案、组会复盘和论文叙事使用。
>
> **核心结论：** `forward reconstruction / forward consistency` 被从“主创新候选”降为“辅助物理一致性验证”，**主要原因不是该思路在本项目里失败，而是文献检索确认已有文章做过高度相近的事情。** 项目的主创新因此转向 `structure–measurement factorized inversion / disentanglement`。

---

## 1. 原先的主线候选

早期定量反演方案曾考虑把下面的闭环作为主要方法升级：

\[
\hat\theta=(\hat a,\hat c,\hat\delta,\widehat{\mathrm{FWHM}})
\rightarrow
F(\hat\theta)
\rightarrow
\hat x
\]

并通过：

\[
F(\hat\theta)\approx x_{obs}
\]

构造 `forward consistency / profile reconstruction loss`，即：

\[
L=L_{param}+\lambda_{forward}L_{forward}.
\]

当时的直觉是：模型预测参数后再用衍射前向模型生成谱，如果生成谱能解释输入谱，则参数更具有物理可信度。

---

## 2. 为什么不再把它当主 novelty

2026-09-01 的文献复核改变了 novelty 判断。

### DONUT (2025)

Luo et al., **DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis**, *npj Computational Materials* 11, 380 (2025), DOI: `10.1038/s41524-025-01860-7`。

该工作已经：

- 将 differentiable X-ray diffraction / forward scattering model 直接嵌入神经网络；
- 从预测的物理 latent parameters 重新生成 diffraction；
- 通过生成 diffraction 与实验输入之间的误差反向传播训练模型。

因此，仅以：

> “预测参数 → 可微前向衍射 → 生成谱接近输入谱”

作为本项目的核心创新，文献新颖性不够安全。

### RAPID (2026)

Mun, Nam & Choi, **Automation of Rietveld refinement through machine learning**, *Journal of Applied Crystallography* 59 (2026), DOI: `10.1107/S1600576726001494`。

该工作已经在 known-phase / single-phase 场景中使用 CNN 预测 lattice、zero shift、profile parameters 等，并将 CNN 参数用于后续 FullProf refinement 初始化。

因此：

- `XRD -> structural/profile parameters` 本身不是足够强的 novelty；
- `ML prediction -> refinement initialization` 本身也不能作为唯一主创新。

---

## 3. 2026-09-01 后的主创新重定位

真正值得作为项目中心的问题改为：

> **一张 PXRD 的变化中，哪些来自样品真实结构状态，哪些来自测量系统 / 仪器状态？能否利用模拟器天然知道的生成关系，让模型显式分解这两类因素？**

定义：

- **structure state**：`a, c`，或内部参数化 `u, v`；
- **measurement state**：`zero shift δ, FWHM w`。

对同一个变形后结构 `s*`，独立采样两个测量状态：

\[
x_1=F(s^*,m_1),\qquad x_2=F(s^*,m_2).
\]

物理上：

\[
\theta_s(x_1)=\theta_s(x_2),
\]

但：

\[
\theta_m(x_1)\neq\theta_m(x_2).
\]

因此模型的核心目标不再只是“预测四个数字”，而是学习：

\[
XRD
\rightarrow
\begin{cases}
\text{structure head}: \hat\theta_s \\
\text{measurement head}: \hat\theta_m
\end{cases}
\]

并利用 paired same-structure / different-measurement supervision 检查：

- measurement condition 改变时，结构预测应保持稳定；
- measurement head 应正确响应 zero shift / FWHM 的变化。

建议术语：

- `structure–measurement factorized inversion`；
- `structure–measurement disentanglement`；
- 中文：**结构—测量因素分解反演**。

其中 `factorized inversion` 比纯粹说 `disentanglement` 更精确，因为这里不是无监督 latent 自行分离，而是由明确物理参数和 simulator-known paired relation 提供监督。

---

## 4. Forward physics 的新位置

Forward model 不删除。

它从“主创新”调整为：

1. **physics consistency regularizer**：辅助限制预测参数；
2. **physics verification layer**：检查预测参数重新生成的谱能否解释观测；
3. **mechanism audit**：判断参数误差与 profile mismatch 是否一致。

因此项目逻辑改为：

```text
reference-conditioned PXRD
        -> structure / measurement factorized inversion
        -> paired-physics supervision
        -> forward diffraction consistency (辅助验证/正则)
        -> local refinement initialization (应用验证)
```

而不是：

```text
PXRD -> parameters -> reconstruct input spectrum
```

作为整个项目的唯一中心。

---

## 5. 这次转向为什么重要

这次变化必须保留在申请用“项目发展心路历程”中，因为它体现的不是实验失败后的被动换题，而是一次**literature-driven novelty correction**：

1. 先提出“forward reconstruction 作为 physics-guided inversion”的方案；
2. 文献检索发现 DONUT 已经把 differentiable forward diffraction reconstruction 用作核心训练机制；
3. 同时 RAPID 进一步覆盖了参数回归与 refinement initialization；
4. 因此主动降低这些部分的 novelty 权重；
5. 回到模拟器真正独有的信息结构——`同一结构状态 + 不同测量状态`；
6. 将问题重新定义为“区分 object / sample state 与 measurement process”。

这使下一阶段与前一阶段的研究逻辑形成连续升级：

```text
上一项目：measurement 改变时，classification semantics 应保持不变

下一项目：measurement 改变时，structure state 应保持不变，
         但 measurement state 应随条件正确变化
```

即从：

`measurement-invariant classification`

推进到：

`structure–measurement factorized quantitative inversion`。

---

## 6. 当前 novelty 权重排序

截至 2026-09-01，建议内部排序为：

1. **Structure–measurement factorized inversion / paired physics supervision** —— 主创新候选；
2. **Reference-conditioned correction formulation** —— 重要任务设计与辅助创新；
3. **Basin-capture / better initialization framing** —— 应用与机制价值；
4. **Forward reconstruction / differentiable physics consistency** —— 辅助物理验证，不再单独作为主 novelty。

该排序是当前阶段判断，未来若进一步文献检索发现更直接先例，应继续修正，不以本记录作为永久冻结的 novelty claim。
