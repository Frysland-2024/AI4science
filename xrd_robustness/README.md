# XRD Robustness

本目录实现基于在线 PXRD 物理扰动的七晶系鲁棒分类。核心对比为 Dynamic ERM 与 Dynamic JS Consistency 两种方法；选定配置为 ResNet-18-GN、不做额外预处理、AdamW、恒定学习率、`lambda_js=60`。

## 结果

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

五组配对种子实验在两个数据集上均为正向提升。

结果文件：

- [`reports/RESULTS.md`](reports/RESULTS.md)
- [`reports/validation_results.json`](reports/validation_results.json)
- [`reports/simulated_test_results.json`](reports/simulated_test_results.json)

## 代码结构

| 路径 | 作用 |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN 骨干网络 |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM 与 JS 一致性目标 |
| `src/xrd_robustness/simulator.py` | PXRD 物理扰动模拟器 |
| `src/xrd_robustness/online_views.py` | 同一母体结构的配对在线视图 |
| `scripts/train.py` | ResNet Dynamic ERM/JS 训练脚本 |

## 安装与测试

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

## 文档

- [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)
- [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)
- [`MANUSCRIPT.md`](MANUSCRIPT.md)

数据集、模型权重、生成谱图、缓存和本地输出不进入 Git。
