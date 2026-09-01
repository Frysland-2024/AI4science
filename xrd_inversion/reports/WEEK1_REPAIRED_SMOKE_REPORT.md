# Week-1 PXRD inversion numerical-gate report

- Overall decision: **REPAIRED_SMOKE_PASS_FORMAL_GATE_PENDING**
- Scope: **repaired smoke only; not the formal Week-1 gate**.
- P2-R is the recoverability gate; P2-L is a nominal-start basin diagnostic.
- P1/P2 physics ran on CUDA float64 with TF32 and autocast disabled.
- Repository HEAD anchor: `8cecc0406d67b8016882c4ad663c951803f34265` (dirty=True; exact source hashes are in JSON).
- Config SHA-256: `5451daf22bfe6c0141c1fd5f92a506240abe7b2b969eb1a8c7ccf040995de20b`
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
| CUDA/CPU forward parity | PASS | max abs=1.19209e-07; RMSE=5.66093e-09 |
| P1 identifiability | PASS | eligible=4/4 (100.0%); numerical failures=0 |
| P2-R clean recoverability gate | PASS | PASS; success=6/6 (100.0%) |
| P2-L clean nominal capture | FAIL (diagnostic) | FAIL; success=3/6 (50.0%) |
| P2-L nuisance stress | FAIL (diagnostic) | FAIL; success=1/2 (50.0%) |

## P0 notes

- Non-conventional stored cells: mp-1104853, mp-1190125, mp-1213207, mp-15050, mp-27344.
- Quarantine by split: {'train': 4, 'validation': 0, 'test': 1}; these parents are excluded until structure fingerprints and reflection caches are regenerated together.
- Maximum metric-d error: 3.55271e-15 angstrom.
- Near-degenerate merged reflection families: 15.
- Maximum dynamic-deformation Bragg error: 4.26326e-14 deg.
- Zero-shift maximum error: 1.36999e-10 deg.
- FWHM maximum error: 2.60714e-10 deg.
- Independent renderer holdout: frozen_unopened; validly frozen unopened=True; outcomes opened=False.

## Per-staircase P2

- S1: P2-R PASS; success=2/2 (100.0%); P2-L clean FAIL; success=1/2 (50.0%); P2-L nuisance NOT_RUN.
- S2: P2-R PASS; success=2/2 (100.0%); P2-L clean FAIL; success=1/2 (50.0%); P2-L nuisance NOT_RUN.
- S3: P2-R PASS; success=2/2 (100.0%); P2-L clean FAIL; success=1/2 (50.0%); P2-L nuisance FAIL; success=1/2 (50.0%).

## Decision boundary

The numerical forward, Jacobian, and recoverability checks passed for this run's scope. This does not authorize formal ML: the full sample requirement, near-duplicate audit, and frozen unopened independent-renderer boundary must all be satisfied first.

Full per-parent parity, Jacobian, candidate-ranking, and recovery records are retained in the JSON artifact; the exact selected parent identities are retained in the configured CSV manifest.
