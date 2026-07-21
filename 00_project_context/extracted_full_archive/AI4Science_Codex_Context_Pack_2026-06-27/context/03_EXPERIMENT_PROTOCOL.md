# 03 — Experiment Protocol and Ablation Standard

## Baseline suite

The following definitions are the default comparison matrix. Any deviation must be named and justified in the config.

| ID | Name | Supervised terms | Consistency term | Purpose |
|---|---|---|---|---|
| E0 | ERM-clean | `CE(x, y)` | none | ordinary clean baseline |
| E1 | Aug-only | `0.5 CE(x,y) + 0.5 CE(T(x),y)` | none | tests conventional data augmentation |
| E2 | Aug + Consistency | `0.5 CE(x,y)+0.5 CE(T(x),y)` | `λD(p(x),p(T(x)))` | tests the added value of paired-view consistency beyond the identical augmentation baseline |

`Consistency-only` is not a core condition. Since `D(p(x), p(T(x)))` requires the transformed view, it cannot isolate consistency from augmentation. If transformed-view CE is removed for a diagnostic study, name the condition explicitly and do not interpret it as no-augmentation consistency.

## Fair-comparison requirements

- Same model architecture and parameter count.
- Same train/validation/test structure groups.
- Same optimizer family, epoch budget, batch size policy, scheduler, and early stopping rules unless an ablation explicitly changes one.
- Identical perturbation families, severity distribution, sampling seeds, and two-view forward passes for E1 and E2.
- Identical classification-loss scaling for E1 and E2; only the consistency term may differ.
- Same number of random seeds for headline results.
- Hyperparameters selected through validation data only.
- Main test data remains untouched until model/protocol freeze.

## Main metrics

For paired samples `(x_i, x'_i)`:

### Accuracy

```text
CleanAcc      = mean[ argmax f(x_i)  == y_i ]
PerturbedAcc  = mean[ argmax f(x'_i) == y_i ]
```

### FlipRate

```text
FlipRate = mean[ argmax f(x_i) != argmax f(x'_i) ]
```

Report FlipRate both overall and conditional on clean-correct predictions.

### Probability disagreement

```text
MeanJS = mean[ JS(p(x_i), p(x'_i)) ]
```

or use the chosen distance `D` consistently.

### Confidence behavior

At minimum record:

- max predicted probability for clean and perturbed views;
- confidence change after perturbation;
- NLL and Brier score where applicable;
- Expected Calibration Error (ECE) with stated binning.

### Sample-level churn

For `K` perturbation draws of a base sample:

```text
Churn_i = 1 - max_c count(prediction_{i,1:K}=c)/K
```

This exposes instability that a one-pair FlipRate can miss.

## Required stratifications

Report at least:

- perturbation family;
- severity level;
- predicted class and true class;
- clean-correct vs clean-incorrect subsets;
- class frequency / minority classes;
- source structure group or material family where metadata permits.

## Statistical reporting

- Use at least 3 independent seeds for headline comparisons when computationally feasible.
- Include mean, standard deviation, and paired confidence intervals or bootstrap intervals for key differences.
- Preserve per-sample predictions; do not retain only aggregate means.
- Avoid over-interpreting small deltas without uncertainty estimates.

## Sanity checks

1. Identity transform should produce near-zero pairwise disagreement.
2. Severity zero should reproduce the clean input under numerical tolerance.
3. All transforms must preserve intensity shape/grid expectations and non-negativity constraints.
4. The transformed pattern should not leak class labels through filenames, ordering, padding, or transformation parameter defaults.
5. Verify a transformation implementation with plotted examples before training.
6. Ensure paired views never cross data splits.

## Result interpretation

A lower FlipRate alone is insufficient if it comes with collapsed confidence, poor clean accuracy, or trivial constant predictions. Always examine clean accuracy, robust accuracy, class-wise behavior, confidence, and the full ablation matrix together.
