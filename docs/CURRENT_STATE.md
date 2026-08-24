# AI4science 当前状态

**状态日期：** 2026-08-23

**阶段：** 结果已确定，进入论文和图表阶段

## 1. 当前科学设计

这个项目想回答一个问题：在线 PXRD 模拟器知道哪些谱图来自同一个母体结构，能不能把这种关系变成额外的监督信号，让七晶系分类器在测量条件变化时更稳。

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
- 精简了公开文件，只留下训练、评估和核对结果需要的部分。

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

## 5. 实验进度

方法对比、验证集和模拟测试集的评估都做完了。目前没有新的训练任务，这些结果就是论文用的最终结果。

## 6. 当前卡点

现在主要是做论文图表、结果和方法部分，同时确保三份公开结果里的数字完全一致。

## 7. 下一步

1. 从 `reports/validation_results.json` 和 `reports/simulated_test_results.json` 生成论文图表。
2. 完成方法、结果和讨论章节。
3. 跑一遍完整测试，确认接口、数据和实现都对得上。

下一条命令：

```powershell
cd xrd_robustness
python -m pytest -q
```
