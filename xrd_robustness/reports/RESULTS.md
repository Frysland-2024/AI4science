# Study Results

## Experiment

The experiment compares Dynamic ERM with JS Consistency
(`lambda = 60`) using the same ResNet-18-GN architecture and five matched
seeds. The simulated PXRD dataset contains 14,060 parent
structures split into 9,842 Train, 2,109 Validation, and 2,109 simulated Test
structures.

## Validation

| Metric | Dynamic ERM | JS Consistency | Paired improvement |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.706891 | 0.734648 | +0.027757 |
| In-range Macro-F1 | 0.705112 | 0.733103 | +0.027991 |
| Mean single-factor OOD Macro-F1 | 0.658495 | 0.705064 | +0.046569 |
| Worst-class F1 | 0.574014 | 0.593611 | +0.019597 |

The primary single-factor OOD improvement was positive in all five matched
pairs. Its paired-bootstrap 95% interval was `[0.038145, 0.052834]`. The
in-range improvement was also positive in all five pairs, with a 95% interval
of `[0.014028, 0.041954]`.

## Simulated Test

| Metric | Dynamic ERM | JS Consistency | Paired improvement |
|---|---:|---:|---:|
| Level-0 Macro-F1 | 0.697280 | 0.737159 | +0.039880 |
| In-range Macro-F1 | 0.695267 | 0.734854 | +0.039587 |
| Mean single-factor OOD Macro-F1 | 0.650737 | 0.705336 | +0.054600 |
| Worst-class F1 | 0.511064 | 0.558558 | +0.047495 |

All four aggregate paired improvements were positive in all five matched
pairs. The primary single-factor OOD improvement had sample SD
`0.007271` and a paired-bootstrap 95% interval of
`[0.048944, 0.060255]`.

## Secondary calibration analysis

A post-hoc readout of the already frozen simulated-Test predictions found
systematically lower Expected Calibration Error (ECE) for JS Consistency than
for matched Dynamic ERM evaluations. Across the 180 matched combinations of
five training seeds, three evaluation seeds, and twelve profiles, the extracted
mean paired difference was `DeltaECE = ECE(JS) - ECE(ERM) = -0.0855`, with
all `180/180` paired comparisons favoring JS. The independent CNRS-318
zero-shot evaluation shows the same direction (`0.6826` ERM vs `0.6124` JS),
although both models remain strongly over-confident in that difficult real
domain.

This is treated as a **secondary reliability observation**, not a new primary
method claim. ECE alone cannot distinguish genuine calibration improvement
from general confidence shrinkage. The interpretation, limitations, and minimum
follow-up with NLL, Brier score, mean confidence, and reliability diagrams are
recorded in [`CALIBRATION_ANALYSIS.md`](CALIBRATION_ANALYSIS.md).

Exact aggregate values are available in `validation_results.json` and
`simulated_test_results.json`. The experiment definition is
`../configs/experiment.public.json`.
