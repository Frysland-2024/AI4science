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
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前科学主线、实验状态、工程阻塞、Gate 与下一步；新会话优先读取 |
| [`AGENTS.md`](AGENTS.md) | Codex/GPT 在仓库中的工作规范与状态更新责任 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 跨台式机、跨 Codex 账号的当前工程接管入口 |
| [`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md) | 从 FerroAI、因果不变性思考到 XRD 与 V9-T 的研究演变历程 |
| [`00_project_context/SYNC_PROTOCOL.md`](00_project_context/SYNC_PROTOCOL.md) | 本地与 GitHub 同步检查、提交和冲突处理规范 |
| [`00_project_context/README.md`](00_project_context/README.md) | 活动研究上下文、历史计划、决策资料与未来方向 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 当前代码、配置、数据、测试与实际运行边界 |
| [`01_literature/README.md`](01_literature/README.md) | 文献分区、阅读审计和论文—代码映射 |
| [`02_code_repositories/README.md`](02_code_repositories/README.md) | 本地外部代码资产及复用边界 |
| `04_external_lab_data/GTIIT/README.md`（仅本地） | GTIIT 实验数据的分类、完整性、隐私风险与当前用途边界；整个顶层目录不进入 Git |

## 文档层级

1. 当前配置、源代码、机器可读清单和匹配的验证报告决定实际可运行状态。
2. `xrd_robustness/CODEX_HANDOFF.md` 规定工程接管、授权和测试集访问边界。
3. `00_project_context/CURRENT_STATE.md` 汇总当前科学身份、实验进度、阻塞与下一步，但不能覆盖更高优先级的机器证据。
4. `00_project_context/PROJECT_JOURNEY.md` 记录方案为什么改变；历史内容不得因为当前方案改变而删除。
5. `00_project_context/archive/`、V6/V7/V8 文档及日期化报告保留为历史证据，不作为当前执行命令。
6. `extracted_full_archive/`、`source_package/`、外部仓库 README、许可证、`.venvs/` 和 `.conda/` 是来源或运行时资产，不参与项目 Markdown 去重。
7. 2026-07-19 清理审计见 [`xrd_robustness/reports/ai4science_cleanup_inventory_20260719.json`](xrd_robustness/reports/ai4science_cleanup_inventory_20260719.json)。
8. `04_external_lab_data/` 是 Git 忽略的本地外部实验资料区；其中的原始光谱、PDF、图片、实验表单和外部脚本不得提交。

## 历史报告

- [`00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md`](00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md)：早期项目组织与 MVP 设计。
- [`01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md`](01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md)：早期跨方向阅读综述。

## 2026-07-21 状态同步

仓库现已建立统一状态入口、研究历程入口和工作规范。任何新的 GPT/Codex 会话应先读取 `AGENTS.md`、`CURRENT_STATE.md`、`PROJECT_JOURNEY.md` 与 `CODEX_HANDOFF.md`，再判断是否可以修改代码或启动实验。
