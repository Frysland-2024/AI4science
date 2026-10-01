# Data and Reproducibility

This repository keeps the **scientific contract and compact evidence** public without redistributing every external dataset, checkpoint, or large intermediate artifact.

## What is tracked

The public tree contains:

- source code;
- frozen experiment configurations;
- compact manifests and provenance records;
- result summaries;
- audit reports;
- tests that check implementation and evidence contracts;
- scripts used for data preparation, training, evaluation, and figure generation.

Authoritative headline results are summarized in:

- ../xrd_robustness/reports/RESULTS.md
- ../xrd_robustness/reports/validation_results.json
- ../xrd_robustness/reports/simulated_test_results.json
- ../xrd_robustness/reports/rruff301_fewshot_results.json
- ../xrd_robustness/reports/CNRS_318_RESULTS.md
- ../xrd_robustness/reports/CALIBRATION_ANALYSIS.md

## What is intentionally not tracked

The repository does not redistribute:

- the full Materials Project structure corpus used to build the local formal dataset;
- raw RRUFF spectra;
- raw CNRS/opXRD/COD source archives;
- trained checkpoints;
- generated spectrum caches;
- large prediction arrays and intermediate analysis tables;
- local laboratory data;
- virtual environments or machine-specific output directories.

Those assets are externally sourced, large, license-sensitive, or reproducible intermediates.

## Materials Project structures

The acquisition script is:

xrd_robustness/scripts/acquire_mp_structures.py

It reads a Materials Project API key from the environment.

~~~bash
export MP_API_KEY="..."
# or
export PMG_MAPI_KEY="..."
~~~

On Windows PowerShell:

~~~powershell
$env:MP_API_KEY="..."
~~~

Never commit API keys.

The final local structure dataset used by the experiments is ignored by Git. Frozen split/configuration logic and validation scripts remain public.

## Experimental domains

### RRUFF

RRUFF is used as an experimental PXRD domain for few-shot adaptation. Raw spectra are not redistributed here. Users should obtain source data from the original provider under its applicable terms and reproduce the local preparation/audit pipeline.

The public reports document the role and split boundaries of RRUFF-301, including the adaptation/test overlap audit.

### CNRS / opXRD / COD-derived evaluation

CNRS-318 is a zero-shot external-domain evaluation assembled through the documented audit/preparation pipeline. Raw source archives are not redistributed.

The public repository retains frozen configuration, manifest-building scripts, audit scripts and reports, run records/hashes where applicable, and aggregate evaluation results.

Labels are reconstructed from deposited crystal structures and were not manually verified spectrum by spectrum; this limitation is part of the public result contract.

## Installation and tests

For the main package:

~~~bash
cd xrd_robustness
python -m pip install -e ".[test]"
python -m pytest -q -m "not data_bound"
~~~

Tests marked data_bound require ignored local research assets and are not expected to run on a fresh clone.

The CI workflow runs the public non-data-bound suite on Python 3.11.

## Reproducing results

There are three distinct levels of reproducibility.

### 1. Code / contract verification

Available from a fresh clone. This checks imports, simulator and objective behavior, split/configuration interfaces, and evidence/result consistency tests.

### 2. Result re-analysis

Where compact result artifacts are tracked, analysis scripts can recompute aggregate metrics and audits without retraining.

Large intermediate outputs that can be regenerated are intentionally excluded from the public tree.

### 3. Full end-to-end rerun

A full training rerun additionally requires external structure/spectrum datasets, local formal-dataset construction, substantial compute, and the exact frozen configs and seeds.

The repository provides the code and frozen scientific contract, but does not claim that a fresh clone alone contains every byte required to reproduce all historical training runs.

## Large-artifact policy

Large arrays, predictions, checkpoints, generated spectra, and presentation/workspace artifacts belong in release assets, external storage, or local experiment directories rather than the Git working tree.

This keeps the public repository reviewable while preserving compact, inspectable evidence.
