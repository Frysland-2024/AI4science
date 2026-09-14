# CNRS-318 structure-linked sim→real representation analysis — pre-run protocol

**Date:** 2026-09-15  
**Status:** analysis code prepared; local execution not yet run  
**Role:** secondary mechanism diagnostic for the frozen Dynamic ERM vs JS Consistency study

## Scientific question

The main study trains the same ResNet-18-GN backbone with the same online PXRD views, comparing ordinary Dynamic ERM against same-parent JS Consistency. The present analysis asks a narrower mechanistic question:

> For one deposited CNRS structure, does the frozen JS model change less than the matched ERM model when the input moves from a frozen simulated observation to the linked experimental CNRS pattern?

This is intended to test whether the same-parent consistency advantage observed in simulated OOD evaluation extends to the simulation→experiment transition at the representation and prediction levels.

## Frozen assets

No new training, tuning, adaptation, calibration fitting, checkpoint selection, seed selection, or CNRS sample selection is allowed.

The analysis uses:

- the existing **318 CNRS structural parents** in `manifests/cnrs318_eval_manifest.csv`;
- the already frozen experimental inputs in `outputs/cnrs318_zero_shot/cnrs318_inputs.npz`;
- the deposited atomic structures in the opXRD/CNRS source records;
- the existing frozen `level0` PXRD simulator profile;
- the five matched Dynamic-ERM and five matched JS checkpoints already frozen in `configs/real.cnrs318.zero_shot.frozen.json`.

All 318 parents are included. The analysis must fail rather than silently drop a parent whose source structure or checkpoint is unavailable.

## Pair construction

For each CNRS parent `s_i`:

1. use the deposited lattice + atomic basis to reconstruct the structure;
2. generate one `level0` simulated Cu Kα PXRD pattern on the same `10–80°`, `0.02°` grid used by the model;
3. pair that simulation with the already frozen experimental CNRS input for the same structure-linked record.

The simulator profile is not fitted to CNRS. It is the existing software-reference `level0` profile.

## Pre-specified diagnostics

For every `(training seed, method, parent)` pair, record:

1. **Embedding cosine distance** between simulated and experimental 256-D `pooled_embedding` outputs;
2. **Prediction JS divergence** between the simulated and experimental seven-class probability vectors;
3. **Prediction flip**: whether the predicted class changes from simulation to experiment;
4. **True-class probability drop** from simulation to experiment;
5. **True-class margin drop** from simulation to experiment.

For these sim→real gap quantities, smaller values are the hypothesized favorable direction. The comparison is always matched as `JS − ERM` within the same training seed.

## Interpretation rule

A representation-stability interpretation is supported only if JS shows systematically smaller sim→real changes than ERM on the pre-specified diagnostics. The analysis is not allowed to redefine the primary metric after observing the result.

A null or mixed result is retained as such. The analysis does not become a new training branch and cannot be used to re-select `lambda_js`, training seeds, checkpoints, CNRS parents, or preprocessing.

## Scope limitation

The deposited CNRS structures were used to derive stable crystal-system labels, but they were **not independently verified by manual spectrum-level phase analysis for every experimental pattern**. Therefore the analysis must use the wording:

> **structure-linked simulated–experimental pairs**

and must not describe the pairs as controlled repeated measurements of an independently verified identical physical specimen.

CNRS also remains a difficult, naturally imbalanced experimental domain. This diagnostic does not claim that broad zero-shot Sim-to-Real classification is solved.

## Execution

Tracked entry point:

```bash
cd xrd_robustness
python scripts/analyze_cnrs_sim_real_pairs.py
```

Expected local outputs under `outputs/cnrs_sim_real_analysis/`:

- `cnrs318_level0_simulated_inputs.npz`
- `simulation_provenance.csv`
- `paired_metrics.csv`
- `seed_method_summary.csv`
- `seed_paired_deltas.csv`
- `summary.json`

The large/raw output directory remains local and should not be used to move external CNRS source data into the public repository.
