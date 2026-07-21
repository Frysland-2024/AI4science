# V9.2 双轨工程实施规范

**文件定位**：V9.2 双轨科学方案的工程落地文件  
**版本日期**：2026-07-16（V9.2；加入结构化扰动封存规范）  
**当前数据规模**：14,060 个去重候选晶体结构  
**执行目标**：先建共享管线，再以最小成本同时验证机制路线 A 与算法迁移路线 B，最终只扩张一条主线。

---

# 0. 工程总原则

1. **共享基础设施先于方法分叉**；
2. **Pilot 先于全量训练**；
3. **Gate 先于论文叙事**；
4. **所有方法匹配数据与计算预算**；
5. **真实谱只用于冻结后的最终验证，不参与反复调参**；
6. **旧版本代码和配置只读保留，不删除**；
7. **任何正式结果都必须可由 config、manifest、commit 和 seed 完整复现**。

---

# 1. 推荐仓库结构

```text
xrd_robustness/
├── configs/
│   ├── common/
│   │   ├── data.v9.json
│   │   ├── simulator.f0.json
│   │   ├── simulator.f1.json
│   │   ├── train.common.v9.json
│   │   └── evaluation.v9.json
│   ├── track_a/
│   │   ├── a1_sim_supervised_residual.json
│   │   └── a2_conditional_leakage.json
│   └── track_b/
│       ├── b1_js_consistency.json
│       └── b2_residual_decorrelation.json
├── data/
│   ├── manifests/
│   ├── base_patterns.h5
│   ├── peak_tables/
│   ├── metadata.parquet
│   ├── eval_panels/
│   └── real_xrd/
├── src/
│   ├── data/
│   ├── simulation/
│   ├── models/
│   ├── losses/
│   ├── probes/
│   ├── evaluation/
│   └── logging/
├── tests/
├── scripts/
│   ├── build_manifests.py
│   ├── cache_base_patterns.py
│   ├── build_eval_panels.py
│   ├── run_pilot.py
│   ├── run_branch_a.py
│   ├── run_branch_b.py
│   └── make_branch_report.py
└── reports/
```

---

# 2. 结构划分与数据资产

## 2.1 正式结构级 split

建议：

| Split | 结构数 |
|---|---:|
| Train | 11,248 |
| Validation | 1,406 |
| Test | 1,406 |

执行顺序：

```text
结构指纹去重
→ source ID 分组
→ 七晶系分层
→ 生成 manifest
→ 生成 SHA256
→ 冻结
```

输出：

```text
data/manifests/train.v9.csv
data/manifests/val.v9.csv
data/manifests/test.v9.csv
data/manifests/split_report.v9.json
```

## 2.2 Pilot split

从正式 split 内部抽取：

| Pilot split | 结构数 |
|---|---:|
| Train | 2,000 |
| Validation | 500 |

要求：

- 按七晶系分层；
- 不改变正式 split；
- Pilot 结果不进入论文主表；
- Pilot 只用于 Gate、吞吐和少量超参数冻结。

## 2.3 永久缓存

每个结构预计算：

- canonical structure ID；
- crystal system；
- peak table；
- base pattern；
- structure fingerprint；
- source ID；
- simulator-compatible metadata。

禁止训练时每 step 重新解析 CIF 或重做完整晶体学计算。

---

# 3. 条件描述与模拟器级别

## 3.1 Pilot 条件向量

```text
m = [shift, broadening, background, noise]
```

每个分量必须同时保存：

- raw value；
- normalized value；
- sampling distribution；
- physical unit；
- schema version。

归一化仅使用 Train 范围。

## 3.2 Texture

Pilot 中：

- 可作为输入增强；
- 不进入 4D 连续条件回归。

正式加入前必须明确：

```text
固定取向轴 + strength regression
或
orientation class + strength multi-head
```

## 3.3 仿真度级别

```text
F0 = simple independent perturbations
F1 = literature-driven physical perturbations with independent/simple mixed sampling
F2 = optional high-fidelity simulator
```

F2 不得成为 Pilot 阻塞项。


## 3.4 封存模块：Structured Perturbation Policy

当前工程状态：

```text
ARCHIVED_FUTURE_DIRECTION
```

本模块定义的是扰动之间的：

- conditional dependency；
- scenario-based co-occurrence；
- correlated strength sampling；
- curriculum schedule；
- unseen dependency OOD。

它不等于新增一个扰动算子，也不等于 F1 的文献驱动物理参数范围。

当前只建立接口和文档占位，不实现正式训练逻辑：

```text
configs/future_structured_perturbation/
├── README.md
├── scenario_schema.example.json
└── dependency_graph.example.json
```

建议预留的可选元数据字段：

```text
scenario_id: Optional[str]
dependency_graph_version: Optional[str]
curriculum_stage: Optional[int]
structured_policy_hash: Optional[str]
```

在当前 V9 Pilot 中以上字段必须为 `null`，不得影响采样。

重新启用前必须提交：

```text
V9_STRUCTURED_PERTURBATION_REACTIVATION_PROPOSAL.md
```

其中至少说明：

1. 物理或实验依据；
2. 场景变量定义；
3. 与独立采样保持公平的方式；
4. 所需消融；
5. 对当前主线的增量价值。

---



# 4. 统一数据对象

```python
from dataclasses import dataclass
from typing import Mapping, Tuple

@dataclass(frozen=True)
class ConditionDescriptor:
    shift: float
    broadening: float
    background: float
    noise: float
    schema_version: str

@dataclass(frozen=True)
class GeneratedView:
    pattern: "Tensor"
    raw_params: Mapping[str, float]
    condition: ConditionDescriptor
    seed: int
    operator_trace: Tuple[str, ...]
    simulator_level: str

@dataclass(frozen=True)
class GeneratedPair:
    structure_id: str
    class_label: int
    view_a: GeneratedView
    view_b: GeneratedView
```

所有训练方法读取同一个 `GeneratedPair`，禁止各方法自行生成不同数据。

---

# 5. 两种 Pair Generator

## 5.1 Controlled Pair Generator

用途：

- Gate A0；
- Gate A1；
- 条件可辨识性；
- 单因素 residual probe。

规则：

- 同一结构；
- 只改变一个目标条件；
- 其他条件与随机种子尽量锁定；
- small/medium/large 三档差值；
- 50% 交换 A/B；
- 正负方向平衡。

## 5.2 Mixed Pair Generator

用途：

- Paired ERM；
- B1/B2；
- A1/A2 正式训练。

建议 batch 内：

- 50% controlled pair；
- 50% natural multi-factor pair。

若实验显示 controlled 比例影响显著，只允许在 Pilot 搜索：

```text
25% / 50% / 75%
```

冻结后不得看 Test 再修改。

---

# 6. Batch 与采样

## 6.1 推荐 batch

```text
28 个不同结构 × 2 views = 56 patterns
```

每个晶系 4 个结构。

显存不足时：

```text
14 个结构 × 2 views = 28 patterns
```

保持类别平衡。

## 6.2 Seed

每个视图 seed：

```text
hash(global_seed, structure_id, virtual_epoch, step, view_id)
```

## 6.3 Virtual epoch

```text
virtual_epoch_steps = ceil(train_structure_count / structures_per_batch)
```

在线训练使用固定 step 数，不把“生成了多少不同谱”模糊地当作 epoch。

---

# 7. 共享模型接口

```python
class XRDEncoderModel(nn.Module):
    def encode(self, x):
        ...

    def classify(self, h):
        ...

class V9DualTrackModel(XRDEncoderModel):
    def predict_condition_delta(self, residual):
        ...

    def predict_class_from_residual(self, residual, condition_delta=None):
        ...
```

主 backbone 固定为当前 PAMPT/Peak-Aware Transformer。

所有方法：

- 同一 encoder；
- 同一 classifier；
- 同一参数初始化规则；
- 仅开启本路线所需的附加头。

---

# 8. 方法实现

## 8.1 C2：Paired ERM

```text
L = CE(C(h_a), y) + CE(C(h_b), y)
```

它是所有路线的共同核心基线。

## 8.2 B1：JS Consistency

```text
L = L_cls + lambda_cons * JS(p_a, p_b)
```

Pilot 只搜索：

```text
lambda_cons ∈ {0.1, 0.3, 1.0}
```

## 8.3 B2：Residual Class Decorrelation

```text
r = h_b - h_a
L = L_cls + lambda_decorr * L_decorr
```

允许 gradient reversal 或 entropy maximization 二选一，不得两者同时无限调参。

## 8.4 A1：Simulation-Supervised Residual

```text
r = h_b - h_a
Delta_m = m_b - m_a
L = L_cls + lambda_meas * SmoothL1(Q(r), Delta_m)
```

增加双向监督：

```text
Q(r) -> Delta_m
Q(-r) -> -Delta_m
```

Pilot 只搜索：

```text
lambda_meas ∈ {0.1, 0.3, 1.0}
```

## 8.5 A2：Conditional Leakage Suppression

仅在 Gate A1/A2 和类别泄漏诊断通过后实现。

```text
D([r, stopgrad(Delta_m)]) -> y
```

要求：

- 从 A1 checkpoint 开始；
- 判别器 warm-up；
- `lambda_adv` 仅三值搜索；
- 主任务 Validation Macro-F1 下降超过 1 个百分点立即停用；
- A2 不得成为默认必跑项。

---

# 9. 训练阶段

## Stage 0：基础设施与 C2

完成：

- manifest；
- cache；
- generators；
- fixed eval panels；
- C2 稳定训练；
- throughput report。

## Stage 1：双轨 Pilot

### Track A

1. A0 raw-spectrum probe；
2. 冻结 C2 encoder 做 residual probe；
3. A1 小规模训练；
4. 10%/25% 数据预算；
5. development-OOD。

### Track B

1. B1；
2. B2；
3. 与同 seed 的 C2 比较；
4. development-OOD。

## Stage 2：分叉报告

自动生成：

```text
reports/V9_BRANCH_DECISION_REPORT.md
```

必须包含：

- Gate 结果；
- 3 seeds；
- ID/OOD；
- 条件预测；
- 样本效率初步曲线；
- 训练稳定性；
- GPU-hour；
- 推荐分支 M/T/H/N。

## Stage 3：单主线全量

Branch 决定后，只全量扩张主线。

另一条路线仅保留必要基线，不继续无边界调参。

---

# 10. Gate 的工程判定

## Gate A0：条件可辨识

Validation structures 上：

- raw-spectrum/handcrafted probe 优于 mean predictor；
- shuffled-label 基线接近随机；
- 至少 3/4 条件方向准确率明显高于 50%。

失败：修标签或模拟器，不训练 A1 全量。

## Gate A1：残差可预测条件

冻结 C2 encoder：

- 线性 probe；
- 两层 MLP；
- 每因素 MAE、R²、方向准确率。

建议 go 标准：

- 4 个因素至少 3 个 `R² > 0.10`；
- bootstrap CI 下界大于 0；
- 优于 shuffled label。

该阈值仅是工程决策标准。

## Gate A2：A1 是否改善任务

满足以下之一：

- development-OOD Macro-F1 稳定提升；
- 25% 数据预算达到 C2 100% 预算的接近性能；
- 固定 GPU-hour 下性能更高。

同时：

- ID Macro-F1 下降不超过 1 个百分点；
- 3 seeds 提升方向一致。

## Gate B：算法迁移是否有效

B1 或 B2 相对 C2：

- 至少一个冻结 OOD 维度稳定提升；
- 不以 ID 损失换取单一 OOD 偶然上涨；
- 3 seeds 方向一致；
- 真实谱阶段至少不系统性恶化。

## Branch 规则

```text
A2 通过 → M 或 H
A2 失败且 B 通过 → T
A/B 均失败 → N
```

---

# 11. 样本效率正式矩阵

## 11.1 结构数量

```text
10% / 25% / 50% / 100%
```

## 11.2 视图/计算预算

使用固定：

```text
pattern forwards
optimizer steps
GPU-hours
```

至少选其中两种口径同时报告。

## 11.3 必须比较

```text
C2 vs A1
```

可选：

```text
B1/B2 只在对应分支成为主线时加入完整曲线
```

禁止对所有方法都跑完整四档，造成算力失控。

---

# 12. 仿真度矩阵

Pilot 只跑：

```text
F0 × {C2, A1}
F1 × {C2, A1}
```

仅当 A1 通过且 F2 已稳定时，增加：

```text
F2 × {C2, A1}
```

主要结果：

- 同仿真度增益；
- 中仿真度 A1 与高仿真度 C2 的比较；
- 不同仿真度下的样本效率变化。

---

# 13. 固定评价面板

## 13.1 Validation

每个 Validation structure 建议：

- 2 ID；
- 4 单因素 development-OOD；
- 2 未见组合 development-OOD。

共 8 views/structure。

## 13.2 Test

每个 Test structure：

1. ID；
2. shift OOD；
3. broadening OOD；
4. background OOD；
5. noise OOD；
6. unseen combination A；
7. unseen combination B；
8. unseen combination C。

每类 3 个固定 seed。

统计单位是 structure，不是单张谱。

## 13.3 真实谱

正式运行前冻结：

- 数据源；
- 标签核验；
- 单相过滤；
- 波长统一；
- 角度范围；
- 插值；
- 重复去除；
- 与训练结构重合审计。

真实谱不得用于选 checkpoint 或 loss 权重。

---

# 14. 指标与日志

## 14.1 主任务

- Accuracy；
- Macro-F1；
- Balanced Accuracy；
- per-class Recall；
- worst-condition Macro-F1；
- ECE；
- 3/5 seeds 均值与标准差。

## 14.2 机制指标

- condition MAE；
- condition R²；
- direction accuracy；
- residual-to-class probe；
- conditional residual-to-class probe；
- learning-curve AUC；
- target-performance sample count；
- GPU-hour。

## 14.3 每个 run 必须记录

```text
run_id
git_commit
config_hash
split_hash
condition_schema_hash
eval_manifest_hash
global_seed
CUDA/PyTorch version
checkpoint_hash
pattern_forward_count
optimizer_step_count
wall_clock
GPU_hours
```

---

# 15. 超参数纪律

## Pilot 允许调

- residual layer；
- `lambda_meas`；
- `lambda_cons`；
- `lambda_decorr`；
- condition head width；
- controlled/mixed pair 比例。

## 不允许同时调

- backbone 深度；
- optimizer 类型；
- learning rate 大范围；
- batch size；
- 五类扰动范围；
- 所有 loss 权重；
- Test OOD 配置。

所有路线使用相同搜索预算。

---

# 16. 单元测试

## 数据与模拟

- 同 seed 生成完全相同视图；
- A/B 交换后 \(\Delta m\) 正确反号；
- controlled pair 只变化目标因素；
- condition normalization 可逆；
- train/val/test 无结构指纹交叉；
- eval panel hash 稳定。

## 模型与损失

- C2 不调用任何附加头；
- B1 仅增加 consistency loss；
- B2 gradient reversal 方向正确；
- A1 双向监督对称；
- A2 stop-gradient 生效；
- 推理模式只保留 encoder + classifier。

## 公平性

- C2/B1/B2/A1 使用相同 pair IDs；
- pattern forward 数一致；
- optimizer step 一致；
- checkpoint 规则一致。

---

# 17. 工程完成定义

## 共同基础设施完成

- [ ] 正式 split manifest 与 hash；
- [ ] Pilot split；
- [ ] base pattern/peak table cache；
- [ ] F0/F1 config；
- [ ] 4D condition schema；
- [ ] Controlled/Mixed Pair Generator；
- [ ] 固定 Validation/Test 面板；
- [ ] C2 可复现；
- [ ] 统一日志与 run registry。

## 路线 A Pilot 完成

- [ ] A0；
- [ ] residual probe；
- [ ] A1；
- [ ] 10%/25% 样本效率；
- [ ] Gate A2 报告。

## 路线 B Pilot 完成

- [ ] B1；
- [ ] B2；
- [ ] 匹配预算审计；
- [ ] Gate B 报告。

## 封存方向记录完成

- [ ] `V9_FUTURE_STRUCTURED_PERTURBATION_NOTE.md`；
- [ ] 占位 schema 与 README；
- [ ] 当前配置确认该模块关闭；

## 分叉完成

- [ ] `V9_BRANCH_DECISION_REPORT.md`；
- [ ] 明确 M/T/H/N；
- [ ] 冻结正式主线；
- [ ] 停止非主线无边界扩张。

---

# 18. 建议时间表

## 2026-07-17 至 2026-07-26

- 数据审计；
- split；
- cache；
- condition schema；
- pair generator；
- fixed validation panel。

## 2026-07-27 至 2026-08-05

- C2；
- A0/A1 probes；
- B1/B2 最小实现；
- 吞吐与显存测试。

## 2026-08-06 至 2026-08-16

- A1 Pilot；
- 10%/25% 样本效率；
- 3 seeds；
- B1/B2 匹配预算实验。

## 2026-08-17 至 2026-08-20

- 生成 Branch Decision Report；
- 冻结 M/T/H/N。

## 2026-08-21 起

- 只对选定主线进行全量、多 seed、OOD、真实谱和论文实验。

日期可因算力调整，但步骤顺序不得颠倒。

---

# 19. Codex 当前任务清单

Codex 应依次产出：

1. `V9_CODE_AUDIT.md`
2. `V9_DATA_SPLIT_REPORT.md`
3. `V9_CONDITION_SCHEMA.json`
4. `V9_PAIR_GENERATOR_SPEC.md`
5. `V9_EVAL_PANEL_MANIFEST.json`
6. `V9_COMMON_TRAINER_PLAN.md`
7. `V9_TRACK_A_IMPLEMENTATION.md`
8. `V9_TRACK_B_IMPLEMENTATION.md`
9. `V9_FAIRNESS_AUDIT.md`
10. `V9_BRANCH_DECISION_TEMPLATE.md`
11. `V9_FUTURE_STRUCTURED_PERTURBATION_NOTE.md`
12. 单元测试与运行命令
13. 旧 V7/V8/V9 草案复现映射表

---

# 20. Codex 禁止事项

- 删除旧版本；
- 修改正式 split；
- 用 Test 选择超参数；
- 为 A/B 使用不同数据分布；
- 未通过 A0 就全量训练 A1；
- 未通过泄漏诊断就实现 A2；
- 同时扩张多个 backbone；
- 新增多相、杂质峰或第六扰动作为当前主线；
- 在当前 Pilot 中启用结构化扰动依赖、场景采样或课程调度；
- 在完成双轨分支决策前，同时修改生成策略与学习目标；
- 把 simulator parameter 称为真实仪器因果标签；
- 把 probe 结果当作因果证明；
- 只报告最好 seed；
- 为保住预定叙事修改 Gate；
- A/B 均失败后继续堆损失函数。

---

# 21. 最简执行路径

```text
冻结 split 与评测
→ 构建统一 paired generator
→ 复现 C2
→ 同时跑 A 的最小 Gate 与 B 的最小算法实验
→ 输出 Branch Decision Report
→ 选择 M/T/H/N
→ 只扩张一条主线
→ 结构化扰动继续封存，除非另行通过重启提案
→ 冻结 OOD 与真实谱验证
→ 写作与复现包
```

最重要的工程原则：

> **V9 不是同时做两篇论文，而是用一套共享实验体系，低成本验证两条可能的论文主线，再依据证据选择其中一条。**
