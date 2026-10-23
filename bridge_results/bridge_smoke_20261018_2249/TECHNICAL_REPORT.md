# Measurement-aware PXRD pilot preflight

Status: **BLOCKED_MISSING_IMPLEMENTATION**

No training was started. This checkout has no validated measurement-aware forward closure or reviewed A/B backend.
The old clean-reference loss prototypes are not used. No V9 result or frozen scientific artifact was changed.

## Gate status

- `structure_and_reference_provenance`: **BLOCKED_MISSING_EVIDENCE**
- `independent_full_spectrum_parity`: **BLOCKED_MISSING_EVIDENCE**
- `measurement_aware_expected_profile`: **BLOCKED_MISSING_EVIDENCE**
- `autograd_vs_finite_difference`: **BLOCKED_MISSING_EVIDENCE**
- `q_eta_identifiability`: **BLOCKED_MISSING_EVIDENCE**
- `non_oracle_nuisance_estimation`: **BLOCKED_MISSING_EVIDENCE**
- `split_and_leakage_audit`: **BLOCKED_MISSING_EVIDENCE**

## Required next steps

- Implement and execute independent BaTiO3/Pymatgen full-spectrum parity tests.
- Implement a differentiable measurement-aware expected profile and autograd/finite-difference tests.
- Measure local q–eta identifiability and a deployable non-oracle nuisance path.
- Produce runtime evidence for split and leakage checks from the approved source tree.
- Add and review a real A/B backend only after every required gate passes.

## Scope

The source-controlled config describes one exploratory, single-CIF BaTiO3 pilot. Even after future gates pass, it will not establish unseen-structure generalization or real-experiment refinement.
The approved scientific training budget is 7,200 seconds. The bridge itself has no wall-clock kill timeout; the budget is an experiment-policy limit for a future reviewed backend.
