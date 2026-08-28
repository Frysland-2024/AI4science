# XRD 鲁棒性

这里做的是：用在线 PXRD 物理扰动做七晶系鲁棒分类。对比 Dynamic ERM 和 Dynamic JS Consistency 两种方法，配置是 ResNet-18-GN、不做额外预处理、AdamW、恒定学习率、`lambda_js=60`。

> **先看五类扰动依据：** [`../docs/PXRD_PERTURBATION_EVIDENCE.md`](../docs/PXRD_PERTURBATION_EVIDENCE.md)。峰位偏移、展宽、择优取向、背景和噪声的文献/物理证据早期已经系统核过；该文件把历史证据、最终 frozen range 与解释边界重新集中到当前主线，避免把这件事误判为新的科研 TODO。

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

## RRUFF-301 组成只读检查

为了把 few-shot 数据组成讲得更清楚，仓库提供 [`scripts/audit_rruff301_composition.py`](scripts/audit_rruff301_composition.py)。它只读取本地已经存在的 `rruff371_master_manifest.csv`、`rruff301_adaptation_test_split.csv` 和规范化谱图，检查：

- adaptation pool 与 locked test 的 RRUFF ID / spectrum SHA 是否重合；
- `mineral_name`、`ideal_chemistry`、`measured_chemistry`、`space_group` 的精确规范化字符串重合；
- 70×231 个跨 split 谱图对的 Pearson 相似度，以及 `0.95 / 0.98 / 0.995` 三个描述性阈值。

这项检查**不是新的实验 Gate**，不会改变 split、删除样本、读取模型预测或重跑结果。相同 mineral / chemistry 的存在也不自动构成数据泄漏，因为当前 RRUFF-301 的用途是同一实验域内的 few-shot adaptation，而不是 unseen-mineral benchmark。

在本地 `xrd_robustness/` 目录运行：

```powershell
python scripts/audit_rruff301_composition.py
```

默认输出 `reports/RRUFF301_COMPOSITION_AUDIT.md` 和 `.json`。如果只想先看 metadata、不读取谱图，可加 `--skip-spectra`。

## 结果与证据索引

| 文件 | 作用 |
|---|---|
| [`../docs/PXRD_PERTURBATION_EVIDENCE.md`](../docs/PXRD_PERTURBATION_EVIDENCE.md) | **五类扰动的物理/文献依据、最终范围与历史详细证据入口** |
| [`reports/RESULTS.md`](reports/RESULTS.md) | 跨域 headline performance、reliability 与严格 audit 摘要 |
| [`reports/validation_results.json`](reports/validation_results.json) | 冻结模拟验证集汇总 |
| [`reports/simulated_test_results.json`](reports/simulated_test_results.json) | 冻结模拟 Test 汇总及 SHA 绑定的 Accuracy 扩展 |
| [`reports/rruff301_fewshot_results.json`](reports/rruff301_fewshot_results.json) | RRUFF-301 K=1/2/5 汇总与结果说明 |
| [`reports/CNRS_318_RESULTS.md`](reports/CNRS_318_RESULTS.md) | CNRS-318 完成结果、完整性审计与 paired bootstrap |
| [`reports/CALIBRATION_ANALYSIS.md`](reports/CALIBRATION_ANALYSIS.md) | 模拟 Test 与 CNRS 的概率可靠性分析 |
| [`reports/CNRS_318_DATASET_AUDIT.md`](reports/CNRS_318_DATASET_AUDIT.md) | CNRS 数据构建与角色审计 |
| [`reports/CNRS_318_EVALUATION_PROTOCOL.md`](reports/CNRS_318_EVALUATION_PROTOCOL.md) | 原样保留的 pre-run 冻结协议 |
| [`configs/real.cnrs318.zero_shot.frozen.json`](configs/real.cnrs318.zero_shot.frozen.json) | 冻结配置 |
| [`manifests/cnrs318_zero_shot_run_record.json`](manifests/cnrs318_zero_shot_run_record.json) | 完成执行、哈希与修正结果绑定 |

[`reports/opxrd_cnrs7cs_independent_parent_audit_20260827.md`](reports/opxrd_cnrs7cs_independent_parent_audit_20260827.md) 是保留的历史审计快照；其 317-parent 结论已被重复代表选择修正后的 318-parent 结果取代，不能当作当前结论。

## 代码结构

| 路径 | 作用 |
|---|---|
| `src/xrd_robustness/models/ml4pxrd_resnet1d.py` | ResNet-18-GN 骨干网络 |
| `src/xrd_robustness/training/objectives.py` | Dynamic ERM 与 JS 一致性目标 |
| `src/xrd_robustness/simulator.py` | PXRD 物理扰动模拟器 |
| `src/xrd_robustness/online_views.py` | 同一母体结构的两份配对谱图 |
| `src/xrd_robustness/training/runner.py` / `xrd-train` | Dynamic ERM 与 JS 一致性训练入口 |
| `scripts/audit_rruff301_composition.py` | 只读检查 RRUFF-301 adaptation/test 的 metadata 与谱图相似度组成 |
| `scripts/build_cnrs318_manifests.py` | 只读核验或显式重建 CNRS-318 冻结 manifests |
| `scripts/analyze_cnrs318_results.py` | 复核 CNRS 输入、预测、checkpoint、指标与 paired bootstrap |
| `scripts/build_cnrs318_audit_artifact.py` | 从审计 CSV/JSON 构建含四张核心图的便携技术报告 |

## 安装与测试

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
```

`pytest` 用于检查实现、接口、配置和公开结果文件之间的一致性，不会重新训练模型或复现论文中的完整训练结果。

本地重建 CNRS 审计包时，在本目录运行：

```powershell
python scripts/analyze_cnrs318_results.py
python scripts/build_cnrs318_audit_artifact.py
```

生成的 `outputs/cnrs318_zero_shot/audit/` 被 Git 忽略；其中包含 machine-readable summary、修正 bootstrap、逐 seed/逐类 CSV 和便携报告。原始 3,180 行预测与 `318 × 3501` 输入仍受 run record 的 SHA-256 绑定，不得移动或删除。

## 文档

- [`../docs/CURRENT_STATE.md`](../docs/CURRENT_STATE.md)
- [`../docs/PXRD_PERTURBATION_EVIDENCE.md`](../docs/PXRD_PERTURBATION_EVIDENCE.md)
- [`MANUSCRIPT.md`](MANUSCRIPT.md)

数据集、模型权重、生成的谱图、缓存和本地输出都不会提交到 Git。
