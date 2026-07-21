# V9 数据与物理模拟统一契约

本文件当前服务于 V9-T 算法迁移论文，并保留 V10 Simulator-Supervised Representation Learning 可复用的基础规范。V10 已延期，不得进入 V9-T 的论文、实验矩阵或资源计划。机器可读配置、schema 和 manifest 是执行时的最终约束。

## 数据粒度与划分

一条正式样本对应一个 Materials Project 晶体结构，而不是一张动态生成谱图。当前正式池为 `data/formal_14060`：Train 9,842 / Validation 2,109 / Test 2,109。划分以唯一结构为单位，按七晶系分层，并将同一匿名 Wyckoff 家族代理整体分配到单一集合。

同一 `material_id`、`structure_fingerprint` 或家族代理标识的所有结构与派生视图必须留在同一个 split。动态视图在完成母结构划分后在线生成并继承母结构 split。测试结构在方法与 checkpoint 冻结前不得评估。

正式结构记录至少保存：`material_id`、化学式、原始/标准化结构、MP 与重算空间群、七晶系、位点数、稳定性、hull energy、结构指纹和 split。排除无序/部分占位结构、空间群复核不一致项和 exact-cell 重复项。

## 缓存与动态视图

允许持久化的模拟中间量只有理想峰位、理想积分强度和 reflection metadata（hkl、多重性、倒易矢量、峰映射）。禁止把渲染后的固定谱或扰动谱当成新的独立结构样本。

每个动态视图必须可重放，至少记录母结构、view ID、simulation seed、五类扰动参数及激活状态、生成顺序、配置哈希和代码版本。同一 seed 下的公平比较复用完全相同的配对视图。

## 五类扰动及边界

当前物理算子为：

1. 全局 `2theta` 零点偏移；同一谱的所有峰位加同一标量，不能用逐峰随机抖动冒充；
2. 有效峰展宽；当前标量 Gaussian FWHM 是工程近似，不是完整仪器函数；
3. March-Dollase 择优取向；修改反射积分强度，不移动峰位；
4. 平滑非负背景；可用 flat、polynomial 或 Gaussian process 表示；
5. 观测噪声；可用 Poisson、Poisson-Gaussian 或明确登记的 Gaussian 近似。

`apply_probability` 只是在线数据生成中的算子覆盖控制，不是某台仪器的真实发生概率。它必须与扰动幅度范围和物理来源分开记录。

## 背景与噪声

背景与噪声是两个独立物理效应。背景是随角度缓慢变化的连续期望信号；噪声是在给定期望强度后产生的随机观测波动。观测链为：

\[
I_{expected,i}=I_{Bragg,i}+B_i,
\]

\[
C_i\sim\operatorname{Poisson}(gI_{expected,i}),\qquad
I_{obs,i}=\operatorname{clip}(C_i/g+\epsilon_{elec,i},0).
\]

随后才进行模型输入归一化。背景不得用逐点独立噪声生成；电子噪声出现负随机值时只在观测后由非负裁剪处理。

## 设备无关与证据来源

当前研究不拟合任何一台本地仪器。模拟参数来源按以下优先级登记：

1. 同行评议 PXRD 文献；
2. 论文实际使用的开源模拟代码；
3. 有明确单位、公式和适用边界的物理约束；
4. 仅在负责人明确批准时使用真实仪器数据。

每个正式扰动字段必须至少具有一个非空的 `literature_source`、`code_source` 或 `physics_basis`。配置不得静默加入仪器序列号、实验室仪器 ID、现场校准文件或标准样品 ID。

开发集谱图质量门禁可以拒绝不合理候选范围，但不能凭空创造物理范围。所有范围冻结必须保存配置哈希、参数表和审计报告。

## 真实谱红线

真实谱只属于最终 `real test`：

- 不定义模拟参数；
- 不参与 Validation 调参、开发阶段方法比较或 checkpoint 选择；
- 必须在来源、标签、预处理、结构重叠检查和评测清单冻结后一次性启用；
- real test 的结果只报告模拟到真实的外部泛化，不回流修改已冻结方法。
