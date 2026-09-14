# MISSING_AND_UNKNOWN — 缺失项、未知项与复现断点

## 关键缺失

1. **原始 DeepSeek session/export**：没有 session ID、逐轮 prompt/response、命令/debug transcript 或 commit 映射。
2. **原始 prereg episode/support-ID 文件**：prereg 提到的 `rruff301_episode_plan.csv` 未在当前树或可达 Git 历史找到。
3. **v1 原始 outputs**：未找到独立 v1 run-level metrics、predictions 或 execution logs；只有错误 split 和后来写成的 invalidation audit。
4. **pipeline diagnostic raw result**：35-sample 数据包与历史报告存在，但独立 raw per-sample result 当前缺失。
5. **RRUFF-301 明确的 paired-comparison CSV**：当前 raw runs 可计算 paired deltas，但未找到一份冻结的 `rruff301_paired_comparisons.csv`。
6. **完整运行绑定**：原始命令、stdout/stderr、运行时间、环境 lock、GPU/runtime 与 pre-execution authorization 记录不完整。
7. **RRUFF-specific scientific figures**：当前只有通用方法/simulated-Test 图和 PPT QA 临时件。
8. **审计中途消失的两份 untracked 草稿**：`docs/RRUFF_LINE_COAUTHOR_CONTRIBUTION.md`（8,313 B；SHA-256 `7D8838B15912BD5C0D7F4DD50CAC9EDE52963E1879DCFA695FDF2A0B5E83C8A5`）与 `docs/RRUFF_COLLABORATOR_RECORD.txt`（5,979 B；SHA-256 `EC4DE0B13851F35C060A9646B3C2298D00A4ED8ED633B867C05B4CAFC099AF30`）曾被只读取证，随后由外部并发流程移除；没有可达 Git blob。本审计没有删除它们。

## 不能冒充原始材料的替代物

- `rruff301_retrospective_replay_episode_plan.json`：2026-08-23 的 post-hoc reconstruction；15 episodes / 280 support assignments，但状态是 `retrospective_replay_plan_generated_not_authorized`。它有助于重建，不是原始 prereg episode plan。
- `.workbuddy`：项目摘要/记忆代理，不是 DeepSeek raw chat。
- `.codex_tmp/p6_rruff_*`：Codex 汇报页编辑与 QA，不是实验 session。
- `PROJECT_HISTORY.md`：综合历史档案，不是当前执行合同或 attribution authority。

## 当前 runner 断点

`tmp/run_rruff301_confirmatory.py` 硬编码的旧 checkpoint 目录不存在；实际 weights 位于另一目录。权重 SHA 与 metadata 一致，但 runner 未保存原始 support IDs，也没有完整命令/runtime binding。未来复现前必须人工复核路径和数据/seed 绑定；Stage 1 不修改脚本。

## 科学表述风险

- RRUFF-70 当前 local JSON 只有 accuracy/per-class recall，不可把旧叙事里的数字自动称作 ΔMacro-F1。
- `tmp/compile_rruff301_report.py` as-is 写死 v1 headline、70/75 与 36,150；不得直接重生成当前报告。
- 当前 RRUFF predictions 无 logits/probabilities；不能据此声称 ECE/NLL/Brier 或 calibrated confidence 改善。
- v1 所有结果 `INVALIDATED`，只可用于科研纠错叙事。
- current reporting 已把 RRUFF 定位为直接的 balanced curated experimental locked-test/label-efficiency 性能；历史 prereg 的 “confirmatory benchmark” 名称不能被夸大为当前独立 evidence tier。

## 许可/权属未知

- `rruff350` contracts 对源 archives 写明 `redistribution_rights_asserted=false`。
- `rruff70` / `rruff371` 有 citation/release policy，但本审计不构成法律或许可结论。
- 因此原始 spectra、DIF、structure refs 与 source ZIP 的 `safe_to_copy` 标为 `PRIVATE_ONLY_AFTER_LICENSE_REVIEW`，不可直接公开发布。

## 范围限制

- 只扫描 `E:\AI4science` 和项目内明确相关的记录。
- 未扫描私人聊天、浏览器资料、无关个人目录或其他项目。
- Git 不能恢复从未 tracked 且已删除的本地文件；“未找到”不证明过去从未存在。
