# Week-1 PXRD inversion numerical-gate report

- Overall decision: **FORMAL_WEEK1_NUMERICAL_GATES_PASS_ADMIN_PENDING**
- Scope: **formal 24-parent x 4-trial numerical gate**.
- P2-R is the recoverability gate; P2-L is a nominal-start basin diagnostic.
- P1/P2 physics ran on CUDA float64 with TF32 and autocast disabled.
- Repository HEAD anchor: `dd4ea3022a03b6dcd9cdad1b7ad8c2b1c4296b5d` (dirty=True; exact source hashes are in JSON).
- Config SHA-256: `467551f20858492cdc98c10e989bd42ac44b36111aea7f7944b0fff346a78788`
- No neural-network training was run.

## Data audit

The authoritative tetragonal pool contains **2009** parents: train=1406, validation=301, test=302.

Exact duplicate fingerprints: 0. Stored non-conventional tetragonal cells: 5; restandardization failures: 0.

The structural audit is complete: 14443 proxy candidate pairs, 0 same-species matches in that proxy scope, and 11629 default-tolerance anonymous-prototype matches. Anonymous overlap is a pre-ML split-policy annotation, not a P0-P2 numerical failure.
The high-recall composition/space-group/nsites proxy flags 154 cross-split groups involving 1538 parents; this is a triage signal, not proof of structural duplication.

## Gate summary

| Gate | Status | Key result |
|---|---|---|
| P0 forward correctness | PASS_WITH_QUARANTINE | 147941 cached reflection families; max Bragg error=9.8943e-06 deg |
| CUDA/CPU forward parity | PASS | max abs=1.19209e-07; RMSE=5.91634e-09 |
| P1 identifiability | PASS | eligible=24/24 (100.0%); numerical failures=0 |
| P2-R clean recoverability gate | PASS | PASS; success=288/288 (100.0%) |
| P2-L clean nominal capture | FAIL (diagnostic) | FAIL; success=181/288 (62.8%) |
| P2-L nuisance stress | FAIL (diagnostic) | FAIL; success=37/96 (38.5%) |

## P0 notes

- Non-conventional stored cells: mp-1104853, mp-1190125, mp-1213207, mp-15050, mp-27344.
- Quarantine by split: {'train': 4, 'validation': 0, 'test': 1}; these parents are excluded until structure fingerprints and reflection caches are regenerated together.
- Maximum metric-d error: 3.55271e-15 angstrom.
- Near-degenerate merged reflection families: 15.
- Maximum dynamic-deformation Bragg error: 5.68434e-14 deg.
- Zero-shift maximum error: 3.16302e-10 deg.
- FWHM maximum error: 3.55283e-10 deg.
- Independent renderer holdout: frozen_unopened; validly frozen unopened=True; outcomes opened=False.

## Per-staircase P2

- S1: P2-R PASS; success=96/96 (100.0%); P2-L clean FAIL; success=56/96 (58.3%); P2-L nuisance NOT_RUN.
- S2: P2-R PASS; success=96/96 (100.0%); P2-L clean FAIL; success=55/96 (57.3%); P2-L nuisance NOT_RUN.
- S3: P2-R PASS; success=96/96 (100.0%); P2-L clean FAIL; success=70/96 (72.9%); P2-L nuisance FAIL; success=37/96 (38.5%).

## Decision boundary

The exact 24-parent x 4-trial numerical scope passed P0, CUDA parity, P1, and every P2-R staircase. Formal ML remains unauthorized because the current split has broad anonymous-prototype overlap; a prototype-aware or explicitly accepted split policy must be frozen first. The independent renderer remains correctly frozen and unopened.

Full per-parent parity, Jacobian, candidate-ranking, and recovery records are retained in the JSON artifact; the exact selected parent identities are retained in the configured CSV manifest.
