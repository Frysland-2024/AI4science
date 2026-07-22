# V9-T 方法参数合法性与调参 Gate

## 当前结论

V9-T 的方法公式、方向、reduction、梯度流和调度语义已经通过审计；但当前两组三点候选范围尚未通过数值尺度 Gate，因此 **Validation-only 7-run 仍然禁止执行**。

这不是方法实现失败。准确状态是：

- 工程/公式 Gate：通过；
- Train-only 数值审计：执行成功；
- 当前候选范围 Gate：阻断；
- Validation、simulated Test、real test：均未使用；
- 正式调参进度：`0/7`。

## 合法性证据链

方法权重不是物理常数，也不要求外部论文给出跨任务唯一数值。V9-T 冻结以下证据链：

1. 方法原理解释参数为什么存在；
2. 损失定义与 batch-mean reduction 给出数学尺度；
3. 只使用 Train 的 loss/gradient 审计排除整体过弱或过强的候选区间；
4. 候选区间冻结后，仅用 Simulation Validation 选择最终值；
5. 三点敏感性、多 seed 和配对比较检验是否依赖幸运点；
6. simulated Test 和 real test 不参与任何参数决策。

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

当前候选的中位辅助/分类 backbone 梯度比为：

| 参数 | 候选值 | 中位梯度比 |
|---|---:|---:|
| `lambda_js` | 0.1 | 7.489e-6 |
| `lambda_js` | 0.3 | 2.247e-5 |
| `lambda_js` | 1.0 | 7.489e-5 |
| `lambda_res` | 0.01 | 7.610e-6 |
| `lambda_res` | 0.1 | 7.610e-5 |
| `lambda_res` | 1.0 | 7.610e-4 |

按预注册的描述性影响带，`R < 0.01` 为几乎不起作用，`0.01 <= R < 0.1` 为弱，`0.1 <= R < 1` 为实质但不主导，`R >= 1` 为主导。当前六个候选全部落在 `R < 0.01`，所以不能声称它们覆盖了“弱—中—强”。

审计给出的中位梯度平衡中心约为：

- JS：`lambda_0 = 9.745e4`；
- Residual：`lambda_0 = 2.950e4`。

这些中心值只是当前 Train-only 轨迹上的诊断量，不是 Validation 选择结果，也没有自动写入正式候选网格。如此大的跨度要求在执行唯一一次整体平移前，先复核短轨迹、训练阶段和 influence bands 是否足以代表正式训练。

## 参数来源与冻结策略

| 参数 | 定位 | 当前依据 | 当前证据 | 正式选择方式 |
|---|---|---|---|---|
| `lambda_js` | 核心 | JS 一致性原理；旧网格仅为内部预注册，不是外部数值权威 | 语义通过；现网格尺度 Gate 阻断 | 修订并冻结三点后只用 Validation |
| `lambda_res` | 核心 | residual entropy/decorrelation 原理；旧 YAML/default 不是外部数值权威 | 语义通过；现网格尺度 Gate 阻断 | 修订并冻结三点后只用 Validation |
| residual head depth=1 | 次要 | 最小容量实现 | 单层/参数量/梯度流测试通过 | 固定，不搜索 |
| warm-up=2 | 次要 | 避免初期辅助目标干扰 | 调度单元测试通过 | 固定，不搜索 |
| ramp=3 | 次要 | 平滑开启正则 | 调度单元测试通过 | 固定，不搜索 |

## 启动 7-run 前必须同时满足

- [x] `lambda=0` 严格退化为 Dynamic/Paired ERM；
- [x] 公式、方向、reduction、数值稳定性与梯度流通过；
- [ ] 冻结候选区间覆盖不同辅助梯度强度；
- [x] 搜索范围依据与调整政策已写入仓库；
- [x] residual head、warm-up、ramp 已明确冻结；
- [x] 选择指标、seed、并列规则保持不变；
- [x] simulated Test 与 real test 完全未接触。

在第三项通过前，主合同中的两个 tuning execution switches 必须保持 `false`。候选范围最多允许在接触 Validation 前整体修订一次；修订不能由性能结果驱动，修订后必须更新配置、文档和哈希并重新运行两份审计。
