# XRD Robustness Project Context

这里是项目研究决策、证据、计划与历史边界的入口。当前可执行事实以 `E:/AI4science/xrd_robustness/CODEX_HANDOFF.md`、冻结配置、源代码、数据清单和验证报告为准；本目录中的 V6/V7/V8/V9.2 文件主要保存研究演进和设计依据。`extracted_full_archive/` 只保存 2026-06-27 原始上下文，不作为当前规则来源。

## 当前执行状态（2026-07-19）

- 当前主线是 **V9-T：Algorithm Transfer for PXRD Robustness**，其工程实现已经存在，不再是“尚未实现的 V9.2 计划”。
- 权威数据根为 `data/formal_14060/`；冻结 family-aware 划分为 train 9,842、validation 2,109、test 2,109。
- 当前比较 Dynamic/Paired ERM、Dynamic JS 和 Dynamic Residual；结构化动态扰动已归档为未来方向，不属于当前 7-run 或 15-run。
- lambda 调参进度是 **0/7**；没有活动训练进程、checkpoint、结果或可恢复 run。迁移到 AMD Ryzen 5 9600X + RTX 4070 Ti SUPER 16 GB 台式机后，七条 run 必须从 optimizer step 0 冷启动。
- 笔记本只允许工程测试、哈希审计、CUDA smoke test 和有界吞吐测试，不进行正式训练。
- 台式机工程门通过后，仍须用户重新明确授权才能启动完整 7-run；15-run、simulated test 和 real test 各自需要后续独立授权。
- 真实 XRD 仅用于后期外部验证，不用于定义模拟参数，也不是训练启动前置条件。

## 当前权威入口

| 文件 | 用途 |
|---|---|
| `../xrd_robustness/CODEX_HANDOFF.md` | 跨台式机、跨 Codex 账号的唯一接管入口与执行边界 |
| `../xrd_robustness/configs/algorithm.v9.method_transfer.json` | V9-T 方法与实验范围合同 |
| `../xrd_robustness/configs/data.v9.method_transfer.family_split.json` | 当前 family-aware split 合同 |
| `../xrd_robustness/configs/training.v9.method_transfer.json` | 训练与硬件流水线合同 |
| `../xrd_robustness/reports/codex_account_handoff_verification.json` | 交接包机器验证结果 |
| `../xrd_robustness/reports/ai4science_cleanup_inventory_20260719.json` | 本次全工作区清理审计 |

## 研究历史与设计参考

| 文件 | 用途 |
|---|---|
| `PROJECT_JOURNEY.md` | 从 FerroAI、V6、V7、V8 到 V9.2/V9-T 的问题演进；其中日期化数字可能已被后续合同取代 |
| `CODEX_METHOD_UPDATE_V9_2_DUAL_TRACK_WITH_ARCHIVED_STRUCTURED_PERTURBATION.md` | V9.2 双轨科学问题、Gate、论文路线和封存边界的设计记录 |
| `CODEX_V9_2_ENGINEERING_WITH_ARCHIVED_STRUCTURED_PERTURBATION.md` | V9.2 工程阶段、交付物、测试和执行门禁的设计记录 |
| `FUTURE_RESEARCH_DIRECTIONS.md` | 后续研究储备及研究生申请表述 |
| `XRD_future_research_branches_2026-07-15.md` | 用户确认的未来研究支线日期快照 |
| `PROJECT_EXECUTION_PLAN_JUL_SEP_2026.md` | 早期 7--9 月路线，不能覆盖当前 V9-T 合同 |
| `V6_METHOD_AND_TRAINING_SPEC.md` | V6 PAMPT、训练方法、公平性与评价协议 |
| `V6_PHYSICS_EVIDENCE_AND_PROBABILITY_PLAN.md` | V6 文献、参数映射与概率敏感性 |
| `V6_EXTERNAL_CODE_REUSE_MEMO.md` | 外部代码审计与复用边界 |
| `KBSS_PROJECT_RELEVANCE.md` | KBSS 方法启发与不接入结论 |
| `LEGACY_FERROAI_REFERENCE.md` | FerroAI 方法拆解 |
| `archive/PROJECT_ORGANIZATION_REPORT_2026-07-04.md` | 早期项目组织与 MVP 快照 |

## 使用原则

1. 判断“现在能运行什么”时，以 `xrd_robustness/CODEX_HANDOFF.md`、配置、源代码、清单和当前验证报告的证据链为准。
2. 本目录中的 V9.2、V8 及更早文档用于解释“为什么这样设计”，不得覆盖 V9-T 当前合同；发生冲突时必须停止并重新审计。
3. V6/V7/V8/V9.2 文档保留为科学与工程证据，不因版本较旧而删除。
4. 未经用户在目标机器上明确授权，不启动调参、正式训练或测试集访问。
