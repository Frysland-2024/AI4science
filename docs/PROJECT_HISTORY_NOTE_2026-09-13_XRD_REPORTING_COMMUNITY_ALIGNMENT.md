# 项目发展记录：PXRD 汇报标准二次瘦身与社区范式对齐

**日期：** 2026-09-13  
**性质：** 项目表达与评价标准修正，不改变任何冻结实验结果。

## 决策

在复核 Oviedo 2019、Lee 2023、Schopmans 2023 等代表性 XRD/PXRD 机器学习论文后，项目决定进一步区分“XRD 科学结果”“论文 Methods 参数”和“内部 AI 工程审计”。

### 正式汇报只保留 Tier A + Tier B

- Accuracy / top-1 Accuracy；
- Macro-F1；
- 天然不平衡实验域的 Balanced Accuracy；
- absolute performance + percentage-point change；
- profile-wise XRD perturbation performance；
- per-class F1 / recall / support、confusion matrix；
- RRUFF few-shot learning curve / label efficiency；
- mean ± SD、matched-seed direction、representative failure analysis 等支持结果；
- 概率质量指标只在必要时作为支持性结果。

### Tier C + Tier D 默认只保存在 JSON / CSV / audit / config / log

不再进入常规导师汇报、PPT 主结果页或论文 Results 主表：

- bootstrap CI / p-value / uncertainty decomposition；
- V6/V7/V9 版本考古；
- gradient gate / gradient norm / gradient ratio；
- fused AdamW、AMP、bfloat16 fallback；
- batch-tail filling、step count、exact stop epoch；
- hash / manifest / checkpoint SHA / exact seed IDs 等 provenance。

## Tier D 中哪些内容仍进入正式文档

参考 XRD-ML 社区惯例，必要复现参数不是“结果”，而是 **Methods / Experimental / Data preparation**：

1. **XRD/模拟条件**：2θ 范围、step size、wavelength、normalization / resampling；
2. **数据条件**：数据来源、筛选、split unit 和 train/validation/test 规模；
3. **物理增广条件**：peak shift、broadening、preferred orientation、background、noise 的模型与范围；
4. **方法定义**：backbone 简述、same-parent two-view design、JS objective、最终 λ_JS；
5. **训练设置**：optimizer、learning rate、batch size、epochs、early stopping 仅以紧凑 Methods 表说明。

其中 2θ step 等参数只有在论文**主动研究其科学/实验权衡**时才升级成 Results。例如 Oviedo 2019 专门研究 step size 对采集时间与 Accuracy 的影响，因此 step size 在那一实验中成为结果变量；本项目固定 0.02° 时，它只是 Methods 参数。

Lee 2023 也将 2θ range/interval、数据筛选与 perturbation generation 放在 Experimental Section，而 hyperparameter optimization 细节放 Supporting Information。Schopmans 2023 把 wavelength、simulation、split 与 online-training setup 放在 Methods/ESI；batch/epoch 数之所以较突出，是因为生成的独特衍射谱规模本身属于其 online-generation 研究问题。

## 对技术备忘录的直接修改

`docs/XRD_技术细节备忘录_彻底重写版.md` 已二次瘦身为 XRD-ML 社区范式：

- 删除 worst-class F1 与 bootstrap CI；
- 删除梯度 Gate 与 λ 梯度尺度考古；
- 删除 V6/V7/V9 历史考古；
- 删除 fused AdamW、AMP/bfloat16、batch 补齐、step count、stop epoch 等运行工程细节；
- 保留 XRD forward model、物理扰动、数据/split 与最小训练配置作为 Methods；
- Results 主体只保留模拟 Test Accuracy/Macro-F1、RRUFF few-shot、CNRS Macro-F1/Balanced Accuracy/Accuracy 与逐类行为。

## 项目发展意义

这次修正的核心不是“降低严谨性”，而是纠正过去用通用 AI/ML 审计范式评价材料 XRD 工作的惯性：

> **项目内部可以保存远比论文更多的统计与工程信息，但正式科学评价必须优先回答 XRD 社区真正关心的问题——分类是否准确、实验谱是否可用、物理扰动下是否稳健、哪些晶系仍然容易错。**

该决策不修改任何 raw output、frozen checkpoint 或历史实验协议，只改变正式报告的信息层级与呈现方式。
