# LOCAL_ONLY — 当前 GitHub 未完整保存的本机资产

“LOCAL_ONLY”在这里指：当前文件/目录的精确内容不在 `origin/main` 当前树，且对 ignored/untracked 项还检查了可达 Git 历史。它不等于“全世界唯一副本”。

## 最高风险：实验原始层

| 路径 | Files / bytes | 状态 | 说明 |
|---|---:|---|---|
| `xrd_robustness/data/real_xrd/rruff371/` | 1,492 / 53,902,912 | ignored | corrected v2 数据、split、raw metrics、predictions；最高优先级 |
| `xrd_robustness/data/real_xrd/rruff70/` | 238 / 11,152,748 | ignored | frozen exploratory 完整包 |
| `xrd_robustness/data/real_xrd/rruff_pipeline_test/` | 36 / 502,350 | ignored | broad diagnostic 输入；独立 raw result 缺失 |
| `xrd_robustness/data/real_xrd/rruff350/` | 1,406 / 213,682,393 | ignored | 371 前身、源 archives 与数据构建证据 |

四个目录总计 3,172 files，不逐一展开为 CSV 行；CSV 以 collection row + 核心文件行表示。目录 TREE_SHA256 定义见 `00_README.md`。

> RRUFF contracts 写明 `redistribution_rights_asserted=false`。这批数据是“本机科研资产”不等于“可公开再分发资产”；Stage 2 只考虑经许可复核后的共同作者私人归档。

## 本地 scripts / raw artifacts

- `tmp/run_rruff301_confirmatory.py`
- `tmp/fix_rruff301_split.py`
- `tmp/analyze_representation.py`
- `tmp/compile_rruff301_report.py`（as-is 含过时硬编码，必须附风险标签）
- `tmp/check_rruff_pool.py`
- `tmp/run_pipeline_smoke_test.py`
- `tmp/run_rruff70_fewshot_v2.py`
- `tmp/run_rruff70_fewshot.py`
- `tmp/analyze_fewshot.py`

这些文件被 `/tmp/` ignore，当前 GitHub 不保存。当前 v2 runner 还存在 checkpoint 路径断链。

## 本地项目记录

- `00_project_context/PROJECT_JOURNEY.md`：85,636 B；ignored；与删除前最后 tracked blob 不同，含本地独有后续编辑。
- `00_project_context/AI4Science_Project_Handoff_for_Admissions_AI_2026-08-07.md`：27,091 B；ignored；从未 tracked。
- `.workbuddy/memory/*.md`：ignored、从未 tracked；是项目摘要而不是 raw DeepSeek session。
- `docs/分工陈述_申请材料.md`：untracked draft。

`docs/RRUFF真实域_科研叙事.md` 已在审计期间进入 main，因此移至 `ALREADY_ON_GITHUB`。另外两份曾观察到的 untracked 草稿已被外部流程移除，移至 `MISSING_AND_UNKNOWN`。

## 报告/汇报临时资产

- `.codex_tmp/p6_rruff_fewshot_20260828/`：18 files / 327,885 B。
- `.codex_tmp/p6_rruff_reframe_20260828/`：38 files / 701,654 B。
- 两组 `tmp/pptx/.../qa_powerpoint_render_rruff_*`：各 27 PNG、约 3.0 MB。

它们只能证明报告叙事/版式迭代，不是 DeepSeek 记录，也不是原始实验结果。独立 RRUFF scientific figure 当前仍缺失。
