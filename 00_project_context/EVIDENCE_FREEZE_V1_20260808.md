# V9 Evidence Freeze V1 — 2026-08-08

> **Supersession notice (2026-08-11):** This is a preserved historical freeze.
> `CURRENT_STATE.md` and the 2026-08-11 metric, split, and RRUFF lineage audits
> are authoritative where they conflict with this document. In particular, all
> RRUFF-301 “confirmatory” wording below is superseded: the recorded numerical
> results are retrospective validation with incomplete historical provenance.
> The frozen simulated Validation/Test primary metrics are unchanged.

**Status:** evidence frozen for manuscript preparation  
**Repository:** `Frysland-2024/AI4science`  
**Active method:** Dynamic JS Consistency, `lambda_js = 60`  
**Baseline:** matched Dynamic ERM  
**Backbone:** ResNet-18-GN

> This document freezes the evidence hierarchy and manuscript-facing result set. It does not authorize new training, retuning, Test reruns, seed exclusion, or post-hoc method changes.

## 1. Scientific question now considered closed for the current paper

The current study asks whether an online PXRD simulator can serve not only as a scalable source of label-preserving perturbed spectra, but also as a source of **measurement-equivalence supervision**: different physically perturbed observations generated from the same parent crystal structure should yield stable predictive distributions.

The paper-level comparison is therefore:

- **Dynamic ERM:** two online views, shared crystal-system label, cross-entropy only;
- **Dynamic JS:** the same two online views and the same data exposure, with an additional Jensen–Shannon consistency term.

Residual-v1, V10 measurement-supervised residual learning, PAMPT, structured-dynamic V8, sample-efficiency branches, and later physics-guided ideas remain historical/future modules and are not part of the active paper claim.

## 2. Frozen evidence hierarchy

### 2.1 Primary evidence — main manuscript

#### A. Simulated Validation paired replication

Authoritative records:

- `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`
- `xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`

Five matched training-seed pairs, ten runs total:

| Metric | Dynamic ERM | JS λ=60 | Paired mean Δ |
|---|---:|---:|---:|
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | **+0.046569** |
| In-range Macro-F1 | 0.705112 | 0.733103 | **+0.027991** |
| Level-0 Macro-F1 | 0.706891 | 0.734648 | **+0.027757** |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

Primary paired-bootstrap 95% interval for OOD Δ: `[0.038145, 0.052834]`.  
All five matched seeds have positive OOD Δ. The preregistered in-range guardrail passes.

#### B. Frozen simulated Test paired confirmation

Authoritative records:

- `xrd_robustness/reports/v9_resnet_js_simulated_test_summary.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_results_20260803.md`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_audit.json`

The frozen one-shot simulated Test independently confirms the Validation direction:

- five-pair mean single-factor OOD Macro-F1 Δ: **+0.054600**;
- sample SD: `0.007271`;
- paired-bootstrap 95% interval: **`[+0.048944, +0.060255]`**;
- all five paired OOD deltas are positive;
- all five in-range deltas are positive.

Claim boundary: this supports **aggregate simulated-domain robustness**, not uniform improvement for every class/profile. Monoclinic and shift/texture conditions remain important limitations.

#### C. RRUFF-301 confirmatory v2 few-shot adaptation

Authoritative records, commit `24d8c8511bdea9df8b52cdf779b04420bebffafc`:

- `xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md`
- `xrd_robustness/reports/rruff301_representation_analysis_20260807.md`
- `xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md`

Protocol:

- 301 real RRUFF spectra, 43 per crystal system;
- 10/class adaptation pool = 70 spectra;
- locked external test = 33/class = 231 spectra;
- Dynamic ERM vs JS λ=60;
- five pretraining seeds × five episode seeds;
- frozen convolutional backbone; projection + head adaptation;
- K = 1, 2, 5 support examples per class.

Primary confirmatory results:

| K | ERM Macro-F1 | JS Macro-F1 | Paired mean Δ | Positive pairs |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 ± 0.026 | 0.3280 ± 0.032 | **+0.0433** | 21/25 |
| 2 | 0.3026 ± 0.040 | 0.3486 ± 0.033 | **+0.0460** | 23/25 |
| 5 | 0.3555 ± 0.030 | 0.4099 ± 0.027 | **+0.0545** | 24/25 |

Across K=1/2/5, **68/75 paired comparisons are positive**.

The fixed-200-step sensitivity check preserves the same direction at K=1 and K=5, so the main conclusion is not an artifact of the early-stopping rule.

Manuscript-facing interpretation:

> JS-pretrained representations consistently require fewer real labeled PXRD examples to adapt to the RRUFF measurement domain than the matched Dynamic-ERM-pretrained representations under the frozen protocol.

This is the strongest current real-domain confirmatory evidence.

### 2.2 Mechanistic / diagnostic evidence — main text selectively, otherwise supplement

Use only to explain where the aggregate effect comes from; do not turn these into independent headline claims.

- RRUFF-301 per-class effects;
- fix/break transition patterns;
- confidence dynamics;
- confusion asymmetry;
- paired prediction consistency;
- simulated worst-class and profile-specific diagnostics.

Important class-level boundary:

- the earlier RRUFF-70 monoclinic negative-transfer signal did **not** replicate in RRUFF-301 v2;
- trigonal/cubic effects remain K-dependent;
- therefore do not claim universal per-class improvement.

### 2.3 Supplementary evidence

Calibration analysis added in commit `a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`:

- `outputs/calibration_metrics.json`
- `outputs/calibration_report.html`

Metrics include ECE, NLL, Brier score, and confidence-distribution analyses. Calibration is supplementary unless manuscript drafting reveals a single clear, nonredundant mechanistic finding that materially strengthens the primary claim.

### 2.4 Historical / audit-only evidence

The following must remain visible in the scientific record but must not be presented as primary confirmatory evidence:

- RRUFF-70 few-shot results — **exploratory/pilot**;
- RRUFF-301 v1 — **invalidated for confirmatory use because of the trigonal/hexagonal label-construction bug**;
- v1 bug audit trail — retained to document the error, diagnosis, fix, and full rerun;
- Residual-v1 / V10 — archived negative or partial mechanism studies;
- PAMPT backbone diagnosis — foundation study, not a paper headline;
- opXRD ferroelectric-domain audit — NO_GO feasibility evidence, not a model result.

## 3. RRUFF-70 → RRUFF-301 evidence transition

The correct evidence chronology is frozen as:

1. **RRUFF-70 exploratory pilot** produced an initial signal that JS-pretrained models may adapt more efficiently than ERM-pretrained models.
2. Because RRUFF-70 was small and had already informed hypothesis formation, it was explicitly downgraded to exploratory evidence rather than promoted to a final real-domain claim.
3. A larger **RRUFF-301 confirmatory protocol** was preregistered prospectively with a locked 231-spectrum test set and frozen K values, episode seeds, split seeds, adaptation procedure, and primary metric.
4. The first RRUFF-301 execution exposed a label-construction error: the RRUFF CELL PARAMETERS convention merged trigonal records into the hexagonal category, creating an invalid class split.
5. The v1 result was not repaired post hoc. It was invalidated for confirmatory use, preserved in an audit trail, and the split/label pipeline was rebuilt using DIF space-group evidence plus `pymatgen.SpaceGroup` mapping.
6. The complete experiment was rerun from the corrected frozen split as **v2**, yielding 68/75 positive paired Macro-F1 effects across K=1/2/5.

This transition is part of the project’s research-methodology story: exploratory evidence generated a hypothesis; a separate confirmatory design tested it; a discovered data-label bug was disclosed and invalidated rather than hidden; the corrected experiment was rerun under an auditable protocol.

## 4. Frozen main-paper figure plan

### Figure 1 — Method and supervision structure

**Purpose:** explain the research question, not performance.

Required elements:

- parent crystal structure `s`;
- two online physical measurement views `x1 = g(s,m1)` and `x2 = g(s,m2)`;
- Dynamic ERM uses the shared class label only;
- Dynamic JS adds prediction-distribution consistency;
- simulator role: from data engine to provider of measurement-equivalence supervision.

### Figure 2 — Simulated robustness evidence

**Purpose:** show that the effect is repeatable in the controlled simulated domain.

Main panels:

- paired Validation OOD deltas across five training seeds;
- paired locked-Test OOD deltas across the same five seeds;
- concise in-range guardrail indicator.

Do not overload this figure with every profile.

### Figure 3 — RRUFF-301 confirmatory few-shot adaptation

**Purpose:** primary real-domain result.

Main panels:

- K=1/2/5 Macro-F1 for ERM vs JS;
- paired Δ distributions or paired points for the 25 comparisons at each K;
- note: 68/75 paired effects positive.

The RRUFF-301 v2 result, not RRUFF-70, is the manuscript’s central experimental-domain evidence.

### Figure 4 — Where the gain appears and where it does not

**Purpose:** prevent the paper from becoming a pure leaderboard claim.

Candidate panels:

- per-class ΔF1 at K=1/2/5;
- fix/break transition counts;
- selected confusion asymmetry or confidence-change view.

Keep one coherent diagnostic message: **the average benefit is broad but not uniform across classes and conditions**.

### Supplementary figures/tables

- calibration metrics and reliability plots;
- complete per-profile simulated results;
- complete per-class tables;
- fixed-200-step sensitivity check;
- RRUFF-301 v1 audit trail;
- additional zero-shot diagnostics;
- implementation/hyperparameter tables.

## 5. Manuscript claim boundary

### Allowed strong claim

> Under matched online physical perturbation exposure, explicitly using parent-structure measurement-equivalence through JS consistency improves simulated OOD robustness and produces more label-efficient adaptation to an external experimental PXRD domain than Dynamic ERM.

### Allowed interpretation

> The online simulator provides supervision beyond class labels because it retains provenance linking multiple perturbed observations to the same latent crystal structure.

### Not allowed

- “JS is a new consistency algorithm.”
- “JS universally solves PXRD Sim2Real.”
- “The method improves every crystal system and every perturbation.”
- “RRUFF-301 represents all experimental XRD.”
- “The method proves semantic/measurement disentanglement.”
- “Residual failure proves residual methods cannot work for XRD.”
- any Test-guided retuning or post-hoc seed exclusion.

## 6. Manuscript readiness decision

**Decision: READY TO DRAFT.**

The current paper has the minimum complete evidence chain:

1. controlled matched-data method comparison;
2. preregistered multi-seed Validation evidence;
3. frozen simulated-Test confirmation;
4. separate experimental-domain few-shot confirmation;
5. class/profile limitations and audit trails;
6. supplementary calibration and representation diagnostics.

### Default action from this freeze

Do **not** launch additional training by default.

New experiments are permitted only if manuscript drafting or external review reveals a specific unanswered reviewer-critical question that cannot be answered from the frozen evidence. Any such experiment must be named in advance, justified as filling a defined evidence gap, and must not reopen JS lambda selection or alter the existing confirmatory results.

## 7. Canonical evidence commits

- five-seed Validation result lineage: `868b079c1b410e6afe877330b7defc4262d82969`
- RRUFF-301 v2 + representation + v1 audit: `24d8c8511bdea9df8b52cdf779b04420bebffafc`
- calibration analysis: `a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`

This file is the manuscript-facing evidence freeze. Historical reasoning remains in `PROJECT_JOURNEY.md` and its dated continuation records; engineering execution details remain in `xrd_robustness/CODEX_HANDOFF.md`.
