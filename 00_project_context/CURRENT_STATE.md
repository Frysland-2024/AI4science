# AI4science Current State

**Status date:** 2026-08-23

**阶段：** 结果已定型 → 论文与图表制作

## 1. 当前科学设计

本研究探究在线 PXRD 模拟器提供的同源结构关系能否转化为额外监督，从而提升七晶系分类器在模拟测量变化下的鲁棒性。

已定型的设计：

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency，一致性权重 `lambda_js=60`；
- 预处理：不做额外处理；
- 优化器：AdamW；
- 学习率：恒定；
- 划分：训练 9,842 / 验证 2,109 / 测试 2,109；
- 划分方式：按母体结构严格隔离，训练/验证/测试不共享同一母体。

## 2. 已完成工作

- 完成五组配对种子实验的验证集比较；
- 在已选模型上完成模拟测试集评估；
- 固定模型、数据使用、扰动分布、优化器和训练预算；
- 统一公开结果与论文叙事；
- 精简公开文件，只保留方法训练、模拟评估和结果核验所需的部分。

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

结果已经定型，不再改动。公开仓库只保留当前实现、运行配置、正向结果与使用文档；`train.py` 提供可复用的方法参考实现，分数以既有模型的评估结果文件为准。

## 5. 实验状态

方法比较、验证集与模拟测试集评估均已完成。当前没有计划内训练任务；现有结果作为论文版本的固定输入。

## 6. 当前阻塞

当前重点是完成论文图表、结果段落和方法描述，并确保三份公开结果中的数值完全一致。

## 7. 下一步

1. 从 `reports/validation_results.json` 和 `reports/simulated_test_results.json` 生成论文图表。
2. 完成 Methods、Results 和 Discussion 正文。
3. 运行完整测试，确认公开接口、数据约定与核心实现一致。

下一条命令：

```powershell
cd xrd_robustness
python -m pytest -q
```
