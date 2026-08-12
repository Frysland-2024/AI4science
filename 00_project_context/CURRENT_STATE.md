# AI4science Current State

**Canonical status date:** 2026-08-11
**Repository:** `Frysland-2024/AI4science`  
**Active engineering root:** `xrd_robustness/`

> This file records only the current authoritative state. Historical reasoning remains in `PROJECT_JOURNEY.md`, dated reports, Git history, and the RRUFF-301 audit trail.

## 1. Current phase

The current V9-T / JS-consistency study has completed the evidence-building phase required for a first manuscript draft.

**Current project mode:**

`experiment-building → evidence freeze → manuscript building`

The default next action is **not additional training**. The default next action is manuscript, figure, and application-narrative preparation from frozen evidence.

Canonical evidence-freeze document:

`00_project_context/EVIDENCE_FREEZE_V1_20260808.md`

## 2. Frozen paper-level research question

The active paper asks:

> Can parent-structure provenance retained by an online PXRD simulator be used as measurement-equivalence supervision, so that physically different observations of the same crystal produce more stable predictions and improve both simulated OOD robustness and low-label adaptation to experimental PXRD relative to matched Dynamic ERM?

The conceptual advance is **not** a new JS algorithm. It is the use of simulator-retained same-parent relationships as structured supervision under a controlled matched-data design.

## 3. Frozen method contract

- task: seven-crystal-system PXRD classification;
- parent structures: 14,060 total;
- split: Train 9,842 / Validation 2,109 / Test 2,109;
- backbone: ResNet-18-GN;
- preprocessing: identity;
- optimizer: AdamW;
- learning-rate schedule: constant;
- baseline: Dynamic ERM with two online physical views;
- selected method: JS Consistency on the same two views;
- frozen weight: `lambda_js = 60`.

Residual-v1 is archived after its preregistered stability Gate failure. V10 measurement-supervised residual learning is archived as a partial/negative mechanism study. PAMPT is a foundation/backbone diagnosis, not the active model. These modules are not part of the current paper’s primary comparison.

## 4. Frozen simulated Validation evidence

Five matched training seeds, two methods per seed, ten runs total.

Authoritative records:

- `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`
- `xrd_robustness/reports/v9_resnet_js_ten_run_results_20260801.md`

| Metric | Dynamic ERM | JS λ=60 | Paired mean Δ |
|---|---:|---:|---:|
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | **+0.046569** |
| In-range Macro-F1 | 0.705112 | 0.733103 | **+0.027991** |
| Level-0 Macro-F1 | 0.706891 | 0.734648 | **+0.027757** |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

Primary paired OOD effect:

- mean Δ = `+0.046569`;
- sample SD = `0.009711`;
- paired-bootstrap 95% interval = `[0.038145, 0.052834]`;
- positive in all five matched training-seed pairs.

The preregistered in-range guardrail passed.

## 5. Frozen simulated Test evidence

The one-shot simulated Test has completed and is frozen.

Authoritative records:

- `xrd_robustness/reports/v9_resnet_js_simulated_test_summary.json`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_results_20260803.md`
- `xrd_robustness/reports/v9_resnet_js_simulated_test_audit.json`

Primary result:

- five-pair mean single-factor OOD Macro-F1 Δ = **`+0.054600`**;
- sample SD = `0.007271`;
- paired-bootstrap 95% interval = **`[+0.048944, +0.060255]`**;
- all five paired OOD deltas are positive;
- all five in-range deltas are positive.

Interpretation boundary: this confirms an **aggregate simulated-domain robustness improvement**. It does not establish uniform improvement for every class and perturbation. Monoclinic and selected shift/texture conditions remain important secondary limitations.

No simulated-Test rerun, Test-guided retuning, checkpoint substitution, seed exclusion, or method reopening is permitted for the current paper.

## 6. Real-domain evidence hierarchy

### 6.1 RRUFF-70 — exploratory only

RRUFF-70 produced the first real-domain few-shot signal that JS-pretrained representations might adapt more efficiently than ERM-pretrained representations. Because the cohort was small and had already informed hypothesis formation, it is now explicitly classified as **exploratory/pilot evidence**, not final confirmatory evidence.

Its role is historical hypothesis generation and pipeline development.

### 6.2 RRUFF-301 v2 — strongest real-domain retrospective validation

Canonical commit:

`24d8c8511bdea9df8b52cdf779b04420bebffafc`

Authoritative records:

- `xrd_robustness/reports/rruff301_confirmatory_full_report_20260807.md`
- `xrd_robustness/reports/rruff301_representation_analysis_20260807.md`
- `xrd_robustness/reports/rruff301_v1_audit_trail_20260807.md`
- `xrd_robustness/reports/rruff301_existing_artifact_lineage_audit.json`

The first three filenames are historical. The lineage audit supersedes their
"confirmatory" wording: the numerical artifacts can be checked at declared levels,
but pre-execution authorization, the original RRUFF-301 runner, the original episode
plan/support IDs, the execution log, and the bound code/runtime state are unavailable.
The results are therefore retrospective evidence, not confirmatory evidence.

Protocol:

- 301 experimental RRUFF mineral PXRD spectra;
- 43 spectra per crystal system;
- adaptation pool: 10/class = 70 total;
- locked test set: 33/class = 231 total;
- K = 1, 2, 5 support examples per class;
- 5 pretraining seeds × 5 episode seeds;
- frozen convolutional backbone;
- trainable projection `7168→256` plus 7-class head;
- AdamW, `lr=1e-4`;
- primary metric: paired ΔMacro-F1 (JS-pretrained − ERM-pretrained).

Recorded v2 results (retrospective validation):

| K | ERM Macro-F1 | JS Macro-F1 | Paired mean Δ | Positive/25 |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 ± 0.026 | 0.3280 ± 0.032 | **+0.0433** | 21 |
| 2 | 0.3026 ± 0.040 | 0.3486 ± 0.033 | **+0.0460** | 23 |
| 5 | 0.3555 ± 0.030 | 0.4099 ± 0.027 | **+0.0545** | 24 |

Across K=1/2/5, **68 of 75 paired comparisons are positive**.

A fixed-200-step sensitivity check at K=1 and K=5 preserves the same direction, reducing concern that the result is driven only by the support-loss early-stopping rule.

The earlier RRUFF-70 monoclinic negative-transfer pattern does **not** replicate in RRUFF-301 v2; however, per-class effects remain nonuniform, so no universal class-wise improvement claim is allowed.

### 6.3 RRUFF-301 v1 label bug

The first intended confirmatory execution was invalidated after a class-label construction error was discovered: RRUFF CELL PARAMETERS metadata represented trigonal records under a hexagonal convention, causing an invalid trigonal/hexagonal split.

The project did not repair or reinterpret v1 post hoc. Instead:

1. v1 was invalidated for confirmatory use;
2. the error and diagnosis were preserved in an audit trail;
3. labels were rebuilt using DIF `space_group` evidence plus crystallographic mapping with `pymatgen.SpaceGroup`;
4. the complete experiment was rerun as v2 on the corrected locked split, but the
   available repository artifacts do not establish a valid confirmatory execution
   lineage.

This exploratory→intended-confirmatory→bug-discovery→full-rerun sequence is part of the project’s research-governance record. The final rerun remains retrospective because its original governance and execution provenance cannot now be reconstructed.

## 7. Representation and calibration evidence

Representation analysis from the RRUFF-301 v2 lineage includes:

- fix/break patterns;
- confidence dynamics;
- confusion asymmetry;
- per-class effects.

Calibration analysis was added in commit:

`a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`

Assets:

- `outputs/calibration_metrics.json`;
- `outputs/calibration_report.html`.

Calibration includes ECE, NLL, Brier score, and confidence-distribution analysis. It is currently **supplementary evidence**, not a primary manuscript claim.

## 8. Frozen manuscript figure plan

### Figure 1 — Method / simulator provenance

Show parent crystal → two online physical measurement views → matched ERM vs JS objectives. Central message: the simulator is both a data engine and a provider of measurement-equivalence supervision.

### Figure 2 — Simulated Validation + Test paired effects

Show the five matched training-seed paired effects on Validation and frozen Test, with the in-range guardrail summarized but not overplotted.

### Figure 3 — RRUFF-301 v2 K=1/2/5 few-shot adaptation

Show ERM vs JS Macro-F1 and paired Δ distributions/points across the 25 comparisons at each K. Mark `68/75 positive`.

### Figure 4 — Effect heterogeneity / mechanism diagnostic

Use per-class ΔF1 plus selected fix/break or confidence evidence. Main message: gains are broad but not uniform.

### Supplementary

- calibration;
- complete profile tables;
- full per-class tables;
- fixed-step sensitivity;
- zero-shot diagnostics;
- v1 audit trail;
- hyperparameter and implementation tables.

## 9. Manuscript claim boundary

### Allowed strong claim — simulated domain

> Under matched online physical perturbation exposure, explicitly using parent-structure measurement-equivalence through JS consistency improves aggregate simulated OOD robustness relative to Dynamic ERM.

### Allowed descriptive claim — RRUFF-301

> In the recorded RRUFF-301 few-shot artifacts, JS-pretrained models have higher
> mean Macro-F1 than their matched ERM-pretrained counterparts at K=1/2/5. The 150
> few-shot metrics and fixed 231-spectrum test membership were recomputed from
> 34,650 prediction rows, but the historical execution provenance is incomplete;
> this is retrospective validation, not confirmatory evidence.

### Allowed interpretation

> The simulator provides structured supervision beyond class labels because it retains provenance linking multiple perturbed observations to the same latent crystal structure.

### Forbidden / unsupported claim

- JS is a novel consistency algorithm;
- the method universally solves PXRD Sim2Real;
- every crystal system and every perturbation improves;
- RRUFF represents all experimental PXRD;
- the method proves semantic/measurement disentanglement;
- residual approaches are impossible for XRD;
- any claim based on Test-guided retuning or post-hoc seed selection.

## 10. Current scientific decision

**The current paper is draft-ready, but its real-domain evidence is not confirmation-complete.**

The evidence chain now contains:

1. matched-data method comparison;
2. preregistered multi-seed Validation replication;
3. frozen simulated Test confirmation;
4. separate RRUFF-301 retrospective experimental-domain validation;
5. per-class/profile limitations;
6. representation and calibration supplementary evidence;
7. transparent v1 label-bug audit and corrected v2 rerun.

The paper should now be drafted from the frozen evidence rather than expanded by default.

## 11. Current next actions

1. Generate the four main figures from existing artifacts.
2. Write the literature-backed Introduction around physical augmentation, on-the-fly PXRD generation, simulator provenance, consistency learning, and Sim2Real/few-shot transfer.
3. Write exact Methods from frozen configs, hashes, and audit reports.
4. Write Results in the frozen order: Validation → simulated Test → RRUFF-301 → heterogeneity/diagnostics.
5. Write Discussion and Limitations before polishing the abstract.
6. Maintain the application-ready narrative in `00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`.

### New-experiment rule

No new training is the default.

A new experiment may be proposed only if manuscript drafting or external review identifies a **specific reviewer-critical evidence gap** that cannot be answered using the frozen artifacts. Such an experiment must be named and justified prospectively and must not reopen `lambda_js`, method selection, or the frozen simulated Test. If a confirmatory real-domain claim is required, it needs a newly authorized prospective execution; the historical RRUFF-301 artifacts cannot be relabelled as confirmatory.

## 12. Future work not required for the current paper

The following remain valuable future research/deployment axes but are **not manuscript blockers**:

- Tan Lab perovskite functional-ceramic phase-state adaptation;
- Residual-v2 / conditional measurement-decoder redesign;
- physics-guided lattice-geometry losses;
- backbone–augmentation compatibility in one-dimensional scientific signals;
- Raman or other scientific characterization modalities;
- broader lab-specific calibration and domain adaptation.

These must remain separate from the frozen evidence of the current paper.

## 13. Repository workflow update (2026-08-10)

- Completed engineering/documentation work: removed the repository-wide mandatory
  `check-journal-indexing` startup requirement. The skill remains optional and
  scoped to explicit SCIE, EI Compendex, or CSCD verification tasks.
- Experiment status: unchanged; no data, model, configuration, or evidence artifact
  was accessed or modified.
- Current blocker: manuscript-building work remains the active project workstream.
- Next action: proceed with the frozen manuscript and figure plan in Section 11.

## 14. Code-and-artifact repair audit (2026-08-11; authoritative)

This section supersedes earlier current-state wording where it conflicts with the
source-code and artifact audit.

### 14.1 Scientific task boundary

The implemented task is robust seven-class PXRD crystal-system classification. The
model emits seven logits and the completed losses/evaluations are classification
losses and metrics. Perturbation parameters are sampled nuisance variables used to
construct views; the current code does not estimate lattice constants, phase
fractions, strain, texture, peak parameters, or another physical quantity. The
project supports a scientific-ML / measurement-robustness capability claim, not a
completed inverse-problem or physical-parameter-recovery claim.

### 14.2 Completed engineering repairs

- Future simulated-Test output now maps the full-panel `per_class_f1` vector to
  canonical crystal-system names. The former implementation filtered to one true
  class and then computed seven-class Macro-F1, creating a defective diagnostic.
- Frozen Test JSON was not edited or rerun. The independent correction sidecar is
  `xrd_robustness/reports/v9_resnet_js_simulated_test_class_metric_correction.json`.
- A split-scope auditor now distinguishes exact-parent isolation from exact-formula
  overlap in `xrd_robustness/reports/v9_formal_split_identity_overlap_audit.json`.
- RRUFF-301 now has a fail-closed retrospective contract, artifact auditor, and
  deterministic replay plan. `run-replay` cannot load a model or spectrum and
  cannot be enabled merely by supplying an authorization path.
- Packaging metadata, clean-install test dependencies, stale handoff tests, and a
  GitHub Actions test workflow were repaired.

### 14.3 Completed evidence checks

- Simulated Test: 360/360 profile records contain a defective legacy named-class
  field; the correct `per_class_f1` values exactly match their confusion matrices.
  Ten frozen per-run hashes remain valid. `macro_f1`, `per_class_f1`,
  `worst_class_f1`, paired deltas, and the primary summary are unaffected.
- Formal split: 0 exact parent fingerprints cross train/validation/test. However,
  47 exact formulas cross splits, involving 585/14,060 records; 12 formulas occur
  in all three splits. The established claim is exact-parent-disjoint only. No
  formula-, chemical-family-, prototype-, or symmetry-equivalence-disjoint claim is
  supported.
- RRUFF-301: all registered file hashes and ten checkpoint hashes pass. For the 150
  few-shot runs, accuracy, Macro-F1, and per-class F1 were recomputed from 34,650
  prediction rows, and every run uses the same 231 locked-test IDs. The 100
  fixed-200 records have hash/schema/grid/step/range checks only. The ten zero-shot
  records additionally pass Macro-F1-versus-per-class internal checks, but their
  accuracy cannot be recomputed without prediction rows.

### 14.4 Experiment status, unresolved risk, and next action

No training, inference, checkpoint substitution, split rebuild, or simulated-Test
access was performed during this repair. Frozen raw artifacts remain unchanged.

The unrecoverable blocker is historical RRUFF-301 provenance: the original runner,
episode support IDs, independent pre-execution authorization, execution log, and
bound code/runtime state are absent. A newly generated retrospective plan cannot
repair that history and remains `NOT_AUTHORIZED`. If confirmation is required, the
next scientific action is a separately reviewed prospective authorization and a new
empty output root—not relabelling the old results.

Exact read-only verification commands:

```powershell
cd E:\AI4science\xrd_robustness
python -s scripts/audit_v9_simulated_test_class_metrics.py --check-only
python -s scripts/audit_formal_split_identity_overlap.py --check-only
python -s scripts/run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only
python -s -m pytest -q
```

## 15. Repository cleanup and authority consolidation (2026-08-11)

This maintenance pass removed redundant repository snapshots and one-time delivery
machinery without changing the scientific evidence:

- removed the duplicated 2026-06-27 extracted context pack, static Git/directory
  inventories, an obsolete sync memo, and superseded cleanup reports;
- removed the legacy account-handoff bundle while retaining the current
  `xrd_robustness/CODEX_HANDOFF.md`;
- removed one-time desktop migration packaging and its 14,301-row payload inventory;
  retained the frozen hardware profiles and all eight implementation paths required
  by the active method-transfer contract, while simplifying first-boot/readiness
  checks so they no longer consume the retired migration payload;
- removed superseded tuning/runtime snapshots, generated pytest XML, empty failure
  tables, and one byte-identical duplicate Gate-3 report pair;
- replaced the legacy handoff/migration test with a current project-state contract
  test and changed the historical Gate-3 launcher to write only the canonical
  `gate3_pampt_vs_resnet` report pair;
- rewrote the three repository entry READMEs to point to the 2026-08-11 authority
  and added explicit supersession notices to the 2026-08-08 freeze, manuscript,
  and application drafts;
- moved only regenerable caches, logs, a temporary wheel, profiling output, and
  confirmed duplicate/intermediate images out of the repository into
  a local temporary cleanup directory outside the repository.

Preserved on purpose: frozen simulated-Test evidence, RRUFF artifacts and audit
trail, datasets, checkpoints, experimental outputs, user admission assets,
literature, virtual environments, and the Residual/V10/PAMPT/opXRD negative or
archived scientific record. The cleanup does not authorize training, inference,
Test reruns, or evidence rewriting.

**Experiment status:** unchanged from Section 14; no training or inference was
performed and no frozen raw artifact was edited.

**Current blocker:** historical RRUFF-301 provenance remains unrecoverable.

**Publication scope (2026-08-13):** the user explicitly authorized publication of
the reviewed local source, configuration, audit, and documentation changes. Local
`outputs/` delivery artifacts remain excluded by repository policy.

**Next action after synchronization:** continue manuscript construction within the
frozen evidence and claim boundaries above.

**Verification:** `283 passed, 39 subtests passed`; current Markdown links and
deleted-basename references passed; Test-metric, split-scope, and RRUFF lineage
audits passed at their declared levels; desktop first-boot `-PlanOnly` listed only
engineering checks with `formal_training_commands=0`.
