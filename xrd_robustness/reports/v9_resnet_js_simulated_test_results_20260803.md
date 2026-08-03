# V9 ResNet-JS simulated-Test result record

**Execution date:** 2026-08-03
**Status:** completed
**Scope:** frozen simulated Test only; no real XRD or real-domain adaptation

## Execution and integrity

- The authorized identical retry used the frozen ten Validation-selected
  checkpoints, three deterministic evaluation seeds, and 2,109 held-out parent
  structures.
- The one-time panel cache contains all 36 seed/profile blocks. Each frozen
  spectrum was rendered once and reused across the ten serial checkpoint
  evaluations.
- Inference batch size was 128. The atomic run state records 10/10 completed
  checkpoint outputs and finished at `2026-08-03T06:10:08.187173+00:00`.
- Wall-clock time observed by the launcher was 323.2 seconds, including cache
  construction, hashing, checkpoint loading, inference, and aggregation.
- A 12-second sample taken during sustained checkpoint inference was
  `95, 92, 97, 96, 96, 92, 97, 91, 92, 96, 91, 96%`: mean 94.25%, range
  91-97%. Cache construction is CPU-bound and is not included in this GPU
  utilization statement.
- `summary_sha256` and `panel_cache_index_sha256` recomputed exactly match the
  completed audit. The summary SHA-256 is
  `AE8D15C0FB7FF54FB3C2499E19F1439F4FC58A7A43EC1AADBF29382756E3F267`.
- The local output directory still contains `runner.stderr.log` from the first
  aborted infrastructure attempt. Its non-empty-output error is historical and
  is not a failure of this completed retry; the completed run was launched
  directly and is evidenced by `run_state.json`, the ten output hashes, the
  summary, and the audit.

## Preregistered primary result

The primary endpoint is the JS-minus-Dynamic-ERM paired delta in mean
single-factor OOD Macro-F1. Each checkpoint is first averaged over six frozen
single-factor OOD profiles and three evaluation-panel seeds; the five matched
training-seed pairs are the only statistical replicates.

| Pair / training seed | OOD Macro-F1 delta | In-range delta | Level-0 delta | Worst-class delta |
|---|---:|---:|---:|---:|
| 1 / 20260711 | +0.054848 | +0.020783 | +0.026645 | +0.056669 |
| 2 / 20260712 | +0.061401 | +0.042799 | +0.038316 | +0.053675 |
| 3 / 20260713 | +0.049859 | +0.046594 | +0.042936 | +0.043196 |
| 4 / 20260714 | +0.045077 | +0.034932 | +0.033839 | +0.005531 |
| 5 / 20260715 | +0.061813 | +0.052829 | +0.057662 | +0.078403 |

The mean paired OOD delta is **+0.054600**, with sample SD `0.007271` and the
preregistered paired-bootstrap 95% interval **[+0.048944, +0.060255]**. All
five paired OOD deltas and all five in-range deltas are positive. This confirms
the frozen simulated-Test hypothesis for JS Consistency relative to matched
Dynamic ERM. It is not evidence about real-XRD external validity.

## Seed 20260714 secondary diagnosis

The Validation-stage seed-20260714 worst-class decline did not reproduce as an
aggregate simulated-Test decline: the paired worst-class delta is `+0.005531`.
Monoclinic remains the bottleneck. Averaged across the six single-factor OOD
profiles and three evaluation seeds, monoclinic F1 changes only from `0.513863`
to `0.516974`, while the paired macro-F1 improves by `+0.045077`.

The profile-level worst-class changes explain the small aggregate gain:

| Single-factor OOD profile | ERM worst class/F1 | JS worst class/F1 | Worst-class delta | Macro-F1 delta |
|---|---:|---:|---:|---:|
| negative shift | monoclinic / 0.547722 | monoclinic / 0.529919 | -0.017803 | +0.016189 |
| positive shift | monoclinic / 0.550454 | monoclinic / 0.517793 | -0.032661 | +0.034481 |
| broadening | monoclinic / 0.410605 | monoclinic / 0.502698 | +0.092093 | +0.100173 |
| noise | monoclinic / 0.537303 | monoclinic / 0.535593 | -0.001710 | +0.019026 |
| background | monoclinic / 0.534451 | monoclinic / 0.551988 | +0.017537 | +0.045402 |
| texture | orthorhombic / 0.489455 | monoclinic / 0.463850 | -0.025605 | +0.055192 |

Thus the aggregate worst-class recovery is driven mainly by a large
broadening-profile improvement and a smaller background improvement, while
shift and texture conditions retain monoclinic/orthorhombic limitations. The
scientifically supportable statement is improved aggregate robustness, not
uniform improvement for every class and perturbation.

## Evidence locations and boundaries

Tracked evidence:

- `reports/v9_resnet_js_simulated_test_preflight.json`
- `reports/v9_resnet_js_simulated_test_summary.json`
- `reports/v9_resnet_js_simulated_test_audit.json`
- this result record

Local Git-ignored evidence:

- `outputs/v9_resnet_js_simulated_test_v1/run_state.json`
- `outputs/v9_resnet_js_simulated_test_v1/raw_results.json`
- ten per-checkpoint result JSON files
- `outputs/v9_resnet_js_simulated_test_panel_cache_v1/index.json` and its 36
  memory-mapped spectrum blocks

No checkpoint, generated spectrum, cache, or raw output is admitted to Git.
Real XRD and real-domain adaptation remain unused and locked.
