# CNRS-318 zero-shot evaluation — results

**Date:** 2026-08-27

**Domain:** CNRS-318 (naturally imbalanced independent experimental domain, 318 structural parents).
**Primary analysis:** zero-shot external evaluation of the frozen models (no CNRS label was used for adaptation or model selection).

> **Reporting role:** this file preserves the complete performance details, integrity
> checks and strict bootstrap audit. The current cross-domain headline follows the
> three-layer policy in
> [`../../docs/PXRD_RESULT_REPORTING_STANDARD.md`](../../docs/PXRD_RESULT_REPORTING_STANDARD.md)
> and [`RESULTS.md`](RESULTS.md). The frozen protocol's historical
> `directional support / stable replication` category is retained below for provenance;
> it is not the current pass/fail criterion for the scientific result.

## Headline

On the second independent experimental source, **all five training seeds favor JS** in
Macro-F1 (mean paired `+0.0187`, about `+1.87 pp`). Pooled Macro-F1, balanced accuracy
and overall accuracy improve, and the performance change is accompanied by lower ECE,
NLL and Brier score. CNRS remains a difficult, naturally imbalanced zero-shot domain;
the performance result does not imply that sim-to-real classification is solved.

| Quantity | Value |
| --- | --- |
| Seed-level Macro-F1, ERM → JS (mean ± sample SD) | **0.1884 ± 0.0263 → 0.2071 ± 0.0213** |
| Mean paired Δ = Macro-F1(JS) − Macro-F1(ERM) (± sample SD) | **+0.0187 ± 0.0068** |
| Positive seeds | **5 / 5** |
| Pooled Macro-F1 | **0.1912 → 0.2091** |
| Pooled balanced accuracy | **0.2182 → 0.2388** |
| Pooled overall accuracy | **0.2000 → 0.2101** |
| Pooled ECE ↓ | **0.6826 → 0.6124** |

The strict class-stratified paired-parent 95% CI is
`[−0.0093, +0.0461]`. It overlaps zero and therefore records substantial uncertainty
under this resampling model, as expected with the natural class imbalance and a
12-parent hexagonal class. It is an audit annotation, not a standalone verdict that
invalidates the 5/5 seed and multi-metric performance picture.

## Per-seed paired Macro-F1

| seed | Dynamic ERM | JS | Δ |
| --- | ---: | ---: | ---: |
| 20260711 | 0.2067 | 0.2212 | +0.0145 |
| 20260712 | 0.1469 | 0.1756 | +0.0286 |
| 20260713 | 0.1842 | 0.1971 | +0.0129 |
| 20260714 | 0.2149 | 0.2295 | +0.0147 |
| 20260715 | 0.1892 | 0.2120 | +0.0228 |

The paired estimand above is the mean of five seed-level Macro-F1 differences. The
pooled values below concatenate the five repeated predictions and are descriptive;
because Macro-F1 is nonlinear, their difference (`+0.01794`) is not the primary
paired estimate (`+0.01871`).

## Descriptive aggregate metrics (five seeds pooled)

| Metric | Dynamic ERM | JS |
| --- | ---: | ---: |
| Macro-F1 | 0.1912 | 0.2091 |
| Balanced accuracy | 0.2182 | 0.2388 |
| Overall accuracy | 0.2000 | 0.2101 |
| ECE | 0.6826 | 0.6124 |
| NLL | 8.3200 | 6.1186 |
| Brier score | 1.4338 | 1.3156 |
| Mean confidence | 0.8826 | 0.8225 |
| Worst-class F1 | 0.0968 | 0.1015 |

## Per-class F1 (five seeds pooled; support = parents)

| Crystal system | n | ERM F1 | JS F1 | ΔF1 |
| --- | ---: | ---: | ---: | ---: |
| triclinic | 21 | 0.1474 | 0.1767 | +0.0292 |
| monoclinic | 87 | 0.2928 | 0.2801 | −0.0128 |
| orthorhombic | 77 | 0.1123 | 0.1811 | +0.0688 |
| tetragonal | 41 | 0.2984 | 0.2362 | −0.0623 |
| trigonal | 33 | 0.0968 | 0.1015 | +0.0047 |
| hexagonal | 12 | 0.1667 | 0.2500 | +0.0833 |
| cubic | 47 | 0.2238 | 0.2383 | +0.0145 |

JS improves five pooled class F1 values and reduces two. The large hexagonal swing is
not a strong class-level result because that class contains only 12 parents.

## Integrity audit

- The eval, parent and preprocessing manifests contain the same 318 unique parents in
  the same order; all labels and representative scan IDs match.
- Rebuilding all 318 inputs from the raw CNRS JSON files reproduces the frozen
  `318 × 3501` float32 array exactly (maximum absolute error `0`).
- All 3,180 `(seed, method, parent)` prediction identities are unique and complete;
  probability sums, argmax values, confidence values and manifest metadata pass.
- All ten checkpoint files exist locally and match the SHA-256 values in the frozen
  configuration.
- Two inputs retain negative measured intensities because the frozen preprocessing did
  not specify clipping: `pattern_409` (minimum `−0.291686`) and `pattern_127`
  (`−0.002875`). This is a documented domain characteristic, not a post-hoc change.
- The original prediction report bound predictions to the eval manifest and recorded
  per-row checkpoint hashes, but did not record the input-NPZ hash, resolved device or
  Git commit. The run record binds the current input and prediction hashes post hoc;
  this is a traceability limitation, not evidence that the stored artifacts disagree.

## Bootstrap correction (2026-08-28)

The first report used `[−0.0149, +0.0521]`. Audit found that the implementation drew
separate multinomial parent weights inside the ERM and JS loops, so the nominally paired
bootstrap was not actually paired. The corrected implementation draws each
class-stratified parent sample once and shares it across both methods and all five fixed
training seeds, as required by the protocol. With 10,000 replicates and seed `20260827`,
the corrected interval is `[−0.009339, +0.046107]`. The interval still crosses zero, so
the result remains in the frozen protocol's historical internal category of
**directional support, not stable replication**. That category is retained to preserve
the pre-run record; current scientific reporting uses the three-layer evidence policy
described at the top of this report.

## Honest interpretation and caveats

- **The 5/5 seed result and multiple standard metrics consistently favor JS; the effect
  remains statistically uncertain.** The corrected parent-bootstrap interval crosses
  zero and is reported in full. Under the historical frozen wording table this mapped
  to "directional support on CNRS", but that internal label is not the current headline
  or a failure judgment.
- **Absolute performance is low.** Balanced accuracy (`0.218→0.239`) is above the
  seven-class uniform reference (`1/7≈0.143`), but overall accuracy (`0.200→0.210`)
  remains below the majority-class baseline (`87/318≈0.274`). The result is evidence
  about relative zero-shot robustness, not a solved sim-to-real classifier.
- **ECE is high** (0.68 ERM / 0.61 JS): the models are over-confident out of domain, a
  typical zero-shot signature.
- **Monoclinic and tetragonal decline.** The larger drop is tetragonal
  (`0.298→0.236`); JS routes many tetragonal patterns to trigonal. This rules out a claim
  of uniform improvement across crystal systems.
- **Hexagonal (n=12) remains underpowered**; its F1 swing (0.167→0.250) is noisy and must
  not be read as a strong per-class conclusion.

## Reproducibility

- Inputs: `outputs/cnrs318_zero_shot/cnrs318_inputs.npz` (318 × 3501, float32), SHA-256
  `980965E95E8A4CFC9020CB1C64976E0B4E95735A7DEFD990407863161C45D7C6`.
- Predictions: `outputs/cnrs318_zero_shot/predictions.ndjson` (3180 rows), SHA-256
  `DE9AE0A3A7C60D84AD8F4DD1083A00811A5A387BD68F3DE49DAF60B81B09A160`.
- Eval manifest: `manifests/cnrs318_eval_manifest.csv`, SHA-256
  `373DDD5FDC9FE5BB879D242C58CDB4969D50FA69AB009383AA6C96416A6A2A98`.
- Lightweight parent manifest: `manifests/cnrs_318_parent_manifest_v2.csv`, SHA-256
  `8E2B4A61C459D440BEFDB18A793E1B413BDD9D253637B99F66AE61C448BD465D`.
- Bootstrap: class-stratified paired parent, shared parent draw across methods and fixed
  seeds, 10,000 replicates, seed `20260827`.
- Tracked analysis entry point: [`../scripts/analyze_cnrs318_results.py`](../scripts/analyze_cnrs318_results.py).
- Tracked report-artifact builder: [`../scripts/build_cnrs318_audit_artifact.py`](../scripts/build_cnrs318_audit_artifact.py).
- Machine-readable run record: [`../manifests/cnrs318_zero_shot_run_record.json`](../manifests/cnrs318_zero_shot_run_record.json).
- Local technical audit: `outputs/cnrs318_zero_shot/audit/report.html` (ignored by Git).
