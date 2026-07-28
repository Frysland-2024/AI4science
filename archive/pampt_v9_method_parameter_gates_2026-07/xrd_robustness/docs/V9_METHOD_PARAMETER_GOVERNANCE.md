# V9-T 方法参数合法性与调参 Gate

## 当前结论

V9-T 的方法公式、方向、reduction、梯度流和调度语义已经通过审计。128-step 短轨迹继续只作为 initialization/chance-state 证据；随后完成的 learned-state 审计证明主干和 residual probe 已进入可解释状态。用户据此批准并消耗唯一一次 pre-Validation 网格修订，最终冻结：

- JS：`[0.3, 3.0, 30.0]`；
- Residual：`[0.2, 2.0, 20.0]`。

六个候选已经在重新从 epoch 0 建立的 Train-only learned state 上逐一做真实 autograd 测量，全部覆盖预注册影响带并通过数值 Gate。候选范围现已冻结，但**Validation-only 7-run 仍然禁止执行**，直到用户另行明确授权。

这不是方法实现失败。准确状态是：

- 工程/公式 Gate：通过；
- Train-only learned-state 与六候选数值审计：通过；
- 分类学习信号：已证明；
- residual probe 类别预测能力：已在互斥 Train 子集证明；
- 当前候选范围 Gate：通过并冻结；
- Validation、simulated Test、real test：均未使用；
- 正式调参进度：`0/7`。

## 合法性证据链

方法权重不是物理常数，也不要求外部论文给出跨任务唯一数值。V9-T 冻结以下证据链：

1. 方法原理解释参数为什么存在；
2. 损失定义与 batch-mean reduction 给出数学尺度；
3. 只使用 Train 的 loss/gradient 审计，并先确认分类主干与 residual probe 已进入可解释的学习阶段；
4. 候选区间冻结后，仅用 Simulation Validation 选择最终值；
5. 三点敏感性、多 seed 和配对比较检验是否依赖幸运点；
6. simulated Test 和 real test 不参与任何参数决策。

## 胡皓天论文能支持什么、不能支持什么

已按原文重新核对 Haotian Hu 等人的 SD3Net 论文（Knowledge-Based Systems 348 (2026) 116429，DOI `10.1016/j.knosys.2026.116429`）：

- 式 (16) 是 `L_cls = lambda_1 L_sd + lambda_2 L_sim`；
- 式 (17) 是 `L_total = L_cls + lambda_3 L_decorr`；
- Table 5 对 Pavia、HyRANK、WHU 都列出 `lambda_3=1`，并分别给出 `(lambda_1, lambda_2)=(0.1,1.0)`、`(0.1,0.1)`、`(0.1,0.3)`；
- 正文说明以 `lambda_3` 为尺度锚点，在 `[0.1,1]` 内联合检查 `lambda_1` 与 `lambda_2`，并用 3D surface 展示敏感性；
- Fig. 12 又单独把一个记作 `lambda` 的 regularization parameter 从 `1e-2` 扫到 `1e-6`，报告约 `1e-4` 最优，但没有明确说明它如何对应式 (17) 和 Table 5 中的 `lambda_3=1`。

因此这篇论文只能为 V9-T 提供三类方法学先例：残差熵/去相关目标确实存在、损失权重应解释为相对贡献、应报告敏感性和模块消融。它**不能**为本项目的 `lambda_res` 提供可直接搬用的数值范围；尤其禁止把 Fig. 12 的 `1e-4` 写成“胡皓天论文的残差损失权重”，也禁止把它倒灌进 V9-T 配置。

本项目的分类损失系数固定为 1，Dynamic/Paired ERM 已充当 `lambda=0` 消融锚点，因此 7-run 仍为 1 个基线加 3 个 JS 和 3 个 Residual 候选，不额外复制两个零权重 run。候选范围的唯一修订已经由人工依据 V9-T Train-only 数值证据完成并冻结；最终值仍只由后续明确授权的 Simulation Validation 协议决定。

## 语义审计

权威机器可读报告是 `reports/v9_method_semantics_audit.json`。

- JS：`lambda_js=0` 与 Dynamic/Paired ERM 更新一致；交换视图不变；相同预测为零；非负；batch duplication 不改变 batch mean；自然对数 JS 不超过 `ln(2)`。
- Residual：`lambda_res=0` 与 Dynamic ERM backbone 更新一致；归一化无 NaN；`KL(q || Uniform)=ln(7)-H(q)`，因此最小化 KL 的确最大化熵；辅助梯度进入 backbone，probe 梯度进入 residual head；2-epoch warm-up 与 3-epoch ramp 精确生效。
- 固定结构：residual head 是单层线性头，正式 B3 参数量为 903；不进行结果驱动搜索。

### 两种 residual 语义不得混用

当前 V9-T 生产方法使用：

```text
abs(L2Norm(z1) - L2Norm(z2))
```

因此交换两个视图时 residual **不变**，类别去相关目标也不变。仓库中为后续工作保留的 signed measurement residual 才满足交换后符号反转。审计分别验证二者，不能为了满足一句测试描述而悄悄改变 V9-T 的冻结公式。

## Train-only 损失—梯度尺度审计

权威机器可读报告是 `reports/v9_loss_gradient_scale_audit.json`。审计设置为：

- 正式 PAMPT-B3，float32，CUDA；
- 七个 crystal systems 各 2 个 Train 结构，共 14 个；
- 128 个 classification-only optimizer steps；
- 前 64 step 为 burn-in，后 64 step 统计；
- backbone 轨迹不使用候选方法、不使用 Validation 指标；
- residual probe 只用 detached features 更新，不改变 backbone；
- 没有候选专属训练，没有模型选择。

新版审计使用 128 个不重复的固定配对 batch，并把 PAMPT 的监督分类头排除在“backbone 梯度”之外。JS 使用 `batchmean` KL（类别维求和、batch 维求均值），Residual 使用逐样本类别维求和再做一次 batch mean；二者都没有重复除以类别数。

审计轨迹三等分的均值如下；这里的 early/middle/late 只表示 128-step 诊断轨迹的三段，不是正式 50-epoch 训练的早中晚：

| 指标 | early (0–41) | middle (42–84) | late (85–127) |
|---|---:|---:|---:|
| `L_cls` | 1.9637 | 1.9507 | 1.9499 |
| `L_JS` / prediction JS | 3.454e-7 | 2.514e-7 | 2.968e-7 |
| `L_res` | 2.604e-4 | 2.562e-4 | 2.527e-4 |
| `||grad L_cls||` | 1.770 | 1.525 | 1.291 |
| `||grad L_JS||` | 7.837e-6 | 4.297e-6 | 4.675e-6 |
| `||grad L_res||` | 8.052e-5 | 5.737e-5 | 5.431e-5 |
| normalized feature residual norm | 7.745e-3 | 6.440e-3 | 6.344e-3 |
| residual-head entropy | 1.945650 | 1.945654 | 1.945658 |
| classification accuracy | 12.59% | 9.97% | 11.96% |
| residual probe pre-update accuracy | 14.29% | 13.95% | 14.62% |

七分类随机准确率为 `14.29%`，均匀预测的交叉熵/最大熵为 `ln(7)=1.94591`。late 段分类准确率仅 `11.96%`，`L_cls=1.9499`；probe 准确率仅 `14.62%`，交叉熵 `1.94613`，residual-head entropy 几乎等于最大熵。两个视图的 top-1 预测 late 段却有 `99.34%` 一致。这说明 JS 很小主要因为两个视图在尚未学会分类时已经输出几乎相同的预测；Residual 很小则与 probe 尚未学会从 residual 预测类别同时发生。此时“均匀 residual 预测”不能被解释为去相关成功。

当前候选在后 64 step 的中位辅助/分类 backbone 梯度比为：

| 参数 | 候选值 | 中位梯度比 |
|---|---:|---:|
| `lambda_js` | 0.1 | 3.480e-7 |
| `lambda_js` | 0.3 | 1.044e-6 |
| `lambda_js` | 1.0 | 3.480e-6 |
| `lambda_res` | 0.01 | 3.913e-7 |
| `lambda_res` | 0.1 | 3.913e-6 |
| `lambda_res` | 1.0 | 3.913e-5 |

按预注册的描述性影响带，`R < 0.01` 为几乎不起作用，`0.01 <= R < 0.1` 为弱，`0.1 <= R < 1` 为实质但不主导，`R >= 1` 为主导。当前六个候选全部落在 `R < 0.01`，所以不能声称它们覆盖了“弱—中—强”。

对这些比值取倒数会得到诊断性的梯度补偿倍数：

- JS：约 `2.874e5`；
- Residual：约 `2.556e4`。

它们不是理论权重、不是候选网格提案、不是 Validation 选择结果，也没有写入正式配置。下一次合法动作是在 Train-only 范围内按“学习里程碑”复测：先确认分类主干已经明显优于随机；对 Residual 还必须确认 pre-update probe 能从 residual 中预测类别。只有这两项成立后，辅助梯度的大小才具有可解释性。在此之前禁止整体平移网格。

## Learned-state 与六候选冻结 Gate

`reports/v9_learned_state_scale_audit.json` 先用完整 9,842 个 Train 结构、固定 seed、五 epoch Dynamic/Paired ERM 证明主干已学习，并在互斥 Train 子集上证明 detached residual probe 高于 chance。它只提供人工作出范围决定所需的证据，不自动改网格。

用户随后明确批准唯一一次修订。机器可读阈值写入 `configs/v9_method_parameter_governance.json`：

- negligible：`R < 0.01`；
- weak：`0.01 <= R < 0.1`；
- material non-dominant：`0.1 <= R < 1`；
- dominant：`R >= 1`。

权威冻结 Gate 是 `reports/v9_candidate_grid_gate.json`，SHA-256 为 `E59EE2A56906757C82238CB47D520B1D74D690455EA907540AFFF59EA2E8A947`。它没有恢复内存 checkpoint，而是从相同固定 seed、epoch 0 重建五 epoch Train-only PAMPT-B3；六个候选分别对加权辅助目标与合并目标执行 autograd，不是只把 `lambda=1` 比率线性相乘。结果为：

| 方法 | λ | 实测中位辅助/分类 backbone 梯度比 | 影响带 |
|---|---:|---:|---|
| JS | 0.3 | 0.02283 | weak |
| JS | 3.0 | 0.22842 | material non-dominant |
| JS | 30.0 | 2.28533 | dominant |
| Residual | 0.2 | 0.02581 | weak |
| Residual | 2.0 | 0.25854 | material non-dominant |
| Residual | 20.0 | 2.58715 | dominant |

所有候选均满足有限性、分类梯度存在、加权辅助梯度存在、影响带匹配、总梯度单 batch 低于 50 倍失控保护、中位合并方向仍为分类下降方向，以及 BF16 多次 autograd 的梯度和一致性容差。审计工具在冻结前透明修正了两项与候选无关的内部判据：`1e-4` 的 float32 风格梯度恒等式容差改为适配 BF16 独立反向遍历的 5%；删除与 dominant 开区间冲突的 p90 `<=10` 上限，但保留 50 倍单 batch 保护。网格、数据和影响带未因这些工具修正而改变。

## 参数来源与冻结策略

| 参数 | 定位 | 当前依据 | 当前证据 | 正式选择方式 |
|---|---|---|---|---|
| `lambda_js` | 核心 | JS 一致性原理；Train-only learned-state 比率；唯一一次人工 decade-grid 修订 | `[0.3,3,30]` 实测覆盖 weak/material/dominant，已冻结 | 获得单独授权后只用 Validation 选择最终值 |
| `lambda_res` | 核心 | residual entropy/decorrelation 原理；Hu et al. 仅支持机制与敏感性流程；Train-only probe 与梯度证据 | `[0.2,2,20]` 实测覆盖 weak/material/dominant，已冻结 | 获得单独授权后只用 Validation 选择最终值 |
| residual head depth=1 | 次要 | 最小容量实现 | 单层/参数量/梯度流测试通过 | 固定，不搜索 |
| warm-up=2 | 次要 | 避免初期辅助目标干扰 | 调度单元测试通过 | 固定，不搜索 |
| ramp=3 | 次要 | 平滑开启正则 | 调度单元测试通过 | 固定，不搜索 |

## 启动 7-run 前必须同时满足

- [x] `lambda=0` 严格退化为 Dynamic/Paired ERM；
- [x] 公式、方向、reduction、数值稳定性与梯度流通过；
- [x] Train-only 分类主干达到非随机学习里程碑；
- [x] residual probe 在施加混淆解释前证明具有类别预测能力；
- [x] 梯度补偿倍数的解释 Gate 通过；
- [x] 冻结候选区间覆盖不同辅助梯度强度；
- [x] 搜索范围依据与调整政策已写入仓库；
- [x] residual head、warm-up、ramp 已明确冻结；
- [x] 选择指标、seed、并列规则保持不变；
- [x] simulated Test 与 real test 完全未接触。

以上科学与工程 Gate 已通过，但它们不等于运行授权。主合同中的两个 tuning execution switches 继续保持 `false`，7-run 仍为 `0/7`。候选范围允许的唯一一次修订已经消耗，不得再改；只有用户另行明确授权后，才能按冻结协议启动 Validation-only 7-run。
