# XRD Robustness Evidence Index

**Last consolidated:** 2026-08-23

**Current scientific line:** V9-T seven-crystal-system PXRD robustness

**Selected comparison:** ResNet-18-GN, Dynamic ERM versus JS Consistency
(`lambda_js = 60`)

**Historical recovery baseline:** Git commit
`f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217`

This file is the compact human-readable index for the evidence that remains
scientifically relevant after repository consolidation. Machine-readable JSON
artifacts remain authoritative for exact values and hashes. Detailed retired
reports, one-off scripts, and obsolete contracts can be inspected at the
recovery baseline without keeping them in the active working tree.

## 1. Scientific identity and frozen design

- The completed task is robust **seven-class crystal-system classification**
  from simulated 1D PXRD, not lattice-parameter, phase-fraction, strain, or
  instrument-parameter inversion.
- The final backbone is ResNet-18-GN. The matched method comparison is ordinary
  Dynamic ERM against JS Consistency with `lambda_js = 60`.
- The formal database contains 14,060 parent structures: 9,842 Train, 2,109
  Validation, and 2,109 simulated Test.
- Exact parent fingerprints are disjoint across the three splits. Exact formula
  identity is not disjoint: 47 formulas cross split boundaries, covering 585
  records, and 12 formulas occur in all three splits. The supported description
  is therefore **exact-parent-disjoint**, not family-disjoint or formula-disjoint.
- Measurement shift, broadening, preferred orientation, background, and noise
  are nuisance variables used to generate views. They are not supervised
  inversion targets in V9-T.

Authoritative split audit:
`v9_formal_split_identity_overlap_audit.json`.

## 2. Five-seed Validation replication

The completed Validation comparison contains five matched training seeds and
ten runs. No simulated Test, real XRD, post-hoc seed exclusion, or lambda
retuning was used at this stage.

| Metric | Dynamic ERM mean | JS mean | Paired mean delta |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

The primary OOD gain was positive in all five pairs. Its paired-bootstrap 95%
interval was `[0.038145, 0.052834]`; the in-range guardrail passed. Worst-class
behavior was not uniform: seed `20260714` had a Validation worst-class delta of
`-0.061139`. This remains a secondary limitation and does not alter the frozen
primary decision.

Authoritative artifact: `v9_resnet_js_ten_run_summary.json`.

## 3. Frozen simulated Test

The already selected ten checkpoints were evaluated serially on the frozen
2,109-parent simulated Test with three evaluation seeds. Spectra were rendered
once and reused; the audit records ten checkpoints and no real-XRD access.

- Primary JS-minus-ERM mean paired single-factor OOD Macro-F1 delta:
  **+0.054600**.
- Sample SD across the five matched training-seed pairs: `0.007271`.
- Paired-bootstrap 95% interval: **[+0.048944, +0.060255]**.
- All five OOD deltas and all five in-range deltas were positive.
- The seed-`20260714` simulated-Test worst-class delta was `+0.005531`, but
  profile- and class-level behavior remained heterogeneous.

The historical `per_crystal_system_f1` diagnostic was computed incorrectly by
applying a seven-class Macro-F1 routine after filtering to one true class. The
360 profile records are corrected in a sidecar generated from each full-panel
confusion matrix. Primary Macro-F1, correct `per_class_f1`, paired deltas,
bootstrap intervals, and the frozen per-run JSON hashes are unchanged.

Authoritative artifacts:

- `v9_resnet_js_simulated_test_preflight.json`
- `v9_resnet_js_simulated_test_summary.json`
- `v9_resnet_js_simulated_test_audit.json`
- `v9_resnet_js_simulated_test_class_metric_correction.json`

## 4. RRUFF-301 retrospective validation

The surviving RRUFF-301 artifacts are useful external-domain **retrospective
validation**, but they do not support a prospective or confirmatory claim. The
historical runner, support IDs, pre-execution authorization, execution log, and
complete code/runtime binding are unavailable. No later documentation can
reconstruct that missing historical governance chain.

What is currently verifiable:

- 150 few-shot records have accuracy, Macro-F1, and per-class F1 recomputed from
  34,650 prediction rows.
- Every few-shot run uses the same locked 231-ID test membership.
- Ten zero-shot and 100 fixed-200 records pass their declared hash, schema,
  grid, and metric-range checks, but their prediction rows are unavailable for
  full metric recomputation.
- Ten local checkpoints matched their registered SHA-256 values when the
  lineage audit was generated.
- The result artifacts are internally consistent at their explicitly declared
  verification levels; original-execution reproducibility remains incomplete.

Retrospective aggregate results, retained here because the verbose report is
retired:

| K | ERM Macro-F1 | JS Macro-F1 | Mean paired delta | Positive pairs |
|---:|---:|---:|---:|---:|
| 1 | 0.2847 | 0.3280 | +0.0433 | 21/25 |
| 2 | 0.3026 | 0.3486 | +0.0460 | 23/25 |
| 5 | 0.3555 | 0.4099 | +0.0545 | 24/25 |

The corresponding accuracy deltas were `+0.0384`, `+0.0488`, and `+0.0568`.
Sample-level fix/break ratios were 1.31, 1.43, and 1.57 for K=1, 2, and 5,
respectively. Benefits were sample- and class-dependent; they do not establish
uniform improvement. The RRUFF-70 monoclinic negative-transfer observation did
not reproduce in these RRUFF-301 artifacts.

Authoritative surviving artifacts:

- `rruff301_existing_artifact_lineage_audit.json`
- `rruff301_representation_analysis_20260807.md`
- `rruff301_retrospective_replay_episode_plan.json`

The episode plan is a new deterministic replay plan, not evidence that the
historical execution used that plan. The replay contract is fail-closed and
does not authorize model or spectrum access.

## 5. Retired branches and negative results

These conclusions remain part of the scientific record, while their verbose
working files and single-use implementations are retired from the active tree.

### PAMPT backbone

PAMPT-B3 was a major bottleneck relative to ResNet-18-GN in the matched Gate 3
diagnostic: level-0 Macro-F1 was `0.5327` versus `0.6522`, and train accuracy at
stop was `0.6385` versus `1.0000`. The project therefore froze ResNet-18-GN for
the final method comparison.

### Measurement-supervised residual mechanism

The train-only residual stability gate did not demonstrate the preregistered
stable signal: 1/3 seeds passed the signal criterion at epoch 5 even though 2/3
passed at epoch 10. Residual-lambda reopening was not authorized. This retired
branch is distinct from the later prospective inversion modules.

### V10 disentanglement pilots

The train-only information premise gate found decodable measurement signal,
but this did not establish disentanglement or held-out benefit. Pilot v1 ended
`HOLD`; pilot v2 ended `PARTIAL` because measurement information was retained
without demonstrating the required leakage reduction or full classification
cost boundary. Neither pilot authorized formal V10 execution.

### opXRD feasibility

After the parser correction, 912 full structures matched the source paper's
reported coverage and five possible ferroelectric-related candidates were
found. They occupied only two classes (three Bi-Fe-O-like orthorhombic and two
Sr-Ti-O-related cubic records), far below every registered class/family gate.
The final decision was evidence-based `NO_GO`; opXRD was not used as a real-XRD
benchmark.

### RRUFF-70 pilot

RRUFF-70 was an exploratory 70-spectrum development asset. It showed positive
mean JS-minus-ERM few-shot accuracy deltas of approximately `+0.043`, `+0.049`,
and `+0.071` for K=1, 2, and 5, but its small query sets and class-specific
effects, including a K=5 monoclinic decline, preclude confirmatory use. It was
superseded by the larger RRUFF-301 retrospective analysis.

## 6. Claim boundary

The repository evidence supports these statements:

1. Under the frozen V9-T simulator, split, backbone, and five matched seeds, JS
   Consistency at `lambda_js = 60` improved aggregate Validation and simulated-
   Test robustness relative to Dynamic ERM.
2. The RRUFF-301 stored artifacts are internally consistent at their declared
   verification levels and show a retrospective JS advantage under few-shot
   adaptation.
3. Several alternatives were rejected by explicit gates rather than silently
   omitted.

The repository evidence does **not** support these statements:

1. The formal split is family-disjoint or exact-formula-disjoint.
2. V9-T is a completed physics-parameter inverse solver.
3. RRUFF-301 is prospective confirmatory evidence or has complete historical
   execution provenance.
4. JS improves every seed, class, perturbation, or individual spectrum.
5. Real ferroelectric-laboratory XRD external validity has been established.
6. Any sealed future inversion module has been implemented or authorized.

## 7. Recovery and preservation policy

For retired tracked material, use the immutable consolidation baseline without
restoring the whole historical tree, for example:

```text
git show f36be82b2a0b5fd3c58ec87a58fa6e3ba839f217:<repository-relative-path>
```

Datasets, spectra, checkpoints, caches, and raw outputs remain local/ignored and
are not evidence that should be committed. The Git-safe ten-run registry and
verification records preserve checkpoint provenance without admitting model
weights into source control.

`reports/provenance/` contains eight earlier V9-T audit artifacts that remain
path- and hash-bound by the frozen method contract. They are retained as a small
dependency set rather than treated as current headline results. The three-file
ten-run Git-safe archive is kept separately. Every maintained report directory
therefore contains fewer than ten direct files even though these evidence roles
remain distinct.
