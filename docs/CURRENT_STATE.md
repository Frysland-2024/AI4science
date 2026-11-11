# AI4science 当前状态

> **权威性说明：** 本文件记录当前科学状态与当前执行口径。历史版本、旧聊天和 `PROJECT_HISTORY.md` 用于解释“为什么改变”，不得覆盖这里的当前结论；AI/Agent 工作规则见 [`../AGENTS.md`](../AGENTS.md) 与 [`RESEARCH_WORKFLOW.md`](RESEARCH_WORKFLOW.md)。

**状态日期：** 2026-11-11

**2026-11-11 ISSUE #61 / PR #75 状态对齐：** Issue #61 已关闭，结论仅覆盖本机 package/schema/manifest/CPU preflight；该本机结论由 Issue 正文及当前主分支验收记录支持。PR #75 目前为 **closed, unmerged**，不得描述为已合并。PR 正文中的“#61 remains open for PR review/merge”与当前 Issue 状态不符，已过时；它不改变 #61 已关闭的本机范围，也不满足 #55 的目标机 readiness gate。

**版本与证据边界：** #61 的本机收据针对 `v11-prefetch-validation-20261109.3`。当前迁移源码合约为 `v11-laptop-gradient-portable-20261110.12`；最新 source-only ZIP 尚待在 cuifa 解包核验，数据缓存另行准备。cuifa Stage 0 仍为 **BLOCKED / NOT_RUN**，没有 HPO 授权。#61 / PR #75 的本机证据不能作为目标 GPU、吞吐、HPO、正式训练或 Test/RRUFF 评分的完成证明。

**2026-11-10 OWNER PRIORITY / HPO DELIBERATION DEFERRED (NO NEW AUTHORIZATION):** 研究者明确决定**暂时不进一步学习或审议 V11 HPO，也不启动 cuifa Stage 0/HPO**。原因：cuifa 的目标电脑据负责人告知未来约两周被其他任务占用（只是预计资源阻塞期限，**不代表到期自动恢复或授权**）；研究者眼前更重要的事务是**2026-11-10 下午的面谈准备、最后一轮套磁安排，以及仍需持续推进的 GRE 备考**。这是一项有意识的研究优先级与注意力分配决定，不代表放弃七晶系分类主线、撤销当前冻结 HPO 方案，或产生新的科学结果。

**NEXT RESEARCH RESUMPTION CHECKPOINT（未来恢复科研时首先执行，仅讨论/检查，不自动训练）：** 遵循长期阶段规则 **先理解 → 再规划 → 后执行**。当前具体从**理解和审议 HPO**开始，而不是从 GPU 启动、Codex 工单或参数调整开始。先用当前代码、Issue #55、冻结协议与 Train-only 梯度证据解释：(1) HPO 的科学目的、为何现在需要它、要消除什么不确定性；(2) 现有完整执行方案与 Optuna/TPE、R=λr 的原理；(3) 三参数 λ / middle stride / kernel 的科学意义、固定变量、四组架构对照与后续探索；(4) 当前 8-trial 设计与分阶段／扩大搜索／暂不 HPO 等替代路线的优劣；(5) Stage 0 实测后可承担的预算、可能结果、决策价值与停止条件。**只有研究者理解并决定采用何种路线，且 Stage 0 与预算等独立门槛实际通过并另行授权，才可推进 HPO。**研究恢复时间由研究者另行决定，不设置自动到期执行。当前 GPU Stage0、HPO、confirmation、final、Test、RRUFF 均仍 NOT_RUN。本条仅保存恢复入口，不更改任何代码、科研合同、数据划分或训练参数。

**2026-11-10 HPO-launch safety repair (CODE + TEST; CUIFA STAGE0/HPO NOT_RUN):**
The current runner now refuses \`--mode run\` without a SHA-verified,
cuifa-local Stage0 PASS receipt and a separate owner HPO approval referencing
that receipt and containing a measured-throughput-based GPU-hour budget.
Stage0 requires real peak-cache, CUDA Train, full six-profile Validation,
checkpoint/resume parity and sustained throughput evidence; this laptop
**cannot certify** cuifa. Total 8 HPO + 2 confirmation stages are estimated
with a 30% buffer before approval; the per-invocation 12-hour deadline is
now checked at complete optimizer-step boundaries, atomically checkpointed
and safely resumed, but an ongoing full Validation evaluation may overrun.
A new **source-only current-commit ZIP** mode lets the owner refresh code,
tests and both pinned Train JSON reports without re-archiving 154,975 cached
PeakTables. All five older source snapshots were pre-.12 and must not be
treated as current. This is launch engineering; R-first science, batch16,
108,478-parent Train and 23,245-parent Validation are unchanged.


**2026-11-10 ACTIVE — V11 R-FIRST HPO FREEZE; LAPTOP STAGE COMPLETE; CUIFA STAGE0/HPO NOT_RUN:** The definitive HPO-scale source is the FIRST, complete **108,478 independent Train-parent / 6,780-batch** learned-state A0 gradient audit (source SHA256 7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020). It measured unweighted trunk r=||grad JS||/||grad CE||=**0.0681726422271**. Transfer V9's **Validation-winning R=1.7541151944**, NOT its numerical lambda=60: the equivalent V11 A0 reference is lambda=R/r≈**25.73**. The primary HPO design uses **R=lambda*r_A0**, nominal R target [0.05,2.0], mapped into frozen **lambda [3.0,29.33728156]** (effective reference R≈[0.20452,2.0] after lambda lower clipping). R<=2 is a **search-focus/budget choice**, NOT a universal unsafe-gradient cutoff. All A0–A3 candidates use this **common A0 reference r** for HPO-space design; their actual learned gradient ratios need not be equal, nor does R itself establish alignment. Four A0–A3 matched-**lambda≈25.73** architecture controls precede 4 multivariate TPE trials (default **8 total**, three HPO dimensions lambda log-float/stride2-or-4/kernel5-or-9), with selection on frozen **23,245-parent × six OOD-profile Validation** only. The SECOND V9-style laptop Train-only safety audit (704 distinct Train parents, 44 batches, lambda0.3/3/30/60, all gate PASS) stays **preserved verbatim as supporting safety/negative-design-history evidence**, but lambda60 and R≈4.09 are **not** in this primary HPO search. Exact old reports are SHA-pinned and combined into the cuifa study gradient_gate.json by a deterministic CPU-only importer; no additional laptop Train gradient measurements or GPU runs are planned. The stage is officially **WAITING_FOR_CUIFA_STAGE0_AND_HPO**; no cuifa Stage0, HPO, confirmation, final, synthetic Test, or RRUFF has run. Effective batch16/micro16, data/simulator/optimizer/splits unchanged.

**Superseded 2026-11-10 intermediate proposal:** An earlier attempt copied V9 lambda [0.3,3,30,60] to V11, producing an overly broad R≈[0.02045,4.09036] domain and default 12 HPO trials. It passed a limited A0 Train-only safety check, which did **not** make that interval more relevant to transferring V9's R≈1.75 success. Keep the original V9-style supplemental safety JSON and commit as research-history evidence; do not use that proposal as the active HPO scope.

**2026-11-10 V11 RTX4060 batch-capacity and sustained-default audit (TRAIN-ONLY ENGINEERING; HPO NOT_RUN):** The owner asked to push the laptop GPU batch to its practical limit **after** the real 108,478-parent Train-only λ gradient gate was published. On Windows **RTX 4060 Laptop 8GB / Ryzen 9 7945HX**, with the original V11 ResNet18-GN A0, two dynamic views/parent, AdamW LR2e-4/WD1e-4, and prefetch **12 workers / 4 queued batches / PeakTable cache64 / native1**, the initial four-update sweep succeeded at effective/microbatch **16:2, 16:4, 16:8, 16:16, 32:32, 64:64, 128:128, 256:256** (batch256 PyTorch allocated VRAM peak **3.535 GiB**). An upper-bound short attempt **320:320 succeeded** (345.94 parents/s, **4 updates**, peak allocated **4.352 GiB**) and **384:384 succeeded** (284.67 parents/s, **4 updates**, peak **5.188 GiB**), but the same process exited abnormally with exit code 1 while attempting larger 448/512: **no OOM diagnosis or 448+ success can be claimed**. 384 is only the *highest demonstrated short-run physical batch*, **NOT** an approved long-run default. The meaningful sustained **effective batch16** comparison over **64 updates / 1,024 parents per candidate** measured microbatch2→68.17, microbatch4→119.69, microbatch8→159.57, microbatch16→**170.74 Train parents/s**; then **16:16 passed 256 consecutive updates / 4,096 parents at 162.10 parents/s**, max PyTorch allocated VRAM **0.419 GiB**, without OOM. Independent bounded Train-only smoke of all four HPO candidate models **A0/A1/A2/A3 at 16:16** passed finite CE/JS gradients, with per-model PyTorch allocated peaks **0.419/0.475/0.402/0.345 GiB** (only 3 training steps/model; not comparative model quality). These are short engineering comparisons, not full-epoch or cuifa throughput guarantees; the GPU+CPU physics input and Validation HPO performance were not measured.

**ACTIVE DEFAULT / frozen scientific identity:** **effective `--batch-size 16` + GPU `--microbatch-size 16` (no accumulation)** is both the best sustained tested microbatch choice under the *already-frozen science batch16* and **ALREADY the effective default in `server_migration/one_click_v11.py`** (`--batch-size` default16; unspecified microbatch automatically equals effective batch). Preserve it for cuifa Optuna unless a newly authorized *scientific* change and fresh batch-matched Train gradient gate are produced; changing effective batch to 32/64/320/384 would change optimizer noise, updates/epoch and JS/CE gradient statistics and invalidate the previously frozen [λ=3..29.3373 Train-only evidence](../server_migration/gradient_gate_v11_train_108478.json). The benchmark helper can explore 512 for engineering but **the production model/trainer source was deliberately not changed**, preserving its source SHA and gradient gate fingerprint. Local inspectable engineering records: `E:\AI4science\_local\v11_batch_extreme_20261110.json`, `v11_batch_sustained_20261110.json`, `v11_batch16_long_20261110.json`; attempted upper-capacity 320/384 lines appear in the stress-process output, which terminated before its JSON write. Existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) contains the complete engineering acceptance summary. **Cuifa hardware Stage0, HPO, confirmation, final/TEST/RRUFF all NOT_RUN.**


**2026-11-10 V11 GPU BATCH PRESSURE / SCIENCE-SAFE DEFAULT (IMPLEMENTED):** Upon completion/publication of the real RTX4060 108,478-Train-parent lambda gradient gate, performed bounded **real V11 dynamic paired-spectrum Train-only** GPU optimization stress on laptop RTX4060 8GiB, CPU prefetch 12/4/cache64. At constant **effective parent batch=16**, 64-step sustained throughput by physical microbatch was **2→68.17**, **4→119.69**, **8→159.57**, **16→170.74 parents/s** (A0 ResNet18-GN; BF16 if supported). Hence the explicit **default for Cuifa Windows HPO is effective batch16 + GPU microbatch16, no accumulation**, frozen in `server_migration/start_windows.ps1` and identical to the direct Python default. A0–A3 architecture CUDA micro16 smoke (3 steps each) **all passed**, worst A1 GPU PyTorch reserved peak 0.520GiB. Effective batch32/64 sustained 64-step Train throughput was 217.18/205.13 parents/s; effective batch128/256 (24 steps) 265.81/234.49 parents/s, but these are **different scientific optimizer regimes**, not automatically legal replacements for a lambda gate explicitly bound to parent batch16. Very short 3-step batch384 PASS (1.123GiB free) and batch512 PASS (PyTorch reserved7.314GiB; CUDA free0.0GiB), **NOT safe routine defaults**. Large-batch benchmark process overlap briefly exhausted aggregate VRAM; the old process tree was cleaned and trials finished; no GPU crash or HPO. **Only batch16/micro16 is the current science-compatible execution default**, not the claim that batch16 is the fastest possible parent-batch on this GPU or that Cuifa's faster 4070 Ti SUPER has been independently tuned. More ambitious effective-batch choices need a justified fresh gradient prior/training contract and on-target GPU Stage0. All metrics/reasons preserved in existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55); benchmark source reused, no new PR, Issue or standalone report.


**2026-11-10 V11 TRAIN-ONLY GRADIENT GATE COMPLETED AND PUBLISHED (cuifa HPO NOT_RUN):** **REAL RTX 4060 LAPTOP EXPERIMENT COMPLETE.** A0 same-parent two-view **ERM (lambda=0)** learned on a **deterministic 20,480-parent stratified Train subset for 20 complete epochs**; the sampled Train-only final-epoch check (816 sampled parents, **NOT** Validation or full-Train accuracy) was **accuracy 0.993873, CE 0.083568**. The strict historical CE-plateau criterion mistakenly rejected this learned model; the archived, **SHA256-pinned** 156,200,035-byte epoch20 checkpoint was restored without rerunning the warmup. A subsequent first scan was rejected because the 1,280-step warmup epoch length was incorrectly reused for the whole Train gradient scan; code now distinguishes **1,280 warmup steps/epoch** from **6,780 full-Train scan batches** and fails closed on incomplete cohorts. Both negative operational events and repairs are preserved in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

**Frozen valid evidence:** full **108,478 unique TRAIN parents / 6,780 paired-view gradient batches**, no Validation, Test, or RRUFF access; unweighted ResNet-trunk JS/CE per-batch gradient norm-ratio **median 0.0681726422** (full-cohort aggregated full-model norm ratio **0.0341939561**). Pre-Validation **gradient-informed Optuna lambda bound [3.000000, 29.3372815643]**, with **weak [3,4.4005922346]**, **medium [4.4005922346,14.6686407822]**, **strong [14.6686407822,29.3372815643]** under the frozen weighted influence windows. This is the chosen prior SEARCH RANGE, **not a measured optimal lambda**; V9's lambda60 now lies outside the constrained V11 range, but has not been disproved by real-domain tests. Crucially, **gradient directions vary**: median per-batch backbone CE–JS cosine **-0.0204393**, 10th/90th percentiles **-0.2599702/+0.1969625**, summed-gradient trunk cosine **+0.1501643**, whole-model cosine **+0.2232630**; a large magnitude ratio does NOT prove JS dominates the update. Train-only gradient diagnostics do not establish generalization.

**GitHub result:** [frozen 5,929-byte TRAIN gradient evidence JSON](../server_migration/gradient_gate_v11_train_108478.json), full SHA256 **`7f6c759f5c6fea7fe855ab579ce2d0dd6771f7edbab815db9339c4e25eb1d020`**, evidence commit **`8d7c7a6b4834d5369f9190cdc418f1e449ac5686`**. Source fix commit **`d04412b655d651e629da4b9c1210c04358f4b9a9`**, **48 server_migration pytest tests + 2 subtests PASS**. Existing `--mode run` automatically imports this Git-tracked gate, enforces the frozen science/data fingerprint and λ bounds, and then runs **fully automatic multivariate Optuna TPE** for λ, middle Stride {2,4}, Kernel {5,9}; it will NOT redo the laptop gradient sweep. **cuifa Stage 0, HPO, confirmation, final training, Test/RRUFF remain NOT_RUN**; previous status text saying the Train gradient gate was NOT_RUN is now superseded. No new docs/PR/issues were created for this receipt.


**2026-11-10 V11 gradient-gated autonomous 3D Optuna (CODE TESTED; GPU NOT_RUN):** Following the owner's direction to retain **FULLY AUTOMATIC Optuna** with scientific bounds rather than six fixed candidate recipes, V11 main source is updated to three explicit dimensions **lambda_js / middle_stride / kernel_size**. Architecture direction is a limited **A0–A3 2x2 control** (middle stride 4 vs 2, kernel 9 vs 5; outer 4/4 fixed, ResNet18 depth/width/head frozen), testing the peak-information-retention hypothesis inspired by Bin Cao/SimXRD rather than assuming that smaller stride/kernel is better. The first four trials compare the 2x2 controls at one **TRAIN-gradient-approved lambda anchor**; remaining candidates are free **multivariate Optuna TPE proposals** over three parameters, in the frozen bounds, default **8 trials** (allowed 6–12). The historical V9 approach is expanded into an automatic **Train-only learned-state gradient gate**: A0 paired-view Dynamic ERM trained for 5–10 complete independent-parent epochs until Train accuracy >=0.30 and CE <=1.85; at learned state, measure all **108,478** unique TRAIN parent samples' FP32 full-model gradients, with **convolutional trunk (excludes embedding/head)** JS-to-CE batch gradient medians used to derive weak/strong JS-influence bounds (0.05..2), absolute safe lambda3..120 and minimum 2x span. Complete whole-model summed-gradient norms are also saved. This is a pre-Validation *search-space prior*, not a statement that any lambda is optimal. Each HPO candidate MUST receive >=50 full parent epochs; Validation 6 OOD profiles every 10 epochs, **only score epoch50+ checkpoints**, shared **100-epoch cosine horizon** with confirmation/final (up to 100 epochs, early stopping only after50, patience3/0.002). Fixed optimizer LR2e-4, WD1e-4; effective batch16 remains the scientific default; CPU workers12/queues4/cache64/native1 follows the latest owner-selected universal default, not a performance guarantee on untested machines. Windows→Linux HPO handoff now requires the frozen Train gradient gate and its SHA; modified/missing range blocks final. Contract **v11-gradient-gated-optuna-20261110.10**; simulator and Validation panel SHA identities unchanged, historical .7/.8/.9 panels can only be reused under strict identity and hash matching. **47 isolated server_migration tests +2 subtests PASS**, including real Optuna 4.9 TPE proposal simulation; no actual 108,478-parent GPU gradient sweep, Cuifa Stage0, HPO, confirmation, final or RRUFF/Test has run. Earlier .9 six fixed candidates / .9 implementation description and `.8` 5/10/10 are superseded *execution* records (retained as chronology). See [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) and [current V11 launcher README](../server_migration/README.md).


**2026-11-09 V11 focused HPO code implementation .9 (NOT_RUN):** GitHub main now implements the owner-selected **focused** scientific tuning: freeze AdamW LR=2e-4, cosine-to-5%-floor and weight_decay=1e-4; select only **JS lambda plus architecture** (stride transitions and residual kernel, separately controllable). ResNet-18-GN depth/width remain unchanged, with A0=(4/4/4,k9), A1=(4/2/4,k9), A2=(4/2/4,k5), A3=(4/4/4,k5); all four architecture proposals use historical lambda=60, followed by lambda=30/90 on the best architecture (6 candidates total). This stagewise design cannot guarantee an absolute optimum or rule out other architecture–lambda interactions. **Exposure guard:** full 108,478-parent epoch_shuffle, HPO >=50 complete parent epochs per candidate (339,000 optimizer updates at batch16, two views per parent), confirmation/final up to 100 complete parent epochs (678,000 steps), full six-profile Validation every 10, patience=3 and min_delta=0.002 with stopping forbidden before epoch50 (earliest plateau stop around epoch80), retain best Validation checkpoint. Effective batch16 stays scientific baseline; microbatch and accumulation are engineering controls. CPU **unified Windows/Linux/cloud default** is 12 workers/4 queued batches/64 cached PeakTables per worker/native_threads=1, regardless of CPU model or RAM, as requested by the owner; only local Windows 7945HX has measured throughput, so cloud Stage 0 remains mandatory and explicit runtime overrides are allowed. Version v11-focused-science-cpu-20261109.9 changes training not V11 physics and permits old .7/.8 frozen Validation cache reuse only with matching identity and file SHA verification. Isolated current-source regression: **41 server_migration tests plus 2 subtests PASS** on the laptop. No cuifa Stage 0, formal HPO, final or held-out Test/RRUFF run. Earlier .8 5/10/10 budgets and four-dimensional Optuna configuration are historical, superseded code snapshots; see [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) and [current migration README](../server_migration/README.md).

**2026-11-09 V11 universal cross-platform CPU prefetch defaults (engineering, NOT_RUN on Linux/cloud):** At the owner's request, the Windows-tested `12 workers / 4 queued batches / 64 PeakTables per worker / native_threads=1` is also the **direct Python CLI and Linux cloud launcher default**, not just the two Windows hosts. `start_server.sh --plan/--run/--final` inherits these defaults; its bounded CPU smoke follows the selected `--prefetch-workers` override instead of hardcoding 4. No CPU model / RAM-based automatic downgrade, and explicit runtime overrides remain supported, subject to cloud Stage 0 resource and deterministic-output checks. Only the local Ryzen 9 7945HX Windows setting has been benchmarked; Linux/cloud 12-worker throughput, available RAM, and long-duration reliability are **unverified**. No scientific protocol, model, loss, Train/Validation/Test split, epoch policy, or RRUFF evaluation is changed; formal HPO/cloud training NOT_RUN. The source-snapshot ZIP and transfer SHA256SUMS must be rebuilt before deployment. See [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).


**2026-11-09 Cuifa Windows CPU prefetch sync (resource-only preparation; target-machine NOT_RUN):** User reports Cuifa's desktop CPU is faster than the local Ryzen 9 7945HX, although its exact CPU model/physical core count remains unverified; Cuifa's Windows RTX 4070 Ti SUPER and 32GB host RAM are already recorded. The V11 Windows launcher's **conservative default** is now the locally verified **12 workers / 4 prefetch batches / 64 cached PeakTables / native_threads=1** on **all Windows machines**, including cuifa's 32GB desktop, with no CPU-model, core-count or RAM-dependent fallback. `-CpuProfile conservative` forces 12/4/64/1, while opt-in `-CpuProfile aggressive16` offers **16/4/32/1**, gated on >=18GiB free RAM before formal HPO. Cuifa-host 12-vs-16 throughput, full Validation, and checkpoint/resume still require on-host verification; the only prior 12-worker throughput and 512-step full Validation evidence is from the local 7945HX laptop. No change to scientific inputs, loss, batch, model, current performance-first plan or Test/RRUFF holdout. No formal HPO launched; see [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).



**2026-11-09 owner-prioritized parameter strategy (DESIGN ONLY; code not updated):** Following the complete V1–V9 research-cycle review and November V10 preliminary tuning, **do not HPO every possible knob**. Continue AdamW **WD=1e-4** as an established regularization baseline, with the planned 100-parent-epoch/frozen-Validation/early-stopping contract as additional overfitting control (**early stopping ≠ weight decay**). Carry forward bundled **LR=2e-4 + cosine-to-5%-floor** V10 A0_R1 as the default training recipe, **not a V11-validated or independently isolated LR/scheduler optimum**. Concentrate scientific selection on **(1) same-parent JS λ** (bounded new-V11 synthetic-Validation choice; λ=60 historical starting point and matched ERM comparator) and **(2) ResNet-18-GN PXRD peak-preservation architecture** inspired by SimXRD/Bin Cao (**stride/downsampling and kernel**, two knobs within one research question; depth/width/head remain initially frozen). Treat **effective parent batch=16** as an engineering-first starting constraint, benchmarking microbatch/gradient accumulation for GPU fit; changing *effective* batch changes optimization and requires evidence. Code still Optuna-searches LR/JS λ/WD/scheduler and lacks the approved 100-epoch stopper; execution is **NOT_RUN**, source refactor and validation required before formal experiments. Full decision in existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55); no new issue, PR or standalone record.


**2026-11-09 科研发展主时间线（历史口径，不改变执行）：** 详见 [PROJECT_HISTORY.md 开头的七阶段时间线](PROJECT_HISTORY.md#核对后的完整时间线2026-11-09-阶段节点)：**FerroAI（前置研究）→ PXRD 早期至 V8（问题和方法探索）→ V9（2026 年 7–8 月，14,060 结构、JS λ=60、ERM–JS 多种子和模拟 Test，第一轮完整主科研）→ 早期 V10（7 月 Residual 负结果，与 V9 后期交叠）→ 2026 年 8–10 月（RRUFF/CNRS/校准/数据效率补充，以及另行归档的参数反演）→ 11 月 V10（下一阶段初步 Stride/Kernel 与 LR/Scheduler 调参及 CNN11 探索）→ V11（规模化训练及 RRUFF-Cu1011 真实域竞争对标，目前正式结果未运行）**。这里 V1–V9 是**研究周期**概括，V1–V5 无逐版本完整证据；7 月 V10 和 11 月 V10 并非同一实验。V9 既有结果保持冻结，不得将 V10/V11 说成修补未完成的 V9；V11 当前代码、参数规划及 Test 锁定规则均不因本历史摘要变更。

**2026-11-09 V11 weight decay initially fixed (OWNER DECISION; PLAN ONLY):** Fix **AdamW `weight_decay=1e-4`** for initial V11 tuning and matched JS/ERM; exclude this dimension from initial HPO. This carries forward the historical V9/V10 project baseline, not a proven V11 optimum. OpenAlphaDiffract 2026 publishes AdamW weight decay 0.01, but different architecture/loss/training means there is no reason to copy it blindly. Revisit only for observed, persistent Train-vs-frozen-six-profile-Validation overfitting via separate targeted ablation, without accessing TEST/RRUFF. Current `one_click_v11.py` **still searches weight_decay from 1e-6 to 1e-3**, so code must be updated under the separately authorized protocol implementation; no training/code/PR change has yet been made. Full rationale in [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).


**2026-11-09 V11 ResNet depth / width initial freeze (OWNER DECISION, NOT A CAPACITY OPTIMUM):** Initial V11 HPO keeps the existing ML4pXRDs-derived **ResNet-18-GN A0** residual stage block counts **(2,2,2,2)**, channels **(64,128,256,512)**, GroupNorm groups=32, Dense/embedding width=256 and seven classes; reference A0 has **13,008,839 parameters**. No depth/width/heads capacity sweep in first HPO. This relies on the old V10 A0_R1 provisional single-seed Validation lead (0.731830, old V10 data/simulator), **not** proof of V11 superiority. **Stride/downsampling and kernel are NOT frozen** and remain high-priority, separate architecture variables. Reopen network capacity only if meaningful controlled full-training Train/Validation diagnostics indicate underfitting/overfitting after optimizing schedule/LR/JS and checking downsampling. Documentation-only; source default already complies, no GPU job/PR or new standalone report. Details in existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).


**2026-11-09 V11 loss / sampling initial HPO exclusion (OWNER DISCUSSION DECISION; CODE DEFAULT ALREADY MATCHES):** The 108,478 unique TRAIN parents (parent_structure_id dedupe) span 7 crystal systems: monoclinic 25,593, orthorhombic 22,814, triclinic 17,025, cubic 14,288, tetragonal 12,147, trigonal 9,118, hexagonal 7,493 (largest/minority 3.416×); Validation n=23,245 preserves similar relative proportions. Therefore **initial HPO fixes natural-frequency parent `epoch_shuffle`, unweighted CE, label_smoothing=0, focal loss OFF**, not because these alternatives are scientifically disproved but because there is no training-error evidence to warrant adding loss/sampling dimensions. Reconsider a controlled, matched weighting/sampler ablation only if full synthetic Validation per-class Recall/F1 reveals persistent minority deficiencies; label smoothing/focal only if separately justified by calibration/learning behaviour. No Test/RRUFF accessed; no code/GPU job or trial-count change. Detailed decision and class counts: existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

**2026-11-09 V11 tuneable-parameter scope archived (DISCUSSION / NOT_RUN):** Owner-approved **10-item candidate inventory and diagnostic-first “对症下药” selection rule** are now consolidated into existing [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55), covering architecture (stride/downsampling, kernel, depth/width), optimizer (LR, scheduler, weight decay, effective batch), JS lambda, and conditional class balancing / deferred loss variants. Priority is **not** a mandate to jointly HPO all parameters. Current code still searches only LR/JS lambda/weight decay/scheduler; no epoch, tuning, trial count, frozen data or model changes were made in this documentation update.

**2026-11-09 V11 performance-first training epochs v3 (OWNER CHOICE; PLAN ONLY / NOT_IMPLEMENTED):** Owner selects the **historical 100 full-parent-epoch maximum**, full six-profile frozen Validation **every 10 parent epochs**, **minimum 50 epochs**, **early stopping patience=3 consecutive Validation checks** (i.e. approximately 30 epochs without meaningful improvement, not 3 training epochs), with the old `run_pairing_ablation.py` **min_delta=0.002 absolute mean OOD Macro-F1** as a provisional default to verify before GPU execution. Select best Validation checkpoint and save `last.pt` with full stopper, RNG, parent sampler and LR state for resume. At 108,478 TRAIN parents and effective parent batch 16, this means **6,780 steps per parent epoch, max 678,000 optimizer updates per run, 67,800 steps between scheduled full Validation checkpoints**; LR horizon must be frozen at 100 epochs before the first update. This replaces the previous planned 50-epoch horizon in active [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55), **not** old experimental evidence. HPO candidate count remains a separately unresolved research-design choice; neither 24 HPO runs nor cloud rental is automatically authorized. Existing main `.8` code **still uses 5/10/10 epoch defaults, full Validation every epoch, and has no implemented automatic early stopping**; the revised scientific protocol needs implementation/contract version, regression tests, Windows→Linux handoff and target GPU Stage 0 before execution. Frozen dataset splits, matched JS/ERM science, parent-data-efficiency requirement, synthetic TEST and RRUFF-Cu1011 lockout remain unchanged. Full V11 HPO/final and held-out scoring NOT_RUN.

**2026-11-09 V11 CPU prefetch optimization (local engineering evidence only; formal HPO NOT_RUN):** Profiling the Ryzen 9 7945HX/32GB Windows laptop with RTX 4060 identified CPU online two-view spectrum rendering as a significant bottleneck. A Train-only CPU sweep with byte-identical paired spectra reached 181.49 parents/s with 12 workers/4 queued batches (vs 84.82 for a 4-worker/2-queue earlier probe). The full CPU-prefetch + GPU A0/JS optimizer measured 168.08 parents/s (12 workers/4 queues/64 cached tables; 160 steps) versus 82.43 parents/s (4 workers/2 queues/128 cached tables; 128 steps); minimum free RAM with 12 workers was 10.25GiB. These are short engineering benchmarks, not HPO throughput guarantees or seven-system accuracy improvements. The Windows launcher now auto-detects only this CPU with >=30GiB installed RAM for the 12-worker profile; cuifa's as-yet-unknown CPU retains conservative defaults. Source simulator, scientific batch=16, parent sampling, frozen Train/Validation, the executable .8 5/10/10 defaults, and RRUFF/Test lockout remain unchanged; the separate performance-first v2 50-epoch plan is active but not implemented. Consolidated private evidence under _local/v11_cpu_optimization_20261109.json; a 12-worker 512-step + full six-profile Validation engineering acceptance also PASS (129.88s train+scoring, 5.80GiB lowest free RAM; 2594MiB peak whole-GPU memory), compared with ~183.17s in an earlier 4-worker full-Validation test. No long-run HPO was started; see [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).

**2026-11-09 V11 pre-HPO budget revision (CODE ONLY; NOT_RUN):** Before any formal V11 HPO starts, planned default training budgets have been extended from 1/2/~7.27 to **5/10/10 full parent epochs** for HPO/independent confirmation/final training under the frozen `epoch_shuffle` sampler. At effective parent batch 16 this is **33,900 / 67,800 / 67,800 optimizer steps** per run, with full six-profile Validation every parent epoch; 6+2+3 default runs total 542,400 updates versus the prior 215,640. This is a convergence-budget design choice prompted by comparison with SimXRD, **not a claim of equal training FLOPs/realized GPU time or changed observed model accuracy**. The implementation contract is now `v11-parent-epoch-budget-20261109.8`; any previously packed private source snapshot must be rebuilt. All target-cuifa GPU Stage 0, HPO, confirmations, final seeds and held-out Test/RRUFF-Cu1011 remain **NOT_RUN** and require separate resource/budget authorization under [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55). Data splits, architecture, same-parent CE+JS objective, frozen Validation and test lockout are unchanged.


**2026-11-09 V11 .7 parent-exposure and batch-engineering change (local verification only):** The `main` trainer now defaults to seeded `epoch_shuffle` over exactly 108,478 independent Train parents: one complete epoch for HPO (batch=16 → 6,780 steps), two for confirmation (13,560), preserving the frozen 23,245-parent six-profile Validation and RRUFF lockout. Optional parent-weighted microbatch accumulation retains effective batch and one optimizer step; cloud final can change only audited prefetch/CPU/cache/hour runtime settings. Local Windows RTX 4060 8GB passed bounded CUDA batch=16 and deterministic 2-worker render smoke, plus 34 original/new regression tests; short Train-only batch benchmarks are engineering measurements, **not** target cuifa GPU validation or formal HPO. Source payload contract `v11-parent-epoch-microbatch-20261109.7`; no Test/RRUFF scores or full GPU training. See [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55).



**2026-11-09 V11 Windows-HPO / Linux-final execution split (code ready, GPU HPO NOT_RUN):** The existing ResNet-A0 / V11 same-parent JS research recipe is unchanged. `server_migration/start_windows.ps1` now provides native Windows plan/smoke/HPO/export for the cuifa desktop candidate (RTX 4070 Ti SUPER 16 GB VRAM, 32 GB RAM; CPU/SSD unconfirmed), defaulting to 2 prefetch workers / 2 queued batches / 256 cached PeakTables per worker. A checksummed `hpo_handoff.zip` transports the completed Optuna selection, two independent confirmations, selected checkpoints, frozen contract and Validation index to the existing Linux `--final` path; final training checks regeneration of the exact panel hashes before running. The source snapshot contract is now `v11-windows-hpo-handoff-20261109.6`. Local Windows `plan` on the 154,975 PeakTable cache passed; 27 server_migration regression tests passed; a **bounded 4-parent** CUDA smoke passed on this laptop's RTX 4060, **not** the target cuifa 4070 Ti SUPER batch=16. Local structure source archive is separate; cached Train/Validation manifest and PeakTables are present. The actual cuifa Stage 0 (GPU resource/throughput, complete 23,245-parent six-profile Validation, and real resume/prefetch recovery), all formal HPO, cloud final and locked Test/RRUFF scoring remain **NOT_RUN / not authorized**. See [Issue #55](https://github.com/Frysland-2024/AI4science/issues/55) and [server_migration/README.md](../server_migration/README.md).

**2026-11-09 Issue #61 local preflight PASS:** latest `main` includes the merged-shard schema adapter/`--records-path`, parent-safe Train+Validation manifest builder with per-PeakTable SHA verification, and regression tests; XRD CI [#42554396816](https://github.com/Frysland-2024/AI4science/actions/runs/42554396816) and V11 migration CI [#42554691047](https://github.com/Frysland-2024/AI4science/actions/runs/42554691047) passed. The `.3` private kit passed its original `start_server.sh --plan`, full shard/cache/manifest checks and bounded CPU smokes. Follow-up CPU and local CUDA interruption/resume regressions pass using the trainer's shared checkpoint functions: a 9-step uninterrupted synthetic run exactly matches a 4-step save/restart/restore/continue run in model parameters, optimizer state, parent draws, history and CPU/CUDA Torch RNG. The CUDA micro-smoke ran on this laptop's RTX 4060 with PyTorch `2.13.0+cu126`; it does not validate the target Linux trainer/prefetch path. The latest source payload contract `.5` has now also been packaged privately from `main` `1f0f691` and passed `start_server.sh --plan`: its 137-file source snapshot, all package ZIP hashes, source checks before/after extraction, all 154,975 PeakTable cache records, and split counts passed. The plan created no study/trial and ran no training. **#61 local scope covers package/schema/manifest, plan-only data readiness and local CPU/CUDA micro-smokes.** Target Linux/CUDA end-to-end smoke, target resource/throughput measurement, GPU full-Validation access and real trainer/prefetch data-cursor recovery remain `BLOCKED / NOT_RUN` and assigned to #55 Stage 0; HPO/formal training still require separate budget and authorization. See [local acceptance receipt](ISSUE61_LOCAL_PREFLIGHT_20261109.md).

**2026-11-09 V11 迁移代码合并：** [PR #70](https://github.com/Frysland-2024/AI4science/pull/70) 已择取 #66/#67 中最新的 `server_migration/` 代码、确定性多进程预取、完整 Validation 面板和 Linux 预检/部署脚本合并至 `main`；源码编译、shell 语法、offline 数据完整性/预取测试的 PR CI [#42501805467](https://github.com/Frysland-2024/AI4science/actions/runs/42501805467) 已通过。#66/#67 已关闭。**这些 CI 仅证明代码集成；完整本机数据包/CPU 预检已由后续本机收据验证。** 目标 Linux GPU readiness 已归入 #55 Stage 0 并仍未运行；没有启动 HPO 或产生 RRUFF-Cu1011 正式评分。

**V11交付与训练边界（2026-11-05）：** PR #58 已合并至 `main`（merge commit `940942d5a9c30307295eb7b7a68c08e47687f955`），V11 模拟器、CIF→paired-view 路径、测试和验收记录已集成。验收记录报告 50 项测试通过、七个 CIF 保持晶系标签；合并提交的 main `XRD tests` CI run [#41965621220](https://github.com/Frysland-2024/AI4science/actions/runs/41965621220) 通过。这些是模拟器工程验证，不是模型训练证据：没有运行 V11 模型训练、HPO 或最终 RRUFF 评测，也没有证明相对 V9/V10 的分类性能提升。154,975-parent 全量 HPO 的 schema adapter/manifest-builder 代码已补入当前 main 并通过离线 CI；本机 package/CPU preflight 已完成。剩余目标 Linux GPU 验收在 #55 Stage 0，云端验收不等于 HPO 授权。

## 2026-11-04 OWNER FINAL BENCHMARK SELECTION — RRUFF-Cu1011 SOURCE MEMBERSHIP FROZEN (before any model inference)

- **Decision: RRUFF-Cu1011 is the official prospective PRIMARY seven-system real-domain benchmark**. Source membership/order, seven-system labels, original RRUFF file hashes and exact 1011 x 3501 V11 preprocessed input are cryptographically **FROZEN**. Do not change IDs due to future accuracy/F1/ECE results. The final checkpoint/HPO must still be selected before any benchmark inference. Model Test remains unrun.
- **Reporting boundary:** Headline zero-shot top-1 Accuracy uses all and only the 1011 primary IDs. Primary Macro-F1 and ECE use the same cohort. The historical 19-case list (15 declared mixed/contaminated + 4 short-range candidates) is a separate case-study record and is distinct from the 19 explicit-Mo records in the later 1034-source audit. No auxiliary predictions are added to the primary metrics. Any ID already frozen in Cu1011 is counted once there under the primary protocol.
- **唯一可执行评分口径：** 正式主基准为已冻结的 **RRUFF-Cu1011（1011 个样本）**；primary zero-shot top-1 Accuracy、Macro-F1、ECE 均只用同一组 1011 个 ID。RRUFF-1030、1032、1034 是先后提议/审计阶段数字，不是可替代主基准；RRUFF-70/301/350/371 仅为历史。旧 19-case（15 个混合/污染候选 + 4 个短角度候选）只作独立历史案例记录；19 个 Mo 辐射源是另一个独立物理分组。任何辅助组不得并入主指标，也不得因预测结果改动 1011 名单。
- **评分前必须完成并记录：** ①逐样本核对原始测量来源及 Cu 波长证据，明确直接证据/推断证据，签核所有剩余波长与来源例外；②核定 7 晶系标签及模型类别索引，审阅 134 个非标准 SG 标记、34 个 RAW–DIF 晶胞差异和保留的混相标记，记录未解决项及负责人决定；③从原始源文件复跑到有序 1011×3501 输入，确认 manifest/input SHA、覆盖掩码、角度修复、插值与归一化行为和冻结输入 preflight 全部通过；④完成仅依赖模拟验证集的 HPO/模型选择，冻结 checkpoint、配置、评估代码、指标定义及评分合同，并确认没有 RRUFF 标签或 holdout 反馈参与训练/选择。四项关闭并留下可审查的签核记录之前，不读取或生成正式模型分数。详见[正式评分门槛](RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md#gates-before-formal-model-scoring)。
- **AlphaDiffract 2026 paper directly checked**: Methods 5.1 uses **1362 curator-background-corrected RRUFF patterns + 2901 DIF** → 2572 metadata-valid DIF → 1880 parseable lattice → 1867 symmetry/volume valid → 837 paired PXRD → 745 crystal-system AND lattice-parameter consistent → **734 post 20-keV Bragg-conversion coverage**. **59 of 734 are calculated**, whereas our source is originally recorded RAW; they use 20 keV/5–20 deg/8192 bins, we use Cu-compatible 10–80 deg/3501 bins. Their published 81.74 ± 0.78% is 10-model ensemble on their distinct 734 IDs. NOT identical test scores.
- **Additional 1011 RAW-vs-DIF lattice cross-check (new):** 758 within max 0.1% axis length and 0.1 deg angles; 219 more within 1% /1 deg; **34** exceed those source cell-difference thresholds, explicitly flagged (not demonstrated wrong seven-system labels). This is NOT independent Niggli/atom-coordinate symmetry validation; 34 remain in the fixed 1011 due to seven-system classification task rather than parameter regression. 134 noncanonical SG B-tier labels, and minor-phase flags, remain clearly marked.
- **Exact frozen SHA checks:** ordered manifest 75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37; 1011x3501 NPZ 19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179; owner freeze JSON d258e3f85506e91867e2d9aebd73b77e2f777636bc6a8b722ebe28bf52129455. Private E:\AI4science\_local\rruff_benchmark_prospective_20261104; no RRUFF Test score accessed.
- **Why 1011:** from 1034 owner-accepted candidates, physically separate 19 explicit Mo-radiation, 3 incomplete Cu 10–80 window and one sparse 232-point XY; avoid comparing unlike radiation or fabricated empty angular data. Original source ZIPs and all historical 910/1049/1045/1030/1032/1034 manifests preserved. Details and exact Alpha methods comparison: [RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md](RRUFF_CU1011_PRIMARY_BENCHMARK_FREEZE_ALPHA_2026_RATIONALE.md).
- Benchmark opponents **Bin Cao XQueryer 1003, Lee, Salgado NPCNN 908 and AlphaDiffract 734** have different RRUFF cohorts and preprocessing. Use published numbers as contextual references; claim same-test ranking only after rerunning baselines on the exact RRUFF-Cu1011 with consistent zero-shot conditions.

## 2026-11-04 SOURCE-AUDIT RECORD — RRUFF-1034 and Cu1011 input prelock

- **Full 1034 original source audit completed**: local original XY_RAW and matched DIF source hash/ID, seven-crystal-system family, native numerical axis, radiation description, fixed V11 preprocessing and no Test/model inference. 0 source hash/ID/SG-family label conflicts in the checked candidate records.
- **1011 directly model-compatible Cu Kα dense experimental RAW spectra with full measured 10°–80° coverage**. This is the source/engineering **PRELOCKED primary** to use for the next formal real-domain zero-shot assessment, replacing homogeneous planned 1034. All 1011 are finite nonnegative max-normalized float32 (1011 × 3501) with 100%-observed-grid mask; results regenerated with identical SHA256.
- **Other 23 prospective records** are not quietly thrown away: **19 explicitly Mo-radiation RAW** require separate measurement-domain handling (11 have incompatible Cu-wavelength matched calculated DIF); **3 Cu-compatible but measured only up to 60°/70°** require separate short-window stress protocol; **1 irregular sparse 232-point Harmotome** is quarantined to avoid fabricating continuous spectra. Explicit Mo spectra can have Bragg-equivalent theta transformed diagnostically, but are not true Cu-radiation intensity measurements.
- Corrected initial source parser mistakes: native scientific-notation intensities recovered (e.g. Hessite range), **19 obvious single-coordinate theta typos** deterministically fixed in derived inputs, **1 duplicate native theta** averaged and **1 physically impossible -2009° metadata/source row** excluded from derived arrays; original source ZIP bytes remain untouched. The earlier “22 incomplete”/“one <30°” first-pass counts were artefacts of uncorrected radiation and numerical parsing and MUST NOT be quoted as final.
- **Class labels:** model-class order explicitly checked; 134 of primary 1011 are B-tier noncanonical DIF symmetry strings, consistent with original RAW crystal-system family (not independently structure-resolved). Trigonal space groups override 'hexagonal' cell-axes notation (129 in primary). Two owner-selected source-mild-mixture records R040049-1/R040064-1 are included in Cu1011 with **not-proven Lee threshold** flags. RAW Cu wavelength often not explicitly recorded and is inferred from paired DIF/peak matching, so source/physical evidence tier remains open.
- **Primary file SHA256:** manifest 75c98cb7ff244121fddd79360ac853c1844661621baacc6cac36258b38f2ab37; complete 1011 × 3501 NPZ 19198cfd4b7e1825522658b1a32b0072557a8a1ed705725c838b9f424d9c9179. Private source and input path E:\AI4science\_local\rruff_benchmark_prospective_20261104.
- **Evidence and protocol:** [RRUFF_1034_FULL_SOURCE_AUDIT_CU1011_PRELOCK_20261104.md](RRUFF_1034_FULL_SOURCE_AUDIT_CU1011_PRELOCK_20261104.md). PRELOCK is source/inputs only; final scientific grade and model Test remain UNRUN. No RRUFF score/HPO selection access. Old historical 70/301/350/371 remains retired for future formal evaluation. Do not claim same test IDs as Bin Cao RRUFF-1003.

## 2026-11-04 HISTORICAL SOURCE VERIFICATION — remaining 13 in the RRUFF-1032 proposal

- After the source-validated two-case expansion to **proposed RRUFF-1032**, all **13 remaining explicitly mixed RRUFF variants** were individually rechecked using original RAW, multiple main/impurity DIF references, peak-overlap inspection, 3 background/smoothing settings, exploratory 2-phase NNLS template-sensitivity analysis, and 13 diagnostic plots.
- Result: **7** with clear source-supported impurity diagnostic peaks exceeding 10% of the observed whole-spectrum maximum (conservative Lee-rejection evidence); **2** with strong *probable* extra-phase contributions (Kutnohorite/unspecified carbonate; Rossmanite/quartz) but no strictly separated Lee ratio; **4** remain Unknown for mild unresolved hematite, chlorite polytype ambiguity, unnamed second phase, or nearly coincident garnet reflections.
- **Zero additional Lee-qualified cases** emerged. All 13 remain outside the proposed 1032 primary cohort; all prior source manifests and the 4 limited-2theta case series remain unchanged. The 7/2/4 breakdown does NOT assert that all 13 have been proved to violate Lee's strict peak-height ratio.
- Full source evidence: [RRUFF_13_MIXED_SOURCE_AUDIT_20261104.md](RRUFF_13_MIXED_SOURCE_AUDIT_20261104.md). Private per-record source hashes and 13 plots under E:\AI4science\_local\rruff_benchmark_prospective_20261104. No trained-model RRUFF/Test inference or HPO selection based on these records. **RRUFF-1032 is a superseded historical proposal, not a pending or executable cohort.**

## 2026-11-04 HISTORICAL PROPOSAL — RRUFF-1032

- The owner proposed revisiting two mild-impurity RRUFF examples and requested additional independent source verification **before** accepting them into the current RRUFF benchmark.
- **Dickite + quartz R090054-1**: source-only conservative upper-bound across 6 quartz DIF reference files x 3 signal processing settings x 4 peak-alignment tolerances. Highest candidate quartz-line measured TOTAL intensity / independently verified Dickite 12.41 main-only peak = **7.60%–7.66%**. High-confidence acceptance for *adapted* Lee-2023 peak-intensity screen.
- **Polylithionite + trace corundum R060215-1**: main 35.15 and corundum 35.17 lines overlap, so direct total mixed peak/main ratio 9.51%–11.09% is **not** the impurity ratio. Using 13 source corundum reference templates x 3 background conditions, separate diagnostic lines yield **7.08%–9.33% estimated** impurity/main peak ratio (conditional on reference intensities/texture). This is a **medium-confidence conditional inclusion**, not proof of a rigorously measured Lee peak ratio.
- **The proposed main cohort at that point was RRUFF-1032**, built from the prior 1030 with these two specifically source-checked additions. Only **13** explicitly mixed samples and **4** limited-2theta samples remain outside the primary candidate cohort. This is a SOURCE-ONLY pre-inference amendment, not score-based sample selection. The proposed membership file is private and labeled NOT FROZEN; no model Test/RRUFF scores have been inspected.
- The prior 1030/15+4 protocol below documents the earlier decision and remains archived for research chronology; RRUFF-1032 was an intermediate proposal superseded by the Cu1011 freeze. Its remaining audit language is historical and does not define open work for a 1032 cohort; the only operative pre-score gates are the Cu1011 gates above. See [RRUFF_TWO_LEE_BORDERLINE_FINAL_SOURCE_AUDIT_20261104.md](RRUFF_TWO_LEE_BORDERLINE_FINAL_SOURCE_AUDIT_20261104.md).

## Historical proposal (superseded): RRUFF-1030 primary + 19 case studies

**Archive only — the following proposal text does not define the current benchmark or authorize scoring.** Its 1030 primary and 19-case roles were superseded by the owner’s final RRUFF-Cu1011 freeze.

**Historical additional owner rule for the 15 declared-mixture cases:** Apply Lee et al. (2023) peak-height criterion: independently attributed secondary-phase strongest observed XRD peak must be <=10% of the main-phase strongest peak to qualify as relatively pure. Lee applied this to *its own 52-powder Ex_dataset_1*, not to Lee's RRUFF set; our extension to RRUFF is adapted. The source descriptions' wt% values are NOT a substitute. **2026-11-04 source-only measured-peak audit result:** 7 samples have clearly attributable impurity-marker heights >10% of the **global** observed profile peak (strong conservative Lee-rejection evidence); 2 have about 7.0%/7.6% low diagnostic-height ratios (PROVISIONAL, NOT confirmed Lee passes); 6 cannot be reliably attributed (Unknown). All 15 raw profiles and named secondary DIF references were inspected with three baseline/smoothing settings and source-only QA figures; the two low values do not bound other overlapped impurity reflections. See [RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md](RRUFF_15_LEE_SOURCE_PEAK_ATTRIBUTION_AUDIT_20261104.md). At that historical stage, the RRUFF-1030 proposal stayed unchanged; it was later superseded by the final RRUFF-Cu1011 decision. See the Lee amendment in [RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md](RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md).

- **Primary cohort in that proposal:** **RRUFF-1030**, all seven crystal systems, with same-variant RAW/DIF pairing, no explicit calculated-pattern description, valid six cell parameters, RAW 2theta width >=30 degrees and **no explicitly declared extra phase/impurity**. Primary result will report Macro-F1, Accuracy, ECE and per-class statistics, only after HPO/checkpoint choice is frozen.
- **Separate prespecified challenge cases (19), never pooled into the 1030 primary denominator:** **15 explicit mixed/contaminated patterns** + **4 samples with original 2theta width <30 degrees**. Evaluate all cases with the same frozen checkpoint for qualitative failure/uncertainty analysis (not multi-phase decomposition). Do not select favorable examples post hoc.
- This supersedes earlier candidate-only recommendations for 910, 1049 or 1045 as the **primary** test definition. The 1045 comprises the 1030 primary and 15 explicit mixed-phase cases; the four shorter-range cases remain separate. At that time these were pre-registered candidate roles. They were later superseded and are not the current scientific freeze.
- By owner decision, RRUFF-70, RRUFF-301, RRUFF-350 and RRUFF-371 are retired from **future formal comparisons**; preserve historical work, files and figures as research evidence but do not use their scores for headline conclusions.
- Historical protocol: [RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md](RRUFF_1030_MAIN_19_CHALLENGE_EVAL_PROTOCOL_20261104.md). The actual row/ID lists and SHA stay in private local `E:\\AI4science\\_local\\rruff_benchmark_prospective_20261104`; no Test/RRUFF model inference during tuning.

## 2026-11-03 LATEST OWNER DECISION — old V10 HPO cancelled; six-cell A0/A1/A2 retained; 154,975-structure cloud HPO next

**Execution decision (this overrides contradictory older sections below, especially old Stage-3 'collection paused' and old Stage-2 sequential Optuna plans):**
- **Keep the existing six-cell A0/A1/A2 × R0/R1 V10 study running until the last A2_R1 finishes; archive, do not re-run.** At direct local inspection on 2026-11-03 **five of six cells were complete**, `A2_R1` still running and unaffected.
- **Stop the legacy-data 9,842-train-parent V10 Optuna follow-on.** Verified the Optuna supervisor was only at `waiting_previous` with **zero new adaptive GPU trial launches**; operator terminated only its three processes (**47944, 7024, 15928**) and verified the independent A2_R1 trainer remains live. Cancellation evidence on the laptop: `E:\AI4science\_local\resnet_optuna_20261103\owner_cancelled_20261103.json` and `supervisor_state.json: cancelled_by_owner`. **Do not restart or reconnect this old Optuna job after the six-cell run ends.** An existing monitoring automation was updated to watch/notify the six-cell completion only.
- **New database is ALREADY collected and split, not a future acquisition job:** **154,975 MP-ID rows**, **154,968 independent parent fingerprints**, **train 108,478 independent parents** (108,483 records), validation 23,245 (23,246 records), test 23,245 (23,246 records), stratified **70/15/15**. Local evidence directly checked at `D:\AI4science_external_data\pxrd_scale_sources_20261103\processed\merged_154975_parent_split_20261103`; `delivery_validation.json` reported `passed`, no malformed structures or cross-split parent leakage, all 14,060 historic IDs retained. The evidence source is local commit **a181f36** on `feat/issue-53-simulator-v11`, now also mirrored as [STRUCTURE_LIBRARY_154975_SPLIT_EVIDENCE.md](STRUCTURE_LIBRARY_154975_SPLIT_EVIDENCE.md) on `main`; compressed structure shards remain external on D:. These are **structure shards**, not a completed simulated PXRD spectrum corpus.
- **Next priority is cloud execution readiness and REAL full-dataset HPO:** V11 is implemented and passed bounded test on seven CIFs + one real library sample per crystal system, but still needs its structure-schema adapter, corpus-scale peak-table build, audits, and GPU throughput proof. **All real HPO candidate configurations run on the new 108,478-parent TRAIN split and 23,245-parent Validation**; use small subsets only for code/throughput smoke, NOT final HPO selection. Preserve locked Test and RRUFF for final evaluation. Consider a rented Tencent GPU machine after readiness gating; hardware rental is **not yet authorized/executed**.
- **Bounded new HPO:** use V10 A0/A1/A2 results as backbone/stride/kernel screening information, select on NEW V11 validation, approximately 6–8 full-data single-seed HPO trials + 2 finalists multi-seed and ~3 fixed-seed final models as compute allows, **not automatic five-seed repetitions for every trial**. Plan link: [PXRD 154,975-parent cloud HPO execution plan](PXRD_154975_CLOUD_HPO_EXECUTION_PLAN_20261103.md). Final 3 project outputs unchanged: **RRUFF real zero-shot Accuracy, independent-parent data-efficiency curve, ECE**.



**阶段（2026-11-03 最新负责人决策）：** 本科毕设已经重启；当前主线为 **PXRD 七晶系分类 + same-parent Dynamic JS**。研究按四阶段推进：**① 模拟器构建（工程阶段已完成）→ ② 模型架构优化（进行中：V10 判断是否换 CNN11，随后 Codex 对选定架构自动调结构和训练超参数）→ ③ 增加经过验证的独立 CIF 数据 → ④ 最终训练和 RRUFF 文献对标跑分**。不再将调参拆出去、放到数据扩容之后；不再开启新的模拟器研究主线。冻结历史结果不改，参数反演仍归档。

## 2026-11-03 earlier owner status snapshot (historical; superseded by LATEST OWNER DECISION above)

**Owner explicitly states in the latest conversation:** (1) the new physically grounded simulator has been constructed, (2) the new structure database has **already been collected**, and (3) **hyperparameter optimization is underway**. **Do not present Stage-3 data collection as work still needing to be started solely because the older Issue #61 text says PAUSED.** However, this is a user-reported dataset-completion claim: the source manifests, unique-CIF counts, dedup audit and integration in final training were **not reverified in this status update**, so do not assert a validated or training-integrated dataset or invent its size. The local acquisition working directory cannot itself establish the collected-data count.

**Direct local execution verification (2026-11-03):** 4060 Laptop 8 GB GPU online; A0_R0, A0_R1, A1_R0, A1_R1 completed in six-cell V10 campaign; **A2_R0 running (~39,000/49,280 steps at last log inspection)**; **A2_R1 yet to run**. A separate Optuna supervisor is **alive but waiting_previous**, so do **not** claim Optuna has begun adaptive trial training. Follow-on automatic tuning is queued to run sequentially after the six-cell evidence. The observed A2_R0 training loop was roughly 11 steps/sec late in the run, **not a benchmark of the expanded dataset**.

**Decision implication:** Seeds and server rental are not additional research stages. Use one seed for exploratory selection, about 3 independent seeds for final model confirmation / headline metrics, and only increase to 5 if score variability or narrow threshold margins warrant. No immediate need to rent the newest accelerator while the current local campaign runs; reassess cloud GPU when the verified new dataset is connected and representative end-to-end training time, VRAM and throughput are measured. Preserve existing running jobs.

## 2026-11-03 — FINAL owner-defined RRUFF acceptance scorecard (current)

**Owner's 2026-11-03 latest acceptance correction: ONLY zero-shot RRUFF seven-crystal-system top-1 Accuracy may enter the 60/80/100 grading table.** Here zero-shot means **zero labeled RRUFF samples used for training or fine-tuning**; our final trained model must also be chosen without optimizing on a locked RRUFF test. **PASS/60: Vecsei et al. 2019 Dense/MLP, 70.0% (now a qualifying pass comparator), Lee 2023, 74.24%, AND Salgado 2023 synthetic-only NPCNN, approximately 74%. 80 points: AlphaDiffract 2026, 81.74 ± 0.78% (PRIMARY/newest 80-tier competitor). FULL/100: SimXRD-4M 2025 CNN11, 89.3%, and XQueryer-NoElem 2025, 91.5%.** Salgado's **86%** result uses ~452 labeled RRUFF spectra for training, so it is **EXCLUDED from final zero-shot grading** (retain as background literature only). AlphaDiffract used zero labeled RRUFF samples for fitting but analyzed RRUFF noise and inspected RRUFF performance to choose some settings: label **RRUFF-informed / not strictly target-domain-blind**, rather than falsely implying pure blind zero-shot. Grades are owner-defined reference tiers, not accuracy percentages and not direct matched-test claims.

**2026-11-03 acceptance-tier clarification (latest owner decision):** **Vecsei et al. 2019 — Dense (MLP), RRUFF Accuracy 70.0%, is explicitly INCLUDED in the PASS/60 tier**, alongside Lee and synthetic-only Salgado. Vecsei's CNN 56.0% stays a below-pass comparison variant. This makes **70.0% the lowest named pass-tier literature reference**, without implying different papers used an identical RRUFF test cohort. All comparisons remain zero labeled RRUFF training/fine-tuning; the 80/full tiers and data-efficiency + ECE outputs are unchanged.

**2026-11-03 comparator-inclusion clarification:** In addition to the five anchor papers that define the **pass / 80 / full thresholds**, include **DiffractGPT 2025 (Choudhary, DGPT-formula)** as a **legitimate zero-labeled-RRUFF literature comparator** in the *same* RRUFF Accuracy comparison and future presentation, with **28.75%** re-evaluated by AlphaDiffract 2026 on its own RRUFF cohort. This is a **below-pass reference**, not a fourth scoring threshold. Its chemical-formula input is a disclosed condition, **not an exclusion criterion**; no claim of a pure PXRD equal-input head-to-head or original Choudhary 28.75% figure is made. See [RRUFF model comparison library](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md).

**Exactly THREE headline research outcomes:** (1) **RRUFF-Cu1011 zero-shot top-1 Accuracy and the literature grading references above**; (2) **independent-CIF-parent data-efficiency curve**; (3) **ECE confidence calibration**, always with the measured domain declared. RRUFF accuracy alone assigns a grade, while the other two are supplementary research outputs. Internal synthetic validation OOD F1 may guide model selection but never substitutes for final RRUFF classification performance.

**2026-11-03 latest user-approved SLIDE five-column scorecard:** **Grade | Paper / model | Simulated training structure count (distinguish actual post-split train CIFs from curated corpus) | Real RRUFF evaluated spectrum count | RRUFF top-1 Accuracy.** All graded literature comparators have **0 labeled RRUFF training/adaptation**, so label-adaptation and non-PXRD metadata are explanatory footnotes, not columns cluttering the headline. Full completed six-row table and original source links: [RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md](RRUFF_ZERO_SHOT_MODEL_COMPARISON_LIBRARY_20261103.md). Key verified details: Vecsei 2019 **114,404 actual training** structures out of 128,404 deduplicated corpus, RRUFF ~800; Salgado **171,006 curated** / ~908 RRUFF entries; Lee **197,131 curated** / estimated ~960 retained (actual unknown); AlphaDiffract **312,267 curated records** / 734 RRUFF; SimXRD **119,569 unique** / RRUFF **≈1,003 HIGH-CONFIDENCE INFERENCE from Bin Cao's own doctoral thesis Chapter 3 (3,002 catalog → only 1,003 usable), although exact Table-5 scored denominator/IDs remain unconfirmed**; XQueryer-NoElem **100,315 structures** / 1,003 RRUFF. This is literature benchmarking with differing test cohorts, not same-test matched experimental evidence. Preserve lockout of RRUFF Test from HPO; Stage 3 CIF expansion remains gated on Stage 2 and does not start merely because the target scoreboard is defined.

## 2026-11-03 earlier four-stage sequence (historical; superseded by LATEST OWNER DECISION above)

**Owner logic:** Every step must answer a useful, distinct question. **Simulator construction is already done as an engineering deliverable** (V11 has working code and tested acceptance; PR merge/integration housekeeping is separate from a new research stage). The goal is improved absolute real-domain classification performance, not an endless menu of experiments.

1. **Stage 1 COMPLETED — Simulator:** Build a usable, source-informed physical PXRD simulator with same-parent paired views and regression tests. The remaining PR #58 status should be handled as merge/integration housekeeping, not a prerequisite to invent another simulator.
2. **Stage 2 ACTIVE — Architecture optimization INCLUDING hyperparameter tuning:** The existing V10 same-simulator pilot determines whether the current ResNet-18-GN should be retained or replaced with CNN11. First diagnose CNN11 first-seed NaN in local training and finish valid comparable runs **[Issue #60](https://github.com/Frysland-2024/AI4science/issues/60)**; this is not proof that CNN11 is worse. Then use Codex to conduct a **bounded optimization of the selected architecture** **[Issue #55](https://github.com/Frysland-2024/AI4science/issues/55)**: stride/kernel size/depth/width where appropriate, learning rate/schedule, JS lambda, weight decay, batch and exposure/step budget. Architecture screening **and tuning** form one stage. No repeat broad architecture sweeps, and no GPU overlap with existing jobs.
3. **Stage 3 — CIF data expansion [Issue #61](https://github.com/Frysland-2024/AI4science/issues/61):** Add more unique, valid crystal parents with source, labels, fingerprint dedup, parent-disjoint split, class coverage and cached peak validation. Data scale is unique CIF parents, not regenerated spectra; target counts follow audit feasibility rather than a mandated 100k.
4. **Stage 4 — RRUFF benchmarking:** Train the selected optimized model on the expanded data and report RRUFF-Cu1011 zero-shot top-1 Accuracy, Macro-F1 and ECE after the scoring gates close. Locked real test is not used for selecting hyperparameters.

**As-of check:** local three V10 ResNet seeds complete; CNN11 seed-1 reached nonfinite CE/JS loss around step 20k, so the backbone decision is **OPEN**. There is no completed stage-2 tuning, expanded dataset or final RRUFF benchmark claim. Historical 2026-11-03 text below is retained as dated planning snapshots and is **superseded where it conflicts with this sequence**.

**最近文档同步（2026-10-29）：** PR #50 已合并到 main，统一了 README、当前状态、项目历史和导师说明中的既有证据边界；没有新增实验或结果，也没有改变 2026-10-26 确定的毕设范围。

## 2026-11-03 PR #58 — V11 reference-scale correction and evidence boundary

V11’s area-normalized TCH peaks cannot use the legacy V9 Gaussian reference scale: in the Gaussian limit, an isolated 0.08° peak would be scaled to about 0.399, unintentionally changing the relative background and count-space Poisson-noise settings. PR #58 calibrates the reused pipeline at the V11 integration boundary using the actual rendered V11 peak maximum (`reference_scale_mode="renderer_peak"`). The standalone renderer keeps its area normalization, and V9 retains its legacy default scale.

**Verification (checked 2026-11-05):** Commit `c486be7` passed [GitHub Actions run 41659169247](https://github.com/Frysland-2024/AI4science/actions/runs/41659169247): 134 non-data-bound tests in 19.71s. The completed Codex review covers the earlier `b43e28d`, not the latest head. Focused tests assert that V11’s preclip maximum is 1.0 and that the V9 default matches the legacy Gaussian mode. The recorded V11 acceptance run also checks fixed-seed replay, all seven crystal-system labels, V9 regression, broadening trends, and integrated peak area. The validation record reports no model training.

**Evidence boundary:** These checks support simulator and paired-view engineering behavior. They do not establish a V11 model-training or HPO result. Follow-on model work is governed by the current sequence and readiness gates above.

## 2026-11-03: PXRD thesis research resumed (NEW DECISION; supersedes 2026-10-26 execution pause)

**Decision / owner confirmation:** The project lead explicitly stated that the undergraduate thesis has restarted. The 2026-10-26 decision to *stop new work and write up only* is therefore **superseded for forward execution**. It remains a correct historical snapshot, and all completed reports/configurations/predictions remain frozen. Reopening investigation is **not** permission to overwrite old results.

**Phase 1 delivery upgrade (owner, 2026-11-03):** The expected deliverable is a **runnable, versioned simulator integrated with same-parent JS paired views, accompanied by a working CIF→two-spectra CLI, tests and examples** — **NOT** a literature-only audit report. Source review and module comparisons are internal implementation steps. [Executable Codex implementation issue #54](https://github.com/Frysland-2024/AI4science/issues/54). The issue is a handoff, not proof that Codex has started; the legacy research bridge cannot modify `xrd_robustness/` without a separately approved route.

**Earlier delivery snapshot (2026-11-03, superseded by PR #58): Phase 1 is an implementation task, not a report.** The owner requested finished, runnable, test-verified simulator code adapted from useful upstream implementations. At that point, execution was pending because the authorized local Desktop Commander machine was offline and the legacy `research_bridge` lane prohibited `xrd_robustness/` writes. That restriction and the instruction not to claim completion before PR/run evidence describe the earlier snapshot; PR #58 and its validation record now provide the implementation and run evidence. This history does not claim model training.

**2026-11-03 updated research decision (V10 / automatic ResNet tuning):** The project lead clarified that the **ongoing V10 three-configuration trial is sufficient to decide whether a CNN11 Backbone replacement is necessary**; its principal purpose is a *ResNet-vs-CNN11 decision on a fixed V10 simulation setup*, not to establish V10 vs V11 simulator superiority. No additional architecture search or second CNN11 campaign is planned. Actual local inspection on 2026-11-03 shows all **three ResNet-18-GN + JS V10 seeds complete**, with CNN11 + JS V10 training started and active; final architecture verdict and real-domain scores are **NOT YET AVAILABLE**. After V10 fully completes and its evidence is frozen, the next Codex action is **bounded, autonomous tuning of the existing ResNet + JS** (stage downsampling/kernel size, LR/schedule, λ_JS, weight decay and training exposures), using a separately accepted validated simulator, in an isolated worktree and without touching the locked RRUFF test for selection. [Queued implementation task #55](https://github.com/Frysland-2024/AI4science/issues/55). This supersedes the prior proposal to require a new architecture comparison after ResNet retuning; the already-running V10 comparison provides the architecture-screening evidence. No new tuning GPU job has been initiated by this decision record.

**New phase-2 priority (2026-11-03, owner clarification):** After the versioned simulator is built and validated, **first retune the existing ML4pXRDs-derived ResNet-18-GN under the same-parent Dynamic JS objective**, *then* compare against SimXRD CNN11 + JS. ResNet adjustments include architectural hyperparameters (downsampling stride, 1D kernel size, optionally channel width/depth/GroupNorm) and optimization hyperparameters (learning rate/schedule, JS lambda, batch size, weight decay, parent exposures / optimizer steps). The old ResNet design's stages with stride=4 and kernel=9 are candidates, not values to preserve without justification. Use a bounded exploratory search and validation-driven selection; preserve old frozen configs and do not tune against the locked RRUFF test. When comparing ResNet and CNN11, allocate comparable tuning/compute opportunities rather than comparing tuned against untuned architectures. This work is **PLANNED AFTER PHASE 1**, not started.

**Execution gate — explicit 2026-11-03 clarification:** **Understand and selectively implement/validate the simulator FIRST; compare model architectures ONLY AFTER the simulator is understood and has passed standalone correctness/reproducibility/performance checks.** No CNN11 training, no architecture leaderboard, and no large-CIF training before this gate. Investigating simulator source is not itself proof of a working upgrade.

**2026-11-03 historical active sequence (SUPERSEDED):** Prior source-audit → simulator → CNN11 pilot → data expansion proposal is replaced by the **four-stage owner sequence stated at top**, where architecture optimization explicitly includes bounded hyperparameter tuning before dataset expansion. No further simulator development is the current science priority.

**Goals:** noticeably improve **absolute experimental RRUFF Accuracy**, report Macro-F1 and ECE, and preserve a fair description of differing paper datasets. This is an **engineering/research objective, not an achieved score**. Borrowing simulator/backbone components does **not** prove any gain is uniquely due to JS. The earlier ResNet-18-GN ERM/JS study remains the basis for the previously demonstrated method effect.

**Unchanged:** parameter-inversion/DONUT tracks remain inactive; CNRS is optional; frozen old reports, datasets, configurations and the previous PR/Issue history remain intact. No claim of supervisor-approved graduation criteria or completed new training is made here.

---

## 2026-10-26: undergraduate-thesis scope (HISTORICAL DECISION, SUPERSEDED FOR NEW EXECUTION ON 2026-11-03)

> The 2026-10-26 section below is retained verbatim as the dated scope freeze and evidence boundary, not the current instruction to stop all new work.

**唯一当前毕设主线：** PXRD 七晶系分类中的同母结构关系监督研究。研究问题是：利用在线模拟器已知的同一母结构身份，将不同测量视图之间的关系作为额外监督，能否在匹配设置下改善分类？核心对照是 ResNet-18-GN 上的 Dynamic JS Consistency 与 Dynamic ERM。

**当前阶段：** 对已完成并冻结的分类证据进行整理、报告和答辩准备；本次决策不包含新实验，也不包含扩容任务。

| Evidence | Current thesis role | Qualification |
| --- | --- | --- |
| Simulated OOD, five matched seeds | Core result; Dynamic JS Macro-F1 gain **+5.46 percentage points** over Dynamic ERM. | Frozen study and split; report as a bounded result, not universal superiority. |
| RRUFF-301 K=1/2/5 and CNRS-318 | Supporting completed evidence, separate from the core comparison. | RRUFF is few-shot, not zero-shot; CNRS absolute accuracy is low and the corrected paired-parent interval crosses zero. |
| Parent-budget study | Supplementary post-main result. | The simulated Test had already been used; no quantitative structure-saving claim is supported. |
| PR #46 parameter-inversion benchmark | **Archived / exploratory only; excluded from evidence for the classification method.** | See the archival disposition below. |

### PR #46: partial parameter-inversion benchmark archived on 2026-10-26

PR #46 completed primary synthetic scoring for 42 models and 8,085 per-parent records, but its overall status was **PARTIAL**. The q-accuracy gate passed **0/42**; the per-DOF cell-MAE constraint passed **41/42**; convergence was no worse in 42/42 and the amortized runtime gate passed 41/42. These are descriptive results from a bounded synthetic setup, not proof that parameter inversion is accurate, robust, or superior.

The held-out parent set had already been evaluated in PR #43, so this was not independent confirmation. New-architecture stress was **BLOCKED_NOT_RUN**; real RRUFF validation was **BLOCKED / NOT RUN**. It was not an exact reproduction of XQueryer, SimXRD-4M, CPICANN, or PyWPEM. These parameter-inversion workstreams are **ARCHIVED / INACTIVE** for current thesis execution; that status does not erase PR #36's separate completed conditional result, described below.

**Claim disposition:** withdraw any claim that PR #46 established method superiority, validated real-data inversion, or reproduced those literature methods. Downgrade the completed matrix, cell-MAE/convergence/runtime passes, and 8,085 rows to exploratory engineering evidence with the limitations above. Do not use them as the thesis's scientific result.

### PR #36: 已完成的条件性合成参数反演证据

PR #36 当前为 closed、unmerged draft；分支中的 [最终技术报告](https://github.com/Frysland-2024/AI4science/blob/codex/donut-pxrd-experiment-20261019/donut_pxrd/reports/FINAL_TECHNICAL_REPORT.md) 标注四阶段 COMPLETE。实验只使用一个已知 COD 9014273 BaTiO3 P4mm CIF；512 个参数母样本在扰动前固定分为 358/77/77，使用 3 个模型种子，测试部分为 77 个母样本（231 个样本-种子记录）。这足以保留为一个已完成、条件严格的合成可行性结果。

| PR #36 阶段 | 冻结报告中的 normalized-q MAE | 边界 |
| --- | ---: | --- |
| 固定仪器参数 | 0.344228 | 单 CIF 合成任务 |
| 联合晶格与零点偏移 | 0.398342 | 显示参数耦合；局部灵敏度绝对余弦 0.924875 |
| 峰宽 / 背景 / 噪声 / 织构压力测试 | 0.457009 / 0.139752 / 0.228037 / 0.291768 | 不同条件，不应横向混为同一主指标 |
| Exp 4 直接 A/B/C / DONUT-PXRD | 0.033607 / 0.033578 / 0.034282 / 0.228037 | 231 个样本-种子记录；直接模型输出 |
| 同一预算的 joint q+instrument L-BFGS-B 精修后 A/B/C / DONUT-PXRD | 0.000343 / 0.000350 / 0.000341 / 0.080026 | 231 次拟合；这些是精修后值，不是网络直接预测值 |

同一报告中的中性初值 L-BFGS-B q-MAE 为 0.050608（77 个测试母样本），各项报告的拟合失败率为 0%。精修后 A/B/C 几乎相同，不能据此声称某个神经方法优于其他方法或强传统多起点物理精修。这个结果仅支持：在已知候选结构、单相、单一冻结生成器的合成插值条件下，网络初值与受限物理精修这条流程可运行并恢复该测试集的参数。它不证明真实测量准确度、未见 CIF/成分泛化、多相能力或通用 PXRD 反演；也不能把 DONUT-PXRD 在此协议下的表现外推为原始 2D DONUT 方法在 PXRD 上失败。报告中的 checkpoint 与生成数组为本地文件，仓库可追溯元数据/哈希，但不含完整重训所需工件。

### 相关 PR 与未合并分支的当前证据边界

| 记录 | 当前状态与可保留内容 | 不支持的结论 |
| --- | --- | --- |
| PR #42 | Closed/unmerged 的决策与研究旅程文档；它不是新增实验。其 DONUT 摘要数值与 PR #36 最终报告不一致，PR #36 最终技术报告为该实验的数值依据。 | 不应引用 PR #42 摘要替代冻结报告，也不构成额外验证。 |
| PR #43 | Closed/unmerged；完成七个受支持合成 CIF 模板、覆盖三个晶系的有限子集。主实验中 N+A q-MAE 与三起点 P3 基本持平；P0 在五种材料上已达到相近精度，在 MgO 和 ZnO 上误差较大。另一个主测试打开后登记的 renderer/peak-shape/background 压力测试使用每种材料 16 个新母样本，未发现相对 P0/P3 的额外精度或可靠性收益。 | 不等于七晶系覆盖、零样本未见材料迁移或真实 XRD 有效性。 |
| PR #45 E1 | Closed/unmerged；七种合成材料的启发式/物理初值比较完成；没有材料通过对 H1/P0 的预注册增量价值规则。 | 不支持广泛神经初始化优势。 |
| PR #45 E2 | **PHYSICS_NOT_READY / NN_NOT_RUN**；三条 RRUFF Rutile 谱均未通过预先物理门控。 | 没有真实谱神经推理、真实域参数准确率或泛化结果。 |
| PR #48 | 2026-10-20 已合并到 main，内容是导师展示与七晶系分类叙事。 | 不构成参数反演证据。 |

### Deferred work

The 2026-10-23 scale-up plan and Issue #49 (new RRUFF zero-shot evaluation, calibration, larger-parent training, simulator upgrade, training retuning, and architecture comparison) are **DEFERRED** as of this decision. They are not current thesis tasks or acceptance gates. No new data acquisition or experiment is being initiated.

Related: [frozen classification results](../xrd_robustness/reports/RESULTS.md), [current supervisor brief](START_HERE_FOR_SUPERVISORS.md), [historical PR #46](https://github.com/Frysland-2024/AI4science/pull/46), [project history](PROJECT_HISTORY.md), [deferred scale-up plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md).

### 2026-10-23: CNRS downgraded to optional second real domain

**User decision:** CNRS is an **optional second real-domain showcase**; it is not required for any of the three headline metrics or the next-stage RRUFF competition. The primary measured-data result remains RRUFF.

**Presentation policy:** Do not allocate main benchmark leaderboard space or new training budget to CNRS by default. It may appear as a separate supplementary external-domain robustness/generalization case if its independently defined dataset quality, task relevance and full evaluation make that informative. **Do not select reports/models/checkpoints or decide whether to disclose completed experiments solely on whether the scores look good.** In any paper or report making broad cross-domain claims, cite the completed CNRS evaluation with its low absolute Accuracy/Macro-F1 and uncertainty, even if detailed plots are in supplementary materials. Existing fixed CNRS-318 results stay public and immutable (JS zero-shot pooled Accuracy 0.2000 → 0.2101; Macro-F1 0.1912 → 0.2091; ECE 0.6826 → 0.6124). Current results show a modest paired relative gain, not high absolute accuracy.

**Status:** historical presentation decision for the completed CNRS evidence, not a current experiment. Under the 2026-10-26 thesis scope, report the existing CNRS result only with its low absolute score and uncertainty; do not start a new CNRS or RRUFF evaluation.

### 2026-10-23 scale-up proposal: simulator and training retuning (DEFERRED 2026-10-26)

**Historical proposal:** At the time, the proposed prerequisites were a more complete reference-guided online dynamic PXRD simulator and re-selection of training settings after data/simulator changes. This proposal is retained for chronology only; it is not part of current thesis execution.

**Historical sequence:** audit sources and simulator coverage → versioned physics changes → physical/label checks → paired old/new pilot → expanded-parent pilot and validation-only tuning → matched ERM/JS scale-up → RRUFF, ECE and parent-budget evaluation. None of these steps is authorized by the current 2026-10-26 scope.

**Sources/status:** [deferred plan](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md), [existing perturbation evidence](PXRD_PERTURBATION_EVIDENCE.md), [Issue #49, deferred](https://github.com/Frysland-2024/AI4science/issues/49). **DEFERRED / NOT IMPLEMENTED.**

### Deferred technical options (not current thesis tasks)

以下均是 2026-10-23 的扩展提案，已于 2026-10-26 推迟；不是当前研究 TODO 或毕设验收门槛。若未来要恢复，需另行确定时间、问题和资源，不能从历史计划直接启动。

- 增加独立训练母结构，并审计各晶系覆盖、去重与拆分。
- 设计带版本的新在线动态 PXRD 模拟器。
- 在数据和模拟器改变后重新选择训练设置。
- 条件性比较其他分类架构。

详情见[历史扩容计划](PXRD_SCALEUP_SIMULATOR_AND_TUNING_PLAN_20261023.md)。当前没有实现、下载或训练这些提案。

## 1. 已完成的科学方法与冻结实验设计

当前已经完成的项目首先是一个**监督学习方法研究**：在线 PXRD 模拟器不仅能生成带晶系标签的谱图，还知道哪些谱图来自同一个母体结构。项目要回答的是：能不能把这种 parent provenance 转化为额外的 measurement-equivalence / relationship supervision，使相同晶体结构数据库提供比普通类别标签更多的监督信息，并由此提高七晶系分类、分布外泛化、真实域迁移和少标签适配表现。

冻结历史研究的实验设计：

- 任务：七晶系分类；
- 骨干网络：ResNet-18-GN；
- 基线：Dynamic ERM；
- 选定方法：Dynamic JS Consistency，一致性权重 `lambda_js=60`；
- 预处理：不做额外处理；
- 优化器：AdamW；
- 学习率：恒定；
- 划分：训练 9,842 / 验证 2,109 / 测试 2,109；
- 划分方式：按母体结构严格分开，训练/验证/测试不共享同一母体。

当前方法贡献的统一表述是（一级 framing 见 [`PXRD_SUPERVISION_FRAMING.md`](PXRD_SUPERVISION_FRAMING.md)）：

> **shared parent identity → measurement equivalence → relationship supervision**

传统 online PXRD simulator 主要承担 `data generator` 的角色；本项目进一步利用 simulator-retained parent identity，使其同时成为 **data generator + relationship supervisor**。JS consistency 是这一 measurement-equivalence supervision 的具体实现，而不是项目声称发明的新算法。

### 当前标签口径

- **项目本体：** supervised learning / PXRD crystal-system classification；
- **方法核心：** structured / relational supervision from simulator provenance；
- **具体实现：** JS consistency regularization；
- **实验设置/结果：** simulated OOD generalization、CNRS zero-shot cross-domain evaluation、RRUFF few-shot adaptation / label efficiency、probability calibration；
- **大领域背景：** AI4Science / AI for Characterization。

`robust learning`、`representation learning`、`domain adaptation`、`computer vision`、`physics-informed ML` 均不再作为整个项目的一级标签；其中只有 RRUFF K-shot 子实验可准确称为 target-domain adaptation。

## 2. 已经做完的事

- 在验证集上跑完了五组配对实验；
- 在选好的模型上完成了模拟测试集评估；
- 固定了模型、数据、扰动、优化器和训练量；
- 把公开的结果和论文的说法统一了；
- 精简了公开文件，只留下训练、评估和核对结果需要的部分；
- 明确当前结果不再通过新增 loss、重新调参或重开训练改变；
- 完成 RRUFF-301 的 K=1/2/5 locked-test few-shot 评测并回溯核验结果；当前直接按 Macro-F1、Accuracy、mean ± SD、paired consistency 与 learning curve 报告；
- 完成 CNRS-318 的 10-checkpoint zero-shot 外部域评测、原始输入复建和结果完整性审计；
- 完成模拟 Test 与 CNRS 的概率可靠性审计；
- 完成跨平台换行规范化哈希校验与全量回归测试（`117 passed`）；
- 完成五类扰动物理/文献依据的当前主线汇总，确认该问题不是新的科研 TODO；
- 完成 RRUFF-301 adaptation/test 的只读 composition audit：301 个 RRUFF ID 全部唯一，ID overlap = 0，spectrum-SHA overlap = 0，16,170 个跨 split 谱图对中 maximum Pearson = `0.947785`，没有 Pearson ≥ 0.95 的近重复谱。

### 2.1 本轮三个问题的最终状态

权威结案文档：[`PXRD_EVIDENCE_CLOSURE.md`](PXRD_EVIDENCE_CLOSURE.md)。

| 问题 | 状态 | 当前处理 |
|---|---|---|
| 五类扰动的物理/文献依据 | **CLOSED** | 已有系统 evidence；后续只在 Methods / PPT / 答辩中调用，不重新调查 |
| RRUFF-301 composition / near-duplicate 检查 | **CLOSED** | 无相同 RRUFF ID、无相同谱、无 Pearson ≥ 0.95 的跨 split 近重复谱；不修改 frozen split |
| 新颖性 framing | **ACTIVE WRITING** | 当前最高优先级；打磨 `simulator = data generator + relationship supervisor`，不是补实验或加算法 |

除非未来 scientific claim 明显改变，否则前两个问题不再重新开启。

## 3. 结果与当前评价口径

主科学判断采用 PXRD / Materials ML 社区常用的 performance-reporting 范式，并按三层证据组织：Macro-F1、balanced accuracy、accuracy、mean ± std、多 seed 一致性、few-shot learning curve、label efficiency 和 per-class F1 是主 performance layer；ECE/NLL/Brier 等是 reliability 增强证据；paired/class-stratified parent bootstrap、95% CI 与不确定性分解是 strict statistical audit。单个 CI 跨 0 不再自动把整体一致的结果判成失败。当前权威规范见 [`PXRD_RESULT_REPORTING_STANDARD.md`](PXRD_RESULT_REPORTING_STANDARD.md)，方法论转变的历史缘由已归并进 [`PROJECT_HISTORY.md`](PROJECT_HISTORY.md)。

这项修正只改变证据层级，不改变实验或原始结果：不得删除不利统计结果、隐藏跨零 CI、看结果后换指标、修改 frozen test 数据、重选 checkpoint/seed、反复重跑到满意，或改写历史 raw outputs。

| 指标 | Dynamic ERM | Dynamic JS | 配对提升 |
|---|---:|---:|---:|
| 模拟验证集 · 单因素分布外 Macro-F1 | 0.658495 ± 0.007417 | 0.705064 ± 0.005841 | Δ `+0.046569`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Macro-F1 | 0.65074 ± 0.00721 | 0.70534 ± 0.00977 | Δ `+0.054600`；5/5 为正 |
| 模拟测试集 · 单因素分布外 Accuracy | 0.65078 ± 0.00780 | 0.70524 ± 0.00856 | Δ `+0.054454`；5/5 为正 |
| RRUFF-301 · K=1 few-shot locked-test Macro-F1 | 0.2847 ± 0.0269 | 0.3280 ± 0.0329 | Δ `+0.0433`；21/25 为正 |
| RRUFF-301 · K=1 few-shot locked-test Accuracy | 0.2990 ± 0.0259 | 0.3375 ± 0.0299 | Δ `+0.0384`；20/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Macro-F1 | 0.3026 ± 0.0407 | 0.3486 ± 0.0335 | Δ `+0.0460`；23/25 为正 |
| RRUFF-301 · K=2 few-shot locked-test Accuracy | 0.3120 ± 0.0383 | 0.3609 ± 0.0343 | Δ `+0.0488`；23/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Macro-F1 | 0.3555 ± 0.0302 | 0.4099 ± 0.0271 | Δ `+0.0545`；24/25 为正 |
| RRUFF-301 · K=5 few-shot locked-test Accuracy | 0.3581 ± 0.0273 | 0.4149 ± 0.0252 | Δ `+0.0568`；23/25 为正 |
| CNRS-318 · zero-shot seed-level Macro-F1 | 0.18837 ± 0.02634 | 0.20708 ± 0.02134 | mean paired Δ `+0.01871 ± 0.00675`；5/5 为正 |
| CNRS-318 · zero-shot pooled Macro-F1（描述性） | 0.19118 | 0.20912 | `+0.01794` |
| CNRS-318 · zero-shot Balanced Accuracy | 0.21823 | 0.23878 | `+0.02055` |
| CNRS-318 · zero-shot Accuracy | 0.20000 | 0.21006 | `+0.01006` |
| CNRS-318 · zero-shot ECE ↓ | 0.68257 | 0.61242 | `−0.07015`（更低为好） |

表中 `±` 均为对应重复运行的 sample standard deviation；完整 mean±SD、paired consistency 与结果说明见 [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)。

结果与证据文件：

- [`PXRD_EVIDENCE_CLOSURE.md`](PXRD_EVIDENCE_CLOSURE.md)
- [`PXRD_PERTURBATION_EVIDENCE.md`](PXRD_PERTURBATION_EVIDENCE.md)
- [`../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md`](../xrd_robustness/reports/RRUFF301_COMPOSITION_AUDIT.md)
- [`../xrd_robustness/reports/RESULTS.md`](../xrd_robustness/reports/RESULTS.md)
- [`../xrd_robustness/reports/validation_results.json`](../xrd_robustness/reports/validation_results.json)
- [`../xrd_robustness/reports/simulated_test_results.json`](../xrd_robustness/reports/simulated_test_results.json)
- [`../xrd_robustness/reports/rruff301_fewshot_results.json`](../xrd_robustness/reports/rruff301_fewshot_results.json)
- [`../xrd_robustness/reports/CNRS_318_RESULTS.md`](../xrd_robustness/reports/CNRS_318_RESULTS.md)
- [`../xrd_robustness/reports/CALIBRATION_ANALYSIS.md`](../xrd_robustness/reports/CALIBRATION_ANALYSIS.md)

## 4. 当前实现

主要实现：

- [`../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py`](../xrd_robustness/src/xrd_robustness/models/ml4pxrd_resnet1d.py)
- [`../xrd_robustness/src/xrd_robustness/training/objectives.py`](../xrd_robustness/src/xrd_robustness/training/objectives.py)
- [`../xrd_robustness/src/xrd_robustness/simulator.py`](../xrd_robustness/src/xrd_robustness/simulator.py)
- [`../xrd_robustness/src/xrd_robustness/online_views.py`](../xrd_robustness/src/xrd_robustness/online_views.py)
- [`../xrd_robustness/src/xrd_robustness/training/runner.py`](../xrd_robustness/src/xrd_robustness/training/runner.py)
- [`../xrd_robustness/scripts/audit_rruff301_composition.py`](../xrd_robustness/scripts/audit_rruff301_composition.py)

结果已经确定，不会再改。公开仓库里只留当前实现、运行配置、结果和使用文档；安装项目后通过 `xrd-train` 调用可复用训练入口，分数看已有模型的评估结果文件。

这里说的“结果已经确定”包括模拟部分和两个角色不同的实验域。CNRS 的结果是
**zero-shot 外部域压力测试**，不是使用 CNRS 标签做域适配；冻结配置保持原样，执行完成状态由
结果报告和 run record 另行记录。

## 5. 实验进度

方法对比、验证集和模拟测试集的评估都做完了，模拟部分的结果已经确定、不会再改。

既有真实域结果的当前定位：

- **RRUFF-301**：平衡、人工整理的实验域。已完成 K=1/2/5 few-shot 历史评测和 split composition audit；共享 mineral identity 被保留，因为该任务并非 unseen-mineral benchmark。下一阶段新增的主要外部评测将是明确协议的 RRUFF zero-shot 结果及可比基准。
- **CNRS-318**：自然不平衡的独立实验域（类别数 `21 / 87 / 77 / 41 / 33 / 12 / 47`），已完成 frozen-model zero-shot 评测。自 2026-10-23 起仅作为 **Optional Secondary Experimental Domain**，不是必须完成的核心评价轴。

既有两个真实域结果均保留，但不合并成一个分数：

- CNRS-318 的权威审计与父样本 manifest 已进入 git（见 [`xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md`](../xrd_robustness/reports/CNRS_318_DATASET_AUDIT.md) 和 [`xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv`](../xrd_robustness/manifests/cnrs_318_parent_manifest_v2.csv)）；
- 评测已按冻结协议执行完毕；pre-run 协议文件保持原样，完成状态与纠错记录见结果报告和 run record（[`xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md`](../xrd_robustness/reports/CNRS_318_EVALUATION_PROTOCOL.md)）；
- 人工标签质量复核**不计划执行**：标签由 deposited structure 稳定重建、未做人工物相核验，这一限制将如实注明；
- 真实数据不参与模型、checkpoint、seed 或 `lambda_js` 选择；
- CNRS-318 的五个 seed 均 favor JS，平均配对 ΔMacro-F1 为 `+0.018713`；pooled Macro-F1、balanced accuracy、accuracy、ECE、NLL 与 Brier 共同改善。修正后的 class-stratified paired-parent 95% CI 为 `[−0.009339, +0.046107]`，说明自然类别不平衡和低支持类别带来较大的统计不确定性；该区间作为严格审计如实保留，但不单独否决上述多 seed、多指标一致的科学结果；
- CNRS 的绝对 sim-to-real 表现仍弱、校准仍差；overall accuracy `0.200→0.210` 低于多数类基线 `0.274`，不能包装成已解决的真实域分类。

## 6. 历史汇报与论文封装待办（2026-10-20 快照；不定义当前科学任务）

以下清单记录 2026-10-20 的论文/展示整理计划，状态可能已变；它们不是新一轮科学实验优先级。当前毕设范围以本文件开头的 2026-10-26 决策为准，扩容计划已延期。

当这些文字或图表需要更新时，仍须以冻结结果为准：

- **最高优先级：**把 `shared parent identity → measurement equivalence → relationship supervision` 做成论文/PPT 的统一方法叙事；
- 制作核心方法图，明确对照 `simulator = data generator` 与 `simulator = data generator + relationship supervisor`；
- 生成五种扰动图、同源双视图方法图和配对结果图；
- 完成仿照“组会1”视觉语言的阶段汇报；
- 完成方法、结果和讨论正文；
- 确保公开结果、图表和讲稿中的数字完全一致。

这里的 framing 工作**不是新实验，也不是算法扩张**。不要重新把项目包装成“JS consistency 用于 XRD”；应把 JS 放在 measurement-equivalence relationship supervision 的下游实现位置。

## 7. 历史展示与论文整理提案（2026-10-20 快照；当前范围以 2026-10-26 决策为准）

1. 首先打磨并固定方法新颖性 framing：`simulator from data generator to relationship supervisor`。
2. 把该 framing 做成 PPT / manuscript 的核心方法图，视觉重点放在 `shared parent identity → measurement equivalence → supervision`，而不是把 JS 画成最大创新模块。
3. 从 `reports/validation_results.json`、`reports/simulated_test_results.json` 和真实域结果文件生成论文与 PPT 图表。
4. 完成 Introduction、Methods、Results 和 Discussion，使标题、摘要、方法图和公开项目叙事使用同一套 measurement-equivalence 语言。
5. 将技术报告、方法图和一页项目摘要整理为可公开复用的成果材料。
6. 把 RRUFF-301 few-shot 与 CNRS-318 zero-shot 分表写入正文并补齐结果图；不重开模型选择、不修改 frozen split、不事后删改真实域样本。

复现当前工程检查的命令：

```powershell
cd xrd_robustness
python -m pytest -q
```

## 8. Archived / Inactive：独立数值反演与旧毕业研究候选

**状态（2026-10-23）：本节所列参数反演、晶格参数预测、Forward Loss 与自动精修均为 Archived / Inactive。** 唯一主动科学任务是本文件前述 PXRD 七晶系分类。此处保留早期计划及其边界，不能作为执行清单或恢复研究路线的依据。

**既有数值反演分支：** `xrd_inversion/` 已有正向模型与数值可恢复性基础设施（见 [README](../xrd_inversion/README.md) 和 [Week-1 报告](../xrd_inversion/reports/WEEK1_FORMAL_REPORT.md)）。早先以结构/测量参数解耦为核心的 Stage-1 方案，在预注册机制 Gate 中获 **NO-GO**，已于 2026-09-07 封存（见 [归档](archive/XRD_FACTORIZATION_STAGE1_ARCHIVED_20260907.md)）；数值基础设施的存在**不等于**该算法假设通过或获得重新开跑许可。

**历史提案（2026-10-08；2026-10-23 已归档）：** 如果硕士申请时本科毕业论文尚未正式开始，拟把毕业研究安排在 AI 辅助材料表征领域。候选课题为：从 PXRD 输入谱预测限定材料体系的结构/测量参数，再通过前向物理模型重构理论谱，以重构差异作为**可能的辅助训练约束**；比较常规参数监督与物理辅助方法，研究参数预测准确性、数据利用效率、训练成本及其在真实实验谱上的适用边界。

- 这是当时的 **FUTURE / CANDIDATE** 提案；目前状态为 **ARCHIVED / INACTIVE**，不是正式毕业论文题目、已启动实验或既定成功方法。
- “预测参数 → 重构理论谱”已有相关研究，不能直接当作原创算法；谱图相似不必然意味着真实参数正确。
- 初期优先限定单相、已知候选结构、有限连续参数（如四方晶格参数、零点偏移与峰宽），先核验参数可辨识性和正向模型；是否加入参数解耦、传统精修或其他模态，由独立验证结果决定。
- 本次计划**不复活**旧解耦 Stage-1 NO-GO，也不影响当前 JS-only 论文或 frozen tests。

原提案见 [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md)，仅供历史追溯；若将来改变科学方向，必须先记录新的明确决策。

### 2026-10-18：铁电陶瓷预精修 12 周提案（ARCHIVED / INACTIVE；原提案未启动）

以下为 2026-10-18 的历史研究提案，2026-10-23 起已归档、不再属于当前下一阶段：在当时的连续参数＋可微重构 Loss 候选思路基础上，曾考虑一个面向真实应用的方案：**一个待定铁电陶瓷家族、模拟谱主训练、Top-K 单相结构候选及经模拟域检验的概率校准、逐候选参数初值与不确定性、物理正向核验、精修前指导**。学长少量真实谱主要用于外部案例，不作为主训练集。重构 Loss 降为可选消融，不作为项目启动的必需步骤。

**两相共存不被排除**：12 周主任务暂以候选单相为核心，但必须用物理合理的合成混相作单相假设失配压力测试，允许 `REVIEW_REQUIRED` 拒判；进一步两相模型提示仅为可选，质量分数定量另立后续课题。**单相 Softmax 的 70% R / 30% C 是互斥候选解释概率，不是两相含量。** ECE 是模拟域可靠性评估，不保证真实域概率准确。

本规划**不是已实施工作、已批准开题或对旧 xrd_inversion/JS 主线的改写**。详情与每双周里程碑见 [FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md](FERROELECTRIC_PRE_REFINEMENT_12W_PLAN.md)。旧 [FUTURE_UNDERGRAD_THESIS_PLAN.md](FUTURE_UNDERGRAD_THESIS_PLAN.md) 原文保留作为 10 月 8 日历史提案。

### 2026-10-18：PXRD AutoLab 工程支持提案（科学首个用例已归档）

[PXRD AutoLab 工程方案](PXRD_AUTOMATED_RESEARCH_PIPELINE_PLAN_20261018.md) 保留为工程自动化设计记录。其历史首个参数反演/Forward Loss 用例已归档；AutoLab 工程代码本身不是第二个科学研究任务，也不授予训练权限。

该方案当时规划了人工审阅协议下的 Gate、A/B、报告与人工审核；**它不是当前主动科学路线，也没有代表自动实验或新结果**。任何工程维护仍须服从 2026-10-23 唯一科研任务及本仓库的安全规则。

## 9. 2026-10-13 独立母结构效率实验提案（历史快照；已于 10-14 完成）

本段保留 2026-10-13 提案原貌，后来由下方 2026-10-14 完成记录取代。实验比较 **10% / 25% / 50% / 100% 的 Train 母结构预算曲线**，检验相同独立结构数、双视图曝光和优化预算下 Dynamic JS 与 Dynamic ERM。

- 本实验是现有 `shared parent identity → relationship supervision` 主张的**独立补充机制/效率验证**，不是新模型、不是 RRUFF few-shot 标签效率，也不替代冻结的主实验。
- 采用原 Train 9,842 母结构的晶系分层嵌套子集；ResNet-18-GN、`lambda_js=60` 不变；配对 seed 和模拟协议固定，训练曝光量/优化步数必须统一。
- 已识别工程风险：目前公共 `runner.py` 的 epoch 末尾可能有不完整 batch，而且每 epoch 进行验证与保存，不适合直接充当完全公平的预算比较入口。CODEX LUNA 应先完成独立固定步数入口、数据审计、单元测试与 smoke，才能执行大规模 run。
- 当前模拟 Test 已在正式论文中使用过；本次应标明为 **post-main supplementary follow-up**，不能声称是全新未打开的 confirmatory Test。
- 提案当时的状态为 **PROPOSED / READY FOR CODEX IMPLEMENTATION / NOT_RUN**；该状态随后被下方完成记录取代。原主实验的报告、划分、权重和历史结果均未修改。


## 10. 2026-10-14 已完成的母结构预算补充实验（post-main）

The formerly proposed parent-budget experiment is complete: 4 budgets (984/2460/4921/9842) × 5 seeds × 2 methods = 40 scored models, 20 pairs. At each budget Dynamic JS outperformed matched Dynamic ERM on the simulated Test by +0.05607 / +0.05173 / +0.04261 / +0.05396 Macro-F1 respectively, with 5/5 paired seeds positive at every budget. The already-used Test makes this explicitly post-main supplementary evidence. No measured budget crossing supports a quantitative crystal-structure saving claim. Full frozen protocol, raw aggregates, audit limitations and figures: [PARENT_BUDGET_EFFICIENCY.md](../xrd_robustness/reports/PARENT_BUDGET_EFFICIENCY.md).

Research-role clarification (reported by project lead): Across the project, **Frysland-2024 has been the principal designer and planner of the scientific approach**, responsible for overall research direction, experimental design and changes in project strategy. This includes the main same-parent JS study, simulated OOD validation, the RRUFF and CNRS real-domain experiments, and the parent-budget/Data Efficiency design. **Cuifa01 participated primarily in executing these plans**, giving auxiliary ideas and feedback, helping collect/organize data, and contributing software implementation, GPU experiments, desktop transfer and other operational work. Supporting ideas and execution should not be presented as joint overall project design or leadership. This clarifies roles without changing original Git authorship, executed data, or independently determining formal manuscript authorship.
