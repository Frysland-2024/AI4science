# V9 Method-Transfer Manuscript Skeleton

Status: result-independent scaffold. Bracketed fields are filled only from frozen artifacts. No sentence below claims a positive result.

## Working title

Learning cross-view invariance for robust crystal-system classification from simulated powder X-ray diffraction

## Abstract template

Simulated powder X-ray diffraction (XRD) enables large labeled training sets, but measurement perturbations create a sim-to-real gap. We compare matched-budget empirical risk minimization (ERM), output-level Jensen-Shannon (JS) consistency, and residual class-decorrelation using a parent-structure-level split and a shared paired dynamic view stream. Hyperparameters are chosen on Validation only; simulated Test and real XRD remain sealed until a single method is frozen. Across [registered profiles], [selected method/outcome] produced [effect with parent-structure-level 95% CI]. Mechanism diagnostics showed [measured observation only]. On the one-time external test, [result].

## 1. Introduction

1. Simulated XRD can cover structures and controlled perturbations at scale.
2. Background, noise, peak-position, broadening, texture, and intensity effects create measurement variability. Keep the observation model additive: `I_obs = I_peak + I_background + noise`.
3. Broader augmentation exposure does not itself teach a model how predictions or representations should relate across two views of one mother structure.
4. This study therefore compares matched-budget Dynamic ERM, JS consistency, and residual decorrelation while holding backbone, structures, paired views, and optimizer-step budget fixed.
5. Contributions: audited paired stream; parent-structure leakage control; test isolation; pre-registered parent-structure cluster statistics; mechanism diagnostics that avoid equating a learned residual with a physical measurement variable.

## 2. Methods

### 2.1 Data and parent-structure-level split

The dataset is split at the parent-structure level. All diffraction patterns generated from the same crystal structure are assigned to the same subset to prevent data leakage. Stratified random sampling is performed according to crystal system to maintain balanced class distributions.

Report parent-structure count, structure fingerprints, split counts, the fixed random seed, and proof that no parent structure crosses splits. `family_id` may be retained for analysis but must not influence assignment.

### 2.2 Forward simulator and five perturbation families

Describe each perturbation with `literature_source`, `code_source`, and `physics_basis`. State that `apply_probability` is a training exposure rate, not an asserted real-world prevalence.

### 2.3 Paired dynamic training stream

Define deterministic epoch shuffle, paired parameter rows, quality-gate retries, replay hashes, checkpoint state, and the evidence from `v9_resume_determinism_audit.json`.

### 2.4 Compared learning principles

- Dynamic ERM: mean classification loss over two views.
- JS: classification plus symmetric, non-negative output-distribution JS.
- Residual: absolute difference between L2-normalized embeddings, a residual classifier trained on detached features, and class-confusion pressure sent through the frozen residual head to the backbone.

The symmetric residual is invariant to view order. Do not describe it as a signed physical perturbation vector.

### 2.5 Matched-budget protocol

Report identical mother structures, accepted parameter pairs, pair schedule, forward-view exposure, backbone, optimizer-step count, evaluation manifests, and registered seeds.

### 2.6 Selection and isolation

Seven Validation-only tuning runs select λ from the registered candidate sets. Fifteen development runs compare the frozen methods. Exactly one method is selected before simulated Test; real XRD is a one-time external evaluation and cannot change method or λ.

### 2.7 Statistics

Primary metric: mean Macro-F1 across the six registered single-factor OOD profiles. Report per-seed paired differences and 95% intervals from a paired parent-structure cluster bootstrap within each seed, averaged across all registered seeds. Do not bootstrap only the three seed-level summaries. Directly test `Residual - JS` for claims of superiority. Also report ID Macro-F1, balanced accuracy, worst-group F1, ECE, per-class values, and confusion matrices.

## 3. Results templates

### 3.1 Numerical legality and reproducibility

Fill from the resume and loss/gradient audit artifacts; do not substitute smoke accuracy.

### 3.2 Main Validation comparison

| Method | ID Macro-F1 | Mean single-factor OOD Macro-F1 | Worst-group F1 | ECE | Δ vs Dynamic (95% CI) |
|---|---:|---:|---:|---:|---:|
| Dynamic ERM | [ ] | [ ] | [ ] | [ ] | reference |
| JS | [ ] | [ ] | [ ] | [ ] | [ ] |
| Residual | [ ] | [ ] | [ ] | [ ] | [ ] |

### 3.3 Registered outcome branches

- A: Residual stably exceeds both Dynamic ERM and JS.
- B: both transfer objectives improve over Dynamic ERM, but Residual and JS are not clearly different.
- C: JS is effective and Residual adds no supported gain.
- D: neither method is effective, or evidence remains inconclusive; diagnose simulator/OOD validity before changing the scientific question.

### 3.4 Mechanism diagnostics

Report paired JS, flip rate, correct-and-consistent rate, ID tradeoff, residual probe performance, norms, within/between-class distribution summaries, feature variance, effective rank, and collapse checks. Permitted wording: “class-predictive information in the residual decreased/increased.” Forbidden wording without separate identification evidence: “the residual is the measurement factor.”

### 3.5 Simulated Test and external real XRD

Fill once, after method freeze and explicit unlock. Test results must not trigger reselection.

## 4. Discussion

Separate what the data support from hypotheses about physical mechanism. Discuss registered negative outcomes, simulator limitations, limited seed count, external-domain limitations, and why parent-structure-level resampling is the relevant uncertainty unit.

## Figure plan

1. Study flow and data/test locks.
2. λ scale audit (numerical magnitude only, never labeled performance tuning).
3. Single-factor OOD radar or grouped bars.
4. Paired parent-structure-level gain and hierarchical 95% intervals.
5. Confusion matrices.
6. Residual probe and representation diagnostics.
7. One-time real-test result table/plot.

## Reproducibility appendix

List git commit, environment, manifest/config/checkpoint hashes, stream audit hashes, exact analysis command, bootstrap seed/replicates, and all failed or excluded samples.
