# CODEX 数据集划分更新说明：取消 Gate 集并合并为 Validation 集

> **历史文档警告（2026-07-26）：**本文保留的是取消 Gate 时的旧划分记录，不是当前执行合同。family-aware 划分也已退役。当前 V9-T 使用 parent-structure-level 70/15/15 随机分层划分；请以 `../CODEX_HANDOFF.md`、`../configs/data.v9.method_transfer.structure_split.json` 和当前 split 审计为准。

## 1. 更新目的

取消原方案中的独立 **方法 Gate 集**。

原来的：

- λ 调参集：1,066 个结构
- 方法 Gate 集：1,064 个结构

现统一合并为一个完整的：

- **Validation 集：2,130 个结构**

不再保留单独的 Gate 数据集或 Gate 判定流程。

---

## 2. 最终数据集划分

总数据量为 **14,060 个唯一晶体结构**，覆盖七种基本均衡的晶系。

| 数据集 | 结构数 | 用途 |
|---|---:|---|
| Train | 9,800 | 模型训练 |
| Validation | 2,130 | 超参数选择、early stopping、checkpoint 选择与开发阶段方法比较 |
| Test | 2,130 | 方法完全冻结后的最终评测 |
| 总计 | 14,060 | — |

其中：

- Train 每个晶系固定为 **1,400 个结构**
- Validation 和 Test 继续保持七晶系基本均衡
- 所有划分必须在**唯一晶体结构层面**完成

---

## 3. Validation 集的新职责

合并后的 Validation 集统一承担以下任务：

1. 选择 residual decorrelation loss 的权重 λ
2. 选择其他预先允许调整的训练超参数
3. 执行 early stopping
4. 选择最佳 checkpoint
5. 在开发阶段比较：
   - 普通数据增广基线
   - residual decorrelation 方法
   - 其他预先定义的对照方法

不再设置“方法是否通过 Gate”的独立数据判断。

---

## 4. Test 集使用规则

Test 集必须保持锁定，仅在以下条件全部满足后使用：

- 模型结构冻结
- 数据扰动方案冻结
- λ 和其他超参数冻结
- checkpoint 选择规则冻结
- 对照组设计冻结
- 评测指标冻结

Test 集不得用于：

- 调整 λ
- 修改模型结构
- 选择 checkpoint
- 调整扰动参数
- 决定是否保留某个方法模块

Test 只负责生成最终论文结果。

---

## 5. 数据隔离要求

必须严格保证结构级数据隔离：

- 同一个 CIF 及其所有模拟谱只能属于一个数据集
- 同一结构产生的 clean、weak、strong、OOD 或其他扰动版本必须跟随母结构所在的数据集
- 不允许先生成大量扰动谱后再按谱随机划分
- 应先划分唯一结构，再分别在 Train、Validation、Test 内部生成对应谱图
- 近重复结构、重复 Materials Project 条目或同源结构应尽可能去重或分组后再划分

---

## 6. 代码修改要求

请在当前项目中完成以下修改：

### 6.1 删除 Gate 相关内容

删除或停用所有与以下内容相关的配置、脚本和逻辑：

- `gate_set`
- `method_gate`
- `gate_loader`
- `gate_metric`
- `gate_threshold`
- `gate_pass`
- `gate_fail`
- 独立 Gate manifest
- 独立 Gate 评测脚本
- 依赖 Gate 结果决定后续实验的流程

如果旧文件需要保留用于审计，请移动到 archive，并明确标记为 deprecated，不得再被正式实验调用。

### 6.2 合并 Validation 数据

将原：

- λ 调参集 1,066 个结构
- Gate 集 1,064 个结构

合并为：

- Validation 2,130 个结构

更新所有：

- split manifest
- dataset config
- dataloader
- training script
- evaluation script
- README
- 实验协议文件
- 统计报告

### 6.3 保持 Test 不变

Test 仍为 2,130 个结构，不得与合并后的 Validation 重叠。

### 6.4 输出划分审计报告

请生成一份新的 split audit，至少包含：

- Train / Validation / Test 的结构总数
- 每个晶系在三个集合中的数量
- 三个集合之间的结构 ID 交集检查
- 重复结构检查
- 母结构与其扰动谱归属一致性检查
- split seed
- split manifest hash
- 数据配置 hash

所有交集应为 0。

---

## 7. 最终冻结结论

本项目正式采用以下数据划分：

```text
Train      = 9,800
Validation = 2,130
Test       = 2,130
Total      = 14,060
```

取消独立 Gate 集。

Validation 统一负责超参数选择、early stopping、checkpoint 选择和开发阶段方法比较；Test 仅用于方法完全冻结后的最终评测。
