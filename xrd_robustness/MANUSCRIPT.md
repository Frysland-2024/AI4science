# Measurement-Equivalence Supervision for Robust PXRD Classification

**Status:** manuscript scaffold with completed simulated, RRUFF-301 few-shot and CNRS-318 zero-shot results; figures and source-backed prose remain in progress.

**Updated:** 2026-08-28

**Result source:** [`reports/RESULTS.md`](reports/RESULTS.md)

## Abstract

Machine-learning analysis of powder X-ray diffraction (PXRD) commonly uses simulated training data, while measured patterns vary with peak shifts, broadening, preferred orientation, background and noise. We study an additional source of supervision created by online simulation: multiple perturbed patterns generated from one parent structure are related measurements of the same latent physical object. We add Jensen-Shannon prediction consistency between paired online views to a matched Dynamic ERM baseline while controlling the backbone, parent structures, perturbation distribution, optimization and data exposure. Across five matched seeds, consistency improves mean single-factor Validation-OOD Macro-F1 by `0.046569`, with all five effects positive. Evaluation of the already selected checkpoints on the simulated Test yields a mean paired improvement of `0.054600`, also positive in all five pairs. On experimental RRUFF-301, JS-pretrained representations improve locked-test Macro-F1 by `0.0433`, `0.0460` and `0.0545` under K=1/2/5 labels per class. On the independent CNRS-318 source, all five frozen zero-shot comparisons favor JS (mean paired delta `+0.0187`); pooled Macro-F1, balanced accuracy, accuracy, ECE, NLL and Brier score also improve. Statistical uncertainty is larger on naturally imbalanced CNRS, particularly because one crystal system has only 12 parents. Together, the simulated OOD, label-efficiency, independent-source and probability-quality evidence supports structured supervision for robust scientific classification while exposing a substantial remaining sim-to-real gap.

## 1. Research question

Does measurement-equivalence supervision improve simulated OOD robustness beyond matched dynamic augmentation for seven-crystal-system PXRD classification?

## 2. Methods

### 2.1 Task and data split

- Seven-class crystal-system classification from 1D PXRD.
- 14,060 parent structures: 9,842 Train, 2,109 Validation and 2,109 Test.
- Exact parent fingerprints define the split identity.

### 2.2 Matched comparison

- Backbone: ResNet-18-GN.
- Preprocessing: identity.
- Optimizer: AdamW.
- Learning-rate schedule: constant.
- Baseline: Dynamic ERM on two independently perturbed online views.
- Method: the same views and classification objective plus Jensen-Shannon prediction consistency with `lambda_js=60`.
- Five matched training seeds and identical data exposure.

### 2.3 Online measurement views

The simulator varies peak position, broadening, preferred orientation, background and noise. Each training step renders paired views from the same parent structure. The shared parent identity defines measurement equivalence and supplies the relationship used by the consistency objective.

### 2.4 Experimental domains

The models are additionally evaluated on two experimental domains with distinct roles. Both evaluations are complete and are reported separately.

- **RRUFF-301** — a class-balanced, curated experimental mineral domain (balanced curated experimental domain). Its role is **few-shot adaptation** (K=1/2/5) under the locked-test design recorded in the historical preregistration; because the prospective provenance is incomplete, the aggregates are treated as retrospectively verified rather than provenance-complete confirmatory results.
- **CNRS-318** — a naturally imbalanced, chemically diverse experimental domain derived from opXRD/COD after spectrum deduplication, structural-parent grouping, stable symmetry reconstruction and overlap exclusion (naturally imbalanced independent experimental domain; 318 independent structural parents with class counts `21 / 87 / 77 / 41 / 33 / 12 / 47`). Its role is **zero-shot external evaluation** of the frozen models, without touching any CNRS label for adaptation.

The primary CNRS comparison is the paired Macro-F1 difference between JS and ERM on identical parents, `Δ = F1_JS − F1_ERM`, with a class-stratified paired-parent bootstrap that preserves the natural class composition. Labels are structure-derived crystal-system labels, reconstructed from the deposited atomic basis and stable across symmetry tolerances; they were not independently verified by manual spectrum-level phase analysis. Hexagonal-specific conclusions remain underpowered.

### 2.5 Evaluation and reporting hierarchy

The main scientific interpretation follows a three-layer hierarchy. Layer A uses
community-standard PXRD / materials-ML performance evidence: effect sizes,
classification metrics, learning curves, matched-seed consistency and per-class
behavior. Layer B treats ECE, NLL, Brier score, entropy and confidence behavior as
supporting reliability evidence rather than replacements for F1/accuracy. Layer C
retains paired bootstrap confidence intervals, class-stratified parent resampling and
uncertainty decomposition as strict audit evidence. These analyses quantify certainty
and expose weak classes; a single interval crossing zero is not treated as an automatic
failure of an otherwise coherent cross-domain result.

## 3. Results

### 3.1 Simulated Validation

| Metric | Dynamic ERM | JS consistency | Paired delta |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

The primary OOD effect is positive for all five matched pairs, with a paired-bootstrap 95% interval of `[0.038145, 0.052834]`.

### 3.2 Simulated Test

- Mean single-factor OOD Macro-F1: `0.650737 ± 0.007208 → 0.705336 ± 0.009767`; mean paired delta `+0.054600`.
- Mean single-factor OOD Accuracy: `0.650782 ± 0.007804 → 0.705237 ± 0.008560`; mean paired delta `+0.054454`.
- Sample SD of the five paired Macro-F1 deltas: `0.007271`; the corresponding Accuracy-delta SD is `0.004149`.
- Paired-bootstrap 95% interval: `[+0.048944, +0.060255]`.
- Five of five primary Macro-F1, Accuracy and in-range paired effects are positive.

### 3.3 Experimental domains

RRUFF-301 provides the primary few-shot adaptation evidence. Under identical real-label
budgets and the same frozen-backbone adaptation procedure, JS-pretrained representations
improve locked-test Macro-F1 at every budget:

| RRUFF labels/class | Metric | Dynamic ERM (mean ± SD) | JS consistency (mean ± SD) | Mean paired delta | Positive pairs |
|---:|---|---:|---:|---:|---:|
| 1 | Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | +0.0433 | 21/25 |
| 1 | Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | +0.0384 | 20/25 |
| 2 | Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | +0.0460 | 23/25 |
| 2 | Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | +0.0488 | 23/25 |
| 5 | Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | +0.0545 | 24/25 |
| 5 | Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | +0.0568 | 23/25 |

For Macro-F1, all 5/5 pretraining seeds favor JS after averaging over episode seeds at
each label budget (68/75 individual matched comparisons are positive). The locked-test
statistics are retrospectively verified; the historical prospective provenance is
incomplete and is not described as a provenance-complete confirmatory execution.

CNRS-318 is a complementary zero-shot external-source stress test; no CNRS label is used
for adaptation or model selection. Seed-level Macro-F1 is
`0.188372 ± 0.026336 → 0.207085 ± 0.021336`; the mean of the five paired differences is
`+0.018713 ± 0.006754`, and all five differences are positive. Descriptively pooling
the five repeated predictions gives Macro-F1 `0.191176→0.209119`, balanced accuracy
`0.218225→0.238777`, ECE `0.682570→0.612420`, NLL `8.319988→6.118566`, and Brier
`1.433841→1.315606`. A corrected 10,000-replicate class-stratified paired-parent
bootstrap, sharing each parent draw across both methods and the five fixed training
seeds, gives `[−0.009339, +0.046107]`. This interval is retained as a strict uncertainty
annotation: the naturally imbalanced domain and its 12-parent hexagonal class limit the
precision of the effect estimate, but the interval does not override the 5/5 seed and
multi-metric agreement. All 318 parents are retained as frozen, with no post-hoc removal
after seeing predictions.

## 4. Discussion

The contribution is the use of simulator-retained parent identity as an equivalence relation for scientific measurements. The matched design isolates the value of this relationship while preserving structures, perturbations, optimization and data exposure. The Validation and Test results consistently support the same aggregate improvement in simulated PXRD robustness. RRUFF further supports improved few-shot adaptation efficiency, while CNRS contributes an independent-source zero-shot result in which all five seeds and several standard classification and reliability metrics favor JS. CNRS also exposes the remaining limitation: pooled overall accuracy is only `0.210`, below the natural-domain majority-class baseline of `0.274`, and both models remain strongly over-confident. Per-class gains are not uniform—monoclinic and tetragonal F1 decline under JS—and the 12-parent hexagonal class is underpowered, producing a wide paired-parent interval. The experimental-domain evidence therefore strengthens the robustness story without supporting a claim that sim-to-real classification is solved.

## 5. Figure plan

1. Online PXRD view generation and matched Dynamic ERM / JS objectives.
2. Five paired Validation effects.
3. Five paired simulated Test effects.
4. Aggregate metrics across clean, in-range and single-factor OOD panels.
5. RRUFF-301 few-shot label-efficiency comparison.
6. CNRS-318 construction funnel, natural class distribution, paired seed effects and per-class changes.

## 6. Submission-facing claim

Online PXRD simulation can supply measurement-equivalence supervision through shared parent identity. In a matched two-view design, JS consistency improves aggregate simulated OOD robustness, supports more label-efficient adaptation on RRUFF-301, and yields consistent five-seed, multi-metric gains on the independent CNRS-318 source, with larger uncertainty in that naturally imbalanced domain.

## 7. Remaining writing work

1. Complete the source-backed Introduction and Related Work.
2. Convert the fixed configurations into an exact Methods description.
3. Generate publication figures from the two result files.
4. Complete the Results and Discussion prose.
5. Integrate the completed RRUFF-301 and CNRS-318 figures, run record and limitations into the submission package.

## 8. Figure generation and provenance

From `xrd_robustness`, regenerate the four tracked manuscript figures with:

```bash
python scripts/generate_paper_figures.py
```

The tracked default is editable SVG. PNG and PDF remain available explicitly through
`--formats png` and `--formats pdf`. The generator reads experimental values only from
`reports/validation_results.json` and `reports/simulated_test_results.json`; before
writing output, it checks the stored paired runs against every published mean, sample
standard deviation, paired delta and available positive-pair count.

Figure 1 is a method schematic. Its deterministic spectrum sketches illustrate legal
paired measurement variation and are not experimental traces. Figures 2 and 3 draw the
five stored seed pairs. Figure 4 summarizes the four frozen simulated-Test metrics and
does not compare Validation and Test worst-class fields because their historical
aggregation definitions differ.

1. `figure_1_method_overview.svg`: paired PXRD views and Dynamic ERM / JS objectives.
2. `figure_2_validation_paired_ood.svg`: five paired Validation OOD effects.
3. `figure_3_simulated_test_paired_ood.svg`: five paired frozen-Test OOD effects and CI.
4. `figure_4_metric_overview.svg`: clean, in-range and OOD metric overview.
