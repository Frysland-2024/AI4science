# XRD 鲁棒性 — 当前交接

**状态日期：** 2026-08-23

**阶段：** 模拟结果已定型；正在写论文和图表

## 当前方法

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency；
- 一致性权重：`lambda_js=60`；
- 不做额外预处理、AdamW、恒定学习率；
- 训练 9,842 / 验证 2,109 / 测试 2,109；
- 按母体结构严格划分，训练/验证/测试不共享同一母体。

## 已完成结果

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

五组配对种子实验在两个数据集上均为正向提升。方法比较、验证集与模拟测试集评估均已完成。

## 结果文件

- [`reports/RESULTS.md`](reports/RESULTS.md)
- [`reports/validation_results.json`](reports/validation_results.json)
- [`reports/simulated_test_results.json`](reports/simulated_test_results.json)

## 主要实现

| 路径 | 作用 |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN 骨干网络 |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM 与 JS 一致性目标 |
| `src/xrd_robustness/simulator.py` | PXRD 扰动模拟器 |
| `src/xrd_robustness/online_views.py` | 配对在线视图生成 |
| `scripts/train.py` | 训练脚本（Dynamic ERM 与 JS 一致性） |

## 当前工作

现有实验结果保持固定。当前在做：

1. 从两份结果文件生成论文图表；
2. 完成方法、结果和讨论章节；
3. 保持公开文档中的方法与数值一致；
4. 运行完整测试确认当前实现。

## 验证

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

## 当前阻塞与下一条命令

当前重点是论文图表与正文。下一条命令：

```powershell
python -m pytest -q
```

完整状态见 [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)。
