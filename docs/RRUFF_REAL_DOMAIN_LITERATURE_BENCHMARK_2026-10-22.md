# RRUFF real-domain literature benchmark plan (2026-10-22)

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
