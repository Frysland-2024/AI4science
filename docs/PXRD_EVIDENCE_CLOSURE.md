# PXRD 证据问题结案与方法新颖性 framing

**状态日期：** 2026-08-29  
**用途：** 汇总本轮三个问题的最终处理状态，防止后续再次把已经完成的证据工作误判为新的科研 TODO，同时固定当前最重要的方法叙事。

## 一页结论

| 问题 | 当前状态 | 结论 |
|---|---|---|
| 1. 五类扰动的物理/文献依据是否充分 | **CLOSED / 已结案** | 早期已经完成系统文献与代码核验；当前只需在 Methods、PPT、答辩中调用现有证据，不再重新做“扰动真实性调查” |
| 2. RRUFF-301 adaptation/test 是否存在样本或近重复谱泄漏 | **CLOSED / 已结案** | RRUFF ID overlap = 0，spectrum SHA overlap = 0，16,170 个跨 split 谱图对中无 Pearson ≥ 0.95；重复 mineral identity 符合 in-domain few-shot benchmark 的任务定义 |
| 3. 项目真正的新颖性如何表达 | **ACTIVE WRITING / 当前最重要** | 不补实验、不加算法；核心是把 online simulator 从单纯 data generator 重新解释并利用为 **data generator + relationship supervisor** |

> 本轮前两个证据问题已经结案。当前真正需要认真打磨的是第三项：**measurement-equivalence supervision 的 scientific framing 和核心方法图。**

---

## 1. 五类扰动物理/文献依据：CLOSED

### 1.1 结论

峰位偏移、峰展宽、择优取向、背景和噪声并非凭感觉设置。V6–V9 阶段已经完成了文献、物理机制、开源实现和参数数量级的系统核验；当前主线还保留了冻结的最终扰动配置。

因此：

- 不再把“五类扰动是否有依据”列为新的科研任务；
- 不需要重新从 RRUFF/CNRS 拟合一套仪器误差分布，除非未来论文主张改变为“特定仪器经验校准模拟器”；
- 当前写作只需说明物理来源、参数范围和边界，不把工程范围包装为某一仪器的真实发生概率。

### 1.2 权威证据入口

- [`PXRD_PERTURBATION_EVIDENCE.md`](PXRD_PERTURBATION_EVIDENCE.md)：当前显式的五类扰动证据索引；
- [`../xrd_robustness/configs/simulation.method_transfer.frozen.json`](../xrd_robustness/configs/simulation.method_transfer.frozen.json)：当前最终冻结配置；
- 历史详细 evidence table 与参数映射仍可由 `PXRD_PERTURBATION_EVIDENCE.md` 追溯。

### 1.3 当前可直接使用的写作口径

> The five perturbation families represent common PXRD measurement and sample variations—global peak-position offset, effective peak broadening, preferred orientation, smooth background, and counting/readout noise. Their mechanisms and numerical scales were anchored to prior PXRD literature and existing simulation implementations before the final perturbation ranges were frozen. The ranges define a physically motivated evaluation space rather than an empirical error distribution calibrated to one specific instrument.

### 1.4 状态

**CLOSED.** 后续只做引用、整理和展示，不重新开题。

---

## 2. RRUFF-301 组成与 split 检查：CLOSED

### 2.1 审计问题

只使用本地已经构建的 RRUFF 数据库，检查：

- adaptation pool（70）与 locked test（231）是否共享 RRUFF ID；
- 是否存在完全相同的规范化谱图；
- mineral name、chemistry、space group 有多少组成重合；
- 70 × 231 = 16,170 个跨 split 谱图对中是否存在高度近重复谱。

该检查是**只读描述性 composition audit**，不是新的实验 Gate；不读取模型预测、不删样本、不改 split、不重跑模型。

### 2.2 结果

权威报告：

- [`../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`](../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md)
- [`../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.json`](../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.json)

核心结果：

| 检查项 | 结果 |
|---|---:|
| adaptation pool | 70 |
| locked test | 231 |
| unique RRUFF IDs | 301 |
| exact RRUFF-ID overlap | **0** |
| exact spectrum-SHA overlap | **0** |
| cross-split spectrum pairs | 16,170 |
| maximum Pearson correlation | **0.947785** |
| Pearson ≥ 0.95 | **0 pairs** |
| Pearson ≥ 0.98 | **0 pairs** |
| Pearson ≥ 0.995 | **0 pairs** |
| shared mineral names | 23 |

因此可以明确排除两种最直接的数据泄漏：

1. adaptation/test 使用同一个 RRUFF 样本；
2. adaptation/test 存在几乎复制的规范化谱图。

### 2.3 为什么有相同 mineral name 仍然合理

23 个 mineral names 同时出现在 adaptation 和 locked test。这个事实需要保留，而不是删除。

RRUFF-301 当前回答的是：

> **在同一个实验 PXRD domain 内，给定很少真实标签时，哪种模拟预训练 representation 更容易适应真实域？**

它不是：

> unseen-mineral / chemistry-disjoint / prototype-disjoint generalization benchmark。

因此，相同 mineral identity 出现在 support pool 和 test 中并不违反当前任务定义。每条记录仍然是不同 RRUFF ID、不同实测谱；而且跨 split 最大 Pearson 也只有 0.947785。

只有未来把 claim 改成“对从未见过的矿物/化学体系进行泛化”时，才需要重新构造 mineral-disjoint、chemistry-disjoint 或 structure-family-disjoint split。当前项目不做这种 claim。

### 2.4 当前可直接使用的写作口径

> The 70-sample adaptation pool and the 231-sample locked test set share no RRUFF IDs or identical stored spectra. Across all 16,170 cross-split spectrum pairs, the maximum Pearson correlation is 0.948 and no pair exceeds 0.95. Repeated mineral identities are retained because RRUFF-301 is used to evaluate in-domain few-shot adaptation and label efficiency rather than unseen-mineral generalization.

### 2.5 状态

**CLOSED.** 不据此修改 frozen split，不删样本，不重跑实验。

---

## 3. 新颖性 framing：当前最重要的未结案写作任务

这项需要认真做，但要把边界说清楚：

> **不是补实验，也不是加算法。**

项目的贡献不是“发明 JS divergence”，也不是“第一次把 consistency regularization 用到 XRD”。JS 是实现 measurement-equivalence supervision 的一个具体、简单且可控的训练目标。

### 3.1 Manuscript 已经出现的正确核心句

当前 manuscript 已经写出两个关键判断：

> multiple perturbed patterns generated from one parent structure are related measurements of the same latent physical object

以及：

> shared parent identity defines measurement equivalence and supplies the relationship used by the consistency objective.

这两句话应该成为全文、PPT 和申请叙事的共同核心，而不是被埋在 Methods 里。

### 3.2 不应该怎么讲

不要把贡献压缩成：

> “我们把 JS consistency 用到了 XRD。”

这种说法会把项目降格成普通算法迁移，而且无法解释为什么在线 PXRD simulator 在这里具有科学结构。

也不要声称：

- JS divergence 本身是新算法；
- consistency regularization 本身由本项目首次提出；
- simulator 生成扰动谱本身是本项目首创。

### 3.3 应该怎么讲

传统 online PXRD simulation 的主要角色通常是：

```text
crystal structure
      ↓
simulator
      ↓
more / more diverse training spectra
```

也就是：

> **simulator = data generator**

本项目进一步利用 simulator 本来就知道、但普通 ERM 没有显式利用的信息：**哪些不同扰动谱来自同一个 parent structure。**

对于同一个母体结构 `s`：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

`x1` 和 `x2` 可以因为峰移、展宽、择优取向、背景和噪声而明显不同，但二者仍然是同一个 latent physical object 的不同测量 realization。

因此 parent identity 定义了一个 measurement-equivalence relation：

```text
x1 ~ x2  because parent(x1) = parent(x2)
```

Dynamic ERM 只使用：

```text
x1 → y
x2 → y
```

而当前方法进一步使用：

```text
(x1, x2) 来自同一 parent
        ↓
measurement equivalence
        ↓
prediction consistency supervision
```

于是 simulator 的角色变成：

> **simulator = data generator + relationship supervisor**

或者更凝练：

> **from data generation to relationship supervision**

这才是项目最应该强调的方法贡献。

### 3.4 为什么这个 framing 比“JS on XRD”更准确

因为真正额外进入学习目标的，不只是更多谱图，而是**样本之间的关系**。

普通 Dynamic ERM 已经看到了同样数量、同样扰动分布的 online views；JS 方法的额外信息来自：

> 这两个不同观测属于同一个母体，因此任务输出应保持一致。

matched design 控制了 backbone、parent structures、perturbation distribution、optimization 和 data exposure，因此 ERM vs JS 的差异可以被解释为：

> **显式使用 simulator-retained measurement relationship 是否有价值。**

这也解释了为什么项目标题采用 **Measurement-Equivalence Supervision for Robust PXRD Classification**，而不是 “JS Consistency for XRD Classification”。

### 3.5 PPT 核心方法图必须怎么画

这张图应该成为 PPT 最核心的方法图之一，视觉上直接呈现角色升级：

```text
                    同一 latent physical object
                    Parent crystal structure s
                              │
                 ┌────────────┴────────────┐
                 │                         │
        measurement state m1      measurement state m2
                 │                         │
              simulator                 simulator
                 │                         │
                x1                        x2
         shifted / broadened /     different background /
          textured / noisy              noise / etc.
                 │                         │
                 └──────────┬──────────────┘
                            │
              shared parent identity
                            │
              measurement equivalence
                            │
              relationship supervision
                            │
          CE(y,x1)+CE(y,x2)+λ JS(p1,p2)
```

图旁边再放一个非常简单的对照：

```text
Conventional online simulation
simulator → data generator

This work
simulator → data generator + relationship supervisor
```

图里不要把“JS”画成最大的创新模块。最大的视觉重点应该是：

> **shared parent identity → measurement equivalence → supervision**

JS 只是最右/最下游的 objective realization。

### 3.6 对外一句话版本

**中文：**

> 传统在线 PXRD 模拟主要利用模拟器生成更多训练谱；本项目进一步利用模拟器保留的母体结构身份，把同一晶体在不同测量条件下的多种观测定义为 measurement-equivalent views，并将这种观测关系直接用于一致性监督。

**英文：**

> Previous online PXRD simulation primarily uses the simulator as a scalable data generator. We additionally exploit simulator-retained parent identity to define measurement-equivalent views of the same latent crystal and use this relation as supervision during training.

### 3.7 状态

**ACTIVE WRITING / FIGURE WORK.**

需要继续做的是：

- 把这套 framing 写进 Introduction、Methods、Discussion；
- 把 `shared parent identity → measurement equivalence → relationship supervision` 做成 PPT/论文的核心方法图；
- 让标题、摘要、图、结果解释和申请叙事使用同一套语言。

**不需要：**新算法、新 loss、新训练、新数据域或重新调参。

---

## 4. 本轮最终决策

截至 2026-08-29：

1. **五类扰动物理/文献依据：结案。**
2. **RRUFF-301 组成与近重复检查：结案。**
3. **measurement-equivalence / relationship-supervision framing：当前最高优先级的写作与图示任务。**

除非未来 scientific claim 明显改变，否则前两项不再重新开启。
