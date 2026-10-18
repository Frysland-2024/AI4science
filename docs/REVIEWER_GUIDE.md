# Researcher's guide to AI4science

**Intended audience:** a prospective supervisor, a materials characterization researcher, or an ML researcher encountering this repository for the first time.

This guide is a navigation layer—not a replacement for the frozen experiment files or result reports. The [README](../README.md) gives the shortest overview; [CURRENT_STATE.md](CURRENT_STATE.md) is authoritative on scientific status.

## The 60-second explanation

**Task:** classify the **seven crystal systems** from powder X-ray diffraction patterns.

**Problem:** realistic measurement conditions can alter peak positions, widths, intensities, background and noise even when the underlying crystal structure is unchanged. A model fitted only to simulated data may generalize poorly.

**Observation:** when an online simulator generates two patterns from one crystal, it knows those patterns share **the same parent structure**, a stronger relationship than merely sharing a crystal-system label.

**Intervention:** keep the standard two-view cross-entropy objective and add **Jensen–Shannon consistency between the two predicted class distributions**. Compare against a **matched two-view Dynamic ERM** baseline, not a one-view baseline.

**Conclusion supported by the completed study:** the additional relationship-supervision term improves simulated OOD Macro-F1, the observed RRUFF-301 few-shot adaptation curve and the directional CNRS-318 zero-shot comparison. Absolute CNRS performance remains low and uncertain.

The simulator acts as both a **data generator** and a **relationship supervisor**. This is the method framing; JS divergence, online augmentation and ResNet are established components.

## What should I inspect first?

| If you have... | Read | Question answered |
|---|---|---|
| **2 minutes** | [README](../README.md), [method figure](../xrd_robustness/figures/figure_1_method_overview.png), [paired Test figure](../xrd_robustness/figures/figure_3_simulated_test_paired_ood.png) | What was tested and what changed? |
| **5 minutes** | [Main results](../xrd_robustness/reports/RESULTS.md), [experiment config](../xrd_robustness/configs/experiment.public.json) | Are the comparison, metrics and evaluation roles clear? |
| **15 minutes (ML)** | [Training objectives](../xrd_robustness/src/xrd_robustness/training/objectives.py), [online views](../xrd_robustness/src/xrd_robustness/online_views.py), [training runner](../xrd_robustness/src/xrd_robustness/training/runner.py), [method/fairness audit](PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md) | Is the incremental learning-method comparison controlled? |
| **15 minutes (materials / measurement)** | [PXRD simulation](../xrd_robustness/src/xrd_robustness/simulator.py), [physical perturbation evidence](PXRD_PERTURBATION_EVIDENCE.md), [RRUFF audit](../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md), [CNRS audit](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) | Are measurements, physics assumptions, source labels and sample identities addressed? |
| **30 minutes (reproducibility)** | [Data policy](DATA_AND_REPRODUCIBILITY.md), [result JSON](../xrd_robustness/reports/simulated_test_results.json), [test suite](../xrd_robustness/tests/), [CI](../.github/workflows/xrd-tests.yml) | What can be verified from a clone, and what requires external data and checkpoints? |

## Experimental design: the comparison that matters

~~~text
One parent crystal structure s; known crystal-system label y
                     |
          Online PXRD simulator
              /             \
      measurement m1      measurement m2
           |                   |
        view x1              view x2
           \                   /
         shared ResNet-18-GN classifier
                  |
       +----------+-----------+
       |                      |
    Dynamic ERM             Dynamic JS
   CE on both views     CE on both views + JS
~~~

The controlled difference is **the loss term**. Both methods use the same parent-level split, the same two-view exposure, the same perturbation distribution, the same architecture, and matched seeds/budgets. The public experiment contract specifies **14,060** parent structures, split **9,842 / 2,109 / 2,109**, and **five matched training seeds**. Hyperparameter selection occurs through validation; simulated Test and experimental sources are separate.

For the exact mathematical implementation and fairness checks, use the [method-detail audit](PXRD_METHOD_DETAIL_EVIDENCE_CLOSURE.md). For the physical construction and limits of measurement transformations, see [simulation config](../xrd_robustness/configs/simulation.method_transfer.frozen.json) and [perturbation evidence](PXRD_PERTURBATION_EVIDENCE.md).

## Three evaluations, three different claims

| Domain | Setup | What it does—and does not—show |
|---|---|---|
| **Simulated Test / OOD** | Parent-disjoint Test structures, held-out perturbation profiles, matched trained models | Strongest controlled evidence for a benefit from the JS training objective under the tested simulated shifts; **mean OOD Macro-F1 0.6507 → 0.7053**, +5.46 pp, five positive seed pairs |
| **RRUFF-301** | Experimentally measured, curated real domain; identical **K=1, 2, 5 labels/class** adaptation budgets with locked Test evaluation | Higher observed performance with the same few labels: paired Macro-F1 gains **+4.33 / +4.60 / +5.45 pp**. **Not** an unseen-mineral benchmark; shared mineral identity across support/test is allowed and documented |
| **CNRS-318** | Second real experimental source; naturally imbalanced and evaluated with **frozen models, zero-shot** | Directional relative advantage: seed-level Macro-F1 **0.1884 → 0.2071** (+1.87 pp; 5/5 seeds). Absolute accuracy is low, lower than the majority-class baseline; source labels were reconstructed from deposited structures, not manually checked spectrum by spectrum; the parent-bootstrap CI on the gain crosses zero |

Do **not** average these three numbers into a universal “real-XRD accuracy.” A secondary [calibration audit](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md) also documents ECE, NLL and Brier improvements, while explicitly noting the remaining overconfidence.

## What counts as original work here?

The research-level contribution is the **formulation, implementation, and controlled empirical study of simulator-parent provenance as supervision** for this scientific measurement task. Concrete technical work visible in the repository includes:

- parent-disjoint dataset and experiment specifications;
- physics-motivated measurement perturbations and online same-parent paired views;
- supervised two-view ERM vs JS objectives and a common network/training pipeline;
- multi-seed simulated OOD and experimental-domain evaluation;
- dataset/composition auditing, frozen configurations, tests, and result/provenance reporting.

The **ResNet implementation is adapted from ML4pXRDs** under the [third-party notice](../THIRD_PARTY_NOTICES.md). The repository **does not claim** invention of consistency regularization or of an entirely new backbone. Literature precedence and exact novelty boundaries are analyzed in [the lineage document](PXRD_NOVELTY_LITERATURE_LINEAGE.md).

## Scientific boundaries and incomplete tracks

- **Main study:** [xrd_robustness](../xrd_robustness/) — completed experimental comparisons, manuscript in progress.
- **Separate numerical investigation:** [xrd_inversion](../xrd_inversion/) — contains forward-model / recoverability gates; its formal report records **288/288** clean P2-R successes while other nominal-start and nuisance diagnostics fail. **No neural training** was run for those numerical gates, and this is **not** evidence of a completed ML inversion model.
- **Planned supplementary study:** [parent-structure efficiency protocol](PXRD_PARENT_STRUCTURE_EFFICIENCY_PLAN.md) — proposed test of whether JS extracts more value per **unique training crystal structure**; it has **no new result yet**.
- **Possible future thesis:** [physics-constrained parameter inversion](FUTURE_UNDERGRAD_THESIS_PLAN.md) — a **candidate plan**, not an approved or executed experiment.
- **Archived directions:** see [project history](PROJECT_HISTORY.md) and [factorization NO-GO archive](archive/XRD_FACTORIZATION_STAGE1_ARCHIVED_20260907.md). Failed routes and changes in interpretation are preserved rather than presented as results.

## Can an external reader reproduce it?

A fresh clone can install and run the public **non-data-bound tests**:

~~~bash
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q -m "not data_bound"
~~~

The public tree contains code, selected configs, compact manifests, results and auditing artifacts, **not** the entire external crystal corpus, raw spectra, historical trained checkpoints or generated caches. This means **code/contract verification and some result re-analysis are available**, whereas a faithful full training replication requires acquiring the external data and rebuilding local assets. Read the [reproducibility policy](DATA_AND_REPRODUCIBILITY.md) before interpreting the public test badge.

## Why did the project change?

The chronological record in [PROJECT_HISTORY.md](PROJECT_HISTORY.md) documents the evolution from earlier materials ML through PXRD measurement simulation, the Residual branch, a PAMPT-versus-ResNet learnability diagnosis, and eventual convergence on a **JS-only same-parent supervision** comparison. It distinguishes **scientific discoveries**, **negative results**, and **future ideas** rather than retroactively describing the current method as the initial plan.
