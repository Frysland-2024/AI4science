# AI4Science: PXRD Seven-Crystal-System Classification

**Current undergraduate thesis scope (decision dated 2026-10-26):** write up and defend the completed PXRD seven-crystal-system classification study, asking whether same-parent measurement-equivalence supervision improves classification over matched Dynamic ERM. Use the frozen evidence and state its limits; no new experiments are in the current thesis scope.

PR #36 is a completed but narrowly conditional synthetic result: on one known BaTiO3 CIF, direct A/B/C normalized-q MAE was 0.033607/0.033578/0.034282 (DONUT: 0.228037); after the same bounded joint q+instrument L-BFGS-B refinement, A/B/C were 0.000343/0.000350/0.000341 (DONUT: 0.080026). The refined values are not direct neural predictions. This supports feasibility only under that frozen synthetic setup; it does not establish real-XRD, unseen-material, multiphase, or general method-superiority performance. The report remains on closed, unmerged PR #36; inversion is inactive and outside the current thesis scope.

## Project Overview

This repository contains a completed ResNet-18-GN comparison of **Dynamic ERM** and **Dynamic JS Consistency**, plus deferred proposals for possible future classification work. The simulator generates two measurement views from the same unchanged parent crystal; Dynamic JS uses that known relationship as additional supervision.

**What is complete:** controlled method comparisons, simulated out-of-distribution (OOD) evaluation, historical RRUFF-301 few-shot adaptation, simulated/CNRS calibration audits, and a parent-structure budget study.

**Current deliverable:** a bounded thesis account of the completed same-parent Dynamic JS vs Dynamic ERM study, including the simulated OOD result and the separate RRUFF/CNRS/parent-budget evidence with their limitations.

**Deferred:** new RRUFF zero-shot evaluation, RRUFF calibration, larger-parent training, simulator upgrades, hyperparameter retuning, and new architecture comparisons. These are not current thesis requirements.

## Scientific Motivation & Method

A simulated PXRD spectrum has a known crystal-system label and a known parent-structure identity. Two spectra generated from the same parent represent different measurements of the same crystal. The study asks whether using this measurement relationship adds value beyond ordinary class-label supervision.

![Same-parent PXRD method overview](xrd_robustness/figures/figure_1_method_overview.png)

The method contribution is the use of simulator-retained parent identity as relationship supervision. JS consistency is its tested implementation; the project does not claim to have invented JS consistency.


<details>
<summary>Earlier project context figures (slides 01–09)</summary>

![Research task](docs/showcase/01_research_task.png)

![Seven crystal systems](docs/showcase/02_seven_crystal_systems.png)

![Project workflow](docs/showcase/03_project_workflow.png)

![Prior work](docs/showcase/04_prior_work.png)

![Study improvement](docs/showcase/05_our_improvement.png)

![Data and setup](docs/showcase/06_data_and_setup.png)

![Measurement perturbations](docs/showcase/07_measurement_perturbations.png)

![Simulated results](docs/showcase/08_simulated_results.png)

![Structure-coupled gains](docs/showcase/09_structure_coupled_gains.png)

</details>

## Completed Research

| Evidence | Completed result | Boundary |
|---|---|---|
| Simulated OOD classification | Test Macro-F1: Dynamic ERM **0.6507**; Dynamic JS **0.7053**; paired gain **+5.46 percentage points** across five matched seeds. | Frozen 14,060-parent study; not a real-domain score. |
| RRUFF-301 few-shot | Macro-F1 gains at K=1/2/5: **+4.33 / +4.60 / +5.45 pp**. | Historical few-shot adaptation evidence; it is not the new zero-shot benchmark. |
| Confidence calibration | Existing simulated-Test and CNRS analyses report ECE, NLL, and Brier; see the frozen analysis. | These do not establish calibration on the planned RRUFF evaluation. |
| CNRS-318 zero-shot | Paired seed-level Macro-F1 gain **+1.87 pp**; pooled accuracy **0.200 → 0.210**, below the 0.274 majority baseline. The corrected paired-parent 95% interval crosses zero. | Optional secondary domain; keep the completed result and its limits visible when making broad generalization claims. |
| Simulated parent-budget study | Dynamic JS had higher OOD Macro-F1 at all four matched budgets (10/25/50/100% of the original training parents). | Post-main use of an already evaluated simulated Test; it does **not** demonstrate a measured number of structures saved. |

Detailed numbers, uncertainty, frozen test caveats, and machine-readable evidence are in [the results report](xrd_robustness/reports/RESULTS.md), [calibration analysis](xrd_robustness/reports/CALIBRATION_ANALYSIS.md), and [parent-budget report](xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).

## Undergraduate Thesis Scope

The single thesis question is: **Does using simulator-known identity between measurements of the same parent crystal as relationship supervision improve PXRD seven-crystal-system classification over matched Dynamic ERM?**

The study and its primary controlled comparison are already complete. The thesis will report the frozen evidence and its limits; **no new experiments are in the current thesis scope**.

| Evidence | Role in the thesis | Boundary |
|---|---|---|
| ResNet-18-GN Dynamic ERM vs Dynamic JS | Core result: simulated OOD Macro-F1 gain of +5.46 percentage points across five matched seeds. | Frozen split and protocol; do not describe it as a new benchmark or universal superiority. |
| RRUFF-301 K=1/2/5 and CNRS-318 | Supporting completed evidence, reported separately with their task and uncertainty limits. | Few-shot RRUFF is not zero-shot. CNRS absolute accuracy is low and its corrected interval crosses zero. |
| Simulated parent-budget study | Supplementary post-main evidence. | It reuses an already evaluated Test and does not establish a measured structure saving. |
| PR #36 conditional parameter inversion | Completed four-stage synthetic study, retained as bounded historical side evidence. | One known BaTiO3 CIF and one frozen generator; the ≈0.00034 q-MAE follows physical refinement, not direct neural inference. No real-XRD or unseen-material claim. |

## Deferred Research Proposals

The 2026-10-23 scale-up proposal (new RRUFF zero-shot evaluation, RRUFF calibration, larger parent budgets, simulator changes, training retuning, and conditional architecture comparisons) is **deferred** as of 2026-10-26. It is not an active task, thesis acceptance gate, or authorization to collect data or run experiments. See the [deferred planning record](docs/PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md) for historical detail.

## Reproducibility & Results

- [Start here for supervisors](docs/START_HERE_FOR_SUPERVISORS.md)
- [Frozen results and limitations](xrd_robustness/reports/RESULTS.md)
- [Data and reproducibility policy](docs/DATA_AND_REPRODUCIBILITY.md)
- [Experiment protocol and code](xrd_robustness/README.md)
- [RRUFF literature benchmark plan](docs/RRUFF_REAL_DOMAIN_LITERATURE_BENCHMARK_2026-10-22.md)
- [Calibration report](xrd_robustness/reports/CALIBRATION_ANALYSIS.md)
- [Parent-budget protocol and report](xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md)
- [Current project state](docs/CURRENT_STATE.md) · [Project history](docs/PROJECT_HISTORY.md)
- [Manuscript](xrd_robustness/MANUSCRIPT.md)
- [Validation results JSON](xrd_robustness/reports/validation_results.json)
- [Simulated-test results JSON](xrd_robustness/reports/simulated_test_results.json)
- [RRUFF-301 few-shot results JSON](xrd_robustness/reports/rruff301_fewshot_results.json)
- [Citation](CITATION.md) · [License](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)

Selected evidence figures:

![Simulated parent-budget comparison](docs/showcase/10_data_efficiency.png)

![RRUFF-301 historical few-shot results](docs/showcase/11_rruff_few_shot.png)

![CNRS-318 optional secondary-domain results](docs/showcase/12_cnrs_zero_shot.png)

The source images and prior presentation files are preserved in [docs/showcase](docs/showcase/). The prior [slide 13](docs/showcase/13_next_stage_HISTORICAL_20261023.png), [PDF](docs/showcase/AI4science_showcase_EN_HISTORICAL_20261023.pdf), and [PowerPoint](docs/showcase/AI4science_showcase_EN_HISTORICAL_20261023.pptx) are explicitly marked as historical; see the [archive note](docs/showcase/HISTORICAL_PRESENTATION.md). Use this README and [CURRENT_STATE](docs/CURRENT_STATE.md) for the current thesis scope; the scale-up plan is deferred.

## Research History

The project path is preserved in [Project History](docs/PROJECT_HISTORY.md): **FerroAI → PXRD classification → same-parent relationship-supervision method research → quantitative parameter-inversion exploration → return to seven-crystal-system classification**.

The four-stage [PR #36](https://github.com/Frysland-2024/AI4science/pull/36) is complete on a single known synthetic BaTiO3 CIF; its [final technical report](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-experiment-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md) is the numerical source for the conditional result above. It is not evidence for real measurements or unseen materials.

Other inversion branches remain separate historical records. [PR #43](https://github.com/Frysland-2024/AI4science/pull/43) completed a supported subset across seven synthetic CIF templates in three crystal systems. In the primary study, N+A q-MAE was essentially tied with the three-start P3 baseline; P0 was already comparable on five materials and had larger errors on MgO and ZnO. A separate post-primary renderer/peak-shape/background stress test, using 16 new parents per material, found no added accuracy or reliability over P0/P3. These bounded synthetic findings do not establish unseen-material transfer or real-XRD validity. [PR #45](https://github.com/Frysland-2024/AI4science/pull/45) E1 found no material meeting its preregistered incremental-value rule against H1/P0; E2 stopped at `PHYSICS_NOT_READY / NN_NOT_RUN`, so it is not neural validation on real XRD. [PR #42](https://github.com/Frysland-2024/AI4science/pull/42) is a closed, unmerged decision record whose DONUT summary conflicts with the PR #36 final report; use the latter for PR #36 metrics. [PR #48](https://github.com/Frysland-2024/AI4science/pull/48) was merged for the classification showcase and adds no parameter-inversion evidence.

The 2026-10-20 [PR #46](https://github.com/Frysland-2024/AI4science/pull/46) recorded a partial synthetic inversion benchmark: 42 models and 8,085 primary rows, with the q-accuracy gate passing **0/42** and the per-DOF cell-MAE constraint passing **41/42**. The PR43 held-out parents had already been evaluated; new-architecture stress was not run and real RRUFF validation was blocked/not run. These are descriptive exploratory results only. They do not establish method superiority, real-domain validity, or an exact reproduction of XQueryer, SimXRD-4M, CPICANN, or PyWPEM.

Quantitative inversion, Forward Reconstruction Loss, DONUT-inspired work, automatic refinement, and ferroelectric pre-refinement remain **Archived / Inactive** as active research lines. That status preserves rather than erases PR #36's completed conditional result; historical artifacts do not reactivate the work or change the current classification thesis scope.
