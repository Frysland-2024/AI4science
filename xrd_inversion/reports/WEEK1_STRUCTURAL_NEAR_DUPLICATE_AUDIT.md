# Week-1 Structural Near-Duplicate Audit

**Audit status: `COMPLETE_ANONYMOUS_PROTOTYPE_OVERLAP_DETECTED`**

This is a read-only audit of the frozen tetragonal parent split. It did not move, remove, or relabel any parent.

## Scope

- Tetragonal parents inspected: 2009
- Cross-split proxy groups: 154
- Parents in those groups: 1538
- Exhaustive cross-split candidate pairs: 14443
- Same-reduced-composition candidate pairs: 0
- Candidate edges: `{'train-test': 5998, 'train-validation': 6952, 'validation-test': 1493}`

The proxy is `anonymized_formula + recomputed_space_group + nsites`. Every cross-split pair inside every cross-split proxy group was evaluated; this is not a sample.

## StructureMatcher results

- Anonymous high-recall matches: 13031 pairs, 150 groups, 1480 parents.
- Anonymous default-tolerance matches: 11629 pairs, 150 groups, 1463 parents.
- Same-species default-tolerance matches: 0 pairs, 0 groups, 0 parents.
- Pair-level errors: 0.

Anonymous matching permits a one-to-one species mapping and is therefore evidence of cross-split structural-prototype overlap, not proof that two records are the same chemical material. Same-species matches are the narrower near-duplicate signal.
In this ledger there are no same-reduced-composition cross-split candidate pairs, so the zero same-species count is descriptive rather than an independently powered negative result.

## Interpretation boundary

The audit is complete when every candidate pair has a valid result. Detected matches are recorded rather than silently repaired: any policy decision about prototype-aware resplitting is separate work and was not authorized by this audit.

## Reproducibility

- Config SHA-256: `5ba23a552a4ec6b3f3dee739a586343748c5ea764692f38a02a895b297280359`
- Records SHA-256: `05d5d33f200194612a8cdbe29d9443fc7bad9c245f66d185364b66a75915cc6c`
- Frozen split SHA-256: `b9d3b72e42ea0fd549dae34425ff61d2d650d5dd7fe6f337d747cb952cf43293`
- Pair ledger SHA-256: `e609c7efb2e577b2f81ce97c7c31f29be61219dc4276e4f21fc48efbe32347ec`
- Pymatgen: `2026.5.4`
- Wall time: 74.129 s
