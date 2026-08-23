# AI4science Current State

**Status date:** 2026-08-23

**Phase:** frozen results → manuscript and figure construction

## 1. Current scientific design

本研究问在线 PXRD 模拟器提供的同源结构关系能否转化为额外监督，从而提升七晶系分类器在模拟测量变化下的鲁棒性。

冻结设计：

- task：7-class crystal-system classification；
- backbone：ResNet-18-GN；
- baseline：Dynamic ERM；
- selected method：Dynamic JS Consistency，`lambda_js=60`；
- preprocessing：identity；
- optimizer：AdamW；
- schedule：constant learning rate；
- split：Train 9,842 / Validation 2,109 / Test 2,109；
- split identity：exact-parent-disjoint。

## 2. Completed work

- 完成五组 matched training-seed pairs 的 Validation 比较；
- 完成已选 checkpoint 的 frozen simulated Test；
- 固定模型、数据暴露、扰动分布、优化器和训练预算；
- 统一公开结果入口与论文叙事；
- 将公开文件树收束为方法训练、模拟评估和结果核验所需实现。

## 3. Frozen results

| Evidence | Dynamic ERM | Dynamic JS | Paired result |
|---|---:|---:|---:|
| Validation mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | Δ `+0.046569`; 5/5 positive |
| Simulated Test mean single-factor OOD Macro-F1 | 0.65074 | 0.70534 | Δ `+0.054600`; 5/5 positive |

结果入口：

- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/reports/validation_results.json`](../xrd_robustness/reports/validation_results.json)
- [`../xrd_robustness/reports/simulated_test_results.json`](../xrd_robustness/reports/simulated_test_results.json)

## 4. Current engineering state

主要实现入口：

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/scripts/train.py`](../xrd_robustness/scripts/train.py)

冻结结果保持只读。公开发布范围仅包含当前实现、运行配置、正向结果与使用文档；`train.py` 提供可复用的方法参考实现，冻结分数以既有 checkpoint 的公开评估入口和结果文件为准。

## 5. Experiment status

方法比较、Validation replication 和 simulated Test 均已完成。当前没有计划内训练任务；现有结果作为论文版本的固定输入。

## 6. Current blocker

当前工作重点是完成论文图表、结果段落和方法描述，并确保三份公开结果入口中的数值完全一致。

## 7. Next actions

1. 从 `reports/validation_results.json` 和 `reports/simulated_test_results.json` 生成论文图表。
2. 完成 Methods、Results 和 Discussion 正文。
3. 运行完整测试，确认公开入口、数据合同与核心实现一致。

下一条命令：

```powershell
cd xrd_robustness
python -m pytest -q
```
