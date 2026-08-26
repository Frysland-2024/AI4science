# CNRS-318 evaluation protocol (frozen)

**Date:** 2026-08-27

**Status:** protocol frozen; **evaluation not yet run** (readiness = PENDING).

This protocol freezes how the frozen models are evaluated on CNRS-318. It does
not run training or inference and does not touch the already-frozen simulated
results.

## Domain role

CNRS-318 = **naturally imbalanced independent experimental domain** (formal
second real domain). RRUFF-301 = **balanced curated experimental domain**. The
two are complementary; CNRS-318 is not required to be class-balanced or equal
in size to RRUFF-301.

## Evaluation scope

- Use **all 318 structural parents**; do **not** downsample to 84.
- Do **not** replicate or oversample hexagonal to "balance" the classes.
- Class imbalance is reported transparently, not corrected.

## Primary question

On the **same 318 parents**, does JS still beat ERM?

```
Δ_CNRS = Macro-F1(JS) − Macro-F1(ERM)
```

All statistics are paired per structural parent.

## Metrics

- **Primary:** Macro-F1.
- **Auxiliary:** balanced accuracy, overall accuracy, per-class
  precision/recall/F1, confusion matrix, per-class support counts, and the
  JS−ERM paired delta.

## Statistical intervals

- Bootstrap **stratified by crystal system** and **paired by structural parent**.
- Resample within each class, preserving the natural composition
  `21 / 87 / 77 / 41 / 33 / 12 / 47`.
- Hexagonal intervals are expected to be wide; report them as-is.

## Label naming

Labels are **structure-derived crystal-system labels** (reconstructed from the
COD deposited atomic basis, stable across all `symprec` values). Do not call
them "pseudo-labels".

## Manual label-quality review (before inference)

- **12 hexagonal** parents: review all.
- **23 others** across the remaining six classes (monoclinic/orthorhombic/
  tetragonal/trigonal/cubic 4 each, triclinic 3).
- Record whether each experimental spectrum matches the deposited structure,
  plus any extra peaks, multi-phase signs, and label confidence.
- This is a label-quality audit, not a go/no-go gate.

## Frozen constraints

- The real domain must **not** be used to re-select checkpoints, seeds, or
  `lambda_js`.
- The manifest and the manual-review record are **frozen before prediction**.
- The frozen simulated results are **not** modified.

## Reporting

- Present RRUFF-301 and CNRS-318 as **two independent experimental domains** in
  a per-domain table (ERM, JS, paired delta, role).
- Do **not** claim the two domains are equal in size or statistical strength.
- Mark hexagonal-specific conclusions as **underpowered**.

## Readiness checklist

- [ ] v2 manifest tracked and frozen (SHA-256 recorded in the dataset audit).
- [ ] 35-spectrum manual label-quality review completed.
- [ ] One-time frozen inference on all 318 parents (ERM and JS, same parents).
- [ ] Stratified paired-bootstrap intervals computed.

## Related records

- Dataset audit: [`CNRS_318_DATASET_AUDIT.md`](CNRS_318_DATASET_AUDIT.md)
- Parent manifest: [`../manifests/cnrs_318_parent_manifest_v2.csv`](../manifests/cnrs_318_parent_manifest_v2.csv)
