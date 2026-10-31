# Project History — Public Research Timeline

This file is the **public, concise history** of how the PXRD project evolved. It preserves major corrections, negative results, and changes in problem definition without reproducing internal handoff notes or application material.

For current scientific claims, use [CURRENT_STATE.md](CURRENT_STATE.md) and the tracked result reports. History explains *how the project changed*; it does not override the current state.

> **新增沟通记录（整理于 2026-09-20）：** [与学长沟通纪要：XRD 项目当前进展与后续计划](PROJECT_HISTORY_NOTE_2026-09-20_SENIOR_MEETING_SUMMARY.md)。依据用户提供的会议摘要截图，记录当前方法与验证进展、定量反演及初步晶体结构预测方向、云算力与协作安排；会议日期未注明。

> **2026-10-22 导师汇报复盘（2026-10-23 整理）：** [方法设计、真实域验证与物理/应用可信度的视角错位](PROJECT_HISTORY_NOTE_2026-10-22_SUPERVISOR_PRESENTATION_REFLECTION.md)。系统记录当晚交流与后续对话纠偏：温度/成分扰动的物理边界、cubic 示例被误认为只做单一晶系、RRUFF 的 K-shot 微调被误听为总训练样本数、CNRS 无目标域适配的 zero-shot 相对增益与低绝对性能的不同评价、原方法/原模型比较及 bias、数据可获得性、扩容和发表文献跑分对标，以及实验室铁电陶瓷 R/T 相真实谱检验建议。保留负责人因方法设计贡献未得到充分理解而受挫及「横向方法研究 vs 纵向材料任务」的认识变化。此为历史反思，不更改冻结实验，也不宣称导师建议已获批或完成。

> **2026-10-23 暂定研究兴趣认识（PROVISIONAL）：** 在复盘导师汇报、准备与东京大学小关泰之老师交流时，项目负责人提出一个新的自我观察：与以材料合成、制备及湿实验为核心的工作相比，自己可能更适合围绕**科学测量系统与测量数据**开展研究，尤其是从物理测量过程、模拟与正向模型、信号处理、监督设计、逆问题到真实域验证的研究链条。过去从 FerroAI 到 PXRD 的选择与反复尝试，为这一兴趣判断提供了经历依据；但当前的已完成研究主要是**基于现有 PXRD 数据/模拟的 ML 方法与评估**，不能据此声称已经具备激光/光学仪器搭建、测控硬件或完整测量系统开发经验。**有待进一步分辨的三个方向是：仪器与光路硬件、测量方法与采集策略、计算测量/信号分析。** 这是一种探索中的自我定位，不是项目主线或毕业课题已经正式变更，也不意味着排斥所有物理实验。未来选择研究组需确认具体课题是否主要涉及光学搭建、信号与算法，还是材料/生物样品制备。

---

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
