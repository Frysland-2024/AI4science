# AI4Science 本地工作区

本文件是 `E:/AI4science` 的 Markdown 总入口。项目代码、研究计划、文献与外部源码各自保留独立职责，不把环境包或来源归档混入活动文档。

## 当前状态

- 当前可运行主线位于 `xrd_robustness/`，版本为 V9-T Algorithm Transfer for PXRD Robustness。
- `formal_14060` 的冻结 family-aware 划分为 train 9,842、validation 2,109、test 2,109。
- lambda 调参尚未开始，当前为 0/7；笔记本上没有活动训练进程、checkpoint 或可恢复 run。
- 项目正在准备迁移到 AMD Ryzen 5 9600X + RTX 4070 Ti SUPER 16 GB 台式机，必须从 optimizer step 0 冷启动。
- 台式机工程门通过后仍需用户重新明确授权，才能启动完整 7-run 调参；15-run 正式实验和两个测试集分别需要后续独立授权。

## 权威入口

| 入口 | 用途 |
|---|---|
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 跨台式机、跨 Codex 账号的当前唯一接管入口 |
| [`00_project_context/README.md`](00_project_context/README.md) | 活动研究上下文、V9.2 计划、决策历史与未来方向 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 当前代码、配置、数据、测试与实际运行边界 |
| [`01_literature/README.md`](01_literature/README.md) | 文献分区、阅读审计和论文—代码映射 |
| [`02_code_repositories/README.md`](02_code_repositories/README.md) | 本地外部代码资产及复用边界 |

## 文档层级

1. `xrd_robustness/CODEX_HANDOFF.md`、当前配置、源代码、清单和验证报告共同决定“本地现在能运行什么”。
2. `00_project_context/` 根部文件解释研究决策和历史路线；其中旧计划不得覆盖当前 V9-T 机器合同。
3. `00_project_context/archive/`、V6/V7 文档及日期化报告保留为历史证据，不作为当前执行命令。
4. `extracted_full_archive/`、`source_package/`、外部仓库 README、许可证、`.venvs/` 和 `.conda/` 是来源或运行时资产，不参与项目 Markdown 去重。
5. 2026-07-19 清理审计见 [`xrd_robustness/reports/ai4science_cleanup_inventory_20260719.json`](xrd_robustness/reports/ai4science_cleanup_inventory_20260719.json)。

## 历史报告

- [`00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md`](00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md)：早期项目组织与 MVP 设计。
- [`01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md`](01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md)：早期跨方向阅读综述。

## 2026-07-16 Markdown 整合

本轮整合保留 V9.2 命名的两份计划作为权威版本，删除其逐字相同的旧别名；项目发展叙事合并到 `00_project_context/PROJECT_JOURNEY.md`；文献导入索引保留 ASCII 工具友好版本及来源包内原始归档。
