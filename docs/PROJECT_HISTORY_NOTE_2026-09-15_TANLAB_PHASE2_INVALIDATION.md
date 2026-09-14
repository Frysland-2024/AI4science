# 2026-09-15 · Tan Lab Phase-2 exploratory pilot 作废记录

## 决策

**状态：INVALID / ARCHIVED / NOT EVIDENCE**

2026-09-15 决定：本次基于谭启组历史 XRD 数据开展的 Tan Lab Phase-2 exploratory pilot **全部作废**，不再作为当前项目的实验结果、科学证据、PPT 内容、论文结果或申请材料依据，也不在现有结果基础上继续修补。

本决定只针对**本次实验设计及其衍生结果**，不否定谭启组原始 XRD 数据本身的潜在价值。

## 作废范围

本次 pilot 的以下内容均视为无效科研结果：

- 无监督聚类及 K=4 分组；
- 基于簇均值谱的自动判相与 `single-phase / multiphase` 推断；
- JS / ERM 在 59 条组内真实谱上的 embedding 可视化与 cluster-separability 比较；
- 由上述流程生成的概率输出、PCA、cluster assignment、phase verdict、peak-identification 图等全部衍生结果；
- 当前 `xrd_robustness/scripts/tanlab_phase2/` 下 4 个脚本仅保留为失败 pilot 的历史代码，不属于当前可复用实验管线。

## 作废原因

这次停止不是因为结果“不好看”，而是因为实验协议本身不足以支持原本想回答的科学问题。

1. **任务定义尚未成立。** 现有历史数据混合了不同材料体系、重复扫描、top / bottom、depolarized、粉末 / 陶瓷等条件，独立 `parent sample` 尚未定义清楚；`59 files` 不能等价为 `59 independent samples`。
2. **聚类实现存在方法问题。** 当前脚本先构造完整相关系数距离矩阵，再直接把二维矩阵传给 `scipy.cluster.hierarchy.linkage`。这会把距离矩阵当 observation matrix，而不是 condensed pairwise distance，因而现有 K=4 聚类结果不应继续使用。
3. **自动判相规则过粗。** 当前规则固定使用伪立方钙钛矿 `a=4.04 Å`、烧绿石 `a=10.4 Å`、固定峰位容差和局部峰分裂启发式，并在 cluster mean spectrum 上做判断，无法作为多个不同材料体系的可靠 ground truth。
4. **主线模型输入适配不物理。** 原始统一谱为 `20–80°`，embedding 脚本为了适配主线 `10–80° / 3501` 输入使用 `np.interp` 对 `10–20°` 区间做边界外推，产生并不存在的平坦输入段。
5. **embedding 评价存在循环性。** 先由 raw spectrum 聚出簇，再用这些簇评价 JS / ERM embedding 的“cluster separability”，最多只能说明模型是否复现 raw-spectrum clustering，不能证明模型更理解物相或结构状态。
6. **证据强度不足。** JS / ERM 对比只使用单一 seed / checkpoint，且没有独立可靠标签，因此不能作为主线真实域结论。

## 对当前项目的影响

**主线不受影响。** 当前已经完成并保留的证据仍然是：

- simulated OOD：Dynamic JS 相对 Dynamic ERM 的冻结 Test 改善；
- RRUFF-301：K=1/2/5 few-shot adaptation；
- CNRS-318：frozen-model zero-shot external evaluation；
- 以及随后独立完成的 CNRS sim-to-real representation diagnostic。

Tan Lab Phase-2 不再承担“补第三真实域”或“证明 single-phase / multiphase few-shot”的义务。

## 后续状态

**Tan Lab Phase-2：FROZEN / NO-GO FOR NOW。**

当前不再主动从无标签历史谱中挖任务，不重新聚类，也不继续调模型。只有在未来能够同时满足以下条件时才考虑重新开启：

- 样品身份与重复扫描关系明确；
- 独立 `parent sample` 可定义；
- 相态 / 结构标签来自可靠实验记录、Rietveld / 相分析或等价的可信来源；
- 科学任务先于模型确定，而不是先聚类再给簇找解释。

## 项目发展意义

这次失败保留一个重要的方法论修正：

> **真实实验室数据并不会因为“真实”就自动成为好 benchmark。数据必须先服务于一个定义清楚、可验证的科学问题。**

本次 pilot 暴露出：在缺少可靠标签和 parent 关系的情况下，无监督聚类很容易把材料体系、表面 / 取向、测量状态和处理条件混入“类别”解释。因此项目选择主动停止，而不是在不成立的问题定义上继续堆模型。

## 优先级覆盖说明

本记录**覆盖并更新**旧历史文件中关于以下内容仍为当前活动路线的表述：

- `GTIIT / Tan Lab perovskite functional-ceramic XRD domain`；
- `few-shot phase-state recognition (single-phase / multiphase)`。

这些内容现在仅保留为历史设想，不再属于当前执行路线。