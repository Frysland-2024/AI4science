# V9-T 真实域少样本适配交接补充

状态日期：2026-07-24

> 本补充只覆盖 RRUFF 真实域评测设计。原 `CODEX_HANDOFF.md` 中关于模拟训练、台式机迁移、lambda Gate、0/7 和 0/15 状态的内容继续有效。

## 当前新增决定

旧的“真实谱只作为完全 zero-shot final test”设计已在任何正式模型访问 RRUFF-70 之前修订。

当前真实域协议是：

```text
RRUFF-70 frozen source corpus
├── adaptation train: 21, 3 per crystal system
├── adaptation validation: 14, 2 per crystal system
└── final real test: 35, 5 per crystal system
```

权威设计入口：

- `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`
- `configs/real_adaptation.v9.method_transfer.json`
- `00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`

本地冻结 manifest：

- `data/real_xrd/rruff70/manifests/rruff70_real_adaptation_split_v1.csv`
  - SHA-256 `32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455`
- `data/real_xrd/rruff70/manifests/rruff70_fewshot_episode_manifest_v1.csv`
  - SHA-256 `B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6`

这些 manifest 和谱图属于 Git 忽略的本地数据，不得提交。

## 科学问题

在完全相同的真实支持样本、验证集、适配目标和计算预算下，比较：

1. Dynamic/Paired ERM simulation pretraining；
2. JS Consistency simulation pretraining；
3. Residual Class Decorrelation simulation pretraining。

主要真实域适配固定为：

- encoder frozen；
- classifier head trainable；
- cross-entropy only；
- 0/1/2/3-shot；
- 三方法共享 support episodes。

## 执行边界

当前只完成科学协议、角色哈希和 episode 哈希冻结。

以下内容尚未完成：

- `scripts/run_v9_real_adaptation.py`；
- `scripts/audit_v9_real_adaptation_contract.py`；
- 真实适配单元测试；
- 本地 manifest 复制和 preflight；
- 任何真实适配训练；
- final real test。

因此：

```text
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

不得因为本文件已经登记设计，就提前运行真实数据。

## 必须保持的顺序

1. 台式机工程验收；
2. 7-run Simulation Validation tuning；
3. 三核心方法正式模拟训练并冻结各自 checkpoint；
4. simulated Test 完成并冻结；
5. 真实适配实现、测试和哈希 preflight；
6. 单独授权 adaptation train/validation；
7. 冻结所有 adapted checkpoints；
8. 单独授权并一次性访问 35 条 final real test。

## 与旧交接文件冲突时

- 模拟训练、lambda、迁移、硬件和 checkpoint 规则：使用原 `CODEX_HANDOFF.md`；
- 真实谱只能 zero-shot 的旧表述：由本补充和新 real-adaptation 协议取代；
- 机器可执行状态：仍以当前代码和配置中的 execution lock 为准。
