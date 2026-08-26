# 下一项目规划：已知相参考条件下的 PXRD 定量反演

**规划日期：** 2026-08-27  
**状态：** 已形成正式方案，尚未启动训练  
**与当前项目的关系：** 本计划独立于已经冻结的 `xrd_robustness` 七晶系分类项目，不修改其数据、模型、结果或论文结论。

## 1. 项目定位

当前项目回答的是：

```text
同一母体结构的不同测量视图
    -> 稳定的七晶系分类
```

下一项目进一步推进为：

```text
观测 PXRD + 名义结构 / 参考谱
    -> 定量结构参数 + 测量参数
    -> 前向衍射验证与局部精修
```

它仍属于 [`A-METRO`](master_route_framework.md) 的“测量结果 -> 物理信息推断”，同时开始触及以物理模型、参数识别和模拟器校准为中心的 `B-DEVICE` 式方法结构。

核心目标不是让神经网络取代完整 Rietveld refinement，而是研究：

> 在已知候选相或名义结构的条件下，机器学习能否从受测量扰动影响的 PXRD 中快速估计可解释的物理参数，并为传统局部精修提供更好的初始化。

## 2. 从早期方案到当前方案

本计划整合了此前两类本地构想：

1. 在晶系分类的 `CE + JS` 基础上加入 lattice auxiliary / Bragg physics；
2. 将 PXRD 从离散分类推进到晶格参数等连续量的定量反演。

需要保留的关键修正是：

- 七晶系不存在固定的绝对“特征峰位置”；
- 晶系约束的是晶格 metric 与整组峰位之间的几何关系；
- 因此，第一版不使用“某晶系必须在某角度出现峰”的硬规则；
- 项目从分类器上的附加 loss，收敛为一个独立的、参考条件下的定量反演任务。

## 3. 第一版 V0 的严格边界

### 3.1 任务范围

第一版只做：

- 单相；
- 已知候选结构 / 名义 CIF；
- 四方晶系；
- 固定元素、占位与分数坐标；
- 小范围、保持四方对称性的晶格变化；
- 受控零点偏移与峰展宽；
- 背景和噪声作为 nuisance，而不是第一版回归目标。

暂时不做：

- 任意未知物相识别；
- 七晶系统一反演；
- 多相及相含量；
- 原子坐标、占位和热参数；
- 晶粒尺寸与微应变同时反演；
- 完整自动 Rietveld refinement；
- 在没有独立实验验证时宣称真实域定量精修成功。

### 3.2 输入

对每个样本构造三通道输入：

```text
1. x_obs：发生晶格变化并叠加测量条件后的观测谱
2. x_ref：名义 CIF 生成的参考谱
3. x_obs - x_ref：观测谱与参考谱的差谱
```

形式为：

\[
X=[x_{\mathrm{obs}},x_{\mathrm{ref}},x_{\mathrm{obs}}-x_{\mathrm{ref}}].
\]

这比只输入 `x_obs` 更符合实际 refinement 场景：实验人员通常已经拥有候选相或名义结构，需要估计它相对参考状态发生了什么变化。

### 3.3 输出

物理解释层面的输出为：

\[
(a,c,\Delta 2\theta,\mathrm{FWHM}).
\]

网络内部优先使用更稳定的坐标：

\[
u=\frac{2\log a+\log c}{3}=\frac{1}{3}\log(a^2c),
\]

\[
v=\log(c/a),
\]

\[
\delta=\Delta 2\theta,
\qquad
w=\log(\mathrm{FWHM}).
\]

其中：

- `u` 表示整体晶胞尺度；
- `v` 表示四方畸变；
- `delta` 表示仪器零点偏移；
- `w` 保证峰宽预测为正。

可由：

\[
\log a=u-\frac{v}{3},
\qquad
\log c=u+\frac{2v}{3}
\]

恢复 `a` 与 `c`。

最终是否保留这一参数化，要由第一个可辨识性与数值稳定性 Gate 决定；不得只凭形式漂亮直接冻结。

## 4. 正式研究问题

### 主问题

> 在已知相的 PXRD 定量反演中，参考条件回归、同源双视图结构一致性和前向衍射一致性，能否比普通直接回归获得更准确、更稳健的参数估计？

### 应用问题

> 机器学习预测是否能比名义参数或普通初值更有效地初始化局部 least-squares / refinement，从而减少迭代次数、失败率和运行时间？

### 机制问题

> 当同一个变形后结构在不同测量条件下被观测时，模型能否保持结构参数预测一致，同时允许零点偏移与峰宽预测随视图变化？

## 5. 数据生成设计

### 5.1 母结构与切分

- 优先从现有 14,060 个母结构及其严格结构级 split 中审计四方子集；
- 若四方数量或参数分布不足，再建立独立数据库，但仍按母结构严格切分；
- 同一名义 CIF、其所有晶格变形及所有测量视图只能属于 Train、Validation 或 Test 中的一个集合；
- 首先检查近重复结构、相同 prototype 和参数分布，不能只依赖随机切分。

### 5.2 同源双视图

对一个名义结构 `s0`：

1. 采样一组保持四方对称性的结构参数 `theta_s=(u,v)`；
2. 由 `s0` 得到变形后结构 `s*`；
3. 独立采样两组测量参数 `theta_m1` 与 `theta_m2`；
4. 生成：

\[
x_1=F(s^*,\theta_{m1}),
\qquad
x_2=F(s^*,\theta_{m2}).
\]

因此：

- 两个视图的结构参数标签相同；
- 两个视图的零点偏移和峰宽标签可以不同；
- 这比分类项目中的“预测分布一致”提供了更细粒度的监督结构。

### 5.3 latent clean profile

每次生成时同时保存或可确定性重建：

- 无背景、无随机噪声的 clean profile；
- 原始参数标签；
- 名义结构身份；
- 测量扰动 provenance。

前向谱损失优先与 latent clean profile 比较，避免强迫少量结构参数解释随机噪声。

### 5.4 防止 inverse crime

至少设置一个独立测试域：

- 使用不同峰形函数；
- 或不同 renderer / refinement engine；
- 或不同角度网格与仪器函数；
- 或使用公开实验谱作为最后 case study。

如果训练与测试完全使用同一个模拟器和同一参数分布，只能证明 simulator inversion，不能证明真实测量反演。

## 6. 模型设计

### 6.1 公共骨干

第一版复用当前已经验证可学习的 ResNet-18-GN 思路：

```text
三通道 PXRD
    -> 共享 1D ResNet 编码器
    -> 结构参数头：u, v
    -> 测量参数头：delta_2theta, log_fwhm
```

不重新开启 PAMPT / Transformer 架构探索，避免把“任务是否成立”和“复杂 backbone 是否可优化”混在一起。

### 6.2 分阶段实现

#### V0a：监督回归与参考条件

先证明任务可学习：

- `x_obs -> parameters`；
- `[x_obs,x_ref,x_obs-x_ref] -> parameters`；
- 名义参数无修正基线；
- 传统局部最小二乘基线。

#### V0b：同源结构一致性

对同一 `s*` 的两个测量视图，只约束结构头：

\[
L_{\mathrm{pair}}
=
\|\hat\theta_s(x_1)-\hat\theta_s(x_2)\|_1.
\]

不能约束测量头一致，因为两条谱的零点偏移和峰宽本来就不同。

#### V0c：前向物理一致性

在验证可微或近似可微 renderer 的正确性后，将预测参数重新生成谱：

\[
\hat x_{\mathrm{clean}}
=
F_{\mathrm{diff}}(\hat\theta_s,\hat\theta_m).
\]

再计算：

\[
L_{\mathrm{forward}}
=
D(\hat x_{\mathrm{clean}},x_{\mathrm{clean}}).
\]

第一版优先使用简单、可审计的 log-intensity Huber 或峰区加权 profile loss，不同时引入 Soft-DTW、Wasserstein 和多种复杂距离。

## 7. 损失函数

所有参数先按训练集统计或物理范围标准化。

### 7.1 参数监督

\[
L_{\mathrm{param}}
=
\mathrm{Huber}(\hat\theta_s,\theta_s)
+
\mathrm{Huber}(\hat\theta_m,\theta_m).
\]

### 7.2 完整候选目标

\[
L
=
L_{\mathrm{param}}
+
\lambda_{\mathrm{pair}}L_{\mathrm{pair}}
+
\lambda_{\mathrm{forward}}L_{\mathrm{forward}}.
\]

执行顺序必须是：

1. 先验证 `L_param` 基线；
2. 再加入 `L_pair`；
3. 最后加入 `L_forward`；
4. 每次只新增一个机制，保留完全匹配的对照。

## 8. 实验矩阵

| 编号 | 方法 | 回答的问题 |
|---|---|---|
| A | 名义参数 / 零修正 | 不做学习时的最低基线 |
| B | 传统局部 least-squares，从名义参数开始 | 传统优化自身能做到什么 |
| C | 仅观测谱的直接监督回归 | 普通端到端回归基线 |
| D | 参考条件监督回归 | 参考谱是否降低反演难度 |
| E | D + 同源结构一致性 | 同源监督是否提高跨测量条件稳定性 |
| F | E + 前向物理一致性 | 物理重建约束是否提高 OOD 参数可靠性 |
| G | F 预测初始化 + 局部精修 | 是否真正加速并稳定 refinement |

主比较优先为：

```text
D vs E vs F
```

最终应用比较优先为：

```text
名义初始化 vs ML 初始化后的相同局部精修
```

## 9. 评测指标

### 9.1 参数准确度

- `a`、`c` 的 MAE 与相对误差；
- `c/a` 误差；
- 晶胞体积相对误差；
- `delta_2theta` MAE；
- FWHM MAE；
- 不同参数的 worst-group / high-error tail。

### 9.2 光谱一致性

- 峰位平均误差；
- latent clean profile 重建误差；
- `R_p` / `R_wp`-like 指标；
- 未解释峰或明显 profile mismatch 数量。

### 9.3 精修初始化价值

- 局部优化中位迭代数；
- 收敛时间；
- 收敛失败率；
- 最终残差；
- 错误局部极小值比例；
- 相同计算预算下的成功率。

### 9.4 OOD 面板

至少分别测试：

1. 未见母结构；
2. 晶格变化超出训练范围；
3. 零点偏移超出训练范围；
4. 峰宽超出训练范围；
5. 未建模背景或噪声；
6. 独立 renderer / 峰形模型；
7. 以后才加入的实验谱。

## 10. 启动前的可辨识性 Gate

训练模型之前，对代表性四方结构计算参数灵敏度：

\[
J=
\left[
\frac{\partial x}{\partial u},
\frac{\partial x}{\partial v},
\frac{\partial x}{\partial \Delta2\theta},
\frac{\partial x}{\partial \mathrm{FWHM}}
\right].
\]

检查：

- 灵敏度向量是否高度共线；
- Jacobian 条件数是否过大；
- 是否同时存在对 `a` 与 `c` 有区分力的反射；
- 整体晶格变化与零点偏移是否严重混淆；
- 当前角度范围和分辨率是否足够；
- 哪些结构天然不可辨识。

不可辨识样本不能被简单视为“模型训练失败”。应当：

- 标记为高不确定性样本；
- 作为困难测试集；
- 或在 V0 中排除，并明确记录筛选标准。

## 11. 四周执行计划

### 第 1 周：数据与物理 Gate

- 审计四方母结构数量、参数分布和 prototype；
- 冻结 V0 输入输出；
- 实现保持四方对称性的晶格变形；
- 完成单结构参数扫描；
- 完成 Jacobian / 可辨识性分析；
- 验证参考谱、变形谱与标签完全一致。

**Go 条件：** 四个参数对谱图产生可检测且不过度共线的响应。

### 第 2 周：基础回归

- 建立三通道数据；
- 先完成小 batch 过拟合测试；
- 跑名义参数、直接回归、参考条件回归和 least-squares 基线；
- 建立 unseen-parent simulated test。

**Go 条件：** 参考条件模型显著优于名义参数 / 零修正基线，并能恢复受控参数变化。

### 第 3 周：结构化监督与前向一致性

- 加入 `L_pair`；
- 验证结构参数跨视图更稳定，而测量参数仍能区分；
- 验证 differentiable renderer；
- 加入 `L_forward`；
- 只做小规模、预先限定的权重网格。

**Go 条件：** 至少在 OOD 参数误差、光谱重建或稳定性中有一项明确改善，且不出现“谱更像但参数更错”的退化。

### 第 4 周：完整证据与应用评测

- 完成多 seed 主比较；
- 完成独立 renderer 测试；
- 完成 ML 初始化 + 局部精修；
- 生成参数散点图、误差分布、重建谱和收敛曲线；
- 写方法、结果和失败分析。

## 12. Go / No-Go 判定

### Go

满足任一项即可继续扩展：

- 参考条件模型明显优于直接回归；
- paired consistency 降低结构参数跨视图方差；
- forward loss 改善 OOD 参数误差或物理重建；
- ML 初始化减少 refinement 迭代、时间或失败；
- 发现一个稳定、可解释且可复现的不可辨识机制。

### No-Go / 收缩

若发生以下情况，则停止扩张：

- 受控四方单相任务都无法稳定恢复参数；
- 结构参数与测量参数在现有输入范围内不可辨识；
- forward loss 只改善 profile residual，却持续恶化真实参数；
- 增益只能通过同一个训练模拟器与测试模拟器获得；
- 完整方案无法优于简单 least-squares 初始化。

No-Go 时优先退回：

```text
参考条件监督回归
    -> paired structural consistency
    -> 作为 refinement initializer
```

不直接跳向更复杂的多相或七晶系统一模型。

## 13. 后续扩展顺序

```text
V0：四方、已知相、单相
    -> 晶胞尺度 + 四方畸变 + zero shift + FWHM
V1：不确定性与独立实验谱
V2：晶粒尺寸或微应变，一次只加入一个
V3：多个已知结构模板 / 多晶系 invariant representation
V4：相含量与多相
V5：GSAS-II / FullProf / RAPID 自动初始化接口
```

## 14. 结论边界

V0 成功后可以主张：

> 在已知相、单相和受控模拟条件下，参考条件机器学习能够估计部分晶格与测量参数，并可能改善局部精修初始化。

没有独立实验与传统软件验证前，不能主张：

- 自动完成通用 Rietveld refinement；
- 从未知 PXRD 唯一恢复完整结构；
- 已经解决广域 Sim-to-Real 定量反演；
- 参数重建误差等同于真实物理测量误差。

## 15. 代码组织建议

```text
xrd_inversion/
├── README.md
├── configs/
├── reports/
├── scripts/
└── src/xrd_inversion/
    ├── lattice_parameterization.py
    ├── tetragonal_forward.py
    ├── paired_dataset.py
    ├── model.py
    ├── losses.py
    ├── identifiability.py
    └── local_refinement.py
```

新目录只在第 1 周 Gate 通过后创建。当前阶段先保留为文档规划，不提前制造半成品代码。

## 16. 参考资源

详细文献、代码与数据清单见：

- [`XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md`](XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md)

当前优先顺序为：

1. Chitturi 2021：晶格参数回归与测量非理想；
2. DONUT 2025：前向物理监督与不确定性；
3. RAPID 2026：ML 参数预测作为 refinement 初始化；
4. PQ-Net 2021：全谱定量回归；
5. AIdex 2025：跨晶系 indexing 与峰位不确定性；
6. Hofgard 2026：多晶系 lattice invariant representation；
7. Gómez-Peralta 2023：晶格参数 CNN 与实验验证。
