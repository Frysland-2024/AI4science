# V9-T 真实域少样本适配交接补充

状态日期：2026-07-24。

> 本补充覆盖 RRUFF 真实域设计与工程状态。原 `CODEX_HANDOFF.md` 中关于模拟训练、台式机迁移、lambda Gate、0/7 和 0/15 的内容继续有效。

## 1. 冻结科学设计

旧的“真实谱只做完全 zero-shot final test”已在任何正式模型访问 RRUFF-70 之前修订。

```text
RRUFF-70 frozen source corpus
├── adaptation train: 21, 3 per crystal system
├── adaptation validation: 14, 2 per crystal system
└── final real test: 35, 5 per crystal system
```

核心比较仍是 Dynamic/Paired ERM、JS Consistency 和 Residual Class Decorrelation。三方法使用相同 support episode、相同 adaptation validation 和相同 CE 适配协议。

权威入口：

- `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`
- `docs/V9_METHOD_TRANSFER_ENGINEERING.md`
- `configs/real_adaptation.v9.method_transfer.json`
- `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`

## 2. 冻结本地 manifest

- `data/real_xrd/rruff70/manifests/rruff70_real_adaptation_split_v1.csv`
  - SHA-256 `32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455`
- `data/real_xrd/rruff70/manifests/rruff70_fewshot_episode_manifest_v1.csv`
  - SHA-256 `B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6`
- RRUFF-70 来源 manifest
  - SHA-256 `17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5`

这些 manifest 和谱图属于 Git-ignored 本地数据，不得提交。

## 3. 已实现

- fail-closed 合同审计：`scripts/audit_v9_real_adaptation_contract.py`；
- 只读计划入口：`scripts/run_v9_real_adaptation.py preflight|plan`；
- 核心审计模块：`src/xrd_robustness/evaluation/real_adaptation.py`；
- 单元测试：`tests/test_v9_real_adaptation_contract.py`。

审计和计划阶段：

- 不导入模型；
- 不加载谱图；
- 不访问 final real test；
- 检查 70 条样品、21/14/35、七类 3/2/5、episode 成员和 CSV SHA-256；
- 哈希或成员不一致时 fail closed。

计划规模：

- primary head-only CE：189 candidate runs、63 checkpoint-selection groups；
- zero-shot：9 evaluations；
- 同时包含 secondary full-network CE：378 candidate runs、126 groups。

## 4. 尚未实现

- 本地 manifest 复制到目标项目路径；
- approved simulation checkpoint loading；
- classifier-head adaptation trainer；
- adaptation-validation checkpoint selection；
- adapted checkpoint/result SHA-256 绑定；
- final-stage inference。

`run_v9_real_adaptation.py run` 必须返回 `refused_execution_disabled`。

## 5. 执行状态

```text
simulation_tuning = 0/7
formal_simulation = 0/15
simulated_test.enabled = false
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

## 6. 必须保持的顺序

1. 台式机工程验收；
2. 7-run Simulation Validation tuning；
3. 三核心方法正式模拟训练并冻结 checkpoint；
4. simulated Test 完成并冻结；
5. 真实适配训练实现、测试和严格 manifest preflight；
6. 单独授权 adaptation train/validation；
7. 冻结 adapted checkpoints；
8. 单独授权并一次性访问 35 条 final real test。

## 7. 当前安全命令

```powershell
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py --require-local-data
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan --include-secondary
```

真实数据训练和 final-test 推理仍需后续独立实现与授权。
