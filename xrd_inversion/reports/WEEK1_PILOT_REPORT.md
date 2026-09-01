# Week-1 PXRD inversion pilot report

- Overall decision: **HOLD_REPAIR_BEFORE_FORMAL_GATE**
- Scope: **smoke pilot only; not the formal Week-1 gate**.
- Repository HEAD anchor: `6669ebd6b36b9c75ba212758e527faf5433d9869` (dirty=True; exact source hashes are in JSON).
- Config SHA-256: `e7b32f4536865e37691a8c1bd2ed5aa39c16210aeb9eca799f87147522cd98f5`
- No neural-network training was run.

## Data audit

The authoritative tetragonal pool contains **2009** parents: train=1406, validation=301, test=302.

Exact duplicate fingerprints: 0. Stored non-conventional tetragonal cells: 5; restandardization failures: 0.

The current source has no prototype labels, so the Week-1 prototype audit is limited to space-group and robust lattice/size/peak-count coverage. The prototype / near-duplicate gate therefore remains pending.
The high-recall composition/space-group/nsites proxy flags 154 cross-split groups involving 1538 parents; this is a triage signal, not proof of structural duplication.

## Gate summary

| Gate | Status | Key result |
|---|---|---|
| P0 forward correctness | PASS_WITH_QUARANTINE | 147941 cached reflection families; max Bragg error=9.8943e-06 deg |
| P1 identifiability | FAIL | eligible=3/4 (75.0%) |
| P2 clean classical recovery | FAIL | success=3/6 (50.0%) |
| S4 nuisance stress diagnostic | FAIL | success=3/6 (50.0%) |

## P0 notes

- Non-conventional stored cells: mp-1104853, mp-1190125, mp-1213207, mp-15050, mp-27344.
- Quarantine by split: {'train': 4, 'validation': 0, 'test': 1}; these parents are excluded until structure fingerprints and reflection caches are regenerated together.
- Maximum metric-d error: 3.55271e-15 angstrom.
- Near-degenerate merged reflection families: 15.
- Maximum dynamic-deformation Bragg error: 4.26326e-14 deg.
- Zero-shift maximum error: 1.36999e-10 deg.
- FWHM maximum error: 2.60714e-10 deg.

## Per-staircase P2

- S1: clean FAIL (1/2); nuisance stress FAIL (1/2).
- S2: clean FAIL (1/2); nuisance stress FAIL (1/2).
- S3: clean FAIL (1/2); nuisance stress FAIL (1/2).

## Decision boundary

At least one smoke-scale P0, P1, or clean P2 requirement failed. Do not start formal ML training. First repair the finite-difference stability check and diagnose single-start optimizer capture; shrink the parameter range only if those diagnostics show intrinsic ambiguity.

Full per-parent Jacobian and recovery records are retained in `week1_pilot_results.json`. Selected parent identities are frozen in `../manifests/week1_selected_parents.csv`.
