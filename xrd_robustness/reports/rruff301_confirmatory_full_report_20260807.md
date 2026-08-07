# RRUFF-301 Confirmatory Few-Shot Adaptation — Complete Evidence Report

**Protocol:** Preregistered, single-run, no incremental inspection
**Date:** 2026-08-07
**Version:** v2 (fixed split — see §0)
**v1→v2 fix:** RRUFF CELL PARAMETERS labels trigonal as "hexagonal". v1 had hexagonal=86, trigonal=0. v2 uses DIF space_group + pymatgen.SpaceGroup to correctly separate 43 trigonal from 43 hexagonal. Split CSV verified: 70 adaptation + 231 test, 33/class, zero overlap.
**Dataset:** 301 RRUFF mineral XRD spectra (43/class × 7 crystal systems)
**Split:** 10/class adaptation pool (70 total) + 33/class locked test set (231 total)
**Primary metric:** ΔMacro-F1 (JS − ERM)
**Methods:** Dynamic ERM vs JS Consistency (λ=60), 5 pretraining seeds × 5 episode seeds
**Adaptation:** Frozen convolutional backbone, projection (7168→256) + head (256→7) trainable, AdamW lr=1e-4, early-stop on support loss (patience=20, max 200 epochs)
**Fixed-step check:** K=1,5 at 200 steps, no early stopping

## 1. Zero-Shot Transfer (231-sample Locked Test Set)

| Method | Seed | Accuracy | Macro-F1 |
|---|---|---|---|
| dynamic_erm | 20260711 | 0.1948 | 0.1629 |
| js_lambda_60 | 20260711 | 0.3074 | 0.2822 |
| dynamic_erm | 20260712 | 0.2165 | 0.1730 |
| js_lambda_60 | 20260712 | 0.2294 | 0.1928 |
| dynamic_erm | 20260713 | 0.2597 | 0.2346 |
| js_lambda_60 | 20260713 | 0.2078 | 0.1845 |
| dynamic_erm | 20260714 | 0.2208 | 0.1901 |
| js_lambda_60 | 20260714 | 0.2684 | 0.2248 |
| dynamic_erm | 20260715 | 0.2987 | 0.2826 |
| js_lambda_60 | 20260715 | 0.2511 | 0.2189 |

**dynamic_erm mean:** accuracy=0.2381±0.0368, macro-F1=0.2086±0.0444

**js_lambda_60 mean:** accuracy=0.2528±0.0340, macro-F1=0.2207±0.0343

### Zero-shot Per-Class F1

| Class | ERM F1 | JS F1 | Δ |
|---|---|---|---|
| triclinic | 0.3103 | 0.3435 | +0.0333 |
| monoclinic | 0.2356 | 0.2249 | -0.0107 |
| orthorhombic | 0.1163 | 0.2573 | +0.1410 |
| tetragonal | 0.1841 | 0.1111 | -0.0730 |
| trigonal | 0.2057 | 0.2051 | -0.0006 |
| hexagonal | 0.3769 | 0.4027 | +0.0258 |
| cubic | 0.0316 | 0.0000 | -0.0316 |

## 2. Few-Shot Adaptation — Main Results (Primary: Macro-F1)

### 2.1. Macro-F1

| K | ERM Macro-F1 | JS Macro-F1 | Mean Paired Δ | Median Δ | Positive/25 |
|---|---|---|---|---|---|
| **1** | 0.2847±0.026 | 0.3280±0.032 | **+0.0433** | +0.0387 | **21/25** |
| **2** | 0.3026±0.040 | 0.3486±0.033 | **+0.0460** | +0.0462 | **23/25** |
| **5** | 0.3555±0.030 | 0.4099±0.027 | **+0.0545** | +0.0551 | **24/25** |

### 2.2. Accuracy

| K | ERM Accuracy | JS Accuracy | Mean Paired Δ | Median Δ | Positive/25 |
|---|---|---|---|---|---|
| **1** | 0.2990±0.025 | 0.3375±0.029 | **+0.0384** | +0.0346 | **20/25** |
| **2** | 0.3120±0.037 | 0.3609±0.034 | **+0.0488** | +0.0519 | **23/25** |
| **5** | 0.3581±0.027 | 0.4149±0.025 | **+0.0568** | +0.0563 | **23/25** |

## 3. Paired Delta Matrices (JS − ERM Macro-F1)

### K = 1

| seed \ episode | ep=42 | ep=123 | ep=456 | ep=789 | ep=1024 | mean | pos? |
|---|---|---|---|---|---|---|---|
| seed=20260711 | +0.0704 | +0.0770 | +0.0354 | +0.0423 | +0.1100 | +0.0670 | 5/5 |
| seed=20260712 | +0.0731 | +0.0118 | +0.0546 | +0.0242 | +0.0454 | +0.0418 | 5/5 |
| seed=20260713 | +0.0204 | +0.0184 | -0.0072 | +0.0190 | +0.0011 | +0.0103 | 4/5 |
| seed=20260714 | +0.0116 | +0.0650 | -0.0427 | -0.0157 | -0.0009 | +0.0035 | 2/5 |
| seed=20260715 | +0.0387 | +0.1079 | +0.0908 | +0.1444 | +0.0880 | +0.0940 | 5/5 |

### K = 2

| seed \ episode | ep=42 | ep=123 | ep=456 | ep=789 | ep=1024 | mean | pos? |
|---|---|---|---|---|---|---|---|
| seed=20260711 | +0.0532 | +0.0445 | +0.0556 | +0.0857 | +0.0977 | +0.0673 | 5/5 |
| seed=20260712 | +0.0255 | +0.0458 | +0.0812 | +0.0149 | +0.0211 | +0.0377 | 5/5 |
| seed=20260713 | +0.0060 | +0.0060 | -0.0021 | +0.0066 | -0.0119 | +0.0009 | 3/5 |
| seed=20260714 | +0.0128 | +0.0227 | +0.0617 | +0.0639 | +0.0462 | +0.0415 | 5/5 |
| seed=20260715 | +0.0700 | +0.0985 | +0.0646 | +0.1217 | +0.0589 | +0.0827 | 5/5 |

### K = 5

| seed \ episode | ep=42 | ep=123 | ep=456 | ep=789 | ep=1024 | mean | pos? |
|---|---|---|---|---|---|---|---|
| seed=20260711 | +0.0414 | +0.0872 | +0.0753 | +0.0976 | +0.0742 | +0.0751 | 5/5 |
| seed=20260712 | +0.0699 | +0.0502 | +0.0482 | +0.0250 | +0.0508 | +0.0488 | 5/5 |
| seed=20260713 | +0.0233 | +0.0061 | +0.0014 | +0.0361 | -0.0099 | +0.0114 | 4/5 |
| seed=20260714 | +0.0147 | +0.0551 | +0.0518 | +0.0664 | +0.0936 | +0.0563 | 5/5 |
| seed=20260715 | +0.0638 | +0.0885 | +0.0652 | +0.0972 | +0.0885 | +0.0806 | 5/5 |

## 4. Per-Class Macro-F1 Breakdown

### K = 1

| Class | ERM F1 | JS F1 | Δ | Direction |
|---|---|---|---|---|
| ✅ triclinic | 0.3372 | 0.4068 | +0.0697 | +20/-5 |
| → monoclinic | 0.2374 | 0.2735 | +0.0360 | +15/-9 |
| → orthorhombic | 0.2013 | 0.2617 | +0.0604 | +17/-7 |
| → tetragonal | 0.2789 | 0.2923 | +0.0133 | +13/-12 |
| ⚠️ trigonal | 0.2655 | 0.2425 | -0.0230 | +11/-14 |
| ✅ hexagonal | 0.4738 | 0.5431 | +0.0693 | +18/-7 |
| ✅ cubic | 0.1989 | 0.2764 | +0.0775 | +20/-5 |

### K = 2

| Class | ERM F1 | JS F1 | Δ | Direction |
|---|---|---|---|---|
| ✅ triclinic | 0.3464 | 0.4310 | +0.0846 | +21/-4 |
| → monoclinic | 0.2335 | 0.3016 | +0.0681 | +17/-8 |
| ✅ orthorhombic | 0.2178 | 0.3232 | +0.1054 | +21/-4 |
| → tetragonal | 0.2915 | 0.3158 | +0.0243 | +13/-12 |
| ⚠️ trigonal | 0.2704 | 0.2360 | -0.0344 | +11/-14 |
| ✅ hexagonal | 0.4663 | 0.5572 | +0.0909 | +23/-2 |
| ⚠️ cubic | 0.2924 | 0.2758 | -0.0167 | +10/-15 |

### K = 5

| Class | ERM F1 | JS F1 | Δ | Direction |
|---|---|---|---|---|
| ✅ triclinic | 0.3722 | 0.4716 | +0.0994 | +23/-2 |
| → monoclinic | 0.2294 | 0.2985 | +0.0691 | +17/-7 |
| ✅ orthorhombic | 0.2670 | 0.3568 | +0.0898 | +20/-5 |
| ✅ tetragonal | 0.3817 | 0.4201 | +0.0383 | +19/-6 |
| ✅ trigonal | 0.3461 | 0.3740 | +0.0279 | +19/-6 |
| ✅ hexagonal | 0.5127 | 0.5845 | +0.0718 | +24/-1 |
| ⚠️ cubic | 0.3790 | 0.3640 | -0.0150 | +10/-15 |

## 5. Fixed-Step Sensitivity Check (200 optimizer steps, no early stopping)

| K | Method | Mean Macro-F1 | Mean Accuracy |
|---|---|---|---|
| 1 | ERM | 0.2856±0.025 | 0.2996±0.025 |
| 1 | JS | 0.3307±0.030 | 0.3392±0.028 |
| **1** | **Δ (JS-ERM) F1** | | **+0.0451** ± 0.043 |

| 5 | ERM | 0.3553±0.030 | 0.3579±0.027 |
| 5 | JS | 0.4101±0.027 | 0.4151±0.025 |
| **5** | **Δ (JS-ERM) F1** | | **+0.0548** ± 0.031 |

### Comparison: Early-Stop vs Fixed-200

| K | Early-Stop ΔF1 | Fixed-200 ΔF1 | Δ Difference |
|---|---|---|---|
| 1 | +0.0433 | +0.0451 | +0.0018 |
| 5 | +0.0545 | +0.0548 | +0.0004 |

## 6. Monoclinic Negative Transfer — Confirmatory Test

**RRUFF-70 pilot finding:** monoclinic F1 dropped −0.088 (K=5) under JS
**RRUFF-301 preregistered hypothesis:** Will monoclinic negative transfer replicate?

| K | ERM Monoclinic F1 | JS Monoclinic F1 | Δ | Positive runs |
|---|---|---|---|---|
| 1 | 0.2374 | 0.2735 | +0.0360 | 15/25 |
| 2 | 0.2335 | 0.3016 | +0.0681 | 17/25 |
| 5 | 0.2294 | 0.2985 | +0.0691 | 17/25 |

**Conclusion: Monoclinic negative transfer is NOT REPLICATED on RRUFF-301.** All K show positive Δ. The RRUFF-70 −0.088 was a small-sample artifact.

## 7. Cross-K Episodes: Per-Seed Aggregation

### 7.1. By Episode Seed (Macro-F1 Δ)

**K=1:**
  ✅ Episode Seed 42: mean Δ=+0.0428, all 5 positive
  ✅ Episode Seed 123: mean Δ=+0.0560, all 5 positive
  ⚠️ Episode Seed 456: mean Δ=+0.0262, all 5 mixed
  ⚠️ Episode Seed 789: mean Δ=+0.0428, all 5 mixed
  ⚠️ Episode Seed 1024: mean Δ=+0.0487, all 5 mixed

**K=2:**
  ✅ Episode Seed 42: mean Δ=+0.0335, all 5 positive
  ✅ Episode Seed 123: mean Δ=+0.0435, all 5 positive
  ⚠️ Episode Seed 456: mean Δ=+0.0522, all 5 mixed
  ✅ Episode Seed 789: mean Δ=+0.0585, all 5 positive
  ⚠️ Episode Seed 1024: mean Δ=+0.0424, all 5 mixed

**K=5:**
  ✅ Episode Seed 42: mean Δ=+0.0426, all 5 positive
  ✅ Episode Seed 123: mean Δ=+0.0574, all 5 positive
  ✅ Episode Seed 456: mean Δ=+0.0484, all 5 positive
  ✅ Episode Seed 789: mean Δ=+0.0645, all 5 positive
  ⚠️ Episode Seed 1024: mean Δ=+0.0594, all 5 mixed

### 7.2. By Pretraining Seed (Macro-F1 Δ)

**K=1:**
  ✅ Pretraining Seed 20260711: mean Δ=+0.0670, all 5 positive
  ✅ Pretraining Seed 20260712: mean Δ=+0.0418, all 5 positive
  ⚠️ Pretraining Seed 20260713: mean Δ=+0.0103, all 5 mixed
  ⚠️ Pretraining Seed 20260714: mean Δ=+0.0035, all 5 mixed
  ✅ Pretraining Seed 20260715: mean Δ=+0.0940, all 5 positive

**K=2:**
  ✅ Pretraining Seed 20260711: mean Δ=+0.0673, all 5 positive
  ✅ Pretraining Seed 20260712: mean Δ=+0.0377, all 5 positive
  ⚠️ Pretraining Seed 20260713: mean Δ=+0.0009, all 5 mixed
  ✅ Pretraining Seed 20260714: mean Δ=+0.0415, all 5 positive
  ✅ Pretraining Seed 20260715: mean Δ=+0.0827, all 5 positive

**K=5:**
  ✅ Pretraining Seed 20260711: mean Δ=+0.0752, all 5 positive
  ✅ Pretraining Seed 20260712: mean Δ=+0.0488, all 5 positive
  ⚠️ Pretraining Seed 20260713: mean Δ=+0.0114, all 5 mixed
  ✅ Pretraining Seed 20260714: mean Δ=+0.0563, all 5 positive
  ✅ Pretraining Seed 20260715: mean Δ=+0.0806, all 5 positive

## 8. Training Budget Analysis (Epochs Used)

| K | Mean Epochs | Min | Max | Early Stop Rate |
|---|---|---|---|---|
| 1 | 138.2 | 86 | 193 | 50/50 (100%) |
| 2 | 189.3 | 144 | 200 | 24/50 (48%) |
| 5 | 200.0 | 200 | 200 | 0/50 (0%) |

## 9. Per-Sample Prediction Summary

### K = 1
  Samples where JS correct rate > ERM: 112
  Samples where ERM correct rate > JS: 78
  Samples tied: 41

### K = 2
  Samples where JS correct rate > ERM: 110
  Samples where ERM correct rate > JS: 66
  Samples tied: 55

### K = 5
  Samples where JS correct rate > ERM: 103
  Samples where ERM correct rate > JS: 70
  Samples tied: 58

## 10. Complete Evidence Chain

| Layer | Domain | Result | JS > ERM? |
|---|---|---|---|
| Simulated Validation | 14,060 structures, OOD split | +0.047 OOD F1, 5/5 seeds | ✅ |
| Simulated Test | 2,109 held-out structures | +0.055 OOD F1, 5/5 seeds | ✅ |
| RRUFF Pipeline Test (zero-shot) | 35 independent mineral spectra | JS 0.234 vs ERM 0.189 accuracy | ✅ |
| RRUFF-70 Exploratory | 70 spectra, K=1,2,5 few-shot | ΔF1 +0.043 to +0.071, 60/75 positive | ✅ |
| **RRUFF-301 Confirmatory v2** | **301 spectra, 7-class balanced split, K=1,2,5 few-shot** | **ΔF1 +0.043 to +0.055, 68/75 positive** | **✅** |
| Fixed-step sensitivity | K=1,5, 200 steps | Δ direction preserved | ✅ |
| Monoclinic confirmatory | 301 spectra | Negative transfer NOT replicated | ✅ |

## 11. Data File Inventory

| File | Contents |
|---|---|
| `rruff301_zero_shot.json` | 10 zero-shot runs (5 seeds × 2 methods), per-class F1 |
| `rruff301_fewshot_runs.json` | 150 few-shot runs, per-class F1, epochs used |
| `rruff301_fixed200.json` | 100 fixed-step runs (K=1,5), per-class F1 |
| `rruff301_predictions.json` | 34,650 per-sample predictions (150 runs × 231 test samples) |
| `rruff301_confirmatory_fewshot.preregistered.json` | Frozen preregistration contract |
| `rruff301_adaptation_test_split.csv` | Split manifest (adaptation pool × test) |
