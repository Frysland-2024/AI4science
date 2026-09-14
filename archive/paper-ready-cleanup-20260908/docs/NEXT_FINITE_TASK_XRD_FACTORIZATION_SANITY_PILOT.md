# 下一步有限任务：XRD 结构–测量分解最小机制验证

**日期：** 2026-09-01  
**性质：** 非正式、Train-only、有限范围机制 Pilot  
**目的：** 在进入正式大规模 ML、forward loss、independent renderer 或 refinement 之前，只回答一个问题：

> **在普通四参数监督回归已经存在的情况下，利用 simulator-known 的“同结构 / 不同测量”和“同测量 / 不同结构”关系，是否真的能减少结构参数与测量参数之间的 cross-talk？**

如果这个问题没有正结果，就不应继续把 `structure–measurement factorized inversion` 当作主创新扩展。

---

## 1. 为什么先做这个有限任务

当前定量反演主线已经从：

```text
PXRD -> parameters -> forward reconstruction
```

转向：

```text
PXRD -> structure state + measurement state
     -> paired-physics supervision
```

但这里有一个必须先回答的风险：

> 既然模拟器本来就提供 `(a,c,zero shift,FWHM)` 的精确标签，那么简单的四参数监督回归是否已经足够？所谓 paired factorization 会不会只是换一种写法，而没有真正增加机制价值？

因此，下一步不做完整项目，只做一个最小可证伪实验。

---

## 2. 严格任务边界

本 Pilot 只使用现有 **Train split** 中的四方结构，不使用 Validation/Test，因此不绕过当前 prototype-overlap 的正式 split-policy 问题。

冻结边界：

- 只选 **32 个 conventional tetragonal training parents**；
- 复用当前 Week-1 已验证的 forward renderer 与参数范围；
- 不改变 P0/P1/P2 物理实现；
- 不打开 independent renderer holdout；
- 不做真实谱；
- 不做 refinement；
- 不加 forward reconstruction loss；
- 不做 backbone 搜索；
- 不做超参数大搜索。

该任务通过前，不扩大数据规模。

---

## 3. 数据：最小 2×2 物理干预块

对每个 parent，重复构造 16 个 factorial block。

每个 block 独立采样：

- 两个结构状态：`s1=(u1,v1)`、`s2=(u2,v2)`；
- 两个测量状态：`m1=(delta1,w1)`、`m2=(delta2,w2)`。

生成四张谱：

\[
x_{11}=F(s_1,m_1),\qquad x_{12}=F(s_1,m_2),
\]

\[
x_{21}=F(s_2,m_1),\qquad x_{22}=F(s_2,m_2).
\]

因此天然知道两类关系：

### 同结构、不同测量

\[
x_{11},x_{12}:\quad s\ \text{相同},\ m\ \text{不同}
\]

\[
x_{21},x_{22}:\quad s\ \text{相同},\ m\ \text{不同}
\]

### 同测量、不同结构

\[
x_{11},x_{21}:\quad m\ \text{相同},\ s\ \text{不同}
\]

\[
x_{12},x_{22}:\quad m\ \text{相同},\ s\ \text{不同}
\]

总规模：

```text
32 parents × 16 blocks × 4 spectra = 2,048 spectra
```

每个 parent 的 12 个 block 用于训练，4 个 block 作为 train-parent 内部的未见干预组合 sanity evaluation。这个 evaluation **不作为正式泛化结果**。

输入继续使用：

\[
[x_{obs},x_{ref},x_{obs}-x_{ref}].
\]

---

## 4. 只比较三种模型

三组必须使用同一 backbone、同一数据、同一优化器、同一训练步数与三个固定 seeds。

### A. Joint direct regression

```text
shared encoder -> 4D output
```

直接监督：

\[
(u,v,\delta,w).
\]

回答：普通四参数回归能做到什么程度？

### B. Two-head direct regression

```text
shared encoder
    -> structure head: (u,v)
    -> measurement head: (delta,w)
```

只有普通参数监督，没有 paired loss。

回答：仅仅拆成两个 head 是否已经足够？

### C. Two-head + paired physics supervision

架构与 B 完全相同，只额外加入关系监督。

同结构 / 不同测量时：

\[
L_{s-inv}=\|\hat s(x_{i1})-\hat s(x_{i2})\|^2.
\]

同测量 / 不同结构时：

\[
L_{m-inv}=\|\hat m(x_{1j})-\hat m(x_{2j})\|^2.
\]

总损失：

\[
L=L_{param}+\lambda_{pair}(L_{s-inv}+L_{m-inv}).
\]

所有输出先按 Train-only 参数统计标准化；Pilot 固定 `lambda_pair = 1`，不做搜索。

---

## 5. 这个 Pilot 真正看什么

不能只看四参数 MAE。主指标是 **cross-talk / leakage**。

### 5.1 Measurement -> Structure leakage

当只改变 measurement state 时，structure prediction 不应该乱动：

\[
E_{s\leftarrow m}
=
\mathbb{E}\|\hat s(s,m_1)-\hat s(s,m_2)\|.
\]

越小越好。

### 5.2 Structure -> Measurement leakage

当只改变 structure state 时，measurement prediction 不应该乱动：

\[
E_{m\leftarrow s}
=
\mathbb{E}\|\hat m(s_1,m)-\hat m(s_2,m)\|.
\]

越小越好。

### 5.3 Own-factor response fidelity

不能通过“所有输出都不动”作弊，因此还要检查：

- 改变结构时，structure head 是否正确跟随真实 `Δs`；
- 改变测量时，measurement head 是否正确跟随真实 `Δm`。

同时继续报告四个参数的直接 MAE。

---

## 6. 预注册式 GO / PARTIAL / NO-GO

以 B（two-head direct regression）为最关键基线。

### GO

C 相比 B：

- `E_{s<-m}` 和 `E_{m<-s}` **两项都平均降低至少 20%**；
- own-factor response error 不恶化超过 10%；
- 四参数直接 MAE 不恶化超过 5%；
- 三个 seeds 方向基本一致。

则认为：paired physics supervision 确实提供了普通参数监督之外的机制价值，可以继续进入正式 factorized inversion。

### PARTIAL

只改善一种 leakage，或改善 cross-talk 但明显牺牲参数精度。

则先分析是哪一对参数耦合最严重，不扩大实验。

### NO-GO

C 相比 B 没有稳定降低 cross-talk，或只能靠明显损失参数精度获得“解耦”。

则不继续把 paired factorization 当主创新，回到 reference-conditioned regression / basin-initialization 主线。

---

## 7. 本任务完成时只允许产生这些结果

完成标志不是“训练了一个大模型”，而是得到：

1. 一个固定的 2×2 factorial synthetic dataset manifest；
2. A/B/C 三组、三个 seeds 的结果；
3. 一张参数 MAE 表；
4. 一张 `structure leakage / measurement leakage` 对比图；
5. 一张 own-factor response 图或 2×2 intervention response matrix；
6. 一页结论：`GO / PARTIAL / NO-GO`。

除此之外，不继续做正式 Test、independent renderer、forward loss 或 refinement。

---

## 8. 这个有限任务真正回答的科学问题

最简单地说：

> **普通监督回归只是教模型“答案是多少”；paired physics supervision 是否进一步教会模型“这个变化到底属于材料，还是属于测量系统”？**

如果答案是 yes，后续主线才值得继续定义为：

`structure–measurement factorized quantitative inversion`。

如果答案是 no，就尽早停掉，而不是在完整项目做完以后才发现所谓“解耦”只是输出头命名不同。
