# 2026-07-24 — P0 Train-only Local Benefit Gate

## Decision

Before authorizing V9-T Validation tuning or formal multi-seed training, add one
strictly Train-only diagnostic that asks whether JS consistency or residual class
decorrelation has a locally favorable optimization direction relative to the
matched Dynamic/Paired ERM baseline.

This is a compute-risk screening step, not an additional paper experiment and not
a substitute for the registered 7-run or 15-run.

## Implemented entry point

```text
scripts/audit_v9_local_benefit.py
```

Default report:

```text
reports/v9_p0_local_benefit.json
```

Utility tests:

```text
tests/test_v9_local_benefit.py
```

## Scientific scope

The diagnostic rebuilds one five-epoch Dynamic/Paired ERM learned state in memory,
fits a competent detached residual probe, and then performs two analyses from the
same learned state:

1. **Gradient-direction analysis**
   - compare the backbone gradient of ERM, ERM + JS, and ERM + Residual with
     independent Train-structure classification gradients under `in_range` and
     the six registered single-factor OOD profiles;
   - positive alignment is only local first-order evidence that an update may
     reduce the panel loss.

2. **Matched one-step counterfactual analysis**
   - restore the identical model and AdamW optimizer state for ERM, JS, and
     Residual branches;
   - apply one update on the same balanced Train batch;
   - evaluate every branch on the same disjoint balanced Train-only in-range/OOD
     panels;
   - report paired changes in CE, correct-class log probability, margin,
     cross-view disagreement, and fixed-probe residual class leakage.

The Residual branch uses the production two-step mechanism: update the residual
classifier on detached residuals, then freeze that classifier while updating the
backbone with classification plus residual-confusion loss.

## Data boundary

Only the frozen Train split is read.

The existing mutually exclusive Train audit subsets remain separated:

- 700 structures for residual-probe calibration;
- 700 structures for residual-probe audit;
- the former 700-structure scale subset is deterministically divided into:
  - 350 local-update structures, 50 per crystal system;
  - 350 local-evaluation structures, 50 per crystal system.

Every diagnostic batch contains two structures per crystal system (14 total).

The following are prohibited and hard-coded as unused:

- Simulation Validation;
- simulated Test;
- RRUFF, GTIIT, opXRD, or any real XRD data;
- checkpoint writing;
- candidate selection;
- changing the frozen lambda grids;
- changing any execution authorization switch.

## Lambda policy

The default diagnostic coefficients are the middle members of the already frozen
candidate grids:

```text
lambda_JS  = 3.0   from {0.3, 3.0, 30.0}
lambda_res = 2.0   from {0.2, 2.0, 20.0}
```

The script accepts only values already present in those grids. A diagnostic value
is not a selected, preferred, or formal value.

## Interpretation boundary

A positive paired CE benefit, favorable bootstrap interval, preserved in-range
behavior, and a method-specific mechanism change may justify continuing to the
registered tuning stage. Mixed or negative results may justify scientific review
before spending the full compute budget.

No result from this P0 gate can establish stable generalization gain, rank final
methods, select a lambda, or appear as the formal paper result. Only the
preregistered Validation tuning followed by matched multi-seed formal evaluation
can support those claims.

## Authorization state

Adding the script and tests does **not** authorize running it automatically. It
does not start tuning or formal training. A human must execute the diagnostic
locally and return the generated JSON report for interpretation.
