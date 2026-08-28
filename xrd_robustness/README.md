# XRD 鲁棒性

这里做的是：用在线 PXRD 物理扰动做七晶系鲁棒分类。对比 Dynamic ERM 和 Dynamic JS Consistency 两种方法，配置是 ResNet-18-GN、不做额外预处理、AdamW、恒定学习率、`lambda_js=60`。

## 结果

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | `+0.054600`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | `+0.054454`；5/5 为正 |
| RRUFF-301 · K=1/2/5 few-shot Macro-F1 | 0.2847±0.0269 / 0.3026±0.0407 / 0.3555±0.0302 | 0.3280±0.0329 / 0.3486±0.0335 / 0.4099±0.0271 | `+0.0433 / +0.0460 / +0.0545` |
| RRUFF-301 · K=1/2/5 few-shot Accuracy | 0.2990±0.0259 / 0.3120±0.0383 / 0.3581±0.0273 | 0.3375±0.0299 / 0.3609±0.0343 / 0.4149±0.0252 | `+0.0384 / +0.0488 / +0.0568` |
| CNRS-318 · zero-shot pooled Macro-F1 | 0.19118 | 0.20912 | mean seed-paired `+0.01871`（约 `+1.87 pp`）；5/5 为正 |

模拟 OOD、RRUFF few-shot、CNRS zero-shot 与 calibration 形成一致证据链。CNRS-318 的 seed-level Macro-F1 为 `0.18837±0.02634→0.20708±0.02134`、配对提升 `+0.01871±0.00675`，且 5/5 seed 为正；它是独立实验来源上的 zero-shot 外推评测，不是用 CNRS 标签做域适配。Balanced accuracy、accuracy、ECE、NLL 与 Brier 也同向改善。自然不平衡和低支持类别使严格 paired-parent CI 较宽；CI 跨 0 作为不确定性说明保留，不再作为科研成败 Gate。

当前默认采用[三层评价体系](../docs/PXRD_RESULT_REPORTING_STANDARD.md)：community-standard performance 是主科学交流层，reliability 是增强证据层，strict statistical audit 是不确定性与可信度审计层。

结果文件：

- [`reports/RESULTS.md`](reports/RESULTS.md)
- [`reports/validation_results.json`](reports/validation_results.json)
- [`reports/simulated_test_results.json`](reports/simulated_test_results.json)
- [`reports/rruff301_fewshot_results.json`](reports/rruff301_fewshot_results.json)
- [`reports/CNRS_318_RESULTS.md`](reports/CNRS_318_RESULTS.md)
- [`reports/README.md`](reports/README.md)

## 代码结构

| 路径 | 作用 |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN 骨干网络 |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM 与 JS 一致性目标 |
| `src/xrd_robustness/simulator.py` | PXRD 物理扰动模拟器 |
| `src/xrd_robustness/online_views.py` | 同一母体结构的两份配对谱图 |
| `scripts/train.py` | 训练脚本（Dynamic ERM 与 JS 一致性） |
| `scripts/build_cnrs318_manifests.py` | 只读核验或显式重建 CNRS-318 冻结 manifests |
| `scripts/analyze_cnrs318_results.py` | 复核 CNRS 输入、预测、checkpoint、指标与 paired bootstrap |
| `scripts/build_cnrs318_audit_artifact.py` | 从审计 CSV/JSON 构建含四张核心图的便携技术报告 |

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
