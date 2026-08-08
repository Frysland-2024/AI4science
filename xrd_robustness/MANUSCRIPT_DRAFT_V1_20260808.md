# Manuscript Draft V1 — Measurement-Equivalence Supervision for Robust PXRD Learning

**Draft date:** 2026-08-08  
**Status:** manuscript-building from frozen evidence  
**Do not use this draft to reopen method selection or trigger unregistered experiments.**

## Working title options

1. **From Data Generation to Measurement-Equivalence Supervision: Consistency Learning for Robust Powder X-Ray Diffraction Classification**
2. **Leveraging Simulator Provenance for Robust and Label-Efficient Powder X-Ray Diffraction Learning**
3. **Physics-Paired Consistency Improves Robustness and Few-Shot Experimental Adaptation in Powder X-Ray Diffraction**

## One-sentence contribution

Online PXRD simulation provides more than scalable augmented spectra: by retaining parent-structure provenance, it defines physically related observations of the same latent crystal structure, and explicitly using this relation through JS consistency improves both simulated OOD robustness and low-label adaptation to experimental RRUFF spectra relative to matched Dynamic ERM.

## Abstract — first draft

Machine-learning analysis of powder X-ray diffraction (PXRD) commonly relies on synthetic training data because large, consistently labeled experimental datasets are difficult to obtain. Prior work has shown that physically informed perturbations and on-the-fly generation can greatly expand the support of synthetic training distributions. We investigate an additional source of supervision created by this simulation process: multiple perturbed patterns generated from the same parent crystal structure are not merely samples with the same class label, but physically related observations of the same latent structure. We therefore augment a matched dynamic-augmentation baseline with Jensen–Shannon prediction consistency between paired online views while keeping the backbone, parent structures, perturbation distribution, data exposure, and optimization protocol controlled. Across five preregistered training-seed pairs, JS consistency improves mean single-factor Validation-OOD Macro-F1 by 0.0466 over Dynamic ERM, with all five paired effects positive; a frozen simulated Test independently confirms the direction with a mean paired improvement of 0.0546. We then evaluate transfer to experimental RRUFF PXRD using a preregistered 301-spectrum confirmatory protocol. Under 1-, 2-, and 5-shot adaptation per crystal system, JS-pretrained representations improve Macro-F1 over ERM-pretrained representations by 0.0433, 0.0460, and 0.0545, respectively, with 68 of 75 paired comparisons positive. Class-level analysis shows that the benefit is broad but not uniform, motivating restrained aggregate rather than universal robustness claims. These results suggest that simulator provenance can be used as structured supervision, extending the role of synthetic-data engines from distribution expansion toward learning measurement-stable scientific representations.

## 1. Introduction — argument skeleton

### 1.1 Experimental PXRD is a difficult deployment domain

PXRD is widely used to infer structural information, but experimental patterns vary because of peak shifts, broadening, preferred orientation, background, noise, instrumental effects, sample preparation, and other measurement factors. Deep-learning models trained on idealized or limited simulated spectra can therefore fail under simulation-to-experiment distribution shift.

### 1.2 Existing synthetic-data work establishes the correct starting point

The manuscript should position physical perturbation augmentation and on-the-fly PXRD generation as strong prior foundations rather than strawman baselines. The key literature line is:

- physics-informed perturbation broadens synthetic realism;
- large-scale and on-the-fly simulation increases coverage;
- a simulator can produce many unique training observations efficiently.

The present work builds on that foundation rather than challenging its value.

### 1.3 The additional opportunity: provenance is supervision

Let

`x = g(s, m)`

where `s` is the latent crystal structure and `m` represents measurement/sample conditions. For a fixed parent structure:

`x1 = g(s, m1)`  
`x2 = g(s, m2)`

Both observations share the same crystal-system label, but their relation is stronger than class equality: they are measurements of the same physical parent structure.

Dynamic ERM uses:

`CE(f(x1), y) + CE(f(x2), y)`

and treats the two views as independent labeled examples at the objective level.

The proposed training objective adds:

`lambda_JS * JS(f(x1), f(x2))`

so that the complete predictive distributions remain locally stable along label-preserving measurement transformations.

### 1.4 Research questions

**RQ1.** Does explicit paired prediction consistency improve robustness beyond matched dynamic augmentation when both methods see the same parent structures, perturbation distribution, and two online views?

**RQ2.** Does a representation learned with measurement-equivalence supervision transfer more efficiently to experimental PXRD when only a few real labels are available?

**RQ3.** Are the gains uniform across crystal systems and perturbation conditions, or do important boundaries remain?

## 2. Methods — frozen structure

### 2.1 Data and split

- 14,060 parent crystal structures.
- Parent-structure split: 9,842 Train / 2,109 Validation / 2,109 Test.
- No derived spectrum from one parent crosses splits.
- Seven crystal-system classification task.

### 2.2 Online physical perturbation simulator

Describe the active perturbation families and their physical motivation. Keep simulator details sufficient for reproduction but do not make simulator novelty the primary contribution.

### 2.3 Shared backbone and optimization

- ResNet-18-GN.
- Identity preprocessing.
- AdamW.
- Constant learning rate.
- Shared budget and checkpoint-selection protocol.

### 2.4 Dynamic ERM baseline

For each parent structure, draw two independent online physical views and train with the average classification cross-entropy.

### 2.5 JS consistency

Use the same two online views and add Jensen–Shannon divergence between their predicted class distributions.

Selected and frozen weight: `lambda_js = 60`.

Crucial fairness statement: the comparison changes the learning objective, not data exposure, backbone, split, perturbation distribution, or number of forward views.

### 2.6 Statistical design

- five matched training seeds;
- paired method comparison within seed;
- parent structures remain the scientific sampling unit where applicable;
- no seed exclusion;
- Validation selects method settings before locked simulated Test;
- simulated Test cannot reopen method choice.

### 2.7 RRUFF-301 confirmatory adaptation

- 301 experimental RRUFF spectra, 43/class;
- 70-spectrum adaptation pool, 10/class;
- locked 231-spectrum test, 33/class;
- K = 1, 2, 5 examples per class;
- five pretraining seeds × five episode seeds;
- frozen convolutional backbone;
- projection + classification head adapted with AdamW;
- primary metric: paired ΔMacro-F1 (JS-pretrained minus ERM-pretrained).

The v1 split-label bug is disclosed in the audit trail and must not be mixed into v2 results.

## 3. Results — frozen order

### 3.1 JS improves controlled simulated Validation robustness

Primary evidence:

- Dynamic ERM OOD Macro-F1: 0.658495;
- JS OOD Macro-F1: 0.705064;
- paired mean Δ: **+0.046569**;
- paired-bootstrap 95% interval: `[0.038145, 0.052834]`;
- all five matched seeds positive.

The in-range guardrail also improves by +0.027991, so the OOD gain is not obtained by sacrificing the registered ID/in-range criterion.

### 3.2 Frozen simulated Test independently confirms the effect

Primary evidence:

- mean five-pair OOD Macro-F1 Δ: **+0.054600**;
- sample SD: 0.007271;
- paired-bootstrap 95% interval: `[+0.048944, +0.060255]`;
- all five paired effects positive.

The manuscript must note that the benefit is aggregate; monoclinic and selected shift/texture profiles remain limitations.

### 3.3 JS-pretrained representations adapt more efficiently to experimental RRUFF PXRD

| K | ERM Macro-F1 | JS Macro-F1 | Paired mean Δ | Positive/25 |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | **+0.0433** | 21 |
| 2 | 0.3026 | 0.3486 | **+0.0460** | 23 |
| 5 | 0.3555 | 0.4099 | **+0.0545** | 24 |

Across all three K values, 68/75 paired comparisons are positive.

The fixed-200-step sensitivity check preserves the direction at K=1 and K=5, reducing concern that the result is driven by the support-loss early-stopping rule.

### 3.4 Gains are broad but class dependent

Use the confirmatory v2 per-class analysis rather than the exploratory RRUFF-70 pattern. Important observations:

- triclinic, orthorhombic, and hexagonal show strong positive average effects across several K values;
- monoclinic negative transfer from the RRUFF-70 pilot does not replicate in the confirmatory cohort;
- trigonal and cubic remain K-dependent and can show negative average effects at some budgets;
- therefore the conclusion is label-efficient aggregate adaptation, not universal class-wise improvement.

### 3.5 Calibration and confidence diagnostics

Move ECE, NLL, Brier score, reliability/confidence plots, and detailed representation diagnostics to Supplementary unless one result is necessary to explain the principal mechanism.

## 4. Discussion — first draft structure

### 4.1 From synthetic-data volume to supervision structure

The central conceptual contribution is not that JS divergence is new. It is that parent-structure provenance in an online scientific simulator supplies an equivalence relation that standard label-only ERM does not explicitly encode. The simulator can therefore play two roles:

1. expand the measurement distribution;
2. identify which observations correspond to the same latent physical object.

### 4.2 Why consistency is an appropriately weak assumption

The method does not require explicit disentanglement of crystal semantics from measurement factors. It only requires predictions to remain stable across physically permissible views of the same parent structure. This is weaker than assuming that a feature residual can be made completely class independent.

### 4.3 External validity

RRUFF is an experimental mineral PXRD domain, not a universal proxy for all instruments, materials, multiphase systems, or laboratory protocols. The result should be framed as an external-domain transfer test showing improved label efficiency under a controlled adaptation protocol.

### 4.4 Limitations

- seven-crystal-system classification is a coarse structural task;
- synthetic perturbations cannot enumerate every experimental effect;
- RRUFF chemistry and instrumentation are heterogeneous;
- zero-shot transfer remains weak in absolute terms;
- class-level gains are nonuniform;
- the current work does not establish causal invariance or explicit semantic/measurement disentanglement;
- the selected JS weight is task/protocol specific, not universal.

## 5. Frozen figure map

- **Fig. 1:** method / simulator provenance / ERM vs JS objective.
- **Fig. 2:** five-pair simulated Validation and locked-Test effects.
- **Fig. 3:** RRUFF-301 K=1/2/5 paired few-shot result.
- **Fig. 4:** per-class effects + selected fix/break/confidence diagnostic.
- **Supplement:** calibration, full profiles/classes, fixed-step sensitivity, v1 audit trail, implementation details.

## 6. Submission-facing claim sentence

> Building on physically informed on-the-fly PXRD generation, we use simulator-retained parent-structure provenance as measurement-equivalence supervision. Under a matched two-view design, JS consistency yields repeatable simulated OOD gains and improves the label efficiency of adaptation to experimental RRUFF PXRD relative to Dynamic ERM.

## 7. Next manuscript tasks — no new training implied

1. turn the frozen figure map into publication-quality plots from existing result artifacts;
2. build the literature-backed Introduction around physical augmentation, online PXRD generation, consistency regularization, and simulation-to-experiment transfer;
3. write exact Methods from frozen configs and audit reports;
4. convert Results tables above into source-backed prose without adding unsupported mechanism claims;
5. draft Limitations before polishing the abstract;
6. only open a new experiment if drafting reveals a specific reviewer-critical evidence gap that cannot be answered from the existing artifacts.
