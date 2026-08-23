# XRD Robustness

本目录实现基于在线 PXRD 物理扰动的七晶系鲁棒分类。冻结比较为 matched Dynamic ERM 与 Dynamic JS Consistency；选定配置为 ResNet-18-GN、identity preprocessing、AdamW、constant learning rate、`lambda_js=60`。

## Results

| Panel | Dynamic ERM | Dynamic JS | Paired improvement |
|---|---:|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| Simulated Test mean single-factor OOD Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

五组 matched seed pairs 在两个面板上均为正向提升。

结果入口：

- [`reports/RESULTS.md`](reports/RESULTS.md)
- [`reports/validation_results.json`](reports/validation_results.json)
- [`reports/simulated_test_results.json`](reports/simulated_test_results.json)

## Code map

| Path | Purpose |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN backbone |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM and JS objectives |
| `src/xrd_robustness/simulator.py` | PXRD physical perturbation simulator |
| `src/xrd_robustness/online_views.py` | deterministic paired online views |
| `scripts/train.py` | reference ResNet Dynamic ERM/JS trainer |

## Install and test

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

## Documentation

- [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)
- [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)
- [`MANUSCRIPT.md`](MANUSCRIPT.md)

数据集、模型权重、生成谱图、缓存和本地输出不进入 Git。
