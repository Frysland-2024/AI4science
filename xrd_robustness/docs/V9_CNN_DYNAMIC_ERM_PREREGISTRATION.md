# V9 CNN Dynamic ERM diagnostic preregistration

Only one scientific factor changes relative to the selected Clean reference:
`clean_erm` becomes `ordinary_dynamic`. The ResNet-18-GN architecture, identity
input representation, AdamW optimizer, constant learning rate, parent-structure
split, seeds, batch size, optimizer-step budget, validation interval, evaluation
panels, dynamic stream contract, and early-stopping rule are fixed.

The diagnostic compares in-range, mean single-factor OOD, and level0 Macro-F1
against the selected Clean reference. Per-class F1, confusion matrices,
ID-to-OOD gaps, and the train-to-validation gap are required secondary evidence.

No JS, Residual, curriculum, clean anchor, new perturbation parameter, new
split, simulated Test, or real XRD access is authorized. The formal seven-run
queue remains 0/7. This development-only diagnostic cannot support a formal
paper performance claim.
