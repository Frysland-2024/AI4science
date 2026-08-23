# AI4Science

本仓库的当前研究主线位于 [`xrd_robustness/`](xrd_robustness/)：利用在线 PXRD 模拟器提供的同源结构配对视图，为七晶系分类学习 measurement-equivalence supervision。

> 状态（2026-08-23）：本研究的方法与模拟域结果已经定型，当前工作是论文和图表制作。

## 本研究结果

冻结比较采用 ResNet-18-GN、Dynamic ERM 与 Dynamic JS Consistency，选定 `lambda_js=60`。

| 数据面板 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| Simulated Validation mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| Simulated Test mean single-factor OOD Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

两个面板的五组 matched seed pairs 均保持正向提升。

## 入口

| 文件 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前完成项、实验状态、工作重点与下一步 |
| [`00_project_context/APPLICATION_RESEARCH_NARRATIVE.md`](00_project_context/APPLICATION_RESEARCH_NARRATIVE.md) | 项目申请与交流叙事 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 安装、代码地图与使用方式 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 当前工程交接 |
| [`xrd_robustness/MANUSCRIPT.md`](xrd_robustness/MANUSCRIPT.md) | 论文正文框架 |
| [`xrd_robustness/reports/RESULTS.md`](xrd_robustness/reports/RESULTS.md) | 人类可读结果汇总 |
| [`xrd_robustness/reports/validation_results.json`](xrd_robustness/reports/validation_results.json) | Validation 机器可读结果 |
| [`xrd_robustness/reports/simulated_test_results.json`](xrd_robustness/reports/simulated_test_results.json) | Test 机器可读结果 |

## 快速验证

```powershell
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q
```

数据集、模型权重、生成谱图、虚拟环境、文献文件和本地输出不进入 Git。
