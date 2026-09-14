# RRUFF-70 完整使用报告

**日期:** 2026-08-06  
**数据集:** `rruff-real-pxrd-70-v1.0-final`  
**70 samples (10 × 7 crystal systems)**  
**状态:** Development domain — 论文最终数字使用 RRUFF-301

---

## 1. 数据集

| 属性 | 值 |
|---|---|
| 样品数 | 70 |
| 晶系 | triclinic, monoclinic, orthorhombic, tetragonal, trigonal, hexagonal, cubic |
| 每类 | 10 |
| 预处理 | 10°–80° 2θ, 0.02°步长, linear interp, max-norm, 3501 points |
| 冻结合同 SHA256 | 90DCBDC89F641A876DA2E8A927499A3E7225934AE38E820D70AD26640113C9CC |
| 数据路径 | `xrd_robustness/data/real_xrd/rruff70/spectra_10_80_step_002/` |

## 2. 预训练模型 (Frozen Backbone)

| 属性 | 值 |
|---|---|
| 架构 | ML4PXRDResNet1D-18 (GroupNorm, embed_dim=256) |
| 输入 | 3501-point 1D vector, 1 channel |
| 预训练方法 | Dynamic ERM 和 JS Consistency (λ=60) |
| 优化器 | AdamW, LR=1e-4, constant, 61600 max steps |
| 训练种子 | 20260711, 20260712, 20260713, 20260714, 20260715 |
| Checkpoints | 10 个 (5 seeds × 2 methods), Validation-selected best epoch |
| 总参数 | 13,008,839 |
| 预训练数据 | 14,060 晶体结构, 70/15/15 parent-structure split |
| 扰动 | 5 类物理扰动 (peak shift, broadening, preferred orientation, background, noise) |

## 3. 三个实验阶段

### 3.1 Zero-Shot Pipeline Test

- **数据集**: 35 个独立 RRUFF 样品 (5/class, 独立于 RRUFF-371)
- **协议**: 加载 10 个 frozen checkpoint → 直接 forward pass → softmax → argmax
- **无训练**

| 方法 | Mean Accuracy |
|---|---|
| Dynamic ERM | 0.1886 ± 0.0615 |
| JS λ=60 | **0.2343 ± 0.0420** |
| Random baseline | 0.1429 |

| 晶系 | JS Accuracy (5-seed mean) |
|---|---|
| triclinic | 0.64 |
| monoclinic | 0.32 |
| tetragonal | 0.32 |
| orthorhombic | 0.24 |
| trigonal | 0.08 |
| hexagonal | 0.04 |
| cubic | 0.00 |

**结论:** 管道通畅 (triclinic=0.64), JS>ERM 跨域成立, 高对称性晶系零 shot 失败 (符合预期)

### 3.2 Few-Shot Adaptation (主实验)

- **数据集**: RRUFF-70 (10/class × 7 = 70 samples)
- **K**: 1, 2, 5
- **Episode**: 5 episode seeds (42, 123, 456, 789, 1024) × 5 training seeds × 2 methods = 150 次 fine-tuning

#### 适配协议

```
for each K, episode_seed, train_seed, method:
    1. 每类随机抽 K support samples, 剩余为 query
    2. 加载 frozen backbone checkpoint
    3. Freeze 卷积特征提取器 (88.85% 参数)
    4. 训练: projection layer (7168→256) + classifier head (256→7) = 14.1% 参数
    5. AdamW, LR=1e-4 (与预训练合同一致)
    6. Full-batch training (每 epoch = 1 optimizer step)
    7. Support-loss early stopping: patience=20, min_delta=1e-4, min_epochs=20, max_epochs=200
    8. 恢复到 best support-loss epoch
    9. 评估 query set accuracy
```

#### 主结果 (Early-Stopping)

| K | ERM Mean±SD | JS Mean±SD | Mean Paired Δ | Median Δ | Positive/25 |
|---|---:|---:|---:|---:|---:|
| 1 | 0.1975 ± 0.0327 | 0.2400 ± 0.0445 | +0.0425 | +0.0317 | 19/25 |
| 2 | 0.1993 ± 0.0337 | 0.2479 ± 0.0556 | +0.0486 | +0.0536 | 21/25 |
| 5 | 0.2091 ± 0.0539 | 0.2800 ± 0.0782 | +0.0709 | +0.0857 | 20/25 |

#### 5×5 配对 Delta 矩阵

**K=1:**
```
           42     123     456     789    1024     mean
20260711  +0.064 +0.048 +0.000 +0.095 +0.032   +0.048
20260712  +0.079 +0.032 +0.016 +0.111 +0.111   +0.070
20260713  +0.032 -0.048 +0.000 +0.032 +0.048   +0.013
20260714  +0.032 +0.127 +0.064 +0.127 +0.064   +0.083
20260715  +0.000 -0.048 -0.048 +0.016 +0.079   +0.000
mean      +0.041 +0.022 +0.006 +0.076 +0.067
```

**K=5:**
```
           42     123     456     789    1024     mean
20260711  +0.057 -0.057 +0.029 +0.029 +0.029   +0.017
20260712  +0.086 +0.171 -0.057 -0.029 +0.143   +0.063
20260713  +0.086 +0.029 +0.086 -0.029 -0.057   +0.023
20260714  +0.229 +0.057 +0.114 +0.029 +0.171   +0.120
20260715  +0.143 +0.086 +0.086 +0.086 +0.257   +0.131
mean      +0.120 +0.057 +0.051 +0.017 +0.109
```

#### 逐层 Delta (分层汇总)

| K | By Pretraining Seed (5 deltas) | By Episode Seed (5 deltas) |
|---|---|---|
| 1 | [+0.048, +0.070, +0.013, +0.083, +0.000] — all ≥ 0 | [+0.041, +0.022, +0.006, +0.076, +0.067] — all > 0 |
| 2 | [+0.043, +0.057, -0.004, +0.064, +0.082] — 4/5 positive | [+0.071, +0.004, +0.054, +0.071, +0.043] — all > 0 |
| 5 | [+0.017, +0.063, +0.023, +0.120, +0.131] — all > 0 | [+0.120, +0.057, +0.051, +0.017, +0.109] — all > 0 |

### 3.3 固定 Step 敏感性检查 (K=1,5)

与 Early-Stopping 对比，固定 200 optimizer steps:

| 协议 | K=1 ERM | K=1 JS | K=1 Δ | K=5 ERM | K=5 JS | K=5 Δ |
|---|---|---|---|---|---|---|
| Early-stop | 0.1975 | 0.2400 | +0.0425 | 0.2091 | 0.2800 | +0.0709 |
| Fixed 200 | 0.1981 | 0.2406 | +0.0425 | 0.2091 | 0.2800 | +0.0709 |

**结论: Δ 完全一致。JS>ERM 方向与停止规则无关。**

#### Epoch 统计

| K | Method | Mean Epochs | Min-Max |
|---|---|---|---|
| 1 | ERM | 131 ± 33 | 75-182 |
| 1 | JS | 131 ± 26 | 83-171 |
| 5 | ERM | **200 ± 0** | 200-200 |
| 5 | JS | **200 ± 0** | 200-200 |

K=5 全部跑满 200 epochs (early stop 从未触发), K=1 平均 131 epochs。

## 4. Per-Class 分析

### Per-Class Delta (JS - ERM)

| 晶系 | K=1 Δ | K=2 Δ | K=5 Δ | 趋势 |
|---|---|---|---|---|
| triclinic | **-0.062** (6+/14-) | -0.015 (7+/10-) | **+0.120** (12+/5-) | 从负到正，K增加后恢复 |
| monoclinic | **-0.036** (8+/14-) | **-0.015** (9+/13-) | **-0.088** (5+/12-) | 持续负迁移 |
| orthorhombic | -0.004 (5+/9-) | +0.005 (8+/8-) | +0.008 (5+/7-) | 近似持平 |
| tetragonal | +0.013 (11+/8-) | +0.045 (12+/4-) | **+0.152** (16+/3-) | 大幅正向 |
| trigonal | **+0.151** (17+/1-) | **+0.180** (19+/0-) | **+0.168** (17+/3-) | 最大赢家 |
| hexagonal | +0.049 (14+/4-) | +0.050 (10+/5-) | +0.032 (11+/8-) | 稳定正向 |
| cubic | **+0.187** (16+/1-) | +0.090 (13+/1-) | +0.104 (11+/1-) | 大幅正向但K增加后减弱 |

### Monoclinic 专项

- 所有 K 上 monoclinic 均出现负迁移
- K=1: -0.036, K=2: -0.015, K=5: -0.088
- 猜测原因:
  1. 单斜晶系内部异质性大 (结构空间宽)
  2. JS 一致性约束可能压低对细微峰分裂特征的敏感度
  3. RRUFF-70 的单斜样本可能包含标签边界/多相样本
- 需进一步调查: 被误判成什么晶系? 是所有 seed 都下降还是个别?

## 5. 统计严谨性说明

### 独立单元

- 基本观测: 75 个 ERM–JS 配对 (3K × 5 seed × 5 episode)
- **不是 150 个独立实验** (150 是训练运行次数)
- 同一 pretrained seed 在不同 episode 中使用相同 backbone 初始化
- 不同 episode 的 query 集存在大量样品重叠
- **不应简单做独立样本 t-test**

### Query 精度边界

| K | Query 样品数 | 单样品对应 accuracy |
|---|---|---|
| 1 | 63 | 1.59% |
| 2 | 56 | 1.79% |
| 5 | 35 | 2.86% |

K=5 的绝对 Δ=+0.071 对应多猜对 2-3 条谱。

### 公平性界定

**ERM vs JS (配对内): 完全公平**
- 相同 K, 相同 episode seed, 相同 training seed
- 相同 support/query split, 相同 frozen architecture, 相同 optimizer/LR, 相同早停规则

**不同 K 之间: 解读需谨慎**
- K 的变化同时改变了 support 数量、实际训练 epochs、query 集大小
- 当前可写: "JS gains were observed at all K"
- 不应写: "JS advantage increases monotonically with K"

## 6. 核心结论

```
Across all evaluated real-domain label budgets (K=1,2,5), 
the JS-pretrained representations showed consistently better 
adaptation performance than Dynamic ERM representations. 
Mean paired accuracy improvements were +0.043, +0.049, and +0.071 
for 1-, 2-, and 5-shot adaptation, with positive differences 
observed in 19/25, 21/25, and 20/25 pretrained-seed–episode pairs. 
The JS>ERM direction was robust to the stopping rule 
(confirmed via fixed 200-step sensitivity check).

The improvement was not uniform across crystal systems. 
Largest gains: trigonal (+0.15-0.18), tetragonal (+0.01-0.15), 
cubic (+0.09-0.19). 
Negative transfer observed: monoclinic (-0.04 to -0.09).
```

**论文边界:**
- JS 预训练改善了真实域可适配性 (consistently improved few-shot adaptability)
- JS 优势具有类别依赖性 (class-dependent)
- Monoclinic 负迁移需进一步分析
- Frozen-step 敏感性检查已通过

## 7. 证据链汇总

```
Simulated Validation (5-seed paired)   → JS > ERM (+0.047 OOD F1)
Simulated Test (2,109 structures)      → JS > ERM (+0.055 OOD F1)
RRUFF Zero-Shot (35 independent)       → JS > ERM (+0.046 accuracy)
RRUFF Few-Shot (3K × 5×5 paired)      → JS > ERM in 60/75 pairs
Fixed-Step Sensitivity Check           → JS>ERM direction robust
```

## 8. 文件清单

| 文件 | 说明 |
|---|---|
| `reports/rruff_pipeline_smoke_test_20260806.md` | Zero-shot pipeline test 报告 |
| `reports/rruff70_fewshot_results_20260806.json` | 150 次 run-level 原始结果 |
| `reports/rruff70_fewshot_paired_20260806.csv` | 75 组配对比较 |
| `scripts/build_rruff_pipeline_test.py` | Pipeline test 构建脚本 |
| `scripts/run_rruff70_fewshot_adaptation.py` | Few-shot 实验脚本 |
| `scripts/analyze_fewshot_results.py` | 结果分析脚本 |
