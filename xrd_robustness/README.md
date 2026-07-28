# XRD Robustness V9-T

> **2026-07-28 JS-only scale Gate:** The shared backbone contract is frozen as
> ResNet-18-GN + identity + AdamW + constant LR, with Dynamic ERM as the strong
> baseline. Residual-v1 is archived after its stability Gate failed. The
> Train-only JS revision `[3,30,60]` passed weak/material/dominant scale and
> combined-gradient guards, so this JS grid is frozen. No candidate training,
> Validation/Test/real-XRD access, or four-run tuning occurred; execution
> remains disabled pending separate authorization.

> **2026-07-28 CNN Clean diagnostics:** A/B/C single-factor search is complete.
> Sqrt, Adam, and warm-up/cosine did not beat the ResNet identity + AdamW +
> constant-LR baseline. Clean search is closed. The one matched Dynamic ERM
> diagnostic then improved level0/in-range/mean single-factor OOD to
> `0.7197/0.7179/0.6563`, passing the CNN foundation diagnostic Gate. Formal
> 7-run, Test, real XRD, and V10 remain locked pending shared-contract review.

> **2026-07-26 split reset:** The active split is a deterministic 70/15/15
> parent-structure-level random split stratified by crystal system (seed
> `20260726`). All results from the retired family-disjoint split are invalid.
> New tuning is reset to 0/7 and restarts from experiment 1. The current-split
> Train-only Gate and authoritative runtime checks pass.

> 跨机器、跨 Codex 账号接管先阅读 [`CODEX_HANDOFF.md`](CODEX_HANDOFF.md)；真实域少样本设计再阅读 [`CODEX_HANDOFF_REAL_ADAPTATION_ADDENDUM.md`](CODEX_HANDOFF_REAL_ADAPTATION_ADDENDUM.md)。这些文档均不构成训练或测试授权。

## 当前研究身份

当前唯一主线仍是 **V9-T：Algorithm Transfer for PXRD Robustness**。

模拟阶段比较三种核心学习原则：

1. Dynamic/Paired ERM：单纯动态增广监督；
2. JS Consistency：跨视图预测一致性；
3. Residual Class Decorrelation：差异感知的残差类别去相关。

论文现在包含两层真实域证据：

- **0-shot real robustness**：完全不使用真实标签；
- **few-shot real adaptation**：三方法使用完全相同的少量真实标签后，比较相对增益和标签效率。

项目仍不声称创造新的通用机器学习理论；核心是严格匹配条件下的跨领域方法迁移和 PXRD 特定验证。

## 当前状态（2026-07-26）

| 阶段 | 状态 |
|---|---|
| 14,060 结构 parent-structure 随机分层划分 | 冻结：Train 9,842 / Validation 2,109 / Test 2,109 |
| 方法参数候选范围 | 冻结：JS `[0.3,3,30]`；Residual `[0.2,2,20]` |
| Simulation Validation tuning | **旧 50-epoch endpoint 7/7 已归档；新合同为最多 100 epoch、每 10 epoch Validation、patience 2，完整网格从 0/7 重启** |
| 正式模拟实验 | **0/15，未开始** |
| simulated Test | 锁定、未执行 |
| RRUFF-70 样品组成 | 冻结 |
| RRUFF 真实域角色划分 | 冻结：21 train / 14 validation / 35 final test |
| real-adaptation 合同审计与计划生成 | 已实现，禁止加载模型或谱图 |
| real-adaptation 训练器 | 尚未实现 |
| 真实适配与 final real test | 均锁定、未执行 |
| V10 Train-only 诊断 | P0 `PASS`、Pilot v1 `HOLD`、Pilot v2 `PARTIAL`；已冻结归档 |

## 核心论文问题

在相同母结构、动态配对视图、backbone、最大优化预算、early-stopping 规则和模拟评测面板下：

> JS Consistency 或 Residual Class Decorrelation 能否在 Dynamic/Paired ERM 之上，提高未知扰动泛化，并在 0/1/2/3-shot 真实域适配中保持相对优势？

真实数据提高三种方法的绝对准确率是允许且预期的。公平性来自：

- 同一个 RRUFF support episode；
- 同一个 adaptation validation；
- 同一个 CE 适配目标；
- 同一优化与 early-stopping 规则；
- final real test 完全隔离。

## RRUFF-70 真实域协议

来源语料：`rruff-real-pxrd-70-v1.0-final`，七晶系各 10 条。

模型访问前按固定 SHA-256 规则冻结为：

| 角色 | 每晶系 | 总数 |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

少样本预算为 0/1/2/3-shot。1-shot 和 2-shot 各有 3 个固定 support episode；3-shot 使用全部 21 条 adaptation train。

主适配实验固定为：冻结 encoder、只更新 classifier head、cross-entropy only。全模型 CE 微调作为预注册次要分析。

完整合同：

- `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`
- `configs/real_adaptation.v9.method_transfer.json`

本地数据 manifest 和谱图属于 Git 忽略数据，不得提交。

## GTIIT 数据边界

GTIIT 不进入 RRUFF 主适配训练、验证或最终 Macro-F1。当前只保留为本地仪器 supplementary case study，且必须先完成样品标签、批次、隐私和 provenance 审计。

## 文档入口

- `docs/V9_METHOD_TRANSFER_ENGINEERING.md`：模拟算法迁移、lambda、五组实验、公平性和执行门禁；
- `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`：RRUFF-70 的 21/14/35 划分、0/1/2/3-shot 与适配统计；
- `docs/DATA_AND_SIMULATION_CONTRACT.md`：模拟与真实数据统一边界；
- `docs/V9_SIMULATOR_SUPERVISED_RESIDUAL_ENGINEERING.md`：V10 工程备忘；
- `docs/V10_MODULE_ARCHIVE_AND_FUTURE_DIRECTIONS.md`：V10 Train-only
  负结果、架构级结论与重启条件；
- `CODEX_HANDOFF.md`：模拟训练与台式机接管；
- `CODEX_HANDOFF_REAL_ADAPTATION_ADDENDUM.md`：真实域新协议交接。

机器可读配置、源代码和匹配哈希报告优先于解释性文档。真实适配训练器仍不存在，因此真实数据训练和 final-test 推理仍不能运行。

本地新增 opXRD/SIMPOD 文献、数据和第三方源码的 Git-safe 元数据索引位于
`../00_project_context/LITERATURE_LOCAL_RESOURCE_INDEX.md`。PDF、数据集、
ZIP 和外部源码树不进入 Git，也不构成当前 V9 的训练或评测输入。

## 模拟数据流程

```text
Materials Project structures
  -> formal_14060 parent-structure split
  -> ideal reflection cache
  -> paired online physical perturbations
  -> PAMPT-B3 + ERM / JS / Residual
  -> Simulation Validation tuning
  -> formal checkpoints
  -> simulated Test
```

## 真实域流程

```text
Frozen core-method checkpoints
  -> RRUFF adaptation train / validation
  -> 0/1/2/3-shot CE adaptation
  -> freeze adapted checkpoints
  -> one immutable evaluation on 35-sample final real test
```

## 当前安全命令

```powershell
# 只读模拟预检
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py preflight

# 仅生成 7-run 计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-plan

# 当前已授权的 100-epoch 上限、每 10 epoch Validation、patience 2 的七条串行调参队列
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-run --confirm-development-tuning --max-parallel-runs 1

# 检查 Test 锁
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py final-preflight

# 真实适配合同审计；不加载模型或谱图
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py

# 本地 manifest 已复制后执行严格哈希与成员审计
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py --require-local-data

# 仅生成 primary head-only 适配计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan

# 同时生成预注册 secondary full-network 计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan --include-secondary

# 单元测试
$env:PYTHONPATH='E:\AI4science\xrd_robustness\src'
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -p 'test_*.py' -v
```

`run_v9_real_adaptation.py run` 当前必须返回 `refused_execution_disabled`，并保证 `model_loaded=false`、`spectra_loaded=false`。

下一项工程任务是复制本地冻结 manifest、在目标仓库运行严格 preflight，并实现 classifier-head adaptation trainer、adaptation-validation checkpoint 选择与结果哈希绑定；完成这些工作仍不自动授权真实适配训练。
