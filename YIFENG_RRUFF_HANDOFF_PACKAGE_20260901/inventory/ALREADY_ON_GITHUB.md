# ALREADY_ON_GITHUB — 不必重复备份的 Git 资产

封版验收时 `origin/main = 93da7d9f5cb3b2389439243d636bba6dcd5f68f9`；最后一次影响本 RRUFF inventory 的 commit 是 `c977ba355989f96ac2da13d31950daa0bb48d715`。下列 anchor commits 均经 `git merge-base --is-ancestor <commit> origin/main` 验证为可达。

## 当前 main

| 路径 | 角色 |
|---|---|
| `docs/PXRD_RRUFF_COLLABORATOR_MODULE_PROVENANCE.md` | 当前 attribution authority |
| `docs/RRUFF真实域_科研叙事.md` | cuifa01/Yifeng 第一人称完整科研叙事；commit `c977ba3` |
| `xrd_robustness/reports/rruff301_fewshot_results.json` | 当前 RRUFF-301 数字 authority |
| `xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md` | 可读 composition/split 审计 |
| `xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.json` | 机器可读 composition 审计 |
| `xrd_robustness/scripts/audit_rruff301_composition.py` | 只读 composition audit 脚本 |
| `xrd_robustness/reports/RESULTS.md` | 当前主结果口径 |
| `xrd_robustness/MANUSCRIPT.md` | 当前 manuscript 叙事 |
| `xrd_robustness/README.md` | 当前项目入口 |
| `docs/PROJECT_HISTORY.md` | 综合历史档案；不是当前执行/归属合同 |
| `docs/PXRD_RESULT_REPORTING_STANDARD.md` | 当前报告证据层级/口径 |
| `xrd_robustness/pyproject.toml` | 当前依赖入口 |

## 当前树已删除、但 Git 历史完整可恢复

恢复时使用 `git show <commit>:<path>`；Stage 1 没有实际导出。

| Commit | Historical path | 角色 |
|---|---|---|
| `5e624f0b` | `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md` | zero-shot→few-shot 决策 |
| `5e624f0b` | `xrd_robustness/configs/real_adaptation.v9.method_transfer.json` | method-transfer config |
| `5e624f0b` | `xrd_robustness/docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md` | few-shot protocol |
| `2cb656c0` | `xrd_robustness/CODEX_HANDOFF_REAL_ADAPTATION_ADDENDUM.md` | 当时 handoff boundary |
| `2cb656c0` | `xrd_robustness/reports/rruff_pipeline_smoke_test_20260806.md` | 35-sample diagnostic |
| `2cb656c0` | `xrd_robustness/reports/rruff350_build_audit.json` | 350 build audit |
| `2cb656c0` | `xrd_robustness/reports/rruff371_build_audit.json` | 371 build audit |
| `2cb656c0` | `xrd_robustness/reports/rruff371_expansion_audit.json` | collection expansion audit |
| `2cb656c0` | `xrd_robustness/reports/v9_real_adaptation_contract_audit.json` | real-adaptation contract audit |
| `2cb656c0` | `xrd_robustness/reports/v9_real_adaptation_plan.json` | large run plan |
| `2cb656c0` | `xrd_robustness/scripts/build_rruff_pipeline_test.py` | pipeline dataset builder |
| `385cbbc9` | `xrd_robustness/configs/rruff301_confirmatory_fewshot.preregistered.json` | RRUFF-301 preregistration |
| `385cbbc9` | `xrd_robustness/reports/rruff70_complete_report_20260806.md` | exploratory report |
| `385cbbc9` | `xrd_robustness/reports/rruff70_fewshot_*` / `rruff70_fixed200_*` | exploratory raw summaries |
| `385cbbc9` | `xrd_robustness/scripts/analyze_fewshot_results.py` | exploratory aggregation |
| `385cbbc9` | `xrd_robustness/scripts/run_rruff70_fewshot_adaptation.py` | exploratory runner |
| `24d8c851` | `xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md` | v1 invalidation / label bug |
| `24d8c851` | `xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md` | corrected v2 full report |
| `24d8c851` | `xrd_robustness/reports/rruff301_representation_analysis_20260807.md` | per-class/fix-break |
| `1bf8a99d` | `00_project_context/EVIDENCE_FREEZE_V1_20260808.md` | evidence freeze |
| `1bf8a99d` | `00_project_context/PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md` | transition/freeze narrative |
| `1eab4d59` | `00_project_context/DECISION_LOG_20260813.md` | corrected rerun-priority rationale |
| `f36be82b` | `xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json` | strict lineage audit |
| `512b05ff` | `xrd_robustness/configs/rruff301_retrospective_replay.v1.json` | post-hoc replay contract |
| `512b05ff` | `xrd_robustness/reports/rruff301_retrospective_replay_episode_plan.json` | post-hoc support plan，非原 prereg plan |
| `512b05ff` | `xrd_robustness/scripts/run_rruff301_retrospective_replay.py` | post-hoc replay runner |
| `512b05ff` | `xrd_robustness/src/xrd_robustness/evaluation/rruff301_replay.py` | post-hoc replay module |

## 不重复备份的原则

- 当前 main 文本/脚本保留 repo URL、commit 与 path 即可。
- 历史 blobs 记录 commit:path、bytes、SHA-256；除非 Yifeng 希望离线独立保存整个历史，否则无需在个人包中复制多份同内容报告。
- ignored/local raw artifacts 不适用这一原则：它们是 GitHub 没有的优先交接对象。
