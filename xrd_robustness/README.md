# XRD 鲁棒性

这里做的是：用在线 PXRD 物理扰动做七晶系鲁棒分类。对比 Dynamic ERM 和 Dynamic JS Consistency 两种方法，配置是 ResNet-18-GN、不做额外预处理、AdamW、恒定学习率、`lambda_js=60`。

## 结果

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

两个数据集上，五组配对实验都有提升。

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
| `src/xrd_robustness/online_views.py` | 同一母体结构的两份配对谱图 |
| `scripts/train.py` | 训练脚本（Dynamic ERM 与 JS 一致性） |

## 安装与测试

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

`pytest` 用于检查实现、接口、配置和公开结果文件之间的一致性，不会重新训练模型或复现论文中的完整训练结果。

## 文档

- [`../docs/CURRENT_STATE.md`](../docs/CURRENT_STATE.md)
- [`MANUSCRIPT.md`](MANUSCRIPT.md)

数据集、模型权重、生成的谱图、缓存和本地输出都不会提交到 Git。
