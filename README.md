# AI4Science 本地工作区

本仓库是 `E:/AI4science` 的 GitHub 同步入口。当前可运行主线位于
`xrd_robustness/`，研究版本为 **V9-T Algorithm Transfer for PXRD
Robustness**。

## 当前状态（2026-08-01）

- `formal_14060` 的冻结 parent-structure split 为 train 9,842、Validation
  2,109、Test 2,109。
- 公共 backbone 已冻结为 ResNet-18-GN，使用 identity preprocessing、AdamW
  和 constant learning rate。
- Residual-v1 已因预注册稳定性 Gate 失败而归档。
- Dynamic ERM versus JS Consistency 的方法比较已经完成。
- JS `lambda_js = 60` 是冻结的 selected method；不得继续调 lambda。
- 五组 paired seeds、共十次 Validation replication 已全部完成。
- JS 相对 Dynamic ERM 的 paired mean OOD Macro-F1 delta 为 `+0.046569`，
  paired-bootstrap 95% interval 为 `[0.038145, 0.052834]`。
- paired mean in-range Macro-F1 delta 为 `+0.027991`，95% interval 为
  `[0.014028, 0.041954]`，guardrail 通过。
- one-shot simulated-Test evaluation contract 已冻结，但执行尚未授权。
- simulated Test、real XRD、real-domain adaptation 和 V10 仍未使用或开启。

## 最新结果与冻结合同

- 机器可读 Validation summary：
  [`xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`](xrd_robustness/reports/v9_resnet_js_ten_run_summary.json)
- 人类可读 Validation 报告：
  [`xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`](xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md)
- 机器可读 simulated-Test 预注册合同：
  [`xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json`](xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json)
- 人类可读 simulated-Test 合同：
  [`xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md`](xrd_robustness/reports/v9_resnet_js_simulated_test_contract_20260801.md)
- ten-run 结果首次提交：`868b079c1b410e6afe877330b7defc4262d82969`

本次 replication 的 primary OOD delta 在五组 paired seeds 中全部为正，
in-range delta 也全部为正。需要保留的次要风险是 seed `20260714` 的
worst-class F1 delta 为 `-0.061139`；该异常需要诊断，但不能用于重新调参或
重新选择方法。

simulated-Test 合同冻结全部五组 paired seeds 和十个 Validation-selected
checkpoints，固定三个 deterministic evaluation seeds、Test profiles、指标、
paired aggregation、bootstrap 和 no-retuning policy。用户本次“冻结”指令不等于
Test 执行授权。

## 权威入口

| 入口 | 用途 |
|---|---|
| [`00_project_context/CURRENT_STATE.md`](00_project_context/CURRENT_STATE.md) | 当前科学主线、实验状态、边界、阻塞与下一步；新会话优先读取 |
| [`AGENTS.md`](AGENTS.md) | Codex/GPT 在仓库中的工作规范与自动同步责任 |
| [`xrd_robustness/CODEX_HANDOFF.md`](xrd_robustness/CODEX_HANDOFF.md) | 当前工程交接、执行边界和下一阶段顺序 |
| [`00_project_context/PROJECT_JOURNEY.md`](00_project_context/PROJECT_JOURNEY.md) | 从 FerroAI、因果不变性思考到 XRD 与 V9-T 的研究演变历程 |
| [`00_project_context/SYNC_PROTOCOL.md`](00_project_context/SYNC_PROTOCOL.md) | 本地与 GitHub 同步检查、提交和冲突处理规范 |
| [`xrd_robustness/README.md`](xrd_robustness/README.md) | 当前代码、配置、数据、测试与运行边界 |
| [`01_literature/README.md`](01_literature/README.md) | 文献分区、阅读审计和论文—代码映射 |
| [`02_code_repositories/README.md`](02_code_repositories/README.md) | 本地外部代码资产及复用边界 |

## 文档层级

1. 当前配置、源代码、机器可读清单和匹配的验证报告决定实际可运行状态。
2. `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json` 是 ten-run
   Validation replication 的权威结果记录。
3. `xrd_robustness/configs/v9_resnet_js_simulated_test.preregistered.json` 是
   下一阶段 Test 设计的权威合同；其当前状态不授权执行。
4. `xrd_robustness/CODEX_HANDOFF.md` 规定工程接管、授权和 Test/real-XRD
   访问边界。
5. `00_project_context/CURRENT_STATE.md` 汇总当前科学身份、实验进度、阻塞
   与下一步。
6. `00_project_context/PROJECT_JOURNEY.md` 记录方案为什么改变；历史内容不得
   因当前方案改变而删除。
7. 日期化报告与 Git 历史保留中间状态，但不得覆盖当前权威记录。
8. `04_external_lab_data/` 是 Git 忽略的本地外部实验资料区；原始光谱、PDF、
   图片、实验表单和外部脚本不得提交。
9. datasets、outputs、checkpoints、generated spectra、caches、环境目录和凭据
   不进入 Git。

## 下一阶段

当前不应重复训练 ten-run，也不应继续调参或执行 Test。下一步是按照冻结合同
实现和审查 read-only preflight 与 serial Test runner，核对十个本地 checkpoint、
三个 Test manifests、哈希、split 隔离和输出边界。只有获得新的明确授权后，
才能执行一次性 simulated-Test evaluation。real XRD 必须作为更后的独立
external-validation stage。

## 历史报告

- [`00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md`](00_project_context/archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md)：早期项目组织与 MVP 设计。
- [`01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md`](01_literature/literature_audit/READING_SYNTHESIS_2026-06-28.md)：早期跨方向阅读综述。
