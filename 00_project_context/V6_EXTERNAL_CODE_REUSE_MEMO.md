# 给 Codex 的实施备忘录：V6 外部代码审计、复用边界与落地方案

> 项目：XRD Robustness
>
> 适用版本：V6 — Peak-Aware Multi-Scale Patch Transformer（PAMPT）
>
> 文档性质：**对 `CODEX_METHOD_UPDATE_V6_PEAK_AWARE_PAMPT.md` 的补充实施说明，不覆盖、不修改 V6 的正式方法定义。**
>
> 核心任务：把已审计的开源仓库中有价值的研究思想和工程边界转化为自己的实现规范，同时保持数据来源、结构级划分、统一 backbone 和四方法公平比较不变。外部研究仓库不直接复制源码，也不作为 V6 核心运行时依赖。

---

# 0. 最高优先级结论

Codex 必须先接受以下结论，不得自行改回旧路线：

1. **正式晶体结构来源只有 Materials Project API。**
2. 不把 CrystDB、SimXRD IL/OL 或 XQueryer 的成品数据库作为正式训练数据源。
3. IL/OL 是任务和划分协议，不是必须下载使用的数据库：
   - 本项目主任务是 structure-level split 下的 out-of-library crystal-system classification；
   - 同一结构及其全部视图不得跨 split。
4. 正式主干是 V6 的 **PAMPT**，不是普通 Patch Transformer，也不是 XQueryer 的 FFT-CNN。
5. 正式比较仍为四种训练方法：

```text
A. Offline Multi-view ERM
B. Dynamic ERM
C. Dynamic JS Consistency
D. Dynamic Measurement-Residual Decorrelation（主方法）
```

6. 先在 Dynamic ERM 下完成 `B0 → B1 → B2 → B3` backbone 消融；选定最小有效 backbone 后冻结配置与 hash，再运行四种方法。
7. 外部代码只能提供部件、baseline 和工程参考，不能改变 V6 的科学问题。
8. 当前真正需要自己完成、也是项目方法学核心的部分是：

```text
PAMPT
+ 同结构在线动态双视图
+ Dynamic JS
+ Measurement-Residual Decorrelation
+ 严格共享视图流和统一评价协议
```

## 外部复用总原则

必须区分三种情况：

1. `pymatgen`、`mp-api`、PyTorch 等成熟基础库：按公开 API 调用，固定版本并记录许可证和环境。
2. XQueryer、SimXRD、XRDMatch、KBSS、ML4pXRDs 等研究仓库：只做源码审计、思想参考、结果对照和文献引用，不复制源码或直接接入核心训练流程。
3. V6 的物理扰动、动态采样、PAMPT、四种训练目标、残差解耦、数据划分和实验协议：必须由本项目自己实现并测试。

如果外部方法需要进入实验，只能先写成独立的、从零实现的对照模块，并在 provenance 清单中注明概念来源和“实现非复制”。

---

# 1. 本轮代码审计范围

已检查的主要源码包：

```text
XQueryer-core.zip
Pysimxrd-0.1.2-source.zip
Pysimxrd-0.1.2-py3-none-any.whl
ML4pXRDs-master.zip
PRDNet-main.zip
PyWPEM-main.zip
CPICANN-main.zip
Desktop.zip 内嵌：
  XRD-AutoAnalyzer-main.zip
  XRDs-main.zip
  autoXRD-master.zip
  Advanced_XRD_Analysis-main.zip
  XRD_扰动文献与代码索引包.zip
    ├── SimXRD-main.zip
    └── 未核验来源的 XRDMatch 代码
```

审计内容包括：源码结构、数据生成方式、训练循环、验证集构建、模型输入输出、扰动模块、缓存、日志、checkpoint、推理和实验数据处理。

限制说明：模型权重、ASE/SQLite 数据库、NumPy 数组等二进制数据只检查接口和结构，不将其视为可逐行审计的源码。

---

# 2. 总体复用判断

建议的复用优先级：

| 优先级 | 来源 | 对 V6 的主要价值 | 使用方式 |
|---|---|---|---|
| P0 | Pysimxrd | 物理 XRD 渲染与仪器/样品效应 | 审计、对照验证；核心渲染器自己实现 |
| P0 | ML4pXRDs | 在线持续生成训练 batch、固定验证集 | 借鉴数据流，自己实现 |
| P0 | XRD-AutoAnalyzer | 模块化扰动算子 | 借鉴边界，自己实现 |
| P0 | PRDNet | 配置、缓存、训练、恢复、DDP 工程框架 | 借鉴组织方式，自己实现 |
| P1 | XRDMatch/semilearn | 双视图 batch、一致性 loss、EMA/hook | 只借软件结构，不接源码 |
| P1 | KBSS | 领域增广、置信度筛选、一致性思想 | 只借高层思想，不接伪标签和结构增广 |
| P1 | XRDs-main | No-Pooling CNN baseline | 自己实现轻量 baseline |
| P1 | XQueryer | 离线扰动、FFT baseline、实验谱处理 | 只作对照和工程参考 |
| P2 | autoXRD | CAM/解释性、旧式真实谱流程 | 只借解释性思想 |
| P2 | SimXRD-main | IL/OL 数据组织和结构级复制逻辑 | 只作对照检查 |
| P2 | PyWPEM | 后续实验谱分解与物理精修 | 不进入主训练 |
| P3 | Advanced_XRD_Analysis | Pix2Pix 去扰动思路、预训练模型调用 | 可选概念参考 |
| P3 | CPICANN | 当前包内缺少足够训练源码 | 暂不复用 |

**禁止把多个仓库拼成一个失控的 model zoo。** 首版仅实现 P0 部件以及 V6 规定的必要 baseline。

---

# 3. XQueryer 的准确参考价值

## 3.1 它做了什么

XQueryer 的公开核心代码体现的是：

```text
MP 来源晶体结构
→ Pysimxrd 离线随机模拟多条 PXRD
→ 固定保存为 ASE .db
→ XRD + 元素组成输入
→ FFT 多尺度视图 + 多尺度 CNN
→ 元素—XRD Cross-Attention
→ 100315 个具体 MP 结构类别
→ 类别映射回 MP ID
```

它是**闭集具体结构检索/分类系统**，不是本项目的七晶系 OOD 鲁棒性模型，也不是在线动态训练系统。

## 3.2 对本项目保留的四项价值

### A. Offline Multi-view ERM 的前人路线参考

XQueryer代表“预先生成大量固定扰动谱，再做监督训练”的路线，可作为本项目 Method A 的方法背景与工程对照。

### B. 扰动因素候选清单

其调用 Pysimxrd 时包含：

```text
晶粒尺寸
优选取向
热振动
零点偏移
晶格形变
背景
混合噪声
探测器/样品几何
```

这些因素只构成候选清单。**参数单位、分布和范围必须在 Pysimxrd 源码与文献中单独核验后冻结。**

### C. FFT baseline

XQueryer将原谱和不同高频截断后的逆变换谱同时编码。可在后续小型消融中实现：

```text
F0：FFT multi-view + 普通 Patch Transformer
```

但不把 FFT 塞进正式 PAMPT，避免主干膨胀和归因混乱。

### D. real-XRD 工程流程

可参考：

```text
实验谱读取
→ 固定 2θ 网格插值
→ 强度归一化
→ 模型推理
→ 类别/结构映射
```

具体角度范围、步长和预处理必须由本项目配置控制，不硬编码照搬。

## 3.3 明确不复用

```text
10 亿参数模型
100315 类分类头
元素组成 Cross-Attention
完整 MP_data CSV 库
公开代码中的 train/val 划分假设
固定生成几百万谱的存储策略
```

---

# 4. Pysimxrd：正式渲染器候选

## 4.1 关键源码

```text
Pysimxrd/generator.py
Pysimxrd/utils/MatgenKit.py
Pysimxrd/utils/WPEMsim.py
Pysimxrd/utils/funs.py
```

核心入口：

```python
generator.parser(...)
```

公开源码中已暴露样品因素、仪器几何、峰形、背景、噪声和形变相关实现，价值高于只调用该包的 XQueryer。

## 4.2 Codex 的迁移目标

不要让训练代码直接调用第三方 `parser(database, entry_id, ...)`。应建立本项目自己的稳定接口：

```python
@dataclass(frozen=True)
class PhysicsParams:
    zero_shift_deg: float
    # 其余字段按审计后的物理定义添加

class XRDRenderer(Protocol):
    def cache_ideal_peaks(self, structure: Structure) -> PeakTable: ...
    def render(self, peak_table: PeakTable, params: PhysicsParams) -> np.ndarray: ...
```

推荐分层：

```text
Structure
→ IdealPeakCalculator
→ PeakTable cache
→ PhysicsParameterSampler
→ FastProfileRenderer
→ normalized XRD tensor
```

训练阶段不应反复从 CIF/ASE DB 重新计算所有反射；优先缓存理想峰表，再执行快速峰移、展宽、背景、噪声和强度变化。

## 4.3 迁移前必须完成的审计

对每个参数生成一份机器可读报告：

```text
参数名
源码位置
代码默认值
代码中的单位
实际公式
随机分布
允许范围
论文/文档依据
是否进入首版
```

重点核查：

- `grainsize` 的单位及数值解释；
- 优选取向参数的具体数学含义；
- deformation 中 extinction/torsion 的实现；
- 背景多项式是否可能生成非物理形状；
- noise ratio 对应何种噪声分布；
- 仪器几何卷积是否适合当前实验设备；
- 输入/输出角度网格、波长和强度归一化。

未完成审计的参数不得直接进入正式训练范围。

---

# 5. ML4pXRDs：动态训练数据流参考

## 5.1 可复用逻辑

关键文件：

```text
ML4pXRDs-master/training/train_classifier.py
```

关键实现：

```text
batch_generator_queue()
CustomSequence
固定 batches_per_epoch / steps_per_epoch
训练数据持续在线生成
验证数据单独生成并固定
```

其生产者不断生成新 pattern batch，写入有界队列；训练消费者从队列取 batch。这个架构与 V6 的 Dynamic branch 最接近。

## 5.2 不直接复制 Ray/Keras 实现

本项目首版优先使用 PyTorch 原生组件：

```text
Dataset 或 IterableDataset
DataLoader(num_workers, prefetch_factor, persistent_workers)
有界预取
确定性 seed 派生
```

只有在 profiling 证明渲染器成为明显瓶颈后，才考虑：

```text
multiprocessing producer queue
Ray actor
GPU renderer
```

不要过早引入分布式数据生成复杂度。

## 5.3 V6 所需数据接口

```python
@dataclass
class DynamicPairBatch:
    x1: torch.Tensor
    x2: torch.Tensor
    y: torch.Tensor
    material_id: list[str]
    params1: list[PhysicsParams]
    params2: list[PhysicsParams]
    pair_seed: torch.Tensor
```

同一个 batch 对 Dynamic ERM、Dynamic JS、Dynamic Residual 必须复用完全相同的 `x1/x2`。

建议 seed 规则：

```text
pair_seed = hash(global_seed, split, epoch, global_step, sample_index, material_id)
view_1_seed = hash(pair_seed, 1)
view_2_seed = hash(pair_seed, 2)
```

验证、OOD 和真实谱不得使用无限随机流；必须来自冻结 manifest。

---

# 6. XRD-AutoAnalyzer：模块化扰动算子参考

关键目录：

```text
autoXRD/spectrum_generation/
  strain_shifts.py
  uniform_shifts.py
  peak_broadening.py
  intensity_changes.py
  impurity_peaks.py
  mixed.py
```

## 6.1 值得迁移的内容

- 晶格应变导致的峰位变化；
- uniform/zero shift；
- 晶粒尺寸相关峰展宽；
- 优选取向/强度变化；
- 杂相峰混合；
- 多扰动组合流水线。

迁移后统一成纯函数算子：

```python
class Perturbation(Protocol):
    def __call__(
        self,
        peak_table: PeakTable,
        profile: np.ndarray,
        params: PhysicsParams,
        rng: np.random.Generator,
    ) -> tuple[PeakTable, np.ndarray]: ...
```

## 6.2 不复用其原数据划分

不能采用：

```text
先对所有结构生成多条谱
→ 再按谱随机划分 train/test
```

必须是：

```text
先 structure-level split
→ split 内生成离线或动态视图
```

## 6.3 与 Pysimxrd 的整合原则

不要在两个框架里重复实现同一种扰动并随机选择。建立唯一 registry：

```text
zero_shift        → 一个正式实现
peak_broadening   → 一个正式实现
background        → 一个正式实现
noise             → 一个正式实现
strain            → 一个正式实现
orientation       → 一个正式实现
impurity          → 可选实现
```

每个算子记录 `source`, `formula_version`, `config_hash`。

---

# 7. PRDNet：统一训练工程骨架参考

关键文件：

```text
trainer.py
prdnet/config.py
prdnet/checkpoint.py
prdnet/cached_dataset.py
prdnet/train.py
prdnet/train_props.py
prdnet/utils.py
```

可迁移的工程能力：

```text
配置加载与校验
随机种子固定
缓存和失效检查
rank-0 预处理
DDP 同步
checkpoint / resume
best model
scheduler
gradient clipping
日志与历史记录
```

## 7.1 推荐的本项目统一 Trainer

```python
class TrainingStrategy(Protocol):
    name: str
    def training_step(self, batch, model, state) -> dict[str, torch.Tensor]: ...

class V6Trainer:
    def __init__(
        self,
        model: PAMPT,
        strategy: TrainingStrategy,
        optimizer,
        scheduler,
        evaluator,
        config,
    ): ...
```

四种 strategy：

```text
OfflineMultiViewERMStrategy
DynamicERMStrategy
DynamicJSStrategy
DynamicResidualStrategy
```

共享：

```text
同一冻结 PAMPT 配置
同一参数初始化 seed 或配对 seed 方案
同一 optimizer/scheduler
同一 batch size 与训练 budget
同一分类损失
同一验证/测试 manifest
同一日志和 checkpoint 规范
```

不同 strategy 只能改变其方法定义允许改变的 loss 和优化步骤。

## 7.2 缓存边界

可以缓存：

```text
标准化结构
标签
结构指纹
理想峰表
冻结离线视图
冻结验证/OOD 参数 manifest
```

不能把动态训练的全部 profile 预先缓存，否则 Dynamic branch 会退化成 Offline branch。

---

# 8. XRDMatch / semilearn：只借双视图和一致性软件结构

可借鉴：

```text
weak/strong view 的 batch 接口
consistency loss 的模块化实现
EMA 可选组件
hook/strategy 组织方式
checkpoint 与评估接口
```

不可直接采用：

```text
伪标签
FlexMatch 类别阈值
将有标签 MP 数据伪装成无标签数据
来源未核验代码中的物理扰动范围
```

本项目当前不是半监督任务。Dynamic JS 的两条视图都拥有相同真实晶系标签。

JS 实现必须满足：

```python
p1 = softmax(logits1)
p2 = softmax(logits2)
m = 0.5 * (p1 + p2)
loss_js = 0.5 * KL(p1 || m) + 0.5 * KL(p2 || m)
```

数值稳定：对概率做 clamp，或用 log-softmax / log_target 兼容实现。

---

# 9. XRDs-main：No-Pooling CNN baseline

V6 明确禁止 PAMPT 局部编码器使用 MaxPooling。为了验证这个决定，不仅比较 B0/B3，还建议保留一个轻量 NoPoolCNN baseline：

```text
C0：NoPoolCNN
```

它回答：

> PAMPT 的收益来自全局注意力和峰先验，还是仅仅来自避免 pooling 对窄峰/弱峰的破坏？

baseline 约束：

- 输入、训练视图、优化器、训练 budget、split 和评价与 PAMPT 一致；
- 参数量应报告；
- 不为 C0 单独调一套大范围超参数；
- C0 不进入四方法主矩阵，除非计算资源允许。

---

# 10. autoXRD：解释性参考

可迁移的不是旧 Keras 训练代码，而是“模型到底看了哪些衍射区域”的解释思路。

PAMPT 建议输出：

```text
全局 self-attention rollout
peak-prior-guided attention map
一阶/二阶导数先验响应
不同晶系的关键 2θ 区间
错误样本与正确样本的注意区域对比
```

必须注意：attention map 不是因果解释。写作中使用“模型关注区域/相关性证据”，不要写成“证明该峰导致分类”。

---

# 11. SimXRD-main、PyWPEM、Advanced_XRD_Analysis、CPICANN 的位置

## SimXRD-main

只用于：

- 对照 IL/OL 定义；
- 检查同一结构的多个视图如何组织；
- 对照已有 benchmark。

不作为正式上游，不复制其依赖条目顺序或硬编码规模的数据脚本。

## PyWPEM

属于分类后的物理分解/精修工具。当前只预留接口：

```text
real XRD
→ PAMPT crystal-system prediction
→ 可选 WPEM peak decomposition/refinement
```

不得混入三个月主任务。

## Advanced_XRD_Analysis

Pix2Pix 的“扰动谱还原为 clean 谱”可作为未来去扰动 baseline，但它会引入额外网络和两阶段误差，目前不做。

## CPICANN

当前压缩包内没有足够可迁移的训练实现。记录文献价值，不安排代码任务。

---

# 12. 推荐的正式代码结构

```text
xrd_robustness/
├── configs/
│   ├── data/
│   ├── renderer/
│   ├── backbone/
│   ├── methods/
│   └── experiments/
├── data/
│   ├── mp_retrieval.py
│   ├── structure_preprocess.py
│   ├── structure_split.py
│   ├── manifests.py
│   ├── offline_dataset.py
│   └── dynamic_pair_dataset.py
├── simulation/
│   ├── peak_table.py
│   ├── ideal_peak_cache.py
│   ├── parameter_sampler.py
│   ├── renderer.py
│   ├── perturbations/
│   │   ├── zero_shift.py
│   │   ├── broadening.py
│   │   ├── background.py
│   │   ├── noise.py
│   │   ├── strain.py
│   │   ├── orientation.py
│   │   └── impurity.py
│   └── audit/
│       ├── pysimxrd_parameter_audit.py
│       └── simulation_report.py
├── models/
│   ├── derivatives.py
│   ├── multiscale_peak_encoder.py
│   ├── overlapping_patch.py
│   ├── peak_prior_attention.py
│   ├── pampt.py
│   ├── residual_head.py
│   └── baselines/
│       ├── patch_transformer.py
│       ├── no_pool_cnn.py
│       └── fft_patch_transformer.py
├── methods/
│   ├── base.py
│   ├── offline_erm.py
│   ├── dynamic_erm.py
│   ├── dynamic_js.py
│   └── dynamic_residual.py
├── training/
│   ├── trainer.py
│   ├── optimizer.py
│   ├── scheduler.py
│   ├── checkpoint.py
│   ├── reproducibility.py
│   └── distributed.py
├── evaluation/
│   ├── classification.py
│   ├── robustness.py
│   ├── consistency.py
│   ├── residual_probe.py
│   ├── real_xrd.py
│   └── interpretability.py
├── tests/
└── reports/
```

Codex 在现有仓库中适配，不得仅因本备忘录而大规模重命名已有稳定目录。若已有等价模块，优先增量重构。

---

# 13. 最小实现顺序

## Phase 0：只读审计与映射

输出：

```text
reports/external_code_audit.md
reports/pysimxrd_parameter_audit.csv
reports/reuse_mapping.json
```

不得修改正式训练逻辑。

## Phase 1：统一数据与模拟接口

实现：

```text
PeakTable
PhysicsParams
PhysicsParameterSampler
XRDRenderer
FrozenEvaluationManifest
```

先只支持 V6 首版四扰动：

```text
zero shift
peak broadening
background
noise
```

其他扰动放入 feature flag，默认关闭。

## Phase 2：动态双视图数据流

实现并测试：

```text
同一 material_id
→ 两套不同参数
→ x1/x2
→ 同一标签
→ 参数完整记录
```

验证集和 OOD 集必须冻结并可重放。

## Phase 3：PAMPT B0–B3

严格按 V6：

```text
B0：普通 Patch Transformer
B1：+ 多尺度局部峰形编码
B2：+ 一阶/二阶导数先验
B3：+ Peak-Prior-Guided Attention
```

只在 Dynamic ERM 下做 Pilot。选出最小有效模型后写入：

```text
backbone_frozen.yaml
backbone_frozen.sha256
backbone_selection_report.md
```

## Phase 4：统一 Trainer 与四 Strategy

先完成 A/B/C，再完成 D 的交替优化。

## Phase 5：公平性与复现

实现 per-step seed/parameter stream 复用，保证 B/C/D 看到相同动态视图。

## Phase 6：评价与机制验证

至少输出：

```text
in-range accuracy / macro-F1
OOD severity curve
per-class recall
ECE 或 Brier score
JS consistency
residual probe accuracy
residual magnitude distribution
real-XRD results
```

---

# 14. Dynamic Residual 的工程红线

主方法不是把 `r` 直接推向零，也不是让 residual head 输出均匀分布。

必须执行交替优化：

## Step A：更新 residual classifier

```text
冻结 encoder/classifier
r = residual(h1.detach(), h2.detach())
最小化 CE(g(r), y)
```

目标：让 residual classifier 尽可能发现残差中的类别信息。

## Step B：更新主网络

```text
冻结 residual classifier 参数
不 detach h1/h2
最小化分类损失
同时最大化 residual classifier 对真实类别的 CE
或使用 V6 指定的等价解耦目标
```

目标：编码器保留分类能力，同时使测量残差难以携带晶系类别信息。

必须写单元测试确认：

- Step A encoder 无梯度；
- Step B residual head 参数无梯度；
- Step B encoder 有来自解耦项的梯度；
- `r(h1,h2) == r(h2,h1)`；
- x1/x2 交换不改变 residual loss。

---

# 15. 公平性和防数据泄漏要求

以下任一项失败，实验结果不得进入正式表格：

1. `material_id` 不跨 split；
2. structure fingerprint 不跨 split；
3. 同一结构所有 offline 视图不跨 split；
4. 动态训练视图只由 train structure 生成；
5. val/test/OOD 参数来自冻结 manifest；
6. B/C/D 使用同一 pair seed stream；
7. 四方法使用同一冻结 backbone；
8. 不根据 test/OOD/real 结果选择 backbone 或超参数；
9. 不把真实测试谱混入训练；
10. 不使用完整 IL/OL 成品数据库替代 MP 结构管线；
11. 不使用谱级随机 split；
12. 每次实验保存 git commit、配置、环境、数据 manifest 和 renderer hash。

---

# 16. 允许的 baseline 范围

## 主矩阵

```text
Offline Multi-view ERM
Dynamic ERM
Dynamic JS
Dynamic Residual
```

## Backbone Pilot

```text
B0 / B1 / B2 / B3
```

## 资源允许时的附加 baseline

```text
C0：NoPoolCNN
F0：FFT + B0
```

暂不增加：

```text
GAN 去噪
半监督伪标签
多模态元素组成
WPEM 端到端
多模型集成
大型预训练 Transformer
```

---

# 17. Codex 每次提交的输出规范

每个实现阶段必须同时提交：

```text
1. 源码变更
2. 配置样例
3. 单元测试
4. 最小运行命令
5. 生成文件清单
6. 已知限制
7. 与 V6 条款的映射
8. 是否改变科学定义：必须回答 No；若 Yes，停止并请求确认
```

禁止只回复“已经实现”，必须给出实际路径、测试结果和关键统计。

推荐每轮报告格式：

```markdown
## 本轮完成
## 修改文件
## 测试结果
## 数据/配置 hash
## 与 V6 的一致性
## 未完成与风险
## 下一步最小任务
```

---

# 18. 当前立即执行的任务

Codex 下一轮应按以下顺序工作：

1. 读取 V6 主文件并生成条款映射，不修改方法定义。
2. 扫描当前项目已有模块，避免重复创建。
3. 对 Pysimxrd 输出逐参数审计表，特别核查单位和公式。
4. 设计 `PeakTable / PhysicsParams / PhysicsParameterSampler / XRDRenderer` 接口。
5. 先实现四个首版扰动和冻结 manifest，不实现额外模型。
6. 写一个最小 DynamicPairDataset：输入两个 MP 结构样本，能确定性地产生可重放的 x1/x2。
7. 补齐 structure-level split 和 fingerprint 防泄漏测试。
8. 再进入 PAMPT B0–B3，不提前实现 Dynamic Residual。

---

# 19. 一句话项目定位

> 本项目不是复现 XQueryer，而是以 Materials Project 结构和文献约束的物理模拟为基础，使用峰形感知的 PAMPT，在严格结构级 OOD 设定中比较离线多视图、在线动态增广、输出一致性与测量残差解耦，从而判断怎样的训练目标最能抵抗未知测量条件和真实实验域偏移。

---

# 20. 最终验收句

只有当下列闭环全部成立，才可宣称 V6 已完成：

```text
MP 结构可追溯
→ structure-level split 无泄漏
→ 物理参数有来源且可审计
→ 动态双视图可重放
→ PAMPT 消融后冻结
→ 四方法共享视图和训练预算
→ in-range / OOD / real 完整评价
→ residual probe 验证机制
→ 所有配置、数据与代码可复现
```
