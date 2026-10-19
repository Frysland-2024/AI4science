# Project History — Public Research Timeline

This file is the **public, concise history** of how the PXRD project evolved. It preserves major corrections, negative results, and changes in problem definition without reproducing internal handoff notes or application material.

For current scientific claims, use [CURRENT_STATE.md](CURRENT_STATE.md) and the tracked result reports. History explains *how the project changed*; it does not override the current state.

> **新增沟通记录（整理于 2026-09-20）：** [与学长沟通纪要：XRD 项目当前进展与后续计划](PROJECT_HISTORY_NOTE_2026-09-20_SENIOR_MEETING_SUMMARY.md)。依据用户提供的会议摘要截图，记录当前方法与验证进展、定量反演及初步晶体结构预测方向、云算力与协作安排；会议日期未注明。

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

**Status at selection:** USER-SELECTED FUTURE RESEARCH PRIORITY; the family-specific study was not started or approved. A bounded engineering pilot was later authorized and is recorded below. Do not overwrite existing V9 results or revive archived NO-GO. See [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md).

## 18. 2026-10-18: first supervised-plus-forward-loss pilot completed

**Previous state:** The single-intervention direction was selected as a research priority, but the continuous NN comparison and differentiable-gradient gate had not been run. The prior note treated training-time reconstruction loss as an optional candidate; the user then explicitly authorized a bounded A/B pilot.

**Evidence:** A separate module used the existing tetragonal CUDA float64 forward model on one source-training-fold HfCd parent, with only normalized `du,dv` active. The Jacobian was full rank (condition number `3.36`); finite-difference checks agreed with autograd. Three matched seeds were run after validation-only selection of `lambda=1.0`.

**Decision/result:** Keep Forward Reconstruction Loss as an experimentally tested candidate, not an assumed improvement. It lowered clean transformed-profile RMSE (`0.009008` to `0.008497`) while the mean normalized two-parameter MAE was slightly higher (`0.01495` to `0.01509`). The pilot supports feasibility of the training graph but does not support a claim of better parameter inference.

**What changes now:** The pilot implementation, failure record, metrics, and next-stage handoff are tracked in `xrd_forward_loss/`; the current-state and 12-week documents point to those results. The family-specific study should proceed only after material/CIF, parameter-identifiability, and prototype-split gates.

**What does not change:** Frozen JS-only classification results, the source split, independent renderer holdout, and archived structure–measurement factorization NO-GO remain untouched. The HfCd result is not ferroelectric evidence and does not establish a better Rietveld initialization.

**Status:** PRELIMINARY ENGINEERING PILOT COMPLETE / FAMILY-SPECIFIC RESEARCH FUTURE. See [pilot report](../xrd_forward_loss/FORWARD_LOSS_PILOT_REPORT.md), [feasibility report](../xrd_forward_loss/FORWARD_FEASIBILITY_REPORT.md), and [handoff](../xrd_forward_loss/NEXT_STAGE_HANDOFF.md).

## 18. 2026-10-18: PXRD AutoLab automation proposal

The user proposed automating repetitive experimental work after choosing a small, literature-based Forward Reconstruction Loss A/B study and a transparent biweekly reporting schedule. The new idea is an auditable engineering workflow: locked config, physics/split/budget gates, paired training, machine-derived metrics and figures, immutable manifests, and draft reports.

The first engineering step should be a minimal P0 (manifest, state machine, safe CPU smoke, reporting and tests), then a P1 scientific pilot, followed by optional GPU scheduling if an authorized worker is accessible. Scientific decisions and claims stay with researchers. No changes to frozen V9 evidence or archived Stage-1 NO-GO.

**Status:** PROPOSED / NOT IMPLEMENTED / NO NEW SCIENTIFIC RESULTS. See [PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md).

## 19. 2026-10-18: reuse V9 measurement simulation in clean-reference Forward Loss pilot

**Date / status:** 2026-10-18 / PRELIMINARY ENGINEERING PILOT COMPLETE; independent draft PR pending review.

**Question / prior limitation:** The first Forward Loss pilot used the existing simple Poisson-count plus linear-background observation path, and its B reconstruction term compared against the perturbed input. A simulator nuisance could therefore be mistaken for lattice error. The V9 measurement operators already existed but had not been adapted to this single-parent inversion task.

**Implementation and evidence:** Starting from the latest PR #11 head in a separate branch, an adapter now retains V9 peak-table rendering, `PhysicsParameterSampler`, Poisson–Gaussian readout, smooth background, area-stable peak broadening, and one global 2θ offset. Nuisance values and seeds are recorded per sample; lattice truth is shared across simple/V9 views. Phase-1 noise/background and phase-2 broadening/zero-shift profiles passed unit and operator checks. The baseline V9 renderer agrees with the differentiable clean forward (max abs `1.04e-7`, RMSE `2.12e-9`). Clean-reference autograd agrees with finite differences (relative errors below `3.8e-8`); lattice Jacobian condition is `3.36`.

**Decision/result:** A new three-seed, 2×2 HfCd pilot was run with fixed `lambda=1`, common data/network/optimizer budget, and validation-only checkpoint selection. On the V9-input condition, B's normalized two-parameter MAE was `0.06842` vs A `0.07293`, while clean-spectrum RMSE was slightly worse (`0.04365` vs `0.04299`) and lattice-a error was slightly worse. Keep the clean-reference objective as a viable, differentiable supervised auxiliary, but do not claim an overall accuracy gain. The reported summary was independently recomputed from saved prediction JSON and profile arrays with maximum per-seed metric difference zero.

**What changes:** The adapter, phased configs, training loss option, run manifests, stop-on-gate-failure behavior, reports, and a small run are preserved under `xrd_forward_loss/` in an independent stacked PR.

**What does not change:** PR #11 results and failed runs, frozen V9 configs/weights/conclusions, independent renderer holdout, and the prior factorization NO-GO are untouched. This remains a one-parent simulated HfCd engineering study, not real PXRD or ferroelectric validation. March–Dollase remains disabled because no orientation nuisance is needed in this pilot.

**Known limits:** The local HfCd source is a standardized-structure JSON, not a CIF. The q array uses the existing float32 training interface; per-sample records retain float64 Sobol truth, with maximum array-rounding difference about `3e-8`. Stress ranges are not instrument calibration. Ferroelectric work still requires approved target structures/CIFs and phase hypotheses, instrument/background/noise/texture calibration, independent material-level splits, and reference measurements/refinements.

See [adapter contract](../xrd_forward_loss/V9_PERTURBATION_ADAPTER.md) and [pilot report](../xrd_forward_loss/reports/v9_perturbation_phase2_pilot_20261018/TECHNICAL_REPORT.md). The failure encountered after training due to a Matplotlib keyword mismatch is preserved in the run log and traceback; plots/report were recovered without retraining or changing result/history JSON.

## 20. 2026-10-18：Issue #19 纠正 Forward 重构目标并完成受控测量闭环

**Date / status:** 2026-10-18 / PRELIMINARY ENGINEERING PILOT COMPLETE; independent Draft PR pending review.

**Question / previous assumption:** 用户指出，PR #11/#16 中固定零点和最窄峰宽的 clean forward 与加入零点偏移、展宽、背景和噪声的 observed profile 不一致；PR #17 虽改用 simulator-provided clean reference，却不能作为未知真实实验 clean target 的替代。单纯物理梯度正确还不足以说明 loss 解释了测量过程。

**Evidence:** 在 COD 9014273 BaTiO₃/P4mm 模板上，P0 的 Torch/Pymatgen/V9 整谱 parity 通过；P1/P2 的测量期望谱 parity、autograd/有限差分、未知 q+eta 可辨识、non-oracle profile fit 和噪声期望 Gate 均通过。v1 因两个自由背景形状系数在 max-normalization 下不可辨识而失败；依据冻结 V9 `background_variation=0` 固定形状后 v2 通过，阈值未改。P3 在 RTX 4060 完成 512 q、3 paired seeds、simple/V9 A/B；test 未用于 λ 选择。第一次正式运行因 checkpoint RNG state 被加载到 CUDA 而在续训 B 前失败；traceback 和 46 个原始 checkpoint 的 SHA 台账纳入 PR；随后完成本地存储优化，保留 12 个逐张量等价的 FP32 最佳权重推理快照（约 596 MiB），释放约 8.34 GiB，精简快照不支持断点续训。修复 RNG 恢复设备后从新 formal 输出完整重跑，并把首次尝试保守 630 秒纳入 2 小时累计预算。

**Decision / result:** measurement-aware expected forward 的训练闭环工程可行。结果并非一致胜出：simple 的两维 q MAE A `0.013533 ± 0.000849`、B `0.013676 ± 0.001923`；V9 的 A `0.032235 ± 0.001255`、B `0.030554 ± 0.002580`。V9 下 B 的 q MAE 小幅降低，但 nuisance 估计误差和 observed expected-profile residual 高于 A 路径；A 的 residual 评估另有逐样本 eta profile fitting 成本。保留为效果尚未确立的单 CIF exploratory result，不宣称普遍精度增益。

**What changes now:** Issue #19 的独立实现、Gate 结果、正式 A/B 与负结果、命令 exit codes、配置和数据 hashes、逐 seed 指标、训练历史和 checkpoint hash manifest 被记录；两小时训练/选择预算 `1386.05/7200 s`。报告见 [结果说明](MEASUREMENT_AWARE_FORWARD_CLOSURE_REPORT_20261018.md) 与 [技术报告](../xrd_forward_loss/measurement_closure/TECHNICAL_REPORT.md)。

**What does not change:** frozen JS-only classification evidence、旧 PR #11/#16/#17 数据、factorization Stage-1 NO-GO、真实域结果和铁电 12 周规划均保持原样。单 CIF 合成条件插值不是未见材料泛化、真实 PXRD 验证或 Rietveld refinement 证据。

**Relevant files / commits:** `xrd_forward_loss/measurement_closure/`; training source commit `0e90eac79c1ae58252b4848a921bf43ee6d2669c`; checkpoint SHA ledger `xrd_forward_loss/measurement_closure/results/p3_issue19_20261018/checkpoint_manifest.json`.

## 21. 2026-10-19: Issue #31 fair PR #26 diagnosis and preregistered A/B/C retraining

**Date / status:** 2026-10-19 / EXPLORATORY SYNTHETIC ROUND COMPLETE; external GitHub delivery blocked by invalid local token.

**Question / previous assumption:** PR #26 reported A/B q error and observed-profile residual, but A used a per-sample nuisance fit while B used its predicted nuisance head. The test-residual comparison therefore had unequal evaluation compute. The extra nuisance head dimensions and gradient influence were also plausible confounds.

**Evidence:** The 12 compact PR #26 inference snapshots passed SHA, architecture loading and CUDA inference; q metrics recomputed from the frozen formal data match the saved seed records. A/B were compared on the same preselected 24-item old-test diagnostic subset with common eta initialization, bounds, objective, solver and iteration budget. The old test is post-hoc only. On validation, V9 q/reconstruction gradient cosine was negative in 6/30 batches, with one seed negative on average; simple condition had no negative q-gradient batches. V9 predicted `du` error and zero-shift error correlations were `0.904`, `0.853`, and `0.949` over three seeds. These observations support a bounded gradient-routing diagnostic but do not establish causation.

**Decision:** Before training, preregister one C change: detach q only on the expected-profile reconstruction path, retain direct q supervision and eta-path gradients. Then run one fresh 512-parent, three-seed A/B/C synthetic BaTiO₃ comparison under validation-only lambda and checkpoint selection.

**Result:** The bounded round completed 30 candidate runs in `681.06/7200` measured GPU seconds and evaluated the fresh test once. C beat A on direct q-MAE in all simple seeds; V9 C versus A was mixed, while both B/C mean direct q-MAE were lower than A and C was slightly higher than B. Equal joint q+eta fitting nearly erased between-method differences. Preserve the mixed outcome; it is not evidence of real-XRD utility, unseen-structure generalization, or Rietveld performance.

**What changes now:** `overnight_pr26_20261019/` contains original metric reproduction, fair post-hoc optimization records, validation cause audit, pretraining frozen config/hash, fresh dataset/splits, raw seed/sample results, failure records and compute/checkpoint manifests. `CURRENT_STATE.md` records the current finding.

**What does NOT change:** Frozen PR #26 formal data/checkpoints/results, V9 classification evidence, prior Issue #19 report and archived experiment results remain untouched. The compact old checkpoints remain inference-only.

**Relevant files / commits:** [overnight report](../overnight_pr26_20261019/TECHNICAL_REPORT.md); [pretraining cause audit](../overnight_pr26_20261019/PRETRAIN_CAUSE_AUDIT.md); frozen config SHA is recorded in `pretrain_manifest.json`. Branch `codex/issue31-pr26-fair-diagnostic` was pushed at `23f344b`; Issue comments and Draft PR creation remain blocked because `gh` returned HTTP 401; no merge was attempted.

## 22. 2026-10-19：DONUT-PXRD 四阶段双分支自监督适配

**Date / status:** 2026-10-19 / FOUR-STAGE SYNTHETIC STUDY COMPLETE; independent Draft PR prepared.

**Question / previous assumption:** DONUT 的双分支自监督训练能否在复用现有可微 PXRD 模拟器的条件下，估计已知四方 BaTiO₃ 合成谱的晶格参数；仪器零点偏移会否造成混淆，逐步加入峰宽、背景、噪声和织构后是否稳健；与 A/B/C 及 L-BFGS-B 相比如何。

**Evidence:** 先核对 DONUT 原论文与官方代码固定版本，再在独立分支适配一维 PXRD；物理分支复用 `CachedTetragonalGPUForward` 和 `expected_profile`。512 个参数样本先按 358/77/77 固定划分，三个 seed 为 20261061/20261062/20261063，测试索引与生成数据均有 SHA-256。测试标签不用于训练、超参数或 checkpoint 选择。四阶段的 q-MAE 依次为：固定仪器 `0.344228`；联合零点偏移 `0.398342`；峰宽/背景/噪声/织构 `0.457009/0.139752/0.228037/0.291768`。零点联合反演的 Jacobian 条件数为 `26.66`，du 与零点偏移灵敏度绝对余弦为 `0.9249`，呈现混淆。

实验 4 在相同噪声测试谱上的 direct q-MAE 为 A/B/C/DONUT `0.033607/0.033578/0.034282/0.228037`；失败率均为 0。相同初始化来源的等预算联合 L-BFGS-B 细化后 q-MAE 为 `0.000343/0.000350/0.000341/0.080026`，失败率仍均为 0；中性初值 L-BFGS-B q-MAE `0.050608`、失败率 0。全研究测得 GPU 训练时间 `2671.169 s`。A/B/C direct 推理 p50 为 `6.62/29.50/22.34 ms`，DONUT 为 `10.07 ms`；joint refinement p50 为 `0.231/0.667/0.602/0.565 s`。所有原始样本、配置、训练日志、机器指标、测试报告和恢复记录均已保存。

**Decision/result:** 四项实验均完成，实验后测试通过。结果显示该模型在这一个合成已知单 CIF 任务上的 direct lattice error 明显高于 A/B/C，联合物理细化也未达到 A/B/C 的 q 误差；不宣称真实实验效用、未见材料泛化或 Rietveld 价值。一次训练参数组引用错误在第一个 optimizer step 前修复；一次织构评估索引错误在核实固定 test 顺序后修复；均保留失败记录，未改变协议。GPU 上的线性上采样反传不支持严格确定性，seed 固定但不承诺 bitwise 重现。

**What changes now:** `donut_pxrd/` 保存源代码核验、冻结配置、运行状态、逐样本 raw CSV、训练日志、机器结果、逐阶段报告和最终报告；数据与模型权重留在本机 `E:\AI4science_DONUT_checkpoints\run_20261019_01`，由仓库 manifest 记录 SHA-256。独立分支 `codex/donut-pxrd-experiment-20261019` 创建 Draft PR 供审查。

**What does NOT change:** 现行 PXRD 分类项目身份、冻结 JS/A/B/C 或 Issue #19 结果、真实域证据与现有 framing 均不修改。本轮是单已知 BaTiO₃ CIF 的合成条件插值，不构成独立材料测试集。

**Status:** COMPLETE / EXPLORATORY SYNTHETIC STUDY. See [`donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md`](../donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md), `EXECUTION_STATUS.json`, and the four `EXPERIMENT_n.md` reports.

## Current perspective

The project is no longer summarized as "a JS loss for XRD" or "an XRD robustness benchmark."

The current research statement is:

> **Use relationships known by scientific data-generation systems — here, simulator-retained parent provenance — as additional supervision for learning from scientific measurements.**

PXRD is the concrete test bed. The broader transferable idea is to identify supervision that already exists in a scientific measurement process but is normally discarded when observations are reduced to independent (x, y) pairs.
