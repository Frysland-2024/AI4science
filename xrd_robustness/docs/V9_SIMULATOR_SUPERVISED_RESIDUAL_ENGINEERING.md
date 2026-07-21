# V10 Simulator-Supervised Representation Learning（延期研究）

状态日期：2026-07-16。该研究正式记为 V10，并已延期。当前唯一主线是先完成 V9-T 算法迁移论文；本文件只保存未来重启时的研究记忆，不属于 V9-T 的论文、实验矩阵或资源计划。未经用户以后明确重新开启，不得继续补工程、执行检验或启动训练。现有完成度仍约 15%。

V10 可以直接复用 V9-T 建立的成对动态扰动生成器、backbone、OOD 面板、真实谱测试集、residual 接口和公平训练协议；因此延期不会浪费当前工作。

## 研究问题

对同一母结构生成两个扰动视图：

\[
x_1=T(x_0,z_1),\qquad x_2=T(x_0,z_2),\qquad r=f(x_2)-f(x_1).
\]

检验模拟器已知的扰动差 `Δz=z2-z1` 能否监督残差 `r`：

1. `r` 能预测测量扰动差；
2. `r` 尽量不泄漏七晶系类别；
3. 主分类器的 OOD 泛化得到改善，且 ID 性能没有不可接受的下降。

该研究不预设机制一定成立，也不把条件参数可预测自动解释为可迁移表征。

## 已有可复用原型

- `perturbation_supervised_residual` 训练模式；
- 有符号残差 `normalize(f(x2))-normalize(f(x1))`；
- 扰动差回归头与晶系残差判别器；
- shift difference 与 `log(FWHM)` difference 的目标构造；
- 两阶段辅助头/主模型更新；
- post-hoc residual class probe；
- 单元测试和 CPU smoke。

现有入口包括 `configs/training_perturbation_supervised_residual.yaml`、`configs/simulation.v7.perturbation_supervision_pilot.json` 和 `scripts/run_v7_perturbation_supervision_smoke.py`。它们只证明旧原型存在，不能作为 V9 参数冻结或正式实验授权。

## 执行前必须完成的检验

### 1. 扰动标签可辨识性

先对全局峰移和有效峰宽分别检验：从谱图对或特征残差预测 `Δshift`、`Δlog(FWHM)`，必须显著优于恒预测零、只看单视图和打乱标签三种对照。报告 MAE、标准化 MAE、R² 和置信区间。

### 2. 模拟器指纹与伪标签对照

至少加入：

- 打乱扰动标签；
- 保持强度分布但破坏参数—谱图对应关系；
- 跨随机种子或替代渲染设置测试；
- 未见扰动强度与未见扰动组合。

如果辅助任务只识别伪随机流、归一化痕迹或单一渲染器指纹，则不能进入正式主实验。

### 3. 残差方向与尺度

冻结有符号方向、特征归一化、连续目标的单位和尺度。交换两个视图时，残差与扰动差都必须同步变号；乘性参数使用对数差。

### 4. 类别泄漏

训练后的主模型冻结后，使用独立 train/validation/test residual probe 预测晶系。必须与单纯数据增广基线（具体采用 Dynamic/Paired ERM）和无扰动监督的残差去相关进行配对比较；probe 下降不能以主任务崩溃或残差坍缩为代价。

### 5. 公平性与消融

正式比较至少包含：

- 单纯数据增广基线（Dynamic/Paired ERM）；
- 无扰动标签的残差类别去相关；
- 仅扰动差监督；
- 扰动差监督 + 残差类别去相关；
- 打乱标签对照。

各组保持相同母结构、配对视图、backbone forward、optimizer steps、结构曝光和 checkpoint 规则。辅助头计算单独报告。

### 6. 独立评测与真实谱

方法选择只用 Validation ID/development-OOD。simulated test 与 real test 在方法、超参数、checkpoint、预处理和评测清单冻结前保持关闭。真实谱只用于最终 real test，不判断扰动标签方案是否进入正式运行。

## 尚未冻结

- V9 机器可读算法契约和 schema；
- 只使用 shift/width 还是扩展背景、噪声与择优取向；
- 参数 target 的统一表示与损失权重；
- 可辨识性诊断达到预注册阈值，且主任务验证指标不退化；
- 固定 OOD/未见组合评测清单；
- CUDA 预算、正式 seeds、运行次数和报告格式；
- simulated test 与 real test 解锁契约。

在以上项目完成前，只允许软件回归和可辨识性检验，不允许宣称“模拟器监督有效”或启动正式大规模研究。
