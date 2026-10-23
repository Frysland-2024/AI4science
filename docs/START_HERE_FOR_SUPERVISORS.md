# Start here for supervisors

## One-minute overview

This is a machine-learning project on **PXRD seven-crystal-system classification**. The completed study asks whether simulator-known relationships between two measurements of the same parent crystal provide useful supervision beyond the class label:

> **Shared Parent Identity → Measurement Equivalence → Relationship Supervision**

The tested implementation compares Dynamic JS Consistency with matched Dynamic ERM using ResNet-18-GN. It improves simulated OOD Macro-F1 by **5.46 percentage points** over five matched seeds. Existing RRUFF-301 K=1/2/5 results are historical few-shot evidence; they do not answer the next zero-shot benchmark question.

**Only active scientific task:** improve and evaluate seven-system classification. The next stage has exactly three axes:

1. **RRUFF real-domain performance:** zero-shot Accuracy and Macro-F1, with fair literature comparisons only on matched spectra and protocols.
2. **Confidence calibration:** ECE primary; NLL, Brier score, and reliability diagrams supporting.
3. **Simulated-data efficiency:** performance versus unique training-parent count, comparing Dynamic ERM and Dynamic JS under matched budgets.

CNRS remains optional secondary-domain evidence. Quantitative parameter inversion, lattice recovery, Forward Reconstruction Loss, DONUT-inspired routes, and automatic refinement are **Archived / Inactive**.

## Five-minute reading path

| Time | Read | What it establishes |
|---|---|---|
| 0–1 min | [Repository README](../README.md) | Active task, completed findings, three axes, future plan |
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

## Future roadmap (planning only)

1. Audit and expand independent training-parent structures toward feasible 30k/60k/100k tiers; report actual per-class availability and deduplication.
2. Build a versioned dynamic simulator guided by SimXRD/Pysimxrd, preserving physically valid same-parent measurements and crystal-system labels.
3. Retune learning rate, batch size, scheduler, training steps/parent exposure, and JS weight for the new data and simulator. The historical JS weight 60 is not assumed optimal.
4. After data and simulation stabilize, conditionally compare SimXRD CNN11 or an optional multi-scale 1D CNN. ResNet-18-GN remains the historical baseline.

See the [full scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md). No items above should be described as implemented results.

## Reproducibility and scope

Start from [the current state](CURRENT_STATE.md), [result report](../xrd_robustness/reports/RESULTS.md), and [data/reproducibility policy](DATA_AND_REPRODUCIBILITY.md). The repository preserves frozen code/configs/results, negative and uncertain evidence, and historical parameter-inversion artifacts. The public tree does not contain all raw structures, spectra, generated caches, or checkpoints, so code checks alone do not reproduce historical training.

For research chronology, see [Project History](PROJECT_HISTORY.md). Older inversion and refinement plans remain linked there as history; they are not active task queues.
