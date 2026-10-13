# Parent-Structure Sample Efficiency Supplementary Experiment

**Status:** preflight complete; **formal training not started**. This is a supplementary post-main analysis using the already evaluated simulated Test split, not a new blind holdout.

## Gate status

| Gate | Status | Evidence |
|---|---|---|
| A — environment, data, history, protocol | PASS | Local 14,060-record split and 14,060 peak tables are available and hash-verified; RTX 4060 Laptop GPU with CUDA/BF16/fused AdamW is available. Historical V9 stopping and optimizer evidence was read from the ten-run summary and source. |
| B — implementation, fairness checks, smoke, throughput benchmark | PASS | Fixed-step paired runner reuses multiprocessing physical rendering and worker-local peak caches; 13 targeted tests pass, a three-step matched-view unit smoke passes, and the full-budget GPU smoke renders bitwise-identical direct/prefetched views while updating both objectives. |
| C — formal matrix and uniform Test evaluation | NOT_RUN | No scientific run has been launched. |
| D — statistics and figures | NOT_RUN | No new scores exist. |
| E — archive and GitHub | NOT_RUN | Final report and outputs will be added after execution. |

## Recovered historical V9 training protocol

The V9 ten-run launcher sets **maximum** 61,600 optimizer steps, batch size 16, 100 maximum epochs, validation every 6,160 steps, minimum 50 epochs before early stopping, patience 3 and `min_delta=0.002`. Each epoch has 616 full batches: 9,856 parent occurrences and 19,712 two-view spectra (the last batch wraps to full size under the fixed-step sampler). The optimizer is AdamW with a constant `1e-4` learning rate and `1e-4` weight decay. The primary checkpoint score is mean Macro-F1 across six single-factor OOD Validation profiles; in-range Macro-F1 is the tie-break. The final early-stop step is not directly stored in the result summary; it is inferred as `stop_epoch × 616`, while runs without early stopping are inferred to reach 61,600.

| Seed | Method | Best checkpoint step | Stop epoch | Inferred terminal steps |
|---:|---|---:|---:|---:|
| 20260711 | ERM | 49,280 | 90 | 55,440 |
| 20260711 | JS | 24,640 | 70 | 43,120 |
| 20260712 | ERM | 55,440 | 100 | 61,600 |
| 20260712 | JS | 49,280 | 100 | 61,600 |
| 20260713 | ERM | 61,600 | 100 | 61,600 |
| 20260713 | JS | 49,280 | 100 | 61,600 |
| 20260714 | ERM | 55,440 | 100 | 61,600 |
| 20260714 | JS | 18,480 | 60 | 36,960 |
| 20260715 | ERM | 49,280 | 100 | 61,600 |
| 20260715 | JS | 36,960 | 90 | 55,440 |

Terminal counts above are inferred from the source stop epoch and the 616-step epoch; they are not directly logged terminal-step values. The V9 ten-run script defaults to 8 workers / 8 prefetched batches. The separate historical laptop tuning profile tested 16/16, but that is not the ten-run launch setting. The selected checkpoint-step median across the ten historical runs is 49,280; this is frozen as the new common supplementary optimizer budget, **not** a claim of reproducing V9's early-stopping trajectory.

## Data and frozen design

Authoritative split manifest: SHA-256 `B9D3B72E42EA0FD549DAE34425FF61D2D650D5DD7FE6F337D747CB952CF43293`; source records: `05D5D33F200194612A8CDBE29D9443FC7BAD9C245F66D185364B6A75915CC6C`; peak-cache manifest: `6AE0CFD1B5B29671E2F532D7A094F2FC412CABD64E4CF77D42915937BACC8D18`. Counts are Train/Validation/Test = 9,842/2,109/2,109. Peak NPZ files were individually hash-checked before the subset list was frozen. The source records' embedded split field disagrees with the authoritative split for 6,601 records; the frozen manifest is authoritative and source IDs, labels and parent fingerprints agree.

Nested crystal-system-stratified subsets use selection seed `20261013`, exact counts 984/2,460/4,921/9,842, and immutable IDs in `manifests/parent_budget_efficiency/`. Dynamic ERM and Dynamic JS (λ=60) will share each initialized weight tensor and the exact same ordered parent batch and rendered pair. Every method receives 49,280 full optimizer steps, 788,480 parent occurrences and 1,576,960 generated views. Validation/checkpoint selection is fixed in `configs/parent_budget_efficiency.v1.json` before any new score.

## Hardware and benchmark

Observed device: NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB; driver 566.26; PyTorch 2.13.0+cu126; CUDA and BF16 are available; fused AdamW is supported. The full 100% parent subset was used for the end-to-end smoke, including online physical spectrum generation, pinned/non-blocking host-to-device transfer, and both ERM and JS forward/backward updates. Two 64-step repeats per setting measured median paired rates of 13.987 steps/s at 8/8, 9.517 at 12/12, and 10.675 at 16/16; direct and prefetched physical views were bitwise equal. The selected 8/8 setting matches the V9 ten-run script default and was fastest across repeats. Its FP32 paired Validation cost was 11.421 seconds per checkpoint. Estimates for 8/24/40 individual method runs (4/12/20 paired budget cells) are 4.02/12.05/20.08 GPU hours, including eight Validation checkpoints per cell. A one-time Validation panel-cache build took 5.14 seconds. The historical 16/16 result of 31.31 batches/s measured rendering throughput; it is not directly comparable with the present 13.987 paired optimizer steps/s, which includes two ResNet updates, physical rendering, and transfer. These are short-benchmark projections; checkpoint I/O, Test evaluation, contention, and any longer-run throttling are excluded. The remembered V9 wall time of about eight hours is unverified; the new fixed matrix has 1,971,200 planned method optimizer steps versus 560,560 inferred historical terminal steps across the ten runs, so the workloads differ.

## Results

No formal training result scores are available yet. Gate C is ready to start with all eight method runs for seed 20260711; no claim about same-budget gains or fewer-parent efficiency is made at preflight.
