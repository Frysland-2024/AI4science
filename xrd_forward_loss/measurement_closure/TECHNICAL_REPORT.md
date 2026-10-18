# Issue #19：测量一致的 Forward 闭环

**状态：** P0–P2 Gate 与 P3 smoke / 正式 exploratory A/B 均完成；结果已保留。
**范围：** 单一公开 BaTiO₃ CIF（COD 9014273，P4mm）的合成谱与连续参数插值。本文不代表未见结构泛化、真实 XRD 验证或 Rietveld 精修能力。

## 结论

Measurement-aware expected forward 的全谱 parity、autograd/有限差分、未知 nuisance 局部可辨识性、non-oracle 数值恢复与噪声期望 Gate 全部通过；P3 在 RTX 4060 上按预算完成。A/B 结果是混合的：simple 条件下 B 的平均两维 q MAE 略高，V9 条件下略低；两种条件下 B 的观测谱残差都高于带有测试时受界 nuisance profile fitting 的 A。B 没有显示出一致优势，本结果只支持闭环可运行，不支持把 B 宣称为更好的参数反演方法。

## P0：旧目标与本次目标

旧 `paired_losses` 将预测的晶格 q 补上固定零点和最窄宽度，再将 clean forward 与 observed profile 做 MSE。`compose_full_q` 固定 zero-shift 坐标为 0、width 坐标为 -1；测量位移、展宽、背景和计数噪声没有进入该 forward。PR #17 的 `clean_reference_paired_losses` 将目标换为模拟器提供的 clean profile，因此数值上自洽，但依赖真实测量中通常不可用的 privileged clean target。

本次定义观测期望谱 `mu(q,eta)=M(F_crystal(q),eta)`。q 为归一化 `du,dv`，映射到 a、c；eta 为 2θ zero shift、FWHM 与背景幅度。噪声是观测生成过程，不要求重建某次 Poisson/readout realization。B 用预测的 eta 与 observed profile 训练，不读取 eta_true；eta_true 只用于生成/元数据和评估后的 nuisance 误差诊断。

P0 使用 5-site BaTiO₃ CIF，参考晶格 `a=b=3.986 Å, c=4.026 Å`，P4mm (#99)，Cu Kα `λ=1.54184 Å`，10–80°、0.02° 网格（3501 点）。Pymatgen/V9 对照覆盖 7 个 q 探针：最大全谱绝对误差 `1.1921×10⁻⁷`（门限 `2×10⁻⁶`），最大 RMSE `4.4403×10⁻⁹`（门限 `2×10⁻⁷`），Bragg 角最大误差 `1.42×10⁻¹⁴°`。P0 通过。

## P1/P2：测量物理、梯度和未知参数 Gate

P1 v1 的五维未知参数为 q 的两个分量，加 zero shift、FWHM、背景幅度以及两个自由背景形状系数。max-normalization 下两个背景形状自由度不可辨识：条件数 `3.06×10¹⁶`，绝对列相关为 1，因此 v1 明确失败。随后按冻结的 V9 配置（`background_variation=0`）固定确定性背景形状，只估计幅度。v2 保持原 Gate 阈值不变；不是降低门槛。

| Gate | 实测 | 阈值 | 结果 |
|---|---:|---:|---|
| Torch/V9 全谱 parity（5 种测量配置，最差 max abs） | `2.0323×10⁻⁸` | `2×10⁻⁶` | PASS |
| Torch/V9 全谱 parity（最差 RMSE） | `2.3100×10⁻⁹` | `2×10⁻⁷` | PASS |
| autograd 与中心有限差分最大相对误差 | `2.2150×10⁻⁴` | `0.01` | PASS |
| q+eta 局部 Jacobian condition number | `23.398` | `≤1000` | PASS |
| q/nuisance Jacobian 最大列相关绝对值 | `0.92390` | `≤0.995` | PASS |
| 两个 non-oracle profile fit 的最大 q 绝对误差 | `8.873×10⁻⁸` | `0.02` | PASS |
| 两个 non-oracle profile fit 的最大归一化 eta 绝对误差 | `1.018×10⁻⁶` | `0.1` | PASS |
| Poisson 期望重复采样 RMSE | `6.455×10⁻⁴` | `0.02` | PASS |

non-oracle fit 不读取 q_true 或 eta_true。错配对照在真实 q 处产生 loss `0.01049` 和 `du` 梯度 `+0.05571`；仅优化 q 时最优 `du` 从 `0.2` 偏到 `0.13950`（偏差 `−0.06050`），说明 clean-versus-observed 配对可诱导晶格参数补偿测量扰动。统计噪声诊断使用 64 次重复抽样；不要求单次噪声谱的梯度为零。`xrd_forward_loss/tests` 共 23 项通过。

## P3：冻结设计与防泄漏

- 512 个 Sobol q 样本，q 范围 `[-0.8,0.8]`；在测量/noise draws 前切分为 358/77/77（train/validation/test）。配对 seeds：20261045、20261046、20261047。
- simple：zero shift=0，FWHM=0.08°，100–200 counts 线性背景，Poisson 计数。
- V9：zero shift `[-0.06,0.06]°`，FWHM `[0.11,0.13]°`，背景比 `[0.005,0.008]`，Poisson 加 0.5–1.5 count Gaussian readout；V9 二次背景形状固定。March–Dollase 关闭。
- A：ResNet-18-GN 参数监督。B：同一主干与输入，参数监督加 `λ × MSE(mu(q_pred,eta_pred),x_observed)`；谱 MSE 在 max-normalized `log1p_100` 域，拟合的是确定性期望谱。B 输出额外 3 个 nuisance 坐标，无 eta_true 监督，模型参数比 A 多 771 个（13,008,325 vs 13,007,554）。
- 两个 λ 候选仅由每个条件内三 seed 的 validation q-MAE 均值决定，平局选较小 λ；test 未用于任何选择。

Smoke 使用 128 q、seed 20261045、A/B×simple/V9、最多 4 epochs；4 条路径 loss 有限，B 的 q/eta reconstruction 梯度均有限且非零，峰值 CUDA 分配 458.21 MiB，Gate 通过。正式训练每个选定 A/B seed 最多 24 epochs；未选 λ 仅训练 4-epoch validation 候选。

## P3：测试结果

每格为三 seed 均值 ± sample SD；每个 seed 的原始数值保存在 `results/p3_issue19_20261018/formal/ab_results.json`。

| 条件 / 方法 | du MAE | dv MAE | 两维 q MAE | a MAE (Å) | c MAE (Å) |
|---|---:|---:|---:|---:|---:|
| simple / A | 0.011954 ± 0.000973 | 0.015112 ± 0.001344 | 0.013533 ± 0.000849 | 0.000498 ± 0.000066 | 0.000699 ± 0.000022 |
| simple / B | 0.012151 ± 0.001764 | 0.015201 ± 0.002392 | 0.013676 ± 0.001923 | 0.000525 ± 0.000110 | 0.000679 ± 0.000028 |
| V9 / A | 0.040573 ± 0.006453 | 0.023897 ± 0.005709 | 0.032235 ± 0.001255 | 0.001571 ± 0.000301 | 0.001879 ± 0.000098 |
| V9 / B | 0.037746 ± 0.004721 | 0.023363 ± 0.003302 | 0.030554 ± 0.002580 | 0.001452 ± 0.000187 | 0.001778 ± 0.000136 |

| 条件 / 方法 | observed expected-profile RMSE | clean-reference residual RMSE（辅助） |
|---|---:|---:|
| simple / A | 0.009456 ± 0.000016 | 0.016700 ± 0.000606 |
| simple / B | 0.015885 ± 0.001492 | 0.016364 ± 0.001357 |
| V9 / A | 0.016034 ± 0.000795 | 0.041246 ± 0.004522 |
| V9 / B | 0.027332 ± 0.001431 | 0.039560 ± 0.003798 |

validation λ 结果：simple 的 `{0.1: 0.036401, 1.0: 0.038089}` 选 `0.1`；V9 的 `{0.1: 0.075494, 1.0: 0.063639}` 选 `1.0`。test 两维 q MAE 上，simple B 比 A 高 `0.000143`；V9 B 比 A 低 `0.001681`（约 5.2%）。三 seed/单 CIF 仅作描述，不能据此称稳定收益。

### Nuisance 诊断与 profile 残差的解释

B 的 nuisance scaled-coordinate MAE（坐标顺序为 zero-shift/FWHM/background，各自按配置范围缩放）为 simple `[0.04180,0.10819,0.03765]`、均值 `0.06255`；V9 `[0.44737,0.21598,0.15530]`、均值 `0.27288`。V9 B seed 20261045 的最差样本（全局 index 406）预测 `δ=+0.00567°`、真实 `δ=−0.05823°`；真实值只用于写入事后诊断。

观测谱残差口径不是相同计算量：B 直接用网络预测 eta；A 没有 eta head，评估时对每个样本固定 q_pred、用 observed profile 做受界 L-BFGS-B eta profile fit（每条件/seed 77 个 fits，平均约 8.5–9.2 iterations；V9/simple 部分拟合会到边界）。该 A profile fit 不读 eta_true，也不改变 q/a/c 指标，但给 A 额外的测试计算。故此 profile 残差表是各自可运行推理路径的记录，不是证明 B 重构更差或 A 方法整体更优的公平单一指标；它显示 B 的 V9 eta head 仍有明显 zero-shift 误差。

## 运行成本、失败记录与复现

设备为 NVIDIA GeForce RTX 4060 Laptop GPU，Torch `2.13.0+cu126`、CUDA `12.6`、Python `3.11.9`。重跑正式训练与 λ 选择 `736.99 s`，smoke `19.05 s`；第一次正式尝试在测试评估前因 checkpoint RNG 恢复错误失败，保守计入 `630 s`。累计训练+λ+smoke 记为 `1386.05 s`（23.10 min），硬预算 `7200 s`；test evaluation 另计 `121.20 s`。正式训练峰值 allocated CUDA memory 约 `775.74 MiB`。

失败保留：P0 首次运行因 Pymatgen API 名称变化在 Gate 前退出；P1 v1 因背景自由度不可辨识而失败；P3 首次正式运行完成 A 和 λ 候选后，在续训 B 时将 RNG ByteTensor 错映射到 CUDA。没有放宽 Gate；P3 修复后从新目录内的全新 formal 数据与 seed 重新执行，且把第一次尝试的保守耗时计入预算。失败日志、数据和 checkpoint manifest 纳入 PR；46 个原始 checkpoint 权重保存在当前 worktree 的 `results/p3_issue19_20261018/` 下，不纳入 Git。

训练源 commit 为 `0e90eac79c1ae58252b4848a921bf43ee6d2669c`；配置 SHA-256 为 `b17a9db0eed38557f4b06a092f8d4a35437619025f78532119e3a923ddf2251f`；`formal_data.npz` SHA-256 为 `88401a857bc7a4849731fbb5e881b37efef7483e0ec13415f977db035e333a29`；CIF SHA-256 为 `e854c9868f643183904606b8c24463f8f0bacc1cca90f283641b33346db748b4`。命令与 exit code 见 `results/p3_issue19_20261018/command_log.json`，46 个原始 checkpoint 的 SHA/大小台账见 `checkpoint_manifest.json`。

原始 46 个 checkpoint 共 `9,579,304,254` bytes（约 8.92 GiB）；每个文件都重复保存 best/last 两份 FP32 模型权重和 Adam 状态。训练结束后保留 12 个最终模型（A/B × simple/V9 × 3 seeds）的 FP32 `best_model_state`，合计 `624,709,422` bytes（约 596 MiB）；逐张量核对与原始权重完全相同，并已用 RTX 4060 的现有加载函数逐个成功加载。其余训练状态和 34 个中间 checkpoint 已清理，释放 `8,954,594,832` bytes（约 8.34 GiB，93.48%）。当前小 checkpoint 可用于模型推理/重算，不含 optimizer、last state、RNG 和训练 history，不能从中断点续训；这些实验记录仍由单独的 history、metrics、数组、配置和原始哈希台账保留。优化详情及精简权重哈希见 `results/p3_issue19_20261018/checkpoint_space_optimization.json`。compact 数据、history、metrics、prediction arrays 与图表在 PR 中跟踪。

主要机器结果：

- Gate：`results/p3_issue19_20261018/gate_report.json`
- Smoke：`results/p3_issue19_20261018/smoke/smoke_report.json`
- λ 选择、A/B 指标和逐 seed 预测：`results/p3_issue19_20261018/formal/ab_results.json`
- 训练曲线历史：`results/p3_issue19_20261018/formal/training_history.json`
- train/validation/test 和测量期望/observed 数据：`results/p3_issue19_20261018/formal/formal_data.npz`
- 测试谱数组：`results/p3_issue19_20261018/formal/test_profile_predictions.npz`
- QA 图：`results/p3_issue19_20261018/formal/figures/p3_training_and_test_summary.png`

## 结论边界

本工单回答的是单一已知 BaTiO₃ 模板、合成测量扰动下的 conditional `du,dv` 插值。v2 的确定性背景形状适用于本配置（V9 variation=0），不等于一般背景已建模。没有真实谱、未见材料、混相、优选取向、仪器校准或精修初值测试；三 seed 结果不能支持一般化方法优势。保留 measurement-aware B 作为经过物理和梯度闭环验证、但效果尚未确立的工程候选。现有冻结 V9 分类结果、PR #11/#16/#17 历史和 factorization NO-GO 不变。
