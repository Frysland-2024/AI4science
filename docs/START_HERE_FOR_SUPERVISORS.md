# Start here for supervisors

This page is a short route into the repository’s evidence and current research lanes. The completed scientific claim is the PXRD classification study; inversion and automation are separate tracks.

## One-minute path

1. Read the [homepage summary and four-result table](../README.md).
2. Scan the [method diagram](../xrd_robustness/figures/figure_1_method_overview.png): the simulator retains the identity linking two measurements to one parent crystal.
3. Compare the [paired simulated OOD figure](../xrd_robustness/figures/figure_3_simulated_test_paired_ood.png) with the [parent-budget learning curve](../xrd_robustness/figures/figure_5_parent_budget_efficiency.png).

**One-minute conclusion:** two-view Dynamic JS adds a same-parent prediction-consistency term to a matched two-view Dynamic ERM baseline. It improves the measured simulated OOD result and the observed RRUFF few-shot curve; CNRS zero-shot evidence is directionally favorable but uncertain in its parent-level interval and weak in absolute performance. The parent-budget supplement shows higher Macro-F1 at each matched budget, not fewer structures needed.

## Five-minute path

| Time | Read | Main question |
|---|---|---|
| 0–1 min | [README](../README.md), including the parent-budget curve | What is the claim and what are the four result settings? |
| 1–3 min | [Main results report](../xrd_robustness/reports/RESULTS.md) | Are the methods, splits, domains, uncertainty, and limitations clear? |
| 3–4 min | [Parent-budget supplement](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md) | Is the curve based on absolute Macro-F1, equal budgets, paired seeds, and a previously used Test? |
| 4–5 min | [Method/fairness audit](PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md) and [current state](CURRENT_STATE.md) | What changed between methods, and what remains out of scope? |

For broader provenance, read the [project history](PROJECT_HISTORY.md). To inspect implementation, start with [the two-view objectives](../xrd_robustness/src/xrd_robustness/training/objectives.py), [online paired views](../xrd_robustness/src/xrd_robustness/online_views.py), and [the simulator](../xrd_robustness/src/xrd_robustness/simulator.py).

## Questions the study addresses

| Question | Evidence-based answer |
|---|---|
| Does parent identity add supervision beyond the crystal-system label? | In the tested protocol, Dynamic JS adds a consistency loss between two measurements of the same parent. A matched two-view ERM comparison isolates that loss-term difference. |
| Does the added term help classification? | Yes on the completed simulated OOD comparison and the RRUFF-301 few-shot results. CNRS-318 zero-shot results favor JS across five seeds, while the class-stratified paired-parent 95% interval crosses zero. |
| Is the real-domain task solved? | No. CNRS accuracy is 0.210, below its 0.274 majority-class baseline; the study supports a relative comparison, not a deployment-ready real-XRD classifier. |
| Does JS reduce the number of structures required? | Not established. It has higher measured Macro-F1 at each of four equal-step parent budgets, but the prespecified assessment supports no parent-count saving. |
| Is the method or backbone claimed as wholly new? | No. The contribution is the use and controlled evaluation of simulator-retained parent provenance as relationship supervision; JS consistency, online simulation, and the ResNet backbone are established components. |

## Strongest evidence and limits

### Completed PXRD classification

- **Simulated OOD:** five matched training seeds; mean single-factor OOD Macro-F1 rises from 0.6507 to 0.7053 (+0.0546; all five seed differences are positive). The parent split separates train, validation, and test.
- **RRUFF-301 few-shot:** with 1 / 2 / 5 adaptation labels per class, Macro-F1 rises by +0.0433 / +0.0460 / +0.0545. This is a curated experimental domain and an adaptation task, not an unseen-mineral evaluation; shared mineral identity between support and test is allowed by the benchmark.
- **CNRS-318 zero-shot:** seed-level Macro-F1 rises from 0.1884 to 0.2071 (+0.0187; 5/5 seeds favor JS), but the corrected paired-parent interval is [−0.009339, +0.046107]. Absolute accuracy rises from 0.200 to 0.210 and remains below the 0.274 majority baseline. Labels were reconstructed from deposited structures and not manually verified spectrum by spectrum.
- **Parent-structure budget:** 40/40 method runs across 984 / 2,460 / 4,921 / 9,842 parents, five paired training seeds per budget, and 49,280 optimizer steps per model. JS has higher absolute OOD Macro-F1 at all four budgets; the frozen report says **no supported parent saving**. This post-main supplement reused the previously opened simulated Test.

### Research status lanes

| Lane | Status in the checked-out repository | Boundary |
|---|---|---|
| **Seven-system PXRD classification** | Completed main Dynamic ERM vs Dynamic JS study and reported simulated OOD, RRUFF few-shot, and CNRS zero-shot evaluations; manuscript work continues. | This is the repository’s completed scientific result. See [RESULTS.md](../xrd_robustness/reports/RESULTS.md). |
| **Known-phase PXRD inversion** | Ongoing exploratory numerical track for known-phase, single-phase tetragonal inversion. The public [xrd_inversion README](../xrd_inversion/README.md) and [formal numerical report](../xrd_inversion/reports/WEEK1_FORMAL_REPORT.md) describe the main-branch gates. | The partial inversion benchmark discussed in [PR #46](https://github.com/Frysland-2024/AI4science/pull/46) is an unmerged pull request and is not part of the main-branch evidence. Do not quote PR-only findings as completed repository evidence. |
| **Automation and operations** | The repository includes research-task execution/monitoring infrastructure, including the [task bridge](../research_bridge/README.md) and [supervisor observer](../research_bridge/SUPERVISOR.md). | This is active engineering support for experiment operations. Passing software checks or delivering status does not establish a scientific result. |

## Role and reproducibility notes

The [research-role statement](RESEARCH_ROLES.md) records Frysland-2024’s scientific leadership and Cuifa01’s execution and engineering contributions. It distinguishes project responsibility from Git authorship and does not decide future formal manuscript authorship.

The public tree supports non-data-bound code and evidence-contract checks, but does not contain all external structures, raw spectra, historical checkpoints, or generated caches. See the [reproducibility policy](DATA_AND_REPRODUCIBILITY.md) before treating a clean-code test run as reproduction of the historical training.
