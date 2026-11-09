# Project History — Public Research Timeline

This file is the **public, concise history** of how the PXRD project evolved. It preserves major corrections, negative results, and changes in problem definition without reproducing internal handoff notes or application material.

For current scientific claims, use [CURRENT_STATE.md](CURRENT_STATE.md) and the tracked result reports. History explains *how the project changed*; it does not override the current state.

## 2026-11-10 · V11 从固定候选转向梯度约束的全自动 HPO

**思路转折（负责人明确纠正）：** 最初过于复杂的全维度 HPO 逐步收缩为两个科学问题——（1）同母结构 JS 正则强度 λ；（2）参考 Bin Cao/SimXRD 产生的 PXRD 峰信息保留假设，即 ResNet 下采样 Stride 与卷积 Kernel。Weight decay=1e-4、LR=2e-4+Cosine 继承 V9/V10 合理训练配方；Batch size=16 优先视为工程预算，不与科研参数混淆。随后早期 V11 .9 曾把这两个问题实现为四组固定架构加两个固定 λ=30/90，负责人进一步强调：**保留 Optuna 的真正全自动优化能力，但给优化限定有依据的方向与范围**，不能反过来把少量预定组合误称“自动调参”。

**新的科学设计：** 以 V9 Train-only learned-state 梯度尺度 Gate 为先例，在新 V11 全部 108,478 个独立 Train 母结构上实施已学习状态的 CE/JS 全模型梯度检查（其中 ResNet trunk 比率用于 λ 作用范围的校准）；在 Validation 之前冻结 λ 的有界搜索范围。将中间 stage stride {2,4} 与 residual kernel {5,9} 分开作为 Optuna 两个变量，在 λ 锚点下先形成 A0/A1/A2/A3 的 2×2 可解释对照，再由多变量 TPE 自由建议后三维组合，决策仍取自冻结 synthetic Validation。为避免上一轮**暴露次数和训练步数过短**，每个 HPO Trial 至少 50 个完整 Train 母结构 Epoch（Batch16 为 339,000 optimizer updates），确认/正式训练最多 100 Epoch，早停不得先于 Epoch50，所有阶段统一 100 Epoch Cosine 时间尺度；没有凭 5/10 Epoch 的临时 F1 选赢家。测试集/RRUFF 严禁参与优化。

**证据状态：** 本次已把 .10 自动方案提交到 main，隔离本机核验 **47 项 server_migration 回归测试 + 2 subtests PASS**，并包含真实 Optuna 4.9 的三维 TPE 候选模拟。它目前是**代码与方案交付，而不是 GPU 科学结果**：5–10 Epoch Train-only learned-state 训练、108,478 Train-parent 完整梯度审计、目标 GPU 的实际 HPO、确认种子和真实 RRUFF-Cu1011 得分均 NOT_RUN。相比 .9，这是一次**为保留科研问题与降低无效搜索，而不是为增加超参数数量**做出的流程纠偏。操作合同与限制以 [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) 为准。

---
## 核对后的完整时间线（2026-11-09 阶段节点）

**这张表是项目发展的主时间线**：记录不同科研阶段实际解决了什么问题，不把 Git 代码版本号当作严格顺序的独立论文，也不覆盖已有结果和失败记录。

| 阶段 | 实际发生的事情 | 科研性质 |
|---|---|---|
| **FerroAI** | 从材料性质预测起步，逐渐建立对数据、模型和证据链的认识 | 前置研究经历 |
| **PXRD 早期—V8** | 物理扰动模拟、PAMPT、Residual、结构化模拟等多次尝试与纠偏 | 研究问题与方法探索 |
| **V9（2026 年 7–8 月）** | 转向 ResNet-18-GN，确定 JS λ=60，完成多种子 ERM–JS 对照及模拟 Test | **完整主研究成果** |
| **早期 V10（7 月）** | 尝试测量信息监督的 Residual 解耦，得到负结果并归档 | 与 V9 后期交叠的探索支线 |
| **2026 年 8–10 月** | RRUFF、CNRS、校准、数据效率补充实验；另探索参数反演，随后归档 | 已完成研究的补充与新方向尝试 |
| **11 月的 V10** | 更新模拟环境，探索 CNN11、ResNet 的 Stride/Kernel，以及 LR/Scheduler | **下一阶段的初步架构与训练优化** |
| **V11（当前）** | V11 物理模拟器、15.5 万结构数据库、完整训练和 RRUFF-Cu1011 竞争性测试规划 | 新阶段的基础设施基本就绪，正式性能实验待运行 |

**主要阶段分界：** 回顾性地把 **V1–V9 视作已经完成的一轮 PXRD 科研**（研究问题→方法形成→V9 的冻结对照与 Test 验证）；**11 月的 V10 只是下一阶段的初步调参/架构筛选**；**V11 则负责更大数据集上的后续训练与真实域性能检验**。V9 不是被 V10/V11 “补做完”的项目。

**历史精确性：** V1–V5 暂无逐版本完整可核验证据，因此“V1–V9”是科研阶段概括，不是九次独立验证；**7 月的 V10 Residual 分支**确实早于 V9 最终收束，与 V9 工作交叠，且和 **11 月的 V10 架构比较**不是同一试验。8–10 月对 V9 的真实域、可靠性和样本效率研究可视为第一轮成果的后续完善，不等于重新开启其超参数选择。11 月的 V10 单种子 A0_R1 优胜（Validation OOD Macro-F1 0.731830）来自 **LR=2e-4 与 Cosine 捆绑改变**；不能据此宣称 LR 单变量最优，更不能当成 V11 或 RRUFF 成绩。

**可追溯依据：** [2026-08-23 历史全档](https://github.com/Frysland-2024/AI4science/blob/d70d84da6535a0a04e7cd5fba3faa794c64656cd/00_project_context/PROJECT_HISTORY.md)（FerroAI→V9、7 月 V10 负结果）、[V9 科研结果](../xrd_robustness/reports/RESULTS.md)、[JS 权重选择证据](PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md)、[11 月 V10→V11 迁移说明](PXRD_SERVER_MIGRATION_V11_ONECLICK_20261103.md)。以下保留各节点的详细经历与负结果。**本表只整理历史，不修改研究合同、训练参数、Test 或 RRUFF 冻结规则。**

---


> **新增沟通记录（整理于 2026-09-20）：** [与学长沟通纪要：XRD 项目当前进展与后续计划](PROJECT_HISTORY_NOTE_2026-09-20_SENIOR_MEETING_SUMMARY.md)。依据用户提供的会议摘要截图，记录当前方法与验证进展、定量反演及初步晶体结构预测方向、云算力与协作安排；会议日期未注明。

> **2026-10-22 导师汇报复盘（2026-10-23 整理）：** [方法设计、真实域验证与物理/应用可信度的视角错位](PROJECT_HISTORY_NOTE_2026-10-22_SUPERVISOR_PRESENTATION_REFLECTION.md)。系统记录当晚交流与后续对话纠偏：温度/成分扰动的物理边界、cubic 示例被误认为只做单一晶系、RRUFF 的 K-shot 微调被误听为总训练样本数、CNRS 无目标域适配的 zero-shot 相对增益与低绝对性能的不同评价、原方法/原模型比较及 bias、数据可获得性、扩容和发表文献跑分对标，以及实验室铁电陶瓷 R/T 相真实谱检验建议。保留负责人因方法设计贡献未得到充分理解而受挫及「横向方法研究 vs 纵向材料任务」的认识变化。此为历史反思，不更改冻结实验，也不宣称导师建议已获批或完成。

> **2026-10-23 暂定研究兴趣认识（PROVISIONAL）：** 在复盘导师汇报、准备与东京大学小关泰之老师交流时，项目负责人提出一个新的自我观察：与以材料合成、制备及湿实验为核心的工作相比，自己可能更适合围绕**科学测量系统与测量数据**开展研究，尤其是从物理测量过程、模拟与正向模型、信号处理、监督设计、逆问题到真实域验证的研究链条。过去从 FerroAI 到 PXRD 的选择与反复尝试，为这一兴趣判断提供了经历依据；但当前的已完成研究主要是**基于现有 PXRD 数据/模拟的 ML 方法与评估**，不能据此声称已经具备激光/光学仪器搭建、测控硬件或完整测量系统开发经验。**有待进一步分辨的三个方向是：仪器与光路硬件、测量方法与采集策略、计算测量/信号分析。** 这是一种探索中的自我定位，不是项目主线或毕业课题已经正式变更，也不意味着排斥所有物理实验。未来选择研究组需确认具体课题是否主要涉及光学搭建、信号与算法，还是材料/生物样品制备。

---

## 2026-11-09 · Cuifa CPU provisional sync, not assumed identical hardware

The user reported that the Windows RTX 4070 Ti SUPER / 32GB desktop used for the intended HPO has a CPU stronger than the local Ryzen 9 7945HX, without supplying the exact model. The previous unrecognized-host 2-worker default would underuse that machine. Therefore, the user's tested **12-worker / 4-queue / 64-cache** profile is the **conservative Windows default** on all Windows hosts, including Cuifa's 32GB desktop, regardless of CPU model or RAM size. The previous 2-worker low-memory fallback was deliberately removed at the owner's request; free-RAM warnings remain. A **16-worker resource profile** is deliberately opt-in for a bounded Train-only benchmark and full GPU/Validation headroom check, not automatically assumed faster or approved for HPO. This decision carries forward the same-parent paired-physics determinism and preserves the existing scientific experiment plans. The owner subsequently extended the **same 12/4/64/1 prefetch baseline to Linux/cloud and direct Python entrypoints**, rejecting an automatic cloud-specific 4-worker fallback. This is a uniform starting configuration, not evidence that 12 workers are optimal on an untested rental host; per-machine explicit runtime overrides and hardware preflight remain valid.

## 2026-11-09 · V11 CPU bottleneck measured and Windows prefetch tuned

Once the complete six-profile Validation and a bounded real RTX 4060 training run had passed, the limiting engineering problem was **CPU-bound online TCH pseudo-Voigt spectrum generation**, not GPU memory. Rather than replacing the physics model, the project compared deterministic multiprocessing worker counts, bounded prefetch and reflection caches. With identical paired-spectrum SHA fingerprints, short CPU+GPU A0/JS comparisons improved from approximately **82 parents/s at 4 workers/2 queues** to **168 parents/s at 12 workers/4 queues** on the user's Ryzen 9 7945HX laptop. A follow-up 12-worker **512-step plus complete six-profile Validation** acceptance passed in 129.88s for the train+scoring phase (versus ~183.17s in the earlier 4-worker acceptance), with cached-panel and checkpoint hashes intact; the lowest observed free system memory was 5.80GiB, so further concurrency increases were not justified. This is a compute pipeline gain, not a trained-model accuracy result.

The Windows launcher gained a machine-specific, reproducible CPU resource profile: auto-enabled only on the known 16-core 7945HX/32GiB host, conservative by default elsewhere. cuifa's Windows 4070 Ti SUPER CPU is still unknown and must be benchmarked separately. The V11 research protocol, frozen Validation and RRUFF holdout are unchanged. The executable .8 CLI still has 5/10/10-epoch defaults, but the active performance-first v2 research plan has moved to 50-epoch matched JS/ERM convergence pilots and a prospective larger HPO; that plan is NOT YET IMPLEMENTED. No formal HPO/final or real-domain inference was performed.

## 2026-11-09 · HPO full-data claim corrected to independently shuffled parent epochs

**Research decision (implementation default, formal HPO not yet authorized):** While adapting V11 to cuifa's Windows 4070 Ti SUPER, a code audit exposed that the old 6,160 × 16 HPO recipe made only 98,560 parent draws from 108,478 independent Train structures, and the prior per-step random selection could repeat a parent across batches. The former phrasing "HPO uses the whole Train library" therefore described the *sampling pool*, not actual coverage. Rather than implying exposure to every structure, V11 now defaults to deterministic **epoch-wise shuffled, without-replacement** sampling, one complete 108,478-parent epoch per HPO candidate (6,780 steps at effective batch 16), two epochs for confirmation (13,560), with a shorter last batch and reproducible resume. The previous random-batch sampler remains selectable for provenance; no old results are reinterpreted as new full-coverage scores.

At the same time, separate GPU microbatches accumulate parent-weighted CE + same-parent JS before one optimizer update (effective batch unchanged), and HPO vs final-training platforms may vary CPU prefetch resources without changing the scientific contract. The motivation was **experimental exposure validity and practical hardware portability**, not a new model, changed RRUFF selection, or an observed accuracy improvement. Bounded local RTX 4060 smokes and microbatch/coverage tests provide only engineering evidence; cuifa Stage 0, large-data HPO and RRUFF evaluation remain unrun. See [current state](CURRENT_STATE.md) and [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

## 2026-11-04 · AlphaDiffract original-paper check and owner freezes RRUFF-Cu1011

After the user explicitly asked whether AlphaDiffract (Andrejevic et al. 2026) used a compatible RRUFF filtering protocol, the team checked the original paper's Methods §5.1 rather than inferring its sample policy from the abstract. Its evaluation uses **1362 curator-background-corrected XY + 2901 DIF**, progressive metadata/structure/cell and radiation conversion screening, **745** PXRD/DIF source label and lattice matches, then **734** after converting wavelengths without missing angular data. Importantly, **59 of the final 734 are calculated powder patterns**, and the authors used **20-keV/8192-bin/5–20°** input (10-model ensemble 81.74 ± 0.78%), not our original RAW/Cu Kα/V11 10–80° 3501-bin source. Thus their rigorous filtering provides a methodological precedent without forcing an identical sample count or author-mismatched test set.

The owner-requested additional full RAW–DIF six-cell-parameter cross-check found **758** close source pairs (≤0.1% lengths and ≤0.1° angles), **219** moderate source-pair differences (≤1% lengths and ≤1° angles) and **34** larger source-lattice discrepancies, including cell-setting-like differences. Those 34 cannot honestly be called AlphaDiffract-certified, but none had previously failed the project's **seven-crystal-system family** source label tests, and the project is not fitting full lattice parameters. Rather than optimizing the held-out sample list with future accuracy, owner-approved decision is to **KEEP and transparently flag the 34**, freeze primary RRUFF-Cu1011 membership and processing before model inference, and optionally report sensitivity on the non-flagged 977 as secondary analysis, never choosing the headline ex post. **134** main-set nonstandard symmetry symbol spellings are separately flag-labeled. Published comparisons to Bin Cao 1003, Lee, Salgado 908 and AlphaDiffract 734 must be cross-paper context or require same-1011 reruns for direct leaderboards.

**Immutable private freeze:** source ordered manifest SHA256 75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37; V11 1011x3501 inputs SHA256 19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179; freeze decision JSON SHA256 d258e3f85506e91867e2d9aebd73b77e2f777636bc6a8b722ebe28bf52129455. Source and code histories retained. See [final selection and AlphaDiffract rationale](RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md).

## 2026-11-04 · Whole-cohort physical audit: 1034 candidates become 1011 Cu-domain primary + 23 separately characterized records

After the owner considered an RRUFF-1034 main set and asked for **final verification of sources, labels, and preprocessing**, every original RAW and DIF file was audited against its SHA, RRUFF ID, sample label, diffraction sampling axis and radiation. The first audit appeared to find 21 broken x axes and 22 incomplete model windows; drilling into the raw bytes showed that scientific-notation intensities were being silently lost and a spurious -2009,10 source row was being treated as a measurement. These were parser defects, not scientifically justified reasons to discard good specimens. The pipeline was repaired, 19 isolated native theta typos corrected deterministically in derived arrays, one duplicate angle averaged, one impossible negative angle excluded, with untouched raw source archives and replayable logs.

The decisive scientific problem was **measurement-condition mismatch** rather than software strictness: **19 specimens explicitly said Mo radiation**, including 11 with paired calculated DIF files in Cu radiation. A Mo raw XRD spectrum cannot be treated as a Cu source merely because its DIF reference uses Cu. Three Cu-compatible spectra stopped at 60°/70° and could not supply complete measured 10°–80° model inputs. One Harmotome RAW comprised 232 irregular peak-like observations rather than a dense profile. The owner-preferred **1034 original records** therefore led to **1011 Cu-compatible, densely sampled, fully measured 10–80° primary spectra**, plus 19 Mo separate-domain candidates, three partial-window challenge spectra, and one quarantined sparse profile. The 1011 has a reproducible 3501-point source-only fixed input array, all seven labels, and cryptographic source/array prelock; no model accuracy was inspected or used for data selection.

This is a central research-methodology lesson: reject arbitrary source filters (such as failure to parse 24 valid nonstandard space-group symbols), **but keep physically meaningful measurement/wavelength and missing-observation distinctions**. The resulting 1011 has roughly the same sample count as the Bin Cao 1003 benchmark, yet the two sample cohorts and source vintages are NOT identical; no same-sample paper leaderboard should be claimed. Original RAW instrument wavelength is not always independently documented, and 134 noncanonical SG family labels in the Cu-primary carry explicit evidence tiers; scientific final certification is distinguished from engineering source prelock. Full record [RRUFF source QA and Cu1011 prelock](RRUFF_1034_FULL_SOURCE_AUDIT_CU1011_PRELOCK_20261104.md).

## 2026-11-04 · Exhaustive source-only reconsideration of remaining 13 mixed RRUFF specimens

After selectively reinstating two mild-impurity specimens into the proposed 1032 sample real-domain benchmark, the project owner asked to examine **all remaining 13** just as seriously rather than stop at the apparently clear examples. The method expanded from single named reference peak checks to all locally available reference variants, baseline/smoothing sensitivity, explicit overlapping-reflection analysis and separate exploratory two-phase NNLS fits, all run on the original RRUFF source spectra without any model inference. The audit produced **7** strong source-supported >10% impurity marker cases, **2** probable large extra-phase cases not formally certified because secondary identity/peak overlap remain unresolved, and **4** genuinely ambiguous cases. In particular, Rutile/hematite independent markers were weak despite 13% sample composition (mass fraction is not the Lee peak-height ratio); chlorite/Actinolite hovered near 10% depending on assumed chlorite family and signal processing; both garnets were structurally near-degenerate; Natrojarosite lacked a named secondary phase. The 13 source cases and all numerical uncertainties were documented and **none was inserted into the proposed 1032 primary Test**. Research lesson: correct application of a benchmark preprocessing rule requires preserving unresolved cases as unresolved, not arbitrarily inflating the sample count or treating ambiguous approximate two-phase fits as experimental proof. See [13-case audit](RRUFF_13_MIXED_SOURCE_AUDIT_20261104.md).

## 2026-11-04 · Historical proposal (superseded): 1030 to proposed 1032 after source-only revalidation

Having first proposed to remove all 15 explicitly mixed RAW profiles, the project owner reconsidered whether two weakly contaminated samples (Dickite/quartz R090054-1 and Polylithionite/corundum R060215-1) could legitimately meet an adapted Lee 2023 10% strongest impurity-peak criterion. Rather than reselect on machine-learning performance, a **blind source-data-only** validation was performed: 6 quartz and 13 corundum DIF reference variants, three background/smoothing settings and four quartz peak-position tolerances. The Dickite specimen passed an observed-total intensity **upper-bound** at 7.60–7.66%, giving high-confidence evidence. The Polylithionite specimen involved an impurity/main 35.17/35.15-degree overlapped reflection; a source-template-constrained estimate over 39 reference/preprocessing combinations was 7.08–9.33%, just under 10% but **dependent on reference-relative-intensity assumptions**. At that point in the decision history, the project prepared a transparent **proposed RRUFF-1032 candidate** retaining the two with different explicit confidence flags, leaving 13 mixed and 4 short-angular-range cases outside the main pool. That proposal was later superseded by the final RRUFF-Cu1011 source freeze; it is not a current cohort or scoring protocol. This decision demonstrates an important research lesson: neither automatic rejection of all minor impurities nor treating model-dependent deconvolution as direct quantitative proof is justified. See [the two-case source audit](RRUFF_TWO_LEE_BORDERLINE_FINAL_SOURCE_AUDIT_20261104.md).

## 2026-11-04 · Empirical Lee impurity peak screen of 15 RRUFF mixed specimens

After adopting Lee's >10% impurity/main peak-height criterion (borrowed from Lee's 52 self-measured powders, not Lee's RRUFF preparation), the project actually read and compared original RRUFF XY_RAW experimental profiles to main-phase DIF and independently named impurity-phase DIF reflections. Three background/smoothing settings and diagnostic peak SNR checks gave **7 strong source-supported impurity exclusions** (where an independently attributed impurity peak alone was >10% of the entire experimental spectrum's largest peak), **2 low observed ratios** of 7.0%/7.6% (still only provisional Lee passes because overlaps can hide impurity peaks), and **6 Unknown** due to unspecified impurities or unresolved phase overlap. Direct Rietveld phase decomposition was not performed. These are source-only evaluations; no model predictions or selection leakage. At that proposal stage, the RRUFF-1030 candidate was unchanged and fifteen source-annotated patterns were retained as proposed challenges; the later Cu1011 freeze superseded these roles. Auditable source file IDs, ratios, sensitivity estimates, and 15 figures saved privately. See [measured-source Lee audit](RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md).

## 2026-11-04 · Mixed-phase challenge screening rule updated to Lee 2023

Owner chose to screen the 15 known multi-phase/contamination RRUFF spectra by **Lee's 10% relative impurity diffraction peak-height threshold**, instead of automatic removal upon seeing a second phase in sample descriptions. Crucial method distinction: Lee applied that rule to its self-measured 52-powder Ex_dataset_1, **not** to its RRUFF Ex_dataset_2 (which used a separate low-angle background standard-deviation cutoff). Transferring the rule to our RRUFF case study is explicitly an **adaptation**. A source-only 15-case peak-identity/phase-reference worksheet was created privately; the 15 cases are currently **Unknown** for quantitative Lee eligibility until observed peaks can be attributed, and wt% cannot stand in for the intensity ratio. At that historical stage, the proposed 1030 primary set was unchanged pending the pre-inference audit; the final Cu1011 freeze later superseded it. Never reselect samples using trained model errors. This supersedes any earlier impression that all 15 must be deleted or automatically qualify as Lee-rejected impurities.

## 2026-11-04 · Superseded RRUFF-1030 proposal: 1030 headline / 19 hard cases

This proposal-time sequence retired RRUFF-70/301/350/371 for future use, then moved from 910 to 1049 after correcting software-only parsing exclusions, to 1045 after the angular-range screen, and to a proposed **1030 primary plus 19 challenge cases** after role assignment. Those counts and roles were later superseded by the owner’s final RRUFF-Cu1011 source-membership freeze. The 19-case list remains historical case-study material; it is separate from the 19 explicit-Mo sources and does not define current primary metrics. At the time of this proposal, source/label provenance and preprocessing review still blocked the then-planned Test freeze. See [RRUFF-1030/19 protocol](RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md).

## 1. From FerroAI to a measurement-centered problem

The project grew out of earlier materials-ML work that emphasized an end-to-end evidence chain: literature and data curation, model training, metric checks, failure analysis, and materials interpretation.

When choosing a new characterization problem, PXRD became attractive because it combines:

- public crystal structures;
- controllable forward simulation;
- physically interpretable peak-position / peak-shape / intensity changes;
- a stable crystal-system label;
- and a natural distinction between latent structure and measurement realization.

The initial question was not simply "can a network classify clean simulated patterns?" but whether a classifier remains reliable when the same structure is observed under plausible measurement variation.

## 2. Physical perturbation and dynamic augmentation

Early versions built a simulator around label-preserving PXRD variation: peak-position shift, peak broadening, preferred orientation, background, and noise.

A key methodological lesson was that **data generation itself had to be treated as part of the scientific design**. Perturbation families were progressively tied to literature, physical mechanisms, and frozen numerical ranges rather than used as arbitrary image-style augmentation.

Parent structures were split before generating measurement views so that different spectra of the same parent could not leak across train / validation / test.

## 3. Over-expansion and the Residual branch

One stage explored richer objectives, including a Residual-style idea intended to separate structure-related and measurement-related information.

This branch was not forced into the final method. Analysis showed that, in PXRD, measurement effects such as peak shift, broadening, and texture are coupled to the underlying peak arrangement. A residual between two spectra therefore need not represent measurement state independently of crystal structure.

The Residual route was archived rather than rescued by adding more auxiliary losses.

**Lesson:** a physically appealing decomposition is not automatically a valid inductive bias.

## 4. Backbone diagnosis: PAMPT to ResNet

A major turning point came from diagnosing model learnability rather than immediately blaming the data pipeline.

The earlier PAMPT configuration did not sufficiently fit the training task, while a mature 1D ResNet could. Replacing the backbone restored strong learning and made dynamic perturbation training beneficial instead of unstable.

This changed the interpretation of earlier failures: the dynamic data scheme itself was not necessarily the bottleneck; there was a substantial **backbone–augmentation interaction**.

ResNet-18-GN was therefore adopted as the public common backbone for the controlled ERM–JS comparison.

## 5. Convergence to a JS-only controlled comparison

After the backbone diagnosis, the main line was deliberately simplified.

Dynamic ERM and Dynamic JS were matched on:

- parent structures;
- two-view exposure;
- perturbation distribution;
- backbone;
- optimizer and training budget;
- checkpoint and evaluation rules.

The intended scientific difference became narrow and testable:

> Does explicitly using the known same-parent relation add value beyond ordinary label supervision when data exposure is otherwise matched?

JS consistency was retained as a simple implementation of that question. The project stopped treating "more algorithms" as progress.

## 6. From "robustness" to provenance-aware relationship supervision

The framing then changed again.

Calling the whole project "robustness research" described an important outcome but not the most distinctive method idea. The simulator does more than generate perturbed spectra: it retains **parent identity**.

For one parent crystal, multiple generated spectra are not merely samples with the same class. They are different measurements of the **same latent physical object**.

This led to the current chain:

~~~text
shared parent identity
      ↓
measurement equivalence
      ↓
relationship supervision
      ↓
prediction consistency
~~~

The simulator is therefore used as:

> **data generator + relationship supervisor**

This is the current method-level interpretation.

## 7. Frozen simulated evaluation

With the method and hyperparameter selection frozen through the validation protocol, the final simulated single-factor OOD comparison showed a consistent gain across five matched seeds.

Headline Test Macro-F1:

- Dynamic ERM: 0.65074 ± 0.00721
- Dynamic JS: 0.70534 ± 0.00977
- paired gain: +0.05460
- positive direction: 5/5 seeds

The largest perturbation-specific gains were observed for peak broadening and preferred orientation, motivating the interpretation that same-parent supervision is especially informative when the measurement change is strongly coupled to the concrete diffraction structure.

## 8. Experimental-domain evidence: RRUFF and CNRS

Two experimental domains were kept separate because they answer different questions.

### RRUFF-301: few-shot adaptation

RRUFF-301 tests whether the simulated pretraining is more label-efficient when a small number of real spectra are available.

At K=1/2/5 labels per class, the JS-pretrained model produced higher locked-test learning curves than the ERM-pretrained model. This is treated as **few-shot adaptation / label-efficiency evidence**, not unseen-mineral generalization.

### CNRS-318: zero-shot external-domain evaluation

CNRS-318 is a separate, naturally imbalanced zero-shot external-domain stress test. No CNRS label is used for adaptation.

Across five matched seeds, the relative Macro-F1 comparison favored JS in all five runs. Absolute scores remain low, and the structure-derived labels were not manually verified spectrum by spectrum, so this result is deliberately framed as supporting relative evidence rather than proof that the sim-to-real problem is solved.

## 9. Reporting-policy correction

Another important correction concerned evaluation standards.

The project initially treated strict statistical auditing too much like a binary gate. The reporting policy was later reorganized into three layers:

1. community-standard performance reporting;
2. probability-quality / reliability evidence;
3. strict paired and bootstrap uncertainty auditing.

Negative or uncertain statistics are retained, but a single cross-zero confidence interval no longer automatically erases an otherwise transparent multi-metric, multi-seed result.

## 10. Secondary inversion work

A separate xrd_inversion line studies numerical quantitative inversion. Its first structure–measurement factorization proposal received a preregistered **NO-GO** and was archived.

The surviving inversion module focuses on auditable forward-model and numerical-recoverability infrastructure. It is intentionally separate from the completed classification evidence.

## 11. 2026-10-08: prospective undergraduate thesis plan (not active research)

For future graduate applications, a possible undergraduate thesis direction was formulated: predict a limited set of structural and measurement parameters from PXRD; reconstruct a theoretical pattern with a forward physical model; then test whether a reconstruction-based **auxiliary** training constraint improves parameter accuracy, data/label efficiency, or training behavior under specific conditions.

This is not a claim of new work completed and not a return to the failed factorization Stage 1. In September 2026, the earlier 2×2 structure–measurement factorization intervention received an explicit preregistered **NO-GO**; the original prediction–forward-reconstruction idea also lost stand-alone novelty weight after related-work review. The new plan therefore explicitly studies **when physics helps and when it fails**, rather than promising improvement or silently reopening that archived experiment.

The conceptual path is now recorded as: provenance-aware PXRD classification (completed main line) → constrained physical parameter inversion (possible undergraduate thesis) → broader AI for scientific measurement, reconstruction and inverse problems (longer-term direction).

**Status:** FUTURE / CANDIDATE; see [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md).

## 12. 2026-10-13: revisit simulated parent-structure efficiency (planned, not run)

An earlier design for `10/25/50/100%` stratified nested training-parent subsets was restored to test the supervision-efficiency consequence of parent provenance. The unit of information is the **independent parent structure**, not synthetic spectrum count. Two-view Dynamic ERM and Dynamic JS (`lambda=60`) will be compared at identical parent, generated-view and optimizer-step budgets.

This design was previously deferred while the JS-only method was still being stabilized; revisiting it **after freezing the main method** now makes it a precise supplementary test. It does not change the original study, does not rerun RRUFF few-shot adaptation, and does not claim that equivalent performance has already been achieved with fewer parents.

The first task is code/data audit and matched fixed-step implementation, because the public epoch-based runner has partial-batch and per-epoch validation behavior that must not confound different parent budgets. The old simulated Test has already been evaluated; this new analysis will be explicitly post-main supplementary work.

**Status:** PROPOSED / NOT_RUN; protocol: [PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md](PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md).

## 13. 2026-10-18: pivot to calibrated pre-refinement assistance; coexistence as a safety boundary (proposed)

**Date / status:** 2026-10-18 / PROPOSED, NOT_STARTED. No new experiments, thesis approval or guaranteed real-data volume.

**Question / prior assumption:** The October 8 candidate framed undergraduate inversion primarily as direct continuous-parameter prediction aided by differentiable PXRD reconstruction. In subsequent discussions the prospective real spectra from a collaborator appeared likely to be scarce, so treating experimental data as the main training set was unrealistic. The candidate also oscillated between very narrow single-phase tetragonal regression and a much larger universal/multiphase ferroelectric project.

**New reasoning:** Retain simulation-trained modeling but focus on what a diffraction expert can actually use *before* conventional refinement: Top-K candidate single-phase structures, simulation-domain-calibrated candidate probabilities, phase-conditional lattice-parameter initializations and estimated intervals, plus forward-pattern checks. Limit the main 12-week scope to one selected ferroelectric ceramic family (family choice pending the collaborator's sample list). ECE concerns probability calibration over datasets; candidate probabilities do **not** represent constituent phase fractions.

**Decision / what changes:** A new [12-week pre-refinement plan](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md) specifies six biweekly milestones. Two-phase coexistence must be represented as a **risk to the single-phase assumption**, evaluated with plausible synthetic mixtures and a possible reject/review output. Explicit two-phase hypothesis testing is optional; quantitative phase fractions and broad multiclass/multimaterial models are future directions. Differentiable reconstruction loss is optional rather than obligatory; physics verification and refinement initialization are the central workflow.

**What does not change:** Completed `xrd_robustness/` frozen JS-only results, the older inverse numerical gates, the archived preregistered factorization NO-GO, and the historical October 8 plan. The new proposal is not an experimentally supported result.

## 14. 2026-10-18: candidate multi-family routing architecture (discussion, not adopted)

**Previous issue:** The latest 12-week project deliberately selects one known ferroelectric ceramic family to keep a simulation-trained, calibrated phase-hypothesis and parameter-initialization study executable; the user then suggested building separate simulation databases/experts for popular families (e.g., PZT, BaTiO3, KNN), with an upstream material-family decision.

**Reasoning/correction:** This is a plausible *modular extension*, but XRD-only inference of a sample's chemical family is not reliable in general for related perovskite ceramics; refinement workflows frequently have nominal sample composition available. Prefer a metadata-guided family router with an explicit unknown/mismatch/review option. Family-specific phase prototypes, simulators/parameter supports and calibration could use a shared interface; auto family recognition is a distinct optional inference problem.

**Decision status:** ARCHITECTURE CANDIDATE / NOT ADOPTED AS 12-WEEK MUST-DO / NO DATA OR MODEL RESULTS. Preserve one-family scientific MVP, allow a second-family configuration smoke only after core milestones. See [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md#9-新的前置构想多材料家族路由--分家族专家discussion--not-yet-adopted). The main frozen JS-only results and archived inversion NO-GO remain unchanged.

## 15. 2026-10-18: CrystalShift changes the forward-model framing (literature audit)

A literature check found a close, public physics-only precedent: Chang et al. (2025) CrystalShift already combines symmetry-constrained XRD lattice refinement, Bayesian probabilities for single- and multi-phase combinations, and forward-pattern model comparison **without a trained neural network**. Related work includes Lee et al. (2020) on simulation-trained multiphase CNNs and Dong et al. (2021) PQ-Net on physical parameter regression. Differentiable forward reconstruction itself also has related precedents in other diffraction modalities.

**Correction:** a pure Top-K classifier would marginalize the user's original forward-model insight; the project should keep forward modeling as a core inference-time physical validity/limited refinement step, with simulation generation as a second role. Training-time forward reconstruction loss remains an independent optional scientific test, not a mandatory contribution. The properly framed research opportunity is the *incremental value and limits* of learned candidate/parameter initialization on top of physics-based optimization, with physics-only, NN-only and hybrid comparisons.

**Status:** evidence-backed research framing correction / future candidate; no new experiments, no revision to frozen V9, no revival of archived factorization Stage-1. Detailed references: [PRE_REFINEMENT_FORWARD_MODEL_RELATED_WORK_20261018.md](PRE_REFINEMENT_FORWARD_MODEL_RELATED_WORK_20261018.md).

## 16. 2026-10-18: user re-prioritizes direct forward-reconstruction-loss training (proposal)

**Question / reasoning:** After reading CrystalShift as a physics-only strong baseline, the user challenged the conservative choice of leaving NN training-time Forward Reconstruction Loss as optional. The user originally wanted physics-model output to send meaningful learning gradients back to the neural network; post-hoc forward checking alone risks collapsing the next research task back into ordinary phase classification. This objection is scientifically sound.

**Candidate correction (not executed or finally approved):** Consider supervised phase/conditional-parameter inversion **with differentiable forward reconstruction loss as the primary candidate method**. Design a small-scope single-phase start; handle discrete class choices explicitly instead of assuming `argmax` differentiability; advance to physically plausible single/dual-phase hypotheses with carefully controlled scale factors and nuisance parameters only if forward correctness and identifiability hold. Compare supervised-only vs supervised-plus-reconstruction and physics-only. Prior work includes Chen et al. (2021) DRNets using reconstruction plus scientific constraint reasoning and CrystalShift (2025) probabilistic physics-only refinement; do not claim differentiable reconstruction itself is original.

**Why previous gating existed:** The current `xrd_inversion` report validates restricted known-tetragonal forward physics, not full mixed-phase differentiable models; previous local-capture and split-policy risks remain. The old archived paired factorization NO-GO **did not experimentally disprove** reconstruction loss in this new task. Train-only reconstruction can reduce spectrum residual yet fail to recover unique physical parameters.

**Status:** FUTURE / DESIGN CANDIDATE, NO NEW EXPERIMENTS. Appended for the user's application-purpose decision history without overriding the main 12-week planning document or frozen V9. See section added before W0 in [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 17. 2026-10-18: converge on a reference-workflow-led, single-intervention thesis direction

After successive expansions to multi-family routing, calibrated single/mixed-phase models, inference-time physical fitting, and train-time differentiable reconstruction, the user intentionally simplified the project: **follow a mature PXRD regression workflow (PQ-Net as practical reference), add and test a forward-reconstruction training constraint (DRNets as related physics-reconstruction reference), then demonstrate whether it helps on one ferroelectric ceramic material family**. The desired result is a bounded, reproducible scientific comparison rather than a universal autonomous Rietveld platform.

**Primary experimental contrast:** matched supervised parameter-regression NN vs the same NN with differentiable forward reconstruction loss; quantitative outcomes should include physical parameter MAE, spectral error, and refinement-initialization utility. Physics-only refinement (CrystalShift-type) is an external strong baseline where practicable. One family, initially known-phase/single-phase and valid CIFs, before considering physically supported coexistence cases. Small amounts of real collaborator data are reserved for independent cases, not relied upon for the main training set. Novelty must be tied to the tested result and task adaptation, not simply to using forward loss, which has prior art.

**Explicit de-scoping:** no mandatory 3-family routing model, broad phase-probability product, universal multiphase fractions, or feature-complete pre-refinement software in the 12-week core. Earlier discussions and competing approaches remain in their original dated entries for provenance; they are no longer equally weighted present implementation priorities.

**Status:** USER-SELECTED FUTURE RESEARCH PRIORITY, NOT_STARTED / NOT APPROVED / NO RESULTS. Do not overwrite existing V9 results or revive archived NO-GO. See the priority note in [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 18. 2026-10-18: PXRD AutoLab automation proposal

The user proposed automating repetitive experimental work after choosing a small, literature-based Forward Reconstruction Loss A/B study and a transparent biweekly reporting schedule. The new idea is an auditable engineering workflow: locked config, physics/split/budget gates, paired training, machine-derived metrics and figures, immutable manifests, and draft reports.

The first engineering step should be a minimal P0 (manifest, state machine, safe CPU smoke, reporting and tests), then a P1 scientific pilot, followed by optional GPU scheduling if an authorized worker is accessible. Scientific decisions and claims stay with researchers. No changes to frozen V9 evidence or archived Stage-1 NO-GO.

**Status:** PROPOSED / NOT IMPLEMENTED / NO NEW SCIENTIFIC RESULTS. See [PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md).

## 19. 2026-10-18: reconcile tiny one-parent pilot with possible multi-material horizontal extension

**Question:** The user chose option A (known-material/known-candidate PXRD continuous parameter inversion), but asked whether the mature PQ-Net-inspired workflow could be replicated horizontally across several materials, and whether the first Forward Reconstruction Loss pilot means reconstruction is useless or simply inaccurate.

**Evidence:** Draft PR #11 on `feat/physics-guided-pxrd-inversion-pilot` used a *single* known tetragonal HfCd structure and 512 simulated parameter realizations (358/77/77). Matched three-seed synthetic results: normalized two-coordinate parameter MAE A=`0.01495 ± 0.00327`, B=`0.01509 ± 0.00120`; clean transformed-profile RMSE A=`0.009008 ± 0.001868`, B=`0.008497 ± 0.000602`. Physical a/c MAEs were approximately 0.0003 Å/0.0015–0.0016 Å for this narrow simulator-matched task. Forward/gradient gate passed. Mean parameter benefit was **not demonstrated**; small mean reconstructed-spectrum improvement and mixed per-seed/parameter effects do **not** prove general failure of forward reconstruction, nor experimental accuracy.

**Possible scope adjustment (DISCUSSION / NOT ADOPTED):** Keep a single clear scientific question and one A/B protocol; once the collaborator's family is known, run separate matched experiments on that family, and *if capacity and reference CIF/physical validity allow*, replicate the **same** workflow on a second family (and optionally third) for cross-material evidence. Distinguish (i) independent family-specific expert models sharing a pipeline, (ii) a jointly trained family-conditioned model, and (iii) genuine unseen-family transfer: these are different claims with different splits; do not accidentally call independent per-family success zero-shot transfer. For any family/phase-specific forward, verify lattice symmetry, occupancies, structure factors, instrument metadata, gradients, identifiability, prototype-grouped splits and real-domain applicability. Avoid arbitrarily adding 14,060 heterogeneous CIFs: that was appropriate to the previous crystal-system classification question, not automatically to known-candidate parameter inversion.

**Current decision:** User explicitly prefers **A: known-family parameter inversion**. Multiple materials are a candidate way to broaden application breadth, *not yet a commitment to three fully trained material experts or a universal model*. Await family information and a bounded protocol; preserve PR #11 as method engineering evidence and frozen V9 untouched.

**Status:** SCIENTIFIC INTERPRETATION + FUTURE SCOPE DISCUSSION; NO NEW EXPERIMENTS. Reference: [PR #11](https://github.com/Frysland-2024/AI4science/pull/11), `xrd_forward_loss/FORWARD_LOSS_PILOT_REPORT.md` on its draft branch, and [12-week proposal](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 20. 2026-10-18: user proposes reusing V9 physical measurement perturbations in forward-guided inversion

The user proposed incorporating the previous V9 PXRD simulator's five physical measurement perturbations into the new known-material continuous-parameter inverse-model pipeline. This follows the narrow HfCd method pilot, in which only count noise plus linear background was added, reconstruction RMSE improved slightly but average parameter MAE did not.

**Scientific reason:** train the same A/B parameter-regression models on varied measurement realizations of the same physically labeled structure/parameter state, examining whether Forward reconstruction constraints help under credible instrument/texture/background/noise mismatch. Reuse source-grounded zero shift, width, March-Dollase preferred orientation, background and Poisson–Gaussian noise **without reviving old V9 scientific experiments or changing archived results**.

**Crucial correction:** in a lattice-parameter-only forward model, zero-shifted input peaks and other nuisance effects are not necessarily reconstructible by changing lattice parameters. Blindly minimizing `D(F(theta_pred), observed_noisy)` can *bias the structural parameters* to imitate nuisance. A valid next experiment must separate `theta_true`, `clean_profile` and `observed_profile`, then explicitly decide whether the new reconstruction target is clean simulation truth or an observed profile with modeled nuisances; it cannot just swap old NumPy functions into a differentiable path.

**Status:** DISCUSSION / FUTURE DESIGN CANDIDATE / NOT IMPLEMENTED / NO NEW RESULTS. The detailed engineering/science proposal is [FORWARD_LOSS_V9_PERTURBATION_REUSE_DISCUSSION_20261018.md](FORWARD_LOSS_V9_PERTURBATION_REUSE_DISCUSSION_20261018.md). The user has not yet approved a new formal experimental protocol; PR #11 remains an unchanged preliminary pilot.

## Current perspective

The project is no longer summarized as "a JS loss for XRD" or "an XRD robustness benchmark."

The current research statement is:

> **Use relationships known by scientific data-generation systems — here, simulator-retained parent provenance — as additional supervision for learning from scientific measurements.**

PXRD is the concrete test bed. The broader transferable idea is to identify supervision that already exists in a scientific measurement process but is normally discarded when observations are reduced to independent (x, y) pairs.


## 2026-10-18: parent-budget archival and explicit design/implementation distinction

The 2026-10-14 parent-budget experiment had completed in Cuifa01's implementation/execution branch but remained outside main due to branch divergence. The results and implementation were integrated without overwriting newer independent developments. The research lead clarified the historical division of labor: Frysland-2024 originated and led the study's scientific framing, simulated OOD and RRUFF/CNRS real-domain experiment design, and the parent-budget learning-curve design; Cuifa01 participated as an engineering implementation/execution collaborator, including desktop GPU training and artifact preparation. This clarification is a statement of research roles, not a rewrite of commit metadata or a final publication authorship ruling. The experimental outcome shows higher JS Macro-F1 at all four matched parent budgets but no demonstrated parent-count reduction. See the preserved full [supplement report](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).


## 2026-10-18: further correction to the attribution of scientific design and supporting work

The project lead clarified that the prior research-role descriptions were still too narrow and insufficiently explicit: **the scientific approaches and project-level plans were principally designed and directed by Frysland-2024 throughout the project's evolution**, not merely for isolated later experiments. This includes framing and redirecting the research, choosing and planning evaluation protocols, designing the simulated OOD, RRUFF, CNRS and Data Efficiency/parent-budget studies, and interpreting the results. Cuifa01's primary role was **participation in carrying out those plans**, alongside **auxiliary idea suggestions, feedback, data gathering/organization, code implementation, computing and experiment operations**, including the desktop GPU work.

The distinction is between **principal research design and planning** versus **supporting intellectual input and execution**. It does not erase the collaborator's execution or suggestions, change the historical Git record, or prejudge formal manuscript authorship. The earlier 2026-10-18 entry remains as a historical record of the first attribution clarification; this entry records the later, more complete correction explicitly rather than silently rewriting history.

## 2026-10-23: Converge on three headline metrics for the crystal-system extension

**Previous assumption / question:** After exploratory quantitative PXRD inversion did not mature into a stable real-domain result, the lead prioritized returning to seven-crystal-system classification. The October 22 supervisor discussion underscored the need for credible *absolute* measured-RRUFF performance against published systems, not only internally matched JS-versus-ERM gains. A scale-up task was opened for independent simulated parent structures.

**Decision (explicit, 2026-10-23):** Exactly three next-stage headline evaluation axes:
1. **RRUFF real-domain leaderboard** — primary zero-shot crystal-system Accuracy, with Macro-F1 and same-test-set published model comparisons.
2. **Confidence calibration** — ECE and reliability, with NLL/Brier as complementary probability scores.
3. **Simulated parent-structure data efficiency** — classification performance versus number of distinct simulated training structures, with matched ERM/JS training budget.

**Why these three:** They respectively answer whether a model *performs*, whether its expressed uncertainty is *trustworthy*, and whether parent-relationship supervision improves the *use of structure data*. This response targets both measurement-facing practical value and the lead's original simulator-provenance method idea.

**What changes:** The next-stage presentation, scaling work and external evaluation prioritize these three axes. RRUFF published benchmark numbers are only reference lines unless protocols/sample IDs are matched. The RRUFF zero-shot and prior K=1/2/5 few-shot tracks must never be conflated; probabilistic calibration requires a declared evaluation domain.

**What does not change:** All frozen historical V9, CNRS and RRUFF experiments and negative/uncertain results stay untouched. A completed 984/2460/4921/9842 parent-budget study demonstrated positive same-budget JS gains but explicitly did **not** establish a statistically supported count of saved parent structures. Residual and parameter-inversion branches remain part of the honest chronology, not newly reactivated.

**Status:** ACTIVE RESEARCH PRIORITY / PLANNING, NO NEW GPU OR LITERATURE-ALIGNED RUN CLAIMED. See [current scientific state](CURRENT_STATE.md) and [scaling task](https://github.com/Frysland-2024/AI4science/issues/49).

## 2026-10-23: CNRS becomes an optional secondary real-domain result

**Previous assumption:** The 2026-10-23 three-pillar evaluation design already made RRUFF the primary real-domain benchmark, but CNRS remained a possible secondary external-domain figure.

**User decision:** Explicitly deprioritize CNRS. Focus the new scale-up and published-paper comparison on RRUFF; CNRS is optional for the headline slides and is not a required fourth research objective. The user expressed a preference to show CNRS when it looks good and omit it otherwise.

**Research-integrity correction:** A result-dependent decision to hide already-run unfavorable tests could bias the scientific record. The appropriate distinction is between *narrative priority* (RRUFF headlined, CNRS optional or supplementary) and *evidence transparency* (retaining and accurately citing all completed material evaluations, including negative/weak results where relevant to generalization claims).

**Existing evidence:** CNRS-318 zero-shot five-seed paired Macro-F1 improves about +0.0187; pooled Macro-F1 0.1912→0.2091, Accuracy 0.2000→0.2101, ECE 0.6826→0.6124. Absolute task performance remains low, and the paired-parent strict CI spans zero. Preserve that distinction.

**What changes:** New training/acquisition/benchmarking work is not required to include CNRS unless justified. Core evaluation themes remain RRUFF running score, ECE, and simulated parent-data efficiency.

**What does not change:** CNRS artifacts, frozen predictions, original result reports, historical analyses and source disclosures must remain unmodified; future papers must not claim comprehensive real-domain generalization by omitting material counterevidence.

**Status:** ACTIVE SCOPE CHANGE / NO NEW EXPERIMENT. See [current state](CURRENT_STATE.md), [CNRS report](../xrd_robustness/reports/CNRS_318_RESULTS.md).

## 2026-10-23: Upgrade measurement simulation before reselecting large-data hyperparameters

**Previous assumption:** After prioritizing seven-crystal-system classification, three headline evidence pillars were fixed (RRUFF real-domain scores, ECE, independent-parent simulated-data efficiency). The initial expansion plan concentrated on acquiring many more CIFs and applying the established V7 online perturbation pipeline.

**New reasoning and user decision:** The project lead identified two prerequisites: borrow from a more comprehensive **dynamic physical simulation** framework, then revisit optimizer/training settings once far more independent structures become available. The rationale is that simulator fidelity and data scale both change the learning task; old parameters, especially the chosen JS λ and fixed optimizer-step budget, may no longer be appropriate.

**Source and implementation observation:** Existing V7 already has global 2θ shift, reflection-aware March–Dollase, Gaussian broadening, smooth/GP background and Poisson/electronic noise. SimXRD/Pysimxrd offers additional size-dependent line profiles, thermal and geometry effects; however code/source inspection shows that its default pymatgen path does not pass the public `zero_shift` argument and unconstrained random lattice shear can threaten seven-system label preservation. Thus the plan is **selective, verified reuse**, not wholesale copying. The 2026 Kikkawa et al. industrial-XRD augmentation study supplies a complementary real-measurement perspective.

**What changes now:** Implement a versioned simulation extension, validate it cheaply against the old simulator on equal structure/compute budgets, and choose a limited validation-only search for LR/scheduler/batch/training exposure/λ before the large-scale matrix.

**What does not change:** The old frozen V7/V9 scientific evidence, RRUFF-301 70/231 protocol, and the three core evaluation axes remain untouched. This is a design decision, not evidence that implementation or new training has been completed.

**Status:** ACTIVE NEXT-STAGE DESIGN / NOT IMPLEMENTED. [Implementation plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md) and [Issue #49](https://github.com/Frysland-2024/AI4science/issues/49).


## 2026-10-23: formal return to seven-crystal-system classification

**Project path:** FerroAI and earlier materials-ML work led into PXRD as a scientific measurement problem; the PXRD study then developed into a controlled method investigation of simulator-retained same-parent identity and relationship supervision. A subsequent exploration tested whether PXRD spectra could support quantitative lattice/measurement-parameter prediction through supervised inversion, Forward Reconstruction Loss, DONUT-inspired reasoning, and automated/refinement-assisted workflows. Those proposals and numerical feasibility results did not establish a stable, validated real-domain parameter-inversion study. On 2026-10-23 the project lead formally returned the sole active scientific task to **machine-learning-based PXRD seven-crystal-system classification**.

**Current plan:** Only three evaluation axes are active for planning: (1) RRUFF real-domain zero-shot Accuracy and Macro-F1 with matched-condition comparisons to Lee (2023), SimXRD-4M (2025), and XQueryer-NoElem (2025); (2) confidence calibration, led by ECE with NLL/Brier/reliability diagrams supporting; and (3) simulated-data efficiency by unique training-parent count under matched Dynamic ERM/JS budgets. CNRS remains optional secondary-domain evidence. See [CURRENT_STATE.md](CURRENT_STATE.md) and the [2026-10-23 scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).

**Technical order:** First audit independent structure availability and develop a versioned online simulator with physically defensible, label-preserving paired views. Then retune training settings against synthetic development evidence. Only after data and simulation stabilize may ResNet-18-GN be compared conditionally with SimXRD CNN11 or an optional multi-scale 1D CNN. These are future plans, not implemented work.

**Archived / Inactive:** Quantitative parameter prediction, lattice-parameter recovery, Forward Reconstruction Loss, DONUT-inspired workflows, automatic refinement, and the ferroelectric pre-refinement candidate. Their code, completed numerical checks, failures, reports, citations, and prior authorizations remain in the repository as historical evidence. No historical issue or detailed proposal can reactivate them.

## 2026-10-26: narrow the undergraduate thesis; archive parameter inversion

**Date:** 2026-10-26

**Question / previous assumption:** The 2026-10-23 decision treated classification scale-up through a new RRUFF zero-shot comparison, calibration, and parent-data efficiency as the active next stage. In parallel, PR #46 recorded a partial multi-architecture synthetic lattice-parameter inversion benchmark.

**Evidence and reasoning:** PR #46 completed primary synthetic scoring for 42 models and 8,085 records, but the q-accuracy gate passed 0/42; the per-DOF cell-MAE constraint passed 41/42. The parent test set had already been opened in PR #43, so the benchmark is exploratory rather than independent confirmation. New-architecture stress was not run, and real RRUFF validation was blocked/not run. The benchmark did not establish consistent neural accuracy gain, real-domain validity, or an exact reproduction of the cited methods. The existing classification study has a bounded, reportable research question and frozen comparative evidence.

**Decision:** The sole current undergraduate thesis line is to write up and defend the completed PXRD seven-crystal-system classification study: test whether same-parent measurement-equivalence supervision improves classification over matched Dynamic ERM. No new experiments are in current thesis scope. Parameter inversion, including PR #46 and its associated routes, is **ARCHIVED / INACTIVE**. The 2026-10-23 classification scale-up plan is **DEFERRED**, not an active task or thesis acceptance gate.

**What changes now:** README, current state, supervisor brief, agent contract, and the scale-up plan status are aligned to the 2026-10-26 thesis scope. PR #46 is closed unmerged; Issue #44 is closed as not planned; Issue #49 is closed as deferred/not planned. Their original text and the PR artifacts remain available as historical records.

**What does not change:** Frozen classification splits, configurations, scores, reports, code, and the negative/uncertain evidence remain unchanged. PR #46's completed metrics remain descriptive exploratory evidence; its incomplete gates are not being rerun, and no new experiment is started.

**Status:** CURRENT THESIS SCOPE / PARAMETER INVERSION ARCHIVED / SCALE-UP DEFERRED.

**Relevant records:** [current state](CURRENT_STATE.md), [README](../README.md), [supervisor brief](START_HERE_FOR_SUPERVISORS.md), [deferred scale-up proposal](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md), [PR #46](https://github.com/Frysland-2024/AI4science/pull/46), [Issue #44](https://github.com/Frysland-2024/AI4science/issues/44), [Issue #49](https://github.com/Frysland-2024/AI4science/issues/49).

## 2026-10-27: final parameter-inversion evidence boundary

This note reconciles the current GitHub state of PRs #36, #42, #43, #45, and #48 with the 2026-10-26 thesis decision. The sole current undergraduate thesis remains the frozen seven-crystal-system classification study; this update does not reopen inversion work or authorize experiments.

**PR #36 — completed conditional synthetic evidence.** The four-stage study is marked COMPLETE in its final technical report, but the PR is currently closed and unmerged. It used one known COD 9014273 tetragonal BaTiO3 CIF, 512 parameter parents split before perturbations into 358/77/77, three model seeds, and 77 held-out parents per seed. In Exp 4, direct normalized-q MAE was 0.033607/0.033578/0.034282 for A/B/C and 0.228037 for DONUT-PXRD. The same bounded joint q+instrument L-BFGS-B refinement yielded 0.000343/0.000350/0.000341 for A/B/C and 0.080026 for DONUT-PXRD. Thus the roughly 0.00034 values are post-refinement results, not neural outputs; A/B/C are effectively tied after the same optimizer. Exp 1/2 and the four Exp 3 conditions are separately reported in the final report and must not be collapsed into the Exp 4 headline. Retain PR #36 as feasibility evidence conditional on this exact known-CIF synthetic setup only. It does not establish real-measurement accuracy, unseen-CIF/composition transfer, multiphase capability, general PXRD inversion, or broad method superiority. The adaptation of a 2D SXDM method to 1D PXRD also does not test or invalidate the original DONUT method. The report includes metric provenance, but model checkpoints and generated arrays are local-only.

**Related branches and source precedence.** Current GitHub state shows PRs #42, #43, and #45 as closed and unmerged; their branches are historical, not current execution queues.

- **PR #42:** decision/journey documentation, not an additional experiment. Its compact DONUT summary lists values (including Exp 1 ≈0.3162 and Exp 2 ≈0.3313) that conflict with PR #36's final report (0.344228 and 0.398342). Use PR #36's final technical report as the numerical source for that study; do not merge the conflicting digest into canonical claims.
- **PR #43:** completed a bounded supported subset of a synthetic cross-CIF pilot (seven templates across three crystal systems; not seven systems). In the primary study, N+A q-MAE was essentially tied with three-start P3; P0 was comparably accurate on five materials but had larger errors on MgO and ZnO. Its separately registered post-primary renderer/peak-shape/background stress test used 16 new parents per material and found no added accuracy or reliability over P0/P3. Neither result establishes unseen-material transfer or real-measurement performance.
- **PR #45:** E1 is complete but no material met the preregistered incremental-value criterion against H1/P0. E2 is **PHYSICS_NOT_READY / NN_NOT_RUN** for three RRUFF rutile profiles; it contributes no neural real-domain validation. The PR body says “open,” but the current GitHub state is closed/unmerged.
- **PR #48:** merged to main on 2026-10-20; it established supervisor-facing classification materials, not parameter-inversion evidence.

**Claim disposition.** Keep PR #36's direct and refined metrics only with the single-CIF synthetic condition attached. Do not present the post-refinement score as direct neural accuracy; do not claim broad robustness, real-XRD validity, cross-material generalization, multiphase solving, neural superiority over strong physical methods, or reproduction of the cited literature systems. Retain PR #43/#45 E1 as completed exploratory comparisons with their negative/limited result, PR #45 E2 as a failed readiness gate with no NN run, PR #42 as historical documentation with a stale numeric summary, and PR #46 as a separate partial benchmark whose q-accuracy gate passed 0/42. The 2026-10-26 classification-only thesis decision remains in force.

**Primary source:** [PR #36 final technical report](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-experiment-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md); related records: [PR #36](https://github.com/Frysland-2024/AI4science/pull/36), [PR #42](https://github.com/Frysland-2024/AI4science/pull/42), [PR #43](https://github.com/Frysland-2024/AI4science/pull/43), [PR #45](https://github.com/Frysland-2024/AI4science/pull/45), [PR #48](https://github.com/Frysland-2024/AI4science/pull/48).

## 2026-10-29: PR #50 documentation sync

PR #50 was merged into `main` on 2026-10-29 (merge commit [`6e4dd70`](https://github.com/Frysland-2024/AI4science/commit/6e4dd70a7134427fc9c8a04b686dce5e20ea6727)). It synchronized `README.md`, `docs/CURRENT_STATE.md`, this history, and `docs/START_HERE_FOR_SUPERVISORS.md` around the existing evidence boundary: PR #36 remains feasibility evidence for one known BaTiO3 CIF under one frozen synthetic setup; its approximately 0.00034 normalized-q MAE values are post-refinement scores, not direct neural outputs; and the 1D DONUT-PXRD adaptation does not test or invalidate the original 2D DONUT method. This was a documentation-only reconciliation: no experiment or result was added, and the 2026-10-26 classification-only undergraduate-thesis scope did not change. See [PR #50](https://github.com/Frysland-2024/AI4science/pull/50).

## 2026-11-03: explicit thesis restart and simulator-first JS performance route

**Question / previous assumption:** On 2026-10-26 the undergraduate-thesis work had been frozen for writing/defense only. The prior October 23 proposal for bigger CIF datasets, more realistic simulators and RRUFF literature benchmarking had been deferred. Recent discussion revisited the supervisor's expressed interest in published-model performance and absolute RRUFF experimental accuracy.

**Evolution of the lead's reasoning (2026-11-03 discussion):**
1. Reject a blanket **zero-shot** target when a target paper used real RRUFF examples for training or fine-tuning: compare each paper under its own disclosed real-data protocol instead. Full replication of the published network is not required for literature-referenced scoring.
2. Prefer **Dynamic JS only for the new exploratory performance run**; older ResNet-18-GN ERM vs JS evidence already exists and is preserved.
3. Ask whether synthetic-data scale should be matched. Clarify that **unique CIF parent count**, not arbitrarily numerous re-rendered spectra, is the meaningful structural dataset axis. Do not pick 30k/60k/100k out of habit or match every paper's total database count mechanically; first audit real training CIF count and availability.
4. Observe that papers with apparently larger structural datasets do not necessarily report higher RRUFF Accuracy, but note **dataset and evaluation protocols differ**. Thus data size alone is a poor selection rule; examine **both simulator implementation and CNN backbone**.
5. State the priority explicitly: **a clear improvement in absolute experimental-data Accuracy** is the immediate engineering success criterion, not a large factorial ablation study.
6. Narrow the immediate action again: **first understand and selectively borrow existing simulators**; after that, run a small same-CIF JS backbone comparison against the old ResNet-18-GN+JS, and only then consider large-scale training.
7. Request a broader shortlist: GSAS-II, ML4pXRDs, PhaseSmith, DebyeCalculator, PowderLine and xrd_simulator alongside SimXRD/Pysimxrd; prefer modules that can be reused, repair simple verified problems, and reject components that violate seven-system label preservation.

**NEW DECISION:** The lead expressly confirmed that **the undergraduate thesis has restarted**. Simulator source investigation, careful module selection and the subsequent bounded JS-only comparison are therefore an **active forward research direction**. The earlier 2026-10-26 *no new experiments* operational pause is superseded, while old results remain frozen as historical evidence.

**What changes now:** [CURRENT_STATE.md](CURRENT_STATE.md) is updated; [simulator candidate inventory](PXRD_SIMULATOR_CANDIDATES_2026-11-03.md) records priorities, evidence status, and next-source-audit deliverable. Initial effort is research/source review, not a claim of newly executed training or scientific validation.

**What does not change:** Existing ERM/JS comparisons, fixed splits, uncertainty caveats, project contribution history and archived parameter-inversion work. Published RRUFF percentages from unmatched sample selections are literature references rather than fair matched head-to-head results.

**Status:** ACTIVE THESIS / SIMULATOR INVESTIGATION FIRST / NO NEW TRAINING RESULT YET.


**2026-11-03 execution-order clarification (project lead):** "先抄明白模拟器，再比较架构" — first understand the external simulator code thoroughly, select and validate useful components as a working, versioned simulator; only **afterwards** compare architectures with the same JS objective. Architectural experiments are not to be launched concurrently with the simulator audit. This sharpens, without replacing, the restart decision above.

**2026-11-03 execution-deliverable correction:** The lead rejected a Phase-1 deliverable consisting only of a simulator audit/report: **“我不要什么报告，我要成品”**. The Phase-1 contract is now working code (versioned PXRD simulator, compatible JS paired-view pipeline, runnable CIF→paired-spectra CLI, tests and example outputs). Upstream source understanding is required to build it, not an independent endpoint. Issue [#54](https://github.com/Frysland-2024/AI4science/issues/54) is the specific Codex-ready implementation specification. At this conversation, the laptop Desktop Commander connection was offline, and the old bridge coding lane explicitly blocked `xrd_robustness/` edits, so creating Issue #54 is **not evidence that Codex executed or that the simulator exists**. No new model architecture trial is authorized until simulator acceptance.

**2026-11-03 implementation-deliverable clarification:** The project lead rejected a research report as Phase 1 output and explicitly requested a *finished, runnable simulator*, built by selecting useful upstream components and validating their integration with current same-parent JS. Implementation task [Issue #53](https://github.com/Frysland-2024/AI4science/issues/53) specifies acceptance tests. No execution is claimed while local Codex machine is disconnected and the legacy bridge code lane forbids core simulator writes.

**2026-11-03 ResNet hyperparameter clarification (owner):** The lead explicitly noted that because the existing ResNet-18-GN was itself borrowed from ML4pXRDs, its *architecture hyperparameters* should not be treated as fixed or optimal for the updated simulator. New sequence: **finish simulator → retune existing ResNet+Dynamic JS architecture (especially heavy downsampling/kernel size) and optimization (LR/scheduler, JS lambda, exposure budget, regularization) → compare fairly with CNN11+JS → consider larger CIF scale and real RRUFF benchmarks**. The old backbone and its frozen experiments remain valid historical references; the new comparison has not been run. Models should receive comparable bounded tuning opportunities, with held-out RRUFF tests reserved for evaluation rather than hyperparameter selection.

**2026-11-03 decision refinement — purpose of V10 and what follows (project lead):** The lead rejected describing V10 mainly as a simulator-vs-simulator test. V10 is the **fixed shared simulation environment** for a simple question: *is replacing the existing ResNet with CNN11 worthwhile?* The lead believes the V10 three-condition outcome is sufficient for this initial decision, and does not want another full backbone sweep. Once V10 results and the planned terminal evaluations are complete, prioritize **Codex's automatic retuning of the existing ML4pXRDs-derived ResNet + Dynamic JS** instead of spending compute on more architecture comparisons. The priority is practical RRUFF absolute performance through an improved, validated simulator and bounded hyperparameter tuning. Code/experiment instructions are queued in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). At this point the three ResNet V10 runs are complete locally and CNN11 V10 training is still in progress; no final verdict or ResNet-retuning result is claimed. This changes an earlier assumption about experimental ordering and should be preserved for future project-development statements.

## 2026-11-03: final clarification — hyperparameter tuning belongs within architecture optimization

**Owner correction and reasoning (chronological):** The lead objected to the assistant's repeated reordering of the project into simulator → immediate ResNet tuning → data and to the later mistaken correction that *deferred* hyperparameter tuning until after dataset expansion. The lead emphasized **“现在要保证做的每一步都是有意义的”** and **“调参本身就是架构优化的一部分”**. These statements refine the scientific logic, not merely a task list.

**Authoritative progression:** (1) Simulator development: engineering task completed, with V11 acceptance evidence (separate PR merge housekeeping); (2) **model architecture optimization as a single stage**: ongoing V10 ResNet-vs-CNN11 screening decides whether to replace the backbone, **followed by autonomous bounded architecture/training hyperparameter tuning of the selected model**, with same-parent Dynamic JS, validation selection and no blind second architecture sweep; (3) build more **unique, valid CIF parent structures**, with class coverage, provenance and deduplicated parent-disjoint splits; (4) run final model training and **RRUFF real-domain literature benchmarking** under comparable disclosed evaluation/real-label-access protocols. Do not confuse V10's screening purpose with a competition between simulator versions.

**Evidence / risks at correction time:** all three existing V10 ResNet seeds completed locally. The CNN11 V10 seed-1 training log showed CE and JS become NaN from ~20,000 steps, invalidating any premature architecture ranking until diagnosed and repaired. No stage-2 tuned checkpoint, larger-CIF dataset or final RRUFF result is claimed. [#60 architecture screening](https://github.com/Frysland-2024/AI4science/issues/60) → [#55 automatic tuning within the same stage](https://github.com/Frysland-2024/AI4science/issues/55) → [#61 expanded CIF data build](https://github.com/Frysland-2024/AI4science/issues/61) → final RRUFF benchmarking. Earlier chronological proposals remain historical and **do not supersede this latest owner clarification**.

## 2026-11-03: SimXRD ML methodology inspires focused ResNet tuning

**Project-lead proposal:** Instead of treating SimXRD solely as a source of simulator physics or replacing ResNet wholesale with CNN11, study **the machine-learning benchmark part of Cao et al.'s SimXRD-4M (ICLR 2025)** as a principled source of *ideas for optimizing the retained ResNet*. This is a methodologically meaningful refinement of Stage 2 (architecture choice plus hyperparameter optimization), not a new phase and not license for blind parameter sweeping.

**Source-based specifics:** SimXRD benchmarked 21 sequence models, used shared batch=128, LR=2.5e-4, up to 50 epochs with early stopping (patience 3), investigated pooling/downsampling, and compared class weighting, label smoothing and focal loss for long-tail symmetry data. Source: https://openreview.net/pdf?id=mkuB677eMM Sections 4.2–4.3. These hyperparameters are **not defaults to copy** into our 8GB GPU online paired-view JS training. Real application requires data-protocol and loss-composition adaptation. Our local ML4pXRDs-derived ResNet presently couples stage stride 4 + kernel 9 in a single Boolean; separate these for targeted, interpretable development experiments. Targeted order: stride/kernel design -> LR/schedule/validation early stopping -> optional smoothing/focal if seven-class imbalance indicates -> targeted JS lambda gradient balance -> selected checkpoint replication. Paper did not use same-parent JS; that part is our own adaptation. Details in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). V10 CNN11 NaN repair and valid architecture verdict remain prerequisites; no new training started by this literature-inspired decision.

## 2026-11-03: direct, non-Codex launch of paper-guided ResNet A1

**Problem:** Codex quota was exhausted while the next architecture-optimization stage remained actionable. The project lead explicitly asked whether ChatGPT could start the experiment directly. **Execution decision:** use authorized Desktop Commander to launch an independent, versioned Python training script with the existing V10 simulator and ResNet+Dynamic JS trainer; do not require Codex or overwrite the dirty root. **Actual proof of start:** local PowerShell session PID 10936 on RTX 4060, source `E:\AI4science\_local\run_resnet_guided_a1_20261103.py`, model shape test passed, training-start event and first finite step recorded. **Hypothesis:** in light of SimXRD's emphasis on peak-information retention, isolate less aggressive residual-stage downsampling (stride transitions 4/4/4 to 4/2/4, residual kernel 9 unchanged), holding existing 14,060 CIF split, V10 simulated spectra distribution, online same-parent JS λ60, LR 1e-4 and batch 16. Changes to head dimension increase model count from ~13.01M to ~14.84M and must be accounted for. **Bounded pilot:** one seed 20260711 for 12,320 steps, validation at fixed 6,160 and 12,320 steps, selecting on Validation OOD Macro-F1 only; prior ResNet V10 same-seed checkpoints provide the direct comparison. Reports and outputs are in new `xrd_robustness/reports/resnet_simxrd_guided_A1_20261103/` and `xrd_robustness/outputs/resnet_simxrd_guided_A1_20261103/`. [Execution evidence / discussion](https://github.com/Frysland-2024/AI4science/issues/55). **Status: STARTED, NOT CLAIMED COMPLETE.** No full-budget final performance/real RRUFF result, no automatic full tuning campaign has been completed. Original simulator and CNN11 instability evidence remain unchanged.

## 2026-11-03: Codex-free A1→A2 autonomous ablation and GitHub evidence handoff

**User decision:** After the direct-launch SimXRD-inspired ResNet A1 trial, the user asked not only to monitor its completion but to **automatically continue to A2 and upload an end-to-end evidence-backed conclusion to GitHub**, without using exhausted Codex quotas. This extends the previous one-shot handoff into a bounded, sequential experiment runner; it is not a new research stage.

**Hypothesis and experimental constraints:** A0 historical V10 ResNet = residual stage-transition strides (4,4,4), kernel9; A1 = strides (4,2,4), kernel9; A2 = strides (4,2,4), kernel5. The V10 simulator, 14,060-parent split, Validation panels, same-parent Dynamic JS λ60, LR1e-4, batch16 and seed 20260711 are fixed. A1 and A2 are **12,320-step single-seed screens**, not 49,280-step replicated claims. Changing kernel in A2 also changes parameter count (A1 ~14.84M; A2 ~9.96M), so interpretation needs careful compute/capacity disclosure. Select based on Validation OOD Macro-F1 only; do not tune on previously inspected RRUFF-70 or Test.

**Execution evidence and safeguards:** The direct local A1 job was still running (at 6,160-step Validation OOD Macro-F1 0.589445; matched historical A0 0.575300). A2 source `E:\AI4science\_local\run_resnet_guided_a2_20261103.py` passed syntax and 7-logit model-shape tests. A new **running** supervisor `E:\AI4science\_local\supervise_resnet_a1_a2_20261103.py`, initial session PID 30608, checks A1's completed training JSON and hashed checkpoint, then starts only one A2 GPU job, verifies A2 evidence, generates A0/A1/A2 summary and report, and uses locally authenticated `gh` to create a GitHub experiment branch plus PR without modifying the dirty root checkout. Separate hourly automation `A1训练完成与Git归档` serves as notification/fallback and was updated to follow both trials. The code preserves failed runs and refuses overwrites or concurrent duplicate jobs. [GitHub Issue #55 execution handoff](https://github.com/Frysland-2024/AI4science/issues/55).

**Status when recorded:** A1 underway, supervisor running; A2 had **not yet begun**, GitHub results PR and final performance conclusions **not yet available**. All final claims must depend on verified completion artifacts and PR links, not a task's existence. If no improvement emerges, that negative result is retained rather than running unbounded searches.

## 2026-11-03: Owner explicitly finalizes three-tier RRUFF performance acceptance and 3 headline outcomes

**Prior misunderstanding corrected:** The AI assistant repeatedly reinterpreted the earlier literature comparison as an invented grade scheme (first replacing the owner's chosen paper set with AlphaDiffract as the sole 80-point benchmark and SimXRD alone as full score, then excluding Salgado). The owner clarified the exact grade grouping and that the literature-comparison sheet should remain simple: paper/model, unique simulated structure count, number of real RRUFF evaluation spectra, seven-class RRUFF Accuracy, and number of labeled real RRUFF adaptation samples. Maintain this original intent rather than inventing extra criteria.

**Final owner decision:** **Pass/60 = Lee 2023 (74.24% RRUFF Accuracy); 80 = Salgado 2023 (86%, ~452 labeled real RRUFF training) AND AlphaDiffract 2026 (81.74 ± 0.78%, 734 RRUFF classification cases, 0 labeled RRUFF training; AlphaDiffract is the PRIMARY newer reference); Full/100 = SimXRD-4M 2025 CNN11 (89.3%) AND XQueryer-NoElem 2025 (91.5%).** This is a tiered literature target set, not a strict numerical conversion from Accuracy to grade, nor a claim that all papers have matched evaluation cohorts. The user additionally insists that the overall work have only three headline outcomes: **RRUFF real-data Accuracy** (the sole grade driver), **unique-parent data-efficiency curve**, and **ECE calibration**; simulation validation metrics remain internal/model-development support.

**Why this matters for the project narrative:** The lead wants a straightforward **industrial/benchmark-style competitive-performance objective** with transparent data scale and target-data adaptation budgets, not increasingly complicated criterion engineering or substitute simulated scores. The 80 tier intentionally includes both a legacy target-adapted model and a newer large-data ensemble; disclose protocol differences honestly. No change to frozen old results or permission to train on locked real test spectra. Canonical scorecard now lives in `docs/RRUFF_REAL_DOMAIN_LITERATURE_BENCHMARK_2026-10-22.md`, and the authoritative project objective is summarized in `docs/CURRENT_STATE.md`.

## 2026-11-03: RRUFF data curation becomes an explicit benchmark reproducibility question

**Owner insight:** After comparing Lee 2023, Salgado 2023, AlphaDiffract 2026, SimXRD-4M, and XQueryer-NoElem, the research lead challenged an implicit double standard: published methods explicitly curate/filter real RRUFF test datasets, so **our study may also use a scientifically justified, auditable selection protocol**, rather than holding itself uniquely to all raw/invalid spectra. The issue is to distinguish data completeness/physics-based quality screens from post-hoc performance cherry-picking. The lead asked for source-by-source verification of each RRUFF cohort rather than speculative attributions of Bin Cao's high score to network design or favorable data filtering.

**Verified research correction:** Lee explicitly removes the top 40% in a low-angle (5–8°) background-STD ranking; AlphaDiffract filters 1,362 corrected spectra and DIF-derived cell/space-group/lattice metadata down to 734 valid classification entries (59 derived computationally from single-crystal patterns); Salgado's 86% used approximately 452 labeled RRUFF entries for training and a roughly half-sized held-out test; XQueryer's paper reports 3,002 → 1,003 and Bin Cao's accompanying thesis documents 2,088 ID-matched XY_RAW+DIF profiles, excluding incomplete measurements/lattice metadata to reach 1,003, while 849 separate MP structure matches support the different *structure identification* task. Original public matching files independently contain 849 distinct paired IDs. **SimXRD-4M Table 5's exact RRUFF ID set and denominator remain unknown**; one cannot assume either 3,002 or XQueryer's 1,003. These different cohorts prevent a strict performance ranking without shared IDs and preprocessing, but provide legitimate *paper-inspired* curation templates.

**Resulting plan, not an executed RRUFF experiment:** preserve historical locked panels; for a prospective cohort create versioned, label/coverage/quality-motivated RRUFF selection rules and an audit manifest **before** measuring accuracy; separately report clean-paper-like and harder broad panels when useful; no HPO on RRUFF locked test. The complete five-paper primary-source and release-file verification is in [RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md). This adds benchmark reproducibility discipline, not a new scientific research pillar or change to the owner-frozen 60/80/full RRUFF Accuracy, unique-parent data efficiency, and ECE outcomes.

## 2026-11-03 — Final zero-shot-only acceptance correction (Salgado moved to pass)

**New owner decision:** Project performance grades are **strictly based on zero labeled RRUFF training/fine-tuning**. The owner explicitly rejected using Salgado 2023's **86% Large Souping** result for grading, because that model trained with about **452 labeled RRUFF spectra**. Instead use Salgado's **synthetic-only NPCNN zero-shot RRUFF Accuracy approximately 74%**, assign it to the **PASS / 60 tier alongside Lee 2023 (74.24%)**. The **80 tier now comprises AlphaDiffract 2026 (81.74 ± 0.78%), PRIMARY**; **FULL / 100 comprises SimXRD-4M 2025 CNN11 (89.3%) and XQueryer-NoElem 2025 (91.5%)**.

**Interpretation:** 'Zero-shot' for comparison denotes **zero labeled real RRUFF training/adaptation examples**. AlphaDiffract consulted RRUFF noise statistics and paper RRUFF scores in development, so the published result is zero labeled adaptation but not completely target-domain-blind; this qualification must accompany its 80-tier primary status. The 86% Salgado 452-labeled setting is retained in the historical evidence table but is not eligible for acceptance. Absolute published test cohort sizes/processing differ; they remain reference markers unless aligned. Model tuning must not use the locked RRUFF test. The scientific deliverables remain RRUFF top-1 Accuracy (grade), unique-parent data efficiency, and ECE.

**Reason for change:** The lead wishes to compare like-for-like *zero-real-label classification capability*, not to grant grade credit to models that saw hundreds of target labels. This corrects earlier assistant-authored scorecard mappings without erasing old discussion. Authoritative targets: `docs/CURRENT_STATE.md` and `docs/RRUFF_REAL_DOMAIN_LITERATURE_BENCHMARK_2026-10-22.md`.

## 2026-11-03: User adopts AlphaDiffract Table 1 as future slide reference; historical baselines expanded

**Decision and preference:** Seeing Andrejevic et al. 2026's minimalist black-background Table 1, the project lead requested that the reference be archived and that **future RRUFF presentation slides use a similarly concise, immediately readable paper/model × benchmark Accuracy comparison table** rather than an overburdened technical audit. The user explicitly added **Vecsei et al. 2019 Dense (70% RRUFF) and Convolutional (56% RRUFF)** plus **Choudhary 2025 DGPT-formula (28.75% RRUFF as re-evaluated by AlphaDiffract on its curated cohort)** to the reference model comparison library. Choudhary uses formula side information and is not a pure PXRD-only graded competitor. A source-attributed dark-theme SVG reference and expanded markdown library have been committed: [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md) and [table-style SVG](assets/alpha_diffract_2026_table1_style_reference.svg). The original user screenshot is retained as the source visual in this conversation; SVG is an explicitly named recreation.

**Further source-research insight:** SimXRD-4M's own ICLR 2025 Table 5 reports multiple architectures on the same RRUFF benchmark, including CNN11 89.3%, CNN7 86.8%, CNN10 85.9%, CNN9 79.2% and several recurrent/Transformer baselines, now separately recorded as *model variants from a single paper*. These additions do not create new 60/80/100 grading targets, alter the owner's zero-labeled-RRUFF adaptation rule, launch a new training campaign, or substitute for the agreed three outputs (RRUFF Accuracy, unique-CIF data-efficiency curve, ECE). The user's project narrative is moving toward a **simple, evidence-grounded competitive benchmark presentation** with more complete literature coverage.

## 2026-11-03: Owner expands RRUFF competitor eligibility to DiffractGPT regardless of formula input

**User's exact conceptual correction:** On seeing that a previous assistant excluded Choudhary's *DiffractGPT DGPT-formula* from the official RRUFF comparison on the basis of formula side-input, the project lead said it **should be included because it is also another researcher's work**. The purpose of the comparison library is a **complete, source-transparent literature competitor panel**, not an artificial exclusion of published alternative methods. The related project-score tiers remain **pass Lee/Salgado synthetic-only; 80 AlphaDiffract; full SimXRD/XQueryer-NoElem**—but lower-scoring competitors and models with additional declared inputs should still appear in the main benchmark comparison if they have an attributable RRUFF crystal-system Accuracy. Thus **DiffractGPT 2025 DGPT-formula 28.75%** joins as a **below-pass legitimate comparator**, with clear note that this particular number is **AlphaDiffract 2026's third-party re-evaluation**, not an original DiffractGPT 2025 headline result, and the model uses chemical formula input. Its original model trained on JARVIS-DFT simulated data without reported labeled RRUFF fitting. This clarification was committed to [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md), the benchmark scorecard, and the authoritative current state. It preserves the original five anchor-paper thresholds and the outcome trio of real RRUFF Accuracy / data efficiency / ECE.

## 2026-11-03: Vecsei Dense moves to pass-tier benchmark

The owner clarified that Vecsei et al. (2019) Dense/MLP with 70% RRUFF Accuracy belongs in the pass (60-point) tier, not below it. Pass-tier comparisons now include Vecsei Dense 70%, Salgado synthetic-only about 74%, and Lee 74.24%. Vecsei CNN 56% and DiffractGPT 28.75% remain comparative results; 80 and full tiers remain unchanged. This is a scoring-policy correction, not a new experiment. See the current state and RRUFF model comparison library.

## 2026-11-03: Five-column slide benchmark fixed — training structures and actual RRUFF N

**Owner's presentation preference refined:** After approving AlphaDiffract Table 1's compact score comparison style and freezing the six-row pass/80/full RRUFF zero-shot scorecard, the owner asked for **two additional visible numerical columns**: (a) **how many independently sourced simulated crystal structures are used in training**, and (b) **how many measured RRUFF spectra support the reported test accuracy**. The user explicitly preferred approximate values when exact paper cohorts are unavailable, but refused extra complexity: keep the slide to **grade, paper/model, simulated structures, RRUFF test N, RRUFF Accuracy**. RRUFF labeled-adaptation remains 0 for all graded comparators, reported in the notes instead of crowding the main table.

**Primary-source verification produced a new concrete finding:** Vecsei et al. 2019's original paper reports **128,404 distinct simulated samples after deduplication, of which 114,404 are actual training samples** after separate 7,000/7,000 validation/test, and about **800 RRUFF spectra**. The table labels other papers' counts as curated parent corpora, not verified final post-split training Ns; Lee's ~960 RRUFF is an **estimate** based on 1,600 initial spectra and a 40% low-angle background exclusion; SimXRD-4M's actual RRUFF Table 5 denominator stays **Unknown** even though its catalog records 3,002 entries. Verified and uncertain counts are now laid out, with source links and a compact slide-friendly format, in [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md). The important shift is from percent-only comparisons to **performance relative to simulation-data scale and real-test scope**, without implying identical cross-paper RRUFF panels. No new experiments or CIF acquisition were started as a result.

## 2026-11-03: Cao thesis reveals SimXRD's usable RRUFF cohort is approximately 1,003

The owner asked to resolve the RRUFF test count behind SimXRD's 89.3% and suggested it may share XQueryer's published **3,002 → 1,003** cohort. Source verification of **Bin Cao's own 2026 doctoral thesis PDF** shows the **SimXRD chapter 3** explicitly reports **3,002 catalog entries in March 2024, only 1,003 usable because of complete diffraction and structural information**, and the same chapter's **Table 3.5** repeats CNN11's **0.893 RRUFF accuracy**. The XQueryer chapter separately documents the **2,088 matched XY_RAW/DIF → 1,003 valid** cleaning flow. The lead instructed us to incorporate this evidence and treat it as likely the same underlying RRUFF dataset. The six-row benchmark slide table now writes **SimXRD RRUFF test ≈1,003 (same-author thesis-supported inference)** rather than an unconstrained Unknown or a misleading 3,002 tested. Exact scored sample IDs and an explicit Table-5 N are still unreleased, so identical test membership between the two papers is **likely but not proven**. This is a correction to earlier overly conservative source accounting, not new measured performance. See [revised cohort audit](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md) and [current leaderboard](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md).

## 2026-11-03: Reconsider old-data HPO after 154,975-structure library becomes available

**Status: research-method reconsideration / proposal, NOT an approved cancellation or a completed new HPO experiment.** The project lead questioned whether tuning hyperparameters with the historical 14,060-row / 9,842-train-parent library is wasted effort now that the 154,975-row, 154,968-parent library exists on external D: storage, split **108,478 actual train parent groups / 23,245 validation / 23,245 test**. The lead specifically hypothesized that the meaningful hyperparameter search should operate against the new larger corpus. This is an important shift in thinking: earlier 'finish tuning before collecting data' made sense when the larger database did not yet exist, but **the database has now been collected and structurally validated** (though full V11 PeakTable adaptation and corpus-scale spectrum generation are still not complete).

**Evidence from current HPO code inspection:** `E:\AI4science\_local\resnet_optuna_20261103\supervise_optuna.py` is still bound to the historical `formal_14060` train 9,842, fixed V10 pseudo-Voigt/Caglioti simulator, and `STEPS=49280`, `batch_size_parents=16`; the queued automatic follow-on explores up to **10** full-length trials plus independent-seed confirmation. This is **788,480 sampled parent presentations** per run, corresponding nominally to about **80.1 old-train-parent passes** or only **7.27 new-train-parent passes** at the same step budget. Moreover the old data are artificially seven-class balanced whereas the new dataset has substantially unequal class frequencies (for example new training hexagonal 7,493 parent groups versus monoclinic 25,593). Therefore exact LR, weight decay, JS lambda, schedule, sampling and training horizon selected on the old balanced sample are **not guaranteed to transfer** to the new data and V11 simulator.

**Provisional methodological recommendation (no code/process changes authorized by this entry):** Preserve all completed six-cell V10 architecture/downsampling and numerical-stability investigations as transferable exploratory evidence. **Do not invest the full planned 10-trial old-data Optuna budget in selecting final full-scale training hyperparameters.** Prefer **new-library-based multi-fidelity optimization** (representative new-parent subsets for broad filtering, full 108,478-train-parent runs only for finalists), with V11 bounded integration/preprocessing readiness checks first. Select checkpoints and hyperparameters on the new library's **validation only**, never its test split or locked RRUFF. Confirm finalists using a small number of seeds; do not require five by habit. The user has **not explicitly instructed stopping the live waiting Optuna supervisor**, so this entry does not claim processes stopped or change the active issue's execution permission. It records the thought evolution and its quantitative rationale for a later owner decision.

## 2026-11-03: Owner cancels old-data Optuna while letting A0/A1/A2 finish; moves final HPO to cloud on 108,478 parents

**Explicit owner decision after reviewing the new D-drive library:** The lead called the old-data hyperparameter optimization “无用功” *for the final target* and directed: **let the in-flight A0/A1/A2 experiments finish and simply archive them; stop further old-database HPO, and plan full 100k+ parent tuning on a new rented GPU server**. This overrides the previous proposal to fully complete the legacy 9,842-parent V10 Optuna before CIF expansion. The revision is not a rejection of the historical A0/A1/A2 architecture/numerical experiments: those already-completed runs are useful, but their `lambda_js`, learning-rate and schedule optima are not portable claims for the larger V11 task.

**Operational action actually performed, 2026-11-03 ~18:06 +0800:** Read process tree and statuses. The six-cell supervisor had completed **A0_R0, A0_R1, A1_R0, A1_R1, A2_R0** and was still running **A2_R1**, independently of Optuna. Targeted `supervise_optuna.py` only, stopped its Python/PowerShell PID chain **47944, 7024, 15928**; verified the A2_R1 Python trial and `run_joint_campaign.py` both remained running. The old Optuna had stayed at `waiting_previous` and **no new Optuna HPO GPU trials were launched**. Appended local `E:\AI4science\_local\resnet_optuna_20261103\owner_cancelled_20261103.json`, changed supervisor state to `cancelled_by_owner`, retaining prior state inside the local record; no training/checkpoint deleted. The prior hourly notification automation was updated to watch **only six-cell archival completion**, never resume old Optuna.

**New dataset was verified earlier in the same session:** `D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103` has **154,975 MP-ID rows, 154,968 independent parent fingerprints, 108,478 train parents, 23,245 val, 23,245 test**; integrity `passed`, old 14,060 kept. The library comprises `*.jsonl.gz` structures, **not** spectra or precomputed ideal peak tables. V11 renders the seven-system sample correctly but still requires conversion from `structure` to the runner's `standardized_structure`/PeakTable contract and corpus-scale readiness verification. The next HPO is therefore gated on the **new library + V11 training workflow**, and should compare candidate hyperparameters on **all 108,478 training parents**, never rely on a small subset as final HPO. Use parent-equivalent epochs not the historical hard-coded 49,280 steps (~80 legacy-parent passes vs ~7.3 new-parent passes at batch 16). Confirm finalists with 2–3 seeds, then freeze and evaluate real RRUFF only after tuning. No cloud instance was rented.

**Paper-trail and implemented status:** [authoritative current state](CURRENT_STATE.md), [new GPU/HPO execution plan](PXRD_154975_CLOUD_HPO_EXECUTION_PLAN_20261103.md), [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) retargeted to cloud/new data, [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61) corrected to already collected database, no repeat acquisition. This is a methodological pivot in response to available resources—not a retroactive rewrite of any experiment.

## 2026-11-03: PR #58 V11 simulator delivered; scale fix and evidence boundary

The earlier 2026-11-03 execution snapshot said implementation could not proceed while the authorized local editing route was unavailable. PR #58 now contains the runnable V11 renderer, online same-parent integration, CIF-to-paired-view path, and acceptance artifacts.

The review identified a mismatch between the V11 unit-area renderer and the legacy Gaussian reference scale: an isolated 0.08° Gaussian-limit peak would reach about 0.399, unintentionally changing the relative background and count-space noise. The PR corrects this at the integration boundary using the rendered V11 peak maximum, while preserving the standalone area-normalized renderer and V9's legacy default.

The PR head `b43e28d` passed 134 non-data-bound CI tests. Its separate validation record also reports seven-system label preservation, fixed-seed replay, V9 regression, broadening trends, and integrated peak-area checks. **No model training was run as part of the V11 validation reported in PR #58, and the PR reports no V11 HPO result.** Later model work follows the current-state readiness gates.

**Integration update (2026-11-05):** PR #58 merged into `main` as commit `940942d5a9c30307295eb7b7a68c08e47687f955`; Stage 1 simulator implementation and integration are complete. The merge commit's main `XRD tests` CI run [#41965621220](https://github.com/Frysland-2024/AI4science/actions/runs/41965621220) passed. The validation record's 50 focused tests and seven-system/paired-view acceptance are simulator engineering evidence only. No V11 model training, HPO, final RRUFF evaluation, or classification improvement is established. Subsequent full-scale HPO remains gated by the structure-schema adapter, corpus-scale PeakTable build, data audits and GPU-throughput proof.

## 2026-11-09: Issue #61 local preflight completed; target-GPU gate assigned to #55 Stage 0

**Date:** 2026-11-09

**Question / previous assumption:** Issue #61 combined local package/schema/manifest/CPU acceptance with target Linux GPU readiness and blocked Issue #55 until both were complete.

**New evidence or reasoning:** Latest `main` commit `158c989` contains the merged-library `--records-path` schema adapter, parent-safe Train+Validation manifest builder with per-PeakTable SHA checks, and regression tests. XRD CI [#42554396816](https://github.com/Frysland-2024/AI4science/actions/runs/42554396816) and V11 migration CI [#42554691047](https://github.com/Frysland-2024/AI4science/actions/runs/42554691047) passed. On the laptop, a fresh private kit using payload contract `v11-prefetch-validation-20261109.3` passed source/archive verification and `start_server.sh --plan`; the full 154,975-record shard/cache readiness audit, frozen 131,729-row Train+Validation manifest reconstruction, one-record CPU PeakTable adapter smoke, one-batch ResNet-A0 CE+JS CPU smoke, and two-worker bitwise prefetch parity smoke passed. Later CPU and local CUDA regressions of the actual shared checkpoint save/restore functions also passed: nine synthetic optimizer steps uninterrupted exactly matched four steps plus checkpoint/restart/restore and five further steps for model tensors, optimizer state, parent sampling, history, and CPU/CUDA Torch RNG. The CUDA test used the local RTX 4060 with PyTorch `2.13.0+cu126`; this does not establish target Linux full-trainer/prefetch resume. The follow-up source contract is `.5`; no `.5` package has been built. The full package evidence and immutable input/output hashes are in `docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md`.

**Decision:** Limit Issue #61 to local package/schema/manifest/CPU acceptance. Move target Linux/CUDA smoke, throughput/resource measurement, complete Validation access through the GPU path, and checkpoint/resume/RNG checks to Stage 0 of Issue #55, before HPO. Stage 0 and any later GPU/HPO work still require separate budget and owner authorization.

**What changes now:** Record the local preflight and CPU checkpoint regression; payload contract `.4` identifies the updated source and the already verified `.3` kit must be rebuilt before transfer. Issue #55 owns the outstanding target-GPU gate as Stage 0.

**What does NOT change:** No cloud instance or target Linux CUDA run was started. No throughput claim, HPO, formal training, research checkpoint, or Test/RRUFF inference was produced; temporary checkpoints in synthetic CPU/CUDA regressions are engineering fixtures only. Local micro-smokes do not establish target Linux GPU readiness, and passing Stage 0 will not automatically authorize HPO.

**Status:** CLOSED for Issue #61 local acceptance; Stage 0 remains ACTIVE / NOT_RUN in Issue #55.
**Relevant files / commits:** `docs/ISSUE61_LOCAL_PREFLIGHT_20261109.md`; `server_migration/README.md`; `server_migration/one_click_v11.py`; `server_migration/tests/test_v11_prefetch_pipeline.py`; source code snapshot `158c989`; CI runs `42554396816`, `42554691047`.
