# 05 — Data, Provenance, and Real-XRD Validation

## Simulated data role

SimXRD-style data provides controlled base structures and a tractable environment for paired perturbation experiments. It is the **mechanistic benchmark layer**, not proof that the model will work on laboratory XRD.

Before implementation, verify in the actual repository/data:

- dataset download/source and license;
- exact input grid and intensity normalization;
- label taxonomy and class mapping;
- source structure IDs;
- whether multiple simulated patterns derive from one structure;
- existing train/validation/test split definition;
- any preprocessing already baked into the data.

## Leakage rule

The split key must identify the **underlying crystal structure/material record**. A raw pattern and every version generated from it—including clean, perturbed, normalized, cropped, or resampled variants—must remain in exactly one split.

## Data provenance record

Create a record for every experiment:

```text
source_name
source_version
download_or_local_path
license_status
checksum_if_available
preprocessing_version
label_mapping_version
split_definition
split_seed
number_of_base_structures
number_of_patterns
notes
```

## Real-XRD validation: required logic

Real XRD validation is intended to test external relevance, not merely to provide a prettier figure.

### Minimum design

1. Identify a real XRD source with defensible labels or reference standards.
2. Preserve acquisition metadata where available: radiation, range, step size, geometry, preprocessing, instrument, sample identity.
3. State a preprocessing compatibility protocol between simulated and real patterns.
4. Keep external test examples out of method/hyperparameter selection where possible.
5. Report both successes and failure cases.
6. Avoid claims that real validation proves universal deployment readiness.

### Stronger validation options

- repeated scans of the same sample under controlled instrument conditions;
- a small externally sourced labeled benchmark;
- standards or well-characterized reference compounds;
- a sim-to-real calibration/preprocessing study explicitly separated from final evaluation;
- comparison of prediction stability across experimentally observed repeat scans.

## Sim-to-real statement discipline

Use language such as:

> Simulated perturbations provide controlled stress tests. Real XRD evaluation assesses whether the qualitative reliability pattern transfers under an external measurement domain.

Do not say the simulator has fully reproduced laboratory domain shift unless that has been quantitatively demonstrated.

## Copyright and usage guardrail

Do not redistribute data or patterns until dataset and source rights are checked. Store source metadata and cite the dataset/paper in all generated reports.
