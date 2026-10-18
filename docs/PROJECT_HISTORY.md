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

## 15. 2026-10-18: W0 pre-refinement engineering sprint completed

**Date / prior assumption:** 2026-10-18. The proposed pre-refinement system could not advance until the collaborator selected a material family; transferable software work and a small structure-backed smoke case could proceed independently.

**Evidence / decision:** Audited current PXRD and inversion modules, added an isolated metadata-first family registry, JSON schemas, an uncalibrated template-ranking baseline and a reusable adapter to the existing simulator. A small BaTiO₃ demo used 2016 published single-crystal structure tables (298 K P4mm and 413 K Pm-3m) to generate idealized powder profiles. The repo CIFs are explicit table transcriptions, not downloaded official supplementary files. The W0 follow-up ran both candidates through forward reconstruction, spectrum comparison, and bounded numerical optimization of symmetry-allowed cell metrics plus 2theta zero shift. On one synthetic tetragonal observation, P4mm normalized RMSE changed 0.286485 → 0.109186 and Pm-3m changed 0.677231 → 0.652587. Thirteen tests pass. These remain engineering diagnostics: no trained parameter predictor, intervals, empirical recovery test, or measured refinement benefit. Template ranking scores remain uncalibrated distances, and the mixture case remains an arbitrary profile-intensity interface smoke test.

**What changes now:** W0 engineering infrastructure is complete and reproducible; run artifacts, provenance, limitations and the next collaborator handoff step are recorded in [`xrd_pre_refinement/reports/W0_HANDOFF.md`](../xrd_pre_refinement/reports/W0_HANDOFF.md).

**What does not change:** The selected research family remains unknown; the formal 12-week study is still PROPOSED / NOT_STARTED. No model training, experimental result, probability calibration or quantitative phase analysis was produced. The frozen JS-only results and archived factorization NO-GO are unchanged.

**Status:** W0 ENGINEERING COMPLETED / FORMAL STUDY NOT_STARTED. Relevant code: [`xrd_pre_refinement/`](../xrd_pre_refinement/README.md).

## 16. 2026-10-18: forward-model role and CrystalShift prior-art correction

**Date / previous assumption:** 2026-10-18. The pre-refinement direction already proposed AI candidate/parameter outputs with a physical forward check. The W0 acceptance was initially implemented only as Top-K ranking plus reference-profile residuals.

**New evidence and reasoning:** The user clarified that a minimum demo must send at least two reference candidates through forward reconstruction, observed-spectrum comparison and a limited parameter optimization. A static audit of the public [`CrystalShift.jl`](https://github.com/MingChiangChang/CrystalShift.jl) source at commit `d95bb2561a504258639fa18e0d25a06684c7c0d5`, its MIT license and its 2025 paper found an existing training-free method combining symmetry-constrained lattice pseudo-refinement, best-first multi-phase candidate search and Bayesian model comparison. The paper also describes its limitations relative to full Rietveld treatment. CrystalShift is relevant prior art and a potential strong baseline; its Julia runtime is absent on the current workstation, so local execution and integration remain unverified. Details are in [`CRYSTALSHIFT_AUDIT.md`](../xrd_pre_refinement/reports/CRYSTALSHIFT_AUDIT.md).

**Decision:** The research question is not to invent a new physical phase-search framework. The forward model is the bridge that makes AI-proposed candidate structures and parameter initializations testable against the measured pattern and conventional numerical refinement. The question is whether simulation-trained AI improves the usefulness and reliability of those initializations, and reduces downstream refinement time or failure under fair comparison with physical-template and compatible numerical baselines. W0 therefore adds a deliberately narrow bounded fit for both BaTiO₃ candidates, not CrystalShift's tree search, combination probabilities or texture-peak optimization.

**What changes now:** The report, handoff, architecture, current state and 12-week candidate plan record the two-candidate forward-fit path and its strict limits. A future CrystalShift comparison is a time-boxed feasibility option after actual family, CIFs, axis/wavelength, runtime and compute budget are confirmed.

**What does not change:** W0's single synthetic-profile result is not evidence of parameter accuracy or saved refinement time. The real material family is still unknown; the 12-week project remains PROPOSED / NOT_STARTED. Frozen PXRD classification evidence and archived inversion NO-GO remain unchanged.

**Status:** ACTIVE research-positioning clarification / W0 fit implemented / CrystalShift execution NOT_RUN.

## Current perspective

The project is no longer summarized as "a JS loss for XRD" or "an XRD robustness benchmark."

The current research statement is:

> **Use relationships known by scientific data-generation systems — here, simulator-retained parent provenance — as additional supervision for learning from scientific measurements.**

PXRD is the concrete test bed. The broader transferable idea is to identify supervision that already exists in a scientific measurement process but is normally discarded when observations are reduced to independent (x, y) pairs.
