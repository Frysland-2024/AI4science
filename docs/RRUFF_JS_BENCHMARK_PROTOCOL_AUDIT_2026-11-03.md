# RRUFF literature protocol and simulation-scale audit — 2026-11-03

**Status:** source audit complete for accessible paper text, supplements, author repositories and dataset descriptions. All four candidate protocols are **PARTIAL**; none supports a strict reproduction with the currently verified cohort and split artifacts. Missing quantities are marked **Unknown** and are not imputed.

**New-stage scope:** our runs use the existing ResNet-18-GN and Dynamic JS. We do not reproduce the papers' architectures. Where a paper used labeled RRUFF data, a matching amount may enter our real-data CE fine-tuning stage after a disjoint train/validation/test split is frozen. Synthetic views may use JS only when a shared CIF parent is recorded. Real RRUFF samples without an audited parent mapping are never made into JS positive pairs.

## Protocol comparison

| Paper / protocol | RRUFF source → evaluated cohort | Seven-system labels / coverage | RRUFF train / validation | Unique synthetic parents and generated views | Actual training volume / rounds / compute | Input and instrument | IDs, preprocessing, status |
|---|---|---|---|---|---|---|---|
| **Lee et al. 2023 — 74.24%** | About 1,600 RRUFF patterns extracted; final retained count after removing the top 40% by low-angle background standard deviation: **Unknown** | Seven-way crystal-system task; per-class RRUFF coverage **Unknown** | Train 0; a separate RRUFF validation split is **Unknown**; the retained RRUFF set is used for evaluation | **197,131 ICSD compounds**; 10 texture-free + 20 texture-involved perturbed patterns per parent = **5,913,930 reported patterns**. The large FCN selects the texture-involved set (**3,942,620 before its split**). | Actual train rows after compound holdout **Unknown**. 40 A100/A10 GPUs reported; epochs, optimizer steps, elapsed time and GPU-hours **Unknown**. | Synthetic input 5–86.91° 2θ, 0.01° step, 8,192 points, peak heights 0–1. RRUFF instrument/preprocessing **Unknown** | Paper says top-1 Accuracy and Table 2 gives 74.24%. Exact retained denominator and RRUFF IDs/split absent. Public repo exposes Ex_dataset_1 and notebooks; availability of complete Ex_dataset_2 is not verified, while data statement says corresponding-author request. Supplement listed by Wiley but inaccessible this session. **PARTIAL** |
| **Salgado et al. 2023 — 86% souping** | Paper reports 908 RRUFF entries; **452** real patterns are put in training. Other 50% is test, but exact test count is **Unknown** (908 total vs 452 train is unreconciled). Post-curation denominator **Unknown** | Seven-way task, but the reported RRUFF data contain six represented systems and **no trigonal samples** | 452 train; validation count/protocol **Unknown**; remaining half test, IDs not published in a split manifest | 204,654 ICSD CIFs before curation → **171,006 retained parents**. “Large” synthetic data is reported as **about 1.2 million**; 7 variants/parent imply **1,197,042 nominal patterns**, exact successful count **Unknown**. | About 1.2m synthetic patterns plus 452 real training spectra are described; exact synthetic train-row count is **Unknown**. Adam, batch 256, softmax cross-entropy. Actual LR, steps, epochs, hardware and wall time **Unknown**. Repository default `train_steps=500000` is recipe evidence only, not verified for the 86% run. | 5–90° 2θ, 0.01° step, Cu wavelength 1.54 Å, max normalized to 1000. No single harmonized RRUFF instrument condition | Article and public arrays/code available; public loader does not expose sample IDs or split membership. Local SI was read; it does not identify the RRUFF cohort. **PARTIAL** |
| **Cao et al. 2025 — SimXRD-4M, 89.3%** | Paper's catalog table lists 3,002 RRUFF patterns/structures; exact Table 5 retained denominator and IDs **Unknown** | Seven-system label mapping is explicitly listed; Table 5 per-class RRUFF counts **Unknown** | Train 0, validation 0; paper says train/validate on SimXRD and test on RRUFF | MP filter leaves **119,569 unique structures**. Paper reports **4,065,346** views and 33 conditions. Author repo documents **3,587,070 train**, 119,569 validation, 239,138 test and 119,569 no-target views. Whether the extra view belongs to the paper's stated 33 conditions is **Unknown**. | Repository train volume is 30 views/parent (3,587,070). Whether this exact repo split/checkpoint generated Table 5 is **Unknown**. Batch 128, LR 2.5e-4, max 50 epochs, patience 3, CE, RTX 3090; actual epochs, steps, GPU-hours **Unknown**. | 3,501 d-I values; 1.199–8.853 Å d-spacing / 10–80° 2θ, 0.02° step; max intensity 100. Exact Table 5 RRUFF transform **Unknown** | Official code and data are public, but the exact SimXRD checkpoint/split and RRUFF Table 5 cohort are not identified. No separate supplement found; article includes appendices. **PARTIAL** |
| **Cao et al. 2025 — XQueryer-NoElem, 91.5%** | Paper reports **1,003** valid RRUFF samples for crystal-system classification. A secondary thesis gives 2,088 XY_RAW–DIF matches → 1,003 retained; structure-matching subset is 849 and is not the 1,003 classification denominator | Seven-system output; per-class counts **Unknown** | Train 0, validation 0; RRUFF is external evaluation. The 21:2 and 21-fold protocol is for simulated data, not RRUFF | **100,315 MP structures × 23 patterns = 2,307,245 nominal spectra**; actual successful generated file count **Unknown** | Actual synthetic training-view count **Unknown**; the reported 21:2 / 21-fold settings are not enough to infer it. Batch 128, LR 2.5e-4, maximum 100 epochs, patience 5, CE, RTX 3090; actual epochs, steps and GPU-hours **Unknown**. | Paper says 10–80° and 3,500 points; official matching script interpolates to 3,500 and max-normalizes to 100. Whether that exact path made every 1,003 classification input is **Unknown**; another benchmark loader uses 3,501 points | Official repo exposes matching files but not a confirmed full 1,003-row test manifest; OneDrive contents could not be inspected. Formal supplement was inaccessible this session. **PARTIAL** |

## Paper-specific notes and source trail

### Accuracy calculation and denominator

The benchmark runner defines its own primary metric as `number of top-1 correct predictions / number of test spectra`; Macro-F1 is the unweighted mean of the seven per-class F1 values. Its ECE uses 15 equal-width confidence bins. Paper reports are kept at the precision and aggregation level the source actually provides:

| Paper | Accuracy calculation disclosed | RRUFF denominator / aggregation |
|---|---|---|
| Lee et al. | Explicitly uses one-top accuracy for the seven-way crystal-system task (rather than top-3/top-5) | Post-filtered Ex_dataset_2 count is **Unknown**; about 1,600 source patterns and top-40% exclusion do not determine the exact denominator |
| Salgado et al. | Reports 7-way test accuracy for the remaining half after training with 452 real examples | Exact held-out count and any validation count are **Unknown**; 908 reported entries do not reconcile with 452 training + exactly 50% test |
| SimXRD-4M | Table 5 reports Accuracy; no alternative top-k metric is indicated for crystal-system classification | Exact Table 5 RRUFF count and sample manifest are **Unknown**; 3,002 is the catalog count, not a confirmed metric denominator |
| XQueryer-NoElem | Table 1 reports NoElem accuracy as 91.5% ± 1.5% for seven-system classification | Paper reports 1,003 RRUFF classification samples; repeat/split count underlying ±1.5% is **Unknown**; complete tested ID manifest unavailable |

For SimXRD and XQueryer, the source gives the metric name and reported result but the exact test rows/aggregation inputs cannot be independently reconstructed from the released panel artifacts. We therefore do not infer a denominator or calculate a paper-equivalent error bar.

### Lee et al. 2023

The 74.24% is Table 2's crystal-system Accuracy for the large FCN tested on RRUFF Ex_dataset_2. The 90.38% result is for a separate 52-sample commercial-powder dataset, not RRUFF. The paper states 1,600 patterns were extracted and removes the highest 40% under a background-variation rule around 5–8° 2θ; it does not give an auditable post-filter denominator. We do not infer that 960 remained. The table reports top-1 accuracy; report the paper number without recasting it as Macro-F1.

The model's synthetic source is 197,131 retained ICSD compounds. Ten texture-free and twenty texture-involved realizations are generated per parent. The article gives aggregate generated counts and says the large model uses the texture-involved set, but does not disclose the final number of training rows after its compound-based holdout. It reports use of 40 GPUs (A100 and A10) without training duration or optimizer-step count. The official repository README advertises 197,131 standard and perturbed patterns; its visible tree contains Ex_dataset_1 but not a verified complete Ex_dataset_2 release, while the article data statement points to the corresponding author.

Sources: [original paper](https://doi.org/10.1002/aisy.202300140), [official code/data repository](https://github.com/socoolblue/Advanced_XRD_Analysis), [RRUFF downloads](https://www.rruff.net/about/download-data/).

### Salgado et al. 2023

Keep the paper's settings distinct: the **74%** synthetic-only NPCNN result and the **86%** “Souping Large Dataset” result are not the same RRUFF training protocol. The 86% run uses 452 labeled RRUFF patterns in training plus about 1.2 million synthetic patterns, and evaluates on the remaining half. The paper says the full RRUFF collection has 908 entries and no trigonal examples; it does not reconcile the 452 training count with a precise held-out denominator or provide sample IDs for that split.

The paper reports 171,006 retained ICSD CIF parents after removing incomplete and duplicate structures. Its seven simulated datasets are four peak-shape settings and three additional intensity-noise settings. The seven-per-parent product (1,197,042) is arithmetic implied by the design and is consistent with the rounded “1.2 million”; the exact successful file count is **Unknown**. The public repo's 500,000-step default is not substituted for an undocumented historical run record.

Sources: [original paper](https://doi.org/10.1038/s41524-023-01164-8), [official code and preprocessed arrays](https://github.com/AGI-init/XRDs), [public default recipe](https://github.com/AGI-init/XRDs/blob/main/Hyperparams/base.yaml), [RRUFF downloads](https://www.rruff.net/about/download-data/).

### SimXRD-4M

The paper reports 4,065,346 patterns, 119,569 structures and 33 conditions. The repository describes supervised train/validation/test collections of 30 + 1 + 2 views per parent, plus 119,569 test-without-target views; these repository factors sum to 4,065,346. The paper does not explain whether that extra view is inside or outside the stated 33 conditions. We preserve this discrepancy explicitly. Its in-library split repeats a parent across splits under different simulated views; its out-of-library split separates parent structures. These are distinct evaluation tracks.

Table 5 reports CNN11 Accuracy 0.893 and Macro-F1 0.920 after training/validation on SimXRD and testing on RRUFF. The table's exact RRUFF sample denominator and IDs, and the exact SimXRD checkpoint/split used for the table, are **Unknown**. Do not treat the catalog's 3,002 RRUFF records as the confirmed table denominator.

Sources: [ICLR 2025 paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/b04843d76c9f090beca55f335c4ea6bf-Paper-Conference.pdf), [official repository and data-distribution notes](https://github.com/Bin-Cao/SimXRD), [CrystDB card](https://huggingface.co/datasets/caobin/CrystDB), [RRUFF data collection](https://huggingface.co/datasets/AI4Spectro/rruff), [official RRUFF downloads](https://www.rruff.net/about/download-data/).

### XQueryer-NoElem

Table 1's **91.5% ± 1.5%** is NoElem seven-system classification; 70.3% is the different structure-identification task. The main article describes 1,003 RRUFF patterns in the crystal-system task. The detailed 2,088 → 1,003 cleaning trail was found in a thesis copy of the authors' work and is secondary evidence; 849 refers to the separate structure-matching subset. Per-class counts and the exact RRUFF test split remain **Unknown**.

The synthetic generation design is 100,315 MP parents and 23 patterns per parent, or **2,307,245 nominal views**; an exact successful-file count and actual training-view count are **Unknown**. The 21:2 ratio and 21-fold protocol describe simulated evaluation, not an RRUFF train/test partition, and are insufficient to infer the actual XQueryer training-row count. The NoElem model masks the elemental input. The official matching code's 3,500-point resampling cannot be assumed to be the only preprocessing path for all 1,003 class samples.

Sources: [original paper](https://doi.org/10.1093/nsr/nwaf421), [official XQueryer repository](https://github.com/Bin-Cao/XQueryer), [XqueryerBench](https://github.com/WPEM/XqueryerBench), [official matching script](https://raw.githubusercontent.com/Bin-Cao/XQueryer/main/match/main.py), [RRUFF downloads](https://www.rruff.net/about/download-data/).

## Reproduction status and next execution choice

| Protocol | Status | Main missing condition | Approximate execution possible? |
|---|---|---|---|
| Lee | **PARTIAL** | Exact post-filter RRUFF denominator/IDs and train-view split; supplement unavailable | Yes after source cohort recovery; label as approximate if IDs remain unavailable |
| Salgado | **PARTIAL** | Exact 452/held-out RRUFF ID split and final synthetic file count | Yes with a newly frozen split and 452 training rows; not an exact split reproduction |
| SimXRD | **PARTIAL** | Table 5 RRUFF IDs/denominator and exact SimXRD checkpoint/split | Yes with a public SimXRD-sized parent collection, but not a strict Table 5 reproduction |
| XQueryer-NoElem | **PARTIAL** | Full 1,003-sample test manifest and formal supplement | Yes if the authors' data bundle can be obtained and verified |

None is labelled READY. The first near-literature simulation target is **100,315 unique parents**, matching XQueryer's reported parent count and near SimXRD's 119,569. It is a target, not a run. A staged 30k → 60k → 100,315 curve is configured. Formal training is gated on a verified public parent source, a prospective RRUFF panel, simulator readiness and an explicit compute budget.

## Next actions, ordered by blocker and cost

1. **Build the prospective RRUFF row manifest from the permitted local archives.** Resolve IDs to seven-system labels, record every exclusion, archive/source hashes, preprocessing, per-class coverage and duplicate-spectrum groups. Then freeze a new train/validation/test split without touching `rruff70`, `rruff350` or `rruff371`. This is the lowest-cost blocker shared by all four papers; it creates a reproducible *approximate* panel but does not recover any paper's private split.
2. **Finish a no-download CIF-parent inventory for COD and the MP-derived CrystDB route.** Establish account/terms feasibility, seven-system candidate counts, invalid/disordered CIF rates, deduplication against existing frozen parents, expected simulated-view storage/compute and a GPU-hour budget. COD is the independent-source candidate; CrystDB is access-conditioned and non-commercial according to its card. No parent count should enter the curve until these filters are audited.
3. **First approximate execution candidate: SimXRD external-test protocol**, because it uses zero real RRUFF training and the authors publish both code and a parsed RRUFF collection. It remains PARTIAL: its Table 5 row manifest/checkpoint link is not available. Use the new panel only under an explicit approximate label, and do not launch the 119,569-parent run before the inventory and budget gates pass.
4. **Next candidates:** XQueryer-NoElem if its linked 1,003-row bundle becomes inspectable; then Salgado if a six-system panel and 452 real-train subset can be frozen; Lee after its retained Ex_dataset_2 cohort and transform can be reconstructed. These are not READY today. Promote a protocol only when its data and split artifacts support the named execution; otherwise keep it PARTIAL and report Unknown fields.

The three smoke runs satisfy the implementation-level training/inference/evaluation check on the local CUDA environment. They do not make any literature protocol READY and are not substitutes for the prospective RRUFF panel or for a scale-curve point.

## Current benchmark execution

The completed training smoke runs are `SMK-20261103-01` and `SMK-20261103-02`; each uses 21 train / 7 validation / 7 test spectra from the repository's explicitly smoke-only 35-sample fixture. Run 01 initializes from the frozen Dynamic JS checkpoint and fine-tunes on real spectra with cross-entropy. Run 02 first applies one Dynamic JS epoch to seven distinct parents from the historical training split, then CE fine-tunes on the real smoke fixture. Neither run forms real JS pairs. A third test-only smoke, `SMK-20261103-03`, evaluates a frozen Dynamic JS checkpoint on seven fixture spectra with zero training or validation rows; it verifies the external-test-only route needed by zero-RRUFF-training protocols. All three are pipeline checks, not literature scores.

All smoke records and provenance are under `xrd_robustness/reports/rruff_benchmark/experiments/`. Their distinct seven-sample test splits measured: Run 01 Accuracy 1/7, Macro-F1 0.0952, ECE 0.5794; Run 02 Accuracy 3/7, Macro-F1 0.3333, ECE 0.3703; Run 03 Accuracy 0/7, Macro-F1 0.0000, ECE 0.8308. These are pipeline diagnostics only and are not ranked or used to select hyperparameters. Full local outputs, split manifests and derived checkpoints remain under the ignored `xrd_robustness/outputs/rruff_js_benchmark/` folder.

## Published accuracy versus this stage's measurements

| Protocol | Published RRUFF Accuracy | Published secondary metric available in the audited source | Our eligible protocol result | Smoke-only result (not comparable) |
|---|---:|---|---|---|
| Lee et al. 2023 | 74.24% | Macro-F1/ECE: **Unknown** | Not run; PARTIAL, cohort denominator and IDs unavailable | Not run against this paper's protocol |
| Salgado et al. 2023, synthetic + real-label souping | 86% | Macro-F1 0.859; ECE: **Unknown** | Not run; PARTIAL, exact split IDs unavailable | Not run against this paper's protocol |
| SimXRD-4M | 89.3% | Macro-F1 0.920; ECE: **Unknown** | Not run; PARTIAL, Table 5 panel/checkpoint unavailable | Not run against this paper's protocol |
| XQueryer-NoElem | 91.5% ± 1.5% | Macro-F1 0.905 ± 0.020; ECE: **Unknown** | Not run; PARTIAL, complete 1,003-row manifest unavailable | Not run against this paper's protocol |

| Smoke run (separate 35-spectrum fixture) | Test n | Accuracy | Macro-F1 | ECE-15 | Training exposure |
|---|---:|---:|---:|---:|---|
| `SMK-20261103-01` | 7 | 14.29% | 0.0952 | 0.5794 | CE fine-tune on 21 real fixture spectra; 0 new JS views |
| `SMK-20261103-02` | 7 | 42.86% | 0.3333 | 0.3703 | 7 unique cached parents, 14 online JS views and 4 JS steps; then CE on 21 real fixture spectra for 11 steps |
| `SMK-20261103-03` | 7 | 0.00% | 0.0000 | 0.8308 | Frozen checkpoint inference only; 0 RRUFF training/validation samples, 0 optimizer steps |

“Not run” means no benchmark result on an eligible, protocol-specific RRUFF panel. The smoke fixture is deliberately displayed in a separate column to keep diagnostic results visible without implying comparability. ECE and Macro-F1 are not inferred when a paper does not report them.

## Simulation scale and JS scale–performance curve

| Source/experiment | Unique synthetic parents | Generated spectra/views | Per-parent design | RRUFF real spectra used for training | Result status |
|---|---:|---:|---|---:|---|
| Lee et al. | 197,131 | 5,913,930 perturbed patterns reported; selected texture-involved subset 3,942,620 before split | 10 texture-free + 20 texture-involved | 0 reported | Literature scale; final train views after split Unknown |
| Salgado et al. | 171,006 | About 1.2m reported; 1,197,042 implied by 7× parents; exact successful count Unknown | Four Caglioti settings + three intensity-noise variants; exact training-view count Unknown | 452 | About 1.2m synthetic +452 real reported; actual steps/epochs/cost Unknown |
| SimXRD-4M | 119,569 | 4,065,346 reported; repository train split 3,587,070, validation 119,569, test 239,138, no-target 119,569 | Repository counts 30+1+2+1 views/parent; 33-condition reconciliation Unknown | 0 | 3,587,070 repository training views; exact Table 5 run linkage, epochs/steps/GPU-hours Unknown |
| XQueryer-NoElem | 100,315 | 2,307,245 nominal by 23×100,315; exact successful count Unknown | 23-pattern design; actual training-view count Unknown | 0 | Exact synthetic training views, epochs/steps/GPU-hours Unknown |
| `SMK-20261103-01` | 0 new parents | 0 new synthetic JS views; 21 real training spectra | Inherited frozen Dynamic JS checkpoint; CE-only real fine-tuning | 21 | Smoke only; excluded from the curve; original checkpoint's verified parent count not asserted here |
| `SMK-20261103-02` | 7 unique parents (selected from the existing frozen train split; no structures newly acquired) | 14 online-generated JS views; 21 real training spectra | One synthetic epoch / 4 JS steps; one real CE epoch / 11 steps | 21 | Smoke only; excluded from the curve; parents come from frozen historical training split |
| `SMK-20261103-03` | 0 new parents (initialized checkpoint's earlier parent count is Unknown) | 0 new JS views; 0 real training spectra | Frozen checkpoint inference only; 0 optimizer steps | 0 | Smoke only; excluded from the curve; test-only interface validation |

| Planned JS training-parent point | Closest published scale | Training views / optimizer steps / cost | RRUFF Accuracy / Macro-F1 / ECE | Status |
|---:|---|---|---|---|
| 30,000 | Below all four published scales | Not measured | Not measured | Planned |
| 60,000 | Below all four published scales | Not measured | Not measured | Planned |
| 100,315 | Matches XQueryer; close to SimXRD 119,569 | Not measured | Not measured | Planned, first near-literature-scale target after gates |

There are **zero eligible points** on the new JS parent-scale versus RRUFF Accuracy curve as of this audit. All three smoke runs use intentionally tiny seven-sample test splits and are excluded. The 100,315 target is a plan, not a claimed run. Formal scale-up remains gated on a verified parent source/simulator, a prospective disjoint RRUFF protocol panel and a recorded compute budget. The runner records online-generated view count, optimizer steps, elapsed time, peak GPU allocation and measured RRUFF Accuracy, Macro-F1 and ECE for future eligible points.

## Scope notes

- Do not modify or re-use the locked RRUFF-70/350/371 evaluation panels for tuning. The 371 contract explicitly sets `real_test_execution_authorized=false`; the 70-sample panel is frozen external test-only. The 35-sample fixture is the only one used here.
- Accuracy is the primary comparison. Macro-F1 and ECE are secondary. The 15-bin ECE definition matches the current project utility.
- All new experiments must have independent IDs, split hashes, checkpoint hashes, raw logs, and an explicit “paper-comparable” flag. No test score may be used for repeated hyperparameter choice.
- The full published models are not being reimplemented. We borrow their data/label/training/evaluation protocols for our Dynamic JS model, and disclose all deviations.
