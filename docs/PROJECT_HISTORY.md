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

## Current perspective

The project is no longer summarized as "a JS loss for XRD" or "an XRD robustness benchmark."

The current research statement is:

> **Use relationships known by scientific data-generation systems — here, simulator-retained parent provenance — as additional supervision for learning from scientific measurements.**

PXRD is the concrete test bed. The broader transferable idea is to identify supervision that already exists in a scientific measurement process but is normally discarded when observations are reduced to independent (x, y) pairs.
