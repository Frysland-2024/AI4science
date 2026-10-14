# Parent-Structure Sample Efficiency Supplementary Experiment

**Status:** COMPLETED; post-main supplementary analysis.

## Gate summary

| Gate | Status | Evidence |
|---|---|---|
| A — data, historical provenance, frozen protocol | PASS | Official split and peak-cache hashes verified; local GPU available; historical terminal steps unavailable and a new shared budget was frozen before scores. |
| B — implementation and fairness smoke | PASS | Deterministic stratified nested subsets, fixed-step paired runner, direct-versus-prefetch bitwise rendering check, tests, and matched-view smoke completed. |
| C — fixed matrix and uniform Test evaluation | PASS | 20/20 seed-by-budget pairs completed (40/40 method runs); incomplete cells are listed below. |
| D — paired statistics and plots | PASS | Per-seed, profile-level, per-class, and matched-seed metrics are summarized; parent-saving claims require paired uncertainty support. |
| E — archive | PASS | Independent Markdown, JSON/CSV, figures, frozen configs, and exact subset manifests are prepared for Git. |

## Frozen protocol

Four nested Train subsets contain 984, 2,460, 4,921, and 9,842 unique parent structures. Per-class counts use Hamilton largest-remainder rounding with the repository crystal-system order as the tie order. The selection seed is 20261013. Dynamic ERM and Dynamic JS (λ=60) share their initial weights and receive the same ordered batch and the same two rendered views at every optimizer step.

Each method receives 49,280 optimizer steps, batch size 16, 788,480 parent occurrences, and 1,576,960 generated views. The optimizer is AdamW (learning rate 1e-4, weight decay 1e-4) with no scheduler. Validation runs every 6,160 steps; the selected checkpoint maximizes mean Macro-F1 across six single-factor OOD Validation profiles at evaluation seed 20260721, with in-range Macro-F1 as the tie-break and the earlier step as the final tie-break.

This is a new fixed-budget supplementary protocol. Available historical checkpoints record selected best-checkpoint steps, not each original run's terminal step. The 49,280-step budget is the median selected-checkpoint step across the 10 historical checkpoints and does not claim to reproduce their stopping behavior.

## Data identity and split audit

Verified source records: 14060; verified peak tables: 14060. Train/Validation/Test counts are 9,842/2,109/2,109. The official split is the hash-bound `split_manifest.json` referenced by the frozen data config. The original structure records' embedded `split` field disagrees with that manifest for **6,601/14,060** records; it is stale and was not used for assignment. Material IDs, crystal systems, parent fingerprints, uniqueness, and all peak-table hashes were checked. Full split-field cross-tab: `test→test 318, test→train 1,469, test→validation 343; train→test 1,469, train→train 6,853, train→validation 1,478; validation→test 322, validation→train 1,520, validation→validation 288`.

The Test split and all original frozen configs, checkpoints, reports, and source split files remain unchanged. The frozen simulated Test was already used by the main study; these results are a post-main follow-up, not an untouched confirmatory test.

## Training matrix status

| Parents | Seed | ERM | JS λ=60 |
|---:|---:|---|---|
| 984 | 20260711 | completed | completed |
| 2,460 | 20260711 | completed | completed |
| 4,921 | 20260711 | completed | completed |
| 9,842 | 20260711 | completed | completed |
| 984 | 20260712 | completed | completed |
| 2,460 | 20260712 | completed | completed |
| 4,921 | 20260712 | completed | completed |
| 9,842 | 20260712 | completed | completed |
| 984 | 20260713 | completed | completed |
| 2,460 | 20260713 | completed | completed |
| 4,921 | 20260713 | completed | completed |
| 9,842 | 20260713 | completed | completed |
| 984 | 20260714 | completed | completed |
| 2,460 | 20260714 | completed | completed |
| 4,921 | 20260714 | completed | completed |
| 9,842 | 20260714 | completed | completed |
| 984 | 20260715 | completed | completed |
| 2,460 | 20260715 | completed | completed |
| 4,921 | 20260715 | completed | completed |
| 9,842 | 20260715 | completed | completed |

Actual method runs: **40/40**.

Before the scored matrix, a source-side preliminary launch was stopped before its first validation checkpoint when an evaluation batch-size audit found a mismatch with the recovered V9 protocol (128 versus 256). It produced no checkpoint or score; the frozen supplementary evaluation batch size was corrected to 256 before the formal matrix. On CUIFA, the transfer inventory check also rejected an unexpected Python `__pycache__` entry during preflight; the package was reverified before scientific training. Neither event is counted among the 40 method runs.

## Results

Primary outcome is the mean Macro-F1 across six single-factor simulated OOD profiles, averaged over the three frozen evaluation seeds. In-range, level0, accuracy, profile-level, and per-class metrics are reported as secondary outcomes.

| Parents | Training seeds | ERM OOD Macro-F1 | JS OOD Macro-F1 | Paired Δ (JS − ERM) | 95% paired CI | Positive pairs |
|---:|---:|---:|---:|---:|---:|---:|
| 984 | 5 | 0.4316 ± 0.0044 | 0.4876 ± 0.0039 | 0.0561 ± 0.0069 | [0.0509, 0.0615] | 5/5 |
| 2,460 | 5 | 0.5193 ± 0.0036 | 0.5710 ± 0.0080 | 0.0517 ± 0.0074 | [0.0458, 0.0573] | 5/5 |
| 4,921 | 5 | 0.5935 ± 0.0041 | 0.6361 ± 0.0059 | 0.0426 ± 0.0066 | [0.0370, 0.0476] | 5/5 |
| 9,842 | 5 | 0.6459 ± 0.0065 | 0.6999 ± 0.0050 | 0.0540 ± 0.0085 | [0.0477, 0.0603] | 5/5 |

Data-saving assessment: **no_supported_parent_saving**.
No parent reduction is supported. Same-budget gains, if any, remain distinct from measured structure savings. Mean-curve crossings without a positive paired 95% interval are exploratory only; no target was extrapolated.

## Per-seed primary and in-range results

| Parents | Seed | Method | OOD Macro-F1 | In-range Macro-F1 |
|---:|---:|---|---:|---:|
| 984 | 20260711 | dynamic_erm | 0.4365 | 0.4502 |
| 984 | 20260711 | dynamic_js | 0.4842 | 0.4923 |
| 984 | 20260712 | dynamic_erm | 0.4341 | 0.4441 |
| 984 | 20260712 | dynamic_js | 0.4897 | 0.4986 |
| 984 | 20260713 | dynamic_erm | 0.4282 | 0.4397 |
| 984 | 20260713 | dynamic_js | 0.4935 | 0.5005 |
| 984 | 20260714 | dynamic_erm | 0.4331 | 0.4464 |
| 984 | 20260714 | dynamic_js | 0.4849 | 0.4913 |
| 984 | 20260715 | dynamic_erm | 0.4259 | 0.4403 |
| 984 | 20260715 | dynamic_js | 0.4858 | 0.4923 |
| 2,460 | 20260711 | dynamic_erm | 0.5198 | 0.5527 |
| 2,460 | 20260711 | dynamic_js | 0.5816 | 0.5943 |
| 2,460 | 20260712 | dynamic_erm | 0.5213 | 0.5407 |
| 2,460 | 20260712 | dynamic_js | 0.5681 | 0.5800 |
| 2,460 | 20260713 | dynamic_erm | 0.5137 | 0.5350 |
| 2,460 | 20260713 | dynamic_js | 0.5682 | 0.5841 |
| 2,460 | 20260714 | dynamic_erm | 0.5182 | 0.5408 |
| 2,460 | 20260714 | dynamic_js | 0.5609 | 0.5778 |
| 2,460 | 20260715 | dynamic_erm | 0.5231 | 0.5488 |
| 2,460 | 20260715 | dynamic_js | 0.5762 | 0.5890 |
| 4,921 | 20260711 | dynamic_erm | 0.5892 | 0.6192 |
| 4,921 | 20260711 | dynamic_js | 0.6401 | 0.6601 |
| 4,921 | 20260712 | dynamic_erm | 0.5994 | 0.6290 |
| 4,921 | 20260712 | dynamic_js | 0.6404 | 0.6620 |
| 4,921 | 20260713 | dynamic_erm | 0.5944 | 0.6224 |
| 4,921 | 20260713 | dynamic_js | 0.6400 | 0.6537 |
| 4,921 | 20260714 | dynamic_erm | 0.5899 | 0.6177 |
| 4,921 | 20260714 | dynamic_js | 0.6327 | 0.6557 |
| 4,921 | 20260715 | dynamic_erm | 0.5945 | 0.6239 |
| 4,921 | 20260715 | dynamic_js | 0.6273 | 0.6497 |
| 9,842 | 20260711 | dynamic_erm | 0.6457 | 0.7059 |
| 9,842 | 20260711 | dynamic_js | 0.7025 | 0.7372 |
| 9,842 | 20260712 | dynamic_erm | 0.6431 | 0.7006 |
| 9,842 | 20260712 | dynamic_js | 0.6915 | 0.7333 |
| 9,842 | 20260713 | dynamic_erm | 0.6383 | 0.6907 |
| 9,842 | 20260713 | dynamic_js | 0.7038 | 0.7349 |
| 9,842 | 20260714 | dynamic_erm | 0.6463 | 0.7037 |
| 9,842 | 20260714 | dynamic_js | 0.7022 | 0.7374 |
| 9,842 | 20260715 | dynamic_erm | 0.6560 | 0.7070 |
| 9,842 | 20260715 | dynamic_js | 0.6994 | 0.7278 |

## Per-class OOD Macro-F1

Values are mean ± sample SD across available training seeds. Each seed value averages the six OOD profiles and three evaluation seeds.

| Parents | Crystal system | ERM | JS λ=60 |
|---:|---|---:|---:|
| 984 | triclinic | 0.5609 ± 0.0058 | 0.5942 ± 0.0160 |
| 984 | monoclinic | 0.3964 ± 0.0174 | 0.4315 ± 0.0088 |
| 984 | orthorhombic | 0.3179 ± 0.0148 | 0.3695 ± 0.0089 |
| 984 | tetragonal | 0.3830 ± 0.0038 | 0.4408 ± 0.0143 |
| 984 | trigonal | 0.3565 ± 0.0136 | 0.4100 ± 0.0093 |
| 984 | hexagonal | 0.4109 ± 0.0142 | 0.5038 ± 0.0157 |
| 984 | cubic | 0.5953 ± 0.0051 | 0.6637 ± 0.0152 |
| 2,460 | triclinic | 0.5969 ± 0.0081 | 0.6344 ± 0.0158 |
| 2,460 | monoclinic | 0.4225 ± 0.0156 | 0.4581 ± 0.0202 |
| 2,460 | orthorhombic | 0.4076 ± 0.0091 | 0.4609 ± 0.0184 |
| 2,460 | tetragonal | 0.4908 ± 0.0086 | 0.5487 ± 0.0139 |
| 2,460 | trigonal | 0.4444 ± 0.0125 | 0.5010 ± 0.0153 |
| 2,460 | hexagonal | 0.5522 ± 0.0064 | 0.6163 ± 0.0062 |
| 2,460 | cubic | 0.7202 ± 0.0118 | 0.7776 ± 0.0183 |
| 4,921 | triclinic | 0.6344 ± 0.0121 | 0.6705 ± 0.0062 |
| 4,921 | monoclinic | 0.4697 ± 0.0137 | 0.5131 ± 0.0182 |
| 4,921 | orthorhombic | 0.4767 ± 0.0215 | 0.5163 ± 0.0046 |
| 4,921 | tetragonal | 0.5843 ± 0.0089 | 0.6371 ± 0.0207 |
| 4,921 | trigonal | 0.5373 ± 0.0120 | 0.5719 ± 0.0046 |
| 4,921 | hexagonal | 0.6646 ± 0.0079 | 0.7108 ± 0.0102 |
| 4,921 | cubic | 0.7875 ± 0.0074 | 0.8332 ± 0.0055 |
| 9,842 | triclinic | 0.6750 ± 0.0055 | 0.7080 ± 0.0201 |
| 9,842 | monoclinic | 0.5075 ± 0.0107 | 0.5676 ± 0.0091 |
| 9,842 | orthorhombic | 0.5310 ± 0.0098 | 0.5987 ± 0.0077 |
| 9,842 | tetragonal | 0.6640 ± 0.0123 | 0.7263 ± 0.0182 |
| 9,842 | trigonal | 0.5979 ± 0.0087 | 0.6422 ± 0.0110 |
| 9,842 | hexagonal | 0.7142 ± 0.0144 | 0.7872 ± 0.0079 |
| 9,842 | cubic | 0.8318 ± 0.0140 | 0.8690 ± 0.0069 |

## GPU and measured runtime

GPU: **NVIDIA GeForce RTX 4070 Ti SUPER**; device record: NVIDIA GeForce RTX 4070 Ti SUPER, 16376 MiB, 591.86.

| Workers / queued batches | Paired steps/s | Views/s | Validation pair seconds | 8 method runs | 24 method runs | 40 method runs |
|---:|---:|---:|---:|---:|---:|---:|
| 4/4 | 20.887 | 668.4 | 3.30 | 2.65 h | 7.95 h | 13.25 h |
| 6/6 | 24.031 | 769.0 | 2.09 | 2.30 h | 6.89 h | 11.49 h |
| 8/8 | 24.364 | 779.7 | 2.08 | 2.27 h | 6.80 h | 11.33 h |
| 12/12 | 24.929 | 797.7 | 2.09 | 2.22 h | 6.65 h | 11.08 h |
| 16/16 | 24.441 | 782.1 | 2.08 | 2.26 h | 6.78 h | 11.29 h |

Each paired cell updates ERM and JS together; estimates therefore count 4/12/20 paired cells for 8/24/40 individual method runs. One-time Validation panel-cache construction took 0.2 s. Estimates include eight FP32 Validation passes per paired cell and exclude one-time panel construction, checkpoint I/O, Test panel construction/evaluation, and machine contention. The ~8 h historical figure is user recollection, not verified wall-time; compare it with these measurements rather than treating it as a benchmark.

The selected training setup used 12/12 workers/queued batches, as recorded before the formal runs. It reuses the V9 online physical-rendering prefetcher, worker-local peak cache, structure-invariant reflection/preferred-orientation work, pinned memory, non-blocking H2D, two CPU intra-op threads, BF16 autocast, fused AdamW, and TF32. Validation and Test inference use FP32.

## Executed runtime

The matrix ran from 2026-10-13T22:05:50+08:00 to 2026-10-14T10:57:09+08:00 (12.86 h end-to-end wall time). The 20 completed paired cells sum to 12.24 h; one interrupted 10% cell attempt added 0.59 h before that cell was restarted from step 0.

Sampled whole-device telemetry integrates to 5.29 GPU-busy-equivalent hours over 9,109 samples. This is device-wide utilization and may include other processes; it is not attributable solely to this experiment.

## Source-machine benchmark comparison

The source Windows laptop (RTX 4060 Laptop GPU, 8/8) measured 11.786 paired optimizer steps/s and projected 23.69 h for 40 method runs. CUIFA (RTX 4070 Ti SUPER, 12/12) measured 24.929 paired steps/s and projected 11.08 h; the measured paired-step rate ratio is 2.12×.

Observed completed-cell wall time was 12.24 h, plus 0.59 h for the interrupted partial attempt; end-to-end wall time was 12.86 h. The historical ~8-hour run is an unverified recollection. The rate comparison includes both a GPU change and runtime-setting change, so it is not a software-only speedup estimate.

## Figures and machine-readable results

- [Learning curve](parent_budget_efficiency/learning_curve.png)
  Error bars show sample SD across the five training seeds.
- [Paired differences](parent_budget_efficiency/paired_deltas.png)
  Error bars show sample SD across the five matched training-seed differences; the dashed line marks zero.
- [Summary JSON](parent_budget_efficiency/results.json)
- [Per-seed metrics CSV](parent_budget_efficiency/per_seed_metrics.csv)
- [Paired-difference CSV](parent_budget_efficiency/paired_deltas.csv)
- Checkpoints, panel caches, and per-parent predictions are retained in the ignored local output directory, outside Git.

## Reproduction files

- [Frozen protocol config](../configs/parent_budget_efficiency.v1.json)
- [Nested parent subset manifest](../manifests/parent_budget_efficiency/parent_subsets.v1.json)
- [Ranked Train-parent list](../manifests/parent_budget_efficiency/ranked_train_parents.v1.csv)
- [Paired fixed-step runner](../scripts/run_parent_budget_pair.py)
- [Matrix launcher](../scripts/run_parent_budget_matrix.py)
- [Result analyzer](../scripts/analyze_parent_budget_matrix.py)

## Provenance and interpretation limits

Parent subset manifest SHA-256: `8A484426AA1DDEABCD11084FAE8F7CAE4A2B56B6B230D0DCAC466E50F043422D`. Protocol config SHA-256: `F8E531868741DFAABC484B9F73E711196911B82BD8836D2FAE14EE409B2B406C`. Local output root: `CUIFA local ignored output directory (excluded from Git)`.

All available cells were retained regardless of outcome. Paired uncertainty is summarized over training seeds; intervals crossing zero are reported as uncertain evidence, not erased or treated as a binary experiment failure. This experiment evaluates simulated parent-structure budget efficiency only; it does not estimate RRUFF real-label efficiency.
