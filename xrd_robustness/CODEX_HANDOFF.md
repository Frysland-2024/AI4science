# XRD Robustness — Current Handoff

**Status date:** 2026-08-23

**Mode:** frozen simulated results; manuscript and figure construction

## Current method

- task：7-class crystal-system classification；
- backbone：ResNet-18-GN；
- baseline：Dynamic ERM；
- selected method：Dynamic JS Consistency；
- `lambda_js=60`；
- identity preprocessing、AdamW、constant learning rate；
- Train 9,842 / Validation 2,109 / Test 2,109；
- exact-parent-disjoint split identity。

## Completed results

| Panel | Dynamic ERM | Dynamic JS | Paired improvement |
|---|---:|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| Simulated Test mean single-factor OOD Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

五组 matched seed pairs 在两个面板上均为正向提升。方法比较、Validation replication 与 simulated Test 已完成。

## Result files

- [`reports/RESULTS.md`](reports/RESULTS.md)
- [`reports/validation_results.json`](reports/validation_results.json)
- [`reports/simulated_test_results.json`](reports/simulated_test_results.json)

## Active implementation

| Path | Role |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN backbone |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM and JS objectives |
| `src/xrd_robustness/simulator.py` | PXRD perturbation simulator |
| `src/xrd_robustness/online_views.py` | paired online view generation |
| `scripts/train.py` | reference ResNet Dynamic ERM/JS trainer |

## Current work

现有实验结果保持固定。当前工作聚焦：

1. 从两份机器可读结果生成论文图表；
2. 完成 Methods、Results 和 Discussion；
3. 保持公开文档中的方法与数值一致；
4. 运行完整测试确认当前实现。

## Verification

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

## Current blocker and next command

当前工作重点是论文图表与正文尚待完成。下一条命令：

```powershell
python -m pytest -q
```

完整状态见 [`../00_project_context/CURRENT_STATE.md`](../00_project_context/CURRENT_STATE.md)。
