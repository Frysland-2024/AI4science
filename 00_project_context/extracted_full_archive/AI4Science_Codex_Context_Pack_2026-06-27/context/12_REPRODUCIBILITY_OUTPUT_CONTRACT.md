# 12 — Reproducibility and Output Contract

## Recommended repository layout

```text
src/
  data/
  transforms/
  models/
  training/
  metrics/
  reporting/
configs/
  data/
  experiments/
  transforms/
scripts/
tests/
data/                 # ignored if source data is restricted
artifacts/
  runs/<run_id>/
reports/
docs/                 # this context pack may live here or at repository root
```

## Mandatory run artifacts

Each completed run should create:

```text
run_manifest.json
resolved_config.yaml
data_split_manifest.json or reference
metrics.json
per_sample_predictions.parquet/csv
checkpoint path + checksum if practical
stdout/stderr logs
environment.txt or lockfile reference
figures/
```

## Recommended run ID pattern

```text
YYYYMMDD_HHMM_<experiment_id>_<seed>_<short_config_hash>
```

Example:

```text
20260627_1430_E2_shift-broadening_s42_a1b2c3
```

## Required configuration fields

```yaml
seed:
data:
  source_version:
  label_mapping_version:
  split_id:
  preprocessing_version:
model:
training:
transform:
  family:
  parameterization:
  severity_tier:
  evidence_ledger_id:
loss:
  supervised_weight:
  consistency_weight:
  distance:
evaluation:
  metrics:
  number_of_perturbation_draws:
```

## Reporting discipline

- Generate figures from saved result files.
- Include caption text that identifies data split, severity, transform version, and seed aggregation.
- Keep a table of excluded samples and preprocessing failures.
- Do not rename/replace prior results after tuning; create a new run.
