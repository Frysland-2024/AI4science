# Start here for supervisors

## One-minute overview

This is a machine-learning project on **PXRD seven-crystal-system classification**. The completed study asks whether simulator-known relationships between two measurements of the same parent crystal provide useful supervision beyond the class label:

> **Shared Parent Identity → Measurement Equivalence → Relationship Supervision**

The tested implementation compares Dynamic JS Consistency with matched Dynamic ERM using ResNet-18-GN. It improves simulated OOD Macro-F1 by **5.46 percentage points** over five matched seeds. Existing RRUFF-301 K=1/2/5 and CNRS-318 results are supporting completed evidence and must be reported with their task and uncertainty limits.

**Only current undergraduate thesis line (decision dated 2026-10-26):** complete the write-up and defense of this frozen seven-system classification study. Its research question is whether same-parent measurement-equivalence supervision improves classification over matched Dynamic ERM. **No new experiments are in the current thesis scope.**

The simulated parent-budget study is supplementary post-main evidence and does not support a quantitative structure-saving claim. New RRUFF zero-shot evaluation, calibration runs, simulator upgrades, larger-parent training, retuning, and new architecture comparisons are deferred.

## Five-minute reading path

| Time | Read | What it establishes |
|---|---|---|
| 0–1 min | [Repository README](../README.md) | Current thesis scope, completed findings, and deferred proposals |
| 1–2 min | [Same-parent method figure](../xrd_robustness/figures/figure_1_method_overview.png) | How simulator-retained parent identity becomes relationship supervision |
| 2–3 min | [Frozen results](../xrd_robustness/reports/RESULTS.md) | Exact simulated, RRUFF few-shot, and CNRS results and limits |
| 3–4 min | [Calibration analysis](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md) and [parent-budget analysis](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md) | Existing reliability and data-efficiency evidence; neither establishes RRUFF calibration or structures saved |
| 4–5 min | [Current state](CURRENT_STATE.md) and [project history](PROJECT_HISTORY.md) | Current decision, research transitions, and historical proposals |

## Completed evidence and limitations

- **Simulated OOD:** Dynamic JS Macro-F1 0.65074 → 0.70534; paired gain +0.05460, positive in 5/5 matched seeds.
- **RRUFF-301 few-shot:** Macro-F1 gains +0.0433 / +0.0460 / +0.0545 at K=1/2/5. This is a curated few-shot adaptation task, not the new zero-shot leaderboard.
- **CNRS-318 zero-shot:** Macro-F1 gain about +0.0187, but absolute Accuracy is 0.210, below the 0.274 majority-class baseline; the strict corrected paired-parent interval spans zero. The results remain reported with these limitations.
- **Parent budget:** the frozen 10/25/50/100% supplement found higher OOD Macro-F1 for JS at each matched budget. It reused the already evaluated simulated Test and does **not** establish a measured structure-count saving.
- Existing simulated-domain and CNRS calibration analyses are historical. The planned RRUFF ECE evaluation has not been completed.

## Parameter-inversion disposition

The thesis remains the frozen seven-system classification study. Parameter inversion is a historical side line and is **Archived / Inactive** for current thesis work.

**PR #36 is completed conditional synthetic evidence.** Its four-stage report used one known COD 9014273 BaTiO3 P4mm CIF, a frozen 358/77/77 split, three seeds, and 77 test parents per seed. In Exp 4, direct normalized-q MAE was **0.033607/0.033578/0.034282** for A/B/C and **0.228037** for DONUT-PXRD; after the same bounded joint q+instrument L-BFGS-B refinement, the results were **0.000343/0.000350/0.000341** for A/B/C and **0.080026** for DONUT-PXRD. The refined score is not direct neural accuracy, and the A/B/C refined scores are nearly tied. Keep this only as feasibility evidence for the one known-CIF synthetic setup; it says nothing about real-XRD accuracy, unseen-material transfer, multiphase inversion, or broad neural superiority. The [final report](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-experiment-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md) is on closed, unmerged PR #36.

PR #46 is a partial synthetic benchmark retained as historical exploration: 42 models, 8,085 primary rows, **0/42** passing the q-accuracy gate, **41/42** meeting the per-DOF cell-MAE constraint, **42/42** meeting the convergence comparison, and **41/42** meeting the amortized runtime gate. The PR43 held-out parents had already been evaluated; new-architecture stress was not run and real RRUFF validation was blocked/not run. It does not establish method superiority or real-domain validity.

Other branch boundaries: [PR #43](https://github.com/Frysland-2024/AI4science/pull/43) is a closed, unmerged synthetic pilot with no added parameter accuracy/reliability over P0/P3; [PR #45](https://github.com/Frysland-2024/AI4science/pull/45) E1 met no preregistered incremental-value rule against H1/P0 and E2 is `PHYSICS_NOT_READY / NN_NOT_RUN`; [PR #42](https://github.com/Frysland-2024/AI4science/pull/42) is closed/unmerged documentation with a DONUT summary superseded by PR #36's final report. [PR #48](https://github.com/Frysland-2024/AI4science/pull/48) is merged classification material, not inversion evidence.

Do not claim that PR #36 or PR #46 established general parameter-inversion reliability, real-domain accuracy, cross-material transfer, or neural superiority over strong physical methods. PR #46 also does not reproduce XQueryer, SimXRD-4M, CPICANN, or PyWPEM. Treat PR #43/#45 E1 as completed exploratory comparisons with bounded negative/limited findings, PR #45 E2 as a readiness gate with no NN run, and PR #46's successful thresholds/rows as exploratory engineering evidence. These archival labels describe project status; they do not erase PR #36's conditional result.

## Deferred proposals

The 2026-10-23 scale-up plan is retained for history but is deferred; it is not a thesis checklist or active task. No simulator, data, training, calibration, or RRUFF benchmark work is being started under the current thesis decision.

## Reproducibility and scope

Start from [the current state](CURRENT_STATE.md), [result report](../xrd_robustness/reports/RESULTS.md), and [data/reproducibility policy](DATA_AND_REPRODUCIBILITY.md). The repository preserves frozen code/configs/results, negative and uncertain evidence, and historical parameter-inversion artifacts. The public tree does not contain all raw structures, spectra, generated caches, or checkpoints, so code checks alone do not reproduce historical training.

For research chronology, see [Project History](PROJECT_HISTORY.md). Older inversion and refinement plans remain linked there as history; they are not active task queues.
