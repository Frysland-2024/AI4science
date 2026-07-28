# V10 Train-only Pilot v2

## Why v2 exists

Pilot v1 ended with all three branches at seven-class chance accuracy. Its `HOLD` result therefore cannot distinguish a failed V10 mechanism from an immature backbone. Pilot v2 adds a mandatory learned-state phase before any V9/V10 residual comparison.

## Phase 1: learned-state pretraining

- PAMPT-B3;
- Dynamic/Paired ERM only;
- complete frozen Train split;
- 5 epochs;
- no Validation, simulated Test, or real XRD;
- no checkpoint.

The learned-state panel is diagnostic rather than a held-out generalization panel. The model may have seen these Train structures; the panel only asks whether classification learning exists.

## Gate A: classification learning

The Pilot continues only if the controlled Train-only panel satisfies both:

1. classification accuracy is above chance plus two binomial standard errors, using 70 material-level sampling units;
2. classification CE is below `ln(7)`.

Failure returns `INELIGIBLE_LEARNED_STATE`. V10 is not interpreted.

## Gate B: premise recheck

On the same learned ERM backbone, the Pilot requires:

- measurement-family signal in the signed residual;
- at least two passing strength probes among background, broadening, and noise;
- crystal-system leakage in either signed or symmetric residual.

Failure returns `HOLD_PREMISE_RECHECK`; the three branches are not started.

## Phase 2: matched branches

After both gates pass, the learned model and main AdamW optimizer state are copied into:

1. Dynamic/Paired ERM;
2. V9 residual decorrelation;
3. V10 signed residual with simulator-known measurement supervision.

All branches receive identical dynamic pairs and matched dropout seeds. The branch phase uses 200 structures per crystal system for 3 epochs.

Frozen diagnostic constants remain:

- residual weight: `0.2`;
- perturbation-supervision weight: `1.0`;
- one branch epoch at zero auxiliary weight;
- two-epoch linear ramp.

These are not selected hyperparameters.

## Final decision

`PASS` requires:

1. measurement-family signal and at least two passing strength probes in V10;
2. V10 signed-residual crystal leakage lower than V9 signed-residual leakage;
3. V10 symmetric-residual leakage no higher than V9 symmetric-residual leakage;
4. V10 classification CE no more than `0.10` above matched ERM.

`PARTIAL` means measurement information is retained but leakage or classification-cost conditions are incomplete. `HOLD` means measurement-strength information is not retained after a demonstrated learned state.

No result automatically authorizes formal V10 training or changes the frozen V9 grid.

## Run

From `E:\AI4science\xrd_robustness`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
& .\scripts\run_v10_pilot_v2.ps1
```

Output:

```text
reports\v10_train_only_pilot_v2.json
```
