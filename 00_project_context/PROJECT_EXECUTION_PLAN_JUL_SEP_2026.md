# XRD Robustness 项目执行计划（2026 年 7–9 月）
## 面向 Codex 的时间安排、任务拆解与验收说明书

> 关联方法文件：`CODEX_METHOD_UPDATE_V5_DYNAMIC_RESIDUAL_DECORRELATION.md`  
> 状态：本文件负责 **时间安排、工程实施、协作分工与阶段验收**；方法定义以 V5 为准。  
> 项目成员：项目负责人 1 人；协作者（室友）自 2026 年 8 月加入。  
> 主训练设备：2026 年 8 月起迁移至台式机。  
> 项目窗口：2026-07-12 至 2026-09-30。

---

# 1. 总体目标

在 2026 年 9 月底前，完成以下闭环：

```text
Materials Project 晶体结构
→ 结构清洗、去重、晶系标签与 structure-level split
→ 峰表/反射信息缓存
→ Offline 与 Dynamic 物理 XRD 生成
→ 1D Patch Transformer
→ 四种训练方法
→ in-range / OOD / real-XRD 统一评估
→ residual probe 与机制分析
→ 论文初稿和核心图表
```

四种正式方法：

1. `Offline Multi-view ERM`
2. `Dynamic ERM`
3. `Dynamic JS Consistency`
4. `Dynamic Measurement-Residual Decorrelation`（主方法）

核心原则：

> 只维护一套公共数据管线、一套主干模型和一套评估框架；四种方法仅在数据暴露方式和训练目标上不同。

---

# 2. 项目阶段划分

| 阶段 | 时间 | 核心目标 | 阶段出口 |
|---|---|---|---|
| Phase 1 | 7 月 12–31 日 | 数据、模拟、模型和训练最小闭环 | 小规模 Dynamic ERM 可训练、可恢复、可评估 |
| Phase 2 | 8 月 1–31 日 | 台式机迁移、四种方法实现和首轮全量实验 | 四种方法均完成至少一次完整训练 |
| Phase 3 | 9 月 1–15 日 | 多随机种子、OOD、机制验证 | 冻结正式主结果 |
| Phase 4 | 9 月 16–30 日 | real-XRD 验证、作图与论文 | 完成论文初稿与结果包 |

## 2.1 数据规模政策：只维护一套数据库，使用三档嵌套规模

项目不再设置 1400 和 7000 的独立数据规模阶段，也不做强制数据规模曲线。

正式数据库统一目标为 14,000 个结构。其内部固定抽取两个嵌套子集：

| 档位 | 结构数 | 用途 | 是否独立数据库 |
|---|---:|---|---|
| 软件测试 | 140 | 检查数据、模型、梯度和 smoke 闭环 | 否，开发子集的子集 |
| 开发实验 | 3,500 | 调 PAMPT、跑通四种方法、检查残差稳定性和少量参数 | 否，正式数据库训练集子集 |
| 正式实验 | 14,000 | 冻结配置后的最终比较、OOD 和 real-XRD 验证 | 是唯一完整数据库 |

嵌套关系固定为：

```text
正式数据库 14,000
└── 开发子集 3,500
    └── 软件测试子集 140
```

七月先用 140 个结构确认整条软件管线，再建立完整 14,000 结构数据库，并从正式训练集固定抽取 3,500 个开发结构。140、3,500 和 14,000 不得分别下载、分别去重或分别定义 split。

---

# 3. 7 月计划：数据库不是终点，最小训练闭环才是终点

## 3.1 7 月阶段目标

7 月不能只完成“训练数据库构建”。7 月底必须跑通：

数据规模出口同时固定为：

```text
140：软件测试子集
3,500：后续开发实验子集
14,000：正式数据库目标规模
```

七月不做 1,400 或 7,000 的中间规模实验。

```text
structure z
→ 两组动态参数 θ1、θ2
→ 两条 XRD：x1、x2
→ Transformer 特征 h1、h2
→ 预测 p1、p2
→ 分类损失
→ 反向传播
→ checkpoint
→ validation metrics
```

## 3.2 7 月 12–18 日：结构数据与审计

### Codex 任务

- 实现 Materials Project 数据获取模块。
- 保存原始结构与标准化结构。
- 重算空间群和晶系标签。
- 生成标签不一致报告。
- 生成结构指纹并执行去重。
- 生成固定的 `train/val/test` structure-level split。
- 保存所有 manifest，保证后续可重放。

### 预期文件

```text
data/
├── raw_structures/
├── standardized_structures/
├── metadata/
│   ├── retrieval_manifest.json
│   ├── structure_manifest.csv
│   ├── label_mismatch_report.csv
│   ├── duplicate_report.csv
│   ├── failed_structures.csv
│   └── split_manifest.csv
```

### 验收标准

- 同一 `material_id` 不跨 split。
- 同一结构指纹不跨 split。
- 七个晶系数量统计可输出。
- 每项筛选规则可由配置文件修改。
- 所有失败结构均有可读错误日志。

## 3.3 7 月 19–24 日：XRD 模拟、缓存与物理扰动

### Codex 任务

- 实现理想峰表与反射信息缓存。
- 实现统一 XRD 网格和渲染器。
- 实现 `PhysicsParameterSampler`。
- 首版至少支持：
  - zero shift；
  - peak broadening；
  - background；
  - noise。
- 每次生成时保存完整扰动参数。
- 实现 Level 0–4 severity 接口，但正式数值范围保持配置化。

### 预期模块

```text
src/xrd/
├── peak_cache.py
├── renderer.py
├── perturbations.py
├── parameter_sampler.py
└── validation.py
```

### 验收标准

- 同一结构、同一 seed、同一参数可完全重现同一条谱。
- 同一结构、不同 seed 可产生不同视图。
- 无扰动谱与扰动谱均无 NaN/Inf。
- 峰位偏移、展宽、背景和噪声均可单独开关。
- 生成结果可以输出对应参数 manifest。

## 3.4 7 月 25–28 日：Offline/Dynamic 数据接口与模型

### Codex 任务

- 实现 Offline Multi-view 数据生成与读取。
- 实现 Dynamic 双视图 Dataset。
- 实现 1D Patch Transformer，返回：
  - `logits`；
  - pooled embedding `h`。
- 实现统一训练 batch schema。
- 实现基础评估：Macro-F1、accuracy、per-class recall、confusion matrix。

### 推荐统一 batch schema

```python
{
    "structure_id": ...,
    "label": ...,
    "x1": ...,
    "x2": ...,
    "theta1": ...,
    "theta2": ...,
}
```

Offline 模式可将固定离线谱映射到同一接口，避免单独维护完全不同的训练器。

### 验收标准

- 输入长度、patch 划分和 positional encoding 无维度错误。
- 单个 batch 可完成前向与反向传播。
- `encoder(x)` 可稳定返回固定维度特征。
- Dataset 不修改已经冻结的 split。

## 3.5 7 月 29–31 日：最小训练闭环与迁移演习

### Codex 任务

- 在小规模数据上跑通 Dynamic ERM。
- 保存并恢复 checkpoint。
- 验证 loss 能下降。
- 验证训练中同一结构的动态视图确实变化。
- 生成一份最小实验报告。
- 完成台式机迁移准备。

### 必须保存

```text
configs/
environment.yml
requirements.txt
scripts/train_small.sh
scripts/eval_small.sh
outputs/smoke_test/
```

### 7 月硬性出口条件

以下项目全部通过后，才能进入 8 月全量训练：

- [ ] 数据 split 已冻结并保存。
- [ ] 峰表缓存可用。
- [ ] 动态双视图生成可复现。
- [ ] 1D Patch Transformer 前向/反向正常。
- [ ] Dynamic ERM 小规模训练 loss 正常下降。
- [ ] checkpoint 可跨目录恢复。
- [ ] 配置文件中无本机绝对路径。
- [ ] 日志记录 seed、git commit、配置与数据 manifest 版本。

---

# 4. 8 月计划：迁移台式机并推进四种方法

## 4.1 台式机迁移原则

8 月台式机承担：

```text
全量训练
多随机种子
OOD sweep
checkpoint 保存
长时间实验
```

开发电脑承担：

```text
代码开发
小规模调试
日志分析
real-XRD 预处理
作图
论文写作
```

## 4.2 8 月 1–4 日：部署和复现

### Codex 任务

- 在台式机创建独立 Conda 环境。
- 记录 Python、PyTorch、CUDA、驱动和 GPU 信息。
- 将路径全部由 YAML 控制。
- 在台式机执行 smoke test。
- 恢复 7 月 checkpoint 并继续训练。
- 对比迁移前后数据 split、batch 形状和初始指标。

### 验收标准

- 同一配置可在开发电脑和台式机运行。
- checkpoint 可正常 resume。
- 迁移不改变 split manifest。
- 所有输出写入带时间戳和配置哈希的实验目录。

## 4.3 8 月 5–11 日：公共训练框架与两个 ERM

### Codex 任务

统一实现：

```text
mode = offline_erm
mode = dynamic_erm
mode = dynamic_js
mode = dynamic_residual
```

优先完成：

1. Offline Multi-view ERM；
2. Dynamic ERM。

### 公平性要求

Offline 与 Dynamic 的比较必须记录：

- 总 optimizer step；
- 每步 batch size；
- 总 forward 数；
- 每个结构平均视图暴露量；
- wall-clock time；
- 数据生成/读取耗时。

不能简单把“在线看见更多谱”误判为训练方法更优。

## 4.4 8 月 12–18 日：Dynamic JS

### Codex 任务

- 在 Dynamic ERM 代码上增加 JS loss。
- 两条视图共享完全相同的数据和 forward 流程。
- JS 输入必须是概率分布或 log-probability 的正确组合。
- 实现数值稳定保护。
- 只做小范围 `lambda_js` 搜索。

### 建议范围

```text
lambda_js ∈ {0.01, 0.1, 1.0}
```

### 验收标准

- 当 `lambda_js = 0` 时，结果与 Dynamic ERM 逻辑等价。
- 交换 `x1/x2` 不改变 JS loss。
- JS loss 非负且无 NaN。
- 分类损失仍同时作用于两条视图。

## 4.5 8 月 12–22 日：Dynamic Measurement-Residual Decorrelation

此任务与 Dynamic JS 并行，由项目负责人主导。

### Codex 任务

- 实现对称残差：

```text
r = abs(l2_normalize(h1) - l2_normalize(h2))
```

- 实现 residual classifier。
- 实现双 optimizer 交替训练。
- 实现分类 warm-up 和 `lambda_res` ramp-up。
- 实现 residual head 的 freeze/detach 逻辑。
- 实现独立 post-hoc residual probe。

### 必须通过的梯度流测试

- [ ] Step A 中 encoder 无梯度，residual classifier 有梯度。
- [ ] Step B 中 residual classifier 参数不更新。
- [ ] Step B 中梯度能穿过冻结的 residual classifier 回到 residual 和 encoder。
- [ ] 主分类头在 Step B 正常更新。
- [ ] 交换 `x1/x2` 不改变残差。
- [ ] 主方法关闭残差损失后可退化为 Dynamic ERM。

### 建议首轮范围

```text
lambda_res ∈ {0.01, 0.1, 1.0}
residual_head_depth ∈ {1, 2}
warmup_epochs ∈ {5, 10}
```

禁止首轮进行大规模超参数搜索。

## 4.6 8 月 23–31 日：四种方法首轮全量比较

### 每种方法至少完成

- 1 个完整训练 run；
- 1 个统一 in-range test；
- 1 个统一 OOD test；
- checkpoint；
- training history；
- prediction CSV；
- config snapshot；
- git commit hash。

### 8 月阶段出口

- [ ] 四种方法均能从统一入口启动。
- [ ] 四种方法使用相同 backbone。
- [ ] 三种 dynamic 方法使用相同 `x1/x2` 生成逻辑。
- [ ] 初步结果表可生成。
- [ ] 主方法 residual probe 可运行。
- [ ] 已知失败模式有记录。
- [ ] 9 月正式实验配置已冻结。

---

# 5. 两人分工

## 5.1 项目负责人

主要负责：

- 项目架构与方法学决策；
- 数据筛选、物理扰动与模拟合理性；
- 1D Patch Transformer；
- Dynamic Measurement-Residual Decorrelation；
- residual classifier、交替优化与 post-hoc probe；
- OOD 与 real-XRD 方案；
- 论文叙事、结果解释与最终整合。

## 5.2 协作者（室友，8 月加入）

主要负责：

- 熟悉公共 pipeline；
- 复现 Dynamic ERM；
- Offline Multi-view ERM；
- Dynamic JS；
- 基线训练任务排队；
- checkpoint、日志与结果表维护；
- 多随机种子实验；
- 基础作图与结果核对。

## 5.3 协作约束

不得采用：

```text
两个人各自复制一份仓库
分别修改数据划分
分别写一套模型
分别定义测试集
最终手工拼结果
```

必须采用：

```text
一个 Git 仓库
一个冻结 split
一个模型实现
一个配置体系
一个评估入口
多个 training mode
```

---

# 6. 9 月计划：正式比较、真实验证和论文

## 6.1 9 月 1–7 日：正式多随机种子实验

### Codex 任务

- 冻结正式配置。
- 四种方法至少运行 3 个随机种子。
- 自动汇总均值与标准差。
- 输出统计表和训练稳定性图。

### 主指标

```text
Macro-F1
accuracy
per-class recall
worst-group F1
ECE
correct-and-consistent rate
```

### 输出

```text
results/main_results.csv
results/seed_summary.csv
figures/training_curves/
figures/confusion_matrices/
```

## 6.2 9 月 8–15 日：OOD 与机制验证

### OOD 评估

- 单因素 severity sweep；
- 多因素组合扰动；
- 超出训练范围的参数；
- robustness AUC；
- `ΔF1 = F1_in-range - F1_OOD`；
- worst-severity performance。

### 主方法机制验证

- residual norm；
- residual entropy；
- 训练中 residual classifier 指标；
- 冻结 encoder 后训练新的 post-hoc residual probe；
- probe accuracy / Macro-F1；
- 主分类性能与 probe 性能的联合分析。

### 判定逻辑

主方法最理想的证据不是单独“残差变小”，而是：

```text
残差仍然非零
+ post-hoc probe 难以预测晶系
+ OOD / real-XRD 分类更好
+ in-range 性能不过度下降
```

## 6.3 真实 XRD 准备不得等到 9 月才开始

Real-XRD 数据源应在 7 月确认，8 月完成预处理 dry run。9 月只做正式验证。

预处理必须记录：

```text
原始文件来源
波长
2θ 范围
步长
插值方法
背景处理
归一化
混相/纯相状态
晶系标签来源
样品与结构对应关系
```

不得为了适配模型而使用测试标签调参。

## 6.4 9 月 16–23 日：real-XRD 正式验证

### Codex 任务

- 实现统一 real-XRD loader。
- 将实验谱映射到训练网格。
- 对四种模型执行完全相同的推理。
- 输出预测、置信度、类别概率与错误案例。
- 生成典型成功/失败样本图。

### 验收标准

- 四种方法使用同一 real-XRD 数据版本。
- 预处理参数冻结并记录。
- 不能为不同模型分别调预处理。
- 错误案例具有可追溯样品 ID。

## 6.5 9 月 24–30 日：论文与结果包

### 论文结构

```text
1. Introduction
2. Related Work
3. Problem Formulation
4. Physical XRD View Generation
5. Four Training Strategies
6. Experimental Protocol
7. Results
8. Residual Mechanism Analysis
9. Real-XRD Validation
10. Discussion and Limitations
11. Conclusion
```

### 9 月底交付物

- [ ] 论文初稿；
- [ ] 方法流程图；
- [ ] 主结果表；
- [ ] OOD 鲁棒性曲线；
- [ ] residual probe 结果；
- [ ] real-XRD 结果；
- [ ] 完整配置和环境文件；
- [ ] 可复现训练命令；
- [ ] 最终数据与模型版本 manifest。

---

# 7. 推荐仓库结构

```text
project_root/
├── configs/
│   ├── data.yaml
│   ├── model.yaml
│   ├── offline_erm.yaml
│   ├── dynamic_erm.yaml
│   ├── dynamic_js.yaml
│   ├── dynamic_residual.yaml
│   └── evaluation.yaml
├── data/
│   ├── raw_structures/
│   ├── standardized_structures/
│   ├── metadata/
│   ├── split_manifests/
│   ├── peak_cache/
│   ├── offline_views/
│   └── real_xrd/
├── src/
│   ├── data/
│   ├── xrd/
│   ├── models/
│   ├── training/
│   │   ├── offline_erm.py
│   │   ├── dynamic_erm.py
│   │   ├── dynamic_js.py
│   │   └── dynamic_residual.py
│   ├── evaluation/
│   └── utils/
├── scripts/
├── tests/
├── outputs/
├── results/
├── figures/
├── environment.yml
├── requirements.txt
└── README.md
```

---

# 8. 统一实验目录与追踪格式

每次训练创建：

```text
outputs/{method}/{timestamp}_{seed}_{config_hash}/
├── config_resolved.yaml
├── environment.txt
├── git_commit.txt
├── data_manifest.json
├── train.log
├── metrics.csv
├── predictions.csv
├── best.ckpt
└── last.ckpt
```

Codex 必须确保：

- 任何结果都可追溯到数据版本、配置、seed 和 commit；
- 不覆盖旧实验；
- 训练异常时仍保存最后状态；
- checkpoint 中包含 optimizer、scheduler、epoch 和 RNG state；
- 支持 `--resume`。

---

# 9. Codex 实施优先级

## P0：项目不能缺少

- structure-level split；
- 数据审计与 manifest；
- peak cache；
- 动态双视图；
- 统一 Transformer；
- 四种 training mode；
- checkpoint/resume；
- 公平测试集；
- OOD 评估；
- residual probe；
- real-XRD loader。

## P1：正式实验需要

- 多随机种子；
- calibration；
- robustness AUC；
- 训练性能分析；
- 自动结果汇总；
- 图表脚本。

## P2：有余力再做

- preferred orientation；
- lattice strain；
- thermal vibration；
- instrumental convolution；
- JS + residual 联合损失；
- 多层 residual；
- 更多 backbone。

P2 不得阻塞 P0/P1。

---

# 10. 关键风险与止损规则

## 风险 A：动态生成成为 CPU 瓶颈

处理顺序：

1. 先缓存峰表；
2. DataLoader 多进程；
3. batch 内向量化渲染；
4. 预取和 pinned memory；
5. 必要时缓存有限数量动态参数结果。

不得直接取消动态训练而不记录原因。

## 风险 B：残差方法退化

检查：

- residual classifier 是否学得动；
- encoder 是否收到正确梯度；
- 分类性能是否因约束过强下降；
- post-hoc probe 是否仍能预测晶系；
- residual norm 是否塌缩。

若 8 月 22 日前主方法仍不稳定：

```text
保留 Dynamic ERM 和 Dynamic JS 的完整结果
缩小 residual 方法超参数范围
优先确保交替优化和 probe 正确
不扩展复杂多层残差
```

## 风险 C：real-XRD 数据不足或标签不可靠

处理：

- 7 月确认来源；
- 8 月完成 5–20 条谱 dry run；
- 明确 pure phase / mixed phase；
- 将真实验证定位为外部验证或 case study；
- 不隐瞒样本量和标签限制。

## 风险 D：四种方法不公平

必须锁定：

```text
同一结构划分
同一测试 manifest
同一 backbone
同一 batch size
同一 optimizer family
同一训练步数
同一 seed 集合
三种 dynamic 方法共享相同双视图逻辑
```

发现不公平后，优先重跑，不使用不可比结果支撑结论。

---

# 11. 每周例会模板

每周固定输出一页状态：

```text
本周完成：
- 已合并的功能
- 已完成的实验
- 已生成的数据/结果

当前阻塞：
- 错误现象
- 最小复现
- 对进度的影响

下周 P0：
- 最多 3 项

实验状态：
- running
- completed
- failed
- needs rerun

风险变化：
- 数据
- 算力
- 方法
- real-XRD
```

---

# 12. Codex 的直接执行顺序

Codex 应按以下顺序实施，不得跳过基础审计直接写主方法：

```text
1. 检查并整理现有仓库
2. 建立 configs 与 manifest 体系
3. 完成结构数据与 split
4. 完成峰表缓存和 XRD renderer
5. 完成 Offline/Dynamic Dataset
6. 完成 1D Patch Transformer
7. 在 140 软件测试子集上跑通 Dynamic ERM smoke；随后固定 3,500 开发子集
8. 完成 checkpoint/resume 与台式机迁移测试
9. 完成 Offline ERM
10. 完成 Dynamic JS
11. 完成 Dynamic Residual Decorrelation
12. 完成 residual probe
13. 完成统一 OOD evaluation
14. 完成 real-XRD loader
15. 完成多 seed 汇总与论文图表脚本
```

每完成一个阶段，先运行对应单元测试和 smoke test，再进入下一阶段。

---

# 13. 最终成功标准

截至 2026 年 9 月 30 日，项目应至少满足：

1. 四种方法均有可复现实现；
2. 四种方法共享同一数据划分和主干模型；
3. 至少完成 3 个随机种子的正式对照；
4. 有 in-range 与 OOD 结果；
5. 有 residual probe 机制验证；
6. 有一套冻结的 real-XRD 外部验证；
7. 有论文初稿、主结果表和核心图；
8. 从空环境可依据 README 和配置重新运行关键实验。

项目最终叙事：

> 本研究在统一的动态物理 XRD 双视图框架下，系统比较离线多视图监督学习、在线动态 ERM、输出级 JS 一致性和测量残差类别解耦，分析不同训练目标对未知测量条件与真实实验 XRD 泛化的影响。
