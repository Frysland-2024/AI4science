# Measurement-Equivalence Supervision for Robust PXRD Classification

**Status:** manuscript scaffold from the simulated results

**Updated:** 2026-08-23

**Result source:** [`reports/RESULTS.md`](reports/RESULTS.md)

## Abstract

Machine-learning analysis of powder X-ray diffraction (PXRD) commonly uses simulated training data, while measured patterns vary with peak shifts, broadening, preferred orientation, background and noise. We study an additional source of supervision created by online simulation: multiple perturbed patterns generated from one parent structure are related measurements of the same latent physical object. We add Jensen-Shannon prediction consistency between paired online views to a matched Dynamic ERM baseline while controlling the backbone, parent structures, perturbation distribution, optimization and data exposure. Across five matched seeds, consistency improves mean single-factor Validation-OOD Macro-F1 by `0.046569`, with all five effects positive. Evaluation of the already selected checkpoints on the simulated Test yields a mean paired improvement of `0.054600`, also positive in all five pairs. These results show how simulator-retained relationships can provide structured supervision for robust scientific classification.

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

- Mean paired single-factor OOD Macro-F1 delta: `+0.054600`.
- Sample SD across five pairs: `0.007271`.
- Paired-bootstrap 95% interval: `[+0.048944, +0.060255]`.
- Five of five OOD and in-range paired effects are positive.

## 4. Discussion

The contribution is the use of simulator-retained parent identity as an equivalence relation for scientific measurements. The matched design isolates the value of this relationship while preserving structures, perturbations, optimization and data exposure. The Validation and Test results consistently support the same aggregate improvement in simulated PXRD robustness.

## 5. Figure plan

1. Online PXRD view generation and matched Dynamic ERM / JS objectives.
2. Five paired Validation effects.
3. Five paired simulated Test effects.
4. Aggregate metrics across clean, in-range and single-factor OOD panels.

## 6. Submission-facing claim

Online PXRD simulation can supply measurement-equivalence supervision through shared parent identity. In a matched two-view design, JS consistency improves aggregate simulated OOD robustness relative to Dynamic ERM across five training seeds and a simulated Test.

## 7. Remaining writing work

1. Complete the source-backed Introduction and Related Work.
2. Convert the fixed configurations into an exact Methods description.
3. Generate publication figures from the two result files.
4. Complete the Results and Discussion prose.
