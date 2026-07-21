# 10 — Known Uncertainties and Stop Conditions

## Unresolved scientific items

| Item | Current status | Safe Codex behavior |
|---|---|---|
| Exact SimXRD files/schema | unverified in this pack | inspect actual data before defining loaders/splits |
| Exact label taxonomy | unverified | load/save a versioned mapping; do not infer class order |
| Dataset license and redistribution rights | unverified | do not publish/redistribute patterns before confirmation |
| Perturbation numeric bounds | unresolved by design | implement parameterized transforms, keep default ranges disabled or clearly provisional |
| Choice of transform distribution | unresolved | expose config; do not hard-code intuitions |
| Chosen network architecture | open | begin with transparent small 1D-CNN baseline; avoid premature architecture search |
| Consistency distance and λ schedule | open | define candidates and tune only on validation data |
| Real-XRD source and labels | open | create an adapter/data-card interface, not fake external results |
| Preprocessing parity sim ↔ real | open | document every operation and test sensitivity |
| Whether texture belongs in main benchmark | unresolved | keep as separate experimental factor until physically justified |
| Whether unit-cell variation is label-preserving | generally unsafe | exclude from central paired-loss study unless structure-aware proof is supplied |

## Stop conditions

Pause and ask the user or create a marked TODO rather than proceeding when:

- source-structure identifiers needed for leakage-safe splits are absent;
- the code would require guessed `2θ` units or grid orientation;
- perturbation magnitudes lack any evidence source;
- a method assumes labels that cannot be verified;
- a real-data result would be presented without provenance;
- an intended change could overwrite raw data or invalidate prior experiments;
- a claimed robust improvement appears with strong clean-accuracy collapse or trivial prediction collapse.

## Claim language guardrail

Use these distinctions:

- **Observed:** directly measured from a saved run.
- **Mechanistically supported:** backed by physics/measurement rationale and evidence.
- **Hypothesis:** plausible explanation awaiting test.
- **Unverified:** required metadata or evidence is missing.

Never turn a hypothesis into a result sentence merely because it is convenient for the project narrative.
