# PXRD 五类扰动：物理与文献依据

**状态：当前主线的显式证据索引。** 这不是新的科研 TODO，而是把 V6–V9 阶段已经完成的扰动文献核验重新放回当前 `main` 的显眼位置，避免后续误以为五类扰动及其数量级是“拍脑袋设定”或仍需重新做一轮文献调查。

当前最终实验使用的权威配置是：

- [`../xrd_robustness/configs/simulation.method_transfer.frozen.json`](../xrd_robustness/configs/simulation.method_transfer.frozen.json)

## 1. 当前冻结的五类扰动

| 扰动 | Train / in-range | 单因素 OOD / stress | 当前物理解释 |
|---|---|---|---|
| 全谱峰位偏移 | `delta_2theta_deg ~ U(-0.2, 0.2)°`, `p=0.5` | `[-0.5,-0.2]°` 与 `[0.2,0.5]°` | 全谱共享的零点/样品高度/标定型角度偏移；不等同于晶格应变 |
| 峰展宽 | `FWHM ~ U(0.08,0.20)°`, `p=1` | `FWHM ~ U(0.20,0.35)°` | 有效标量峰宽代理；物理上对应有限晶粒、微应变、仪器展宽等造成的峰宽变化 |
| 择优取向 | March–Dollase `r ~ U(0.8,1.0)`, `p=0.7`，优选轴取低指数反射 | March–Dollase `r ~ U(0.5,0.8)`, `p=1` | 结构条件的择优取向/织构导致相对峰强系统变化 |
| 背景 | 三阶平滑多项式；`background_to_peak_ratio ~ U(0,0.02)`, `p=0.5` | GP 背景；ratio `0.02–0.05` | 样品、空气散射、荧光、基底与仪器等产生的平滑非负背景 |
| 计数/电子噪声 | Poisson–Gaussian；count scale `2500–40000`，电子噪声 `0–2 counts` | count scale `100–2500`，电子噪声 `0–5 counts` | 光子/计数统计与电子读出噪声；在归一化之前生成 |

**重要：** `apply_probability` 是训练数据生成策略超参数，不是“现实中该现象发生的真实概率”。这些参数定义的是一个文献锚定、物理合理、冻结的模拟扰动空间，而不是某一台具体仪器的经验误差分布。

## 2. 已经完成的文献证据链

早期项目曾建立逐条参数证据表，核心来源包括：

- **Szymanski et al. 2021**
- **SimXRD-4M 2025**
- **XQueryer 2025**
- **Salgado et al. 2023**
- **CPICANN 2024**
- **Lee et al. 2023**
- **Schopmans et al. 2023**
- 噪声模型还参考过 **Vecsei et al. 2019** 的相关实现/设定

当时的原则是：**理论/物理公式决定变化方式，文献给出合理数量级，代码核验具体生成方式，最终实验配置再以统一 frozen range 固定。**

下面只保留与当前五类扰动最直接的锚点。

| 当前扰动 | 已核验的代表性来源 | 原文/代码中的直接锚点 | 对当前配置的含义 |
|---|---|---|---|
| 全谱峰位偏移 | Szymanski 2021；SimXRD-4M 2025；XQueryer | Szymanski 的 uniform shift 可到约 `±0.5°`；SimXRD-4M 报告过约 `[-1.2,1.2]°` 的 global zero shift；XQueryer 保留同类全谱 offset 接口 | 当前 train `±0.2°` 属于更保守范围；OOD `0.2–0.5°` 仍处在已有 PXRD 模拟/扰动量级内 |
| 峰展宽 | Salgado 2023；Schopmans 2023；Szymanski 2021；CPICANN 2024 | Salgado 使用多组 Caglioti 参数；Schopmans 使用 Scherrer 晶粒尺度 `20–100 nm` 及 Caglioti `U/W`；Szymanski 报告过实验伪影中可达更宽的峰；CPICANN 也使用 grain-size broadening | 当前固定标量 FWHM 是工程代理，不冒充完整 Scherrer/Caglioti 仪器模型；`0.08–0.20°` 是保守训练区间，`0.20–0.35°` 是更强压力区间 |
| 背景 | Schopmans 2023；SimXRD-4M 2025；Lee 2023；CPICANN 2024 | Schopmans 使用 GP background；SimXRD-4M 报告 `background_ratio=0.02` 条件；Lee 使用随机高阶多项式背景；CPICANN 也设置背景条件 | 当前 train ratio `0–0.02` 与已有数值锚点同量级；OOD `0.02–0.05` 则作为更强背景压力 |
| 噪声 | Schopmans 2023；Salgado 2023；Szymanski 2021；Lee 2023；SimXRD-4M 2025 | Schopmans additive noise `std 0–0.02`（归一化强度）；Salgado 约 `0.2–2%`；Szymanski/Lee 常见 `1–5%` 量级；SimXRD-4M 报告 `0.02` whole-pattern noise 条件 | 这些文献主要锚定“实验噪声机制与数量级”；当前正式实现进一步改成 Poisson–Gaussian 计数模型，因此不应把旧百分比 sigma 与当前 count scale 做一一等价换算 |
| 择优取向 | Szymanski 2021；SimXRD-4M 2025；标准 March–Dollase 模型 | Szymanski 对相对峰强/texture 做过大幅度变化；SimXRD 显式包含 orientation variation；当前实现不做逐峰独立乱乘，而使用结构条件的 March–Dollase 晶面族模型 | 文献明确支持“择优取向是需要覆盖的 PXRD 测量/样品变化”；当前 `r=0.8–1.0` 与 OOD `0.5–0.8` 是冻结的工程参数化，不宣称是某台仪器统计得到的发生分布 |

## 3. 这套证据支持什么，不支持什么

它足以支持当前论文/汇报中的表述：

> 本项目在文献与 PXRD 物理机制支持下，构造峰位偏移、峰展宽、择优取向、背景和计数/电子噪声五类测量变化，并在统一冻结的训练范围和更强 OOD 范围内比较 Dynamic ERM 与 JS consistency。

它**不需要**被升级成以下更强主张：

- “这些分布精确拟合了某一台真实仪器”；
- “每个 `apply_probability` 是现实发生频率”；
- “固定标量 FWHM 等价于完整的 Scherrer/Caglioti 精修模型”；
- “March–Dollase 的当前 `r` 范围来自一套真实样本的大规模统计标定”。

这些更强表述不是当前科学结论成立的前提。

## 4. 为什么现在把它重新放到主分支

早期仓库里其实已经存在非常详细的逐参数证据表和五扰动源码对照，但后来为精简公开仓库被移出当前主线。这样会产生一个副作用：后续读者或 AI 只看到最终 frozen config，容易误以为参数缺乏来源，再次建议做一轮已经完成过的“扰动真实性调查”。

因此从现在起，本文件是当前主线的**canonical perturbation-evidence index**。未来写 Methods、PPT 或答辩时，应先引用本文件和最终 frozen config，而不是重新启动文献调查。

历史详细表仍可在 Git 历史中核对：

- [`literature_parameter_raw.csv`（历史快照）](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/xrd_robustness/reports/literature_parameter_raw.csv)
- [`V8_FIVE_PERTURBATION_COMPARISON.csv`（历史快照）](https://github.com/Frysland-2024/AI4science/blob/f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217/xrd_robustness/reports/V8_FIVE_PERTURBATION_COMPARISON.csv)

当前结果与当前参数仍分别以：

- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/configs/simulation.method_transfer.frozen.json`](../xrd_robustness/configs/simulation.method_transfer.frozen.json)

为准。