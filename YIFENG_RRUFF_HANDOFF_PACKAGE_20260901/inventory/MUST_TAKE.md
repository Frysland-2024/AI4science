# MUST_TAKE — 后续交接包的核心候选

> 本页只是 Stage 1 选择建议。当前没有复制任何文件。凡涉及 RRUFF 原始 spectra / DIF / source ZIP 的项目，必须先做私人共同作者交接与再分发条款复核。

## 1. 贡献归属与科学结论

- `docs/PXRD_RRUFF_COLLABORATOR_MODULE_PROVENANCE.md`：当前 attribution authority；同时写明共享工作站 Git identity 不能用来推断实际操作者。
- `xrd_robustness/reports/rruff301_fewshot_results.json`：当前公开数字权威。
- `xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.{md,json}` 与 `scripts/audit_rruff301_composition.py`：证明 70/231 split、无 ID/SHA overlap 与 composition 边界。
- `docs/PROJECT_HISTORY.md` 与本目录 `RRUFF_TIMELINE.md`：可读时间线入口。

这些项目已在 GitHub current main，重要但不必为“备份”制造重复副本；真正打包时可放一个 Git spec/commit manifest，或只放小型文本副本。

## 2. 本地 v2 原始证据链 — 最高优先级

根目录：`xrd_robustness/data/real_xrd/rruff371/`

- `contracts/dataset_contract.json`
- `manifests/rruff371_master_manifest.csv`
- `splits/rruff301_adaptation_test_split.csv`
- `splits/rruff301_manifest.json`
- `results/rruff301_fewshot_runs.json`：150 条方法/seed/K/episode 级 metrics。
- `results/rruff301_predictions.json`：34,650 条逐样本预测。
- `results/rruff301_fixed200.json`：固定 200-step sensitivity。
- `results/rruff301_zero_shot.json`：secondary diagnostic。
- `results/rruff301_split.csv`：错误 v1 split；必须保留，但明确标 `INVALIDATED`。
- `spectra_10_80_step_002/`、`evidence/`、`structure_refs/`：复现所需实验输入与证据；只可在许可复核后进入私人包。

整个 `rruff371` 为 1,492 files / 53,902,912 bytes，TREE_SHA256 `6C51ADD46D00AFE75F479942E641B19B079AAB6C9F4811BBDEAC7A1AA2B50980`。

## 3. RRUFF-specific local scripts

- `tmp/run_rruff301_confirmatory.py`：v2 runner 强候选；当前硬编码旧 checkpoint 路径，复制时必须附断链说明，不能声称一键可跑。
- `tmp/fix_rruff301_split.py`：trigonal/hexagonal 修复与正确 split 生成。
- `tmp/analyze_representation.py`：per-class / fix-break / correctness-rate proxy 分析。
- `tmp/check_rruff_pool.py`：数据池/标签诊断辅助。
- `tmp/compile_rruff301_report.py`：保留作历史 aggregation 源码，但内含 v1 headline、70/75 与 36,150 的过时硬编码；只能标 `INVALIDATED_AS_IS`，先修订/复核后再运行。
- `tmp/run_rruff70_fewshot_v2.py`、`tmp/analyze_fewshot.py`、`tmp/run_rruff70_fewshot.py`：RRUFF-70 exploratory 执行/汇总链。
- `tmp/run_pipeline_smoke_test.py`：Stage 1 diagnostic runner。

## 4. RRUFF-70 exploratory frozen package

根目录：`xrd_robustness/data/real_xrd/rruff70/`，238 files / 11,152,748 bytes，TREE_SHA256 `585EB07AED8C36AC9AE6D25A594AC77A26EB052E32CFE1D86C0B4A4FB20AEBBD`。

必须保留的内部结构：

- `README.md`、`RRUFF_REAL_PXRD_70_FINAL_REPORT.md`、citation/release policy、freeze certificate。
- `contracts/`、`manifests/`、`results/`。
- `audits/file_manifest_sha256.csv`、`freeze_record.json`、`integrity_audit.csv`、`phase_evidence_audit.csv`。
- spectra/evidence/structure refs 仅在许可复核后进入私人包。

科学标签固定为 `EXPLORATORY`。当前 local JSON 的 headline 是 accuracy 增益与 60/75 正配对，不得误写成 confirmatory ΔMacro-F1。

## 5. broad diagnostic 与数据构建链

- `xrd_robustness/data/real_xrd/rruff_pipeline_test/`：36 files / 502,350 bytes，TREE_SHA256 `32E5CF6DF32841AA52B0B096C6F77570E12C447FD09C1339D32FF61371AD0D73`。
- `xrd_robustness/data/real_xrd/rruff350/`：1,406 files / 213,682,393 bytes，TREE_SHA256 `72D6B24938BA533CB5D93FDF6B1FD30E2599AE7A578B058A2890A8B584AA12F0`；是 371 前身且含源 archives，科研史上重要，但被 371 supersede。
- Git history 中的 `rruff350_build_audit.json`、`rruff371_build_audit.json`、`rruff371_expansion_audit.json`、`build_rruff_pipeline_test.py`。

## 6. 必须保留的 Git 历史 blobs

这些文件当前树已删除，但均在 `origin/main` 可达历史中，无需先复制几十份；必须在交接 manifest 中记录以下恢复 spec：

- `5e624f0b:00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`
- `5e624f0b:xrd_robustness/configs/real_adaptation.v9.method_transfer.json`
- `5e624f0b:xrd_robustness/docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`
- `2cb656c0:xrd_robustness/reports/rruff_pipeline_smoke_test_20260806.md`
- `385cbbc9:xrd_robustness/configs/rruff301_confirmatory_fewshot.preregistered.json`
- `385cbbc9:xrd_robustness/reports/rruff70_complete_report_20260806.md`
- `24d8c851:xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md`
- `24d8c851:xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md`
- `24d8c851:xrd_robustness/reports/rruff301_representation_analysis_20260807.md`
- `1bf8a99d:00_project_context/EVIDENCE_FREEZE_V1_20260808.md`
- `1bf8a99d:00_project_context/PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md`
- `1eab4d59:00_project_context/DECISION_LOG_20260813.md`
- `f36be82b:xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json`

## 7. 本地独有的叙事/项目记录

- `00_project_context/PROJECT_JOURNEY.md`：ignored，本地精确版不同于最后 tracked blob。
- `00_project_context/AI4Science_Project_Handoff_for_Admissions_AI_2026-08-07.md`：ignored、从未 tracked。
- `.workbuddy/memory/2026-08-06.md`、`2026-08-13.md`、`2026-08-16.md`、`2026-08-23.md`、`2026-08-27.md`、`2026-09-01.md`：项目摘要型旁证；不是 raw DeepSeek session。
- `docs/RRUFF真实域_科研叙事.md`：已在 commit `c977ba3` 进入 main，与当前 attribution 对齐；作为申请叙事候选仍需科学措辞复核。
- `docs/分工陈述_申请材料.md`：当前唯一仍在工作树中的 untracked attribution/申请草稿；需先复核。
- 审计中途移除的 `RRUFF_LINE_COAUTHOR_CONTRIBUTION.md` 与 `RRUFF_COLLABORATOR_RECORD.txt` 只保留瞬时 SHA/大小记录；当前已无文件可带。

## 1 GB 选择顺序

1. 所有小型文档、CSV/JSON、scripts、manifests、audits 与 checkpoint metadata。
2. `rruff371`。
3. `rruff70`。
4. `rruff_pipeline_test`。
5. 若许可复核通过，再带 `rruff350` 及其 source archives。

上述四个数据包总计约 266.3 MiB。不要把 1.455 GiB checkpoint weights 放入 1 GB 个人模块包。
