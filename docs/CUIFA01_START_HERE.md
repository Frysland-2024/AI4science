# cuifa01 从零接手 AI4Science / PXRD 项目

> **用途：** 给第一次接触这个项目的人看的零基础说明。默认你不知道 XRD、机器学习、这个仓库、历史版本号，也不知道为什么项目会从 FerroAI 一路变成现在这样。  
> **更新日期：** 2026-09-26  
> **本说明读取基线：** GitHub `main` 已读取至 `7ae035c7`（在创建本文件之前）。  
> **最重要的规则：** 本文是“入口地图”。当前科学事实以 `docs/CURRENT_STATE.md`、`xrd_robustness/reports/RESULTS.md`、冻结配置和较新的日期化 history note 为准；`archive/` 和旧版本号只用于追溯“为什么改”，不能拿来覆盖当前结论。

---

# 0. 如果你只有 3 分钟：先读这里

这个项目现在有两条必须分开的线。

## A. 已完成并冻结的主项目：PXRD 鲁棒七晶系分类

一句话：

> **同一个晶体结构，在不同测量条件下会得到不同的 PXRD。普通 Dynamic ERM 只知道这些谱“标签相同”；本项目进一步利用模拟器保留的“它们来自同一个母结构”这一关系，对两份预测施加 JS consistency，从而让模型对测量变化更稳定。**

核心逻辑：

```text
同一个 parent crystal structure
        ↓
在线模拟两种不同 measurement realization
        ↓
x1 ------------------ x2
 |                      |
ResNet                ResNet
 |                      |
p1                     p2
                       /
  ---- same label ----/
   -- same parent ----/

Dynamic ERM：只用两份 CE
Dynamic JS ：同样两份 CE + JS(p1,p2)
```

最终主方法：

- 任务：七晶系分类；
- Backbone：**ResNet-18-GN**；
- Baseline：**Dynamic ERM**；
- Method：**Dynamic JS Consistency**；
- `lambda_js = 60`；
- 数据：14,060 个 Materials Project 母结构；
- Train / Val / Test：9,842 / 2,109 / 2,109；
- 划分单位：**parent structure**，同一个母结构绝不能跨 split；
- 两种方法看到**完全相同的两张动态扰动谱**；唯一差别是 JS 是否利用 same-parent relationship。

最核心结果：

| 证据 | Dynamic ERM | Dynamic JS | 变化 |
|---|---:|---:|---:|
| Simulated Test，mean single-factor OOD Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | **+5.46 pp，5/5 seeds 正向** |
| RRUFF-301，1-shot/class Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | **+4.33 pp** |
| RRUFF-301，2-shot/class Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | **+4.60 pp** |
| RRUFF-301，5-shot/class Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | **+5.45 pp** |
| CNRS-318 zero-shot，seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | **+1.87 pp，5/5 seeds 正向** |

但必须同时记住：

> **CNRS 绝对性能依然很低，sim-to-real gap 没有被“解决”。**  
> 本项目可以说“一致性监督改善了鲁棒性、真实域适配标签效率和外部域趋势”，不能说“已经解决真实 XRD 自动分类”。

## B. 下一阶段：定量反演 / AI + 表征

方向是：

```text
XRD
→ robust structural recognition
→ quantitative physical parameters
→ physics / self-consistency check
→ refinement initialization
→ characterization workflow
```

但是：

- 这**不是**当前分类论文已经证明的结果；
- `xrd_inversion/` 的 Stage-1 structure–measurement factorization v1 已经 **NO-GO / ARCHIVED**；
- 现有数值 forward/inversion 基础设施仍可复用；
- 2026-09-19 提出的下一步“限定领域参数反演 + 物理自洽 + refinement”是**新的研究方向提案**，必须重新做数据可行性和预注册 Gate，不能把旧失败版本直接复活。

---

# 1. 先把最基本的词讲懂

## 1.1 XRD / PXRD 是什么

PXRD = Powder X-Ray Diffraction，粉末 X 射线衍射。

你可以把一张谱先想成：

```text
横轴：2θ（衍射角）
纵轴：强度
```

晶体有周期性的原子排列，因此会在某些角度出现衍射峰。

这些峰的：

- **位置**；
- **间距**；
- **相对强度**；
- **峰宽**；
- **缺失 / 出现关系**

都与晶体结构有关。

这个项目当前不是做完整结构求解，而是做更粗一级的任务：

> 输入一张 PXRD，判断它属于七个晶系中的哪一个。

七晶系：

1. triclinic 三斜；
2. monoclinic 单斜；
3. orthorhombic 正交；
4. tetragonal 四方；
5. trigonal 三方；
6. hexagonal 六方；
7. cubic 立方。

## 1.2 parent structure 是什么

这是整个项目最重要的词之一。

**parent structure = 母体晶体结构。**

例如 Materials Project 中一个具体晶体结构，我们先把它当作“真实潜在对象”：

```text
parent structure s
```

然后模拟器可以从同一个 `s` 生成很多张不同的 PXRD：

```text
s
├── measurement condition m1 → x1
├── measurement condition m2 → x2
├── measurement condition m3 → x3
└── ...
```

这些谱可以长得不一样，但对“晶系分类”这个任务来说，它们共享同一个结构标签。

**统计和 split 的独立单位必须优先看 parent，而不是“生成了多少张谱”。**

## 1.3 measurement view 是什么

对同一个母结构施加一次具体的模拟测量条件，得到的一张谱，叫一个 view。

本项目训练时每个 parent 同时在线生成两个 view：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

其中：

- `s`：固定母结构；
- `m1, m2`：两次独立随机测量状态；
- `g`：PXRD 模拟器。

## 1.4 ERM 是什么

ERM = Empirical Risk Minimization。

在这里不用把它想得太玄学，就是：

> 每张谱都拿正确标签做交叉熵分类训练。

因为我们的公平 baseline 也同时看两张 view：

```text
L_ERM = 0.5 * [ CE(p1,y) + CE(p2,y) ]
```

## 1.5 JS consistency 是什么

JS = Jensen–Shannon divergence。

先定义：

```text
m = 0.5 * (p1 + p2)
JS(p1,p2)
= 0.5 * KL(p1 || m)
+ 0.5 * KL(p2 || m)
```

它是一个**对称的概率分布差异度量**。

本项目的 JS loss：

```text
L_JS
= 0.5 * [ CE(p1,y) + CE(p2,y) ]
+ lambda_js * JS(p1,p2)
```

其中 `lambda_js = 60`。

它不是在说：

> 两张谱必须长得一样。

也不是在说：

> 两张谱中间 feature 必须完全一样。

它只要求：

> **既然两张谱来自同一个母结构，那么模型对“它属于哪个晶系”的概率判断不应该因为测量条件变化而任意漂移。**

## 1.6 OOD 是什么

OOD = Out-of-Distribution。

训练时模型只见过一定范围的扰动。

测试时故意给它更强、训练范围外的扰动：

> 看它是不是只记住了训练条件，还是学到了更稳健的结构判断。

## 1.7 zero-shot / few-shot

- **zero-shot**：真实域完全不参与训练和微调，直接测试；
- **few-shot**：给很少的真实标签做适配，比如每类 1 / 2 / 5 条。

在本项目：

- CNRS-318：**zero-shot external evaluation**；
- RRUFF-301：**K=1/2/5 few-shot adaptation**。

## 1.8 Macro-F1 为什么常用

七类任务不能只看 Accuracy。

Macro-F1 是：

> 每个类别先各自算 F1，再对七类等权平均。

所以不会让大类完全压住小类。

## 1.9 seed 是什么

神经网络训练有随机初始化、batch 顺序、动态扰动流等随机性。

不同 seed = 不同随机实验重复。

本项目正式训练 seeds：

```text
20260711
20260712
20260713
20260714
20260715
```

不能只拿“最好的一次”讲故事。

---

# 2. 为什么这个项目会出现：从 FerroAI 到 XRD

## 2.1 FerroAI 阶段留下的真正东西

FerroAI 最重要的遗产不是某个具体模型。

它让项目形成一个意识：

> **科研不是“跑一个模型出一个分数”，而是文献 → 数据 → 表征 → 模型 → 指标 → 误差分析 → 材料解释 → 可复现证据链。**

所以后来的 XRD 项目才会特别执着于：

- manifest；
- hash；
- 冻结配置；
- parent-level split；
- Validation / Test 隔离；
- matched control；
- negative result；
- 失败实验归档。

## 2.2 为什么最后选择 XRD，而不是 TEM / Raman

当时比较过 XRD、TEM、Raman。

PXRD 的优势是：

1. 有大量公开晶体结构来源；
2. 可以从 CIF / crystal structure 高通量模拟；
3. 七晶系标签相对明确；
4. 峰位、峰宽、相对强度有直接物理含义；
5. 可以人为控制“结构不变，只改变测量条件”；
6. 很适合研究 **simulation → experiment domain shift**。

所以项目不是：

> 先想用一个 Transformer，再硬找 XRD 场景。

而是先问：

> **哪里存在“可控干预 + 稳定标签 + 可复现实验”的科学数据问题？**

XRD 和“不变性 / 鲁棒性”问题自然对上了。

---

# 3. 第一个核心科学问题：会分类 ≠ 可靠

假设一个模型在理想模拟谱上准确率很高。

这不代表它面对：

- 峰整体偏一点；
- 峰变宽；
- 择优取向导致相对峰强改变；
- 背景抬高；
- 计数噪声变强

时仍然稳定。

而现实实验谱恰恰包含这些变化。

所以早期问题不是：

> 如何把 clean accuracy 从 95% 变成 96%？

而是：

> **同一个晶体结构，在标签不变的合理测量变化下，模型的判断能不能保持稳定？**

这就是整个 XRD robustness 项目的原点。

---

# 4. 项目为什么改了这么多次：版本演化一定要看懂

下面不是为了背版本号，而是要理解“为什么每次都改”。

| 阶段 | 当时在做什么 | 为什么后来改 | 最终留下什么 |
|---|---|---|---|
| FerroAI | 材料 ML 流水线 | 想研究更明确的 scientific-ML 问题 | 可复现证据链意识 |
| V6 | PAMPT + Offline/Dynamic ERM + JS + Residual | 主问题太散、backbone 未充分验证 | parent split、物理扰动、双视图 |
| V7 | 加 March–Dollase texture；又加 25/50/100% sample efficiency | 样本效率是另一条完整研究轴，会分散主线 | 五类扰动体系 |
| V8 | 想用 sample/instrument/acquisition state 做 structured simulation + residual decorrelation | 联合物理状态证据不够，方案太大 | “测量因素要有物理来源”的意识 |
| V9.2 / V9-T | 把方法收缩成 ERM / JS / Residual 可控比较，强调预注册和审计 | Residual/V10 暴露结构-测量不可轻易解耦；PAMPT 也有 learnability 问题 | 严格实验治理 |
| ResNet 诊断 | 用成熟 1D ResNet 检查是不是 backbone 问题 | PAMPT 连 Train 都没充分拟合 | ResNet-18-GN 成为公共 backbone |
| JS-only | 只保留最干净、最稳的方法问题 | Residual 路线归档 | 当前正式主线 |
| 真实域扩展 | RRUFF / CNRS | 不再追求一个“万能真实域分数” | few-shot 标签效率 + 独立 zero-shot |
| 解释阶段 | profile / class / case analysis | 不再堆新 loss | XRD-specific mechanism discussion |
| 定量反演探索 | 从分类走向物理参数 | Stage-1 factorization v1 NO-GO | forward/inversion 基础设施 + 下一代问题 |

这段历史非常重要：

> **项目不是“一开始就想好了 JS，然后一路顺利”。**  
> 真正的科研价值之一，是不断发现原问题太大、原假设不成立、对照不公平、模型学不会、真实数据不够可靠，然后主动收缩。

---

# 5. 五类物理扰动到底是什么

当前 frozen simulator 的主训练扰动是五类。

## 5.1 2θ shift：峰位整体偏移

可以理解为仪器零点误差等导致整张谱沿横轴有小偏移。

训练范围：

```text
Δ2θ ~ Uniform(-0.2°, +0.2°)
apply probability = 0.5
```

OOD：

```text
negative: -0.5° ~ -0.2°
positive: +0.2° ~ +0.5°
```

## 5.2 Broadening：峰展宽

训练：

```text
FWHM = 0.08° ~ 0.20°
```

OOD：

```text
FWHM = 0.20° ~ 0.35°
```

它会让相邻峰合并、肩峰消失，所以和母结构原本的峰间距高度相关。

## 5.3 Preferred orientation / texture：择优取向

用 March–Dollase 模型改变具体 `hkl` 反射的相对强度。

训练：

```text
r = 0.8 ~ 1.0
apply probability = 0.7
```

更强 texture OOD：

```text
r = 0.5 ~ 0.8
```

它不是随便缩放整条谱，而是 reflection-level 的强度变化。

## 5.4 Background：背景

训练主要用平滑 polynomial background，强度相对主峰较低。

训练 background-to-peak ratio：

```text
0 ~ 0.02
apply probability = 0.5
```

OOD 使用更强、形状更复杂的 Gaussian-process background：

```text
0.02 ~ 0.05
```

## 5.5 Noise：计数噪声 + 电子读出噪声

训练包含 Poisson / Poisson-Gaussian 观测过程。

训练 photon count scale：

```text
2500 ~ 40000
```

强噪声 OOD：

```text
100 ~ 2500
```

并允许更高 electronic noise。

## 5.6 一个极其重要的物理边界

这五类 perturbation 都是在：

> **固定 parent structure 的理想 diffraction representation 之上改变观测。**

它们不会：

- 重写原子坐标；
- 重写晶格参数；
- 把 structure A 变成 structure B；
- 改掉 crystal-system label。

所以：

```text
structure A
→ ideal PXRD of A
→ measurement perturbation
→ perturbed PXRD of A
```

不是：

```text
structure A
→ structural transformation
→ structure B
→ PXRD of B
```

这正是 same-parent measurement equivalence 可以成立的前提。

---

# 6. 数据是怎么一步一步构建的

## 6.1 母结构池

最终正式数据叫：

```text
formal_14060
```

共：

```text
14,060 parent structures
```

来自已审计的 Materials Project 结构层确定性合并。

## 6.2 先 split，再生成谱

顺序绝对不能反。

正确顺序：

```text
14,060 parent structures
        ↓
按 parent structure 划分
        ↓
Train 9,842
Val   2,109
Test  2,109
        ↓
每个 split 内再在线生成不同 PXRD views
```

这样一个 parent 的所有 view 永远只属于同一个 split。

当前 exact split：

- 70% Train；
- 15% Validation；
- 15% Test；
- 按 crystal system 分层；
- parent identity 用 `structure_fingerprint`。

**这只能叫 exact-parent-disjoint。**

不要乱说成：

- formula-disjoint；
- prototype-disjoint；
- chemical-family-disjoint；
- unseen-composition benchmark。

那些不是当前 split 保证的。

## 6.3 为什么不能随机切谱图

假如先给一个晶体生成 100 张扰动谱，然后随机分 80 张 Train、20 张 Test：

> Test 里虽然是“新谱”，但模型已经见过同一个母结构。

这会产生严重 leakage。

所以本项目统计与划分一直强调：

> 独立单位优先是 parent structure，不是谱图文件数量。

---

# 7. 一次训练 step 到底发生什么

对一个训练 parent：

## Step 1：取理想 reflection / peak table

从固定 structure 得到：

- peak positions；
- intensities；
- hkl；
- multiplicity；
- reciprocal-vector metadata。

## Step 2：独立采样两个 measurement state

```text
m1
m2
```

## Step 3：渲染两张 view

```text
x1 = g(s,m1)
x2 = g(s,m2)
```

## Step 4：质量 Gate

当前 frozen quality gate 包括：

- top-20 peak recall ≥ 0.8；
- retained integrated intensity ≥ 0.95；
- clipped fraction ≤ 0.55；
- 2θ window = 10°–80°；
- 非有限值拒绝；
- 负强度拒绝。

不合格 view 不能悄悄进训练。

## Step 5：送进同一个 ResNet

```text
x1 → ResNet → logits1 → p1
x2 → ResNet → logits2 → p2
```

## Step 6：根据方法算 loss

ERM：

```text
0.5 * (CE1 + CE2)
```

JS：

```text
0.5 * (CE1 + CE2)
+ 60 * JS(p1,p2)
```

## Step 7：反向传播更新模型

两种方法：

- parent 一样；
- 两张 view 一样；
- 数据量一样；
- backbone 一样；
- optimizer 一样；
- 训练预算一样；
- paired seeds 一样。

**唯一新增信息就是 same-parent relationship supervision。**

这件事以后有人质疑“JS 是不是因为看了更多数据才赢”，直接回答：

> **不是。ERM 也看完全相同的两张谱。**

---

# 8. 为什么最后用 ResNet，不用 PAMPT

项目早期对 PAMPT 有兴趣，是因为它看起来更“懂峰”：

- 多尺度卷积；
- patch token；
- attention；
- derivative / peak-aware prior。

但是科学实验首先要求：

> backbone 自己能把基础任务学会。

实际诊断中：

- PAMPT 在 clean 任务上 Train accuracy 只有约 0.638；
- 换成 1D ResNet 后，同类任务 Train accuracy 可以达到 1.0；
- Dynamic augmentation 也在 ResNet 上明显恢复。

所以判断变成：

> PAMPT 首先存在 **learnability / optimization bottleneck**，而不是一个“训练很好、只是 OOD 不好”的问题。

于是正式主线使用更成熟稳定的 **ResNet-18-GN**。

这不是“ResNet 比 Transformer 永远高级”。

它只说明：

> 在当前数据规模、当前 XRD 连续信号、当前动态扰动和当前研究目标下，ResNet 是更可靠的公共实验底座。

PAMPT 为什么失败本身后来被封存为一个未来 ML 问题：

> 科学上看起来更“懂峰”的复杂先验，为什么可能反而不如简单卷积？

这不是当前论文要回答的主问题。

---

# 9. 为什么 Residual 路线被封存

这段历史非常重要，因为它不是“跑分不好所以删掉”。

## 9.1 Residual 最初想做什么

直觉是：

```text
feature difference
≈ measurement difference
```

希望：

- residual 保留测量变化；
- residual 不携带晶系类别信息。

也就是想显式做：

> measurement / semantic disentanglement。

## 9.2 实验真正发现了什么

首先发现：

> residual 里确实可以读出晶系信息。

所以问题不是假的。

但后续：

- 对抗去相关训练不稳定；
- V10 加上“让 residual 更能预测测量因素”的正向监督后，测量信息确实更可解码；
- 可是独立 probe 发现晶系泄漏反而更强。

也就是说：

> “测量信息变多”并不会自动等于“晶体语义被分开”。

## 9.3 最重要的机制反思

XRD 的 measurement nuisance 往往不是简单加在 structure semantic 外面的独立噪声。

更像：

```text
residual = f(measurement condition, crystal structure)
```

例如：

- 同样的 broadening 到底会不会把两个峰合并，取决于原结构峰距；
- texture 改哪些峰，取决于这个结构具体有哪些 hkl reflections。

所以“让 residual 完全与晶系无关”可能是一个过强假设。

最后 Residual / V10 被**正式归档**。

当前主线不是：

```text
ERM vs JS vs Residual
```

而是：

```text
Dynamic ERM vs Dynamic JS
```

---

# 10. 为什么 JS 反而更干净

JS 不要求：

> 把 measurement 和 structure 在 feature 空间里彻底拆开。

它只要求：

> **结构没变时，任务输出不要因 measurement realization 乱跳。**

这是更弱、更安全的假设。

可以把它理解为：

```text
我不强迫你“忘掉”测量差异；
我只要求你在做晶系判断时，不要被这些差异轻易带跑。
```

这就是为什么当前项目最后从复杂的“显式解耦”收缩成了“task-level measurement equivalence”。

---

# 11. lambda_js=60 不是拍脑袋选的

这是别人很容易追问的地方。

## 阶段 1：Train-only 梯度尺度 Gate

只用 Train，不看 Validation/Test/真实谱。

候选：

```text
lambda = 3, 30, 60
```

测得辅助梯度 / classification 梯度的中位比大约：

| λ | ratio | 当时解释 |
|---:|---:|---|
| 3 | 0.087859 | weak |
| 30 | 0.877058 | material non-dominant |
| 60 | 1.754115 | dominant |

这个阶段只问：

> 参数尺度是否合法，会不会数值崩。

**不问谁分数最高。**

## 阶段 2：Validation-only 选择

相同 ResNet 训练合同比较：

| 方法 | in-range Macro-F1 | mean single-factor OOD Macro-F1 |
|---|---:|---:|
| ERM | 0.714013 | 0.666471 |
| JS 3 | 0.718417 | 0.676134 |
| JS 30 | 0.716428 | 0.676164 |
| **JS 60** | **0.729806** | **0.699742** |

预先规则：

1. in-range 相对 ERM 不能恶化超过 1 pp；
2. 合格候选中选 OOD 最好；
3. 平手再看 in-range / 较小 λ。

因此选：

```text
lambda_js = 60
```

此时：

- simulated Test 没看；
- RRUFF 没看；
- CNRS 没看。

后面真实域和 Test 结果出来后也没有再调 λ。

---

# 12. 正式 simulated Test 到底证明了什么

五个 matched training seeds。

核心结果：

```text
Mean single-factor OOD Macro-F1

ERM: 0.65074 ± 0.00721
JS : 0.70534 ± 0.00977
Δ  : +0.05460
5/5 training seeds positive
```

Accuracy：

```text
0.65078 → 0.70524
Δ +0.05445
```

所以最稳妥的主结论：

> **在完全匹配的数据暴露与训练条件下，显式使用 same-parent measurement-equivalence consistency，提高了 simulator-defined OOD robustness。**

---

# 13. 最漂亮的物理结果：不是所有扰动收益一样

六个 single-factor OOD 的 Macro-F1 改善：

| OOD 类型 | ERM → JS 提升 |
|---|---:|
| negative 2θ shift | +3.64 pp |
| positive 2θ shift | +4.36 pp |
| noise | +3.22 pp |
| background | +5.05 pp |
| **broadening** | **+8.40 pp** |
| **texture** | **+8.09 pp** |

最值得讲的是：

> broadening 和 texture 既是 ERM 比较困难的扰动，也是 JS 收益最大的扰动。

为什么？

### Broadening

FWHM 这个参数可以独立抽样，但最终后果取决于 parent：

- 哪些峰离得近；
- 哪些峰会重叠；
- 哪些肩峰会消失。

所以它是**结构依赖的 measurement effect**。

### Texture

March–Dollase 直接对具体 `hkl` reflection family 改相对强度。

所以它天然和具体 parent 的 reciprocal geometry 耦合。

这让项目从：

> “JS 平均涨了 5.46 pp”

推进成：

> **关系监督在 measurement nuisance 与 latent crystal structure 耦合更强时，价值尤其明显。**

注意：这个物理机制仍应写成**机制线索 / Discussion**，不是普适定律。

---

# 14. same-parent vs same-class 消融到底能说什么

后来做了一个探索性挑战：

- same-parent：同一个母结构的两张 view 做 JS；
- same-class：同一晶系、但不同 parent 的 view 做 JS。

100-epoch single-seed exploratory：

```text
mean OOD Macro-F1
same-parent ≈ 0.7106
same-class  ≈ 0.6979
Δ ≈ +1.27 pp
```

但总体差距不大，所以**不能**说：

> same-parent 一定比 same-class 普遍强很多。

真正有意思的是 profile-wise：

- shift / noise：差异近零甚至 same-class 略高；
- background：约 +0.70 pp；
- broadening：same-parent 约 +5.19 pp；
- texture：same-parent 约 +3.34 pp。

所以更克制的解释：

> generic consistency 本身就有价值；parent-specific relationship 的额外信息，可能主要体现在结构耦合更强的 nuisance 上。

这是单 seed post-hoc mechanism exploration。

**不能升级成确认性主结论。**

---

# 15. RRUFF-301：真实域为什么做 few-shot

## 15.1 数据怎么分

RRUFF-301：

- 301 条实验 PXRD；
- 七晶系各 43 条；
- adaptation pool：每类 10 条，共 70；
- locked test：每类 33 条，共 231；
- K = 1 / 2 / 5；
- 5 pretraining seeds × 5 episode seeds。

两种 pretrained model：

```text
Dynamic ERM pretrained
Dynamic JS pretrained
```

用完全相同的少量真实 support 做后续适配。

## 15.2 它回答的不是“zero-shot 万能分类器”

它问的是：

> **同样给很少的真实标签，哪种模拟预训练学到的表示更容易适配实验域？**

结果：

### K=1

```text
0.2847 → 0.3280
+4.33 pp
```

### K=2

```text
0.3026 → 0.3486
+4.60 pp
```

### K=5

```text
0.3555 → 0.4099
+5.45 pp
```

因此更稳妥的说法是：

> **相同少量真实标签预算下，JS-pretrained model 的 real-domain adaptation 更有效，表现出更高 label efficiency。**

不要偷换成：

> “已经证明只需要一半真实数据达到一样性能。”

除非专门有那个等性能阈值实验。

## 15.3 RRUFF 数据审计

adaptation / test：

- RRUFF ID overlap = 0；
- exact spectrum SHA overlap = 0；
- 16,170 个 cross-split spectrum pairs；
- max Pearson = 0.947785；
- 无 Pearson ≥ 0.95。

但 shared mineral identity 被允许保留。

所以：

> 这是 few-shot adaptation benchmark，不是 unseen-mineral generalization benchmark。

---

# 16. CNRS-318：为什么要单独做 zero-shot

RRUFF 回答 few-shot。

CNRS 回答另一个问题：

> **完全不使用这个实验来源的标签，冻结模型直接去另一个真实域，会不会仍看到同方向趋势？**

CNRS-318：

- 自然类别不平衡；
- 不做目标域训练；
- 不做 adaptation；
- 不用 CNRS 做 λ / checkpoint / seed 选择。

结果：

```text
seed-level Macro-F1
ERM 0.18837 ± 0.02634
JS  0.20708 ± 0.02134
paired Δ ≈ +0.01871 ± 0.00675
5/5 seeds positive
```

pooled：

```text
Macro-F1: 0.19118 → 0.20912
Balanced Acc: 0.21823 → 0.23878
Accuracy: 0.20000 → 0.21006
ECE: 0.68257 → 0.61242
```

严格 paired-parent 95% CI：

```text
[-0.009339, +0.046107]
```

这个 CI 跨 0，要保留。

而且：

```text
overall accuracy ≈ 0.21
majority-class baseline ≈ 0.274
```

所以 CNRS 的正确说法：

> 有一致的相对改善和概率质量改善，但**绝对性能仍差**；它证明支持性外推趋势，不证明真实域问题已解决。

---

# 17. CNRS sim-to-real representation diagnostic 在看什么

CNRS 有一部分结构可以将：

```text
真实 experimental spectrum
↔ deposited structure
↔ simulated counterpart
```

对应起来。

于是可以问：

> 同一个结构，从模拟谱换成真实谱后，模型内部 representation 和 prediction 会变多少？

这个诊断后来发现很多 seed 上 JS 的 sim→real prediction shift / embedding change 更小。

一个很直观的例子是：

```text
CNRS parent_0207 / pattern_585
true = triclinic
```

某个 seed 下：

- ERM 对 simulated counterpart 很自信地判 triclinic；
- 换成 real spectrum 后被带到 monoclinic；
- JS 从 simulated 到 real 仍保持 triclinic。

这个例子只能做**解释性案例**，总体结论仍必须来自全部 paired structures，而不是靠挑一个好看的 sample。

---

# 18. 评价标准为什么后来改过一次

项目一度把非常严格的 bootstrap CI 当成“项目成败考试”。

后来重新校准成三层证据：

## 第一层：主 performance

社区最常用、最容易解释：

- Macro-F1；
- Accuracy；
- Balanced Accuracy；
- mean ± std；
- multi-seed direction；
- few-shot learning curve；
- per-class F1。

## 第二层：reliability

- ECE；
- NLL；
- Brier。

## 第三层：strict audit

- paired bootstrap；
- class-stratified parent bootstrap；
- 95% CI；
- uncertainty decomposition。

规则是：

> **严格统计审计必须如实保留，但不能把一个 cross-zero CI 单独升级成“所有其他一致证据都作废”。**

同样不能反过来：

> 因为主分数好看就删除不利 CI。

这次修正改变的是**证据层级**，不是原始结果。

---

# 19. Tan Lab Phase-2：这一段绝对不要误用

2026-09-15 已正式：

```text
INVALID / ARCHIVED / NOT EVIDENCE
```

作废内容包括：

- K=4 无监督聚类；
- cluster mean 自动判相；
- 59 条谱上的 JS / ERM embedding cluster-separability；
- PCA / phase verdict / cluster assignment 等衍生结果。

为什么作废：

1. 59 files ≠ 59 independent samples；
2. top / bottom / depolarized / powder / ceramic / 不同体系混在一起；
3. hierarchical clustering 调用本身有方法错误；
4. 自动判相规则过粗；
5. 10–20° 做了不物理的边界外推；
6. 先用 raw spectrum 聚类，再用这些 cluster 评价 embedding，存在循环性；
7. 只有单 seed，没有独立可靠 ground truth。

最重要的科研教训：

> **真实实验室数据不会因为“真实”就自动成为好 benchmark。任务定义、parent identity、可靠标签必须先成立。**

以后任何人看到 `tanlab_phase2/`：

> 只能当失败历史代码，不得当科研证据。

---

# 20. 当前已经冻结的分类主线，绝对不要随便重开

不要做这些事：

- 看完 Test / RRUFF / CNRS 后再调 `lambda_js`；
- 为了让结果更漂亮重选 seed；
- 恢复 Residual/V10 到当前论文主线；
- 再换 Transformer 然后把整个公平对照推倒；
- 往当前主实验再塞新 loss；
- 修改 frozen split；
- 把真实域拿来反向挑 checkpoint；
- 把 same-class single-seed 结果包装成最终确认性结论；
- 把 CNRS 的低绝对性能隐藏掉；
- 把 Tan Lab Phase-2 结果放回 PPT；
- 把 archive 里的旧 V8/V9 计划误认为当前执行合同。

当前 classification project 的研究结果已经结案。

现在更重要的是：

> 论文、图表、方法 framing、物理解释、申请叙事和成果封装。

---

# 21. 当前论文真正的 contribution 是什么

不要说：

> “我们发明了 JS divergence。”

错。

不要说：

> “第一次有人做 XRD consistency。”

仓库证据不足以支持 world-first。

不要说：

> “我们发明了 online PXRD simulation。”

也错，前人早就做过。

最准确的贡献 framing：

> **已有 online PXRD simulator 主要作为 data generator；本项目进一步利用 simulator-retained parent identity，把来自同一母结构的不同 measurement realizations 定义为 measurement-equivalent views，并将这种 provenance relationship 转化为 consistency supervision。**

压缩成：

```text
parent provenance
→ measurement equivalence
→ relationship supervision
```

一句最容易讲给别人听的话：

> **前人让模拟器不断“造更多数据”；我们进一步利用模拟器知道“哪些数据其实来自同一个物理对象”这件事。**

---

# 22. 这个项目现在最干净的三条科学结论

## 结论 1：总体鲁棒性提高

> same-parent consistency 在模拟 OOD 上稳定改善七晶系分类，5/5 matched seeds 正向。

## 结论 2：真实域标签效率更高

> 在 RRUFF 上，相同 1/2/5-shot 标签预算下，JS-pretrained 模型均比 ERM-pretrained 更好。

## 结论 3：收益有 XRD 物理结构

> broadening / texture 等与具体母结构衍射模式耦合更强的扰动，正式 ERM→JS 增益最大。

这三条分别回答：

1. 有效吗？
2. 实际有什么用？
3. 为什么特别适合 PXRD？

---

# 23. 当前项目不能声称什么

这是新成员最容易踩雷的地方。

**不能声称：**

- 已经解决真实 PXRD classification；
- CNRS 上性能已经足够部署；
- JS 是全新算法；
- 当前工作是因果推断；
- same-parent 已经被多 seed 证明普遍优于 same-class；
- 所有七个晶系都改善；
- current split 是 formula/prototype/family disjoint；
- Residual 已成功完成结构-测量解耦；
- Tan Lab Phase-2 是第三真实域证据；
- quantitative inversion 已经成功；
- 当前模型已经自动 Rietveld refinement。

---

# 24. 定量反演下一步到底是什么，什么又不是

## 24.1 为什么想继续做参数反演

分类只能告诉你：

```text
“它大概属于哪个晶系”
```

更接近表征实际用途的问题是：

```text
“晶格参数是多少？”
“峰位偏移是结构变化还是仪器误差？”
“峰宽是多少？”
“能不能给 refinement 一个更好的初始化？”
```

所以 2026-09-19 用户本人提出的下一步是：

> 把“物理关系监督”从离散标签扩展到连续结构 / 测量参数，并与 forward physics 和 refinement 接上。

## 24.2 当前 `xrd_inversion/` 已经有什么

现有 numerical infrastructure 包括：

- tetragonal parent / cell audit；
- forward renderer；
- CUDA float64 数值路径；
- Jacobian / identifiability；
- multistart parameter recoverability；
- nominal-start local capture；
- independent renderer holdout；
- split / prototype audit。

formal numerical Gate 中，clean P2-R 288/288 可恢复；P2-L 181/288，只作为 nominal basin diagnostic。

## 24.3 什么已经 NO-GO

Stage-1：

```text
structure–measurement factorization v1
```

已经 preregistered **NO-GO**，并归档。

不要从 main 直接恢复旧 implementation。

如果未来重新做：

> 必须是新版本、新研究问题、新 Gate。

## 24.4 未来可重新设计的最小问题

一个比较合理的下一代 V0 思路是限定：

- known phase；
- single phase；
- tetragonal；
- 少数结构参数；
- 少数 measurement parameters。

例如：

```text
structure:
a, c 或 scale + tetragonal distortion

measurement:
delta_2theta
FWHM
```

再比较：

1. 普通参数回归；
2. reference-conditioned regression；
3. same-structure parameter consistency；
4. forward spectral consistency；
5. ML initialization + identical local refinement。

但这只是**下一代规划**，不是当前已完成 claim。

---

# 25. 如果你今天第一次打开仓库，按这个顺序读

## 第 1 层：10–20 分钟看懂“现在是什么”

1. `docs/CUIFA01_START_HERE.md` —— 就是本文；
2. `docs/CURRENT_STATE.md` —— 当前正式状态；
3. `xrd_robustness/reports/RESULTS.md` —— 结果；
4. `docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md` —— 最常被追问的方法细节。

## 第 2 层：想知道“为什么这样设计”

5. `docs/PXRD_NOVELTY_LITERATURE_LINEAGE.md`
6. `docs/PXRD_PERTURBATION_EVIDENCE.md`
7. `docs/PXRD_RESULT_REPORTING_STANDARD.md`

## 第 3 层：想知道“项目为什么改这么多次”

8. `docs/PROJECT_HISTORY.md`
9. `docs/PROJECT_HISTORY_NOTE_2026-09-13_XRD_INTERPRETATION_CLOSURE.md`
10. `docs/PROJECT_HISTORY_NOTE_2026-09-14_STRUCTURE_COUPLED_PERTURBATION_INSIGHT.md`
11. `docs/PROJECT_HISTORY_NOTE_2026-09-15_TANLAB_PHASE2_INVALIDATION.md`
12. `docs/PROJECT_HISTORY_NOTE_2026-09-19_SENIOR_DISCUSSION_XRD_NEXT_STEP.md`

## 第 4 层：要碰下一代反演

13. `xrd_inversion/README.md`
14. `docs/NEXT_PROJECT_XRD_QUANTITATIVE_INVERSION.md`
15. 对应 archive NO-GO 记录。

---

# 26. 仓库代码地图

主项目：

```text
xrd_robustness/
├── configs/
│   ├── experiment.public.json
│   ├── data.method_transfer.structure_split.json
│   └── simulation.method_transfer.frozen.json
├── src/xrd_robustness/
│   ├── models/
│   │   └── ml4pxrd_resnet1d.py
│   ├── training/
│   │   ├── objectives.py
│   │   └── runner.py
│   ├── simulator.py
│   └── online_views.py
├── scripts/
│   ├── run_simulated_test.py
│   ├── run_cnrs318_zero_shot.py
│   └── ...
├── reports/
│   ├── RESULTS.md
│   ├── simulated_test_results.json
│   ├── rruff301_fewshot_results.json
│   ├── CNRS_318_RESULTS.md
│   └── CALIBRATION_ANALYSIS.md
└── MANUSCRIPT.md
```

最重要的阅读关系：

```text
simulation config
    ↓
simulator.py
    ↓
online_views.py
    ↓
runner.py
    ↓
objectives.py
    ↓
ResNet
    ↓
reports/
```

---

# 27. clone 后为什么你看不到所有数据和模型权重

这是正常的。

公开 Git 仓库主要保存：

- 代码；
- configs；
- manifests / hashes；
- machine-readable results；
- 报告；
- 审计证据。

不会把所有东西都塞 Git：

- 大型模型 checkpoint；
- 本地虚拟环境；
- 大型原始数据；
- 受许可限制的 RRUFF raw assets；
- 本地文献包；
- 部分生成中间文件。

所以：

> `git clone` 后能读懂并审计当前方法与结果，不代表可以在没有外部数据资产的情况下“一键从头重训整个论文”。

不要为了“补齐仓库”擅自把受许可或几 GB 的本地文件 push 上去。

---

# 28. 新成员第一次操作仓库

## Clone / 更新

```bash
git clone https://github.com/Frysland-2024/AI4science.git
cd AI4science
git pull
```

## 快速读状态

```text
README.md
docs/CUIFA01_START_HERE.md
docs/CURRENT_STATE.md
xrd_robustness/reports/RESULTS.md
```

## 跑代码级回归测试

```bash
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q
```

这里的 pytest 主要检查：

- 接口；
- 配置；
- 实现；
- 公开结果文件契约。

它**不会**重新训练论文全部模型。

---

# 29. 如果你要修改东西，先判断属于哪一类

## A. 论文 / PPT / figure / wording

通常安全。

但结果数字必须从当前 tracked reports 读取，不能凭聊天记忆手填。

## B. 分析已有 frozen outputs

可以。

前提：

- 不改变原始结果；
- 明确 exploratory / post-hoc / confirmatory 的层级；
- 不用后验分析反向重调模型。

## C. 修改主训练代码 / lambda / split / simulator

这不是普通“修代码”。

这等于重新打开已结案主实验。

**没有新协议，不要做。**

## D. 下一代 quantitative inversion

可以独立开新版本。

但是：

- 不能把旧 factorization-v1 当可继续项目；
- 先定义任务；
- 先做 identifiability / data Gate；
- 再训练模型。

## E. Tan Lab 历史真实谱

原始数据未来可能还有价值。

但当前 Phase-2 实验设计无效。

如果重开：

1. 先建立 parent sample；
2. 先有可靠 phase / structure ground truth；
3. 再定义科学任务；
4. 最后才碰模型。

---

# 30. 给 cuifa01 的“60 秒讲项目”版本

你可以直接这样说：

> 我们研究的是模拟 PXRD 模型在测量条件变化下不稳定的问题。过去在线模拟主要用来不断生成不同扰动谱；但模拟器其实还知道哪些谱来自同一个母晶体。我们把这个 parent provenance 看作 measurement-equivalence supervision：同一个结构在不同峰移、展宽、择优取向、背景和噪声下虽然谱形不同，但晶系判断应该稳定。于是我们让 ERM 和 JS 看完全相同的两张动态扰动谱，唯一让 JS 多用一个“这两张谱来自同一 parent”的一致性约束。五个 matched seeds 上，JS 在模拟 OOD Test 的 Macro-F1 平均提高约 5.46 个百分点；在 RRUFF 的 1/2/5-shot 真实域适配中也都更好，在 CNRS 独立 zero-shot 域上 5/5 seeds 同方向改善，但绝对真实域性能仍然较低。现在分类主线已经冻结，下一步想把“物理关系监督”继续推进到限定领域的定量参数反演和表征流程。

---

# 31. 给 cuifa01 的“5 分钟答辩”框架

按这 7 句话走：

1. **Problem**：模拟 PXRD 和实验 PXRD 存在 measurement-domain shift。
2. **Prior paradigm**：在线物理扰动可以扩大训练分布，但通常把每张生成谱当独立有标签样本。
3. **Observation**：模拟器保留 parent provenance，知道两张谱其实是同一物理对象的不同观测。
4. **Method**：两张同源 view 用同样 CE；JS 分支额外最小化两份晶系预测的 JS divergence。
5. **Fairness**：ERM 和 JS 看一样的数据、扰动、ResNet、optimizer、预算和 seeds。
6. **Evidence**：sim OOD +5.46 pp；RRUFF 1/2/5-shot 全部更好；CNRS zero-shot 5/5 seeds 正向但绝对性能仍弱。
7. **Interpretation**：broadening / texture 增益最大，提示同源关系在 structure-coupled nuisance 下尤其有用。

---

# 32. 最后给下一次 AI / 新协作者的读取协议

如果你要把仓库交给另一个 AI，请先贴这段：

```text
你正在阅读 Frysland-2024/AI4science。

先按顺序读：
1. docs/CUIFA01_START_HERE.md
2. docs/CURRENT_STATE.md
3. xrd_robustness/reports/RESULTS.md
4. docs/PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md

规则：
- CURRENT_STATE / RESULTS / frozen configs 优先级高于历史文档。
- archive 只能解释历史，不能推断 current state。
- 当前 classification 主线是 Dynamic ERM vs Dynamic JS (lambda_js=60), ResNet-18-GN。
- Residual/V10 已归档，不是当前主线。
- Tan Lab Phase-2 是 INVALID / NOT EVIDENCE。
- CNRS 是 zero-shot external domain；RRUFF-301 是 K=1/2/5 few-shot adaptation。
- xrd_inversion 的 factorization-v1 已 NO-GO；未来定量反演需要新协议。
- 回答项目问题前先读取 GitHub 当前 main，不要只依赖聊天记忆。
```

---

# 33. 一句话记住整个项目的“精神”

如果你最后只记一句：

> **这个项目真正的变化，不是从一个网络换成另一个网络，而是从“让模拟器造更多数据”走到“利用模拟器知道数据之间是什么关系”，再进一步追问这些关系如何帮助科学测量模型学得更稳、更省真实标签。**

这就是从 FerroAI 到当前 PXRD 项目最重要的发展线。
