# Report and evidence index

Use this file to distinguish current, frozen and historical records. Large generated
arrays, prediction rows, checkpoints and portable reports remain under `../outputs/`
and are intentionally ignored by Git.

Current reporting follows
[`../../docs/PXRD_RESULT_REPORTING_STANDARD.md`](../../docs/PXRD_RESULT_REPORTING_STANDARD.md):
Layer A is community-standard performance, Layer B is supporting reliability evidence,
and Layer C is strict statistical/provenance audit. Frozen protocols and historical
wording categories remain preserved, but do not override the current cross-domain
scientific interpretation.

## Current canonical results

| Record | Scope |
|---|---|
| [`RESULTS.md`](RESULTS.md) | Layer-A cross-domain headline performance、Layer-B reliability 与 Layer-C audit 摘要 |
| [`validation_results.json`](validation_results.json) | Frozen simulated-validation aggregates |
| [`simulated_test_results.json`](simulated_test_results.json) | Frozen simulated-Test aggregates plus a SHA-bound community-reporting Accuracy extension |
| [`rruff301_fewshot_results.json`](rruff301_fewshot_results.json) | Retrospectively verified K=1/2/5 RRUFF Macro-F1 and Accuracy aggregates, with provenance boundary |
| [`CNRS_318_RESULTS.md`](CNRS_318_RESULTS.md) | Completed CNRS-318 performance details plus Layer-C integrity and paired-bootstrap audit |
| [`CALIBRATION_ANALYSIS.md`](CALIBRATION_ANALYSIS.md) | Calibration/proper-scoring-rule analysis on simulated Test and CNRS |
| [`CALIBRATION_EVIDENCE_PACKAGE.md`](CALIBRATION_EVIDENCE_PACKAGE.md) | Claim-to-artifact evidence map for the reliability result |

## Frozen CNRS design and data identity

| Record | Scope |
|---|---|
| [`CNRS_318_DATASET_AUDIT.md`](CNRS_318_DATASET_AUDIT.md) | Git-trackable dataset construction and role decision |
| [`CNRS_318_EVALUATION_PROTOCOL.md`](CNRS_318_EVALUATION_PROTOCOL.md) | Pre-run frozen protocol retained unchanged; completion and corrections live in the result/run records |
| [`../configs/real.cnrs318.zero_shot.frozen.json`](../configs/real.cnrs318.zero_shot.frozen.json) | Immutable pre-run configuration; `status=spec_frozen` is historical by design |
| [`../manifests/cnrs318_zero_shot_run_record.json`](../manifests/cnrs318_zero_shot_run_record.json) | Machine-readable completed-run binding and corrected result summary |

## Historical or superseded records

[`opxrd_cnrs7cs_independent_parent_audit_20260827.md`](opxrd_cnrs7cs_independent_parent_audit_20260827.md)
is a preserved independent audit snapshot. Its early 317-parent conclusion was
superseded after fixing duplicate-representative selection within the eligible stratum;
the current count is 318. It is retained for audit history, not as the current result.

## Local generated package

Run:

```powershell
python scripts/analyze_cnrs318_results.py
python scripts/build_cnrs318_audit_artifact.py
node <data-analytics-plugin-root>/skills/build-report/scripts/deliver_portable_artifact.mjs `
  --input outputs/cnrs318_zero_shot/audit/artifact.json `
  --output outputs/cnrs318_zero_shot/audit/report.html
```

The ignored directory `../outputs/cnrs318_zero_shot/audit/` then contains
`summary.json`, corrected bootstrap output, per-seed/per-class CSVs and the portable
`report.html`. The raw 3,180-row predictions and `318 × 3501` input NPZ remain one level
above it. Do not move or delete those frozen artifacts while the run record refers to
their SHA-256 values.
