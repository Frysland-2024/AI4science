# CNRS-318 evaluation protocol (frozen)

**Date:** 2026-08-27

**Status:** spec frozen; **inference not yet run** (readiness = PENDING on the one-time
frozen inference; no manual spectrum-level label review is planned).

## Domain role

CNRS-318 = **naturally imbalanced independent experimental domain**, the formal second
experimental domain. Primary analysis is **zero-shot**: the frozen models are evaluated
without touching any CNRS label for adaptation. RRUFF-301 remains the balanced primary
few-shot domain; the two are reported separately and never merged into one score.

## Frozen identity and preprocessing

These are fixed in `configs/real.cnrs318.zero_shot.frozen.json` and must not change:

| Field | Value |
| --- | --- |
| dataset_id | `opxrd_v11_cnrs318` |
| class_order | triclinic, monoclinic, orthorhombic, tetragonal, trigonal, hexagonal, cubic |
| class_counts | 21 / 87 / 77 / 41 / 33 / 12 / 47 (total 318) |
| target_wavelength_angstrom | 1.5406 (Cu Kα) |
| two_theta range | 10.0–80.0°, step 0.02° → 3501 points |
| interpolation | linear |
| normalization | max |
| model_selection_on_cnrs | forbidden |

Wavelength mapping uses Bragg's law pointwise; source points with
`| (λ_target/λ_source) sin(θ_source) | > 1` are discarded, never clipped.

## Primary question

On the same 318 parents, does JS still beat ERM?

```
Δ_CNRS = Macro-F1(JS) − Macro-F1(ERM)
```

All statistics are paired per structural parent, and the primary analysis uses the five
independent training seeds (not a five-model ensemble).

## Metrics

- **Primary:** Macro-F1.
- **Auxiliary:** balanced accuracy, overall accuracy, per-class precision / recall / F1,
  confusion matrix, per-class support, ECE, worst-class F1, and the JS−ERM paired delta.

## Statistical intervals

- **Class-stratified paired parent bootstrap**: within each crystal system, resample
  parents with replacement, preserving the natural composition
  `21 / 87 / 77 / 41 / 33 / 12 / 47`, then compute the paired ERM→JS delta.
- Training seeds are fixed; they are not resampled as if they were an infinite sample.
- Hexagonal intervals are expected to be wide; report them as-is.

## Labels

Labels are **structure-derived crystal-system labels** (reconstructed from the COD
deposited atomic basis, accepted only when stable across all `symprec` values). They are
not "pseudo-labels".

> **Label-verification limitation (report with the results):** labels are derived from the
> deposited crystal structures through stable symmetry reconstruction and were **not**
> independently verified by manual spectrum-level phase analysis. This means we cannot
> claim that all 318 spectra were individually confirmed, nor that every experimental
> spectrum is an ideal single phase exactly matching its deposited structure. The
> Discussion must acknowledge the possibility of a small amount of metadata, extra-phase,
> or spectrum-structure mismatch.

## No manual review (and the one hard rule that replaces it)

The 35/42-spectrum manual label-quality review is **not planned** — the machine audit
(deposited-structure parsing, multi-`symprec` stability, exact-spectrum deduplication,
structural-parent clustering, `formal_14060` overlap exclusion) is the QC that the
research question actually needs, and it is already complete.

Because there is no pre-hoc manual review, the one non-negotiable rule is:

> **All 318 parents are used exactly as in the frozen manifest. Error analysis is allowed,
> but the evaluation set must not be edited after seeing model predictions** — no dropping
> "bad-looking" samples post-hoc, since that would turn into result-driven data cleaning.

## Frozen constraints

- The real domain must **not** be used to re-select checkpoints, seeds, or `lambda_js`.
- The eval manifest is frozen **before** prediction.
- The frozen simulated results are **not** modified.
- No downsampling to 84; no replication / oversampling of hexagonal.
- No CNRS-specific preprocessing beyond the fixed pipeline (no background subtraction,
  smoothing, peak detection, sqrt/log scaling, etc.).
- No post-hoc removal of samples after seeing predictions (result-driven cleaning).

## Frozen interpretation

| Result | Wording |
| --- | --- |
| Mean Δ > 0, 5/5 positive, CI > 0 | stable replication on CNRS |
| Mean Δ > 0, mixed direction or CI crosses 0 | directional support on CNRS |
| Mean Δ ≈ 0 | no clear difference |
| Mean Δ < 0 | not replicated on CNRS; possible negative transfer |

Even a negative result does not demote CNRS-318 back to exploratory.

## Reporting

- Report RRUFF-301 (few-shot) and CNRS-318 (zero-shot) in separate tables.
- Core figures:
  1. dataset-construction flow (`1052 → 886 → 476 → 323 → 318`);
  2. natural class distribution (mark hexagonal `n=12`);
  3. five-seed ERM→JS paired line plot;
  4. per-class F1 and ΔF1 with support counts (no strong hexagonal conclusion).

## Readiness checklist

- [ ] v2 manifest tracked and frozen (SHA in the dataset audit).
- [ ] `cnrs318_eval_manifest.csv` finalized (318 parents, no post-hoc exclusions).
- [ ] `cnrs318_inputs.npz` built (N × 3501, float32, max-normalized, no NaN/Inf).
- [ ] One-time frozen zero-shot inference: 10 checkpoints (5 ERM + 5 JS).
- [ ] Class-stratified paired parent bootstrap + report.

## Related records

- Dataset audit: [`CNRS_318_DATASET_AUDIT.md`](CNRS_318_DATASET_AUDIT.md)
- Frozen config: [`../configs/real.cnrs318.zero_shot.frozen.json`](../configs/real.cnrs318.zero_shot.frozen.json)
- Eval manifest: [`../manifests/cnrs318_eval_manifest.csv`](../manifests/cnrs318_eval_manifest.csv)
- Parent manifest: [`../manifests/cnrs_318_parent_manifest_v2.csv`](../manifests/cnrs_318_parent_manifest_v2.csv)
- Project history node: [`../../docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md`](../../docs/PROJECT_HISTORY_NOTE_2026-08-27_CNRS_RECLASSIFICATION.md)
