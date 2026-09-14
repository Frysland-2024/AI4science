# DeepSeek RRUFF session index

## 审计结论

在 `E:\AI4science` 项目范围内，**没有找到可验证的原始 DeepSeek chat/session export**：无 session ID、逐轮 prompt/response、命令 transcript、debug response 或 session-to-commit 映射。没有扫描项目外私人聊天、浏览器数据库或其他个人目录。

当前 provenance 明确确认 Yifeng 的 RRUFF 实验执行含 DeepSeek-assisted coding/debugging，但这只能证明工具角色边界，不能复原具体会话内容。下表因此是“代理记录/缺口索引”，不是伪造的会话清单。

| date | research question | task | experiment stage | important decision | related file | related git commit | source record location |
|---|---|---|---|---|---|---|---|
| 2026-07-24 | broad zero-shot 是否足以回答 real-domain transfer | 将问题重构为 few-shot / label efficiency | 3 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：从零样本诊断转向少标签适配 | `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md` | `5e624f0b` | Git historical proxy；raw DeepSeek session missing |
| 2026-08-06 | 小样本 RRUFF-70 能否快速检验方向 | 设计/运行 K=1/2/5 paired exploratory | 2–4 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：将 70-sample 证据降级为 exploratory | `xrd_robustness/reports/rruff70_complete_report_20260806.md` | `385cbbc9` | Git historical report + `.workbuddy/memory/2026-08-06.md`; raw session missing |
| 2026-08-06 | 如何构造更可信的 confirmatory test | 设计 70 adaptation + 231 locked test、5×5 paired | 5 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：冻结 K/seeds/primary metric | `xrd_robustness/configs/rruff301_confirmatory_fewshot.preregistered.json` | `385cbbc9` | Git historical prereg; raw session missing |
| 2026-08-07 | 为什么 v1 类别计数异常 | 审计 trigonal/hexagonal label mapping | 7 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：发现 CELL PARAMETERS/hexagonal-setting 语义 bug | `xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md` | `24d8c851` | Git historical audit + local scripts; raw session missing |
| 2026-08-07 | v1 是否还能使用 | 作废 v1、冻结其失败证据并完整重跑 v2 | 8–9 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：不改超参，只修标签语义 | `xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md` | `24d8c851` | Git historical report + `.workbuddy/memory/2026-08-06.md`; raw session missing |
| 2026-08-07 | RRUFF-70 monoclinic 负迁移是否复现 | per-class follow-up + representation/fix-break | 11–12 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：monoclinic v2 三个 K 均为正，早期信号未复现 | `xrd_robustness/reports/rruff301_representation_analysis_20260807.md` | `24d8c851` | Git historical report; raw session missing |
| 2026-08-08 | 如何冻结证据并收束科学结论 | evidence freeze / journey continuation | 12–13 | `HIGH_VALUE_FOR_APPLICATION_NARRATIVE`：结论限定为 label-efficiency 改善 | `00_project_context/EVIDENCE_FREEZE_V1_20260808.md` | `1bf8a99d` | Git historical project record; raw session missing |
| 2026-09-01 | RRUFF 模块实际归属与 AI 工具角色 | 形成当前 contributor provenance | 1–13 | Yifeng 负责设计、执行、bug audit、v2 与解释；DeepSeek 是辅助工具 | `docs/PXRD_RRUFF_COLLABORATOR_MODULE_PROVENANCE.md` | `cffd735` | Current authoritative record；不是早期 contemporaneous session |
| 2026-09-01 | 如何形成可签署 contributor record | 建立贡献记录模板 | 1–13 | 当时仍有姓名、日期、commit/report 链接占位符，不能视为完成记录 | `docs/RRUFF_COLLABORATOR_RECORD.txt` | — | 审计中曾读取的 untracked incomplete template；随后被外部流程移除；raw session 仍缺失 |

## 明确缺失

- 原始 DeepSeek 对话导出与 session IDs。
- 逐轮 prompt、代码建议、命令、debug response、时间戳。
- DeepSeek session 与具体 script/commit/run 的一一映射。
- 2026-09-01 attribution 澄清的原始对话；当前只有项目摘要和随后形成的 provenance。

`.workbuddy` 是项目摘要型代理记录，来源 agent 未自证为 DeepSeek；不得把它们重命名成 DeepSeek session。两组 `.codex_tmp/p6_rruff_*` 是 Codex 生成的汇报页编辑/QA 痕迹，也不是 DeepSeek 实验记录。
