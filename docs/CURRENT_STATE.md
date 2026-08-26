# AI4science 当前状态

**状态日期：** 2026-08-27

**阶段：** 模拟结果已确定，进入论文、图表与汇报成果封装阶段；实验真实域评测资产正在冻结（推理尚未运行）

## 1. 当前科学设计

当前已经完成的项目想回答一个问题：在线 PXRD 模拟器知道哪些谱图来自同一个母体结构，能不能把这种关系变成额外的监督信号，让七晶系分类器在测量条件变化时更稳。

最终确定的设计：

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency，一致性权重 `lambda_js=60`；
- 预处理：不做额外处理；
- 优化器：AdamW；
- 学习率：恒定；
- 划分：训练 9,842 / 验证 2,109 / 测试 2,109；
- 划分方式：按母体结构严格分开，训练/验证/测试不共享同一母体。

## 2. 已经做完的事

- 在验证集上跑完了五组配对实验；
- 在选好的模型上完成了模拟测试集评估；
- 固定了模型、数据、扰动、优化器和训练量；
- 把公开的结果和论文的说法统一了；
- 精简了公开文件，只留下训练、评估和核对结果需要的部分；
- 明确当前结果不再通过新增 loss、重新调参或重开训练改变。

## 3. 结果

| 指标 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | Δ `+0.046569`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | Δ `+0.054600`；5/5 为正 |

结果文件：

- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/reports/validation_results.json`](../xrd_robustness/reports/validation_results.json)
- [`../xrd_robustness/reports/simulated_test_results.json`](../xrd_robustness/reports/simulated_test_results.json)

## 4. 当前实现

主要实现：

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/scripts/train.py`](../xrd_robustness/scripts/train.py)

结果已经确定，不会再改。公开仓库里只留了当前实现、运行配置、结果和使用文档；`train.py` 是可复用的方法参考，分数看已有模型的评估结果文件。

这里说的"结果已经确定"指**模拟部分**（验证集、模拟测试集）。实验真实域（RRUFF-301、CNRS-318）的评测资产正在冻结，正式推理尚未运行，不包含在已确定结果之内。

## 5. 实验进度

方法对比、验证集和模拟测试集的评估都做完了，模拟部分的结果已经确定、不会再改。

实验真实域分两层：

- **RRUFF-301**：平衡、人工整理的实验真实域（balanced curated experimental domain）。
- **CNRS-318**：自然不平衡、跨数据库的独立实验真实域（naturally imbalanced independent experimental domain），已正式定级为第二真实域，保留自然类别分布 `21 / 87 / 77 / 41 / 33 / 12 / 47`。

两个真实域的评测资产正在冻结，**正式推理尚未运行**：

- CNRS-318 的权威审计与父样本 manifest 已进入 git（见 [`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) 和 [`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv)）；
- 评测协议已锁定（[`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md)）；
- 35 条人工标签质量复核尚未完成；
- 真实数据不参与模型、checkpoint、seed 或 `lambda_js` 选择。

## 6. 当前卡点

现在主要是把已有数字转化为清楚、可复述的成果：

- 生成五种扰动图、同源双视图方法图和配对结果图；
- 完成仿照“组会1”视觉语言的阶段汇报；
- 完成方法、结果和讨论正文；
- 确保公开结果、图表和讲稿中的数字完全一致。

## 7. 当前项目下一步

1. 从 `reports/validation_results.json` 和 `reports/simulated_test_results.json` 生成论文与 PPT 图表。
2. 完成方法、结果和讨论章节。
3. 跑一遍完整测试，确认接口、数据和实现都对得上。
4. 将组会 PPT、技术报告和一页项目摘要整理为申请可复用成果。
5. 完成 CNRS-318 的 35 条人工标签质量复核后，按冻结协议跑一次性真实域推理（RRUFF-301 与 CNRS-318）。

下一条工程检查命令：

```powershell
cd xrd_robustness
python -m pytest -q
```

## 8. 并行的下一项目规划（尚未启动）

在不改变当前分类项目的前提下，下一代项目已经正式收敛为：

> **已知相参考条件下的 PXRD 定量反演：从观测谱和名义参考谱中估计晶格与测量参数，并通过前向衍射和局部精修验证。**

第一版只计划做：

- 单相；
- 已知候选结构；
- 四方晶系；
- 晶胞尺度、四方畸变、零点偏移和峰宽；
- 同源双视图中的结构参数一致性；
- 分阶段加入前向物理一致性；
- 比较名义初始化与 ML 初始化后的相同局部精修。

相关文档：

- [`NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md)
- [`XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md`](XRD_QUANTITATIVE_INVERSION_RESOURCE_MANIFEST.md)
- [`PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md`](PROJECT_HISTORY_NOTE_2026-08-27_XRD_QUANTITATIVE_INVERSION.md)

该项目目前仅完成问题定义、边界收缩和执行规划。必须先完成四方结构数量审计与可辨识性 Gate，才创建 `xrd_inversion/` 代码目录并启动训练。
