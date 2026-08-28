# AI4Science

这个仓库主要做 XRD 鲁棒性研究，代码在 [`xrd_robustness/`](xrd_robustness/)。核心想法是：在线 PXRD 模拟器知道哪些谱图来自同一个母体结构，把这个关系变成一种监督信号，让七晶系分类器在测量条件变化时更稳。

> 状态（2026-08-29）：模拟结果、RRUFF-301 few-shot 与 CNRS-318 zero-shot 已完成；当前在做论文、图表与成果封装。

> **本轮两个证据问题已经结案。** 五类扰动的物理/文献依据已经完成系统核验；RRUFF-301 composition audit 也确认 adaptation/test 之间无 RRUFF ID 或相同谱图重合，16,170 个跨 split 谱图对中无 Pearson ≥ 0.95。结案结果与当前方法新颖性 framing 统一见 [`docs/PXRD_EVIDENCE_CLOSURE.md`](docs/PXRD_EVIDENCE_CLOSURE.md)。

> **五个方法细节问题也已完成本地仓库/Git 历史考古并结案。** Related Work 边界、ERM–JS 公平对照、formal_14060 数据集构建、五类扰动是否保持 parent structure 不变、以及 `lambda_js=60` 的选择路径，统一见 [`docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`](docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md)。这些不是新的实验 TODO；后续直接用于 Methods、Related Work、PPT 和答辩。

> **当前最重要的写作任务不是补实验或加算法，而是把方法贡献讲清楚：**传统 online simulator 主要是 `data generator`；本项目进一步利用 simulator-retained parent identity，把同一晶体的不同测量 realization 定义为 measurement-equivalent views，从而让 simulator 同时成为 **data generator + relationship supervisor**。

## 一眼看懂这个项目

```text
同一个母体晶体结构
      ↓ 在线物理扰动
两份不同测量条件下的 PXRD 谱图
      ↓
shared parent identity
      ↓
measurement equivalence
      ↓
Dynamic ERM：只使用共同晶系标签
Dynamic JS：共同标签 + measurement-equivalence consistency
      ↓
更稳定的分布外泛化
```

## 研究结果

在 ResNet-18-GN 上对比了 Dynamic ERM 和 Dynamic JS Consistency 两种方法，一致性权重 `lambda_js=60`。

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | `+0.054600`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | `+0.054454`；5/5 为正 |
| RRUFF-301 · K=1/2/5 few-shot Macro-F1 | 0.2847±0.0269 / 0.3026±0.0407 / 0.3555±0.0302 | 0.3280±0.0329 / 0.3486±0.0335 / 0.4099±0.0271 | `+0.0433 / +0.0460 / +0.0545` |
| RRUFF-301 · K=1/2/5 few-shot Accuracy | 0.2990±0.0259 / 0.3120±0.0383 / 0.3581±0.0273 | 0.3375±0.0299 / 0.3609±0.0343 / 0.4149±0.0252 | `+0.0384 / +0.0488 / +0.0568` |
| CNRS-318 · zero-shot pooled Macro-F1 | 0.19118 | 0.20912 | mean seed-paired `+0.01871`（约 `+1.87 pp`）；5/5 为正 |

模拟 OOD 的 5/5 seed、RRUFF 的三档 few-shot label budget、CNRS 的 5/5 seed 与概率可靠性结果共同支持 JS 学到更稳健的模型。CNRS 的 seed-level Macro-F1 为 `0.18837±0.02634→0.20708±0.02134`，配对提升 `+0.01871±0.00675`；它是自然不平衡的第二实验来源上的 zero-shot 压力测试，不是使用 CNRS 标签做过域适配。其 pooled balanced accuracy `0.2182→0.2388`、accuracy `0.2000→0.2101`、ECE `0.6826→0.6124` 也同向改善，但绝对 sim-to-real 表现仍弱。

当前评价采用三层证据体系：社区常用 performance 指标承担主科学叙事；ECE/NLL/Brier 等 reliability 指标作为增强证据；paired/class-stratified parent bootstrap、95% CI 和逐类不确定性作为严格统计审计。CNRS 的修正后 95% CI `[−0.009339, +0.046107]` 如实保留，但 CI 跨 0 只表示效应估计仍不确定，不再单独充当科研成败 Gate。详见 [`docs/PXRD_RESULT_REPORTING_STANDARD.md`](docs/PXRD_RESULT_REPORTING_STANDARD.md)。

## 文档

| 文件 | 用途 |
|---|---|
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | 项目现状、进度和下一步 |
| [`docs/PXRD_EVIDENCE_CLOSURE.md`](docs/PXRD_EVIDENCE_CLOSURE.md) | **本轮两个证据问题的结案结果 + measurement-equivalence / relationship-supervision 新颖性 framing** |
| [`docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md`](docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md) | **五个方法细节问题的仓库考古结案：Related Work、公平对照、formal_14060、structure-preserving 扰动、λ=60 选择历史** |
| [`docs/PXRD_PERTURBATION_EVIDENCE.md`](docs/PXRD_PERTURBATION_EVIDENCE.md) | 五类扰动的物理/文献依据、最终冻结范围与历史详细证据入口 |
| [`docs/PXRD_RESULT_REPORTING_STANDARD.md`](docs/PXRD_RESULT_REPORTING_STANDARD.md) | 当前三层评价体系与各域默认汇报模板 |
| [`docs/GRADUATE_RESEARCH_DIRECTION.md`](docs/GRADUATE_RESEARCH_DIRECTION.md) | 申请叙事、研究方向框架、方向地图与日本导师检索关键词 |
| [`docs/NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`](docs/NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md) | 下一代定量反演计划及论文、代码、数据资源附录 |
| [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) | 完整研究演化档案；含日期化决策节点、失败、版本变化和评价体系修正 |
| [`docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md`](docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md) | 冻结 CNRS 协议所链接的独立历史节点 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 安装、代码结构与结果/证据索引 |
| [`xrd_robustness/MANUSCRIPT.md`](xrd_robustness/MANUSCRIPT.md) | 论文正文框架 |
| [`xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`](xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md) | RRUFF-301 adaptation/test 的只读组成与近重复谱检查 |
| [`xrd_robustness/reports/RESULTS.md`](xrd_robustness/reports/RESULTS.md) | 结果汇总 |
| [`xrd_robustness/reports/CNRS_318_RESULTS.md`](xrd_robustness/reports/CNRS_318_RESULTS.md) | CNRS-318 zero-shot 结果、完整性审计与修正后的 paired bootstrap |
| [`xrd_robustness/reports/CALIBRATION_ANALYSIS.md`](xrd_robustness/reports/CALIBRATION_ANALYSIS.md) | 模拟 Test 与 CNRS 概率可靠性分析 |
| [`xrd_robustness/reports/validation_results.json`](xrd_robustness/reports/validation_results.json) | 验证集结果（JSON） |
| [`xrd_robustness/reports/simulated_test_results.json`](xrd_robustness/reports/simulated_test_results.json) | 测试集结果（JSON） |
| [`xrd_robustness/reports/rruff301_fewshot_results.json`](xrd_robustness/reports/rruff301_fewshot_results.json) | RRUFF-301 few-shot 机器可读汇总 |

建议先读 `CURRENT_STATE.md`、`PXRD_EVIDENCE_CLOSURE.md`、`PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md` 和 `RESULTS.md`；需要扰动参数依据时再看 `PXRD_PERTURBATION_EVIDENCE.md`，只有追溯旧判断、失败实验或方法转变时才查 `PROJECT_HISTORY.md`。当前科学说法以当前状态、结案文档、评价规范和结果文件为准，历史档案不覆盖当前结论。

## 快速验证

```powershell
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q
```

这里的 `pytest` 用来核对实现、接口、配置和公开结果文件之间是否一致；它不会重新训练模型，也不会复现论文中的完整训练结果。数据集、模型权重、生成的谱图、虚拟环境、文献和本地输出都不会提交到 Git。
