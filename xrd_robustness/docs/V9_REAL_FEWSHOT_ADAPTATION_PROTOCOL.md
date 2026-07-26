# V9-T 真实域少样本适配协议

状态日期：2026-07-24  
协议状态：**scientific design frozen; role assignment frozen; execution disabled**

## 1. 研究目的

V9-T 保留原有三方法受控比较：

1. `ordinary_dynamic_augmentation`：Dynamic/Paired ERM；
2. `js_consistency_transfer`：JS Consistency；
3. `residual_decorrelation_transfer`：Residual Class Decorrelation。

新增的真实域问题不是“真实数据能否救活模型”，而是：

> 在三种模拟预训练方法使用完全相同的少量真实标签、相同适配目标、相同支持样本、相同验证集和相同计算预算时，JS 或 Residual 是否仍能相对 Dynamic/Paired ERM 提供更高的真实域准确率和更好的标签效率？

因此论文形成两层证据：

- **0-shot robustness**：完全不使用真实标签时的真实域泛化；
- **few-shot adaptation efficiency**：使用 1/2/3 个每类真实样本适配后的相对增益。

绝对准确率可以因真实数据适配而提高；科学比较对象仍是三种预训练原则之间的相对差异。

## 2. RRUFF-70 来源语料与冻结角色

来源语料保持不变：`rruff-real-pxrd-70-v1.0-final`，共 70 条实验矿物粉末 PXRD，七晶系各 10 条。

在任何模型访问前，使用以下确定性规则分配角色：

```text
SHA256(20260724 | crystal_system | sample_id)
```

每个晶系按哈希升序排列并分配：

| 角色 | 每晶系 | 总数 | 用途 |
|---|---:|---:|---|
| `adaptation_train` | 3 | 21 | 少样本真实域适配 |
| `adaptation_validation` | 2 | 14 | 适配 early stopping、适配 checkpoint 与共享协议选择 |
| `final_real_test` | 5 | 35 | 一次性最终真实测试 |

冻结文件位于本地、Git 忽略的数据区：

- `data/real_xrd/rruff70/manifests/rruff70_real_adaptation_split_v1.csv`
  - SHA-256: `32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455`
- `data/real_xrd/rruff70/manifests/rruff70_fewshot_episode_manifest_v1.csv`
  - SHA-256: `B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6`
- 来源 70 条 manifest SHA-256:
  - `17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5`

这些数据文件不得提交到 GitHub；仓库只保存合同、哈希和执行边界。

## 3. 嵌套少样本预算

`adaptation_train` 中每个晶系的 3 条样品按冻结哈希顺序标记 rank 1/2/3。

| 预算 | Episode | 每晶系支持样本 |
|---|---|---|
| 0-shot | E0 | 无真实训练样本 |
| 1-shot | E1 / E2 / E3 | 分别使用 rank 1 / 2 / 3 |
| 2-shot | E1 / E2 / E3 | 分别使用 (1,2) / (1,3) / (2,3) |
| 3-shot | E1 | 使用 (1,2,3) |

同一个 shot/episode 的支持样本必须在 Dynamic ERM、JS、Residual 及所有预训练 seed 间完全一致。

## 4. 模拟预训练阶段保持不变

真实域协议不改变以下已经冻结的模拟阶段：

- 9,842 / 2,109 / 2,109 parent-structure 随机分层划分；
- Dynamic/Paired ERM、JS、Residual 的配对谱图流与计算预算；
- JS `[0.3, 3.0, 30.0]`、Residual `[0.2, 2.0, 20.0]` 候选范围；
- 7-run Simulation Validation-only tuning；
- 3 个正式预训练 seed；
- simulated Test 的独立锁。

但最终真实比较不再只保留一个方法。进入真实域阶段前，必须分别冻结三个核心方法的：

- 最终超参数；
- 三个预训练 checkpoint SHA-256；
- 模拟 Validation 和 simulated Test 结果；
- 源代码与配置哈希。

真实结果不得用于回头选择模拟预训练方法或修改模拟超参数。

## 5. 主适配实验：统一 CE 头部适配

主分析固定为：

> 保留各方法模拟预训练所得 encoder 与 classifier 初始化，只使用真实标签交叉熵；冻结 encoder，仅更新分类头。

目的：最大程度把差异归因于模拟预训练表示，而不是把真实域中的 JS/Residual 算法再次混入比较。

统一要求：

- 三方法使用同一支持 episode；
- 同一优化器、批处理、epoch 上限、early-stopping 规则和验证指标；
- 真实域不使用 JS、Residual、模拟器标签或额外无标签真实谱；
- 不根据 final real test 选择学习率、epoch、checkpoint 或样品；
- 分类标签仍为七晶系。

共享候选协议：

- optimizer: AdamW；
- classifier-head learning rate candidates: `[1e-4, 3e-4, 1e-3]`；
- weight decay: `1e-4`；
- maximum epochs: `200`；
- patience: `30`；
- checkpoint metric: adaptation-validation Macro-F1；
- tie breaker: 更小学习率，其次更早 epoch；
- batch policy: 每个 epoch 使用全部支持样本，按类均衡并确定性打乱。

每个方法、预训练 seed 和支持 episode使用同一候选集合和同一选择规则。候选合法性必须在只读 preflight 中通过后才能执行。

## 6. 次要适配实验：统一全模型微调

全模型 CE 微调是预注册次要分析，不取代头部适配主结论：

- encoder 与 classifier 全部可训练；
- 仅使用交叉熵；
- learning rate candidates: `[1e-6, 3e-6, 1e-5]`；
- weight decay: `1e-4`；
- maximum epochs: `100`；
- patience: `20`；
- 其他选择规则与主实验一致。

若计算资源不足，论文必须明确标记该分析为未执行，不能依据主实验结果临时决定只运行有利的预算或方法。

## 7. 最终评测顺序

必须按以下顺序执行：

1. 完成 7-run 模拟调参；
2. 完成三核心方法的正式模拟训练并冻结 checkpoint；
3. 完成 simulated Test 并冻结结果；
4. 冻结真实适配代码、候选协议和所有 role/episode manifest 哈希；
5. 只读取 21 条 adaptation train 与 14 条 adaptation validation；
6. 完成全部预注册适配 run 并冻结适配 checkpoint；
7. 最后一次性对 35 条 `final_real_test` 同时生成 0-shot 与 1/2/3-shot 结果；
8. final real test 结果不得回流改变方法、协议、支持样本或 checkpoint。

## 8. 主指标与统计

每个 shot 预算的主要效应为：

```text
Delta_JS(s)  = MacroF1_JS(s)  - MacroF1_DynamicERM(s)
Delta_RES(s) = MacroF1_RES(s) - MacroF1_DynamicERM(s)
```

必须同时报告：

- 绝对 Accuracy、Balanced Accuracy、Macro-F1；
- 每类 Recall/F1 与混淆矩阵；
- 0-shot 到各 shot 的方法内绝对提升；
- JS/Residual 相对 Dynamic ERM 的同 episode 配对差；
- 三个预训练 seed 和支持 episode 的全部结果；
- 以 final-test 样本为单位、按晶系分层的 paired bootstrap 95% CI；
- 标签效率曲线，不只报告最佳 shot。

不得把单次支持样本选择、单个 seed 或最有利 shot 当作唯一结果。

## 9. GTIIT 的位置

GTIIT 数据不进入 RRUFF 主适配训练、验证或最终指标。其当前角色保持为：

- 本地仪器 supplementary case study；
- 仅使用标签和样品证据充分的少量样品；
- 不用于选择真实适配协议；
- 不与 RRUFF-35 final test 合并计算总 Macro-F1。

## 10. 当前执行状态

- RRUFF-70 样品组成：冻结；
- 21/14/35 角色分配：冻结；
- few-shot episodes：冻结；
- GitHub 科学协议：已登记；
- 本地数据文件：需复制到 Git 忽略路径并由哈希 preflight 验证；
- 适配训练代码：尚未实现；
- 真实域执行：`disabled`；
- final real test：继续锁定。

本协议是对旧“真实谱只能作为完全 zero-shot final test”设计的前瞻性修订。修订发生在任何正式模型访问 RRUFF-70 之前，因此不构成基于结果的事后改题。
