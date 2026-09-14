# 项目发展节点：PXRD robustness 的 80/20 双人切分

**日期：** 2026-09-01  
**状态：** 正式记录为内部项目分工与后续申请叙事边界。  
**详细方案：** [`PXRD_ROBUSTNESS_TEAM_DIVISION_80_20.md`](PXRD_ROBUSTNESS_TEAM_DIVISION_80_20.md)

## 1. 为什么需要重新切分

当前 PXRD robustness 项目已经完成主方法与主要证据链：

- Dynamic ERM / Dynamic JS matched comparison；
- 5-seed simulated Validation / Test；
- RRUFF-301 K=1/2/5 few-shot adaptation；
- CNRS-318 zero-shot external evaluation；
- calibration / reliability 分析；
- novelty framing 已收敛为 `shared parent identity -> measurement equivalence -> relationship supervision`。

因此，不再适合为了给协作者制造工作量而重新打开新算法、新 loss 或新数据域。

新的目标是：

> **把已有项目自然拆成约 80% 的方法主线与约 20% 的真实域低标签迁移模块，使协作者拥有独立科学问题，但不稀释主 novelty。**

## 2. 最终选择的切法

主负责人约 75–80%：

> **Provenance-Aware Measurement-Equivalence Supervision**

负责：

- simulator / physical perturbation；
- parent-level dataset governance；
- Dynamic ERM / Dynamic JS；
- `lambda_js=60` 选择；
- 5-seed simulated OOD；
- CNRS zero-shot 与 calibration；
- novelty / manuscript 主线。

协作者约 20–25%：

> **Experimental Few-Shot Adaptation & Label Efficiency on RRUFF-301**

负责：

- RRUFF-301 adaptation / locked-test 数据角色；
- composition / near-duplicate audit；
- K=1/2/5 matched CE adaptation；
- ERM-pretrained vs JS-pretrained representation comparison；
- learning curve / label-efficiency analysis；
- RRUFF-specific figures and subsection writing。

## 3. 为什么 RRUFF few-shot 是最合适的 20%

它有一个可以独立讲清楚的问题：

> **模拟预训练得到的鲁棒表示，到了实验 PXRD 后，是否需要更少真实标签才能完成适配？**

它依赖主负责人的 frozen pretrained models，但这属于正常的：

```text
representation learning
        ->
downstream transfer / adaptation
```

关系。

协作者可以独立讲 transfer learning / few-shot scientific data，而不需要声称自己提出了 JS 或 simulator-provenance supervision。

当前结果也足以支撑这一故事：RRUFF-301 在 K=1/2/5 下，JS 初始化相对 ERM 初始化的 Macro-F1 提升约为 `+0.0433 / +0.0460 / +0.0545`，三档真实标签预算均保持正向。

## 4. 明确没有采用的切法

没有把 simulator / physical perturbation 主体切给协作者，因为：

```text
online simulator
  -> parent provenance
  -> measurement equivalence
  -> relationship supervision
```

正是当前方法创新的逻辑地基。

没有单独把 CNRS-318 当作 20% 主模块，因为它更适合作为主方法的 independent zero-shot stress test，独立叙事完整度低于 RRUFF few-shot adaptation。

也没有为了凑贡献增加：

- 新 loss；
- Residual；
- 新 backbone；
- 新真实域；
- 新的 simulator benchmark。

## 5. 最终申请叙事边界

主负责人：

> 从科学模拟器的生成机制中发现未利用的 parent-provenance relation，并把它转化为 measurement-equivalence supervision，研究更稳健的科学信号表示学习。

协作者：

> 研究 simulation-pretrained representations 在真实 PXRD 下的 low-label transfer，设计并评估 RRUFF-301 K-shot adaptation 与 label-efficiency learning curve。

两条故事彼此连接，但问题定义、主要实验和结论边界不同。

## 6. 记录原则

该 80/20 比例只作为当前内部项目管理与申请叙事规划，不机械替代最终 authorship / CRediT statement。最终贡献声明必须按实际完成工作如实调整。
