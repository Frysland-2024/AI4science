# V10 Module Archive and Future Directions

## Status

**V10 is frozen and archived.**

The active project mainline remains the frozen V9 method-transfer study. No further V10 training, parameter search, architecture modification, or additional pilot is authorized at this stage.

V10 may only be reopened after the V9 validation program is completed and a new, explicit scientific decision record is approved.

## Original V10 hypothesis

V10 was designed to improve the V9 residual-decorrelation idea by using simulator-known measurement labels.

The intended decomposition was:

- the residual should retain measurement information;
- the residual should not retain crystal-system information.

In other words, V10 attempted to turn the residual from an unconstrained feature difference into an interpretable measurement representation.

## Evidence chain

### 1. V10-P0 premise gate

The Train-only premise gate passed.

It demonstrated that the learned residual was not pure noise:

- measurement-family information was independently decodable;
- several measurement strengths were independently decodable;
- crystal-system information was also independently decodable.

This supported the scientific legitimacy of a measurement-semantic disentanglement study, but it did not authorize formal V10 training.

Protected report:

```text
reports/v10_p0_measurement_information_gate.json
SHA256: 22EF5EFCFD63ABEA3AFE1848B0F7E1B12C3849B006B1FE091FE5918AD5AC2CAB
```

### 2. V10 Train-only Pilot v1

Pilot v1 returned `HOLD`, but all three branches remained near seven-class chance performance.

Therefore, the result could not distinguish a failed V10 mechanism from an immature backbone. It was recorded as an insufficient learned-state experiment rather than a rejection of the V10 hypothesis.

Protected report:

```text
reports/v10_train_only_pilot.json
SHA256: C3F1B64A8022B011F0997085A7D4F42A56CD28C95EAFBAF2B62263F7D326B1DB
```

### 3. V10 Train-only Pilot v2

Pilot v2 first pretrained the backbone on the complete frozen Train split and required a learned-state gate before comparing ERM, V9 residual, and V10 supervised residual branches.

The learned-state gate passed:

- Train-only controlled-panel accuracy: `31.43%`;
- Train-only controlled-panel CE: `1.7016`;
- seven-class chance accuracy: `14.29%`;
- uniform CE: `ln(7) = 1.9459`.

The final Pilot status was `PARTIAL`.

Positive findings:

- V10 retained measurement-family information;
- by the final branch epoch, background, broadening, and noise strengths were all independently decodable;
- classification cost relative to matched ERM was small: CE delta `+0.00394`.

Failed disentanglement findings:

- V10 signed-residual crystal leakage exceeded matched V9 signed leakage by `+0.01429` accuracy;
- V10 symmetric-residual crystal leakage exceeded matched V9 symmetric leakage by `+0.03714` accuracy;
- the leakage increase appeared after auxiliary supervision was activated.

Protected report:

```text
reports/v10_train_only_pilot_v2.json
SHA256: 86762B1B0AD74C32AB8E7BA8A8E1A6BC366F2F0C8F6A245AE4856CE1B47B4228
```

## Current scientific conclusion

The V10 experiments support the following asymmetric conclusion:

> Measurement representation learning is feasible, but unconditional simulator supervision increases the total information content of the residual rather than separating measurement information from crystal semantics.

The original V10 mechanism therefore did not complete the intended disentanglement.

A second important observation is that the internal adversarial probe could approach chance while an independent detached probe still decoded crystal-system information. This indicates that the current adversarial head can be defeated without removing the underlying leakage.

The present failure mode is therefore structural, not merely a question of running more epochs or selecting a different scalar weight.

## Candidate redesign if V10 is reopened

The leading future direction is a **semantically conditioned measurement decoder with stop-gradient context**.

Instead of requiring the residual alone to predict measurement strength,

```text
measurement_decoder(residual) -> measurement labels
```

provide the decoder with a detached crystal-semantic context:

```text
semantic_context = stop_gradient(crystal_semantic_representation)
measurement_decoder(residual, semantic_context) -> measurement labels
```

The motivation is that the physical response to broadening, background, or noise can depend on the underlying crystal pattern. Without context, the residual may be forced to re-encode crystal identity in order to predict the measurement variable. A detached semantic context can supply this conditional information without allowing the measurement objective to reshape the semantic pathway.

A future implementation should preserve the independent requirement:

```text
crystal_probe(residual) -> unpredictable crystal system
```

while testing whether the conditioned decoder preserves measurement-family and strength information.

This is an architecture-level redesign. It must not be treated as a post-hoc weight adjustment to the current V10 implementation.

## Reopening conditions

V10 remains archived unless all of the following are satisfied:

1. the frozen V9 validation study has been completed;
2. the V9 results justify further residual-mechanism research;
3. a new Train-only protocol is preregistered before any new run;
4. the redesign is compared against matched ERM and matched V9 residual baselines;
5. no Validation, simulated Test, or real XRD is used for V10 architecture invention;
6. the new study is explicitly separated from the current V9 paper mainline.

## Project-development record

This module records an important change in the project’s reasoning:

1. residual class leakage was first treated as a problem to suppress;
2. the project then asked whether the residual contained meaningful measurement information rather than noise;
3. simulator supervision successfully strengthened measurement decodability;
4. the controlled Pilot showed that measurement information and crystal semantics were strengthened together;
5. the project therefore rejected the simplistic assumption that positive measurement supervision automatically produces disentanglement;
6. V10 was frozen rather than repeatedly tuned until it passed.

This is a negative-but-informative result: it identifies a concrete failure mode and a principled future redesign while protecting the V9 mainline from uncontrolled expansion.
