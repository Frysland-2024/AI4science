# PXRD 方法细节证据考古与结案

**状态日期：** 2026-08-29  
**用途：** 把当前方法叙事最容易被追问的五个细节问题，从当前代码、当前配置和 Git 历史中重新整理出来。这里做的是**证据整理与说法定界**，不是新增实验、重新调参或重开模型选择。

## 一页结论

| 问题 | 状态 | 最终结论 |
|---|---|---|
| 1. Related Work / 新颖性边界 | **CLOSED** | 本地证据足以支持“online simulation、consistency 本身都有前例；本项目贡献是利用 simulator-retained parent identity 做 measurement-equivalence / relationship supervision”的当前说法；**不做 world-first 声明** |
| 2. Dynamic ERM 与 Dynamic JS 是否是在真正相同的训练条件下比较 | **CLOSED** | 两者共享母体结构、在线双视图生成器、扰动分布、骨干网络、优化设置、训练预算和配对 seed；classification loss 完全相同，JS 唯一新增的是同一母体两份预测之间的 consistency term |
| 3. formal_14060 数据集如何构建、如何避免 parent leakage | **CLOSED** | 14,060 个 Materials Project 结构来自已审计结构层的确定性合并；当前最终划分以 `structure_fingerprint` 为 parent identity，按晶系分层做 70/15/15，得到 9,842 / 2,109 / 2,109，并在生成任何扰动谱之前完成 parent-level split |
| 4. 五类扰动是否只改变观测谱，而没有把 structure A 变成 structure B | **CLOSED** | 是。代码先由固定 parent structure 计算 ideal peak table，后续扰动只作用于峰位坐标、峰宽、相对峰强、背景和噪声；不重写母体原子结构、晶格或 crystal-system label。因此 structure A 经扰动后仍是 structure A 的另一种测量 realization |
| 5. `lambda_js=60` 是怎么选出来的 | **CLOSED** | 先用 Train-only 梯度尺度把候选固定为 `[3,30,60]`，再仅用 Validation 按预先定义的 OOD + in-range 规则选择 60；选择时没有使用 simulated Test、RRUFF 或 CNRS，之后不再 retune |

> 五项都已经有本地证据，可以结案。当前剩下的是把这些已结案事实写进 Methods、Related Work、PPT 和申请叙事，而不是再补实验。

---

## 1. Related Work / 新颖性边界：CLOSED

### 1.1 真正需要回答的问题

这里不是要证明“别人什么都没做过”，而是要把**哪些东西是前人的成熟做法，哪些东西才是本项目自己的方法组织方式**讲清楚。

本地历史材料已经能确认三件事：

1. PXRD / materials-ML 中，利用模拟器生成训练谱、加入峰移、展宽、背景、噪声等变化有大量先例；
2. “同一对象的不同合理视图应保持预测一致”这一 consistency 思想也有前例，例如项目早期专门审读过 KBSS；
3. 当前项目没有把这些已有组件包装成新算法，而是把 simulator 已经保留的 **parent identity** 进一步解释并使用为一条样本关系：`same parent -> measurement equivalence -> consistency supervision`。

### 1.2 本地证据

历史参数证据表记录了 Szymanski、SimXRD-4M、Lee、Schopmans、CPICANN 等工作如何用模拟/扰动谱进行训练或实验域适应，说明“simulation / augmentation as data generation”并不是本项目首创：

- 历史文件：`xrd_robustness/reports/literature_parameter_raw.csv`
- 历史 commit：`f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217`

KBSS 思想吸收笔记则明确记录：KBSS 提供的是“同一对象不同视图保持稳定”的高层 consistency 思想；当前 XRD 项目不移植其代码、任务、伪标签阈值或具体训练流程，而是把这个原则重新落到有物理依据的 PXRD measurement views 上：

- 历史文件：`00_project_context/KBSS_PROJECT_RELEVANCE.md`
- 历史 commit：`f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217`

项目申请叙事历史稿也已经把方法转折记录为：最初是“generate more realistic synthetic data and train a model”，后来转向“what additional supervision is hidden in the scientific data-generation process”；并明确写出 Dynamic ERM 与 Dynamic JS 看同样的两份 view，区别在于 JS 使用 simulator provenance：

- 历史文件：`00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`

### 1.3 当前允许的 claim

可以说：

> 传统 online PXRD simulation 主要把 simulator 用作数据生成器；本项目进一步利用 simulator-retained parent identity，把同一母体结构的不同测量 realization 定义为 measurement-equivalent views，并把这条关系用于训练监督。

不要说：

- “我们发明了 consistency regularization”；
- “我们发明了 JS divergence”；
- “我们第一次用模拟器生成扰动 PXRD”；
- “这是世界上第一个使用 parent identity 的工作”。

本地仓库足以**关闭当前 contribution boundary**，但它不是一份穷尽全领域的系统综述，因此不支持 world-first 口号。当前 manuscript 本来就不需要这种口号。

### 1.4 状态

**CLOSED.** Related Work 后续只需把已有前例与当前 contribution boundary 写清楚。

---

## 2. Dynamic ERM 与 Dynamic JS 是否是在真正相同的条件下比较：CLOSED

### 2.1 问题要怎样讲清楚

当我们说“JS 的提升来自 relationship supervision”时，首先要排除一种很普通的混淆：**会不会其实是 JS 那组看了更多数据、用了更强的扰动、换了模型或训练预算，所以分数才更高？**

因此这个问题真正要核实的是：

> **Dynamic ERM 和 Dynamic JS 是否使用同一批母体结构、同一套在线双视图生成方式、同一扰动分布、同样的骨干网络、优化器、训练预算和配对随机种子；并且在这些条件都相同的情况下，JS 唯一多出来的东西是否只是“这两张谱来自同一母体，因此两份预测应保持一致”的关系约束。**

如果这一点成立，那么两组实验的性能差异才可以主要解释为：**显式利用 same-parent relationship 是否有价值。**

### 2.2 当前代码给出的直接答案

当前 `online_views.py` 中，`make_pair` / `make_pair_from_peaks` 从**同一个 structure / material_id**生成 view 1 和 view 2；训练 runner 无论 ERM 还是 JS，都先通过同一个 `render_pair_batch` 得到 `x1, x2, target`，然后才进入训练 objective。

当前 `training/objectives.py` 更直接：

Dynamic ERM：

```text
classification = 0.5 * [CE(x1,y) + CE(x2,y)]
total = classification
```

Dynamic JS：

```text
classification = 0.5 * [CE(x1,y) + CE(x2,y)]
consistency = JS(p1,p2)
total = classification + lambda_js * consistency
```

因此两种方法的 classification 部分完全相同；JS 唯一多出来的是同一 pair 上的 prediction-consistency term。

### 2.3 配置与历史记录也支持同条件比较

当前 `configs/experiment.public.json` 固定：

- 相同 ResNet-18-GN；
- 相同五个 training seeds；
- 每个 seed 都有一组 ERM / JS 配对 run；
- 同一 data config 与 simulation config。

V9 历史的 four-run 方案则更早就把 scientific question 写成：在 frozen ResNet backbone 与 **identical dynamic exposure** 下比较 Dynamic ERM 和 JS，并固定相同 preprocessing、AdamW、learning rate、weight decay、batch size 与训练预算。

历史 manuscript skeleton 也明确要求 matched-budget protocol 报告 identical mother structures、accepted parameter pairs、pair schedule、forward-view exposure、backbone 和 optimizer-step count。

### 2.4 最终判断

因此当前可以合理地把 ERM vs JS 的核心差异解释为：

> **两组看到的是同样的数据与同样的测量扰动；JS 额外利用了 simulator 已知的 same-parent relationship。**

这不是因为 JS 看了更多谱，也不是因为 JS 使用了更强的 augmentation。

### 2.5 状态

**CLOSED.** 后续只需要在论文/PPT 做一张 matched-design 表，不需要重跑实验。

---

## 3. formal_14060 数据集构建与 parent-level split：CLOSED

### 3.1 14,060 是怎么来的

历史 `build_formal_14060.py` 记录：formal_14060 是由两个已经存在并审计过的 Materials Project 结构层确定性合并得到：

- formal tier：14,000 条；
- gate tier：140 条；
- 两者重合：80 条；
- 新增唯一结构：60 条；
- 合并后：14,060 条。

历史 retrieval manifest 的来源描述是：

> deterministic union of existing audited Materials Project tiers

并记录了 `max_energy_above_hull = 0.1` 的来源筛选条件。

### 3.2 当前真正生效的 split 不是旧的历史 split

早期 `build_formal_14060.py` 曾带有旧的 `9800 / 2130 / 2130` 划分。这个数字已经被后来的 parent-structure split **取代**，不能再用于当前论文。

当前权威配置是：

- Train：9,842；
- Validation：2,109；
- Test：2,109；
- 比例：70% / 15% / 15%；
- seed：20260726；
- stratification：`crystal_system`；
- split unit：`parent_structure`；
- parent identity：`structure_fingerprint`。

### 3.3 为什么不会出现“同一个 parent 的不同谱跨 split”

当前 `build_structure_split.py` 的顺序是：

```text
14,060 parent structures
        ↓
先按 structure_fingerprint 分 Train / Validation / Test
        ↓
每个 parent 的所有 clean / in-range / OOD / online views
继承 parent 所属 split
```

脚本还显式检查：

- duplicate material ID = 0；
- Train / Validation / Test 的 material ID intersections = 0；
- Train / Validation / Test 的 parent-structure ID intersections = 0；
- `split_before_view_generation = True`；
- `all_generated_views_inherit_parent_structure_split = True`。

因此当前的防泄漏单位不是“谱图文件”，而是更上游的**母体结构**。

### 3.4 claim 边界

当前 split 可以称为：

> **exact-parent-disjoint / parent-structure-disjoint**

不要称为：

- formula-disjoint；
- prototype-disjoint；
- chemistry-disjoint；
- structure-family-disjoint。

当前 assignment 明确没有使用 family fields。

### 3.5 状态

**CLOSED.** 当前数据来源、14,060 的形成过程和 parent-level split 都已有足够本地证据。

---

## 4. 五类扰动是否只改变观测谱，而没有把 structure A 变成 structure B：CLOSED

### 4.1 问题要怎样讲清楚

这是 measurement-equivalence 能不能成立的物理前提。

我们真正要确认的是：

> **从一个固定的母体晶体结构 A 出发，施加峰位偏移、峰展宽、择优取向、背景和噪声以后，得到的是否仍然只是“structure A 在另一种测量/样品条件下的 PXRD 观测”；还是说模拟器实际上修改了晶格或原子坐标，把 structure A 变成了另一个 structure B。**

只有前一种情况成立，同一 parent 的两张谱才天然共享同一个七晶系标签。

也就是说，我们要验证的是：

```text
structure A
    ↓ diffraction
ideal PXRD of A
    ↓ measurement/sample perturbation
perturbed PXRD of A
```

而不是：

```text
structure A
    ↓ structural modification
structure B
    ↓ diffraction
PXRD of B
```

### 4.2 当前 simulator 的实际执行顺序

当前 `simulator.py` 先调用 `ideal_peak_table(structure, grid)`，由**传入的固定 structure** 计算理想 Bragg peak table，包括 peak positions、intensities、hkl、multiplicity 与 reciprocal-vector metadata。

随后 `simulate_from_peak_table(...)` 接收的是已经生成好的 peak table / peak arrays，并在观测层进行扰动：

- **peak shift**：对全部 `2θ` positions 加一个统一 `delta_2theta_deg`；代码明确把它解释为 instrument zero offset；
- **broadening**：使用 `fwhm_deg` 把同一组 peak positions / intensities 渲染成不同峰宽；
- **preferred orientation**：在 reflection table 上改变相对反射强度；
- **background**：向已经生成的 diffraction signal 叠加平滑背景；
- **noise**：向 signal 加入 Gaussian / Poisson-count / electronic readout noise。

在这些步骤里，没有把新的 atomic coordinates、lattice parameters 或新的 `structure` 对象写回 simulator，也没有重新计算一个不同结构的 crystal-system label。

因此代码层面实际是：

```text
s = fixed parent structure
P(s) = ideal peak table of s
x1 = T_m1(P(s))
x2 = T_m2(P(s))
```

而不是：

```text
s1 = A
s2 = structural_transform(A) = B
x1 = diffraction(A)
x2 = diffraction(B)
```

### 4.3 pair generator 也保持同一个 parent

当前 `online_views.py` 对一个 parent 生成 pair 时：

- 两个 view 使用同一个 `structure` 或同一个 cached `PeakTable`；
- 使用同一个 `material_id`；
- 只是 `view_id=1/2` 和对应 sampled measurement state 不同。

所以可以写成：

```text
x1 = g(s, m1)
x2 = g(s, m2)
```

其中 `s` 始终是同一个 parent，变化的是 measurement/sample state `m`。

### 4.4 这和“谱图完全一样”不是一回事

结论不是：

```text
x1 == x2
```

而是：

```text
parent(x1) = parent(x2) = s
crystal_system(x1) = crystal_system(x2) = h(s)
```

因此，**structure A 仍然是 structure A，但它的观测谱可以因为测量和样品状态而显著变化。**

这就是当前项目里 measurement equivalence 的准确含义：

> **structure-preserving / label-preserving measurement variation**，而不是 signal identity。

### 4.5 为什么用 prediction-level consistency，而不是强迫内部特征完全相同

峰移、展宽、texture、background 等确实会带来真实的测量差异；内部 representation 可以保留这些差异。当前任务真正需要稳定的是**关于晶系类别的判断**。

所以更准确的约束是：

> 两张谱可以不同，但既然它们仍然来自同一个 structure A，模型对 crystal-system 的 task-level belief 不应因为 measurement state 改变而任意漂移。

这与项目后来放弃强残差解耦、保留 prediction-level JS 的方法收缩也是一致的。

### 4.6 claim 边界

可以说：

> measurement-equivalent views of the same latent crystal for the seven-crystal-system classification task

不要把它扩张成：

- 两个 PXRD 信号在所有物理意义上等价；
- 所有 measurement perturbations 都对所有下游任务保持不变；
- 模型内部 feature 必须完全 invariant。

### 4.7 状态

**CLOSED.** 当前代码已经直接证明五类 perturbation 在实现上是对固定 parent diffraction representation 的观测层变换，而不是把 structure A 变成 structure B；不需要新增实验来验证这一点。

---

## 5. `lambda_js = 60` 的选择历史：CLOSED

### 5.1 第一阶段：只确定合理候选尺度，不看 Validation/Test/真实域

历史 `v9_resnet_js_only_scale_gate` 在 Train-only 条件下检查了 `[3,30,60]` 三个 JS 权重的梯度尺度：

| lambda | median auxiliary/classification gradient ratio | 当时记录的尺度解释 |
|---:|---:|---|
| 3 | 0.087859 | weak |
| 30 | 0.877058 | material non-dominant |
| 60 | 1.754115 | dominant |

这一步没有训练候选模型，也没有访问 Validation、simulated Test 或 real XRD；作用只是把候选范围固定为 `[3,30,60]`。

### 5.2 第二阶段：Validation 选择 60

之后的 four-run comparison 固定同一个 ResNet 训练合同，比较：

- Dynamic ERM；
- JS λ=3；
- JS λ=30；
- JS λ=60。

预先写好的选择规则是：

1. JS 的 in-range Macro-F1 不能比 Dynamic ERM 低超过 0.01；
2. 在合格候选中，选择 mean single-factor OOD Macro-F1 最高者；
3. 如再平手，才看 in-range，再看较小 λ。

实际 Validation 结果：

| 方法 | in-range Macro-F1 | mean single-factor OOD Macro-F1 |
|---|---:|---:|
| Dynamic ERM | 0.714013 | 0.666471 |
| JS λ=3 | 0.718417 | 0.676134 |
| JS λ=30 | 0.716428 | 0.676164 |
| **JS λ=60** | **0.729806** | **0.699742** |

三个 JS candidate 都通过 in-range guardrail，λ=60 的 Validation OOD 指标最高，因此被选定。

当时的 summary 明确记录：

- simulated Test used = false；
- real XRD used = false。

随后五个 training seeds 的 ERM vs λ=60 Validation replication 仍然保持 5/5 主 OOD effect 为正，并且记录 `lambda_retuned = false`。之后才进入 simulated Test 和真实域评估。

### 5.3 最终判断

因此最简单、最准确的解释是：

> `lambda_js=60` 不是看到 Test、RRUFF 或 CNRS 结果以后挑出来的；它先由 Train-only 梯度尺度限定候选范围，再由 simulated Validation 上预先定义的 OOD / in-range 规则选出，随后固定用于最终多 seed、Test 和真实域实验。

### 5.4 状态

**CLOSED.** 不需要重新 sweep λ，也不需要用真实域重新调 λ。

---

## 6. 本轮考古的最终决策

截至 2026-08-29，这五个“方法细节是否有证据”的问题均已结案：

1. **Related Work / contribution boundary：CLOSED。**
2. **ERM vs JS 公平对照：CLOSED。**
3. **formal_14060 数据集构建与 parent split：CLOSED。**
4. **五类扰动的 structure-preserving / label-preserving 实现：CLOSED。**
5. **λ=60 的选择路径：CLOSED。**

这不意味着新颖性 framing 的写作已经完成。**证据问题已经关闭，表达工作仍然是当前最高优先级。**

后续不应再把这五项重新包装成“需要补实验的科研缺口”；只需从本文件和对应当前/历史源文件抽取内容，用于 Methods、Related Work、核心方法图、组会 PPT 和申请材料。