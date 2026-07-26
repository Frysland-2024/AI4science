# V9-T 算法迁移与真实域适配工程契约

> 2026-07-26 latest execution override: Validation now runs every 10 epochs /
> 6,160 optimizer steps with patience 2. The effective 20-epoch
> no-improvement window is unchanged. The superseded 5-epoch / patience-4
> partial run is isolated and does not count; all seven candidates restart from
> optimizer step 0 in the new output root.

> 2026-07-26 execution override: the complete frozen seven-candidate
> Validation-only grid is being rerun from optimizer step 0 with
> `max_epochs=100`, `max_optimizer_steps=61600`, Validation every 5 epochs
> (3,080 steps), `min_epochs=50`, `min_delta=0.001`, and patience 4. The
> selection monitor is mean single-factor Validation-OOD Macro-F1. Both best
> and last checkpoints are retained; ties use higher Validation-ID Macro-F1
> and then the earlier epoch. The historical 50-epoch selection is not the
> final selection under this new optimization contract.

> 2026-07-26 parent-structure split override: the former family-disjoint split
> and all results produced from it are retired. The active dataset uses a
> deterministic 70/15/15 parent-structure random split stratified by crystal
> system. New tuning is reset to 0/7 and restarts from experiment 1. The fresh
> current-split Train-only and authoritative runtime gates pass.

状态日期：2026-07-24。

## 1. 论文问题

V9-T 比较三种模拟预训练原则：

1. `ordinary_dynamic_augmentation`：Dynamic/Paired ERM；
2. `js_consistency_transfer`：JS Consistency；
3. `residual_decorrelation_transfer`：Residual Class Decorrelation。

核心问题是：在母结构、配对扰动视图、backbone、优化预算和模拟评测面板严格匹配时，JS 或 Residual 是否能在 Dynamic/Paired ERM 之上提高未知扰动泛化，并在少量真实标签适配后保持相对优势。

证据链冻结为：

```text
augmentation-only simulated pretraining
→ cross-view consistency / residual decorrelation
→ simulated OOD robustness
→ zero-shot experimental robustness
→ label-efficient experimental adaptation
```

本论文不声称创造新的通用机器学习理论。

## 2. 模拟实验保持不变

模拟数据仍使用 `formal_14060`：

| Split | 数量 | 用途 |
|---|---:|---|
| Train | 9,842 | 模拟训练和动态视图生成 |
| Validation | 2,109 | lambda、early stopping、checkpoint 和开发比较 |
| Test | 2,109 | 独立 simulated Test |

正式模拟实验仍是五方法 × 三 seed：Near-clean、Offline、Dynamic ERM、JS、Residual。真实少样本核心比较只使用 Dynamic ERM、JS 和 Residual。

三个核心方法在相同 seed 下必须共享母结构顺序、dynamic pair schedule、实际扰动 parameter-pair hash、optimizer steps、backbone forward 数和谱图曝光数。

## 3. Lambda 与模拟执行状态

候选范围已通过 Train-only Gate 并冻结：

```text
lambda_JS  ∈ {0.3, 3.0, 30.0}
lambda_res ∈ {0.2, 2.0, 20.0}
```

7-run 包含 Dynamic ERM 1 次、JS 三个 lambda 和 Residual 三个 lambda。调参只使用 Simulation Validation；真实数据不得参与 lambda、模拟 checkpoint 或模拟方法选择。

当前状态：

```text
simulation_tuning = 0/7
formal_simulation = 0/15
simulated_test.enabled = false
```

7-run 仍需台式机工程验收和用户单独授权。

## 4. simulated Test

真实适配需要保留三个核心方法的独立模拟证据，因此 simulated Test 不再只评估一个开发阶段胜者。进入 Test 前必须冻结：

- JS 与 Residual 最终 lambda；
- 三个核心方法各三个正式 checkpoint SHA-256；
- 源代码、配置和 Test manifest 哈希；
- Simulation Validation 结果。

simulated Test 结果不得回流修改方法、lambda 或 checkpoint。

## 5. RRUFF-70 与角色冻结

来源语料：`rruff-real-pxrd-70-v1.0-final`，七晶系各 10 条。

来源 manifest SHA-256：

```text
17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5
```

模型访问前，按

```text
SHA256(20260724 | crystal_system | sample_id)
```

在每个晶系内升序分配：

| 角色 | 每晶系 | 总数 |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

角色 manifest SHA-256：

```text
32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455
```

Episode manifest SHA-256：

```text
B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6
```

本地 manifest 与谱图保持 Git ignored；GitHub 只保存合同、代码和哈希。

## 6. 0/1/2/3-shot 设计

每类 adaptation-train 三条谱按冻结哈希排序为 rank 1/2/3：

- 0-shot：E0，无真实训练；
- 1-shot：E1=rank1、E2=rank2、E3=rank3；
- 2-shot：E1=(1,2)、E2=(1,3)、E3=(2,3)；
- 3-shot：E1=(1,2,3)。

同一 episode 必须跨方法和预训练 seed 完全一致。

## 7. 主真实适配

主分析固定为 head-only CE：

- encoder frozen；
- classifier head trainable；
- cross-entropy only；
- 不使用真实域 JS、Residual 或模拟器标签；
- AdamW；
- learning rate `[1e-4, 3e-4, 1e-3]`；
- weight decay `1e-4`；
- maximum epochs `200`；
- patience `30`；
- adaptation-validation Macro-F1 选 checkpoint；
- 并列时选择更小学习率，再选择更早 epoch。

次要分析预注册 full-network CE：learning rate `[1e-6, 3e-6, 1e-5]`、maximum epochs `100`、patience `20`。

## 8. 真实域统计

每个 shot 的主要效应：

```text
Delta_JS(s)  = MacroF1_JS(s)  - MacroF1_DynamicERM(s)
Delta_RES(s) = MacroF1_RES(s) - MacroF1_DynamicERM(s)
```

必须报告所有预训练 seed、所有 support episode、绝对指标、0-shot 到各 shot 的方法内提升、每类指标、混淆矩阵和按晶系分层的 paired bootstrap 95% CI。不得只报告最有利 shot 或 episode。

## 9. final real test

35 条 final-real-test 只能在以下条件全部满足后一次性访问：

1. 7-run 完成；
2. 正式模拟训练完成；
3. 三核心方法的 checkpoint 哈希冻结；
4. simulated Test 完成且不可变；
5. adaptation 合同审计、训练实现和单元测试通过；
6. 21/14 数据上的 adapted checkpoint 全部冻结；
7. 用户单独授权。

final real test 不得选择学习率、epoch、checkpoint、support episode 或样品排除规则。

## 10. GTIIT 边界

GTIIT 不进入 RRUFF 主适配 train、validation 或 final-test 聚合指标。它仅保留为本地仪器 supplementary case study，并继续要求去标识化、样品级标签证据、批次隔离、provenance 和单独授权。

## 11. 已实现的真实适配工程

已经实现：

- `configs/real_adaptation.v9.method_transfer.json`；
- `src/xrd_robustness/evaluation/real_adaptation.py`；
- `scripts/audit_v9_real_adaptation_contract.py`；
- `scripts/run_v9_real_adaptation.py` 的 `preflight` 与 `plan`；
- `tests/test_v9_real_adaptation_contract.py`。

合同审计只读取 JSON/CSV，不导入模型、不加载谱图。它验证：

- 70 条唯一样品；
- 21/14/35 总计数；
- 七晶系各 3/2/5；
- adaptation-train rank 1/2/3；
- episode 成员、类别平衡与哈希；
- final-test 样品不进入 support 或 validation；
- primary adaptation 必须是 head-only CE；
- 任何哈希不匹配都 fail closed。

计划器在不加载模型和谱图时生成：

- primary candidate runs：189；
- primary checkpoint-selection groups：63；
- zero-shot evaluations：9；
- 加入 secondary full-network 后 candidate runs：378，selection groups：126。

`run_v9_real_adaptation.py run` 当前必须拒绝执行并返回 `refused_execution_disabled`。

## 12. 尚未完成

- 将本地冻结 manifest 复制到项目 Git-ignored 路径；
- 在真实仓库运行 `--require-local-data` 严格审计；
- 实现 approved-checkpoint loading；
- 实现 classifier-head adaptation trainer；
- 实现 adaptation-validation checkpoint selection；
- 绑定 adapted checkpoint 与结果哈希；
- final-stage inference。

因此：

```text
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

## 13. 当前安全命令

```powershell
# 模拟预检与计划
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py preflight
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-plan

# 真实适配设计审计，不加载模型或谱图
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py

# 本地 manifest 就位后的严格审计
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\audit_v9_real_adaptation_contract.py --require-local-data

# 只生成计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_real_adaptation.py plan --include-secondary

# 单元测试
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -q
```
