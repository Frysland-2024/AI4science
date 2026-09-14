# PXRD 定量反演 V0：一个月执行协议与 Pilot Gates

**日期：** 2026-08-31  
**状态：** 执行协议；用于收缩并落地 `NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md` 的一个月版本。  
**原则：** 不修改已经冻结的 `xrd_robustness` 分类项目；本协议只规定下一项目 V0 的执行优先级、Pilot Gates、Go/No-Go 与四周节奏。

---

## 1. 一个月版本的核心目标

研究问题固定为：

```text
观测 PXRD + 名义结构 / 参考谱
    -> 定量结构参数 + 测量参数
    -> 前向衍射一致性验证
    -> 作为局部 refinement 的初始化
```

第一版不是通用 Rietveld 替代器，而是一个 **known-phase, single-phase, tetragonal quantitative inversion** 问题。

### V0 冻结边界

只做：

- 单相；
- 已知候选结构 / nominal CIF；
- tetragonal；
- 固定元素、占位和分数坐标；
- 小范围、保持 tetragonal symmetry 的晶格变化；
- 结构参数：`a, c`；
- 测量参数：`zero shift, FWHM`；
- background / noise 只作为 nuisance。

暂时不做：

- 七晶系统一反演；
- unknown-phase indexing；
- 多相 / 相含量；
- 原子坐标、占位、热参数；
- crystallite size 与 microstrain 同时反演；
- Transformer / PAMPT backbone 探索；
- 完整自动 Rietveld；
- 没有独立实验验证时的广域 Sim-to-Real 定量结论。

---

## 2. 方法优先级：V0a 必做，V0c 核心升级，V0b 降为可选

### V0a — Reference-conditioned supervised regression【必须完成】

输入：

\[
X=[x_{obs},x_{ref},x_{obs}-x_{ref}]
\]

输出物理量：

\[
(a,c,\Delta 2\theta,\mathrm{FWHM})
\]

内部参数化优先测试：

\[
u=\frac{2\log a+\log c}{3},\qquad v=\log(c/a)
\]

\[
\delta=\Delta2\theta,\qquad w=\log(\mathrm{FWHM})
\]

但 `u,v` 不能预设为最终参数化；必须由 identifiability / numerical-stability Gate 决定是否保留。

### V0c — Forward-consistent inversion【核心升级】

预测参数：

\[
\hat\theta=(\hat\theta_s,\hat\theta_m)
\]

重新通过 diffraction forward model：

\[
\hat x_{clean}=F_{diff}(\hat\theta_s,\hat\theta_m)
\]

损失：

\[
L=L_{param}+\lambda_{forward}L_{forward}
\]

第一版只允许一种简单、可审计的 profile loss，例如：

- log-intensity Huber；或
- peak-region weighted Huber。

禁止同时引入 Soft-DTW、Wasserstein、复杂组合距离。

### V0b — Paired structural consistency【条件扩展】

只有 V0a 与 V0c 提前完成时再做。

对同一个变形后结构 `s*` 的两个测量视图，仅约束结构头：

\[
L_{pair}=\|\hat\theta_s(x_1)-\hat\theta_s(x_2)\|_1
\]

不能要求 measurement head 一致，因为两个 view 的 zero shift / FWHM 本来允许不同。

**一个月主线不得因 V0b 阻塞。**

---

## 3. Pilot Gates：正式训练前必须逐级通过

在 P0–P2 完成前，禁止启动大规模神经网络训练。

### P0 — Forward correctness Gate

随机抽取代表性 tetragonal structures，验证：

\[
\frac{1}{d_{hkl}^2}=\frac{h^2+k^2}{a^2}+\frac{l^2}{c^2}
\]

以及 Bragg：

\[
2d\sin\theta=\lambda
\]

必须检查：

- 改 `a` 后峰位变化符合 tetragonal metric；
- 改 `c` 后对应 reflections 的峰位变化符合预期；
- zero shift 是整体 `2θ` 平移；
- FWHM 改变峰宽，不偷偷移动 peak center；
- parent ID、参数标签和 rendered spectrum 一一对应；
- 没有缓存、插值或单位错位。

**任何一项失败 -> STOP，先修 forward model。**

### P1 — Identifiability Gate

对代表性结构计算：

\[
J=\left[
\frac{\partial x}{\partial u},
\frac{\partial x}{\partial v},
\frac{\partial x}{\partial\delta},
\frac{\partial x}{\partial w}
\right]
\]

检查：

- sensitivity-vector cosine similarity；
- singular values；
- condition number；
- `u` 与 zero shift 是否高度共线；
- 是否存在足够 reflections 区分 `a` 与 `c`；
- 当前角度范围 / 分辨率是否足够；
- 哪些 parent 天然不可辨识。

不设置任意 magic threshold；结合 P2 的实际 recovery 决定 Go/No-Go。

**Week-1 数值修订（2026-09-01）：** P1 的 Gate Jacobian 使用 CUDA float64
autograd。有限差分只作数值审计，固定扫描
`h_q = 0.005, 0.01, 0.02, 0.04`，原有 `0.1` 相对误差阈值不放宽。
由于 sampled max-normalization 会在相邻 bin 间切换，有限差分在每个 anchor
固定该 anchor 的局部 normalization branch；这不改变 anchor 处的 Jacobian，
只避免把离散 argmax 切换误报成可辨识性失败。

### P2 — Classical Recovery Gate【新增关键 Gate】

完全不使用 neural network。

生成：

\[
x=F(\theta_{true})
\]

使用同一套 bounded local least-squares：

\[
\hat\theta=\arg\min_\theta D(F(\theta),x)
\]

#### P2-R — Clean Recoverability Gate

无随机 background / noise。

允许预注册的 deterministic multistart。正式方案使用一份冻结的 4D
scrambled-Sobol 嵌套设计，GPU 分块计算初始 residual，选择固定数量的候选
进入完全相同的 local least-squares；P2-L 的 nominal 解无条件复用并进入最终候选池。
最终解只按 finite final cost 与固定 start ID 选择，严禁查看 truth/NAE 选解。

要求：对绝大多数冻结样本，P2-R 能恢复受控真值。P2-R 才是项目数值
recoverability Gate。

#### P2-L — Nominal Local-capture Baseline

保留原始 `θ0 = θ_nominal` 单起点 local least-squares，但它只衡量 basin / initialization
sensitivity，不再作为四参数任务的 Go/No-Go Gate。后续 ML initializer 必须与它使用
同一个 local refinement，才能形成公平比较。

#### P2-N — Nuisance diagnostic

加入未显式建模的 background / noise，记录完整四参数 nominal local capture 的下降。
该结果不进入 clean recoverability Gate，也不能单独用于删除 FWHM 或收缩参数空间。

若 clean 条件下 P2-R 都无法稳定恢复参数：

> 不允许归因于神经网络；优先缩减参数维度或修改任务定义。

### P3 — Tiny-overfit ML Gate

固定约 32–64 个样本，让 ResNet 明显过拟合。

检查：

- output standardization；
- parameter decoding；
- model heads；
- optimizer；
- three-channel input；
- loss scaling；
- labels 与 spectra 对应关系。

若固定小样本都无法过拟合：

> 禁止正式训练。

### P4 — Differentiable-forward Gate

在 `L_forward` 接入神经网络前单独验证其梯度。

生成：

\[
x^*=F(\theta^*)
\]

从错误参数 `θ0` 出发，仅优化：

\[
\theta_{t+1}=\theta_t-\eta\nabla_\theta D(F(\theta),x^*)
\]

确认在 clean / controlled setting 下：

\[
\theta_t\rightarrow\theta^*
\]

若 profile loss 的梯度不能把参数拉向真值：

> 不允许把该 loss 接入 neural-network training。

---

## 4. 参数阶梯 Pilot

禁止第一天直接四参数 + nuisance 全开。

| 阶段 | 反演参数 | 目的 |
|---|---|---|
| S1 | `u, v` | 先验证晶格参数本身能否恢复 |
| S2 | `u, v, delta` | 检查整体晶格尺度与 zero shift 是否可分 |
| S3 | `u, v, delta, w` | 再加入 FWHM |
| S4 | 四参数 + background/noise nuisance | 进入鲁棒反演 |

每一级必须记录：

- Jacobian / sensitivity；
- classical recovery error；
- parameter coupling；
- tiny-overfit behavior（进入 ML 后）。

特别关注：

\[
u\leftrightarrow\delta
\]

如果 S1 成功但 S2 显著恶化，优先研究结构尺度与 zero shift 的 identifiability，不换 backbone 救火。

---

## 5. 四周执行计划

### Week 1 — Physics & Identifiability

**原则：不做正式 ML 跑分。**

完成：

1. tetragonal parent audit；
2. parent-level Train / Validation / Test；
3. prototype / near-duplicate audit；
4. P0 Forward correctness；
5. S1–S4 参数阶梯；
6. P1 Jacobian / identifiability；
7. P2 classical recovery；
8. 冻结 parameter ranges；
9. 冻结数据 split；
10. 提前构造并冻结 independent-renderer Test。

**Independent-renderer Test 在 Week 4 前不得用于调参数、改 loss、改 renderer。**

该 renderer 必须在 Week 1 构造、记录源码哈希并冻结候选 parent/seeds；冻结时不得
生成候选 profile、计算 metric 或打开 outcome。

#### Week-1 Go

至少核心参数组合在 clean / controlled setting 下具有明确可辨识性，且 P2-R
deterministic multistart inversion 能恢复真值。P2-L 失败只说明 nominal capture basin
脆弱，不能直接解释为任务不可恢复。

正式数值 Gate 精确使用 24 个冻结 train parent × 每 parent 4 trials；P1 eligibility
保留为分层标签，不得在观察 Gate 结果后筛掉或替补 P2 parent。prototype / near-duplicate
审计与 independent-renderer seal 同时记录，但不得用 independent outcome 调 Week 1–3。

否则缩减参数空间，不进入正式 ML。

---

### Week 2 — Direct Inversion

公共 backbone 固定：

```text
1D ResNet-18-GN
```

不重新做架构搜索。

执行顺序：

1. P3 tiny overfit；
2. Nominal-parameter baseline；
3. Traditional local least-squares baseline；
4. `x_obs -> parameters`；
5. `[x_obs, x_ref, x_obs-x_ref] -> parameters`。

Week 2 结束必须形成一个可独立成立的 baseline：

```text
Reference-conditioned direct inversion
```

即使后续 forward physics 失败，这一阶段也必须能够单独汇报。

---

### Week 3 — Forward Physics

1. 先完成 P4 differentiable-forward Gate；
2. 比较：

\[
L_{param}
\]

vs.

\[
L_{param}+\lambda_{forward}L_{forward}
\]

3. 先做 gradient-scale audit；
4. `lambda_forward` 最多只测试 2–3 个预先定义候选；
5. 禁止无限调参；
6. 同时检查 parameter error 和 profile error。

特别警惕：

```text
profile residual 下降
但 parameter error 上升
```

该情况视为退化，不视为 physics-guided 成功。

如果 V0a + V0c 提前完成，再考虑 V0b paired structural consistency。

---

### Week 4 — Frozen Evaluation & Refinement Utility

参数、模型和方法完全冻结后：

1. 3–5 independent seeds；
2. unseen-parent Test；
3. 打开 frozen independent-renderer Test；
4. parameter MAE / relative error；
5. `c/a` error；
6. cell-volume error；
7. zero-shift / FWHM error；
8. profile reconstruction；
9. high-error tail；
10. Nominal initialization -> same local refinement；
11. ML initialization -> same local refinement。

最终比较：

- convergence iterations；
- runtime；
- failure rate；
- final residual；
- wrong-local-minimum rate；
- fixed-budget success rate。

应用结论应回答：

> ML 是否提供了比 nominal initialization 更好的 refinement initializer？

而不是声称 ML 取代 refinement。

---

## 6. 一个月主实验矩阵

核心只保留四组：

| 方法 | 角色 |
|---|---|
| Nominal parameters | zero-learning lower baseline |
| Local least-squares | traditional physics baseline |
| Reference-conditioned regression | ML baseline |
| Regression + forward consistency | proposed method |

附加消融：

- `x_obs only`；
- paired structural consistency。

附加消融不得阻塞主实验。

---

## 7. Go / No-Go 规则

### Go

出现以下任一稳定、可复现结果即可继续：

- reference-conditioned regression 明显优于 nominal；
- ML 在 unseen-parent 上稳定恢复参数；
- forward consistency 改善 parameter OOD；
- forward consistency 改善 independent-renderer robustness；
- ML initialization 降低 refinement iterations / failure rate；
- 发现稳定、可解释、可重复的 identifiability failure mechanism。

### No-Go / 收缩

若发生：

- clean classical recovery 都失败；
- `u, delta` 等参数严重不可辨识；
- forward loss 持续出现 `profile better / parameter worse`；
- 增益只存在于同一训练 renderer；
- ML initialization 不优于 nominal / local LS；

则停止扩大复杂度。

优先退回：

```text
reference-conditioned regression
    -> refinement initialization
```

不跳向七晶系、多相或更复杂模型。

---

## 8. 执行原则

一次只回答一个问题。

禁止同时：

```text
换 backbone
+ 改参数化
+ 改 renderer
+ 加 paired loss
+ 加 forward loss
```

完整顺序固定为：

```text
Forward 是否正确
    -> 参数是否可辨识
    -> 传统方法能否反演
    -> ML 能否学习
    -> forward gradient 是否有效
    -> physics-guided ML 是否更好
    -> 是否改善 refinement initialization
```

这份协议是 V0 的一个月执行优先级；更完整的长期扩展仍以 `NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md` 为总规划。
