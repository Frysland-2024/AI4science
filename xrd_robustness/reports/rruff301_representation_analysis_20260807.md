# RRUFF-301 Representation Analysis — Fix/Break Patterns & Confidence Dynamics

**Data:** 34,650 per-sample predictions (150 runs × 231 test samples)
**Methods:** JS-ERM paired within each episode

## 1. Fix/Break Patterns: Which Samples Does JS Repair or Damage?

For each K, aggregate across all 25 (pretrained seed × episode) pairs.
Per sample, count how many times ERM gets it right but JS gets it wrong ("broken"),
and vice versa ("fixed"). Samples with net > 0 are JS-improved; net < 0 are JS-damaged.

### K = 1

| Metric | Value |
|---|---|
| Samples improved by JS (net > 0) | 112 |
| Samples damaged by JS (net < 0) | 78 |
| Samples neutral (net = 0) | 41 |
| Total JS-only-correct episodes | 934 |
| Total ERM-only-correct episodes | 712 |
| Fix/break ratio | 934/712 = 1.31 |

### K = 1 — Per-Class Fix/Break

| Class | Net Fixes | Fix Episodes | Break Episodes | Both Right | Both Wrong | Net Score |
|---|---|---|---|---|---|---|
| triclinic | -52 | 132 | 184 | 234 | 275 | -1.58/sample |
| monoclinic | +8 | 116 | 108 | 107 | 494 | +0.24/sample |
| orthorhombic | +69 | 147 | 78 | 94 | 506 | +2.09/sample |
| tetragonal | +20 | 119 | 99 | 101 | 506 | +0.61/sample |
| trigonal | -42 | 98 | 140 | 86 | 501 | -1.27/sample |
| hexagonal | +73 | 136 | 63 | 309 | 317 | +2.21/sample |
| cubic | +146 | 186 | 40 | 84 | 515 | +4.42/sample |

### K = 2

| Metric | Value |
|---|---|
| Samples improved by JS (net > 0) | 110 |
| Samples damaged by JS (net < 0) | 66 |
| Samples neutral (net = 0) | 55 |
| Total JS-only-correct episodes | 936 |
| Total ERM-only-correct episodes | 654 |
| Fix/break ratio | 936/654 = 1.43 |

### K = 2 — Per-Class Fix/Break

| Class | Net Fixes | Fix Episodes | Break Episodes | Both Right | Both Wrong | Net Score |
|---|---|---|---|---|---|---|
| triclinic | +28 | 176 | 148 | 266 | 235 | +0.85/sample |
| monoclinic | +67 | 152 | 85 | 114 | 474 | +2.03/sample |
| orthorhombic | +140 | 200 | 60 | 116 | 449 | +4.24/sample |
| tetragonal | +5 | 96 | 91 | 116 | 522 | +0.15/sample |
| trigonal | -53 | 84 | 137 | 81 | 523 | -1.61/sample |
| hexagonal | +109 | 138 | 29 | 355 | 303 | +3.30/sample |
| cubic | -14 | 90 | 104 | 100 | 531 | -0.42/sample |

### K = 5

| Metric | Value |
|---|---|
| Samples improved by JS (net > 0) | 103 |
| Samples damaged by JS (net < 0) | 70 |
| Samples neutral (net = 0) | 58 |
| Total JS-only-correct episodes | 902 |
| Total ERM-only-correct episodes | 574 |
| Fix/break ratio | 902/574 = 1.57 |

### K = 5 — Per-Class Fix/Break

| Class | Net Fixes | Fix Episodes | Break Episodes | Both Right | Both Wrong | Net Score |
|---|---|---|---|---|---|---|
| triclinic | +68 | 180 | 112 | 278 | 255 | +2.06/sample |
| monoclinic | +74 | 152 | 78 | 99 | 496 | +2.24/sample |
| orthorhombic | +116 | 177 | 61 | 166 | 421 | +3.52/sample |
| tetragonal | +30 | 90 | 60 | 202 | 473 | +0.91/sample |
| trigonal | -14 | 105 | 119 | 181 | 420 | -0.42/sample |
| hexagonal | +81 | 120 | 39 | 404 | 262 | +2.45/sample |
| cubic | -27 | 78 | 105 | 164 | 478 | -0.82/sample |

## 2. Top Fix/Break Samples (K=5, most dramatic JS effects)

### Top 10 JS-Improved Samples

| Sample | Class | Net | Fixes | Breaks |
|---|---|---|---|---|
| R090034 | orthorhombic | +24 | 24 | 0 |
| R070562 | triclinic | +22 | 22 | 0 |
| R050008 | orthorhombic | +19 | 19 | 0 |
| R050027 | hexagonal | +19 | 19 | 0 |
| R130079 | cubic | +19 | 19 | 0 |
| R050526 | monoclinic | +18 | 18 | 0 |
| R050648 | hexagonal | +15 | 15 | 0 |
| R050276 | cubic | +15 | 15 | 0 |
| R130034 | orthorhombic | +14 | 14 | 0 |
| R050015 | hexagonal | +14 | 14 | 0 |

### Top 10 JS-Damaged Samples

| Sample | Class | Net | Fixes | Breaks |
|---|---|---|---|---|
| R050657 | triclinic | -20 | 0 | 20 |
| R040027 | cubic | -18 | 0 | 18 |
| R050609 | cubic | -14 | 2 | 16 |
| R100216 | cubic | -14 | 1 | 15 |
| R060598 | triclinic | -13 | 0 | 13 |
| R060136 | trigonal | -10 | 2 | 12 |
| R050621 | triclinic | -9 | 0 | 9 |
| R070195 | monoclinic | -9 | 5 | 14 |
| R060082 | triclinic | -8 | 0 | 8 |
| R050222 | tetragonal | -8 | 0 | 8 |

## 3. Confusion Asymmetry: Where Does JS Systematically Differ from ERM?

### K = 1 — Confusion Delta (JS − ERM): More → JS favors this confusion, Less → ERM favors

| True \ Pred | tric | mono | orth | tetr | trig | hexa | cubi |
|---|---|---|---|---|---|---|---|
| triclinic    | **-52** | -16 | -40 | +6 | -3 | +5 | +100 |
| monoclinic   | -144 | **+8** | +74 | +11 | -7 | -20 | +78 |
| orthorhombic | -84 | -80 | **+69** | +52 | -53 | +19 | +77 |
| tetragonal   | -69 | -41 | +81 | **+20** | -88 | -18 | +115 |
| trigonal     | -121 | +34 | -26 | +41 | **-42** | +24 | +90 |
| hexagonal    | -123 | -9 | +20 | +26 | -57 | **+73** | +70 |
| cubic        | -61 | -18 | -24 | -30 | -22 | +9 | **+146** |

### K = 1 — Diagonal Gain (More Correct Predictions)

| Class | ERM Correct | JS Correct | Δ | JS Gain % |
|---|---|---|---|---|
| triclinic | 418 | 366 | -52 | -12.4% |
| monoclinic | 215 | 223 | +8 | +3.7% |
| orthorhombic | 172 | 241 | +69 | +40.1% |
| tetragonal | 200 | 220 | +20 | +10.0% |
| trigonal | 226 | 184 | -42 | -18.6% |
| hexagonal | 372 | 445 | +73 | +19.6% |
| cubic | 124 | 270 | +146 | +117.7% |

### K = 2 — Confusion Delta (JS − ERM): More → JS favors this confusion, Less → ERM favors

| True \ Pred | tric | mono | orth | tetr | trig | hexa | cubi |
|---|---|---|---|---|---|---|---|
| triclinic    | **+28** | +1 | -18 | -5 | -11 | +8 | -3 |
| monoclinic   | -71 | **+67** | +76 | -24 | -17 | -21 | -10 |
| orthorhombic | -38 | -59 | **+140** | +4 | -45 | +20 | -22 |
| tetragonal   | -20 | -3 | +115 | **+5** | -83 | -39 | +25 |
| trigonal     | -84 | +78 | -8 | +18 | **-53** | +29 | +20 |
| hexagonal    | -104 | +22 | +39 | -13 | -42 | **+109** | -11 |
| cubic        | -26 | +8 | +28 | -28 | -4 | +36 | **-14** |

### K = 2 — Diagonal Gain (More Correct Predictions)

| Class | ERM Correct | JS Correct | Δ | JS Gain % |
|---|---|---|---|---|
| triclinic | 414 | 442 | +28 | +6.8% |
| monoclinic | 199 | 266 | +67 | +33.7% |
| orthorhombic | 176 | 316 | +140 | +79.5% |
| tetragonal | 207 | 212 | +5 | +2.4% |
| trigonal | 218 | 165 | -53 | -24.3% |
| hexagonal | 384 | 493 | +109 | +28.4% |
| cubic | 204 | 190 | -14 | -6.9% |

### K = 5 — Confusion Delta (JS − ERM): More → JS favors this confusion, Less → ERM favors

| True \ Pred | tric | mono | orth | tetr | trig | hexa | cubi |
|---|---|---|---|---|---|---|---|
| triclinic    | **+68** | · | -41 | -4 | -19 | +9 | -13 |
| monoclinic   | -21 | **+74** | +47 | -19 | -28 | -33 | -20 |
| orthorhombic | -24 | -34 | **+116** | +11 | -27 | -12 | -30 |
| tetragonal   | -7 | +25 | +93 | **+30** | -104 | -42 | +5 |
| trigonal     | -66 | +67 | -42 | +17 | **-14** | +30 | +8 |
| hexagonal    | -83 | -1 | +27 | +8 | -29 | **+81** | -3 |
| cubic        | -24 | +8 | +29 | -16 | +7 | +23 | **-27** |

### K = 5 — Diagonal Gain (More Correct Predictions)

| Class | ERM Correct | JS Correct | Δ | JS Gain % |
|---|---|---|---|---|
| triclinic | 390 | 458 | +68 | +17.4% |
| monoclinic | 177 | 251 | +74 | +41.8% |
| orthorhombic | 227 | 343 | +116 | +51.1% |
| tetragonal | 262 | 292 | +30 | +11.5% |
| trigonal | 300 | 286 | -14 | -4.7% |
| hexagonal | 443 | 524 | +81 | +18.3% |
| cubic | 269 | 242 | -27 | -10.0% |

## 4. Confidence Proxy Analysis (Correctness Rate per Sample)

Since raw logit confidences aren't in predictions.json, we approximate
confidence as the correctness rate across runs. Higher rate = model is more
consistently confident about this sample.
### K = 1
- ERM mean correctness rate: 0.2990 ± 0.287
- JS mean correctness rate: 0.3375 ± 0.311
- ERM: 139 low-conf (<30%), 67 mid-conf (30-70%), 25 high-conf (>70%)
- JS:  132 low-conf (<30%), 55 mid-conf (30-70%), 44 high-conf (>70%)
- Samples flipped ERM-low→JS-high: 7
- Samples flipped ERM-high→JS-low: 1

### K = 2
- ERM mean correctness rate: 0.3120 ± 0.296
- JS mean correctness rate: 0.3609 ± 0.338
- ERM: 133 low-conf (<30%), 67 mid-conf (30-70%), 31 high-conf (>70%)
- JS:  123 low-conf (<30%), 61 mid-conf (30-70%), 47 high-conf (>70%)
- Samples flipped ERM-low→JS-high: 8
- Samples flipped ERM-high→JS-low: 3

### K = 5
- ERM mean correctness rate: 0.3581 ± 0.328
- JS mean correctness rate: 0.4149 ± 0.369
- ERM: 119 low-conf (<30%), 69 mid-conf (30-70%), 43 high-conf (>70%)
- JS:  107 low-conf (<30%), 53 mid-conf (30-70%), 71 high-conf (>70%)
- Samples flipped ERM-low→JS-high: 8
- Samples flipped ERM-high→JS-low: 2

## 5. Detailed Sample-Level Flip Table (K=5)

Samples with the largest net effect. Rows = per-sample aggregate over 25 pairs.

| Sample ID | Class | ERM Rate | JS Rate | Net | Both✓ | Neither✗ | JS Only | ERM Only |
|---|---|---|---|---|---|---|---|---|
| R090034 | orthorhombic | 0.04 | 1.00 | +24 | 1 | 0 | 24 | 0 |
| R070562 | triclinic | 0.08 | 0.96 | +22 | 2 | 1 | 22 | 0 |
| R050657 | triclinic | 0.84 | 0.04 | -20 | 1 | 4 | 0 | 20 |
| R050008 | orthorhombic | 0.24 | 1.00 | +19 | 6 | 0 | 19 | 0 |
| R050027 | hexagonal | 0.24 | 1.00 | +19 | 6 | 0 | 19 | 0 |
| R130079 | cubic | 0.16 | 0.92 | +19 | 4 | 2 | 19 | 0 |
| R050526 | monoclinic | 0.20 | 0.92 | +18 | 5 | 2 | 18 | 0 |
| R040027 | cubic | 0.80 | 0.08 | -18 | 2 | 5 | 0 | 18 |
| R050648 | hexagonal | 0.28 | 0.88 | +15 | 7 | 3 | 15 | 0 |
| R050276 | cubic | 0.12 | 0.72 | +15 | 3 | 7 | 15 | 0 |
| R130034 | orthorhombic | 0.00 | 0.56 | +14 | 0 | 11 | 14 | 0 |
| R050015 | hexagonal | 0.44 | 1.00 | +14 | 11 | 0 | 14 | 0 |
| R050609 | cubic | 0.68 | 0.12 | -14 | 1 | 6 | 2 | 16 |
| R100216 | cubic | 0.60 | 0.04 | -14 | 0 | 9 | 1 | 15 |
| R060598 | triclinic | 0.68 | 0.16 | -13 | 4 | 8 | 0 | 13 |
| R050417 | tetragonal | 0.44 | 0.96 | +13 | 11 | 1 | 13 | 0 |
| R050419 | hexagonal | 0.48 | 1.00 | +13 | 12 | 0 | 13 | 0 |
| R050054 | triclinic | 0.32 | 0.80 | +12 | 8 | 5 | 12 | 0 |
| R050354 | triclinic | 0.36 | 0.84 | +12 | 7 | 2 | 14 | 2 |
| R050293 | triclinic | 0.32 | 0.76 | +11 | 6 | 4 | 13 | 2 |
| R050393 | triclinic | 0.00 | 0.44 | +11 | 0 | 14 | 11 | 0 |
| R050398 | monoclinic | 0.08 | 0.52 | +11 | 1 | 11 | 12 | 1 |
| R040130 | orthorhombic | 0.56 | 1.00 | +11 | 14 | 0 | 11 | 0 |
| R050044 | monoclinic | 0.40 | 0.80 | +10 | 10 | 5 | 10 | 0 |
| R060917 | orthorhombic | 0.00 | 0.40 | +10 | 0 | 15 | 10 | 0 |
| R050149 | tetragonal | 0.04 | 0.44 | +10 | 0 | 13 | 11 | 1 |
| R060136 | trigonal | 0.64 | 0.24 | -10 | 4 | 7 | 2 | 12 |
| R040035 | trigonal | 0.52 | 0.92 | +10 | 13 | 2 | 10 | 0 |
| R050621 | triclinic | 0.36 | 0.00 | -9 | 0 | 16 | 0 | 9 |
| R040181 | monoclinic | 0.40 | 0.76 | +9 | 9 | 5 | 10 | 1 |

---
*Generated 2026-08-07 from rruff301_predictions.json (v2, 34,650 predictions)*