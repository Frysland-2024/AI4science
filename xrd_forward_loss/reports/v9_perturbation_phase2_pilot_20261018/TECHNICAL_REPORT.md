# V9 扰动与 clean-reference Forward Loss 工程 Pilot

> 这是单一已知 HfCd 母结构上的模拟器工程 Pilot，不代表铁电陶瓷或真实实验谱验证。B 使用模拟器生成的 clean reference；不得解释为真实实验谱上的无监督物理重建。

## 数据与接口

- 材料：HfCd（mp-1007758），来源 split=train；共 128 个晶格参数样本，train/validation/test=90/19/19。
- CIF：未提供；从本地冻结 structure_records.jsonl 的 standardized_structure JSON 重建结构，指纹 `3372b44a22899c7f335410eb74d2f7e8f50270ef242a7fddc21af142f05cd46f`。
- `sample_records.jsonl` 保留 Sobol float64 的 `theta_true` 和晶格真值；NN 输入数组中的 q 按现有训练接口存为 float32，本次两者最大舍入差为 2.9802322387695312e-08。
- 配置 SHA-256：`2801ab28d547fddd63eab21c801ec0195c2aaf6e8de69496fdb0b1a8d741a144`；数据阵列 SHA-256：`d65a946d545f0c50645c89caa380ea551bb2233836bd22fac504fc1a1ceeca3e`。逐样本 q、lattice truth、扰动参数/类型/采样 seed、结构来源与配置哈希在 `sample_records.jsonl`；profile 阵列按同一 sample_index 存于 `pilot_samples.npz`。
- A/B 汇总值由 `validate_v9_pilot_results.py` 从逐 seed 预测、保存谱阵列及 JSON 结果重新计算；复算状态和 SHA-256 见 `results_validation.json`。
- 谱顺序：干净相对强度（峰值归一化）→ V9 平滑背景 → Poisson 计数和计数域 Gaussian 读出 → clip → 每谱单次 max 归一化 → log1p 变换。背景与噪声前不做归一化。原始绝对计数未建模，因此是相对计数工程模拟。
- Forward/V9 clean renderer 兼容 Gate：通过，max abs=1.04e-07，RMSE=2.12e-09。

## V9 接入范围与物理检查

- 操作 Gate 总体：通过。noise=True，smooth background=True，area-stable broadening=True，whole-pattern zero shift=True。
- Forward lattice Jacobian rank/condition：full-rank=True，condition=3.36；有限差分与 autograd Gate=通过。Loss 名称为 `simulator-supervised clean-reference forward loss`。
- March–Dollase 保持关闭：当前 pilot 不需要择优取向，且没有将随机逐峰缩放伪装成晶面择优取向。
- 扰动范围是工程压力测试范围，不是任何仪器标定范围。零点偏移和峰宽只改变输入谱，不改变 q 标签。

## 运行结果

- 本报告阶段：`phase2_add_broadening_and_zero_shift`。四格单 seed smoke 的有限损失检查：通过。Smoke 只跑 1 epoch，最多 16 个训练样本，不作为效果结论。

### 测试集聚合指标（每 seed 独立评估；报告 mean ± sample SD）

| 条件 | 方法 | normalized-q MAE | a MAE (Å) | c MAE (Å) | clean谱 RMSE | observed谱 RMSE | 秒/训练 | 峰值显存 MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| simple | A | 0.059126 ± 0.0086 | 0.00088773 ± 0.00019 | 0.0071814 ± 0.00078 | 0.029855 ± 0.0038 | 0.073714 ± 0.0014 | 3.2978 ± 0.071 | 615.11 ± 59 |
| simple | B | 0.05208 ± 0.0072 | 0.00081906 ± 0.00015 | 0.006147 ± 0.0011 | 0.027205 ± 0.0022 | 0.072762 ± 0.0007 | 4.5655 ± 1.1 | 790.74 ± 1.6 |
| v9 | A | 0.072926 ± 0.011 | 0.0017368 ± 0.00015 | 0.0094225 ± 0.0012 | 0.042989 ± 0.0027 | 0.096505 ± 0.00068 | 7.1738 ± 0.29 | 650.42 ± 1.3 |
| v9 | B | 0.068419 ± 0.006 | 0.0018474 ± 0.00025 | 0.0089636 ± 0.00053 | 0.04365 ± 0.0039 | 0.095836 ± 0.00018 | 8.939 ± 0.22 | 790.86 ± 2.1 |

A 为普通监督参数回归；B 为相同网络、数据和预算的监督回归加 clean-reference Forward Loss。`paired_differences_b_minus_a` 中负数表示 B 的该误差更低，正数表示更高。三组 seed 是预先配置的配对 Pilot，不做测试集超参选择。逐 seed 指标见 `results_summary.json`；完整预测和重建谱保存在 `results_full.json.gz`，训练过程见 `training_histories.json`，失败样本见 `failure_cases.json`。

## 结果解释与迁移限制

少量单父结构结果只用于工程可运行性与 A/B 初步诊断。不能将测试集差异解释成材料泛化、铁电陶瓷表现或真实谱物理有效性；无论正负均完整保留。迁移前置条件见上节。
