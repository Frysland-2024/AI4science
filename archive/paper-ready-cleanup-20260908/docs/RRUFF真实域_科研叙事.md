# RRUFF 真实域实验验证：完整科研叙事

> 这是一份从仓库可追溯产物（git 提交轨迹 + 报告原文 + 预注册合同 + 决策文档 + 审计记录）还原的科研过程档案，用于帮你恢复这段研究经历的记忆。
> 诚实说明：当年的逐句对话原文已不在本机当前记忆里，以下叙事主要**从产物反推**（git 提交轨迹、报告原文、预注册合同、决策文档、审计记录），另有少量内容来自**你本人回忆补充**（已在正文单独标注"本人回忆补充"）。
> 用"我"指代你（cuifa01），即 RRUFF 真实域线的设计者与执行者。

---

## 一、缘起：主线方法缺一个"真实实验域"的证据

整个大项目的核心方法，是用模拟器预训练出一个对物理测量扰动稳健的 XRD 表征（JS Consistency，`lambda=60`，ResNet-18-GN）。在受控模拟域内，这套方法已经反复证明有效：

- 模拟 Validation 单因子 OOD Macro-F1 +0.047（5/5 配对正）；
- 冻结的 simulated Test 单因子 OOD Macro-F1 +0.055（5/5 配对正）。

但模拟域里"稳健"不代表真实实验室里"有用"。缺的是一块**真实实验 XRD 谱**上的证据。

为什么选 RRUFF 而不是别的实验库：当时读了大量文献，发现 **RRUFF 是社区里主流的 real domain 基准**（被多篇 PXRD 表征学习工作用作真实域验证），而且它和本机已有的文献库数据比较吻合——用它能对齐到社区公认的实验域口径，而不是自己造一个难以被同行认可的真实域。因此 RRUFF（矿物的公开实测 PXRD 数据库）成为这块证据的候选来源。

> 注：本条为本人回忆补充，非 git 产物反推。

**当时的真实动机不是"再刷一个 benchmark 分数"，而是回答：模拟器学到的表征，到底能不能迁移到真实谱？**

---

## 二、关键决策（07-24）：把"一次性验收"升级为"研究问题"

最初的真实域协议，是把真实谱只当一次性的 zero-shot 最终验收——目的是避免真实数据参与模拟参数、lambda、方法和 checkpoint 的选择（这是保住模拟域实验纯净性的红线）。

但这一步对科学问题太浪费了。真实数据不该只被用来"验收"，它本身能构造一个更硬的迁移学习问题：**在同样的少量真实标签预算下，不同预训练方法学到的表征，谁更容易适配？**

于是 07-24 做了转向（提交 `5e624f0` 及其后一整串工程落地：protocol `c8ed3d0`、contract `a1ebcf6`、preflight `4b042e2`、planner `9468d1d`）：

- 从纯 zero-shot 验收，扩展为 **0/1/2/3-shot 少样本适配轴**；
- 冻结 RRUFF-70 作为首批真实语料；
- 明确规定"公平性冻结"：三种方法共享同一 support episode、同一适配程序、同一预算，主适配只用 cross-entropy、冻结 encoder、只更新 classifier head。

这一步的实质是：**研究问题从"我的模型迁移得准不准"变成了"哪种预训练表征更容易被迁移"**——后者才是能检验方法本身价值的问题。

---

## 三、数据资产：model-blind 的 RRUFF 语料（350 → 371）

在模型访问真实数据之前，先把数据资产建好、冻结、审计：

- 08-03 构建 RRUFF-350（提交 `cb57944`，含 build 审计）；
- 08-03 扩展为 RRUFF-371（提交 `0ec3d88`，含 expansion 审计）。

"model-blind" 是这条线反复强调的原则：**数据在模型接触前就冻结，用确定性 SHA-256 规则锁定，谱图与 manifest 不提交 GitHub、只登记哈希**——防止用真实数据反过来"偷看"地调模拟方法。

---

## 四、第一枪：zero-shot pipeline 诊断（35 样本，08-06）

在正式 few-shot 之前，先做了一次纯管道诊断（提交 `2cb656c`）：

- 从 RRUFF 源归档独立抽样 **35 样本（5/class × 7 晶系）**，与 RRUFF-371 零交叉；
- 加载 10 个 frozen checkpoint（5 seeds × 2 methods），直接 forward，不训练；
- 波长审计：34/35 是 CuKα，排除波长失配干扰。

**结果**（只做诊断，不报论文数字）：

| 方法 | 平均准确率 | vs 随机 (0.1429) |
|---|---|---|
| Dynamic ERM | 0.1886 | +0.046 |
| JS Consistency (λ=60) | **0.2343** | +0.091 |

**三类关键发现：**

1. **管道通畅**：triclinic 零 shot 准确率 0.64，证明预处理对齐、checkpoint 加载、模型读谱全都正确。
2. **JS > ERM 跨域成立**：真实域上仍保持 +4.6pp 优势，方向与模拟域一致。
3. **高对称性坍缩**：cubic=0.00、hexagonal=0.04、trigonal=0.08——高对称晶系峰少、信号弱，零 shot 下模型缺"真实谱锚点"来区分它们。

**这一枪的直接结论：zero-shot 不够，few-shot 是必需的下一步。** 这也是整条线从"broad zero-shot transfer"转向"label-efficient adaptation"的第一个硬证据。

---

## 五、探索性研究：RRUFF-70 few-shot（08-06）

用 70 样本（10/class × 7）跑完整的 few-shot 适配（提交 `385cbbc`）：

- **K = 1 / 2 / 5**；
- **5 pretraining seeds × 5 episode seeds = 150 次 fine-tune**；
- 冻结卷积 backbone（88.85% 参数），只训练 projection(7168→256) + classifier head(256→7)；
- support-loss early stopping（patience=20，max 200 epochs）；
- 主结果（accuracy，early-stopping）：

| K | ERM | JS | 平均配对 Δ |
|---|---|---|---|
| 1 | 0.1975 | 0.2400 | +0.0425 |
| 2 | 0.1993 | 0.2479 | +0.0486 |
| 5 | 0.2091 | 0.2800 | +0.0709 |

JS 在所有 K 上都更易适配，60/75 配对为正。

**但同时暴露了两个真问题：**

1. **统计严谨性**：150 次训练 ≠ 150 个独立观测。真实独立单元是 75 组配对（3K × 5 seed × 5 episode），不同 episode 的 query 集大量重叠——不能做 naive t-test。
2. **monoclinic 负迁移**：monoclinic 在所有 K 上负迁移（K=5 时 Δ=−0.088），一度被认为可能是 JS 的方法边界。

---

## 六、主动降级：RRUFF-70 → exploratory

拿到"看起来有效"的结果后，最容易的做法是直接把 RRUFF-70 当论文的真实域结论。但我没有这么做（CONTINUATION 第 21 节明确记录了理由）：

- RRUFF-70 **样本量小**；
- 这些结果**已经参与了后续假设的形成**。

如果再把同一批数据包装成"最终确认"，**探索和确认就混在一起了**——这是实验治理上的大忌。

所以 RRUFF-70 被主动定义为：

> **exploratory / hypothesis-generating evidence**

它的作用收缩为四点：证明管线可运行、暴露类依赖效应、产生可检验假设、为更大的独立确认实验提供设计依据。

**这一步是整个研究过程最重要的转向之一：目标从"找到一个支持方法的真实谱结果"，变成了"建立探索—确认分离的证据结构"。**

---

## 七、预注册确证设计：RRUFF-301

用 RRUFF-371 资产里的 **301-sample extension** 构建 confirmatory 实验，并在模型访问前冻结（提交 `385cbbc` 的 preregistration + `24d8c85` 的 confirmatory）：

- 301 条实验 PXRD，**七晶系各 43 条**；
- **10/class adaptation pool（70 条）+ 33/class locked test（231 条）**；
- K = 1 / 2 / 5；
- 5 pretraining seeds × 5 episode seeds；
- **paired ERM-pretrained vs JS-pretrained comparison**；
- **primary metric = paired ΔMacro-F1**；
- 适配使用相同 support、相同优化器、相同可训练 head；
- **不允许增量查看结果后修改 K、episode、split 或 primary endpoint**。

真实域问题被正式写成：

> **在相同少量真实标签预算下，JS 预训练学到的表示是否比 Dynamic ERM 预训练表示更容易适配实验 RRUFF PXRD？**

至此，项目第一次真正形成了完整证据结构：

```
simulation hypothesis → exploratory real evidence → independent confirmatory real-domain test
```

preregistration 解决的核心问题就是：**防止自己拿到结果后反过来"改题"**——这是对"探索性结果已经污染了假设形成"这一教训的直接回应。

---

## 八、数据事故：trigonal/hexagonal 标签 bug（v1 作废）

RRUFF-301 第一次确认实验跑完后，内部审计发现标签构建有严重问题（提交 `24d8c85` 的 v1 audit trail）：

- RRUFF 的 **CELL PARAMETERS 元数据在晶格约定下，把 trigonal/rhombohedral 表示在 hexagonal setting**；
- v1 parser 因此把 trigonal 错并入 hexagonal；
- 结果：**hexagonal=86（43 真 + 43 误标）、trigonal=0、test=241（不是协议的 231）**。

**这个 bug 的危险在于：代码能正常跑完，也能输出一套"看似完整"的结果。** 只盯着分数，很容易把"软件成功执行"误当成"科学实验有效"。

发现它的方式不是灵光一现，而是**样本数对不上**：预测文件 36,150 条 / 150 runs = 241 每条（不是 231），trigonal 在所有 K 上 F1 恒为 0，adaptation pool 是 60 不是 70。

**为什么选择作废而不是修补：**

一个"好看的结果"不能比数据身份更重要。所以：

1. 明确将 v1 **invalidated for confirmatory use**；
2. 保留完整审计轨迹 `rruff301_v1_audit_trail_20260807.md`；
3. 改用 DIF `space_group` 证据；
4. 用 `pymatgen.SpaceGroup` 做晶系映射；
5. 重新验证 70 adaptation + 231 test、33/class、zero overlap；
6. 从修正后的冻结 split **完整重跑全部 150 个 adaptation runs**。

这一事件后来成为整条线最硬的方法论节点：

> **科研的目标不是保住一个好看的结果，而是确保结果的身份、标签和评估协议值得相信。**

---

## 九、重建：v2 全量重跑（08-07）

修复后的 RRUFF-301 v2 完整结束。**Primary Macro-F1 结果：**

| K | ERM | JS | paired mean Δ | positive pairs |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | **+0.0433** | 21/25 |
| 2 | 0.3026 | 0.3486 | **+0.0460** | 23/25 |
| 5 | 0.3555 | 0.4099 | **+0.0545** | 24/25 |

合计 **68/75 配对为正**。同时 K=1/5 的 fixed-200-step 敏感性检查保持同方向（Δ 差异仅 0.0004~0.0018），证明主要差异不是 early-stopping 的偶然产物。

证据等级因此上升：从"模拟 OOD 稳定优于 ERM + 一个小 pilot 有潜力"，变为：

> **"JS 在受控模拟域形成重复性 robustness gain，并在独立、预注册、纠错后完整重跑的 RRUFF-301 确认实验中表现出更高的 few-shot adaptation efficiency。"**

但结论仍然保持克制：zero-shot 绝对性能不高；不同晶系收益不均匀；RRUFF 是矿物域、不代表全部 PXRD；不能把 JS 描述成新算法；不能声称已显式 disentangle。

---

## 十、深入分析：per-class / fix-break / calibration

v2 之后没有急着再开新模型，而是分析已有预测（提交 `24d8c85` 的 representation analysis + 后续 calibration）：

- JS **fix** 了哪些 ERM 错误、又 **break** 了哪些 ERM 正确样本；
- confidence 如何变化；
- 哪些类之间存在 **asymmetric confusion**；
- per-class gain 是否随 K 一致；
- 补充 ECE / NLL / Brier / confidence distributions。

**这一步的意义不是新增一个"calibration 创新点"，而是把问题从"哪个分数更高"推进到：这个学习原则在哪些样本、哪些类、哪些置信度状态下改变了模型行为？**

---

## 十一、monoclinic 负迁移没有复制（08-07~08）

RRUFF-70 曾出现 monoclinic 在 K=5 下明显负迁移，一度被认为可能是 JS 的方法边界。RRUFF-301 v2 对它做了明确的 confirmatory check：

| K | ERM monoclinic F1 | JS monoclinic F1 | Δ |
|---|---|---|---|
| 1 | 0.2374 | 0.2735 | +0.0360 |
| 2 | 0.2335 | 0.3016 | +0.0681 |
| 5 | 0.2294 | 0.2985 | +0.0691 |

**monoclinic 在所有 K 上 Δ 均为正，早期负迁移没有复制。** 于是它被重新解释为：

> RRUFF-70 小样本探索性伪影 / 不稳定的类级信号。

这强化了一条证据观：**探索性结果负责提出问题；确认性结果有权否定探索阶段的故事。**

---

## 十二、Evidence Freeze 与论文冻结（08-08 起）

到 08-08（提交 `1bf8a99`），主线已经拥有完整证据链：

1. matched Dynamic ERM baseline；
2. train-only lambda legality / scale governance；
3. five-seed paired Validation replication；
4. frozen simulated Test confirmation；
5. exploratory RRUFF-70；
6. independent RRUFF-301 confirmatory v2；
7. per-class / fix-break / confidence diagnostics；
8. calibration supplementary evidence；
9. v1 label-bug audit trail。

于是主动停止"默认继续训练"，切换到 `experiment-building → evidence freeze → manuscript building`。规则变成：除非论文写作或外部 review 暴露明确且现有 frozen artifacts 无法回答的 gap，否则不新增训练。

**这不是"做不动了"，而是第一次主动承认：一个研究项目的完成标准不是永远还能多跑一个实验，而是现有证据是否已经足够回答冻结的问题。**

随后（08-13，提交 `dbc09df`）进一步明确：项目当前不以发表为目标，RRUFF-301 单纯为了"论文级确认/执行溯源/reviewer 证据"而重跑**不是优先事项**；除非未来研究目标独立要求新的真实域实验，否则不花精力做重复跑。

---

## 十三、最终认识：研究问题的层级跃迁

回顾整条线，最重要的变化已经不是某一次 +0.05 Macro-F1，而是研究问题的层级变化（CONTINUATION 第 29 节）：

> 最开始：怎样让模拟 XRD 更像真实谱？
> 然后：怎样让模型对物理扰动更鲁棒？
> 再然后：Residual 是否能把测量差异与晶体语义分开？
> 最终：**模拟器知道哪些数据是同一个物理对象的不同观测；这种关系本身能否成为监督？**

对 sim-to-real / real-domain adaptation 的最终认识：

- **zero-shot 直接迁移是困难的**（高对称晶系直接坍缩），但这不否定方法，而是说明真实域需要"锚点"；
- **few-shot / label efficiency 才是检验预训练表征价值的正确战场**——它问的是"表征好不好迁移"，而不是"迁移得准不准"；
- **类依赖的收益异质性必须报告**，平均涨点会掩盖"有的类在变好、有的类在变坏"；
- **数据身份（标签、split、协议）比一个好看的数字更重要**——一个跑得通但标签错的实验，不如一个作废重跑后可信的实验。

这条线最终最适合被概括为：

> **从一个 PXRD Sim2Real 工程问题出发，通过多次失败和协议修正，把科学测量中的同源关系重构成一个可验证的机器学习监督问题。**

---

## 十四、完整证据链与关键文件索引

### 证据链（从强到弱）

| 层级 | 域 | 结果 | JS > ERM? |
|---|---|---|---|
| 模拟 Validation | 14,060 结构 OOD split | +0.047 OOD F1，5/5 | ✅ |
| 模拟 Test | 2,109 结构 | +0.055 OOD F1，5/5 | ✅ |
| RRUFF pipeline test（zero-shot） | 35 独立矿物谱 | JS 0.234 vs ERM 0.189 | ✅ |
| RRUFF-70 exploratory | 70 谱，K=1/2/5 | Δacc +0.043~+0.071，60/75 | ✅ |
| **RRUFF-301 confirmatory v2** | **301 谱，7 类平衡，K=1/2/5** | **ΔF1 +0.043~+0.055，68/75** | ✅ |
| fixed-step 敏感性 | K=1/5，200 steps | 方向不变 | ✅ |
| monoclinic confirmatory | 301 谱 | 负迁移未复制 | ✅ |

### 关键文件（git 可追溯）

- 决策：`00_project_context/decisions/2026-07-24_RRUFF_FEWSHOT_ADAPTATION.md`、`00_project_context/DECISION_LOG_20260813.md`
- 报告：`xrd_robustness/reports/` 下 `rruff_pipeline_smoke_test_20260806.md`、`rruff70_complete_report_20260806.md`、`rruff301_confirmatory_full_report_20260807.md`、`rruff301_v1_audit_trail_20260807.md`、`rruff301_representation_analysis_20260807.md`、`RRUFF301_COMPOSITION_AUDIT.md`
- 结果数据：`xrd_robustness/data/real_xrd/rruff371/results/`（`rruff301_fewshot_runs.json` 等）、`xrd_robustness/reports/rruff301_fewshot_results.json`
- 历史叙事：`PROJECT_JOURNEY_CONTINUATION_20260807_20260808.md`（已并入 `docs/PROJECT_HISTORY.md`）

### 关键提交（时间线）

| 提交 | 日期 | 内容 |
|---|---|---|
| `5e624f0` ~ `9468d1d` | 07-24 | few-shot 决策 + protocol/contract/preflight/planner 工程落地 |
| `55a2edb` | 07-29 | five-seed paired ten-run 预注册 |
| `cb57944` / `0ec3d88` | 08-03 | RRUFF-350 构建 / RRUFF-371 扩展 |
| `2cb656c` | 08-06 | pipeline smoke test + Tan Lab 域重定义 |
| `385cbbc` | 08-07 | RRUFF-70 exploratory + RRUFF-301 预注册 |
| `24d8c85` | 08-07 | RRUFF-301 v2 + representation analysis + v1 audit trail |
| `1bf8a99` | 08-08 | confirmatory transition + evidence freeze |
| `dbc09df` / `1eab4d5` | 08-13 | RRUFF-301 rerun 非优先（+理由修正） |
| `907c287` / `90f8efe` | 08-29 | 去 evidence-tier、locked-test 直接报告、measurement-equivalence framing |
