# V9 数据、物理模拟与真实域适配统一契约

状态日期：2026-07-24。

本文件服务于 V9-T 算法迁移论文，并保留 V10 Simulator-Supervised Representation Learning 可复用的模拟基础。机器可读配置、schema、manifest 与匹配哈希是执行时最终约束。

## 1. 模拟数据粒度与划分

一条正式模拟样本对应一个 Materials Project 晶体结构，而不是一张动态生成谱图。当前正式池为 `data/formal_14060`：

- Train 9,842；
- Validation 2,109；
- Test 2,109。

划分以 parent structure 为唯一单位，采用固定随机种子的 70% / 15% / 15% 随机抽样，并仅按七晶系分层。`family_id` 可用于分析，但不得参与划分决策。

同一 `parent_structure_id` 的所有 clean、weak、strong、ID、OOD 谱图必须留在同一个 split。动态视图在完成母结构划分后在线生成并继承母结构 split。Test 在方法、超参数和 checkpoint 冻结前不得评估。

正式结构记录至少保存：`material_id`、化学式、原始/标准化结构、MP 与重算空间群、七晶系、位点数、稳定性、hull energy、结构指纹和 split。排除无序/部分占位结构、空间群复核不一致项和 exact-cell 重复项。

## 2. 缓存与动态视图

允许持久化的模拟中间量只有理想峰位、理想积分强度和 reflection metadata：hkl、多重性、倒易矢量与峰映射。禁止把渲染后的固定谱或扰动谱当成新的独立结构样本。

每个动态视图必须可重放，至少记录母结构、view ID、simulation seed、五类扰动参数及激活状态、生成顺序、配置哈希和代码版本。同一 seed 下的公平比较复用完全相同的配对视图。

## 3. 五类扰动及边界

当前物理算子为：

1. 全局 `2theta` 零点偏移；同一谱的所有峰位加同一标量；
2. 有效峰展宽；当前标量 Gaussian FWHM 是工程近似，不是完整仪器函数；
3. March-Dollase 择优取向；修改反射积分强度，不移动峰位；
4. 平滑非负背景；
5. Poisson 计数与可选电子读出噪声。

`apply_probability` 是在线生成中的算子覆盖控制，不是某台仪器中的经验发生频率。它必须与扰动幅度范围和物理来源分开记录。

## 4. 背景与噪声

背景与噪声是两个独立物理效应。观测链为：

\[
I_{expected,i}=I_{Bragg,i}+B_i,
\]

\[
C_i\sim\operatorname{Poisson}(gI_{expected,i}),\qquad
I_{obs,i}=\operatorname{clip}(C_i/g+\epsilon_{elec,i},0).
\]

随后才进行模型输入归一化。背景不得用逐点独立噪声生成；电子噪声出现负随机值时只在观测后由非负裁剪处理。

## 5. 设备无关与证据来源

模拟参数不拟合任何一台本地仪器。参数来源按以下优先级登记：

1. 同行评议 PXRD 文献；
2. 论文实际使用的开源模拟代码；
3. 有明确单位、公式和适用边界的物理约束；
4. 仅在负责人明确批准时使用真实仪器数据。

每个正式扰动字段必须至少具有一个非空的 `literature_source`、`code_source` 或 `physics_basis`。真实域适配数据不得回流定义模拟扰动范围、lambda 或模拟 checkpoint。

## 6. RRUFF-70 真实数据语料

来源语料固定为 `rruff-real-pxrd-70-v1.0-final`：70 条实验矿物粉末 PXRD，七晶系各 10 条。

来源 manifest SHA-256：

```text
17236DA1654E43370034DB6F7391C5882583FFAF62147856B8A85D79BC1174C5
```

真实谱预处理固定为：

- `2theta` 10–80°；
- 步长 0.02°；
- 线性插值；
- 区间外填 0；
- max normalization；
- 不扣基线；
- 不平滑；
- 不人工修改峰。

## 7. 真实域角色冻结

在任何模型访问前，按

```text
SHA256(20260724 | crystal_system | sample_id)
```

在每个晶系内排序并冻结：

| 角色 | 每晶系 | 总数 |
|---|---:|---:|
| adaptation train | 3 | 21 |
| adaptation validation | 2 | 14 |
| final real test | 5 | 35 |

角色 manifest：

```text
data/real_xrd/rruff70/manifests/rruff70_real_adaptation_split_v1.csv
SHA256 32C63334CF8EBEAC4CBE109E273E409345C5998C4247E867D464836B92EA4455
```

few-shot episode manifest：

```text
data/real_xrd/rruff70/manifests/rruff70_fewshot_episode_manifest_v1.csv
SHA256 B38CE6083CE2F0D181C7E0B597112C0CAB852B9B8F92D9C77EDBACA7359EB0E6
```

上述数据文件属于 Git 忽略的本地数据区，不得提交 GitHub。

## 8. 真实域允许和禁止的用途

允许：

- `adaptation_train` 用于 1/2/3-shot 真实域适配；
- `adaptation_validation` 用于适配 early stopping、学习率和适配 checkpoint 选择；
- `final_real_test` 在所有适配 checkpoint 冻结后一次性评估 0/1/2/3-shot。

禁止：

- 真实数据定义模拟参数或 lambda；
- 真实适配结果回头选择模拟预训练方法或 checkpoint；
- final real test 选择学习率、epoch、support episode 或样品；
- 根据模型预测删除、更换或重新标注 final-test 样品；
- 只报告最有利的 shot、episode 或 seed。

## 9. 三方法适配公平性

Dynamic/Paired ERM、JS 与 Residual 必须使用：

- 相同 support episode；
- 相同 adaptation validation；
- 相同 CE 目标；
- 相同优化器和候选范围；
- 相同训练预算与 early-stopping 规则。

主适配冻结 encoder，只更新 classifier head。真实适配主分析不启用 JS 或 Residual 辅助损失，以免把“模拟预训练原则差异”和“真实微调算法差异”混在一起。

完整协议见 `docs/V9_REAL_FEWSHOT_ADAPTATION_PROTOCOL.md` 和 `configs/real_adaptation.v9.method_transfer.json`。

## 10. GTIIT 数据边界

GTIIT 数据不进入 RRUFF adaptation train、validation 或 final-test 总指标。它只可作为独立的本地仪器 supplementary case study，并继续要求：

- 去标识化；
- 样品级标签证据；
- 批次和重复样品隔离；
- provenance manifest；
- 单独授权。

## 11. 当前执行锁

科学设计和 RRUFF 角色哈希已经冻结，但真实适配代码尚未实现。因此：

- `real_adaptation.execution_enabled = false`；
- final real test 继续 locked；
- 任何真实数据训练和推理都需要独立工程 preflight 与用户授权。
