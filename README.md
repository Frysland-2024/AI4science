# AI4Science

本仓库的当前研究主线位于 [`xrd_robustness/`](xrd_robustness/)：利用在线 PXRD 模拟器，把同一母体结构生成的两份配对谱图转化为测量等价性监督，用于七晶系分类。

> 状态（2026-08-23）：方法与模拟域结果已经定型，当前在做论文和图表。

## 研究结果

核心对比采用 ResNet-18-GN 结构，比较 Dynamic ERM 与 Dynamic JS Consistency 两种方法，一致性权重 `lambda_js=60`。

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

两个数据集上的五组配对实验都取得了正向提升。

## 文档

| 文件 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前完成项、实验状态、工作重点与下一步 |
| [`00_project_context/APPLICATION_RESEARCH_NARRATIVE.md`](00_project_context/APPLICATION_RESEARCH_NARRATIVE.md) | 项目申请与交流叙事 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 安装、代码结构与使用方式 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 当前工作交接 |
| [`xrd_robustness/MANUSCRIPT.md`](xrd_robustness/MANUSCRIPT.md) | 论文正文框架 |
| [`xrd_robustness/reports/RESULTS.md`](xrd_robustness/reports/RESULTS.md) | 结果汇总 |
| [`xrd_robustness/reports/validation_results.json`](xrd_robustness/reports/validation_results.json) | 验证集结果（JSON） |
| [`xrd_robustness/reports/simulated_test_results.json`](xrd_robustness/reports/simulated_test_results.json) | 测试集结果（JSON） |

## 快速验证

```powershell
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q
```

数据集、模型权重、生成谱图、虚拟环境、文献文件和本地输出不进入 Git。
