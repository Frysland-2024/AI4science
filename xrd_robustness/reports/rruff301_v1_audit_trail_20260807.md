# RRUFF-301 v1 Audit Trail (INVALIDATED — Split Bug)

**Status:** INVALIDATED. Replaced by v2 (fixed split).
**Date of v1 run:** 2026-08-07, ~00:30
**Date of invalidation:** 2026-08-07, ~00:40
**Reason:** Implementation error in crystal system labeling. RRUFF CELL PARAMETERS
labels all trigonal samples as "hexagonal" (crystallographic convention in RRUFF).
The v1 split used CELL PARAMETERS directly, resulting in:
- hexagonal: 86 samples (43 hexagonal + 43 mislabeled trigonal)
- trigonal: 0 samples
- Test set: 241 samples (not 231 as specified in preregistered protocol)
- Adaptation pool: 60 samples (not 70)

**v2 fix:** DIF space_group + pymatgen.SpaceGroup correctly separates trigonal/hexagonal.
v2 split: 70 adaptation + 231 test, 33/class × 7, zero overlap.

---

## V1 Results (for audit record only — NOT for paper)

**Protocol:** Same as v2 except buggy split.
Same checkpoints, same LR, same early-stop, same episode seeds.

### V1 Primary: ΔMacro-F1 (on buggy 241-sample test, 6-class adaptation)

| K | ERM F1 | JS F1 | Δ | Positive/25 |
|---|---:|---:|---:|---:|
| 1 | 0.228 | 0.291 | +0.063 | 23/25 |
| 2 | 0.271 | 0.352 | +0.081 | 23/25 |
| 5 | 0.309 | 0.387 | +0.078 | 24/25 |

### V1 Per-Class F1 (note: trigonal had 0 support, 0 test samples)

| Class | K=1 Δ | K=2 Δ | K=5 Δ |
|---|---|---|---|
| triclinic | +0.076 | +0.089 | +0.121 |
| monoclinic | +0.037 | +0.050 | +0.048 |
| orthorhombic | +0.077 | +0.122 | +0.095 |
| tetragonal | +0.003 | -0.008 | +0.018 |
| trigonal | **0.000** | **0.000** | **0.000** ← no samples |
| hexagonal | +0.089 | +0.080 | +0.067 |
| cubic | +0.084 | +0.077 | +0.011 |

### V1 Zero-Shot

| Method | Macro-F1 |
|---|---|
| ERM | 0.155 |
| JS | 0.164 |

### V1 Fixed-200 Check

| K | Early-Stop Δ | Fixed-200 Δ |
|---|---|---|
| 1 | +0.063 | +0.068 |
| 5 | +0.078 | +0.077 |

### V1 Per-Sample

| K | JS better | ERM better | Tied | Total |
|---|---|----|----|---|
| 1 | 138 | 66 | 37 | **241** |
| 2 | 123 | 70 | 48 | **241** |
| 5 | 119 | 56 | 66 | **241** |

### V1 Monoclinic (preregistered test — NOT replicated)

| K | ERM F1 | JS F1 | Δ |
|---|---|---|---|
| 1 | 0.224 | 0.261 | +0.037 |
| 2 | 0.240 | 0.290 | +0.050 |
| 5 | 0.233 | 0.281 | +0.048 |

RRUFF-70 monoclinic Δ=−0.088 was NOT replicated on v1 either.

---

## How the Bug Was Found

1. Per-sample counts summed to 241 (not 231 as specified)
2. Predictions file had 36,150 entries → 36,150/150 = 241 per run (not 231)
3. Zero-shot accuracy denominators matched 241 (e.g., 65/241 = 0.2697)
4. Trigonal had F1=0 across all K (no support, no test)
5. Adaptation pool total = 301 − 241 = 60 (not 70)

## Root Cause

```
RRUFF CELL PARAMETERS: "crystal system: hexagonal" for BOTH trigonal and hexagonal
                                      ↓
        v1 regex matched "hexagonal" for all
                                      ↓
        43 trigonal → mislabeled as hexagonal
        0 trigonal in adaptation pool
        0 trigonal in test set
        86 hexagonal total (43 real + 43 mislabeled)
```

## Fix (v2)

DIF files contain correct `SPACE GROUP` symbols. Using `pymatgen.SpaceGroup(sg).crystal_system`
correctly distinguishes trigonal (space groups: R3, R-3, R32, R3m, R3c, R-3m, R-3c, P3, P31, P32, 
P-3, P312, P321, P3112, P3121, P3212, P3221, P3m1, P31m, P3c1, P31c, P-31m, P-31c, P-3m1, P-3c1)
from hexagonal (space groups: P6, P61, P65, P62, P64, P63, P-6, P6/m, P63/m, P622, ...).

## Comparison: v1 vs v2 ΔMacro-F1

| K | v1 Δ (bug) | v2 Δ (fixed) | Difference |
|---|---|---|---|
| 1 | +0.063 | +0.043 | −0.020 |
| 2 | +0.081 | +0.046 | −0.035 |
| 5 | +0.078 | +0.055 | −0.023 |

V1 inflated the JS advantage because trigonal (a hard class) was not evaluated.
V2 is the correct, 7-class balanced result. JS > ERM holds in both versions.

---

## Paper Statement

For the paper's Methods section:

> An initial confirmatory run (v1) was invalidated after an internal sample-count
> audit revealed that RRUFF CELL PARAMETERS labels trigonal as "hexagonal",
> causing trigonal samples to be excluded from both the adaptation pool and
> test set. The experiment was repeated (v2) under the original preregistered
> 7-class balanced protocol using DIF space groups for trigonal/hexagonal
> disambiguation. No model, optimizer, hyperparameter, or analysis decisions 
> were changed between v1 and v2. All reported results are from v2.
