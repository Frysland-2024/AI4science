# AI4Science

这个仓库主要做 XRD 鲁棒性研究，代码在 [`xrd_robustness/`](xrd_robustness/)。核心想法是：在线 PXRD 模拟器知道哪些谱图来自同一个母体结构，把这个关系变成一种监督信号，让七晶系分类器在测量条件变化时更稳。

> 状态（2026-08-23）：方法和模拟结果已经确定，现在在写论文、做图表。

## 一眼看懂这个项目

```text
同一个母体晶体结构
      ↓ 在线物理扰动
两份不同测量条件下的 PXRD 谱图
      ↓
Dynamic ERM：只使用共同晶系标签
Dynamic JS：共同标签 + 预测一致性
      ↓
更稳定的分布外泛化
```

## 研究结果

在 ResNet-18-GN 上对比了 Dynamic ERM 和 Dynamic JS Consistency 两种方法，一致性权重 `lambda_js=60`。

| 数据集 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 | 0.705064 | `+0.046569` |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 | 0.70534 | `+0.054600` |

两个数据集上，五组配对实验都有提升。

## 文档

| 文件 | 用途 |
|---|---|
| [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) | 项目现状、进度和下一步 |
| [`docs/APPLICATION_RESEARCH_NARRATIVE.md`](docs/APPLICATION_RESEARCH_NARRATIVE.md) | 申请和面试用的项目介绍 |
| [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) | 完整研究演化档案；记录失败、版本变化和历史决策，不代表当前方法主张 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 安装、代码结构与使用方式 |
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

这里的 `pytest` 用来核对实现、接口、配置和公开结果文件之间是否一致；它不会重新训练模型，也不会复现论文中的完整训练结果。数据集、模型权重、生成的谱图、虚拟环境、文献和本地输出都不会提交到 Git。
