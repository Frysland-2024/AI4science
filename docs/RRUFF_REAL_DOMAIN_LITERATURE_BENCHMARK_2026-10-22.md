# RRUFF real-domain literature benchmark plan (2026-10-22)


**2026-11-03 source audit of FIVE papers' actual RRUFF screening cohorts:** [RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md](RRUFF_FIVE_PAPER_COHORT_SOURCE_AUDIT_20261103.md). This distinguishes Lee's top-40% low-angle-background rejection, Salgado's 452-real-spectrum souping, AlphaDiffract's exact 734 chain, XQueryer's 2,088→1,003 data-adequacy filtering and 849 separate MP matches, and the still-unknown SimXRD Table-5 test denominator. **Publication targets do not authorize score-conditioned filtering of a locked test.**

**2026-11-03 presentation style + expanded model-variant library:** [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md) (user-approved AlphaDiffract Table-1 minimalist dark presentation reference; Vecsei 2019 Dense/CNN; Choudhary 2025 DGPT-formula; SimXRD Table-5 same-paper architectures). This comparison expansion does **not** change the grading tiers. Source SVG: [assets/alpha_diffract_2026_table1_style_reference.svg](assets/alpha_diffract_2026_table1_style_reference.svg).

## CURRENT ACCEPTANCE SCORECARD — owner decision, 2026-11-03

**Only three top-level research outcomes are assessed: (1) real-RRUFF seven-crystal-system top-1 Accuracy; (2) unique-CIF-parent data-efficiency curve; (3) ECE / probability calibration.** RRUFF Accuracy is the **sole criterion for the 60/80/100 project-performance grade**; data efficiency and ECE remain complementary headline evidence, not substitutes for RRUFF classification performance. Simulated OOD F1 is an internal optimization metric, not a final-grade score. Retain negative historical results and full scientific audit separately.

**Owner-frozen literature tiers — 2026-11-03 latest correction: ZERO-SHOT RESULTS ONLY.** Here zero-shot means **no labeled RRUFF spectra were used for training/fine-tuning**. The final project must also freeze the model without searching the locked RRUFF test. Some source papers consulted RRUFF for design decisions, so *zero labeled adaptation* must not be misrepresented as *fully target-domain blind*.

| Grade tier | Named paper and selected model condition | RRUFF crystal-system Accuracy | Labeled RRUFF training / fine-tuning count | Priority / qualification |
| --- | --- | ---: | ---: | --- |
| **Pass / 60** | **Vecsei et al. 2019, Dense/MLP** | **70.0%** | **0** | **Qualifies as PASS**; historical RRUFF classification reference reported in AlphaDiffract 2026 Table 1; paper-specific cohort |
| **Pass / 60** | **Lee 2023, large FCN** | **74.24%** | **0** | Zero-shot reference |
| **Pass / 60** | **Salgado 2023, synthetic-only NPCNN** | **about 74%** | **0** | **Use this model result, NOT the 86% adapted result** |
| **80** | **AlphaDiffract 2026, 10-model ensemble** | **81.74 ± 0.78%** | **0** | **PRIMARY 80-tier**; RRUFF-informed simulation noise statistics and loss selection, not strictly domain-blind |
| **Full / 100** | **SimXRD-4M 2025, CNN11** | **89.3%** | **0** | Zero-shot RRUFF |
| **Full / 100** | **XQueryer-NoElem 2025** | **91.5%** | **0** | Zero-shot RRUFF; PXRD-only |

**Explicitly excluded from acceptance tier:** Salgado's **86%** 'Large Souping' result trained on about **452 labeled RRUFF profiles** and evaluates a different held-out split; it remains source evidence in historical protocol audit, but must NOT appear as a graded zero-shot comparator. Paper cohorts and filters differ; these percentages are literature target markers, not a same-test-set leaderboard.

**Owner-added below-pass RRUFF competitor (INCLUDED, not excluded):** **Choudhary 2025, DiffractGPT DGPT-formula — 28.75% RRUFF crystal-system Accuracy**, as **third-party evaluated by AlphaDiffract 2026 Table 1 on its own RRUFF cohort**, NOT an Accuracy claimed in the original Choudhary 2025 paper. Choudhary trained DiffractGPT using JARVIS-DFT simulated structures and PXRD, without reported labeled RRUFF training; its `DGPT-formula` variant additionally receives chemical formula. Both features must be disclosed but do **not** bar inclusion in the actual RRUFF performance comparison. This model is a **below-pass external benchmark**, not a new owner-defined 60/80/100 target. Full details in [model comparison library](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md) and [original DiffractGPT paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874033/).

**2026-11-03 latest pass-tier clarification:** Vecsei et al. 2019 **Dense (MLP) 70.0% RRUFF Accuracy is an explicit PASS/60 reference**, alongside Lee 74.24% and Salgado synthetic-only ~74%. Vecsei 2019 CNN 56.0% remains a comparison result **below** the pass tier; Choudhary DGPT-formula 28.75% remains included as an external result below pass. This change does not move AlphaDiffract 2026 (80) or SimXRD/XQueryer-NoElem (full), or imply paper cohorts are identical.

**Mandatory comparison-table columns, always:** Paper/model | **number of simulated independent crystal structures / curated CIF records** (distinguish duplicate records from verified unique parents) | **actual number of real RRUFF spectra in the evaluation** (report source catalog separately if metric denominator unknown) | **RRUFF Accuracy** | **number of labeled real RRUFF spectra used for training/adaptation**. For AlphaDiffract, also note RRUFF statistical-domain information use and ten-model ensemble. In grading rows, use ONLY Salgado's synthetic-only ~74% result with 0 RRUFF labels; preserve its 86%/452-real-label result in a separate historically informative, non-grading row.

**Acceptance and fairness boundary:** This is a simple owner-defined *literature reference scorecard*, NOT a claim that published results were measured on the same RRUFF IDs / curation / instrument / preprocessing / class distribution. Use these scores to communicate ambitions; record matched-test re-evaluation whenever reproducible, and label unmatched papers as reference thresholds. Never select hyperparameters by repeatedly consulting a locked real-RRUFF test. Never call use of unlabeled target-domain statistics 'strict target-domain blind'.

**Other two headline deliverables:** (2) **data-efficiency curve** uses the count of independent **training CIF parents**, not synthetic spectra produced from the same CIF, with matched simulator/optimization protocol and explicitly named output-domain score (ideally RRUFF Accuracy when sufficient frozen real-domain cohorts exist; otherwise simulated-validation efficiency must be labeled as supportive and cannot silently become the RRUFF grade). (3) **ECE** is an explicitly named domain's calibration metric (ideally RRUFF ECE for the final model), report its bins/calibration protocol and do not treat it as Accuracy.

**Current code-stage dependency is unchanged:** finish bounded architecture+Optuna tuning on synthetic validation, then resume independent CIF data expansion, then execute final RRUFF evaluation after protocol freeze. This grading declaration does not mean RRUFF test is authorized for exploratory tuning, does not auto-start Stage 3, and does not retroactively change frozen earlier experiments.

## Status and purpose
**PLANNING ONLY; no new scores, training, model inference, or benchmark creation is claimed by this document.** The project lead specified that the next crystal-system-classification objective is **comparison against published work on real RRUFF PXRD data**, not merely simulated accuracy. Archive quantitative parameter inversion as an inactive exploration.

Keep the original RRUFF-301 results, its adaptation-pool/locked-test split, raw predictions, all negative findings, and historical evaluation protocol unchanged. This is a new extension, not a rewrite of the existing confirmatory study.

## Current in-house evidence
- RRUFF-301 = 70 adaptation-pool spectra + 231 locked-test spectra, seven-class balanced design. See `xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`.
- K=1/2/5 real spectra/class adaptation, Dynamic ERM vs Dynamic JS:
  - K=1 Macro-F1 0.2847 vs 0.3280; Accuracy 0.2990 vs 0.3375
  - K=2 Macro-F1 0.3026 vs 0.3486; Accuracy 0.3120 vs 0.3609
  - K=5 Macro-F1 0.3555 vs 0.4099; Accuracy 0.3581 vs 0.4149
- JS improves over matched ERM in most pairs, but these scores do NOT establish superiority to published RRUFF systems.

## RRUFF literature evidence (author-reported; NOT directly comparable)
| Work | Real-data setting | Reported 7-crystal-system outcome | Critical comparability issue |
| --- | --- | --- | --- |
| Vecsei et al., Phys Rev B (2019) | ~800 RRUFF experimental spectra | ~70% Accuracy in a revised network, reported by later review | Different spectra/quality/split |
| Lee et al., Adv Intelligent Systems (2023) | RRUFF Ex_dataset_2: 1,600 collected; high-background top 40% excluded | 74.24% Accuracy best RRUFF model (large FCN, perturbed + texture). The 90.38% result is **NOT RRUFF**; it is Ex_dataset_1 (52 lab-measured compounds) | Filtered RRUFF subset, unmatched test set |
| Salgado et al., npj Comput Mater (2023) | 908 RRUFF; 'Large Souping' adds ~452 real spectra to training, other half evaluated | 86% Accuracy, F1 0.859, after 50% real-data inclusion. Synthetic-only large model ~74% Accuracy | Data composition unbalanced, approximately half RRUFF training labels; their RRUFF set has no trigonal class |
| Cao et al., SimXRD-4M, ICLR (2025) | models trained/validated on SimXRD, RRUFF evaluated without target fine-tuning | CNN11 89.3% Accuracy, F1 0.920; table 5 | Substantially larger/higher-fidelity synthetic training data, exact eval IDs need confirmation |
| Cao et al., XQueryer, Natl Sci Rev (2025) | 1,003 cleaned RRUFF experimental spectra | XQueryer 93.3% Accuracy / F1 0.920; **NoElem** 91.5% Accuracy / F1 0.905 | XQueryer full version uses element information. NoElem is the more relevant pattern-only benchmark; unmatched RRUFF selection |
| Andrejevic et al., AlphaDiffract (arXiv preprint 2026-03) | real RRUFF benchmark, simulated pretraining ~31M patterns | 81.7% crystal-system Accuracy | Multi-task prediction and different simulation/test setting; preprint status |

Primary references:
- https://doi.org/10.1103/PhysRevB.99.245120
- https://doi.org/10.1002/aisy.202300140
- https://www.nature.com/articles/s41524-023-01164-8
- https://proceedings.iclr.cc/paper_files/paper/2025/file/b04843d76c9f090beca55f335c4ea6bf-Paper-Conference.pdf (Table 5)
- https://academic.oup.com/nsr/article/12/12/nwaf421/8268901 (Table 1)
- https://arxiv.org/abs/2603.23367

Do **not** equate Accuracy and Macro-F1, or combine results on different RRUFF selection manifests. Paper-reported F1 may use distinct averaging conventions; audit their definitions.

## Two complementary evaluation tracks
**Track A — fixed in-house RRUFF-301 evaluation (highest immediate priority):**
- Never change current frozen IDs, labels, train/test split, seed list, and past outputs.
- Try published models using released weights / code on **the same 231 spectra** (after separately auditing wavelength, 2theta range, preprocessing compatibility, labels and input conditions). If a model lacks released weights or cannot accept equivalent inputs, mark `not directly reproducible` instead of inventing results.
- Compare zero-shot (no RRUFF use at all) separately from target-domain adaptation. For few-shot, all **adaptable** baselines receive the same support IDs at K=1,2,5, no additional labeled RRUFF samples and equivalent validation selection. For architectures that cannot fine-tune, report zero-shot only.
- Report Accuracy, Macro-F1, Balanced Accuracy, per-class F1, confusion matrix, training structure count, simulated spectra exposure, parameter count, GPU/compute and whether elemental composition is supplied. Distinguish shared-mineral identity from unseen-mineral generalization; existing RRUFF-301 is NOT mineral-disjoint.

**Track B — independent public/literature-aligned RRUFF benchmark (after data feasibility audit):**
- Recover **exact case IDs and curation** for published 908/1003 RRUFF releases where possible, or construct a new prospectively frozen real-data set; document inability to reproduce any unpublished selection.
- Before comparing methods, lock labels, wavelength, angular range, contamination checks, parent/mineral duplication audit, preprocessing and evaluation code. Do not use the previously evaluated RRUFF-231 test for tuning.
- Compare a pure-PXRD model to XQueryer-NoElem and SimXRD CNN11; put XQueryer with composition in a distinct `PXRD + chemistry` track.
- For paper-aligned zero-shot, zero experimental RRUFF labels are used for model selection or training; for few-shot, publish K/class, split hashes and source domain split. Do not mix them on one ranking.
- A new external split is required to support fresh confirmatory claims, because the old locked test is already evaluated.

## Prioritized execution gates
1. **Feasibility:** obtain public checkpoints, licenses, code and exact dataset IDs for SimXRD CNN11, XQueryer-NoElem, Salgado NPCNN, AlphaDiffract; classify each baseline as executable / needs retraining / irreproducible.
2. **Input/split audit:** annotate RRUFF-301 spectrum wavelength, angular range and preprocessing; document any mismatch and no-data-leakage, with only non-destructive adapters.
3. **Matched inference:** run available published model checkpoints on identical RRUFF-231 without test-driven tuning. If supported, also run a strictly 0-shot comparison.
4. **Matched few-shot:** on existing 70-sample adaptation pool, compare ERM and JS to reproducible baselines at identical K, no transductive access to test data.
5. **External prospective replication:** freeze a literature-aligned or newly curated larger real-domain benchmark, then report performance and costs on that benchmark.
6. **Analysis and write-up:** preserve negative results; distinguish absolute benchmark accuracy from attributable gains of same-parent consistency. Rank by matched evaluation only.

## Research decision framing
The realistic immediate objective is **credible head-to-head RRUFF reproducibility and improvement over comparable baselines at matched real-data budgets**. There is presently no evidence that the current model beats literature's 74–93% RRUFF results. The higher numbers show that scaling/physical fidelity/representation and real-label access materially affect the ceiling, but cannot isolate a single cause without controlled tests.

## 2026-11-03 addendum — five-column RRUFF comparison

**Owner-requested comparison format:** simulated crystal-structure count, real RRUFF evaluation count, RRUFF seven-crystal-system Accuracy, and labeled real RRUFF data used for training/adaptation. This is a literature-reference table, not a strict same-test-cohort leaderboard. The original Lee / SimXRD / XQueryer-NoElem acceptance roster remains unchanged; AlphaDiffract is an **additional comparator**, not a replacement or newly assigned grade tier.

| Paper / model | Curated simulated structure records (CIF) | RRUFF classification evaluation count | RRUFF seven-system top-1 Accuracy | Labeled RRUFF training / fine-tuning spectra |
| --- | ---: | --- | ---: | ---: |
| Lee et al. 2023, Large FCN | 197,131 ICSD | ~1,600 initially acquired; after 40% background exclusion **Unknown** | 74.24% | 0 |
| **Andrejevic et al. 2026, AlphaDiffract (10-model ensemble)** | **312,267** ICSD+MP, not cross-source deduplicated | **734 classification profiles** | **81.74 ± 0.78%** | **0 labeled**¹ |
| Cao et al. 2025, SimXRD-4M CNN11 | 119,569 MP | 3,002 in catalog; exact Table 5 cohort **Unknown** | 89.3% | 0 |
| Cao et al. 2025, XQueryer-NoElem | 100,315 MP | 1,003 | 91.5% | 0 |
| Salgado et al. 2023, Large Souping | 171,006 ICSD | 908 original entries; exact held-out test count **Unknown** | 86% | ~452 labeled |

¹ **Important AlphaDiffract protocol nuance:** The source reports *zero labeled RRUFF samples for neural training or fine-tuning*, but **RRUFF measurements were used to characterize Poisson/Gaussian noise for synthetic augmentation** (Methods §5.2) and the authors consulted RRUFF performance in choosing the space-group GEMD weight μ=1 (§2.3). Do **not** describe this as strictly target-domain-blind, or as zero use of RRUFF measurements. The 734 classification entries include 59 powder profiles computed from single-crystal data (Methods §5.1), despite inclusion in the RRUFF benchmark. **312,267 is a curated structure-record count, not a formally proven number of distinct parent structures**: the authors state that duplicates were not removed prior to later curation (Methods §5.1). The 81.74% result is specifically the **10-model ensemble**, not a single released checkpoint; the separate publicly released MP-only single-model implementation reports materially different RRUFF performance and must not be conflated with it.

Primary original source: Andrejevic et al., *AlphaDiffract: Automated Crystallographic Analysis of Powder X-ray Diffraction Data* (arXiv:2603.23367v1), https://arxiv.org/html/2603.23367v1 , §2.3, Table 1, §5.1, §5.2 and §5.6. Other sources for existing rows and caveats appear in this document and `docs/RRUFF_JS_BENCHMARK_PROTOCOL_AUDIT_2026-11-03.md` (local audit file).

**How to read this table:** RRUFF spectra and preprocessing differ across papers. Comparing author-reported percentages as *targets* is useful, but claiming a controlled direct head-to-head comparison requires identical evaluation sample IDs and labels (and the same adaptation budget and input metadata). The final project's official paper-tier roster is not changed by this additional row. Simulated validation performance is not a substitute for final RRUFF Accuracy.
