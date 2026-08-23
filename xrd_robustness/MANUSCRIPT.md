# Measurement-Equivalence Supervision for Robust PXRD Classification

**Status:** current manuscript scaffold from frozen evidence

**Updated:** 2026-08-23

**Evidence authority:** [`reports/EVIDENCE_INDEX.md`](reports/EVIDENCE_INDEX.md)

## Abstract

Machine-learning analysis of powder X-ray diffraction (PXRD) often relies on
synthetic training data, while experimental patterns vary with peak shifts,
broadening, preferred orientation, background and noise. We study an additional
source of supervision created by online simulation: multiple perturbed patterns
from one parent structure are related measurements of the same latent physical
object, not merely examples with a shared class label. We add Jensen-Shannon
prediction consistency between paired online views to a matched Dynamic ERM
baseline while controlling the backbone, parent structures, perturbation
distribution, optimization and data exposure. Across five matched training-seed
pairs, consistency improves mean single-factor Validation-OOD Macro-F1 by
`0.046569`, with all five effects positive. Evaluation of the already selected
checkpoints on the locked simulated Test yields a mean paired improvement of
`0.054600`, also positive in all five pairs. Stored RRUFF-301 few-shot artifacts
show Macro-F1 improvements of `0.0433`, `0.0460` and `0.0545` at K=1, 2 and 5,
respectively, but incomplete historical execution provenance limits this result
to retrospective validation. The gains are aggregate rather than universal.
These results show how simulator-retained relationships can provide structured
supervision for robust scientific classification.

## 1. Research questions

1. Does paired prediction consistency improve simulated OOD robustness beyond
   matched dynamic augmentation?
2. Do stored experimental-domain artifacts indicate more label-efficient
   adaptation from a consistency-trained representation?
3. Where do seed-, class- and perturbation-level limitations remain?

## 2. Frozen methods

### 2.1 Task and split

- Seven-class crystal-system classification from 1D PXRD.
- 14,060 parent structures: 9,842 Train, 2,109 Validation and 2,109 Test.
- Exact parent fingerprints do not cross splits.
- Formula identities do cross splits; the design is not formula-, family- or
  prototype-disjoint.

### 2.2 Matched comparison

- Backbone: ResNet-18-GN.
- Preprocessing: identity.
- Optimizer and schedule: AdamW with constant learning rate.
- Baseline: Dynamic ERM on two independently perturbed online views.
- Method: the same views and classification loss plus Jensen-Shannon prediction
  consistency, with frozen `lambda_js = 60`.
- Five matched training seeds; no post-hoc seed exclusion.
- Validation selected the method before the locked simulated Test was accessed.

The simulator varies measurement shift, broadening, preferred orientation,
background and noise. These variables define nuisance views; V9-T does not
estimate them or any lattice, strain or phase-fraction parameter.

### 2.3 RRUFF-301 evidence level

The retained artifacts cover 301 experimental spectra, a 70-spectrum adaptation
pool, a fixed 231-spectrum test membership, K=1/2/5 budgets, five pretrained
seeds and five episode seeds. Few-shot metrics can be recomputed from retained
prediction rows; other artifact families pass their declared hash/schema checks.
The original runner, episode support IDs, independent execution authorization,
execution log and complete code/runtime binding are unavailable. Consequently,
this section reports retrospective evidence and not confirmatory evidence.

## 3. Frozen results

### 3.1 Simulated Validation

| Metric | Dynamic ERM | JS consistency | Paired delta |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

The primary OOD effect is positive for all five pairs, with a paired-bootstrap
95% interval of `[0.038145, 0.052834]`. Worst-class behavior is heterogeneous;
one Validation seed has a negative worst-class delta.

### 3.2 Locked simulated Test

- Mean paired single-factor OOD Macro-F1 delta: `+0.054600`.
- Sample SD across five pairs: `0.007271`.
- Paired-bootstrap 95% interval: `[+0.048944, +0.060255]`.
- Five of five OOD and in-range paired effects are positive.

The original named-class diagnostic was incorrect. Its correction sidecar was
derived from full-panel confusion matrices; primary Macro-F1, paired effects and
per-run artifact hashes are unchanged.

### 3.3 RRUFF-301 retrospective few-shot adaptation

| K | ERM Macro-F1 | JS Macro-F1 | Mean paired delta | Positive pairs |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | +0.0433 | 21/25 |
| 2 | 0.3026 | 0.3486 | +0.0460 | 23/25 |
| 5 | 0.3555 | 0.4099 | +0.0545 | 24/25 |

The stored artifacts indicate an aggregate advantage, not a uniform class-wise
effect. The result is useful as retrospective external-domain validation but
cannot establish prospective confirmation or full original-execution
reproducibility.

## 4. Discussion boundary

The contribution is not a new divergence. It is the use of simulator-retained
parent identity as an equivalence relation for scientific measurements while
keeping data exposure controlled. This is weaker than claiming causal
invariance or complete disentanglement of structure and measurement factors.

Limitations include the coarse seven-class task, incomplete coverage of real
instrument/sample effects, exact-parent-only split isolation, heterogeneous
class effects, weak absolute zero-shot transfer, RRUFF domain specificity and
incomplete RRUFF execution provenance. No claim extends to physical-parameter
inversion or universal experimental PXRD robustness.

## 5. Figure plan

1. Simulator provenance and the matched ERM/JS objectives.
2. Five paired Validation and locked-Test effects.
3. RRUFF-301 retrospective K=1/2/5 paired effects with provenance boundary.
4. Class/profile heterogeneity and the corrected diagnostic.

## 6. Submission-facing claim

Online PXRD simulation can supply measurement-equivalence supervision through
parent-structure provenance. In a matched two-view design, JS consistency
improves aggregate simulated OOD robustness relative to Dynamic ERM; retained
RRUFF-301 artifacts provide consistent but retrospective evidence of improved
few-shot adaptation.

## 7. Remaining writing work

1. Build source-backed Introduction and Related Work prose.
2. Convert frozen configs and audits into exact reproducible Methods.
3. Generate publication figures only from retained evidence artifacts.
4. Complete Results, Discussion and Limitations without widening claims.
5. Do not open a new experiment unless a distinct question is explicitly
   authorized and preregistered.
