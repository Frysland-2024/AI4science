# XRD Robustness V9-T — Current Handoff

**Status date:** 2026-08-11
**Repository:** `Frysland-2024/AI4science`  
**Branch:** `main`

> Current mode is **evidence freeze / manuscript building**. This handoff is intentionally concise. Historical engineering details remain in Git history, dated reports, `00_project_context/PROJECT_JOURNEY.md`, and the RRUFF-301 audit trail.

## 1. Current instruction to any new Codex/GPT session

Do **not** begin by proposing another training run.

Read in this order:

1. `AGENTS.md`
2. `00_project_context/CURRENT_STATE.md`
3. `00_project_context/EVIDENCE_FREEZE_V1_20260808.md`
4. this file
5. `xrd_robustness/MANUSCRIPT_DRAFT_V1_20260808.md`
6. `00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`
7. `00_project_context/PROJECT_JOURNEY.md`

The current task is to transform frozen evidence into a manuscript and application-ready research narrative without silently reopening method selection.

## 2. Frozen active method

- task: seven-crystal-system PXRD classification;
- split: parent-structure 70/15/15 = 9,842 / 2,109 / 2,109;
- backbone: ResNet-18-GN;
- preprocessing: identity;
- optimizer: AdamW;
- baseline: Dynamic ERM;
- selected method: Dynamic JS Consistency;
- selected weight: `lambda_js = 60`;
- same two online physical views for ERM and JS;
- JS differs only by the added prediction-consistency objective.

Residual-v1 is archived. V10 is archived as a partial/negative mechanism study. PAMPT is historical foundation/backbone evidence. None should be reintroduced into the current main comparison unless a new project version is explicitly opened.

## 3. Simulated Validation evidence

Authoritative files:

- `reports/v9_resnet_js_ten_run_summary.json`
- `reports/v9_resnet_js_ten_run_results_20260801.md`

Five matched training-seed pairs:

- OOD Macro-F1 paired mean Δ = **+0.046569**;
- paired-bootstrap 95% interval = `[0.038145, 0.052834]`;
- all five paired seeds positive;
- in-range paired mean Δ = **+0.027991**;
- in-range guardrail passed.

This stage closed method selection and froze `lambda_js=60`.

## 4. Frozen simulated Test evidence

Authoritative files:

- `reports/v9_resnet_js_simulated_test_summary.json`
- `reports/v9_resnet_js_simulated_test_results_20260803.md`
- `reports/v9_resnet_js_simulated_test_audit.json`

Primary result:

- mean five-pair single-factor OOD Macro-F1 Δ = **+0.054600**;
- sample SD = `0.007271`;
- paired-bootstrap 95% interval = `[+0.048944, +0.060255]`;
- all five paired OOD effects positive;
- all five in-range effects positive.

No repeated Test access or Test-guided method modification is allowed for the current manuscript.

Secondary limitation: improvement is aggregate, not uniform. Monoclinic remains a difficult class and selected shift/texture profiles retain local declines.

## 5. Real-domain evidence — RRUFF-301 v2 is retrospective

RRUFF-70 is exploratory only.

The strongest recorded experimental-domain signal is the RRUFF-301 v2 artifact set in commit:

`24d8c8511bdea9df8b52cdf779b04420bebffafc`

Authoritative files:

- `reports/rruff301_confirmatory_full_report_20260807.md`
- `reports/rruff301_representation_analysis_20260807.md`
- `reports/rruff301_v1_audit_trail_20260807.md`
- `reports/rruff301_existing_artifact_lineage_audit.json`

The first three filenames are historical. Do not inherit their confirmatory label.
The current audit verifies the 150 few-shot metrics from 34,650 prediction rows and
the fixed 231-spectrum test membership; fixed-200 and zero-shot artifacts have only
the narrower verification levels recorded in the audit. Missing authorization,
runner, episode-support, execution-log, code-state, and runtime provenance cannot be
reconstructed after the fact. Treat all RRUFF-301 results as retrospective evidence.

Protocol:

- 301 spectra, 43/class;
- 70 adaptation-pool spectra, 10/class;
- 231 locked-test spectra, 33/class;
- K = 1/2/5;
- five pretraining seeds × five episode seeds;
- frozen convolutional backbone;
- trainable projection + head;
- paired JS-pretrained versus ERM-pretrained comparison.

Results:

| K | ERM Macro-F1 | JS Macro-F1 | Paired mean Δ | Positive/25 |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | **+0.0433** | 21 |
| 2 | 0.3026 | 0.3486 | **+0.0460** | 23 |
| 5 | 0.3555 | 0.4099 | **+0.0545** | 24 |

**68/75 paired comparisons are positive.**

Fixed-200-step sensitivity at K=1 and K=5 preserves the direction.

## 6. RRUFF-301 v1 bug handling

The first intended confirmatory execution must never be cited as valid v2 evidence.

Bug:

- RRUFF CELL PARAMETERS convention caused trigonal samples to be absorbed into hexagonal during label construction;
- v1 therefore had an invalid trigonal/hexagonal split.

Governance response:

1. invalidate v1 for confirmatory claims;
2. preserve the audit trail;
3. rebuild labels from DIF `space_group` plus `pymatgen.SpaceGroup` mapping;
4. verify 70 adaptation + 231 test, 33/class, zero overlap;
5. rerun the complete experiment as v2; its numerical artifacts remain useful, but
   the available lineage is insufficient for a confirmatory claim.

This is a research-integrity event, not a result to hide.

## 7. Representation and calibration evidence

RRUFF-301 representation report includes:

- fix/break patterns;
- confidence dynamics;
- confusion asymmetry;
- per-class effects.

Calibration commit:

`a1966ba939f16b291dad2dd4d48e79bfedfc7b8f`

Assets:

- `../outputs/calibration_metrics.json`
- `../outputs/calibration_report.html`

Calibration covers ECE, NLL, Brier, and confidence distributions. Default placement is Supplementary.

## 8. Frozen paper figures

### Fig. 1 — Method

Parent structure → paired online physical views → matched Dynamic ERM vs Dynamic JS. Show simulator provenance as measurement-equivalence supervision.

### Fig. 2 — Simulated evidence

Paired five-seed Validation OOD effects + frozen-Test paired effects. Include in-range guardrail concisely.

### Fig. 3 — Real-domain evidence

RRUFF-301 v2 K=1/2/5 Macro-F1 ERM vs JS plus paired deltas / positive-pair counts.

### Fig. 4 — Heterogeneity / diagnostic

Per-class effects plus one coherent fix/break/confidence diagnostic. Message: gains are broad but not uniform.

### Supplementary

Calibration, full profiles, full class tables, fixed-step sensitivity, zero-shot diagnostics, v1 audit trail, implementation details.

## 9. Claim boundary

Allowed strong simulated-domain claim:

> Parent-structure provenance from the online simulator can be used as measurement-equivalence supervision; under a matched two-view design, JS consistency improves aggregate simulated OOD robustness relative to Dynamic ERM.

Allowed descriptive RRUFF claim:

> The recorded RRUFF-301 artifacts show higher mean few-shot Macro-F1 for
> JS-pretrained than matched ERM-pretrained models at K=1/2/5. This is retrospective
> validation with incomplete historical provenance, not confirmatory evidence.

Do not claim:

- JS itself is algorithmically novel;
- universal PXRD Sim2Real solution;
- every class/profile improves;
- RRUFF is all experimental PXRD;
- semantic/measurement disentanglement is proven;
- Residual methods are impossible for PXRD.

## 10. Current manuscript files

- evidence freeze: `../00_project_context/EVIDENCE_FREEZE_V1_20260808.md`
- manuscript draft: `MANUSCRIPT_DRAFT_V1_20260808.md`
- application narrative: `../00_project_context/APPLICATION_RESEARCH_NARRATIVE_V1_20260808.md`

## 11. Current next actions

1. Generate publication-quality versions of the four frozen main figures from existing artifacts.
2. Write Introduction with literature support; do not rewrite the literature history as if JS or on-the-fly simulation were invented here.
3. Extract exact Method parameters from frozen configs and audits.
4. Write Results in order: Validation → simulated Test → RRUFF-301 v2 → heterogeneity.
5. Put calibration and detailed diagnostics into Supplementary by default.
6. Draft Discussion and Limitations before polishing the abstract.
7. Keep the application narrative synchronized with `PROJECT_JOURNEY.md`.

## 12. New experiment policy

No new training by default.

A new experiment may be opened only if manuscript drafting or external review identifies one concrete reviewer-critical question that the frozen evidence cannot answer. Such an experiment must be named prospectively and must not:

- retune `lambda_js`;
- exclude or replace seeds;
- rerun the frozen simulated Test to improve a number;
- modify the locked RRUFF-301 v2 evidence;
- reopen Residual/PAMPT as if they were part of the current paper.

Tan Lab phase-state adaptation, Residual-v2, physics-guided lattice losses, backbone–augmentation compatibility, and Raman remain future projects rather than current-paper blockers.

## 13. Repository workflow update (2026-08-10)

The repository-wide mandatory `check-journal-indexing` startup requirement was
removed. The skill is now optional and should be used only for tasks that explicitly
require SCIE, EI Compendex, or CSCD coverage verification. This change does not alter
the frozen experiment contract, evidence, or execution authorization.

## 14. Repair audit and current authority (2026-08-11)

When earlier sections conflict with this section, use this section and the bound
JSON audits.

### Implemented task and claim boundary

The current code implements robust seven-class PXRD crystal-system classification,
not physical-parameter inversion. It demonstrates forward perturbation simulation,
classification robustness, and few-shot adaptation workflows. Do not describe it as
completed lattice/phase/strain/texture estimation, TCAD, PDE inversion, or a general
inverse solver.

### Repairs and authoritative audits

- `reports/v9_resnet_js_simulated_test_class_metric_correction.json`: 360/360
  legacy `per_crystal_system_f1` records are defective. Correct full-panel class F1
  is already present as `per_class_f1`; primary and aggregate metrics are unchanged.
  No frozen Test result was edited or rerun.
- `reports/v9_formal_split_identity_overlap_audit.json`: exact parents are disjoint
  across splits, but 47 exact formulas / 585 records cross splits and 12 formulas
  cross all three. Never call the active split family-, formula-, prototype-, or
  symmetry-equivalence-disjoint.
- `reports/rruff301_existing_artifact_lineage_audit.json`: registered hashes and ten
  checkpoint hashes pass; 150 few-shot metrics are recomputed from 34,650 prediction
  rows with fixed 231-ID test membership. Fixed-200 and zero-shot verification is
  explicitly narrower and recorded per artifact.
- `reports/rruff301_retrospective_replay_episode_plan.json`: a new deterministic
  15-episode / 280-support-assignment plan with a fixed 231-spectrum test set. It
  has `historical_plan_claim=false` and is not authorized for execution.

### Hard execution boundary

`scripts/run_rruff301_retrospective_replay.py run-replay` must return
`refused_execution_not_authorized` before model or spectrum access. Supplying any
path via `--authorization` cannot enable this v1 repair runner. The historical
RRUFF-301 outputs are retrospective evidence because the original runner, support
IDs, authorization, execution log, and code/runtime bindings are unavailable.

### Current commands

```powershell
cd E:\AI4science\xrd_robustness
python -s scripts/audit_v9_simulated_test_class_metrics.py --check-only
python -s scripts/audit_formal_split_identity_overlap.py --check-only
python -s scripts/run_rruff301_retrospective_replay.py audit-existing --verify-checkpoints --check-only
python -s scripts/run_rruff301_retrospective_replay.py plan-replay --check-only
python -s -m pytest -q
```

Current blocker: historical RRUFF-301 governance provenance is unrecoverable. A
confirmatory real-domain claim requires a newly authorized prospective execution in
a new empty output root. No training or inference was run during this repair.

## 15. Repository cleanup handoff (2026-08-11)

The active repository surface is now intentionally smaller:

- current entrypoints are `../README.md`, `README.md`,
  `../00_project_context/CURRENT_STATE.md`, and this file;
- the duplicated extracted context pack, old static inventories, and legacy
  account-handoff generator/manifest/DOCX bundle were removed; their committed
  versions remain recoverable from Git history;
- one-time desktop migration packaging and its payload inventory were removed;
  frozen hardware profiles, bootstrap, first-boot orchestration, and all eight
  implementation paths required by the method-transfer contract were retained;
- first-boot/readiness now performs the engineering acceptance checks directly and
  no longer depends on the retired migration verification payload;
- obsolete laptop/runtime snapshots, generated XML/empty failure tables, and the
  duplicate `gate3_resnet_summary` report pair were removed;
- `tests/test_project_state_contract.py` now checks the completed simulated-Test
  summary/hash, closed post-hoc boundaries, live audit references, and absence of
  retired handoff links;
- the 2026-08-08 freeze, manuscript, and application documents remain as historical
  records with a 2026-08-11 supersession notice rather than being silently deleted.

Do not recreate the retired account-handoff or migration-packaging bundles unless a
concrete new delivery requirement appears. Do not delete the active desktop-contract
implementation, V10, Residual, PAMPT, opXRD, RRUFF, or
other negative-result records merely because they are outside the current runtime
path. No data, checkpoint, frozen result, training, inference, or authorization
state changed during cleanup.

Cleanup verification: `283 passed, 39 subtests passed`; all current Markdown links
resolve; no active deleted-file references remain; the Test-metric, split-scope,
and RRUFF lineage auditors pass at their declared levels; desktop first-boot
`-PlanOnly` reports `formal_training_commands=0`.

Publication decision (2026-08-13): the user authorized synchronization of the
reviewed source, configuration, audit, documentation, and cleanup changes to
`origin/main`. Local `outputs/` artifacts and unreviewed personal application drafts
remain excluded. After synchronization, continue manuscript construction within the
frozen evidence and claim boundaries above.
