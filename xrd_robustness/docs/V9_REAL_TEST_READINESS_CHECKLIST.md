# V9 Real-XRD Readiness Checklist

This checklist prepares a future one-time external test. It does not authorize loading spectra into a model.

## Manifest and provenance

- One row per sample with the exact columns in `configs/v9_prediction_rows.schema.json`'s companion real-test contract.
- Record source, license or permission, label evidence, phase-purity assessment, structure identifier, and SHA256 for every spectrum.
- Preserve conversion logs, missing-angle coverage, duplicate-angle handling, non-finite removals, and anomalous-point decisions.
- Freeze the manifest hash before any selected checkpoint is evaluated.

## Overlap controls

- Compare structure identifier/material ID when available.
- Compare structure fingerprint for known structures.
- Otherwise compare formula plus space group and flag uncertainty.
- Exclude Train overlaps from the primary external population and report them separately.

## Frozen preprocessing

- Grid: 10–80° 2θ inclusive, 0.02° step.
- Stable sort, first duplicate angle retained, linear interpolation, zero outside observed range.
- Max normalization only; no baseline subtraction, smoothing, or manual peak editing.
- Audit output must report the contract and every spectrum hash.

## Unlock conditions

- Validation tuning and 15-run comparison complete.
- Exactly one method and checkpoint set frozen.
- Simulated Test complete and immutable.
- Real manifest, preprocessing contract, and overlap audit frozen.
- User explicitly authorizes the one-time run.

Forbidden: choosing simulator settings, λ, or method from real spectra; inspecting real accuracy early; rerunning after seeing performance without labeling the new work as a separate study.
