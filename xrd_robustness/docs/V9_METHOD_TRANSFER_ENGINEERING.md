# V9-T 算法迁移与真实域适配工程契约

状态日期：2026-07-24。

当前身份仍是 **V9-T：Algorithm Transfer for PXRD Robustness**。本契约包含两段：

1. 完全受控的模拟预训练方法比较；
2. 0-shot 与 1/2/3-shot 真实域适配比较。

训练仍为 0/7 调参、0/15 正式模拟实验；simulated Test、真实适配和 final real test 均未执行。所有执行开关保持关闭。

## 1. 核心科学问题

在相同母结构、物理扰动视图、模型、优化预算和模拟评测面板下：

> 显式建模同一晶体结构不同扰动视图之间的关系——JS prediction consistency 或 residual class decorrelation——能否在 Dynamic/Paired ERM 之上，提高未知扰动泛化，并在少量真实标签适配后保持相对优势？

论文证据链固定为：

```text
augmentation-only supervised pretraining
→ cross-view consistency / residual decorrelation
→ simulated OOD robustness
→ zero-shot experimental robustness
→ label-efficient experimental adaptation
```

本论文不声称创造新的通用一致性理论或 residual 学习理论。

## 2. 五个模拟方法

正式模拟实验仍是五组、每组 3 个 seed，共 15 次：

1. `clean_erm_reference`：Near-clean ERM；
2. `offline_physical_augmentation_reference`：冻结四视图物理增广参考；
3. `ordinary_dynamic_augmentation`：Dynamic/Paired ERM，最强匹配直接基线；
4. `js_consistency_transfer`：JS Consistency；
5. `residual_decorrelation_transfer`：Residual Class Decorrelation。

真实域适配的核心比较只使用第 3、4、5 组。Near-clean 与 Offline 仍可报告 0-shot 参考，但不进入少样本核心效应。

## 3. 模拟数据与公平性

冻结 family-aware 划分：

| Split | 数量 | 用途 |
|---|---:|---|
| Train | 9,842 | 模拟训练和动态视图生成 |
| Validation | 2,109 | lambda、early stopping、checkpoint 和模拟开发比较 |
| Test | 2,109 | 独立 simulated Test |

三个核心方法在相同 seed 下必须共享：

- 母结构顺序；
- dynamic pair schedule；
- 实际接受的扰动参数 pair；
- optimizer steps；
- backbone forward 数；
- 谱图曝光数；
- 模拟评测 manifest。

Near-clean 与 Offline 的视图按定义不同，但计算预算和评测面板一致。

## 4. Lambda 候选与 7-run

候选范围已通过 Train-only Gate 并冻结：

```text
lambda_JS  ∈ {0.3, 3.0, 30.0}
lambda_res ∈ {0.2, 2.0, 20.0}
```

7-run 只做：

- Dynamic/Paired ERM 基线 1 次；
- JS 三个 lambda；
- Residual 三个 lambda。

调参 seed：`20260710`。主指标：六个单因素 OOD 的平均 Macro-F1；ID Macro-F1 相对 Dynamic ERM 下降不得超过 0.01；并列时选择更小 lambda。

7-run 的职责是分别冻结 JS 与 Residual 的 lambda，不使用真实数据，也不在这一阶段删除任何核心方法。

## 5. 15-run 正式模拟比较

冻结 lambda 后运行五方法 × 三 seed：

```text
20260711, 20260712, 20260713
```

必须报告：

- ID、六个单因素 OOD、三个未见组合和 `ood_all`；
- Accuracy、Balanced Accuracy、Macro-F1；
- per-class Recall/F1；
- confusion matrix；
- worst-group F1；
- 15-bin ECE；
- 每个 run 的完整 provenance 和 SHA-256 链。

正式 run 必须导出并哈希绑定 `prediction_rows.jsonl`。独立统计单位是母结构/family cluster；禁止只对三个 seed 汇总值 bootstrap。

## 6. 模拟方法效应

对 JS 与 Residual 分别报告相对 Dynamic/Paired ERM 的：

- 三 seed 平均差；
- 每个 seed 的配对差；
- family-level paired hierarchical bootstrap 95% CI；
- ID/OOD trade-off；
- 每个 OOD profile 的变化。

“Residual 优于 JS”必须直接计算 `Residual - JS`，不能由二者分别优于 ERM 推断。

## 7. simulated Test

simulated Test 使用锁定的 2,109 个 Test 结构、固定评测 seed 和完整扰动面板。

进入 simulated Test 前必须：

- JS 与 Residual lambda 冻结；
- 五方法三 seed checkpoint SHA-256 冻结；
- 所有模拟开发结果不可变；
- Test manifest 在推理前生成并冻结；
- 用户单独授权。

新真实适配协议需要三个核心方法的模拟 Test 结果全部保留，因此不得只测试一个开发阶段胜者。参考基线也应在计算允许时一起推理，因为这里只增加评估成本，不改变训练。

simulated Test 结果不得回流修改模拟方法、lambda 或 checkpoint。

## 8. RRUFF-70 真实语料

来源：`rruff-real-pxrd-70-v1.0-final`，70 条实验矿物粉末 PXRD，七晶系各 10 条。

来源 manifest SHA-256：

```text
17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5
```

统一预处理：10–80°、0.02°、线性插值、区间外填 0、max normalization；不扣基线、不平滑、不人工改峰。

## 9. 真实域 21/14/35 角色冻结

模型访问前，按

```text
SHA256(20260724 | crystal_system | sample_id)
```

在每个晶系内排序并分配：

| 角色 | 每晶系 | 总数 |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

角色 manifest SHA-256：

```text
32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455
```

few-shot episode manifest SHA-256：

```text
B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6
```

数据文件保持本地 Git ignored；GitHub 只保存合同和哈希。

## 10. 0/1/2/3-shot 支持集

每类 3 条 adaptation-train 样品按冻结哈希顺序编号 1/2/3：

- 0-shot：E0，无真实训练；
- 1-shot：E1=rank1，E2=rank2，E3=rank3；
- 2-shot：E1=(1,2)，E2=(1,3)，E3=(2,3)；
- 3-shot：E1=(1,2,3)。

同一 episode 必须跨方法、预训练 seed 和 adaptation implementation 完全一致。

## 11. 主真实适配：head-only CE

主分析固定为：

- 从每个核心方法和预训练 seed 的冻结 checkpoint 开始；
- encoder frozen；
- classifier head trainable；
- objective 为 cross-entropy only；
- 不使用真实域 JS、Residual 或模拟器标签；
- AdamW；
- learning rate candidates `[1e-4, 3e-4, 1e-3]`；
- weight decay `1e-4`；
- maximum epochs `200`；
- patience `30`；
- adaptation-validation Macro-F1 选择 checkpoint；
- tie breaker：更小学习率、再更早 epoch。

这样主要效应可以解释为模拟预训练表示的可适配性，而不是不同真实微调算法的混合效应。

## 12. 次要真实适配：full-network CE

预注册次要分析：

- encoder 与 classifier 全部训练；
- cross-entropy only；
- learning rate candidates `[1e-6, 3e-6, 1e-5]`；
- weight decay `1e-4`；
- maximum epochs `100`；
- patience `20`。

若资源不足而未执行，必须完整披露；不能根据主结果只运行有利方法或预算。

## 13. 真实域统计

每个 shot 的主要效应：

```text
Delta_JS(s)  = MacroF1_JS(s)  - MacroF1_DynamicERM(s)
Delta_RES(s) = MacroF1_RES(s) - MacroF1_DynamicERM(s)
```

必须报告：

- 绝对 Accuracy、Balanced Accuracy、Macro-F1；
- 0-shot 到各 shot 的方法内提升；
- 所有支持 episode 与预训练 seed；
- per-class Recall/F1 和 confusion matrix；
- final-test 样本层面、按晶系分层的 paired bootstrap 95% CI；
- 完整标签效率曲线。

## 14. final real test

35 条 final-real-test 只能在以下条件全部满足后一次性访问：

1. 7-run 完成；
2. 五方法正式模拟训练完成；
3. 三核心方法的 checkpoint 哈希冻结；
4. simulated Test 完成并不可变；
5. adaptation 代码、单元测试和 preflight 通过；
6. 21/14 数据上所有 adapted checkpoint 冻结；
7. 用户单独授权。

最后一次推理必须同时生成所有预注册的 0/1/2/3-shot、method、seed 和 episode 结果。final real test 不得选择学习率、epoch、checkpoint、支持样本或样品排除规则。

## 15. GTIIT 位置

GTIIT 不进入 RRUFF 主适配 train/validation/final-test 指标。它只保留为本地仪器 supplementary case study，并继续要求去标识化、样品级标签证据、批次隔离和单独授权。

## 16. 机器可读入口

- `configs/algorithm.v9.method_transfer.json`：当前模拟训练实现合同；
- `configs/evaluation.v9.method_transfer.json`：当前模拟与旧 real-test 执行锁；
- `configs/real_adaptation.v9.method_transfer.json`：新真实适配科学设计与 role/episode 哈希；
- `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md`：完整真实适配解释；
- `configs/v9_method_parameter_governance.json`：lambda 治理；
- `configs/simulation.v9.method_transfer.frozen.json`：模拟扰动；
- `configs/data.v9.method_transfer.family_split.json`：模拟划分。

当前 runner 尚未集成 `real_adaptation.v9.method_transfer.json`。若旧 algorithm/evaluation 配置中的“只选择一个方法进入 real test”与本契约冲突，必须 fail closed；不得运行任何真实数据。后续工程任务是更新 schema、runner、hash 引用和审计报告。

## 17. 当前执行状态

```text
simulation_tuning = 0/7
formal_simulation = 0/15
simulated_test.enabled = false
real_adaptation.execution_enabled = false
final_real_test.enabled = false
```

科学修订已经冻结，但工程集成尚未完成。

## 18. 当前允许命令

```powershell
# 只读模拟预检
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py preflight

# 生成调参计划，不训练
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py tune-plan

# final-stage 锁检查
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s scripts\run_v9_method_transfer.py final-preflight

# 单元测试
E:\AI4science\.venvs\xrd_tools\Scripts\python.exe -s -m unittest discover -s tests -q
```

尚未实现、不得假装运行：

```text
scripts/audit_v9_real_adaptation_contract.py
scripts/run_v9_real_adaptation.py
```
