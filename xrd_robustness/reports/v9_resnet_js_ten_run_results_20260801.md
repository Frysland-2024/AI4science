# V9 ResNet JS five-seed paired replication results

**Status date:** 2026-08-01  
**Stage:** completed Validation-only replication  
**Comparison:** Dynamic ERM versus JS Consistency (`lambda_js = 60`)  
**Design:** five matched training seeds, two methods per seed, ten runs total

## Executive result

The preregistered five-seed paired replication completed successfully. JS
Consistency improved the primary mean single-factor Validation-OOD Macro-F1 in
all five matched seed pairs and passed the preregistered in-range guardrail.
The result supports retaining JS Consistency with `lambda_js = 60` as the
selected V9 method for the next separately authorized evaluation stage.

This is still development evidence. Simulated Test and real XRD were not used.
No lambda was retuned and no seed was excluded post hoc.

## Aggregate results

| Metric | Dynamic ERM, mean ± sample SD | JS lambda=60, mean ± sample SD | Paired mean delta |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 ± 0.006272 | 0.734648 ± 0.008533 | +0.027757 |
| In-range Macro-F1 | 0.705112 ± 0.010905 | 0.733103 ± 0.008101 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | +0.046569 |
| Worst-class F1 | 0.574014 ± 0.017829 | 0.593611 ± 0.033188 | +0.019597 |

Relative to Dynamic ERM, the aggregate JS gains are approximately `+7.07%`
for mean single-factor OOD Macro-F1, `+3.97%` for in-range Macro-F1, and
`+3.93%` for level-0 Macro-F1.

## Paired effect

The five paired OOD deltas were:

| Training seed | Delta OOD Macro-F1 | Delta in-range Macro-F1 | Delta level-0 Macro-F1 | Delta worst-class F1 |
|---:|---:|---:|---:|---:|
| 20260711 | +0.052272 | +0.012408 | +0.019419 | +0.018822 |
| 20260712 | +0.050535 | +0.042118 | +0.029871 | +0.044035 |
| 20260713 | +0.045151 | +0.034059 | +0.039685 | +0.036783 |
| 20260714 | +0.030343 | +0.005631 | +0.011162 | -0.061139 |
| 20260715 | +0.054546 | +0.045737 | +0.038649 | +0.059483 |

The paired mean OOD improvement is `+0.046569`, with sample SD `0.009711` and
the preregistered paired-bootstrap 95% interval `[0.038145, 0.052834]`.
The paired mean in-range improvement is `+0.027991`, with sample SD `0.017987`
and paired-bootstrap 95% interval `[0.014028, 0.041954]`.

Both intervals exclude zero, and the direction is positive in all five pairs
for the primary OOD metric and the in-range metric. This is strong replication
evidence under the frozen Validation protocol, while the small number of paired
seeds should remain explicit in any paper claim.

## Guardrail and diagnostic caveat

The preregistered guardrail

```text
mean_js_in_range_macro_f1 >= mean_dynamic_erm_in_range_macro_f1 - 0.01
```

passed. In fact, mean in-range Macro-F1 increased by `+0.027991`.

Worst-class F1 is less uniform: four seed pairs improved, but seed `20260714`
decreased by `-0.061139`. Consequently, worst-class F1 should remain a
secondary diagnostic rather than be summarized as uniformly improved. Before
publication, inspect the affected class and condition for that seed and report
whether the drop is class-specific, condition-specific, or checkpoint-specific.
This diagnostic does not overturn the preregistered primary result.

## Research decision

1. Freeze JS Consistency at `lambda_js = 60`; do not reopen lambda tuning from
   these replication results.
2. Treat Dynamic ERM versus JS lambda=60 as the finalized V9 method comparison.
3. Do not access simulated Test or real XRD automatically. Each requires a new,
   explicit protocol and authorization.
4. The next scientific gate should be a frozen simulated-Test evaluation of the
   already selected checkpoints or a clearly specified checkpoint-selection
   rule. No additional Validation-guided method choice is permitted.
5. Preserve the seed-20260714 worst-class anomaly as an explicit limitation and
   diagnostic task.

## Authoritative evidence

- Machine-readable summary:
  `xrd_robustness/reports/v9_resnet_js_ten_run_summary.json`
- Preregistered contract:
  `xrd_robustness/configs/v9_resnet_js_ten_run.preregistered.json`
- Execution authorization:
  `xrd_robustness/configs/v9_resnet_js_ten_run.authorization.json`
- Summary implementation:
  `xrd_robustness/scripts/summarize_v9_resnet_js_ten_run.py`
- Result commit:
  `868b079c1b410e6afe877330b7defc4262d82969`

## Boundary audit

The summary records:

- `simulated_test_used = false`;
- `real_xrd_used = false`;
- `lambda_retuned = false`;
- `seed_excluded_posthoc = false`.

The completed result therefore answers the registered Validation-replication
question only. It is not yet a simulated-Test result, a sim-to-real result, or
a final external-validity claim.
