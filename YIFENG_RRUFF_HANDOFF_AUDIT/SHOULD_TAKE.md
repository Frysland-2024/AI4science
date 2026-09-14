# SHOULD_TAKE — 建议保存的辅助材料

## 数据冻结与审计补充

- `rruff70/audits/` 的完整冻结、integrity、phase-evidence、pairwise-correlation 与 screening 文件。
- `rruff70/evidence/`、`structure_refs/`；与 spectra 一样先做许可复核。
- `rruff371/CITATION_AND_RELEASE_POLICY.md` 与 RRUFF-350 source archive 的 per-file SHA。
- Git 历史中的 collection build/expansion audits、v9 adaptation contract audit/plan、RRUFF-70 fixed200 结果。
- `xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json`：严格说明现有 artifact 能证明什么、不能证明什么。

## 复现辅助

- `xrd_robustness/pyproject.toml`：当前 Python 依赖入口，但不是完整历史 lockfile。
- `xrd_robustness/outputs/simulated_test_checkpoints/metadata/` 四个小文件：checkpoint 路径、原始路径与 SHA-256。
- 历史 retrospective replay config/episode plan/runner/module/test：有助于恢复 support assignment，但必须标注 `POST_HOC_RECONSTRUCTION_NOT_ORIGINAL_PREREG_PLAN`。
- compiled-only `__pycache__` RRUFF 痕迹只作为“源码曾在本地存在”的发现线索，不作为可执行权威资产。

## 项目叙事与会议材料

- `docs/PROJECT_HISTORY.md`：最佳综合时间线，已在 GitHub。
- `.workbuddy/memory/2026-08-04.md` 等 RRUFF 相关日期记录：仅作为二手项目摘要。
- `docs/presentation_materials/如何讲清楚你的XRD项目_讲解指南.md`、`project_brief_for_TanQi.md`：旧讲解/简报，需按当前 attribution 和结果口径复核。
- `.codex_tmp/p6_rruff_fewshot_20260828/`、`.codex_tmp/p6_rruff_reframe_20260828/`：两组 slide-6 编辑/渲染/QA 束，合计约 1.0 MB；能证明汇报叙事迭代，不是实验执行证据。
- 两个 `tmp/pptx/.../qa_powerpoint_render_rruff_*` 目录：视觉 QA 参考，非科研核心。

## 草稿风险

- `docs/RRUFF真实域_科研叙事.md`：cuifa01/Yifeng 第一人称与当前 provenance 对齐，已由 commit `c977ba3` 纳入 main；其中 ECE/NLL/Brier/confidence 是后续分析议程，当前 RRUFF probability/logit 证据不足以把它们写成已完成结论。
- `docs/分工陈述_申请材料.md`：可继续润色，但不是实验结果 authority。
- `docs/RRUFF_COLLABORATOR_RECORD.txt`：审计中曾观察到的未完成模板，随后由外部流程移除；没有当前文件可保存，也不能当签署记录。
- `docs/RRUFF_LINE_COAUTHOR_CONTRIBUTION.md`：审计中曾观察到的 stale draft，随后由外部流程移除；其 attribution 与部分 per-class 内容已过时，只保留审计指纹。
