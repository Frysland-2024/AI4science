# Project Context

本目录保存当前状态、科研决策、申请叙事和未来研究边界。判断“现在已经完成什么、允许主张什么、下一步是什么”时，以 2026-08-11 当前状态、源代码、冻结配置和机器可读审计为准；日期较早的设计文档用于解释研究演进，不能覆盖后续证据。

## 当前入口

| 文件 | 权威范围 |
|---|---|
| [`CURRENT_STATE.md`](CURRENT_STATE.md) | 当前任务、结果、限制、阻塞项和下一步；本目录最高优先级 |
| [`../xrd_robustness/CODEX_HANDOFF.md`](../xrd_robustness/CODEX_HANDOFF.md) | 当前工程实现、证据文件和核验命令 |
| [`EVIDENCE_FREEZE_V1_20260808.md`](EVIDENCE_FREEZE_V1_20260808.md) | 2026-08-08 冻结快照；RRUFF confirmatory 措辞已被 2026-08-11 lineage audit 取代 |
| [`PROJECT_JOURNEY.md`](PROJECT_JOURNEY.md) | 研究决策主历史，保留失败、否决和方向变化 |
| [`PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md`](PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md) | 2026-08-07 至 08-08 的历史续篇 |

## 申请与研究方向

- [`APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`](APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md)：历史申请叙事草稿，使用前必须按当前审计边界更新；
- [`FUTURE_RESEARCH_DIRECTIONS.md`](FUTURE_RESEARCH_DIRECTIONS.md) 与 [`future_modules/`](future_modules/)：未来方向，不代表当前已实现能力；
- 本地个人研究兴趣和申请交付物不纳入 Git；公开使用前必须按当前 claim boundary 单独复核。

## 历史设计记录

V6、V7、V8、V9.2、Residual、PAMPT、V10、opXRD 等文档和决策记录解释“为什么这样设计、哪些路线失败、何时停止”。它们可以退出当前运行主线，但其科学结论不应被当作普通缓存删除。

## 使用规则

1. 当前事实优先级：`CURRENT_STATE.md` → 源代码/配置/机器审计 → `CODEX_HANDOFF.md` → 日期化历史文档。
2. 当前项目只证明 robust seven-class PXRD classification、simulation-driven scientific ML 和 few-shot adaptation 能力；不写成已完成的物理参数反演。
3. Active split 只保证 exact-parent-disjoint；不写成 family/formula/prototype-disjoint。
4. RRUFF-301 是 provenance 不完整的 retrospective validation，不写成 confirmatory evidence。
5. 删除重复快照、一次性交接包和可再生清单时，Git 历史继续提供恢复路径；科研决策和冻结证据不得随版本清理一并抹除。
