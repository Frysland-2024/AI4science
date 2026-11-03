# PXRD 模拟器版本与就绪状态登记

**记录日期：** 2026-11-03

**范围：** 本文登记当前 Git 分支中可复现的 V9/V11 PXRD 模拟器实现，以及 V11 与 154,975 条结构库的接通证据。这里记录的是工程就绪状态，不是模型精度或实验科学结论。

## 当前结论

- **V9** 是历史结果和既有调用路径的基线/默认渲染器；既有 V9 结果与配置保持不变。
- **V11 `v11_tch_pseudo_voigt`** 是版本化的 opt-in 实现，配置状态为 `development_opt_in`。它通过七 CIF 验收，并已能从全库验证通过的 PeakTable 在线渲染。
- **154,975 条结构库 → 理想反射 PeakTable → train/validation runner manifest → V11 在线谱渲染** 的路径已完成本地整库集成和文件级审计。
- 这些证据不表示全量持久化谱图已经生成、全 epoch 渲染速度已测量或模型训练已开始。全规模谱图生成与模型训练仍以用户计划的腾讯云环境为目标。

## Git 可复现版本清单

| 版本 | 当前角色 | 主要实现/记录 | 使用口径 |
| --- | --- | --- | --- |
| V9 | 历史基线、遗留调用默认值 | [`simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py) | 复现既有实验；不因 V11 的实现而改写历史结果。 |
| V11 | 当前版本化的物理线型 opt-in renderer | [`simulator_v11.py`](../xrd_robustness/src/xrd_robustness/simulator_v11.py)、[`V11 配置`](../xrd_robustness/configs/simulation.v11_tch_pseudo_voigt.json) | 显式选择配置；目前适用于受控试验和已有 PeakTable 的在线渲染。 |

V11 的版本化实现来自提交 `f18c27b`。本登记不把工作区里未跟踪的试验脚本或未归档的 V10 工作当作可复现发布版本。

## V11 模型与输入约定

V11 复用 V9 的反射计算和已建立的零点偏移、织构、背景与计数噪声阶段，在峰线型阶段使用 TCH pseudo-Voigt。高斯分量使用 Caglioti 角度依赖宽度；洛伦兹分量可叠加 Scherrer 晶粒尺寸展宽和微应变展宽。首选取向通过 March–Dollase 调整反射积分强度，背景和 Poisson/可选计数空间电子噪声沿用显式 profile 配置。

当前配置的基础网格为 **10–80° 2θ、0.02° 步长、Cu Kα、3,501 点**。线型配置包括 Caglioti `U=0.0012°²`、`V=0.0004°²`、形状因子 `K=0.9`、晶粒尺寸 `50–200 nm`、微应变 `1×10⁻⁵–2×10⁻⁴` 和波长 `1.54184 Å`。这些是配置参数，不是对具体仪器已完成校准的声明。

## 验收与整库接通证据

1. **独立模拟器验收：** 七个真实 CIF、每个晶系一个代表样本；标签保持、输出有限、同母结构双视图不同、固定随机状态下重放一致。Caglioti、Scherrer、微应变展宽和峰面积检查通过，V9 渲染路径保持不变。
2. **整库 PeakTable：** 70/15/15 划分按 108,483 / 23,246 / 23,246 条结构处理；完成 **154,975/154,975**，跳过 0。全部缓存的 ID、fingerprint、文件大小和逐文件 SHA256 审计通过。缓存共 **1,739,337,682 bytes**，本地 Windows 执行合计约 **40.78 分钟**。
3. **训练清单隔离：** runner manifest 有 **131,729** 行，只包含 train 和 validation；test 行数为 0。test PeakTable 虽已生成用于文件完整性核验，但 test 没有进入训练/验证清单。
4. **缓存到 V11：** train 与 validation 各抽取一个真实缓存，均得到有限的 3,501 点同母结构双视图；两视图不同且可确定性重放。
5. **定向测试：** `test_simulator_v11.py` 与 `test_peak_cache.py` 共 **10 项通过**。V11/V9 的双视图耗时对比约 **2.63×**，该值来自七个缓存样本的 renderer-only 小测，不可外推为全 epoch 或云端运行时间。

详细数据、源分片哈希、分片耗时和缓存 aggregate 哈希见[机器可读整库报告](../xrd_robustness/reports/simulator_v11/merged_154975_precompute_20261103.json)。逐步复现命令见[结构库适配说明](STRUCTURE_LIBRARY_154975_TRAINING_ADAPTER.md)。V11 的独立验收边界见[readiness 记录](SIMULATOR_V11_READINESS_20261103.md)。

## 数据边界、执行环境与后续门槛

- PeakTable 保存理想反射中间数据；V11 在线渲染谱图。整库运行没有导出持久化 V11 谱图，也没有启动训练。
- PeakTable 缓存位于 Git 忽略路径 `xrd_robustness/data/merged_154975_v11`，总量约 **1.62 GiB**。仓库提交保存适配代码、清单构建器、运行摘要和哈希证据，不保存这些大缓存文件。
- 本轮整库预计算在本地 Windows 工作站完成，**不是腾讯云测试**。这次测量只用于本地接通和完整性验证，不作为云端资源配置建议。
- 全规模训练前仍需在计划租用的腾讯云环境测实际渲染吞吐、存储/传输需求与运行成本，并继续遵守 train 用于拟合、validation 用于选择、test 仅用于最终评估的划分角色。
- 七 CIF 验收的 renderer-only 双视图均值为 V11 `0.00690 s`、V9 `0.00262 s`。正式仪器校准、跨来源真实数据评估及全规模训练表现仍未由本登记证明。

## 归档索引与决策状态

- 实现：[`simulator_v11.py`](../xrd_robustness/src/xrd_robustness/simulator_v11.py)
- 配置：[`simulation.v11_tch_pseudo_voigt.json`](../xrd_robustness/configs/simulation.v11_tch_pseudo_voigt.json)
- 验收脚本：[`accept_simulator_v11.py`](../xrd_robustness/scripts/accept_simulator_v11.py)
- 定向测试：[`test_simulator_v11.py`](../xrd_robustness/tests/simulation/test_simulator_v11.py)、[`test_peak_cache.py`](../xrd_robustness/tests/simulation/test_peak_cache.py)
- 整库报告：[`merged_154975_precompute_20261103.json`](../xrd_robustness/reports/simulator_v11/merged_154975_precompute_20261103.json)
- 相关实现/证据提交：`f18c27b`（V11 实现）、`47f47ff`（有界 readiness）、`a181f36`（结构库划分证据）、`600c0cd`（全库 PeakTable 接通）。

**状态：** V11 BOUNDED ACCEPTANCE PASS / FULL PEAKTABLE INTEGRATION VALIDATED / FULL-TRAINING THROUGHPUT NOT MEASURED.
