# AI4Science

本仓库当前主线是 [`xrd_robustness/`](xrd_robustness/) 中的 V9-T：利用在线 PXRD 物理扰动视图和 parent-structure provenance，研究七晶系分类的合成域鲁棒性。

> 状态（2026-08-23）：**证据已冻结，进入论文与图表整理阶段**。不默认新增训练、重跑 frozen Test、替换 checkpoint，或根据 Test 结果重新选方法。

## 当前结论

- 模型：ResNet-18-GN；对照：Dynamic ERM；选定方法：Dynamic JS Consistency，`lambda_js=60`。
- 数据划分：Train 9,842 / Validation 2,109 / Test 2,109；只支持 exact-parent-disjoint 表述。
- Validation：mean single-factor OOD Macro-F1 `0.658495 → 0.705064`，Δ `+0.046569`，5/5 paired seeds 为正。
- Frozen simulated Test：`0.65074 → 0.70534`，Δ `+0.054600`，5/5 paired seeds 为正。
- RRUFF-301 K=1/2/5 few-shot 的 Δ 分别为 `+0.0433/+0.0460/+0.0545`，属于 retrospective validation。历史执行 provenance 不完整是 **claim limitation**，不是当前工程 blocker。

本项目不声称进行晶格常数、相分数、应变、织构或峰宽反演；模拟 Test 的 aggregate 改善也不代表所有晶系和压力条件都改善。

## 权威入口

| 文件 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前科学状态、执行锁、限制与下一步 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 工程入口、证据链接和核验命令 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 安装、代码地图和目录合同 |
| [`xrd_robustness/reports/EVIDENCE_INDEX.md`](xrd_robustness/reports/EVIDENCE_INDEX.md) | 冻结结果与负结果的合并索引 |
| [`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md) | 不可改写的研究决策历史 |
| [`xrd_robustness/MANUSCRIPT.md`](xrd_robustness/MANUSCRIPT.md) | 当前论文 scaffold |
| [`00_project_context/APPLICATION_RESEARCH_NARRATIVE.md`](00_project_context/APPLICATION_RESEARCH_NARRATIVE.md) | 与当前证据边界一致的申请叙事 |
| [`00_project_context/future_modules/`](00_project_context/future_modules/) | 已登记但未获执行授权的未来模块 |

## 精简后的目录合同

- `xrd_robustness/src/`：可复用模型、模拟、训练目标和评估实现；
- `xrd_robustness/scripts/`：当前数据准备、训练和只读核验入口，顶层直接文件不超过 10 个；
- `xrd_robustness/configs/`：当前冻结合同，顶层直接文件不超过 10 个；
- `xrd_robustness/reports/`：当前机器可读证据和合并索引，顶层直接文件不超过 10 个；
- `xrd_robustness/tests/`：保留高价值回归测试并按主题组织，每个目录尽量不超过 10 个直接文件；
- `00_project_context/`：当前状态、研究历程、申请叙事和未来模块注册。

历史一次性 runner、重复报告和已关闭分支已从工作树合并或删除；科学结论保留在 Journey/证据索引中，完整原文件仍可由 Git 历史恢复。

数据、checkpoint、生成谱图、虚拟环境、文献 PDF、第三方仓库和凭据不得进入 Git。

## 默认核验

```powershell
cd E:\AI4science\xrd_robustness
E:\AI4science\.venvs\xrd_test\Scripts\python.exe -m pytest -q
```

下一步是依据冻结证据完成论文正文与图表，不是补做无新科学问题的实验。
