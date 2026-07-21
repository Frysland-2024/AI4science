# XRD Robustness 项目方法论更新 V6
## Peak-Aware Multi-Scale Patch Transformer + Offline/Dynamic ERM + Dynamic JS + Dynamic Measurement-Residual Decorrelation

> 目标读者：Codex、项目协作者、后续论文写作者  
> 状态：**本文件在完整保留 V5 数据、训练目标、公平性与评价体系的基础上，正式升级主干网络。V6 覆盖 V5 中“普通 1D Patch Transformer”相关设计。**  
> 当前正式方案：**Materials Project 晶体结构 + 物理测量扰动 + Peak-Aware Multi-Scale Patch Transformer（PAMPT）+ Offline Multi-view ERM / Dynamic ERM / Dynamic JS / Dynamic Measurement-Residual Decorrelation。**

---

# 0. V6 相对 V5 的核心变化

V6 不改变 V5 的四种训练方法，也不改变残差解耦主假设；本轮只升级统一 backbone，并增加严格的 backbone 消融协议。

四级训练方法链保持不变：

```text
Offline Multi-view ERM
        ↓
Dynamic ERM
        ↓
Dynamic JS Consistency
        ↓
Dynamic Measurement-Residual Decorrelation（主方法）
```

V6 的新增与修改：

1. 将普通 `1D Patch Transformer` 升级为 `Peak-Aware Multi-Scale Patch Transformer（PAMPT）`。
2. 输入除原始 XRD 强度外，增加一阶导数与二阶导数通道，用于显式提示峰边缘、峰顶、峰肩与重叠峰。
3. 在 patch embedding 前加入浅层一维多尺度局部峰形编码器，默认感受野为 `5 / 11 / 21`。
4. 局部编码器不使用 MaxPooling，避免丢失窄峰、弱峰和精细峰间关系。
5. 将非重叠 patch 改为默认 50% 重叠 patch，首选 `patch_size=16, stride=8`。
6. 在全局 self-attention 之外增加 `Peak-Prior-Guided Attention`：以主特征为 Query，以导数与峰形先验 token 为 Key/Value。
7. 仍然只使用最终 pooled embedding \(h\) 进行分类和测量残差构造，不改变 V5 的残差定义。
8. 新增 backbone 消融链：`B0 → B1 → B2 → B3`，且仅在 Dynamic ERM 下完成。
9. backbone 选定后必须冻结模型配置与 hash，再运行四种正式训练方法；禁止不同训练方法使用不同 backbone。
10. 不照搬二维 Gabor、空间金字塔或完整 TASAM 架构，只迁移“多尺度局部表征 + 先验引导注意力”的思想并重新设计为一维 PXRD 模块。

当前 backbone 演进链：

```text
B0：普通 Patch Transformer
B1：B0 + 多尺度局部峰形编码
B2：B1 + 导数先验通道
B3：B2 + 峰形先验引导注意力（完整 PAMPT）
```

V6 的实验原则：

> 先在小规模 Pilot 中用 Dynamic ERM 选择最小且有效的 backbone，再用同一冻结 backbone 比较 Offline ERM、Dynamic ERM、Dynamic JS 与 Dynamic Residual。任何正则化结论都不得与 backbone 差异混杂。

---

# 1. 项目的当前核心问题

项目不再只问：

> 一致性正则化能否提高 XRD 分类鲁棒性？

而是拆成三个递进问题：

## Q1：在线动态物理采样是否优于固定离线多视图训练？

比较：

```text
Offline Multi-view ERM
vs
Dynamic ERM
```

## Q2：在相同动态双视图下，传统输出一致性是否带来额外收益？

比较：

```text
Dynamic ERM
vs
Dynamic JS
```

## Q3：对于 XRD，直接对齐预测分布，还是解耦测量残差，更适合未知测量条件与真实实验域？

比较：

```text
Dynamic JS
vs
Dynamic Measurement-Residual Decorrelation
```

当前最重要的科学假设是：

> 同一晶体在不同物理测量条件下产生的表征差异不必被完全消除；更合理的目标是允许非零测量残差存在，同时抑制其中与晶系类别相关的判别信息，从而将测量因素与晶体对称性语义解耦。

---

# 2. 项目的正式贡献定位

本项目不是：

```text
仅仅把 CNN 换成 Transformer
仅仅增加数据增强
仅仅使用一个新的损失函数
仅仅比较谁的 accuracy 更高
照搬二维视觉模型到一维 XRD
```

V6 的正式方法组合是：

```text
物理可解释的 XRD 测量条件生成
+
结构级严格数据划分
+
峰形感知的局部—全局一维表征
+
在线动态双视图训练
+
传统输出一致性基线
+
测量残差—晶系标签解耦
+
OOD 与真实实验谱验证
```

backbone 贡献的准确定位：

```text
浅层多尺度 Conv1D：
捕获局部峰顶、峰宽、峰肩、重叠峰与背景形态

overlapping patch：
降低峰被 patch 边界切断的风险

global self-attention：
建模远距离峰间关系与全谱峰拓扑

peak-prior-guided attention：
用导数和多尺度峰形先验引导注意力，而非让模型完全从零学习
```

它不是独立的深层 CNN，也不是模型 zoo；主干仍以 Patch Transformer 的全局序列建模为核心。

与 Bin Cao 相关工作的关系：

```text
Bin Cao / SimXRD / XQueryer：
- 大规模、高保真模拟数据基础设施
- 多条件离线数据库
- FFT、CNN、cross-attention 等结构识别架构
- 多模型 benchmark 与实验部署

本项目：
- 研究在线动态测量环境下的训练目标
- 设计适合一维 XRD 的局部峰形 + 全局峰关系 backbone
- 区分离线多视图、动态增广、输出一致性和残差解耦
- 重点分析测量变化是否污染晶系语义
- 通过 residual probe 验证表示机制
```

与胡皓天 SD3Net 的关系：

```text
SD3Net：
原始高光谱场景 vs 结构化生成场景
→ 构造特征残差
→ 让残差趋向类别无关

本项目：
同一晶体在测量条件 θ1 vs θ2 下的动态 PXRD
→ 构造对称测量残差
→ 让残差难以预测晶系类别
```

与 TASAM 类工作的关系：

```text
TASAM：
多尺度局部结构
+ 全局注意力
+ 领域先验引导

本项目：
一维多尺度峰形编码
+ 全谱 self-attention
+ 导数/峰形先验引导
```

正式写作必须使用：

> inspired by / adapted from / reformulated for PXRD

不得声称：

> 残差无关思想由本项目首次提出。  
> PAMPT 是 TASAM 的直接复现。  
> 浅层 Conv1D 本身构成完整方法创新。

在完成系统文献检索前，也不得直接声称：

> 首次将该方法用于 XRD。

---

# 3. 当前唯一数据与训练主线

```text
Materials Project 晶体结构
        ↓
结构筛选、标准化、标签复核、去重
        ↓
structure-level split
        ↓
缓存理想峰位、峰强与反射信息
        ↓
┌──────────────────────────────┐
│ Offline branch               │
│ 预先生成固定 K 条物理视图     │
│ → Offline Multi-view ERM     │
└──────────────────────────────┘
        或
┌──────────────────────────────┐
│ Dynamic branch               │
│ 每次读取重新采样 θ1、θ2       │
│ → x1、x2                     │
│ → Dynamic ERM / JS / Residual│
└──────────────────────────────┘
        ↓
共享 PAMPT backbone
├── 原始强度分支
├── 一阶/二阶导数先验分支
├── 多尺度局部峰形编码
├── overlapping patch embedding
├── global self-attention
└── peak-prior-guided attention
        ↓
in-range / OOD / real-XRD evaluation
        ↓
residual probe 与机制分析
```

晶体结构是唯一语义锚点。

本项目仍然不依赖：

```text
canonical clean spectrum
reference mother spectrum
全量 reference HDF5
CrystDB
多模型 zoo
半监督伪标签
```

导数与峰形先验全部由当前输入谱在线、确定性计算，不构成额外标签，也不需要 clean reference。

---

# 4. 数据源与持久化字段

正式结构数据源：

```text
Materials Project API
```

建议持久化字段：

```text
material_id
formula
original_structure
standardized_structure
space_group_mp
space_group_recomputed
crystal_system
nsites
is_stable
energy_above_hull
structure_fingerprint
split
```

必须生成的审计文件：

```text
retrieval_manifest.json
structure_manifest.csv
label_mismatch_report.csv
duplicate_report.csv
failed_structures.csv
split_manifest.csv
```

所有 API 字段名和查询参数必须依据运行时官方文档确认，不得依赖过期示例硬编码。

---

# 5. 结构筛选、标签复核与去重

初始筛选：

```text
deprecated = false
结构可被 pymatgen 正常读取
Spglib 可识别空间群
MP 标签与重算标签一致
标准传统晶胞原子数 ≤ 500
去除重复或等价结构
优先保留稳定结构
```

同时保留：

```text
original_structure
standardized_structure
```

用途：

- 原始结构：数据追溯；
- 标准化结构：标签复核、指纹、去重和模拟。

所有筛选规则必须进入配置文件，不得散落在代码中。

---

# 6. Structure-level split

必须先划分结构，再生成任何离线或动态 PXRD 视图。

正确：

```text
structure A → train
structure B → validation
structure C → test
```

错误：

```text
先生成大量谱
→ 再按谱图随机划分
```

强制要求：

```text
同一 material_id 不得跨 split
同一 structure fingerprint 不得跨 split
同一结构的全部离线视图不得跨 split
同一结构的全部动态视图不得跨 split
```

主任务：

> out-of-library crystal-system classification，即测试结构在训练阶段从未出现。

---

# 7. XRD 物理扰动体系

首版动态与离线模拟均至少支持：

```text
zero shift
peak broadening
background
noise
```

后续可增加：

```text
preferred orientation / intensity variation
lattice strain
thermal vibration
instrumental convolution
```

每项扰动必须具有明确参数：

| 扰动 | 建议记录字段 |
|---|---|
| 峰位偏移 | `delta_2theta_deg` |
| 峰展宽 | `fwhm_deg` 或物理等价参数 |
| 噪声 | `snr_db`、`noise_std_ratio` |
| 背景 | `background_type`、`background_to_peak_ratio` |
| 峰强变化 | `intensity_scale_range` |
| 组合复杂度 | `active_perturbation_count` |

每项扰动还必须记录：

```text
apply_probability
sampling_distribution
min_value
max_value
random_seed
severity_level
```

统一强度等级：

```text
Level 0：无扰动
Level 1：很轻
Level 2：轻度
Level 3：中度
Level 4：较强
```

重要限制：

> 数值范围不得凭感觉设定。正式范围必须结合 XRD 文献、仪器说明、实验数据或导师确认后冻结。

---

# 8. 峰表缓存与渲染

为了避免每次训练都重算完整衍射，可缓存：

```text
ideal peak positions
ideal peak intensities
reflection metadata
structure-level simulation intermediates
```

训练或离线生成阶段再完成：

```text
peak shift
peak broadening
background rendering
noise injection
intensity variation
```

缓存不是 canonical reference spectrum。

它只用于工程加速，不改变方法学定义。

---

# 9. PhysicsParameterSampler

实现：

```python
PhysicsParameterSampler
```

至少支持：

```python
sample_train()
sample_offline()
sample_val_in_range()
sample_test_in_range()
sample_test_ood()
```

要求：

- `sample_train()`：连续范围在线采样；
- `sample_offline()`：为每个结构预生成固定 K 个参数组合；
- `sample_val/test_*()`：从冻结 manifest 中读取；
- OOD 范围必须与训练范围有明确、可审计的边界差异；
- 所有采样均可通过 seed 完整重放。

---

# 10. 主模型：Peak-Aware Multi-Scale Patch Transformer（PAMPT）

## 10.1 当前唯一正式主干

```text
Peak-Aware Multi-Scale Patch Transformer
缩写：PAMPT（工作名，投稿前需检索是否重名）
中文：峰形感知多尺度 Patch Transformer
```

设计目标：

> 用浅层一维多尺度局部编码捕获单峰与局部峰群形态，用 Transformer 建模远距离峰间关系，再利用导数与峰形先验引导注意力关注具有结构意义的区域。

不把以下内容作为当前主线：

```text
vanilla Transformer
深层独立 CNN
完整 XQueryer 复现
二维 Gabor 直接迁移
完整 TASAM 复现
多架构模型 zoo
```

---

## 10.2 总体编码流程

```text
输入 XRD：x ∈ R^L
        │
        ├── Signal branch
        │   x
        │   → 多尺度局部峰形编码
        │   → overlapping patch embedding
        │   → 主 tokens H
        │
        └── Prior branch
            [一阶导数, 二阶导数]
            → 轻量先验编码
            → overlapping patch embedding
            → 先验 tokens P
                    ↓
        Global Self-Attention blocks
                    ↕
        Peak-Prior-Guided Attention blocks
                    ↓
             mean pooling
                    ↓
            pooled embedding h
                    ↓
      7-class crystal-system head
```

---

## 10.3 输入归一化与先验通道

原始输入：

\[
x\in\mathbb{R}^{L}
\]

首版先验通道：

\[
d_1 = \nabla x,\qquad d_2=\nabla^2 x
\]

组合为：

\[
X_{\mathrm{prior}}
=
[x,d_1,d_2]
\in\mathbb{R}^{3\times L}
\]

建议实现：

```text
1. 对当前谱执行与所有方法一致的强度归一化
2. 使用固定有限差分核计算一阶与二阶导数
3. 边界使用 reflect padding
4. 每个通道单独做稳定缩放或 LayerNorm
5. 不对不同训练方法使用不同平滑或导数参数
```

可采用的固定差分核：

\[
k_1=\frac{1}{2}[-1,0,1]
\]

\[
k_2=[1,-2,1]
\]

注意：

- 导数会放大高频噪声；
- 首版允许在求导前使用一个固定、很轻的 Gaussian smoothing；
- smoothing 参数必须写入配置并对四种方法完全一致；
- 不允许依据测试集或真实谱单独调节平滑强度。

首版默认：

```text
prior_channels = [first_derivative, second_derivative]
raw signal remains in the signal branch
```

暂不加入：

```text
人工 peak picking 标签
Rietveld 拟合参数
WPEM 分解结果
clean-reference residual
手工选择的峰索引
```

---

## 10.4 一维多尺度局部峰形编码器

目的：

```text
kernel 5  ：窄峰、峰顶、局部边缘
kernel 11 ：一般峰形、峰肩、近邻峰
kernel 21 ：宽峰、重叠峰、局部背景
```

默认并行分支：

\[
F_k=\operatorname{PWConv}
\left(
\operatorname{GELU}
\left(
\operatorname{DWConv}_{k}(x)
\right)
\right),
\quad
k\in\{5,11,21\}
\]

融合：

\[
F_{\mathrm{local}}
=
\operatorname{Conv}_{1\times1}
\left[
F_5;F_{11};F_{21}
\right]
+
\operatorname{Proj}(x)
\]

首版工程配置：

```text
branch_channels = 32
num_branches = 3
fusion_dim = 128
padding = same
activation = GELU
normalization = LayerNorm 或 BatchNorm1d（二选一后冻结）
residual_connection = true
```

强制要求：

```text
不使用 MaxPooling
不降低原始序列长度
不在局部编码器中堆叠深层 CNN
```

原因：

> 本模块的任务只是提供局部峰形 inductive bias，而不是替代 Transformer；池化可能抹去窄峰、弱峰和峰间细节。

---

## 10.5 先验分支

先验分支只处理：

\[
[d_1,d_2]
\]

建议结构：

```text
2-channel derivative input
→ Conv1D(kernel=5, channels=32)
→ GELU
→ Conv1D(kernel=11, channels=64)
→ GELU
→ projection to d_model
```

输出：

\[
F_{\mathrm{prior}}\in\mathbb{R}^{d_{\mathrm{model}}\times L}
\]

先验分支的作用不是直接预测类别，而是提供：

```text
峰边缘位置
峰顶与曲率
峰肩与重叠峰线索
局部形态变化
```

---

## 10.6 Overlapping Patch Embedding

普通非重叠 patch 可能把峰切在边界上。

V6 默认：

```text
patch_size = 16
stride = 8
overlap = 50%
```

备选：

```text
patch_size = 32
stride = 16
```

实现：

```python
nn.Conv1d(
    in_channels=feature_dim,
    out_channels=d_model,
    kernel_size=patch_size,
    stride=stride,
)
```

主分支与先验分支必须使用：

```text
相同 patch_size
相同 stride
相同 token 数
```

得到：

\[
H\in\mathbb{R}^{N\times d},
\qquad
P\in\mathbb{R}^{N\times d}
\]

其中 \(H\) 是主 token，\(P\) 是峰形先验 token。

---

## 10.7 位置编码

首版允许：

```text
learnable 1D positional embedding
或
fixed sinusoidal positional encoding
```

只选择一种并冻结。

必须保证：

- 输入长度变化时有明确插值或裁剪策略；
- Offline、Dynamic 与真实谱使用同一 2θ / d-spacing 网格；
- 不把仪器或数据集 ID 编入位置编码。

---

## 10.8 Global Self-Attention

主 token 首先学习全谱关系：

\[
H'
=
H+
\operatorname{MHSA}
\left(
\operatorname{LN}(H)
\right)
\]

它负责建模：

```text
远距离峰之间的相对关系
多个峰群的联合出现
全谱峰密度与分布
弱峰与主峰之间的组合
晶系相关的全局峰拓扑
```

---

## 10.9 Peak-Prior-Guided Attention

主特征作为 Query，先验 token 作为 Key 和 Value：

\[
Q=W_QH,
\qquad
K=W_KP,
\qquad
V=W_VP
\]

\[
H_{\mathrm{guided}}
=
H+
\operatorname{softmax}
\left(
\frac{QK^\top}{\sqrt d}
\right)V
\]

直观含义：

```text
主分支：
决定当前分类表征需要查询什么

先验分支：
提示哪些位置具有峰顶、峰肩、边缘和曲率变化
```

首版 4 个 block 建议交替：

```text
Block 1：Global Self-Attention
Block 2：Peak-Prior-Guided Attention
Block 3：Global Self-Attention
Block 4：Peak-Prior-Guided Attention
```

每个 block 均包含：

```text
Pre-LN
attention
residual connection
MLP
residual connection
```

禁止首版加入：

```text
双向 cross-attention
多层 prior 更新
复杂 gating 网络
token pruning
多尺度 token merge
```

---

## 10.10 Pooling 与分类头

默认：

```text
mean pooling
```

得到：

\[
h
=
\frac{1}{N}
\sum_{i=1}^{N}H_i^{(L)}
\in\mathbb{R}^{d}
\]

分类头：

\[
p=C(h)\in\mathbb{R}^{7}
\]

首版允许在 Pilot 中比较：

```text
mean pooling
vs
CLS token
```

但一旦选定，四种正式方法必须完全一致。

---

## 10.11 初始配置

| 参数 | V6 初始值 |
|---|---:|
| input length | 约 3500 |
| signal channels | 1 |
| prior channels | 2 |
| local kernels | 5 / 11 / 21 |
| branch channels | 32 |
| fusion dimension | 128 |
| patch size | 16 |
| patch stride | 8 |
| embedding dimension | 128 |
| Transformer blocks | 4 |
| self-attention blocks | 2 |
| prior-guided blocks | 2 |
| attention heads | 4 |
| MLP ratio | 4 |
| dropout | 0.1 |
| pooling | mean |
| output classes | 7 |

Pilot 只允许小范围比较：

```text
patch_size/stride ∈ {(16,8), (32,16)}
pooling ∈ {mean, CLS}
local_encoder ∈ {off, on}
prior_guided_attention ∈ {off, on}
```

禁止大规模架构搜索。

---

## 10.12 Backbone 消融协议

所有 backbone 消融只能使用：

```text
Dynamic ERM
```

定义：

### B0：原始 Patch Transformer

```text
raw XRD
→ non-overlap 或原始 patch embedding
→ Transformer
```

### B1：多尺度局部编码

```text
B0
+ kernels 5/11/21
+ overlapping patches
```

### B2：增加导数先验通道

```text
B1
+ first derivative
+ second derivative
```

但暂不使用 prior-guided cross-attention，仅在输入或局部层融合。

### B3：完整 PAMPT

```text
B2
+ separate prior tokens
+ Peak-Prior-Guided Attention
```

选择规则：

```text
优先看 OOD Macro-F1、Robustness AUC、worst-group F1
其次看 in-range Macro-F1
同时考虑参数量、训练稳定性和推理成本
```

复杂度约束：

> 若 B3 相比 B1/B2 没有稳定、可复现的鲁棒性收益，则选择更简单的 B1 或 B2，不得为了“方法看起来复杂”而强行保留 B3。

backbone 选定后必须保存：

```text
model_config.yaml
model_config_hash
parameter_count
FLOPs 或近似计算量
training_seed
selection_manifest
```

---

## 10.13 特征与残差接口

主分类特征仍定义为分类头之前的最终 pooled embedding：

\[
h = E_{\mathrm{PAMPT}}(x)\in\mathbb{R}^{d}
\]

V6 仍只使用这一层构造残差：

\[
\tilde h_i
=
\frac{h_i}{\|h_i\|_2+\epsilon}
\]

\[
r
=
\left|
\tilde h_1-\tilde h_2
\right|
\]

暂不加入：

```text
多层残差
局部 token residual
attention-map residual
prior-token residual
MRCE 式多尺度残差融合
复杂 cross-layer feature matching
```

理由：

> backbone 已经增加结构复杂度；残差主方法必须继续使用单一、可审计的 pooled representation，避免同时改变表征层级和正则化机制。

---

## 10.14 推理阶段

推理时保留：

```text
signal branch
prior branch
PAMPT backbone
main classifier
```

丢弃：

```text
training-time residual classifier
post-hoc residual probe
```

导数与峰形先验由单条输入 XRD 在线确定性计算，因此不需要成对输入，也不需要 reference spectrum。

---

# 11. 四种正式训练方法

## 11.1 Method A：Offline Multi-view ERM

### 定义

每个训练结构预先生成固定的 K 条物理扰动谱：

\[
\mathcal{X}^{\mathrm{off}}_z
=
\{G(z,\theta_1),\ldots,G(z,\theta_K)\}
\]

训练期间只重复读取这些固定视图，不再在线重新采样。

损失：

\[
L_{\mathrm{offline}}
=
L_{\mathrm{cls}}(C(E(x)),y)
\]

### 一句话解释

> 每个晶体提前生成若干条固定扰动谱，训练时反复使用这些离线数据，只做普通监督分类。

### 回答的问题

> 固定离线多条件数据库训练能达到什么水平？

### 定位

- 强于旧版“一结构一条谱”的 Fixed-ERM；
- 更接近 SimXRD 式离线多条件数据库范式；
- 是辅助基线，不是主方法。

---

## 11.2 Method B：Dynamic ERM

### 定义

同一结构在每次读取时重新采样两组物理参数：

\[
x_1=G(z,\theta_1),
\qquad
x_2=G(z,\theta_2)
\]

经过共享编码器和分类头：

\[
h_1=E(x_1),\quad h_2=E(x_2)
\]

\[
p_1=C(h_1),\quad p_2=C(h_2)
\]

分类损失：

\[
L_{\mathrm{cls}}
=
\frac{1}{2}
\left[
CE(p_1,y)+CE(p_2,y)
\right]
\]

Dynamic ERM 总损失：

\[
L_{\mathrm{DERM}}=L_{\mathrm{cls}}
\]

### 一句话解释

> 同一晶体每次动态生成两条新谱，两条都用真实标签训练，但不额外约束它们必须一致。

### 回答的问题

> 单靠在线动态物理增广能获得多少鲁棒性？

---

## 11.3 Method C：Dynamic JS Consistency

### 定义

使用与 Dynamic ERM 完全相同的：

```text
structure_id
θ1、θ2
x1、x2
encoder forward
classification loss
```

令：

\[
m=\frac{p_1+p_2}{2}
\]

Jensen–Shannon 一致性损失：

\[
L_{\mathrm{JS}}
=
\frac{1}{2}KL(p_1\|m)
+
\frac{1}{2}KL(p_2\|m)
\]

总损失：

\[
L_{\mathrm{DJS}}
=
L_{\mathrm{cls}}
+
\lambda_{\mathrm{JS}}L_{\mathrm{JS}}
\]

### 一句话解释

> 在 Dynamic ERM 基础上，再要求同一晶体两条动态谱的最终预测概率尽量接近。

### 回答的问题

> 传统输出级一致性是否能在动态增广基础上进一步提升鲁棒性？

### 为什么只保留 JS

两个动态视图地位对称，没有：

```text
teacher / student
clean / noisy anchor
weak / strong view
source / target direction
```

因此 JS 比单向 KL 更自然。

V5 不再把以下三者同时作为实验：

```text
ordinary KL
symmetric KL
JS
```

JS 作为传统输出一致性的唯一代表即可。

---

## 11.4 Method D：Dynamic Measurement-Residual Decorrelation

### 方法定位

这是 V5 的主方法。

它不是要求：

\[
h_1 \approx h_2
\]

也不是只要求：

\[
p_1 \approx p_2
\]

而是允许：

\[
h_1 \neq h_2
\]

同时抑制特征差异中的类别信息。

### 对称残差定义

由于本项目的两个动态视图没有固定的“源—生成”方向，首版使用对称残差：

\[
\tilde h_i
=
\frac{h_i}{\|h_i\|_2+\epsilon}
\]

\[
r
=
\left|
\tilde h_1-
\tilde h_2
\right|
\]

首版不要使用有方向的：

\[
r=h_1-h_2
\]

原因：交换 \(x_1,x_2\) 不应改变残差语义。

### 残差分类器

增加一个小型 MLP：

\[
q=D_r(r)
\]

其中 \(q\) 是残差对七个晶系的预测分布。

目标不是让 \(r=0\)，而是让一个训练充分的分类器难以通过 \(r\) 判断晶系。

令均匀分布：

\[
u=
\left[
\frac{1}{7},\ldots,\frac{1}{7}
\right]
\]

残差混淆损失：

\[
L_{\mathrm{ind}}
=
KL(q\|u)
=
\log 7-H(q)
\]

主分类损失仍然是：

\[
L_{\mathrm{cls}}
=
\frac{1}{2}
\left[
CE(p_1,y)+CE(p_2,y)
\right]
\]

编码器目标：

\[
L_{\mathrm{DMRD}}
=
L_{\mathrm{cls}}
+
\lambda_{\mathrm{res}}L_{\mathrm{ind}}
\]

### 一句话解释

> 同一晶体生成两条动态谱，允许其中间特征不同，但要求这些特征差异无法有效预测晶系类别。

### 回答的问题

> 与直接强制预测一致相比，把测量差异与晶系语义解耦是否更适合 XRD？

### 术语限制

论文中可以写：

```text
measurement-residual decorrelation
residual class-independence regularization
measurement-semantic disentanglement
```

但不得声称已经数学证明：

\[
r \perp y
\]

更准确的表述是：

> adversarially reduce the class-predictive information contained in the measurement residual.

---

# 12. 为什么不能直接让残差头输出均匀分布

如果编码器和残差分类器同时最小化：

\[
KL(D_r(r)\|u)
\]

残差分类器可能学会一个退化解：

```text
无论输入是什么
→ 永远输出七类均匀分布
```

此时高熵不代表残差真的不含类别信息。

因此必须采用对抗式交替优化。

---

# 13. 主方法的交替优化

每个 batch 执行两个逻辑步骤。

## Step A：训练残差分类器寻找类别信息

冻结或 detach 编码器输出：

\[
L_{\mathrm{probe}}
=
CE(D_r(\operatorname{stopgrad}(r)),y)
\]

优化：

```text
仅更新 residual classifier D_r
不更新 encoder E
不更新主分类头 C
```

目的：

> 让残差分类器尽可能强，主动发现残差中的晶系信息。

## Step B：训练编码器消除残差类别信息

冻结残差分类器参数，但保持从 \(D_r(r)\) 到 \(r\) 的梯度：

\[
L_{\mathrm{encoder}}
=
L_{\mathrm{cls}}
+
\lambda_{\mathrm{res}}
KL(D_r(r)\|u)
\]

优化：

```text
更新 encoder E
更新主分类头 C
不更新 residual classifier D_r
```

目的：

> 让编码器保留正常分类能力，同时使残差分类器无法再从测量残差中识别晶系。

## 推荐工程实现

使用两个 optimizer：

```python
optimizer_main   # encoder + main classifier
optimizer_res    # residual classifier
```

首版优先使用交替优化，不优先使用 GRL。

原因：

- 梯度流更容易审计；
- `uniform confusion` 的目标比简单反向 CE 更直观；
- 更适合写单元测试；
- 更容易定位训练退化。

---

# 14. 推荐训练伪代码

```python
# x1, x2, y are shared with Dynamic ERM and Dynamic JS
h1 = encoder(x1)
h2 = encoder(x2)
p1 = classifier(h1)
p2 = classifier(h2)

h1n = l2_normalize(h1)
h2n = l2_normalize(h2)
r = torch.abs(h1n - h2n)

# ---------------------------------
# Step A: update residual classifier
# ---------------------------------
set_requires_grad(residual_classifier, True)
optimizer_res.zero_grad()
q_probe = residual_classifier(r.detach())
loss_probe = cross_entropy(q_probe, y)
loss_probe.backward()
optimizer_res.step()

# ---------------------------
# Step B: update main network
# ---------------------------
set_requires_grad(residual_classifier, False)
optimizer_main.zero_grad()

loss_cls = 0.5 * (
    cross_entropy(p1, y) +
    cross_entropy(p2, y)
)

q_confuse = residual_classifier(r)
uniform = torch.full_like(q_confuse, 1.0 / num_classes)
loss_ind = kl_divergence(q_confuse, uniform)

loss_main = loss_cls + lambda_res * loss_ind
loss_main.backward()
optimizer_main.step()

set_requires_grad(residual_classifier, True)
```

实现时必须确认 KL 的参数方向与 PyTorch API 定义，避免把 `KL(q || u)` 错写成其他方向。

---

# 15. 训练稳定性策略

首版允许以下稳定策略：

## 15.1 分类 warm-up

训练初期先只优化：

\[
L_{\mathrm{cls}}
\]

建议 warm-up：

```text
前 5–10 个 epoch
或总 epoch 的前 10%
```

## 15.2 λ 逐步增加

\[
\lambda_{\mathrm{res}}(t)
\]

从 0 逐步增加到目标值，避免主任务尚未成形时残差约束过强。

## 15.3 梯度裁剪

对 Transformer 和 residual head 进行必要的 gradient clipping。

## 15.4 小范围超参数

首轮只比较：

```text
lambda_res ∈ {0.01, 0.1, 1.0}
residual_head_depth ∈ {1, 2}
```

不要进行大规模搜索。

---

# 16. 四种方法的公平性

## 16.1 三个动态方法的严格公平性

以下三组必须共享完全相同的：

```text
Dynamic ERM
Dynamic JS
Dynamic Measurement-Residual Decorrelation
```

共享内容：

```text
structure_id
θ1、θ2
x1、x2
batch order
encoder architecture
classifier architecture
初始化方案
optimizer 与 scheduler
训练 epoch
主干 forward 次数
分类损失
测试 manifest
随机种子集合
```

三者唯一差别：

```text
Dynamic ERM：只有 L_cls
Dynamic JS：L_cls + λ_JS L_JS
Dynamic Residual：L_cls + λ_res L_ind，并增加残差头交替优化
```

## 16.2 视图复用

推荐两种方式：

### 方式 A：冻结 per-step seed manifest

```text
每个 seed、epoch、step 对应固定 θ1、θ2
所有动态方法重放同一视图对
```

### 方式 B：预先记录参数流

```text
只保存 θ1、θ2 与 seed
不保存全量谱
训练时重新渲染
```

禁止：

```text
每个方法独立随机采样不同动态谱
```

否则结果差异可能来自采样噪声。

## 16.3 Offline 与 Dynamic 的公平性

Offline 与 Dynamic 无法做到“见过完全相同的唯一谱集合”，因为二者定义不同。

但必须控制：

```text
相同 structure split
相同 batch size
相同总训练 step
相同每 step 主干 forward 数
相同模型与优化器
相同测试集
相近总样本暴露数量
```

Offline 建议设置：

```text
每个结构固定 K 条谱
每个 epoch 从固定 K 条中采样
```

K 必须报告，并进行最小必要的敏感性分析。

不要把 Offline 设计得故意过弱。

---

# 17. 四种方法的实验优先级

## 主实验

```text
Dynamic ERM
Dynamic JS
Dynamic Measurement-Residual Decorrelation
```

这三组回答核心算法问题。

## 次级基线

```text
Offline Multi-view ERM
```

它回答离线数据库与在线采样的差异，并与现有 XRD 模拟训练范式形成对话。

## 后续可选消融

```text
Dynamic JS + Residual Decorrelation
signed residual vs absolute residual
normalized vs unnormalized residual
不同 residual head 容量
不同 λ_res
```

第一轮不要把 `JS + residual` 混合作为主方法，因为会难以判断收益来自哪项约束。

---

# 18. 评价体系

## 18.1 分类与鲁棒性指标

主指标：

```text
Macro-F1
balanced accuracy
performance drop（ΔF1）
Robustness AUC
worst-group F1
ECE
real-XRD Macro-F1
```

必须绘制：

```text
severity level → Macro-F1
severity level → ΔF1
severity level → ECE
```

分别测试：

```text
zero shift severity
broadening severity
noise severity
background severity
combined perturbation severity
```

## 18.2 输出一致性指标

```text
prediction agreement
JS divergence between paired predictions
correct-and-consistent rate
```

注意：

> 一致率不能单独作为成功指标，因为模型可能稳定地预测错误。

## 18.3 残差机制指标

主方法必须额外报告：

```text
post-hoc residual probe accuracy
post-hoc residual probe Macro-F1
residual prediction entropy
residual norm
classification performance
```

理想证据不是残差归零，而是：

```text
residual norm 非零
+
独立 probe 难以预测晶系
+
OOD / real-XRD 分类性能提高
```

在七类平衡数据下，随机准确率约为：

\[
\frac{1}{7}\approx14.3\%
\]

但正式评价不得只看 accuracy，还应报告 Macro-F1，并考虑类别不平衡。

---

# 19. 独立 Post-hoc Residual Probe

训练过程中的 residual classifier 不能作为唯一证据。

正式 probe 流程：

```text
1. 训练完成后冻结 encoder
2. 使用冻结 train/val/test pair manifests 生成残差
3. 新建一个随机初始化、从未参与主训练的 MLP probe
4. 仅在 train residual 上训练 probe
5. 用 val 选择停止点
6. 在 test residual 上报告 accuracy / Macro-F1
```

要求：

- probe 容量对所有方法一致；
- Dynamic ERM、Dynamic JS、Residual 方法都要训练 post-hoc probe；
- 不能只对主方法训练 probe；
- probe 的输入必须来自相同结构和相同动态视图 manifest；
- 需要多随机种子报告均值与标准差。

Residual 方法成功的必要但不充分条件：

```text
post-hoc probe 表现显著低于 Dynamic ERM / Dynamic JS
```

同时还必须保证主分类不明显退化。

---

# 20. 真实 XRD 验证

真实测试谱可来自：

```text
RRUFF
opXRD
本校实验数据
其他标签可靠的公开实验集
```

原则：

```text
真实测试集不参与模型选择
真实测试集不参与扰动范围调参
尽量保留单相、标签可靠、测量信息明确的样本
```

流程：

```text
Materials Project 结构
→ 模拟训练
→ 冻结模型
→ 真实实验 XRD 直接测试
```

注意：

- 若真实数据只有每个样品一条谱，只评估分类、校准和 sim-to-real 泛化；
- 不强行在无重复测量的真实数据上计算 paired residual；
- 若存在同一样品的重复测量，才额外做真实 paired consistency / residual 分析。

---

# 21. 当前任务性质

本项目属于：

```text
supervised robustness learning
supervised consistency regularization
single-source domain generalization style evaluation
physics-guided data augmentation
measurement-semantic disentanglement
```

不是：

```text
FixMatch
FlexMatch
半监督伪标签
无标签目标域适应
教师—学生弱强增强框架
```

除非后续真正加入无标签实验谱，否则不要引入：

```text
pseudo-label
confidence threshold
curriculum pseudo-labeling
```

---

# 22. Pilot 设计

Pilot 分为两个阶段，禁止直接把 backbone 选择与正则化比较混在同一张主结果表中。

## 22.1 Pilot-A：Backbone 选择

数据规模政策：

```text
软件测试：140 个结构
开发实验：3,500 个结构
正式实验：14,000 个结构
```

三档数据必须是同一正式数据库中的嵌套子集，不得分别维护数据库。140 只用于软件测试；PAMPT 选择和四种方法开发实验使用 3,500；正式比较使用 14,000。

Backbone 选择的正式开发规模固定为 3,500 个结构。

固定训练方式：

```text
Dynamic ERM only
```

依次比较：

```text
B0：普通 Patch Transformer
B1：多尺度局部峰形编码 + overlapping patch
B2：B1 + 导数先验通道
B3：完整 PAMPT
```

最低要求：

```text
1–2 个随机种子用于快速筛选
相同 dynamic paired-view manifest
相同训练 step
相同优化器与 scheduler
相同验证/OOD manifest
```

选择标准：

```text
OOD Macro-F1
Robustness AUC
worst-group F1
in-range Macro-F1
训练稳定性
参数量与吞吐量
```

选择完成后：

```text
冻结 backbone 配置
生成 config hash
不再针对不同训练方法单独改 backbone
```

## 22.2 Pilot-B：四种训练方法闭环

使用冻结 backbone，跑通：

```text
结构读取
→ 标签复核
→ structure-level split
→ 峰表缓存
→ Offline K-view 数据
→ Dynamic paired views
→ PAMPT
→ Offline ERM
→ Dynamic ERM
→ Dynamic JS
→ Dynamic Residual
→ 冻结 in-range / OOD 测试
→ post-hoc residual probe
```

最低要求：

```text
3 个随机种子
相同动态视图参数流
统一评价脚本
统一结果表
```

Pilot-B 通过并冻结配置后，再扩大到：

```text
14,000 个正式结构
```

不设置 1,400 或 7,000 的强制中间阶段。除非审稿或结果异常明确要求，否则不做数据规模曲线。

---

# 23. 推荐代码结构

```text
xrd_robustness/
├── data/
│   ├── mp_raw/
│   ├── mp_processed/
│   ├── offline_views/
│   └── manifests/
│
├── src/
│   ├── data/
│   │   ├── mp_download.py
│   │   ├── structure_filter.py
│   │   ├── structure_dataset.py
│   │   ├── offline_multiview_dataset.py
│   │   ├── dynamic_pair_dataset.py
│   │   └── split_manager.py
│   │
│   ├── simulation/
│   │   ├── peak_cache.py
│   │   ├── renderer.py
│   │   ├── parameter_sampler.py
│   │   ├── offline_view_generator.py
│   │   ├── paired_view_generator.py
│   │   └── validation.py
│   │
│   ├── models/
│   │   ├── derivative_channels.py
│   │   ├── multiscale_peak_encoder.py
│   │   ├── peak_prior_encoder.py
│   │   ├── overlap_patch_embedding_1d.py
│   │   ├── positional_encoding_1d.py
│   │   ├── global_self_attention_block.py
│   │   ├── peak_prior_attention_block.py
│   │   ├── xrd_patch_transformer_baseline.py
│   │   ├── xrd_pampt.py
│   │   ├── classifier_head.py
│   │   └── residual_classifier.py
│   │
│   ├── training/
│   │   ├── offline_erm.py
│   │   ├── dynamic_erm.py
│   │   ├── dynamic_js.py
│   │   ├── dynamic_residual_decorrelation.py
│   │   ├── consistency_losses.py
│   │   ├── residual_losses.py
│   │   └── trainer_factory.py
│   │
│   └── evaluation/
│       ├── backbone_ablation.py
│       ├── perturbation_eval.py
│       ├── ood_eval.py
│       ├── calibration_eval.py
│       ├── real_xrd_eval.py
│       ├── residual_probe.py
│       └── representation_diagnostics.py
│
├── configs/
│   ├── data.yaml
│   ├── simulation.yaml
│   ├── offline_views.yaml
│   ├── model_patch_transformer_baseline.yaml
│   ├── model_pampt.yaml
│   ├── backbone_ablation.yaml
│   ├── training_offline_erm.yaml
│   ├── training_dynamic_erm.yaml
│   ├── training_dynamic_js.yaml
│   └── training_dynamic_residual.yaml
│
└── tests/
    ├── test_structure_split.py
    ├── test_no_leakage.py
    ├── test_offline_views_fixed.py
    ├── test_dynamic_resampling.py
    ├── test_view_pairing.py
    ├── test_dynamic_methods_view_identity.py
    ├── test_derivative_channels.py
    ├── test_derivative_determinism.py
    ├── test_multiscale_encoder_shapes.py
    ├── test_local_encoder_no_pooling.py
    ├── test_overlap_patch_coverage.py
    ├── test_main_prior_token_alignment.py
    ├── test_peak_prior_attention_shapes.py
    ├── test_peak_prior_attention_gradient.py
    ├── test_pampt_forward.py
    ├── test_backbone_config_hash.py
    ├── test_residual_symmetry.py
    ├── test_residual_head_detach.py
    ├── test_residual_encoder_gradient.py
    ├── test_residual_head_frozen_in_main_step.py
    └── test_probe_protocol.py
```

---

# 24. 必须实现的 Backbone 与梯度流单元测试

## 24.1 导数通道确定性

同一输入、同一配置下：

```text
first derivative 完全一致
second derivative 完全一致
无随机平滑
无数据集依赖分支
```

## 24.2 导数边界与有限值

要求：

```text
输出长度与输入一致
无 NaN / Inf
常数输入的一阶、二阶导数接近零
```

## 24.3 多尺度编码形状

三个分支：

```text
kernel 5 / 11 / 21
```

输出序列长度必须一致，融合后维度符合配置。

## 24.4 不允许池化

测试模型图或模块属性，确认局部编码器中不存在：

```text
MaxPool1d
AvgPool1d
adaptive pooling
```

最终 mean pooling 例外。

## 24.5 Overlapping patch 覆盖

确认：

```text
stride < patch_size
主分支与先验分支 token 数相同
输入末端具有明确 padding / truncation 策略
```

## 24.6 Peak-prior attention 梯度

在 guided-attention block 中：

```text
主 token 分支有非零梯度
prior encoder 有非零梯度
Q/K/V projection 均有非零梯度
```

## 24.7 Backbone 输出接口

PAMPT 必须稳定返回：

```python
{
    "logits": logits,
    "pooled_embedding": h,
    "main_tokens": optional_H,
    "prior_tokens": optional_P,
}
```

正式训练默认只依赖：

```text
logits
pooled_embedding
```

## 24.8 Backbone 配置一致性

四种正式方法启动时必须检查同一个：

```text
model_config_hash
parameter_count
backbone_class_name
```

若不一致，训练应直接报错。

## 24.9 Residual symmetry

交换两个视图：

\[
r(h_1,h_2)=r(h_2,h_1)
\]

## 24.10 Probe step detach

在 residual classifier 更新时：

```text
residual classifier 有非零梯度
encoder 梯度为零或 None
main classifier 梯度为零或 None
```

## 24.11 Main step encoder gradient

在 residual confusion 更新时：

```text
encoder 能从 L_ind 获得非零梯度
main classifier 能从 L_cls 获得非零梯度
```

## 24.12 Residual head frozen

在主网络更新时：

```text
residual classifier 参数不发生变化
```

## 24.13 Dynamic view identity

Dynamic ERM、Dynamic JS、Dynamic Residual 在相同 run manifest 下必须读取完全相同的：

```text
structure_id
θ1、θ2
x1、x2
```

---

# 25. 团队分工建议

若增加一名协作者，可按模块分工，而不是各自重写整套代码。

## 协作者 A：离线与 ERM 基线

```text
Offline K-view 生成
Offline Multi-view ERM
Dynamic ERM
训练日志与可复现性
```

## 协作者 B：传统一致性

```text
Dynamic JS
λ_JS 小范围实验
输出一致性指标
JS 与 ERM 的公平性检查
```

## 项目负责人：主方法与整合

```text
Dynamic Residual Decorrelation
残差分类器与交替优化
post-hoc residual probe
OOD / real-XRD 机制分析
统一配置、图表和论文叙事
```

所有人必须共用：

```text
同一 Git 仓库
同一 structure split
同一 simulator
同一 model config
同一 evaluation scripts
```

禁止每个人维护一套互不兼容的 pipeline。

---

# 26. Codex 实施顺序

## Phase 1：从 V5 升级到 V6

1. 保留 V5 的 Materials Project、structure-level split、峰表缓存、四种 trainer、评价指标与 residual probe。
2. 不修改现有 Offline/Dynamic 数据定义。
3. 将旧 `xrd_patch_transformer.py` 保留为 B0 baseline。
4. 新增 PAMPT 组件，不直接覆盖旧模型，便于消融与回归测试。
5. 更新 README、配置文件和实验命名。

## Phase 2：实现 PAMPT 基础模块

按顺序实现：

```text
derivative_channels.py
multiscale_peak_encoder.py
peak_prior_encoder.py
overlap_patch_embedding_1d.py
peak_prior_attention_block.py
xrd_pampt.py
```

每完成一个模块立即补充单元测试。

## Phase 3：Backbone Pilot 消融

只使用：

```text
Dynamic ERM
```

比较：

```text
B0 / B1 / B2 / B3
```

要求：

```text
相同结构 split
相同动态视图 manifest
相同训练 step
相同优化器
相同评价 manifest
```

输出：

```text
in-range Macro-F1
OOD Macro-F1
Robustness AUC
worst-group F1
参数量
吞吐量
显存峰值
```

## Phase 4：冻结正式 Backbone

1. 按预设规则选择最小且有效的 backbone。
2. 保存 `model_config.yaml`。
3. 生成 `model_config_hash`。
4. 在四种 trainer 启动时强制校验 hash。
5. backbone 冻结指的是“架构与配置冻结”，不是冻结参数训练。

## Phase 5：完成四种训练模式

使用同一正式 backbone：

```text
offline_erm
dynamic_erm
dynamic_js
dynamic_residual
```

统一由 `trainer_factory.py` 调用。

## Phase 6：建立严格公平性

1. 实现 frozen per-step dynamic seed manifest。
2. 三个动态方法重放相同 θ1、θ2。
3. 控制主干 forward 次数。
4. 固定随机种子集合。
5. 输出实验配置 hash。
6. 输出 backbone hash。

## Phase 7：残差主方法与评价

1. 最终 pooled embedding 构造残差。
2. L2 normalize。
3. absolute difference。
4. 小型 residual MLP。
5. probe step。
6. encoder confusion step。
7. warm-up 与 λ ramp。
8. 梯度流单元测试。
9. in-range / OOD / ECE。
10. post-hoc residual probe。
11. real-XRD 接口。

## Phase 8：3,500 开发规模完整 Pilot

完成四种方法的：

```text
3 个以上随机种子
相同 test manifests
统一结果表
统一鲁棒性曲线
统一 residual probe 报告
统一 backbone 配置
```

Pilot 通过并冻结配置后，直接进入 14,000 正式实验规模。140 只承担软件测试，不承担正式 backbone 选择或科学结论。

---

# 27. 验收标准

## 数据与模拟

- [ ] Materials Project 是正式结构上游。
- [ ] structure fingerprint 不跨 split。
- [ ] 同一结构所有离线视图不跨 split。
- [ ] 同一结构所有动态视图不跨 split。
- [ ] Offline 视图在训练过程中保持固定。
- [ ] Dynamic 视图在不同 epoch 持续变化。
- [ ] 验证与测试使用冻结 manifest。
- [ ] 每条测试谱可追溯到所有扰动参数与 seed。

## Backbone

- [ ] B0 普通 Patch Transformer 被保留为消融基线。
- [ ] PAMPT 支持原始强度、一阶导数、二阶导数。
- [ ] 导数通道确定、可复现、无 NaN/Inf。
- [ ] 多尺度局部卷积使用 5/11/21 感受野或配置等价物。
- [ ] 局部编码器不使用 MaxPooling。
- [ ] 默认 patch 为 50% overlap。
- [ ] 主 token 与 prior token 数量一致。
- [ ] global self-attention 与 prior-guided attention 均可正常前向和反向。
- [ ] backbone 消融只在 Dynamic ERM 下完成。
- [ ] 正式 backbone 选定后生成 config hash。
- [ ] 四组使用同一 backbone class、配置与参数量。
- [ ] 模型能完成单 batch 过拟合测试。
- [ ] residual 只使用最终 pooled embedding。
- [ ] 当前 MVP 不依赖深层独立 CNN。

## Offline 公平性

- [ ] 报告每结构固定视图数 K。
- [ ] Offline 与 Dynamic 总 step 相同。
- [ ] 每 step 主干 forward 数相同。
- [ ] 测试集完全相同。

## 动态方法公平性

- [ ] Dynamic ERM、JS、Residual 使用相同 structure_id。
- [ ] 三者使用相同 θ1、θ2。
- [ ] 三者使用相同 x1、x2。
- [ ] 三者使用相同 L_cls。
- [ ] 三者使用相同主干 forward 次数。
- [ ] 三者使用相同 PAMPT config hash。
- [ ] Dynamic JS 唯一新增项是 L_JS。
- [ ] Dynamic Residual 唯一新增主约束是 residual decorrelation 模块。

## 残差训练

- [ ] Probe step 中 encoder 被 detach。
- [ ] Main step 中 residual head 被冻结。
- [ ] Main step 中 encoder 能收到 L_ind 梯度。
- [ ] residual 定义对视图交换不敏感。
- [ ] 使用独立 post-hoc probe 评价。
- [ ] 不以训练中辅助头高熵作为唯一成功证据。

## 评价

- [ ] 输出 Macro-F1、balanced accuracy、ΔF1。
- [ ] 输出 Robustness AUC、worst-group F1。
- [ ] 输出 ECE。
- [ ] 输出 correct-and-consistent rate。
- [ ] 输出 residual probe accuracy / Macro-F1。
- [ ] 输出 residual entropy 与 residual norm。
- [ ] 输出 backbone 参数量、吞吐量与显存峰值。
- [ ] 预留真实 XRD 测试接口。

---

# 28. 成功与失败判据

## 理想结果

```text
Dynamic Residual：
- clean / in-range 性能不明显下降
- OOD Macro-F1 高于 Dynamic ERM 与 Dynamic JS
- 真实 XRD 性能提高
- severity 增强时性能下降更慢
- post-hoc residual probe 接近随机或显著降低
- residual norm 保持非零
```

这支持：

> 模型没有简单压平两个视图，而是保留测量差异并减少其中的晶系信息。

## 仍然有价值的结果

若 Dynamic JS 与 Residual 都优于 ERM，但二者接近：

> 说明显式一致性有效，但残差解耦未显示明显额外优势。

若 Dynamic JS 优于 Residual：

> 说明当前 XRD 任务中直接输出对齐更简单有效，或残差定义、对抗训练仍需改进。

若 Dynamic ERM 已经最好：

> 说明动态物理增广本身已覆盖主要变化，额外正则化可能过强。

任何结果都必须报告，不得只保留支持主假设的实验。

---

# 29. 当前不做的内容

V6 第一阶段不要：

```text
恢复一结构一谱 Fixed-ERM
同时比较 JS、KL、symmetric KL
直接混合 JS + residual 作为主方法
加入多层残差
照搬 SD3Net 的全部生成模块
引入 SALS / MSVS / MRCE 的完整实现
照搬二维 Gabor 或二维空间金字塔
完整复现 TASAM
把深层 CNN 作为第二条主模型路线
同时加入 FFT、小波、Gabor、双 patch-size 多分支
加入复杂双向 cross-attention
引入伪标签
引入目标域数据适应
开展大规模模型 zoo
把 Transformer 或 Conv1D 本身包装成创新
```

Backbone 第一版只允许：

```text
原始强度
一阶导数
二阶导数
浅层 5/11/21 多尺度 Conv1D
50% overlapping patch
global self-attention
单向 peak-prior-guided attention
```

任何额外模块必须等 B0–B3 消融完成后再决定。

---

# 30. 当前项目正式定义

## 中文

> 本项目以 Materials Project 晶体结构作为语义锚点，通过物理可解释的 XRD 测量扰动构建离线多视图与在线动态双视图训练环境。模型采用峰形感知多尺度 Patch Transformer：浅层一维多尺度编码器提取峰顶、峰宽、峰肩、重叠峰和局部背景特征，重叠 patch 降低峰被边界切断的风险，全局自注意力建模远距离峰关系，峰形先验引导注意力则利用一阶、二阶导数提示结构显著区域。在冻结统一 backbone 配置后，项目比较 Offline Multi-view ERM、Dynamic ERM、Dynamic JS Consistency 与 Dynamic Measurement-Residual Decorrelation。核心目标是在严格匹配动态数据暴露和模型结构的条件下，检验传统输出一致性与测量残差类别解耦对未知测量条件和真实实验域泛化的影响。主方法不强制两种测量条件下的表征完全重合，而是允许非零测量残差存在，同时对抗性地降低该残差中可用于预测晶系类别的信息。

## English

> We use crystal structures from the Materials Project as semantic anchors and construct both offline multi-view and online dynamically resampled PXRD training environments through physically motivated measurement perturbations. The shared backbone is a Peak-Aware Multi-Scale Patch Transformer: a shallow multi-scale 1D encoder captures local peak morphology, overlapping patches reduce boundary fragmentation, global self-attention models long-range peak relationships, and peak-prior-guided attention uses first- and second-order derivative cues to highlight structurally informative regions. After freezing a single backbone configuration, we compare Offline Multi-view ERM, Dynamic ERM, Dynamic JS Consistency, and Dynamic Measurement-Residual Decorrelation. The central objective is to determine, under strictly matched dynamic data exposure and model architecture, whether conventional output-level consistency or explicit class-decorrelation of measurement-induced feature residuals provides better generalization to unseen measurement conditions and real experimental PXRD. Rather than forcing representations from two measurements to coincide, the proposed method allows non-zero residuals while adversarially reducing their predictive information about the crystal-system label.

---

# 31. 推荐论文方法名称

## Backbone 工作名

```text
Peak-Aware Multi-Scale Patch Transformer
PAMPT
```

中文：

```text
峰形感知多尺度 Patch Transformer
```

投稿前必须检索缩写是否与现有模型冲突；若重名，优先保留描述性全称并更换缩写。

## 主训练方法名称

```text
Dynamic Measurement-Residual Decorrelation
```

中文：

```text
动态测量残差解耦
```

更严格的替代表述：

```text
Dynamic Measurement-Residual Class-Independence Regularization
动态测量残差类别无关正则化
```

## 项目标题候选

```text
Peak-Aware Dynamic PXRD Classification via Measurement-Residual Decorrelation
```

或：

```text
Decoupling Measurement Variation from Crystal-System Semantics with a Peak-Aware Patch Transformer
```

或更保守：

```text
Robust Crystal-System Classification under Dynamic PXRD Measurement Perturbations
```

最终标题应由实验结果决定：

- 若 backbone 提升明显且消融充分，可进入标题；
- 若主要收益来自 residual method，则标题突出 residual decorrelation；
- 若两者均仅有有限收益，则使用保守的 robustness 标题。

---

# 32. Codex 本轮输出要求

完成 V6 改造后，Codex 必须输出：

```text
1. 修改文件清单
2. V5 中被覆盖的 backbone 逻辑
3. B0 baseline 的保留方式
4. 导数通道的计算、边界处理与确定性验证
5. 多尺度局部编码器结构
6. overlapping patch 的尺寸与 token 数
7. peak-prior-guided attention 的 Q/K/V 来源
8. PAMPT 前向输出接口
9. B0/B1/B2/B3 消融配置
10. backbone 选择规则与最终 config hash
11. 四种 trainer 共用同一 backbone 的验证
12. Offline K-view 数据生成方式
13. Dynamic paired-view 数据流
14. residual 定义与 residual head 结构
15. 交替优化的梯度流说明
16. 所有相关单元测试结果
17. 小规模端到端 pilot 日志
18. 分类、鲁棒性与校准指标
19. post-hoc residual probe 结果
20. 参数量、吞吐量、显存峰值
21. 当前失败模式与性能瓶颈
22. 下一步建议
```

本轮不要：

```text
直接运行正式大规模训练
删除 B0 baseline
让不同 trainer 使用不同 backbone
下载 CrystDB
生成 canonical reference spectrum
开展 CNN / RNN / Transformer 模型 zoo
引入二维 Gabor 或完整 TASAM
引入半监督伪标签
同时优化大量超参数
跳过 residual probe
只报告 accuracy
```

当前唯一优先级：

```text
Materials Project 结构
→ 结构级 split
→ 物理 XRD 扰动
→ PAMPT 模块实现
→ B0/B1/B2/B3 Dynamic-ERM Pilot
→ 冻结 backbone config
→ Offline K-view + Dynamic paired views
→ Offline ERM / Dynamic ERM / Dynamic JS / Dynamic Residual
→ 冻结 OOD 测试
→ 独立 residual probe
→ 真实 XRD 验证接口
```
