# DONUT 原论文工作流逆向重建及本科毕设最小复现方案

**日期：** 2026-10-19。**状态：** 文献/代码调研与方法适配建议；并非新实验结论，也不表示已改动正在执行的 DONUT-PXRD 分支。

## 0. 调研对象与证据边界

- 原论文：Aileen Luo et al.，*DONUT: physics-aware machine learning for real-time X-ray nanodiffraction analysis*，*npj Computational Materials* **11**, 380 (2025)，2025-12-16，https://doi.org/10.1038/s41524-025-01860-7 。
- 官方代码：https://github.com/AdvancedPhotonSource/DONUT ，参考源提交 `090c10bdf99333d3670dc26e617a93364f714bdc`（2026-10-19 对照版本）。
- 核心文件：`sim_SIO_gpu.py`（GPU 可微纳米衍射正向模型）、`generate_sim_library.py`（模拟库）、`train_with_thickness.py`（可运行的**四参数 thickness 扩展版**）、`training.py`（训练器、两个 loss）、`correlation_fit_gpu.py`（传统相关拟合）。
- 公开数据：论文 Data availability 指向 https://doi.org/10.5281/zenodo.17586299 。
- **注意：** 本文是从公开论文 Methods/Results、代码重建“可复现实验顺序”，并非作者私下的真实构思时间线；后者公开证据不足，不能伪称其研发日记。

## 1. 作者论文中可复原的完整实验工作流（按合理依赖顺序）

### Step 1：把测量任务限制到可解物理反演

- **样品/任务：** SrIrO3 薄膜的 SXDM 单 Bragg 峰二维衍射图像；初始目标是 `strain ε`、`in-plane tilt ω`、`out-of-plane tilt χ`。
- **已知/固定：** 先验体相晶格常数、薄膜厚度、Bragg 几何、光子能量、探测器几何、聚焦光学参数；这些是实验测量/已有文献支持的**物理先验**，不是网络自动发现的未知参数。
- 原本已有传统相关拟合/模拟基础；本研究目标是不需要晶格参数标签而快速解析结构参数，同时降低传统相关拟合中的参数串扰。
- 来源：原论文 Introduction、Results「Model approach」、Methods「Physics-based forward model」；原代码 `sim_SIO_gpu.py`。

### Step 2：先搭建可微的物理 Forward Model

- 将 SXDM 设备坐标转到 reciprocal-space `Q`；用 zone-plate 光学限制定义入射角分布。
- 从预测的 `ε, ω, χ` 确定 Bragg 峰在 `Qx,Qy,Qz` 中的形状与位置；面内为窄高斯峰，薄膜法向为 `sinc²` 型厚度条纹；投影得到 detector 2D intensity。
- 固定几何常数，**参数变化的强度谱必须可微，梯度须能传回 Encoder**；物理分支并不是另一个可任意生成衍射图样的自由神经网络。
- 论文说明此前非光滑矩形峰函数不利于自监督反传，因此采用高斯近似。来源：Methods「Physics-based forward model」「Automatic differentiation」与 `sim_SIO_gpu.py`。

### Step 3：准备模拟、真实、混合数据三种训练域

- **模拟：** 主论文三参数扫描各 41 个点，`41³=68,921` 条 `64×64` 图像；`ε∈[-0.005,0.005]`，`ω∈[-0.05°,0.05°]`，`χ∈[-0.1°,0.1°]`。匹配实验的 photon counts，并引入 Poisson 噪声；Results 模拟对照提及每像素最高约 7 photon 的标定。
- **真实：** 同一 SrIrO3 薄膜的一次 SXDM 测量，扫描 165×165 个位置；探测器上取 128×128 ROI，再降采样到 64×64。
- **三种数据域：** simulated only / experimental only / noisy simulated + experimental mixed；最后一个在论文的覆盖范围/预测不确定性综合比较中较理想；实验数据单独训练通常更快收敛。
- 原论文给出的划分是 80% train / 10% val / 10% test。这一随机划分是**原论文事实**，不自动保证其他高度相关扫描或重复观测无泄漏。
- 来源：Methods「Neural network architecture and training」、Results「Performance on simulated/experimental data」；`train_with_thickness.py` 开头 `sim_mat_noisy`、`data`、`all_data=np.vstack(...)`。

### Step 4：建立 DONUT 双分支物理瓶颈架构

```text
      Experimental / simulated 2D diffraction
                        |
                 CNN Encoder
                        |
     3 physical latent coordinates (ε, ω, χ)
       = 1.7159*tanh(2*z/3) × physical scale
                /                  \
    trainable CNN Decoder      fixed differentiable
    reconstruct 2D image       SXDM forward renderer
                \                  /
                  compare both to input image
```

- Encoder 使用 Conv、BatchNorm、ReLU、pooling 等；Decoder 对物理 latent 进行图像重建。
- **同一个**物理瓶颈输出同时进入 Decoder 与 Physics，不允许绕过 latent 建立原始图像的捷径。
- 目标参数依次作为低维 bottleneck 的坐标，而不是用一个任意的特征 embedding 后强行解释。
- 来源：原论文 Fig.1、Methods「Neural network architecture and training」、官方 `train_with_thickness.py` 的 `Encoder`、`Decoder`、`DonutNN2`。

### Step 5：以图谱自身为监督，训练整个 Encoder–Decoder

- `L = wd * SmoothL1(decoder_reconstruction, observed_image) + wf * SmoothL1(physics_render, observed_image)`，正文 `wd=1`、`wf=5` 或 `9`；官方当前 thickness 代码使用 `(1,5)`。
- DONUT 训练 **不读 ε/ω/χ 真值作为监督标签**；模拟真值只用来评估参数误差。缺少真实晶格标签≠不需要物理 Forward。
- 正文报告 AdamW、Encoder 量级 `1e-4`、Decoder `1e-5`、batch 16、30 epochs，四张 RTX3090 完整模拟/混合训练约 4h；实验数据单独约 40min（不同训练域学习率可能调整）。
- **论文 vs 公开代码差异必须明列：** `train_with_thickness.py` 是延伸到 thickness 四个参数的脚本，当前脚本有 `EPOCHS=60`、`BATCH_SIZE=256`、`NGPUS=8` 和 Decoder `3e-5`，不等于文章中三参数主实验的固定协议。用于论文式复现应优先声明采用论文主协议，再列出硬件必要适配。
- 源码 `training.py` 的 `Trainer.train` 与 `validate` 明确计算 decoder/physics 两个损失和加权和，跟踪 validation 并保留 best checkpoint。

### Step 6：在有真值的模拟谱上检验物理参数准确性

- 模拟测试集用真实 `ε/ω/χ` 比较 DONUT、传统 correlation fitting；重点看各参数误差、二维空间预测图、strains 和 tilts 的相互串扰。
- 传统方法不是论文中的每条谱 SciPy L-BFGS-B：**原论文主要对照是模拟库 correlation matching + 轴向投影/插值**；速度比值不能直接当作 DONUT 相对于 L-BFGS-B 的加速倍数。
- 无真实参数标签也能训练，但**评估**仍可在模拟数据上有真值进行。
- 来源：Results「Performance on simulated data」、Methods「Experimental data analysis」、`correlation_fit_gpu.py`。

### Step 7：用真正实验谱做外部物理合理性检查

- 对 SrIrO3 实际测量谱比较传统拟合的图、之前 supervised NanobeamNN 的结果，以及 DONUT 结构图；特别看参数串扰和实空间条纹/畴形貌。
- MC dropout 以 10% dropout、30 次预测作为不确定性案例；论文还说明推理终版不推荐默认使用 dropout，因为减慢收敛。
- **不能将相关拟合法推得的实验参数当作严格真值，也不能把相似的实验图谱重建当作晶格参数真值。**
- 来源：Results「Performance on experimental data」、Discussion。

### Step 8：做必要方法消融、性能速度与失败边界

- 论文观察：移除 Decoder 仍能训练，但收敛可慢约 5 倍；SmoothL1/MAE 比同条件 MSE 更可训练；物理分支大权重有助于约束 latent。
- 速度是在单 RTX3090 上比较：传统 **correlation fitting** `5.6±0.4 ms/frame`，DONUT Encoder `0.024±0.001 ms/frame`，约 230 倍，CPU `0.27±0.07 ms/frame`。此为论文 SXDM 专用实验，**不得宣传为 DONUT-PXRD 的实测速度**。
- 原论文后续扩展 thickness 为四参数 bottleneck，报告混合模拟+真实训练中的强度归一化偏差与参数混淆；不能把 thickness 成功泛化到 PXRD。
- 论文提出先收集约 20,000 条谱再边测边微调 encoder 的仪器工作流作为未来部署构想；不是本文已对任意 PXRD 实验台实现的功能。
- 来源：Results「Fig.4」、Discussion 与 Methods。

## 2. 一张源代码对照表

| 作者的环节 | 官方源文件 | 作用 | 直接移植程度 |
|---|---|---|---|
| 固定物理几何、可微散射 | `sim_SIO_gpu.py` | `forward(params)` | **核心思路照搬，SXDM 数学不照搬** |
| 生成模拟库 | `generate_sim_library.py` | 模拟参数空间/传统基线 | 生成训练评估谱的流程可借鉴 |
| 单/混合训练集 + Conv Encoder/Decoder | `train_with_thickness.py` | 数据流、参数瓶颈、模型 | 改 2D Conv 为 1D，注意 thickness 扩展 |
| 两支损失和 checkpoint | `training.py` | `loss_decoder`、`loss_sim` | **直接复用训练机制** |
| 传统反演对照 | `correlation_fit_gpu.py` | Correlation lookup/interpolation | PXRD 可改为现有 L-BFGS-B，注明不是原文同算法 |
| 原始示例数据 | Zenodo 17586299 | 模拟与真实 SXDM 样品 | 不可直接作为粉末 XRD 训练数据 |

## 3. 我们的本科毕设「照抄」方案：尽量小而闭环

**一句话研究命题：** 将 Luo 等人的 DONUT 双分支无参数标签训练范式由 **二维 SXDM** 迁移到 **单相已知模板的一维 PXRD 参数反演**，验证是否能得到有意义的晶格初值，并量化其相对传统物理优化和监督学习的计算代价。

**明确不是**发现通用全结构反演模型、从未知混相自动解结构、完整 Rietveld、复现 DONUT 原 2D 数值。

### 我们的最小 6 步（与作者流程逐一对应）

1. **固定对象+采样协议。** 使用已有公开 `BaTiO3 P4mm` 模板，输入固定波长、10–80°、0.02° 的 1D PXRD；第一版预测 `q=(du,dv)`→`a,c`。用 `512` 条参数样本、分配 train/val/test 后才扰动；3 seeds（用现有 PR #26/#31 工程记录与协议）。
2. **复用已经验证的可微 Forward。** 使用 `xrd_inversion.gpu_forward` 和 PR #26 measurement-aware expected profile；先固定 zero shift、FWHM 和 background。只作必要的 parity/梯度检查，不再另造一套物理软件。
3. **真正移植 DONUT。** 1D Encoder → 2D physical bottleneck → (1D trainable Decoder, fixed differentiable PXRD Forward)；对**观测谱**用 `SmoothL1` 双分支损失 `wd=1,wf=5` 起步，**不对 DONUT 使用 `q_true` 的监督损失**。记录两分支梯度、train/val curves 与 best weight。
4. **按 DONUT 方法扩展第二个物理维度问题。** 允许 zero shift 成为第 3 个输出，检查它与 `du/dv` 的误差混淆；逐项添加 FWHM、背景、噪声，再做一次织构分布偏移压力测试。**March–Dollase 只有在真实实现并核验后才称作织构模拟**；允许把不具可微性时的织构作为 OOD 测试，不必强行进行无依据的联合反演。
5. **公平对照。** 同一测试谱比 DONUT 直接输出、监督 A/B/C 直接输出、传统 L-BFGS-B 从中性初值，以及 NN 初值后同预算的 L-BFGS-B。输出 `q/a/c error`、profile RMSE、零点参数 error、成功率、推理 P50/P95、训练 GPU 时间，不能把作者的“230× correlation fitting”挪用。
6. **一个真正实验谱案例**（如能获得相同相/已知候选结构且有波长、零点等元数据的公开粉末谱）：展示结构合理性、模拟/观测谱叠图、传统物理拟合对照、失效原因；无独立晶格真值时明确只能验证谱拟合和一致性。COD 的 CIF **不是**真实实验粉末谱，不能代替实验域验证。

### 本科毕设最低交付（而非无限追加课题）

- **图 1**：二维 SXDM DONUT → 一维 PXRD DONUT 的对应方法图；
- **图 2**：模拟测试上参数预测 `a/c` 真值–预测散点图 + 噪声变化；
- **图 3**：一张实验谱的测量/physics forward/reconstruction 叠图（数据可得时）；
- **表 1**：同数据、同硬件 DONUT vs A/B/C vs L-BFGS-B 精度/速度/失败率；若真实谱无真值就用谱残差和物理合理性报告；
- **表 2（可选）**：去 Decoder 或替换 MSE 的训练收敛消融，直接对应论文关键机制；
- 技术报告包含失败、不适用边界、所有权重哈希及清晰声明“移植现有 DONUT 方法，未发明新架构”。

### Go/No-Go（轻量版）

- 可微物理模型与原始模拟器数值一致、梯度有效；
- 自监督训练真实执行并能输出有限物理参数；不要求它必须超过所有监督基线；
- 模拟测试上参数 error 可量化，实验谱上不宣称无标签真值；
- 相同计算预算和相同数据评估下，明确知道 DONUT 相对监督模型与传统拟合在**标签需求 / 速度 / 精度**中的至少一个实际强项或边界；没有强项也可如实形成“方法适用性评估”毕业论文。

## 4. 与当前 AI4science 的关系 / 不要干扰正在执行的任务

- 已启动的四项 DONUT-PXRD 实验任务在独立 `codex/donut-pxrd-four-stage-20261019` 分支，其原协议 `docs/DONUT_PXRD_FOUR_STAGE_EXECUTION_20261019.md` 保持不变。本文仅作来源复核和后续毕设范围建议，**不自动重启/改写正在运行的 Codex**。
- 之前 `PR #26`、`Issue #31` 的 A/B/C 代码和模拟器属于已经完成的技术准备，对照应复用并标注其监督学习标签；冻结 V9 七晶系分类主线不受影响。
- 因为“昨天是先做 A/B/C 后系统对照 DONUT”，此次方法演进可记录为：**从监督回归中的物理辅助损失探索，转到对已有 physics-aware 双分支 self-supervised 范式的来源核验与受限 PXRD 移植**。不得反向宣称最初就是 DONUT 引导整个 XRD 项目。

## 5. 引用与关键代码路径（官方）

1. Original paper: https://www.nature.com/articles/s41524-025-01860-7 ，尤其 Results: Model approach/Simulated/Experimental，Methods: Neural network architecture and training/Forward/AD。
2. Official code: https://github.com/AdvancedPhotonSource/DONUT ，pin `090c10bdf99333d3670dc26e617a93364f714bdc`。
3. Training entry: https://github.com/AdvancedPhotonSource/DONUT/blob/main/train_with_thickness.py 。
4. Loss implementation: https://github.com/AdvancedPhotonSource/DONUT/blob/main/training.py 。
5. Forward implementation: https://github.com/AdvancedPhotonSource/DONUT/blob/main/sim_SIO_gpu.py 。
6. Conventional baseline: https://github.com/AdvancedPhotonSource/DONUT/blob/main/correlation_fit_gpu.py 。
7. Original data archive: https://doi.org/10.5281/zenodo.17586299 。

**重要：这是一个易于毕业答辩的复现/应用迁移方案，不是优先寻求算法 novelty 的大规模研究计划。**
