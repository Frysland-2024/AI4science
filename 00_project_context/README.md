# Project Context

本目录只保留当前权威状态、不可改写的研究历程、申请叙事、文献索引和
sealed future modules。V6–V10、PAMPT、Residual、opXRD 等阶段性协议的结论已
合并进 Journey 和证据索引；原文可从整理前提交
`f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217` 恢复。

## 权威入口

| 文件 | 用途 |
|---|---|
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | 当前完成项、限制、阻塞项与下一步 |
| [`PROJECT_JOURNEY.md`](PROJECT_JOURNEY.md) | 研究决策历史、失败路线与方向变化 |
| [`APPLICATION_RESEARCH_NARRATIVE.md`](APPLICATION_RESEARCH_NARRATIVE.md) | 与当前 claim boundary 一致的申请叙事 |
| [`LITERATURE_LOCAL_RESOURCE_INDEX.md`](LITERATURE_LOCAL_RESOURCE_INDEX.md) | 本地文献资源入口 |
| [`future_modules/`](future_modules/) | 已登记但未获执行授权的未来模块 |
| [`../xrd_robustness/CODEX_HANDOFF.md`](../xrd_robustness/CODEX_HANDOFF.md) | 工程入口与核验命令 |
| [`../xrd_robustness/reports/EVIDENCE_INDEX.md`](../xrd_robustness/reports/EVIDENCE_INDEX.md) | 冻结结果与负结果索引 |
| [`../xrd_robustness/MANUSCRIPT.md`](../xrd_robustness/MANUSCRIPT.md) | 当前论文 scaffold |

## 使用规则

1. 当前事实优先级：`CURRENT_STATE.md` → 源代码/配置/机器审计 →
   `CODEX_HANDOFF.md` → Journey 中的历史记录。
2. 当前项目只证明 robust seven-class PXRD classification；不写成已完成的
   物理参数反演。
3. Active split 只保证 exact-parent-disjoint；不写成
   family/formula/prototype-disjoint。
4. RRUFF-301 是 retrospective validation，不写成 confirmatory evidence。
5. 历史文件退出当前树不等于删除科研历史；Journey、Evidence Index 和 Git
   baseline 共同提供恢复路径。
