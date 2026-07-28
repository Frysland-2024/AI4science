# V10 Train-only Matched Pilot

## Purpose

This Pilot tests whether the proposed V10 simulator-supervised residual method is trainable and behaves in the intended direction before any formal V10 experiment is designed.

It is allowed only because `reports/v10_p0_measurement_information_gate.json` passed the V10 premise Gate. The Pilot does **not** wait for V9 formal hyperparameter selection because it is isolated from Validation/Test and cannot change the frozen V9 comparison.

## Matched branches

Three branches start from exactly the same PAMPT-B3 initialization and consume the same paired dynamic Train views:

1. Dynamic/Paired ERM;
2. V9 residual decorrelation;
3. V10 signed residual with simulator-known measurement supervision and crystal-class decorrelation.

Batch-level random seeds are reset so stochastic backbone operations are matched across branches.

## V10 supervision target

The signed residual uses `second - first` and predicts four normalized simulator deltas:

- log peak-width difference;
- background-to-peak-ratio difference;
- log inverse photon-count-scale difference;
- electronic readout-noise difference.

These represent the three measurement families that passed the V10-P0 strength Gate: broadening, background, and noise. Peak shift and texture are not core strength-supervision targets in this Pilot.

## Frozen Pilot defaults

- Train-only;
- 3 epochs;
- 200 structures per crystal system for training;
- 10 structures per crystal system for each independent calibration/audit panel;
- 100 grouped permutation draws;
- residual target weight: `0.2`;
- perturbation target weight: `1.0`;
- 1 epoch ERM warm-up followed by a 2-epoch linear ramp.

These weights are diagnostic constants, not selected formal V10 hyperparameters.

## Pilot decision

`PASS` requires all three conditions at the final epoch:

1. signed residual still contains identifiable measurement-family information and at least two of background/broadening/noise strength targets pass independent probing;
2. V10 signed-residual crystal leakage is lower than V9 symmetric-residual crystal leakage;
3. V10 controlled-panel classification CE is no more than `0.10` above matched ERM.

`PARTIAL` means measurement information is retained but leakage reduction or the classification-cost boundary is not demonstrated. `HOLD` means measurement information is not retained.

No result automatically authorizes formal V10 training.

## Isolation boundaries

The Pilot:

- reads only the frozen Train split;
- uses mutually disjoint training, calibration, and audit structures;
- reads no Validation, simulated Test, RRUFF, GTIIT, opXRD, or other real XRD;
- writes no checkpoint;
- does not select V9 or V10 hyperparameters;
- cannot modify the frozen V9 seven-run grid.

## Run

From `E:\AI4science\xrd_robustness`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\run_v10_pilot.ps1
```

Output:

```text
reports\v10_train_only_pilot.json
```
